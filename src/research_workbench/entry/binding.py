"""Explicit application callers for capability freeze and Runtime inputs.

These callers persist existing contracts; they do not resolve a Method, grant
permissions, establish source trust, run a Host, or admit a Skill.  Callers must
supply the complete pinned read set and their trusted evidence verifier.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

from research_workbench.capability.requirements import CapabilityRequirement
from research_workbench.capability.supply import (
    CapabilitySupplyReport, SkillReleaseProjectionReference, SupplyIdentity,
    assess_supply, resolve_status,
)
from research_workbench.execution.execution_view import (
    PinnedExecutionInput, produce_resolved_execution_view,
)
from research_workbench.execution.host import load_resolved_execution_view
from research_workbench.execution.runtime_bundle import ALLOWED_KINDS, load_runtime_bundle
from research_workbench.io import load_document_bytes
from research_workbench.validation.capability_supply_registry import validate_capability_supply_chain
from research_workbench.validation.document_core import LoadedDocuments
from research_workbench.validation.document_kinds import infer_document_kind
from research_workbench.validation.schemas import SchemaCatalog


class EntryBindingError(ValueError):
    """An explicit input or its frozen closure cannot be safely consumed."""


@dataclass(frozen=True, slots=True)
class CapabilityFreezeResult:
    status: str
    resolution: PinnedExecutionInput | None
    snapshot: PinnedExecutionInput | None
    summary_path: str
    assessments: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True, slots=True)
class ExecutionInputsResult:
    bundle: PinnedExecutionInput
    view: PinnedExecutionInput
    summary_path: str


def _relative(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise EntryBindingError("Expected a portable repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise EntryBindingError("Input/output path must not escape or alias the project root")
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise EntryBindingError("Input/output path escapes the project root") from exc
    if resolved == root:
        raise EntryBindingError("Input/output must name a child of the project root")
    return resolved


def _hash(value: str) -> str:
    if not isinstance(value, str):
        raise EntryBindingError("Missing SHA-256 pin")
    normalized = value.removeprefix("sha256:").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise EntryBindingError("Invalid SHA-256 pin")
    return normalized


def _bytes(document: Mapping[str, Any]) -> bytes:
    return (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _schema(catalog: SchemaCatalog, kind: str, document: Any) -> None:
    errors = catalog.validate(kind, document)
    if errors:
        raise EntryBindingError(f"{kind} schema invalid: " + "; ".join(
            f"{error.pointer}: {error.message}" for error in errors
        ))
    if not isinstance(document, Mapping) or infer_document_kind(document) != kind:
        raise EntryBindingError(f"Pinned input does not have declared kind {kind}")


def _load(root: Path, pin: PinnedExecutionInput, kind: str,
          catalog: SchemaCatalog, documents: LoadedDocuments) -> Mapping[str, Any]:
    path = _relative(root, pin.path)
    if path in documents:
        raise EntryBindingError(f"Duplicate input path: {pin.path}")
    if not path.is_file():
        raise EntryBindingError(f"Pinned input is not one file: {pin.path}")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != _hash(pin.sha256):
        raise EntryBindingError(f"Input SHA-256 mismatch: {pin.path}")
    document = load_document_bytes(path, raw)
    _schema(catalog, kind, document)
    documents.add(path, document, sha256=digest)
    return document


def _chain(documents: LoadedDocuments) -> None:
    issues = validate_capability_supply_chain(documents)
    if issues:
        raise EntryBindingError("Capability closure invalid: " + "; ".join(
            f"{issue.code}: {issue.message}" for issue in issues
        ))


def _ref(pin: PinnedExecutionInput, reference: str) -> dict[str, str]:
    return {"ref": reference, "document_path": pin.path, "content_hash": _hash(pin.sha256)}


def _new_directory(root: Path, relative: str) -> Path:
    directory = _relative(root, relative)
    directory.parent.mkdir(parents=True, exist_ok=True)
    # mkdir's exclusive leaf creation is the ownership claim; no existing run is overwritten.
    directory.mkdir()
    return directory


def _write(root: Path, directory: Path, name: str, raw: bytes) -> PinnedExecutionInput:
    path = directory / name
    with path.open("xb") as stream:
        stream.write(raw)
    return PinnedExecutionInput(path.relative_to(root).as_posix(), hashlib.sha256(raw).hexdigest())


def _summary(root: Path, directory: Path, status: str, lines: Sequence[str]) -> str:
    pin = _write(root, directory, "SUMMARY.md", (
        f"# Control freeze: {status}\n\n" + "\n".join(lines) + "\n"
    ).encode("utf-8"))
    return pin.path


def freeze_capability_selection(
    project_root: str | Path, *, task: PinnedExecutionInput, method: PinnedExecutionInput,
    requirement: PinnedExecutionInput, supplies: Sequence[PinnedExecutionInput],
    supporting_documents: Sequence[Mapping[str, str]],
    evidence_check: Callable[[SupplyIdentity, Mapping[str, Any], str], str] | None,
    output_directory: str, resolution_id: str, snapshot_id: str, evaluated_at: str,
    qualification: str = "structural-replay", revision: int = 1,
    projection_eligibility_check: Callable[[SkillReleaseProjectionReference], bool] | None = None,
    schema_root: str | Path | None = None,
) -> CapabilityFreezeResult:
    """Freeze exactly one existing Requirement; never rank or retry candidates.

    supporting_documents uses existing ``kind/path/sha256`` document references.
    A missing trusted verifier or a blocked Method produces a readable blocked
    result without a Resolution/Snapshot.  Invalid pins/closures raise before
    publication.  A trusted verifier must agree with the pinned typed evidence;
    registry validation independently recomputes all comparison rows.
    """
    root = Path(project_root).resolve()
    catalog = SchemaCatalog(schema_root)
    documents = LoadedDocuments()
    task_doc = _load(root, task, "task_packet", catalog, documents)
    method_doc = _load(root, method, "method_resolution", catalog, documents)
    requirement_doc = _load(root, requirement, "capability_requirement", catalog, documents)
    report_docs = [_load(root, pin, "capability_supply_report", catalog, documents) for pin in supplies]
    for reference in supporting_documents:
        if set(reference) != {"kind", "path", "sha256"} or reference["kind"] not in {
            "capability_conformance_evidence", "provider_conformance_report", "skill_release_projection",
        }:
            raise EntryBindingError("Unexpected supporting document reference")
        _load(root, PinnedExecutionInput(reference["path"], reference["sha256"]),
              reference["kind"], catalog, documents)
    reports = [CapabilitySupplyReport.from_mapping(doc) for doc in report_docs]
    if len({report.reference for report in reports}) != len(reports):
        raise EntryBindingError("Candidate Supply identities must be unique")
    expected_task = {"task_id": task_doc["task_id"], "revision": task_doc.get("revision", 1),
                     "sha256": _hash(task.sha256)}
    actual_task = dict(method_doc["task_ref"])
    actual_task["sha256"] = _hash(actual_task["sha256"])
    if actual_task != expected_task:
        raise EntryBindingError("Method Task lineage does not match the pinned Task")
    method_capabilities = {capability for decision in method_doc["action_decisions"]
                           for capability in decision["capability_requirements"]}
    if method_capabilities != set(task_doc.get("required_capabilities", [])):
        raise EntryBindingError("Method capabilities do not preserve the pinned Task demand")
    requirement_id = requirement_doc["requirement_id"]
    if not any(requirement_id in decision["capability_requirements"]
               for decision in method_doc["action_decisions"]):
        raise EntryBindingError("Method does not request the pinned Requirement")
    _chain(documents)
    if qualification not in {"structural-replay", "runtime-execution"}:
        raise EntryBindingError("Unsupported qualification")
    missing_projection_verifier = qualification == "runtime-execution" and any(
        report.supply_identity.supply_kind == "skill"
        and report.supply_identity.skill_release_projection_ref is not None for report in reports
    ) and projection_eligibility_check is None
    if method_doc["resolution_status"] != "proceed" or (reports and evidence_check is None) or missing_projection_verifier:
        reason = ("Pinned Method does not permit proceeding." if method_doc["resolution_status"] != "proceed"
                  else "Trusted Skill projection verifier is missing; Runtime qualification remains blocked."
                  if missing_projection_verifier
                  else "Trusted evidence verifier is missing; source/runtime qualification remains blocked.")
        directory = _new_directory(root, output_directory)
        return CapabilityFreezeResult("blocked", None, None,
            _summary(root, directory, "blocked", [reason, "No Snapshot or execution authority was created."]), ())

    unconfirmed_evidence: list[str] = []

    def verified(identity: SupplyIdentity, evidence: Mapping[str, Any], capability: str) -> str:
        assert evidence_check is not None
        answer = evidence_check(identity, copy.deepcopy(evidence), capability)
        if answer not in {"pass", "fail", "unknown"}:
            raise EntryBindingError("Trusted verifier must return pass, fail, or unknown")
        if answer != "pass":
            unconfirmed_evidence.append(f"{evidence.get('evidence_id', 'unspecified evidence')}: {answer}")
        return answer

    parsed_requirement = CapabilityRequirement.from_mapping(requirement_doc)
    assessed_objects = [assess_supply(parsed_requirement, report, qualification=qualification,
        evaluated_at=evaluated_at, evidence_check=verified,
        projection_eligibility_check=projection_eligibility_check) for report in reports]
    assessments = tuple(assessment.to_mapping() for assessment in assessed_objects)
    if unconfirmed_evidence:
        directory = _new_directory(root, output_directory)
        lines = ["Trusted verification did not pass: " + ", ".join(unconfirmed_evidence),
                 "Failed/unknown verification is preserved; no contract records an unsupported pass or qualification.",
                 "No Resolution or Snapshot was published."]
        for assessment in assessments:
            lines.append(f"- {assessment['supply_report_ref']}: eligible={assessment['eligible']}")
            lines.extend(f"  - {row['check']}: {row['status']} — {row['reason']}" for row in assessment["checks"])
        return CapabilityFreezeResult("blocked", None, None,
            _summary(root, directory, "blocked", lines), assessments)
    # resolve_status consumes assessments, not an application ranking policy.
    status, selected = resolve_status(assessed_objects)
    method_ref = _ref(method, f"{method_doc['resolution_id']}@r{method_doc['revision']}")
    requirement_ref = {"requirement_id": requirement_id, "document_path": requirement.path,
                       "content_hash": _hash(requirement.sha256)}
    limitations = ["Freeze preserves the pinned Method and trusted evidence; it grants no execution authority.",
                  "Structural replay cannot establish real Runtime qualification." if qualification == "structural-replay"
                  else "Runtime qualification comes from supplied non-fixture evidence; final Runtime admission remains external."]
    resolution = {"schema_version": "0.1.0", "resolution_id": resolution_id, "revision": revision,
        "qualification": qualification, "evaluated_at": evaluated_at,
        "method_resolution_ref": method_ref, "requirement_ref": requirement_ref,
        "candidate_supply_report_refs": [_ref(pin, report.reference) for pin, report in zip(supplies, reports)],
        "comparisons": list(assessments), "resolution_status": status, "limitations": limitations,
        "boundaries": {"method_contract": "unchanged", "automatic_fallback": False,
                       "permission_grant": False, "claim_effect": False, "human_decision": False}}
    if selected is not None:
        resolution["selected_supply_report_ref"] = selected
    _schema(catalog, "capability_resolution", resolution)
    directory = _relative(root, output_directory)
    resolution_path = directory / "capability-resolution.json"
    resolution_raw = _bytes(resolution)
    resolution_pin = PinnedExecutionInput(resolution_path.relative_to(root).as_posix(), hashlib.sha256(resolution_raw).hexdigest())
    documents.add(resolution_path, resolution, sha256=resolution_pin.sha256)
    snapshot = None
    snapshot_raw = None
    if selected is not None:
        index = next(i for i, report in enumerate(reports) if report.reference == selected)
        supply_doc = report_docs[index]
        snapshot = {"schema_version": "0.1.0", "snapshot_id": snapshot_id, "revision": revision,
            "qualification": qualification,
            "task_ref": _ref(task, f"{task_doc['task_id']}@r{task_doc.get('revision', 1)}"),
            "resolution_ref": _ref(resolution_pin, f"{resolution_id}@r{revision}"),
            "method_resolution_ref": method_ref, "requirement_ref": requirement_ref,
            "selected_supply_report_ref": _ref(supplies[index], selected),
            "supply_identity": copy.deepcopy(supply_doc["supply_identity"]),
            "supply_required_permissions": copy.deepcopy(supply_doc["required_permissions"]),
            "supply_data_egress": copy.deepcopy(supply_doc["data_egress_behavior"]),
            "supply_side_effects": copy.deepcopy(supply_doc["side_effects"]),
            "conformance_evidence_refs": [copy.deepcopy(item["artifact_ref"]) for item in supply_doc["conformance_evidence"]],
            "limitations": limitations,
            "boundaries": {"execution_input": qualification == "runtime-execution", "method_decision": False,
                "permission_grant": False, "claim_effect": False, "human_decision": False, "fallback_authority": False}}
        _schema(catalog, "resolved_capability_snapshot", snapshot)
        snapshot_raw = _bytes(snapshot)
        documents.add(directory / "capability-snapshot.json", snapshot, sha256=hashlib.sha256(snapshot_raw).hexdigest())
    _chain(documents)
    # Recheck every external pin before exclusive publication (including callbacks that mutate files).
    for path in tuple(documents):
        if path in {resolution_path, directory / "capability-snapshot.json"}:
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != documents.sha256_for(path):
            raise EntryBindingError("Pinned input changed during freeze")
    directory = _new_directory(root, output_directory)
    _write(root, directory, "capability-resolution.json", resolution_raw)
    snapshot_pin = _write(root, directory, "capability-snapshot.json", snapshot_raw) if snapshot_raw else None
    lines = [f"Requirement: {requirement_id}", f"Qualification: {qualification}",
             f"Selected Supply: {selected or 'none'}", ""]
    for assessment in assessments:
        lines.append(f"- {assessment['supply_report_ref']}: eligible={assessment['eligible']}")
        lines.extend(f"  - {row['check']}: {row['status']} — {row['reason']}" for row in assessment["checks"])
    lines.extend(["", *limitations])
    return CapabilityFreezeResult(status, resolution_pin, snapshot_pin,
        _summary(root, directory, status, lines), assessments)


def freeze_execution_inputs(
    project_root: str | Path, *, manifest: Mapping[str, Any],
    agent_profile: PinnedExecutionInput, data_policy: PinnedExecutionInput,
    host_policy: PinnedExecutionInput, execution_binding: PinnedExecutionInput,
    output_directory: str, execution_at: str, view_id: str, revision: int = 1,
    schema_root: str | Path | None = None,
) -> ExecutionInputsResult:
    """Persist and validate an explicit Bundle manifest, then produce its View.

    The complete existing manifest supplies slice/closure/import/consumer pins.
    On a Runtime/View failure the candidate manifest and a blocked summary stay
    visible for diagnosis, but no successful result is returned.  No selection,
    qualification upgrade, permission grant, Host operation or fallback occurs.
    """
    root = Path(project_root).resolve()
    catalog = SchemaCatalog(schema_root)
    candidate = copy.deepcopy(dict(manifest))
    _schema(catalog, "runtime_bundle_manifest", candidate)
    documents = LoadedDocuments()
    for reference in candidate["documents"]:
        if reference["kind"] not in ALLOWED_KINDS:
            raise EntryBindingError("Unexpected Runtime closure document kind")
        _load(root, PinnedExecutionInput(reference["path"], reference["sha256"]), reference["kind"], catalog, documents)
    for pin, kind in ((agent_profile, "agent_profile"), (data_policy, "execution_policy"),
                      (host_policy, "execution_policy"), (execution_binding, "execution_binding")):
        _load(root, pin, kind, catalog, documents)
    _chain(documents)
    directory = _new_directory(root, output_directory)
    bundle_pin = _write(root, directory, "runtime-bundle.json", _bytes(candidate))
    try:
        bundle = load_runtime_bundle(bundle_pin.path, project_root=root, schema_root=schema_root)
        view = produce_resolved_execution_view(bundle, agent_profile=agent_profile,
            data_policy=data_policy, host_policy=host_policy, execution_binding=execution_binding,
            execution_at=execution_at, view_id=view_id, revision=revision,
            expected_bundle_sha256=bundle_pin.sha256, schema_root=schema_root)
        _schema(catalog, "resolved_execution_view", view)
        view_pin = _write(root, directory, "execution-view.json", _bytes(view))
        load_resolved_execution_view(view_pin.path, expected_sha256=view_pin.sha256,
                                    bundle=bundle, schema_root=schema_root)
    except Exception as exc:
        _summary(root, directory, "blocked", ["Runtime inputs did not complete validation.", str(exc),
                 "Candidate files are diagnostic artifacts; no Host execution or fallback occurred."])
        raise EntryBindingError(f"Runtime input freeze blocked; see {output_directory}/SUMMARY.md: {exc}") from exc
    return ExecutionInputsResult(bundle_pin, view_pin, _summary(root, directory, "frozen", [
        f"Bundle: {bundle_pin.path}", f"View: {view_pin.path}",
        f"Selected Supply: {view['selected_supply_report_ref']}",
        "The View preserves the Snapshot's unique selection and intersects the supplied constraints.",
        "This freeze does not run a Host or grant execution authority."]))
