"""Contract tests for execution.closeout (K-API-2 §3/§4).

Every test builds the ExecutionPlan/ExecutionRunResult by hand inside a scratch
workspace; no real provider, network, or credential is ever touched.
"""

from __future__ import annotations

import contextlib
import json
import unittest
from dataclasses import replace
from pathlib import Path

import yaml

from research_workbench.adapters.models.port import (
    ContentBlock,
    FinishReason,
    ModelRequest,
    ModelResponse,
    Usage,
)
from research_workbench.adapters.models.session import (
    AggregateUsage,
    ApiSessionLimits,
    ApiSessionResult,
    ApiSessionStatus,
)
from research_workbench.artifacts.integrity import hash_file
from research_workbench.capability.models import SkillLock
from research_workbench.capability.resolver import _assignment_identifier
from research_workbench.contracts import PermissionPolicy, RiskLevel
from research_workbench.execution import (
    ATTEMPT_FILENAME,
    CHECK_REPORT_FILENAME,
    COMPLETION_MANIFEST_FILENAME,
    HANDOFF_FILENAME,
    PLAN_FILENAME,
    RECEIPT_FILENAME,
    TRANSCRIPT_FILENAME,
    ExecutionPlan,
    ExecutionRunResult,
    FrozenContractRef,
    ModelBinding,
    ToolEvent,
)
from research_workbench.execution.closeout import (
    MANIFEST_FILENAME,
    TRANSFER_AUDIT_FILENAME,
    closeout,
    verify_attempt,
)
from research_workbench.io import load_document
from research_workbench.observability.trace import AgentTraceRecorder
from research_workbench.tasks import FileReference, HandoffPolicy

from support import temporary_workspace

TASK_ID = "T-001"
ATTEMPT_ID = "A-001"
ATTEMPT_DIR = f"work/{TASK_ID}/{ATTEMPT_ID}"
STARTED_AT = "2026-08-19T00:00:00Z"

EVIDENCE_RECORD = """\
schema_version: 0.1.0
object_type: evidence
object_id: EVID-T-001-01
revision: 1
status: drafted
content_hash: 82ea6f0d2455b97cf98786d01b8b461953e1badba4491f168a04471b39820b67
kind: bounded-text-excerpt
source_ref: INPUT-SYNTHETIC-001@1
locator: lines 1-2
statement: The bounded source explicitly identifies itself as a synthetic structural fixture.
quality_flags: [synthetic_fixture, not_scientific_evidence]
metadata:
  generated_by: closeout-test
  source_file_ref:
    path: inputs/paper.txt
    sha256: __SOURCE_SHA256__
"""

FINAL_COMPLETED = json.dumps(
    {
        "status": "completed",
        "summary": "Extracted one bounded Evidence record from the synthetic source.",
        "limitations": ["The source is a synthetic structural fixture, not scientific evidence."],
        "unresolved": [],
    }
)


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_yaml(root: Path, relative: str, document: dict) -> Path:
    return _write(root, relative, yaml.safe_dump(document, sort_keys=False, allow_unicode=True))


class CloseoutWorkspace:
    """One scratch project root with the frozen Task/Profile/Assignment inputs."""

    def __init__(self, root: Path, *, with_task: bool = True, require_manifest: bool = False):
        self.root = root
        self.input_path = _write(root, "inputs/paper.txt", "synthetic bounded source\n")
        self.input_ref = FileReference("inputs/paper.txt", hash_file(self.input_path))
        _write_yaml(
            root,
            "profiles/test-profile.yaml",
            {
                "schema_version": "0.1.0",
                "agent_profile_id": "test-profile",
                "version": "1.0.0",
                "purpose": "bounded closeout test double",
                "model_policy": {},
                "permission_ceiling": {"filesystem": "worktree-write", "external_write": False},
                "allowed_tool_capabilities": ["document-read"],
                "default_context_policy": "minimal",
                "delegation": {"allowed": False},
                "output_contracts": ["evidence-record", "handoff-packet"],
            },
        )
        # ResolvedTask validates assignment_id against canonical content, so the
        # fixture derives it with the same helper the resolver uses.
        assignment_id = _assignment_identifier(
            task_id=TASK_ID,
            task_revision=1,
            agent_profile="test-profile@1.0.0",
            skill_lock=(SkillLock("skill-a", "1.0.0", "a" * 64),),
            resolved_tools=("read_file",),
            effective_permissions=PermissionPolicy(
                filesystem="worktree-write", external_write=False
            ),
            output_contracts=("evidence-record", "handoff-packet"),
            registry_digest=None,
        )
        _write_yaml(
            root,
            "assignments/assignment.yaml",
            {
                "schema_version": "0.1.0",
                "assignment_id": assignment_id,
                "task_id": TASK_ID,
                "task_revision": 1,
                "agent_profile": "test-profile@1.0.0",
                "skill_lock": [
                    {"skill_id": "skill-a", "version": "1.0.0", "content_hash": "a" * 64}
                ],
                "resolved_tools": ["read_file"],
                "effective_permissions": {"filesystem": "worktree-write", "external_write": False},
                "output_contracts": ["evidence-record", "handoff-packet"],
                "resolution_reason": ["all required capabilities are covered"],
            },
        )
        _write_yaml(
            root,
            "project-protocol.yaml",
            {
                "schema_version": "0.1.0",
                "project_id": "closeout-test",
                "question_refs": ["Q-1@1"],
                "active_modes": ["evidence-synthesis"],
                "claim_ceiling": ["bounded"],
                "required_human_gates": ["publication"],
                "budgets": {
                    "max_parallel_subagents": 1,
                    "max_delegation_depth": 1,
                    "coordination_cost_ratio_warn": 0.33,
                },
                "context_policy": {},
                "data_boundary": {"local_only": True},
            },
        )
        if with_task:
            required_outputs = ["evidence-record", "handoff-packet"]
            if require_manifest:
                required_outputs.insert(1, "handoff-transfer-manifest")
            _write_yaml(
                root,
                f"tasks/{TASK_ID}.yaml",
                {
                    "schema_version": "0.1.0",
                    "task_id": TASK_ID,
                    "goal": "Extract one bounded evidence record.",
                    "question_refs": ["Q-1@1"],
                    "active_modes": ["evidence-synthesis"],
                    "required_capabilities": ["evidence-extraction"],
                    "required_skills": ["skill-a@1.0.0"],
                    "forbidden_skills": [],
                    "agent_profile": "test-profile",
                    "input_refs": [{"path": self.input_ref.path, "sha256": self.input_ref.sha256}],
                    "write_scope": [f"work/{TASK_ID}/**"],
                    "required_outputs": required_outputs,
                    "permissions": {
                        "filesystem": "worktree-write",
                        "external_write": False,
                        "allowed_roots": [f"work/{TASK_ID}"],
                    },
                    "delegation": {"allowed": False},
                    "budget": {"max_turns": 5},
                    "atomic_boundary": "One bounded source is inspected.",
                    "completion_checks": ["required outputs pass deterministic checks"],
                    "safe_pause_conditions": ["a required source is unavailable"],
                    "stop_conditions": ["required_outputs_complete"],
                    "stale_if": ["any_input_hash_changes"],
                    "handoff_policy": {
                        "require_transfer_manifest": require_manifest,
                        "semantic_review": "risk-triggered",
                        "minimum_semantic_samples": 1,
                    },
                },
            )
        self.require_manifest = require_manifest

    def plan(self, *, required_outputs: tuple[str, ...] | None = None) -> ExecutionPlan:
        if required_outputs is None:
            required_outputs = ("evidence-record", "handoff-packet")
            if self.require_manifest:
                required_outputs = ("evidence-record", "handoff-transfer-manifest", "handoff-packet")
        return ExecutionPlan(
            attempt_id=ATTEMPT_ID,
            task_id=TASK_ID,
            task_revision=1,
            root=str(self.root),
            attempt_dir=ATTEMPT_DIR,
            model_binding=ModelBinding(
                slot_id="worker",
                provider_adapter="test-adapter",
                provider="scripted",
                model="stub-model",
            ),
            request=ModelRequest(model="stub-model", messages=()),
            limits=ApiSessionLimits(
                max_model_turns=8,
                max_tool_calls=12,
                max_parallel_tool_calls=4,
                max_tool_result_chars=8000,
                max_output_tokens_per_turn=4096,
                max_seconds=900.0,
            ),
            input_lock=(self.input_ref,),
            readable_inputs=(self.input_ref.path,),
            write_scope=(f"work/{TASK_ID}/**",),
            required_outputs=required_outputs,
            skill_lock=("skill-a@1.0.0",),
            assignment_ref="assignments/assignment.yaml",
            profile_ref="profiles/test-profile.yaml",
            handoff_policy=HandoffPolicy(
                require_transfer_manifest=self.require_manifest,
                semantic_review="risk-triggered",
                minimum_semantic_samples=1,
            ),
            started_at=STARTED_AT,
        )

    def write_output(self, name: str = "evidence-record.yaml", content: str = EVIDENCE_RECORD) -> Path:
        content = content.replace("__SOURCE_SHA256__", self.input_ref.sha256)
        return _write(self.root, f"{ATTEMPT_DIR}/outputs/{name}", content)

    def run(
        self,
        *,
        status: ApiSessionStatus = ApiSessionStatus.COMPLETED,
        stop_reason: str = "complete",
        final_text: str | None = FINAL_COMPLETED,
        usage: AggregateUsage | None = None,
        stale_inputs: tuple[str, ...] = (),
        with_output_event: bool = True,
    ) -> ExecutionRunResult:
        if usage is None:
            usage = AggregateUsage(
                input_tokens=2100,
                output_tokens=340,
                cached_input_tokens=None,
                reasoning_tokens=None,
                provider_reported_cost=None,
                currency=None,
            )
        final_response = None
        if final_text is not None:
            final_response = ModelResponse(
                response_id="resp-1",
                provider="scripted",
                model="stub-model",
                output=(ContentBlock(kind="text", text=final_text),),
                finish_reason=FinishReason.COMPLETE,
                usage=Usage(input_tokens=1200, output_tokens=120),
            )
        tool_events: tuple[ToolEvent, ...] = ()
        if with_output_event:
            output_path = self.root / ATTEMPT_DIR / "outputs" / "evidence-record.yaml"
            sha256 = hash_file(output_path) if output_path.is_file() else None
            tool_events = (
                ToolEvent(
                    name="write_artifact",
                    ok=True,
                    path=f"{ATTEMPT_DIR}/outputs/evidence-record.yaml",
                    sha256=sha256,
                ),
            )
        session = ApiSessionResult(
            status=status,
            stop_reason=stop_reason,
            provider="scripted",
            requested_model="stub-model",
            observed_models=("stub-model",),
            model_turns=2,
            tool_calls=1 if with_output_event else 0,
            usage=usage,
            final_response=final_response,
            warnings=(),
        )
        index_path = self.root / ATTEMPT_DIR / "INDEX.yaml"
        redactions = 0
        if not index_path.exists():
            plan = self.plan()
            recorder = AgentTraceRecorder(
                self.root / ATTEMPT_DIR,
                task_id=TASK_ID,
                task_revision=1,
                attempt_id=ATTEMPT_ID,
                task_snapshot=plan.to_mapping(),
                accountable_owner="closeout-test-owner",
                actor_id="runtime-closeout-test",
                runtime_identity="test-adapter:stub-model",
                provider="scripted",
                read_allowlist=(self.input_ref.path,),
                write_scope=(f"work/{TASK_ID}/**",),
                tool_allowlist=(),
            )
            recorder.record("provider-request", {"request": {"model": "stub-model", "messages": []}})
            if final_response is not None:
                recorder.record("provider-response", {"response": final_response})
            recorder.record("session-status", {"status": status.value, "reason": stop_reason})
            recorder.seal(status.value)
            redactions = recorder.redaction_count
        return ExecutionRunResult(
            session=session,
            tool_events=tool_events,
            stale_inputs=stale_inputs,
            transcript=(
                {
                    "request": {"model": "stub-model", "messages": []},
                    "response": {"response_id": "resp-1", "model": "stub-model"},
                },
            ),
            trace_ref=FrozenContractRef(
                path=f"{ATTEMPT_DIR}/INDEX.yaml",
                sha256=hash_file(index_path),
            ),
            trace_redactions=redactions,
        )


def _block_codes(result_risks) -> set[str]:
    return {risk.code for risk in result_risks if risk.level == RiskLevel.BLOCK}


class CloseoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self._stack = contextlib.ExitStack()
        self.addCleanup(self._stack.close)
        self.root = self._stack.enter_context(temporary_workspace())

    def workspace(self, **kwargs) -> CloseoutWorkspace:
        return CloseoutWorkspace(self.root, **kwargs)

    def test_completed_closeout_publishes_the_full_chain(self) -> None:
        workspace = self.workspace(require_manifest=True)
        workspace.write_output()
        result = closeout(workspace.plan(), workspace.run(), root=self.root)

        self.assertEqual("completed", result.status, [str(risk) for risk in result.risks])
        self.assertEqual(set(), _block_codes(result.risks))
        attempt_dir = self.root / ATTEMPT_DIR
        for name in (
            PLAN_FILENAME,
            TRANSCRIPT_FILENAME,
            ATTEMPT_FILENAME,
            RECEIPT_FILENAME,
            HANDOFF_FILENAME,
            CHECK_REPORT_FILENAME,
            MANIFEST_FILENAME,
            TRANSFER_AUDIT_FILENAME,
            COMPLETION_MANIFEST_FILENAME,
        ):
            self.assertTrue((attempt_dir / name).is_file(), name)
        self.assertEqual(f"{ATTEMPT_DIR}/{ATTEMPT_FILENAME}", result.attempt_path)
        self.assertEqual(f"{ATTEMPT_DIR}/{RECEIPT_FILENAME}", result.receipt_path)
        self.assertEqual(f"{ATTEMPT_DIR}/{HANDOFF_FILENAME}", result.handoff_path)
        self.assertEqual(f"{ATTEMPT_DIR}/{CHECK_REPORT_FILENAME}", result.check_report_path)

        attempt = load_document(attempt_dir / ATTEMPT_FILENAME)
        self.assertEqual("completed", attempt["status"])
        self.assertEqual(f"{ATTEMPT_DIR}/{RECEIPT_FILENAME}", attempt["execution_receipt_ref"])
        self.assertEqual(f"{ATTEMPT_DIR}/{HANDOFF_FILENAME}", attempt["handoff_ref"])
        handoff = load_document(attempt_dir / HANDOFF_FILENAME)
        self.assertEqual("completed", handoff["status"])
        self.assertEqual(f"{ATTEMPT_DIR}/{MANIFEST_FILENAME}", handoff["transfer_manifest_ref"])
        self.assertEqual([f"{ATTEMPT_DIR}/{TRANSFER_AUDIT_FILENAME}"], handoff["validation_refs"])
        receipt = load_document(attempt_dir / RECEIPT_FILENAME)
        self.assertEqual("model-api", receipt["execution_kind"])
        self.assertEqual("execution-only", receipt["completion_claim"])
        self.assertEqual("scripted", receipt["runtime"]["name"])
        self.assertEqual("test-adapter", receipt["runtime"]["adapter_version"])
        self.assertEqual("resp-1", receipt["runtime"]["native_execution_id"])
        self.assertEqual("measured", receipt["model_usage_status"])

        # verify_attempt is file-only, idempotent, and clean on the fresh chain.
        first = verify_attempt(attempt_dir, root=self.root)
        second = verify_attempt(attempt_dir, root=self.root)
        self.assertEqual(first, second)
        self.assertEqual([], [risk for risk in first if risk.level == RiskLevel.BLOCK])

    def test_missing_trace_ref_blocks_and_forbids_completion_marker(self) -> None:
        workspace = self.workspace()
        workspace.write_output()
        run = replace(workspace.run(), trace_ref=None)
        result = closeout(workspace.plan(), run, root=self.root)
        self.assertNotEqual("completed", result.status)
        self.assertIn("EXEC-TRACE-MISSING", _block_codes(result.risks))
        self.assertIsNone(result.completion_manifest_path)
        self.assertFalse((self.root / ATTEMPT_DIR / COMPLETION_MANIFEST_FILENAME).exists())

    def test_receipt_usage_reconciliation_is_field_exact(self) -> None:
        workspace = self.workspace()
        workspace.write_output()
        usage = AggregateUsage(
            input_tokens=2100,
            output_tokens=340,
            cached_input_tokens=10,
            reasoning_tokens=5,
            provider_reported_cost=0.03,
            currency="USD",
        )
        result = closeout(workspace.plan(), workspace.run(usage=usage), root=self.root)
        self.assertEqual("completed", result.status, [str(risk) for risk in result.risks])
        receipt = load_document(self.root / ATTEMPT_DIR / RECEIPT_FILENAME)
        self.assertEqual(1, len(receipt["model_usage"]))
        record = receipt["model_usage"][0]
        self.assertEqual(
            {
                "provider": "scripted",
                "model": "stub-model",
                "requests": 2,
                "input_tokens": 2100,
                "output_tokens": 340,
                "cached_input_tokens": 10,
                "reasoning_tokens": 5,
                "provider_reported_cost": 0.03,
                "currency": "USD",
            },
            record,
        )

    def test_safe_paused_session_maps_to_safe_paused(self) -> None:
        workspace = self.workspace()
        workspace.write_output()
        run = workspace.run(
            status=ApiSessionStatus.SAFE_PAUSED,
            stop_reason="model-turn-budget",
            final_text=None,
        )
        result = closeout(workspace.plan(), run, root=self.root)
        self.assertEqual("safe-paused", result.status)
        attempt_dir = self.root / ATTEMPT_DIR
        for name in (ATTEMPT_FILENAME, RECEIPT_FILENAME, HANDOFF_FILENAME):
            self.assertEqual("safe-paused", load_document(attempt_dir / name)["status"])
        handoff = load_document(attempt_dir / HANDOFF_FILENAME)
        self.assertTrue(handoff["unresolved"])
        self.assertTrue(handoff["recommended_next_actions"])
        # Until M6-006 produces measured Context Snapshots, model-api safe
        # pauses retain a transcript trigger record and surface a warning.
        self.assertNotIn("RECEIPT-SAFE-PAUSE-CONTEXT-MISSING", _block_codes(result.risks))
        self.assertIn(
            "RECEIPT-SAFE-PAUSE-CONTEXT-DEFERRED",
            {risk.code for risk in result.risks},
        )
        first = verify_attempt(attempt_dir, root=self.root)
        self.assertEqual(first, verify_attempt(attempt_dir, root=self.root))

    def test_declared_safe_pause_maps_to_safe_paused(self) -> None:
        workspace = self.workspace()
        workspace.write_output()
        final_text = json.dumps(
            {
                "status": "safe-paused",
                "summary": "Paused before the second source.",
                "limitations": [],
                "unresolved": ["second source not inspected"],
            }
        )
        result = closeout(workspace.plan(), workspace.run(final_text=final_text), root=self.root)
        self.assertEqual("safe-paused", result.status)

    def test_incomplete_session_maps_to_incomplete(self) -> None:
        workspace = self.workspace()
        workspace.write_output()
        run = workspace.run(status=ApiSessionStatus.INCOMPLETE, stop_reason="length")
        result = closeout(workspace.plan(), run, root=self.root)
        self.assertEqual("incomplete", result.status)
        attempt = load_document(self.root / ATTEMPT_DIR / ATTEMPT_FILENAME)
        self.assertEqual("incomplete", attempt["status"])

    def test_failed_session_maps_to_failed(self) -> None:
        workspace = self.workspace()
        run = workspace.run(
            status=ApiSessionStatus.FAILED,
            stop_reason="error",
            final_text=None,
            with_output_event=False,
        )
        result = closeout(workspace.plan(), run, root=self.root)
        self.assertEqual("failed", result.status)
        attempt = load_document(self.root / ATTEMPT_DIR / ATTEMPT_FILENAME)
        self.assertEqual("failed", attempt["status"])
        self.assertIn("reason", attempt["failure"])
        first = verify_attempt(self.root / ATTEMPT_DIR, root=self.root)
        self.assertEqual(first, verify_attempt(self.root / ATTEMPT_DIR, root=self.root))

    def test_stale_inputs_pause_a_completed_session(self) -> None:
        workspace = self.workspace()
        workspace.write_output()
        self.input = _write(self.root, "inputs/paper.txt", "drifted content\n")
        run = workspace.run(stale_inputs=("inputs/paper.txt",))
        result = closeout(workspace.plan(), run, root=self.root)
        self.assertEqual("safe-paused", result.status)
        self.assertIn("TASK-STALE-INPUT", _block_codes(result.risks))
        receipt = load_document(self.root / ATTEMPT_DIR / RECEIPT_FILENAME)
        self.assertTrue(
            any("input lock drifted" in note for note in receipt["limitations"]),
            receipt["limitations"],
        )

    def test_invalid_final_json_degrades_to_incomplete(self) -> None:
        workspace = self.workspace()
        workspace.write_output()
        run = workspace.run(final_text="this is not the closeout JSON")
        result = closeout(workspace.plan(), run, root=self.root)
        self.assertEqual("incomplete", result.status)
        receipt = load_document(self.root / ATTEMPT_DIR / RECEIPT_FILENAME)
        self.assertTrue(
            any("not a valid JSON" in note for note in receipt["limitations"]),
            receipt["limitations"],
        )

    def test_missing_required_output_degrades_to_incomplete(self) -> None:
        workspace = self.workspace()
        run = workspace.run(with_output_event=False)
        result = closeout(workspace.plan(), run, root=self.root)
        self.assertEqual("incomplete", result.status)
        receipt = load_document(self.root / ATTEMPT_DIR / RECEIPT_FILENAME)
        self.assertTrue(
            any("evidence-record" in note for note in receipt["limitations"]),
            receipt["limitations"],
        )

    def test_duplicate_publish_is_rejected(self) -> None:
        workspace = self.workspace()
        workspace.write_output()
        plan = workspace.plan()
        closeout(plan, workspace.run(), root=self.root)
        with self.assertRaises(FileExistsError):
            closeout(plan, workspace.run(), root=self.root)

    def test_replay_rejects_an_attempt_without_the_marker_last_commit(self) -> None:
        workspace = self.workspace()
        workspace.write_output()
        closeout(workspace.plan(), workspace.run(), root=self.root)
        (self.root / ATTEMPT_DIR / COMPLETION_MANIFEST_FILENAME).unlink()
        self.assertIn(
            "EXEC-COMPLETION-MARKER-MISSING",
            _block_codes(verify_attempt(self.root / ATTEMPT_DIR, root=self.root)),
        )

    def test_evidence_without_exact_task_file_binding_cannot_complete(self) -> None:
        workspace = self.workspace()
        workspace.write_output(content=EVIDENCE_RECORD.replace("source_file_ref", "unbound_source"))
        result = closeout(workspace.plan(), workspace.run(), root=self.root)
        self.assertNotEqual("completed", result.status)

    def test_verify_detects_tampered_output(self) -> None:
        workspace = self.workspace(require_manifest=True)
        output_path = workspace.write_output()
        result = closeout(workspace.plan(), workspace.run(), root=self.root)
        self.assertEqual("completed", result.status, [str(risk) for risk in result.risks])
        output_path.write_text(
            EVIDENCE_RECORD.replace("synthetic structural fixture", "tampered statement"),
            encoding="utf-8",
        )
        first = verify_attempt(self.root / ATTEMPT_DIR, root=self.root)
        self.assertIn("REF-HASH-MISMATCH", _block_codes(first))
        self.assertEqual(first, verify_attempt(self.root / ATTEMPT_DIR, root=self.root))

    def test_missing_task_degrades_the_manifest_flow(self) -> None:
        workspace = self.workspace(with_task=False, require_manifest=True)
        workspace.write_output()
        result = closeout(workspace.plan(), workspace.run(), root=self.root)
        self.assertEqual("incomplete", result.status)
        self.assertIn("HANDOFF-AUDIT-REF-MISSING", _block_codes(result.risks))
        attempt_dir = self.root / ATTEMPT_DIR
        self.assertTrue((attempt_dir / MANIFEST_FILENAME).is_file())
        self.assertFalse((attempt_dir / TRANSFER_AUDIT_FILENAME).exists())
        handoff = load_document(attempt_dir / HANDOFF_FILENAME)
        self.assertEqual([], handoff["validation_refs"])
        first = verify_attempt(attempt_dir, root=self.root)
        self.assertIn("HANDOFF-AUDIT-REF-MISSING", _block_codes(first))
        self.assertEqual(first, verify_attempt(attempt_dir, root=self.root))


if __name__ == "__main__":
    unittest.main()
