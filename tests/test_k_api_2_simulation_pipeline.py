import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.adapters.models import (
    ApiSessionLimits,
    Capability,
    ContentBlock,
    DataPolicy,
    FinishReason,
    ModelAssignment,
    ModelBinding,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    ProviderRegistry,
    Usage,
)
from research_workbench.artifacts import hash_file
from research_workbench.capability import ResolvedTask
from research_workbench.capability.resolver import _assignment_identifier
from research_workbench.execution import CloseoutError, run_task_api_attempt
from research_workbench.execution.compiler import derive_execution_controls
from research_workbench.execution.contracts import default_execution_contract_registry
from research_workbench.io import load_document
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import FileReference, TaskPacket


SOURCE_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_REF = "examples/project-protocol.yaml"
TASK_REF = "examples/task-simulation.yaml"
PROFILE_REF = "examples/profiles/simulation-auditor.yaml"
ASSIGNMENT_REF = "examples/vertical-slice/simulation-assignment.yaml"
INPUT_REF = "examples/fixtures/run-manifest.txt"
CHECKER_REF = ".agents/skills/simulation-vv/scripts/check_vv_report.py"


class SimulationProvider:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
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
            models=("simulation-model",),
            deployment="local",
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        if self.requests:
            raise AssertionError("Provider was replayed after its single scripted response")
        self.requests.append(request)
        return ModelResponse(
            response_id="transient-simulation-response",
            provider="fake-local",
            model="simulation-model",
            output=(ContentBlock(kind="text", text=json.dumps(self.payload)),),
            finish_reason=FinishReason.COMPLETE,
            usage=Usage(input_tokens=20, output_tokens=10),
        )


def simulation_payload() -> dict:
    input_hash = hash_file(SOURCE_ROOT / INPUT_REF)
    return {
        "report": {
            "run_ref": "RUN-001@1",
            "model_version": "bounded-demo@0.1.0",
            "input_lock": [{"path": INPUT_REF, "sha256": input_hash}],
            "parameter_boundary": "Synthetic fixture only; no physical parameter claim.",
            "checks": {
                "convergence": {"status": "blocked", "evidence_refs": []},
                "sensitivity": {"status": "blocked", "evidence_refs": []},
                "benchmark_comparison": {"status": "not-run", "evidence_refs": []},
            },
            "assumptions": ["The fixture tests structural behavior only."],
            "limitations": [
                "No convergence, sensitivity, benchmark, or real-world validation data is present."
            ],
            "claim_ceiling": "unresolved",
        },
        "handoff": {
            "result": {
                "summary": "The structural V&V packet records missing numerical evidence.",
                "facts": ["The report input lock matches the frozen run-manifest fixture."],
                "inferences": [],
                "recommendations": [],
            },
            "limitations": ["Convergence, sensitivity, and benchmark evidence are absent."],
            "conflicts": [],
            "unresolved": ["All numerical V&V checks require additional run outputs."],
            "human_decision_required": [],
            "recommended_next_actions": ["Review the structural report scientifically."],
        },
    }


class SimulationPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for relative in (PROTOCOL_REF, TASK_REF, PROFILE_REF, ASSIGNMENT_REF, INPUT_REF):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE_ROOT / relative, target)
        shutil.copytree(
            SOURCE_ROOT / ".agents/skills/simulation-vv",
            self.root / ".agents/skills/simulation-vv",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_fake_payload_does_not_pass_checks_without_numerical_evidence(self) -> None:
        report = simulation_payload()["report"]

        self.assertEqual("blocked", report["checks"]["convergence"]["status"])
        self.assertEqual("blocked", report["checks"]["sensitivity"]["status"])
        self.assertEqual([], report["checks"]["convergence"]["evidence_refs"])
        self.assertEqual([], report["checks"]["sensitivity"]["evidence_refs"])
        self.assertEqual("unresolved", report["claim_ceiling"])

    @staticmethod
    def limits() -> ApiSessionLimits:
        return ApiSessionLimits(
            max_model_turns=2,
            max_tool_calls=2,
            max_parallel_tool_calls=1,
            max_tool_result_chars=4096,
            max_output_tokens_per_turn=1600,
            max_seconds=30,
            max_total_tokens=4000,
            allowed_tool_side_effects=frozenset({"none", "read-only"}),
            max_compute_values_per_call=32,
        )

    @staticmethod
    def binding() -> ModelBinding:
        return ModelBinding(
            slot_id="worker",
            role="worker",
            provider_adapter="fake-local",
            model="simulation-model",
            capabilities=frozenset(
                {Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}
            ),
            reasoning_effort=None,
            specialties=(),
        )

    @staticmethod
    def actions() -> dict[str, str]:
        return {
            "completed": "Review the completed closeout.",
            "stage-completed": "Perform human scientific review before accepting the result.",
            "safe-paused": "Review the budget before a new Attempt.",
            "incomplete": "Review missing work before a new Attempt.",
            "failed": "Inspect the bounded failure record.",
            "blocked": "Revise the Task contract before retrying.",
        }

    def assignment(self, attempt_id: str) -> ModelAssignment:
        protocol = ProjectProtocol.from_mapping(load_document(self.root / PROTOCOL_REF))
        task = TaskPacket.from_mapping(load_document(self.root / TASK_REF))
        resolved = ResolvedTask.from_mapping(load_document(self.root / ASSIGNMENT_REF))
        contract = default_execution_contract_registry().require(task, resolved)
        policy, limits = derive_execution_controls(
            protocol=protocol,
            task=task,
            runtime_limits=self.limits(),
            execution_contract=contract,
        )
        return ModelAssignment.create(
            attempt_id=attempt_id,
            task_id=task.task_id,
            task_revision=task.revision,
            agent_profile_ref=FileReference(PROFILE_REF, hash_file(self.root / PROFILE_REF)),
            pool_id="test-model-pool",
            pool_config_hash=hashlib.sha256(b"test-model-pool-config").hexdigest(),
            binding=self.binding(),
            selection_source="profile-default",
            selection_reason="The frozen Agent Profile explicitly selects its default slot.",
            effective_data_policy=policy,
            execution_limits=limits,
        )

    def run_pipeline(
        self,
        provider: SimulationProvider,
        attempt_id: str,
        *,
        fault_injector=None,
    ):
        registry = ProviderRegistry()
        registry.register("fake-local", provider)
        return run_task_api_attempt(
            root=self.root,
            protocol_ref=PROTOCOL_REF,
            task_ref=TASK_REF,
            profile_ref=PROFILE_REF,
            assignment_ref=ASSIGNMENT_REF,
            model_assignment=self.assignment(attempt_id),
            providers=registry,
            runtime_limits=self.limits(),
            attempt_id=attempt_id,
            started_at="2026-08-16T02:00:00Z",
            finished_at="2026-08-16T02:01:00Z",
            next_actions=self.actions(),
            trace_accountable_owner="Huang Yi",
            fault_injector=fault_injector,
        )

    def test_h1_stage_completed_has_report_and_dcr_without_h2_manifest(self) -> None:
        provider = SimulationProvider(simulation_payload())
        attempt_id = "A-K2-SIMULATION-H1"

        publication = self.run_pipeline(provider, attempt_id)

        attempt_root = self.root / "work/SIM-001" / attempt_id
        attempt = load_document(attempt_root / "attempt.yaml")
        receipt = load_document(attempt_root / "execution-receipt.yaml")
        handoff = load_document(attempt_root / "handoff.yaml")
        trace = load_document(attempt_root / "INDEX.yaml")
        state = load_document(attempt_root / "main-state.yaml")
        self.assertEqual("stage-completed", publication.status)
        self.assertTrue((attempt_root / "simulation-vv-report.yaml").is_file())
        self.assertTrue((attempt_root / "simulation-vv-check.yaml").is_file())
        self.assertFalse((attempt_root / "transfer-manifest.yaml").exists())
        self.assertFalse((attempt_root / "transfer-audit.yaml").exists())
        self.assertEqual("simulation-h1@0.1.0", receipt["execution_contract"])
        model_assignment_path = f"work/SIM-001/{attempt_id}/model-assignment.yaml"
        self.assertEqual(
            model_assignment_path,
            receipt["model_assignment_ref"]["path"],
        )
        self.assertEqual(
            hash_file(self.root / model_assignment_path),
            receipt["model_assignment_ref"]["sha256"],
        )
        self.assertEqual("H1", receipt["handoff_tier"])
        self.assertEqual("H1", attempt["handoff_tier"])
        self.assertEqual(
            ["fresh-model-api-without-transfer-manifest"],
            receipt["handoff_tier_reasons"],
        )
        self.assertEqual(
            [f"work/SIM-001/{attempt_id}/simulation-vv-check.yaml"],
            receipt["validation_refs"],
        )
        self.assertEqual(receipt["validation_refs"], handoff["validation_refs"])
        self.assertEqual(
            [f"work/SIM-001/{attempt_id}/handoff.yaml"],
            [item["path"] for item in trace["handoff_refs"]],
        )
        self.assertEqual(
            [f"work/SIM-001/{attempt_id}/simulation-vv-report.yaml"],
            [item["path"] for item in trace["output_refs"]],
        )
        self.assertEqual(
            [f"work/SIM-001/{attempt_id}/simulation-vv-check.yaml"],
            [item["path"] for item in trace["check_refs"]],
        )
        self.assertTrue(handoff["human_decision_required"])
        self.assertEqual("stage-completed", state["continuity_status"])
        self.assertIn(CHECKER_REF, {item["path"] for item in state["machine_state_refs"]})
        self.assertEqual(
            {"file-read", "bounded-compute"},
            {tool.name for tool in provider.requests[0].tools},
        )
        self._assert_provider_content_gap(trace)

    def test_h1_fault_checkpoints_resume_without_provider_replay(self) -> None:
        cases = (
            ("AFTER-STAGE", "after-stage-validation"),
            ("FIRST-PUBLISH", "first-after-publish"),
            ("BEFORE-MAIN", "before-main-state-publish"),
            ("AFTER-MAIN", "after-main-state-publish"),
        )

        for suffix, checkpoint in cases:
            with self.subTest(checkpoint=checkpoint):
                attempt_id = f"A-K2-SIMULATION-FAULT-{suffix}"
                provider = SimulationProvider(simulation_payload())
                triggered: list[str] = []

                def crash(point: str) -> None:
                    first_non_main = (
                        checkpoint == "first-after-publish"
                        and point.startswith("after-publish:")
                        and not point.endswith("/main-state.yaml")
                    )
                    if not triggered and (point == checkpoint or first_non_main):
                        triggered.append(point)
                        raise RuntimeError(f"injected H1 fault at {point}")

                with self.assertRaisesRegex(RuntimeError, "injected H1 fault"):
                    self.run_pipeline(provider, attempt_id, fault_injector=crash)

                self.assertEqual(1, len(triggered))
                self.assertEqual(1, len(provider.requests))
                provider_calls = len(provider.requests)
                capability_calls = provider.capability_calls
                attempt_root = self.root / "work/SIM-001" / attempt_id
                main_state = attempt_root / "main-state.yaml"
                stage_attempt = (
                    self.root
                    / ".rwb/closeout"
                    / attempt_id
                    / "tree/work/SIM-001"
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

    def test_unsupported_signature_blocks_before_provider_discovery(self) -> None:
        task_document = load_document(self.root / TASK_REF)
        assignment_document = load_document(self.root / ASSIGNMENT_REF)
        original_assignment = ResolvedTask.from_mapping(assignment_document)
        task_document["required_outputs"] = ["unknown-research-contract", "handoff-packet"]
        assignment_document["output_contracts"] = [
            "unknown-research-contract",
            "handoff-packet",
        ]
        assignment_document["assignment_id"] = _assignment_identifier(
            task_id=original_assignment.task_id,
            task_revision=original_assignment.task_revision,
            agent_profile=original_assignment.agent_profile,
            skill_lock=original_assignment.skill_lock,
            resolved_tools=original_assignment.resolved_tools,
            effective_permissions=original_assignment.effective_permissions,
            output_contracts=tuple(assignment_document["output_contracts"]),
            registry_digest=original_assignment.registry_digest,
        )
        (self.root / TASK_REF).write_text(
            yaml.safe_dump(task_document, sort_keys=False), encoding="utf-8"
        )
        (self.root / ASSIGNMENT_REF).write_text(
            yaml.safe_dump(assignment_document, sort_keys=False), encoding="utf-8"
        )
        provider = SimulationProvider(simulation_payload())
        registry = ProviderRegistry()
        registry.register("fake-local", provider)

        with self.assertRaises(CloseoutError) as raised:
            run_task_api_attempt(
                root=self.root,
                protocol_ref=PROTOCOL_REF,
                task_ref=TASK_REF,
                profile_ref=PROFILE_REF,
                assignment_ref=ASSIGNMENT_REF,
                model_assignment=self.assignment_for_unsupported("A-K2-UNSUPPORTED"),
                providers=registry,
                runtime_limits=self.limits(),
                attempt_id="A-K2-UNSUPPORTED",
                started_at="2026-08-16T02:00:00Z",
                finished_at="2026-08-16T02:01:00Z",
                next_actions=self.actions(),
                trace_accountable_owner="Huang Yi",
            )
        self.assertEqual("OUTPUT-CONTRACT-UNSUPPORTED", raised.exception.code)
        self.assertEqual(0, provider.capability_calls)
        self.assertEqual([], provider.requests)

    def assignment_for_unsupported(self, attempt_id: str) -> ModelAssignment:
        task = TaskPacket.from_mapping(load_document(self.root / TASK_REF))
        return ModelAssignment.create(
            attempt_id=attempt_id,
            task_id=task.task_id,
            task_revision=task.revision,
            agent_profile_ref=FileReference(PROFILE_REF, hash_file(self.root / PROFILE_REF)),
            pool_id="test-model-pool",
            pool_config_hash="0" * 64,
            binding=self.binding(),
            selection_source="profile-default",
            selection_reason="The frozen Agent Profile explicitly selects its default slot.",
            effective_data_policy=DataPolicy(local_only=True),
            execution_limits=self.limits(),
        )

    def _assert_recovered_archive(self, publication, attempt_id: str) -> None:
        attempt_root = self.root / "work/SIM-001" / attempt_id
        attempt_ref = f"work/SIM-001/{attempt_id}/attempt.yaml"
        receipt_ref = f"work/SIM-001/{attempt_id}/execution-receipt.yaml"
        state = load_document(attempt_root / "main-state.yaml")
        attempt = load_document(attempt_root / "attempt.yaml")
        receipt = load_document(attempt_root / "execution-receipt.yaml")
        trace_ref = receipt["agent_trace_index_ref"]
        trace = load_document(self.root / trace_ref["path"])

        self.assertEqual("stage-completed", publication.status)
        self.assertEqual("stage-completed", receipt["status"])
        self.assertEqual("stage-completed", state["continuity_status"])
        self.assertEqual(attempt_ref, receipt["attempt_ref"])
        self.assertEqual(receipt_ref, attempt["execution_receipt_ref"])
        self.assertEqual(trace_ref, attempt["agent_trace_index_ref"])
        self.assertEqual([trace_ref], state["agent_trace_index_refs"])
        self.assertEqual(hash_file(self.root / trace_ref["path"]), trace_ref["sha256"])
        self.assertEqual(attempt_id, trace["attempt_id"])
        self.assertEqual("stage-completed", trace["attempt_status"])
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
