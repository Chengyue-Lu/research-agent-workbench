"""Single-writer manual checkpoint submission using the existing MainState contract."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from research_workbench.artifacts.integrity import resolve_within_root
from research_workbench.context.models import MainStatePacket, checkpoint_digest
from research_workbench.entry.workflow import WorkflowResult, _scope_within
from research_workbench.io import load_document_bytes
from research_workbench.protocol.models import ProjectProtocol
from research_workbench.tasks import FileReference
from research_workbench.validation.schemas import SchemaCatalog


def _read(root, ref, *, parse=True):
    item = ref if isinstance(ref, FileReference) else FileReference.from_mapping(ref)
    path = resolve_within_root(root, item.path)
    if path is None or not path.is_file():
        raise ValueError("checkpoint input is missing or outside project")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != item.sha256.removeprefix("sha256:"):
        raise ValueError("checkpoint input hash drift")
    return item, load_document_bytes(path, data) if parse else data


def publish_workflow_checkpoint(root, *, result: WorkflowResult, protocol_ref, checkpoint_id,
                                output, write_scope, previous_state_ref=None, created_at=None, catalog=None):
    """Persist an immutable checkpoint, never resume an Agent or accept a Claim.

    Caller owns the single state submission responsibility and output authority.
    No current-head CAS, daemon, automatic next-action dispatch or Topic5 recovery
    is provided. Prior human decisions are preserved verbatim, never generated.
    """
    project = Path(root).resolve()
    catalog = catalog or SchemaCatalog()
    protocol_pin, protocol_doc = _read(project, protocol_ref)
    if catalog.validate("project_protocol", protocol_doc):
        raise ValueError("checkpoint Protocol schema invalid")
    protocol = ProjectProtocol.from_mapping(protocol_doc)
    report_pin, report = _read(project, result.report_ref)
    retained_ref = {"path": report_pin.path, "sha256": report_pin.sha256}
    supplied = asdict(result)
    supplied.pop("report_ref")  # The report is already pinned by its exact bytes.
    if not isinstance(report, dict) or not supplied.keys() <= report.keys():
        raise ValueError("checkpoint result does not match retained workflow")
    def canonical(value):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    if canonical(supplied) != canonical({key: report[key] for key in supplied}):
        raise ValueError("checkpoint result does not match retained workflow")
    if report.get("human_acceptance") is not False or report.get("task_completion") is not False:
        raise ValueError("workflow result tried to grant completion or Human authority")
    previous = {}
    previous_pin = None
    if previous_state_ref:
        previous_pin, previous = _read(project, previous_state_ref)
        if catalog.validate("main_state", previous):
            raise ValueError("previous checkpoint Schema invalid")
        MainStatePacket.from_mapping(previous)
    machine = {protocol_pin.path: {"path": protocol_pin.path, "sha256": protocol_pin.sha256},
               report_pin.path: retained_ref}
    for ref in previous.get("machine_state_refs", []):
        _read(project, ref, parse=False)
        machine[ref["path"]] = dict(ref)
    for observation in report["observations"]:
        for ref in observation.get("artifact_refs", []):
            _read(project, ref, parse=False)
            machine[ref["path"]] = dict(ref)
    constraints = list(previous.get("pinned_constraints", []))
    constraint = "claim ceiling: "+", ".join(protocol.claim_ceiling)
    if constraint not in constraints:
        constraints.append(constraint)
    if protocol.data_boundary.get("local_only") and "local data must not be uploaded" not in constraints:
        constraints.append("local data must not be uploaded")
    risks = list(dict.fromkeys([*previous.get("open_risks", []), *report["limitations"]]))
    if report["held_tokens"]:
        risks.append("Actual model usage is unknown; retained token reservation requires review.")
    document = {"schema_version": "0.1.0", "checkpoint_id": checkpoint_id,
                "continuity_status": report["status"], "project_protocol_ref": f"{protocol_pin.path}@{protocol.revision}",
                "current_questions": list(protocol.question_refs), "pinned_constraints": constraints,
                "accepted_decisions": list(previous.get("accepted_decisions", [])),
                "active_tasks": [i for i in previous.get("active_tasks", []) if i["task_id"] != report["task_id"]]
                    +[{"task_id": report["task_id"], "status": report["status"]}],
                "recent_handoffs": list(previous.get("recent_handoffs", []))
                    +[{"ref": report_pin.path, "disposition": report["disposition"]}],
                "open_conflicts": list(previous.get("open_conflicts", [])), "open_risks": risks,
                "next_actions": list(report["next_actions"]) or ["Human review of the retained execution result."],
                "artifact_index_refs": list(dict.fromkeys([*previous.get("artifact_index_refs", []), report_pin.path])),
                "machine_state_refs": [machine[p] for p in sorted(machine)],
                "created_at": created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    if previous_pin:
        document["previous_checkpoint_ref"] = previous_pin.path
    document["checkpoint_digest"] = checkpoint_digest(document)
    if catalog.validate("main_state", document):
        raise ValueError("generated MainState failed Schema validation")
    MainStatePacket.from_mapping(document)
    destination = resolve_within_root(project, str(output))
    if destination is None:
        raise ValueError("checkpoint destination escaped project")
    relative = destination.relative_to(project).as_posix()
    if not any(_scope_within(relative, scope) for scope in write_scope):
        raise ValueError("checkpoint exceeds the caller's explicit state write scope")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)+"\n").encode("utf-8")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".checkpoint-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # Recheck consumed pins at publication; this does not promise cross-file CAS.
        _read(project, protocol_pin)
        _read(project, report_pin)
        if previous_pin:
            _read(project, previous_pin)
        for ref in machine.values():
            _read(project, ref, parse=False)
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return FileReference(destination.relative_to(project).as_posix(), hashlib.sha256(payload).hexdigest())


__all__ = ["publish_workflow_checkpoint"]
