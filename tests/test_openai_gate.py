import contextlib
import io
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from research_workbench.adapters.models import (
    Capability,
    ContentBlock,
    FinishReason,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    ProviderError,
    ProviderErrorCategory,
    ToolCall,
    Usage,
    openai_gate_plan,
    run_openai_gate,
)
from research_workbench.artifacts import hash_file
from research_workbench.cli import main
from research_workbench.io import load_document


SOURCE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = SOURCE_ROOT / "tests" / "fixtures" / "providers" / "openai-gate-passing.json"
PROTOCOL_REF = "examples/openai-live-gate/project-protocol.yaml"
TASK_REF = "examples/task-evidence.yaml"
PROFILE_REF = "examples/profiles/evidence-scout.yaml"
ASSIGNMENT_REF = "examples/vertical-slice/evidence-assignment.yaml"
INPUT_REF = "examples/fixtures/paper-001.txt"


def output_payload(root: Path) -> dict[str, object]:
    source_hash = hash_file(root / INPUT_REF)
    fact = "The bounded source identifies itself as a synthetic structural fixture."
    limitation = "The source is not scientific evidence and cannot support a real claim."
    return {
        "artifacts": [
            {
                "document": {
                    "schema_version": "0.1.0",
                    "object_type": "evidence",
                    "object_id": "EVID-001-OPENAI-GATE",
                    "revision": 1,
                    "status": "admitted-fixture",
                    "content_hash": source_hash,
                    "kind": "bounded-text-excerpt",
                    "source_ref": INPUT_REF,
                    "locator": "lines 1-2",
                    "statement": fact,
                    "quality_flags": ["synthetic_fixture", "not_scientific_evidence"],
                    "metadata": {"boundary": limitation},
                }
            }
        ],
        "handoff": {
            "result": {
                "summary": "One bounded synthetic Evidence record was persisted.",
                "facts": [fact],
                "inferences": [],
                "recommendations": [],
            },
            "limitations": [limitation],
            "conflicts": [],
            "unresolved": [],
            "human_decision_required": [],
            "recommended_next_actions": ["Review the fixture closeout."],
        },
        "transfer_items": [
            {
                "item_id": "HTI-GATE-FACT",
                "kind": "fact",
                "criticality": "material",
                "required_for_handoff": True,
                "statement": fact,
                "source_object_id": "EVID-001-OPENAI-GATE",
                "source_locator": "/statement",
                "handoff_locator": "/result/facts/0",
            },
            {
                "item_id": "HTI-GATE-LIMITATION",
                "kind": "limitation",
                "criticality": "material",
                "required_for_handoff": True,
                "statement": limitation,
                "source_object_id": "EVID-001-OPENAI-GATE",
                "source_locator": "/metadata/boundary",
                "handoff_locator": "/limitations/0",
            },
        ],
    }


class FixtureProvider:
    def __init__(self, model: str, fixture: list[dict[str, object]], root: Path) -> None:
        self.model = model
        self.fixture = list(fixture)
        self.root = root
        self.requests: list[ModelRequest] = []

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider="openai",
            adapter_version="0.1.0",
            supported=frozenset(
                {Capability.TEXT, Capability.STRUCTURED_OUTPUT, Capability.TOOLS}
            ),
            models=(self.model,),
            deployment="remote",
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if not self.fixture:
            raise AssertionError("unexpected provider invocation")
        item = self.fixture.pop(0)
        text = item.get("text")
        if text == "__EVIDENCE_OUTPUT__":
            text = json.dumps(output_payload(self.root), ensure_ascii=False)
        output = (
            (ContentBlock(kind="text", text=str(text)),)
            if isinstance(text, str)
            else ()
        )
        tool_calls = ()
        if isinstance(item.get("tool_name"), str):
            tool_calls = (
                ToolCall(
                    call_id=str(item["tool_call_id"]),
                    name=str(item["tool_name"]),
                    arguments=dict(item["tool_arguments"]),
                ),
            )
        raw_cost = item.get("provider_reported_cost")
        return ModelResponse(
            response_id=str(item["response_id"]),
            provider="openai",
            model=self.model,
            output=output,
            finish_reason=FinishReason(str(item["finish_reason"])),
            tool_calls=tool_calls,
            usage=Usage(
                input_tokens=int(item["input_tokens"]),
                output_tokens=int(item["output_tokens"]),
                provider_reported_cost=(
                    float(raw_cost) if isinstance(raw_cost, (int, float)) else None
                ),
                currency="USD" if isinstance(raw_cost, (int, float)) else None,
            ),
        )


class FailingProvider(FixtureProvider):
    def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        raise ProviderError(
            ProviderErrorCategory.RATE_LIMIT,
            "provider-body-must-not-be-retained",
            retryable=True,
            status_code=429,
        )


class ExplodingEnvironment(dict[str, str]):
    def get(self, key: str, default: str | None = None) -> str | None:
        raise AssertionError(f"environment must not be read: {key}")


def fixture_document() -> list[dict[str, object]]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def run_cli(arguments: list[str]) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(arguments)
    return code, output.getvalue()


class OpenAIGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for relative in (PROTOCOL_REF, TASK_REF, PROFILE_REF, ASSIGNMENT_REF, INPUT_REF):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE_ROOT / relative, target)
        shutil.copytree(
            SOURCE_ROOT / ".agents/skills/literature-evidence-extraction",
            self.root / ".agents/skills/literature-evidence-extraction",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def fixed_now():
        current = datetime(2026, 8, 16, 4, 0, tzinfo=timezone.utc)

        def advance() -> datetime:
            nonlocal current
            value = current
            current += timedelta(seconds=1)
            return value

        return advance

    def test_policy_is_fixed_to_worker_model_and_project_h2_budgets(self) -> None:
        plan = openai_gate_plan()
        self.assertEqual("env:RWB_WORKER_MODEL", plan["model_source"])
        self.assertEqual(["text", "structured", "tools"], plan["conformance"]["checks"])
        self.assertEqual(64, plan["conformance"]["max_output_tokens_per_invocation"])
        self.assertEqual(0, plan["conformance"]["automatic_retries"])
        self.assertEqual(3, plan["e2e"]["max_model_turns"])
        self.assertEqual(["document-read"], plan["e2e"]["tool_allowlist"])
        self.assertEqual(2, plan["e2e"]["max_tool_calls"])
        self.assertEqual(1, plan["e2e"]["max_parallel_tool_calls"])
        self.assertEqual(["read-only"], plan["e2e"]["allowed_tool_side_effects"])
        self.assertEqual(5_000, plan["e2e"]["max_total_tokens"])
        self.assertEqual(0.50, plan["e2e"]["max_provider_reported_cost"])
        self.assertEqual("H2", plan["e2e"]["handoff_tier"])

    def test_non_execute_is_deterministic_not_run_without_environment_access(self) -> None:
        first = run_openai_gate(execute=False, environment=ExplodingEnvironment())
        second = run_openai_gate(execute=False, environment=ExplodingEnvironment())
        self.assertEqual(first, second)
        self.assertEqual("not-run", first["status"])
        self.assertIs(first["environment_checked"], False)

    def test_missing_key_or_model_is_not_run_before_provider_construction(self) -> None:
        constructed: list[str] = []
        report = run_openai_gate(
            execute=True,
            environment={"RWB_WORKER_MODEL": "fixture-model"},
            provider_factory=lambda model: constructed.append(model),
            root=self.root,
            attempt_id="A-OPENAI-GATE-MISSING-KEY",
            accountable_owner="Huang Yi",
            report_path=self.root / "missing-env.json",
        )
        self.assertEqual("not-run", report["status"])
        self.assertEqual(["OPENAI_API_KEY"], report["missing_environment"])
        self.assertEqual([], constructed)
        self.assertNotIn("fixture-model", json.dumps(report))
        self.assertEqual(
            "not-run",
            load_document(self.root / "missing-env.decision.json")["decision"],
        )

    def test_passing_fixture_publishes_complete_h2_closeout_and_redacted_report(self) -> None:
        attempt_id = "A-OPENAI-GATE-PASS"
        provider = FixtureProvider("fixture-model", fixture_document(), self.root)
        secret = "credential-value-must-not-be-retained"
        report = run_openai_gate(
            execute=True,
            environment={"OPENAI_API_KEY": secret, "RWB_WORKER_MODEL": "fixture-model"},
            provider_factory=lambda model: provider,
            root=self.root,
            attempt_id=attempt_id,
            accountable_owner="Huang Yi",
            report_path=self.root / "gate-pass.yaml",
            now=self.fixed_now(),
        )

        self.assertEqual("passed", report["status"])
        self.assertEqual(6, len(provider.requests))
        self.assertEqual({"fixture-model"}, {request.model for request in provider.requests})
        self.assertTrue(all(request.max_output_tokens == 64 for request in provider.requests[:3]))
        self.assertEqual(["document-read"], [tool.name for tool in provider.requests[3].tools])
        attempt_root = self.root / "work" / "EVID-001" / attempt_id
        required = {
            "model-assignment.yaml",
            "provider-conformance.yaml",
            "attempt.yaml",
            "INDEX.yaml",
            "ACTORS.yaml",
            "events.jsonl",
            "handoff.yaml",
            "transfer-manifest.yaml",
            "transfer-audit.yaml",
            "execution-receipt.yaml",
            "main-state.yaml",
        }
        self.assertTrue(required <= {path.name for path in attempt_root.iterdir()})
        self.assertEqual(1, len(tuple((attempt_root / "artifacts").glob("*.yaml"))))
        self.assertEqual(2, len(tuple((attempt_root / "messages").glob("*.md"))))
        self.assertGreaterEqual(len(tuple((attempt_root / "tool-events").glob("*.json"))), 1)
        attempt = load_document(attempt_root / "attempt.yaml")
        receipt = load_document(attempt_root / "execution-receipt.yaml")
        trace = load_document(attempt_root / "INDEX.yaml")
        state = load_document(attempt_root / "main-state.yaml")
        assignment = load_document(attempt_root / "model-assignment.yaml")
        self.assertEqual("H2", attempt["handoff_tier"])
        self.assertEqual("H2", receipt["handoff_tier"])
        self.assertNotIn("API-LIVE-CONFORMANCE-NOT-RUN", state["open_risks"])
        self.assertGreater(receipt["coordination"]["execution_seconds"], 0)
        event_times = {
            json.loads(line)["occurred_at"]
            for line in (attempt_root / "events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line
        }
        self.assertGreater(len(event_times), 1)
        self.assertEqual(attempt["agent_trace_index_ref"], receipt["agent_trace_index_ref"])
        self.assertIn(attempt["agent_trace_index_ref"], state["agent_trace_index_refs"])
        self.assertEqual(attempt["model_assignment_ref"], receipt["model_assignment_ref"])
        self.assertIn(attempt["model_assignment_ref"], state["machine_state_refs"])
        self.assertEqual(attempt["provider_conformance_ref"], receipt["provider_conformance_ref"])
        self.assertIn(attempt["provider_conformance_ref"], state["machine_state_refs"])
        self.assertIs(assignment["automatic_fallback"], False)
        self.assertEqual("openai-responses", assignment["provider_adapter_id"])
        self.assertEqual(
            {"handoff.yaml", "transfer-manifest.yaml"},
            {Path(item["path"]).name for item in trace["handoff_refs"]},
        )
        self.assertEqual(
            {"transfer-audit.yaml", "provider-conformance.yaml"},
            {Path(item["path"]).name for item in trace["check_refs"]},
        )
        decision = load_document(self.root / "gate-pass.decision.yaml")
        self.assertEqual("accept", decision["decision"])
        self.assertEqual(report["e2e"]["main_state_ref"], decision["main_state_ref"])
        self.assertEqual(report["e2e"]["receipt_ref"], decision["receipt_ref"])
        self.assertEqual(report["e2e"]["trace_ref"], decision["trace_ref"])
        self.assertEqual("passed", report["e2e"]["fresh_process_resume_check"]["status"])
        self.assertEqual(0, report["e2e"]["fresh_process_resume_check"]["returncode"])
        for reference in report["e2e"]["published_refs"]:
            self.assertEqual(reference["sha256"], hash_file(self.root / reference["path"]))
        serialized = json.dumps(report)
        for marker in (
            secret,
            "response-body-must-not-be-retained",
            "resp-e2e-final-must-not-be-retained",
            "call-read-two-must-not-be-retained",
            INPUT_REF,
        ):
            self.assertNotIn(marker, serialized)
        report_code, _ = run_cli(
            ["validate", str(self.root / "gate-pass.yaml"), "--root", str(self.root)]
        )
        decision_code, _ = run_cli(
            [
                "validate",
                str(self.root / "gate-pass.decision.yaml"),
                "--root",
                str(self.root),
            ]
        )
        self.assertEqual(0, report_code)
        self.assertEqual(0, decision_code)
        with (self.root / "gate-pass.yaml").open("a", encoding="utf-8") as stream:
            stream.write("\n")
        drift_code, drift_output = run_cli(
            [
                "validate",
                str(self.root / "gate-pass.decision.yaml"),
                "--root",
                str(self.root),
            ]
        )
        self.assertEqual(1, drift_code)
        self.assertIn("REF-HASH-MISMATCH", drift_output)

    def test_provider_failure_is_not_retried_and_does_not_run_project_e2e(self) -> None:
        provider = FailingProvider("fixture-model", [], self.root)
        report = run_openai_gate(
            execute=True,
            environment={"OPENAI_API_KEY": "secret", "RWB_WORKER_MODEL": "fixture-model"},
            provider_factory=lambda model: provider,
            root=self.root,
            attempt_id="A-OPENAI-GATE-CONFORMANCE-FAIL",
            accountable_owner="Huang Yi",
            report_path=self.root / "gate-fail.yaml",
        )
        self.assertEqual("failed", report["status"])
        self.assertEqual(1, len(provider.requests))
        self.assertEqual("failed", report["conformance"]["status"])
        self.assertEqual("not-run", report["e2e"]["status"])
        self.assertFalse((self.root / "work").exists())
        archive = self.root / ".rwb/openai-gates/A-OPENAI-GATE-CONFORMANCE-FAIL"
        self.assertTrue((archive / "intent.yaml").is_file())
        self.assertTrue((archive / "model-assignment.yaml").is_file())
        self.assertTrue((archive / "provider-conformance.yaml").is_file())
        self.assertEqual("reject", load_document(self.root / "gate-fail.decision.yaml")["decision"])
        self.assertNotIn("provider-body-must-not-be-retained", json.dumps(report))

    def test_missing_openai_cost_fails_closed_after_safe_paused_h2_closeout(self) -> None:
        fixture = fixture_document()
        fixture[3]["provider_reported_cost"] = None
        provider = FixtureProvider("fixture-model", fixture, self.root)
        report = run_openai_gate(
            execute=True,
            environment={"OPENAI_API_KEY": "secret", "RWB_WORKER_MODEL": "fixture-model"},
            provider_factory=lambda model: provider,
            root=self.root,
            attempt_id="A-OPENAI-GATE-COST-UNAVAILABLE",
            accountable_owner="Huang Yi",
            report_path=self.root / "gate-cost.yaml",
            now=self.fixed_now(),
        )
        self.assertEqual("failed", report["status"])
        self.assertEqual("cost-usage-unavailable", report["reason"])
        self.assertEqual("failed", report["e2e"]["status"])
        self.assertEqual("cost-usage-unavailable", report["e2e"]["reason"])
        self.assertEqual("safe-paused", report["e2e"]["closeout_status"])
        self.assertEqual(4, len(provider.requests))
        self.assertEqual("reject", load_document(self.root / "gate-cost.decision.yaml")["decision"])
        self.assertEqual(
            "safe-paused",
            load_document(
                self.root
                / "work/EVID-001/A-OPENAI-GATE-COST-UNAVAILABLE/attempt.yaml"
            )["status"],
        )

    def test_cli_missing_environment_is_not_run_and_report_write_is_exclusive(self) -> None:
        report_path = self.root / "gate-missing.json"
        arguments = [
            "providers",
            "openai-gate",
            "--execute",
            "--root",
            str(self.root),
            "--attempt-id",
            "A-OPENAI-GATE-MISSING-ENV",
            "--accountable-owner",
            "Huang Yi",
            "--report",
            str(report_path),
        ]
        with patch.dict("os.environ", {}, clear=True):
            code, output = run_cli(arguments)
            repeat_code, _ = run_cli(arguments)
        self.assertEqual(0, code)
        self.assertIn("not-run", output)
        self.assertEqual("not-run", load_document(report_path)["status"])
        self.assertEqual(
            "not-run",
            load_document(self.root / "gate-missing.decision.json")["decision"],
        )
        self.assertEqual(0, repeat_code)
        report_path.write_text("{}\n", encoding="utf-8")
        with patch.dict("os.environ", {}, clear=True):
            changed_code, _ = run_cli(arguments)
        self.assertEqual(2, changed_code)

    def test_cli_execute_without_report_exits_before_gate_or_network(self) -> None:
        with patch("research_workbench.cli.run_openai_gate") as gate:
            code, output = run_cli(["providers", "openai-gate", "--execute"])

        self.assertEqual(2, code)
        self.assertIn("--execute requires --report", output)
        gate.assert_not_called()

    def test_cli_rejects_non_document_report_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "gate.txt"
            code, output = run_cli(["providers", "openai-gate", "--report", str(report_path)])
        self.assertEqual(2, code)
        self.assertIn(".json, .yaml, or .yml", output)
        self.assertFalse(report_path.exists())


if __name__ == "__main__":
    unittest.main()
