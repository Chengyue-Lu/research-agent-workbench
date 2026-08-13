"""Deterministic coverage checks for compressed subagent Handoffs.

The assessor proves reference and transfer coverage. It never infers semantic
equivalence from matching structure; a bounded human review records that claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from research_workbench.artifacts.integrity import hash_file, resolve_within_root
from research_workbench.contracts import ContractError, ContractRisk, RiskLevel
from research_workbench.io import load_document
from research_workbench.tasks import HandoffPacket, TaskPacket
from research_workbench.validation.relationships import check_handoff_against_task
from research_workbench.validation.schemas import SchemaCatalog


RISK_REVIEW_KINDS = {
    "assumption",
    "conflict",
    "human-decision",
    "method-boundary",
    "negative-result",
}

KIND_LOCATOR_PREFIXES: Mapping[str, tuple[str, ...]] = {
    "fact": ("/result/facts/",),
    "inference": ("/result/inferences/",),
    "recommendation": ("/result/recommendations/", "/recommended_next_actions/"),
    "limitation": ("/limitations/",),
    "conflict": ("/conflicts/",),
    "unresolved": ("/unresolved/",),
    "human-decision": ("/human_decision_required/",),
    "negative-result": ("/result/facts/", "/limitations/", "/unresolved/"),
    "parameter": ("/result/facts/",),
    "assumption": ("/result/facts/", "/limitations/"),
    "method-boundary": ("/result/inferences/", "/limitations/"),
}


@dataclass(frozen=True, slots=True)
class HandoffTransferAssessment:
    verdict: str
    review_required: bool
    risks: tuple[ContractRisk, ...]


def assess_handoff_transfer(
    document: Mapping[str, Any], *, root: str | Path = "."
) -> HandoffTransferAssessment:
    project_root = Path(root).resolve()
    risks: list[ContractRisk] = []
    audit_errors = SchemaCatalog().validate("handoff_transfer_audit", document)
    if audit_errors:
        first = audit_errors[0]
        risks.append(
            _block(
                "HANDOFF-AUDIT-CONTRACT",
                f"Transfer Audit is invalid at {first.pointer}: {first.message}",
            )
        )
        return HandoffTransferAssessment("not-transfer-ready", False, tuple(risks))
    task_value = _load_document_ref(
        project_root,
        _mapping(document.get("task_ref")),
        "task_packet",
        "Task",
        risks,
    )
    handoff_value = _load_document_ref(
        project_root,
        _mapping(document.get("handoff_ref")),
        "handoff_packet",
        "Handoff",
        risks,
    )
    manifest_value = _load_document_ref(
        project_root,
        _mapping(document.get("manifest_ref")),
        "handoff_transfer_manifest",
        "Transfer Manifest",
        risks,
    )
    if task_value is None or handoff_value is None or manifest_value is None:
        return HandoffTransferAssessment("not-transfer-ready", False, tuple(risks))

    try:
        task = TaskPacket.from_mapping(task_value)
        handoff = HandoffPacket.from_mapping(handoff_value)
    except ContractError as exc:
        risks.append(_block("HANDOFF-AUDIT-CONTRACT", f"linked Task or Handoff is invalid: {exc}"))
        return HandoffTransferAssessment("not-transfer-ready", False, tuple(risks))

    risks.extend(check_handoff_against_task(task, handoff, project_root=project_root))
    manifest_path = _mapping(document.get("manifest_ref")).get("path")
    if handoff.transfer_manifest_ref != manifest_path:
        risks.append(
            _block(
                "HANDOFF-AUDIT-MANIFEST-DRIFT",
                "Handoff does not point to the audited Transfer Manifest",
            )
        )
    if (
        manifest_value.get("task_id") != task.task_id
        or manifest_value.get("task_revision") != task.revision
        or manifest_value.get("attempt_id") != handoff.attempt_id
    ):
        risks.append(
            _block(
                "HANDOFF-AUDIT-IDENTITY-DRIFT",
                "Transfer Manifest, Task, and Handoff identify different work",
            )
        )

    source_refs = [
        item for item in manifest_value.get("source_artifact_refs", []) if isinstance(item, Mapping)
    ]
    source_identities = {_ref_identity(item) for item in source_refs}
    for index, source_ref in enumerate(source_refs):
        risks.extend(_check_file_ref(project_root, source_ref, f"source artifact[{index}]"))
        if source_ref.get("path") not in handoff.artifact_refs:
            risks.append(
                _block(
                    "HANDOFF-AUDIT-SOURCE-NOT-INDEXED",
                    f"source artifact is absent from Handoff artifact_refs: {source_ref.get('path')}",
                )
            )

    item_values = [item for item in manifest_value.get("items", []) if isinstance(item, Mapping)]
    items: dict[str, Mapping[str, Any]] = {}
    for item in item_values:
        item_id = str(item.get("item_id", ""))
        if item_id in items:
            risks.append(_block("HANDOFF-AUDIT-ITEM-DUPLICATE", f"duplicate item_id: {item_id}"))
        items[item_id] = item
        source_ref = _mapping(item.get("source_ref"))
        if _ref_identity(source_ref) not in source_identities:
            risks.append(
                _block(
                    "HANDOFF-AUDIT-SOURCE-UNDECLARED",
                    f"{item_id}: source_ref is not frozen in source_artifact_refs",
                )
            )
        risks.extend(_check_file_ref(project_root, source_ref, f"{item_id} source"))
        source_path = source_ref.get("path")
        source_locator = item.get("source_locator")
        if isinstance(source_path, str) and isinstance(source_locator, str) and source_locator.startswith("/"):
            resolved_source = resolve_within_root(project_root, source_path)
            source_value = (
                load_document(resolved_source)
                if resolved_source is not None
                and resolved_source.is_file()
                and resolved_source.suffix.lower() in {".json", ".yaml", ".yml"}
                else _MISSING
            )
            if source_value is _MISSING or _resolve_pointer(source_value, source_locator) is _MISSING:
                risks.append(
                    _block(
                        "HANDOFF-AUDIT-SOURCE-LOCATOR-INVALID",
                        f"{item_id}: source locator does not resolve",
                    )
                )

    mapping_values = [item for item in document.get("mappings", []) if isinstance(item, Mapping)]
    mappings: dict[str, Mapping[str, Any]] = {}
    carried_locators: set[str] = set()
    for mapping in mapping_values:
        item_id = str(mapping.get("item_id", ""))
        if item_id in mappings:
            risks.append(_block("HANDOFF-AUDIT-MAPPING-DUPLICATE", f"duplicate mapping: {item_id}"))
        mappings[item_id] = mapping
        item = items.get(item_id)
        if item is None:
            risks.append(_block("HANDOFF-AUDIT-MAPPING-UNKNOWN", f"mapping references unknown item: {item_id}"))
            continue
        if mapping.get("status") == "omitted-with-reason":
            if item.get("required_for_handoff"):
                risks.append(
                    _block("HANDOFF-AUDIT-REQUIRED-OMITTED", f"required item was omitted: {item_id}")
                )
            continue
        locator = mapping.get("handoff_locator")
        if not isinstance(locator, str) or _resolve_pointer(handoff_value, locator) is _MISSING:
            risks.append(
                _block("HANDOFF-AUDIT-LOCATOR-INVALID", f"{item_id}: invalid Handoff locator {locator!r}")
            )
            continue
        allowed = KIND_LOCATOR_PREFIXES.get(str(item.get("kind")), ())
        if not any(locator.startswith(prefix) for prefix in allowed):
            risks.append(
                _block(
                    "HANDOFF-AUDIT-SECTION-DRIFT",
                    f"{item_id}: {item.get('kind')} maps to an incompatible Handoff section",
                )
            )
        carried_locators.add(locator)

    missing_mappings = sorted(set(items) - set(mappings))
    if missing_mappings:
        risks.append(
            _block(
                "HANDOFF-AUDIT-COVERAGE",
                "manifest items have no Handoff mapping: " + ", ".join(missing_mappings),
            )
        )
    risks.extend(_check_negative_section_coverage(handoff_value, carried_locators))

    required_items = {
        item_id: item
        for item_id, item in items.items()
        if item.get("required_for_handoff") and mappings.get(item_id, {}).get("status") == "carried"
    }
    review_required = task.handoff_policy.semantic_review == "required" or any(
        item.get("criticality") == "critical" or item.get("kind") in RISK_REVIEW_KINDS
        for item in required_items.values()
    )
    review = _mapping(document.get("review"))
    if review.get("status") == "completed":
        risks.extend(_check_semantic_review(task, required_items, review))
    elif review_required:
        risks.append(
            _block(
                "HANDOFF-SEMANTIC-REVIEW-REQUIRED",
                "Task policy or transfer risk requires a bounded independent human review",
            )
        )
    else:
        risks.append(
            ContractRisk(
                "HANDOFF-SEMANTIC-UNREVIEWED",
                RiskLevel.WARNING,
                "structural coverage passed without a semantic-equivalence claim",
            )
        )

    if any(risk.level == RiskLevel.BLOCK for risk in risks):
        verdict = "not-transfer-ready"
    elif review.get("status") == "completed":
        verdict = "transfer-ready-after-review"
    else:
        verdict = "structurally-ready"
    return HandoffTransferAssessment(verdict, review_required, tuple(risks))


def _check_semantic_review(
    task: TaskPacket,
    required_items: Mapping[str, Mapping[str, Any]],
    review: Mapping[str, Any],
) -> list[ContractRisk]:
    risks: list[ContractRisk] = []
    if review.get("reviewer_kind") not in {"human", "mixed"}:
        risks.append(_block("HANDOFF-REVIEW-NOT-HUMAN", "model-only review cannot establish semantic preservation"))
    if not review.get("reviewer_independent"):
        risks.append(_block("HANDOFF-REVIEW-NOT-INDEPENDENT", "reviewer is not independent of Handoff production"))
    sampled = [str(value) for value in review.get("sampled_item_ids", [])]
    if len(sampled) != len(set(sampled)):
        risks.append(_block("HANDOFF-REVIEW-SAMPLE-DUPLICATE", "sampled item IDs are not unique"))
    unknown = sorted(set(sampled) - set(required_items))
    if unknown:
        risks.append(_block("HANDOFF-REVIEW-SAMPLE-UNKNOWN", "review sampled non-carried items: " + ", ".join(unknown)))
    if len(sampled) < task.handoff_policy.minimum_semantic_samples:
        risks.append(
            _block(
                "HANDOFF-REVIEW-SAMPLE-SMALL",
                f"semantic samples={len(sampled)} below Task minimum={task.handoff_policy.minimum_semantic_samples}",
            )
        )
    critical = {
        item_id for item_id, item in required_items.items() if item.get("criticality") == "critical"
    }
    missing_critical = sorted(critical - set(sampled))
    if missing_critical:
        risks.append(
            _block(
                "HANDOFF-REVIEW-CRITICAL-MISSING",
                "critical items were not reviewed: " + ", ".join(missing_critical),
            )
        )
    for kind in sorted(RISK_REVIEW_KINDS):
        candidates = {
            item_id for item_id, item in required_items.items() if item.get("kind") == kind
        }
        if candidates and not candidates.intersection(sampled):
            risks.append(
                _block(
                    "HANDOFF-REVIEW-RISK-KIND-MISSING",
                    f"no {kind} item was sampled",
                )
            )
    finding_values = [item for item in review.get("findings", []) if isinstance(item, Mapping)]
    findings = {str(item.get("item_id", "")): item for item in finding_values}
    if len(findings) != len(finding_values):
        risks.append(_block("HANDOFF-REVIEW-FINDING-DUPLICATE", "review findings contain duplicate item IDs"))
    if set(findings) != set(sampled):
        risks.append(_block("HANDOFF-REVIEW-FINDING-COVERAGE", "review findings do not match sampled item IDs"))
    failed = sorted(
        item_id
        for item_id, finding in findings.items()
        if finding.get("status") in {"distorted", "unverifiable"}
    )
    if failed:
        risks.append(
            _block(
                "HANDOFF-SUMMARY-DISTORTION",
                "semantic review did not preserve: " + ", ".join(failed),
            )
        )
    return risks


def _check_negative_section_coverage(
    handoff: Mapping[str, Any], carried_locators: set[str]
) -> list[ContractRisk]:
    risks: list[ContractRisk] = []
    for section in ("limitations", "conflicts", "unresolved", "human_decision_required"):
        values = handoff.get(section, [])
        if not isinstance(values, list):
            continue
        missing = [f"/{section}/{index}" for index in range(len(values)) if f"/{section}/{index}" not in carried_locators]
        if missing:
            risks.append(
                _block(
                    "HANDOFF-NEGATIVE-UNMAPPED",
                    f"{section} entries lack source mappings: {', '.join(missing)}",
                )
            )
    return risks


def _load_document_ref(
    root: Path,
    reference: Mapping[str, Any],
    kind: str,
    label: str,
    risks: list[ContractRisk],
) -> Mapping[str, Any] | None:
    risks.extend(_check_file_ref(root, reference, label))
    relative = reference.get("path")
    if not isinstance(relative, str):
        return None
    resolved = resolve_within_root(root, relative)
    if resolved is None or not resolved.is_file():
        return None
    value = load_document(resolved)
    if not isinstance(value, Mapping) or SchemaCatalog().validate(kind, value):
        risks.append(_block("HANDOFF-AUDIT-DOCUMENT-INVALID", f"{label} is not a valid {kind}"))
        return None
    return value


def _check_file_ref(root: Path, reference: Mapping[str, Any], label: str) -> list[ContractRisk]:
    relative = reference.get("path")
    expected = reference.get("sha256")
    if not isinstance(relative, str) or not isinstance(expected, str):
        return [_block("HANDOFF-AUDIT-REF-INVALID", f"{label}: invalid file reference")]
    resolved = resolve_within_root(root, relative)
    if resolved is None:
        return [_block("HANDOFF-AUDIT-REF-OUTSIDE", f"{label}: path escapes project root")]
    if not resolved.is_file():
        return [_block("HANDOFF-AUDIT-REF-MISSING", f"{label}: missing file {relative}")]
    if hash_file(resolved) != expected.removeprefix("sha256:").lower():
        return [_block("HANDOFF-AUDIT-REF-HASH", f"{label}: content hash mismatch")]
    return []


class _Missing:
    pass


_MISSING = _Missing()


def _resolve_pointer(document: object, pointer: str) -> object:
    if not pointer.startswith("/"):
        return _MISSING
    current = document
    for raw_part in pointer[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            if part not in current:
                return _MISSING
            current = current[part]
        elif isinstance(current, list):
            try:
                index = int(part)
            except ValueError:
                return _MISSING
            if index < 0 or index >= len(current):
                return _MISSING
            current = current[index]
        else:
            return _MISSING
    return current


def _ref_identity(reference: Mapping[str, Any]) -> tuple[str, str]:
    return (
        str(reference.get("path", "")),
        str(reference.get("sha256", "")).removeprefix("sha256:").lower(),
    )


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _block(code: str, message: str) -> ContractRisk:
    return ContractRisk(code, RiskLevel.BLOCK, message)
