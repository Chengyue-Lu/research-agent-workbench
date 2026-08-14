"""K-API-2 end-to-end offline execution tests.

A resolved evidence Task must run through one fresh fake-provider session
and close out into the full file chain for every outcome class. After the
in-memory session is gone, a fresh CLI invocation must recover the unique
next action from files alone.
"""

import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from research_workbench.adapters.models import (
    ApiSessionStatus,
    Capability,
    ContentBlock,
    DataPolicyGap,
    FinishReason,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    ProviderRegistry,
    ToolCall,
    Usage,
)
from research_workbench.cli import main as cli_main
from research_workbench.execution import (
    CompileError,
    ExecutionPolicy,
    execute_task,
)
from research_workbench.io import load_document
from research_workbench.tasks import AttemptRecord, HandoffPacket
from research_workbench.observability import ExecutionReceipt


ROOT = Path(__file__).resolve().parents[1]

TASK_PATH = "examples/task-evidence.yaml"
PROFILE_PATH = "registry/agents/evidence-scout.yaml"
ASSIGNMENT_PATH = "examples/vertical-slice/evidence-assignment.yaml"
PROTOCOL_PATH = "examples/project-protocol.yaml"
POOL_PATH = "registry/models/pool.test.yaml"
CHECKER_PATH = "src/research_workbench/execution/checks.py"

POOL_DOCUMENT = """\
schema_version: "0.1.0"
registry_kind: model_pool
pool_id: offline-test-pool
selection_policy: explicit-slot-only
slots:
  - slot_id: worker
    role: worker
    provider_adapter: fake-worker
    model_env: RWB_WORKER_MODEL
    enabled: true
    capabilities: [text, tools, structured_output]
"""

STRUCTURED_OUTPUT = {
    "statement": "The source explicitly identifies itself as a synthetic structural fixture.",
    "source_locator": "lines 1-2",
    "quality_flags": ["synthetic_fixture", "not_scientific_evidence"],
    "summary": "One bounded extraction from the admitted fixture source.",
    "facts": ["The source identifies itself as synthetic and not scientific evidence."],
    "inferences": ["The fixture cannot support a causal claim about Q-001."],
    "recommendations": ["Keep the claim boundary at source_reported strength."],
    "limitations": ["Only the approved synthetic fixture source was reviewed."],
    "unresolved": [],
}

ENVIRONMENT = {"RWB_WORKER_MODEL": "worker-model"}


class OfflineProvider:
    """Scripted fake provider with the capabilities the evidence task needs."""

    def __init__(self, *responses: ModelResponse) -> None:
        self.responses = list(responses)
        self.requests: list[ModelRequest] = []

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider="fake-worker",
            adapter_version="0",
            supported=frozenset({Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}),
            models=("worker-model",),
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("unexpected provider call")
        return self.responses.pop(0)


def text_response(response_id: str, text: str, *, model: str = "worker-model", usage: Usage | None = None, reason: FinishReason = FinishReason.COMPLETE) -> ModelResponse:
    return ModelResponse(
        response_id=response_id,
        provider="fake-worker",
        model=model,
        output=(ContentBlock(kind="text", text=text),),
        finish_reason=reason,
        usage=usage or Usage(input_tokens=5, output_tokens=2),
    )


def tool_response(response_id: str, calls: tuple[ToolCall, ...]) -> ModelResponse:
    return ModelResponse(
        response_id=response_id,
        provider="fake-worker",
        model="worker-model",
        output=(),
        finish_reason=FinishReason.TOOL_CALL,
        tool_calls=calls,
        usage=Usage(input_tokens=5, output_tokens=2),
    )


def structured_response(response_id: str = "r-final") -> ModelResponse:
    return text_response(response_id, json.dumps(STRUCTURED_OUTPUT))


def build_project(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "examples" / "fixtures", destination / "examples" / "fixtures", dirs_exist_ok=True)
    shutil.copytree(
        ROOT / ".agents" / "skills" / "literature-evidence-extraction",
        destination / ".agents" / "skills" / "literature-evidence-extraction",
        dirs_exist_ok=True,
    )
    for relative in (TASK_PATH, PROTOCOL_PATH, ASSIGNMENT_PATH, PROFILE_PATH):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / relative, target)
    pool = destination / POOL_PATH
    pool.parent.mkdir(parents=True, exist_ok=True)
    pool.write_text(POOL_DOCUMENT, encoding="utf-8")
    checker = destination / CHECKER_PATH
    checker.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / CHECKER_PATH, checker)
    return destination


def fixed_clock():
    ticks = iter(
        f"2026-08-14T12:00:{second:02d}Z" for second in range(0, 60)
    )
    return lambda: next(ticks)


def run_execute(root: Path, provider: OfflineProvider, **overrides):
    parameters = {
        "root": root,
        "task_path": TASK_PATH,
        "profile_path": PROFILE_PATH,
        "assignment_path": ASSIGNMENT_PATH,
        "slot": "worker",
        "pool_path": POOL_PATH,
        "environment": ENVIRONMENT,
        "protocol_path": PROTOCOL_PATH,
        "provider_registry": _registry(provider),
        "now": fixed_clock(),
    }
    parameters.update(overrides)
    return execute_task(**parameters)


def _registry(provider: OfflineProvider) -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register("fake-worker", provider)
    return registry


def run_cli(arguments: list[str]) -> tuple[int, str]:
    import io
    from contextlib import redirect_stdout

    stream = io.StringIO()
    with redirect_stdout(stream):
        code = cli_main(arguments)
    return code, stream.getvalue()


def batch_dir(root: Path, run) -> Path:
    return root / "work" / "EVID-001" / run.compiled.attempt_id


class CompletedPathTests(unittest.TestCase):
    def test_completed_path_writes_full_closed_chain(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            provider = OfflineProvider(
                tool_response(
                    "r1", (ToolCall("call-1", "document-read", {"path": "examples/fixtures/paper-001.txt"}),)
                ),
                structured_response("r2"),
            )
            run = run_execute(root, provider)

            self.assertEqual(ApiSessionStatus.COMPLETED.value, run.outcome.status)
            self.assertEqual(
                ("document-read",), tuple(tool.name for tool in provider.requests[0].tools)
            )
            batch = batch_dir(root, run)
            attempt = AttemptRecord.from_mapping(load_document(batch / "attempt.yaml"))
            handoff = HandoffPacket.from_mapping(load_document(batch / "handoff.yaml"))
            receipt = ExecutionReceipt.from_mapping(load_document(batch / "execution-receipt.yaml"))
            self.assertEqual("completed", attempt.status)
            self.assertEqual("completed", handoff.status)
            self.assertEqual("contract-satisfied", receipt.completion_claim)
            self.assertEqual("measured", receipt.model_usage_status)
            evidence = load_document(batch / "evidence.yaml")
            self.assertEqual(STRUCTURED_OUTPUT["statement"], evidence["statement"])
            self.assertTrue((root / run.main_state_path).exists())

    def test_fresh_session_recovers_unique_next_action_from_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            provider = OfflineProvider(
                tool_response(
                    "r1", (ToolCall("call-1", "document-read", {"path": "examples/fixtures/paper-001.txt"}),)
                ),
                structured_response("r2"),
            )
            run = run_execute(root, provider)
            # The in-memory session is gone here; recovery uses only files.
            del provider

            code, output = run_cli(
                [
                    "context", "resume-check",
                    str(root / run.main_state_path),
                    "--protocol", str(root / PROTOCOL_PATH),
                    "--root", str(root),
                ]
            )
            self.assertEqual(0, code, output)
            self.assertIn("no blocking", output)

            state = load_document(root / run.main_state_path)
            self.assertEqual("stage-completed", state["continuity_status"])
            for action in state["next_actions"]:
                self.assertIn("Verify", action)
                self.assertNotIn("re-extract", action.lower())
            self.assertFalse(batch_dir(root, run).joinpath(".staging").exists())
            self.assertTrue(batch_dir(root, run).joinpath("closeout-complete.txt").exists())

    def test_rerun_after_success_skips_model_and_closeout(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            first_provider = OfflineProvider(
                tool_response(
                    "r1", (ToolCall("call-1", "document-read", {"path": "examples/fixtures/paper-001.txt"}),)
                ),
                structured_response("r2"),
            )
            run = run_execute(root, first_provider)
            state_before = (root / run.main_state_path).read_bytes()

            empty_provider = OfflineProvider()
            rerun = run_execute(root, empty_provider)

            self.assertTrue(rerun.closeout.resumed)
            self.assertEqual([], empty_provider.requests)
            self.assertEqual(state_before, (root / rerun.main_state_path).read_bytes())

    def test_model_drift_withholds_completion_claim(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            provider = OfflineProvider(
                tool_response(
                    "r1", (ToolCall("call-1", "document-read", {"path": "examples/fixtures/paper-001.txt"}),)
                ),
                text_response("r2", json.dumps(STRUCTURED_OUTPUT), model="other-model"),
            )
            run = run_execute(root, provider)

            batch = batch_dir(root, run)
            receipt = ExecutionReceipt.from_mapping(load_document(batch / "execution-receipt.yaml"))
            state = load_document(root / run.main_state_path)
            self.assertIsNone(receipt.completion_claim)
            self.assertIn("model differs", state["rollover_reason"])

    def test_dry_run_compiles_without_session_or_writes(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            provider = OfflineProvider()
            run = run_execute(root, provider, dry_run=True)

            self.assertEqual([], provider.requests)
            self.assertTrue(run.compiled.attempt_id.startswith("A-"))
            self.assertFalse((root / "work").exists())
            self.assertFalse((root / "checkpoints").exists())


class FailureAndPausePathTests(unittest.TestCase):
    def test_tool_failure_writes_failed_chain(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            provider = OfflineProvider(
                tool_response(
                    "r1", (ToolCall("call-1", "document-read", {"path": "registry/agents/evidence-scout.yaml"}),)
                ),
                text_response("r2", "cannot complete", reason=FinishReason.ERROR),
            )
            run = run_execute(root, provider)

            batch = batch_dir(root, run)
            attempt = AttemptRecord.from_mapping(load_document(batch / "attempt.yaml"))
            handoff = HandoffPacket.from_mapping(load_document(batch / "handoff.yaml"))
            receipt = ExecutionReceipt.from_mapping(load_document(batch / "execution-receipt.yaml"))
            self.assertEqual("failed", attempt.status)
            self.assertEqual("failed", handoff.status)
            self.assertIsNone(receipt.completion_claim)
            self.assertIn("tool", " ".join(handoff.limitations).lower())

    def test_contract_violation_writes_failed_chain_with_failure_block(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            provider = OfflineProvider(text_response("r1", "not json at all"))
            run = run_execute(root, provider)

            batch = batch_dir(root, run)
            attempt = AttemptRecord.from_mapping(load_document(batch / "attempt.yaml"))
            self.assertEqual("failed", attempt.status)
            self.assertIsNotNone(attempt.failure)
            self.assertTrue((root / run.main_state_path).exists())

    def test_budget_pause_writes_safe_paused_chain_and_resumes_from_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            provider = OfflineProvider(tool_response("r1", (ToolCall("call-1", "document-read", {"path": "examples/fixtures/paper-001.txt"}),)))
            run = run_execute(root, provider, policy=ExecutionPolicy(max_total_tokens=6))

            batch = batch_dir(root, run)
            handoff = HandoffPacket.from_mapping(load_document(batch / "handoff.yaml"))
            receipt = ExecutionReceipt.from_mapping(load_document(batch / "execution-receipt.yaml"))
            self.assertEqual("safe-paused", handoff.status)
            self.assertIn("safe pause", load_document(root / run.main_state_path)["rollover_reason"])
            self.assertTrue(handoff.unresolved)
            for action in handoff.recommended_next_actions:
                self.assertNotIn("re-extract", action.lower())

            code, output = run_cli(
                [
                    "context", "resume-check",
                    str(root / run.main_state_path),
                    "--protocol", str(root / PROTOCOL_PATH),
                    "--root", str(root),
                ]
            )
            self.assertEqual(0, code, output)

    def test_usage_unavailable_hard_budget_safe_pauses(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            provider = OfflineProvider(
                text_response("r1", json.dumps(STRUCTURED_OUTPUT), usage=Usage())
            )
            run = run_execute(root, provider, policy=ExecutionPolicy(max_total_tokens=100))

            self.assertEqual("safe-paused", run.outcome.status)
            self.assertEqual("token-usage-unavailable", run.outcome.stop_reason)
            receipt = ExecutionReceipt.from_mapping(
                load_document(batch_dir(root, run) / "execution-receipt.yaml")
            )
            self.assertEqual("safe-paused", receipt.status)

    def test_stale_input_blocks_before_session_with_zero_writes(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            (root / "examples/fixtures/paper-001.txt").write_text("tampered", encoding="utf-8")
            provider = OfflineProvider()

            with self.assertRaises(CompileError) as caught:
                run_execute(root, provider)
            self.assertEqual("TASK-STALE-INPUT", caught.exception.code)
            self.assertEqual([], provider.requests)
            self.assertFalse((root / "work").exists())
            self.assertFalse((root / "checkpoints").exists())

    def test_capability_gap_blocks_without_writes(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))

            class TextOnlyProvider(OfflineProvider):
                def capabilities(self) -> ProviderCapabilities:
                    return ProviderCapabilities(
                        provider="fake-worker",
                        adapter_version="0",
                        supported=frozenset({Capability.TEXT}),
                        models=("worker-model",),
                    )

            provider = TextOnlyProvider()
            with self.assertRaises(ValueError):
                run_execute(root, provider)
            self.assertEqual([], provider.requests)
            self.assertFalse((root / "work").exists())
            self.assertFalse((root / "checkpoints").exists())

    def test_all_writes_stay_inside_declared_scopes(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            provider = OfflineProvider(
                tool_response(
                    "r1", (ToolCall("call-1", "document-read", {"path": "examples/fixtures/paper-001.txt"}),)
                ),
                structured_response("r2"),
            )
            run = run_execute(root, provider)

            written = [
                path.relative_to(root).as_posix()
                for path in root.rglob("*")
                if path.is_file()
                and ".staging" not in path.parts
                and path.name != "closeout-complete.txt"
                and not path.relative_to(root).as_posix().startswith(
                    ("examples/", "registry/", ".agents/", "src/")
                )
            ]
            for relative in written:
                self.assertTrue(
                    relative.startswith("work/EVID-001/") or relative.startswith("checkpoints/"),
                    f"write outside the declared scope: {relative}",
                )


if __name__ == "__main__":
    unittest.main()
