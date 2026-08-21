from __future__ import annotations

from typing import Any, Mapping, Sequence

from research_workbench.contracts.common import ContractError, require_string
from research_workbench.method.models import canonical_document_sha256


def migrate_research_mode_v01_to_v02(
    document: Mapping[str, Any],
    *,
    action_refs: Sequence[Mapping[str, Any]],
    migration_id: str,
) -> dict[str, Any]:
    """Create a new v0.2 Mode document; never mutate or reinterpret v0.1 in place."""

    if document.get("schema_version") != "0.1.0" or document.get("version") != "0.1.0":
        raise ContractError("schema_version", "migration input must be Research Mode v0.1.0")
    if not action_refs:
        raise ContractError("action_refs", "migration requires at least one frozen Mode Action")
    mode_id = require_string(document, "mode_id")
    normalized_refs: list[dict[str, Any]] = []
    for index, reference in enumerate(action_refs):
        if reference.get("mode_id") != mode_id:
            raise ContractError(f"action_refs[{index}].mode_id", "must match the migrated Mode")
        normalized_refs.append(dict(reference))

    return {
        "schema_version": "0.2.0",
        "mode_id": mode_id,
        "version": "0.2.0",
        "applies_when": list(document.get("applies_when", [])),
        "action_refs": normalized_refs,
        "claim_rules": dict(document.get("claim_rules", {})),
        "human_decisions": list(document.get("human_decisions", [])),
        "risk_rules": list(document.get("risk_rules", [])),
        "migration": {
            "migration_id": migration_id,
            "source_schema_version": "0.1.0",
            "source_mode_version": "0.1.0",
            "source_hash": canonical_document_sha256(document),
            "implementation": "research_workbench.method.migration:migrate_research_mode_v01_to_v02",
        },
    }
