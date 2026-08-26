"""Explicit, supply-neutral Runtime Bundle/Profile validation.

This module intentionally does not import the repository-wide document
validator or any Skill evolution model.  A Runtime bundle is an allowlisted,
hash-pinned closure, not a directory and not an execution authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from research_workbench.artifacts.integrity import hash_bytes, resolve_within_root
from research_workbench.io import load_document_bytes
from research_workbench.validation.schemas import SchemaCatalog


ALLOWED_KINDS = frozenset(
    {
        "task_packet",
        "method_resolution",
        "capability_requirement",
        "capability_conformance_evidence",
        "capability_supply_report",
        "capability_resolution",
        "resolved_capability_snapshot",
    }
)


@dataclass(frozen=True, slots=True)
class RuntimeBundleIssue:
    path: Path
    code: str
    message: str


class RuntimeBundleValidationError(ValueError):
    def __init__(self, issues: Iterable[RuntimeBundleIssue]):
        self.issues = tuple(issues)
        detail = "; ".join(f"{issue.path}:{issue.code}:{issue.message}" for issue in self.issues)
        super().__init__("Runtime Bundle validation failed: " + detail)


@dataclass(frozen=True, slots=True)
class ValidatedRuntimeBundle:
    project_root: Path
    manifest_path: Path
    manifest_sha256: str
    manifest: Mapping[str, Any]
    documents: Mapping[Path, Mapping[str, Any]]

    @property
    def entrypoint_path(self) -> Path:
        return (self.project_root / str(self.manifest["entrypoint"]["path"])).resolve()


def _read_only(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _read_only(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_read_only(item) for item in value)
    return value


def _normalized_hash(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.lower().removeprefix("sha256:")
    if len(normalized) != 64:
        return None
    try:
        int(normalized, 16)
    except ValueError:
        return None
    return normalized


def _ref_edge(
    source: str,
    value: object,
    relation: str,
    *,
    path_key: str = "document_path",
    hash_key: str = "content_hash",
) -> tuple[tuple[str, str, str], tuple[str, str]] | None:
    if not isinstance(value, Mapping):
        return None
    path = value.get(path_key)
    digest = _normalized_hash(value.get(hash_key))
    if not isinstance(path, str) or digest is None:
        return None
    return (source, path, relation), (path, digest)


def _derived_edges(
    documents: Mapping[str, Mapping[str, Any]], kinds: Mapping[str, str]
) -> tuple[set[tuple[str, str, str]], list[tuple[str, str]]]:
    edges: set[tuple[str, str, str]] = set()
    pins: list[tuple[str, str]] = []
    for source, document in documents.items():
        kind = kinds[source]
        refs: list[tuple[object, str, str, str]] = []
        if kind == "resolved_capability_snapshot":
            refs.extend(
                [
                    (document.get("task_ref"), "snapshot-task", "document_path", "content_hash"),
                    (document.get("method_resolution_ref"), "snapshot-method", "document_path", "content_hash"),
                    (document.get("requirement_ref"), "snapshot-requirement", "document_path", "content_hash"),
                    (document.get("resolution_ref"), "snapshot-resolution", "document_path", "content_hash"),
                    (document.get("selected_supply_report_ref"), "snapshot-supply", "document_path", "content_hash"),
                ]
            )
            for value in document.get("conformance_evidence_refs", ()):
                refs.append((value, "snapshot-conformance", "path", "sha256"))
        elif kind == "capability_resolution":
            refs.extend(
                [
                    (document.get("method_resolution_ref"), "resolution-method", "document_path", "content_hash"),
                    (document.get("requirement_ref"), "resolution-requirement", "document_path", "content_hash"),
                ]
            )
            for value in document.get("candidate_supply_report_refs", ()):
                refs.append((value, "resolution-candidate-supply", "document_path", "content_hash"))
        elif kind == "capability_supply_report":
            for evidence in document.get("conformance_evidence", ()):
                if isinstance(evidence, Mapping):
                    refs.append((evidence.get("artifact_ref"), "supply-conformance", "path", "sha256"))
        for value, relation, path_key, hash_key in refs:
            item = _ref_edge(source, value, relation, path_key=path_key, hash_key=hash_key)
            if item is not None:
                edge, pin = item
                edges.add(edge)
                pins.append(pin)
    method_paths = [path for path, kind in kinds.items() if kind == "method_resolution"]
    task_paths = [path for path, kind in kinds.items() if kind == "task_packet"]
    if len(method_paths) == 1 and len(task_paths) == 1:
        method_path, task_path = method_paths[0], task_paths[0]
        method = documents[method_path]
        task = documents[task_path]
        task_ref = method.get("task_ref")
        if isinstance(task_ref, Mapping):
            expected = _normalized_hash(task_ref.get("sha256"))
            if expected is not None:
                edges.add((method_path, task_path, "method-task"))
                pins.append((task_path, expected))
            if task_ref.get("task_id") != task.get("task_id") or task_ref.get("revision") != task.get("revision"):
                pins.append((task_path, "identity-mismatch"))
    return edges, pins


def _revisioned_identity(document: Mapping[str, Any], identity_key: str) -> str:
    return f"{document.get(identity_key)}@r{document.get('revision')}"


def _versioned_identity(document: Mapping[str, Any], identity_key: str) -> str:
    return f"{document.get(identity_key)}@{document.get('version')}"


def _validate_lineage(
    root: Path,
    documents: Mapping[str, Mapping[str, Any]],
    kinds: Mapping[str, str],
) -> list[RuntimeBundleIssue]:
    issues: list[RuntimeBundleIssue] = []
    by_kind = {
        kind: [(path, documents[path]) for path, actual_kind in kinds.items() if actual_kind == kind]
        for kind in ALLOWED_KINDS
    }
    singleton_kinds = {
        "task_packet",
        "method_resolution",
        "capability_requirement",
        "capability_supply_report",
        "capability_resolution",
        "resolved_capability_snapshot",
    }
    for kind in singleton_kinds:
        if len(by_kind[kind]) != 1:
            issues.append(
                RuntimeBundleIssue(
                    root,
                    "RUNTIME-BUNDLE-CARDINALITY",
                    f"Core bundle requires exactly one {kind}; found {len(by_kind[kind])}",
                )
            )
    if any(len(by_kind[kind]) != 1 for kind in singleton_kinds):
        return issues

    task_path, task = by_kind["task_packet"][0]
    method_path, method = by_kind["method_resolution"][0]
    requirement_path, requirement = by_kind["capability_requirement"][0]
    supply_path, supply = by_kind["capability_supply_report"][0]
    resolution_path, resolution = by_kind["capability_resolution"][0]
    snapshot_path, snapshot = by_kind["resolved_capability_snapshot"][0]

    task_revision = task.get("revision", 1)
    expected_task_ref = f"{task.get('task_id')}@r{task_revision}"
    method_task_ref = method.get("task_ref", {})
    if not isinstance(method_task_ref, Mapping) or (
        method_task_ref.get("task_id") != task.get("task_id")
        or method_task_ref.get("revision") != task_revision
    ):
        issues.append(
            RuntimeBundleIssue(
                root / method_path,
                "RUNTIME-BUNDLE-TASK-IDENTITY-MISMATCH",
                expected_task_ref,
            )
        )

    expected_method_ref = _revisioned_identity(method, "resolution_id")
    expected_resolution_ref = _revisioned_identity(resolution, "resolution_id")
    expected_requirement_id = requirement.get("requirement_id")
    expected_supply_ref = _versioned_identity(supply, "report_id")

    resolution_method_ref = resolution.get("method_resolution_ref", {})
    resolution_requirement_ref = resolution.get("requirement_ref", {})
    candidate_refs = resolution.get("candidate_supply_report_refs", ())
    candidate_identities = {
        item.get("ref") for item in candidate_refs if isinstance(item, Mapping)
    }
    if not isinstance(resolution_method_ref, Mapping) or resolution_method_ref.get("ref") != expected_method_ref:
        issues.append(
            RuntimeBundleIssue(
                root / resolution_path,
                "RUNTIME-BUNDLE-METHOD-IDENTITY-MISMATCH",
                expected_method_ref,
            )
        )
    if not isinstance(resolution_requirement_ref, Mapping) or (
        resolution_requirement_ref.get("requirement_id") != expected_requirement_id
    ):
        issues.append(
            RuntimeBundleIssue(
                root / resolution_path,
                "RUNTIME-BUNDLE-REQUIREMENT-IDENTITY-MISMATCH",
                str(expected_requirement_id),
            )
        )
    if candidate_identities != {expected_supply_ref}:
        issues.append(
            RuntimeBundleIssue(
                root / resolution_path,
                "RUNTIME-BUNDLE-SUPPLY-IDENTITY-MISMATCH",
                expected_supply_ref,
            )
        )
    if resolution.get("resolution_status") != "satisfied" or resolution.get("selected_supply_report_ref") != expected_supply_ref:
        issues.append(
            RuntimeBundleIssue(
                root / resolution_path,
                "RUNTIME-BUNDLE-RESOLUTION-NOT-SATISFIED",
                "Runtime Core requires one deterministically selected Supply Report",
            )
        )

    method_requirements = {
        item
        for decision in method.get("action_decisions", ())
        if isinstance(decision, Mapping)
        for item in decision.get("capability_requirements", ())
        if isinstance(item, str)
    }
    if expected_requirement_id not in method_requirements:
        issues.append(
            RuntimeBundleIssue(
                root / requirement_path,
                "RUNTIME-BUNDLE-METHOD-REQUIREMENT-MISSING",
                str(expected_requirement_id),
            )
        )

    expected_snapshot_refs = {
        "task_ref": expected_task_ref,
        "method_resolution_ref": expected_method_ref,
        "resolution_ref": expected_resolution_ref,
    }
    for field, expected in expected_snapshot_refs.items():
        reference = snapshot.get(field, {})
        if not isinstance(reference, Mapping) or reference.get("ref") != expected:
            issues.append(
                RuntimeBundleIssue(
                    root / snapshot_path,
                    "RUNTIME-BUNDLE-SNAPSHOT-IDENTITY-MISMATCH",
                    f"{field} must identify {expected}",
                )
            )
    snapshot_requirement = snapshot.get("requirement_ref", {})
    if not isinstance(snapshot_requirement, Mapping) or snapshot_requirement.get("requirement_id") != expected_requirement_id:
        issues.append(
            RuntimeBundleIssue(
                root / snapshot_path,
                "RUNTIME-BUNDLE-SNAPSHOT-IDENTITY-MISMATCH",
                f"requirement_ref must identify {expected_requirement_id}",
            )
        )
    snapshot_supply = snapshot.get("selected_supply_report_ref", {})
    if not isinstance(snapshot_supply, Mapping) or snapshot_supply.get("ref") != expected_supply_ref:
        issues.append(
            RuntimeBundleIssue(
                root / snapshot_path,
                "RUNTIME-BUNDLE-SNAPSHOT-IDENTITY-MISMATCH",
                f"selected_supply_report_ref must identify {expected_supply_ref}",
            )
        )
    if snapshot.get("method_resolution_ref") != resolution.get("method_resolution_ref") or snapshot.get(
        "requirement_ref"
    ) != resolution.get("requirement_ref"):
        issues.append(
            RuntimeBundleIssue(
                root / snapshot_path,
                "RUNTIME-BUNDLE-SNAPSHOT-LINEAGE-DRIFT",
                "Snapshot Method and Requirement refs must equal Resolution refs",
            )
        )
    copied_supply_fields = {
        "supply_identity": "supply_identity",
        "supply_required_permissions": "required_permissions",
        "supply_data_egress": "data_egress_behavior",
        "supply_side_effects": "side_effects",
    }
    for snapshot_field, supply_field in copied_supply_fields.items():
        if snapshot.get(snapshot_field) != supply.get(supply_field):
            issues.append(
                RuntimeBundleIssue(
                    root / snapshot_path,
                    "RUNTIME-BUNDLE-SUPPLY-FACT-DRIFT",
                    f"{snapshot_field} must equal Supply Report {supply_field}",
                )
            )
    expected_evidence_refs = [
        item.get("artifact_ref")
        for item in supply.get("conformance_evidence", ())
        if isinstance(item, Mapping)
    ]
    if snapshot.get("conformance_evidence_refs") != expected_evidence_refs:
        issues.append(
            RuntimeBundleIssue(
                root / snapshot_path,
                "RUNTIME-BUNDLE-EVIDENCE-LINEAGE-DRIFT",
                "Snapshot evidence refs must equal Supply Report evidence refs",
            )
        )
    evidence_ids = {
        document.get("evidence_id")
        for _, document in by_kind["capability_conformance_evidence"]
    }
    supply_evidence_ids = {
        item.get("evidence_id")
        for item in supply.get("conformance_evidence", ())
        if isinstance(item, Mapping)
    }
    if evidence_ids != supply_evidence_ids:
        issues.append(
            RuntimeBundleIssue(
                root / supply_path,
                "RUNTIME-BUNDLE-EVIDENCE-IDENTITY-MISMATCH",
                "Supply evidence identities must equal the explicit evidence closure",
            )
        )
    return issues


def load_runtime_bundle(
    manifest_path: str | Path,
    *,
    project_root: str | Path = ".",
    schema_root: str | Path | None = None,
) -> ValidatedRuntimeBundle:
    root = Path(project_root).resolve()
    candidate = Path(manifest_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if candidate.is_dir():
        raise RuntimeBundleValidationError(
            (RuntimeBundleIssue(candidate, "RUNTIME-BUNDLE-DIRECTORY-INPUT", "manifest input must be one file"),)
        )
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Runtime Bundle manifest escapes project root: {manifest_path}") from exc
    if not candidate.is_file():
        raise FileNotFoundError(candidate)

    catalog = SchemaCatalog(schema_root)
    try:
        manifest_content = candidate.read_bytes()
        manifest_raw = load_document_bytes(candidate, manifest_content)
    except Exception as exc:
        raise RuntimeBundleValidationError(
            (RuntimeBundleIssue(candidate, "RUNTIME-BUNDLE-MANIFEST-PARSE", str(exc)),)
        ) from exc
    if not isinstance(manifest_raw, Mapping):
        raise RuntimeBundleValidationError(
            (RuntimeBundleIssue(candidate, "RUNTIME-BUNDLE-MANIFEST-SHAPE", "manifest must be an object"),)
        )
    manifest_errors = catalog.validate("runtime_bundle_manifest", manifest_raw)
    if manifest_errors:
        raise RuntimeBundleValidationError(
            RuntimeBundleIssue(candidate, "RUNTIME-BUNDLE-MANIFEST-SCHEMA", f"{item.pointer}: {item.message}")
            for item in manifest_errors
        )

    issues: list[RuntimeBundleIssue] = []
    documents: dict[str, Mapping[str, Any]] = {}
    kinds: dict[str, str] = {}
    hashes: dict[str, str] = {}
    for reference in manifest_raw["documents"]:
        relative = str(reference["path"])
        kind = str(reference["kind"])
        if relative in documents:
            issues.append(RuntimeBundleIssue(candidate, "RUNTIME-BUNDLE-DUPLICATE-PATH", relative))
            continue
        if kind not in ALLOWED_KINDS:
            issues.append(RuntimeBundleIssue(candidate, "RUNTIME-BUNDLE-KIND-FORBIDDEN", kind))
            continue
        path = resolve_within_root(root, relative)
        if path is None:
            issues.append(RuntimeBundleIssue(candidate, "RUNTIME-BUNDLE-PATH-ESCAPE", relative))
            continue
        if not path.is_file():
            code = "RUNTIME-BUNDLE-DIRECTORY-INPUT" if path.is_dir() else "RUNTIME-BUNDLE-DOCUMENT-MISSING"
            issues.append(RuntimeBundleIssue(path, code, relative))
            continue
        content = path.read_bytes()
        actual_hash = hash_bytes(content)
        expected_hash = _normalized_hash(reference["sha256"])
        if actual_hash != expected_hash:
            issues.append(RuntimeBundleIssue(path, "RUNTIME-BUNDLE-HASH-MISMATCH", relative))
            continue
        try:
            document = load_document_bytes(path, content)
        except Exception as exc:
            issues.append(RuntimeBundleIssue(path, "RUNTIME-BUNDLE-DOCUMENT-PARSE", str(exc)))
            continue
        schema_errors = catalog.validate(kind, document)
        if schema_errors:
            issues.extend(
                RuntimeBundleIssue(path, "RUNTIME-BUNDLE-DOCUMENT-SCHEMA", f"{item.pointer}: {item.message}")
                for item in schema_errors
            )
            continue
        assert isinstance(document, Mapping)
        documents[relative] = document
        kinds[relative] = kind
        hashes[relative] = actual_hash

    entrypoint = manifest_raw["entrypoint"]
    entrypoint_path = str(entrypoint["path"])
    entrypoint_hash = _normalized_hash(entrypoint["sha256"])
    if kinds.get(entrypoint_path) != "resolved_capability_snapshot" or hashes.get(entrypoint_path) != entrypoint_hash:
        issues.append(RuntimeBundleIssue(candidate, "RUNTIME-BUNDLE-ENTRYPOINT-MISMATCH", entrypoint_path))

    for relative, document in documents.items():
        kind = kinds[relative]
        if kind in {"capability_resolution", "resolved_capability_snapshot"} and document.get("qualification") != "runtime-execution":
            issues.append(RuntimeBundleIssue(root / relative, "RUNTIME-BUNDLE-STRUCTURAL-REPLAY", kind))
        if kind == "capability_conformance_evidence" and document.get("evidence_kind") == "deterministic-fixture":
            issues.append(RuntimeBundleIssue(root / relative, "RUNTIME-BUNDLE-FIXTURE-EVIDENCE", "live/local evidence required"))
        if kind == "capability_supply_report":
            identity = document.get("supply_identity", {})
            availability = document.get("availability", {})
            if isinstance(identity, Mapping) and (
                identity.get("supply_kind") == "skill"
                or any(isinstance(item, Mapping) and item.get("component_kind") == "skill" for item in identity.get("components", ()))
            ):
                issues.append(RuntimeBundleIssue(root / relative, "RUNTIME-BUNDLE-SKILL-FORBIDDEN", "Core bundle is zero-Skill"))
            if isinstance(availability, Mapping) and availability.get("scope", {}).get("scope_kind") == "fixture-only":
                issues.append(RuntimeBundleIssue(root / relative, "RUNTIME-BUNDLE-FIXTURE-AVAILABILITY", "fixture-only availability is not runtime input"))
        if kind == "method_resolution" and document.get("skill_disposition", {}).get("status") != "no-skill":
            issues.append(RuntimeBundleIssue(root / relative, "RUNTIME-BUNDLE-SKILL-FORBIDDEN", "Core requires no-skill Method disposition"))

    issues.extend(_validate_lineage(root, documents, kinds))

    derived_edges, pins = _derived_edges(documents, kinds)
    declared_edges = {
        (str(item["from_path"]), str(item["to_path"]), str(item["relation"]))
        for item in manifest_raw["imports"]
    }
    if declared_edges != derived_edges:
        issues.append(RuntimeBundleIssue(candidate, "RUNTIME-BUNDLE-IMPORT-GRAPH-MISMATCH", "declared imports must equal the derived closure"))
    declared_paths = set(documents)
    for path, expected in pins:
        if path not in declared_paths:
            issues.append(RuntimeBundleIssue(candidate, "RUNTIME-BUNDLE-UNDECLARED-IMPORT", path))
        elif expected == "identity-mismatch":
            issues.append(RuntimeBundleIssue(root / path, "RUNTIME-BUNDLE-TASK-IDENTITY-MISMATCH", path))
        elif hashes.get(path) != expected:
            issues.append(RuntimeBundleIssue(root / path, "RUNTIME-BUNDLE-REF-HASH-MISMATCH", path))
    reachable = {entrypoint_path}
    changed = True
    while changed:
        changed = False
        for source, target, _ in derived_edges:
            if source in reachable and target not in reachable:
                reachable.add(target)
                changed = True
    if reachable != declared_paths:
        issues.append(RuntimeBundleIssue(candidate, "RUNTIME-BUNDLE-CLOSURE-MISMATCH", "documents must be the exact entrypoint closure"))
    if issues:
        raise RuntimeBundleValidationError(issues)

    frozen_documents = MappingProxyType(
        {(root / path).resolve(): _read_only(document) for path, document in documents.items()}
    )
    frozen_manifest = _read_only(manifest_raw)
    assert isinstance(frozen_manifest, Mapping)
    return ValidatedRuntimeBundle(
        root,
        candidate,
        hash_bytes(manifest_content),
        frozen_manifest,
        frozen_documents,
    )


__all__ = [
    "RuntimeBundleIssue",
    "RuntimeBundleValidationError",
    "ValidatedRuntimeBundle",
    "load_runtime_bundle",
]
