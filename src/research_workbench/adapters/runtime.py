"""Provider-neutral runtime adapter value objects.

Runtime adapters translate canonical research contracts to native agent surfaces.
They do not own project state, select scientific claims, or approve human gates.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuntimeCapabilitySnapshot:
    runtime: str
    adapter_version: str
    platform_version: str
    project_agent_root: str
    repository_skill_root: str
    supports_project_agents: bool
    supports_repository_skills: bool
    supports_explicit_skill_invocation: bool
    max_concurrent_threads: int | None
    enforceable_constraints: tuple[str, ...]
    advisory_constraints: tuple[str, ...]
    known_gaps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RuntimeAgentConfig:
    runtime: str
    profile_ref: str
    runtime_agent_name: str
    config_path: str
    sandbox_mode: str | None
    model: str | None
    model_reasoning_effort: str | None


@dataclass(frozen=True, slots=True)
class RuntimeSkillBinding:
    runtime: str
    assignment_id: str
    explicit_invocations: tuple[str, ...]
    source_paths: tuple[str, ...]
    content_hashes: tuple[str, ...]
    package_hashes: tuple[str | None, ...]
    registry_digest: str | None
