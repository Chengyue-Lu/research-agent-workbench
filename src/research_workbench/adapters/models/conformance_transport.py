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
    """

    __slots__ = ("_delegate", "_journal", "_guard", "_clock", "_deadline", "_binding",
                 "_active", "_used", "_intent_attempted", "_intent_durable", "_entry",
                 "_response", "_maximum", "_last_time", "_failure_code")

    def __init__(self, delegate, journal, guard, *, deadline: float, clock=None):
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
        binding = (delegate, type(delegate), journal, guard, actual_clock, bound,
                   json.dumps(source, sort_keys=True), _callback(guard), _callback(actual_clock), float(deadline), maximum)
        observed_time = actual_clock()
        if type(observed_time) not in {int, float} or not math.isfinite(observed_time) or observed_time >= deadline:
            _fail("deadline-exhausted")
        for name, value in (("_delegate", delegate), ("_journal", journal), ("_guard", guard),
                            ("_clock", actual_clock), ("_deadline", float(deadline)),
                            ("_maximum", maximum), ("_binding", binding), ("_active", None),
                            ("_used", False), ("_intent_attempted", False),
                            ("_intent_durable", False), ("_entry", False), ("_response", None),
                            ("_last_time", observed_time), ("_failure_code", None)):
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
    def received_response(self):
        # Private runtime observation, never included in a report or summary.
        return self._response

    @property
    def failure_code(self):
        return self._failure_code

    def _verify(self):
        delegate, cls, journal, guard, clock, methods, source, guard_pin, clock_pin, deadline, maximum = self._binding
        if (self._delegate is not delegate or type(self._delegate) is not cls
                or self._journal is not journal or self._guard is not guard or self._clock is not clock
                or self._deadline != deadline or self._maximum != maximum
                or getattr(delegate, "max_response_bytes", None) != self._maximum
                or _callback(guard) != guard_pin or _callback(clock) != clock_pin):
            _fail("transport-binding-drift")
        if any(_method(delegate, name) is not function for name, function in methods):
            _fail("transport-binding-drift")
        _, _, current = _source_state(cls.__module__)
        if json.dumps(current, sort_keys=True) != source:
            _fail("transport-binding-drift")

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

    def arm(self, reservation):
        if type(reservation) is not ConformanceJournalReservation or self._active is not None:
            _fail("transport-protocol-failed")
        for name, value in (("_used", False), ("_intent_attempted", False),
                            ("_intent_durable", False), ("_entry", False), ("_response", None), ("_failure_code", None)):
            object.__setattr__(self, name, value)
        self._verify()
        self._journal._owned_values(reservation)
        object.__setattr__(self, "_active", reservation)

    def preinvoke(self):
        if self._active is None or self._used:
            _fail("transport-protocol-failed")
        self._guarded("preinvoke")

    def disarm(self):
        object.__setattr__(self, "_active", None)

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
        object.__setattr__(self, "_intent_attempted", True)
        self._journal.persist_send_intent(self._active)
        object.__setattr__(self, "_intent_durable", True)
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
            self._journal.record_http_entry(self._active)
            object.__setattr__(self, "_entry", True)
