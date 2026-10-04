"""Nonexecuting live-pilot preflight; authority is supplied independently."""
from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from research_workbench.evaluation.comparability import validate_comparability
from research_workbench.evaluation.harness_plan import validate_harness_plan
from research_workbench.evaluation.harness_preflight import _fresh
from research_workbench.evaluation.live_inputs import LiveEvaluationInputs
from research_workbench.evaluation.overlap import validate_overlap
from research_workbench.evaluation.overlay import AdmissionVerifier, validate_overlay
from research_workbench.evaluation.pins import EvaluationValidationError, digest, file_ref, require, timestamp
from research_workbench.evaluation.qualification import validate_qualification
from research_workbench.evaluation.system_protocol import validate_protocol
from research_workbench.execution.baseline_envelope import compile_baseline_envelope


KIND = "evaluation_live_preflight"
BOUNDARIES = dict.fromkeys(("runtime_input", "execution_authority", "actual_execution",
                           "supply_selection", "human_decision", "task_completion"), False)
REF_FIELDS = ("protocol_ref", "scope_ref", "plan_ref", "case_closure_ref", "provider_config_ref",
              "provider_applicability_ref", "windows_context_ref", "budget_checkpoint_ref", "authorization_ref")


@dataclass(frozen=True)
class FrozenLiveContext:
    """Caller-owned pins. Never construct trusted context from a report under test."""
    protocol_ref: Mapping
    scope_ref: Mapping
    plan_ref: Mapping
    case_closure_ref: Mapping
    provider_config_ref: Mapping
    provider_applicability_ref: Mapping
    windows_context_ref: Mapping
    budget_checkpoint_ref: Mapping
    authorization_ref: Mapping
    source_commit: str
    case_selection_frozen_at: str
    run_id: str
    cumulative_token_ceiling: int

    def __post_init__(self):
        for name in REF_FIELDS:
            object.__setattr__(self, name, MappingProxyType(file_ref(getattr(self, name))))
        require(isinstance(self.source_commit, str) and re.fullmatch(r"[0-9a-f]{40}", self.source_commit),
                "external live context needs an exact source commit")
        require(isinstance(self.run_id, str) and self.run_id.strip(), "external run identity required")
        require(type(self.cumulative_token_ceiling) is int and self.cumulative_token_ceiling > 0,
                "external cumulative token ceiling required")
        timestamp(self.case_selection_frozen_at)

    def value(self):
        return {**{name: dict(getattr(self, name)) for name in REF_FIELDS},
                "source_commit": self.source_commit, "case_selection_frozen_at": self.case_selection_frozen_at,
                "run_id": self.run_id, "cumulative_token_ceiling": self.cumulative_token_ceiling}


@dataclass(frozen=True)
class VerifiedBudgetCheckpoint:
    """Verified frozen ledger prefix, supplied by a trusted reader, not a file flag.

    This is the checkpoint at input freeze; it is not a live current reservation
    or available-balance grant. The later per-use guard must query current usage.
    """
    checkpoint_ref: Mapping
    known_total_tokens: int
    held_total_tokens: int
    cumulative_token_limit: int
    usage_complete: bool

    def __post_init__(self):
        object.__setattr__(self, "checkpoint_ref", MappingProxyType(file_ref(self.checkpoint_ref)))
        require(all(type(getattr(self, k)) is int and getattr(self, k) >= 0 for k in
                    ("known_total_tokens", "held_total_tokens", "cumulative_token_limit")),
                "invalid external budget snapshot")
        require(type(self.usage_complete) is bool, "external budget completeness must be explicit")

    def value(self):
        return {"checkpoint_ref": dict(self.checkpoint_ref), "known_total_tokens": self.known_total_tokens,
                "held_total_tokens": self.held_total_tokens, "cumulative_token_limit": self.cumulative_token_limit,
                "usage_complete": self.usage_complete}


@dataclass(frozen=True)
class LivePreflightVerifiers:
    """Trusted Maintainer callbacks, never loaded/deserialized from artifacts.

    Each callback receives independent expected pins plus reloaded inputs. It
    must verify actual named authority/applicability/ledger evidence. No callback
    has a default; truthy strings or a JSON approved flag are never accepted.
    """
    admission: AdmissionVerifier
    authorization: Callable[[Mapping], bool]
    applicability: Callable[[Mapping], bool]
    budget_checkpoint: Callable[[Mapping], VerifiedBudgetCheckpoint]

    def __post_init__(self):
        require(all(callable(getattr(self, k)) for k in
                    ("admission", "authorization", "applicability", "budget_checkpoint")),
                "all external live verifiers are required")


def _verify(callback, argument, label):
    failed = False
    try:
        return callback(copy.deepcopy(argument))
    except Exception:
        # Untrusted exception text can contain payloads or credentials.
        failed = True
    if failed:
        # A caller's active exception also must not become implicit context.
        error = EvaluationValidationError(f"external {label} verifier failed")
        try:
            raise error from None
        finally:
            error.__cause__ = None
            error.__context__ = None
            error.__suppress_context__ = True


def validator_identity(inputs):
    from research_workbench.evaluation import (bounded_evidence, comparability, harness_plan, harness_preflight,
                                             live_budget, live_budget_history, live_inputs, live_verification,
                                             overlap, overlay, pins, qualification, system_protocol)
    from research_workbench.execution import baseline_envelope
    from research_workbench.validation import schemas
    paths = [Path(m.__file__) for m in (bounded_evidence, comparability, harness_plan, harness_preflight,
             live_budget, live_budget_history, live_inputs, live_verification, overlap, overlay, pins, qualification,
             system_protocol, baseline_envelope, schemas)]
    paths.append(Path(__file__))
    return {"identity": "evaluation-live-preflight", "version": "2.0.0",
            "sources": dict(sorted(("/".join(p.parts[p.parts.index("research_workbench"):]),
                                     hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths)),
            "schemas_sha256": digest(inputs.schema_identity())}


def compile_live_preflight(inputs: LiveEvaluationInputs, *, context: FrozenLiveContext,
                           preflight_id: str, checked_at: str, a2_qualification_ref: Mapping,
                           a3_qualification_ref: Mapping, overlap_ref: Mapping, case_bindings,
                           verifiers: LivePreflightVerifiers):
    """Recompute all shared gates. Never produce A2, execute or grant permission."""
    require(isinstance(inputs, LiveEvaluationInputs) and isinstance(context, FrozenLiveContext)
            and isinstance(verifiers, LivePreflightVerifiers), "explicit live inputs/context/verifiers required")
    require(inputs.cumulative_token_ceiling == context.cumulative_token_ceiling,
            "reader/external token ceiling mismatch")
    request = {"preflight_id": preflight_id, "checked_at": checked_at,
               "a2_qualification_ref": file_ref(a2_qualification_ref),
               "a3_qualification_ref": file_ref(a3_qualification_ref), "overlap_ref": file_ref(overlap_ref),
               "case_bindings": copy.deepcopy(list(case_bindings))}
    # Validate only the request shape before dereferencing its fields.
    _validate_request_shape(inputs, request)
    identity = validator_identity(inputs)
    # Shared validators expose FileReferences to admission callbacks. Supply a
    # primitive copy, while retaining the immutable caller-owned context.
    protocol_ref = dict(context.protocol_ref)
    case_closure_ref = dict(context.case_closure_ref)
    protocol = validate_protocol(inputs, protocol_ref)
    require(file_ref(protocol["live_scope_ref"]) == dict(context.scope_ref), "external scope substitution")
    scope = inputs.read(context.scope_ref, "evaluation_live_scope")
    require(scope["source_commit"] == context.source_commit, "external source commit substitution")
    for name in ("provider_config_ref", "provider_applicability_ref", "windows_context_ref", "budget_checkpoint_ref"):
        require(file_ref(scope[name]) == dict(getattr(context, name)), "external " + name + " substitution")
    require(file_ref(scope["input_closure_ref"]) == dict(context.case_closure_ref), "external input closure substitution")
    inputs.read_bytes(context.authorization_ref)
    require(timestamp(checked_at) >= timestamp(context.case_selection_frozen_at), "live preflight precedes case freeze")
    require(timestamp(protocol["frozen_at"]) <= timestamp(checked_at)
            <= timestamp(scope["window"]["not_after"]), "live preflight has an expired or inconsistent window")
    plan = validate_harness_plan(inputs, inputs.read(context.plan_ref, "evaluation_harness_plan"),
        expected_protocol_ref=protocol_ref, expected_case_closure_ref=case_closure_ref,
        case_selection_frozen_at=context.case_selection_frozen_at, expected_run_id=context.run_id)
    verification_input = {"context": context.value(), "checked_at": checked_at, "scope": scope,
                          "protocol": protocol, "plan": plan}
    require(_verify(verifiers.authorization, verification_input, "authorization") is True,
            "named Pilot authorization was not independently verified")
    require(_verify(verifiers.applicability, verification_input, "applicability") is True,
            "qualified current applicability was not independently verified")
    checkpoint = _verify(verifiers.budget_checkpoint, verification_input, "budget checkpoint")
    require(isinstance(checkpoint, VerifiedBudgetCheckpoint), "verified typed budget checkpoint required")
    require(dict(checkpoint.checkpoint_ref) == dict(context.budget_checkpoint_ref), "budget checkpoint substitution")
    require(checkpoint.usage_complete and checkpoint.held_total_tokens == 0, "unresolved/held frozen budget")
    require(checkpoint.known_total_tokens == scope["budget"]["prior_tokens"], "actual frozen usage differs from scope history")
    require(scope["budget"]["cumulative_token_limit"] <= checkpoint.cumulative_token_limit
            <= context.cumulative_token_ceiling, "actual frozen ledger ceiling mismatch")
    inputs.recheck()
    qualifications = {}
    for arm_id, ref in (("plain-agent-tool", a2_qualification_ref), ("mode-no-skill", a3_qualification_ref)):
        doc = inputs.read(ref, "arm_execution_qualification")
        require(doc["arm_id"] == arm_id and timestamp(doc["checked_at"]) <= timestamp(checked_at),
                "live qualification arm/time substitution")
        chains = validate_qualification(inputs, doc, expected_protocol_ref=protocol_ref)
        _fresh(chains, checked_at)
        qualifications[arm_id] = {"ref": file_ref(ref), "bindings_sha256": digest(doc["bindings"])}
    overlap = validate_overlap(inputs, inputs.read(overlap_ref, "admission_evidence_overlap"),
        expected_protocol_ref=protocol_ref, expected_case_closure_ref=case_closure_ref,
        case_selection_frozen_at=context.case_selection_frozen_at)
    require(overlap["overlap_status"] != "unresolved", "live overlap is unresolved")
    by_case = {b["case_id"]: b for b in request["case_bindings"]}
    require(len(by_case) == len(request["case_bindings"])
            and set(by_case) == {c["case_id"] for c in plan["cases"]}, "live bindings must cover unique planned cases")
    cases = []
    for case in plan["cases"]:
        binding = by_case[case["case_id"]]
        overlay = inputs.read(binding["a4_overlay_ref"], "a4_execution_qualification")
        require(file_ref(overlay["task_ref"]) == case["task_ref"]
                and file_ref(overlay["admission_overlap_assessment_ref"]) == file_ref(overlap_ref),
                "live overlay Task/overlap substitution")
        require(timestamp(overlay["checked_at"]) <= timestamp(checked_at), "live overlay is from the future")
        admission = lambda evidence: _verify(verifiers.admission, evidence, "admission") is True
        a4 = validate_overlay(inputs, overlay, expected_protocol_ref=protocol_ref,
            expected_case_closure_ref=case_closure_ref,
            case_selection_frozen_at=context.case_selection_frozen_at, admission_verifier=admission)
        _fresh(a4, checked_at)
        pairwise = inputs.read(binding["pairwise_ref"], "a3_a4_pairwise_comparability")
        require(pairwise["stage"] == "plan-pre-run"
                and file_ref(pairwise["a3_qualification_ref"]) == file_ref(a3_qualification_ref)
                and file_ref(pairwise["a4_overlay_ref"]) == file_ref(binding["a4_overlay_ref"]),
                "live pairwise stage/qualification substitution")
        require(timestamp(pairwise["checked_at"]) <= timestamp(checked_at), "live pairwise is from the future")
        comparison = validate_comparability(inputs, pairwise, expected_protocol_ref=protocol_ref,
            expected_case_closure_ref=case_closure_ref,
            case_selection_frozen_at=context.case_selection_frozen_at, admission_verifier=admission)
        payloads = {}
        for arm_id in ("plain-agent", "plain-agent-tool"):
            envelope = compile_baseline_envelope(inputs, protocol_ref=protocol_ref,
                task_ref=case["task_ref"], public_payload_ref=case["public_payload_ref"], arm_id=arm_id,
                envelope_id="LIVE-H2-" + digest([case["case_id"], arm_id]), accountable_owner="evaluation-harness",
                qualification_ref=a2_qualification_ref if arm_id == "plain-agent-tool" else None)
            payloads[arm_id] = digest(envelope["provider_visible_payload"])
        require(payloads["plain-agent"] == case["public_payload_sha256"], "live public payload drift")
        cases.append({"case_id": case["case_id"], "comparison": dict(comparison),
                      "baseline_payload_sha256": payloads, "primary_confirmatory_eligible": False,
                      "pilot_primary_eligible": False})
    request["case_bindings"] = sorted(request["case_bindings"], key=lambda b: b["case_id"])
    inputs.recheck()
    require(validator_identity(inputs) == identity, "live validator identity changed during preflight")
    result = {"schema_version": "0.2.0", "record_kind": KIND, "version": "2.0.0", "purpose": "live-pilot",
              "status": "preflight-checked", "context": context.value(), "request": request,
              "validator": identity, "checkpoint": checkpoint.value(), "qualifications": qualifications,
              "overlap": dict(overlap), "cases": cases, "boundaries": dict(BOUNDARIES)}
    inputs.validate(KIND, result)
    inputs.recheck()
    return result


def _validate_request_shape(inputs, request):
    """Validate the self-contained request fragment, without authority facts."""
    try:
        digest(request)
    except (TypeError, ValueError):
        raise EvaluationValidationError("live request is not finite JSON data") from None
    schema = inputs.live_catalog.schema_for_kind(KIND)
    fragment = {"$schema": schema["$schema"], "$defs": schema["$defs"], **schema["properties"]["request"]}
    errors = list(Draft202012Validator(fragment, format_checker=FormatChecker()).iter_errors(request))
    require(not errors, "live preflight request schema invalid")


def validate_live_preflight(inputs, document, *, context, expected_checked_at, verifiers):
    """Recompute with external expected pins/time, never adopt a saved permit."""
    inputs.validate(KIND, document)
    require(document["context"] == context.value() and document["request"]["checked_at"] == expected_checked_at,
            "live preflight external context/time substitution")
    expected = compile_live_preflight(inputs, context=context, verifiers=verifiers, **document["request"])
    require(document == expected, "live preflight differs from independent recomputation")
    return expected
