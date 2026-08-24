from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from research_workbench.capability.requirements import CapabilityRequirement
from research_workbench.capability.resolver import permission_policy_covers
from research_workbench.contracts.common import (
    ContractError,
    PermissionPolicy,
    mapping_value,
    require_string,
    string_tuple,
)


CHECK_ORDER = (
    "capability",
    "inputs",
    "outputs",
    "artifacts",
    "permission",
    "data-egress",
    "side-effects",
    "conformance-evidence",
    "availability",
    "skill-runtime-eligibility",
)

SUPPLY_KINDS = {"procedure", "tool", "adapter-provider", "skill"}


def _mapping_tuple(data: Mapping[str, Any], key: str) -> tuple[Mapping[str, Any], ...]:
    value = data.get(key)
    if not isinstance(value, list):
        raise ContractError(key, "must be an array")
    result: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ContractError(f"{key}[{index}]", "must be an object")
        result.append(item)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class SupplyComponent:
    component_kind: str
    component_ref: str
    version: str
    content_hash: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SupplyComponent":
        return cls(
            component_kind=require_string(data, "component_kind"),
            component_ref=require_string(data, "component_ref"),
            version=require_string(data, "version"),
            content_hash=require_string(data, "content_hash"),
        )


@dataclass(frozen=True, slots=True)
class SupplyIdentity:
    supply_kind: str
    implementation_ref: str
    implementation_version: str
    content_hash: str
    components: tuple[SupplyComponent, ...]
    skill_lifecycle_ref: str | None = None
    runtime_eligibility_ref: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "SupplyIdentity":
        supply_kind = require_string(data, "supply_kind")
        skill_lifecycle_ref = data.get("skill_lifecycle_ref")
        runtime_eligibility_ref = data.get("runtime_eligibility_ref")
        if skill_lifecycle_ref is not None and not isinstance(skill_lifecycle_ref, str):
            raise ContractError("skill_lifecycle_ref", "must be a string")
        if runtime_eligibility_ref is not None and not isinstance(runtime_eligibility_ref, str):
            raise ContractError("runtime_eligibility_ref", "must be a string")
        if supply_kind not in SUPPLY_KINDS:
            raise ContractError(
                "supply_kind",
                f"must be one of {sorted(SUPPLY_KINDS)}; no-Skill is a binding disposition, not a Supply",
            )
        if supply_kind == "skill":
            if not skill_lifecycle_ref:
                raise ContractError(
                    "skill_lifecycle_ref", "is required for a Skill Supply"
                )
            if not runtime_eligibility_ref:
                raise ContractError(
                    "runtime_eligibility_ref", "is required for a Skill Supply"
                )
        elif skill_lifecycle_ref is not None or runtime_eligibility_ref is not None:
            raise ContractError(
                "supply_identity",
                "Skill lifecycle and runtime eligibility references are forbidden for non-Skill Supplies",
            )
        return cls(
            supply_kind=supply_kind,
            implementation_ref=require_string(data, "implementation_ref"),
            implementation_version=require_string(data, "implementation_version"),
            content_hash=require_string(data, "content_hash"),
            components=tuple(
                SupplyComponent.from_mapping(item)
                for item in _mapping_tuple(data, "components")
            ),
            skill_lifecycle_ref=skill_lifecycle_ref,
            runtime_eligibility_ref=runtime_eligibility_ref,
        )


@dataclass(frozen=True, slots=True)
class CapabilitySupplyReport:
    schema_version: str
    report_id: str
    version: str
    observation_scope: str
    supply_identity: SupplyIdentity
    provided_capabilities: tuple[str, ...]
    supported_inputs: tuple[str, ...]
    supported_outputs: tuple[str, ...]
    produced_artifacts: tuple[str, ...]
    required_permissions: Mapping[str, Any]
    data_egress_behavior: Mapping[str, Any]
    side_effects: Mapping[str, Any]
    conformance_evidence: tuple[Mapping[str, Any], ...]
    availability: Mapping[str, Any]
    limits: Mapping[str, Any]
    limitations: tuple[str, ...]

    @property
    def reference(self) -> str:
        return f"{self.report_id}@{self.version}"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "CapabilitySupplyReport":
        return cls(
            schema_version=require_string(data, "schema_version"),
            report_id=require_string(data, "report_id"),
            version=require_string(data, "version"),
            observation_scope=require_string(data, "observation_scope"),
            supply_identity=SupplyIdentity.from_mapping(
                mapping_value(data, "supply_identity", required=True)
            ),
            provided_capabilities=string_tuple(
                data, "provided_capabilities", required=True
            ),
            supported_inputs=string_tuple(data, "supported_inputs", required=True),
            supported_outputs=string_tuple(data, "supported_outputs", required=True),
            produced_artifacts=string_tuple(data, "produced_artifacts", required=True),
            required_permissions=dict(
                mapping_value(data, "required_permissions", required=True)
            ),
            data_egress_behavior=dict(
                mapping_value(data, "data_egress_behavior", required=True)
            ),
            side_effects=dict(mapping_value(data, "side_effects", required=True)),
            conformance_evidence=_mapping_tuple(data, "conformance_evidence"),
            availability=dict(mapping_value(data, "availability", required=True)),
            limits=dict(mapping_value(data, "limits", required=True)),
            limitations=string_tuple(data, "limitations", required=True),
        )


@dataclass(frozen=True, slots=True)
class SupplyAssessment:
    supply_report_ref: str
    checks: tuple[Mapping[str, Any], ...]
    eligible: bool

    def to_mapping(self) -> dict[str, Any]:
        return {
            "supply_report_ref": self.supply_report_ref,
            "checks": [dict(check) for check in self.checks],
            "eligible": self.eligible,
        }


def _check(name: str, status: str, reason: str) -> dict[str, str]:
    return {"check": name, "status": status, "reason": reason}


def _permission_check(requirement: CapabilityRequirement, report: CapabilitySupplyReport) -> dict[str, str]:
    ceiling = requirement.constraints.permission_ceiling
    ceiling_policy = PermissionPolicy(
        filesystem=ceiling.filesystem,
        network=ceiling.network,
        external_write=ceiling.external_write,
        allowed_roots=(),
    )
    supply_policy = PermissionPolicy.from_mapping(report.required_permissions)
    valid = permission_policy_covers(ceiling_policy, supply_policy)
    return _check(
        "permission",
        "pass" if valid else "fail",
        "Supply permissions are within the Requirement ceiling."
        if valid
        else "Supply permissions exceed or are incomparable with the Requirement ceiling.",
    )


def _data_egress_check(requirement: CapabilityRequirement, report: CapabilitySupplyReport) -> dict[str, str]:
    ceiling = requirement.constraints.data_egress
    supply = report.data_egress_behavior
    supply_policy = str(supply.get("policy"))
    supply_allowed = set(supply.get("allowed_payloads", []))
    ceiling_allowed = set(ceiling.allowed_payloads)
    ceiling_forbidden = set(ceiling.forbidden_payloads)
    valid = not (supply_allowed & ceiling_forbidden)
    if ceiling.policy == "forbidden":
        valid = valid and supply_policy == "forbidden" and not supply_allowed
    else:
        valid = valid and supply_policy in {"forbidden", "allowlisted-only"}
        valid = valid and supply_allowed <= ceiling_allowed
    return _check(
        "data-egress",
        "pass" if valid else "fail",
        "Supply data-egress behavior is within the Requirement ceiling."
        if valid
        else "Supply data-egress behavior exceeds the Requirement ceiling.",
    )


def _side_effect_check(requirement: CapabilityRequirement, report: CapabilitySupplyReport) -> dict[str, str]:
    ceiling = requirement.constraints.side_effects
    supply = report.side_effects
    effects = set(supply.get("allowed_effects", []))
    valid = effects <= set(ceiling.allowed_effects)
    if ceiling.policy == "none":
        valid = valid and supply.get("policy") == "none" and not effects
    else:
        valid = valid and supply.get("policy") in {"none", "allowlisted-only"}
    return _check(
        "side-effects",
        "pass" if valid else "fail",
        "Supply side effects are within the Requirement ceiling."
        if valid
        else "Supply side effects exceed the Requirement ceiling.",
    )


def _qualification_check(
    report: CapabilitySupplyReport,
    *,
    qualification: str,
) -> dict[str, str]:
    scope = report.availability.get("scope")
    scope_mapping = scope if isinstance(scope, Mapping) else {}
    scope_kind = str(scope_mapping.get("scope_kind"))
    status = str(report.availability.get("status"))
    if qualification == "runtime-execution":
        if (
            report.observation_scope == "synthetic-bounded-fixture"
            or scope_kind == "fixture-only"
        ):
            return _check(
                "availability",
                "fail",
                "Synthetic or fixture-only Supply facts can qualify structural replay only.",
            )
        if status == "available":
            return _check(
                "availability",
                "pass",
                f"Supply reports non-fixture availability in scope {scope_kind!r}; final Runtime admission remains external.",
            )
        return _check(
            "availability",
            "fail" if status == "unavailable" else "unknown",
            f"Supply reports availability status {status!r} in scope {scope_kind!r}.",
        )
    if status == "available":
        return _check(
            "availability",
            "pass",
            f"Supply reports availability in scope {scope_kind!r}.",
        )
    return _check(
        "availability",
        "fail" if status == "unavailable" else "unknown",
        f"Supply reports availability status {status!r} in scope {scope_kind!r}.",
    )


def assess_supply(
    requirement: CapabilityRequirement,
    report: CapabilitySupplyReport,
    *,
    evaluated_at: object | None = None,
    qualification: str = "structural-replay",
    evidence_check: Callable[[SupplyIdentity, Mapping[str, Any], str], str] | None = None,
    runtime_eligibility_check: Callable[[str, str], bool] | None = None,
) -> SupplyAssessment:
    if qualification not in {"structural-replay", "runtime-execution"}:
        raise ValueError(f"unknown capability qualification: {qualification}")
    # Kept as a compatibility input for persisted Resolution callers. Phase B
    # records the timestamp but does not use it as an availability admission
    # clock; real execution freshness belongs to the Runtime producer/consumer.
    _ = evaluated_at
    required_inputs = set(requirement.required_inputs)
    required_outputs = set(requirement.required_outputs)
    supported_inputs = set(report.supported_inputs)
    supported_outputs = set(report.supported_outputs)
    produced_artifacts = set(report.produced_artifacts)
    eligible_evidence_class = "live" if qualification == "runtime-execution" else "deterministic"
    relevant_evidence = [
        item
        for item in report.conformance_evidence
        if item.get("evidence_class") == eligible_evidence_class
    ]
    verified = [
        evidence_check(report.supply_identity, item, requirement.requirement_id)
        if evidence_check is not None
        else "unknown"
        for item in relevant_evidence
    ]
    if any(status == "fail" for status in verified):
        conformance_status = "fail"
        conformance_reason = "A typed conformance artifact fails or does not match its declared subject."
    elif any(status == "pass" for status in verified):
        conformance_status = "pass"
        conformance_reason = "A typed, hash-bound conformance artifact proves the required capability."
    else:
        conformance_status = "unknown"
        conformance_reason = "No typed, verified conformance artifact proves the required capability."
    if report.supply_identity.supply_kind == "skill":
        lifecycle_ref = report.supply_identity.skill_lifecycle_ref
        eligibility_ref = report.supply_identity.runtime_eligibility_ref
        lifecycle_reports_eligible = bool(
            runtime_eligibility_check
            and lifecycle_ref
            and eligibility_ref
            and runtime_eligibility_check(lifecycle_ref, eligibility_ref)
        )
        if qualification == "structural-replay":
            skill_status = "not-applicable"
            skill_reason = "Structural replay does not create a new Skill binding."
        elif lifecycle_reports_eligible:
            skill_status = "pass"
            skill_reason = "The caller verified lifecycle evidence and Human-decision provenance for this new binding."
        else:
            skill_status = "unknown"
            skill_reason = "Skill new-binding eligibility is absent or unverified and remains fail-closed."
    else:
        skill_status = "not-applicable"
        skill_reason = "This Core supply is not a Skill and needs no Skill lifecycle decision."

    checks = (
        _check(
            "capability",
            "pass" if requirement.requirement_id in report.provided_capabilities else "fail",
            "Supply reports the required capability."
            if requirement.requirement_id in report.provided_capabilities
            else "Supply does not report the required capability.",
        ),
        _check(
            "inputs",
            "pass" if required_inputs <= supported_inputs else "fail",
            "Supply covers every required input class."
            if required_inputs <= supported_inputs
            else f"Supply misses input classes: {sorted(required_inputs - supported_inputs)}.",
        ),
        _check(
            "outputs",
            "pass" if required_outputs <= supported_outputs else "fail",
            "Supply covers every required output class."
            if required_outputs <= supported_outputs
            else f"Supply misses output classes: {sorted(required_outputs - supported_outputs)}.",
        ),
        _check(
            "artifacts",
            "pass" if set(requirement.required_artifacts) <= produced_artifacts else "fail",
            "Supply produces every required artifact class."
            if set(requirement.required_artifacts) <= produced_artifacts
            else f"Supply misses artifact classes: {sorted(set(requirement.required_artifacts) - produced_artifacts)}.",
        ),
        _permission_check(requirement, report),
        _data_egress_check(requirement, report),
        _side_effect_check(requirement, report),
        _check("conformance-evidence", conformance_status, conformance_reason),
        _qualification_check(
            report,
            qualification=qualification,
        ),
        _check("skill-runtime-eligibility", skill_status, skill_reason),
    )
    eligible = all(item["status"] in {"pass", "not-applicable"} for item in checks)
    return SupplyAssessment(report.reference, checks, eligible)


def resolve_status(assessments: Sequence[SupplyAssessment]) -> tuple[str, str | None]:
    eligible = [item.supply_report_ref for item in assessments if item.eligible]
    if len(eligible) == 1:
        return "satisfied", eligible[0]
    if len(eligible) > 1:
        return "ambiguous", None
    ceiling_checks = {"permission", "data-egress", "side-effects"}
    if any(
        check["check"] in ceiling_checks and check["status"] == "fail"
        for assessment in assessments
        for check in assessment.checks
    ):
        return "blocked", None
    return "gap", None
