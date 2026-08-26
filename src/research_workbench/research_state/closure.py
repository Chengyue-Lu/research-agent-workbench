"""Exact-ref closure for the M10-001 Research State candidate."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from research_workbench.io import load_document


STATE_ROLE_TYPES: dict[str, tuple[str, ...]] = {
    "question": ("question",),
    "hypothesis": ("hypothesis", "proposition"),
    "evidence": ("evidence",),
    "claim": ("claim",),
    "decision": ("decision",),
    "run": ("run",),
    "task": ("task_packet",),
}


@dataclass(frozen=True, slots=True)
class IndexedDocument:
    kind: str
    semantic_type: str
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
    """Identity index over one explicit bounded document set."""

    by_id: dict[str, list[IndexedDocument]] = field(default_factory=dict)
    duplicate_identities: set[tuple[str, int]] = field(default_factory=set)

    @classmethod
    def from_documents(
        cls, documents: Mapping[Path, Any] | Iterable[tuple[Path, Any]]
    ) -> "ClosureIndex":
        index = cls()
        items = documents.items() if isinstance(documents, Mapping) else documents
        seen: set[tuple[str, int]] = set()
        for path, document in items:
            entry = _index_document(Path(path), document)
            if entry is None:
                continue
            identity = (entry.identifier, entry.revision)
            if identity in seen:
                index.duplicate_identities.add(identity)
            seen.add(identity)
            index.by_id.setdefault(entry.identifier, []).append(entry)
        for entries in index.by_id.values():
            entries.sort(key=lambda item: (item.revision, item.path.as_posix() if item.path else ""))
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

    def identity_problems(self) -> list[str]:
        return [
            f"closure contains duplicate identity {identifier}@{revision}"
            for identifier, revision in sorted(self.duplicate_identities)
        ]

    def resolve(self, raw_ref: Any) -> dict[str, Any]:
        """Resolve one objectRef; ambiguity and unverifiable pins fail closed."""

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
            revision = candidates[-1].revision
        exact = [entry for entry in candidates if entry.revision == revision]
        if not exact:
            resolved["status"] = "revision-missing"
            return resolved
        if len(exact) > 1:
            resolved["status"] = "ambiguous"
            return resolved
        entry = exact[0]
        resolved.update(
            revision=entry.revision,
            path=entry.path.as_posix() if entry.path is not None else None,
            kind=entry.kind,
            semantic_type=entry.semantic_type,
        )
        if declared_sha256 is not None:
            if entry.content_hash is None:
                resolved["status"] = "hash-unverifiable"
            elif (
                declared_sha256.removeprefix("sha256:").lower()
                != entry.content_hash.removeprefix("sha256:").lower()
            ):
                resolved["status"] = "hash-mismatch"
        return resolved

    def latest_revision(self, identifier: str) -> int | None:
        candidates = self.by_id.get(identifier)
        return max((item.revision for item in candidates), default=None) if candidates else None


def _index_document(path: Path | None, document: Any) -> IndexedDocument | None:
    if not isinstance(document, Mapping):
        return None
    if "state_id" in document:
        identifier = document.get("state_id")
        revision = document.get("revision")
        if isinstance(identifier, str) and identifier and isinstance(revision, int):
            return IndexedDocument(
                "research_state", "research_state", identifier, revision, path, document
            )
        return None
    if "task_id" in document and "goal" in document:
        identifier = document.get("task_id")
        revision = document.get("revision", 1)
        if isinstance(identifier, str) and identifier and isinstance(revision, int):
            return IndexedDocument(
                "task_packet", "task_packet", identifier, revision, path, document
            )
        return None
    if (
        "object_type" in document
        and "object_id" in document
        and isinstance(document.get("revision"), int)
    ):
        return IndexedDocument(
            "research_object",
            str(document["object_type"]),
            str(document["object_id"]),
            int(document["revision"]),
            path,
            document,
        )
    return None


def _parse_object_ref(raw: Any) -> tuple[str, int | None, str | None]:
    if isinstance(raw, str):
        object_id, separator, revision = raw.partition("@")
        if not object_id:
            raise ValueError("object reference identity must not be empty")
        if not separator:
            return object_id, None, None
        try:
            parsed_revision = int(revision)
        except ValueError as exc:
            raise ValueError(f"invalid object reference revision: {raw}") from exc
        if parsed_revision < 1:
            raise ValueError(f"invalid object reference revision: {raw}")
        return object_id, parsed_revision, None
    if isinstance(raw, Mapping):
        object_id = str(raw.get("object_id", ""))
        if not object_id:
            raise ValueError("object_ref.object_id must not be empty")
        revision = raw.get("revision")
        if revision is not None and (not isinstance(revision, int) or revision < 1):
            raise ValueError(f"invalid object reference revision: {raw!r}")
        sha256 = raw.get("sha256")
        return object_id, revision, str(sha256) if sha256 is not None else None
    raise ValueError(f"unsupported object reference: {raw!r}")


def _ref_problems(
    index: ClosureIndex,
    raw_ref: Any,
    label: str,
    *,
    expected_types: tuple[str, ...] = (),
) -> list[str]:
    try:
        resolved = index.resolve(raw_ref)
    except ValueError as exc:
        return [f"{label}: {exc}"]
    status = resolved["status"]
    problems: list[str] = []
    if status == "missing":
        problems.append(f"{label}: unresolvable reference {resolved['object_id']}")
    elif status == "unversioned":
        problems.append(f"{label}: reference lacks a revision ({resolved['object_id']})")
    elif status == "revision-missing":
        problems.append(
            f"{label}: revision {resolved['revision']} of {resolved['object_id']} not found"
        )
    elif status == "ambiguous":
        problems.append(
            f"{label}: identity {resolved['object_id']}@{resolved['revision']} is ambiguous"
        )
    elif status == "hash-unverifiable":
        problems.append(
            f"{label}: pinned sha256 cannot be verified because target "
            f"{resolved['object_id']} has no content_hash"
        )
    elif status == "hash-mismatch":
        problems.append(
            f"{label}: pinned sha256 drifts from target content_hash ({resolved['object_id']})"
        )
    if expected_types and status == "ok" and resolved.get("semantic_type") not in expected_types:
        problems.append(
            f"{label}: role/type mismatch; target is {resolved.get('semantic_type')}, "
            f"expected {' or '.join(expected_types)}"
        )
    return problems


def check_research_state(document: Mapping[str, Any], index: ClosureIndex) -> list[str]:
    """M10-001 closure, lineage, staleness, role/type, and open-item rules."""

    problems = index.identity_problems()
    state_id = document.get("state_id")
    if document.get("supersedes") is not None:
        problems.extend(
            _ref_problems(
                index,
                document["supersedes"],
                "supersedes",
                expected_types=("research_state",),
            )
        )
        try:
            superseded = index.resolve(document["supersedes"])
        except ValueError:
            superseded = {"status": "invalid"}
        if superseded.get("status") == "ok":
            if superseded["object_id"] != state_id:
                problems.append("supersedes: must reference the same state_id lineage")
            if not (
                isinstance(superseded["revision"], int)
                and superseded["revision"] < document.get("revision", 0)
            ):
                problems.append("supersedes: must reference a strictly earlier revision")

    for position, entry in enumerate(document.get("entries", [])):
        label = f"entries[{position}]"
        expected = STATE_ROLE_TYPES.get(str(entry.get("role")), ())
        problems.extend(
            _ref_problems(index, entry.get("ref"), label, expected_types=expected)
        )
        try:
            resolved = index.resolve(entry.get("ref"))
        except ValueError:
            continue
        if resolved["status"] == "ok" and entry.get("disposition") == "current":
            latest = index.latest_revision(resolved["object_id"])
            if (
                isinstance(latest, int)
                and isinstance(resolved["revision"], int)
                and latest > resolved["revision"]
            ):
                problems.append(
                    f"{label}: marked current but revision {resolved['revision']} of "
                    f"{resolved['object_id']} is stale (latest {latest})"
                )

    for position, item in enumerate(document.get("open_items", [])):
        label = f"open_items[{position}]"
        if item.get("status") in {"resolved", "invalidated"} and not item.get(
            "provenance_refs"
        ):
            problems.append(f"{label}: closed item requires provenance_refs")
        for ref_position, ref in enumerate(item.get("provenance_refs", [])):
            problems.extend(
                _ref_problems(index, ref, f"{label}.provenance_refs[{ref_position}]")
            )
    return problems
