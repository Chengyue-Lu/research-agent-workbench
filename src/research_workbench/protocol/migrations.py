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


def _action_entries_for_mode(
    action_registry: Mapping[str, Any], mode_ref: str
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
        if entry.get("mode_ref") != mode_ref:
            continue
        action_id = entry.get("action_id")
        version = entry.get("version")
        if not isinstance(action_id, str) or not action_id or not isinstance(version, str):
            raise ContractError(
                f"action_registry.entries[{index}]",
                "must contain action_id and version",
            )
        if action_id in result:
            raise ContractError("action_registry.entries", f"duplicate action_id for {mode_ref}: {action_id}")
        result[action_id] = entry
    if not result:
        raise ContractError("action_registry.entries", f"no actions found for {mode_ref}")
    return result


def research_mode_action_migrations(
    source_mode_ref: str,
    target_mode_ref: str,
    action_registry: Mapping[str, Any],
) -> tuple[tuple[Mapping[str, Any], Mapping[str, Any]], ...]:
    source_entries = _action_entries_for_mode(action_registry, source_mode_ref)
    target_entries = _action_entries_for_mode(action_registry, target_mode_ref)
    if set(source_entries) != set(target_entries):
        raise ContractError(
            "action_registry.entries",
            "source and target Mode revisions must expose the same Action IDs",
        )
    result: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    for action_id in sorted(source_entries):
        source = source_entries[action_id]
        target = target_entries[action_id]
        if source.get("version") == target.get("version"):
            raise ContractError(
                "action_registry.entries",
                f"Action {action_id} must publish a new version for the target Mode revision",
            )
        result.append((source, target))
    return tuple(result)


def migrate_research_mode_v01_to_v02(
    source_mode: Mapping[str, Any], action_registry: Mapping[str, Any]
) -> dict[str, Any]:
    parsed = ResearchMode.from_mapping(source_mode)
    if parsed.version != "0.1.0":
        raise ContractError("version", "migration source must be Research Mode v0.1.0")
    source_ref = f"{parsed.mode_id}@0.1.0"
    target_ref = f"{parsed.mode_id}@0.2.0"
    action_migrations = research_mode_action_migrations(
        source_ref, target_ref, action_registry
    )
    target_action_refs = [
        f"{target['action_id']}@{target['version']}"
        for _, target in action_migrations
    ]

    target: dict[str, Any] = {}
    for key, value in source_mode.items():
        if key == "version":
            target[key] = "0.2.0"
        elif key == "recommended_skill_capabilities":
            target["action_refs"] = target_action_refs
        else:
            target[key] = deepcopy(value)
    if "action_refs" not in target:
        target["action_refs"] = target_action_refs
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
    expected_target = migrate_research_mode_v01_to_v02(source_mode, action_registry)
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
