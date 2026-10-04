"""Conformance facade over shared once-only reserved HTTP entry mechanics.

Fixed synthetic body assertions and the Conformance journal remain explicit.
The caller owns current authorization/time/source; entry is not wire proof.
"""

from __future__ import annotations

from research_workbench.adapters.models.conformance_body import (
    policy_pin, prepare_body_admission, revalidate_body_admission, validate_encoded_body,
)
from research_workbench.adapters.models.conformance_journal import (
    ConformanceJournalReservation, ConformanceUsageJournal,
)
from research_workbench.adapters.models.reserved_transport import (
    ReservedProviderTransport, ReservedTransportError, transport_fail,
)


class ConformanceTransportError(ReservedTransportError):
    def __init__(self, code: str):
        self.code = code
        RuntimeError.__init__(self, "conformance transport: " + code)


def _fail(code):
    transport_fail(ConformanceTransportError, code)


class GuardedConformanceTransport(ReservedProviderTransport):
    """Retains existing component journal and three-phase body assertions."""

    __slots__ = ("_body_policy", "_body_policy_pin", "_body_admission", "_body_state")

    def __init__(self, delegate, journal, guard, *, deadline, clock=None, body_policy=None):
        if type(journal) is not ConformanceUsageJournal:
            _fail("transport-binding-drift")
        pin = None if body_policy is None else self._body_checked(lambda: policy_pin(body_policy))
        for name, value in (("_body_policy", body_policy), ("_body_policy_pin", pin),
                            ("_body_admission", None), ("_body_state", None)):
            object.__setattr__(self, name, value)
        super().__init__(delegate, journal, guard, deadline=deadline, clock=clock)

    def _fail(self, code):
        _fail(code)

    def _reservation_ordinal(self, reservation):
        if type(reservation) is not ConformanceJournalReservation:
            _fail("transport-protocol-failed")
        self._journal._owned_values(reservation)
        return reservation.reservation_ordinal

    def _policy_binding(self):
        current = None if self._body_policy is None else self._body_checked(lambda: policy_pin(self._body_policy))
        if current != self._body_policy_pin:
            _fail("transport-protocol-failed")
        return (id(self._body_policy), self._body_policy_pin)

    def _intent_guard_stage(self):
        # Keep the old component guard observations. Pilot checks reserved
        # preinvoke before intent, then durable-intent send after persistence.
        return "send"

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

    def _encoded_verify(self, request):
        if self._body_policy_pin is not None:
            self._body_checked(lambda: validate_encoded_body(self._body_policy, self._body_admission, self._body_state, request.body))

    def arm(self, reservation, *, body_phase=None, model_request=None, expected_call_id=None, expected_assistant_text=()):
        if type(reservation) is not ConformanceJournalReservation or self._active is not None:
            _fail("transport-protocol-failed")
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
        self._arm(reservation)

    def disarm(self):
        super().disarm()
        object.__setattr__(self, "_body_admission", None)
        object.__setattr__(self, "_body_state", None)
