"""Compact typed Handoff production and exact actual-observation consumption.

File integrity is structural evidence, never Task/scientific/Human acceptance.
H2 policies fail closed here; this compact adapter does not manufacture audits.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Mapping

from research_workbench.artifacts.integrity import resolve_within_root
from research_workbench.contracts.common import to_plain
from research_workbench.contracts.risks import RiskLevel
from research_workbench.entry.roles import document_bytes, read_pinned_inputs
from research_workbench.io import load_document_bytes
from research_workbench.tasks.models import FileReference, HandoffPacket, TaskPacket
from research_workbench.validation.relationships import check_handoff_against_task
from research_workbench.validation.schemas import SchemaCatalog


class EntryHandoffError(ValueError):
    """Formal transfer cannot consume its declared actual facts."""


def _read(root, ref):
    reference = ref if isinstance(ref, FileReference) else FileReference.from_mapping(to_plain(ref))
    item = read_pinned_inputs(root, (reference,))[0]
    return load_document_bytes(Path(reference.path), item["text"].encode("utf-8"))


def _ref(value):
    return {key: item for key, item in to_plain(value).items() if item is not None}


def _normalize(observation):
    value = json.loads(document_bytes(observation))
    required = {"status", "summary", "limitations", "conflicts", "unresolved",
                "human_decision_required", "next_actions", "artifact_refs", "receipt_refs", "usage"}
    if not isinstance(value, dict) or not required <= value.keys() or value["status"] == "completed":
        raise EntryHandoffError("HANDOFF-OBSERVATION-CONTRACT")
    # Supplied actual pin sets are retained and checked before publication.
    return value


def _packet(task, attempt_id, observation, source_path):
    paths = list(dict.fromkeys([ref["path"] for ref in
                               [*observation["artifact_refs"], *observation["receipt_refs"]]]))
    missing = observation.get("output_contract_status", {}).get("unverified", [])
    partial = bool(missing) and observation["status"] == "stage-completed"
    return {"schema_version": "0.1.0", "task_id": task["task_id"], "attempt_id": attempt_id,
        "status": "safe-paused" if partial else observation["status"], "input_lock": to_plain(task.get("input_refs", [])),
        "skill_lock": [], "result": {"summary": observation["summary"],
            "facts": list(observation.get("facts", [])) + ["Actual usage: " + json.dumps(observation["usage"], sort_keys=True)],
            "inferences": list(observation.get("inferences", [])),
            "recommendations": list(observation.get("recommendations", []))},
        "artifact_refs": paths + [source_path],
        "validation_refs": [ref["path"] for ref in observation.get("validation_refs", [])],
        "limitations": list(dict.fromkeys([*observation["limitations"], "Structural Handoff; Task, Claim and Human acceptance are not granted."])),
        "conflicts": observation["conflicts"], "unresolved": list(dict.fromkeys([*observation["unresolved"],
            *(["Required output contracts not verified: " + ", ".join(missing)] if missing else [])])),
        "human_decision_required": observation["human_decision_required"],
        "recommended_next_actions": list(dict.fromkeys([*observation["next_actions"],
            *(["Verify the missing declared output contracts before Task completion."] if missing else [])]))}


def _check_task(task, catalog):
    if catalog.validate("task_packet", task):
        raise EntryHandoffError("HANDOFF-TASK-SCHEMA")
    packet = TaskPacket.from_mapping(task)
    if packet.required_skills:
        raise EntryHandoffError("HANDOFF-SKILL-LOADING-UNSUPPORTED")
    if packet.handoff_policy.require_transfer_manifest or packet.handoff_policy.semantic_review == "required":
        raise EntryHandoffError("HANDOFF-TRANSFER-AUDIT-REQUIRED: compact adapter has no actual Manifest/Audit")
    return packet


def _check_pins(root, observation):
    refs = {}
    for ref in [*observation["artifact_refs"], *observation["receipt_refs"], *observation.get("validation_refs", [])]:
        actual = FileReference.from_mapping(ref)
        if actual.path in refs and refs[actual.path] != to_plain(actual):
            raise EntryHandoffError("HANDOFF-ARTIFACT-PIN-CONFLICT")
        refs[actual.path] = to_plain(actual)
    # Output artifacts need not be UTF-8 input snapshots. Check their exact
    # bytes without imposing the input reader's text/size contract.
    for ref in refs.values():
        path = resolve_within_root(root, ref["path"])
        if path is None or not path.is_file():
            raise EntryHandoffError("HANDOFF-ARTIFACT-MISSING")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != ref["sha256"].removeprefix("sha256:"):
            raise EntryHandoffError("HANDOFF-ARTIFACT-HASH-DRIFT")
        if ref.get("revision") is not None:
            doc = load_document_bytes(path, raw)
            if not isinstance(doc, Mapping) or doc.get("revision") != ref["revision"]:
                raise EntryHandoffError("HANDOFF-ARTIFACT-REVISION-DRIFT")
    return list(refs.values())


def _receipt_evidence(root, task, observation):
    from research_workbench.execution import load_runtime_bundle, validate_generic_execution_receipt
    observed = dict(observation)
    counts = {}
    receipt_paths = set()
    artifacts = set()
    artifact_hashes = {}
    for ref in observed["receipt_refs"]:
        path = resolve_within_root(root, ref["path"])
        if path in receipt_paths:
            raise EntryHandoffError("HANDOFF-DUPLICATE-RECEIPT")
        receipt_paths.add(path)
        receipt = _read(root, ref)
        view = _read(root, receipt["view_ref"])
        bundle_ref = view["runtime_bundle_ref"]
        bundle = load_runtime_bundle(bundle_ref["path"], project_root=root)
        if bundle.manifest_sha256 != bundle_ref["sha256"].removeprefix("sha256:"):
            raise EntryHandoffError("HANDOFF-RECEIPT-BUNDLE-DRIFT")
        validated = validate_generic_execution_receipt(ref["path"], expected_sha256=ref["sha256"], bundle=bundle)
        actual_task = _read(root, validated.document["task_ref"])
        if actual_task["task_id"] == task["task_id"]:
            if document_bytes(actual_task) != document_bytes(task):
                raise EntryHandoffError("HANDOFF-RECEIPT-TASK-DRIFT")
            if validated.document["status"] == "completed":
                for artifact in validated.document["artifact_refs"]:
                    if isinstance(artifact.get("contract"), str):
                        contract = artifact["contract"]
                        artifact_path = resolve_within_root(root, artifact["path"])
                        digest = artifact["sha256"].removeprefix("sha256:")
                        if artifact_path in artifact_hashes and artifact_hashes[artifact_path] != digest:
                            raise EntryHandoffError("HANDOFF-ARTIFACT-PIN-CONFLICT")
                        artifact_hashes[artifact_path] = digest
                        identity = (artifact_path, digest, contract)
                        if identity not in artifacts:
                            artifacts.add(identity)
                            counts[contract] = counts.get(contract, 0) + 1
    missing = []
    satisfied = []
    for output in task["required_outputs"]:
        contract = output if isinstance(output, str) else output.get("contract")
        minimum = 1 if isinstance(output, str) else output.get("min_count", 1)
        if counts.get(contract, 0) < minimum:
            missing.append(str(contract))
        else:
            satisfied.append(contract)
    observed["output_contract_status"] = {"satisfied": sorted(satisfied), "unverified": missing,
        "observed_counts": counts,
        "scope": "validated-Receipt-artifact-contracts", "task_completion": False}
    return observed


def publish_compact_handoff(root, *, task, attempt_id, directory, observation, catalog=None):
    project = Path(root).resolve()
    catalog = catalog or SchemaCatalog()
    task = json.loads(document_bytes(task))
    packet = _check_task(task, catalog)
    observed = _receipt_evidence(project, task, _normalize(observation))
    if not isinstance(attempt_id, str) or not attempt_id.strip():
        raise EntryHandoffError("HANDOFF-ATTEMPT-MISSING")
    read_pinned_inputs(project, task.get("input_refs", []))
    _check_pins(project, observed)
    if (not isinstance(directory, str) or not directory or "\\" in directory
            or PurePosixPath(directory).is_absolute() or PureWindowsPath(directory).drive
            or any(part in {"", ".", ".."} for part in directory.split("/"))):
        raise EntryHandoffError("HANDOFF-WRITE-SCOPE")
    destination = resolve_within_root(project, directory)
    relative = destination.relative_to(project).as_posix() if destination is not None else ""
    def within(value, scope):
        anchor = scope.removesuffix("/**").rstrip("/")
        return value == anchor or value.startswith(anchor + "/")
    if (destination is None or destination == project or packet.permissions.filesystem != "worktree-write"
            or not any(within(relative, scope) for scope in packet.write_scope)
            or not any(within(relative, scope) for scope in packet.permissions.allowed_roots)):
        raise EntryHandoffError("HANDOFF-WRITE-SCOPE")
    destination.mkdir(parents=True, exist_ok=False)
    def write(name, document):
        raw = document_bytes(document)
        path = destination / name
        with path.open("xb") as stream:
            stream.write(raw)
        return FileReference(path.relative_to(project).as_posix(), hashlib.sha256(raw).hexdigest())
    task_ref = write("task.json", task)
    source_path = (destination / "source.json").relative_to(project).as_posix()
    handoff = _packet(task, attempt_id, observed, source_path)
    source_ref = write("source.json", {"format_version": "0.1.0", "task_ref": to_plain(task_ref),
        "attempt_id": attempt_id, "observation": observed, "handoff": handoff,
        "qualification": "structural-compact-handoff", "task_completion": False, "human_acceptance": False})
    handoff["producer_ref"] = _ref(source_ref)
    if catalog.validate("handoff_packet", handoff):
        raise EntryHandoffError("HANDOFF-SCHEMA")
    reference = write("handoff.json", handoff)
    consume_compact_handoff(project, reference, expected_task=task, expected_attempt_id=attempt_id,
                            expected_observation=observed, catalog=catalog)
    return reference


def consume_compact_handoff(root, handoff_ref, *, expected_task, expected_attempt_id,
                            expected_observation, catalog=None):
    project = Path(root).resolve()
    catalog = catalog or SchemaCatalog()
    task = json.loads(document_bytes(expected_task))
    packet = _check_task(task, catalog)
    observed = _receipt_evidence(project, task, _normalize(expected_observation))
    handoff = _read(project, handoff_ref)
    if not isinstance(handoff, Mapping) or catalog.validate("handoff_packet", handoff):
        raise EntryHandoffError("HANDOFF-SCHEMA")
    if "producer_ref" not in handoff:
        raise EntryHandoffError("HANDOFF-PRODUCER-PIN-MISSING")
    source = _read(project, handoff["producer_ref"])
    if (not isinstance(source, Mapping) or source.get("task_completion") is not False or source.get("human_acceptance") is not False
            or source.get("qualification") != "structural-compact-handoff"):
        raise EntryHandoffError("HANDOFF-AUTHORITY-MISMATCH")
    actual_task = _read(project, source["task_ref"])
    if document_bytes(actual_task) != document_bytes(task) or source["attempt_id"] != expected_attempt_id:
        raise EntryHandoffError("HANDOFF-TASK-ATTEMPT-MISMATCH")
    if document_bytes(source["observation"]) != document_bytes(observed):
        raise EntryHandoffError("HANDOFF-ACTUAL-OBSERVATION-MISMATCH")
    expected = _packet(task, expected_attempt_id, observed, handoff["producer_ref"]["path"])
    body = {key: value for key, value in handoff.items() if key != "producer_ref"}
    if document_bytes(body) != document_bytes(expected) or document_bytes(source["handoff"]) != document_bytes(expected):
        raise EntryHandoffError("HANDOFF-CONTENT-MISMATCH")
    if any(to_plain(left) != to_plain(right) for left, right in
           zip(HandoffPacket.from_mapping(handoff).input_lock, packet.input_refs)) or len(handoff["input_lock"]) != len(packet.input_refs):
        raise EntryHandoffError("HANDOFF-EXACT-INPUT-LOCK-MISMATCH")
    risks = check_handoff_against_task(packet, HandoffPacket.from_mapping(handoff), project_root=project)
    blocks = [risk.code for risk in risks if risk.level == RiskLevel.BLOCK]
    if blocks:
        raise EntryHandoffError("; ".join(blocks))
    pins = _check_pins(project, observed)
    return {"document": dict(handoff), "producer_ref": dict(handoff["producer_ref"]),
            "task_ref": dict(source["task_ref"]), "artifact_pins": pins,
            "qualification": "structural-only", "task_completion": False, "human_acceptance": False}


def receipt_validation_refs(root, receipt_refs):
    return [ref for receipt in receipt_refs for ref in _read(root, receipt).get("validation_refs", [])]


def workflow_handoff_observation(report, root=None):
    sections = report.get("handoff_sections", {})
    child_documents = []
    if root is not None:
        for item in report.get("handoff_consumptions", []):
            child_documents.append(consume_compact_handoff(root, item["handoff_ref"],
                expected_task=item["task"], expected_attempt_id=item["attempt_id"],
                expected_observation=item["observation"])["document"])
    unresolved = list(sections.get("unresolved", []))
    if report["status"] == "safe-paused":
        unresolved += [report["summary"]] + list(report["unstarted_tasks"])
    if report["held_tokens"]:
        unresolved.append("Actual usage is unknown; retained reservation=" + str(report["held_tokens"]))
    unresolved += [item for child in child_documents for item in child["unresolved"]]
    conflicts = list(sections.get("conflicts", []))
    for conflict in [item for child in child_documents for item in child["conflicts"]]:
        if conflict not in conflicts:
            conflicts.append(conflict)
    human = list(dict.fromkeys([*sections.get("human_decision_required", []),
        *[item for child in child_documents for item in child["human_decision_required"]]]))
    status = report["status"]
    if status == "stage-completed" and any(child["status"] == "safe-paused" for child in child_documents):
        status = "safe-paused"
    receipts = [ref for observation in report["observations"] for ref in observation.get("receipt_refs", [])]
    return {"status": status, "summary": report["summary"],
        "limitations": list(dict.fromkeys([*report["limitations"],
            *[item for child in child_documents for item in child["limitations"]]])), "conflicts": conflicts,
        "unresolved": list(dict.fromkeys(unresolved)),
        "human_decision_required": human
            or (list(report["next_actions"]) if report["status"] == "waiting" else []),
        "next_actions": list(report["next_actions"]),
        "artifact_refs": [ref for observation in report["observations"] for ref in observation["artifact_refs"]]
            + [item["handoff_ref"] for item in report.get("handoff_consumptions", [])],
        "receipt_refs": receipts, "validation_refs": receipt_validation_refs(root, receipts) if root is not None else [],
        "usage": {key: report[key] for key in ("model_calls", "known_tokens", "held_tokens")}}


def publish_workflow_handoff(root, *, result, directory=None, attempt_id=None, catalog=None):
    from dataclasses import asdict
    report = _read(root, result.report_ref)
    supplied = asdict(result)
    supplied.pop("report_ref")
    if document_bytes(supplied) != document_bytes({key: report[key] for key in supplied}):
        raise EntryHandoffError("HANDOFF-WORKFLOW-RESULT-MISMATCH")
    if report.get("task_completion") is not False or report.get("human_acceptance") is not False:
        raise EntryHandoffError("HANDOFF-WORKFLOW-AUTHORITY")
    observation = workflow_handoff_observation(report, root)
    observation["artifact_refs"].append(dict(result.report_ref))
    return publish_compact_handoff(root, task=report["task"],
        attempt_id=attempt_id or report.get("attempt_id", "WORKFLOW-" + report["task_id"]),
        directory=directory or (Path(result.report_ref["path"]).parent / "handoff").as_posix(),
        observation=observation, catalog=catalog)


__all__ = ["EntryHandoffError", "publish_compact_handoff", "consume_compact_handoff",
           "publish_workflow_handoff", "workflow_handoff_observation"]
