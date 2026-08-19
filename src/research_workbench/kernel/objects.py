"""Small, method-neutral research objects.

These objects intentionally contain no model-provider, agent-runtime, or
discipline-specific fields. Method packs can reference them without changing
their identity and provenance rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from research_workbench.contracts.common import (
    ContractError,
    mapping_value,
    optional_string,
    require_string,
    string_tuple,
)


SCHEMA_VERSION = "0.1.0"

CLAIM_STRENGTHS = (
    "exploratory",
    "source_reported",
    "derivation_supported",
    "simulation_supported",
    "observationally_supported",
    "experimentally_supported",
    "synthesis_supported",
    "unresolved",
    "withdrawn",
)

SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")


def _positive_int(data: Mapping[str, Any], field: str) -> int:
    value = data.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ContractError(field, "must be a positive integer")
    return value


def _sha256(value: str, field: str) -> str:
    if not SHA256_RE.fullmatch(value):
        raise ContractError(field, "must be a SHA-256 digest")
    return value.removeprefix("sha256:").lower()


def _ref_list(data: Mapping[str, Any], field: str, *, required: bool = False) -> list[ObjectRef]:
    value = data.get(field)
    if value is None and not required:
        return []
    if not isinstance(value, list):
        raise ContractError(field, "must be an array of object references")
    return [ObjectRef.from_mapping(item) for item in value]


def _required_ref(data: Mapping[str, Any], field: str) -> ObjectRef:
    value = data.get(field)
    if value is None:
        raise ContractError(field, "must reference an object")
    return ObjectRef.from_mapping(value)


def _base_fields(data: Mapping[str, Any], object_types: tuple[str, ...]) -> dict[str, Any]:
    object_type = require_string(data, "object_type")
    if object_type not in object_types:
        raise ContractError("object_type", f"must be one of {list(object_types)}")
    schema_version = require_string(data, "schema_version")
    if schema_version != SCHEMA_VERSION:
        raise ContractError("schema_version", f"must be {SCHEMA_VERSION}")
    content_hash = optional_string(data, "content_hash")
    if content_hash is not None:
        content_hash = _sha256(content_hash, "content_hash")
    supersedes = data.get("supersedes")
    return {
        "object_id": require_string(data, "object_id"),
        "schema_version": schema_version,
        "revision": _positive_int(data, "revision"),
        "status": require_string(data, "status"),
        "content_hash": content_hash,
        "supersedes": ObjectRef.from_mapping(supersedes) if supersedes is not None else None,
        "metadata": dict(mapping_value(data, "metadata")),
    }


@dataclass(frozen=True, slots=True)
class ObjectRef:
    object_id: str
    revision: int
    sha256: str | None = None

    @property
    def pinned(self) -> bool:
        return self.sha256 is not None

    @classmethod
    def from_mapping(cls, data: Any) -> "ObjectRef":
        """Parse a schema objectRef: "ID", "ID@revision", or a mapping."""

        if isinstance(data, str):
            object_id, separator, revision = data.partition("@")
            if not object_id.strip():
                raise ContractError("object_ref", "must be a non-empty string")
            if not separator:
                return cls(object_id, 1)
            if not revision.isdigit() or int(revision) < 1:
                raise ContractError("object_ref", "string reference must end with @<positive revision>")
            return cls(object_id, int(revision))
        if isinstance(data, Mapping):
            sha256 = optional_string(data, "sha256")
            return cls(
                object_id=require_string(data, "object_id"),
                revision=_positive_int(data, "revision"),
                sha256=_sha256(sha256, "sha256") if sha256 is not None else None,
            )
        raise ContractError("object_ref", "must be a string or an object")

    def to_mapping(self) -> dict[str, Any]:
        document: dict[str, Any] = {"object_id": self.object_id, "revision": self.revision}
        if self.sha256 is not None:
            document["sha256"] = self.sha256
        return document


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

    def to_mapping(self) -> dict[str, Any]:
        # Subclasses extend this via ResearchObject.to_mapping(self): zero-argument
        # super() breaks under @dataclass(slots=True) class recreation.
        document: dict[str, Any] = {
            "schema_version": self.schema_version,
            "object_type": self.object_type,
            "object_id": self.object_id,
            "revision": self.revision,
            "status": self.status,
        }
        if self.content_hash is not None:
            document["content_hash"] = self.content_hash
        if self.supersedes is not None:
            document["supersedes"] = self.supersedes.to_mapping()
        if self.metadata:
            document["metadata"] = dict(self.metadata)
        return document


@dataclass(slots=True)
class Question(ResearchObject):
    object_type: str = field(init=False, default="question")
    text: str = ""
    scope: list[str] = field(default_factory=list)
    known_ambiguities: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Question":
        return cls(
            text=require_string(data, "text"),
            scope=list(string_tuple(data, "scope", required=True)),
            known_ambiguities=list(string_tuple(data, "known_ambiguities", required=True)),
            **_base_fields(data, ("question",)),
        )

    def to_mapping(self) -> dict[str, Any]:
        document = ResearchObject.to_mapping(self)
        document.update(
            {
                "text": self.text,
                "scope": list(self.scope),
                "known_ambiguities": list(self.known_ambiguities),
            }
        )
        return document


@dataclass(slots=True)
class Proposition(ResearchObject):
    object_type: str = "proposition"
    statement: str = ""
    assumptions: list[str] = field(default_factory=list)
    applicability: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Proposition":
        return cls(
            object_type=require_string(data, "object_type"),
            statement=require_string(data, "statement"),
            assumptions=list(string_tuple(data, "assumptions", required=True)),
            applicability=list(string_tuple(data, "applicability", required=True)),
            **_base_fields(data, ("hypothesis", "proposition")),
        )

    def to_mapping(self) -> dict[str, Any]:
        document = ResearchObject.to_mapping(self)
        document.update(
            {
                "statement": self.statement,
                "assumptions": list(self.assumptions),
                "applicability": list(self.applicability),
            }
        )
        return document


@dataclass(slots=True)
class Method(ResearchObject):
    object_type: str = field(init=False, default="method")
    kind: str = "unspecified"
    spec_ref: ObjectRef | None = None
    version: str = "0.1.0"
    limitations: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Method":
        return cls(
            kind=require_string(data, "kind"),
            spec_ref=_required_ref(data, "spec_ref"),
            version=require_string(data, "version"),
            limitations=list(string_tuple(data, "limitations", required=True)),
            **_base_fields(data, ("method",)),
        )

    def to_mapping(self) -> dict[str, Any]:
        document = ResearchObject.to_mapping(self)
        document.update(
            {
                "kind": self.kind,
                "spec_ref": self.spec_ref.to_mapping() if self.spec_ref is not None else None,
                "version": self.version,
                "limitations": list(self.limitations),
            }
        )
        return document


@dataclass(slots=True)
class Run(ResearchObject):
    object_type: str = field(init=False, default="run")
    method_ref: ObjectRef | None = None
    input_refs: list[ObjectRef] = field(default_factory=list)
    environment_ref: ObjectRef | None = None
    started_at: str | None = None
    output_refs: list[ObjectRef] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Run":
        return cls(
            method_ref=_required_ref(data, "method_ref"),
            input_refs=_ref_list(data, "input_refs", required=True),
            environment_ref=_required_ref(data, "environment_ref"),
            started_at=require_string(data, "started_at"),
            output_refs=_ref_list(data, "output_refs", required=True),
            **_base_fields(data, ("run",)),
        )

    def to_mapping(self) -> dict[str, Any]:
        document = ResearchObject.to_mapping(self)
        document.update(
            {
                "method_ref": self.method_ref.to_mapping() if self.method_ref is not None else None,
                "input_refs": [ref.to_mapping() for ref in self.input_refs],
                "environment_ref": (
                    self.environment_ref.to_mapping() if self.environment_ref is not None else None
                ),
                "started_at": self.started_at,
                "output_refs": [ref.to_mapping() for ref in self.output_refs],
            }
        )
        return document


@dataclass(slots=True)
class Evidence(ResearchObject):
    object_type: str = field(init=False, default="evidence")
    kind: str = "unspecified"
    statement: str = ""
    source_ref: ObjectRef | None = None
    locator: str | None = None
    quality_flags: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Evidence":
        fields = _base_fields(data, ("evidence",))
        if fields["content_hash"] is None:
            raise ContractError("content_hash", "is required for evidence objects")
        return cls(
            kind=require_string(data, "kind"),
            statement=require_string(data, "statement"),
            source_ref=_required_ref(data, "source_ref"),
            locator=require_string(data, "locator"),
            quality_flags=list(string_tuple(data, "quality_flags", required=True)),
            **fields,
        )

    def to_mapping(self) -> dict[str, Any]:
        document = ResearchObject.to_mapping(self)
        document.update(
            {
                "kind": self.kind,
                "statement": self.statement,
                "source_ref": self.source_ref.to_mapping() if self.source_ref is not None else None,
                "locator": self.locator,
                "quality_flags": list(self.quality_flags),
            }
        )
        return document


@dataclass(slots=True)
class Claim(ResearchObject):
    object_type: str = field(init=False, default="claim")
    statement: str = ""
    strength: str = "unresolved"
    support_refs: list[ObjectRef] = field(default_factory=list)
    counterevidence_refs: list[ObjectRef] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Claim":
        strength = require_string(data, "strength")
        if strength not in CLAIM_STRENGTHS:
            raise ContractError("strength", f"must be one of {list(CLAIM_STRENGTHS)}")
        return cls(
            statement=require_string(data, "statement"),
            strength=strength,
            support_refs=_ref_list(data, "support_refs", required=True),
            counterevidence_refs=_ref_list(data, "counterevidence_refs", required=True),
            limitations=list(string_tuple(data, "limitations", required=True)),
            **_base_fields(data, ("claim",)),
        )

    def to_mapping(self) -> dict[str, Any]:
        document = ResearchObject.to_mapping(self)
        document.update(
            {
                "statement": self.statement,
                "strength": self.strength,
                "support_refs": [ref.to_mapping() for ref in self.support_refs],
                "counterevidence_refs": [ref.to_mapping() for ref in self.counterevidence_refs],
                "limitations": list(self.limitations),
            }
        )
        return document


@dataclass(slots=True)
class Decision(ResearchObject):
    object_type: str = field(init=False, default="decision")
    decision: str = ""
    scope: list[str] = field(default_factory=list)
    reason_refs: list[ObjectRef] = field(default_factory=list)
    actor: str = "human"
    timestamp: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Decision":
        return cls(
            decision=require_string(data, "decision"),
            scope=list(string_tuple(data, "scope", required=True)),
            reason_refs=_ref_list(data, "reason_refs", required=True),
            actor=require_string(data, "actor"),
            timestamp=require_string(data, "timestamp"),
            **_base_fields(data, ("decision",)),
        )

    def to_mapping(self) -> dict[str, Any]:
        document = ResearchObject.to_mapping(self)
        document.update(
            {
                "decision": self.decision,
                "scope": list(self.scope),
                "reason_refs": [ref.to_mapping() for ref in self.reason_refs],
                "actor": self.actor,
                "timestamp": self.timestamp,
            }
        )
        return document
