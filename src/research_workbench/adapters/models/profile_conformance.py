"""Opt-in three-invocation profile conformance kernel, with caller-attested gates.

This offline-reviewable kernel does not qualify a live run, prove billable input
bounds or close the complete execution source graph. No execute CLI is supplied.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

from research_workbench.adapters.models.configured import build_profile_provider
from research_workbench.adapters.models.conformance_body import (
    policy_pin, prepare_body_admission, validated_response_context,
)
from research_workbench.adapters.models.conformance_journal import ConformanceUsageJournal
from research_workbench.adapters.models.conformance_transport import GuardedConformanceTransport, ConformanceTransportError
from research_workbench.adapters.models.port import (
    Capability, ContentBlock, FinishReason, Message, ModelRequest, ProviderError,
    ProviderErrorCategory, ProviderRegistry, ResponseFormat, ToolChoice, ToolDefinition, Usage,
)
from research_workbench.adapters.models.profile_configuration import ProviderAdapterConfigV2, resolve_profile_configuration
from research_workbench.adapters.models.session import ApiSessionLimits, ApiSessionStatus, ClientTool, IsolatedApiSessionRunner
from research_workbench.adapters.models.session_policy import ConformanceSessionPolicy
from research_workbench.adapters.models.wire_codecs import _profile, _usage


STOP_CODES = (
    "completed", "plan-blocked", "input-bounds-required", "journal-blocked",
    "attempt-admission-refused", "provider-construction-refused", "guard-refused",
    "deadline-exhausted", "transport-binding-drift", "transport-protocol-failed",
    "provider-invocation-failed", "accounting-failed", "session-failed", "capture-gap",
    "tool-shape-failed", "text-assertion-failed", "schema-assertion-failed", "unknown-token-usage",
)
WARNING_CODES = (
    "caller-attested-gates", "partial-source-closure", "input-bound-proof-unverified",
    "windows-run-unaccepted", "remote-strict-unclaimed", "capture-gap",
)


class ProfileConformanceError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__("profile conformance: " + code)


def _fail(code: str):
    error = ProfileConformanceError(code)
    try:
        raise error from None
    finally:
        error.__cause__ = None
        error.__context__ = None
        error.__suppress_context__ = True


def _provider_stop():
    error = ProviderError(ProviderErrorCategory.UNKNOWN, "profile conformance invocation stopped")
    try:
        raise error from None
    finally:
        error.__cause__ = None
        error.__context__ = None
        error.__suppress_context__ = True


def _limits(output, seconds):
    if (type(output) is not int or not 16 <= output <= 256 or type(seconds) not in {int, float}
            or not math.isfinite(seconds) or not 0 < seconds <= 360):
        _fail("plan-blocked")


def _detached(value):
    return json.loads(json.dumps(value, ensure_ascii=True, allow_nan=False))


def profile_conformance_plan(config, *, root, max_output_tokens=256, max_seconds=120):
    """Resolve only nonsecret explicit references. Never probe an environment."""
    _limits(max_output_tokens, max_seconds)
    if type(config) is not ProviderAdapterConfigV2:
        _fail("plan-blocked")
    failed = False
    try:
        profile, resolved = resolve_profile_configuration(config, root=root)
    except Exception:
        failed = True
    if failed:
        _fail("plan-blocked")
    required = {Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}
    missing = sorted(str(item) for item in required - config.capabilities)
    return _detached({
        "schema_version": "0.1.0", "record_kind": "profile_conformance_plan",
        "plan_version": "1.1.0" if max_seconds > 120 else "1.0.0",
        "provider": profile.provider, "profile_id": profile.profile_id, "requested_model": resolved["model"],
        "profile_ref": dict(config.profile_ref), "config_enabled": config.enabled,
        "protocol_family": profile.document["protocol"]["family"],
        "required_capabilities": ["text", "tools", "structured_output"], "missing_capabilities": missing,
        "readiness": "ready" if config.enabled and not missing else "blocked",
        "max_provider_invocations": 3, "max_tool_executions": 1,
        "max_output_tokens": max_output_tokens, "max_seconds": float(max_seconds),
        "session_policy_id": "profile-conformance-specific-none", "session_policy_version": "1.0.0",
        "schema_dialect": "enum-local-exact", "remote_strict_claim": False,
        "live_qualified": False, "qualification": "external-accepted-run-gates-required",
    })


def _numeric(value):
    return value if type(value) is int and 0 <= value <= 2**63 - 1 else None


def _business(phase, response):
    if phase == "specific-tool":
        return (response.finish_reason == FinishReason.TOOL_CALL and len(response.tool_calls) == 1
                and response.tool_calls[0].name == "add_ints" and response.tool_calls[0].executed_by == "client"
                and dict(response.tool_calls[0].arguments) == {"a": 3, "b": 4}
                and all(type(value) is int for value in response.tool_calls[0].arguments.values()))
    text = "".join(block.text or "" for block in response.output if block.kind == "text")
    if response.finish_reason not in {FinishReason.COMPLETE, FinishReason.STOP} or response.tool_calls:
        return False
    if phase == "result-text":
        return text == "7" and all(block.kind == "text" for block in response.output)
    failed = False
    value = None
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        failed = True
    return not failed and type(value) is dict and set(value) == {"sum"} and type(value["sum"]) is int and value["sum"] == 7


def _observed_usage(http_response, profile):
    """Failed-path numeric receipt only; never authenticate identity/content."""
    value = None
    try:
        if http_response is not None:
            document = json.loads(http_response.body)
            if type(document) is dict:
                selected = _profile(profile.to_mapping())
                usage_key = "usageMetadata" if selected.family == "gemini-generate-content" else "usage"
                raw = document.get(usage_key)
                # Monetary validity is separate from token exposure. The
                # Journal intentionally never retains or requires these values.
                if type(raw) is dict:
                    document = {usage_key: {name: item for name, item in raw.items() if name not in {"cost", "currency"}}}
                    value, _ = _usage(document, selected)
    except Exception:
        pass
    return value if type(value) is Usage else None


class _BudgetedProvider:
    def __init__(self, provider, transport, journal, bounds, output, body_policy=None):
        self.provider, self.transport, self.journal = provider, transport, journal
        self.bounds, self.output = bounds, output
        self.calls = []
        self.observed_models = []
        self.invocations = 0
        self.entries = 0
        self.stop = None
        self.body_policy = body_policy
        self.validated_context = None

    def capabilities(self):
        return self.provider.capabilities()

    def _receipt(self, call, usage):
        for name in ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens"):
            call[name] = _numeric(getattr(usage, name, None))

    def generate(self, request):
        index = len(self.calls)
        if index >= 3:
            self.stop = "transport-protocol-failed"
            _provider_stop()
        phase = ("specific-tool", "result-text", "structured")[index]
        handle = None
        received = False
        response = None
        call = {"ordinal": index + 1, "phase": phase, "finish_reason": None,
                "response_received": False, "assertion_passed": False,
                "input_tokens": None, "output_tokens": None, "cached_input_tokens": None, "reasoning_tokens": None}
        try:
            body_options = {}
            if self.body_policy is not None:
                context = self.validated_context if phase == "result-text" else (None, ())
                if context is None:
                    self.stop = "transport-protocol-failed"
                    _provider_stop()
                body_options = {"body_phase": phase, "model_request": request,
                                "expected_call_id": context[0], "expected_assistant_text": context[1]}
                try:
                    prepare_body_admission(self.body_policy, phase, request,
                        expected_call_id=context[0], expected_assistant_text=context[1])
                except Exception:
                    self.stop = "transport-protocol-failed"
                    _provider_stop()
            handle = self.journal.reserve(input_upper_tokens=self.bounds[index], output_upper_tokens=self.output)
            self.calls.append(call)
            self.transport.arm(handle, **body_options)
            self.transport.preinvoke()
            self.invocations += 1
            response = self.provider.generate(request)
            received = True
            call["response_received"] = True
            call["finish_reason"] = response.finish_reason.value
            self._receipt(call, response.usage)
            self.observed_models.append(response.model)
            passed = _business(phase, response)
            call["assertion_passed"] = passed
            # Known facts settle before Session summary capture/business can fail.
            try:
                self.journal.settle(handle, usage=response.usage, successful=passed, response_received=True)
            except Exception:
                self.stop = ("unknown-token-usage" if call["input_tokens"] is None or call["output_tokens"] is None
                             else "accounting-failed")
                _provider_stop()
            if not passed:
                self.stop = {"specific-tool": "tool-shape-failed", "result-text": "text-assertion-failed",
                             "structured": "schema-assertion-failed"}[phase]
                _provider_stop()
            if self.body_policy is not None and phase == "specific-tool":
                try:
                    self.validated_context = validated_response_context(response)
                except Exception:
                    self.stop = "transport-protocol-failed"
                    _provider_stop()
            return response
        except Exception as error:
            if self.stop is None:
                self.stop = self.transport.failure_code or (error.code if type(error) is ConformanceTransportError
                             and type(error.code) is str and error.code in STOP_CODES else "provider-invocation-failed")
            if handle is not None and not received:
                observed = self.transport.received_response
                usage = _observed_usage(observed, self.provider.profile)
                call["response_received"] = observed is not None
                self._receipt(call, usage)
                if observed is not None and not self.transport.entry_recorded:
                    self.stop = "accounting-failed"
                try:
                    if not self.transport.intent_attempted:
                        self.journal.reject_before_send(handle)
                    elif self.transport.entry_recorded:
                        self.journal.settle(handle, usage=usage, successful=False, response_received=observed is not None)
                    elif self.transport.intent_durable:
                        self.journal.record_uncertain_failure(handle)
                    # Failed durable-intent write is conservatively pending,
                    # even when commit outcome cannot be independently known.
                except Exception:
                    if call["input_tokens"] is None or call["output_tokens"] is None:
                        self.stop = "unknown-token-usage" if self.transport.intent_attempted else self.stop
                    else:
                        self.stop = "accounting-failed"
            _provider_stop()
        finally:
            if handle is not None and self.transport.entry_observed:
                self.entries += 1
            self.transport.disarm()


def _source_refs():
    from research_workbench.adapters.models import conformance_transport
    return [{"module": "research_workbench.adapters.models.profile_conformance",
             "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
            {"module": conformance_transport.__name__,
             "source_sha256": hashlib.sha256(Path(conformance_transport.__file__).read_bytes()).hexdigest()}]


def _report(plan, journal, budget, assertions, tool_executions, stop, binding=None, extension=None):
    accounting = None
    try:
        accounting = journal.snapshot()
    except Exception:
        stop = "accounting-failed"
    calls = [] if budget is None else budget.calls
    # Retain observed per-run facts even if the final cumulative snapshot fails.
    entries = 0 if budget is None else budget.entries
    document = {
        "schema_version": "0.1.0", "record_kind": "profile_conformance_report", "report_version": "1.0.0",
        "status": "blocked" if accounting is None or budget is None else "completed" if stop == "completed" else "failed",
        "stop_code": stop, "provider": plan["provider"], "profile_id": plan["profile_id"],
        "requested_model": plan["requested_model"], "observed_models": [] if budget is None else sorted(set(budget.observed_models)),
        "profile_ref": plan["profile_ref"], "config_ref": None,
        "source_refs": binding["source_refs"] if binding is not None else _source_refs(),
        "limits": {"max_provider_invocations": 3, "max_tool_executions": 1,
                   "max_output_tokens": plan["max_output_tokens"], "max_seconds": plan["max_seconds"]},
        "calls": calls, "actual_counts": {"provider_invocations": 0 if budget is None else budget.invocations,
            "http_entry_observations": entries, "tool_executions": tool_executions,
            "responses_received": sum(call["response_received"] for call in calls)},
        "assertions": assertions, "accounting": accounting, "remote_strict_claim": False,
        "live_qualified": False, "qualification": "external-accepted-run-gates-required",
        "http_observation": "delegate-entry-only-not-socket-proof",
        "warnings": list(WARNING_CODES if stop == "capture-gap" else WARNING_CODES[:-1]),
    }
    if binding is not None:
        document.update(binding)
        document["report_version"] = "1.1.0"
    if extension is not None:
        if binding is None:
            _fail("attempt-admission-refused")
        document.update(report_version="1.2.0", budget_extension=extension)
    return _detached(document)


def _report_binding_material(root, transport, body_policy, binding_manifest_ref, input_upper_tokens):
    from research_workbench.adapters.models.http import UrllibTransport
    from research_workbench.adapters.models.provider_binding import (
        CONFORMANCE_ROOTS, GRAPH_POLICY, read_provider_binding_manifest,
    )
    from research_workbench.evaluation.pins import EvaluationInputs
    if body_policy is None or type(transport) is not UrllibTransport:
        raise ValueError("bound conformance requires its production transport and body policy")
    policy_pin(body_policy)
    if (type(input_upper_tokens) is not tuple or len(input_upper_tokens) != 3
            or any(type(value) is not int or not 0 < value <= 10_000_000 for value in input_upper_tokens)):
        raise ValueError("bound conformance requires its input bounds")
    reference = _detached(binding_manifest_ref)
    inputs = EvaluationInputs(root)
    manifest = read_provider_binding_manifest(inputs, reference).to_mapping()
    if (manifest["version"] != "1.1.0" or manifest["binding_policy_version"] != GRAPH_POLICY
            or not set(CONFORMANCE_ROOTS) <= set(manifest["source_roots"])):
        raise ValueError("bound conformance requires its selected source graph")
    implementation_ref = manifest["implementation_closure_ref"]
    graph = inputs.read(implementation_ref)
    frozen_sources = [{"module": item["module"],
        "source_sha256": graph["modules"][item["module"]]["source_ref"]["sha256"]}
        for item in _source_refs()]
    selected = {"config_ref": manifest["resolved_config_ref"], "source_refs": frozen_sources,
        "binding": {"manifest_ref": reference, "implementation_closure_ref": implementation_ref,
            "attempt_ordinal": None,
            "body_policy": {"policy_version": body_policy.policy_version,
                "max_output_tokens": body_policy.max_output_tokens, "max_body_bytes": body_policy.max_body_bytes},
            "input_upper_tokens": list(input_upper_tokens),
            "session_policy": {"policy_id": "profile-conformance-specific-none", "policy_version": "1.0.0"},
            "delegated_transport_class": "research_workbench.adapters.models.http.UrllibTransport"}}
    return selected, implementation_ref, inputs, reference


def run_profile_conformance(config, *, root, journal, transport, credential, guard,
                            input_upper_tokens=None, max_output_tokens=256, max_seconds=120,
                            clock=None, event_sink=None, repair_refreeze_confirmed=False, body_policy=None,
                            binding_manifest_ref=None):
    """Explicit caller-attested execution kernel; no live eligibility is granted."""
    plan = profile_conformance_plan(config, root=root, max_output_tokens=max_output_tokens, max_seconds=max_seconds)
    assertions = {"tool_call_shape": False, "tool_executed_once": False, "text_exact": False, "schema_exact": False}
    report_binding = None
    extension = None
    def emit(stop, budget=None, tool_executions=0):
        # Freeze verified grant provenance before any execution. A later closed
        # or unavailable journal must not erase already observed response facts.
        return _report(plan, journal, budget, assertions, tool_executions, stop, report_binding, extension)
    if type(journal) is not ConformanceUsageJournal:
        _fail("accounting-failed")
    actual_clock = time.monotonic if clock is None else clock
    binding_material = None
    early_started = None
    try:
        extension = journal.extension_metadata()
    except Exception:
        return emit("accounting-failed")
    if max_seconds > 120 and extension is None:
        _fail("attempt-admission-refused")
    if extension is not None:
        try:
            early_started = actual_clock()
            if type(early_started) not in {int, float} or not math.isfinite(early_started):
                raise ValueError("invalid clock")
            if binding_manifest_ref is None:
                raise ValueError("extended execution requires selected binding")
            binding_material = _report_binding_material(root, transport, body_policy, binding_manifest_ref, input_upper_tokens)
            report_binding = binding_material[0]
        except Exception:
            _fail("attempt-admission-refused")
    if plan["readiness"] != "ready":
        return emit("plan-blocked")
    if body_policy is not None:
        try:
            policy_pin(body_policy)
            selected_profile, _ = resolve_profile_configuration(config, root=root)
            document = selected_profile.document
            if (plan["provider"] != body_policy.provider or plan["requested_model"] != body_policy.model
                    or plan["protocol_family"] != body_policy.protocol_family
                    or plan["profile_id"] != "deepseek-responses-nonthinking-v1"
                    or document["generation"]["mode"] != body_policy.mode
                    or max_output_tokens != body_policy.max_output_tokens):
                raise ValueError("unsupported synthetic body profile")
        except Exception:
            return emit("transport-protocol-failed")
    if (type(input_upper_tokens) is not tuple or len(input_upper_tokens) != 3
            or any(type(value) is not int or not 0 < value <= 10_000_000 for value in input_upper_tokens)):
        return emit("input-bounds-required")
    try:
        if journal.snapshot()["blocked"]:
            return emit("journal-blocked")
    except Exception:
        return emit("accounting-failed")
    try:
        started = actual_clock() if early_started is None else early_started
    except Exception:
        return emit("deadline-exhausted")
    if type(started) not in {int, float} or not math.isfinite(started):
        return emit("deadline-exhausted")
    try:
        implementation_ref = None
        actual_guard = guard
        selected_binding = None
        if binding_manifest_ref is not None:
            from research_workbench.adapters.models.provider_binding import (
                observe_provider_binding,
            )
            if binding_material is None:
                binding_material = _report_binding_material(root, transport, body_policy, binding_manifest_ref, input_upper_tokens)
            selected_binding, implementation_ref, inputs, reference = binding_material
            def checked_guard(stage, ordinal):
                accepted = guard(stage, ordinal)
                # A caller guard can run after encoding: check the actual graph
                # again before credentials (preinvoke) or durable send intent.
                provider._assert_frozen_binding()
                inputs.recheck()
                return accepted
            actual_guard = checked_guard
        shared_deadline = started + max_seconds
        bounded = GuardedConformanceTransport(transport, journal, actual_guard, deadline=shared_deadline,
                                             clock=actual_clock, body_policy=body_policy)
        options = {} if implementation_ref is None else {"implementation_closure_ref": implementation_ref}
        provider = build_profile_provider(config, root=root, transport=bounded, credential=credential, **options)
        if selected_binding is not None:
            observe_provider_binding(provider, inputs=inputs, manifest_ref=reference)
            inputs.recheck()
            report_binding = selected_binding
    except Exception:
        return emit("provider-construction-refused")
    try:
        attempt_ordinal = journal.start_attempt(repair_refreeze_confirmed=repair_refreeze_confirmed)
        if report_binding is not None:
            report_binding["binding"]["attempt_ordinal"] = attempt_ordinal
    except Exception:
        return emit("attempt-admission-refused")
    budget = _BudgetedProvider(provider, bounded, journal, input_upper_tokens, max_output_tokens, body_policy=body_policy)
    tool_runs = 0
    tool_schema = {"type": "object", "properties": {"a": {"type": "integer", "enum": [3]},
                    "b": {"type": "integer", "enum": [4]}}, "required": ["a", "b"], "additionalProperties": False}
    definition = ToolDefinition("add_ints", "Add two synthetic integers.", tool_schema, strict=False)
    def remaining_time():
        try:
            # Use the transport's same absolute deadline and monotonic clock
            # validation; a fresh Session/Tool phase never renews this budget.
            return bounded._remaining()
        except Exception:
            budget.stop = "deadline-exhausted"
            _provider_stop()
    def add_ints(arguments):
        nonlocal tool_runs
        remaining_time()
        if dict(arguments) != {"a": 3, "b": 4} or any(type(value) is not int for value in arguments.values()) or tool_runs:
            raise ValueError("conformance Tool contract failed")
        tool_runs += 1
        return arguments["a"] + arguments["b"]
    registry = ProviderRegistry()
    registry.register(plan["provider"], budget)
    runner = IsolatedApiSessionRunner(registry, tools=(ClientTool(definition, add_ints),), clock=actual_clock)
    policy = ConformanceSessionPolicy("profile-conformance-specific-none", "1.0.0", ToolChoice("specific", "add_ints"),
                                      ToolChoice("none"), "add_ints", 1, 2, 1)
    request = ModelRequest(plan["requested_model"], (Message("user", (ContentBlock("text", text=
                           "Call add_ints once with a=3 and b=4. After its result, return only 7."),)),),
                           tools=(definition,), tool_choice=ToolChoice("specific", "add_ints"), max_output_tokens=max_output_tokens)
    stop = None
    try:
        session_remaining = remaining_time()
        session = runner.run(provider_name=plan["provider"], request=request,
            limits=ApiSessionLimits(2, 1, 1, 128, max_output_tokens, session_remaining),
            event_sink=event_sink, tool_choice_transition=policy)
        assertions["tool_call_shape"] = bool(budget.calls and budget.calls[0]["assertion_passed"])
        assertions["tool_executed_once"] = tool_runs == 1
        assertions["text_exact"] = len(budget.calls) == 2 and budget.calls[1]["assertion_passed"]
        if session.status != ApiSessionStatus.COMPLETED:
            stop = budget.stop or ("capture-gap" if session.stop_reason == "trace-capture-gap" else "session-failed")
        elif not all(assertions[key] for key in ("tool_call_shape", "tool_executed_once", "text_exact")):
            stop = "session-failed"
        else:
            schema = {"type": "object", "properties": {"sum": {"type": "integer", "enum": [7]}},
                      "required": ["sum"], "additionalProperties": False}
            structured = ModelRequest(plan["requested_model"], (Message("user", (ContentBlock("text", text=
                                       "Return an object with sum equal to 7."),)),),
                                      response_format=ResponseFormat("json_schema", "sum", schema),
                                      max_output_tokens=max_output_tokens)
            budget.generate(structured)
            assertions["schema_exact"] = budget.calls[2]["assertion_passed"]
            # A synchronous response can return after the shared admission
            # deadline. Its facts were settled first; do not claim a timely
            # completed Attempt or start more work after that boundary.
            remaining_time()
            journal.finish_attempt()
            stop = "completed"
    except Exception:
        stop = budget.stop or "session-failed"
    if stop != "completed":
        try:
            snapshot = journal.snapshot()
            if not snapshot["blocked"] and snapshot["attempts"][-1]["status"] == "open":
                journal.fail_attempt()
        except Exception:
            pass
    return emit(stop, budget, tool_runs)
