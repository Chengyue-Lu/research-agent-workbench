"""Deterministic document-kind inference shared by validation modules."""

from __future__ import annotations

from typing import Any, Mapping


def infer_document_kind(document: Mapping[str, Any]) -> str | None:
    registry_kind = document.get("registry_kind")
    if isinstance(registry_kind, str):
        return registry_kind
    if "attempt_id" in document and "task_id" in document:
        if "result" in document:
            return "handoff_packet"
        if "started_at" in document and "task_revision" in document:
            return "attempt"
    if "goal" in document and "task_id" in document:
        return "task_packet"
    if "project_id" in document and "active_modes" in document:
        return "project_protocol"
    if "mode_id" in document and "claim_rules" in document:
        return "research_mode"
    if (
        document.get("migration_kind") == "research_mode_migration"
        and "source_mode" in document
        and "target_mode" in document
    ):
        return "research_mode_migration"
    if "matrix_id" in document and "authority_classes" in document and "entries" in document:
        return "decision_authority_matrix"
    if "eligibility_id" in document and "matrix_ref" in document and "result" in document:
        return "authority_rule_eligibility"
    if "action_id" in document and "mode_ref" in document and "claim_effects" in document:
        return "mode_action"
    if "resolution_id" in document and "mode_resolution" in document and "action_decisions" in document:
        return "method_resolution"
    if "requirement_id" in document and "constraints" in document and "unsatisfied_requirement" in document:
        return "capability_requirement"
    if document.get("evidence_kind") in {
        "deterministic-fixture",
        "local-conformance",
        "live-conformance",
    }:
        return "capability_conformance_evidence"
    if "need_id" in document and "semantic_gap" in document and "evaluation_requirements" in document:
        return "skill_need"
    if "lifecycle_id" in document and "skill_ref" in document and "runtime_eligibility" in document:
        return "skill_lifecycle_record"
    if "migration_id" in document and "source_registry_path" in document and "target_index_path" in document:
        return "skill_lifecycle_migration"
    if "profile_id" in document and "method_standard" in document and "method_obligations" in document:
        return "protocol_profile"
    if "report_id" in document and "supply_identity" in document and "availability" in document:
        return "capability_supply_report"
    if "snapshot_id" in document and "selected_supply_report_ref" in document:
        return "resolved_capability_snapshot"
    if document.get("profile") == "runtime-bundle" and "bundle_id" in document and "documents" in document:
        return "runtime_bundle_manifest"
    if "binding_id" in document and "selected_supply_report_ref" in document and "host" in document:
        return "execution_binding"
    if document.get("record_kind") == "actual-execution-binding" and "actual_binding" in document:
        return "execution_trace_fact"
    if "report_id" in document and "actual_binding" in document and "actual_facts" in document:
        return "execution_host_report"
    if document.get("scope") == "m11-core" and "gate_id" in document and "paths" in document:
        return "execution_core_gate"
    if "receipt_id" in document and "host_report_ref" in document and "view_ref" in document:
        return "generic_execution_receipt"
    if "policy_id" in document and "policy_kind" in document and "permission_ceiling" in document:
        return "execution_policy"
    if "view_id" in document and "execution_binding_ref" in document and "effective_constraints" in document:
        return "resolved_execution_view"
    if "resolution_id" in document and "requirement_ref" in document and "comparisons" in document:
        return "capability_resolution"
    if document.get("scope") == "phase-b-evolution" and "gate_id" in document:
        return "phase_b_evolution_gate"
    if "case_id" in document and "state_alias" in document and "method_trace_alias" in document:
        return "phase_c_gate_manifest"
    if "gate_id" in document and "machine_gate" in document and "phase_c_closeout" in document:
        return "phase_c_gate_report"
    if "agent_profile_id" in document and "permission_ceiling" in document:
        return "agent_profile"
    if "skill_id" in document and "capabilities" in document:
        return "skill_manifest"
    if "assignment_id" in document and "skill_lock" in document:
        return "skill_assignment"
    if "checkpoint_id" in document and "project_protocol_ref" in document:
        return "main_state"
    if "snapshot_id" in document and "assessment" in document and "metrics" in document:
        return "context_snapshot"
    if "receipt_id" in document and "execution_kind" in document and "attempt_ref" in document:
        return "execution_receipt"
    if "audit_id" in document and "manifest_ref" in document and "mappings" in document:
        return "handoff_transfer_audit"
    if "manifest_id" in document and "source_artifact_refs" in document and "items" in document:
        return "handoff_transfer_manifest"
    if "report_id" in document and "adapter_id" in document and "checks" in document:
        return "provider_conformance_report"
    if "report_id" in document and "checker" in document and "checks" in document:
        return "deterministic_check_report"
    if "report_id" in document and "source_id" in document and "archive_signals" in document:
        return "skill_archive_audit"
    if "evaluation_id" in document and "candidate_id" in document and "cases" in document:
        return "skill_evaluation"
    if "admission_id" in document and "acquisition" in document and "admitted_path" in document:
        return "source_admission"
    if "state_id" in document and "entries" in document and "open_items" in document:
        return "research_state"
    if "trace_id" in document and "method_application" in document and "path_dispositions" in document:
        return "method_trace"
    if "lineage_id" in document and "execution_attempt_ref" in document and "state_ref" in document:
        return "research_attempt_lineage"
    if "failure_id" in document and "learned_result" in document and "revisit_condition" in document:
        return "research_failure"
    if "object_type" in document and "object_id" in document:
        return "research_object"
    return None
