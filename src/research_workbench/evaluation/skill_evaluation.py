"""Deterministic readiness checks for paired Skill evaluations.

The evaluator never invokes a model and never admits a Skill. It checks whether
the persisted evidence is sufficient for a human admission decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from research_workbench.artifacts.integrity import hash_directory, hash_file, resolve_within_root
from research_workbench.capability import AgentProfile, ResolvedTask
from research_workbench.capability.catalog import load_candidates
from research_workbench.context import ContextSnapshot
from research_workbench.contracts import ContractError, ContractRisk, RiskLevel
from research_workbench.io import load_document
from research_workbench.observability import ExecutionReceipt, check_execution_receipt
from research_workbench.protocol import ProjectProtocol
from research_workbench.validation import SchemaCatalog


@dataclass(frozen=True, slots=True)
class SkillEvaluationAssessment:
    verdict: str
    risks: tuple[ContractRisk, ...]


def _load_project_protocol(
    root: Path, evaluation: Mapping[str, Any]
) -> tuple[ProjectProtocol | None, list[ContractRisk]]:
    reference = _mapping(evaluation.get("project_protocol_ref"))
    risks = _check_file_ref(root, reference, "Project Protocol")
    relative = reference.get("path")
    if not isinstance(relative, str):
        return None, risks or [_block("EVAL-PROJECT-PROTOCOL-MISSING", "live evaluation has no Project Protocol")]
    resolved = resolve_within_root(root, relative)
    if resolved is None or not resolved.is_file():
        return None, risks
    value = load_document(resolved)
    if not isinstance(value, Mapping) or SchemaCatalog().validate("project_protocol", value):
        risks.append(_block("EVAL-PROJECT-PROTOCOL-INVALID", "Project Protocol fails its Schema"))
        return None, risks
    try:
        return ProjectProtocol.from_mapping(value), risks
    except ContractError as exc:
        risks.append(
            _block("EVAL-PROJECT-PROTOCOL-INVALID", f"Project Protocol contract error: {exc}")
        )
        return None, risks


def assess_skill_evaluation(
    document: Mapping[str, Any],
    *,
    root: str | Path = ".",
    candidate_registry: str | Path | None = None,
) -> SkillEvaluationAssessment:
    project_root = Path(root).resolve()
    risks: list[ContractRisk] = []
    scope = document.get("evaluation_scope")
    protocol = _mapping(document.get("protocol"))
    cases = [item for item in document.get("cases", []) if isinstance(item, Mapping)]

    source_ref = _mapping(document.get("skill_source_ref"))
    risks.extend(_check_file_ref(project_root, source_ref, "Skill source"))
    source_path = source_ref.get("path")
    if isinstance(source_path, str):
        resolved_source = resolve_within_root(project_root, source_path)
        if resolved_source is not None and resolved_source.is_file():
            expected_package = str(document.get("skill_package_hash", "")).removeprefix("sha256:").lower()
            if hash_directory(resolved_source.parent) != expected_package:
                risks.append(_block("EVAL-SKILL-PACKAGE-DRIFT", "Skill package hash does not match live files"))
    if candidate_registry is not None:
        risks.extend(_check_candidate_pin(document, project_root, candidate_registry))

    project_protocol: ProjectProtocol | None = None
    if scope == "live-forward-test":
        project_protocol, protocol_risks = _load_project_protocol(project_root, document)
        risks.extend(protocol_risks)
        risks.extend(
            _check_file_ref(
                project_root,
                _mapping(document.get("model_config_ref")),
                "redacted model configuration",
            )
        )
    else:
        risks.append(
            _block(
                "EVAL-FIXTURE-ONLY",
                "fixture-only evidence can test the harness but cannot support Skill admission",
            )
        )

    required_kinds = set(protocol.get("required_case_kinds", []))
    observed_kinds = {str(case.get("case_kind")) for case in cases}
    missing_kinds = sorted(required_kinds - observed_kinds)
    if missing_kinds:
        risks.append(
            _block("EVAL-CASE-COVERAGE", "missing required case kinds: " + ", ".join(missing_kinds))
        )
    if scope == "live-forward-test" and len(cases) < int(protocol.get("minimum_live_cases", 1)):
        risks.append(
            _block(
                "EVAL-LIVE-CASE-COUNT",
                f"live cases={len(cases)} below required minimum={protocol.get('minimum_live_cases')}",
            )
        )

    case_ids: set[str] = set()
    for case in cases:
        case_id = str(case.get("case_id", "<unknown>"))
        if case_id in case_ids:
            risks.append(_block("EVAL-CASE-DUPLICATE", f"duplicate case_id: {case_id}"))
        case_ids.add(case_id)
        risks.extend(
            _assess_case(
                case,
                protocol,
                document,
                project_root,
                live=scope == "live-forward-test",
                project_protocol=project_protocol,
            )
        )

    declared = _mapping(document.get("admission"))
    blockers = [risk for risk in risks if risk.level == RiskLevel.BLOCK]
    if blockers and declared.get("status") != "not-eligible":
        risks.append(
            _block(
                "EVAL-STATUS-OVERCLAIM",
                "the evaluation declares admission eligibility despite blocking evidence gaps",
            )
        )
    if declared.get("status") == "human-decided":
        decision_ref = declared.get("decision_ref")
        if not isinstance(decision_ref, str) or not _existing_file(project_root, decision_ref):
            risks.append(_block("EVAL-DECISION-MISSING", "human-decided evaluation lacks a live Decision file"))
        else:
            risks.extend(_check_human_decision(document, project_root, decision_ref))

    blockers = [risk for risk in risks if risk.level == RiskLevel.BLOCK]
    if blockers:
        verdict = "not-eligible"
    elif declared.get("status") == "human-decided":
        verdict = "human-decision-recorded"
    else:
        verdict = "eligible-for-human-decision"
    return SkillEvaluationAssessment(verdict, tuple(risks))


def _assess_case(
    case: Mapping[str, Any],
    protocol: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    root: Path,
    *,
    live: bool,
    project_protocol: ProjectProtocol | None,
) -> list[ContractRisk]:
    risks: list[ContractRisk] = []
    case_id = str(case.get("case_id", "<unknown>"))
    arms = _mapping(case.get("arms"))
    baseline = _mapping(arms.get("baseline"))
    with_skill = _mapping(arms.get("with_skill"))

    risks.extend(
        _check_file_ref(root, _mapping(case.get("task_contract_ref")), f"{case_id} task contract")
    )
    risks.extend(_check_file_ref(root, _mapping(case.get("input_ref")), f"{case_id} input"))

    validation_reports: dict[str, Mapping[str, Any]] = {}
    for name, arm in (("baseline", baseline), ("with-skill", with_skill)):
        risks.extend(_check_file_ref(root, _mapping(arm.get("output_ref")), f"{case_id} {name} output"))
        risks.extend(
            _check_file_ref(root, _mapping(arm.get("validation_ref")), f"{case_id} {name} validation")
        )
        validation_report, validation_risks = _load_validation_report(
            root, case, arm, case_id, name
        )
        risks.extend(validation_risks)
        if validation_report is not None:
            validation_reports[name] = validation_report
    if {"baseline", "with-skill"} <= validation_reports.keys() and _checker_identity(
        validation_reports["baseline"]
    ) != _checker_identity(validation_reports["with-skill"]):
        risks.append(
            _block(
                "EVAL-CHECKER-DRIFT",
                f"{case_id}: paired arms used different deterministic checkers",
            )
        )
    if with_skill.get("deterministic_status") != "pass":
        risks.append(
            _block(
                "EVAL-WITH-SKILL-CHECK",
                f"{case_id}: with-Skill deterministic status is not pass",
            )
        )

    baseline_context = _mapping(baseline.get("context"))
    skill_context = _mapping(with_skill.get("context"))
    expected_input_characters = _paired_input_characters(root, case)
    if expected_input_characters is not None and (
        baseline_context.get("task_input_characters") != expected_input_characters
        or skill_context.get("task_input_characters") != expected_input_characters
    ):
        risks.append(
            _block(
                "EVAL-INPUT-MEASUREMENT-DRIFT",
                f"{case_id}: recorded task input characters differ from frozen files",
            )
        )
    if baseline_context.get("skill_instruction_characters") != 0:
        risks.append(_block("EVAL-BASELINE-CONTAMINATED", f"{case_id}: baseline loaded Skill instructions"))
    if int(skill_context.get("skill_instruction_characters", 0)) <= 0:
        risks.append(_block("EVAL-SKILL-NOT-LOADED", f"{case_id}: with-Skill arm loaded no instructions"))
    if baseline_context.get("task_input_characters") != skill_context.get("task_input_characters"):
        risks.append(_block("EVAL-INPUT-DRIFT", f"{case_id}: paired arms report different input sizes"))
    for name, context in (("baseline", baseline_context), ("with-skill", skill_context)):
        minimum = int(context.get("task_input_characters", 0)) + int(
            context.get("skill_instruction_characters", 0)
        )
        if int(context.get("total_loaded_characters", 0)) < minimum:
            risks.append(
                _block(
                    "EVAL-CONTEXT-INCONSISTENT",
                    f"{case_id} {name}: total loaded characters are below task plus Skill characters",
                )
            )
    baseline_other = (
        int(baseline_context.get("total_loaded_characters", 0))
        - int(baseline_context.get("task_input_characters", 0))
        - int(baseline_context.get("skill_instruction_characters", 0))
    )
    skill_other = (
        int(skill_context.get("total_loaded_characters", 0))
        - int(skill_context.get("task_input_characters", 0))
        - int(skill_context.get("skill_instruction_characters", 0))
    )
    if baseline_other != skill_other:
        risks.append(
            _block(
                "EVAL-BASE-CONTEXT-DRIFT",
                f"{case_id}: paired arms loaded different non-Skill context volumes",
            )
        )
    if live and (
        baseline_context.get("status") != "measured" or skill_context.get("status") != "measured"
    ):
        risks.append(_block("EVAL-CONTEXT-UNMEASURED", f"{case_id}: live paired context must be measured"))

    if live:
        expected_config_hash = _normalized_hash(
            _mapping(evaluation.get("model_config_ref")).get("sha256")
        )
        for name, arm in (("baseline", baseline), ("with-skill", with_skill)):
            if _normalized_hash(arm.get("model_config_hash")) != expected_config_hash:
                risks.append(
                    _block(
                        "EVAL-MODEL-CONFIG-UNPINNED",
                        f"{case_id} {name}: model configuration hash differs from the frozen artifact",
                    )
                )
        baseline_receipt, baseline_assignment, baseline_risks = _load_receipt(
            root,
            baseline,
            case_id,
            "baseline",
            evaluation=evaluation,
            project_protocol=project_protocol,
        )
        skill_receipt, skill_assignment, skill_risks = _load_receipt(
            root,
            with_skill,
            case_id,
            "with-skill",
            evaluation=evaluation,
            project_protocol=project_protocol,
        )
        risks.extend(baseline_risks)
        risks.extend(skill_risks)
        if baseline_receipt and skill_receipt:
            risks.extend(_compare_receipts(case_id, baseline, with_skill, baseline_receipt, skill_receipt))
        if baseline_assignment and skill_assignment:
            risks.extend(
                _compare_assignments(
                    case_id,
                    str(evaluation.get("skill_id", "")),
                    baseline_assignment,
                    skill_assignment,
                )
            )

    review = _mapping(case.get("review"))
    if live and review.get("status") != "completed":
        risks.append(_block("EVAL-REVIEW-PENDING", f"{case_id}: live case has no completed blind review"))
    if review.get("status") == "completed":
        if review.get("reviewer_kind") not in {"human", "mixed"}:
            risks.append(_block("EVAL-HUMAN-REVIEW-MISSING", f"{case_id}: review has no human reviewer"))
        if not review.get("reviewer_independent"):
            risks.append(_block("EVAL-REVIEW-NOT-INDEPENDENT", f"{case_id}: reviewer is not independent"))
        if not review.get("blinded") or not review.get("order_revealed_after_scoring"):
            risks.append(_block("EVAL-REVIEW-UNBLINDED", f"{case_id}: condition order was exposed before scoring"))
        else:
            scored_at = datetime.fromisoformat(str(review.get("scored_at")).replace("Z", "+00:00"))
            revealed_at = datetime.fromisoformat(str(review.get("revealed_at")).replace("Z", "+00:00"))
            if revealed_at < scored_at:
                risks.append(
                    _block("EVAL-REVIEW-TIME-DRIFT", f"{case_id}: condition reveal precedes scoring")
                )
        criterion_items = [item for item in review.get("criteria", []) if isinstance(item, Mapping)]
        criteria = {
            str(item.get("criterion_id")): item
            for item in criterion_items
        }
        if len(criteria) != len(criterion_items):
            risks.append(_block("EVAL-REVIEW-CRITERIA-DUPLICATE", f"{case_id}: duplicate criterion IDs"))
        missing = sorted(set(protocol.get("required_review_criteria", [])) - set(criteria))
        if missing:
            risks.append(
                _block("EVAL-REVIEW-CRITERIA", f"{case_id}: missing review criteria: {', '.join(missing)}")
            )
        if criteria and all(
            int(item.get("with_skill_score", 0)) <= int(item.get("baseline_score", 0))
            for item in criteria.values()
        ):
            risks.append(
                ContractRisk(
                    "EVAL-NO-OBSERVED-GAIN",
                    RiskLevel.WARNING,
                    f"{case_id}: with-Skill scores do not improve any recorded criterion",
                )
            )
    return risks


def _load_receipt(
    root: Path,
    arm: Mapping[str, Any],
    case_id: str,
    arm_name: str,
    *,
    evaluation: Mapping[str, Any],
    project_protocol: ProjectProtocol | None,
) -> tuple[ExecutionReceipt | None, ResolvedTask | None, list[ContractRisk]]:
    relative = arm.get("execution_receipt_ref")
    if not isinstance(relative, str):
        return None, None, [_block("EVAL-RECEIPT-MISSING", f"{case_id} {arm_name}: receipt is required")]
    resolved = resolve_within_root(root, relative)
    if resolved is None or not resolved.is_file():
        return None, None, [_block("EVAL-RECEIPT-MISSING", f"{case_id} {arm_name}: missing receipt {relative}")]
    value = load_document(resolved)
    if not isinstance(value, Mapping):
        return None, None, [_block("EVAL-RECEIPT-INVALID", f"{case_id} {arm_name}: receipt is not an object")]
    errors = SchemaCatalog().validate("execution_receipt", value)
    if errors:
        return None, None, [_block("EVAL-RECEIPT-INVALID", f"{case_id} {arm_name}: receipt fails Schema")]
    try:
        receipt = ExecutionReceipt.from_mapping(value)
    except ContractError as exc:
        return None, None, [
            _block("EVAL-RECEIPT-INVALID", f"{case_id} {arm_name}: receipt contract error: {exc}")
        ]
    risks: list[ContractRisk] = []
    if project_protocol is None:
        risks.append(
            _block(
                "EVAL-PROJECT-PROTOCOL-MISSING",
                f"{case_id} {arm_name}: live receipt cannot be checked without a Project Protocol",
            )
        )
    else:
        try:
            linkage_risks = check_execution_receipt(
                receipt,
                project_protocol,
                root=root,
                receipt_ref=relative,
            )
            risks.extend(risk for risk in linkage_risks if risk.code != "COST-USAGE-UNKNOWN")
        except (ContractError, OSError, ValueError) as exc:
            risks.append(
                _block(
                    "EVAL-RECEIPT-LINKAGE-INVALID",
                    f"{case_id} {arm_name}: linked execution evidence is invalid: {exc}",
                )
            )
    assignment, assignment_risks = _load_skill_assignment(
        root,
        receipt,
        case_id,
        arm_name,
        evaluation=evaluation,
        should_load=bool(arm.get("skill_loaded")),
    )
    risks.extend(assignment_risks)
    if receipt.execution_kind not in {"native-agent", "model-api"}:
        risks.append(
            _block(
                "EVAL-RECEIPT-NOT-LIVE",
                f"{case_id} {arm_name}: execution kind {receipt.execution_kind} is not a live model run",
            )
        )
    if receipt.status != "completed":
        risks.append(
            _block("EVAL-RECEIPT-INCOMPLETE", f"{case_id} {arm_name}: execution status is {receipt.status}")
        )
    if receipt.model_usage_status == "not-applicable":
        risks.append(
            _block(
                "EVAL-USAGE-UNCOMPARABLE",
                f"{case_id} {arm_name}: live model execution cannot use not-applicable usage",
            )
        )
    elif receipt.model_usage_status in {"measured", "estimated"} and len(receipt.model_usage) != 1:
        risks.append(
            _block(
                "EVAL-USAGE-UNCOMPARABLE",
                f"{case_id} {arm_name}: measured/estimated usage requires exactly one model record",
            )
        )
    elif receipt.model_usage_status in {"estimated", "unavailable"}:
        risks.append(
            ContractRisk(
                "EVAL-USAGE-NOT-MEASURED",
                RiskLevel.WARNING,
                f"{case_id} {arm_name}: token/cost usage is {receipt.model_usage_status}; do not claim token savings",
            )
        )
    output_path = _mapping(arm.get("output_ref")).get("path")
    if isinstance(output_path, str) and output_path not in receipt.output_refs:
        risks.append(
            _block("EVAL-RECEIPT-OUTPUT-DRIFT", f"{case_id} {arm_name}: receipt omits paired output")
        )
    validation_path = _mapping(arm.get("validation_ref")).get("path")
    if isinstance(validation_path, str) and validation_path not in receipt.validation_refs:
        risks.append(
            _block(
                "EVAL-RECEIPT-VALIDATION-DRIFT",
                f"{case_id} {arm_name}: receipt omits paired validation report",
            )
        )
    if not receipt.context_snapshot_ref:
        risks.append(
            _block("EVAL-CONTEXT-RECEIPT-MISSING", f"{case_id} {arm_name}: receipt has no Context Snapshot")
        )
    else:
        snapshot_path = resolve_within_root(root, receipt.context_snapshot_ref)
        if snapshot_path is None or not snapshot_path.is_file():
            risks.append(
                _block(
                    "EVAL-CONTEXT-RECEIPT-MISSING",
                    f"{case_id} {arm_name}: missing Context Snapshot {receipt.context_snapshot_ref}",
                )
            )
        else:
            snapshot_value = load_document(snapshot_path)
            errors = (
                SchemaCatalog().validate("context_snapshot", snapshot_value)
                if isinstance(snapshot_value, Mapping)
                else [object()]
            )
            if errors:
                risks.append(
                    _block("EVAL-CONTEXT-INVALID", f"{case_id} {arm_name}: invalid Context Snapshot")
                )
            else:
                try:
                    ContextSnapshot.from_mapping(snapshot_value)
                except ContractError as exc:
                    risks.append(
                        _block(
                            "EVAL-CONTEXT-INVALID",
                            f"{case_id} {arm_name}: Context Snapshot contract error: {exc}",
                        )
                    )
                    return receipt, assignment, risks
                metrics = _mapping(snapshot_value.get("metrics"))
                arm_context = _mapping(arm.get("context"))
                if snapshot_value.get("measurement_source") not in {"runtime", "mixed"}:
                    risks.append(
                        _block(
                            "EVAL-CONTEXT-NOT-RUNTIME",
                            f"{case_id} {arm_name}: Context Snapshot is not runtime-measured",
                        )
                    )
                if (
                    metrics.get("loaded_chars") != arm_context.get("total_loaded_characters")
                    or metrics.get("skill_instruction_chars")
                    != arm_context.get("skill_instruction_characters")
                ):
                    risks.append(
                        _block(
                            "EVAL-CONTEXT-DRIFT",
                            f"{case_id} {arm_name}: arm context differs from Context Snapshot",
                        )
                    )
    if receipt.coordination.execution_seconds is None:
        risks.append(
            _block("EVAL-TIME-UNMEASURED", f"{case_id} {arm_name}: execution wall time is unavailable")
        )
    return receipt, assignment, risks


def _load_skill_assignment(
    root: Path,
    receipt: ExecutionReceipt,
    case_id: str,
    arm_name: str,
    *,
    evaluation: Mapping[str, Any],
    should_load: bool,
) -> tuple[ResolvedTask | None, list[ContractRisk]]:
    risks: list[ContractRisk] = []
    resolved = resolve_within_root(root, receipt.skill_assignment_ref)
    if resolved is None or not resolved.is_file():
        return None, [
            _block(
                "EVAL-ASSIGNMENT-MISSING",
                f"{case_id} {arm_name}: missing Skill Assignment {receipt.skill_assignment_ref}",
            )
        ]
    value = load_document(resolved)
    if not isinstance(value, Mapping) or SchemaCatalog().validate("skill_assignment", value):
        return None, [
            _block("EVAL-ASSIGNMENT-INVALID", f"{case_id} {arm_name}: invalid Skill Assignment")
        ]
    try:
        assignment = ResolvedTask.from_mapping(value)
    except ContractError as exc:
        return None, [
            _block(
                "EVAL-ASSIGNMENT-INVALID",
                f"{case_id} {arm_name}: Skill Assignment contract error: {exc}",
            )
        ]
    if (assignment.task_id, assignment.task_revision) != (
        receipt.task_id,
        receipt.task_revision,
    ):
        risks.append(
            _block(
                "EVAL-ASSIGNMENT-TASK-DRIFT",
                f"{case_id} {arm_name}: Skill Assignment belongs to a different Task",
            )
        )

    profile_path = resolve_within_root(root, receipt.agent_profile_ref)
    if profile_path is None or not profile_path.is_file():
        risks.append(
            _block(
                "EVAL-PROFILE-MISSING",
                f"{case_id} {arm_name}: missing Agent Profile {receipt.agent_profile_ref}",
            )
        )
    else:
        profile_value = load_document(profile_path)
        if not isinstance(profile_value, Mapping) or SchemaCatalog().validate(
            "agent_profile", profile_value
        ):
            risks.append(
                _block("EVAL-PROFILE-INVALID", f"{case_id} {arm_name}: invalid Agent Profile")
            )
        else:
            try:
                profile = AgentProfile.from_mapping(profile_value)
            except ContractError as exc:
                risks.append(
                    _block(
                        "EVAL-PROFILE-INVALID",
                        f"{case_id} {arm_name}: Agent Profile contract error: {exc}",
                    )
                )
            else:
                if assignment.agent_profile != f"{profile.agent_profile_id}@{profile.version}":
                    risks.append(
                        _block(
                            "EVAL-PROFILE-ASSIGNMENT-DRIFT",
                            f"{case_id} {arm_name}: Agent Profile differs from Skill Assignment",
                        )
                    )

    skill_id = str(evaluation.get("skill_id", ""))
    candidate_locks = [lock for lock in assignment.skill_lock if lock.skill_id == skill_id]
    if not should_load and candidate_locks:
        risks.append(
            _block(
                "EVAL-BASELINE-CANDIDATE-LOADED",
                f"{case_id}: baseline Skill Assignment contains candidate {skill_id}",
            )
        )
    if should_load:
        if len(candidate_locks) != 1:
            risks.append(
                _block(
                    "EVAL-CANDIDATE-ASSIGNMENT-MISSING",
                    f"{case_id}: with-Skill Assignment must contain exactly one {skill_id} lock",
                )
            )
        else:
            lock = candidate_locks[0]
            source_ref = _mapping(evaluation.get("skill_source_ref"))
            expected = {
                "version": str(evaluation.get("skill_version", "")),
                "content_hash": _normalized_hash(source_ref.get("sha256")),
                "source_locator": str(source_ref.get("path", "")),
                "package_hash": _normalized_hash(evaluation.get("skill_package_hash")),
            }
            observed = {
                "version": lock.version,
                "content_hash": _normalized_hash(lock.content_hash),
                "source_locator": str(lock.source_locator or ""),
                "package_hash": _normalized_hash(lock.package_hash),
            }
            drift = [key for key in expected if expected[key] != observed[key]]
            if drift:
                risks.append(
                    _block(
                        "EVAL-CANDIDATE-ASSIGNMENT-DRIFT",
                        f"{case_id}: candidate Skill lock differs at: {', '.join(drift)}",
                    )
                )
    return assignment, risks


def _compare_receipts(
    case_id: str,
    baseline_arm: Mapping[str, Any],
    skill_arm: Mapping[str, Any],
    baseline: ExecutionReceipt,
    with_skill: ExecutionReceipt,
) -> list[ContractRisk]:
    risks: list[ContractRisk] = []
    if (
        baseline.runtime.name,
        baseline.runtime.version,
        baseline.runtime.adapter_version,
    ) != (
        with_skill.runtime.name,
        with_skill.runtime.version,
        with_skill.runtime.adapter_version,
    ):
        risks.append(_block("EVAL-RUNTIME-DRIFT", f"{case_id}: paired arms used different runtimes"))
    if (baseline.task_id, baseline.task_revision) != (with_skill.task_id, with_skill.task_revision):
        risks.append(_block("EVAL-TASK-DRIFT", f"{case_id}: paired receipts identify different Tasks"))
    if baseline.agent_profile_ref != with_skill.agent_profile_ref:
        risks.append(_block("EVAL-PROFILE-DRIFT", f"{case_id}: paired arms used different Agent Profiles"))
    left_provider = baseline_arm.get("provider")
    right_provider = skill_arm.get("provider")
    left_model = baseline_arm.get("model")
    right_model = skill_arm.get("model")
    if not all(isinstance(value, str) and value for value in (left_provider, right_provider, left_model, right_model)):
        risks.append(_block("EVAL-MODEL-IDENTITY-MISSING", f"{case_id}: paired arms must identify provider and model"))
    elif (left_provider, left_model) != (right_provider, right_model):
        risks.append(_block("EVAL-MODEL-DRIFT", f"{case_id}: paired arms declare different provider/models"))
    if baseline.model_usage_status != with_skill.model_usage_status:
        risks.append(_block("EVAL-USAGE-STATUS-DRIFT", f"{case_id}: paired usage status differs"))
    if len(baseline.model_usage) == 1 and len(with_skill.model_usage) == 1:
        left = baseline.model_usage[0]
        right = with_skill.model_usage[0]
        if (left.provider, left.model) != (right.provider, right.model):
            risks.append(_block("EVAL-MODEL-DRIFT", f"{case_id}: paired arms used different provider/models"))
        if isinstance(left_provider, str) and isinstance(left_model, str) and (
            left.provider,
            left.model,
        ) != (left_provider, left_model):
            risks.append(_block("EVAL-MODEL-RECEIPT-DRIFT", f"{case_id}: receipt differs from arm model identity"))
        if isinstance(right_provider, str) and isinstance(right_model, str) and (
            right.provider,
            right.model,
        ) != (right_provider, right_model):
            risks.append(_block("EVAL-MODEL-RECEIPT-DRIFT", f"{case_id}: receipt differs from arm model identity"))
    left_hash = baseline_arm.get("model_config_hash")
    right_hash = skill_arm.get("model_config_hash")
    if not isinstance(left_hash, str) or not isinstance(right_hash, str) or left_hash != right_hash:
        risks.append(_block("EVAL-MODEL-CONFIG-DRIFT", f"{case_id}: model configuration hashes differ"))
    return risks


def _compare_assignments(
    case_id: str,
    candidate_skill_id: str,
    baseline: ResolvedTask,
    with_skill: ResolvedTask,
) -> list[ContractRisk]:
    def base_locks(assignment: ResolvedTask) -> tuple[tuple[str, str, str, str, str], ...]:
        return tuple(
            sorted(
                (
                    lock.skill_id,
                    lock.version,
                    _normalized_hash(lock.content_hash),
                    str(lock.source_locator or ""),
                    _normalized_hash(lock.package_hash),
                )
                for lock in assignment.skill_lock
                if lock.skill_id != candidate_skill_id
            )
        )

    comparisons = {
        "task": (baseline.task_id, baseline.task_revision)
        == (with_skill.task_id, with_skill.task_revision),
        "agent_profile": baseline.agent_profile == with_skill.agent_profile,
        "base_skill_locks": base_locks(baseline) == base_locks(with_skill),
        "resolved_tools": baseline.resolved_tools == with_skill.resolved_tools,
        "effective_permissions": baseline.effective_permissions == with_skill.effective_permissions,
        "output_contracts": baseline.output_contracts == with_skill.output_contracts,
        "registry_digest": baseline.registry_digest == with_skill.registry_digest,
    }
    drift = [field for field, matches in comparisons.items() if not matches]
    if not drift:
        return []
    return [
        _block(
            "EVAL-ASSIGNMENT-DRIFT",
            f"{case_id}: paired Skill Assignments differ beyond the candidate at: {', '.join(drift)}",
        )
    ]


def _check_candidate_pin(
    document: Mapping[str, Any], root: Path, registry_path: str | Path
) -> list[ContractRisk]:
    path = Path(registry_path)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        return [_block("EVAL-CANDIDATE-REGISTRY-MISSING", f"candidate Registry is missing: {path}")]
    candidate_id = document.get("candidate_id")
    try:
        candidates = load_candidates(path)
    except (OSError, ValueError) as exc:
        return [_block("EVAL-CANDIDATE-REGISTRY-INVALID", f"cannot load candidate Registry: {exc}")]
    matches = [item for item in candidates if item.get("candidate_id") == candidate_id]
    if len(matches) != 1:
        return [_block("EVAL-CANDIDATE-UNPINNED", f"candidate {candidate_id!r} is not uniquely registered")]
    candidate = matches[0]
    source_ref = _mapping(document.get("skill_source_ref"))
    drift: list[str] = []
    if candidate.get("source_path") != source_ref.get("path"):
        drift.append("source_path")
    for key, value in (
        ("content_hash", source_ref.get("sha256")),
        ("package_hash", document.get("skill_package_hash")),
    ):
        if str(candidate.get(key, "")).removeprefix("sha256:").lower() != str(
            value or ""
        ).removeprefix("sha256:").lower():
            drift.append(key)
    if drift:
        return [_block("EVAL-CANDIDATE-PIN-DRIFT", "candidate Registry differs at: " + ", ".join(drift))]
    return []


def _load_validation_report(
    root: Path,
    case: Mapping[str, Any],
    arm: Mapping[str, Any],
    case_id: str,
    arm_name: str,
) -> tuple[Mapping[str, Any] | None, list[ContractRisk]]:
    relative = _mapping(arm.get("validation_ref")).get("path")
    if not isinstance(relative, str):
        return None, []
    resolved = resolve_within_root(root, relative)
    if resolved is None or not resolved.is_file():
        return None, []
    value = load_document(resolved)
    if not isinstance(value, Mapping) or SchemaCatalog().validate("deterministic_check_report", value):
        return None, [
            _block(
                "EVAL-VALIDATION-INVALID",
                f"{case_id} {arm_name}: validation evidence is not a deterministic check report",
            )
        ]
    risks: list[ContractRisk] = []
    checker = _mapping(value.get("checker"))
    checker_ref = _mapping(checker.get("source_ref"))
    risks.extend(_check_file_ref(root, checker_ref, f"{case_id} {arm_name} checker"))
    for index, subject in enumerate(value.get("subject_refs", [])):
        if isinstance(subject, Mapping):
            risks.extend(
                _check_file_ref(root, subject, f"{case_id} {arm_name} validation subject[{index}]")
            )
    if value.get("status") != arm.get("deterministic_status"):
        risks.append(
            _block(
                "EVAL-VALIDATION-STATUS-DRIFT",
                f"{case_id} {arm_name}: arm status differs from validation report",
            )
        )
    subject_paths = {
        item.get("path")
        for item in value.get("subject_refs", [])
        if isinstance(item, Mapping)
    }
    required_paths = {
        _mapping(case.get("input_ref")).get("path"),
        _mapping(arm.get("output_ref")).get("path"),
    }
    missing = sorted(str(path) for path in required_paths - subject_paths if path is not None)
    if missing:
        risks.append(
            _block(
                "EVAL-VALIDATION-SUBJECT-DRIFT",
                f"{case_id} {arm_name}: validation report omits: {', '.join(missing)}",
            )
        )
    return value, risks


def _checker_identity(report: Mapping[str, Any]) -> tuple[str, str, str, str]:
    checker = _mapping(report.get("checker"))
    source = _mapping(checker.get("source_ref"))
    return (
        str(checker.get("checker_id", "")),
        str(checker.get("version", "")),
        str(source.get("path", "")),
        str(source.get("sha256", "")).removeprefix("sha256:").lower(),
    )


def _check_file_ref(root: Path, reference: Mapping[str, Any], label: str) -> list[ContractRisk]:
    relative = reference.get("path")
    expected = reference.get("sha256")
    if not isinstance(relative, str) or not isinstance(expected, str):
        return [_block("EVAL-REF-INVALID", f"{label}: invalid file reference")]
    resolved = resolve_within_root(root, relative)
    if resolved is None:
        return [_block("EVAL-REF-OUTSIDE", f"{label}: path escapes project root")]
    if not resolved.is_file():
        return [_block("EVAL-REF-MISSING", f"{label}: missing file {relative}")]
    actual = hash_file(resolved)
    if actual != expected.removeprefix("sha256:").lower():
        return [_block("EVAL-REF-HASH", f"{label}: content hash mismatch")]
    return []


def _existing_file(root: Path, relative: str) -> bool:
    resolved = resolve_within_root(root, relative)
    return resolved is not None and resolved.is_file()


def _check_human_decision(
    evaluation: Mapping[str, Any], root: Path, relative: str
) -> list[ContractRisk]:
    resolved = resolve_within_root(root, relative)
    if resolved is None or not resolved.is_file():
        return [_block("EVAL-DECISION-MISSING", f"missing Decision file: {relative}")]
    value = load_document(resolved)
    if (
        not isinstance(value, Mapping)
        or value.get("object_type") != "decision"
        or SchemaCatalog().validate("research_object", value)
    ):
        return [_block("EVAL-DECISION-INVALID", "admission decision is not a valid Decision object")]
    metadata = _mapping(value.get("metadata"))
    expected = {
        "skill_evaluation_id": evaluation.get("evaluation_id"),
        "skill_candidate_id": evaluation.get("candidate_id"),
        "decision_owner": "human",
        "skill_admission_outcome": _mapping(evaluation.get("admission")).get("outcome"),
    }
    drift = [key for key, expected_value in expected.items() if metadata.get(key) != expected_value]
    if drift:
        return [
            _block(
                "EVAL-DECISION-DRIFT",
                "Decision metadata differs at: " + ", ".join(drift),
            )
        ]
    return []


def _paired_input_characters(root: Path, case: Mapping[str, Any]) -> int | None:
    total = 0
    for key in ("task_contract_ref", "input_ref"):
        relative = _mapping(case.get(key)).get("path")
        if not isinstance(relative, str):
            return None
        resolved = resolve_within_root(root, relative)
        if resolved is None or not resolved.is_file():
            return None
        try:
            total += len(resolved.read_text(encoding="utf-8-sig"))
        except UnicodeDecodeError:
            return None
    return total


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _normalized_hash(value: object) -> str:
    return str(value or "").removeprefix("sha256:").lower()


def _block(code: str, message: str) -> ContractRisk:
    return ContractRisk(code, RiskLevel.BLOCK, message)
