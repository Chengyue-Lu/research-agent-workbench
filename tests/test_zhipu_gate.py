from __future__ import annotations

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
    run_zhipu_gate,
    zhipu_gate_plan,
)
from research_workbench.cli import main
from research_workbench.io import load_document, write_yaml_exclusive
from research_workbench.validation import SchemaCatalog


SOURCE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (
    SOURCE_ROOT
    / "tests"
    / "fixtures"
    / "providers"
    / "zhipu-gate-cost-unavailable.json"
)
PROTOCOL_REF = "examples/zhipu-live-gate/project-protocol.yaml"
TASK_REF = "examples/task-evidence.yaml"
PROFILE_REF = "examples/profiles/evidence-scout.yaml"
ASSIGNMENT_REF = "examples/vertical-slice/evidence-assignment.yaml"
INPUT_REF = "examples/fixtures/paper-001.txt"


class FixtureScenario:
    def __init__(self, fixture: list[dict[str, object]]) -> None:
        self.fixture = list(fixture)
        self.requests: list[ModelRequest] = []
        self.providers: list[FixtureProvider] = []

    def factory(self, model: str) -> "FixtureProvider":
        provider = FixtureProvider(model, self)
        self.providers.append(provider)
        return provider


class FixtureProvider:
    def __init__(self, model: str, scenario: FixtureScenario) -> None:
        self.model = model
        self.scenario = scenario
        self.discard_count = 0

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider="zhipu",
            adapter_version="0.1.0",
            supported=frozenset(
                {
                    Capability.TEXT,
                    Capability.STRUCTURED_OUTPUT,
                    Capability.TOOLS,
                    Capability.REASONING,
                }
            ),
            models=(self.model,),
            deployment="remote",
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.scenario.requests.append(request)
        if not self.scenario.fixture:
            raise AssertionError("unexpected provider invocation")
        item = self.scenario.fixture.pop(0)
        text = item.get("text")
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
        return ModelResponse(
            response_id=str(item["response_id"]),
            provider="zhipu",
            model=self.model,
            output=output,
            finish_reason=FinishReason(str(item["finish_reason"])),
            tool_calls=tool_calls,
            usage=Usage(
                input_tokens=int(item["input_tokens"]),
                output_tokens=int(item["output_tokens"]),
                provider_reported_cost=(
                    float(item["provider_reported_cost"])
                    if isinstance(item.get("provider_reported_cost"), (int, float))
                    else None
                ),
                currency=(
                    "USD"
                    if isinstance(item.get("provider_reported_cost"), (int, float))
                    else None
                ),
            ),
        )

    def discard_ephemeral_continuation(self) -> None:
        self.discard_count += 1


class FailingProvider(FixtureProvider):
    def generate(self, request: ModelRequest) -> ModelResponse:
        self.scenario.requests.append(request)
        raise ProviderError(
            ProviderErrorCategory.UNSUPPORTED,
            "zhipu-provider-body-must-not-be-retained",
            retryable=False,
            status_code=400,
        )


class CleanupFailingProvider(FixtureProvider):
    def discard_ephemeral_continuation(self) -> None:
        self.discard_count += 1
        raise RuntimeError("private-cleanup-message-must-not-be-retained")


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


class ZhipuGateTests(unittest.TestCase):
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
        current = datetime(2026, 8, 16, 6, 0, tzinfo=timezone.utc)

        def advance() -> datetime:
            nonlocal current
            value = current
            current += timedelta(seconds=1)
            return value

        return advance

    def test_policy_is_fixed_to_standard_api_auto_tools_and_fail_closed_cost(self) -> None:
        plan = zhipu_gate_plan()
        self.assertEqual("env:RWB_ZHIPU_MODEL", plan["model_source"])
        self.assertEqual(
            "https://open.bigmodel.cn/api/paas/v4", plan["base_url"]
        )
        self.assertEqual(["text", "structured", "tools"], plan["conformance"]["checks"])
        self.assertEqual("auto", plan["conformance"]["tool_choice"])
        self.assertEqual("low", plan["conformance"]["reasoning_effort"])
        self.assertEqual(0, plan["conformance"]["automatic_retries"])
        self.assertEqual(0.50, plan["e2e"]["max_provider_reported_cost"])
        self.assertEqual("low", plan["e2e"]["reasoning_effort"])
        self.assertIs(plan["e2e"]["automatic_fallback"], False)

    def test_non_execute_is_deterministic_and_does_not_read_environment(self) -> None:
        first = run_zhipu_gate(execute=False, environment=ExplodingEnvironment())
        second = run_zhipu_gate(execute=False, environment=ExplodingEnvironment())
        self.assertEqual(first, second)
        self.assertEqual("not-run", first["status"])
        self.assertIs(first["environment_checked"], False)
        forged = json.loads(json.dumps(first))
        forged["status"] = "passed"
        forged["reason"] = "forged"
        self.assertTrue(SchemaCatalog().validate("zhipu_live_gate_report", forged))

    def test_missing_environment_writes_not_run_report_and_decision_without_provider(self) -> None:
        constructed: list[str] = []
        report = run_zhipu_gate(
            execute=True,
            environment={"RWB_ZHIPU_MODEL": "glm-fixture"},
            provider_factory=lambda model: constructed.append(model),
            root=self.root,
            attempt_id="A-ZHIPU-GATE-MISSING",
            accountable_owner="Huang Yi",
            report_path=self.root / "missing.yaml",
        )
        self.assertEqual("not-run", report["status"])
        self.assertEqual([], constructed)
        self.assertEqual(
            "not-run", load_document(self.root / "missing.decision.yaml")["decision"]
        )

    def test_cost_unavailable_safe_pauses_full_failure_chain_and_never_accepts(self) -> None:
        scenario = FixtureScenario(fixture_document())
        report = run_zhipu_gate(
            execute=True,
            environment={"ZHIPU_API_KEY": "secret", "RWB_ZHIPU_MODEL": "glm-fixture"},
            provider_factory=scenario.factory,
            root=self.root,
            attempt_id="A-ZHIPU-GATE-COST",
            accountable_owner="Huang Yi",
            report_path=self.root / "cost.yaml",
            now=self.fixed_now(),
        )

        self.assertEqual("safe-paused", report["status"])
        self.assertEqual("cost-usage-unavailable", report["reason"])
        self.assertEqual("safe-paused", report["e2e"]["closeout_status"])
        self.assertEqual(4, len(scenario.requests))
        self.assertEqual("auto", scenario.requests[2].tool_choice.kind)
        self.assertEqual(2, len(scenario.providers))
        self.assertEqual([1, 1], [item.discard_count for item in scenario.providers])
        attempt_root = self.root / "work/EVID-001/A-ZHIPU-GATE-COST"
        required = {
            "model-assignment.yaml",
            "provider-conformance.yaml",
            "attempt.yaml",
            "INDEX.yaml",
            "handoff.yaml",
            "execution-receipt.yaml",
            "main-state.yaml",
        }
        self.assertTrue(required <= {path.name for path in attempt_root.iterdir()})
        attempt = load_document(attempt_root / "attempt.yaml")
        receipt = load_document(attempt_root / "execution-receipt.yaml")
        trace = load_document(attempt_root / "INDEX.yaml")
        state = load_document(attempt_root / "main-state.yaml")
        model_assignment = load_document(attempt_root / "model-assignment.yaml")
        self.assertEqual("safe-paused", attempt["status"])
        self.assertEqual("low", model_assignment["reasoning_effort"])
        self.assertIn("reasoning", model_assignment["capabilities"])
        self.assertEqual(attempt["provider_conformance_ref"], receipt["provider_conformance_ref"])
        self.assertIn(attempt["provider_conformance_ref"], trace["check_refs"])
        self.assertIn(attempt["provider_conformance_ref"], state["machine_state_refs"])
        self.assertEqual("passed", report["e2e"]["fresh_process_resume_check"]["status"])
        decision = load_document(self.root / "cost.decision.yaml")
        self.assertEqual("defer", decision["decision"])
        self.assertIs(decision["adr_0013_passed"], False)
        self.assertEqual(report["e2e"]["main_state_ref"], decision["main_state_ref"])
        report_code, _ = run_cli(
            ["validate", str(self.root / "cost.yaml"), "--root", str(self.root)]
        )
        decision_code, _ = run_cli(
            [
                "validate",
                str(self.root / "cost.decision.yaml"),
                "--root",
                str(self.root),
            ]
        )
        self.assertEqual(0, report_code)
        self.assertEqual(0, decision_code)
        forged_decision = dict(decision)
        forged_decision["reason"] = "forged-reason"
        forged_path = self.root / "cost-forged.decision.yaml"
        write_yaml_exclusive(forged_path, forged_decision)
        forged_code, forged_output = run_cli(
            ["validate", str(forged_path), "--root", str(self.root)]
        )
        self.assertEqual(1, forged_code)
        self.assertIn("ZHIPU-GATE-DECISION-MISMATCH", forged_output)
        serialized = json.dumps(report) + json.dumps(decision)
        for marker in (
            "secret",
            "zhipu-text-body-must-not-be-retained",
            "zhipu-document-call-id-must-not-be-retained",
        ):
            self.assertNotIn(marker, serialized)

    def test_conformance_unavailable_archives_and_defers_without_research_attempt(self) -> None:
        scenario = FixtureScenario([])

        def failing_factory(model: str) -> FailingProvider:
            provider = FailingProvider(model, scenario)
            scenario.providers.append(provider)
            return provider

        report = run_zhipu_gate(
            execute=True,
            environment={"ZHIPU_API_KEY": "secret", "RWB_ZHIPU_MODEL": "glm-fixture"},
            provider_factory=failing_factory,
            root=self.root,
            attempt_id="A-ZHIPU-GATE-UNAVAILABLE",
            accountable_owner="Huang Yi",
            report_path=self.root / "unavailable.yaml",
        )
        self.assertEqual("safe-paused", report["status"])
        self.assertEqual(1, len(scenario.requests))
        self.assertEqual(1, len(scenario.providers))
        self.assertEqual(1, scenario.providers[0].discard_count)
        archive = self.root / ".rwb/zhipu-gates/A-ZHIPU-GATE-UNAVAILABLE"
        self.assertTrue((archive / "intent.yaml").is_file())
        self.assertTrue((archive / "model-assignment.yaml").is_file())
        self.assertTrue((archive / "provider-conformance.yaml").is_file())
        self.assertFalse((self.root / "work").exists())
        decision = load_document(self.root / "unavailable.decision.yaml")
        self.assertEqual("defer", decision["decision"])
        self.assertIs(decision["adr_0013_passed"], False)

    def test_incomplete_project_closeout_remains_linked_and_is_rejected(self) -> None:
        fixture = fixture_document()
        fixture[-1] = {
            "response_id": "zhipu-incomplete-id-must-not-be-retained",
            "finish_reason": "length",
            "text": "partial-body-must-not-be-retained",
            "input_tokens": 30,
            "output_tokens": 5,
            "provider_reported_cost": 0.01,
        }
        scenario = FixtureScenario(fixture)
        report = run_zhipu_gate(
            execute=True,
            environment={"ZHIPU_API_KEY": "secret", "RWB_ZHIPU_MODEL": "glm-fixture"},
            provider_factory=scenario.factory,
            root=self.root,
            attempt_id="A-ZHIPU-GATE-INCOMPLETE",
            accountable_owner="Huang Yi",
            report_path=self.root / "incomplete.yaml",
            now=self.fixed_now(),
        )

        self.assertEqual("failed", report["status"])
        self.assertEqual("incomplete", report["e2e"]["status"])
        self.assertEqual("incomplete", report["e2e"]["closeout_status"])
        self.assertEqual("passed", report["e2e"]["fresh_process_resume_check"]["status"])
        for key in ("main_state_ref", "receipt_ref", "trace_ref"):
            self.assertIn(key, report["e2e"])
        self.assertEqual(
            "reject", load_document(self.root / "incomplete.decision.yaml")["decision"]
        )
        self.assertNotIn("partial-body-must-not-be-retained", json.dumps(report))

    def test_project_cleanup_failure_closes_with_fixed_code_and_no_orphan_report(self) -> None:
        scenario = FixtureScenario(fixture_document())

        def factory(model: str) -> FixtureProvider:
            provider_type = FixtureProvider if not scenario.providers else CleanupFailingProvider
            provider = provider_type(model, scenario)
            scenario.providers.append(provider)
            return provider

        report = run_zhipu_gate(
            execute=True,
            environment={"ZHIPU_API_KEY": "secret", "RWB_ZHIPU_MODEL": "glm-fixture"},
            provider_factory=factory,
            root=self.root,
            attempt_id="A-ZHIPU-GATE-CLEANUP",
            accountable_owner="Huang Yi",
            report_path=self.root / "cleanup.yaml",
            now=self.fixed_now(),
        )

        self.assertEqual("failed", report["status"])
        self.assertEqual("PROVIDER-EPHEMERAL-CLEANUP-FAILED", report["reason"])
        self.assertEqual([1, 1], [item.discard_count for item in scenario.providers])
        attempt = load_document(
            self.root / "work/EVID-001/A-ZHIPU-GATE-CLEANUP/attempt.yaml"
        )
        self.assertEqual(
            "PROVIDER-EPHEMERAL-CLEANUP-FAILED", attempt["failure"]["code"]
        )
        self.assertEqual(
            "reject", load_document(self.root / "cleanup.decision.yaml")["decision"]
        )
        serialized = json.dumps(report) + json.dumps(attempt)
        self.assertNotIn("private-cleanup-message-must-not-be-retained", serialized)

    def test_cli_execute_without_report_exits_before_gate(self) -> None:
        with patch("research_workbench.cli.run_zhipu_gate") as gate:
            code, output = run_cli(["providers", "zhipu-gate", "--execute"])
        self.assertEqual(2, code)
        self.assertIn("--execute requires --report", output)
        gate.assert_not_called()

    def test_cli_missing_environment_persists_execute_report_only_once(self) -> None:
        report_path = self.root / "cli-missing.yaml"
        with patch.dict("os.environ", {}, clear=True):
            code, output = run_cli(
                [
                    "providers",
                    "zhipu-gate",
                    "--execute",
                    "--root",
                    str(self.root),
                    "--attempt-id",
                    "A-ZHIPU-CLI-MISSING",
                    "--accountable-owner",
                    "Huang Yi",
                    "--report",
                    str(report_path),
                ]
            )
        self.assertEqual(0, code)
        self.assertIn("not-run", output)
        self.assertEqual("not-run", load_document(report_path)["status"])
        self.assertTrue((self.root / "cli-missing.decision.yaml").is_file())


if __name__ == "__main__":
    unittest.main()
