"""Application stage records; source consistency never grants research acceptance."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from research_workbench.artifacts.integrity import resolve_within_root
from research_workbench.context.models import MainStatePacket
from research_workbench.entry.handoff import (
    _packet, consume_compact_handoff, workflow_handoff_observation,
)
from research_workbench.entry.workflow import _parse_control, _scope_within
from research_workbench.io import load_document_bytes
from research_workbench.tasks import FileReference
from research_workbench.validation.schemas import SchemaCatalog


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def _pin(value):
    try:
        item = value if isinstance(value, FileReference) else FileReference.from_mapping(value)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("stage source pin is invalid") from exc
    pin = {"path": item.path, "sha256": item.sha256.removeprefix("sha256:")}
    if item.revision is not None:
        pin["revision"] = item.revision
    return pin


def _read(root, ref, *, raw=False):
    pin = _pin(ref)
    path = resolve_within_root(root, pin["path"])
    if path is None or not path.is_file():
        raise ValueError("stage source missing or outside project")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != pin["sha256"]:
        raise ValueError("stage source hash drift")
    document = None
    if not raw or "revision" in pin:
        document = load_document_bytes(path, data)
    if "revision" in pin and (not isinstance(document, dict) or document.get("revision") != pin["revision"]):
        raise ValueError("stage source revision drift")
    return data if raw else document


def _report(root, result):
    report = _read(root, result.report_ref)
    supplied = asdict(result)
    supplied.pop("report_ref")
    if not isinstance(report, dict) or not supplied.keys() <= report.keys() or _canonical(supplied) != _canonical({key: report[key] for key in supplied}):
        raise ValueError("stage result does not match retained workflow")
    _authority(report)
    return report


def _authority(document):
    if document.get("task_completion") is not False or document.get("human_acceptance") is not False:
        raise ValueError("stage source attempted completion or Human authority")


def _records(root, report, report_ref, handoff_ref, *, catalog):
    expected = workflow_handoff_observation(report, root)
    expected["artifact_refs"].append(_pin(report_ref))
    final = consume_compact_handoff(root, handoff_ref, expected_task=report["task"],
        expected_attempt_id=report.get("attempt_id", "WORKFLOW-" + report["task_id"]),
        expected_observation=expected, catalog=catalog)
    children = []
    for item in report.get("handoff_consumptions", []):
        consumed = consume_compact_handoff(root, item["handoff_ref"], expected_task=item["task"],
            expected_attempt_id=item["attempt_id"], expected_observation=item["observation"], catalog=catalog)
        children.append({"handoff_ref": _pin(item["handoff_ref"]),
                         "producer_ref": _pin(consumed["producer_ref"]), "task_ref": _pin(consumed["task_ref"])})
    return {"report_ref": _pin(report_ref), "journal_ref": _pin(report["journal_ref"]) if report.get("journal_ref") else None,
            "final_handoff_ref": _pin(handoff_ref), "final_producer_ref": _pin(final["producer_ref"]),
            "final_task_ref": _pin(final["task_ref"]), "child_sources": children}, final["document"]


def _source_pins(sources):
    if not isinstance(sources, dict) or not {"report_ref", "journal_ref", "final_handoff_ref", "final_producer_ref", "final_task_ref", "child_sources"} <= sources.keys():
        raise ValueError("stage source set is incomplete")
    if not isinstance(sources["child_sources"], list) or any(not isinstance(item, dict) or not {"handoff_ref", "producer_ref", "task_ref"} <= item.keys() for item in sources["child_sources"]):
        raise ValueError("stage child source set is incomplete")
    pins = [sources[key] for key in ("report_ref", "journal_ref", "final_handoff_ref", "final_producer_ref", "final_task_ref") if sources.get(key) is not None]
    for item in sources["child_sources"]:
        pins.extend(item[key] for key in ("handoff_ref", "producer_ref", "task_ref"))
    unique = {}
    for ref in pins:
        pin = _pin(ref)
        if pin["path"] in unique and unique[pin["path"]] != pin:
            raise ValueError("stage source has conflicting pins")
        unique[pin["path"]] = pin
    return list(unique.values())


def _derive(root, report, sources, final):
    _authority(report)
    stages, unknowns = [], []
    if report["held_tokens"]:
        unknowns.append("Actual usage remains unknown; the retained token hold is not closed by this evidence.")
    expected_children = {item["task"]["task_id"]: item for item in report.get("handoff_consumptions", [])}
    if len(expected_children) != len(report.get("handoff_consumptions", [])):
        raise ValueError("stage report has duplicate child Task identities")
    child_sources = {item["handoff_ref"]["path"]: item for item in sources["child_sources"]}
    expected_journal = _pin(report["journal_ref"]) if report.get("journal_ref") else None
    if sources["journal_ref"] != expected_journal:
        raise ValueError("stage journal pin differs from retained workflow")
    if not sources["journal_ref"]:
        unknowns.append("Retained workflow has no pinned journal; role phases and child consumption are unknown.")
    else:
        try:
            events = [json.loads(line) for line in _read(root, sources["journal_ref"], raw=True).decode("utf-8").splitlines()]
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("stage journal is invalid") from exc
        if any(not isinstance(event, dict) or event.get("kind") not in {"workflow-started", "role-started", "role-finished", "role-unknown", "delegation-proposed", "handoff-produced-and-validated", "child-results-consumed", "workflow-stopped", "workflow-finished"} for event in events):
            raise ValueError("stage journal contains malformed caller events")
        ending = {"kind": "workflow-finished", **{key: report[key] for key in ("status", "model_calls", "known_tokens", "held_tokens")}}
        if not events or events[-1] != ending or sum(event.get("kind") == "workflow-finished" for event in events) != 1:
            raise ValueError("stage journal is not closed by exact workflow-finished")
        active, finishes, published = None, [], {}
        for line, event in enumerate(events, 1):
            kind = event.get("kind")
            if kind == "role-started":
                ordinal = event["ordinal"]
                context = event["context"]
                if active is not None or type(ordinal) is not int or ordinal != len(stages) + 1 or not isinstance(context, dict) or context.get("phase") not in {"plan-or-execute", "consume-child-results"} or type(event["depth"]) is not int or event["depth"] < 0 or event["role"] not in {"main", "child"} or (event["role"] == "main") != (event["depth"] == 0):
                    raise ValueError("stage journal has invalid dispatch order or phase")
                inputs = context.get("child_results", [])
                if context["phase"] == "plan-or-execute" and inputs:
                    raise ValueError("planning dispatch invents child consumption")
                if context["phase"] == "consume-child-results" and not inputs:
                    raise ValueError("child consumption dispatch has no child inputs")
                for item in inputs:
                    expected = expected_children.get(item["task_id"])
                    if expected is None or item.get("handoff_ref") != expected["handoff_ref"] or item["task_id"] not in published:
                        raise ValueError("fresh main input lacks prior exact child Handoff")
                    if _canonical(item["handoff"]) != _canonical(_read(root, item["handoff_ref"])):
                        raise ValueError("fresh main input substituted child Handoff")
                active = {"ordinal": ordinal, "role": event["role"], "task_id": event["task_id"],
                    "depth": event["depth"], "phase": context["phase"], "source_records": [line],
                    "dispatch_recorded": True, "execution_status": "unknown", "input_child_task_ids": [item["task_id"] for item in inputs],
                    "input_handoff_refs": [item["handoff_ref"] for item in inputs], "child_results_consumed": False,
                    "negative_items": {"limitations": [], "conflicts": [], "unresolved": [], "human_decision_required": []}}
                stages.append(active)
            elif kind in {"role-finished", "role-unknown"}:
                if active is None or event["ordinal"] != active["ordinal"]:
                    raise ValueError("stage journal has unmatched role result")
                active["source_records"].append(line)
                if kind == "role-unknown":
                    active["unknown_fact"] = {key: value for key, value in event.items() if key != "kind"}
                    unknowns.append("Ordinal " + str(active["ordinal"]) + " has unknown outbound/usage facts.")
                else:
                    observed = {key: value for key, value in event.items() if key != "kind"}
                    if observed["role"] != active["role"] or observed["task_id"] != active["task_id"]:
                        raise ValueError("stage role identity drift")
                    finishes.append(observed)
                    active["execution_status"] = observed["status"]
                    active["execution_facts"] = {key: observed[key] for key in ("model_calls", "tool_calls", "input_tokens", "output_tokens")}
                    active["artifact_refs"] = observed["artifact_refs"]
                    active["receipt_refs"] = observed.get("receipt_refs", [])
                    active["negative_items"]["limitations"] = list(observed["limitations"])
                    try:
                        control = _parse_control(observed["text"])
                    except (ValueError, TypeError):
                        active["control_parse_status"] = "unparseable"
                    else:
                        active["control_parse_status"] = "parseable-only"
                        active["summary"] = control["summary"]
                        for key in active["negative_items"]:
                            active["negative_items"][key].extend(control.get(key, []))
                        if control["decision"] == "human-review" and not control.get("human_decision_required"):
                            active["negative_items"]["human_decision_required"].extend(control["next_actions"])
                active = None
            elif kind == "handoff-produced-and-validated":
                item = expected_children.get(event["task_id"])
                source = child_sources.get(event["handoff_ref"]["path"])
                finished = [stage for stage in stages if stage["task_id"] == event["task_id"] and stage["execution_status"] == "completed"]
                if item is None or source is None or not finished or event["handoff_ref"] != item["handoff_ref"] or event["producer_ref"] != source["producer_ref"] or event["task_id"] in published:
                    raise ValueError("stage journal has unbound or duplicate child Handoff")
                published[event["task_id"]] = event
                finished[-1]["formal_handoff_ref"] = event["handoff_ref"]
                finished[-1]["source_records"].append(line)
            elif kind == "child-results-consumed":
                if not stages or active is not None:
                    raise ValueError("child consumption without returned main")
                stage = stages[-1]
                if stage["phase"] != "consume-child-results" or stage["task_id"] != event["parent"] or stage["execution_status"] != "completed" or stage.get("control_parse_status") != "parseable-only" or stage["input_child_task_ids"] != event["task_ids"] or stage["child_results_consumed"]:
                    raise ValueError("stage journal invented child consumption")
                stage["child_results_consumed"] = True
                stage["source_records"].append(line)
        if active is not None or _canonical(finishes) != _canonical(report["observations"]) or set(published) != set(expected_children):
            raise ValueError("stage journal and actual observations/Handoffs differ")
    final_observation = {key: report[key] for key in ("status", "disposition", "summary", "model_calls", "known_tokens", "held_tokens", "unstarted_tasks")}
    final_observation.update(handoff_status=final["status"], limitations=final["limitations"], conflicts=final["conflicts"],
        unresolved=final["unresolved"], human_decision_required=final["human_decision_required"], next_actions=final["recommended_next_actions"])
    return {"format_version": "1.0.0", "record_kind": "workflow-stage-evidence", "qualification": "caller-record-stage-evidence",
        "attempt_id": report.get("attempt_id", "WORKFLOW-" + report["task_id"]), "task_id": report["task_id"],
        "sources": sources, "stages": stages, "final_observation": final_observation,
        "unknowns": unknowns, "intake_stage": "not-recorded", "task_completion": False, "human_acceptance": False}


def publish_workflow_stage_evidence(root, *, result, handoff_ref, output, write_scope, catalog=None) -> FileReference:
    project = Path(root).resolve()
    catalog = catalog or SchemaCatalog()
    destination = resolve_within_root(project, str(output))
    if destination is None or not any(_scope_within(destination.relative_to(project).as_posix(), scope) for scope in write_scope):
        raise ValueError("stage evidence exceeds explicit write scope")
    report = _report(project, result)
    sources, final = _records(project, report, result.report_ref, handoff_ref, catalog=catalog)
    document = _derive(project, report, sources, final)
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = (_canonical(document) + "\n").encode("utf-8")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".stage-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        for pin in _source_pins(sources):
            _read(project, pin, raw=True)
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return FileReference(destination.relative_to(project).as_posix(), hashlib.sha256(data).hexdigest())


def _light_handoff(root, record, expected_task, expected_attempt, expected_observation, catalog):
    handoff = _read(root, record["handoff_ref"])
    if catalog.validate("handoff_packet", handoff) or handoff.get("producer_ref") != record["producer_ref"]:
        raise ValueError("stage Handoff source identity/schema mismatch")
    source = _read(root, record["producer_ref"])
    _authority(source)
    if source.get("qualification") != "structural-compact-handoff" or _pin(source.get("task_ref")) != _pin(record["task_ref"]) or source["attempt_id"] != expected_attempt or _canonical(_read(root, record["task_ref"])) != _canonical(expected_task):
        raise ValueError("stage Handoff Task/attempt mismatch")
    observed = source["observation"]
    for key, value in expected_observation.items():
        if key != "validation_refs" and _canonical(observed.get(key)) != _canonical(value):
            raise ValueError("stage Handoff source differs from independent workflow facts")
    body = {key: value for key, value in handoff.items() if key != "producer_ref"}
    expected = _packet(expected_task, expected_attempt, observed, record["producer_ref"]["path"])
    if _canonical(body) != _canonical(expected) or _canonical(source["handoff"]) != _canonical(expected):
        raise ValueError("stage Handoff record/content mismatch")
    return handoff


def assess_workflow_stage_evidence(root, *, main_state_ref, evidence_ref, verification_refs=(), catalog=None) -> dict:
    """Read granted caller records only; never recursively replay Receipts/Bundle."""
    project = Path(root).resolve()
    catalog = catalog or SchemaCatalog()
    state = _read(project, main_state_ref)
    if catalog.validate("main_state", state):
        raise ValueError("stage MainState schema invalid")
    MainStatePacket.from_mapping(state)
    machine = {}
    for ref in state["machine_state_refs"]:
        pin = _pin(ref)
        if pin["path"] in machine and machine[pin["path"]] != pin:
            raise ValueError("stage MainState has conflicting pins")
        machine[pin["path"]] = pin
    evidence_pin = _pin(evidence_ref)
    if machine.get(evidence_pin["path"]) != evidence_pin:
        raise ValueError("stage evidence does not match MainState pin")
    evidence = _read(project, evidence_pin)
    _authority(evidence)
    if evidence.get("format_version") != "1.0.0" or evidence.get("record_kind") != "workflow-stage-evidence":
        raise ValueError("unsupported stage evidence format")
    sources = evidence["sources"]
    required = _source_pins(sources)
    if any(machine.get(pin["path"]) != pin for pin in required):
        raise ValueError("stage source does not match MainState pin")
    grants = [_pin(ref) for ref in verification_refs]
    missing = [pin for pin in required if pin not in grants]
    answer = {"status": "not-checked", "qualification": "not-checked", "source_ref": evidence_pin,
        "checked_refs": [_pin(main_state_ref), evidence_pin], "missing_verification_refs": missing,
        "validation_scope": ["caller source records and canonical derived stages only; no Receipt/Bundle replay or semantic/scientific/Human acceptance"],
        "limitations": []}
    if missing:
        answer["limitations"] = ["Stage source read grants are incomplete; source records were not read."]
        return answer
    report = _read(project, sources["report_ref"])
    _authority(report)
    expected_children = report.get("handoff_consumptions", [])
    if len(expected_children) != len(sources["child_sources"]):
        raise ValueError("stage child source set mismatch")
    child_documents = []
    for item, record in zip(expected_children, sources["child_sources"]):
        if record["handoff_ref"] != item["handoff_ref"]:
            raise ValueError("stage child Handoff pin mismatch")
        child_documents.append(_light_handoff(project, record, item["task"], item["attempt_id"], item["observation"], catalog))
    expected = workflow_handoff_observation(report)
    for field in ("limitations", "unresolved", "human_decision_required"):
        expected[field] = list(dict.fromkeys([*expected[field], *[value for child in child_documents for value in child[field]]]))
    for child in child_documents:
        for conflict in child["conflicts"]:
            if conflict not in expected["conflicts"]:
                expected["conflicts"].append(conflict)
    expected["human_decision_required"] = list(dict.fromkeys([
        *report.get("handoff_sections", {}).get("human_decision_required", []),
        *[value for child in child_documents for value in child["human_decision_required"]]]))
    if not expected["human_decision_required"] and report["status"] == "waiting":
        expected["human_decision_required"] = list(report["next_actions"])
    if report["status"] == "stage-completed" and any(child["status"] == "safe-paused" for child in child_documents):
        expected["status"] = "safe-paused"
    expected["artifact_refs"].append(sources["report_ref"])
    final = _light_handoff(project, {"handoff_ref": sources["final_handoff_ref"], "producer_ref": sources["final_producer_ref"],
        "task_ref": sources["final_task_ref"]}, report["task"], report.get("attempt_id", "WORKFLOW-" + report["task_id"]), expected, catalog)
    rebuilt = _derive(project, report, sources, final)
    if _canonical(rebuilt) != _canonical(evidence):
        raise ValueError("stage evidence canonical content drift")
    for pin in required:
        _read(project, pin, raw=True)
    answer.update(status="checked" if sources["journal_ref"] else "unknown",
        qualification="source-checked" if sources["journal_ref"] else "unknown",
        checked_refs=[*answer["checked_refs"], *required], stages=rebuilt["stages"],
        final_observation=rebuilt["final_observation"], limitations=rebuilt["unknowns"])
    return answer


__all__ = ["publish_workflow_stage_evidence", "assess_workflow_stage_evidence"]
