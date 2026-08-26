"""Phase C closure semantics: exact-ref indexes and deterministic checks.

Shared by repository validation and the staged fresh-actor gates.  Refs are
resolved by document identity (``object_id``/``state_id``/``failure_id``/
``decision_id``/``trace_id``/``task_id``) plus revision; an optional ref-level
``sha256`` pin is compared against the target's declared ``content_hash``
(the kernel object-content pin, identical to the M4-003 semantic).  The
composition documents themselves are pinned by id+revision and append-only
supersession, never by self-hashing their own bytes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from research_workbench.io import load_document

STATE_KIND_IDS = ("state_id", "failure_id", "decision_id", "trace_id")


@dataclass(frozen=True, slots=True)
class IndexedDocument:
    kind: str
    identifier: str
    revision: int
    path: Path | None
    document: Mapping[str, Any]

    @property
    def content_hash(self) -> str | None:
        value = self.document.get("content_hash")
        return str(value) if value is not None else None


@dataclass(slots=True)
class ClosureIndex:
    """Identity index over one bounded document set (batch or case tree)."""

    by_id: dict[str, list[IndexedDocument]] = field(default_factory=dict)

    @classmethod
    def from_documents(
        cls, documents: Mapping[Path, Any] | Iterable[tuple[Path, Any]]
    ) -> "ClosureIndex":
        index = cls()
        items = documents.items() if isinstance(documents, Mapping) else documents
        for path, document in items:
            entry = _index_document(Path(path), document)
            if entry is not None:
                index.by_id.setdefault(entry.identifier, []).append(entry)
        for entries in index.by_id.values():
            entries.sort(key=lambda item: item.revision)
        return index

    @classmethod
    def from_paths(cls, paths: Iterable[Path]) -> "ClosureIndex":
        loaded: dict[Path, Any] = {}
        for path in paths:
            try:
                loaded[Path(path)] = load_document(Path(path))
            except Exception:
                continue
        return cls.from_documents(loaded)

    def resolve(self, raw_ref: Any) -> dict[str, Any]:
        """Resolve one objectRef to an exact location or a fail-closed status."""

        object_id, revision, declared_sha256 = _parse_object_ref(raw_ref)
        resolved: dict[str, Any] = {
            "requested": raw_ref if isinstance(raw_ref, str) else dict(raw_ref),
            "object_id": object_id,
            "revision": revision,
            "path": None,
            "status": "ok",
            "declared_sha256": declared_sha256,
        }
        candidates = self.by_id.get(object_id)
        if not candidates:
            resolved["status"] = "missing"
            return resolved
        if revision is None:
            resolved["status"] = "unversioned"
            entry = candidates[-1]
        else:
            entry = next((item for item in candidates if item.revision == revision), None)
            if entry is None:
                resolved["status"] = "revision-missing"
                return resolved
        resolved["revision"] = entry.revision
        resolved["path"] = entry.path.as_posix() if entry.path is not None else None
        resolved["kind"] = entry.kind
        if declared_sha256 is not None and entry.content_hash is not None:
            if (
                declared_sha256.removeprefix("sha256:").lower()
                != entry.content_hash.removeprefix("sha256:").lower()
            ):
                resolved["status"] = "hash-mismatch"
        return resolved

    def latest_revision(self, identifier: str) -> int | None:
        candidates = self.by_id.get(identifier)
        return candidates[-1].revision if candidates else None


def _index_document(path: Path | None, document: Any) -> IndexedDocument | None:
    if not isinstance(document, Mapping):
        return None
    for key, kind in (
        ("state_id", "research_state"),
        ("failure_id", "research_failure"),
        ("decision_id", "human_decision_record"),
        ("trace_id", "method_trace"),
    ):
        if key in document:
            identifier = document.get(key)
            revision = document.get("revision")
            if isinstance(identifier, str) and identifier and isinstance(revision, int):
                return IndexedDocument(kind, identifier, revision, path, document)
            return None
    if "task_id" in document and "goal" in document:
        identifier = document.get("task_id")
        revision = document.get("revision", 1)
        if isinstance(identifier, str) and identifier:
            return IndexedDocument("task_packet", identifier, int(revision), path, document)
        return None
    if "object_type" in document and "object_id" in document and isinstance(
        document.get("revision"), int
    ):
        return IndexedDocument(
            "research_object",
            str(document["object_id"]),
            int(document["revision"]),
            path,
            document,
        )
    return None


def _parse_object_ref(raw: Any) -> tuple[str, int | None, str | None]:
    if isinstance(raw, str):
        object_id, separator, revision = raw.partition("@")
        if not separator:
            return object_id, None, None
        try:
            return object_id, int(revision), None
        except ValueError as exc:
            raise ValueError(f"invalid object reference revision: {raw}") from exc
    if isinstance(raw, Mapping):
        object_id = str(raw.get("object_id", ""))
        if not object_id:
            raise ValueError("object_ref.object_id must not be empty")
        revision = raw.get("revision")
        if revision is not None and (not isinstance(revision, int) or revision < 1):
            raise ValueError(f"invalid object reference revision: {raw!r}")
        return object_id, revision, raw.get("sha256")
    raise ValueError(f"unsupported object reference: {raw!r}")


def _ref_problems(
    index: ClosureIndex, raw_ref: Any, label: str, *, expected_kinds: tuple[str, ...] = ()
) -> list[str]:
    try:
        resolved = index.resolve(raw_ref)
    except ValueError as exc:
        return [f"{label}: {exc}"]
    problems: list[str] = []
    if resolved["status"] == "missing":
        problems.append(f"{label}: unresolvable reference {resolved['object_id']}")
    elif resolved["status"] == "unversioned":
        problems.append(f"{label}: reference lacks a revision ({resolved['object_id']})")
    elif resolved["status"] == "revision-missing":
        problems.append(
            f"{label}: revision {resolved['revision']} of {resolved['object_id']} not found"
        )
    elif resolved["status"] == "hash-mismatch":
        problems.append(f"{label}: pinned sha256 drifts from target content_hash ({resolved['object_id']})")
    if expected_kinds and resolved.get("kind") not in expected_kinds and resolved["status"] == "ok":
        problems.append(
            f"{label}: {resolved['object_id']} is {resolved['kind']}, expected {' or '.join(expected_kinds)}"
        )
    return problems


def check_research_state(document: Mapping[str, Any], index: ClosureIndex) -> list[str]:
    """M10-001: closure, staleness, supersession, and open-item rules."""

    problems: list[str] = []
    state_id = document.get("state_id")
    if document.get("supersedes") is not None:
        sup = index.resolve(document["supersedes"])
        if sup["status"] != "ok":
            problems.append(f"supersedes: prior revision unresolvable ({sup['object_id']})")
        else:
            if sup["object_id"] != state_id:
                problems.append("supersedes: must reference the same state_id lineage")
            if not (isinstance(sup["revision"], int) and sup["revision"] < document.get("revision", 0)):
                problems.append("supersedes: must reference a strictly earlier revision")
            if sup.get("kind") != "research_state":
                problems.append("supersedes: target is not a research state")

    for position, entry in enumerate(document.get("entries", [])):
        label = f"entries[{position}]"
        problems.extend(_ref_problems(index, entry.get("ref"), label))
        resolved = index.resolve(entry.get("ref"))
        if resolved["status"] == "ok" and entry.get("disposition") == "current":
            latest = index.latest_revision(resolved["object_id"])
            if isinstance(latest, int) and isinstance(resolved["revision"], int) and latest > resolved["revision"]:
                problems.append(
                    f"{label}: marked current but revision {resolved['revision']} of "
                    f"{resolved['object_id']} is stale (latest {latest})"
                )

    for position, item in enumerate(document.get("open_items", [])):
        label = f"open_items[{position}]"
        if item.get("status") == "invalidated" and not item.get("provenance_refs"):
            problems.append(f"{label}: invalidated item requires provenance_refs")
        for ref_position, ref in enumerate(item.get("provenance_refs", [])):
            problems.extend(_ref_problems(index, ref, f"{label}.provenance_refs[{ref_position}]"))

    for position, ref in enumerate(document.get("revisit_refs", [])):
        label = f"revisit_refs[{position}]"
        problems.extend(
            _ref_problems(index, ref, label, expected_kinds=("research_failure",))
        )
    return problems


def check_research_failure(document: Mapping[str, Any], index: ClosureIndex) -> list[str]:
    """M10-002: required learned semantics and exact source provenance."""

    problems: list[str] = []
    for field_name in ("evidence_refs", "invalidated_assumption_refs"):
        for position, ref in enumerate(document.get(field_name, [])):
            expected = ("research_object",) if field_name == "invalidated_assumption_refs" else ()
            problems.extend(
                _ref_problems(index, ref, f"{field_name}[{position}]", expected_kinds=expected)
            )
    if document.get("from_state_ref") is not None:
        problems.extend(
            _ref_problems(index, document["from_state_ref"], "from_state_ref")
        )
    if document.get("source_attempt_ref") is not None:
        problems.extend(
            _ref_problems(index, document["source_attempt_ref"], "source_attempt_ref")
        )
    return problems


def check_human_decision(document: Mapping[str, Any], index: ClosureIndex) -> list[str]:
    """M10 slice 3: provenance-bearing human decision stays distinct from eligibility."""

    problems: list[str] = []
    for position, ref in enumerate(document.get("subject_refs", [])):
        problems.extend(_ref_problems(index, ref, f"subject_refs[{position}]"))
    for position, ref in enumerate(document.get("asserted_fact_refs", [])):
        problems.extend(_ref_problems(index, ref, f"asserted_fact_refs[{position}]"))
    problems.extend(
        _ref_problems(
            index,
            document.get("state_effect_ref"),
            "state_effect_ref",
            expected_kinds=("research_state",),
        )
    )
    if document.get("decision_object_ref") is not None:
        problems.extend(_ref_problems(index, document["decision_object_ref"], "decision_object_ref"))
    return problems


_METHOD_TRACE_REQUIRED_REFS = {
    "method-resolution-applied": ("method_resolution_ref",),
    "execution-fact-recorded": ("execution_ref",),
    "human-decision-applied": ("decision_ref",),
    "research-state-changed": ("state_after_ref",),
    "failure-rationale-recorded": ("failure_ref",),
    "reopen-reviewable": ("failure_ref",),
}


def check_method_trace(document: Mapping[str, Any], index: ClosureIndex) -> list[str]:
    """M3-009 v0.1: contiguous append-only events, ref-only, family obligations."""

    problems: list[str] = []
    problems.extend(
        _ref_problems(
            index,
            document.get("subject_state_ref"),
            "subject_state_ref",
            expected_kinds=("research_state",),
        )
    )
    events = document.get("events", [])
    sequences: list[int] = []
    for position, event in enumerate(events):
        label = f"events[{position}]"
        sequence = event.get("sequence")
        if isinstance(sequence, int):
            sequences.append(sequence)
        family = event.get("family")
        gap_recorded = bool(event.get("actual_binding_gap"))
        refs = event.get("refs") or {}
        if family == "execution-fact-recorded":
            if gap_recorded and refs.get("execution_ref") is not None:
                problems.append(
                    f"{label}: an actual-binding gap must not also pin refs.execution_ref"
                )
            elif not gap_recorded and refs.get("execution_ref") is None:
                problems.append(
                    f"{label}: family execution-fact-recorded requires refs.execution_ref; "
                    "record an explicit gap instead of inventing the fact"
                )
        else:
            if gap_recorded:
                problems.append(
                    f"{label}: actual_binding_gap applies only to execution-fact-recorded events"
                )
            required = _METHOD_TRACE_REQUIRED_REFS.get(family, ())
            for required_ref in required:
                if refs.get(required_ref) is None:
                    problems.append(
                        f"{label}: family {family} requires refs.{required_ref}"
                    )
        for ref_name, ref in refs.items():
            problems.extend(_ref_problems(index, ref, f"{label}.refs.{ref_name}"))
        if family == "research-state-changed" and refs.get("state_before_ref") is not None:
            problems.extend(_ref_problems(index, refs["state_before_ref"], f"{label}.refs.state_before_ref"))
    if sequences and sequences != list(range(1, len(sequences) + 1)):
        problems.append("events: sequence must be contiguous from 1 without gaps or duplicates")
    return problems


def check_phase_c_document(
    kind: str, document: Mapping[str, Any], index: ClosureIndex
) -> list[str]:
    handlers = {
        "research_state": check_research_state,
        "research_failure": check_research_failure,
        "human_decision_record": check_human_decision,
        "method_trace": check_method_trace,
    }
    handler = handlers.get(kind)
    return handler(document, index) if handler else []
