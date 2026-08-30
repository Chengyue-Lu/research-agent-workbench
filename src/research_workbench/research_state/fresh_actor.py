"""Fresh-process consumer for the runner-owned Phase C exact closure."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

from research_workbench.artifacts.integrity import hash_bytes
from research_workbench.io import load_document_bytes
from research_workbench.research_state.boundaries import (
    AUTHORITY_LIMITS,
    TRUSTED_RUNTIME_SCHEMA_SURFACE,
)
from research_workbench.research_state.closure import _parse_object_ref
from research_workbench.validation.documents import (
    LoadedDocuments,
    infer_document_kind,
    validate_documents,
)
from research_workbench.validation.schemas import SchemaCatalog


def _is_write_mode(raw_mode: Any) -> bool:
    if isinstance(raw_mode, str):
        return any(marker in raw_mode for marker in ("w", "a", "x", "+"))
    if isinstance(raw_mode, int):
        return bool(raw_mode & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND))
    return False


class FileAccessPolicy:
    """Deny undeclared data files and record the exact case-data surface."""

    def __init__(
        self,
        *,
        root: Path,
        allowed_reads: set[Path],
        allowed_writes: set[Path],
        trusted_read_roots: tuple[Path, ...] = (),
    ) -> None:
        self.root = root.resolve()
        self.allowed_reads = {path.resolve() for path in allowed_reads}
        self.allowed_writes = {path.resolve() for path in allowed_writes}
        self.trusted_read_roots = tuple(path.resolve() for path in trusted_read_roots)
        self.case_data_read_surface: set[str] = set()
        self.input_write_surface: set[str] = set()

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def _trusted_read(self, path: Path) -> bool:
        return any(path == root or path.is_relative_to(root) for root in self.trusted_read_roots)

    def record_manifest_read(self, path: Path) -> None:
        resolved = path.resolve()
        if resolved not in self.allowed_reads:
            raise PermissionError("actor manifest is not in the read allowlist")
        self.case_data_read_surface.add(self._relative(resolved))

    def read_bytes(self, path: Path) -> bytes:
        """Read one staged input through the explicit allowlist.

        The audit hook remains a process-wide backstop; this method also makes the
        consumer's intended reads explicit and independently testable.
        """

        resolved = path.resolve()
        if resolved not in self.allowed_reads:
            raise PermissionError(f"actor read outside runner-owned allowlist: {resolved}")
        self.case_data_read_surface.add(self._relative(resolved))
        return resolved.read_bytes()

    def _audit(self, event: str, args: tuple[Any, ...]) -> None:
        if event != "open" or not args or isinstance(args[0], int):
            return
        raw_path = args[0]
        if not isinstance(raw_path, (str, bytes, os.PathLike)):
            return
        path = Path(os.fsdecode(raw_path)).resolve()
        write = _is_write_mode(args[1] if len(args) > 1 else "r")
        if write:
            if path not in self.allowed_writes:
                if path.is_relative_to(self.root):
                    self.input_write_surface.add(self._relative(path))
                raise PermissionError(f"actor write outside output allowlist: {path}")
            return
        if path in self.allowed_reads:
            self.case_data_read_surface.add(self._relative(path))
            return
        if self._trusted_read(path):
            return
        raise PermissionError(f"actor read outside runner-owned allowlist: {path}")

    def install(self) -> None:
        sys.addaudithook(self._audit)


def _safe_staged_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError(f"staged path escapes actor root: {relative}")
    return candidate


def _identity(kind: str, document: Mapping[str, Any]) -> tuple[str, int]:
    fields = {
        "research_state": "state_id",
        "research_object": "object_id",
        "research_attempt_lineage": "lineage_id",
        "attempt": "attempt_id",
        "research_failure": "failure_id",
        "task_packet": "task_id",
        "method_resolution": "resolution_id",
        "method_trace": "trace_id",
    }
    identifier = document.get(fields[kind])
    revision = document.get("revision", 1)
    if not isinstance(identifier, str) or not identifier:
        raise ValueError(f"{kind} lacks its durable identity")
    if not isinstance(revision, int) or revision < 1:
        raise ValueError(f"{kind} has an invalid revision")
    return identifier, revision


def _ref_string(raw_ref: Any) -> str:
    identifier, revision, _ = _parse_object_ref(raw_ref)
    return f"{identifier}@{revision}"


def _selected_ref_strings(state: Mapping[str, Any], role: str) -> list[str]:
    return sorted(
        _ref_string(entry["ref"])
        for entry in state.get("entries", [])
        if isinstance(entry, Mapping)
        and entry.get("role") == role
        and entry.get("disposition") == "current"
    )


def _trace_failure_refs(trace: Mapping[str, Any]) -> list[Any]:
    return [
        ref
        for disposition in trace.get("path_dispositions", [])
        if isinstance(disposition, Mapping)
        for ref in disposition.get("failure_refs", [])
    ]


def _classify_paths(
    candidate_paths: list[Any],
    failures: Mapping[str, Mapping[str, Any]],
    identity_kinds: Mapping[str, str],
) -> tuple[list[dict[str, str]], str | None]:
    classified: list[dict[str, str]] = []
    seen_path_ids: set[str] = set()
    for raw in candidate_paths:
        if not isinstance(raw, Mapping):
            raise ValueError("candidate path must be an object")
        path_id = str(raw.get("path_id", ""))
        if not path_id or path_id in seen_path_ids:
            raise ValueError(f"candidate path identity is empty or duplicate: {path_id}")
        seen_path_ids.add(path_id)
        repeated = raw.get("repeats_failure_ref")
        if repeated is None:
            classification = "recommendable"
        else:
            failure_id, failure_revision, _ = _parse_object_ref(repeated)
            if failure_revision is None:
                raise ValueError("candidate path failure ref must be versioned")
            failure_key = f"{failure_id}@{failure_revision}"
            if failure_key not in failures:
                raise ValueError(f"candidate path references unknown failure: {failure_key}")
            for basis in raw.get("reopen_basis_refs", []):
                basis_id, basis_revision, _ = _parse_object_ref(basis)
                if basis_revision is None:
                    raise ValueError("candidate path reopen basis must be versioned")
                basis_key = f"{basis_id}@{basis_revision}"
                if identity_kinds.get(basis_key) not in {
                    "research_failure",
                    "decision",
                    "evidence",
                    "research_state",
                }:
                    raise ValueError(
                        f"candidate path reopen basis is absent or wrong-kind: {basis_key}"
                    )
            classification = (
                "reviewable" if raw.get("reopen_basis_refs") else "known-failed-avoid"
            )
        classified.append({"path_id": path_id, "classification": classification})
    recommended = next(
        (
            item["path_id"]
            for item in classified
            if item["classification"] == "recommendable"
        ),
        None,
    )
    return classified, recommended


def run_actor(manifest_path: Path, output_path: Path) -> dict[str, Any]:
    """Consume one staged exact closure without directory discovery."""

    manifest_path = manifest_path.resolve()
    output_path = output_path.resolve()
    if output_path.exists():
        raise FileExistsError(f"actor output already exists: {output_path}")
    root = manifest_path.parent.resolve()
    raw_manifest = manifest_path.read_bytes()
    manifest = json.loads(raw_manifest.decode("utf-8"))
    if not isinstance(manifest, Mapping):
        raise ValueError("actor manifest must be an object")

    entries = manifest.get("documents", [])
    if not isinstance(entries, list) or not entries:
        raise ValueError("actor manifest has no documents")
    alias_paths: dict[str, Path] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("actor manifest document entry must be an object")
        alias = str(entry.get("alias", ""))
        if not alias or alias in alias_paths:
            raise ValueError(f"actor manifest alias is empty or duplicate: {alias}")
        alias_paths[alias] = _safe_staged_path(root, str(entry.get("path", "")))

    catalog = SchemaCatalog()
    policy = FileAccessPolicy(
        root=root,
        allowed_reads={manifest_path, *alias_paths.values()},
        allowed_writes={output_path},
        trusted_read_roots=(catalog.directory,),
    )
    policy.record_manifest_read(manifest_path)
    policy.install()

    documents = LoadedDocuments()
    documents_by_alias: dict[str, Mapping[str, Any]] = {}
    for entry in entries:
        alias = str(entry["alias"])
        path = alias_paths[alias]
        content = policy.read_bytes(path)
        expected_hash = str(entry.get("sha256", "")).removeprefix("sha256:").lower()
        if hash_bytes(content) != expected_hash:
            raise ValueError(f"staged byte pin drifts for alias {alias}")
        document = load_document_bytes(path, content)
        if not isinstance(document, Mapping):
            raise ValueError(f"staged document is not an object: {alias}")
        kind = infer_document_kind(document)
        expected_kind = str(entry.get("kind", ""))
        if kind != expected_kind:
            raise ValueError(
                f"staged document kind mismatch for {alias}: expected {expected_kind}, got {kind}"
            )
        expected_identity = entry.get("identity", {})
        actual_identity = _identity(expected_kind, document)
        if not isinstance(expected_identity, Mapping) or actual_identity != (
            expected_identity.get("object_id"),
            expected_identity.get("revision"),
        ):
            raise ValueError(f"staged document identity mismatch for {alias}")
        documents.add(path, document, sha256=hash_bytes(content))
        documents_by_alias[alias] = document

    issues = validate_documents(documents)
    if issues:
        rendered = "; ".join(f"{issue.code}: {issue.message}" for issue in issues[:12])
        raise ValueError(f"staged closure validation failed: {rendered}")

    state_alias = str(manifest.get("state_alias", ""))
    trace_alias = str(manifest.get("method_trace_alias", ""))
    state = documents_by_alias.get(state_alias)
    trace = documents_by_alias.get(trace_alias)
    if state is None or infer_document_kind(state) != "research_state":
        raise ValueError("state_alias does not select a Research State")
    if trace is None or infer_document_kind(trace) != "method_trace":
        raise ValueError("method_trace_alias does not select a Method Trace")
    if state.get("status") != "active" or trace.get("status") != "active":
        raise ValueError("selected State and Method Trace must both be active")

    state_id = str(state.get("state_id", ""))
    active_heads = [
        document
        for document in documents_by_alias.values()
        if infer_document_kind(document) == "research_state"
        and document.get("state_id") == state_id
        and document.get("status") == "active"
    ]
    if len(active_heads) != 1:
        raise ValueError(f"selected State lineage has {len(active_heads)} active heads")
    trace_id = str(trace.get("trace_id", ""))
    active_trace_heads = [
        document
        for document in documents_by_alias.values()
        if infer_document_kind(document) == "method_trace"
        and document.get("trace_id") == trace_id
        and document.get("status") == "active"
    ]
    if len(active_trace_heads) != 1:
        raise ValueError(
            f"selected Method Trace lineage has {len(active_trace_heads)} active heads"
        )
    selected_state_ref = f"{state_id}@{state.get('revision')}"
    trace_state_refs = {
        _ref_string(item.get("ref"))
        for item in trace.get("state_refs", [])
        if isinstance(item, Mapping) and item.get("role") in {"current", "result"}
    }
    if selected_state_ref not in trace_state_refs:
        raise ValueError("selected Method Trace is stale for the selected State revision")

    failures: dict[str, Mapping[str, Any]] = {}
    for raw_ref in _trace_failure_refs(trace):
        failure_id, revision, _ = _parse_object_ref(raw_ref)
        match = next(
            (
                document
                for document in documents_by_alias.values()
                if infer_document_kind(document) == "research_failure"
                and document.get("failure_id") == failure_id
                and document.get("revision") == revision
            ),
            None,
        )
        if match is None:
            raise ValueError(f"Method Trace failure ref is absent: {failure_id}@{revision}")
        failures[f"{failure_id}@{revision}"] = match

    identity_kinds: dict[str, str] = {}
    for document in documents_by_alias.values():
        kind = infer_document_kind(document)
        if kind in {
            "research_state",
            "research_object",
            "research_attempt_lineage",
            "attempt",
            "research_failure",
            "task_packet",
            "method_resolution",
            "method_trace",
        }:
            identifier, revision = _identity(kind, document)
            semantic_kind = (
                str(document.get("object_type")) if kind == "research_object" else kind
            )
            identity_kinds[f"{identifier}@{revision}"] = semantic_kind

    choices, recommended = _classify_paths(
        list(manifest.get("candidate_paths", [])), failures, identity_kinds
    )
    answer = {
        "status": "ok",
        "case_id": str(manifest.get("case_id", "")),
        "profile": str(manifest.get("profile", "")),
        "actor_pid": os.getpid(),
        "active_state": selected_state_ref,
        "method_trace": f"{trace.get('trace_id')}@{trace.get('revision')}",
        "applied_modes": list(trace.get("method_application", {}).get("mode_refs", [])),
        "applied_actions": list(
            trace.get("method_application", {}).get("action_decision_ids", [])
        ),
        "current_evidence_refs": _selected_ref_strings(state, "evidence"),
        "human_decision_refs": sorted(
            _ref_string(ref) for ref in trace.get("human_decision_refs", [])
        ),
        "open_items": sorted(
            str(item.get("item_id"))
            for item in state.get("open_items", [])
            if isinstance(item, Mapping) and item.get("status") == "open"
        ),
        "invalidated_items": sorted(
            str(item.get("item_id"))
            for item in state.get("open_items", [])
            if isinstance(item, Mapping) and item.get("status") == "invalidated"
        ),
        "known_failures": sorted(
            (
                {
                    "failure_id": failure_id.split("@", 1)[0],
                    "learned_result": str(failure.get("learned_result", "")),
                    "revisit_condition": str(failure.get("revisit_condition", "")),
                }
                for failure_id, failure in failures.items()
            ),
            key=lambda item: item["failure_id"],
        ),
        "candidate_paths": choices,
        "recommended_path": recommended,
        "actual_binding_status": str(trace.get("actual_binding", {}).get("status", "")),
        "actual_binding_coverage": str(
            trace.get("actual_binding", {}).get("coverage", "")
        ),
        "authority_limits": AUTHORITY_LIMITS,
        "case_data_read_surface": sorted(policy.case_data_read_surface),
        "trusted_runtime_schema_surface": [
            dict(item) for item in TRUSTED_RUNTIME_SCHEMA_SURFACE
        ],
        "input_write_surface": sorted(policy.input_write_surface),
    }
    return answer


def main(argv: list[str] | None = None) -> int:
    arguments = list(argv if argv is not None else sys.argv[1:])
    if len(arguments) != 2:
        print(
            "usage: python -m research_workbench.research_state.fresh_actor "
            "<actor-manifest.json> <answer.json>",
            file=sys.stderr,
        )
        return 2
    manifest_path = Path(arguments[0])
    output_path = Path(arguments[1])
    try:
        answer = run_actor(manifest_path, output_path)
        with output_path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(answer, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
    except Exception as exc:
        try:
            if not output_path.exists():
                with output_path.open("x", encoding="utf-8", newline="\n") as stream:
                    json.dump(
                        {"status": "blocked", "problems": [str(exc)]},
                        stream,
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    )
                    stream.write("\n")
        except Exception:
            pass
        print(f"fresh actor blocked: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
