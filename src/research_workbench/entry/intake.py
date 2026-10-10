"""Compile bounded model proposals into existing, schema-valid control drafts."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from research_workbench.artifacts.integrity import resolve_within_root
from research_workbench.capability.resolver import permission_policy_covers
from research_workbench.contracts.common import PermissionPolicy, require_relative_path, to_plain
from research_workbench.tasks.models import FileReference, HandoffPolicy
from research_workbench.validation.schemas import SchemaCatalog
from research_workbench.entry.roles import EntryInputError, document_bytes, read_pinned_inputs


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EntryInputError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _json(value: str | Mapping[str, Any]) -> dict[str, Any]:
    try:
        raw = value if isinstance(value, str) else json.dumps(to_plain(value), allow_nan=False)
        document = json.loads(raw, object_pairs_hook=_unique_object,
                              parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (TypeError, ValueError) as exc:
        raise EntryInputError(f"invalid internal JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise EntryInputError("internal JSON must be an object")
    return document


def _schema(catalog: SchemaCatalog, kind: str, document: Mapping[str, Any]) -> None:
    errors = catalog.validate(kind, document)
    if errors:
        raise EntryInputError(f"invalid {kind}: " + "; ".join(
            f"{error.pointer}: {error.message}" for error in errors))


def _subset(values, ceiling, label: str) -> None:
    if not set(values) <= set(ceiling):
        raise EntryInputError(f"draft expands {label}")


def _scope_within(scope: str, allowed: str) -> bool:
    require_relative_path(scope, "write_scope")
    require_relative_path(allowed, "write_scope ceiling")
    scope, allowed = scope.replace("\\", "/"), allowed.replace("\\", "/")
    if scope == allowed:
        return True
    if allowed.endswith("/**"):
        base = allowed[:-3].rstrip("/")
        return scope == base or scope.startswith(base + "/")
    return False


def _permissions(proposed: Mapping[str, Any], ceiling: Mapping[str, Any]) -> None:
    current, maximum = PermissionPolicy.from_mapping(proposed), PermissionPolicy.from_mapping(ceiling)
    # "unspecified" is unknown, not a grant. The compatibility rank must not
    # turn omitted human permissions into permission to use network or write.
    for key in ("filesystem", "network"):
        if getattr(maximum, key) == "unspecified" and getattr(current, key) != "unspecified":
            raise EntryInputError(f"human {key} boundary is unknown")
    if not permission_policy_covers(maximum, current):
        raise EntryInputError("draft expands permissions")


def _budget(proposed: Mapping[str, Any], ceiling: Mapping[str, Any], label: str) -> None:
    # Absence is not a narrower value: downstream callers otherwise fall back
    # to their own defaults and lose the human-supplied limit.
    missing = ceiling.keys() - proposed.keys()
    if missing:
        raise EntryInputError(f"draft removes {label} " + ", ".join(sorted(missing)))
    for key, value in proposed.items():
        maximum = ceiling.get(key)
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0
                or isinstance(maximum, bool) or not isinstance(maximum, (int, float))
                or not math.isfinite(maximum) or maximum < 0 or value > maximum):
            raise EntryInputError(f"draft expands {label} {key}")


def _handoff_policy(task: Mapping[str, Any], maximum_task: Mapping[str, Any]) -> None:
    if "handoff_policy" in maximum_task and "handoff_policy" not in task:
        raise EntryInputError("draft removes human handoff_policy")
    proposed = HandoffPolicy.from_mapping(task.get("handoff_policy", {}))
    required = HandoffPolicy.from_mapping(maximum_task.get("handoff_policy", {}))
    if (required.require_transfer_manifest and not proposed.require_transfer_manifest
            or required.semantic_review == "required" and proposed.semantic_review != "required"
            or proposed.minimum_semantic_samples < required.minimum_semantic_samples):
        raise EntryInputError("draft weakens human handoff_policy")


@dataclass(frozen=True, slots=True)
class ControlDraft:
    protocol: Mapping[str, Any]
    task: Mapping[str, Any]
    method: Mapping[str, Any] | None
    requirements: tuple[Mapping[str, Any], ...]
    unknowns: tuple[str, ...]
    protocol_ceiling: Mapping[str, Any] = field(repr=False)
    task_ceiling: Mapping[str, Any] = field(repr=False)

    def as_mapping(self) -> dict[str, Any]:
        result = {"protocol": to_plain(self.protocol), "task": to_plain(self.task),
                  "requirements": to_plain(self.requirements), "unknowns": list(self.unknowns)}
        if self.method is not None:
            result["method"] = to_plain(self.method)
        return result


def compile_control_draft(
    root: str | Path, *, response: str | Mapping[str, Any],
    protocol_ceiling: Mapping[str, Any], task_ceiling: Mapping[str, Any],
    schema_catalog: SchemaCatalog | None = None,
) -> ControlDraft:
    """Validate model output under caller-supplied human ceilings; never approve."""
    payload = _json(response)
    if set(payload) - {"protocol", "task", "method", "requirements", "unknowns"}:
        raise EntryInputError("unsupported internal control fields")
    if not {"protocol", "task", "unknowns"} <= payload.keys():
        raise EntryInputError("protocol, task and unknowns are required")
    maximum_protocol, maximum_task = _json(protocol_ceiling), _json(task_ceiling)
    catalog = schema_catalog or SchemaCatalog()
    _schema(catalog, "project_protocol", maximum_protocol)
    _schema(catalog, "task_packet", maximum_task)
    protocol, task = payload["protocol"], payload["task"]
    for kind, document in (("project_protocol", protocol), ("task_packet", task)):
        if not isinstance(document, dict):
            raise EntryInputError(f"{kind} must be an object")
        _schema(catalog, kind, document)
    for key in ("project_id",):
        if protocol[key] != maximum_protocol[key]:
            raise EntryInputError(f"draft changes human {key}")
    for key in ("task_id", "goal", "agent_profile"):
        if task[key] != maximum_task[key]:
            raise EntryInputError(f"draft changes human {key}")
    for document, maximum in ((protocol, maximum_protocol), (task, maximum_task)):
        if document.get("revision", 1) != maximum.get("revision", 1):
            raise EntryInputError("draft changes human revision")
    for key in ("active_modes", "claim_ceiling", "question_refs"):
        _subset(protocol[key], maximum_protocol[key], key)
    if not set(maximum_protocol["required_human_gates"]) <= set(protocol["required_human_gates"]):
        raise EntryInputError("draft removes required Human gates")
    for key in ("max_parallel_subagents", "max_delegation_depth"):
        if protocol["budgets"][key] > maximum_protocol["budgets"][key]:
            raise EntryInputError(f"draft expands {key}")
    if protocol["budgets"]["coordination_cost_ratio_warn"] != maximum_protocol["budgets"]["coordination_cost_ratio_warn"]:
        raise EntryInputError("draft changes coordination warning boundary")
    if protocol["context_policy"] != maximum_protocol["context_policy"]:
        raise EntryInputError("draft changes human context policy")
    boundary, maximum_boundary = protocol["data_boundary"], maximum_protocol["data_boundary"]
    for key in ("local_only", "external_upload_requires_approval", "zero_data_retention_required"):
        if maximum_boundary.get(key) is True and boundary.get(key) is not True:
            raise EntryInputError(f"draft weakens {key}")
    _subset(boundary.get("allowed_regions", []), maximum_boundary.get("allowed_regions", []), "regions")
    for key in boundary.keys() - {"local_only", "external_upload_requires_approval", "zero_data_retention_required", "allowed_regions"}:
        if boundary[key] != maximum_boundary.get(key):
            raise EntryInputError(f"draft changes unrecognized data boundary {key}")
    _permissions(task["permissions"], maximum_task["permissions"])
    for scope in task["write_scope"]:
        if not any(_scope_within(scope, allowed) for allowed in maximum_task["write_scope"]):
            raise EntryInputError("draft expands write scope")
    _budget(task["budget"], maximum_task["budget"], "budget")
    delegation, maximum_delegation = task["delegation"], maximum_task["delegation"]
    if delegation["allowed"] and not maximum_delegation["allowed"]:
        raise EntryInputError("draft enables unauthorized delegation")
    for key in ("max_depth", "max_parallel"):
        value = delegation.get(key, 0)
        protocol_key = "max_delegation_depth" if key == "max_depth" else "max_parallel_subagents"
        if value > maximum_delegation.get(key, 0) or value > protocol["budgets"][protocol_key]:
            raise EntryInputError(f"draft expands delegation {key}")
    _budget(delegation.get("sub_budget", {}), maximum_delegation.get("sub_budget", {}),
            "child sub-budget")
    _subset(task["active_modes"], maximum_task["active_modes"], "Task modes")
    _subset(task["active_modes"], protocol["active_modes"], "Protocol modes")
    _subset(task["question_refs"], maximum_task["question_refs"], "Task questions")
    _subset(task["required_skills"], maximum_task["required_skills"], "required Skills")
    if not set(maximum_task["required_skills"]) <= set(task["required_skills"]):
        raise EntryInputError("draft removes required human Skills")
    _handoff_policy(task, maximum_task)
    if not set(maximum_task["forbidden_skills"]) <= set(task["forbidden_skills"]):
        raise EntryInputError("draft removes forbidden Skills")
    for key in ("completion_checks", "safe_pause_conditions", "stop_conditions", "stale_if"):
        if not set(maximum_task[key]) <= set(task[key]):
            raise EntryInputError(f"draft removes human {key}")
    required_outputs = {document_bytes(item) for item in maximum_task["required_outputs"]}
    if not required_outputs <= {document_bytes(item) for item in task["required_outputs"]}:
        raise EntryInputError("draft removes required human outputs")
    permitted_refs = {document_bytes(ref) for ref in maximum_task["input_refs"]}
    if any(document_bytes(ref) not in permitted_refs for ref in task["input_refs"]):
        raise EntryInputError("draft adds or changes human input pins")
    read_pinned_inputs(root, task["input_refs"])
    unknowns = payload["unknowns"]
    if not isinstance(unknowns, list) or any(not isinstance(item, str) or not item.strip() for item in unknowns):
        raise EntryInputError("unknowns must be an array of nonempty strings")
    requirements = payload.get("requirements", [])
    if not isinstance(requirements, list):
        raise EntryInputError("requirements must be an array")
    for requirement in requirements:
        _schema(catalog, "capability_requirement", requirement)
        _permissions(requirement["constraints"]["permission_ceiling"], maximum_task["permissions"])
        if maximum_boundary.get("local_only") is True and requirement["constraints"]["data_egress"]["policy"] != "forbidden":
            raise EntryInputError("Requirement expands human data egress boundary")
    if len({item["requirement_id"] for item in requirements}) != len(requirements):
        raise EntryInputError("duplicate Requirement identity")
    method = payload.get("method")
    if method is not None:
        if not isinstance(method, dict) or not isinstance(method.get("task_ref"), dict):
            raise EntryInputError("Method must contain a task_ref object")
        reference = method["task_ref"]
        if reference.get("task_id") != task["task_id"] or reference.get("revision") != task.get("revision", 1):
            raise EntryInputError("Method/Task identity mismatch")
        reference["sha256"] = hashlib.sha256(document_bytes(task)).hexdigest()
        _schema(catalog, "method_resolution", method)
        permitted_modes = set(protocol["active_modes"])
        if any(ref not in permitted_modes and ref.split("@", 1)[0] not in permitted_modes
               for ref in method["mode_resolution"]["selected_mode_refs"]):
            raise EntryInputError("draft expands Method modes")
    return ControlDraft(_freeze(protocol), _freeze(task), _freeze(method),
                        tuple(_freeze(item) for item in requirements), tuple(unknowns),
                        _freeze(maximum_protocol), _freeze(maximum_task))


def persist_control_draft(
    root: str | Path, *, directory: str, draft: ControlDraft,
) -> tuple[FileReference, ...]:
    """Publish only in a new exclusive directory; a manifest remains a draft."""
    require_relative_path(directory, "draft directory")
    destination = resolve_within_root(root, directory)
    if destination is None or destination == Path(root).resolve():
        raise EntryInputError("draft directory must be a new child of project root")
    # Recheck pins before publication; immutable mappings prevent later mutation.
    draft = compile_control_draft(root, response=draft.as_mapping(),
                                  protocol_ceiling=draft.protocol_ceiling,
                                  task_ceiling=draft.task_ceiling)
    documents = {"project-protocol.json": draft.protocol, "task.json": draft.task}
    if draft.method is not None:
        documents["method.json"] = draft.method
    for index, requirement in enumerate(draft.requirements):
        documents[f"requirement-{index + 1}.json"] = requirement
    prepared = {name: document_bytes(value) for name, value in documents.items()}
    destination.mkdir(parents=True, exist_ok=False)
    references = []
    for name, raw in prepared.items():
        path = destination / name
        with path.open("xb") as stream:
            stream.write(raw)
        references.append(FileReference(path.relative_to(Path(root).resolve()).as_posix(),
                                        hashlib.sha256(raw).hexdigest()))
    manifest = {"status": "draft", "qualification": "schema-validated-control-draft",
                "unknowns": list(draft.unknowns), "documents": to_plain(references),
                "limitations": ["Human approval and runtime admission are separate.",
                                "No full Method/Registry/Runtime closure validation is claimed.",
                                "Partial publication failures are retained; no transaction is claimed."]}
    with (destination / "draft.json").open("xb") as stream:
        stream.write(document_bytes(manifest))
    return tuple(references)
