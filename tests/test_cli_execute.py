import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from research_workbench.capability import (
    AcceptedSkillRegistry,
    AgentProfile,
    resolve_task_from_registry,
)
from research_workbench.cli import main
from research_workbench.contracts import to_plain
from research_workbench.context.models import checkpoint_digest
from research_workbench.io import load_document
from research_workbench.tasks import TaskPacket


ROOT = Path(__file__).resolve().parents[1]
SCRIPTED_SESSION = ROOT / "examples" / "api-execution" / "scripted-session-evidence.json.txt"
ATTEMPT_ID = "AT-CLI-001"
SECRET_MARKER = "fake-key-marker-that-must-not-appear"


def run_cli(arguments: list[str]) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        try:
            code = main(arguments)
        except SystemExit as exc:  # argparse usage errors exit before the handler runs
            code = exc.code if isinstance(exc.code, int) else 2
    return code, output.getvalue()


def prepare_project(root: Path) -> Path:
    """Copy the frozen Task/Registry inputs into a scratch root and resolve the Assignment."""
    shutil.copytree(ROOT / "examples", root / "examples")
    shutil.copytree(ROOT / "registry", root / "registry")
    shutil.copytree(ROOT / ".agents" / "skills", root / ".agents" / "skills")
    # The scripted Provider declares text/tools/structured_output for any model,
    # so the bound slot must not pin a reasoning_effort.
    pool_path = root / "registry" / "models" / "pool.example.yaml"
    pool_path.write_text(
        "\n".join(
            [
                "schema_version: 0.1.0",
                "registry_kind: model_pool",
                "pool_id: test-pool",
                "selection_policy: explicit-slot-only",
                "slots:",
                "  - slot_id: primary",
                "    role: primary",
                "    provider_adapter: openai-responses",
                "    model_env: RWB_PRIMARY_MODEL",
                "    enabled: true",
                "    capabilities: [text, tools, structured_output]",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    task = TaskPacket.from_mapping(load_document(root / "examples" / "task-evidence.yaml"))
    profile = AgentProfile.from_mapping(load_document(root / "registry" / "agents" / "evidence-scout.yaml"))
    registry = AcceptedSkillRegistry.load(root / "registry" / "skills" / "accepted.json", project_root=root)
    resolved = resolve_task_from_registry(task, profile, registry, resolution_purpose="historical-replay")
    assignment_path = root / "assignments" / "evidence-assignment.yaml"
    assignment_path.parent.mkdir(parents=True)
    assignment_path.write_text(
        yaml.safe_dump(to_plain(resolved), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return assignment_path


def execute_arguments(root: Path, assignment: Path, *extra: str) -> list[str]:
    return [
        "execute",
        "task",
        "--task",
        str(root / "examples" / "task-evidence.yaml"),
        "--assignment",
        str(assignment),
        "--slot",
        "primary",
        "--pool",
        str(root / "registry" / "models" / "pool.example.yaml"),
        "--adapters",
        str(root / "registry" / "providers" / "adapters.yaml"),
        "--root",
        str(root),
        "--attempt-id",
        ATTEMPT_ID,
        "--accountable-owner",
        "Huang Yi test owner",
        *extra,
    ]


class ExecuteTaskTests(unittest.TestCase):
    def test_scripted_session_completes_verifies_and_never_leaks_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            assignment = prepare_project(root)
            with patch.dict("os.environ", {"OPENAI_API_KEY": SECRET_MARKER}, clear=True):
                code, output = run_cli(
                    execute_arguments(root, assignment, "--scripted-session", str(SCRIPTED_SESSION))
                )
                verify_code, verify_output = run_cli(
                    [
                        "execute",
                        "verify",
                        "--attempt",
                        str(root / "work" / "EVID-001" / ATTEMPT_ID),
                        "--root",
                        str(root),
                    ]
                )
            self.assertEqual(0, code, output)
            self.assertIn("status\tcompleted", output)
            for label in ("attempt\t", "receipt\t", "handoff\t", "check_report\t"):
                self.assertIn(label, output)
            attempt_dir = root / "work" / "EVID-001" / ATTEMPT_ID
            for name in (
                "execution-plan.yaml",
                "session-transcript.json",
                "attempt.yaml",
                "execution-receipt.yaml",
                "handoff.yaml",
                "check-report.yaml",
                "completion-manifest.yaml",
            ):
                self.assertTrue((attempt_dir / name).is_file(), name)
            self.assertTrue((attempt_dir / "outputs" / "evidence-record.yaml").is_file())
            self.assertEqual(0, verify_code, verify_output)
            self.assertNotIn(SECRET_MARKER, output)
            self.assertNotIn(SECRET_MARKER, verify_output)
            for path in attempt_dir.rglob("*"):
                if path.is_file():
                    rendered = path.read_text(encoding="utf-8")
                    self.assertNotIn(SECRET_MARKER, rendered, str(path))
                    self.assertNotIn(str(root), rendered, str(path))

    def test_governed_method_capability_execution_closes_the_architecture_loop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            assignment = prepare_project(root)
            code, output = run_cli(
                execute_arguments(
                    root,
                    assignment,
                    "--method-resolution",
                    str(root / "examples/method-resolutions/MR-EVID-001.yaml"),
                    "--capability-snapshot",
                    str(root / "examples/capability-snapshots/RCS-EVID-001.yaml"),
                    "--scripted-session",
                    str(root / "examples/api-execution/scripted-session-evidence.json.txt"),
                )
            )
            attempt_dir = root / "work" / "EVID-001" / ATTEMPT_ID
            verify_code, verify_output = run_cli(
                ["execute", "verify", "--attempt", str(attempt_dir), "--root", str(root)]
            )
        self.assertEqual(0, code, output)
        self.assertIn("execution_identity\t", output)
        self.assertIn("completion_manifest\t", output)
        self.assertEqual(0, verify_code, verify_output)

    def test_governed_resume_pins_the_exact_main_state_predecessor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            assignment = prepare_project(root)
            state = dict(load_document(root / "examples/main-state.yaml"))
            state["active_tasks"] = [{"task_id": "EVID-001", "status": "safe-paused"}]
            state.pop("checkpoint_digest", None)
            state["checkpoint_digest"] = checkpoint_digest(state)
            state_path = root / "examples/main-state-evid-predecessor.yaml"
            state_path.write_text(
                yaml.safe_dump(state, sort_keys=False, allow_unicode=True), encoding="utf-8"
            )
            code, output = run_cli(
                execute_arguments(
                    root,
                    assignment,
                    "--method-resolution",
                    str(root / "examples/method-resolutions/MR-EVID-001.yaml"),
                    "--capability-snapshot",
                    str(root / "examples/capability-snapshots/RCS-EVID-001.yaml"),
                    "--from-state",
                    str(state_path),
                    "--scripted-session",
                    str(root / "examples/api-execution/scripted-session-evidence.json.txt"),
                )
            )
            plan = load_document(root / "work/EVID-001" / ATTEMPT_ID / "execution-plan.yaml")
        self.assertEqual(0, code, output)
        predecessor = plan["resolved_view"]["predecessor_state_ref"]
        self.assertEqual("examples/main-state-evid-predecessor.yaml", predecessor["path"])

    def test_execute_task_requires_exactly_one_provider_flag(self) -> None:
        base = ["execute", "task", "--task", "t.yaml", "--assignment", "sa.yaml", "--slot", "primary"]
        missing_code, _ = run_cli(base)
        self.assertEqual(2, missing_code)
        both_code, _ = run_cli([*base, "--scripted-session", "s.json", "--allow-live"])
        self.assertEqual(2, both_code)

    def test_unknown_slot_is_a_compile_block_not_a_crash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            assignment = prepare_project(root)
            arguments = execute_arguments(root, assignment, "--scripted-session", str(SCRIPTED_SESSION))
            arguments[arguments.index("primary")] = "no-such-slot"
            with patch.dict("os.environ", {}, clear=True):
                code, output = run_cli(arguments)
            self.assertEqual(1, code)
            self.assertIn("BLOCK", output)
            self.assertIn("EXEC-MODEL-UNBOUND", output)
            self.assertFalse((root / "work" / "EVID-001" / ATTEMPT_ID).exists())


if __name__ == "__main__":
    unittest.main()
