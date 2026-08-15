import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import yaml

from research_workbench.adapters.models import (
    AggregateUsage,
    ApiSessionLimits,
    ApiSessionResult,
    ApiSessionStatus,
    ContentBlock,
    FinishReason,
    ModelResponse,
)
from research_workbench.adapters.models.session import ToolFailureSummary
from research_workbench.artifacts import hash_file
from research_workbench.capability import AgentProfile, ResolvedTask
from research_workbench.context import checkpoint_digest
from research_workbench.execution.closeout import (
    CloseoutError,
    closeout_api_attempt,
    validate_closeout_preconditions,
)
from research_workbench.io import load_document, write_yaml_exclusive
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import TaskPacket


SOURCE_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_REF = "examples/project-protocol.yaml"
TASK_REF = "examples/task-evidence.yaml"
PROFILE_REF = "examples/profiles/evidence-scout.yaml"
ASSIGNMENT_REF = "examples/vertical-slice/evidence-assignment.yaml"
INPUT_REF = "examples/fixtures/paper-001.txt"


def limits() -> ApiSessionLimits:
    return ApiSessionLimits(
        max_model_turns=3,
        max_tool_calls=2,
        max_parallel_tool_calls=1,
        max_tool_result_chars=4096,
        max_output_tokens_per_turn=1800,
        max_seconds=30,
        max_total_tokens=5000,
    )


def session_result(
    *,
    status: ApiSessionStatus = ApiSessionStatus.COMPLETED,
    model: str = "worker-model",
    failures: tuple[ToolFailureSummary, ...] = (),
) -> ApiSessionResult:
    response = ModelResponse(
        response_id="transient-response-id",
        provider="fake-local",
        model=model,
        output=(ContentBlock(kind="text", text="{}"),),
        finish_reason=FinishReason.COMPLETE,
    )
    return ApiSessionResult(
        status=status,
        stop_reason="complete" if status == ApiSessionStatus.COMPLETED else "model-turn-budget",
        provider="fake-local",
        requested_model="worker-model",
        observed_models=(model,),
        model_turns=2,
        tool_calls=1,
        usage=AggregateUsage(20, 10, None, None, None, None),
        final_response=response,
        warnings=(),
        tool_failures=failures,
    )


def completed_output() -> dict:
    source_hash = hash_file(SOURCE_ROOT / INPUT_REF)
    return {
        "artifacts": [
            {
                "document": {
                    "schema_version": "0.1.0",
                    "object_type": "evidence",
                    "object_id": "EVID-001-K2-01",
                    "revision": 1,
                    "status": "admitted-fixture",
                    "content_hash": source_hash,
                    "kind": "bounded-text-excerpt",
                    "source_ref": INPUT_REF,
                    "locator": "lines 1-2",
                    "statement": "The admitted source explicitly identifies itself as a synthetic fixture.",
                    "quality_flags": ["synthetic_fixture", "not_scientific_evidence"],
                    "metadata": {"fixture": True},
                }
            },
            {
                "document": {
                    "schema_version": "0.1.0",
                    "object_type": "claim",
                    "object_id": "CLAIM-EVID-001-K2-BOUNDARY",
                    "revision": 1,
                    "status": "proposed-fixture",
                    "statement": "The synthetic fixture does not support a causal claim.",
                    "strength": "unresolved",
                    "support_refs": ["EVID-001-K2-01@1"],
                    "counterevidence_refs": [],
                    "limitations": [
                        "Only the approved synthetic fixture was reviewed.",
                        "No source directly measures the proposed mediator.",
                    ],
                    "metadata": {"fixture": True, "not_scientific_evidence": True},
                }
            },
        ],
        "handoff": {
            "result": {
                "summary": "One synthetic fixture Evidence record was extracted without a causal claim.",
                "facts": [
                    "The admitted source explicitly identifies itself as a synthetic fixture."
                ],
                "inferences": ["The synthetic fixture does not support a causal claim."],
                "recommendations": ["Review the bounded result before creating another Task."],
            },
            "limitations": ["Only the approved synthetic fixture was reviewed."],
            "conflicts": [],
            "unresolved": ["No source directly measures the proposed mediator."],
            "human_decision_required": [],
            "recommended_next_actions": [
                "Review the admitted Evidence and decide whether to create a separate replication-search Task."
            ],
        },
        "transfer_items": [
            {
                "item_id": "HTI-K2-FACT-001",
                "kind": "fact",
                "criticality": "material",
                "required_for_handoff": True,
                "statement": "The admitted source explicitly identifies itself as a synthetic fixture.",
                "source_object_id": "EVID-001-K2-01",
                "source_locator": "/statement",
                "handoff_locator": "/result/facts/0",
            },
            {
                "item_id": "HTI-K2-INFERENCE-001",
                "kind": "inference",
                "criticality": "material",
                "required_for_handoff": True,
                "statement": "The synthetic fixture does not support a causal claim.",
                "source_object_id": "CLAIM-EVID-001-K2-BOUNDARY",
                "source_locator": "/statement",
                "handoff_locator": "/result/inferences/0",
            },
            {
                "item_id": "HTI-K2-LIMITATION-001",
                "kind": "limitation",
                "criticality": "material",
                "required_for_handoff": True,
                "statement": "Only the approved synthetic fixture was reviewed.",
                "source_object_id": "CLAIM-EVID-001-K2-BOUNDARY",
                "source_locator": "/limitations/0",
                "handoff_locator": "/limitations/0",
            },
            {
                "item_id": "HTI-K2-UNRESOLVED-001",
                "kind": "unresolved",
                "criticality": "material",
                "required_for_handoff": True,
                "statement": "No source directly measures the proposed mediator.",
                "source_object_id": "CLAIM-EVID-001-K2-BOUNDARY",
                "source_locator": "/limitations/1",
                "handoff_locator": "/unresolved/0",
            },
        ],
    }


class ApiExecutionCloseoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for relative in (PROTOCOL_REF, TASK_REF, PROFILE_REF, ASSIGNMENT_REF, INPUT_REF):
            source = SOURCE_ROOT / relative
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def closeout(self, attempt_id: str, **overrides):
        values = {
            "root": self.root,
            "protocol_ref": PROTOCOL_REF,
            "task_ref": TASK_REF,
            "profile_ref": PROFILE_REF,
            "assignment_ref": ASSIGNMENT_REF,
            "attempt_id": attempt_id,
            "started_at": "2026-08-14T00:00:00Z",
            "finished_at": "2026-08-14T00:01:00Z",
            "terminal_status": "completed",
            "next_action": (
                "Review the admitted Evidence and decide whether to create a separate replication-search Task."
            ),
            "provider_adapter_id": "fake-local",
            "requested_model": "worker-model",
            "provider_adapter_version": "fixture-1",
            "expected_provider_identity": "fake-local",
            "limits": limits(),
            "session_result": session_result(),
            "output": completed_output(),
            "extra_limitations": ("Offline fake Provider; no live API compatibility was tested.",),
        }
        values.update(overrides)
        return closeout_api_attempt(**values)

    def test_windows_reserved_attempt_id_is_rejected_before_staging(self) -> None:
        with self.assertRaises(CloseoutError) as raised:
            self.closeout("CON")

        self.assertEqual("CLOSEOUT-ATTEMPT-ID", raised.exception.code)
        self.assertFalse((self.root / ".rwb").exists())

    def test_read_only_assignment_cannot_authorize_trusted_closeout(self) -> None:
        protocol = ProjectProtocol.from_mapping(load_document(self.root / PROTOCOL_REF))
        task = TaskPacket.from_mapping(load_document(self.root / TASK_REF))
        profile = AgentProfile.from_mapping(load_document(self.root / PROFILE_REF))
        assignment = ResolvedTask.from_mapping(load_document(self.root / ASSIGNMENT_REF))
        assignment = replace(
            assignment,
            effective_permissions=replace(
                assignment.effective_permissions,
                filesystem="read-only",
            ),
        )

        with self.assertRaises(CloseoutError) as raised:
            validate_closeout_preconditions(
                root=self.root,
                protocol=protocol,
                task=task,
                profile=profile,
                assignment=assignment,
                protocol_ref=PROTOCOL_REF,
                task_ref=TASK_REF,
                profile_ref=PROFILE_REF,
                assignment_ref=ASSIGNMENT_REF,
                attempt_id="A-K2-READ-ONLY",
                started_at="2026-08-14T00:00:00Z",
                finished_at="2026-08-14T00:01:00Z",
            )

        self.assertEqual("TASK-PERMISSION-ESCALATION", raised.exception.code)
        self.assertFalse((self.root / ".rwb").exists())

    def test_completed_bundle_validates_and_new_process_recovers_one_action(self) -> None:
        publication = self.closeout("A-K2-COMPLETED")

        self.assertEqual("completed", publication.status)
        self.assertTrue((self.root / publication.main_state_ref).is_file())
        self.assertFalse((self.root / ".rwb" / "closeout" / "A-K2-COMPLETED").exists())
        receipt = load_document(self.root / "work/EVID-001/A-K2-COMPLETED/execution-receipt.yaml")
        self.assertEqual("contract-satisfied", receipt["completion_claim"])
        self.assertEqual(
            {
                "provider_adapter_id": "fake-local",
                "requested_model": "worker-model",
            },
            receipt["model_binding"],
        )
        serialized = "\n".join(
            (self.root / relative).read_text(encoding="utf-8")
            for relative in publication.published_refs
        )
        self.assertNotIn("transient-response-id", serialized)

        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "research_workbench",
                "context",
                "resume-check",
                str(self.root / publication.main_state_ref),
                "--protocol",
                str(self.root / PROTOCOL_REF),
                "--root",
                str(self.root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("ok: no blocking deterministic risks", completed.stdout)
        state = load_document(self.root / publication.main_state_ref)
        self.assertEqual(1, len(state["next_actions"]))
        self.assertNotIn("extract", state["next_actions"][0].lower())

    def test_tool_failure_is_persisted_and_cannot_claim_completion(self) -> None:
        result = session_result(
            failures=(ToolFailureSummary("document-read", 1, "OSError"),)
        )
        publication = self.closeout("A-K2-TOOL-FAILED", session_result=result)

        self.assertEqual("failed", publication.status)
        attempt = load_document(self.root / "work/EVID-001/A-K2-TOOL-FAILED/attempt.yaml")
        receipt = load_document(
            self.root / "work/EVID-001/A-K2-TOOL-FAILED/execution-receipt.yaml"
        )
        self.assertEqual("CLIENT-TOOL-FAILED", attempt["failure"]["code"])
        self.assertEqual("document-read", attempt["failure"]["tool_failures"][0]["tool_name"])
        self.assertEqual(1, attempt["failure"]["tool_failures"][0]["call_number"])
        self.assertEqual("execution-only", receipt["completion_claim"])
        self.assertFalse(
            (self.root / "work/EVID-001/A-K2-TOOL-FAILED/transfer-manifest.yaml").exists()
        )

    def test_model_identity_mismatch_is_failed_not_completed(self) -> None:
        publication = self.closeout(
            "A-K2-MODEL-MISMATCH",
            session_result=session_result(model="unexpected-model"),
        )
        attempt = load_document(self.root / "work/EVID-001/A-K2-MODEL-MISMATCH/attempt.yaml")
        self.assertEqual("failed", publication.status)
        self.assertEqual("MODEL-IDENTITY-MISMATCH", attempt["failure"]["code"])

    def test_completed_closeout_requires_matching_session_identity(self) -> None:
        with self.assertRaises(CloseoutError) as missing:
            self.closeout("A-K2-NO-SESSION", session_result=None)
        self.assertEqual("CLOSEOUT-SESSION-RESULT-MISSING", missing.exception.code)
        self.assertFalse((self.root / ".rwb/closeout/A-K2-NO-SESSION").exists())

        with self.assertRaises(CloseoutError) as provider:
            self.closeout(
                "A-K2-PROVIDER-DRIFT",
                expected_provider_identity="another-provider",
            )
        self.assertEqual("CLOSEOUT-PROVIDER-MISMATCH", provider.exception.code)
        self.assertFalse((self.root / ".rwb/closeout/A-K2-PROVIDER-DRIFT").exists())

    def test_dynamic_artifact_path_must_match_exact_write_scope(self) -> None:
        attempt_id = "A-K2-DYNAMIC-SCOPE"
        task_path = self.root / TASK_REF
        task_document = load_document(task_path)
        task_document["write_scope"] = [
            f"work/EVID-001/{attempt_id}/*.yaml",
            f"work/EVID-001/{attempt_id}/artifacts/place*.yaml",
        ]
        task_path.write_text(
            yaml.safe_dump(task_document, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

        with self.assertRaises(CloseoutError) as raised:
            self.closeout(attempt_id)

        self.assertEqual("CLOSEOUT-WRITE-SCOPE", raised.exception.code)
        self.assertFalse((self.root / ".rwb/closeout" / attempt_id).exists())
        self.assertFalse((self.root / "work/EVID-001" / attempt_id).exists())

    def test_safe_pause_has_recoverable_handoff_without_fabricated_artifacts(self) -> None:
        paused = session_result(status=ApiSessionStatus.SAFE_PAUSED)
        publication = self.closeout(
            "A-K2-SAFE-PAUSED",
            terminal_status="safe-paused",
            session_result=paused,
            output=None,
            next_action="Increase the explicit budget or stop; do not replay the prior tool call automatically.",
        )
        handoff = load_document(self.root / "work/EVID-001/A-K2-SAFE-PAUSED/handoff.yaml")
        receipt = load_document(
            self.root / "work/EVID-001/A-K2-SAFE-PAUSED/execution-receipt.yaml"
        )
        self.assertEqual("safe-paused", publication.status)
        self.assertTrue(handoff["unresolved"])
        self.assertEqual([], handoff["artifact_refs"])
        self.assertEqual("execution-only", receipt["completion_claim"])

    def test_stale_input_is_a_blocked_closeout_with_refresh_as_only_action(self) -> None:
        (self.root / INPUT_REF).write_text("changed after Task freeze", encoding="utf-8")
        action = "Create a new Task revision with the refreshed input hash; do not run this stale Task."
        publication = self.closeout(
            "A-K2-STALE",
            terminal_status="blocked",
            session_result=None,
            output=None,
            failure_code="REF-HASH-MISMATCH",
            failure_summary="The frozen input hash no longer matches the project file.",
            next_action=action,
        )
        state = load_document(self.root / publication.main_state_ref)
        self.assertEqual("blocked", publication.status)
        self.assertEqual([action], state["next_actions"])
        self.assertFalse((self.root / "work/EVID-001/A-K2-STALE/transfer-manifest.yaml").exists())

    def test_main_state_is_last_and_identical_retry_resumes_publication(self) -> None:
        previous_ref = "work/checkpoints/main-state-before-k2.yaml"
        previous = {
            "schema_version": "0.1.0",
            "checkpoint_id": "MS-BEFORE-K2",
            "continuity_status": "active",
            "project_protocol_ref": f"{PROTOCOL_REF}@1",
            "current_questions": ["Q-001@1"],
            "pinned_constraints": ["keep-this-constraint"],
            "accepted_decisions": ["D-001@1"],
            "active_tasks": [],
            "recent_handoffs": [],
            "open_conflicts": [],
            "open_risks": [],
            "next_actions": ["Run the bounded K-API-2 fixture."],
            "artifact_index_refs": [],
            "machine_state_refs": [
                {"path": PROTOCOL_REF, "sha256": hash_file(self.root / PROTOCOL_REF)}
            ],
        }
        previous["checkpoint_digest"] = checkpoint_digest(previous)
        write_yaml_exclusive(self.root / previous_ref, previous)
        previous_hash = hash_file(self.root / previous_ref)

        def crash(point: str) -> None:
            if point == "before-main-state-publish":
                raise RuntimeError("simulated process loss")

        with self.assertRaisesRegex(RuntimeError, "simulated process loss"):
            self.closeout(
                "A-K2-CRASH",
                previous_main_state_ref=previous_ref,
                fault_injector=crash,
            )

        new_state = self.root / "work/EVID-001/A-K2-CRASH/main-state.yaml"
        self.assertFalse(new_state.exists())
        self.assertEqual(previous_hash, hash_file(self.root / previous_ref))
        self.assertTrue((self.root / "work/EVID-001/A-K2-CRASH/handoff.yaml").is_file())

        publication = self.closeout(
            "A-K2-CRASH",
            previous_main_state_ref=previous_ref,
        )
        self.assertTrue((self.root / publication.main_state_ref).is_file())
        state = load_document(self.root / publication.main_state_ref)
        self.assertIn("keep-this-constraint", state["pinned_constraints"])
        self.assertIn("D-001@1", state["accepted_decisions"])

    def test_different_existing_target_is_never_overwritten_or_committed(self) -> None:
        attempt_root = self.root / "work/EVID-001/A-K2-COLLISION"
        attempt_root.mkdir(parents=True)
        handoff = attempt_root / "handoff.yaml"
        sentinel = b"sentinel: do-not-overwrite\n"
        handoff.write_bytes(sentinel)

        with self.assertRaises(FileExistsError):
            self.closeout("A-K2-COLLISION")

        self.assertEqual(sentinel, handoff.read_bytes())
        self.assertFalse((attempt_root / "main-state.yaml").exists())
        self.assertTrue((self.root / ".rwb/closeout/A-K2-COLLISION/plan.yaml").is_file())


if __name__ == "__main__":
    unittest.main()
