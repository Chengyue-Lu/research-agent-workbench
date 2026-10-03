"""Frozen, one-reservation transport entry gate; no socket-send attestation.

The caller supplies the guard and freezes its external time/source/authorization
inputs. Delegated-entry observations cannot prove billing or network transmission.
"""

from __future__ import annotations

import inspect
import json
import math
import time
from dataclasses import replace

from research_workbench.adapters.models.conformance_body import (
    policy_pin, prepare_body_admission, revalidate_body_admission, validate_encoded_body,
)
from research_workbench.adapters.models.conformance_journal import (
    ConformanceJournalReservation, ConformanceUsageJournal,
)
from research_workbench.adapters.models.http import HttpRequest, HttpResponse, UrllibTransport
from research_workbench.adapters.models.provider_binding import _source_state


class ConformanceTransportError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__("conformance transport: " + code)


def _fail(code: str):
    error = ConformanceTransportError(code)
    try:
        raise error from None
    finally:
        error.__cause__ = None
        error.__context__ = None
        error.__suppress_context__ = True


def _method(instance, name: str):
    method = getattr(instance, name, None)
    if not (inspect.ismethod(method) and method.__self__ is instance
            and method.__func__ is getattr(type(instance), name, None)):
        _fail("transport-binding-drift")
    return method.__func__


def _callback(callable_value):
    if not callable(callable_value):
        _fail("transport-binding-drift")
    return (callable_value, type(callable_value), getattr(callable_value, "__code__", None),
            getattr(type(callable_value), "__call__", None))


class GuardedConformanceTransport:
    """Factory-injected immutable binding with private per-invocation state.

    Entry is committed after the delegated method has returned or raised. A
    crash before that receipt retains the durable intent and full reservation.
    The caller guard can be checked more than once for the same send stage.
    """

    __slots__ = ("_delegate", "_journal", "_guard", "_clock", "_deadline", "_binding",
                 "_active", "_used", "_intent_attempted", "_intent_durable", "_entry", "_entry_observed",
                 "_response", "_maximum", "_last_time", "_failure_code", "_body_policy",
                 "_body_policy_pin", "_body_admission", "_body_state")

    def __init__(self, delegate, journal, guard, *, deadline: float, clock=None, body_policy=None):
        if type(journal) is not ConformanceUsageJournal:
            _fail("transport-binding-drift")
        maximum = getattr(delegate, "max_response_bytes", None)
        if type(maximum) is not int or maximum <= 0:
            _fail("transport-binding-drift")
        if type(deadline) not in {int, float} or not math.isfinite(deadline):
            _fail("deadline-exhausted")
        actual_clock = time.monotonic if clock is None else clock
        methods = ("send", "_read_bounded") if type(delegate) is UrllibTransport else ("send",)
        bound = tuple((name, _method(delegate, name)) for name in methods)
        _, _, source = _source_state(type(delegate).__module__)
        body_pin = None if body_policy is None else self._body_checked(lambda: policy_pin(body_policy))
        binding = (delegate, type(delegate), journal, guard, actual_clock, bound,
                   json.dumps(source, sort_keys=True), _callback(guard), _callback(actual_clock), float(deadline), maximum)
        binding += (body_policy, body_pin)
        observed_time = actual_clock()
        if type(observed_time) not in {int, float} or not math.isfinite(observed_time) or observed_time >= deadline:
            _fail("deadline-exhausted")
        for name, value in (("_delegate", delegate), ("_journal", journal), ("_guard", guard),
                            ("_clock", actual_clock), ("_deadline", float(deadline)),
                            ("_maximum", maximum), ("_binding", binding), ("_active", None),
                            ("_used", False), ("_intent_attempted", False),
                            ("_intent_durable", False), ("_entry", False), ("_entry_observed", False), ("_response", None),
                            ("_last_time", observed_time), ("_failure_code", None),
                            ("_body_policy", body_policy), ("_body_policy_pin", body_pin),
                            ("_body_admission", None), ("_body_state", None)):
            object.__setattr__(self, name, value)

    def __setattr__(self, name, value):
        raise AttributeError("conformance transport binding is frozen")

    @property
    def max_response_bytes(self):
        return self._maximum

    @property
    def intent_attempted(self):
        return self._intent_attempted

    @property
    def intent_durable(self):
        return self._intent_durable

    @property
    def entry_recorded(self):
        return self._entry

    @property
    def entry_observed(self):
        # This process's observation survives a failed durable receipt write.
        return self._entry_observed

    @property
    def received_response(self):
        # Private runtime observation, never included in a report or summary.
        return self._response

    @property
    def failure_code(self):
        return self._failure_code

    def _verify(self):
        delegate, cls, journal, guard, clock, methods, source, guard_pin, clock_pin, deadline, maximum, body_policy, body_pin = self._binding
        if (self._delegate is not delegate or type(self._delegate) is not cls
                or self._journal is not journal or self._guard is not guard or self._clock is not clock
                or self._deadline != deadline or self._maximum != maximum
                or getattr(delegate, "max_response_bytes", None) != self._maximum
                or _callback(guard) != guard_pin or _callback(clock) != clock_pin
                or self._body_policy is not body_policy or self._body_policy_pin != body_pin):
            _fail("transport-binding-drift")
        if any(_method(delegate, name) is not function for name, function in methods):
            _fail("transport-binding-drift")
        _, _, current = _source_state(cls.__module__)
        if json.dumps(current, sort_keys=True) != source:
            _fail("transport-binding-drift")
        if self._body_policy_pin is not None:
            if self._body_checked(lambda: policy_pin(self._body_policy)) != self._body_policy_pin:
                _fail("transport-protocol-failed")

    @staticmethod
    def _body_checked(operation):
        failed = False
        result = None
        try:
            result = operation()
        except Exception:
            failed = True
        if failed:
            _fail("transport-protocol-failed")
        return result

    def _body_verify(self):
        if self._body_policy_pin is not None:
            if self._body_admission is None or self._body_state is None:
                _fail("transport-protocol-failed")
            self._body_checked(lambda: revalidate_body_admission(self._body_policy, self._body_admission, self._body_state))

    def _remaining(self):
        value = self._clock()
        if type(value) not in {int, float} or not math.isfinite(value) or value < self._last_time:
            _fail("deadline-exhausted")
        object.__setattr__(self, "_last_time", value)
        remaining = self._deadline - value
        if remaining <= 0:
            _fail("deadline-exhausted")
        return remaining

    def _guarded(self, stage: str):
        self._verify()
        self._remaining()
        accepted = False
        try:
            accepted = self._guard(stage, self._active.reservation_ordinal) is True
        except Exception:
            pass
        if not accepted:
            _fail("guard-refused")
        # Guard callbacks cannot swap the routing/delegate after validation.
        self._verify()
        self._remaining()

    def arm(self, reservation, *, body_phase=None, model_request=None, expected_call_id=None, expected_assistant_text=()):
        if type(reservation) is not ConformanceJournalReservation or self._active is not None:
            _fail("transport-protocol-failed")
        for name, value in (("_used", False), ("_intent_attempted", False),
                            ("_intent_durable", False), ("_entry", False), ("_entry_observed", False), ("_response", None), ("_failure_code", None)):
            object.__setattr__(self, name, value)
        self._verify()
        self._journal._owned_values(reservation)
        if self._body_policy_pin is not None:
            if reservation.output_upper_tokens < self._body_policy.max_output_tokens:
                _fail("transport-protocol-failed")
            admission = self._body_checked(lambda: prepare_body_admission(self._body_policy, body_phase, model_request,
                expected_call_id=expected_call_id, expected_assistant_text=expected_assistant_text))
            state = (admission.phase, admission.policy_state, admission.model_request, admission.request_state,
                     admission.expected_body, admission.expected_call_id, admission.expected_assistant_text)
            object.__setattr__(self, "_body_admission", admission)
            object.__setattr__(self, "_body_state", state)
        elif body_phase is not None or model_request is not None or expected_call_id is not None or expected_assistant_text:
            _fail("transport-protocol-failed")
        object.__setattr__(self, "_active", reservation)

    def preinvoke(self):
        if self._active is None or self._used:
            _fail("transport-protocol-failed")
        self._body_verify()
        self._guarded("preinvoke")
        self._body_verify()

    def disarm(self):
        object.__setattr__(self, "_active", None)
        object.__setattr__(self, "_body_admission", None)
        object.__setattr__(self, "_body_state", None)

    def send(self, request: HttpRequest) -> HttpResponse:
        try:
            return self._send_once(request)
        except ConformanceTransportError as error:
            if type(error.code) is str and error.code in (
                "guard-refused", "deadline-exhausted", "transport-binding-drift", "transport-protocol-failed",
            ):
                object.__setattr__(self, "_failure_code", error.code)
            raise

    def _send_once(self, request: HttpRequest) -> HttpResponse:
        if self._active is None or self._used or type(request) is not HttpRequest:
            _fail("transport-protocol-failed")
        object.__setattr__(self, "_used", True)
        self._guarded("send")
        remaining = self._remaining()
        if type(request.timeout_seconds) not in {int, float} or not math.isfinite(request.timeout_seconds) or request.timeout_seconds <= 0:
            _fail("transport-protocol-failed")
        clipped = replace(request, timeout_seconds=min(float(request.timeout_seconds), remaining))
        if self._body_policy_pin is not None:
            self._body_checked(lambda: validate_encoded_body(self._body_policy, self._body_admission,
                                                            self._body_state, clipped.body))
        object.__setattr__(self, "_intent_attempted", True)
        self._journal.persist_send_intent(self._active)
        object.__setattr__(self, "_intent_durable", True)
        # Persistence and its callbacks can consume the remaining time or
        # invalidate the caller's gate. Recheck before delegated entry; a
        # refusal here retains the committed intent and full reservation.
        self._guarded("send")
        self._body_verify()
        remaining = self._remaining()
        if type(request.timeout_seconds) not in {int, float} or not math.isfinite(request.timeout_seconds) or request.timeout_seconds <= 0:
            _fail("transport-protocol-failed")
        clipped = replace(request, timeout_seconds=min(float(request.timeout_seconds), remaining))
        if self._body_policy_pin is not None:
            self._body_checked(lambda: validate_encoded_body(self._body_policy, self._body_admission,
                                                            self._body_state, clipped.body))
        send = self._delegate.send
        try:
            response = send(clipped)
            if (type(response) is not HttpResponse or type(response.body) is not bytes
                    or len(response.body) > self._maximum):
                _fail("transport-protocol-failed")
            object.__setattr__(self, "_response", response)
            return response
        finally:
            # The delegated method was invoked, even when it raised before a
            # socket operation. This is a caller-observed entry, not wire proof.
            object.__setattr__(self, "_entry_observed", True)
            self._journal.record_http_entry(self._active)
            object.__setattr__(self, "_entry", True)
