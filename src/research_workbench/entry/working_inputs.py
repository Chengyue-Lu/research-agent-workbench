"""Candidate v0.2.0 model work projection; no I/O or execution authority.

The caller validates the original control Task and admits all input reads first.
This module projects data only. It neither migrates that Task nor changes the
legacy runtime's economic controls. Consumers must opt into this new contract.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

WORKING_INPUT_VERSION = "0.2.0"
SOURCE_TASK_VERSIONS = frozenset({"0.1.0"})
STOP_KINDS = frozenset({
    "completed", "cancelled", "execution-failed", "permission-denied",
    "data-boundary", "input-missing-or-stale", "supply-unavailable", "human-gate",
    "technical-capacity", "transport-timeout",
})


class WorkingInputError(ValueError):
    """A requested projection is malformed; this is not an admission decision."""


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkingInputError("a nonempty text value is required")
    return value  # Preserve task prose, including explicit discussion of costs.


def _items(value: Any) -> Sequence:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise WorkingInputError("an explicit sequence is required")
    return value


def _texts(value: Any) -> list[str]:
    return [_text(item) for item in _items(value)]


def _object(value: Any, keys: set[str], required: set[str]) -> Mapping:
    if not isinstance(value, Mapping) or set(value) - keys or not required <= set(value):
        raise WorkingInputError("record fields are outside the projection contract")
    return value


def _integer(value: Any, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise WorkingInputError("invalid integer in projection")
    return value


def _path(value: Any) -> str:
    value = _text(value)
    normalized = value.replace("\\", "/")
    if (PureWindowsPath(value).drive or PurePosixPath(normalized).is_absolute()
            or ".." in PurePosixPath(normalized).parts or "\x00" in value or ":" in value):
        raise WorkingInputError("a repository-relative path is required")
    return value


def _ref(value: Any) -> dict[str, Any]:
    value = _object(value, {"path", "sha256", "revision"}, {"path", "sha256"})
    digest = value["sha256"]
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise WorkingInputError("a SHA-256 pin is required")
    result = {"path": _path(value["path"]), "sha256": digest}
    if value.get("revision") is not None:
        result["revision"] = _integer(value["revision"], 1)
    return result


def _ref_key(value: Mapping) -> tuple:
    return value["path"], value["sha256"], value.get("revision")


def _records(values: Sequence, permitted: set[tuple]) -> list[dict[str, Any]]:
    result = []
    for value in _items(values):
        record = _object(value, {"statement", "source_ref"}, {"statement", "source_ref"})
        reference = _ref(record["source_ref"])
        if _ref_key(reference) not in permitted:
            raise WorkingInputError("record reference is outside the Task read set")
        result.append({"statement": _text(record["statement"]), "source_ref": reference})
    return result


def project_working_input(
    task: Mapping[str, Any], *, role: str, responsibilities: Sequence[str],
    materials: Sequence[Mapping[str, Any]], stop_conditions: Sequence[Mapping[str, Any]],
    necessary_decisions: Sequence[Mapping[str, Any]] = (),
    counterevidence: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Select explicit work fields from a caller-validated v0.1.0 Task.

    Materials are already-admitted UTF-8 snapshots, never paths to open here.
    Snapshot hashes are rechecked against the same encoded bytes and exact Task
    pins. Stops must be explicitly classified by the caller: legacy free-form
    budget/safe-pause strings are not guessed or filtered by keyword. Missing
    control validation, actual gates and new-version dispatch remain caller work.
    """
    if (not isinstance(task, Mapping) or not isinstance(task.get("schema_version"), str)
            or task["schema_version"] not in SOURCE_TASK_VERSIONS):
        raise WorkingInputError("unsupported source Task version")
    references = [_ref(value) for value in _items(task["input_refs"])]
    permitted = {_ref_key(value) for value in references}
    captured, seen = [], set()
    for value in _items(materials):
        record = _object(value, {"path", "sha256", "revision", "text"}, {"path", "sha256", "text"})
        reference = _ref({key: record[key] for key in ("path", "sha256", "revision") if key in record})
        key = _ref_key(reference)
        if key not in permitted or key in seen:
            raise WorkingInputError("snapshot is outside or duplicates the Task read set")
        text = record["text"]
        if not isinstance(text, str):
            raise WorkingInputError("snapshot text must be UTF-8 text")
        try:
            encoded = text.encode("utf-8")
        except UnicodeEncodeError:
            raise WorkingInputError("snapshot text must be UTF-8 text") from None
        if hashlib.sha256(encoded).hexdigest() != reference["sha256"]:
            raise WorkingInputError("snapshot hash mismatch")
        seen.add(key)
        captured.append({**reference, "text": text})

    permissions = _object(task["permissions"],
        {"filesystem", "network", "external_write", "allowed_roots"},
        {"filesystem", "network", "external_write"})
    if permissions["filesystem"] == "unspecified" or permissions["network"] == "unspecified":
        raise WorkingInputError("permissions must be explicit")
    external = permissions["external_write"]
    if type(external) is not bool and external not in ("allowed", "forbidden"):
        raise WorkingInputError("external_write must be explicit")
    permission_view = {"filesystem": _text(permissions["filesystem"]),
        "network": _text(permissions["network"]), "external_write": external,
        "allowed_roots": [_path(value) for value in _items(permissions.get("allowed_roots", ()))]}
    delegation = task["delegation"]
    if not isinstance(delegation, Mapping) or type(delegation.get("allowed")) is not bool:
        raise WorkingInputError("delegation must be explicit")
    delegation_view = {"allowed": delegation["allowed"]}
    for key in ("max_depth", "max_parallel"):
        if key in delegation:
            value = _integer(delegation[key])
            if not delegation["allowed"] and value:
                raise WorkingInputError("disabled delegation has a positive ceiling")
            delegation_view[key] = value

    outputs = []
    for value in _items(task["required_outputs"]):
        if isinstance(value, str):
            outputs.append(_text(value))
        else:
            output = _object(value, {"contract", "min_count"}, {"contract"})
            projected = {"contract": _text(output["contract"])}
            if "min_count" in output:
                projected["min_count"] = _integer(output["min_count"])
            outputs.append(projected)
    checks = _texts(task["completion_checks"])
    write_scope = [_path(value) for value in _items(task["write_scope"])]
    duties = _texts(responsibilities)
    stops = []
    for value in _items(stop_conditions):
        record = _object(value, {"kind", "condition"}, {"kind", "condition"})
        if not isinstance(record["kind"], str) or record["kind"] not in STOP_KINDS:
            raise WorkingInputError("unsupported actual stop kind")
        stops.append({"kind": record["kind"], "condition": _text(record["condition"])})
    if not outputs or not checks or not write_scope or not duties or not stops:
        raise WorkingInputError("work duties, delivery and actual stops must be explicit")

    return {
        "schema_version": WORKING_INPUT_VERSION,
        "role": _text(role), "responsibilities": duties,
        "source_task": {"schema_version": task["schema_version"], "task_id": _text(task["task_id"]),
                        "revision": _integer(task.get("revision", 1), 1)},
        "objective": {"goal": _text(task["goal"]), "atomic_boundary": _text(task["atomic_boundary"]),
                      "question_refs": _texts(task["question_refs"]), "active_modes": _texts(task["active_modes"])},
        "materials": captured,
        "necessary_decisions": _records(necessary_decisions, permitted),
        "counterevidence": _records(counterevidence, permitted),
        "authority": {"permissions": permission_view, "delegation": delegation_view,
            "agent_profile": _text(task["agent_profile"]),
            "required_capabilities": _texts(task["required_capabilities"]),
            "required_skills": _texts(task["required_skills"]), "forbidden_skills": _texts(task["forbidden_skills"])},
        "delivery": {"write_scope": write_scope,
                     "required_outputs": outputs, "completion_checks": checks},
        "stop_conditions": stops,
        "boundaries": {"permission_grant": False, "input_admission": False,
                       "supply_selection": False, "runtime_authority": False, "task_completion": False},
    }
