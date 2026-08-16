from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from research_workbench.artifacts.integrity import hash_file, resolve_within_root
from research_workbench.capability import (
    AcceptedSkillRegistry,
    AgentProfile,
    ResolutionError,
    resolve_task_from_registry,
)
from research_workbench.contracts import ContractError, ContractRisk, RiskLevel
from research_workbench.io import load_document
from research_workbench.protocol import ResearchModeRegistry
from research_workbench.selection.models import ModeDecisionCard, ModeSkillSelectionDecision
from research_workbench.tasks import FileReference, TaskPacket


@dataclass(frozen=True, slots=True)
class SelectionAssessment:
    verdict: str
    ready: bool
    risks: tuple[ContractRisk, ...]


def _block(code: str, message: str) -> ContractRisk:
    return ContractRisk(code, RiskLevel.BLOCK, message)


def _warn(code: str, message: str) -> ContractRisk:
    return ContractRisk(code, RiskLevel.WARNING, message)


def _normalized_hash(value: object) -> str:
    return str(value or "").removeprefix("sha256:").lower()


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _check_ref(root: Path, reference: FileReference, label: str) -> tuple[Path | None, list[ContractRisk]]:
    resolved = resolve_within_root(root, reference.path)
    if resolved is None:
        return None, [_block("SELECTION-REF-OUTSIDE", f"{label} escapes the project root")]
    if not resolved.is_file():
        return None, [_block("SELECTION-REF-MISSING", f"{label} is missing: {reference.path}")]
    if hash_file(resolved) != reference.sha256:
        return resolved, [_block("SELECTION-REF-HASH", f"{label} hash does not match: {reference.path}")]
    return resolved, []


def _file_ref(value: object, field: str) -> FileReference:
    if not isinstance(value, Mapping):
        raise ContractError(field, "must be a file reference")
    return FileReference.from_mapping(value)


def load_mode_card(path: str | Path) -> ModeDecisionCard:
    value = load_document(path)
    if not isinstance(value, Mapping):
        raise ValueError(f"Mode card is not an object: {path}")
    return ModeDecisionCard.from_mapping(value)


def assess_mode_card(
    card: ModeDecisionCard,
    *,
    registry: ResearchModeRegistry,
    root: str | Path = ".",
) -> tuple[ContractRisk, ...]:
    project_root = Path(root).resolve()
    risks: list[ContractRisk] = []
    entries = {entry.mode_id: entry for entry in registry.entries}
    entry = entries.get(card.mode_id)
    if entry is None:
        return (_block("MODE-CARD-UNREGISTERED", f"card targets unregistered Mode {card.mode_id}"),)
    if card.mode_version != entry.version:
        risks.append(_block("MODE-CARD-VERSION-DRIFT", f"card version differs for {card.mode_id}"))
    if card.mode_ref.path != entry.path or card.mode_ref.sha256 != entry.content_hash:
        risks.append(_block("MODE-CARD-MANIFEST-DRIFT", f"card manifest lock differs for {card.mode_id}"))
    _, ref_risks = _check_ref(project_root, card.mode_ref, f"Mode card {card.card_id} manifest")
    risks.extend(ref_risks)
    registered_ids = set(entries)
    partners = {
        str(rule.get("with_mode_id"))
        for rule in card.combination_rules
        if isinstance(rule.get("with_mode_id"), str)
    }
    unknown = sorted(partners - registered_ids)
    if unknown:
        risks.append(
            _block("MODE-CARD-COMBINATION-UNKNOWN", "unregistered combination Modes: " + ", ".join(unknown))
        )
    return tuple(risks)


def _effective_mode_constraints(modes) -> dict[str, object]:
    return {
        "required_artifact_types": sorted(
            {item for mode in modes for item in mode.required_artifact_types}
        ),
        "human_decisions": sorted({item for mode in modes for item in mode.human_decisions}),
        "risk_rules": sorted({item for mode in modes for item in mode.risk_rules}),
        "forbidden_claims": sorted(
            {item for mode in modes for item in mode.claim_forbids_without_other_mode}
        ),
        "claim_support_by_mode": {
            mode.mode_id: sorted(mode.claim_allows) for mode in sorted(modes, key=lambda item: item.mode_id)
        },
    }


def assess_mode_skill_selection(
    document: Mapping[str, Any],
    *,
    root: str | Path = ".",
    mode_directory: str | Path = "registry/modes",
    accepted_registry: str | Path = "registry/skills/accepted.json",
) -> SelectionAssessment:
    project_root = Path(root).resolve()
    risks: list[ContractRisk] = []
    try:
        decision = ModeSkillSelectionDecision.from_mapping(document)
    except ContractError as exc:
        return SelectionAssessment("invalid", False, (_block("SELECTION-CONTRACT", str(exc)),))
    mode_registry = ResearchModeRegistry.load(mode_directory, project_root=project_root)
    skill_registry = AcceptedSkillRegistry.load(accepted_registry, project_root=project_root)
    if decision.mode_registry_digest != mode_registry.digest:
        risks.append(_block("MODE-REGISTRY-DRIFT", "selection Mode registry digest differs from live registry"))
    if decision.accepted_skill_registry_digest != skill_registry.digest:
        risks.append(
            _block("SKILL-SELECTION-REGISTRY-DRIFT", "selection Skill registry digest differs from live registry")
        )

    task_path, task_ref_risks = _check_ref(project_root, decision.task_ref, "selection Task")
    risks.extend(task_ref_risks)
    task: TaskPacket | None = None
    if task_path is not None and task_path.is_file():
        value = load_document(task_path)
        if not isinstance(value, Mapping):
            risks.append(_block("SELECTION-TASK-INVALID", "selection Task is not an object"))
        else:
            try:
                task = TaskPacket.from_mapping(value)
            except ContractError as exc:
                risks.append(_block("SELECTION-TASK-INVALID", str(exc)))
    if task is not None and task.revision != decision.task_revision:
        risks.append(_block("SELECTION-TASK-REVISION", "selection Task revision differs"))

    considered_modes = [item for item in decision.mode_assessment.get("considered", []) if isinstance(item, Mapping)]
    considered_mode_ids = [str(item.get("mode_id")) for item in considered_modes]
    registered_mode_ids = {entry.mode_id for entry in mode_registry.entries}
    if len(considered_mode_ids) != len(set(considered_mode_ids)) or set(considered_mode_ids) != registered_mode_ids:
        risks.append(_block("MODE-SELECTION-INCOMPLETE", "selection must consider every locked Mode exactly once"))
    selected_by_cards: list[str] = []
    plausible_by_cards: list[str] = []
    for item in considered_modes:
        mode_id = str(item.get("mode_id", ""))
        try:
            card_ref = _file_ref(item.get("card_ref"), f"mode_assessment.{mode_id}.card_ref")
        except ContractError as exc:
            risks.append(_block("MODE-CARD-REF", str(exc)))
            continue
        card_path, card_ref_risks = _check_ref(project_root, card_ref, f"Mode card {mode_id}")
        risks.extend(card_ref_risks)
        if card_path is None or not card_path.is_file():
            continue
        try:
            card = load_mode_card(card_path)
        except (ContractError, OSError, ValueError) as exc:
            risks.append(_block("MODE-CARD-INVALID", f"{mode_id}: {exc}"))
            continue
        risks.extend(assess_mode_card(card, registry=mode_registry, root=project_root))
        if card.mode_id != mode_id:
            risks.append(_block("MODE-CARD-ID-DRIFT", f"considered Mode {mode_id} uses card for {card.mode_id}"))
        expected_disposition = card.disposition(
            decision.evidence_basis, decision.produces_research_output
        )
        if item.get("disposition") != expected_disposition:
            risks.append(
                _block("MODE-SELECTION-MISMATCH", f"{mode_id} should be {expected_disposition}")
            )
        if expected_disposition == "selected":
            selected_by_cards.append(mode_id)
        elif expected_disposition == "plausible":
            plausible_by_cards.append(mode_id)

    declared_selected = tuple(decision.mode_assessment.get("selected_mode_ids", []))
    if set(declared_selected) != set(selected_by_cards):
        risks.append(_block("MODE-SELECTION-SELECTED-DRIFT", "selected Mode ids differ from card results"))
    modes = mode_registry.require(selected_by_cards) if selected_by_cards else ()
    expected_constraints = _effective_mode_constraints(modes)
    observed_constraints = _mapping(decision.mode_assessment.get("effective_constraints"))
    for key in ("required_artifact_types", "human_decisions", "risk_rules", "forbidden_claims"):
        if set(observed_constraints.get(key, [])) != set(expected_constraints[key]):
            risks.append(_block("MODE-CONSTRAINT-DRIFT", f"effective Mode constraints differ at {key}"))
    observed_support = _mapping(observed_constraints.get("claim_support_by_mode"))
    expected_support = _mapping(expected_constraints["claim_support_by_mode"])
    if set(observed_support) != set(expected_support) or any(
        set(observed_support.get(key, [])) != set(value) for key, value in expected_support.items()
    ):
        risks.append(_block("MODE-CONSTRAINT-DRIFT", "claim support must remain scoped to each Mode"))

    forbidden_requested = set(decision.requested_claim_strengths) & set(
        expected_constraints["forbidden_claims"]
    )
    if forbidden_requested:
        expected_mode_outcome = "blocked"
    elif selected_by_cards:
        expected_mode_outcome = "selected"
    elif plausible_by_cards:
        expected_mode_outcome = "ambiguous"
    elif decision.produces_research_output:
        expected_mode_outcome = "unsupported"
    else:
        expected_mode_outcome = "none"
    if decision.mode_assessment.get("outcome") != expected_mode_outcome:
        risks.append(
            _block("MODE-SELECTION-OUTCOME", f"Mode outcome should be {expected_mode_outcome}")
        )
    if task is not None and set(task.active_modes) != set(selected_by_cards):
        risks.append(_block("TASK-MODE-SELECTION-DRIFT", "Task active_modes differ from selection"))

    candidate_items = [item for item in decision.skill_assessment.get("candidates", []) if isinstance(item, Mapping)]
    candidate_ids = [str(item.get("skill_id")) for item in candidate_items]
    accepted_by_id = {entry.skill_id: entry for entry in skill_registry.entries}
    if len(candidate_ids) != len(set(candidate_ids)) or set(candidate_ids) != set(accepted_by_id):
        risks.append(
            _block("SKILL-SELECTION-INCOMPLETE", "selection must consider every accepted Skill exactly once")
        )
    selected_skill_ids = tuple(decision.skill_assessment.get("selected_skill_ids", []))
    for item in candidate_items:
        skill_id = str(item.get("skill_id", ""))
        entry = accepted_by_id.get(skill_id)
        if entry is None:
            continue
        expected_lock = {
            "version": entry.version,
            "manifest_hash": entry.manifest_hash,
            "content_hash": entry.content_hash,
            "package_hash": entry.package_hash,
        }
        drift = [
            field
            for field, expected in expected_lock.items()
            if _normalized_hash(item.get(field)) != _normalized_hash(expected)
        ]
        if drift:
            risks.append(
                _block("SKILL-SELECTION-LOCK-DRIFT", f"{skill_id} lock differs at: {', '.join(drift)}")
            )
        expected_disposition = "selected" if skill_id in selected_skill_ids else "excluded"
        if item.get("disposition") != expected_disposition:
            risks.append(
                _block("SKILL-SELECTION-DISPOSITION", f"{skill_id} should be {expected_disposition}")
            )
        covers = set(item.get("covers", []))
        if task is not None and (
            covers - set(task.required_capabilities) or covers - set(entry.manifest.capabilities)
        ):
            risks.append(_block("SKILL-SELECTION-COVERS", f"{skill_id} declares unsupported coverage"))

    deterministic_coverage = {
        capability
        for mechanism in decision.skill_assessment.get("deterministic_coverage", [])
        if isinstance(mechanism, Mapping)
        for capability in mechanism.get("covers", [])
        if isinstance(capability, str)
    }
    if task is not None:
        expected_before = set(task.required_capabilities) - deterministic_coverage
        if set(decision.skill_assessment.get("capability_gaps_before", [])) != expected_before:
            risks.append(_block("SKILL-SELECTION-GAP-DRIFT", "capability_gaps_before is inconsistent"))
        selected_capabilities = {
            capability
            for skill_id in selected_skill_ids
            if skill_id in accepted_by_id
            for capability in accepted_by_id[skill_id].manifest.capabilities
        }
        expected_after = expected_before - selected_capabilities
        if set(decision.skill_assessment.get("capability_gaps_after", [])) != expected_after:
            risks.append(_block("SKILL-SELECTION-GAP-DRIFT", "capability_gaps_after is inconsistent"))
    else:
        expected_after = set()

    skill_outcome = str(decision.skill_assessment.get("outcome", ""))
    expected_execution = {
        "assign-skills": (True, "execute"),
        "no-skill": (True, "deterministic-local"),
        "split-task": (False, "split-task"),
        "human-gate": (False, "human-gate"),
        "blocked": (False, "blocked"),
    }.get(skill_outcome)
    if expected_execution is None:
        risks.append(_block("SKILL-SELECTION-OUTCOME", f"unsupported Skill outcome: {skill_outcome}"))
    else:
        if (
            decision.execution.get("ready") != expected_execution[0]
            or decision.execution.get("disposition") != expected_execution[1]
        ):
            risks.append(_block("SELECTION-EXECUTION-DRIFT", "execution does not match Skill outcome"))
    if skill_outcome == "assign-skills":
        if task is None or set(task.required_skills) != set(selected_skill_ids) or expected_after:
            risks.append(_block("SKILL-SELECTION-ASSIGNMENT", "explicit Skill selection does not close Task gaps"))
        else:
            missing_inputs = sorted(
                {
                    contract
                    for skill_id in selected_skill_ids
                    for contract in accepted_by_id[skill_id].manifest.input_contracts
                }
                - set(decision.available_input_contracts)
            )
            if missing_inputs:
                risks.append(
                    _block("SKILL-SELECTION-INPUT-GAP", "selected Skills lack inputs: " + ", ".join(missing_inputs))
                )
            profile_path = project_root / "registry" / "agents" / f"{task.agent_profile}.yaml"
            if not profile_path.is_file():
                risks.append(_block("SELECTION-PROFILE-MISSING", f"missing Agent Profile: {profile_path}"))
            else:
                profile_value = load_document(profile_path)
                try:
                    profile = AgentProfile.from_mapping(profile_value)
                    resolve_task_from_registry(task, profile, skill_registry)
                except (ContractError, KeyError, ResolutionError, ValueError) as exc:
                    risks.append(_block("SKILL-SELECTION-RESOLUTION", str(exc)))
    elif skill_outcome == "no-skill":
        if selected_skill_ids or (task is not None and task.required_skills) or expected_after:
            risks.append(_block("SKILL-SELECTION-NO-SKILL", "no-Skill decision leaves a Skill or capability gap"))
    elif selected_skill_ids or (task is not None and task.required_skills):
        risks.append(_block("SKILL-SELECTION-PREEXECUTION", "non-executable parent decision must not select Skills"))

    initial_refs = [
        _file_ref(item, "read_plan.initial_content_refs")
        for item in decision.read_plan.get("initial_content_refs", [])
        if isinstance(item, Mapping)
    ]
    selected_refs = [
        _file_ref(item, "read_plan.selected_skill_content_refs")
        for item in decision.read_plan.get("selected_skill_content_refs", [])
        if isinstance(item, Mapping)
    ]
    for reference in (*initial_refs, *selected_refs):
        _, ref_risks = _check_ref(project_root, reference, "selection read plan")
        risks.extend(ref_risks)
    expected_selected_sources = {
        (accepted_by_id[skill_id].source_path, accepted_by_id[skill_id].content_hash)
        for skill_id in selected_skill_ids
        if skill_id in accepted_by_id
    }
    observed_selected_sources = {(item.path, item.sha256) for item in selected_refs}
    if observed_selected_sources != expected_selected_sources:
        risks.append(_block("SKILL-READ-PLAN-DRIFT", "selected Skill content refs differ from selection"))
    unselected_ids = set(accepted_by_id) - set(selected_skill_ids)
    if set(decision.read_plan.get("metadata_only_skill_ids", [])) != unselected_ids:
        risks.append(_block("SKILL-READ-PLAN-METADATA", "unselected Skills must remain metadata-only"))
    unselected_source_paths = {
        accepted_by_id[skill_id].source_path for skill_id in unselected_ids
    }
    leaked = sorted(
        {item.path for item in (*initial_refs, *selected_refs)} & unselected_source_paths
    )
    if leaked:
        risks.append(_block("SKILL-READ-PLAN-LEAK", "unselected Skill bodies enter read plan: " + ", ".join(leaked)))

    tier = decision.handoff.get("tier")
    if skill_outcome == "split-task" and tier != "H2":
        risks.append(_block("HANDOFF-TIER-SELECTION", "split Task integration requires H2"))
    if skill_outcome in {"no-skill", "human-gate", "blocked"} and tier != "H0":
        risks.append(_block("HANDOFF-TIER-SELECTION", f"{skill_outcome} fixture must use H0"))
    if skill_outcome == "assign-skills" and tier not in {"H1", "H2"}:
        risks.append(_block("HANDOFF-TIER-SELECTION", "delegated Skill execution requires H1 or H2"))

    blockers = [risk for risk in risks if risk.level == RiskLevel.BLOCK]
    ready = bool(decision.execution.get("ready")) and not blockers
    if blockers:
        verdict = "invalid"
    elif ready:
        verdict = "ready"
    else:
        verdict = str(decision.execution.get("disposition", "recorded"))
    return SelectionAssessment(verdict, ready, tuple(risks))


def assess_skill_boundary_audit(
    document: Mapping[str, Any],
    *,
    registry: AcceptedSkillRegistry,
    root: str | Path = ".",
) -> tuple[ContractRisk, ...]:
    project_root = Path(root).resolve()
    risks: list[ContractRisk] = []
    lock = _mapping(document.get("skill_lock"))
    skill_id = str(lock.get("skill_id", ""))
    matches = [entry for entry in registry.entries if entry.skill_id == skill_id]
    if len(matches) != 1:
        return (_block("SKILL-AUDIT-UNKNOWN", f"audit targets unknown Skill {skill_id}"),)
    entry = matches[0]
    expected = {
        "version": entry.version,
        "manifest_hash": entry.manifest_hash,
        "content_hash": entry.content_hash,
        "package_hash": entry.package_hash,
    }
    drift = [
        field
        for field, value in expected.items()
        if _normalized_hash(lock.get(field)) != _normalized_hash(value)
    ]
    if drift:
        risks.append(_block("SKILL-AUDIT-LOCK-DRIFT", f"{skill_id} differs at: {', '.join(drift)}"))
    for field in ("trigger_fixture_ids", "boundary_fixture_ids", "non_trigger_fixture_ids", "deletion_conditions"):
        value = document.get(field)
        if not isinstance(value, list) or not value:
            risks.append(_block("SKILL-AUDIT-BOUNDARY-MISSING", f"{skill_id} lacks {field}"))
    for item in document.get("evidence_refs", []):
        if not isinstance(item, Mapping):
            continue
        try:
            reference = FileReference.from_mapping(item)
        except ContractError as exc:
            risks.append(_block("SKILL-AUDIT-REF", str(exc)))
            continue
        _, ref_risks = _check_ref(project_root, reference, f"{skill_id} audit evidence")
        risks.extend(ref_risks)
    return tuple(risks)


def _optional_ref(value: object) -> FileReference | None:
    if value is None:
        return None
    return _file_ref(value, "comparison reference")


def _character_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8-sig"))


def assess_handoff_tier_comparison(
    document: Mapping[str, Any],
    *,
    root: str | Path = ".",
) -> tuple[ContractRisk, ...]:
    project_root = Path(root).resolve()
    risks: list[ContractRisk] = []
    for key in ("task_ref", "input_ref", "outcome_criteria_ref"):
        try:
            reference = _file_ref(document.get(key), key)
        except ContractError as exc:
            risks.append(_block("HANDOFF-COMPARISON-REF", str(exc)))
            continue
        _, ref_risks = _check_ref(project_root, reference, key)
        risks.extend(ref_risks)
    arms = [item for item in document.get("arms", []) if isinstance(item, Mapping)]
    tiers = [str(item.get("tier")) for item in arms]
    if len(tiers) != 3 or set(tiers) != {"H0", "H1", "H2"}:
        risks.append(_block("HANDOFF-COMPARISON-TIERS", "comparison must contain H0, H1, and H2 exactly once"))
    for arm in arms:
        tier = str(arm.get("tier", ""))
        metrics = _mapping(arm.get("metrics"))
        resolved_refs: dict[str, Path | None] = {}
        for key in (
            "archive_ref",
            "returned_context_ref",
            "handoff_ref",
            "transfer_manifest_ref",
            "transfer_audit_ref",
        ):
            try:
                reference = _optional_ref(arm.get(key))
            except ContractError as exc:
                risks.append(_block("HANDOFF-COMPARISON-REF", f"{tier} {exc}"))
                resolved_refs[key] = None
                continue
            if reference is None:
                resolved_refs[key] = None
                continue
            path, ref_risks = _check_ref(project_root, reference, f"{tier} {key}")
            resolved_refs[key] = path
            risks.extend(ref_risks)
        artifact_paths: list[Path] = []
        for value in arm.get("artifact_refs", []):
            if not isinstance(value, Mapping):
                continue
            try:
                reference = FileReference.from_mapping(value)
            except ContractError as exc:
                risks.append(_block("HANDOFF-COMPARISON-REF", f"{tier} {exc}"))
                continue
            path, ref_risks = _check_ref(project_root, reference, f"{tier} artifact")
            risks.extend(ref_risks)
            if path is not None and path.is_file():
                artifact_paths.append(path)
        expected_counts = {
            "archived_message_chars": _character_count(resolved_refs["archive_ref"])
            if resolved_refs.get("archive_ref") else 0,
            "returned_context_chars": _character_count(resolved_refs["returned_context_ref"])
            if resolved_refs.get("returned_context_ref") else 0,
            "handoff_chars": _character_count(resolved_refs["handoff_ref"])
            if resolved_refs.get("handoff_ref") else 0,
            "transfer_manifest_chars": _character_count(resolved_refs["transfer_manifest_ref"])
            if resolved_refs.get("transfer_manifest_ref") else 0,
            "transfer_audit_chars": _character_count(resolved_refs["transfer_audit_ref"])
            if resolved_refs.get("transfer_audit_ref") else 0,
            "artifact_count": len(artifact_paths),
            "artifact_chars": sum(_character_count(path) for path in artifact_paths),
        }
        drift = [key for key, value in expected_counts.items() if metrics.get(key) != value]
        if drift:
            risks.append(
                _block("HANDOFF-COMPARISON-METRIC-DRIFT", f"{tier} differs at: {', '.join(drift)}")
            )
        if tier == "H0":
            if any(resolved_refs.get(key) for key in ("archive_ref", "handoff_ref", "transfer_manifest_ref", "transfer_audit_ref")):
                risks.append(_block("HANDOFF-H0-INCONSISTENT", "H0 must not contain inter-agent or Handoff artifacts"))
            if any(metrics.get(key) != 0 for key in ("visible_message_count", "visible_message_chars", "archived_message_count", "capture_gap_count")):
                risks.append(_block("HANDOFF-H0-INCONSISTENT", "H0 inter-agent metrics must be zero"))
        elif tier in {"H1", "H2"}:
            if not resolved_refs.get("archive_ref") or not resolved_refs.get("handoff_ref"):
                risks.append(_block(f"HANDOFF-{tier}-INCOMPLETE", f"{tier} requires an Archive and Handoff"))
            if (
                metrics.get("visible_message_count") != metrics.get("archived_message_count")
                or metrics.get("visible_message_chars") != metrics.get("archived_message_chars")
                or metrics.get("capture_gap_count") != 0
            ):
                risks.append(_block("HANDOFF-ARCHIVE-GAP", f"{tier} visible messages are not completely archived"))
            if tier == "H1" and any(
                resolved_refs.get(key) for key in ("transfer_manifest_ref", "transfer_audit_ref")
            ):
                risks.append(_block("HANDOFF-H1-OVERBUILT", "H1 fixture must not contain H2 audit artifacts"))
            if tier == "H2":
                if not resolved_refs.get("transfer_manifest_ref") or not resolved_refs.get("transfer_audit_ref"):
                    risks.append(_block("HANDOFF-H2-INCOMPLETE", "H2 requires transfer manifest and audit"))
                if metrics.get("required_transfer_items") != metrics.get("carried_transfer_items"):
                    risks.append(_block("HANDOFF-H2-COVERAGE", "H2 fixture does not carry every required item"))
    if document.get("evidence_scope") == "fixture-only":
        if document.get("declared_best_tier") is not None:
            risks.append(_block("HANDOFF-COMPARISON-OVERCLAIM", "fixture-only comparison cannot declare an optimal tier"))
        risks.append(_warn("HANDOFF-COMPARISON-FIXTURE-ONLY", "fixture metrics do not establish real coordination value"))
    return tuple(risks)
