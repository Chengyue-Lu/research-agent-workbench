"""Stage/validate/publish closeout transaction for one attempt.

Every document of a batch is staged and fully validated before anything is
published, then published by exclusive hard link in a fixed order with the
Main State strictly last: the Main State is the only recovery entry point,
so a crash at any earlier point can never expose a state that references
missing files. The completion marker is written only after post-publish
verification passes, so a batch that was never verified is never treated as
complete. Re-running the SAME plan (byte-identical documents, e.g. within
one process) resumes an interrupted publish; a cross-process interruption
produces a batch without a marker, which the runner's pre-flight check
blocks for a manual decision instead of re-executing the model.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.capability.resolver import ResolvedTask
from research_workbench.context import assess_handoff_transfer
from research_workbench.contracts import ContractRisk, RiskLevel
from research_workbench.execution.errors import CloseoutError
from research_workbench.io import load_document
from research_workbench.observability import ExecutionReceipt, check_execution_receipt
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import AttemptRecord, HandoffPacket, TaskPacket
from research_workbench.validation import check_handoff_against_task
from research_workbench.validation.documents import infer_document_kind
from research_workbench.validation.schemas import SchemaCatalog


# Risks that describe the expected post-publish handoff-gate state rather
# than a broken batch: a freshly published audit always carries
# review.status=pending because the bounded semantic review is a human action
# recorded after publishing. Structural risks still block publication.
_POST_PUBLISH_DEFERRED_RISK_CODES = frozenset({"HANDOFF-SEMANTIC-REVIEW-REQUIRED"})

ROLE_KINDS: Mapping[str, str] = {
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

PUBLISH_ORDER = (
    "evidence",
    "check",
    "manifest",
    "audit",
    "task-snapshot",
    "main-snapshot",
    "assignment",
    "handoff",
    "attempt",
    "receipt",
    "main-state",
)


@dataclass(frozen=True, slots=True)
class CloseoutDocument:
    role: str
    path: str
    document: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class CloseoutPlan:
    batch_dir: str
    documents: tuple[CloseoutDocument, ...]
    main_state_path: str

    def __post_init__(self) -> None:
        roles = tuple(document.role for document in self.documents)
        expected = tuple(role for role in PUBLISH_ORDER if role in roles)
        if roles != expected or not roles or roles[-1] != "main-state":
            raise CloseoutError(
                "EXEC-CLOSEOUT-ORDER",
                "documents must follow the publish order and end with the main state",
            )

    def path_for(self, role: str) -> str:
        for document in self.documents:
            if document.role == role:
                return document.path
        raise CloseoutError("EXEC-CLOSEOUT-ORDER", f"plan lacks the {role} document")


@dataclass(frozen=True, slots=True)
class CloseoutResult:
    published: tuple[tuple[str, str, str], ...]
    marker_path: str
    resumed: bool


def serialize_document(document: Mapping[str, Any]) -> bytes:
    return yaml.safe_dump(dict(document), sort_keys=False, allow_unicode=True).encode("utf-8")


def run_closeout(
    plan: CloseoutPlan,
    *,
    root: Path,
    protocol: ProjectProtocol,
    task: TaskPacket,
    assignment: ResolvedTask,
) -> CloseoutResult:
    """Stage, validate, and atomically publish one closeout batch."""

    project_root = Path(root).resolve()
    batch_root = project_root / plan.batch_dir
    staging = batch_root / ".staging"
    marker = batch_root / "closeout-complete.txt"

    marker_state = _marker_state(plan, project_root, marker) if marker.exists() else "absent"
    if marker_state == "complete":
        return CloseoutResult(_published_snapshot(plan, project_root), _relative(project_root, marker), True)

    staged = _stage_all(plan, staging)
    try:
        _validate_staged(plan, staged, task=task, assignment=assignment)
    except CloseoutError:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    published, resumed = _publish_all(plan, project_root, staged)
    try:
        _verify_published(plan, project_root, protocol=protocol, task=task, assignment=assignment)
    except CloseoutError:
        # The batch is published but NOT verified: no completion marker is
        # written, so no later run may treat it as complete.
        shutil.rmtree(staging, ignore_errors=True)
        raise
    _write_marker(marker, published)
    shutil.rmtree(staging, ignore_errors=True)
    return CloseoutResult(tuple(published), _relative(project_root, marker), resumed)


def _stage_all(plan: CloseoutPlan, staging: Path) -> dict[str, Path]:
    staging.mkdir(parents=True, exist_ok=True)
    staged: dict[str, Path] = {}
    for document in plan.documents:
        staged_path = staging / f"{document.role}.yaml"
        _write_flushed(staged_path, serialize_document(document.document))
        staged[document.role] = staged_path
    return staged


def _write_flushed(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _validate_staged(
    plan: CloseoutPlan,
    staged: dict[str, Path],
    *,
    task: TaskPacket,
    assignment: ResolvedTask,
) -> None:
    catalog = SchemaCatalog()
    for document in plan.documents:
        kind = ROLE_KINDS[document.role]
        inferred = infer_document_kind(document.document)
        errors = catalog.validate(kind, document.document)
        if errors:
            first = errors[0]
            raise CloseoutError(
                "EXEC-CLOSEOUT-INVALID",
                f"staged {document.role} document is schema-invalid "
                f"({first.pointer}: {first.message})",
            )
        if inferred != kind:
            raise CloseoutError(
                "EXEC-CLOSEOUT-INVALID",
                f"staged {document.role} document reads as {inferred!r}, expected {kind!r}",
            )
    _validate_cross_references(plan, staged, task=task, assignment=assignment)


def _validate_cross_references(
    plan: CloseoutPlan,
    staged: dict[str, Path],
    *,
    task: TaskPacket,
    assignment: ResolvedTask,
) -> None:
    documents = {document.role: document.document for document in plan.documents}
    hashes = {role: hash_file(path) for role, path in staged.items()}

    def require(condition: bool, message: str) -> None:
        if not condition:
            raise CloseoutError("EXEC-CLOSEOUT-INVALID", message)

    attempt = documents["attempt"]
    handoff = documents["handoff"]
    receipt = documents["receipt"]
    main_state = documents["main-state"]
    manifest = documents["manifest"]
    audit = documents["audit"]

    require(
        attempt["status"] == handoff["status"] == receipt["status"],
        "attempt, handoff, and receipt statuses disagree",
    )
    require(handoff["transfer_manifest_ref"] == plan.path_for("manifest"), "handoff manifest reference drift")
    require(attempt["execution_receipt_ref"] == plan.path_for("receipt"), "attempt receipt backref drift")
    require(receipt["attempt_ref"] == plan.path_for("attempt"), "receipt attempt backref drift")
    require(
        receipt["skill_assignment_ref"] == plan.path_for("assignment")
        and attempt["skill_assignment_ref"] == plan.path_for("assignment"),
        "assignment reference drift",
    )
    expected_inputs = {(ref["path"], ref["sha256"]) for ref in input_lock_entries(task)}
    require(
        expected_inputs == {(ref["path"], ref["sha256"]) for ref in handoff["input_lock"]},
        "handoff input lock differs from the task inputs",
    )
    require(
        expected_inputs == {(ref["path"], ref["sha256"]) for ref in attempt["input_lock"]},
        "attempt input lock differs from the task inputs",
    )
    require(
        {ref["path"] for ref in manifest["source_artifact_refs"]}
        <= set(handoff["artifact_refs"]),
        "manifest sources must be indexed by the handoff artifact refs",
    )
    item_ids = [item["item_id"] for item in manifest["items"]]
    mapping_ids = [mapping["item_id"] for mapping in audit["mappings"]]
    require(len(set(item_ids)) == len(item_ids), "manifest item ids repeat")
    require(sorted(item_ids) == sorted(mapping_ids), "audit mappings do not cover the manifest items")
    require(
        all(mapping["status"] == "carried" for mapping in audit["mappings"]),
        "generated audits must carry every item",
    )
    machine_refs = {ref["path"]: ref["sha256"] for ref in main_state["machine_state_refs"]}
    for role, digest in hashes.items():
        if role == "main-state":
            # The main state is the recovery entry point; its own integrity is
            # proven by checkpoint_digest, not by a self-reference.
            continue
        require(
            machine_refs.get(plan.path_for(role)) == digest,
            f"main state hash for {role} does not match the staged content",
        )
    require(
        main_state["context_snapshot_ref"] == plan.path_for("main-snapshot"),
        "main state must reference the batch main snapshot",
    )
    require(receipt["context_snapshot_ref"] == plan.path_for("task-snapshot"), "receipt task snapshot drift")

    AttemptRecord.from_mapping(attempt)
    HandoffPacket.from_mapping(handoff)
    ExecutionReceipt.from_mapping(receipt)
    require(
        sorted(handoff["skill_lock"])
        == sorted(lock.identifier for lock in assignment.skill_lock),
        "handoff skill lock differs from the assignment",
    )


def input_lock_entries(task: TaskPacket) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for reference in task.input_refs:
        entry: dict[str, Any] = {"path": reference.path, "sha256": reference.sha256}
        if reference.revision is not None:
            entry["revision"] = reference.revision
        entries.append(entry)
    return entries


def _publish_all(
    plan: CloseoutPlan, project_root: Path, staged: dict[str, Path]
) -> tuple[list[tuple[str, str, str]], bool]:
    published: list[tuple[str, str, str]] = []
    resumed = False
    try:
        for document in plan.documents:
            staged_path = staged[document.role]
            target = project_root / document.path
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = hash_file(staged_path)
            if target.exists():
                resumed = True
                if hash_file(target) != digest:
                    raise CloseoutError(
                        "EXEC-CLOSEOUT-PATH-CONFLICT",
                        f"target already exists with different content: {document.path}",
                    )
            else:
                os.link(staged_path, target)
            published.append((document.role, document.path, digest))
    except OSError as exc:
        raise CloseoutError(
            "EXEC-CLOSEOUT-INCOMPLETE",
            "publish interrupted before the main state; recover by re-running the same plan "
            f"({len(published)}/{len(plan.documents)} published): {exc}",
        ) from exc
    return published, resumed


def _write_marker(marker: Path, published: list[tuple[str, str, str]]) -> None:
    lines = [f"published={len(published)}"]
    lines.extend(f"{role} {relative} {digest}" for role, relative, digest in published)
    _write_flushed(marker, ("\n".join(lines) + "\n").encode("utf-8"))


def read_completion_marker(marker: Path) -> tuple[tuple[str, str, str], ...]:
    """Parse a completion marker into (role, relative path, sha256) entries."""

    entries: list[tuple[str, str, str]] = []
    for line in marker.read_text(encoding="utf-8").splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3:
            entries.append((parts[0], parts[1], parts[2]))
    return tuple(entries)


def _marker_state(plan: CloseoutPlan, project_root: Path, marker: Path) -> str:
    """Classify a marked batch: complete, repairable (files lost), or diverged.

    A missing file is repaired deterministically by re-running the publish
    path; a file whose content differs from the recorded digest is external
    divergence and blocks.
    """

    recorded = {relative: digest for _, relative, digest in read_completion_marker(marker)}
    repairable = False
    for document in plan.documents:
        digest = recorded.get(document.path)
        target = project_root / document.path
        if digest is None:
            raise CloseoutError(
                "EXEC-CLOSEOUT-PATH-CONFLICT",
                f"completion marker does not record {document.path}",
            )
        if not target.exists():
            repairable = True
            continue
        if hash_file(target) != digest:
            raise CloseoutError(
                "EXEC-CLOSEOUT-PATH-CONFLICT",
                f"published batch diverges from the plan at {document.path}",
            )
    return "repairable" if repairable else "complete"


def _published_snapshot(
    plan: CloseoutPlan, project_root: Path
) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (document.role, document.path, hash_file(project_root / document.path))
        for document in plan.documents
    )


def _verify_published(
    plan: CloseoutPlan,
    project_root: Path,
    *,
    protocol: ProjectProtocol,
    task: TaskPacket,
    assignment: ResolvedTask,
) -> None:
    by_role = {document.role: project_root / document.path for document in plan.documents}
    receipt = ExecutionReceipt.from_mapping(load_document(by_role["receipt"]))
    handoff = HandoffPacket.from_mapping(load_document(by_role["handoff"]))
    assessment = assess_handoff_transfer(
        load_document(by_role["audit"]), root=project_root
    )
    risk_groups = (
        check_execution_receipt(
            receipt, protocol, root=project_root, receipt_ref=plan.path_for("receipt")
        ),
        check_handoff_against_task(task, handoff, project_root=project_root, assignment=assignment),
        assessment.risks,
    )
    blockers = [
        f"{risk.code}: {risk.message}"
        for risks in risk_groups
        for risk in risks
        # A freshly published audit always carries review.status=pending: the
        # semantic review is a bounded human action recorded after publishing,
        # so "review still pending" describes the expected handoff-gate state
        # rather than a broken batch. Structural risks still block here.
        if risk.level == RiskLevel.BLOCK
        and risk.code not in _POST_PUBLISH_DEFERRED_RISK_CODES
    ]
    if blockers:
        raise CloseoutError(
            "EXEC-CLOSEOUT-VERIFICATION-FAILED",
            "post-publish verification failed: " + "; ".join(blockers),
        )


def _relative(project_root: Path, path: Path) -> str:
    return path.relative_to(project_root).as_posix()
