"""Synthetic authorities/books/credentials only; no real API/key/Tool usage."""

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from research_workbench.adapters.models.configured import build_profile_provider
from research_workbench.adapters.models.http import HttpRequest
from research_workbench.adapters.models.port import ContentBlock, Message, ModelRequest, ProviderError
from research_workbench.adapters.models.profile_configuration import ProviderAdapterConfigV2
from research_workbench.adapters.models.profile_conformance import _observed_usage
from research_workbench.adapters.models.request_admission import (
    RequestAdmissionError, VerifiedInputUpperBound, prepare_provider_request,
)
from research_workbench.evaluation.live_budget import PilotBudgetError, PilotUsageJournal
from research_workbench.evaluation.live_preflight import VerifiedBudgetCheckpoint
from research_workbench.evaluation.live_transport import GuardedPilotTransport, PilotTransportError
from tests.live_preflight_fixtures import LivePreflightFixture
from tests.test_configured_provider import SyntheticTransport, _response
from tests.test_conformance_transport import FakeClock

ROOT = Path(__file__).resolve().parents[1]


class SyntheticCredential:
    def __init__(self):
        self.resolutions = 0
        self.callback = None

    @property
    def label(self):
        return "env:SYNTHETIC_API_KEY"

    def available(self):
        raise AssertionError("must not probe credential presence")

    def resolve(self):
        self.resolutions += 1
        if self.callback is not None:
            self.callback()
        return "synthetic-offline-key"


class ObservedDelegate(SyntheticTransport):
    def __init__(self, document):
        super().__init__(document)
        self.callback = None

    def send(self, request):
        response = super().send(request)
        if self.callback is not None:
            self.callback()
        return response


class OpaqueHeaders:
    def __iter__(self):
        raise AssertionError("admission must not inspect authentication headers")


class LiveTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temp.cleanup)
        cls.template = LivePreflightFixture(Path(temp.name)).build_live()
        selected = sorted((ROOT / "registry/providers/profiles").glob("deepseek-*.json"))
        assert len(selected) == 1
        cls.profile = json.loads(selected[0].read_text(encoding="utf-8"))

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.f = copy.deepcopy(self.template)
        self.f.root = Path(temp.name)
        shutil.copytree(self.template.root, self.f.root, dirs_exist_ok=True)
        self.context = self.f.context()
        self.prior = VerifiedBudgetCheckpoint(self.context.budget_checkpoint_ref, 1744, 0, 10_000_000, True)
        self.now = "2026-09-11T10:00:00Z"
        self.book = PilotUsageJournal.create(self.f.root / "pilot.sqlite", self.f.root / "pilot.anchor",
            inputs=self.f.live_inputs(), context=self.context, prior_reader=lambda: self.prior,
            clock=lambda: self.now, journal_identity="5a1d31b4-59df-429b-8c59-cc7196d74f73")
        self.addCleanup(self.book.close)
        self.slot = next(s["attempt_id"] for b in self.f.plan["blocks"] if b["phase"] == "pilot"
                         for a in b["arms"] for s in a["attempt_slots"])
        self.book.start_attempt(self.slot)
        raw = json.dumps(self.profile).encode()
        (self.f.root / "selected-profile.json").write_bytes(raw)
        self.config = ProviderAdapterConfigV2.from_mapping({
            "adapter_id": "synthetic-profile", "enabled": True,
            "profile_ref": {"path": "selected-profile.json", "sha256": hashlib.sha256(raw).hexdigest()},
            "model_selector": {"kind": "literal", "value": self.profile["model"]["requested_id"]},
            "credential_source": {"kind": "environment", "name": "SYNTHETIC_API_KEY"},
            "capabilities": list(self.profile["implementation"]["capabilities"]),
            "transport": {"timeout_seconds": 10, "max_response_bytes": 8388608,
                          "redirect_policy": "deny", "retry_policy": "none"}, "conformance_ref": None})
        self.request = ModelRequest(self.profile["model"]["requested_id"],
            (Message("user", (ContentBlock("text", text="Synthetic bounded check."),)),), max_output_tokens=16)
        self.bound, self.bound_callback = 32, None
        self.credential, self.delegate, self.clock = SyntheticCredential(), ObservedDelegate(_response(self.profile)), FakeClock()
        self.stages, self.guard_callback = [], None
        self.verifier = self.input_bound
        self.transport = GuardedPilotTransport(self.delegate, self.book, self.guard,
            input_upper_verifier=self.verifier, deadline=15, clock=self.clock)
        self.provider = build_profile_provider(self.config, root=self.f.root,
            credential=self.credential, transport=self.transport)

    def input_bound(self, material):
        # Deliberately synthetic token proof. No real tokenizer/rule authority.
        if self.bound_callback is not None:
            self.bound_callback()
        return VerifiedInputUpperBound(material.root, self.bound)

    def guard(self, stage, ordinal):
        if stage == "preinvoke":
            value = self.book.observe(attempt_id=self.slot, surface="provider", handle=self.handle)
        else:
            value = self.book.observe_before_entry(attempt_id=self.slot, handle=self.handle)
        self.stages.append((stage, ordinal, value.send_intent_durable))
        if self.guard_callback is not None:
            return self.guard_callback(stage)
        return True

    def arm(self):
        self.admission = prepare_provider_request(self.config, root=self.f.root, request=self.request,
            input_upper_verifier=self.verifier, max_body_bytes=4096)
        self.handle = self.book.reserve(input_upper_tokens=32, output_upper_tokens=16)
        self.transport.arm(self.handle, admission=self.admission)

    def encoded(self, **changes):
        value = self.admission.material
        request = HttpRequest("POST", value.url, OpaqueHeaders(), value.body, value.timeout_seconds)
        return replace(request, **changes)

    def test_existing_configured_provider_uses_precredential_port_and_same_book_handle(self):
        self.arm()
        response = self.provider.generate(self.request)
        self.book.settle(self.handle, usage=response.usage, successful=True, response_received=True)
        self.assertEqual([("preinvoke", 1, False), ("preinvoke", 1, False), ("send", 1, True)], self.stages)
        self.assertEqual(1, self.credential.resolutions)
        self.assertEqual(1, len(self.delegate.requests))
        self.assertEqual(5.0, self.delegate.requests[0].timeout_seconds)
        self.assertEqual(1746, self.book.snapshot()["known_total_tokens"])
        self.assertEqual(0, self.book.snapshot()["held_total_tokens"])
        with self.assertRaises(PilotTransportError):
            self.transport.send(self.encoded())
        self.assertEqual(1, len(self.delegate.requests))

    def test_missing_admission_and_send_without_precredential_check_are_rejected(self):
        with self.assertRaises(ProviderError):
            self.provider.generate(self.request)
        self.assertEqual(0, self.credential.resolutions)
        self.arm()
        with self.assertRaises(PilotTransportError):
            self.transport.send(self.encoded())
        self.assertFalse(self.transport.intent_attempted)
        self.assertEqual([], self.delegate.requests)

    def test_guard_mutates_ignored_metadata_is_rejected_before_credential(self):
        self.arm()
        def mutate(_):
            self.request.metadata["synthetic"] = "changed"
            return True
        self.guard_callback = mutate
        with self.assertRaises(ProviderError) as caught:
            self.provider.generate(self.request)
        self.assertEqual("provider request admission failed", str(caught.exception))
        self.assertIsNone(caught.exception.__context__)
        self.assertEqual(0, self.credential.resolutions)
        self.assertFalse(self.transport.intent_attempted)

    def test_actual_encoded_body_mismatch_is_rejected_without_reading_headers(self):
        self.arm()
        with self.assertRaises(PilotTransportError):
            self.transport.prepare_request(self.encoded(body=b"{}"))
        self.assertFalse(self.transport.intent_attempted)
        self.assertEqual([], self.delegate.requests)

    def test_destination_change_is_rejected_without_reading_headers(self):
        self.arm()
        with self.assertRaises(PilotTransportError):
            self.transport.prepare_request(self.encoded(url="https://synthetic.invalid/other"))
        self.assertFalse(self.transport.intent_attempted)
        self.assertEqual([], self.delegate.requests)

    def test_foreign_handle_and_wrong_material_bound_are_rejected(self):
        self.arm()
        self.transport.disarm()
        with self.assertRaises(PilotBudgetError):
            self.transport.arm(copy.copy(self.handle), admission=self.admission)
        with self.assertRaises(RequestAdmissionError):
            prepare_provider_request(self.config, root=self.f.root, request=self.request, max_body_bytes=4096,
                input_upper_verifier=lambda _: VerifiedInputUpperBound("0" * 64, 32))
        self.assertEqual(0, self.credential.resolutions)

    def test_proof_drift_during_synthetic_credential_resolution_has_no_intent(self):
        self.arm()
        self.credential.callback = lambda: setattr(self, "bound", 31)
        with self.assertRaises(ProviderError):
            self.provider.generate(self.request)
        self.assertEqual(1, self.credential.resolutions)
        self.assertFalse(self.transport.intent_attempted)
        self.assertEqual([], self.delegate.requests)
        self.book.reject_before_send(self.handle)
        self.assertEqual(0, self.book.snapshot()["held_total_tokens"])

    def test_slow_bound_verifier_after_intent_cannot_enter_delegate(self):
        self.arm()
        def delayed():
            if self.book.snapshot()["calls"][0]["status"] == "intent":
                self.clock.value = 15
        self.bound_callback = delayed
        with self.assertRaises(ProviderError):
            self.provider.generate(self.request)
        self.assertTrue(self.transport.intent_durable)
        self.assertFalse(self.transport.entry_observed)
        self.assertEqual([], self.delegate.requests)
        self.assertEqual(48, self.book.snapshot()["held_total_tokens"])
        with self.assertRaises(PilotBudgetError):
            self.book.reject_before_send(self.handle)

    def test_slow_bound_verifier_before_credential_exhausts_deadline(self):
        self.arm()
        self.bound_callback = lambda: setattr(self.clock, "value", 15)
        with self.assertRaises(ProviderError):
            self.provider.generate(self.request)
        self.assertEqual(0, self.credential.resolutions)
        self.assertFalse(self.transport.intent_attempted)
        self.assertEqual([], self.delegate.requests)

    def test_post_intent_callback_changes_body_retains_hold_without_entry(self):
        self.arm()
        encoded = self.encoded()
        self.transport.prepare_request(encoded)
        def mutate(stage):
            if stage == "send":
                object.__setattr__(encoded, "body", b"{}")
            return True
        self.guard_callback = mutate
        with self.assertRaises(PilotTransportError):
            self.transport.send(encoded)
        self.assertTrue(self.transport.intent_durable)
        self.assertFalse(self.transport.entry_observed)
        self.assertEqual([], self.delegate.requests)
        self.assertEqual(48, self.book.snapshot()["held_total_tokens"])

    def test_post_intent_guard_refusal_preserves_hold(self):
        self.arm()
        self.guard_callback = lambda stage: stage == "preinvoke"
        with self.assertRaises(ProviderError):
            self.provider.generate(self.request)
        self.assertTrue(self.transport.intent_durable)
        self.assertFalse(self.transport.entry_observed)
        self.assertEqual(48, self.book.snapshot()["held_total_tokens"])

    def test_late_return_preserves_entry_and_decoded_usage_then_stops(self):
        self.arm()
        self.delegate.callback = lambda: setattr(self, "now", "2026-09-11T10:02:00Z")
        response = self.provider.generate(self.request)
        self.book.settle(self.handle, usage=response.usage, successful=False, response_received=True)
        self.assertTrue(self.transport.entry_recorded)
        state = self.book.snapshot()
        self.assertTrue(state["stopped"])
        self.assertEqual(1746, state["known_total_tokens"])
        self.assertEqual(0, state["held_total_tokens"])

    def test_prior_drift_during_call_preserves_entry_and_usage(self):
        self.arm()
        self.delegate.callback = lambda: setattr(self, "prior", replace(self.prior, usage_complete=False))
        response = self.provider.generate(self.request)
        self.book.settle(self.handle, usage=response.usage, successful=False, response_received=True)
        self.assertTrue(self.transport.entry_recorded)
        self.assertEqual(1746, self.book.snapshot()["known_total_tokens"])
        self.assertEqual(0, self.book.snapshot()["held_total_tokens"])

    def test_entry_capture_failure_keeps_private_response_and_numeric_observation(self):
        self.arm()
        with patch.object(PilotUsageJournal, "record_http_entry", side_effect=OSError("synthetic capture failure")):
            with self.assertRaises(ProviderError):
                self.provider.generate(self.request)
        self.assertTrue(self.transport.entry_observed)
        self.assertFalse(self.transport.entry_recorded)
        usage = _observed_usage(self.transport.received_response, self.provider.profile)
        self.assertEqual(2, usage.total_tokens)
        self.assertEqual(48, self.book.snapshot()["held_total_tokens"])
        self.assertNotIn("synthetic capture", str(self.transport.failure_code))

    def test_http_failure_preserves_numeric_usage_for_failed_settlement(self):
        self.arm()
        self.delegate.status = 500
        with self.assertRaises(ProviderError):
            self.provider.generate(self.request)
        usage = _observed_usage(self.transport.received_response, self.provider.profile)
        self.book.settle(self.handle, usage=usage, successful=False, response_received=True)
        self.assertTrue(self.transport.entry_recorded)
        self.assertEqual(1746, self.book.snapshot()["known_total_tokens"])
        self.assertEqual(0, self.book.snapshot()["held_total_tokens"])
        self.assertTrue(self.book.snapshot()["stopped"])

    def test_partial_received_usage_keeps_hold_and_does_not_become_zero(self):
        self.arm()
        self.delegate.status = 500
        self.delegate.document["usage"] = {"input_tokens": 1}
        with self.assertRaises(ProviderError):
            self.provider.generate(self.request)
        usage = _observed_usage(self.transport.received_response, self.provider.profile)
        self.book.settle(self.handle, usage=usage, successful=False, response_received=True)
        state = self.book.snapshot()
        self.assertEqual(1745, state["known_total_tokens"])
        self.assertEqual(48, state["held_total_tokens"])
        self.assertFalse(state["usage_complete"])

    def test_precredential_failure_clears_callers_active_exception_context(self):
        self.arm()
        self.guard_callback = lambda _: False
        try:
            raise RuntimeError("synthetic private caller exception")
        except RuntimeError:
            with self.assertRaises(ProviderError) as caught:
                self.provider.generate(self.request)
        self.assertIsNone(caught.exception.__context__)
        self.assertIsNone(caught.exception.__cause__)
        self.assertTrue(caught.exception.__suppress_context__)
        self.assertEqual(0, self.credential.resolutions)

    def test_model_mutation_by_input_verifier_is_rejected_before_reservation(self):
        def mutate():
            self.request.metadata["changed"] = "synthetic"
        self.bound_callback = mutate
        with self.assertRaises(RequestAdmissionError):
            prepare_provider_request(self.config, root=self.f.root, request=self.request,
                input_upper_verifier=self.verifier, max_body_bytes=4096)
        self.assertEqual([], self.book.snapshot()["calls"])
        self.assertEqual(0, self.credential.resolutions)

    def test_guard_replaces_equal_admission_object_is_rejected_before_credential(self):
        self.arm()
        def replace_admission(_):
            object.__setattr__(self.transport, "_admission", replace(self.admission))
            return True
        self.guard_callback = replace_admission
        with self.assertRaises(ProviderError):
            self.provider.generate(self.request)
        self.assertEqual(0, self.credential.resolutions)
        self.assertFalse(self.transport.intent_attempted)


if __name__ == "__main__":
    unittest.main()
