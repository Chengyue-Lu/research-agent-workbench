"""Fail-closed Capability Supply, Resolution, and Snapshot registry validation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from research_workbench.capability.lifecycle import SkillLifecycleRecord
from research_workbench.capability.requirements import CapabilityRequirement
from research_workbench.capability.supply import CapabilitySupplyReport, assess_supply, resolve_status
from research_workbench.contracts.common import ContractError
from research_workbench.validation.document_core import (
    ValidationIssue,
    document_has_loaded_bytes as _document_has_loaded_bytes,
    document_hash as _document_hash,
    loaded_document_at as _loaded_document_at,
)
from research_workbench.validation.document_kinds import infer_document_kind


def _aware_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def validate_capability_supply_chain(
    documents: Mapping[Path, Any],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    reports: dict[str, tuple[Path, Mapping[str, Any], CapabilitySupplyReport]] = {}
    resolutions: dict[str, tuple[Path, Mapping[str, Any]]] = {}
    lifecycle_records: dict[str, SkillLifecycleRecord] = {}
    for document in documents.values():
        if not isinstance(document, Mapping) or infer_document_kind(document) != "skill_lifecycle_record":
            continue
        try:
            record = SkillLifecycleRecord.from_mapping(document)
        except ContractError:
            continue
        lifecycle_records[record.reference] = record

    def runtime_eligibility_check(lifecycle_ref: str, eligibility_ref: str) -> bool:
        record = lifecycle_records.get(lifecycle_ref)
        return bool(
            record
            and record.runtime_eligibility.eligibility_ref == eligibility_ref
            and record.externally_verified_for_new_binding(
                # Phase B has no authoritative Phase D evidence or Human
                # Decision document resolver.  Lifecycle state and reference
                # strings therefore remain structural facts and must fail
                # closed for a new Runtime binding.
                evidence_resolver=lambda _reference: False,
                decision_resolver=lambda _reference: False,
            )
        )

    def loaded_ref(
        owner_path: Path,
        reference: Any,
        *,
        missing_code: str,
        hash_code: str,
    ) -> tuple[Path, Mapping[str, Any]] | None:
        if not isinstance(reference, Mapping):
            issues.append(
                ValidationIssue(owner_path, missing_code, "reference must be an object")
            )
            return None
        document_path = reference.get("document_path")
        expected_hash = reference.get("content_hash")
        if not isinstance(document_path, str):
            issues.append(
                ValidationIssue(
                    owner_path,
                    missing_code,
                    "reference has no repository-relative document_path",
                )
            )
            return None
        loaded = _loaded_document_at(documents, document_path)
        if loaded is None:
            issues.append(
                ValidationIssue(
                    owner_path,
                    missing_code,
                    f"referenced document is not loaded: {document_path}",
                )
            )
            return None
        loaded_path, document = loaded
        if isinstance(expected_hash, str) and _document_has_loaded_bytes(documents, loaded_path):
            if _document_hash(documents, loaded_path) != expected_hash.removeprefix("sha256:").lower():
                issues.append(
                    ValidationIssue(
                        owner_path,
                        hash_code,
                        f"referenced document hash does not match: {document_path}",
                    )
                )
        return loaded_path, document

    def validate_evidence(
        identity: Any,
        evidence: Mapping[str, Any],
        required_capability: str | None,
        *,
        owner_path: Path | None = None,
    ) -> str:
        """Validate evidence semantics and return pass/fail/unknown.

        Provider conformance checks prove only low-level adapter behavior.  They
        therefore remain ``unknown`` for a high-level M9 Requirement even when
        the provider report itself passed.
        """

        artifact_ref = evidence.get("artifact_ref")
        if not isinstance(artifact_ref, Mapping):
            return "fail"
        artifact_path = artifact_ref.get("path")
        artifact_hash = artifact_ref.get("sha256")
        if not isinstance(artifact_path, str):
            return "fail"
        loaded = _loaded_document_at(documents, artifact_path)
        if loaded is None:
            return "fail"
        loaded_path, artifact = loaded
        if not isinstance(artifact_hash, str) or (
            _document_has_loaded_bytes(documents, loaded_path)
            and _document_hash(documents, loaded_path) != artifact_hash.removeprefix("sha256:").lower()
        ):
            return "fail"

        declared_kind = evidence.get("artifact_kind")
        expected_kind = {
            "capability-conformance-evidence": "capability_conformance_evidence",
            "provider-conformance-report": "provider_conformance_report",
        }.get(str(declared_kind))
        actual_kind = infer_document_kind(artifact)
        if expected_kind is None or actual_kind != expected_kind:
            if owner_path is not None:
                issues.append(
                    ValidationIssue(
                        owner_path,
                        "CAPABILITY-SUPPLY-EVIDENCE-KIND-MISMATCH",
                        f"declared artifact kind {declared_kind!r} does not match {actual_kind!r}",
                    )
                )
            return "fail"

        evidence_id = evidence.get("evidence_id")
        if expected_kind == "capability_conformance_evidence":
            valid = True
            checks: tuple[tuple[bool, str, str], ...] = (
                (
                    evidence_id == artifact.get("evidence_id"),
                    "CAPABILITY-SUPPLY-EVIDENCE-IDENTITY-MISMATCH",
                    "evidence_id does not match the capability evidence identity",
                ),
                (
                    artifact.get("implementation_ref") == identity.implementation_ref,
                    "CAPABILITY-SUPPLY-EVIDENCE-IMPLEMENTATION-MISMATCH",
                    "capability evidence implementation does not match Supply identity",
                ),
                (
                    artifact.get("implementation_version") == identity.implementation_version,
                    "CAPABILITY-SUPPLY-EVIDENCE-VERSION-MISMATCH",
                    "capability evidence version does not match Supply identity",
                ),
            )
            for passed, code, message in checks:
                if not passed:
                    valid = False
                    if owner_path is not None:
                        issues.append(ValidationIssue(owner_path, code, message))
            capabilities = artifact.get("capability_ids")
            if required_capability is not None and (
                not isinstance(capabilities, list)
                or required_capability not in capabilities
            ):
                valid = False
                if owner_path is not None:
                    issues.append(
                        ValidationIssue(
                            owner_path,
                            "CAPABILITY-SUPPLY-EVIDENCE-CAPABILITY-MISMATCH",
                            f"capability evidence does not prove {required_capability!r}",
                        )
                    )
            evidence_kind = artifact.get("evidence_kind")
            evidence_class = evidence.get("evidence_class")
            if (
                (evidence_class == "deterministic" and evidence_kind != "deterministic-fixture")
                or (
                    evidence_class == "live"
                    and evidence_kind not in {"local-conformance", "live-conformance"}
                )
            ):
                valid = False
                if owner_path is not None:
                    issues.append(
                        ValidationIssue(
                            owner_path,
                            "CAPABILITY-SUPPLY-EVIDENCE-CLASS-MISMATCH",
                            "Supply evidence_class does not match the typed evidence_kind",
                        )
                    )
            if not valid or artifact.get("result") == "fail":
                if owner_path is not None and artifact.get("result") == "fail":
                    issues.append(
                        ValidationIssue(
                            owner_path,
                            "CAPABILITY-SUPPLY-EVIDENCE-RESULT-FAILED",
                            "referenced capability evidence records a failed result",
                        )
                    )
                return "fail"
            return "pass" if artifact.get("result") == "pass" else "unknown"

        adapter_components = [
            component
            for component in identity.components
            if component.component_kind == "adapter"
        ]
        adapter_matches = any(
            component.component_ref == artifact.get("adapter_id")
            and component.version == artifact.get("adapter_version")
            for component in adapter_components
        )
        provider_components = [
            component
            for component in identity.components
            if component.component_kind == "provider"
        ]
        provider_matches = any(
            component.component_ref == artifact.get("provider")
            for component in provider_components
        )
        valid = True
        provider_checks: tuple[tuple[bool, str, str], ...] = (
            (
                evidence_id == artifact.get("report_id"),
                "CAPABILITY-SUPPLY-EVIDENCE-IDENTITY-MISMATCH",
                "evidence_id does not match ProviderConformanceReport.report_id",
            ),
            (
                evidence.get("evidence_class") == "live",
                "CAPABILITY-SUPPLY-EVIDENCE-CLASS-MISMATCH",
                "ProviderConformanceReport must be referenced as live evidence",
            ),
            (
                adapter_matches,
                "CAPABILITY-SUPPLY-EVIDENCE-IMPLEMENTATION-MISMATCH",
                "ProviderConformanceReport adapter identity/version does not match a Supply component",
            ),
            (
                provider_matches,
                "CAPABILITY-SUPPLY-EVIDENCE-IMPLEMENTATION-MISMATCH",
                "ProviderConformanceReport provider identity does not match a Supply component",
            ),
        )
        for passed, code, message in provider_checks:
            if not passed:
                valid = False
                if owner_path is not None:
                    issues.append(ValidationIssue(owner_path, code, message))
        if not valid or artifact.get("status") == "failed":
            if owner_path is not None and artifact.get("status") == "failed":
                issues.append(
                    ValidationIssue(
                        owner_path,
                        "CAPABILITY-SUPPLY-EVIDENCE-RESULT-FAILED",
                        "referenced ProviderConformanceReport records a failed result",
                    )
                )
            return "fail"
        # text/structured/tools checks are intentionally not a proof of a
        # scientific or method-level Capability Requirement.
        return "unknown"

    def evidence_check(identity: Any, evidence: Mapping[str, Any], requirement_id: str) -> str:
        return validate_evidence(identity, evidence, requirement_id)

    for path, document in documents.items():
        if not isinstance(document, Mapping) or infer_document_kind(document) != "capability_supply_report":
            continue
        try:
            parsed = CapabilitySupplyReport.from_mapping(document)
        except ContractError as exc:
            issues.append(
                ValidationIssue(path, "CAPABILITY-SUPPLY-CONTRACT", str(exc))
            )
            continue
        if parsed.reference in reports:
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-SUPPLY-IDENTITY-DUPLICATE",
                    f"duplicate Supply Report identity: {parsed.reference}",
                )
            )
            continue
        reports[parsed.reference] = (path, document, parsed)

        component_kinds = {component.component_kind for component in parsed.supply_identity.components}
        required_kinds = {
            "procedure": {"procedure"},
            "tool": {"tool"},
            "adapter-provider": {"adapter", "provider"},
            "skill": {"skill"},
        }.get(parsed.supply_identity.supply_kind, set())
        if not required_kinds <= component_kinds:
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-SUPPLY-COMPONENT-INCOMPLETE",
                    f"{parsed.supply_identity.supply_kind} supply requires component kinds {sorted(required_kinds)}",
                )
            )
        # A Report only states supply facts.  Skill lifecycle and external
        # admission evidence are evaluated by Resolution for a requested
        # qualification; they do not make the Report itself invalid.
        component_keys = [
            (component.component_kind, component.component_ref, component.version)
            for component in parsed.supply_identity.components
        ]
        if len(component_keys) != len(set(component_keys)):
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-SUPPLY-COMPONENT-DUPLICATE",
                    "Supply Report component identities must be unique",
                )
            )
        availability_scope = parsed.availability.get("scope")
        expected_scope_kind = {
            "synthetic-bounded-fixture": "fixture-only",
            "deterministic-local": "local-environment",
            "live-observation": "provider-observation",
        }.get(parsed.observation_scope)
        if (
            not isinstance(availability_scope, Mapping)
            or availability_scope.get("scope_kind") != expected_scope_kind
        ):
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-SUPPLY-OBSERVATION-SCOPE-MISMATCH",
                    "Report observation_scope does not match its provider-neutral availability scope",
                )
            )
        observed_at = _aware_datetime(parsed.availability.get("observed_at"))
        valid_until_value = parsed.availability.get("valid_until")
        valid_until = (
            _aware_datetime(valid_until_value)
            if valid_until_value is not None
            else None
        )
        if observed_at is None or (
            valid_until_value is not None
            and (valid_until is None or observed_at > valid_until)
        ):
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-SUPPLY-AVAILABILITY-TIME-INVALID",
                    "availability timestamps must be timezone-aware and valid_until cannot precede observed_at",
                )
            )
        evidence_ids: set[str] = set()
        for evidence in parsed.conformance_evidence:
            evidence_id = evidence.get("evidence_id")
            if isinstance(evidence_id, str):
                if evidence_id in evidence_ids:
                    issues.append(
                        ValidationIssue(
                            path,
                            "CAPABILITY-SUPPLY-EVIDENCE-DUPLICATE",
                            f"duplicate conformance evidence identity: {evidence_id}",
                        )
                    )
                evidence_ids.add(evidence_id)
            artifact_ref = evidence.get("artifact_ref")
            if not isinstance(artifact_ref, Mapping):
                continue
            artifact_path = artifact_ref.get("path")
            artifact_hash = artifact_ref.get("sha256")
            if not isinstance(artifact_path, str):
                continue
            loaded = _loaded_document_at(documents, artifact_path)
            if loaded is None:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-SUPPLY-EVIDENCE-MISSING",
                        f"conformance evidence artifact is not loaded: {artifact_path}",
                    )
                )
            elif isinstance(artifact_hash, str) and _document_has_loaded_bytes(documents, loaded[0]):
                if _document_hash(documents, loaded[0]) != artifact_hash.removeprefix("sha256:").lower():
                    issues.append(
                        ValidationIssue(
                            path,
                            "CAPABILITY-SUPPLY-EVIDENCE-HASH-MISMATCH",
                            f"conformance evidence hash does not match: {artifact_path}",
                        )
                    )
            # Check typed identity and result independently of the status text
            # carried by the Supply Report.  Report fields never override the
            # referenced artifact.
            validate_evidence(parsed.supply_identity, evidence, None, owner_path=path)
            loaded_artifact = _loaded_document_at(documents, artifact_path)
            if loaded_artifact is not None and evidence.get("artifact_kind") == "capability-conformance-evidence":
                capabilities = loaded_artifact[1].get("capability_ids")
                if isinstance(capabilities, list) and not set(capabilities) <= set(parsed.provided_capabilities):
                    issues.append(
                        ValidationIssue(
                            path,
                            "CAPABILITY-SUPPLY-EVIDENCE-CAPABILITY-DRIFT",
                            "capability evidence claims capabilities absent from the Supply Report",
                        )
                    )
                artifact_scope = loaded_artifact[1].get("scope")
                availability_scope = parsed.availability.get("scope")
                scope_matches = False
                if isinstance(artifact_scope, Mapping) and isinstance(
                    availability_scope, Mapping
                ):
                    if evidence.get("evidence_class") == "deterministic":
                        scope_matches = (
                            artifact_scope.get("scope_kind")
                            == "synthetic-bounded-fixture"
                            and availability_scope.get("scope_kind") == "fixture-only"
                            and artifact_scope.get("fixture_id")
                            == availability_scope.get("fixture_id")
                        )
                    else:
                        scope_matches = (
                            artifact_scope.get("scope_kind")
                            == availability_scope.get("scope_kind")
                            and artifact_scope.get("scope_kind")
                            in {"local-environment", "provider-observation"}
                            and artifact_scope.get("scope_ref")
                            == availability_scope.get("scope_ref")
                        )
                if not scope_matches:
                    issues.append(
                        ValidationIssue(
                            path,
                            "CAPABILITY-SUPPLY-EVIDENCE-SCOPE-MISMATCH",
                            "typed evidence observation scope does not match the Supply availability scope",
                        )
                    )

    for path, document in documents.items():
        if not isinstance(document, Mapping) or infer_document_kind(document) != "capability_resolution":
            continue
        resolution_id = document.get("resolution_id")
        revision = document.get("revision")
        if not isinstance(resolution_id, str) or not isinstance(revision, int):
            continue
        resolution_ref = f"{resolution_id}@r{revision}"
        if resolution_ref in resolutions:
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-RESOLUTION-IDENTITY-DUPLICATE",
                    f"duplicate Capability Resolution identity: {resolution_ref}",
                )
            )
            continue
        resolutions[resolution_ref] = (path, document)

        method_loaded = loaded_ref(
            path,
            document.get("method_resolution_ref"),
            missing_code="CAPABILITY-RESOLUTION-METHOD-MISSING",
            hash_code="CAPABILITY-RESOLUTION-METHOD-HASH-MISMATCH",
        )
        method_document: Mapping[str, Any] | None = None
        if method_loaded is not None:
            _, method_document = method_loaded
            expected_method_ref = f"{method_document.get('resolution_id')}@r{method_document.get('revision')}"
            if document.get("method_resolution_ref", {}).get("ref") != expected_method_ref:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-METHOD-IDENTITY-MISMATCH",
                        f"Method Resolution identity does not match referenced document: {expected_method_ref}",
                    )
                )

        requirement_loaded = loaded_ref(
            path,
            document.get("requirement_ref"),
            missing_code="CAPABILITY-RESOLUTION-REQUIREMENT-MISSING",
            hash_code="CAPABILITY-RESOLUTION-REQUIREMENT-HASH-MISMATCH",
        )
        requirement: CapabilityRequirement | None = None
        requirement_id = None
        if requirement_loaded is not None:
            requirement_path, requirement_document = requirement_loaded
            requirement_id = requirement_document.get("requirement_id")
            if document.get("requirement_ref", {}).get("requirement_id") != requirement_id:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-REQUIREMENT-IDENTITY-MISMATCH",
                        f"Requirement identity does not match referenced document: {requirement_id}",
                    )
                )
            try:
                requirement = CapabilityRequirement.from_mapping(requirement_document)
            except ContractError as exc:
                issues.append(
                    ValidationIssue(requirement_path, "CAPABILITY-REQUIREMENT-CONTRACT", str(exc))
                )
        if method_document is not None and isinstance(requirement_id, str):
            method_requirements = {
                value
                for decision in method_document.get("action_decisions", [])
                if isinstance(decision, Mapping)
                for value in decision.get("capability_requirements", [])
                if isinstance(value, str)
            }
            if requirement_id not in method_requirements:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-METHOD-REQUIREMENT-MISSING",
                        f"Method Resolution does not require capability: {requirement_id}",
                    )
                )

        candidate_refs = document.get("candidate_supply_report_refs", [])
        candidate_ids: list[str] = []
        candidate_reports: list[CapabilitySupplyReport] = []
        method_is_no_skill = (
            method_document is not None
            and isinstance(method_document.get("skill_disposition"), Mapping)
            and method_document["skill_disposition"].get("status") == "no-skill"
        )
        for candidate in candidate_refs:
            if not isinstance(candidate, Mapping) or not isinstance(candidate.get("ref"), str):
                continue
            candidate_ref = str(candidate["ref"])
            candidate_ids.append(candidate_ref)
            loaded = loaded_ref(
                path,
                candidate,
                missing_code="CAPABILITY-RESOLUTION-SUPPLY-MISSING",
                hash_code="CAPABILITY-RESOLUTION-SUPPLY-HASH-MISMATCH",
            )
            registered = reports.get(candidate_ref)
            if registered is None:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-SUPPLY-IDENTITY-MISSING",
                        f"candidate Supply Report identity is not loaded: {candidate_ref}",
                    )
                )
                continue
            if loaded is not None and loaded[0] != registered[0]:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-SUPPLY-PATH-MISMATCH",
                        f"candidate path does not identify Supply Report: {candidate_ref}",
                    )
                )
            candidate_report = registered[2]
            candidate_identity = candidate_report.supply_identity
            if method_is_no_skill and (
                candidate_identity.supply_kind == "skill"
                or any(
                    component.component_kind == "skill"
                    for component in candidate_identity.components
                )
                or candidate_identity.skill_lifecycle_ref is not None
                or candidate_identity.runtime_eligibility_ref is not None
            ):
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-NO-SKILL-SUPPLY",
                        "a Method with no-skill disposition cannot resolve through a Skill Supply, Skill component, or Skill lifecycle binding",
                    )
                )
            candidate_reports.append(candidate_report)
        if len(candidate_ids) != len(set(candidate_ids)):
            issues.append(
                ValidationIssue(
                    path,
                    "CAPABILITY-RESOLUTION-SUPPLY-DUPLICATE",
                    "candidate Supply Report references must be unique",
                )
            )

        if requirement is not None and len(candidate_reports) == len(candidate_ids):
            assessments = [
                assess_supply(
                    requirement,
                    report,
                    evaluated_at=document.get("evaluated_at"),
                    qualification=str(document.get("qualification")),
                    evidence_check=evidence_check,
                    runtime_eligibility_check=runtime_eligibility_check,
                )
                for report in candidate_reports
            ]
            expected_comparisons = [assessment.to_mapping() for assessment in assessments]
            if document.get("comparisons") != expected_comparisons:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-COMPARISON-DRIFT",
                        "recorded supply comparisons do not match deterministic recomputation",
                    )
                )
            expected_status, expected_selected = resolve_status(assessments)
            if document.get("resolution_status") != expected_status:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-STATUS-DRIFT",
                        f"recorded status does not match deterministic result: {expected_status}",
                    )
                )
            if document.get("selected_supply_report_ref") != expected_selected:
                issues.append(
                    ValidationIssue(
                        path,
                        "CAPABILITY-RESOLUTION-SELECTION-DRIFT",
                        f"recorded selection does not match deterministic result: {expected_selected}",
                    )
                )

    snapshot_ids: set[str] = set()
    for path, document in documents.items():
        if not isinstance(document, Mapping) or infer_document_kind(document) != "resolved_capability_snapshot":
            continue
        snapshot_ref = f"{document.get('snapshot_id')}@r{document.get('revision')}"
        if snapshot_ref in snapshot_ids:
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-IDENTITY-DUPLICATE",
                    f"duplicate Resolved Capability Snapshot identity: {snapshot_ref}",
                )
            )
            continue
        snapshot_ids.add(snapshot_ref)
        resolution_loaded = loaded_ref(
            path,
            document.get("resolution_ref"),
            missing_code="RESOLVED-CAPABILITY-SNAPSHOT-RESOLUTION-MISSING",
            hash_code="RESOLVED-CAPABILITY-SNAPSHOT-RESOLUTION-HASH-MISMATCH",
        )
        if resolution_loaded is None:
            continue
        resolution_path, resolution = resolution_loaded
        resolution_ref = f"{resolution.get('resolution_id')}@r{resolution.get('revision')}"
        if document.get("resolution_ref", {}).get("ref") != resolution_ref:
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-RESOLUTION-IDENTITY-MISMATCH",
                    f"Resolution identity does not match referenced document: {resolution_ref}",
                )
            )
        if resolution.get("resolution_status") != "satisfied":
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-UNSATISFIED",
                    "Snapshot requires a satisfied Capability Resolution",
                )
            )
        qualification = document.get("qualification")
        if qualification != resolution.get("qualification"):
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-QUALIFICATION-DRIFT",
                    "Snapshot qualification does not match Capability Resolution",
                )
            )
        for field in ("method_resolution_ref", "requirement_ref"):
            if document.get(field) != resolution.get(field):
                issues.append(
                    ValidationIssue(
                        path,
                        "RESOLVED-CAPABILITY-SNAPSHOT-LINEAGE-DRIFT",
                        f"Snapshot {field} does not match Capability Resolution",
                    )
                )

        method_loaded = loaded_ref(
            path,
            document.get("method_resolution_ref"),
            missing_code="RESOLVED-CAPABILITY-SNAPSHOT-METHOD-MISSING",
            hash_code="RESOLVED-CAPABILITY-SNAPSHOT-METHOD-HASH-MISMATCH",
        )
        task_loaded = loaded_ref(
            path,
            document.get("task_ref"),
            missing_code="RESOLVED-CAPABILITY-SNAPSHOT-TASK-MISSING",
            hash_code="RESOLVED-CAPABILITY-SNAPSHOT-TASK-HASH-MISMATCH",
        )
        task_document: Mapping[str, Any] | None = None
        if method_loaded is not None:
            expected_method_ref = f"{method_loaded[1].get('resolution_id')}@r{method_loaded[1].get('revision')}"
            if document.get("method_resolution_ref", {}).get("ref") != expected_method_ref:
                issues.append(
                    ValidationIssue(
                        path,
                        "RESOLVED-CAPABILITY-SNAPSHOT-METHOD-IDENTITY-MISMATCH",
                        f"Snapshot Method identity does not match {expected_method_ref}",
                    )
                )
        if task_loaded is not None:
            task_path, task_document = task_loaded
            task_revision = task_document.get("revision", 1)
            expected_task_ref = f"{task_document.get('task_id')}@r{task_revision}"
            if document.get("task_ref", {}).get("ref") != expected_task_ref:
                issues.append(
                    ValidationIssue(
                        path,
                        "RESOLVED-CAPABILITY-SNAPSHOT-TASK-IDENTITY-MISMATCH",
                        f"Snapshot Task identity does not match {expected_task_ref}",
                    )
                )
            if method_loaded is not None:
                method_task_ref = method_loaded[1].get("task_ref")
                expected_hash = (
                    _document_hash(documents, task_path)
                    if _document_has_loaded_bytes(documents, task_path)
                    else None
                )
                if not isinstance(method_task_ref, Mapping) or (
                    method_task_ref.get("task_id") != task_document.get("task_id")
                    or method_task_ref.get("revision") != task_revision
                    or (
                        expected_hash is not None
                        and str(method_task_ref.get("sha256", "")).removeprefix("sha256:").lower()
                        != expected_hash
                    )
                ):
                    issues.append(
                        ValidationIssue(
                            path,
                            "RESOLVED-CAPABILITY-SNAPSHOT-TASK-METHOD-LINEAGE-DRIFT",
                            "Snapshot Task does not match the Task frozen by Method Resolution",
                        )
                    )

        selected = document.get("selected_supply_report_ref")
        selected_ref = selected.get("ref") if isinstance(selected, Mapping) else None
        if selected_ref != resolution.get("selected_supply_report_ref"):
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-SELECTION-DRIFT",
                    "Snapshot supply selection does not match Capability Resolution",
                )
            )
        loaded_supply = loaded_ref(
            path,
            selected,
            missing_code="RESOLVED-CAPABILITY-SNAPSHOT-SUPPLY-MISSING",
            hash_code="RESOLVED-CAPABILITY-SNAPSHOT-SUPPLY-HASH-MISMATCH",
        )
        supply_entry = reports.get(str(selected_ref))
        if loaded_supply is None or supply_entry is None:
            continue
        if loaded_supply[0] != supply_entry[0]:
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-SUPPLY-PATH-MISMATCH",
                    f"Snapshot path does not identify Supply Report: {selected_ref}",
                )
            )
        supply_document = supply_entry[1]
        copied_supply_fields = {
            "supply_identity": "supply_identity",
            "supply_required_permissions": "required_permissions",
            "supply_data_egress": "data_egress_behavior",
            "supply_side_effects": "side_effects",
        }
        for snapshot_field, report_field in copied_supply_fields.items():
            if document.get(snapshot_field) != supply_document.get(report_field):
                issues.append(
                    ValidationIssue(
                        path,
                        "RESOLVED-CAPABILITY-SNAPSHOT-SUPPLY-FACT-DRIFT",
                        f"Snapshot {snapshot_field} does not match selected Supply Report",
                    )
                )
        expected_evidence_refs = [
            item.get("artifact_ref")
            for item in supply_document.get("conformance_evidence", [])
            if isinstance(item, Mapping)
        ]
        if document.get("conformance_evidence_refs") != expected_evidence_refs:
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-EVIDENCE-DRIFT",
                    "Snapshot conformance evidence refs do not match selected Supply Report",
                )
            )
        if resolution_path != resolutions.get(resolution_ref, (None, None))[0]:
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-RESOLUTION-PATH-MISMATCH",
                    f"Snapshot path does not identify Capability Resolution: {resolution_ref}",
                )
            )

        if qualification == "structural-replay":
            if document.get("boundaries", {}).get("execution_input") is not False:
                issues.append(
                    ValidationIssue(
                        path,
                        "RESOLVED-CAPABILITY-SNAPSHOT-STRUCTURAL-EXECUTION-FORBIDDEN",
                        "structural-replay Snapshot cannot be an execution input",
                    )
                )
            continue

        if qualification != "runtime-execution":
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-QUALIFICATION-UNKNOWN",
                    f"unsupported Snapshot qualification: {qualification!r}",
                )
            )
            continue

        if document.get("boundaries", {}).get("execution_input") is not True:
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-RUNTIME-EXECUTION-REQUIRED",
                    "runtime-execution Snapshot must be marked as an execution input",
                )
            )
        parsed_report = supply_entry[2]
        required_capability = document.get("requirement_ref", {}).get("requirement_id")
        live_typed_evidence = False
        for evidence in parsed_report.conformance_evidence:
            if evidence.get("evidence_class") != "live":
                continue
            artifact_ref = evidence.get("artifact_ref")
            artifact_loaded = (
                _loaded_document_at(documents, artifact_ref.get("path"))
                if isinstance(artifact_ref, Mapping)
                else None
            )
            if (
                artifact_loaded is not None
                and isinstance(required_capability, str)
                and validate_evidence(
                    parsed_report.supply_identity,
                    evidence,
                    required_capability,
                )
                == "pass"
            ):
                live_typed_evidence = True
        availability_scope = parsed_report.availability.get("scope")
        fixture_only = (
            parsed_report.observation_scope == "synthetic-bounded-fixture"
            or (
                isinstance(availability_scope, Mapping)
                and availability_scope.get("scope_kind") == "fixture-only"
            )
        )
        if (
            fixture_only
            or not live_typed_evidence
        ):
            issues.append(
                ValidationIssue(
                    path,
                    "RESOLVED-CAPABILITY-SNAPSHOT-RUNTIME-EVIDENCE-INELIGIBLE",
                    "runtime Snapshot requires non-fixture live typed capability evidence",
                )
            )
    return issues
