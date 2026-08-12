from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from research_workbench.capability.models import AgentProfile, SkillLock, SkillManifest
from research_workbench.contracts.common import PermissionPolicy
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


@dataclass(frozen=True, slots=True)
class ResolvedTask:
    task_id: str
    task_revision: int
    agent_profile: str
    skill_lock: tuple[SkillLock, ...]
    resolved_tools: tuple[str, ...]
    effective_permissions: PermissionPolicy
    output_contracts: tuple[str, ...]
    resolution_reason: tuple[str, ...]


def check_task_binding(
    task: TaskPacket,
    profile: AgentProfile,
    skills: Iterable[SkillManifest],
) -> list[ContractRisk]:
    risks: list[ContractRisk] = []
    skills_by_id = {skill.skill_id: skill for skill in skills}
    if task.agent_profile != profile.agent_profile_id:
        risks.append(
            ContractRisk(
                "TASK-PROFILE-MISMATCH",
                RiskLevel.BLOCK,
                f"task requests {task.agent_profile!r}, loaded profile is {profile.agent_profile_id!r}",
            )
        )
    missing = sorted(set(task.required_skills) - set(skills_by_id))
    if missing:
        risks.append(
            ContractRisk("SKILL-MISSING", RiskLevel.BLOCK, f"required skills are missing: {', '.join(missing)}")
        )
    forbidden = sorted(set(task.forbidden_skills) & set(skills_by_id))
    if forbidden:
        risks.append(
            ContractRisk("SKILL-FORBIDDEN", RiskLevel.BLOCK, f"forbidden skills are loaded: {', '.join(forbidden)}")
        )
    selected = [skills_by_id[item] for item in task.required_skills if item in skills_by_id]
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
        conflicts = sorted(set(skill.incompatible_with) & set(skills_by_id))
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
        raise ValueError(f"unknown {field} permission values: {', '.join(unknown)}")
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
) -> ResolvedTask:
    skill_list = tuple(skills)
    risks = check_task_binding(task, profile, skill_list)
    blockers = tuple(risk for risk in risks if risk.level == RiskLevel.BLOCK)
    if blockers:
        raise ResolutionError(blockers)
    selected_by_id = {skill.skill_id: skill for skill in skill_list}
    selected = tuple(selected_by_id[skill_id] for skill_id in task.required_skills)
    locks = tuple(
        SkillLock(
            skill_id=skill.skill_id,
            version=skill.version,
            content_hash=skill.source_content_hash,
            source_locator=skill.source_locator,
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
    return ResolvedTask(
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
    )
