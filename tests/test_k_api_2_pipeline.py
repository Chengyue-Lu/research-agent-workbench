import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import yaml

from research_workbench.adapters.models import (
    ApiSessionLimits,
    Capability,
    ContentBlock,
    FinishReason,
    ModelAssignment,
    ModelBinding,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    ProviderError,
    ProviderErrorCategory,
    ProviderRegistry,
    ToolCall,
    Usage,
)
from research_workbench.artifacts import hash_file
from research_workbench.capability import AgentProfile, ResolvedTask
from research_workbench.execution import (
    CloseoutError,
    run_task_api_attempt,
    validate_closeout_preconditions,
)
from research_workbench.execution.compiler import derive_execution_controls
from research_workbench.execution.contracts import default_execution_contract_registry
from research_workbench.io import load_document
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import FileReference, TaskPacket


SOURCE_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_REF = "examples/project-protocol.yaml"
TASK_REF = "examples/task-evidence.yaml"
PROFILE_REF = "examples/profiles/evidence-scout.yaml"
ASSIGNMENT_REF = "examples/vertical-slice/evidence-assignment.yaml"
INPUT_REF = "examples/fixtures/paper-001.txt"


class ScriptedLocalProvider:
    def __init__(self, *steps) -> None:
        self.steps = list(steps)
        self.requests: list[ModelRequest] = []
        self.capability_calls = 0

    def capabilities(self) -> ProviderCapabilities:
        self.capability_calls += 1
        return ProviderCapabilities(
            provider="fake-local",
            adapter_version="fixture-1",
            supported=frozenset(
                {Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}
            ),
            models=("worker-model",),
            deployment="local",
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if not self.steps:
            raise AssertionError("Provider was replayed after its script was exhausted")
        step = self.steps.pop(0)
        if isinstance(step, BaseException):
            raise step
        if callable(step):
            return step(request)
        return step


def response(
    response_id: str,
    reason: FinishReason,
    *,
    text: str = "",
    calls: tuple[ToolCall, ...] = (),
    usage: Usage = Usage(input_tokens=10, output_tokens=5),
    model: str = "worker-model",
    provider: str = "fake-local",
) -> ModelResponse:
    return ModelResponse(
        response_id=response_id,
        provider=provider,
        model=model,
        output=(ContentBlock(kind="text", text=text),) if text else (),
        finish_reason=reason,
        tool_calls=calls,
        usage=usage,
    )


def output_payload() -> dict:
    source_hash = hash_file(SOURCE_ROOT / INPUT_REF)
    fact = "The bounded source identifies itself as a synthetic structural fixture."
    limitation = "The source is not scientific evidence and cannot support a real claim."
    return {
        "artifacts": [
            {
                "document": {
                    "schema_version": "0.1.0",
                    "object_type": "evidence",
                    "object_id": "EVID-001-K2-PIPELINE",
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
                "item_id": "HTI-PIPELINE-FACT",
                "kind": "fact",
                "criticality": "material",
                "required_for_handoff": True,
                "statement": fact,
                "source_object_id": "EVID-001-K2-PIPELINE",
                "source_locator": "/statement",
                "handoff_locator": "/result/facts/0",
            },
            {
                "item_id": "HTI-PIPELINE-LIMITATION",
                "kind": "limitation",
                "criticality": "material",
                "required_for_handoff": True,
                "statement": limitation,
                "source_object_id": "EVID-001-K2-PIPELINE",
                "source_locator": "/metadata/boundary",
                "handoff_locator": "/limitations/0",
            },
        ],
    }


class KApi2PipelineTests(unittest.TestCase):
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
    def binding() -> ModelBinding:
        return ModelBinding(
            slot_id="worker",
            role="worker",
            provider_adapter="fake-local",
            model="worker-model",
            capabilities=frozenset(
                {Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}
            ),
            reasoning_effort=None,
            specialties=(),
        )

    @staticmethod
    def limits(*, total_tokens: int = 5000) -> ApiSessionLimits:
        return ApiSessionLimits(
            max_model_turns=3,
            max_tool_calls=2,
            max_parallel_tool_calls=1,
            max_tool_result_chars=4096,
            max_output_tokens_per_turn=1800,
            max_seconds=30,
            max_total_tokens=total_tokens,
        )

    @staticmethod
    def actions() -> dict[str, str]:
        return {
            "completed": "Review K-API-2 closeout; do not repeat the completed evidence extraction.",
            "stage-completed": "Review the stage-complete result before scientific acceptance.",
            "safe-paused": "Review the explicit budget before creating a new Attempt; do not replay automatically.",
            "incomplete": "Review the bounded incomplete result before creating a new Attempt.",
            "failed": "Inspect the persisted failure summary before explicitly creating a new Attempt.",
            "blocked": "Create a new Task revision with refreshed inputs; do not run the stale Task.",
        }

    def run_pipeline(self, provider: ScriptedLocalProvider, attempt_id: str, **overrides):
        binding = overrides.pop("binding", self.binding())
        runtime_limits = overrides.get("runtime_limits", self.limits())
        protocol = ProjectProtocol.from_mapping(load_document(self.root / PROTOCOL_REF))
        task = TaskPacket.from_mapping(load_document(self.root / TASK_REF))
        assignment = ResolvedTask.from_mapping(load_document(self.root / ASSIGNMENT_REF))
        model_assignment = overrides.pop("model_assignment", None)
        if model_assignment is None:
            execution_contract = default_execution_contract_registry().require(task, assignment)
            policy, effective_limits = derive_execution_controls(
                protocol=protocol,
                task=task,
                runtime_limits=runtime_limits,
                execution_contract=execution_contract,
            )
            model_assignment = ModelAssignment.create(
                attempt_id=attempt_id,
                task_id=task.task_id,
                task_revision=task.revision,
                agent_profile_ref=FileReference(PROFILE_REF, hash_file(self.root / PROFILE_REF)),
                pool_id="test-model-pool",
                pool_config_hash=hashlib.sha256(b"test-model-pool-config").hexdigest(),
                binding=binding,
                selection_source="profile-default",
                selection_reason="The frozen Agent Profile explicitly selects its default slot.",
                effective_data_policy=policy,
                execution_limits=effective_limits,
            )
        registry = ProviderRegistry()
        registry.register(binding.provider_adapter, provider)
        values = {
            "root": self.root,
            "protocol_ref": PROTOCOL_REF,
            "task_ref": TASK_REF,
            "profile_ref": PROFILE_REF,
            "assignment_ref": ASSIGNMENT_REF,
            "model_assignment": model_assignment,
            "providers": registry,
            "runtime_limits": runtime_limits,
            "attempt_id": attempt_id,
            "started_at": "2026-08-14T02:00:00Z",
            "finished_at": "2026-08-14T02:01:00Z",
            "next_actions": self.actions(),
            "trace_accountable_owner": "Huang Yi",
            "extra_limitations": ("Offline fake Provider; no live API compatibility was tested.",),
        }
        values.update(overrides)
        return run_task_api_attempt(**values)

    def test_completed_path_uses_scoped_tool_and_recovers_without_transcript(self) -> None:
        payload = json.dumps(output_payload(), ensure_ascii=False)
        provider = ScriptedLocalProvider(
            response(
                "r1",
                FinishReason.TOOL_CALL,
                calls=(ToolCall("read-1", "document-read", {"path": INPUT_REF}),),
            ),
            response("r2", FinishReason.COMPLETE, text=payload),
        )
        publication = self.run_pipeline(provider, "A-K2-E2E-COMPLETED")

        self.assertEqual("completed", publication.status)
        self.assertEqual(2, len(provider.requests))
        source = (self.root / INPUT_REF).read_text(encoding="utf-8").strip()
        initial_prompt = "\n".join(
            block.text or ""
            for message in provider.requests[0].messages
            for block in message.content
        )
        self.assertNotIn(source, initial_prompt)
        self.assertEqual("tool", provider.requests[1].messages[-1].role)

        # Simulate deleting all in-memory child-session state before a fresh
        # process validates the only authoritative recovery entrypoint.
        provider.requests.clear()
        del provider
        checked = self.resume_check(publication.main_state_ref)
        self.assertEqual(0, checked.returncode, checked.stdout + checked.stderr)
        state = load_document(self.root / publication.main_state_ref)
        self.assertEqual([self.actions()["completed"]], state["next_actions"])
        attempt_root = self.root / "work/EVID-001/A-K2-E2E-COMPLETED"
        attempt = load_document(attempt_root / "attempt.yaml")
        receipt = load_document(attempt_root / "execution-receipt.yaml")
        trace = load_document(attempt_root / "INDEX.yaml")
        self.assertEqual("H2", attempt["handoff_tier"])
        self.assertEqual("H2", receipt["handoff_tier"])
        self.assertEqual(
            ["task-policy-requires-transfer-manifest"],
            receipt["handoff_tier_reasons"],
        )
        self.assertEqual(
            {"handoff.yaml", "transfer-manifest.yaml"},
            {Path(item["path"]).name for item in trace["handoff_refs"]},
        )
        self.assertEqual(
            {"transfer-audit.yaml"},
            {Path(item["path"]).name for item in trace["check_refs"]},
        )
        self.assertEqual(1, len(trace["output_refs"]))
        self.assertIn(
            "/artifacts/",
            "/" + trace["output_refs"][0]["path"],
        )
        self._assert_provider_content_gap(trace)

    def test_model_assignment_is_hash_pinned_before_first_provider_call(self) -> None:
        attempt_id = "A-K2-E2E-MODEL-ASSIGNMENT-EARLY"
        relative = f"work/EVID-001/{attempt_id}/model-assignment.yaml"

        def assert_frozen_assignment(_request: ModelRequest) -> ModelResponse:
            assignment_path = self.root / relative
            intent_path = self.root / f".rwb/attempt-intents/{attempt_id}.yaml"
            self.assertTrue(assignment_path.is_file())
            self.assertTrue(intent_path.is_file())
            intent = load_document(intent_path)
            expected_ref = {
                "path": relative,
                "sha256": hash_file(assignment_path),
            }
            self.assertEqual(expected_ref, intent["model_assignment_ref"])
            persisted = ModelAssignment.from_mapping(load_document(assignment_path))
            self.assertEqual(
                persisted.model_assignment_id,
                intent["model_assignment_id"],
            )
            return response(
                "r-model-assignment-early",
                FinishReason.COMPLETE,
                text=json.dumps(output_payload()),
            )

        publication = self.run_pipeline(
            ScriptedLocalProvider(assert_frozen_assignment),
            attempt_id,
        )

        attempt_root = self.root / f"work/EVID-001/{attempt_id}"
        expected_ref = {
            "path": relative,
            "sha256": hash_file(attempt_root / "model-assignment.yaml"),
        }
        attempt = load_document(attempt_root / "attempt.yaml")
        receipt = load_document(attempt_root / "execution-receipt.yaml")
        state = load_document(self.root / publication.main_state_ref)
        self.assertEqual(expected_ref, attempt["model_assignment_ref"])
        self.assertEqual(expected_ref, receipt["model_assignment_ref"])
        self.assertIn(expected_ref, state["machine_state_refs"])

    def test_tool_failed_path_retains_failure_without_completion_claim(self) -> None:
        payload = json.dumps(output_payload(), ensure_ascii=False)
        input_path = self.root / INPUT_REF
        frozen_bytes = input_path.read_bytes()

        def drift_before_tool(_request):
            input_path.write_text("temporary drift during tool execution", encoding="utf-8")
            return response(
                "r1",
                FinishReason.TOOL_CALL,
                calls=(ToolCall("read-failed", "document-read", {"path": INPUT_REF}),),
            )

        def restore_before_closeout(_request):
            input_path.write_bytes(frozen_bytes)
            return response("r2", FinishReason.COMPLETE, text=payload)

        provider = ScriptedLocalProvider(
            drift_before_tool,
            restore_before_closeout,
        )
        publication = self.run_pipeline(provider, "A-K2-E2E-TOOL-FAILED")
        attempt = load_document(self.root / "work/EVID-001/A-K2-E2E-TOOL-FAILED/attempt.yaml")
        receipt = load_document(
            self.root / "work/EVID-001/A-K2-E2E-TOOL-FAILED/execution-receipt.yaml"
        )
        self.assertEqual("failed", publication.status)
        self.assertEqual("CLIENT-TOOL-FAILED", attempt["failure"]["code"])
        self.assertEqual(1, attempt["failure"]["tool_failures"][0]["call_number"])
        self.assertEqual("DocumentReadBoundaryError", attempt["failure"]["tool_failures"][0]["error_type"])
        self.assertEqual("execution-only", receipt["completion_claim"])

    def test_wrong_model_is_recorded_and_blocked_before_its_tool_call(self) -> None:
        provider = ScriptedLocalProvider(
            response(
                "transient-wrong-model-response",
                FinishReason.TOOL_CALL,
                calls=(ToolCall("wrong-model-read", "document-read", {"path": INPUT_REF}),),
                model="unexpected-model",
            )
        )

        publication = self.run_pipeline(provider, "A-K2-E2E-WRONG-MODEL")

        attempt_root = self.root / "work/EVID-001/A-K2-E2E-WRONG-MODEL"
        attempt = load_document(attempt_root / "attempt.yaml")
        receipt = load_document(attempt_root / "execution-receipt.yaml")
        persisted = "\n".join(
            path.read_text(encoding="utf-8") for path in attempt_root.rglob("*.yaml")
        )
        self.assertEqual("failed", publication.status)
        self.assertEqual("MODEL-IDENTITY-MISMATCH", attempt["failure"]["code"])
        self.assertEqual(1, len(provider.requests))
        self.assertEqual("unexpected-model", receipt["model_usage"][0]["model"])
        self.assertNotIn("transient-wrong-model-response", persisted)

    def test_empty_provider_model_identity_is_failed_without_partial_stage(self) -> None:
        provider = ScriptedLocalProvider(
            response("r-empty-model", FinishReason.COMPLETE, text="{}", model="")
        )

        publication = self.run_pipeline(provider, "A-K2-E2E-EMPTY-MODEL")

        attempt_root = self.root / "work/EVID-001/A-K2-E2E-EMPTY-MODEL"
        attempt = load_document(attempt_root / "attempt.yaml")
        self.assertEqual("failed", publication.status)
        self.assertEqual("PROVIDER-CONTRACT_VIOLATION", attempt["failure"]["code"])
        self.assertEqual(1, len(provider.requests))
        self.assertFalse((self.root / ".rwb/closeout/A-K2-E2E-EMPTY-MODEL").exists())

    def test_late_model_identity_mismatch_preserves_each_observed_model(self) -> None:
        provider = ScriptedLocalProvider(
            response(
                "r-correct-tool",
                FinishReason.TOOL_CALL,
                calls=(ToolCall("read-before-drift", "document-read", {"path": INPUT_REF}),),
            ),
            response(
                "r-late-wrong-model",
                FinishReason.COMPLETE,
                text=json.dumps(output_payload()),
                model="unexpected-model",
            ),
        )

        publication = self.run_pipeline(provider, "A-K2-E2E-LATE-WRONG-MODEL")

        attempt_root = self.root / "work/EVID-001/A-K2-E2E-LATE-WRONG-MODEL"
        attempt = load_document(attempt_root / "attempt.yaml")
        receipt = load_document(attempt_root / "execution-receipt.yaml")
        self.assertEqual("failed", publication.status)
        self.assertEqual("MODEL-IDENTITY-MISMATCH", attempt["failure"]["code"])
        self.assertEqual(
            ["worker-model", "unexpected-model"], attempt["failure"]["observed_models"]
        )
        self.assertEqual("unavailable", receipt["model_usage_status"])
        self.assertEqual(
            {("worker-model", 1), ("unexpected-model", 1)},
            {(item["model"], item["requests"]) for item in receipt["model_usage"]},
        )
        self.assertEqual(2, len(provider.requests))
        self.assertFalse((attempt_root / "artifacts").exists())

    def test_usage_budget_path_safe_pauses_after_one_provider_call(self) -> None:
        provider = ScriptedLocalProvider(
            response(
                "r-budget",
                FinishReason.COMPLETE,
                text=json.dumps(output_payload()),
                usage=Usage(input_tokens=80, output_tokens=40),
            )
        )
        publication = self.run_pipeline(
            provider,
            "A-K2-E2E-SAFE-PAUSED",
            runtime_limits=self.limits(total_tokens=100),
        )
        self.assertEqual("safe-paused", publication.status)
        self.assertEqual(1, len(provider.requests))
        handoff = load_document(self.root / "work/EVID-001/A-K2-E2E-SAFE-PAUSED/handoff.yaml")
        self.assertEqual("safe-paused", handoff["status"])
        self.assertEqual([], handoff["artifact_refs"])

    def test_provider_incomplete_finish_reasons_have_a_distinct_recoverable_terminal(self) -> None:
        for suffix, reason in (
            ("LENGTH", FinishReason.LENGTH),
            ("PAUSED", FinishReason.PAUSED),
            ("CONTEXT-LIMIT", FinishReason.CONTEXT_LIMIT),
        ):
            with self.subTest(reason=reason):
                provider = ScriptedLocalProvider(
                    response(f"r-{suffix.lower()}", reason, text="bounded partial response")
                )
                attempt_id = f"A-K2-E2E-INCOMPLETE-{suffix}"

                publication = self.run_pipeline(provider, attempt_id)

                attempt_root = self.root / "work/EVID-001" / attempt_id
                attempt = load_document(attempt_root / "attempt.yaml")
                handoff = load_document(attempt_root / "handoff.yaml")
                receipt = load_document(attempt_root / "execution-receipt.yaml")
                state = load_document(self.root / publication.main_state_ref)
                self.assertEqual("incomplete", publication.status)
                self.assertEqual("incomplete", attempt["status"])
                self.assertEqual("API-SESSION-INCOMPLETE", attempt["failure"]["code"])
                self.assertEqual(str(reason), attempt["failure"]["stop_reason"])
                self.assertEqual("incomplete", handoff["status"])
                self.assertEqual([], handoff["artifact_refs"])
                self.assertTrue(any("new Attempt" in item for item in handoff["unresolved"]))
                self.assertEqual(
                    [self.actions()["incomplete"]], handoff["recommended_next_actions"]
                )
                self.assertEqual("incomplete", receipt["status"])
                self.assertEqual("execution-only", receipt["completion_claim"])
                self.assertEqual("blocked", state["continuity_status"])
                self.assertEqual([self.actions()["incomplete"]], state["next_actions"])
                self.assertFalse((attempt_root / "artifacts").exists())
                self.assertFalse((attempt_root / "transfer-manifest.yaml").exists())
                self.assertFalse((attempt_root / "transfer-audit.yaml").exists())
                self.assertEqual(1, len(provider.requests))
                self.assertEqual(0, self.resume_check(publication.main_state_ref).returncode)
                capability_calls = provider.capability_calls

                recovered = self.run_pipeline(provider, attempt_id)

                self.assertEqual("incomplete", recovered.status)
                self.assertEqual(1, len(provider.requests))
                self.assertEqual(capability_calls, provider.capability_calls)

    def test_pipeline_requires_a_distinct_incomplete_next_action_before_discovery(self) -> None:
        provider = ScriptedLocalProvider()
        actions = self.actions()
        actions.pop("incomplete")

        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.run_pipeline(
                provider,
                "A-K2-E2E-INCOMPLETE-ACTION-MISSING",
                next_actions=actions,
            )

        self.assertEqual(0, provider.capability_calls)
        self.assertEqual([], provider.requests)

    def test_runtime_side_effect_ceiling_blocks_before_provider_discovery(self) -> None:
        protocol = ProjectProtocol.from_mapping(load_document(self.root / PROTOCOL_REF))
        task = TaskPacket.from_mapping(load_document(self.root / TASK_REF))
        assignment = ResolvedTask.from_mapping(load_document(self.root / ASSIGNMENT_REF))
        contract = default_execution_contract_registry().require(task, assignment)
        policy, effective_limits = derive_execution_controls(
            protocol=protocol,
            task=task,
            runtime_limits=self.limits(),
            execution_contract=contract,
        )

        for label, allowed in (
            ("EMPTY", frozenset()),
            ("ONLY-NONE", frozenset({"none"})),
        ):
            with self.subTest(label=label):
                attempt_id = f"A-K2-E2E-SIDE-EFFECT-{label}"
                model_assignment = ModelAssignment.create(
                    attempt_id=attempt_id,
                    task_id=task.task_id,
                    task_revision=task.revision,
                    agent_profile_ref=FileReference(
                        PROFILE_REF,
                        hash_file(self.root / PROFILE_REF),
                    ),
                    pool_id="test-model-pool",
                    pool_config_hash=hashlib.sha256(
                        b"test-model-pool-config"
                    ).hexdigest(),
                    binding=self.binding(),
                    selection_source="profile-default",
                    selection_reason=(
                        "The frozen Agent Profile explicitly selects its default slot."
                    ),
                    effective_data_policy=policy,
                    execution_limits=effective_limits,
                )
                provider = ScriptedLocalProvider()

                with self.assertRaises(CloseoutError) as raised:
                    self.run_pipeline(
                        provider,
                        attempt_id,
                        runtime_limits=replace(
                            self.limits(),
                            allowed_tool_side_effects=allowed,
                        ),
                        model_assignment=model_assignment,
                    )

                self.assertEqual(
                    "TOOL-PERMISSION-ESCALATION", raised.exception.code
                )
                self.assertEqual(0, provider.capability_calls)
                self.assertEqual([], provider.requests)

    def test_stale_input_blocks_with_zero_provider_and_tool_calls(self) -> None:
        (self.root / INPUT_REF).write_text("stale", encoding="utf-8")
        provider = ScriptedLocalProvider()
        publication = self.run_pipeline(provider, "A-K2-E2E-STALE")
        attempt = load_document(self.root / "work/EVID-001/A-K2-E2E-STALE/attempt.yaml")
        self.assertEqual("blocked", publication.status)
        self.assertEqual([], provider.requests)
        self.assertEqual(0, provider.capability_calls)
        self.assertEqual("REF-HASH-MISMATCH", attempt["failure"]["code"])
        self.assertEqual(0, self.resume_check(publication.main_state_ref).returncode)

    def test_missing_input_blocks_with_zero_provider_and_tool_calls(self) -> None:
        (self.root / INPUT_REF).unlink()
        provider = ScriptedLocalProvider()

        publication = self.run_pipeline(provider, "A-K2-E2E-MISSING")

        attempt = load_document(self.root / "work/EVID-001/A-K2-E2E-MISSING/attempt.yaml")
        self.assertEqual("blocked", publication.status)
        self.assertEqual("REF-MISSING", attempt["failure"]["code"])
        self.assertEqual(0, provider.capability_calls)
        self.assertEqual([], provider.requests)
        self.assertEqual(0, self.resume_check(publication.main_state_ref).returncode)

    def test_capability_discovery_failure_is_closed_out_without_message(self) -> None:
        class BrokenCapabilitiesProvider:
            def capabilities(self):
                raise RuntimeError("sensitive-capability-message")

            def generate(self, _request):
                raise AssertionError("generate must not be called")

        provider = BrokenCapabilitiesProvider()

        publication = self.run_pipeline(provider, "A-K2-E2E-CAPABILITIES")

        attempt_root = self.root / "work/EVID-001/A-K2-E2E-CAPABILITIES"
        attempt = load_document(attempt_root / "attempt.yaml")
        persisted = "\n".join(
            path.read_text(encoding="utf-8") for path in attempt_root.rglob("*.yaml")
        )
        self.assertEqual("blocked", publication.status)
        self.assertEqual("PROVIDER-CAPABILITIES-UNAVAILABLE", attempt["failure"]["code"])
        self.assertNotIn("sensitive-capability-message", persisted)

    def test_capability_snapshot_drift_is_blocked_before_generate(self) -> None:
        class DriftingCapabilitiesProvider(ScriptedLocalProvider):
            def capabilities(self) -> ProviderCapabilities:
                snapshot = super().capabilities()
                return replace(snapshot, deployment="remote") if self.capability_calls > 1 else snapshot

        provider = DriftingCapabilitiesProvider(
            response("must-not-run", FinishReason.COMPLETE, text=json.dumps(output_payload()))
        )

        publication = self.run_pipeline(provider, "A-K2-E2E-CAPABILITY-DRIFT")

        attempt_root = self.root / "work/EVID-001/A-K2-E2E-CAPABILITY-DRIFT"
        attempt = load_document(attempt_root / "attempt.yaml")
        self.assertEqual("failed", publication.status)
        self.assertEqual("PROVIDER-CONTRACT_VIOLATION", attempt["failure"]["code"])
        self.assertEqual(2, provider.capability_calls)
        self.assertEqual([], provider.requests)

    def test_invalid_research_document_is_failed_before_staging(self) -> None:
        payload = output_payload()
        payload["artifacts"][0]["document"] = {}
        provider = ScriptedLocalProvider(
            response("r-invalid", FinishReason.COMPLETE, text=json.dumps(payload))
        )

        publication = self.run_pipeline(provider, "A-K2-E2E-INVALID-DOCUMENT")

        attempt = load_document(
            self.root / "work/EVID-001/A-K2-E2E-INVALID-DOCUMENT/attempt.yaml"
        )
        self.assertEqual("failed", publication.status)
        self.assertEqual("API-OUTPUT-ARTIFACT-CONTRACT", attempt["failure"]["code"])
        self.assertFalse((self.root / ".rwb/closeout/A-K2-E2E-INVALID-DOCUMENT").exists())

    def test_oversized_json_integer_is_normalized_to_failed_closeout(self) -> None:
        provider = ScriptedLocalProvider(
            response("r-large-integer", FinishReason.COMPLETE, text='{"value":' + "9" * 5000 + "}")
        )

        publication = self.run_pipeline(provider, "A-K2-E2E-LARGE-INTEGER")

        attempt_root = self.root / "work/EVID-001/A-K2-E2E-LARGE-INTEGER"
        attempt = load_document(attempt_root / "attempt.yaml")
        self.assertEqual("failed", publication.status)
        self.assertEqual("PROVIDER-CONTRACT_VIOLATION", attempt["failure"]["code"])
        self.assertFalse((self.root / ".rwb/closeout/A-K2-E2E-LARGE-INTEGER").exists())

    def test_non_finite_json_number_is_rejected_before_artifact_staging(self) -> None:
        payload = output_payload()
        payload["artifacts"][0]["document"]["metadata"]["non_finite"] = float("nan")
        provider = ScriptedLocalProvider(
            response("r-non-finite", FinishReason.COMPLETE, text=json.dumps(payload))
        )

        publication = self.run_pipeline(provider, "A-K2-E2E-NON-FINITE")

        attempt_root = self.root / "work/EVID-001/A-K2-E2E-NON-FINITE"
        attempt = load_document(attempt_root / "attempt.yaml")
        self.assertEqual("failed", publication.status)
        self.assertEqual("PROVIDER-CONTRACT_VIOLATION", attempt["failure"]["code"])
        self.assertFalse((attempt_root / "artifacts").exists())
        self.assertFalse((self.root / ".rwb/closeout/A-K2-E2E-NON-FINITE").exists())

    def test_oversized_pointer_index_is_normalized_to_failed_closeout(self) -> None:
        payload = output_payload()
        payload["transfer_items"][0]["source_locator"] = "/quality_flags/" + "0" * 5000
        provider = ScriptedLocalProvider(
            response("r-large-pointer", FinishReason.COMPLETE, text=json.dumps(payload))
        )

        publication = self.run_pipeline(provider, "A-K2-E2E-LARGE-POINTER")

        attempt_root = self.root / "work/EVID-001/A-K2-E2E-LARGE-POINTER"
        attempt = load_document(attempt_root / "attempt.yaml")
        self.assertEqual("failed", publication.status)
        self.assertEqual("API-OUTPUT-SOURCE-LOCATOR", attempt["failure"]["code"])
        self.assertFalse((self.root / ".rwb/closeout/A-K2-E2E-LARGE-POINTER").exists())

    def test_wrong_evidence_hash_is_failed_and_artifact_is_not_admitted(self) -> None:
        payload = output_payload()
        payload["artifacts"][0]["document"]["content_hash"] = "0" * 64
        provider = ScriptedLocalProvider(
            response("r-wrong-hash", FinishReason.COMPLETE, text=json.dumps(payload))
        )

        publication = self.run_pipeline(provider, "A-K2-E2E-WRONG-HASH")

        attempt_root = self.root / "work/EVID-001/A-K2-E2E-WRONG-HASH"
        attempt = load_document(attempt_root / "attempt.yaml")
        receipt = load_document(attempt_root / "execution-receipt.yaml")
        self.assertEqual("failed", publication.status)
        self.assertEqual("API-OUTPUT-EVIDENCE-HASH", attempt["failure"]["code"])
        self.assertEqual("execution-only", receipt["completion_claim"])
        self.assertFalse((attempt_root / "artifacts").exists())

    def test_windows_reserved_artifact_id_is_failed_before_path_construction(self) -> None:
        payload = output_payload()
        payload["artifacts"][0]["document"]["object_id"] = "NUL"
        payload["transfer_items"][0]["source_object_id"] = "NUL"
        payload["transfer_items"][1]["source_object_id"] = "NUL"
        provider = ScriptedLocalProvider(
            response("r-reserved-id", FinishReason.COMPLETE, text=json.dumps(payload))
        )

        publication = self.run_pipeline(provider, "A-K2-E2E-RESERVED-OBJECT")

        attempt_root = self.root / "work/EVID-001/A-K2-E2E-RESERVED-OBJECT"
        attempt = load_document(attempt_root / "attempt.yaml")
        self.assertEqual("failed", publication.status)
        self.assertEqual("API-OUTPUT-OBJECT-ID", attempt["failure"]["code"])
        self.assertFalse((attempt_root / "artifacts").exists())

    def test_case_insensitive_artifact_collision_is_failed_before_staging(self) -> None:
        payload = output_payload()
        duplicate = json.loads(json.dumps(payload["artifacts"][0]))
        duplicate["document"]["object_id"] = "evid-001-k2-pipeline"
        payload["artifacts"].append(duplicate)
        provider = ScriptedLocalProvider(
            response("r-case-collision", FinishReason.COMPLETE, text=json.dumps(payload))
        )

        publication = self.run_pipeline(provider, "A-K2-E2E-CASE-COLLISION")

        attempt_root = self.root / "work/EVID-001/A-K2-E2E-CASE-COLLISION"
        attempt = load_document(attempt_root / "attempt.yaml")
        self.assertEqual("failed", publication.status)
        self.assertEqual("API-OUTPUT-OBJECT-DUPLICATE", attempt["failure"]["code"])
        self.assertFalse((attempt_root / "artifacts").exists())
        self.assertFalse((self.root / ".rwb/closeout/A-K2-E2E-CASE-COLLISION").exists())

    def test_risk_triggered_semantic_review_becomes_failed_closeout(self) -> None:
        payload = output_payload()
        payload["transfer_items"][0]["kind"] = "negative-result"
        provider = ScriptedLocalProvider(
            response("r-review-required", FinishReason.COMPLETE, text=json.dumps(payload))
        )

        publication = self.run_pipeline(provider, "A-K2-E2E-REVIEW-REQUIRED")

        attempt_root = self.root / "work/EVID-001/A-K2-E2E-REVIEW-REQUIRED"
        attempt = load_document(attempt_root / "attempt.yaml")
        self.assertEqual("failed", publication.status)
        self.assertEqual("API-OUTPUT-HUMAN-REVIEW-REQUIRED", attempt["failure"]["code"])
        self.assertFalse((self.root / ".rwb/closeout/A-K2-E2E-REVIEW-REQUIRED").exists())

    def test_committed_same_attempt_is_validated_without_provider_replay(self) -> None:
        provider = ScriptedLocalProvider(
            response(
                "r-committed",
                FinishReason.COMPLETE,
                text=json.dumps(output_payload()),
            )
        )
        first = self.run_pipeline(provider, "A-K2-E2E-COMMITTED")
        calls = len(provider.requests)
        capability_calls = provider.capability_calls

        second = self.run_pipeline(provider, "A-K2-E2E-COMMITTED")

        self.assertEqual("completed", second.status)
        self.assertEqual(first.main_state_ref, second.main_state_ref)
        self.assertEqual(calls, len(provider.requests))
        self.assertEqual(capability_calls, provider.capability_calls)

    def test_committed_attempt_rejects_changed_requested_binding_without_replay(self) -> None:
        provider = ScriptedLocalProvider(
            response(
                "r-committed-binding",
                FinishReason.COMPLETE,
                text=json.dumps(output_payload()),
            )
        )
        attempt_id = "A-K2-E2E-COMMITTED-BINDING"
        original_binding = replace(self.binding(), provider_adapter="fake-local-alias")
        self.run_pipeline(provider, attempt_id, binding=original_binding)
        receipt = load_document(
            self.root / f"work/EVID-001/{attempt_id}/execution-receipt.yaml"
        )
        self.assertEqual(
            {
                "provider_adapter_id": "fake-local-alias",
                "requested_model": "worker-model",
            },
            receipt["model_binding"],
        )
        self.assertEqual(
            {"fake-local"},
            {record["provider"] for record in receipt["model_usage"]},
        )
        calls = len(provider.requests)
        capability_calls = provider.capability_calls

        for field, changed_binding in (
            ("model", replace(original_binding, model="different-model")),
            (
                "provider_adapter",
                replace(original_binding, provider_adapter="second-fake-local-alias"),
            ),
        ):
            with self.subTest(field=field):
                with self.assertRaises(CloseoutError) as raised:
                    self.run_pipeline(provider, attempt_id, binding=changed_binding)

                self.assertEqual("CLOSEOUT-COMMITTED-IDENTITY", raised.exception.code)
                self.assertEqual(calls, len(provider.requests))
                self.assertEqual(capability_calls, provider.capability_calls)

    def test_incomplete_stage_fails_closed_without_provider_discovery(self) -> None:
        stage = self.root / ".rwb/closeout/A-K2-E2E-INCOMPLETE/tree"
        stage.mkdir(parents=True)
        (stage / "partial.yaml").write_text("partial: true\n", encoding="utf-8")
        provider = ScriptedLocalProvider()

        with self.assertRaises(CloseoutError) as raised:
            self.run_pipeline(provider, "A-K2-E2E-INCOMPLETE")

        self.assertEqual("CLOSEOUT-STAGE-INCOMPLETE", raised.exception.code)
        self.assertEqual(0, provider.capability_calls)
        self.assertEqual([], provider.requests)

    def test_stage_identity_cannot_cross_tasks_with_same_attempt_id(self) -> None:
        provider = ScriptedLocalProvider(
            response(
                "r-cross-task",
                FinishReason.COMPLETE,
                text=json.dumps(output_payload()),
            )
        )

        def crash(point: str) -> None:
            if point == "before-main-state-publish":
                raise RuntimeError("leave validated stage")

        with self.assertRaisesRegex(RuntimeError, "leave validated stage"):
            self.run_pipeline(provider, "A-K2-SHARED-ID", fault_injector=crash)
        task_path = self.root / TASK_REF
        task_path.write_text(
            task_path.read_text(encoding="utf-8").replace(
                "task_id: EVID-001",
                "task_id: EVID-OTHER",
                1,
            ),
            encoding="utf-8",
        )

        with self.assertRaises(CloseoutError) as raised:
            self.run_pipeline(provider, "A-K2-SHARED-ID")

        self.assertEqual("CLOSEOUT-STAGE-IDENTITY", raised.exception.code)
        self.assertEqual(1, len(provider.requests))

    def test_invalid_closeout_timestamp_blocks_before_provider_discovery(self) -> None:
        provider = ScriptedLocalProvider()

        with self.assertRaises(CloseoutError) as raised:
            self.run_pipeline(
                provider,
                "A-K2-BAD-TIME",
                started_at="2026-08-14T02:02:00Z",
                finished_at="2026-08-14T02:01:00Z",
            )

        self.assertEqual("CLOSEOUT-TIMESTAMP", raised.exception.code)
        self.assertEqual(0, provider.capability_calls)
        self.assertEqual([], provider.requests)

    def test_timezone_free_closeout_timestamp_blocks_before_provider_discovery(self) -> None:
        for suffix, started_at in (
            ("NAIVE", "2026-08-14T02:00:00"),
            ("DATE-ONLY", "2026-08-14"),
        ):
            with self.subTest(started_at=started_at):
                provider = ScriptedLocalProvider()

                with self.assertRaises(CloseoutError) as raised:
                    self.run_pipeline(
                        provider,
                        f"A-K2-BAD-TIME-{suffix}",
                        started_at=started_at,
                    )

                self.assertEqual("CLOSEOUT-TIMESTAMP", raised.exception.code)
                self.assertEqual(0, provider.capability_calls)
                self.assertEqual([], provider.requests)

    def test_contract_ref_must_be_canonical_before_provider_discovery(self) -> None:
        provider = ScriptedLocalProvider()

        with self.assertRaises(CloseoutError) as raised:
            self.run_pipeline(
                provider,
                "A-K2-NONCANONICAL-REF",
                task_ref="examples/../examples/task-evidence.yaml",
            )

        self.assertEqual("CLOSEOUT-CONTRACT-REF", raised.exception.code)
        self.assertEqual(0, provider.capability_calls)
        self.assertEqual([], provider.requests)

    def test_schema_invalid_contract_blocks_before_provider_discovery(self) -> None:
        task_path = self.root / TASK_REF
        task_document = load_document(task_path)
        task_document["unknown_contract_field"] = "must be rejected"
        task_path.write_text(
            yaml.safe_dump(task_document, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        provider = ScriptedLocalProvider()

        with self.assertRaises(CloseoutError) as raised:
            self.run_pipeline(provider, "A-K2-SCHEMA-INVALID-CONTRACT")

        self.assertEqual("CLOSEOUT-CONTRACT-SCHEMA", raised.exception.code)
        self.assertEqual(0, provider.capability_calls)
        self.assertEqual([], provider.requests)

    def test_path_like_task_id_cannot_escape_effective_write_root(self) -> None:
        protocol = ProjectProtocol.from_mapping(load_document(self.root / PROTOCOL_REF))
        task = TaskPacket.from_mapping(load_document(self.root / TASK_REF))
        profile = AgentProfile.from_mapping(load_document(self.root / PROFILE_REF))
        assignment = ResolvedTask.from_mapping(load_document(self.root / ASSIGNMENT_REF))
        escaped_task = replace(
            task,
            task_id="X/../../OTHER",
            write_scope=("work/**",),
        )
        escaped_assignment = replace(
            assignment,
            task_id="X/../../OTHER",
            effective_permissions=replace(
                assignment.effective_permissions,
                allowed_roots=("work",),
            ),
        )

        with self.assertRaises(CloseoutError) as raised:
            validate_closeout_preconditions(
                root=self.root,
                protocol=protocol,
                task=escaped_task,
                profile=profile,
                assignment=escaped_assignment,
                protocol_ref=PROTOCOL_REF,
                task_ref=TASK_REF,
                profile_ref=PROFILE_REF,
                assignment_ref=ASSIGNMENT_REF,
                attempt_id="A-K2-PATH-ESCAPE",
                started_at="2026-08-14T02:00:00Z",
                finished_at="2026-08-14T02:01:00Z",
            )

        self.assertEqual("CLOSEOUT-TASK-ID", raised.exception.code)
        self.assertFalse((self.root / "OTHER").exists())

    def test_provider_exception_is_closed_out_without_leaking_message(self) -> None:
        provider = ScriptedLocalProvider(
            ProviderError(
                ProviderErrorCategory.TRANSIENT,
                "sensitive-provider-message-must-not-persist",
                retryable=True,
            )
        )
        publication = self.run_pipeline(provider, "A-K2-E2E-PROVIDER-FAILED")
        self.assertEqual("failed", publication.status)
        attempt_dir = self.root / "work/EVID-001/A-K2-E2E-PROVIDER-FAILED"
        persisted = "\n".join(path.read_text(encoding="utf-8") for path in attempt_dir.rglob("*.yaml"))
        self.assertNotIn("sensitive-provider-message-must-not-persist", persisted)
        attempt = load_document(attempt_dir / "attempt.yaml")
        self.assertEqual("PROVIDER-TRANSIENT", attempt["failure"]["code"])

    def test_contract_drift_during_provider_call_cannot_publish_main_state(self) -> None:
        task_path = self.root / TASK_REF

        def mutate_contract(_request):
            task_document = load_document(task_path)
            task_document["goal"] = "MUTATED-AFTER-COMPILATION"
            task_path.write_text(
                yaml.safe_dump(task_document, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            return response(
                "r-contract-drift",
                FinishReason.COMPLETE,
                text=json.dumps(output_payload()),
            )

        provider = ScriptedLocalProvider(mutate_contract)

        with self.assertRaises(CloseoutError) as raised:
            self.run_pipeline(provider, "A-K2-E2E-CONTRACT-DRIFT")

        self.assertEqual("EXECUTION-CONTRACT-DRIFT", raised.exception.code)
        self.assertEqual(1, len(provider.requests))
        self.assertFalse(
            (self.root / "work/EVID-001/A-K2-E2E-CONTRACT-DRIFT/main-state.yaml").exists()
        )
        with self.assertRaises(CloseoutError) as retry:
            self.run_pipeline(provider, "A-K2-E2E-CONTRACT-DRIFT")
        self.assertEqual("API-ATTEMPT-RESULT-UNKNOWN", retry.exception.code)
        self.assertEqual(1, len(provider.requests))

    def test_mid_session_provider_failure_marks_partial_metrics_unknown(self) -> None:
        provider = ScriptedLocalProvider(
            response(
                "r-before-failure",
                FinishReason.TOOL_CALL,
                calls=(ToolCall("read-before-failure", "document-read", {"path": INPUT_REF}),),
            ),
            ProviderError(
                ProviderErrorCategory.TRANSIENT,
                "sensitive-mid-session-message",
                retryable=True,
            ),
        )

        publication = self.run_pipeline(provider, "A-K2-E2E-MID-SESSION-FAILED")

        attempt_root = self.root / "work/EVID-001/A-K2-E2E-MID-SESSION-FAILED"
        context = load_document(attempt_root / "context-task.yaml")
        receipt = load_document(attempt_root / "execution-receipt.yaml")
        self.assertEqual("failed", publication.status)
        self.assertEqual(2, len(provider.requests))
        self.assertNotIn("turns", context["metrics"])
        self.assertIn("turns", context["unknown_metrics"])
        self.assertEqual("unavailable", receipt["model_usage_status"])
        self.assertEqual([], receipt["model_usage"])
        self.assertTrue(
            any("must not be inferred" in item for item in receipt["limitations"])
        )

    def test_process_loss_after_intent_never_replays_provider_automatically(self) -> None:
        provider = ScriptedLocalProvider(KeyboardInterrupt())

        with self.assertRaises(KeyboardInterrupt):
            self.run_pipeline(provider, "A-K2-E2E-INDETERMINATE")
        calls = len(provider.requests)
        capability_calls = provider.capability_calls
        self.assertTrue(
            (self.root / ".rwb/attempt-intents/A-K2-E2E-INDETERMINATE.yaml").is_file()
        )

        with self.assertRaises(CloseoutError) as raised:
            self.run_pipeline(provider, "A-K2-E2E-INDETERMINATE")

        self.assertEqual("API-ATTEMPT-RESULT-UNKNOWN", raised.exception.code)
        self.assertEqual(calls, len(provider.requests))
        self.assertEqual(capability_calls, provider.capability_calls)

    def test_concurrent_same_attempt_has_one_atomic_provider_winner(self) -> None:
        class ConcurrentProvider:
            def __init__(self) -> None:
                self.lock = threading.Lock()
                self.capability_calls = 0
                self.generate_calls = 0

            def capabilities(self) -> ProviderCapabilities:
                with self.lock:
                    self.capability_calls += 1
                return ProviderCapabilities(
                    provider="fake-local",
                    adapter_version="fixture-1",
                    supported=frozenset(
                        {Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}
                    ),
                    models=("worker-model",),
                    deployment="local",
                )

            def generate(self, _request) -> ModelResponse:
                with self.lock:
                    self.generate_calls += 1
                return response(
                    "r-concurrent",
                    FinishReason.COMPLETE,
                    text=json.dumps(output_payload()),
                )

        provider = ConcurrentProvider()

        def invoke():
            try:
                return self.run_pipeline(provider, "A-K2-E2E-CONCURRENT")
            except CloseoutError as exc:
                return exc

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(executor.map(lambda _index: invoke(), range(2)))

        publications = [item for item in results if not isinstance(item, Exception)]
        failures = [item for item in results if isinstance(item, CloseoutError)]
        self.assertEqual(1, provider.generate_calls)
        self.assertEqual(1, len(publications))
        self.assertEqual("completed", publications[0].status)
        self.assertEqual(1, len(failures))
        self.assertEqual("API-ATTEMPT-RESULT-UNKNOWN", failures[0].code)

    def test_h2_fault_checkpoints_resume_without_provider_replay(self) -> None:
        cases = (
            ("AFTER-STAGE", "after-stage-validation"),
            ("FIRST-PUBLISH", "first-after-publish"),
            ("BEFORE-MAIN", "before-main-state-publish"),
            ("AFTER-MAIN", "after-main-state-publish"),
        )

        for suffix, checkpoint in cases:
            with self.subTest(checkpoint=checkpoint):
                attempt_id = f"A-K2-E2E-FAULT-{suffix}"
                provider = ScriptedLocalProvider(
                    response(
                        f"r-fault-{suffix.lower()}",
                        FinishReason.COMPLETE,
                        text=json.dumps(output_payload()),
                    )
                )
                triggered: list[str] = []

                def crash(point: str) -> None:
                    first_non_main = (
                        checkpoint == "first-after-publish"
                        and point.startswith("after-publish:")
                        and not point.endswith("/main-state.yaml")
                    )
                    if not triggered and (point == checkpoint or first_non_main):
                        triggered.append(point)
                        raise RuntimeError(f"injected H2 fault at {point}")

                with self.assertRaisesRegex(RuntimeError, "injected H2 fault"):
                    self.run_pipeline(provider, attempt_id, fault_injector=crash)

                self.assertEqual(1, len(triggered))
                self.assertEqual(1, len(provider.requests))
                provider_calls = len(provider.requests)
                capability_calls = provider.capability_calls
                attempt_root = self.root / "work/EVID-001" / attempt_id
                main_state = attempt_root / "main-state.yaml"
                stage_attempt = (
                    self.root
                    / ".rwb/closeout"
                    / attempt_id
                    / "tree/work/EVID-001"
                    / attempt_id
                    / "attempt.yaml"
                )
                self.assertTrue(
                    (self.root / ".rwb/closeout" / attempt_id / "plan.yaml").is_file()
                )

                if checkpoint == "after-main-state-publish":
                    self.assertTrue(main_state.is_file())
                    self.assertTrue(stage_attempt.is_file())
                    stage_attempt.unlink()
                else:
                    self.assertFalse(
                        main_state.exists(),
                        "non-Main files must not become an authoritative checkpoint",
                    )
                if checkpoint == "first-after-publish":
                    published_ref = triggered[0].removeprefix("after-publish:")
                    self.assertFalse(published_ref.endswith("/main-state.yaml"))
                    self.assertTrue((self.root / published_ref).is_file())
                if checkpoint == "before-main-state-publish":
                    self.assertTrue((attempt_root / "execution-receipt.yaml").is_file())
                    self.assertTrue((attempt_root / "INDEX.yaml").is_file())

                publication = self.run_pipeline(provider, attempt_id)

                self.assertEqual(provider_calls, len(provider.requests))
                self.assertEqual(capability_calls, provider.capability_calls)
                self._assert_recovered_archive(publication, attempt_id)

    def test_resume_rejects_noncanonical_stage_publication_paths(self) -> None:
        provider = ScriptedLocalProvider(
            response(
                "r-stage-path-identity",
                FinishReason.COMPLETE,
                text=json.dumps(output_payload()),
            )
        )

        def crash(point: str) -> None:
            if point == "before-main-state-publish":
                raise RuntimeError("leave stage for identity tampering")

        attempt_id = "A-K2-E2E-STAGE-PATH-IDENTITY"
        with self.assertRaisesRegex(RuntimeError, "identity tampering"):
            self.run_pipeline(provider, attempt_id, fault_injector=crash)

        stage_parent = self.root / ".rwb/closeout" / attempt_id
        stage_root = stage_parent / "tree"
        plan_path = stage_parent / "plan.yaml"
        plan = load_document(plan_path)
        original_attempt = plan["attempt_ref"]
        original_main = plan["main_state_ref"]
        outside_attempt = "outside-scope/attempt.yaml"
        outside_main = "outside-scope/main-state.yaml"
        for source_ref, target_ref in (
            (original_attempt, outside_attempt),
            (original_main, outside_main),
        ):
            target = stage_root / target_ref
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(stage_root / source_ref, target)
        plan["attempt_ref"] = outside_attempt
        plan["attempt_sha256"] = hash_file(stage_root / outside_attempt)
        plan["main_state_ref"] = outside_main
        plan["main_state_sha256"] = hash_file(stage_root / outside_main)
        plan["publication_hashes"].pop(original_attempt)
        plan["publication_hashes"].pop(original_main)
        plan["publication_hashes"][outside_attempt] = hash_file(stage_root / outside_attempt)
        plan["publication_hashes"][outside_main] = hash_file(stage_root / outside_main)
        plan_path.write_text(
            yaml.safe_dump(plan, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

        with self.assertRaises(CloseoutError) as raised:
            self.run_pipeline(provider, attempt_id)

        self.assertEqual("CLOSEOUT-STAGE-IDENTITY", raised.exception.code)
        self.assertEqual(1, len(provider.requests))
        self.assertFalse((self.root / outside_attempt).exists())
        self.assertFalse((self.root / outside_main).exists())

    def test_stage_and_committed_attempt_bind_previous_main_state_identity(self) -> None:
        provider = ScriptedLocalProvider(
            response(
                "r-previous-base",
                FinishReason.COMPLETE,
                text=json.dumps(output_payload()),
            ),
            response(
                "r-previous-child",
                FinishReason.COMPLETE,
                text=json.dumps(output_payload()),
            ),
        )
        base = self.run_pipeline(provider, "A-K2-E2E-PREVIOUS-BASE")

        def crash(point: str) -> None:
            if point == "before-main-state-publish":
                raise RuntimeError("leave stage bound to previous Main State")

        child_id = "A-K2-E2E-PREVIOUS-CHILD"
        with self.assertRaisesRegex(RuntimeError, "bound to previous"):
            self.run_pipeline(
                provider,
                child_id,
                previous_main_state_ref=base.main_state_ref,
                fault_injector=crash,
            )

        with self.assertRaises(CloseoutError) as staged_mismatch:
            self.run_pipeline(provider, child_id, previous_main_state_ref=None)

        self.assertEqual("CLOSEOUT-STAGE-IDENTITY", staged_mismatch.exception.code)
        self.assertEqual(2, len(provider.requests))

        child = self.run_pipeline(
            provider,
            child_id,
            previous_main_state_ref=base.main_state_ref,
        )
        self.assertEqual("completed", child.status)
        self.assertEqual(2, len(provider.requests))

        with self.assertRaises(CloseoutError) as committed_mismatch:
            self.run_pipeline(provider, child_id, previous_main_state_ref=None)

        self.assertEqual("CLOSEOUT-COMMITTED-IDENTITY", committed_mismatch.exception.code)
        self.assertEqual(2, len(provider.requests))

    def test_input_drift_at_commit_window_cannot_publish_main_or_replay_provider(self) -> None:
        input_path = self.root / INPUT_REF
        frozen_input = input_path.read_bytes()
        provider = ScriptedLocalProvider(
            response(
                "r-input-window",
                FinishReason.COMPLETE,
                text=json.dumps(output_payload()),
            )
        )

        def drift(point: str) -> None:
            if point == "before-main-state-publish":
                input_path.write_text("drifted at the Main State commit window", encoding="utf-8")

        with self.assertRaises(CloseoutError) as first:
            self.run_pipeline(provider, "A-K2-E2E-INPUT-WINDOW", fault_injector=drift)

        main_state = self.root / "work/EVID-001/A-K2-E2E-INPUT-WINDOW/main-state.yaml"
        self.assertEqual("TASK-STALE-INPUT", first.exception.code)
        self.assertFalse(main_state.exists())
        self.assertEqual(1, len(provider.requests))

        with self.assertRaises(CloseoutError) as retry_while_drifted:
            self.run_pipeline(provider, "A-K2-E2E-INPUT-WINDOW")

        self.assertEqual("TASK-STALE-INPUT", retry_while_drifted.exception.code)
        self.assertFalse(main_state.exists())
        self.assertEqual(1, len(provider.requests))

        input_path.write_bytes(frozen_input)
        publication = self.run_pipeline(provider, "A-K2-E2E-INPUT-WINDOW")
        self.assertEqual("completed", publication.status)
        self.assertTrue(main_state.is_file())
        self.assertEqual(1, len(provider.requests))

    def test_skill_drift_at_commit_window_cannot_publish_main_or_replay_provider(self) -> None:
        skill_path = self.root / ".agents/skills/literature-evidence-extraction/SKILL.md"
        frozen_skill = skill_path.read_bytes()
        provider = ScriptedLocalProvider(
            response(
                "r-skill-window",
                FinishReason.COMPLETE,
                text=json.dumps(output_payload()),
            )
        )

        def drift(point: str) -> None:
            if point == "before-main-state-publish":
                skill_path.write_text("# drifted selected Skill", encoding="utf-8")

        with self.assertRaises(CloseoutError) as first:
            self.run_pipeline(provider, "A-K2-E2E-SKILL-WINDOW", fault_injector=drift)

        main_state = self.root / "work/EVID-001/A-K2-E2E-SKILL-WINDOW/main-state.yaml"
        self.assertEqual("ASSIGNMENT-SKILL-DRIFT", first.exception.code)
        self.assertFalse(main_state.exists())
        self.assertEqual(1, len(provider.requests))

        with self.assertRaises(CloseoutError) as retry_while_drifted:
            self.run_pipeline(provider, "A-K2-E2E-SKILL-WINDOW")

        self.assertEqual("ASSIGNMENT-SKILL-DRIFT", retry_while_drifted.exception.code)
        self.assertFalse(main_state.exists())
        self.assertEqual(1, len(provider.requests))

        skill_path.write_bytes(frozen_skill)
        publication = self.run_pipeline(provider, "A-K2-E2E-SKILL-WINDOW")
        self.assertEqual("completed", publication.status)
        self.assertTrue(main_state.is_file())
        self.assertEqual(1, len(provider.requests))

    def test_published_non_main_drift_at_commit_window_cannot_publish_main(self) -> None:
        provider = ScriptedLocalProvider(
            response(
                "r-publication-window",
                FinishReason.COMPLETE,
                text=json.dumps(output_payload()),
            )
        )
        attempt_path = (
            self.root
            / "work/EVID-001/A-K2-E2E-PUBLISHED-WINDOW/attempt.yaml"
        )

        def drift(point: str) -> None:
            if point == "before-main-state-publish":
                attempt_path.write_text("tampered: true\n", encoding="utf-8")

        with self.assertRaises(CloseoutError) as raised:
            self.run_pipeline(provider, "A-K2-E2E-PUBLISHED-WINDOW", fault_injector=drift)

        main_state = self.root / "work/EVID-001/A-K2-E2E-PUBLISHED-WINDOW/main-state.yaml"
        self.assertEqual("CLOSEOUT-PUBLISHED-DRIFT", raised.exception.code)
        self.assertFalse(main_state.exists())
        self.assertEqual(1, len(provider.requests))

        with self.assertRaises(CloseoutError) as retry:
            self.run_pipeline(provider, "A-K2-E2E-PUBLISHED-WINDOW")

        self.assertEqual("CLOSEOUT-STAGE-DRIFT", retry.exception.code)
        self.assertEqual(1, len(provider.requests))

    def _assert_recovered_archive(self, publication, attempt_id: str) -> None:
        attempt_root = self.root / "work/EVID-001" / attempt_id
        attempt_ref = f"work/EVID-001/{attempt_id}/attempt.yaml"
        receipt_ref = f"work/EVID-001/{attempt_id}/execution-receipt.yaml"
        state = load_document(attempt_root / "main-state.yaml")
        attempt = load_document(attempt_root / "attempt.yaml")
        receipt = load_document(attempt_root / "execution-receipt.yaml")
        trace_ref = receipt["agent_trace_index_ref"]
        trace = load_document(self.root / trace_ref["path"])

        self.assertEqual("completed", publication.status)
        self.assertEqual("completed", receipt["status"])
        self.assertEqual("active", state["continuity_status"])
        self.assertEqual(attempt_ref, receipt["attempt_ref"])
        self.assertEqual(receipt_ref, attempt["execution_receipt_ref"])
        self.assertEqual(trace_ref, attempt["agent_trace_index_ref"])
        self.assertEqual([trace_ref], state["agent_trace_index_refs"])
        self.assertEqual(hash_file(self.root / trace_ref["path"]), trace_ref["sha256"])
        self.assertEqual(attempt_id, trace["attempt_id"])
        self.assertEqual("completed", trace["attempt_status"])
        self.assertEqual("frozen", trace["trace_status"])
        checked = self.resume_check(publication.main_state_ref)
        self.assertEqual(0, checked.returncode, checked.stdout + checked.stderr)

    def _assert_provider_content_gap(self, trace: dict) -> None:
        self.assertEqual("gapped", trace["completeness"])
        events = [
            json.loads(line)
            for line in (self.root / trace["event_ledger"]["path"])
            .read_text(encoding="utf-8")
            .splitlines()
            if line
        ]
        provider_gap_ids = {
            event["event_id"]
            for event in events
            if event["event_type"] == "capture-gap"
            and event["payload"].get("affected_stream") == "messages"
            and event["payload"].get("reason_category") == "policy-omission"
            and event["payload"].get("reason")
            == "Provider boundary content is excluded by Trace policy."
        }
        self.assertTrue(provider_gap_ids)
        self.assertTrue(
            provider_gap_ids & {gap["event_id"] for gap in trace["capture_gaps"]},
            "Provider-content omission must be indexed as an explicit capture gap",
        )

    def resume_check(self, main_state_ref: str):
        return subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "research_workbench",
                "context",
                "resume-check",
                str(self.root / main_state_ref),
                "--protocol",
                str(self.root / PROTOCOL_REF),
                "--root",
                str(self.root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
