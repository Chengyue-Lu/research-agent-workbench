"""Shared once-only reserved HTTP entry mechanics, with explicit journal hooks.

This layer neither selects a Provider nor grants an invocation. A concrete
facade supplies owned-handle and body checks; the trusted caller supplies the
current-use guard. Observed entry is not proof of network transmission/billing.
"""

from __future__ import annotations

import inspect
import json
import math
import time
from dataclasses import replace

from research_workbench.adapters.models.http import HttpRequest, HttpResponse, UrllibTransport
from research_workbench.adapters.models.provider_binding import _source_state


class ReservedTransportError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__("reserved transport: " + code)


def transport_fail(error_type, code):
    error = error_type(code)
    try:
        raise error from None
    finally:
        error.__cause__ = None
        error.__context__ = None
        error.__suppress_context__ = True


def _method(instance, name, fail):
    method = getattr(instance, name, None)
    if not (inspect.ismethod(method) and method.__self__ is instance
            and method.__func__ is getattr(type(instance), name, None)):
        fail("transport-binding-drift")
    return method.__func__


def _callback(value, fail):
    if not callable(value):
        fail("transport-binding-drift")
    return (value, type(value), getattr(value, "__code__", None), getattr(type(value), "__call__", None))


class ReservedProviderTransport:
    """Mechanical base only; journal/body semantics stay in concrete facades.

    The active handle is consumed before intent persistence. After delegated
    return/raise, retain a private response before durable entry capture. A
    failure before the latter leaves the original durable intent conservative.
    """

    __slots__ = ("_delegate", "_journal", "_guard", "_clock", "_deadline", "_binding",
                 "_active", "_ordinal", "_used", "_intent_attempted", "_intent_durable",
                 "_entry", "_entry_observed", "_response", "_maximum", "_last_time", "_failure_code")

    def __init__(self, delegate, journal, guard, *, deadline, clock=None):
        maximum = getattr(delegate, "max_response_bytes", None)
        if type(maximum) is not int or maximum <= 0:
            self._fail("transport-binding-drift")
        if type(deadline) not in {int, float} or not math.isfinite(deadline):
            self._fail("deadline-exhausted")
        actual_clock = time.monotonic if clock is None else clock
        methods = ("send", "_read_bounded") if type(delegate) is UrllibTransport else ("send",)
        bound = tuple((name, _method(delegate, name, self._fail)) for name in methods)
        _, _, source = _source_state(type(delegate).__module__)
        hooks = tuple((name, _method(self, name, self._fail)) for name in (
            "_fail", "_reservation_ordinal", "_policy_binding", "_body_verify", "_encoded_verify", "_intent_guard_stage"))
        binding = (delegate, type(delegate), journal, guard, actual_clock, bound,
                   json.dumps(source, sort_keys=True), _callback(guard, self._fail), _callback(actual_clock, self._fail),
                   float(deadline), maximum, hooks, self._policy_binding())
        observed = actual_clock()
        if type(observed) not in {int, float} or not math.isfinite(observed) or observed >= deadline:
            self._fail("deadline-exhausted")
        for name, value in (("_delegate", delegate), ("_journal", journal), ("_guard", guard),
                            ("_clock", actual_clock), ("_deadline", float(deadline)), ("_maximum", maximum),
                            ("_binding", binding), ("_active", None), ("_ordinal", None), ("_used", False),
                            ("_intent_attempted", False), ("_intent_durable", False), ("_entry", False),
                            ("_entry_observed", False), ("_response", None), ("_last_time", observed), ("_failure_code", None)):
            object.__setattr__(self, name, value)

    def __setattr__(self, name, value):
        raise AttributeError("reserved transport binding is frozen")

    def _fail(self, code):
        transport_fail(ReservedTransportError, code)

    def _reservation_ordinal(self, reservation):
        self._fail("transport-protocol-failed")

    def _policy_binding(self):
        self._fail("transport-protocol-failed")

    def _body_verify(self):
        self._fail("transport-protocol-failed")

    def _encoded_verify(self, request):
        self._fail("transport-protocol-failed")

    def _intent_guard_stage(self):
        return "preinvoke"

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
        return self._entry_observed

    @property
    def received_response(self):
        # Memory-only runtime observation; never included in diagnostics.
        return self._response

    @property
    def failure_code(self):
        return self._failure_code

    def _verify(self):
        delegate, cls, journal, guard, clock, methods, source, guard_pin, clock_pin, deadline, maximum, hooks, policy = self._binding
        if (self._delegate is not delegate or type(self._delegate) is not cls or self._journal is not journal
                or self._guard is not guard or self._clock is not clock or self._deadline != deadline or self._maximum != maximum
                or getattr(delegate, "max_response_bytes", None) != maximum
                or _callback(guard, self._fail) != guard_pin or _callback(clock, self._fail) != clock_pin):
            self._fail("transport-binding-drift")
        if any(_method(self, name, self._fail) is not function for name, function in hooks):
            self._fail("transport-binding-drift")
        if self._policy_binding() != policy:
            self._fail("transport-binding-drift")
        if any(_method(delegate, name, self._fail) is not function for name, function in methods):
            self._fail("transport-binding-drift")
        _, _, current = _source_state(cls.__module__)
        if json.dumps(current, sort_keys=True) != source:
            self._fail("transport-binding-drift")

    def _remaining(self):
        now = self._clock()
        if type(now) not in {int, float} or not math.isfinite(now) or now < self._last_time:
            self._fail("deadline-exhausted")
        object.__setattr__(self, "_last_time", now)
        remaining = self._deadline - now
        if remaining <= 0:
            self._fail("deadline-exhausted")
        return remaining

    def _guarded(self, stage):
        self._verify()
        self._remaining()
        if self._reservation_ordinal(self._active) != self._ordinal:
            self._fail("transport-protocol-failed")
        accepted = False
        try:
            accepted = self._guard(stage, self._ordinal) is True
        except Exception:
            pass
        if not accepted:
            self._fail("guard-refused")
        self._verify()
        self._remaining()
        if self._reservation_ordinal(self._active) != self._ordinal:
            self._fail("transport-protocol-failed")

    def _arm(self, reservation):
        if self._active is not None:
            self._fail("transport-protocol-failed")
        self._verify()
        ordinal = self._reservation_ordinal(reservation)
        if type(ordinal) is not int or ordinal <= 0:
            self._fail("transport-protocol-failed")
        for name, value in (("_used", False), ("_intent_attempted", False), ("_intent_durable", False),
                            ("_entry", False), ("_entry_observed", False), ("_response", None), ("_failure_code", None)):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "_active", reservation)
        object.__setattr__(self, "_ordinal", ordinal)

    def preinvoke(self):
        if self._active is None or self._used:
            self._fail("transport-protocol-failed")
        self._body_verify()
        self._guarded("preinvoke")
        self._body_verify()

    def disarm(self):
        object.__setattr__(self, "_active", None)
        object.__setattr__(self, "_ordinal", None)

    def send(self, request):
        try:
            return self._send_once(request)
        except ReservedTransportError as error:
            if type(error.code) is str and error.code in (
                "guard-refused", "deadline-exhausted", "transport-binding-drift", "transport-protocol-failed"):
                object.__setattr__(self, "_failure_code", error.code)
            raise

    def _send_once(self, request):
        if self._active is None or self._used or type(request) is not HttpRequest:
            self._fail("transport-protocol-failed")
        object.__setattr__(self, "_used", True)
        self._body_verify()
        self._guarded(self._intent_guard_stage())
        remaining = self._remaining()
        if type(request.timeout_seconds) not in {int, float} or not math.isfinite(request.timeout_seconds) or request.timeout_seconds <= 0:
            self._fail("transport-protocol-failed")
        clipped = replace(request, timeout_seconds=min(float(request.timeout_seconds), remaining))
        self._encoded_verify(clipped)
        self._remaining()
        object.__setattr__(self, "_intent_attempted", True)
        self._journal.persist_send_intent(self._active)
        object.__setattr__(self, "_intent_durable", True)
        self._body_verify()
        self._guarded("send")
        remaining = self._remaining()
        if type(request.timeout_seconds) not in {int, float} or not math.isfinite(request.timeout_seconds) or request.timeout_seconds <= 0:
            self._fail("transport-protocol-failed")
        clipped = replace(request, timeout_seconds=min(float(request.timeout_seconds), remaining))
        self._encoded_verify(clipped)
        self._remaining()
        send = self._delegate.send
        try:
            response = send(clipped)
            if type(response) is not HttpResponse or type(response.body) is not bytes or len(response.body) > self._maximum:
                self._fail("transport-protocol-failed")
            object.__setattr__(self, "_response", response)
            return response
        finally:
            object.__setattr__(self, "_entry_observed", True)
            self._journal.record_http_entry(self._active)
            object.__setattr__(self, "_entry", True)
