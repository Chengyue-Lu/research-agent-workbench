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
    revision: int = 1
    source_refs: list[ObjectRef] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def ref(self) -> ObjectRef:
        return ObjectRef(self.object_id, self.revision)


@dataclass(slots=True)
class Question(ResearchObject):
    prompt: str = ""
    scope: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Proposition(ResearchObject):
    statement: str = ""
    falsifiers: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Method(ResearchObject):
    name: str = ""
    assumptions: list[str] = field(default_factory=list)
    protocol_refs: list[ObjectRef] = field(default_factory=list)


@dataclass(slots=True)
class Run(ResearchObject):
    method_ref: ObjectRef | None = None
    status: str = "planned"
    input_refs: list[ObjectRef] = field(default_factory=list)
    output_refs: list[ObjectRef] = field(default_factory=list)


@dataclass(slots=True)
class Evidence(ResearchObject):
    statement: str = ""
    locator: str | None = None
    polarity: str = "neutral"


@dataclass(slots=True)
class Claim(ResearchObject):
    statement: str = ""
    evidence_refs: list[ObjectRef] = field(default_factory=list)
    counterevidence_refs: list[ObjectRef] = field(default_factory=list)
    claim_ceiling: str = "unresolved"


@dataclass(slots=True)
class Decision(ResearchObject):
    decision: str = ""
    rationale_refs: list[ObjectRef] = field(default_factory=list)
    decided_by: str = "human"
