"""Codex-native mapping for canonical Agent Profiles and Skill Assignments."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Mapping

from research_workbench.artifacts.integrity import hash_directory, hash_file, resolve_within_root
from research_workbench.capability import AgentProfile, ResolvedTask
from research_workbench.tasks import TaskPacket

from .runtime import RuntimeAgentConfig, RuntimeCapabilitySnapshot, RuntimeSkillBinding


class CodexRuntimeAdapter:
    """Map contracts to native Codex files and prompts without launching a scheduler."""

    adapter_version = "0.1.0"

    def __init__(self, project_root: str | Path, *, platform_version: str = "unprobed") -> None:
        self.project_root = Path(project_root).resolve()
        self.platform_version = platform_version

    def capabilities(self) -> RuntimeCapabilitySnapshot:
        maximum: int | None = None
        config = self.project_root / ".codex" / "config.toml"
        if config.is_file():
            with config.open("rb") as stream:
                document = tomllib.load(stream)
            agents = document.get("agents", {})
            if isinstance(agents, Mapping):
                value = agents.get("max_concurrent_threads_per_session")
                if isinstance(value, int):
                    maximum = value
        return RuntimeCapabilitySnapshot(
            runtime="codex",
            adapter_version=self.adapter_version,
            platform_version=self.platform_version,
            project_agent_root=".codex/agents",
            repository_skill_root=".agents/skills",
            supports_project_agents=True,
            supports_repository_skills=True,
            supports_explicit_skill_invocation=True,
            max_concurrent_threads=maximum,
            enforceable_constraints=("sandbox_mode", "runtime_tool_availability", "session_concurrency_ceiling"),
            advisory_constraints=("task_write_scope", "claim_ceiling", "stop_conditions", "handoff_contract"),
            known_gaps=(
                "Codex sandbox_mode does not enforce repository subdirectory write scopes by itself",
                "scientific claim ceilings require artifact validation and human governance",
            ),
        )

    def resolve_agent(self, profile: AgentProfile) -> RuntimeAgentConfig:
        aliases = profile.model_policy.get("runtime_aliases", {})
        alias = None
        if isinstance(aliases, Mapping):
            candidate = aliases.get("codex")
            if isinstance(candidate, str):
                alias = candidate
        expected_name = alias or profile.agent_profile_id.replace("-", "_")
        matches: list[tuple[Path, Mapping[str, Any]]] = []
        for path in sorted((self.project_root / ".codex" / "agents").glob("*.toml")):
            with path.open("rb") as stream:
                document = tomllib.load(stream)
            if document.get("name") == expected_name:
                matches.append((path, document))
        if len(matches) != 1:
            raise ValueError(f"expected one Codex agent named {expected_name!r}, found {len(matches)}")
        path, document = matches[0]
        for field in ("name", "description", "developer_instructions"):
            if not isinstance(document.get(field), str) or not document[field].strip():
                raise ValueError(f"Codex agent {path} lacks required field {field}")
        return RuntimeAgentConfig(
            runtime="codex",
            profile_ref=f"{profile.agent_profile_id}@{profile.version}",
            runtime_agent_name=expected_name,
            config_path=path.relative_to(self.project_root).as_posix(),
            sandbox_mode=document.get("sandbox_mode") if isinstance(document.get("sandbox_mode"), str) else None,
            model=document.get("model") if isinstance(document.get("model"), str) else None,
            model_reasoning_effort=(
                document.get("model_reasoning_effort")
                if isinstance(document.get("model_reasoning_effort"), str)
                else None
            ),
        )

    def resolve_skills(self, assignment: ResolvedTask) -> RuntimeSkillBinding:
        invocations: list[str] = []
        paths: list[str] = []
        hashes: list[str] = []
        package_hashes: list[str | None] = []
        for lock in assignment.skill_lock:
            if not lock.source_locator:
                raise ValueError(f"Skill lock has no source locator: {lock.identifier}")
            path = resolve_within_root(self.project_root, lock.source_locator)
            if path is None or not path.is_file():
                raise ValueError(f"Skill source is missing or outside the project: {lock.source_locator}")
            expected = lock.content_hash.removeprefix("sha256:").lower()
            actual = hash_file(path)
            if expected != actual:
                raise ValueError(f"Skill source drift: {lock.identifier} expected={expected} actual={actual}")
            expected_package = lock.package_hash.removeprefix("sha256:").lower() if lock.package_hash else None
            if expected_package is not None:
                actual_package = hash_directory(path.parent)
                if expected_package != actual_package:
                    raise ValueError(
                        f"Skill package drift: {lock.identifier} expected={expected_package} actual={actual_package}"
                    )
            invocations.append(f"${lock.skill_id}")
            paths.append(lock.source_locator)
            hashes.append(expected)
            package_hashes.append(expected_package)
        return RuntimeSkillBinding(
            runtime="codex",
            assignment_id=assignment.assignment_id,
            explicit_invocations=tuple(invocations),
            source_paths=tuple(paths),
            content_hashes=tuple(hashes),
            package_hashes=tuple(package_hashes),
            registry_digest=assignment.registry_digest,
        )

    def render_task_prompt(
        self,
        task: TaskPacket,
        profile: AgentProfile,
        assignment: ResolvedTask,
    ) -> str:
        agent = self.resolve_agent(profile)
        binding = self.resolve_skills(assignment)
        lines = [
            f"Execute Task {task.task_id}@{task.revision} as custom agent `{agent.runtime_agent_name}`.",
            "Required Skills: " + ", ".join(binding.explicit_invocations),
            f"Skill Assignment: {assignment.assignment_id}",
            "Goal: " + task.goal,
            "Active modes: " + ", ".join(task.active_modes),
            "Input references:",
        ]
        lines.extend(f"- {ref.path} sha256:{ref.sha256}" for ref in task.input_refs)
        lines.append("Write scope:")
        lines.extend(f"- {scope}" for scope in task.write_scope)
        lines.append("Required outputs:")
        lines.extend(
            f"- {item if isinstance(item, str) else item.get('contract', '')}" for item in task.required_outputs
        )
        lines.append("Stop conditions:")
        lines.extend(f"- {condition}" for condition in task.stop_conditions)
        lines.extend(
            [
                "Do not expand the task, load unrelated Skills, or delegate unless the Task Packet explicitly permits it.",
                "Persist formal artifacts before returning. Return a compact Handoff Packet; do not return raw logs or full source text.",
            ]
        )
        return "\n".join(lines) + "\n"

    def validate_project_layout(self) -> tuple[str, ...]:
        issues: list[str] = []
        agent_root = self.project_root / ".codex" / "agents"
        skill_root = self.project_root / ".agents" / "skills"
        if not agent_root.is_dir():
            issues.append("missing .codex/agents")
        if not skill_root.is_dir():
            issues.append("missing .agents/skills")
        names: set[str] = set()
        for path in sorted(agent_root.glob("*.toml")) if agent_root.is_dir() else ():
            try:
                with path.open("rb") as stream:
                    document = tomllib.load(stream)
            except (OSError, tomllib.TOMLDecodeError) as exc:
                issues.append(f"invalid TOML {path.name}: {exc}")
                continue
            for field in ("name", "description", "developer_instructions"):
                if not isinstance(document.get(field), str) or not document[field].strip():
                    issues.append(f"{path.name} lacks {field}")
            name = document.get("name")
            if isinstance(name, str):
                if name in names:
                    issues.append(f"duplicate Codex agent name: {name}")
                names.add(name)
        for path in sorted(skill_root.glob("*/SKILL.md")) if skill_root.is_dir() else ():
            if path.stat().st_size == 0:
                issues.append(f"empty Skill file: {path.relative_to(self.project_root).as_posix()}")
        return tuple(issues)
