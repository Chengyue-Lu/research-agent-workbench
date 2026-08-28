"""Exact-ref closure for the bounded Phase C state and lineage candidates."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from research_workbench.artifacts.integrity import hash_bytes, hash_file
from research_workbench.io import load_document_bytes


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
    file_sha256: str | None = None

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
    def _from_indexed(cls, entries: Iterable[IndexedDocument]) -> "ClosureIndex":
        index = cls()
        seen: set[tuple[str, int]] = set()
        for entry in entries:
            identity = (entry.identifier, entry.revision)
            if identity in seen:
                index.duplicate_identities.add(identity)
            seen.add(identity)
            index.by_id.setdefault(entry.identifier, []).append(entry)
        for values in index.by_id.values():
            values.sort(
                key=lambda item: (
                    item.revision,
                    item.path.as_posix() if item.path else "",
                )
            )
        return index

    @classmethod
    def from_documents(
        cls, documents: Mapping[Path, Any] | Iterable[tuple[Path, Any]]
    ) -> "ClosureIndex":
        items = documents.items() if isinstance(documents, Mapping) else documents
        entries: list[IndexedDocument] = []
        for path, document in items:
            normalized_path = Path(path)
            entry = _index_document(
                normalized_path,
                document,
                file_sha256=_document_file_hash(documents, normalized_path),
            )
            if entry is not None:
                entries.append(entry)
        return cls._from_indexed(entries)

    @classmethod
    def from_paths(cls, paths: Iterable[Path]) -> "ClosureIndex":
        entries: list[IndexedDocument] = []
        for path in paths:
            try:
                normalized_path = Path(path)
                content = normalized_path.read_bytes()
                document = load_document_bytes(normalized_path, content)
            except Exception:
                continue
            entry = _index_document(
                normalized_path,
                document,
                file_sha256=hash_bytes(content),
            )
            if entry is not None:
                entries.append(entry)
        return cls._from_indexed(entries)

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

    def resolve_file_ref(
        self, raw_ref: Any, *, expected_types: tuple[str, ...] = ()
    ) -> dict[str, Any]:
        """Resolve one fileRef inside the explicit closure and verify its byte pin."""

        if not isinstance(raw_ref, Mapping):
            raise ValueError("file reference must be an object")
        relative = raw_ref.get("path")
        declared_sha256 = raw_ref.get("sha256")
        if not isinstance(relative, str) or not relative:
            raise ValueError("file reference path must not be empty")
        normalized = relative.replace("\\", "/")
        parts = normalized.split("/")
        if normalized.startswith("/") or ":" in parts[0] or ".." in parts:
            raise ValueError("file reference path must be repository-relative")
        if not isinstance(declared_sha256, str) or not declared_sha256:
            raise ValueError("file reference sha256 must not be empty")

        candidates: list[IndexedDocument] = []
        for entries in self.by_id.values():
            for entry in entries:
                if entry.path is None:
                    continue
                indexed_path = entry.path.as_posix().replace("\\", "/")
                if indexed_path == normalized or indexed_path.endswith(f"/{normalized}"):
                    candidates.append(entry)
        result: dict[str, Any] = {
            "path": normalized,
            "status": "ok",
            "declared_sha256": declared_sha256,
            "entry": None,
        }
        if not candidates:
            result["status"] = "missing"
            return result
        if len(candidates) > 1:
            result["status"] = "ambiguous"
            return result
        entry = candidates[0]
        result["entry"] = entry
        if expected_types and entry.semantic_type not in expected_types:
            result["status"] = "type-mismatch"
            result["semantic_type"] = entry.semantic_type
        elif entry.file_sha256 is None:
            result["status"] = "hash-unverifiable"
        elif (
            declared_sha256.removeprefix("sha256:").lower()
            != entry.file_sha256.removeprefix("sha256:").lower()
        ):
            result["status"] = "hash-mismatch"
        return result


def _document_file_hash(documents: Mapping[Path, Any], path: Path) -> str | None:
    digest_getter = getattr(documents, "sha256_for", None)
    if callable(digest_getter):
        digest = digest_getter(path)
        if isinstance(digest, str) and digest:
            return digest
    try:
        return hash_file(path) if path.is_file() else None
    except OSError:
        return None


def _index_document(
    path: Path | None, document: Any, *, file_sha256: str | None = None
) -> IndexedDocument | None:
    if not isinstance(document, Mapping):
        return None
    if "state_id" in document:
        identifier = document.get("state_id")
        revision = document.get("revision")
        if isinstance(identifier, str) and identifier and isinstance(revision, int):
            return IndexedDocument(
                "research_state",
                "research_state",
                identifier,
                revision,
                path,
                document,
                file_sha256,
            )
        return None
    if "lineage_id" in document and "execution_attempt_ref" in document:
        identifier = document.get("lineage_id")
        revision = document.get("revision")
        if isinstance(identifier, str) and identifier and isinstance(revision, int):
            return IndexedDocument(
                "research_attempt_lineage",
                "research_attempt_lineage",
                identifier,
                revision,
                path,
                document,
                file_sha256,
            )
        return None
    if "failure_id" in document and "learned_result" in document:
        identifier = document.get("failure_id")
        revision = document.get("revision")
        if isinstance(identifier, str) and identifier and isinstance(revision, int):
            return IndexedDocument(
                "research_failure",
                "research_failure",
                identifier,
                revision,
                path,
                document,
                file_sha256,
            )
        return None
    if "trace_id" in document and "method_application" in document:
        identifier = document.get("trace_id")
        revision = document.get("revision")
        if isinstance(identifier, str) and identifier and isinstance(revision, int):
            return IndexedDocument(
                "method_trace",
                "method_trace",
                identifier,
                revision,
                path,
                document,
                file_sha256,
            )
        return None
    if "resolution_id" in document and "mode_resolution" in document:
        identifier = document.get("resolution_id")
        revision = document.get("revision")
        if isinstance(identifier, str) and identifier and isinstance(revision, int):
            return IndexedDocument(
                "method_resolution",
                "method_resolution",
                identifier,
                revision,
                path,
                document,
                file_sha256,
            )
        return None
    if document.get("record_kind") == "actual-execution-binding" and "fact_id" in document:
        identifier = document.get("fact_id")
        if isinstance(identifier, str) and identifier:
            return IndexedDocument(
                "execution_trace_fact",
                "execution_trace_fact",
                identifier,
                1,
                path,
                document,
                file_sha256,
            )
        return None
    if "snapshot_id" in document and "selected_supply_report_ref" in document:
        identifier = document.get("snapshot_id")
        revision = document.get("revision")
        if isinstance(identifier, str) and identifier and isinstance(revision, int):
            return IndexedDocument(
                "resolved_capability_snapshot",
                "resolved_capability_snapshot",
                identifier,
                revision,
                path,
                document,
                file_sha256,
            )
        return None
    if "task_id" in document and "goal" in document:
        identifier = document.get("task_id")
        revision = document.get("revision", 1)
        if isinstance(identifier, str) and identifier and isinstance(revision, int):
            return IndexedDocument(
                "task_packet",
                "task_packet",
                identifier,
                revision,
                path,
                document,
                file_sha256,
            )
        return None
    if "attempt_id" in document and "started_at" in document and "task_revision" in document:
        identifier = document.get("attempt_id")
        if isinstance(identifier, str) and identifier:
            return IndexedDocument(
                "attempt",
                "execution_attempt",
                identifier,
                1,
                path,
                document,
                file_sha256,
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
            file_sha256,
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


def _file_ref_problems(
    index: ClosureIndex,
    raw_ref: Any,
    label: str,
    *,
    expected_types: tuple[str, ...] = (),
) -> tuple[list[str], IndexedDocument | None]:
    try:
        resolved = index.resolve_file_ref(raw_ref, expected_types=expected_types)
    except ValueError as exc:
        return [f"{label}: {exc}"], None
    status = resolved["status"]
    if status == "missing":
        return [f"{label}: file is absent from the explicit closure ({resolved['path']})"], None
    if status == "ambiguous":
        return [f"{label}: file path is ambiguous in the explicit closure ({resolved['path']})"], None
    if status == "type-mismatch":
        return [
            f"{label}: role/type mismatch; target is {resolved.get('semantic_type')}, "
            f"expected {' or '.join(expected_types)}"
        ], None
    if status == "hash-unverifiable":
        return [f"{label}: file sha256 cannot be verified ({resolved['path']})"], None
    if status == "hash-mismatch":
        return [f"{label}: pinned sha256 drifts from loaded file bytes ({resolved['path']})"], None
    return [], resolved.get("entry")


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


def check_research_attempt_lineage(
    document: Mapping[str, Any], index: ClosureIndex
) -> list[str]:
    """Validate separation, exact execution pin, predecessor, and failure refs."""

    problems = index.identity_problems()
    file_problems, execution_attempt = _file_ref_problems(
        index,
        document.get("execution_attempt_ref"),
        "execution_attempt_ref",
        expected_types=("execution_attempt",),
    )
    problems.extend(file_problems)
    if execution_attempt is not None and execution_attempt.identifier != document.get("attempt_id"):
        problems.append(
            "execution_attempt_ref: target attempt_id does not match lineage attempt_id"
        )

    problems.extend(
        _ref_problems(
            index,
            document.get("state_ref"),
            "state_ref",
            expected_types=("research_state",),
        )
    )

    predecessor = document.get("predecessor_attempt_ref")
    justification = document.get("reopen_justification")
    if predecessor is not None:
        problems.extend(
            _ref_problems(
                index,
                predecessor,
                "predecessor_attempt_ref",
                expected_types=("research_attempt_lineage",),
            )
        )
        try:
            resolved = index.resolve(predecessor)
        except ValueError:
            resolved = {"status": "invalid"}
        if resolved.get("status") == "ok" and resolved.get("object_id") == document.get(
            "lineage_id"
        ):
            problems.append(
                "predecessor_attempt_ref: must identify a distinct predecessor Attempt"
            )
    if justification is not None:
        if not isinstance(justification, Mapping):
            problems.append("reopen_justification: must be a structured independent relation")
        else:
            for position, ref in enumerate(justification.get("basis_refs", [])):
                problems.extend(
                    _ref_problems(
                        index,
                        ref,
                        f"reopen_justification.basis_refs[{position}]",
                        expected_types=(
                            "research_failure",
                            "decision",
                            "evidence",
                            "research_state",
                        ),
                    )
                )
            for condition_position, condition in enumerate(
                justification.get("changed_conditions", [])
            ):
                if not isinstance(condition, Mapping):
                    continue
                for ref_position, ref in enumerate(condition.get("provenance_refs", [])):
                    problems.extend(
                        _ref_problems(
                            index,
                            ref,
                            "reopen_justification.changed_conditions"
                            f"[{condition_position}].provenance_refs[{ref_position}]",
                            expected_types=(
                                "research_failure",
                                "decision",
                                "evidence",
                                "research_state",
                            ),
                        )
                    )

    for position, ref in enumerate(document.get("failure_refs", [])):
        problems.extend(
            _ref_problems(
                index,
                ref,
                f"failure_refs[{position}]",
                expected_types=("research_failure",),
            )
        )
    return problems


def check_research_failure(
    document: Mapping[str, Any], index: ClosureIndex
) -> list[str]:
    """Validate only the optional bounded execution profile of a Research Failure."""

    problems = index.identity_problems()
    origin_kind = document.get("origin_kind")
    profile = document.get("execution_profile")
    if origin_kind == "execution" and not isinstance(profile, Mapping):
        problems.append("execution-origin Research Failure requires execution_profile")
    if origin_kind == "non-execution" and profile is not None:
        problems.append("non-execution Research Failure must not carry execution_profile")
    if isinstance(profile, Mapping):
        problems.extend(
            _ref_problems(
                index,
                profile.get("source_attempt_ref"),
                "execution_profile.source_attempt_ref",
                expected_types=("research_attempt_lineage",),
            )
        )
    return problems


def _resolved_entry(index: ClosureIndex, raw_ref: Any) -> IndexedDocument | None:
    try:
        resolved = index.resolve(raw_ref)
    except ValueError:
        return None
    if resolved.get("status") != "ok":
        return None
    candidates = index.by_id.get(str(resolved.get("object_id")), [])
    exact = [item for item in candidates if item.revision == resolved.get("revision")]
    return exact[0] if len(exact) == 1 else None


def _ref_identity(raw_ref: Any) -> tuple[str, int | None] | None:
    try:
        identifier, revision, _ = _parse_object_ref(raw_ref)
    except ValueError:
        return None
    return identifier, revision


def check_method_trace(document: Mapping[str, Any], index: ClosureIndex) -> list[str]:
    """Validate the ref-only Method Trace and its honest actual-binding boundary."""

    from research_workbench.validation.schemas import SchemaCatalog

    problems = index.identity_problems()
    catalog = SchemaCatalog()
    attempt_ref = document.get("attempt_ref")
    task_ref = document.get("task_ref")
    method_application = document.get("method_application", {})
    resolution_ref = (
        method_application.get("resolution_ref")
        if isinstance(method_application, Mapping)
        else None
    )

    problems.extend(
        _ref_problems(
            index,
            attempt_ref,
            "attempt_ref",
            expected_types=("research_attempt_lineage",),
        )
    )
    problems.extend(
        _ref_problems(index, task_ref, "task_ref", expected_types=("task_packet",))
    )
    problems.extend(
        _ref_problems(
            index,
            resolution_ref,
            "method_application.resolution_ref",
            expected_types=("method_resolution",),
        )
    )

    task_entry = _resolved_entry(index, task_ref)
    attempt_entry = _resolved_entry(index, attempt_ref)
    resolution_entry = _resolved_entry(index, resolution_ref)
    if task_entry is not None and resolution_entry is not None:
        for error in catalog.validate("method_resolution", resolution_entry.document):
            problems.append(
                "method_application.resolution_ref: referenced Method Resolution "
                f"is schema-invalid at {error.pointer}: {error.message}"
            )
        resolution_task = resolution_entry.document.get("task_ref")
        resolution_identity = None
        if isinstance(resolution_task, Mapping):
            resolution_identity = (
                str(resolution_task.get("task_id", "")),
                resolution_task.get("revision"),
            )
        if resolution_identity != (task_entry.identifier, task_entry.revision):
            problems.append(
                "method_application.resolution_ref: Method Resolution binds a different Task"
            )
        elif isinstance(resolution_task, Mapping):
            declared_hash = str(resolution_task.get("sha256", "")).removeprefix(
                "sha256:"
            ).lower()
            if task_entry.file_sha256 is None:
                problems.append(
                    "method_application.resolution_ref: Method Resolution Task pin "
                    "cannot be verified"
                )
            elif declared_hash != task_entry.file_sha256.removeprefix("sha256:").lower():
                problems.append(
                    "method_application.resolution_ref: Method Resolution Task byte pin drifts"
                )

    if attempt_entry is not None and task_entry is not None:
        file_problems, execution_attempt = _file_ref_problems(
            index,
            attempt_entry.document.get("execution_attempt_ref"),
            "attempt_ref.execution_attempt_ref",
            expected_types=("execution_attempt",),
        )
        problems.extend(file_problems)
        if (
            execution_attempt is not None
            and execution_attempt.document.get("task_id") != task_entry.identifier
        ):
            problems.append("attempt_ref: execution Attempt binds a different Task")

    if resolution_entry is not None and isinstance(method_application, Mapping):
        mode_resolution = resolution_entry.document.get("mode_resolution", {})
        expected_modes = (
            list(mode_resolution.get("selected_mode_refs", []))
            if isinstance(mode_resolution, Mapping)
            else []
        )
        if list(method_application.get("mode_refs", [])) != expected_modes:
            problems.append(
                "method_application.mode_refs must exactly match Method Resolution selected modes"
            )

        resolution_decisions = [
            item
            for item in resolution_entry.document.get("action_decisions", [])
            if isinstance(item, Mapping)
        ]
        expected_ids = [str(item.get("decision_id", "")) for item in resolution_decisions]
        dispositions = [
            item
            for item in document.get("path_dispositions", [])
            if isinstance(item, Mapping)
        ]
        disposition_ids = [str(item.get("action_decision_id", "")) for item in dispositions]
        if len(disposition_ids) != len(set(disposition_ids)):
            problems.append("path_dispositions contain duplicate action_decision_id")
        if set(disposition_ids) != set(expected_ids):
            problems.append(
                "path_dispositions must cover each Method Resolution action decision exactly once"
            )
        applied_ids = {
            str(item.get("action_decision_id", ""))
            for item in dispositions
            if item.get("disposition") == "applied"
        }
        if set(method_application.get("action_decision_ids", [])) != applied_ids:
            problems.append(
                "method_application.action_decision_ids must exactly match applied path dispositions"
            )
        if resolution_entry.document.get("resolution_status") != "proceed" and applied_ids:
            problems.append("a non-proceed Method Resolution cannot be recorded as applied")

    state_documents: list[Mapping[str, Any]] = []
    from_state_identity: tuple[str, int | None] | None = None
    seen_state_roles: set[str] = set()
    for position, state_ref in enumerate(document.get("state_refs", [])):
        if not isinstance(state_ref, Mapping):
            continue
        role = str(state_ref.get("role", ""))
        if role in seen_state_roles:
            problems.append(f"state_refs contain duplicate role {role}")
        seen_state_roles.add(role)
        ref = state_ref.get("ref")
        problems.extend(
            _ref_problems(
                index,
                ref,
                f"state_refs[{position}]",
                expected_types=("research_state",),
            )
        )
        entry = _resolved_entry(index, ref)
        if entry is not None:
            state_documents.append(entry.document)
        if role == "from-state":
            from_state_identity = _ref_identity(ref)

    if attempt_entry is not None:
        if from_state_identity != _ref_identity(attempt_entry.document.get("state_ref")):
            problems.append("state_refs.from-state must equal the Attempt lineage state_ref")

    for position, ref in enumerate(document.get("human_decision_refs", [])):
        problems.extend(
            _ref_problems(
                index,
                ref,
                f"human_decision_refs[{position}]",
                expected_types=("decision",),
            )
        )

    path_ref_types = {
        "decision_refs": ("decision",),
        "evidence_refs": ("evidence",),
        "failure_refs": ("research_failure",),
        "state_refs": ("research_state",),
    }
    for path_position, disposition in enumerate(document.get("path_dispositions", [])):
        if not isinstance(disposition, Mapping):
            continue
        for field_name, expected_types in path_ref_types.items():
            for ref_position, ref in enumerate(disposition.get(field_name, [])):
                problems.extend(
                    _ref_problems(
                        index,
                        ref,
                        f"path_dispositions[{path_position}].{field_name}[{ref_position}]",
                        expected_types=expected_types,
                    )
                )

    if task_entry is not None and state_documents:
        task_questions = {
            str(value).split("@", 1)[0]
            for value in task_entry.document.get("question_refs", [])
        }
        state_questions: set[str] = set()
        for state in state_documents:
            for entry in state.get("entries", []):
                if isinstance(entry, Mapping) and entry.get("role") == "question":
                    identity = _ref_identity(entry.get("ref"))
                    if identity is not None:
                        state_questions.add(identity[0])
        if state_questions and not task_questions.intersection(state_questions):
            problems.append("Task question_refs do not intersect Method Trace State questions")

    actual_binding = document.get("actual_binding")
    if isinstance(actual_binding, Mapping) and actual_binding.get("status") == "captured":
        fact_schema_accepted = "execution_trace_fact" in catalog.document_kinds
        if not fact_schema_accepted:
            problems.append(
                "actual_binding: no accepted execution fact producer exists in this schema baseline"
            )
        file_problems, fact_entry = _file_ref_problems(
            index,
            actual_binding.get("execution_fact_ref"),
            "actual_binding.execution_fact_ref",
            expected_types=("execution_trace_fact",),
        )
        problems.extend(file_problems)
        if fact_entry is not None and attempt_entry is not None:
            fact_errors = (
                catalog.validate("execution_trace_fact", fact_entry.document)
                if fact_schema_accepted
                else []
            )
            for error in fact_errors:
                problems.append(
                    "actual_binding.execution_fact_ref: referenced execution fact "
                    f"is schema-invalid at {error.pointer}: {error.message}"
                )
            if fact_entry.document.get("attempt_id") != attempt_entry.document.get("attempt_id"):
                problems.append("actual_binding: execution fact belongs to a different Attempt")

    if document.get("supersedes") is not None:
        problems.extend(
            _ref_problems(
                index,
                document["supersedes"],
                "supersedes",
                expected_types=("method_trace",),
            )
        )
        identity = _ref_identity(document["supersedes"])
        if identity is not None:
            if identity[0] != document.get("trace_id"):
                problems.append("supersedes: must reference the same Method Trace lineage")
            if not isinstance(identity[1], int) or identity[1] >= document.get("revision", 0):
                problems.append("supersedes: must reference a strictly earlier Method Trace revision")
    return problems
