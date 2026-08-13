"""Small, method-neutral research objects.

These objects intentionally contain no model-provider, agent-runtime, or
discipline-specific fields. Method packs can reference them without changing
their identity and provenance rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ObjectRef:
    object_id: str
    revision: int
    sha256: str | None = None

    @property
    def pinned(self) -> bool:
        return self.sha256 is not None


@dataclass(slots=True)
class ResearchObject:
    object_id: str
    schema_version: str = "0.1.0"
    object_type: str = field(init=False, default="research_object")
    revision: int = 1
    status: str = "draft"
    content_hash: str | None = None
    supersedes: ObjectRef | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ref(self) -> ObjectRef:
        return ObjectRef(self.object_id, self.revision, self.content_hash)


@dataclass(slots=True)
class Question(ResearchObject):
    object_type: str = field(init=False, default="question")
    text: str = ""
    scope: list[str] = field(default_factory=list)
    known_ambiguities: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Proposition(ResearchObject):
    object_type: str = field(init=False, default="proposition")
    statement: str = ""
    assumptions: list[str] = field(default_factory=list)
    applicability: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Method(ResearchObject):
    object_type: str = field(init=False, default="method")
    kind: str = "unspecified"
    spec_ref: ObjectRef | None = None
    version: str = "0.1.0"
    limitations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Run(ResearchObject):
    object_type: str = field(init=False, default="run")
    method_ref: ObjectRef | None = None
    input_refs: list[ObjectRef] = field(default_factory=list)
    environment_ref: ObjectRef | None = None
    started_at: str | None = None
    output_refs: list[ObjectRef] = field(default_factory=list)


@dataclass(slots=True)
class Evidence(ResearchObject):
    object_type: str = field(init=False, default="evidence")
    kind: str = "unspecified"
    statement: str = ""
    source_ref: ObjectRef | None = None
    locator: str | None = None
    quality_flags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Claim(ResearchObject):
    object_type: str = field(init=False, default="claim")
    statement: str = ""
    strength: str = "unresolved"
    support_refs: list[ObjectRef] = field(default_factory=list)
    counterevidence_refs: list[ObjectRef] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    @property
    def evidence_refs(self) -> list[ObjectRef]:
        """Compatibility alias; canonical field name is support_refs."""

        return self.support_refs


@dataclass(slots=True)
class Decision(ResearchObject):
    object_type: str = field(init=False, default="decision")
    decision: str = ""
    scope: list[str] = field(default_factory=list)
    reason_refs: list[ObjectRef] = field(default_factory=list)
    actor: str = "human"
    timestamp: str | None = None
