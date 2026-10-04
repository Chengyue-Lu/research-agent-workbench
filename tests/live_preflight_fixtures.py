"""Synthetic v2 shared-gate inputs and a temporary accounting fixture.

No Provider/Tool, production journal, real Human decision or admitted Skill.
Common fixture resources are reused; fresh v2 records never relabel an H2 result.
"""
import copy

from research_workbench.adapters.models.conformance_journal import ConformanceUsageJournal
from research_workbench.adapters.models.port import Usage
from research_workbench.evaluation.comparability import (
    comparison_surface, derive_comparability,
)
from research_workbench.evaluation.harness_plan import compile_harness_plan
from research_workbench.evaluation.harness_preflight import produce_a3_qualification
from research_workbench.evaluation.live_inputs import LiveEvaluationInputs
from research_workbench.evaluation.live_preflight import (
    FrozenLiveContext, LivePreflightVerifiers, VerifiedBudgetCheckpoint,
)
from research_workbench.evaluation.overlap import derive_overlap, validator_identity
from research_workbench.evaluation.overlay import validate_overlay
from research_workbench.evaluation.pins import digest, require
from research_workbench.evaluation.qualification import validate_qualification
from research_workbench.execution.baseline_envelope import produce_a2_qualification
from tests.harness_fixtures import HarnessFixture
from tests.system_evaluation_fixtures import AT, ROOT, record

TOKEN_CEILING = 10_000_000
JOURNAL_POLICY = {"namespace": "556d73bd-31a6-48a5-965d-731f082d9e82",
                  "total_token_limit": TOKEN_CEILING}


class LivePreflightFixture(HarnessFixture):
    def live_inputs(self):
        return LiveEvaluationInputs(self.root, ROOT / "schemas", cumulative_token_ceiling=TOKEN_CEILING)

    def journal(self):
        return ConformanceUsageJournal.open(self.root / "live/fixture.sqlite", **JOURNAL_POLICY)

    def build_live(self, *, overlap_state=None):
        self.build_harness()
        if overlap_state is not None:
            self.refreeze_overlap(overlap_state)
        (self.root / "live").mkdir()
        with ConformanceUsageJournal.create(self.root / "live/fixture.sqlite", **JOURNAL_POLICY) as journal:
            journal.start_attempt()
            handle = journal.reserve(input_upper_tokens=1700, output_upper_tokens=44)
            # Caller-attested synthetic history, not an actual HTTP call.
            journal.persist_send_intent(handle)
            journal.record_http_entry(handle)
            journal.settle(handle, usage=Usage(1700, 44), successful=True, response_received=True)
            # Retain known usage after a synthetic post-response business failure.
            journal.fail_attempt()
            checkpoint = journal.snapshot()
        self.scope = {
            "schema_version": "0.2.0", "record_kind": "evaluation_live_scope", "version": "2.0.0",
            "purpose": "live-pilot", "scope_id": "FIXTURE-LIVE-PREFLIGHT",
            "status": "frozen-inputs-not-authorized", "frozen_at": AT, "source_commit": "0" * 40,
            "source_artifact_refs": [self.raw("live/source.txt", b"synthetic source, not qualification")],
            "provider_config_ref": self.write("live/config.json", {"fixture-only": True}),
            "provider_applicability_ref": self.write("live/applicability.json", {"qualified": False}),
            "windows_context_ref": self.write("live/windows.json", {"fixture-only": True}),
            "budget_checkpoint_ref": self.write("live/checkpoint.json", checkpoint),
            "input_closure_ref": self.case_closure_ref, "tool_configuration_refs": [],
            "execution_phase_allowlist": ["pilot"],
            "output_contract": {"format": "bounded-evidence-relations-v1", "max_body_bytes": 16384,
                "max_json_depth": 5, "cases": [{"case_id": c["case"]["identity"], "claim_ids": ["C01"],
                                              "source_ids": ["S01"]} for c in self.case_closure["cases"]]},
            "budget": {"cumulative_token_limit": TOKEN_CEILING, "prior_tokens": 1744,
                "max_provider_calls": 24, "max_attempts": 8, "max_calls_per_attempt": 3,
                "max_request_input_tokens": 512, "max_request_output_tokens": 64,
                "max_attempt_seconds": 120, "max_run_seconds": 1800, "automatic_retry": False, "fallback": False},
            "window": {"time_zone": "Asia/Shanghai", "not_before": "2026-09-11T10:00:00Z",
                "not_after": "2026-09-11T12:00:00Z",
                "official_window_ref": self.raw("live/window.txt", b"fixture, not official evidence")},
            "boundaries": dict.fromkeys(("runtime_input", "execution_authority", "supply_selection",
                                         "human_decision", "task_completion", "analysis_eligibility"), False)}
        self.scope_ref = self.write("live/scope.json", self.scope)
        self.protocol = copy.deepcopy(self.protocol)
        self.protocol.update(schema_version="0.2.0", version="2.0.0", purpose="live-pilot",
            live_scope_ref=self.scope_ref,
            admission_case_closure_ref=self.write("live/admission-cases.json", self.admission_closure))
        self.protocol["design"]["retry"].update(max_retries=0, eligible_failures=[])
        self.protocol_ref = self.write("live/protocol.json", self.protocol)
        inputs = self.live_inputs()
        # A2 is produced by M6 before invocation of the new preflight.
        self.a2 = produce_a2_qualification(inputs, protocol_ref=self.protocol_ref,
            qualification_id="FIXTURE-LIVE-A2", checked_at=AT, bindings=self.qualification()["bindings"])
        self.a2_ref = self.write("live/a2.json", self.a2)
        self.a3 = produce_a3_qualification(inputs, protocol_ref=self.protocol_ref,
            qualification_id="FIXTURE-LIVE-A3", preflight_checked_at=AT,
            bindings=self.qualification("mode-no-skill")["bindings"])
        self.a3_ref = self.write("live/a3.json", self.a3)
        evaluation = self.doc(self.evaluation_ref["path"])
        admission = {"skill_evaluation_ref": self.evaluation_ref,
            **{k: evaluation[k] for k in ("candidate_id", "skill_id", "skill_version")},
            "closure": self.admission_closure}
        left, right, result = derive_overlap(inputs, self.admission_closure, self.case_closure)
        self.overlap = record("admission_evidence_overlap", "assessment_id", "FIXTURE-LIVE-OVERLAP",
            admission_case_closure=admission, comparison_input_closure={"protocol_ref": self.protocol_ref,
                "case_closure_ref": self.case_closure_ref, "admission_closure_sha256": digest(admission),
                "admission_subjects": left, "comparison_subjects": right,
                "input_digest": digest({"admission": left, "comparison": right})},
            assessment_result={"checked_at": AT, "validator": validator_identity(inputs), **result})
        self.overlap_ref = self.write("live/overlap.json", self.overlap)
        self.overlay = copy.deepcopy(self.overlay)
        self.overlay.update(protocol_ref=self.protocol_ref, manifest_ref=self.manifest_ref,
                            admission_overlap_assessment_ref=self.overlap_ref)
        for key in ("overlap_status", "overlap_refs", "primary_confirmatory_eligible"):
            self.overlay[key] = result[key]
        self.overlay_ref = self.write("live/overlay.json", self.overlay)
        self.admission_pins = {"evaluation_ref": self.overlay["admission_evaluation_ref"],
                              "decision_ref": self.overlay["admission_decision_ref"],
                              "accountable_human": self.overlay["accountable_human"]}
        a3 = validate_qualification(inputs, self.a3, expected_protocol_ref=self.protocol_ref)
        for chain, binding in zip(a3, self.pairwise["a3_runtime_bindings"]):
            chain["view"] = self.doc(binding["view_ref"]["path"])
        comparison = copy.deepcopy(self.pairwise["result"])
        if result["overlap_status"] != "unresolved":
            a4 = validate_overlay(inputs, self.overlay, expected_protocol_ref=self.protocol_ref,
                expected_case_closure_ref=self.case_closure_ref, case_selection_frozen_at=AT,
                admission_verifier=self.verify_admission)
            comparison = derive_comparability(comparison_surface(a3), comparison_surface(a4), admitted_skill_count=1)
        self.pairwise = record("a3_a4_pairwise_comparability", "comparability_id", "FIXTURE-LIVE-PAIRWISE",
            protocol_ref=self.protocol_ref, manifest_ref=self.manifest_ref, a3_qualification_ref=self.a3_ref,
            a4_overlay_ref=self.overlay_ref, a3_runtime_bindings=self.pairwise["a3_runtime_bindings"],
            case_closure_ref=self.case_closure_ref, checked_at=AT, stage="plan-pre-run",
            preregistered_record_ref=None,
            result=comparison)
        self.pairwise_ref = self.write("live/pairwise.json", self.pairwise)
        self.case_bindings = [{"case_id": c["case_id"], "a4_overlay_ref": self.overlay_ref,
                               "pairwise_ref": self.pairwise_ref} for c in self.public_cases]
        self.plan = compile_harness_plan(inputs, protocol_ref=self.protocol_ref,
            case_closure_ref=self.case_closure_ref, case_selection_frozen_at=AT, public_cases=self.public_cases,
            plan_id="FIXTURE-LIVE-PLAN", run_id="FIXTURE-LIVE-RUN")
        self.plan_ref = self.write("live/plan.json", self.plan)
        self.authorization_ref = self.write("live/authorization.json", {"approved": False})
        self.trusted_context = self.context().value()
        return self

    def context(self):
        return FrozenLiveContext(protocol_ref=self.protocol_ref, scope_ref=self.scope_ref, plan_ref=self.plan_ref,
            case_closure_ref=self.case_closure_ref,
            **{k: self.scope[k] for k in ("provider_config_ref", "provider_applicability_ref",
                                        "windows_context_ref", "budget_checkpoint_ref")},
            authorization_ref=self.authorization_ref, source_commit="0" * 40,
            case_selection_frozen_at=AT, run_id="FIXTURE-LIVE-RUN", cumulative_token_ceiling=TOKEN_CEILING)

    def verify_admission(self, evidence):
        # An independent test authority approves only this synthetic fixture.
        return all(evidence[k] == value for k, value in self.admission_pins.items())

    def verify_fixture_scope(self, argument):
        return argument["context"] == self.trusted_context and argument["checked_at"] == AT

    def verify_checkpoint(self, argument):
        require(self.verify_fixture_scope(argument), "synthetic expected context differs")
        with self.journal() as journal:
            snapshot = journal.snapshot()
        pinned = self.doc(argument["context"]["budget_checkpoint_ref"]["path"])
        require(pinned == snapshot, "synthetic checkpoint disagrees with replayed temporary journal")
        return VerifiedBudgetCheckpoint(argument["context"]["budget_checkpoint_ref"],
            snapshot["known_total_tokens"], snapshot["unresolved_reserved_tokens"],
            snapshot["limits"]["total_token_limit"], snapshot["unresolved_reserved_tokens"] == 0)

    def verifiers(self, **overrides):
        return LivePreflightVerifiers(**({"admission": self.verify_admission,
            "authorization": self.verify_fixture_scope, "applicability": self.verify_fixture_scope,
            "budget_checkpoint": self.verify_checkpoint} | overrides))

    def arguments(self, **overrides):
        return {"context": self.context(), "preflight_id": "FIXTURE-LIVE-PREFLIGHT", "checked_at": AT,
                "a2_qualification_ref": self.a2_ref, "a3_qualification_ref": self.a3_ref,
                "overlap_ref": self.overlap_ref, "case_bindings": self.case_bindings,
                "verifiers": self.verifiers()} | overrides
