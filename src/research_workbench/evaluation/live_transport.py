"""Explicit Pilot journal facade over shared reserved Provider transport.

No Skill/Pilot authority is generated. Actual independent LiveUseGuard and
official input-bound proof ports must be supplied by the trusted Driver.
"""

from __future__ import annotations

from research_workbench.adapters.models.http import HttpRequest
from research_workbench.adapters.models.request_admission import PreparedProviderRequest
from research_workbench.adapters.models.reserved_transport import (
    ReservedProviderTransport, ReservedTransportError, _callback, transport_fail,
)
from research_workbench.evaluation.live_budget import PilotReservation, PilotUsageJournal


class PilotTransportError(ReservedTransportError):
    pass


class GuardedPilotTransport(ReservedProviderTransport):
    __slots__ = ("_input_upper_verifier", "_admission", "_admission_pin", "_prepared")

    def __init__(self, delegate, journal, guard, *, input_upper_verifier, deadline, clock=None):
        if type(journal) is not PilotUsageJournal or not callable(input_upper_verifier):
            transport_fail(PilotTransportError, "transport-binding-drift")
        for name, value in (("_input_upper_verifier", input_upper_verifier), ("_admission", None),
                            ("_admission_pin", None), ("_prepared", False)):
            object.__setattr__(self, name, value)
        super().__init__(delegate, journal, guard, deadline=deadline, clock=clock)

    def _fail(self, code):
        transport_fail(PilotTransportError, code)

    def _policy_binding(self):
        return _callback(self._input_upper_verifier, self._fail)

    def _reservation_ordinal(self, reservation):
        if type(reservation) is not PilotReservation:
            self._fail("transport-protocol-failed")
        return self._journal._transaction(lambda state: self._journal._owned_call(state, reservation)["ordinal"])

    def _body_verify(self):
        failed = False
        try:
            admission = self._admission
            if type(admission) is not PreparedProviderRequest or self._admission_state(admission) != self._admission_pin:
                self._fail("transport-protocol-failed")
            admission.verify(self._input_upper_verifier)
        except Exception:
            failed = True
        if failed:
            self._fail("transport-protocol-failed")

    @staticmethod
    def _admission_state(admission):
        return (id(admission), id(admission.request), id(admission.config), admission.root,
                id(admission.environment), admission.max_body_bytes, admission.material, admission.bound)

    def _material_verify(self):
        failed = False
        try:
            if type(self._admission) is not PreparedProviderRequest or self._admission_state(self._admission) != self._admission_pin:
                self._fail("transport-protocol-failed")
            self._admission.verify_material()
        except Exception:
            failed = True
        if failed:
            self._fail("transport-protocol-failed")

    def _encoded_verify(self, request):
        self._material_verify()
        material = self._admission.material
        if (type(request) is not HttpRequest or request.method != "POST" or request.url != material.url
                or type(request.body) is not bytes or request.body != material.body
                or request.timeout_seconds > material.timeout_seconds):
            self._fail("transport-protocol-failed")
        # Headers may contain credentials. Never inspect or retain them here.

    def arm(self, reservation, *, admission):
        if self._active is not None or type(admission) is not PreparedProviderRequest:
            self._fail("transport-protocol-failed")
        admission.verify(self._input_upper_verifier)
        if (type(reservation) is not PilotReservation or reservation.input_upper_tokens != admission.bound.input_upper_tokens
                or reservation.output_upper_tokens < admission.material.output_upper_tokens):
            self._fail("transport-protocol-failed")
        self._reservation_ordinal(reservation)
        object.__setattr__(self, "_admission", admission)
        object.__setattr__(self, "_admission_pin", self._admission_state(admission))
        object.__setattr__(self, "_prepared", False)
        self._arm(reservation)

    def preinvoke(self):
        if self._active is None or self._used:
            self._fail("transport-protocol-failed")
        self._body_verify()
        self._guarded("preinvoke")
        self._material_verify()
        self._remaining()

    def prepare_request(self, request):
        """Optional HTTP port called after encoding, before credential resolve."""
        if self._prepared:
            self._fail("transport-protocol-failed")
        self.preinvoke()
        self._encoded_verify(request)
        self._remaining()
        object.__setattr__(self, "_prepared", True)

    def send(self, request):
        if not self._prepared:
            self._fail("transport-protocol-failed")
        return super().send(request)

    def disarm(self):
        super().disarm()
        object.__setattr__(self, "_admission", None)
        object.__setattr__(self, "_admission_pin", None)
        object.__setattr__(self, "_prepared", False)
