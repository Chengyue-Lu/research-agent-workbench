import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_workbench.cli import main
from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]


def run_cli(arguments: list[str]) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(arguments)
    return code, output.getvalue()


class CliTests(unittest.TestCase):
    def test_model_pool_probe_is_explicit_and_value_free(self) -> None:
        model_marker = "model-id-that-must-not-appear"
        with patch.dict("os.environ", {"RWB_PRIMARY_MODEL": model_marker}, clear=True):
            code, output = run_cli(
                [
                    "models",
                    "probe",
                    "--config",
                    str(ROOT / "registry" / "models" / "pool.example.yaml"),
                    "--json",
                ]
            )
        self.assertEqual(0, code)
        document = json.loads(output)
        self.assertEqual("explicit-slot-only", document["selection_policy"])
        self.assertIs(document["environment_checked"], False)
        self.assertTrue(all(slot["model_status"] == "unchecked" for slot in document["slots"]))
        self.assertNotIn(model_marker, output)

    def test_provider_probe_defaults_to_config_only_and_never_prints_values(self) -> None:
        secret = "must-never-appear-in-cli-output"
        with patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": secret, "RWB_OPENAI_MODEL": "test-model"},
            clear=False,
        ):
            code, output = run_cli(
                [
                    "providers",
                    "probe",
                    "--config",
                    str(ROOT / "registry" / "providers" / "adapters.yaml"),
                    "--json",
                ]
            )
        self.assertEqual(0, code)
        document = json.loads(output)
        self.assertIs(document["environment_checked"], False)
        self.assertEqual("unchecked", document["adapters"][0]["credential_status"])
        self.assertNotIn(secret, output)
        self.assertNotIn("test-model", output)

    def test_provider_probe_presence_check_is_explicit_and_value_free(self) -> None:
        secret = "another-secret-that-must-not-appear"
        with patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": secret, "RWB_OPENAI_MODEL": "configured-model"},
            clear=True,
        ):
            code, output = run_cli(
                [
                    "providers",
                    "probe",
                    "--config",
                    str(ROOT / "registry" / "providers" / "adapters.yaml"),
                    "--check-environment",
                    "--json",
                ]
            )
        self.assertEqual(0, code)
        document = json.loads(output)
        self.assertIs(document["environment_checked"], True)
        self.assertEqual("present", document["adapters"][0]["credential_status"])
        self.assertEqual("missing", document["adapters"][1]["credential_status"])
        self.assertNotIn(secret, output)
        self.assertNotIn("configured-model", output)

    def test_provider_conformance_defaults_to_zero_environment_dry_run(self) -> None:
        code, output = run_cli(
            [
                "providers",
                "conformance",
                "--config",
                str(ROOT / "registry" / "providers" / "adapters.yaml"),
                "--adapter",
                "openai-responses",
            ]
        )
        self.assertEqual(0, code)
        document = json.loads(output)
        self.assertEqual("dry-run", document["mode"])
        self.assertIs(document["environment_read"], False)
        self.assertEqual(0, document["network_requests"])

    def test_provider_conformance_execute_rejects_disabled_template_before_environment(self) -> None:
        secret = "must-not-be-read-or-printed"
        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "report.yaml"
            with patch.dict(
                "os.environ",
                {"OPENAI_API_KEY": secret, "RWB_OPENAI_MODEL": "secret-model-marker"},
                clear=True,
            ):
                code, output = run_cli(
                    [
                        "providers",
                        "conformance",
                        "--config",
                        str(ROOT / "registry" / "providers" / "adapters.yaml"),
                        "--adapter",
                        "openai-responses",
                        "--execute",
                        "--execution-context",
                        "offline-cli-test",
                        "--output",
                        str(output_path),
                    ]
                )
            self.assertEqual(2, code)
            self.assertIn("is disabled", output)
            self.assertNotIn(secret, output)
            self.assertNotIn("secret-model-marker", output)
            self.assertFalse(output_path.exists())

    def test_validate_runs_schema_and_live_reference_checks(self) -> None:
        code, output = run_cli(
            [
                "validate",
                str(ROOT / "examples"),
                str(ROOT / "registry"),
                "--root",
                str(ROOT),
            ]
        )
        self.assertEqual(0, code)
        self.assertIn("errors=0 warnings=0", output)

    def test_invalid_fixture_returns_nonzero_with_local_pointer(self) -> None:
        code, output = run_cli(
            [
                "validate",
                str(ROOT / "tests" / "fixtures" / "invalid" / "objects" / "claim.json"),
                "--root",
                str(ROOT),
            ]
        )
        self.assertEqual(1, code)
        self.assertIn("$.strength", output)

    def test_task_resolve_emits_pinned_skill_and_effective_permissions(self) -> None:
        code, output = run_cli(
            [
                "task",
                "resolve",
                str(ROOT / "examples" / "task-evidence.yaml"),
                "--profile",
                str(ROOT / "examples" / "profiles" / "evidence-scout.yaml"),
                "--skill",
                str(ROOT / "examples" / "skills" / "literature-evidence-extraction.yaml"),
            ]
        )
        self.assertEqual(0, code)
        resolved = json.loads(output)
        self.assertEqual("worktree-write", resolved["effective_permissions"]["filesystem"])
        self.assertEqual(["work/EVID-001"], resolved["effective_permissions"]["allowed_roots"])
        self.assertEqual(64, len(resolved["skill_lock"][0]["content_hash"]))

    def test_handoff_check_matches_task_and_live_input(self) -> None:
        code, output = run_cli(
            [
                "handoff",
                "validate",
                str(ROOT / "examples" / "handoff-evidence.yaml"),
                "--task",
                str(ROOT / "examples" / "task-evidence.yaml"),
                "--root",
                str(ROOT),
            ]
        )
        self.assertEqual(0, code)
        self.assertIn("no blocking", output)

    def test_init_and_checkpoint_create_valid_non_overwriting_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "demo"
            code, _ = run_cli(["init", str(project), "--project-id", "demo"])
            self.assertEqual(0, code)
            checkpoint = project / "checkpoints" / "MS-0001.yaml"
            code, _ = run_cli(
                [
                    "context",
                    "checkpoint",
                    "--id",
                    "MS-0001",
                    "--protocol",
                    str(project / "project-protocol.yaml"),
                    "--output",
                    str(checkpoint),
                    "--root",
                    str(project),
                    "--next-action",
                    "Define the first bounded question.",
                ]
            )
            self.assertEqual(0, code)
            self.assertEqual([], SchemaCatalog(ROOT / "schemas").validate("main_state", load_document(checkpoint)))
            repeat_code, _ = run_cli(["init", str(project)])
            self.assertEqual(2, repeat_code)


if __name__ == "__main__":
    unittest.main()
