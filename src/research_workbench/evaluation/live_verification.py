"""Pinned evidence readers and current-use checks; Human authority stays external.

No key, Provider send, Tool dispatch, reservation creation or grant is performed.
The selected old conformance journal is a retained history, not a Pilot journal.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from datetime import timedelta, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping
from uuid import UUID

from research_workbench.adapters.models.conformance_budget_anchor import ConformanceBudgetAnchor
from research_workbench.adapters.models.conformance_journal import ConformanceUsageJournal
from research_workbench.adapters.models.conformance_ledger import ConformanceUsageLimits
from research_workbench.adapters.models.profile_conformance_report import verify_profile_conformance_report
from research_workbench.adapters.models.provider_binding import observe_provider_binding
from research_workbench.capability.lifecycle import SkillLifecycleRecord
from research_workbench.evaluation.live_preflight import (
    FrozenLiveContext, LivePreflightVerifiers, VerifiedBudgetCheckpoint,
    _verify, compile_live_preflight, validate_live_preflight,
)
from research_workbench.evaluation.pins import digest, file_ref, require, timestamp
from research_workbench.evaluation.skill_evaluation import assess_skill_evaluation
from research_workbench.io import load_document_bytes


def _json_copy(value):
    # JSON-detached primitives, without retaining aliases to caller mappings.
    def plain(item):
        if isinstance(item, Mapping):
            return {k: plain(v) for k, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [plain(v) for v in item]
        return item
    return json.loads(json.dumps(plain(value), ensure_ascii=False, allow_nan=False))


def _immutable(value):
    if isinstance(value, dict):
        return MappingProxyType({k: _immutable(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_immutable(v) for v in value)
    return value


def _named(value):
    require(type(value) is str and bool(value.strip()) and value.casefold() not in
            {"human", "agent", "system", "unknown"}, "named accountable actor required")
    return value


def _context_commitment(context):
    # The authorization Decision cannot contain its own byte hash.
    result = context.value()
    del result["authorization_ref"]
    return result


def _pin_evaluation_closure(inputs, refs):
    """Pin transitive FileReferences and the existing receipt's file paths."""
    by_path = {ref["path"]: ref for ref in refs}
    documents = []
    for ref in refs:
        raw = inputs.read_bytes(ref)
        if Path(ref["path"]).suffix.lower() in {".json", ".yaml", ".yml"}:
            documents.append(load_document_bytes(Path(ref["path"]), raw))
    bare_paths = {"execution_receipt_ref", "attempt_ref", "agent_profile_ref", "skill_assignment_ref",
                  "context_snapshot_ref", "handoff_ref", "output_refs", "validation_refs"}

    def walk(value, key=None):
        if isinstance(value, Mapping):
            if "path" in value and "sha256" in value:
                ref = file_ref(value)
                require(by_path.get(ref["path"]) == ref, "admission closure omits a transitive FileReference")
            for name, item in value.items():
                walk(item, name)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item, key)
        elif isinstance(value, str) and key in bare_paths:
            require(value in by_path, "admission closure omits an existing receipt file path")
    for value in documents:
        walk(value)


@dataclass(frozen=True, repr=False)
class RetainedConformanceBudget:
    """Independently selected existing DB/anchor/identity; never recreate them.

    The old journal's send observations remain caller attestations. A copied or
    coherently replaced DB+anchor is outside its authentication boundary.
    """
    database: Path
    anchor: Path
    namespace: str
    journal_identity: str
    limits: ConformanceUsageLimits
    grant_root: Path | None = None
    grant_sha256: str | None = None

    def __post_init__(self):
        require(type(self.limits) is ConformanceUsageLimits, "explicit retained budget limits required")
        require(all(type(v) is str and str(UUID(v)) == v for v in
                    (self.namespace, self.journal_identity)), "explicit retained budget identity required")
        object.__setattr__(self, "database", Path(self.database).resolve())
        object.__setattr__(self, "anchor", Path(self.anchor).resolve())
        require((self.grant_root is None) == (self.grant_sha256 is None), "retained grant selection incomplete")
        if self.grant_root is not None:
            object.__setattr__(self, "grant_root", Path(self.grant_root).resolve())
            file_ref({"path": "selected-grant", "sha256": self.grant_sha256})

    def __repr__(self):
        return "<independently selected retained conformance budget>"

    def snapshot(self):
        options = {"namespace": self.namespace, "total_token_limit": self.limits.total_token_limit,
                   "max_attempts": self.limits.max_attempts,
                   "max_invocations_per_attempt": self.limits.max_invocations_per_attempt,
                   "max_output_tokens_per_invocation": self.limits.max_output_tokens_per_invocation}
        anchor_limits = {k: options[k] for k in options if k != "namespace"}
        def read():
            selected = ConformanceBudgetAnchor.open(self.anchor, database_path=self.database,
                namespace=self.namespace, limits=anchor_limits)
            require(selected.identity == self.journal_identity, "retained journal identity substitution")
            with ConformanceUsageJournal.open(self.database, **options, anchor_path=self.anchor,
                    grant_root=self.grant_root, expected_grant_sha256=self.grant_sha256) as journal:
                result = journal.snapshot()
            require(not result["blocked"] and not result["recovery_required"]
                    and result["unresolved_reserved_tokens"] == 0
                    and all(c["settled"] and c["accounting_status"] in
                            {"known", "released-before-send", "verified-reconciled"} for c in result["calls"]),
                    "retained budget contains incomplete usage")
            require(all(a["status"] in {"failed", "completed"} for a in result["attempts"]),
                    "retained budget has an open Attempt")
            return result
        # Fixed diagnostics even for database paths or hostile underlying errors.
        return _verify(lambda _: read(), {}, "retained budget")

    def checkpoint(self, inputs, context):
        pinned = inputs.read(context.budget_checkpoint_ref)
        actual = self.snapshot()
        require(actual == pinned, "retained journal disagrees with frozen checkpoint")
        inputs.recheck()
        return VerifiedBudgetCheckpoint(context.budget_checkpoint_ref, actual["known_total_tokens"],
            actual["unresolved_reserved_tokens"], actual["limits"]["total_token_limit"], True)


@dataclass(frozen=True)
class CurrentLiveObservation:
    """Trusted observer result, never decoded from an applicability artifact."""
    source_commit: str
    windows_context: Mapping
    source_artifact_refs: tuple[Mapping, ...]
    _encoded: str = field(init=False, repr=False)

    def __post_init__(self):
        # Reuse exact commit validation without accepting this object's fields
        # as proof. The independently supplied observer owns their derivation.
        import re
        require(type(self.source_commit) is str and re.fullmatch("[0-9a-f]{40}", self.source_commit),
                "runtime observer needs exact source commit")
        value = {"source_commit": self.source_commit, "windows_context": _json_copy(self.windows_context),
                 "source_artifact_refs": [file_ref(r) for r in self.source_artifact_refs]}
        require(type(value["windows_context"]) is dict and value["windows_context"],
                "runtime observer needs explicit Windows context")
        object.__setattr__(self, "_encoded", json.dumps(value, ensure_ascii=False, allow_nan=False))
        # Public values are detached; value() always uses the frozen encoding.
        object.__setattr__(self, "windows_context", _immutable(value["windows_context"]))
        object.__setattr__(self, "source_artifact_refs", tuple(_immutable(r) for r in value["source_artifact_refs"]))

    def value(self):
        return json.loads(self._encoded)


@dataclass(frozen=True, init=False, repr=False)
class LiveEvidenceVerifiers:
    """Concrete evidence checks around independently supplied Human/actor ports.

    human_verifier must check actual named acceptance, including full Need and
    promotion evidence. runtime_observer must observe this execution context.
    Neither is loaded from a file, defaulted or replaceable by an approved flag.
    """

    inputs: object
    context: FrozenLiveContext
    _admission_json: str
    _need_json: str
    _closure_json: str
    _applicability_json: str
    _binding_json: str
    pilot_owner: str
    executor_id: str
    provider_owner: str
    provider: object
    budget: RetainedConformanceBudget
    cumulative_history: object
    _relation_json: str | None
    human_verifier: Callable
    runtime_observer: Callable

    def __init__(self, inputs, *, context: FrozenLiveContext, admission_evidence: Mapping,
                 need_ref: Mapping, admission_closure_ref: Mapping, pilot_owner: str, executor_id: str,
                 applicability_decision_ref: Mapping, provider_owner: str,
                 binding_ref: Mapping, provider, retained_budget: RetainedConformanceBudget,
                 human_verifier: Callable, runtime_observer: Callable, cumulative_history=None,
                 applicability_relation_ref=None):
        # Local import keeps the journal's existing verification dependency acyclic.
        from research_workbench.evaluation.live_budget_history import RetainedBudgetHistory
        require(isinstance(context, FrozenLiveContext) and type(retained_budget) is RetainedConformanceBudget
                and callable(human_verifier) and callable(runtime_observer)
                and (cumulative_history is None or (type(cumulative_history) is RetainedBudgetHistory
                     and cumulative_history.base == retained_budget)),
                "independent live evidence context and verifiers required")
        require(applicability_relation_ref is None
                or file_ref(applicability_relation_ref) == dict(context.provider_applicability_ref),
                "explicit applicability relation must be the frozen context selection")
        values = {"inputs": inputs, "context": context,
                  "_admission_json": json.dumps(_json_copy(admission_evidence), ensure_ascii=False, allow_nan=False),
                  "_need_json": json.dumps(file_ref(need_ref)),
                  "_closure_json": json.dumps(file_ref(admission_closure_ref)),
                  "_applicability_json": json.dumps(file_ref(applicability_decision_ref)),
                  "_binding_json": json.dumps(file_ref(binding_ref)),
                  "pilot_owner": _named(pilot_owner), "executor_id": _named(executor_id),
                  "provider_owner": _named(provider_owner), "provider": provider, "budget": retained_budget,
                  "cumulative_history": cumulative_history,
                  "_relation_json": None if applicability_relation_ref is None
                                    else json.dumps(file_ref(applicability_relation_ref)),
                  "human_verifier": human_verifier, "runtime_observer": runtime_observer}
        for name, value in values.items():
            object.__setattr__(self, name, value)

    def __repr__(self):
        return "<independently pinned live evidence verifiers>"

    def _expected_inputs(self, argument):
        require(argument["context"] == self.context.value(), "live evidence external context substitution")
        scope = self.inputs.read(self.context.scope_ref, "evaluation_live_scope")
        protocol = self.inputs.read(self.context.protocol_ref, "system_evaluation_protocol")
        plan = self.inputs.read(self.context.plan_ref, "evaluation_harness_plan")
        require(all(argument[k] == v for k, v in (("scope", scope), ("protocol", protocol), ("plan", plan))),
                "live evidence argument differs from pinned inputs")
        when = timestamp(argument["checked_at"])
        require(timestamp(protocol["frozen_at"]) <= when <= timestamp(scope["window"]["not_after"]),
                "live evidence time is outside frozen scope")
        return scope, protocol, plan

    def _human(self, reference, owner, when, operation, evidence):
        decision = self.inputs.read(reference, "research_object")
        require(decision.get("object_type") == "decision" and decision.get("status") == "accepted"
                and decision.get("actor") == _named(owner)
                and decision.get("metadata", {}).get("decision_owner") == "human"
                and timestamp(decision["timestamp"]) <= timestamp(when),
                "accepted named Human Decision required")
        require(_verify(self.human_verifier, {"operation": operation, "decision_ref": file_ref(reference),
            "accountable_human": owner, "checked_at": when, "decision": decision,
            "evidence": evidence}, "Human decision") is True, "named Human acceptance was not verified")
        self.inputs.recheck()
        return decision

    def admission(self, evidence):
        expected = json.loads(self._admission_json)
        require(evidence == expected and file_ref(evidence["protocol_ref"]) == dict(self.context.protocol_ref),
                "independent admission pin substitution")
        protocol = self.inputs.read(self.context.protocol_ref, "system_evaluation_protocol")
        require(file_ref(evidence["admission_case_closure_ref"]) == file_ref(protocol["admission_case_closure_ref"]),
                "independent admission closure substitution")
        evaluation = self.inputs.read(evidence["evaluation_ref"], "skill_evaluation")
        lifecycle = SkillLifecycleRecord.from_mapping(self.inputs.read(evidence["lifecycle_ref"], "skill_lifecycle_record"))
        need_ref = json.loads(self._need_json)
        need = self.inputs.read(need_ref, "skill_need")
        # The shared overlay validates Release/Projection/promotion endpoints.
        # This reader independently checks actual live evidence, not eligibility
        # strings, and passes the full Need to the required Human verifier.
        require(lifecycle.eligible_for_new_binding()
                and need["need_ref"] in lifecycle.need_refs
                and lifecycle.evaluation.evaluation_record_ref == evidence["evaluation_ref"]["path"]
                and lifecycle.admission.decision_ref == evidence["decision_ref"]["path"],
                "admission lifecycle endpoints disagree")
        baseline_paths, trial_paths = [], []
        for target, name in ((baseline_paths, "baseline"), (trial_paths, "with_skill")):
            for case in evaluation["cases"]:
                arm = case["arms"][name]
                target.extend(arm[key]["path"] for key in ("output_ref", "validation_ref"))
                target.append(arm["execution_receipt_ref"])
        require(lifecycle.evaluation.baseline_ref in baseline_paths
                and lifecycle.evaluation.trial_ref in trial_paths
                and all(p in baseline_paths + trial_paths for p in lifecycle.evaluation.promotion_evidence_refs),
                "Lifecycle evidence is outside actual Evaluation arms")
        closure_ref = json.loads(self._closure_json)
        closure = self.inputs.read(closure_ref)
        require(set(closure) == {"version", "purpose", "evaluation_ref", "file_refs"}
                and closure["version"] == "1.0.0" and closure["purpose"] == "skill-admission-evidence"
                and file_ref(closure["evaluation_ref"]) == file_ref(evidence["evaluation_ref"])
                and type(closure["file_refs"]) is list and 0 < len(closure["file_refs"]) <= 4096,
                "independent admission evidence closure required")
        refs = [file_ref(r) for r in closure["file_refs"]]
        by_path = {r["path"]: r for r in refs}
        require(len(by_path) == len(refs) and all(p in by_path for p in baseline_paths + trial_paths)
                and by_path.get(evidence["evaluation_ref"]["path"]) == file_ref(evidence["evaluation_ref"]),
                "admission evidence closure omits or aliases Evaluation artifacts")
        _pin_evaluation_closure(self.inputs, refs)
        assessment = assess_skill_evaluation(evaluation, root=self.inputs.root)
        require(assessment.verdict == "human-decision-recorded", "actual Skill Evaluation closure is not eligible")
        decision = self._human(evidence["decision_ref"], evidence["accountable_human"],
            self.context.case_selection_frozen_at, "skill-admission",
            {"pins": evidence, "need_ref": need_ref, "need": need, "evaluation": evaluation,
             "admission_closure_ref": closure_ref})
        require(decision["metadata"].get("m5_skill_need_evidence") == {
            "need_ref": need_ref, "evaluation_ref": file_ref(evidence["evaluation_ref"]),
            "admission_closure_ref": closure_ref},
            "Human admission does not bind the selected full Need")
        require(evaluation["candidate_id"] in decision["scope"], "Human admission scope omits candidate")
        require(assess_skill_evaluation(evaluation, root=self.inputs.root).verdict == "human-decision-recorded",
                "Skill evidence changed during Human verification")
        self.inputs.recheck()
        return True

    def authorization(self, argument):
        self._expected_inputs(argument)
        decision = self._human(dict(self.context.authorization_ref), self.pilot_owner, argument["checked_at"],
            "m5-live-pilot", {"context": _context_commitment(self.context), "executor_id": self.executor_id})
        require(decision["metadata"].get("m5_live_pilot_authorization") == {
            "task_id": "M5-008", "purpose": "live-pilot", "context": _context_commitment(self.context),
            "executor_id": self.executor_id}, "Pilot Decision does not bind frozen inputs/executor")
        require({"M5-008", self.context.run_id} <= set(decision["scope"]), "Pilot Decision scope omits Task/run")
        return True

    def applicability(self, argument):
        scope, protocol, _ = self._expected_inputs(argument)
        binding_ref = json.loads(self._binding_json)
        relation = None
        if self._relation_json is None:
            report = verify_profile_conformance_report(self.inputs.read(self.context.provider_applicability_ref),
                root=self.inputs.root, schema_root=self.inputs.catalog.directory.parent)
            # Preserve the original exact same-binding path.
            require(file_ref(report["binding"]["manifest_ref"]) == binding_ref
                    and file_ref(report["config_ref"]) == dict(self.context.provider_config_ref),
                    "bound completed M6 evidence differs from external selection")
        else:
            from research_workbench.evaluation.live_applicability import read_provider_applicability_relation
            relation_ref = json.loads(self._relation_json)
            relation, report, pilot = read_provider_applicability_relation(self.inputs, relation_ref,
                expected_pilot_binding_ref=binding_ref)
            require(file_ref(pilot["resolved_config_ref"]) == dict(self.context.provider_config_ref),
                    "Pilot applicability configuration differs from frozen selection")
        require(report["report_version"] in {"1.1.0", "1.2.0"}
                and report["status"] == report["stop_code"] == "completed"
                and report["accounting"] is not None and report["calls"]
                and all(report["assertions"].values()),
                "bound completed M6 evidence differs from external selection")
        require(report["accounting"] == self.budget.snapshot(),
                "qualified M6 report does not match selected retained usage history")
        selected = observe_provider_binding(self.provider, inputs=self.inputs, manifest_ref=binding_ref)
        require(selected == protocol["execution_binding"]["adapter"],
                "actual Provider differs from shared Protocol binding")
        require(report["requested_model"] == protocol["execution_binding"]["model"]["ref"],
                "qualified model differs from frozen Protocol")
        observed = _verify(self.runtime_observer, {"context": self.context.value(),
            "checked_at": argument["checked_at"]}, "runtime context")
        require(type(observed) is CurrentLiveObservation, "typed current runtime observation required")
        actual = observed.value()
        require(actual["source_commit"] == self.context.source_commit
                and actual["windows_context"] == self.inputs.read(self.context.windows_context_ref)
                and actual["source_artifact_refs"] == [file_ref(r) for r in scope["source_artifact_refs"]],
                "current source/Windows context differs from frozen inputs")
        pins = {"task_id": "M5-008", "purpose": "live-pilot", "context": _context_commitment(self.context),
                "binding_ref": binding_ref, "runtime_observation_sha256": digest(actual)}
        if relation is not None:
            pins["applicability_relation"] = {"ref": relation_ref,
                "qualified_report_ref": relation["qualified_report_ref"],
                "qualified_binding_ref": relation["qualified_binding_ref"],
                "pilot_binding_ref": relation["pilot_binding_ref"],
                "comparison_sha256": digest(relation["comparison"]), "limitations": relation["limitations"]}
        decision = self._human(json.loads(self._applicability_json), self.provider_owner, argument["checked_at"],
            "m5-provider-applicability", {**pins, "report": report, **({"relation": relation} if relation is not None else {})})
        require(decision["metadata"].get("m5_live_provider_applicability") == pins,
                "named applicability does not bind current implementation/context")
        require({"M5-008", self.context.run_id} <= set(decision["scope"]), "applicability Decision scope omits Task/run")
        if relation is not None:
            # _human rechecked all selected evidence bytes after its callback.
            # Now reobserve actual loaded Provider state; no Key or HTTP.
            require(observe_provider_binding(self.provider, inputs=self.inputs, manifest_ref=binding_ref) == selected,
                    "Pilot binding changed during Human applicability verification")
        self.inputs.recheck()
        return True

    def budget_checkpoint(self, argument):
        self._expected_inputs(argument)
        selected = self.budget if self.cumulative_history is None else self.cumulative_history
        return selected.checkpoint(self.inputs, self.context)

    def preflight_verifiers(self):
        return LivePreflightVerifiers(self.admission, self.authorization, self.applicability, self.budget_checkpoint)


@dataclass(frozen=True)
class VerifiedPilotReservation:
    """Return from a trusted current Pilot ledger; not a deserialized permit.

    The actual ledger must atomically own single-use handles, durable send
    intent, settlement and failure retention. This DTO implements none of them.
    """
    attempt_id: str
    known_total_tokens: int
    reserved_input_tokens: int
    reserved_output_tokens: int
    other_held_tokens: int
    cumulative_token_limit: int
    provider_calls: int
    attempt_calls: int
    attempt_elapsed_seconds: int
    run_elapsed_seconds: int
    usage_complete: bool
    reservation_ordinal: int | None = None
    send_intent_durable: bool = False

    def __post_init__(self):
        require(type(self.attempt_id) is str and self.attempt_id, "verified Pilot slot required")
        require(all(type(getattr(self, k)) is int and getattr(self, k) >= 0 for k in (
            "known_total_tokens", "reserved_input_tokens", "reserved_output_tokens", "other_held_tokens",
            "cumulative_token_limit", "provider_calls", "attempt_calls", "attempt_elapsed_seconds",
            "run_elapsed_seconds"))
            and type(self.usage_complete) is bool and type(self.send_intent_durable) is bool,
            "invalid verified Pilot reservation")
        require(self.reservation_ordinal is None or (type(self.reservation_ordinal) is int
                and self.reservation_ordinal > 0), "invalid current request reservation identity")
        require(not self.send_intent_durable or self.reservation_ordinal is not None,
                "durable intent needs a current request reservation identity")


class LiveUseGuard:
    """Recheck every Provider/Tool entry; does not execute or issue a permit."""
    def __init__(self, factory: LiveEvidenceVerifiers, *, preflight_ref: Mapping, checked_at: str,
                 clock: Callable, official_window_verifier: Callable, reservation_verifier: Callable):
        require(type(factory) is LiveEvidenceVerifiers and all(callable(p) for p in
                (clock, official_window_verifier, reservation_verifier)), "explicit current live guard ports required")
        self.factory, self._reference, self.checked_at = factory, json.dumps(file_ref(preflight_ref)), checked_at
        timestamp(checked_at)
        self.clock, self.official_window_verifier, self.reservation_verifier = (
            clock, official_window_verifier, reservation_verifier)

    def _clock(self):
        def read(_):
            value = self.clock()
            require(type(value) is str, "trusted clock must return an explicit timestamp")
            return value, timestamp(value)
        return _verify(read, {}, "trusted clock")

    def _reservation(self, context, now, slot, surface, budget, provider_stage):
        reservation = _verify(self.reservation_verifier, {"context": context.value(), "checked_at": now,
            "slot": slot, "surface": surface, "provider_stage": provider_stage,
            "executor_id": self.factory.executor_id}, "current Pilot reservation")
        require(type(reservation) is VerifiedPilotReservation and reservation.attempt_id == slot["attempt_id"],
                "current typed reservation for exact Pilot slot required")
        require(reservation.send_intent_durable == (surface == "provider" and provider_stage == "send"),
                "current request send stage differs from durable intent")
        require(reservation.usage_complete and reservation.other_held_tokens == 0
                and reservation.known_total_tokens >= budget["prior_tokens"]
                and 0 < reservation.cumulative_token_limit <= budget["cumulative_token_limit"]
                and reservation.known_total_tokens + reservation.reserved_input_tokens +
                    reservation.reserved_output_tokens <= reservation.cumulative_token_limit,
                "current cumulative Pilot budget is unknown or exhausted")
        require(reservation.provider_calls <= budget["max_provider_calls"]
                and reservation.attempt_calls <= budget["max_calls_per_attempt"]
                and reservation.reserved_input_tokens <= budget["max_request_input_tokens"]
                and reservation.reserved_output_tokens <= budget["max_request_output_tokens"],
                "current Pilot reservation exceeds frozen request/call bounds")
        require(reservation.attempt_elapsed_seconds < budget["max_attempt_seconds"]
                and reservation.run_elapsed_seconds < budget["max_run_seconds"],
                "current Pilot elapsed time exhausted")
        if surface == "provider":
            require(reservation.reserved_input_tokens > 0 and reservation.reserved_output_tokens > 0
                    and reservation.provider_calls > 0 and reservation.attempt_calls > 0
                    and reservation.reservation_ordinal is not None,
                    "Provider entry needs a current counted reservation")
        return reservation

    def _window(self, now, when, window):
        require(timestamp(window["not_before"]) <= when < timestamp(window["not_after"])
                and when.astimezone(timezone(timedelta(hours=8))).hour >= 18,
                "live entry outside frozen Beijing evening")
        require(_verify(self.official_window_verifier, {"checked_at": now,
            "official_window_ref": file_ref(window["official_window_ref"])}, "official idle window") is True,
                "current official idle window was not verified")

    def check(self, *, attempt_id: str, surface: str, provider_stage: str = "preinvoke"):
        require(surface in {"provider", "tool"}, "unknown live use surface")
        require(provider_stage in {"preinvoke", "send"} and (surface == "provider" or provider_stage == "preinvoke"),
                "unknown live Provider send stage")
        inputs, context = self.factory.inputs, self.factory.context
        now, when = self._clock()
        require(when >= timestamp(self.checked_at), "live clock precedes preflight")
        scope = inputs.read(context.scope_ref, "evaluation_live_scope")
        window, budget = scope["window"], scope["budget"]
        self._window(now, when, window)
        plan = inputs.read(context.plan_ref, "evaluation_harness_plan")
        slots = [{**s, "arm_id": a["arm_id"], "phase": b["phase"], "case_id": b["case_id"],
                  "replicate": b["replicate"]} for b in plan["blocks"] if b["phase"] == "pilot"
                 for a in b["arms"] for s in a["attempt_slots"] if s["attempt_id"] == attempt_id]
        require(len(slots) == 1, "only an exact frozen Pilot slot may enter live use")
        slot = slots[0]
        require(not (surface == "tool" and slot["arm_id"] == "plain-agent"), "A1 Tool entry denied")
        initial = self._reservation(context, now, slot, surface, budget, provider_stage)
        # Cheap denials above touch no execution ports. A successful entry still
        # recomputes the entire original record and all gates at current time.
        original = inputs.read(json.loads(self._reference), "evaluation_live_preflight")
        verifiers = self.factory.preflight_verifiers()
        validate_live_preflight(inputs, original, context=context, expected_checked_at=self.checked_at, verifiers=verifiers)
        request = copy.deepcopy(original["request"])
        request["checked_at"] = now
        compile_live_preflight(inputs, context=context, verifiers=verifiers, **request)
        # Rechecking slow evidence must not leave the entry using an expired
        # clock or a reservation consumed/changed during those checks.
        final_now, final_when = self._clock()
        require(final_when >= when, "live clock moved backwards during verification")
        self._window(final_now, final_when, window)
        final = self._reservation(context, final_now, slot, surface, budget, provider_stage)
        require((initial.reservation_ordinal, initial.reserved_input_tokens, initial.reserved_output_tokens) ==
                (final.reservation_ordinal, final.reserved_input_tokens, final.reserved_output_tokens),
                "current request reservation changed during verification")
        inputs.recheck()
        return True
