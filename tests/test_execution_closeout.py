"""K-API-2 closeout transaction tests.

The closeout must turn one session outcome into the full seven-object file
chain atomically: a crash between publishes may never expose a main state
that references documents which do not exist, and a re-run with the same
deterministic plan must resume instead of duplicating or diverging.
"""

import os
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from research_workbench.adapters.models import (
    AggregateUsage,
    ApiSessionResult,
    ApiSessionStatus,
    Capability,
    FinishReason,
    ModelBinding,
    ModelResponse,
)
from research_workbench.artifacts.integrity import hash_file
from research_workbench.capability.models import AgentProfile
from research_workbench.capability.resolver import ResolvedTask
from research_workbench.context import assess_handoff_transfer
from research_workbench.contracts import to_plain
from research_workbench.execution import (
    CloseoutError,
    CloseoutStatuses,
    CompiledSession,
    ExecutionPolicy,
    SessionOutcome,
    build_closeout_documents,
    compile_session,
    map_outcome,
    outcome_from_result,
    run_closeout,
)
from research_workbench.io import load_document
from research_workbench.observability import ExecutionReceipt, check_execution_receipt
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import AttemptRecord, FileReference, HandoffPacket, TaskPacket
from research_workbench.validation import check_handoff_against_task
from research_workbench.validation.schemas import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]

TASK_PATH = "examples/task-evidence.yaml"
PROFILE_PATH = "registry/agents/evidence-scout.yaml"
CHECKER_PATH = "src/research_workbench/execution/checks.py"

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


def build_project(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "examples" / "fixtures", destination / "examples" / "fixtures", dirs_exist_ok=True)
    shutil.copytree(
        ROOT / ".agents" / "skills" / "literature-evidence-extraction",
        destination / ".agents" / "skills" / "literature-evidence-extraction",
        dirs_exist_ok=True,
    )
    shutil.copy(ROOT / "examples" / "task-evidence.yaml", destination / "examples" / "task-evidence.yaml")
    shutil.copy(ROOT / "examples" / "project-protocol.yaml", destination / "examples" / "project-protocol.yaml")
    destination.joinpath("registry", "agents").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / PROFILE_PATH, destination / PROFILE_PATH)
    checker = destination / CHECKER_PATH
    checker.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / CHECKER_PATH, checker)
    return destination


def worker_binding() -> ModelBinding:
    return ModelBinding(
        slot_id="worker",
        role="worker",
        provider_adapter="fake-worker",
        model="worker-model",
        capabilities=frozenset({Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}),
        reasoning_effort=None,
        specialties=(),
    )


def fake_result(status: ApiSessionStatus, stop_reason: str, *, turns: int = 2, tools: int = 1) -> ApiSessionResult:
    return ApiSessionResult(
        status=status,
        stop_reason=stop_reason,
        provider="fake-worker",
        requested_model="worker-model",
        observed_models=("worker-model",),
        model_turns=turns,
        tool_calls=tools,
        usage=AggregateUsage(
            input_tokens=48,
            output_tokens=12,
            cached_input_tokens=None,
            reasoning_tokens=None,
            provider_reported_cost=None,
            currency=None,
        ),
        final_response=ModelResponse(
            response_id="r2",
            provider="fake-worker",
            model="worker-model",
            output=(),
            finish_reason=FinishReason.COMPLETE,
        ),
        warnings=(),
    )


def completed_outcome() -> SessionOutcome:
    return outcome_from_result(
        fake_result(ApiSessionStatus.COMPLETED, "complete"), structured_output=dict(STRUCTURED_OUTPUT)
    )


def paused_outcome() -> SessionOutcome:
    return outcome_from_result(
        fake_result(ApiSessionStatus.SAFE_PAUSED, "tool-result-size-budget", turns=1, tools=0)
    )


def prepare(root: Path, outcome: SessionOutcome):
    task = TaskPacket.from_mapping(load_document(root / TASK_PATH))
    profile = AgentProfile.from_mapping(load_document(root / PROFILE_PATH))
    assignment = ResolvedTask.from_mapping(
        load_document(ROOT / "examples" / "vertical-slice" / "evidence-assignment.yaml")
    )
    protocol = ProjectProtocol.from_mapping(load_document(root / "examples" / "project-protocol.yaml"))
    compiled = compile_session(task, profile, assignment, worker_binding(), root=root)
    plan = build_closeout_documents(
        task,
        assignment,
        worker_binding(),
        compiled,
        outcome,
        root=root,
        protocol=protocol,
        protocol_path="examples/project-protocol.yaml",
        profile_path=PROFILE_PATH,
        task_path=TASK_PATH,
        started_at="2026-08-14T00:00:00Z",
        finished_at="2026-08-14T00:01:00Z",
    )
    return task, assignment, protocol, plan


class MapOutcomeTests(unittest.TestCase):
    def test_completed_with_passing_check_claims_contract_satisfied(self) -> None:
        statuses = map_outcome(
            ApiSessionStatus.COMPLETED, "complete", check_passed=True, model_drift=False
        )
        self.assertEqual("completed", statuses.record_status)
        self.assertEqual("stage-completed", statuses.continuity_status)
        self.assertEqual("contract-satisfied", statuses.completion_claim)

    def test_completed_without_check_stays_execution_only(self) -> None:
        statuses = map_outcome(ApiSessionStatus.COMPLETED, "stop", check_passed=False)
        self.assertEqual("execution-only", statuses.completion_claim)

    def test_model_drift_blocks_completion_claim(self) -> None:
        statuses = map_outcome(
            ApiSessionStatus.COMPLETED, "complete", check_passed=True, model_drift=True
        )
        self.assertIsNone(statuses.completion_claim)
        self.assertIn("model differs", statuses.rollover_reason)

    def test_non_completed_statuses_map_to_recoverable_states(self) -> None:
        paused = map_outcome(ApiSessionStatus.SAFE_PAUSED, "tool-call-budget")
        self.assertEqual(("safe-paused", "safe-paused", None), (paused.record_status, paused.continuity_status, paused.completion_claim))
        self.assertIn("tool-call-budget", paused.rollover_reason)

        blocked = map_outcome(ApiSessionStatus.BLOCKED, "refusal")
        self.assertEqual(("blocked", "blocked", None), (blocked.record_status, blocked.continuity_status, blocked.completion_claim))

        incomplete = map_outcome(ApiSessionStatus.INCOMPLETE, "length")
        self.assertEqual(("incomplete", "waiting", None), (incomplete.record_status, incomplete.continuity_status, incomplete.completion_claim))

        failed = map_outcome(ApiSessionStatus.FAILED, "error")
        self.assertEqual(("failed", "blocked", None), (failed.record_status, failed.continuity_status, failed.completion_claim))


class CloseoutDocumentTests(unittest.TestCase):
    def test_plan_is_publish_ordered_with_main_state_last(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            _, _, _, plan = prepare(root, completed_outcome())
            roles = tuple(doc.role for doc in plan.documents)
            self.assertEqual("main-state", roles[-1])
            self.assertLess(roles.index("receipt"), roles.index("main-state"))
            self.assertLess(roles.index("attempt"), roles.index("receipt"))
            self.assertLess(roles.index("handoff"), roles.index("attempt"))
            for document in plan.documents[:-1]:
                self.assertTrue(document.path.startswith(plan.batch_dir + "/"), document.path)
            self.assertTrue(plan.main_state_path.startswith("checkpoints/"))
            self.assertNotIn("main-state", plan.documents[-2].path)

    def test_run_closeout_publishes_valid_cross_consistent_chain(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            task, assignment, protocol, plan = prepare(root, completed_outcome())
            result = run_closeout(plan, root=root, protocol=protocol, task=task, assignment=assignment)

            self.assertFalse(result.resumed)
            for _, relative, digest in result.published:
                self.assertEqual(digest, hash_file(root / relative))
            self.assertFalse((root / plan.batch_dir / ".staging").exists())

            catalog = SchemaCatalog()
            kinds = {
                "evidence": "research_object",
                "check": "deterministic_check_report",
                "manifest": "handoff_transfer_manifest",
                "audit": "handoff_transfer_audit",
                "task-snapshot": "context_snapshot",
                "main-snapshot": "context_snapshot",
                "assignment": "skill_assignment",
                "handoff": "handoff_packet",
                "attempt": "attempt",
                "receipt": "execution_receipt",
                "main-state": "main_state",
            }
            for document in plan.documents:
                written = load_document(root / document.path)
                self.assertEqual(
                    [], catalog.validate(kinds[document.role], written), document.role
                )

            attempt = AttemptRecord.from_mapping(load_document(root / plan.batch_dir / "attempt.yaml"))
            handoff = HandoffPacket.from_mapping(load_document(root / plan.batch_dir / "handoff.yaml"))
            receipt = ExecutionReceipt.from_mapping(
                load_document(root / plan.batch_dir / "execution-receipt.yaml")
            )
            self.assertEqual("completed", attempt.status)
            self.assertEqual("completed", handoff.status)
            self.assertEqual("contract-satisfied", receipt.completion_claim)
            self.assertEqual("model-api", receipt.execution_kind)
            self.assertEqual("measured", receipt.model_usage_status)
            self.assertTrue(
                set(attempt.artifact_refs) | {attempt.handoff_ref}
                <= set(receipt.output_refs)
            )
            self.assertEqual(
                sorted(ref.path for ref in attempt.input_lock),
                sorted(ref.path for ref in task.input_refs),
            )

            receipt_risks = check_execution_receipt(
                receipt, protocol, root=root, receipt_ref=plan.path_for("receipt")
            )
            handoff_risks = check_handoff_against_task(
                task, handoff, project_root=root, assignment=assignment
            )
            audit_risks = assess_handoff_transfer(
                load_document(root / plan.batch_dir / "transfer-audit.yaml"), root=root
            )
            for risks, label in (
                (receipt_risks, "receipt"),
                (handoff_risks, "handoff"),
                (audit_risks.risks, "audit"),
            ):
                blockers = [risk.code for risk in risks if risk.level.value == "block"]
                self.assertEqual([], blockers, label)

    def test_safe_paused_chain_satisfies_recovery_rules(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            task, assignment, protocol, plan = prepare(root, paused_outcome())
            run_closeout(plan, root=root, protocol=protocol, task=task, assignment=assignment)

            handoff = HandoffPacket.from_mapping(load_document(root / plan.batch_dir / "handoff.yaml"))
            receipt = ExecutionReceipt.from_mapping(
                load_document(root / plan.batch_dir / "execution-receipt.yaml")
            )
            attempt = AttemptRecord.from_mapping(load_document(root / plan.batch_dir / "attempt.yaml"))
            self.assertEqual("safe-paused", handoff.status)
            self.assertTrue(handoff.unresolved)
            self.assertTrue(handoff.recommended_next_actions)
            self.assertIsNotNone(receipt.context_snapshot_ref)
            self.assertIsNotNone(attempt.handoff_ref)
            self.assertIsNone(receipt.completion_claim)

            receipt_risks = check_execution_receipt(
                receipt, protocol, root=root, receipt_ref=plan.path_for("receipt")
            )
            handoff_risks = check_handoff_against_task(task, handoff, project_root=root, assignment=assignment)
            audit = assess_handoff_transfer(
                load_document(root / plan.batch_dir / "transfer-audit.yaml"), root=root
            )
            for risks in (receipt_risks, handoff_risks, audit.risks):
                blockers = [risk.code for risk in risks if risk.level.value == "block"]
                self.assertEqual([], blockers)

            main_state = load_document(root / plan.main_state_path)
            self.assertEqual("safe-paused", main_state["continuity_status"])
            self.assertTrue(main_state["rollover_reason"])


    def test_verification_failure_writes_no_marker_and_reruns_raise(self) -> None:
        """H-1 regression: a failed post-publish verification must never be
        swallowed by the idempotent skip on a later run."""

        import dataclasses

        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            task, assignment, protocol, plan = prepare(root, completed_outcome())
            drifted_task = dataclasses.replace(task, revision=task.revision + 1)

            for _ in range(2):
                with self.assertRaises(CloseoutError) as caught:
                    run_closeout(
                        plan,
                        root=root,
                        protocol=protocol,
                        task=drifted_task,
                        assignment=assignment,
                    )
                self.assertEqual("EXEC-CLOSEOUT-VERIFICATION-FAILED", caught.exception.code)

            marker = root / plan.batch_dir / "closeout-complete.txt"
            self.assertFalse(marker.exists())


class CloseoutAtomicityTests(unittest.TestCase):
    def test_rerun_with_same_plan_is_idempotent(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            task, assignment, protocol, plan = prepare(root, completed_outcome())
            first = run_closeout(plan, root=root, protocol=protocol, task=task, assignment=assignment)
            hashes = {relative: digest for _, relative, digest in first.published}

            second = run_closeout(plan, root=root, protocol=protocol, task=task, assignment=assignment)

            self.assertTrue(second.resumed)
            self.assertEqual(sorted(hashes), sorted(relative for _, relative, _ in second.published))
            for relative, digest in hashes.items():
                self.assertEqual(digest, hash_file(root / relative))

    def test_partial_publish_resumes_without_diverging(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            task, assignment, protocol, plan = prepare(root, completed_outcome())
            run_closeout(plan, root=root, protocol=protocol, task=task, assignment=assignment)
            survivors = {
                document.path: hash_file(root / document.path)
                for document in plan.documents
            }
            removed = plan.documents[-3].path
            (root / removed).unlink()

            run_closeout(plan, root=root, protocol=protocol, task=task, assignment=assignment)

            for document in plan.documents:
                self.assertTrue((root / document.path).exists(), document.path)
            for relative, digest in survivors.items():
                if relative == removed:
                    continue
                self.assertEqual(digest, hash_file(root / relative))

    def test_os_link_failure_matrix_never_exposes_partial_main_state(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            task, assignment, protocol, plan = prepare(root, completed_outcome())
            real_link = os.link

            for fail_position in range(1, len(plan.documents) + 1):
                with self.subTest(fail_position=fail_position):
                    for document in plan.documents:
                        target = root / document.path
                        if target.exists():
                            target.unlink()
                    marker = root / plan.batch_dir / "closeout-complete.txt"
                    if marker.exists():
                        marker.unlink()
                    shutil.rmtree(root / plan.batch_dir / ".staging", ignore_errors=True)
                    state = {"calls": 0}

                    def failing_link(source, destination):
                        state["calls"] += 1
                        if state["calls"] == fail_position:
                            raise OSError("injected link failure")
                        return real_link(source, destination)

                    with mock.patch("research_workbench.execution.closeout.os.link", failing_link):
                        with self.assertRaises(CloseoutError) as caught:
                            run_closeout(
                                plan, root=root, protocol=protocol, task=task, assignment=assignment
                            )
                    self.assertEqual("EXEC-CLOSEOUT-INCOMPLETE", caught.exception.code)

                    self.assertFalse((root / plan.main_state_path).exists())
                    self.assertFalse((root / plan.batch_dir / "closeout-complete.txt").exists())
                    published = [doc.path for doc in plan.documents if (root / doc.path).exists()]
                    self.assertLess(len(published), len(plan.documents))

                    run_closeout(plan, root=root, protocol=protocol, task=task, assignment=assignment)
                    for document in plan.documents:
                        self.assertTrue((root / document.path).exists(), document.path)
                    self.assertTrue((root / plan.batch_dir / "closeout-complete.txt").exists())

    def test_conflicting_existing_target_blocks_publish(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            task, assignment, protocol, plan = prepare(root, completed_outcome())
            conflicting = root / plan.documents[2].path
            conflicting.parent.mkdir(parents=True, exist_ok=True)
            conflicting.write_text("different content", encoding="utf-8")

            with self.assertRaises(CloseoutError) as caught:
                run_closeout(plan, root=root, protocol=protocol, task=task, assignment=assignment)
            self.assertEqual("EXEC-CLOSEOUT-PATH-CONFLICT", caught.exception.code)
            self.assertFalse((root / plan.main_state_path).exists())

    def test_staged_validation_failure_publishes_nothing(self) -> None:
        with TemporaryDirectory() as directory:
            root = build_project(Path(directory))
            task, assignment, protocol, plan = prepare(root, completed_outcome())
            tampered = {
                **plan.documents[0].document,
                "status": "tampered",
            }
            import dataclasses

            broken = dataclasses.replace(plan.documents[0], document=tampered)
            documents = (broken, *plan.documents[1:])
            broken_plan = dataclasses.replace(plan, documents=documents)

            with self.assertRaises(CloseoutError) as caught:
                run_closeout(
                    broken_plan, root=root, protocol=protocol, task=task, assignment=assignment
                )
            self.assertEqual("EXEC-CLOSEOUT-INVALID", caught.exception.code)
            for document in plan.documents:
                self.assertFalse((root / document.path).exists(), document.path)
            self.assertFalse((root / plan.main_state_path).exists())
            self.assertFalse((root / plan.batch_dir / ".staging").exists())


if __name__ == "__main__":
    unittest.main()
