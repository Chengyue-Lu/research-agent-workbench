"""Pure runtime-facing SkillReleaseProjection → Supply fact checks.

This module intentionally imports neither Lifecycle nor Evaluation.  It can be
used by both maintainer validation and the explicit Runtime Bundle loader.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import PurePosixPath
from typing import Any, Mapping


_FILESYSTEM_ORDER = {
    "forbidden": 0,
    "read-only": 1,
    "worktree-write": 2,
    "workspace-write": 3,
}
_NETWORK_ORDER = {"forbidden": 0, "search-and-fetch": 1, "allowed": 2}


def _string_set(value: object) -> set[str] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None
    if not all(isinstance(item, str) for item in value):
        return None
    return set(value)


def _path_within(candidate: str, ceiling: str) -> bool:
    candidate_path = PurePosixPath(candidate.replace("\\", "/"))
    ceiling_path = PurePosixPath(ceiling.replace("\\", "/"))
    return candidate_path == ceiling_path or ceiling_path in candidate_path.parents


def projection_reference(projection: Mapping[str, Any]) -> str:
    return f"{projection.get('projection_id')}@{projection.get('projection_version')}"


def projection_is_runtime_eligible(projection: Mapping[str, Any]) -> bool:
    eligibility = projection.get("eligibility")
    boundaries = projection.get("boundaries")
    return bool(
        isinstance(eligibility, Mapping)
        and eligibility.get("state") == "eligible"
        and "new-binding" in eligibility.get("scopes", ())
        and isinstance(boundaries, Mapping)
        and boundaries
        and all(value is False for value in boundaries.values())
    )


def _permission_within_ceiling(
    required: object, ceiling: object
) -> bool:
    if not isinstance(required, Mapping) or not isinstance(ceiling, Mapping):
        return False
    required_filesystem = required.get("filesystem")
    ceiling_filesystem = ceiling.get("filesystem")
    required_network = required.get("network")
    ceiling_network = ceiling.get("network")
    required_roots = _string_set(required.get("allowed_roots"))
    ceiling_roots = _string_set(ceiling.get("allowed_roots"))
    if (
        required_filesystem not in _FILESYSTEM_ORDER
        or ceiling_filesystem not in _FILESYSTEM_ORDER
        or required_network not in _NETWORK_ORDER
        or ceiling_network not in _NETWORK_ORDER
        or required_roots is None
        or ceiling_roots is None
    ):
        return False
    required_external = required.get("external_write") in {True, "allowed"}
    ceiling_external = ceiling.get("external_write") in {True, "allowed"}
    return (
        _FILESYSTEM_ORDER[str(required_filesystem)]
        <= _FILESYSTEM_ORDER[str(ceiling_filesystem)]
        and _NETWORK_ORDER[str(required_network)]
        <= _NETWORK_ORDER[str(ceiling_network)]
        and (not required_external or ceiling_external)
        and all(
            any(_path_within(required_root, ceiling_root) for ceiling_root in ceiling_roots)
            for required_root in required_roots
        )
    )


def _data_egress_within_ceiling(actual: object, ceiling: object) -> bool:
    if not isinstance(actual, Mapping) or not isinstance(ceiling, Mapping):
        return False
    actual_allowed = _string_set(actual.get("allowed_payloads"))
    actual_forbidden = _string_set(actual.get("forbidden_payloads"))
    ceiling_allowed = _string_set(ceiling.get("allowed_payloads"))
    ceiling_forbidden = _string_set(ceiling.get("forbidden_payloads"))
    if any(
        value is None
        for value in (
            actual_allowed,
            actual_forbidden,
            ceiling_allowed,
            ceiling_forbidden,
        )
    ):
        return False
    assert actual_allowed is not None
    assert actual_forbidden is not None
    assert ceiling_allowed is not None
    assert ceiling_forbidden is not None
    if actual_allowed & ceiling_forbidden or not ceiling_forbidden <= actual_forbidden:
        return False
    if ceiling.get("policy") == "forbidden":
        return actual.get("policy") == "forbidden" and not actual_allowed
    return (
        actual.get("policy") in {"forbidden", "allowlisted-only"}
        and actual_allowed <= ceiling_allowed
    )


def _side_effects_within_ceiling(actual: object, ceiling: object) -> bool:
    if not isinstance(actual, Mapping) or not isinstance(ceiling, Mapping):
        return False
    actual_effects = _string_set(actual.get("allowed_effects"))
    ceiling_effects = _string_set(ceiling.get("allowed_effects"))
    if actual_effects is None or ceiling_effects is None:
        return False
    if ceiling.get("policy") == "none":
        return actual.get("policy") == "none" and not actual_effects
    return (
        actual.get("policy") in {"none", "allowlisted-only"}
        and actual_effects <= ceiling_effects
    )


def projection_supply_fact_issues(
    projection: Mapping[str, Any],
    supply_report: Mapping[str, Any],
) -> tuple[tuple[str, str], ...]:
    """Return deterministic drift findings without granting selection authority."""

    issues: list[tuple[str, str]] = []
    release = projection.get("release")
    contract = projection.get("runtime_contract")
    identity = supply_report.get("supply_identity")
    if not all(isinstance(item, Mapping) for item in (release, contract, identity)):
        return (("SKILL-PROJECTION-SUPPLY-SHAPE", "projection and Supply facts must be objects"),)
    assert isinstance(release, Mapping)
    assert isinstance(contract, Mapping)
    assert isinstance(identity, Mapping)

    expected_identity = (
        release.get("skill_id"),
        release.get("skill_version"),
        str(release.get("content_hash", "")).removeprefix("sha256:").lower(),
    )
    actual_identity = (
        identity.get("implementation_ref"),
        identity.get("implementation_version"),
        str(identity.get("content_hash", "")).removeprefix("sha256:").lower(),
    )
    raw_components = identity.get("components")
    components = (
        tuple(raw_components)
        if isinstance(raw_components, Sequence)
        and not isinstance(raw_components, (str, bytes))
        else ()
    )
    skill_components = [
        component
        for component in components
        if isinstance(component, Mapping) and component.get("component_kind") == "skill"
    ]
    component_identities = {
        (
            component.get("component_ref"),
            component.get("version"),
            str(component.get("content_hash", "")).removeprefix("sha256:").lower(),
        )
        for component in skill_components
    }
    if (
        identity.get("supply_kind") != "skill"
        or actual_identity != expected_identity
        or component_identities != {expected_identity}
        or len(skill_components) != 1
    ):
        issues.append(
            (
                "SKILL-PROJECTION-SUPPLY-IDENTITY-DRIFT",
                "Skill Supply identity/component must exactly match the projected Release",
            )
        )

    dependencies = contract.get("dependencies")
    required_tools: set[str] | None = None
    optional_tools: set[str] | None = None
    if isinstance(dependencies, Mapping):
        required_tools = _string_set(dependencies.get("required_tools"))
        optional_tools = _string_set(dependencies.get("optional_tools"))
    allowed_tools = (required_tools or set()) | (optional_tools or set())
    supplied_tools = {
        str(component.get("component_ref"))
        for component in components
        if isinstance(component, Mapping) and component.get("component_kind") == "tool"
    }
    invalid_components = [
        component
        for component in components
        if not isinstance(component, Mapping)
        or (
            component.get("component_kind") != "skill"
            and not (
                component.get("component_kind") == "tool"
                and component.get("component_ref") in allowed_tools
            )
        )
    ]
    if (
        required_tools is None
        or optional_tools is None
        or invalid_components
        or not required_tools <= supplied_tools
    ):
        issues.append(
            (
                "SKILL-PROJECTION-SUPPLY-COMPONENT-DRIFT",
                "Skill Supply must contain every required Tool and no component outside projected dependencies",
            )
        )

    copied_facts = (
        ("provided_capabilities", "provided_capabilities"),
        ("supported_inputs", "supported_inputs"),
        ("supported_outputs", "supported_outputs"),
    )
    copied_values = [
        (_string_set(supply_report.get(report_field)), _string_set(contract.get(contract_field)))
        for report_field, contract_field in copied_facts
    ]
    if any(actual is None or expected is None or actual != expected for actual, expected in copied_values):
        issues.append(
            (
                "SKILL-PROJECTION-SUPPLY-CONTRACT-DRIFT",
                "Skill Supply capability/input/output facts must equal the projection",
            )
        )
    if not _permission_within_ceiling(
        supply_report.get("required_permissions"), contract.get("permission_ceiling")
    ):
        issues.append(
            (
                "SKILL-PROJECTION-SUPPLY-PERMISSION-EXCEEDED",
                "Skill Supply required permissions exceed the projection ceiling",
            )
        )
    if not _data_egress_within_ceiling(
        supply_report.get("data_egress_behavior"),
        contract.get("data_egress_ceiling"),
    ):
        issues.append(
            (
                "SKILL-PROJECTION-SUPPLY-EGRESS-EXCEEDED",
                "Skill Supply data egress exceeds the projection ceiling",
            )
        )
    if not _side_effects_within_ceiling(
        supply_report.get("side_effects"), contract.get("side_effect_ceiling")
    ):
        issues.append(
            (
                "SKILL-PROJECTION-SUPPLY-EFFECT-EXCEEDED",
                "Skill Supply side effects exceed the projection ceiling",
            )
        )
    return tuple(issues)


__all__ = [
    "projection_is_runtime_eligible",
    "projection_reference",
    "projection_supply_fact_issues",
]
