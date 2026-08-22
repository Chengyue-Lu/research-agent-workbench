from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from dataclasses import replace
from itertools import combinations
from typing import Iterable, Literal, Mapping

from research_workbench.capability.catalog import AcceptedSkillRegistry, SkillRegistrySelectionError
from research_workbench.capability.models import AgentProfile, SkillLock, SkillManifest
from research_workbench.contracts.common import (
    ContractError,
    PermissionPolicy,
    mapping_tuple,
    mapping_value,
    optional_string,
    parse_skill_reference,
    require_string,
    string_tuple,
)
from research_workbench.contracts.risks import ContractRisk, RiskLevel
from research_workbench.tasks.models import TaskPacket


FILESYSTEM_RANK = {
    "forbidden": 0,
    "none": 0,
    "read-only": 1,
    "worktree-write": 2,
    "workspace-write": 3,
    "unspecified": 99,
}
NETWORK_RANK = {
    "forbidden": 0,
    "none": 0,
    "search-and-fetch": 1,
    "allowed": 2,
    "unspecified": 99,
}


class ResolutionError(ValueError):
    def __init__(self, risks: Iterable[ContractRisk]):
        self.risks = tuple(risks)
        super().__init__("task resolution blocked: " + "; ".join(risk.message for risk in self.risks))


def _match_required_skills(
    task: TaskPacket,
    skills: Iterable[SkillManifest],
) -> tuple[tuple[SkillManifest, ...], tuple[ContractRisk, ...]]:
    by_id: dict[str, list[SkillManifest]] = {}
    for skill in skills:
        by_id.setdefault(skill.skill_id, []).append(skill)

    selected: list[SkillManifest] = []
    risks: list[ContractRisk] = []
    selected_keys: set[tuple[str, str]] = set()
    for index, raw_reference in enumerate(task.required_skills):
        try:
            reference = parse_skill_reference(raw_reference, f"required_skills[{index}]")
        except ContractError as exc:
            risks.append(ContractRisk("SKILL-SELECTOR-INVALID", RiskLevel.BLOCK, str(exc)))
            continue
        matches = by_id.get(reference.skill_id, [])
        if reference.version is not None:
            matches = [skill for skill in matches if skill.version == reference.version]
        if not matches:
            risks.append(
                ContractRisk(
                    "SKILL-MISSING",
                    RiskLevel.BLOCK,
                    f"required Skill is missing: {reference.identifier}",
                )
            )
            continue
        if len(matches) != 1:
            versions = ", ".join(sorted(skill.version for skill in matches))
            risks.append(
                ContractRisk(
                    "SKILL-VERSION-AMBIGUOUS",
                    RiskLevel.BLOCK,
                    f"Skill selector requires an exact version: {reference.skill_id} ({versions})",
                )
            )
            continue
        skill = matches[0]
        key = (skill.skill_id, skill.version)
        if key in selected_keys:
            risks.append(
                ContractRisk(
                    "SKILL-DUPLICATE",
                    RiskLevel.BLOCK,
                    f"Skill is selected more than once: {skill.skill_id}@{skill.version}",
                )
            )
            continue
        if any(existing.skill_id == skill.skill_id for existing in selected):
            risks.append(
                ContractRisk(
                    "SKILL-VERSION-CONFLICT",
                    RiskLevel.BLOCK,
                    f"one Task cannot load multiple versions of Skill {skill.skill_id}",
                )
            )
            continue
        selected_keys.add(key)
        selected.append(skill)
    return tuple(selected), tuple(risks)


def _assignment_identifier(
    *,
    task_id: str,
    task_revision: int,
    agent_profile: str,
    skill_lock: tuple[SkillLock, ...],
    resolved_tools: tuple[str, ...],
    effective_permissions: PermissionPolicy,
    output_contracts: tuple[str, ...],
    registry_digest: str | None,
) -> str:
    payload = {
        "task_id": task_id,
        "task_revision": task_revision,
        "agent_profile": agent_profile,
        "skill_lock": [
            {
                "skill_id": lock.skill_id,
                "version": lock.version,
                "content_hash": lock.content_hash,
                "source_locator": lock.source_locator,
                "package_hash": lock.package_hash,
            }
            for lock in skill_lock
        ],
        "resolved_tools": resolved_tools,
        "effective_permissions": {
            "filesystem": effective_permissions.filesystem,
            "network": effective_permissions.network,
            "external_write": effective_permissions.external_write,
            "allowed_roots": effective_permissions.allowed_roots,
        },
        "output_contracts": output_contracts,
        "registry_digest": registry_digest,
    }
    return "SA-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16].upper()


@dataclass(frozen=True, slots=True)
class ResolvedTask:
    schema_version: str
    assignment_id: str
    task_id: str
    task_revision: int
    agent_profile: str
    skill_lock: tuple[SkillLock, ...]
    resolved_tools: tuple[str, ...]
    effective_permissions: PermissionPolicy
    output_contracts: tuple[str, ...]
    resolution_reason: tuple[str, ...]
    registry_digest: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "ResolvedTask":
        revision = data.get("task_revision")
        if not isinstance(revision, int) or revision < 1:
            raise ContractError("task_revision", "must be a positive integer")
        assignment = cls(
            schema_version=require_string(data, "schema_version"),
            assignment_id=require_string(data, "assignment_id"),
            task_id=require_string(data, "task_id"),
            task_revision=revision,
            agent_profile=require_string(data, "agent_profile"),
            skill_lock=tuple(SkillLock.from_mapping(item) for item in mapping_tuple(data, "skill_lock")),
            resolved_tools=string_tuple(data, "resolved_tools", required=True),
            effective_permissions=PermissionPolicy.from_mapping(
                mapping_value(data, "effective_permissions", required=True)
            ),
            output_contracts=string_tuple(data, "output_contracts", required=True),
            resolution_reason=string_tuple(data, "resolution_reason", required=True),
            registry_digest=optional_string(data, "registry_digest"),
        )
        expected = _assignment_identifier(
            task_id=assignment.task_id,
            task_revision=assignment.task_revision,
            agent_profile=assignment.agent_profile,
            skill_lock=assignment.skill_lock,
            resolved_tools=assignment.resolved_tools,
            effective_permissions=assignment.effective_permissions,
            output_contracts=assignment.output_contracts,
            registry_digest=assignment.registry_digest,
        )
        if assignment.assignment_id != expected:
            raise ContractError(
                "assignment_id",
                f"does not match canonical assignment content; expected {expected}",
            )
        return assignment


def check_task_binding(
    task: TaskPacket,
    profile: AgentProfile,
    skills: Iterable[SkillManifest],
) -> list[ContractRisk]:
    risks: list[ContractRisk] = []
    skill_list = tuple(skills)
    selected, selection_risks = _match_required_skills(task, skill_list)
    risks.extend(selection_risks)
    if task.agent_profile != profile.agent_profile_id:
        risks.append(
            ContractRisk(
                "TASK-PROFILE-MISMATCH",
                RiskLevel.BLOCK,
                f"task requests {task.agent_profile!r}, loaded profile is {profile.agent_profile_id!r}",
            )
        )
    forbidden: list[str] = []
    for index, raw_reference in enumerate(task.forbidden_skills):
        try:
            reference = parse_skill_reference(raw_reference, f"forbidden_skills[{index}]")
        except ContractError as exc:
            risks.append(ContractRisk("SKILL-SELECTOR-INVALID", RiskLevel.BLOCK, str(exc)))
            continue
        if any(
            skill.skill_id == reference.skill_id
            and (reference.version is None or skill.version == reference.version)
            for skill in skill_list
        ):
            forbidden.append(reference.identifier)
    if forbidden:
        risks.append(
            ContractRisk(
                "SKILL-FORBIDDEN",
                RiskLevel.BLOCK,
                f"forbidden skills are loaded: {', '.join(sorted(forbidden))}",
            )
        )
    covered_capabilities = {capability for skill in selected for capability in skill.capabilities}
    capability_gaps = sorted(set(task.required_capabilities) - covered_capabilities)
    if capability_gaps:
        risks.append(
            ContractRisk(
                "TASK-SKILL-MISMATCH",
                RiskLevel.BLOCK,
                f"required capabilities are not covered: {', '.join(capability_gaps)}",
            )
        )
    required_tools = {tool for skill in selected for tool in skill.required_tools}
    tool_gaps = sorted(required_tools - set(profile.allowed_tool_capabilities))
    if tool_gaps:
        risks.append(
            ContractRisk(
                "SKILL-TOOL-GAP",
                RiskLevel.BLOCK,
                f"profile does not allow required tool capabilities: {', '.join(tool_gaps)}",
            )
        )
    required_outputs = {
        item if isinstance(item, str) else str(item.get("contract", ""))
        for item in task.required_outputs
    }
    provided_outputs = set(profile.output_contracts) | {
        contract for skill in selected for contract in skill.output_contracts
    }
    output_gaps = sorted(required_outputs - provided_outputs)
    if output_gaps:
        risks.append(
            ContractRisk(
                "TASK-OUTPUT-GAP",
                RiskLevel.BLOCK,
                f"required output contracts are not covered: {', '.join(output_gaps)}",
            )
        )
    for skill in selected:
        if task.active_modes and not set(task.active_modes) & set(skill.applies_to_modes):
            risks.append(
                ContractRisk(
                    "SKILL-MODE-MISMATCH",
                    RiskLevel.BLOCK,
                    f"skill {skill.skill_id!r} applies to none of the active modes",
                )
            )
        conflicts = sorted(
            incompatible
            for incompatible in skill.incompatible_with
            if any(loaded.skill_id == incompatible for loaded in skill_list)
        )
        if conflicts:
            risks.append(
                ContractRisk(
                    "SKILL-CONFLICT",
                    RiskLevel.BLOCK,
                    f"skill {skill.skill_id!r} conflicts with: {', '.join(conflicts)}",
                )
            )
    if task.permissions.external_write and not profile.permission_ceiling.external_write:
        risks.append(
            ContractRisk(
                "TASK-PERMISSION-ESCALATION",
                RiskLevel.BLOCK,
                "task requests external write but the profile forbids it",
            )
        )
    if task.delegation.allowed and not profile.delegation_allowed:
        risks.append(
            ContractRisk(
                "TASK-DELEGATION-ESCALATION",
                RiskLevel.BLOCK,
                "task allows delegation but the profile forbids it",
            )
        )
    return risks


def _narrowest(values: Iterable[str], ranks: Mapping[str, int], field: str) -> str:
    candidates = [value for value in values if value != "unspecified"]
    unknown = sorted({value for value in candidates if value not in ranks})
    if unknown:
        raise ContractError(field, f"has unknown permission values: {', '.join(unknown)}")
    if not candidates:
        return "unspecified"
    return min(candidates, key=lambda value: ranks[value])


def _effective_permissions(
    task: TaskPacket,
    profile: AgentProfile,
    skills: Iterable[SkillManifest],
) -> PermissionPolicy:
    policies = [task.permissions, profile.permission_ceiling, *(skill.permission_ceiling for skill in skills)]
    nonempty_roots = [set(policy.allowed_roots) for policy in policies if policy.allowed_roots]
    roots: set[str] = set()
    if nonempty_roots:
        candidates = set().union(*nonempty_roots)
        roots = {
            candidate
            for candidate in candidates
            if all(
                any(candidate == ceiling or candidate.startswith(ceiling.rstrip("/") + "/") for ceiling in ceiling_set)
                for ceiling_set in nonempty_roots
            )
        }
        roots = {
            candidate
            for candidate in roots
            if not any(
                other != candidate and other.startswith(candidate.rstrip("/") + "/")
                for other in roots
            )
        }
    return PermissionPolicy(
        filesystem=_narrowest((policy.filesystem for policy in policies), FILESYSTEM_RANK, "filesystem"),
        network=_narrowest((policy.network for policy in policies), NETWORK_RANK, "network"),
        external_write=all(policy.external_write for policy in policies),
        allowed_roots=tuple(sorted(roots)),
    )


def resolve_task(
    task: TaskPacket,
    profile: AgentProfile,
    skills: Iterable[SkillManifest],
    *,
    registry_digest: str | None = None,
) -> ResolvedTask:
    skill_list = tuple(skills)
    risks = check_task_binding(task, profile, skill_list)
    blockers = tuple(risk for risk in risks if risk.level == RiskLevel.BLOCK)
    if blockers:
        raise ResolutionError(blockers)
    selected, _ = _match_required_skills(task, skill_list)
    locks = tuple(
        SkillLock(
            skill_id=skill.skill_id,
            version=skill.version,
            content_hash=skill.source_content_hash,
            source_locator=skill.source_locator,
            package_hash=skill.source_package_hash,
        )
        for skill in selected
    )
    tools = tuple(sorted({tool for skill in selected for tool in skill.required_tools}))
    outputs = tuple(
        sorted(
            set(profile.output_contracts)
            | {contract for skill in selected for contract in skill.output_contracts}
        )
    )
    effective_permissions = _effective_permissions(task, profile, selected)
    if task.write_scope and FILESYSTEM_RANK.get(effective_permissions.filesystem, 99) < FILESYSTEM_RANK["worktree-write"]:
        raise ResolutionError(
            [
                ContractRisk(
                    "TASK-PERMISSION-ESCALATION",
                    RiskLevel.BLOCK,
                    "task has write_scope but the effective filesystem permission is read-only or forbidden",
                )
            ]
        )
    if effective_permissions.allowed_roots:
        outside = []
        for scope in task.write_scope:
            anchor = scope.replace("\\", "/").split("*", 1)[0].split("?", 1)[0].rstrip("/")
            if not any(
                anchor == root or anchor.startswith(root.rstrip("/") + "/")
                for root in effective_permissions.allowed_roots
            ):
                outside.append(scope)
        if outside:
            raise ResolutionError(
                [
                    ContractRisk(
                        "TASK-PERMISSION-ESCALATION",
                        RiskLevel.BLOCK,
                        "write scopes exceed effective allowed roots: " + ", ".join(outside),
                    )
                ]
            )
    assignment_id = _assignment_identifier(
        task_id=task.task_id,
        task_revision=task.revision,
        agent_profile=f"{profile.agent_profile_id}@{profile.version}",
        skill_lock=locks,
        resolved_tools=tools,
        effective_permissions=effective_permissions,
        output_contracts=outputs,
        registry_digest=registry_digest,
    )
    return ResolvedTask(
        schema_version="0.1.0",
        assignment_id=assignment_id,
        task_id=task.task_id,
        task_revision=task.revision,
        agent_profile=f"{profile.agent_profile_id}@{profile.version}",
        skill_lock=locks,
        resolved_tools=tools,
        effective_permissions=effective_permissions,
        output_contracts=outputs,
        resolution_reason=(
            "all required capabilities are covered",
            "no forbidden or incompatible skill is loaded",
            "permissions are the intersection of task, profile, and selected skills",
        ),
        registry_digest=registry_digest,
    )


CONTEXT_COST_RANK = {"low": 1, "medium": 2, "high": 4, "extreme": 16}


def _is_forbidden_by_task(skill: SkillManifest, task: TaskPacket) -> bool:
    for index, raw_reference in enumerate(task.forbidden_skills):
        reference = parse_skill_reference(raw_reference, f"forbidden_skills[{index}]")
        if reference.skill_id == skill.skill_id and (
            reference.version is None or reference.version == skill.version
        ):
            return True
    return False


def _select_minimal_skills(
    task: TaskPacket,
    profile: AgentProfile,
    registry: AcceptedSkillRegistry,
) -> tuple[SkillManifest, ...]:
    candidates = [
        skill
        for skill in registry.active_manifests
        if not _is_forbidden_by_task(skill, task)
        and (not task.active_modes or set(task.active_modes) & set(skill.applies_to_modes))
        and set(skill.required_tools) <= set(profile.allowed_tool_capabilities)
    ]
    solutions: list[tuple[tuple[int, int], tuple[SkillManifest, ...]]] = []
    required_capabilities = set(task.required_capabilities)
    required_outputs = {
        item if isinstance(item, str) else str(item.get("contract", ""))
        for item in task.required_outputs
    }
    for size in range(1, min(3, len(candidates)) + 1):
        for selected in combinations(candidates, size):
            if required_capabilities - {cap for skill in selected for cap in skill.capabilities}:
                continue
            provided_outputs = set(profile.output_contracts) | {
                output for skill in selected for output in skill.output_contracts
            }
            if required_outputs - provided_outputs:
                continue
            ids = {skill.skill_id for skill in selected}
            if any(set(skill.incompatible_with) & ids for skill in selected):
                continue
            cost = sum(CONTEXT_COST_RANK.get(skill.context_cost.get("instructions", "high"), 8) for skill in selected)
            solutions.append(((size, cost), selected))
        if solutions:
            break
    if not solutions:
        raise ResolutionError(
            [ContractRisk("SKILL-MISSING", RiskLevel.BLOCK, "accepted registry cannot cover the task contracts")]
        )
    best_score = min(score for score, _ in solutions)
    best = [selected for score, selected in solutions if score == best_score]
    if len(best) != 1:
        choices = ["+".join(skill.skill_id for skill in selected) for selected in best]
        raise ResolutionError(
            [
                ContractRisk(
                    "SKILL-AMBIGUOUS",
                    RiskLevel.BLOCK,
                    "equivalent accepted Skill sets require an explicit human choice: " + ", ".join(sorted(choices)),
                )
            ]
        )
    return best[0]


def resolve_task_from_registry(
    task: TaskPacket,
    profile: AgentProfile,
    registry: AcceptedSkillRegistry,
    *,
    allow_auto_select: bool = False,
    resolution_purpose: Literal["new-assignment", "historical-replay"] = "new-assignment",
) -> ResolvedTask:
    if resolution_purpose == "historical-replay" and allow_auto_select:
        raise ResolutionError(
            [
                ContractRisk(
                    "SKILL-REPLAY-AUTOSELECT-FORBIDDEN",
                    RiskLevel.BLOCK,
                    "historical replay requires explicit exact Skill versions",
                )
            ]
        )
    if task.required_skills:
        try:
            selected = registry.require(task.required_skills, purpose=resolution_purpose)
        except SkillRegistrySelectionError as exc:
            raise ResolutionError([ContractRisk(exc.code, RiskLevel.BLOCK, str(exc))]) from exc
        resolved_task = replace(
            task,
            required_skills=tuple(f"{skill.skill_id}@{skill.version}" for skill in selected),
        )
    elif allow_auto_select:
        selected = _select_minimal_skills(task, profile, registry)
        resolved_task = replace(
            task,
            required_skills=tuple(f"{skill.skill_id}@{skill.version}" for skill in selected),
        )
    else:
        raise ResolutionError(
            [ContractRisk("SKILL-IMPLICIT-CRITICAL", RiskLevel.BLOCK, "Task Packet does not explicitly name Skills")]
        )
    assignment = resolve_task(resolved_task, profile, selected, registry_digest=registry.digest)
    return replace(
        assignment,
        resolution_reason=assignment.resolution_reason
        + (f"skill selection purpose: {resolution_purpose}",),
    )
