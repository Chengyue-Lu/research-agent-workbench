from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from research_workbench.artifacts.integrity import hash_file, resolve_within_root
from research_workbench.contracts.common import ContractError, require_relative_path
from research_workbench.io import load_document
from research_workbench.protocol.models import ResearchMode


RESEARCH_MODE_MIGRATION_ID = "research-mode-v0.1-to-v0.2"
RESEARCH_MODE_MIGRATION_VERSION = "1.0.0"
RESEARCH_MODE_ACTION_REF_MIGRATIONS_V1: dict[
    str, tuple[tuple[str, str], ...]
] = {
    mode_id: tuple(
        (f"{prefix}-A{index}@1.0.0", f"{prefix}-A{index}@2.0.0")
        for index in range(1, 9)
    )
    for mode_id, prefix in (
        ("evidence-synthesis", "ES"),
        ("simulation", "SIM"),
    )
}


def _action_entries_by_ref(
    action_registry: Mapping[str, Any]
) -> dict[str, Mapping[str, Any]]:
    if action_registry.get("registry_kind") != "mode_action_registry":
        raise ContractError("action_registry", "must be a Mode Action Registry")
    result: dict[str, Mapping[str, Any]] = {}
    entries = action_registry.get("entries")
    if not isinstance(entries, list):
        raise ContractError("action_registry.entries", "must be an array")
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise ContractError(f"action_registry.entries[{index}]", "must be an object")
        action_id = entry.get("action_id")
        version = entry.get("version")
        if not isinstance(action_id, str) or not action_id or not isinstance(version, str):
            raise ContractError(
                f"action_registry.entries[{index}]",
                "must contain action_id and version",
            )
        action_ref = f"{action_id}@{version}"
        if action_ref in result:
            raise ContractError("action_registry.entries", f"duplicate Action ref: {action_ref}")
        result[action_ref] = entry
    if not result:
        raise ContractError("action_registry.entries", "must contain at least one Action")
    return result


def research_mode_action_migrations(
    source_mode_ref: str,
    target_mode_ref: str,
    action_registry: Mapping[str, Any],
) -> tuple[tuple[Mapping[str, Any], Mapping[str, Any]], ...]:
    source_mode_id = source_mode_ref.partition("@")[0]
    target_mode_id = target_mode_ref.partition("@")[0]
    if source_mode_id != target_mode_id:
        raise ContractError("mode_ref", "source and target Mode IDs must match")
    pairs = RESEARCH_MODE_ACTION_REF_MIGRATIONS_V1.get(source_mode_id)
    if pairs is None:
        raise ContractError("mode_ref", f"unsupported Research Mode migration: {source_mode_id}")
    entries = _action_entries_by_ref(action_registry)
    result: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    for source_ref, target_ref in pairs:
        source = entries.get(source_ref)
        target = entries.get(target_ref)
        if source is None or target is None:
            raise ContractError(
                "action_registry.entries",
                f"migration-pinned Action is missing: {source_ref} -> {target_ref}",
            )
        if source.get("mode_ref") != source_mode_ref or target.get("mode_ref") != target_mode_ref:
            raise ContractError("action_registry.entries", "migration-pinned Action belongs to the wrong Mode revision")
        result.append((source, target))
    return tuple(result)


def migrate_research_mode_v01_to_v02(
    source_mode: Mapping[str, Any],
    target_action_refs: list[str] | tuple[str, ...],
    action_registry: Mapping[str, Any],
) -> dict[str, Any]:
    parsed = ResearchMode.from_mapping(source_mode)
    if parsed.version != "0.1.0":
        raise ContractError("version", "migration source must be Research Mode v0.1.0")
    target_ref = f"{parsed.mode_id}@0.2.0"
    entries = _action_entries_by_ref(action_registry)
    if not target_action_refs or len(target_action_refs) != len(set(target_action_refs)):
        raise ContractError("target_action_refs", "must be a non-empty unique exact Action ref list")
    for action_ref in target_action_refs:
        entry = entries.get(action_ref)
        if entry is None:
            raise ContractError("target_action_refs", f"Action is not in the Registry: {action_ref}")
        if entry.get("mode_ref") != target_ref:
            raise ContractError("target_action_refs", f"Action belongs to the wrong Mode revision: {action_ref}")

    target: dict[str, Any] = {}
    for key, value in source_mode.items():
        if key == "version":
            target[key] = "0.2.0"
        elif key == "recommended_skill_capabilities":
            target["action_refs"] = list(target_action_refs)
        else:
            target[key] = deepcopy(value)
    if "action_refs" not in target:
        target["action_refs"] = list(target_action_refs)
    ResearchMode.from_mapping(target)
    return target


def _resolved_repository_file(root: Path, relative_path: str, field: str) -> Path:
    require_relative_path(relative_path, field)
    resolved = resolve_within_root(root, relative_path)
    if resolved is None or not resolved.is_file():
        raise ContractError(field, "must resolve to an existing file within the repository")
    return resolved


def build_research_mode_migration_record(
    *,
    root: str | Path,
    migration_id: str,
    source_mode_path: str,
    target_mode_path: str,
    action_registry_path: str = "registry/modes/actions.json",
) -> dict[str, Any]:
    repository_root = Path(root).resolve()
    source_path = _resolved_repository_file(repository_root, source_mode_path, "source_mode_path")
    target_path = _resolved_repository_file(repository_root, target_mode_path, "target_mode_path")
    registry_path = _resolved_repository_file(
        repository_root, action_registry_path, "action_registry_path"
    )
    source_mode = load_document(source_path)
    target_mode = load_document(target_path)
    action_registry = load_document(registry_path)
    if not isinstance(source_mode, Mapping) or not isinstance(target_mode, Mapping):
        raise ContractError("mode", "source and target Mode documents must be objects")
    if not isinstance(action_registry, Mapping):
        raise ContractError("action_registry", "must be an object")
    target_action_refs = target_mode.get("action_refs")
    if not isinstance(target_action_refs, list) or not all(
        isinstance(value, str) for value in target_action_refs
    ):
        raise ContractError("target_mode.action_refs", "must be an exact Action ref list")
    expected_target = migrate_research_mode_v01_to_v02(
        source_mode, target_action_refs, action_registry
    )
    if dict(target_mode) != expected_target:
        raise ContractError("target_mode", "does not match the deterministic migration result")

    source_ref = f"{source_mode['mode_id']}@{source_mode['version']}"
    target_ref = f"{target_mode['mode_id']}@{target_mode['version']}"
    action_migrations = []
    for source, target in research_mode_action_migrations(
        source_ref, target_ref, action_registry
    ):
        action_migrations.append(
            {
                "source": {
                    "ref": f"{source['action_id']}@{source['version']}",
                    "document_path": source["document_path"],
                    "content_hash": source["content_hash"],
                },
                "target": {
                    "ref": f"{target['action_id']}@{target['version']}",
                    "document_path": target["document_path"],
                    "content_hash": target["content_hash"],
                },
            }
        )

    preserved_fields = [
        key
        for key in source_mode
        if key not in {"version", "recommended_skill_capabilities"}
    ]
    return {
        "schema_version": "0.1.0",
        "migration_kind": "research_mode_migration",
        "migration_id": migration_id,
        "migration_version": RESEARCH_MODE_MIGRATION_VERSION,
        "implementation": {
            "id": RESEARCH_MODE_MIGRATION_ID,
            "version": RESEARCH_MODE_MIGRATION_VERSION,
        },
        "source_mode": {
            "ref": source_ref,
            "document_path": source_mode_path,
            "content_hash": f"sha256:{hash_file(source_path)}",
        },
        "target_mode": {
            "ref": target_ref,
            "document_path": target_mode_path,
            "content_hash": f"sha256:{hash_file(target_path)}",
        },
        "action_migrations": action_migrations,
        "preserved_fields": preserved_fields,
        "removed_fields": ["recommended_skill_capabilities"],
        "added_fields": ["action_refs"],
        "limitations": [
            "The migration records structural lineage only and does not prove scientific validity.",
            "Historical Method Resolutions remain pinned to Research Mode v0.1 and Action v1 documents.",
        ],
    }
