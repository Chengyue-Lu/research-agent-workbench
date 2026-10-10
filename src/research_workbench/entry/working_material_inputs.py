"""Candidate v0.3.0 typed material/result projection, with no I/O or authority.

Callers validate the control Task, authorize reads and validate source-admission
semantics before passing captured material snapshots. This projection checks
typed data and exact captured pins; it does not establish research qualification.
The frozen v0.2.0 projection continues to own the unchanged common work fields.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from research_workbench.entry.working_inputs import (
    WorkingInputError, _items, _object, _ref, _ref_key, _text,
    project_working_input,
)

WORKING_INPUT_VERSION = "0.3.0"
RESULT_KINDS = frozenset({"formal-handoff", "result-artifact"})
_BASE_FIELDS = {
    "schema_version", "admission_id", "admission_ref", "raw_ref", "acquisition",
    "parser", "license_or_data_use", "sensitivity", "egress_restriction",
    "verification_scope", "scientific_qualification", "permission_grant",
}


def _normalized(path: str) -> str:
    return "/".join(part for part in path.replace("\\", "/").split("/") if part not in ("", "."))


def _zone(path: str, zone: str) -> bool:
    return f"/{zone}/" in f"/{_normalized(path).casefold()}/"


def _captured_ref(value: Any, captured: Mapping[tuple, dict]) -> dict:
    reference = _ref(value)
    if _ref_key(reference) not in captured:
        raise WorkingInputError("provenance ref lacks an authorized captured material")
    return reference


def _provenance(value: Any, own: Mapping, captured: Mapping[tuple, dict]) -> dict:
    if not isinstance(value, Mapping):
        raise WorkingInputError("typed material provenance is required")
    kind = value.get("kind")
    if kind == "ordinary-input":
        fields = {"kind", "source_relation", "scientific_qualification", "gap"}
        record = _object(value, fields, fields)
        if (record["source_relation"] != "not-declared"
                or record["scientific_qualification"] != "not-established"
                or _zone(own["path"], "sources/raw")
                or _normalized(own["path"]).casefold().endswith(".admission.yaml")):
            raise WorkingInputError("ordinary material cannot claim an admitted source relation")
        return {"kind": kind, "source_relation": "not-declared",
                "scientific_qualification": "not-established", "gap": _text(record["gap"])}
    if kind not in ("raw-source", "source-admission", "source-derivative"):
        raise WorkingInputError("unsupported material provenance kind")
    fields = {"kind", *_BASE_FIELDS}
    if kind == "source-derivative":
        fields |= {"derivative_ref", "relation"}
    record = _object(value, fields, fields)
    if (record["schema_version"] != "0.1.0"
            or record["verification_scope"] != "selected-input-bytes-and-declared-source-relation"
            or record["scientific_qualification"] != "not-established"
            or record["permission_grant"] is not False):
        raise WorkingInputError("provenance cannot grant permission or scientific qualification")
    raw = _captured_ref(record["raw_ref"], captured)
    admission = _captured_ref(record["admission_ref"], captured)
    raw_path, admission_path = _normalized(raw["path"]), _normalized(admission["path"])
    if (not _zone(raw_path, "sources/raw") or _zone(raw_path, "sources/inbox")
            or admission_path != raw_path + ".admission.yaml"):
        raise WorkingInputError("raw and admission sidecar paths do not bind")
    expected = raw if kind == "raw-source" else admission
    if kind == "source-derivative":
        expected = _captured_ref(record["derivative_ref"], captured)
        if _ref_key(expected) in {_ref_key(raw), _ref_key(admission)}:
            raise WorkingInputError("derivative must be distinct from raw and sidecar")
    if _ref_key(expected) != _ref_key(own):
        raise WorkingInputError("material own pin differs from its provenance role")
    acquisition_fields = {"origin", "acquired_at", "operator"}
    acquisition = _object(record["acquisition"], acquisition_fields, acquisition_fields)
    origin = _object(acquisition["origin"], {"uri", "doi", "device"}, set())
    if not origin:
        raise WorkingInputError("acquisition origin must be explicit")
    acquired_at = _text(acquisition["acquired_at"])
    try:
        timestamp = datetime.fromisoformat(acquired_at.replace("Z", "+00:00"))
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("missing timezone")
    except ValueError:
        raise WorkingInputError("acquisition timestamp needs an explicit timezone") from None
    parser = _object(record["parser"], {"name", "version"}, {"name", "version"})
    result = {
        "kind": kind, "schema_version": "0.1.0", "admission_id": _text(record["admission_id"]),
        "admission_ref": admission, "raw_ref": raw,
        "acquisition": {"origin": {key: _text(origin[key]) for key in ("uri", "doi", "device") if key in origin},
                        "acquired_at": acquired_at, "operator": _text(acquisition["operator"])},
        "parser": {"name": _text(parser["name"]), "version": _text(parser["version"])},
        "license_or_data_use": _text(record["license_or_data_use"]),
        "sensitivity": _text(record["sensitivity"]), "egress_restriction": _text(record["egress_restriction"]),
        "verification_scope": "selected-input-bytes-and-declared-source-relation",
        "scientific_qualification": "not-established", "permission_grant": False,
    }
    if kind == "source-derivative":
        result.update(derivative_ref=expected, relation=_text(record["relation"]))
    return result


def project_working_material_input(
    task: Mapping[str, Any], *, role: str, responsibilities: Sequence[str],
    materials: Sequence[Mapping[str, Any]], stop_conditions: Sequence[Mapping[str, Any]],
    results: Sequence[Mapping[str, Any]] = (),
    necessary_decisions: Sequence[Mapping[str, Any]] = (),
    counterevidence: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Project already-authorized captures into typed v0.3.0 work slots.

    A result ref must already be in this Task.input_refs and cannot also occupy
    the material slot. Captured text is checked against its UTF-8 hash, including
    CRLF. Result tags establish neither formal contract validity nor completion.
    Callers retain source-admission parsing, permissions, egress and final read
    freshness checks; this function never opens a referenced file.
    """
    plain, provenance = [], []
    for value in _items(materials):
        fields = {"path", "sha256", "revision", "text", "material_provenance"}
        record = _object(value, fields, fields - {"revision"})
        reference = _ref({key: record[key] for key in ("path", "sha256", "revision") if key in record})
        if _zone(reference["path"], "sources/inbox"):
            raise WorkingInputError("unadmitted inbox cannot occupy a work material slot")
        plain.append({**reference, "text": record["text"]})
        provenance.append(record["material_provenance"])
    result_inputs = []
    for value in _items(results):
        fields = {"kind", "source_ref", "text"}
        record = _object(value, fields, fields)
        if not isinstance(record["kind"], str) or record["kind"] not in RESULT_KINDS:
            raise WorkingInputError("unsupported typed result kind")
        reference = _ref(record["source_ref"])
        if _zone(reference["path"], "sources/inbox"):
            raise WorkingInputError("unadmitted inbox cannot occupy a result slot")
        result_inputs.append({"kind": record["kind"], "source_ref": reference, "text": record["text"]})
    all_snapshots = plain + [{**record["source_ref"], "text": record["text"]} for record in result_inputs]
    projection = project_working_input(task, role=role, responsibilities=responsibilities,
        materials=all_snapshots, stop_conditions=stop_conditions,
        necessary_decisions=necessary_decisions, counterevidence=counterevidence)
    captures = projection["materials"][:len(plain)]
    captured = {_ref_key(record): record for record in captures}
    # Path aliases must not split a single capture into multiple slots.
    paths = [_normalized(record["path"]).casefold() for record in projection["materials"]]
    if len(set(paths)) != len(paths):
        raise WorkingInputError("material/result capture paths must be distinct")
    typed = [{**record, "material_provenance": _provenance(value, record, captured)}
             for record, value in zip(captures, provenance)]
    typed_by_pin = {_ref_key(record): record["material_provenance"] for record in typed}
    for record in typed:
        evidence = record["material_provenance"]
        if evidence["kind"] == "ordinary-input":
            continue
        for key, kind in (("raw_ref", "raw-source"), ("admission_ref", "source-admission")):
            sibling = typed_by_pin[_ref_key(evidence[key])]
            if (sibling["kind"] != kind
                    or any(sibling.get(field) != evidence[field] for field in _BASE_FIELDS)):
                raise WorkingInputError("captured source provenance closure is inconsistent")
    projection["schema_version"] = WORKING_INPUT_VERSION
    projection["materials"] = typed
    projection["results"] = [{**record,
        "verification_scope": "captured-utf8-bytes-and-task-pin",
        "scientific_qualification": "not-established", "contract_validation": "not-established",
        "task_completion": False} for record in result_inputs]
    return projection


__all__ = ["WORKING_INPUT_VERSION", "RESULT_KINDS", "WorkingInputError", "project_working_material_input"]
