"""Supply-neutral Resolved Execution View production.

The producer consumes one already validated Runtime Bundle and four explicit,
hash-pinned inputs.  It computes constraints but does not execute, reselect,
rebind, fall back, or grant permission.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from research_workbench.artifacts.integrity import hash_bytes, resolve_within_root
from research_workbench.execution.runtime_bundle import ValidatedRuntimeBundle
from research_workbench.io import load_document_bytes
from research_workbench.validation.schemas import SchemaCatalog


_FILESYSTEM_ORDER = {
    "forbidden": 0,
    "read-only": 1,
    "worktree-write": 2,
    "workspace-write": 3,
}
_NETWORK_ORDER = {"forbidden": 0, "search-and-fetch": 1, "allowed": 2}
_INPUT_SCHEMAS = {
    "agent_profile": "agent_profile",
    "data_policy": "execution_policy",
    "host_policy": "execution_policy",
    "execution_binding": "execution_binding",
}


@dataclass(frozen=True, slots=True)
class PinnedExecutionInput:
    path: str
    sha256: str


@dataclass(frozen=True, slots=True)
class ExecutionViewIssue:
    path: Path
    code: str
    message: str


class ExecutionViewValidationError(ValueError):
    def __init__(self, issues: Iterable[ExecutionViewIssue]):
        self.issues = tuple(issues)
        detail = "; ".join(f"{item.path}:{item.code}:{item.message}" for item in self.issues)
        super().__init__("Resolved Execution View validation failed: " + detail)


def _normalized_hash(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.lower().removeprefix("sha256:")
    if len(normalized) != 64:
        return None
    try:
        int(normalized, 16)
    except ValueError:
        return None
    return normalized


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _manifest_entry(bundle: ValidatedRuntimeBundle, kind: str) -> Mapping[str, Any]:
    entries = [item for item in bundle.manifest["documents"] if item["kind"] == kind]
    if len(entries) != 1:
        raise ExecutionViewValidationError(
            (
                ExecutionViewIssue(
                    bundle.manifest_path,
                    "EXECUTION-VIEW-BUNDLE-CARDINALITY",
                    f"expected exactly one {kind}; found {len(entries)}",
                ),
            )
        )
    return entries[0]


def _bundle_document(
    bundle: ValidatedRuntimeBundle, kind: str
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    entry = _manifest_entry(bundle, kind)
    path = (bundle.project_root / str(entry["path"])).resolve()
    document = bundle.documents.get(path)
    if document is None:
        raise ExecutionViewValidationError(
            (
                ExecutionViewIssue(
                    path,
                    "EXECUTION-VIEW-BUNDLE-DOCUMENT-MISSING",
                    kind,
                ),
            )
        )
    return entry, document


def _load_pinned_input(
    root: Path,
    pin: PinnedExecutionInput,
    *,
    schema_kind: str,
    catalog: SchemaCatalog,
) -> tuple[Path, str, Mapping[str, Any]]:
    path = resolve_within_root(root, pin.path)
    if path is None:
        raise ExecutionViewValidationError(
            (ExecutionViewIssue(root, "EXECUTION-VIEW-PATH-ESCAPE", pin.path),)
        )
    if not path.is_file():
        code = "EXECUTION-VIEW-DIRECTORY-INPUT" if path.is_dir() else "EXECUTION-VIEW-INPUT-MISSING"
        raise ExecutionViewValidationError((ExecutionViewIssue(path, code, pin.path),))
    content = path.read_bytes()
    actual_hash = hash_bytes(content)
    expected_hash = _normalized_hash(pin.sha256)
    if expected_hash != actual_hash:
        raise ExecutionViewValidationError(
            (ExecutionViewIssue(path, "EXECUTION-VIEW-INPUT-HASH-MISMATCH", pin.path),)
        )
    try:
        document = load_document_bytes(path, content)
    except Exception as exc:
        raise ExecutionViewValidationError(
            (ExecutionViewIssue(path, "EXECUTION-VIEW-INPUT-PARSE", str(exc)),)
        ) from exc
    errors = catalog.validate(schema_kind, document)
    if errors:
        raise ExecutionViewValidationError(
            ExecutionViewIssue(path, "EXECUTION-VIEW-INPUT-SCHEMA", f"{item.pointer}: {item.message}")
            for item in errors
        )
    if not isinstance(document, Mapping):
        raise ExecutionViewValidationError(
            (ExecutionViewIssue(path, "EXECUTION-VIEW-INPUT-SHAPE", "document must be an object"),)
        )
    return path, actual_hash, document


def _normalized_external_write(value: object) -> bool:
    if value in {False, "forbidden"}:
        return False
    if value in {True, "allowed"}:
        return True
    raise ValueError(f"unsupported external_write value: {value!r}")


def _permission_source(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} permissions must be an object")
    filesystem = value.get("filesystem")
    network = value.get("network")
    if filesystem not in _FILESYSTEM_ORDER or network not in _NETWORK_ORDER:
        raise ValueError(f"{label} permissions use an unsupported filesystem/network value")
    roots = value.get("allowed_roots", ())
    if not isinstance(roots, Sequence) or isinstance(roots, (str, bytes)) or not all(
        isinstance(item, str) for item in roots
    ):
        raise ValueError(f"{label} allowed_roots must be an array of paths")
    return {
        "filesystem": filesystem,
        "network": network,
        "external_write": _normalized_external_write(value.get("external_write", False)),
        "allowed_roots": tuple(roots),
    }


def _contains(root: str, candidate: str) -> bool:
    root_path = PurePosixPath(root)
    candidate_path = PurePosixPath(candidate)
    return candidate_path == root_path or root_path in candidate_path.parents


def _intersect_roots(sources: Sequence[Sequence[str]]) -> list[str]:
    if any(not source for source in sources):
        return []
    candidates = {
        candidate
        for source in sources
        for candidate in source
        if all(any(_contains(root, candidate) for root in other) for other in sources)
    }
    return sorted(
        candidate
        for candidate in candidates
        if not any(candidate != other and _contains(candidate, other) for other in candidates)
    )


def _intersect_permissions(sources: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    filesystem = min(sources, key=lambda item: _FILESYSTEM_ORDER[str(item["filesystem"])])["filesystem"]
    network = min(sources, key=lambda item: _NETWORK_ORDER[str(item["network"])])["network"]
    external_write = all(bool(item["external_write"]) for item in sources)
    roots = _intersect_roots([tuple(item["allowed_roots"]) for item in sources])
    if filesystem in {"worktree-write", "workspace-write"} and not roots:
        raise ValueError("permission intersection leaves write access without an allowed root")
    return {
        "filesystem": filesystem,
        "network": network,
        "external_write": external_write,
        "allowed_roots": roots,
    }


def _intersect_data_egress(sources: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    forbidden = sorted(
        {
            item
            for source in sources
            for item in source.get("forbidden_payloads", ())
            if isinstance(item, str)
        }
    )
    if any(source.get("policy") == "forbidden" for source in sources):
        return {"policy": "forbidden", "allowed_payloads": [], "forbidden_payloads": forbidden}
    allowed_sets = [set(source.get("allowed_payloads", ())) for source in sources]
    allowed = sorted(set.intersection(*allowed_sets) - set(forbidden))
    if not allowed:
        return {"policy": "forbidden", "allowed_payloads": [], "forbidden_payloads": forbidden}
    return {
        "policy": "allowlisted-only",
        "allowed_payloads": allowed,
        "forbidden_payloads": forbidden,
    }


def _intersect_side_effects(sources: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if any(source.get("policy") == "none" for source in sources):
        return {"policy": "none", "allowed_effects": []}
    allowed_sets = [set(source.get("allowed_effects", ())) for source in sources]
    allowed = sorted(set.intersection(*allowed_sets))
    if not allowed:
        return {"policy": "none", "allowed_effects": []}
    return {"policy": "allowlisted-only", "allowed_effects": allowed}


def _intersect_budget(sources: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    keys = {key for source in sources for key in source if key in {"max_turns", "max_output_tokens", "max_seconds"}}
    result = {
        key: min(int(source[key]) for source in sources if key in source)
        for key in sorted(keys)
    }
    if not result:
        raise ValueError("budget intersection requires at least one ceiling")
    return result


def _require_supply_satisfiable(
    supply_permissions: Mapping[str, Any],
    supply_egress: Mapping[str, Any],
    supply_effects: Mapping[str, Any],
    effective_permissions: Mapping[str, Any],
    effective_egress: Mapping[str, Any],
    effective_effects: Mapping[str, Any],
) -> None:
    """Reject a final intersection that makes the selected Supply unusable."""

    if _FILESYSTEM_ORDER[str(effective_permissions["filesystem"])] < _FILESYSTEM_ORDER[
        str(supply_permissions["filesystem"])
    ]:
        raise ValueError("effective filesystem boundary is below selected Supply requirements")
    if _NETWORK_ORDER[str(effective_permissions["network"])] < _NETWORK_ORDER[
        str(supply_permissions["network"])
    ]:
        raise ValueError("effective network boundary is below selected Supply requirements")
    if bool(supply_permissions["external_write"]) and not bool(
        effective_permissions["external_write"]
    ):
        raise ValueError("effective external-write boundary is below selected Supply requirements")

    supply_payloads = set(supply_egress.get("allowed_payloads", ()))
    effective_payloads = set(effective_egress.get("allowed_payloads", ()))
    if supply_egress.get("policy") == "allowlisted-only" and (
        effective_egress.get("policy") != "allowlisted-only"
        or not supply_payloads.issubset(effective_payloads)
    ):
        raise ValueError("effective data-egress boundary excludes selected Supply behavior")
    if supply_payloads.intersection(effective_egress.get("forbidden_payloads", ())):
        raise ValueError("effective data-egress forbidden set conflicts with selected Supply behavior")

    supply_allowed_effects = set(supply_effects.get("allowed_effects", ()))
    effective_allowed_effects = set(effective_effects.get("allowed_effects", ()))
    if supply_effects.get("policy") == "allowlisted-only" and (
        effective_effects.get("policy") != "allowlisted-only"
        or not supply_allowed_effects.issubset(effective_allowed_effects)
    ):
        raise ValueError("effective side-effect boundary excludes selected Supply behavior")


def _file_ref(ref: str, path: str, digest: str) -> dict[str, str]:
    return {"ref": ref, "path": path, "sha256": digest}


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return copy.deepcopy(value)


def _required_output_contracts(required: Sequence[Any]) -> set[str]:
    contracts: set[str] = set()
    for item in required:
        if isinstance(item, str):
            contracts.add(item)
        elif isinstance(item, Mapping) and isinstance(item.get("contract"), str):
            contracts.add(str(item["contract"]))
        else:
            raise ValueError("Task required_outputs contains an unsupported contract")
    return contracts


def produce_resolved_execution_view(
    bundle: ValidatedRuntimeBundle,
    *,
    agent_profile: PinnedExecutionInput,
    data_policy: PinnedExecutionInput,
    host_policy: PinnedExecutionInput,
    execution_binding: PinnedExecutionInput,
    execution_at: str,
    view_id: str,
    revision: int = 1,
    expected_bundle_sha256: str,
    schema_root: str | Path | None = None,
) -> dict[str, Any]:
    """Produce one final frozen View without executing or selecting Supply."""

    root = bundle.project_root
    catalog = SchemaCatalog(schema_root)
    manifest_bytes = bundle.manifest_path.read_bytes()
    bundle_hash = hash_bytes(manifest_bytes)
    if (
        _normalized_hash(expected_bundle_sha256) != bundle_hash
        or bundle_hash != bundle.manifest_sha256
    ):
        raise ExecutionViewValidationError(
            (
                ExecutionViewIssue(
                    bundle.manifest_path,
                    "EXECUTION-VIEW-BUNDLE-PIN-MISMATCH",
                    "external Runtime Bundle pin does not match current manifest bytes",
                ),
            )
        )

    pins = {
        "agent_profile": agent_profile,
        "data_policy": data_policy,
        "host_policy": host_policy,
        "execution_binding": execution_binding,
    }
    loaded = {
        name: _load_pinned_input(root, pin, schema_kind=_INPUT_SCHEMAS[name], catalog=catalog)
        for name, pin in pins.items()
    }
    profile_path, profile_hash, profile = loaded["agent_profile"]
    data_path, data_hash, data = loaded["data_policy"]
    host_path, host_hash, host = loaded["host_policy"]
    binding_path, binding_hash, binding = loaded["execution_binding"]
    if data.get("policy_kind") != "data-policy" or host.get("policy_kind") != "host-policy":
        raise ExecutionViewValidationError(
            (
                ExecutionViewIssue(data_path, "EXECUTION-VIEW-POLICY-KIND", "expected data-policy"),
                ExecutionViewIssue(host_path, "EXECUTION-VIEW-POLICY-KIND", "expected host-policy"),
            )
        )

    task_entry, task = _bundle_document(bundle, "task_packet")
    method_entry, method = _bundle_document(bundle, "method_resolution")
    resolution_entry, resolution = _bundle_document(bundle, "capability_resolution")
    snapshot_entry, snapshot = _bundle_document(bundle, "resolved_capability_snapshot")
    supply_entry, supply = _bundle_document(bundle, "capability_supply_report")
    _, requirement = _bundle_document(bundle, "capability_requirement")
    selected_ref = snapshot["selected_supply_report_ref"]["ref"]
    if binding.get("selected_supply_report_ref") != selected_ref:
        raise ExecutionViewValidationError(
            (
                ExecutionViewIssue(
                    binding_path,
                    "EXECUTION-VIEW-SUPPLY-RESELECTION",
                    "Execution Binding must preserve the Snapshot-selected Supply",
                ),
            )
        )
    if profile.get("agent_profile_id") != task.get("agent_profile"):
        raise ExecutionViewValidationError(
            (
                ExecutionViewIssue(
                    profile_path,
                    "EXECUTION-VIEW-PROFILE-IDENTITY-MISMATCH",
                    f"Task requires Agent Profile {task.get('agent_profile')}",
                ),
            )
        )

    allowed_tool_capabilities = {
        item for item in profile.get("allowed_tool_capabilities", ()) if isinstance(item, str)
    }
    supply_kind = supply.get("supply_identity", {}).get("supply_kind")
    selected_tool_capabilities = (
        {
            item
            for item in supply.get("provided_capabilities", ())
            if isinstance(item, str)
        }
        if supply_kind == "tool"
        else set()
    )
    required_tool_capabilities = selected_tool_capabilities
    if not required_tool_capabilities.issubset(allowed_tool_capabilities):
        raise ExecutionViewValidationError(
            (
                ExecutionViewIssue(
                    profile_path,
                    "EXECUTION-VIEW-PROFILE-TOOL-CAPABILITY",
                    "selected Tool capabilities exceed Agent Profile allowed_tool_capabilities",
                ),
            )
        )
    try:
        required_output_contracts = _required_output_contracts(
            requirement.get("required_artifacts", ())
        )
    except ValueError as exc:
        raise ExecutionViewValidationError(
            (ExecutionViewIssue(profile_path, "EXECUTION-VIEW-PROFILE-OUTPUT-CONTRACT", str(exc)),)
        ) from exc
    profile_output_contracts = {
        item for item in profile.get("output_contracts", ()) if isinstance(item, str)
    }
    if not required_output_contracts.issubset(profile_output_contracts):
        raise ExecutionViewValidationError(
            (
                ExecutionViewIssue(
                    profile_path,
                    "EXECUTION-VIEW-PROFILE-OUTPUT-CONTRACT",
                    "Task required outputs exceed Agent Profile output_contracts",
                ),
            )
        )
    model_policy = profile.get("model_policy", {})
    model_binding = binding.get("model", {})
    required_model_capabilities = {
        item for item in model_policy.get("required_capabilities", ()) if isinstance(item, str)
    }
    bound_model_capabilities = {
        item for item in model_binding.get("capabilities", ()) if isinstance(item, str)
    }
    if (
        model_binding.get("model_class") != model_policy.get("class")
        or (
            model_policy.get("default_slot") is not None
            and model_binding.get("slot") != model_policy.get("default_slot")
        )
        or not required_model_capabilities.issubset(bound_model_capabilities)
    ):
        raise ExecutionViewValidationError(
            (
                ExecutionViewIssue(
                    binding_path,
                    "EXECUTION-VIEW-PROFILE-MODEL-POLICY",
                    "bound Model does not satisfy Agent Profile class/slot/capabilities",
                ),
            )
        )
    if host.get("subject_host") != binding.get("host"):
        raise ExecutionViewValidationError(
            (
                ExecutionViewIssue(
                    host_path,
                    "EXECUTION-VIEW-HOST-POLICY-SUBJECT",
                    "Host policy subject does not equal the exact bound Host",
                ),
            )
        )

    supply_components = {
        item.get("component_kind"): item
        for item in supply.get("supply_identity", {}).get("components", ())
        if isinstance(item, Mapping)
    }
    for component_kind in ("provider", "adapter"):
        selected_component = supply_components.get(component_kind)
        if selected_component is None:
            continue
        actual = binding.get(component_kind, {})
        if not isinstance(actual, Mapping) or (
            actual.get("ref") != selected_component.get("component_ref")
            or actual.get("version") != selected_component.get("version")
            or _normalized_hash(actual.get("content_hash"))
            != _normalized_hash(selected_component.get("content_hash"))
        ):
            raise ExecutionViewValidationError(
                (
                    ExecutionViewIssue(
                        binding_path,
                        "EXECUTION-VIEW-BINDING-IDENTITY-MISMATCH",
                        f"{component_kind} binding does not match selected Supply identity",
                    ),
                )
            )

    try:
        at = _timestamp(execution_at, "execution_at")
        availability = supply["availability"]
        if availability.get("status") != "available":
            raise ValueError("selected Supply is not available")
        observed = _timestamp(availability["observed_at"], "supply.observed_at")
        valid_until = _timestamp(availability.get("valid_until"), "supply.valid_until")
        data_from = _timestamp(data["valid_from"], "data_policy.valid_from")
        data_until = _timestamp(data["valid_until"], "data_policy.valid_until")
        host_from = _timestamp(host["valid_from"], "host_policy.valid_from")
        host_until = _timestamp(host["valid_until"], "host_policy.valid_until")
        if not (observed <= at <= valid_until and data_from <= at <= data_until and host_from <= at <= host_until):
            raise ValueError("execution_at is outside Supply or policy freshness windows")
        supply_identity = supply["supply_identity"]
        evidence_documents = [
            document
            for path, document in bundle.documents.items()
            if any(
                item["kind"] == "capability_conformance_evidence"
                and (root / str(item["path"])).resolve() == path
                for item in bundle.manifest["documents"]
            )
        ]
        if not evidence_documents:
            raise ValueError("selected Supply has no typed conformance evidence")
        availability_scope = availability["scope"]
        for evidence in evidence_documents:
            if evidence.get("evidence_kind") not in {"local-conformance", "live-conformance"}:
                raise ValueError("Runtime View requires local/live typed evidence")
            if evidence.get("result") != "pass":
                raise ValueError("typed conformance evidence did not pass")
            if evidence.get("implementation_ref") != supply_identity.get("implementation_ref") or evidence.get(
                "implementation_version"
            ) != supply_identity.get("implementation_version"):
                raise ValueError("typed evidence implementation identity does not match selected Supply")
            if requirement.get("requirement_id") not in evidence.get("capability_ids", ()):
                raise ValueError("typed evidence does not cover the selected Capability Requirement")
            evidence_scope = evidence.get("scope", {})
            if evidence_scope.get("scope_kind") != availability_scope.get("scope_kind") or evidence_scope.get(
                "scope_ref"
            ) != availability_scope.get("scope_ref"):
                raise ValueError("typed evidence scope does not match Supply availability")
        permission_sources = [
            _permission_source(task.get("permissions"), "Task"),
            _permission_source(profile.get("permission_ceiling"), "Agent Profile"),
            _permission_source(
                {
                    **snapshot.get("supply_required_permissions", {}),
                    "allowed_roots": task.get("permissions", {}).get("allowed_roots", ()),
                },
                "Supply",
            ),
            _permission_source(data.get("permission_ceiling"), "DataPolicy"),
            _permission_source(host.get("permission_ceiling"), "Host policy"),
        ]
        effective_permissions = _intersect_permissions(permission_sources)
        effective_egress = _intersect_data_egress(
            [snapshot["supply_data_egress"], data["data_egress"], host["data_egress"]]
        )
        effective_effects = _intersect_side_effects(
            [snapshot["supply_side_effects"], data["side_effects"], host["side_effects"]]
        )
        effective_budget = _intersect_budget(
            [task.get("budget", {}), data["budget_ceiling"], host["budget_ceiling"]]
        )
        _require_supply_satisfiable(
            permission_sources[2],
            snapshot["supply_data_egress"],
            snapshot["supply_side_effects"],
            effective_permissions,
            effective_egress,
            effective_effects,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ExecutionViewValidationError(
            (ExecutionViewIssue(bundle.manifest_path, "EXECUTION-VIEW-PREFLIGHT-BLOCKED", str(exc)),)
        ) from exc

    task_revision = task.get("revision", 1)
    view = {
        "schema_version": "0.1.0",
        "view_id": view_id,
        "revision": revision,
        "execution_at": execution_at,
        "runtime_bundle_ref": _file_ref(
            f"{bundle.manifest['bundle_id']}@r{bundle.manifest['revision']}",
            _relative(root, bundle.manifest_path),
            bundle_hash,
        ),
        "execution_scope": _plain(bundle.manifest["execution_scope"]),
        "task_ref": _file_ref(
            f"{task['task_id']}@r{task_revision}", str(task_entry["path"]), str(task_entry["sha256"])
        ),
        "method_resolution_ref": _file_ref(
            f"{method['resolution_id']}@r{method['revision']}",
            str(method_entry["path"]),
            str(method_entry["sha256"]),
        ),
        "capability_resolution_ref": _file_ref(
            f"{resolution['resolution_id']}@r{resolution['revision']}",
            str(resolution_entry["path"]),
            str(resolution_entry["sha256"]),
        ),
        "snapshot_ref": _file_ref(
            f"{snapshot['snapshot_id']}@r{snapshot['revision']}",
            str(snapshot_entry["path"]),
            str(snapshot_entry["sha256"]),
        ),
        "selected_supply_report_ref": _file_ref(
            selected_ref, str(supply_entry["path"]), str(supply_entry["sha256"])
        ),
        "agent_profile_ref": _file_ref(
            f"{profile['agent_profile_id']}@{profile['version']}",
            _relative(root, profile_path),
            profile_hash,
        ),
        "data_policy_ref": _file_ref(
            f"{data['policy_id']}@{data['version']}", _relative(root, data_path), data_hash
        ),
        "host_policy_ref": _file_ref(
            f"{host['policy_id']}@{host['version']}", _relative(root, host_path), host_hash
        ),
        "execution_binding_ref": _file_ref(
            f"{binding['binding_id']}@r{binding['revision']}",
            _relative(root, binding_path),
            binding_hash,
        ),
        "binding": {
            key: _plain(binding[key])
            for key in ("provider", "adapter", "model", "runtime", "host")
        },
        "freshness": {
            "supply_observed_at": availability["observed_at"],
            "supply_valid_until": availability["valid_until"],
            "data_policy_valid_from": data["valid_from"],
            "data_policy_valid_until": data["valid_until"],
            "host_policy_valid_from": host["valid_from"],
            "host_policy_valid_until": host["valid_until"],
        },
        "profile_constraints": {
            "required_tool_capabilities": sorted(required_tool_capabilities),
            "required_output_contracts": sorted(required_output_contracts),
            "model": _plain(model_binding),
        },
        "effective_constraints": {
            "permissions": effective_permissions,
            "data_egress": effective_egress,
            "side_effects": effective_effects,
            "budget": effective_budget,
        },
        "required_outputs": _plain(requirement["required_artifacts"]),
        "completion_checks": _plain(
            requirement["verification_expectations"]["deterministic"]
        ),
        "safe_pause_conditions": _plain(
            next(
                decision["blocked_conditions"]
                for decision in method["action_decisions"]
                if decision.get("action_ref")
                == bundle.manifest["execution_scope"]["action_ref"]
            )
        ),
        "stop_conditions": _plain(
            next(
                decision["stop_conditions"]
                for decision in method["action_decisions"]
                if decision.get("action_ref")
                == bundle.manifest["execution_scope"]["action_ref"]
            )
        ),
        "boundaries": {
            "supply_selection": False,
            "automatic_fallback": False,
            "permission_grant": False,
            "method_decision": False,
            "claim_effect": False,
            "human_decision": False,
            "task_completion": False,
            "execution": False,
        },
    }
    errors = catalog.validate("resolved_execution_view", view)
    if errors:
        raise ExecutionViewValidationError(
            ExecutionViewIssue(
                bundle.manifest_path,
                "EXECUTION-VIEW-OUTPUT-SCHEMA",
                f"{item.pointer}: {item.message}",
            )
            for item in errors
        )
    return view


__all__ = [
    "ExecutionViewIssue",
    "ExecutionViewValidationError",
    "PinnedExecutionInput",
    "produce_resolved_execution_view",
]
