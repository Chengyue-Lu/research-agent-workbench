"""Zero-Provider guarded transport observations and durable conservative failures."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_workbench.adapters.models.conformance_body import ConformanceBodyPolicy, prepare_body_admission
from research_workbench.adapters.models.conformance_journal import ConformanceJournalError, ConformanceUsageJournal
from research_workbench.adapters.models.conformance_transport import GuardedConformanceTransport, ConformanceTransportError
from research_workbench.adapters.models.http import HttpRequest, HttpResponse
from tests.test_conformance_body import synthetic_request


class FakeDelegate:
    def __init__(self, failure=None):
        self.max_response_bytes = 65536
        self.requests = []
        self.failure = failure

    def send(self, request):
        self.requests.append(request)
        if self.failure:
            raise RuntimeError("synthetic private exception")
        return HttpResponse(200, {}, b"{}")


class FakeClock:
    def __init__(self):
        self.value = 10.0

    def __call__(self):
        return self.value


class ConformanceTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "budget.sqlite"
        self.journal = ConformanceUsageJournal.create(self.path, namespace="11111111-1111-4111-8111-111111111111", total_token_limit=1000)
        self.addCleanup(self.journal.close)
        self.journal.start_attempt()
        self.delegate = FakeDelegate()
        self.clock = FakeClock()
        self.stages = []

    def guard(self, stage, ordinal):
        self.stages.append((stage, ordinal))
        return True

    def transport(self, guard=None):
        return GuardedConformanceTransport(self.delegate, self.journal, self.guard if guard is None else guard,
                                           deadline=15.0, clock=self.clock)

    def request(self):
        return HttpRequest("POST", "https://synthetic.invalid", {}, b"{}", 60)

    def test_unarmed_duplicate_and_timeout_clip(self):
        transport = self.transport()
        with self.assertRaises(ConformanceTransportError):
            transport.send(self.request())
        handle = self.journal.reserve(input_upper_tokens=20, output_upper_tokens=30)
        transport.arm(handle)
        transport.preinvoke()
        transport.send(self.request())
        self.assertEqual(self.delegate.requests[0].timeout_seconds, 5)
        self.assertEqual(self.stages, [("preinvoke", 1), ("send", 1), ("send", 1)])
        self.assertEqual(self.journal.snapshot()["durable_send_intents"], 1)
        self.assertEqual(self.journal.snapshot()["http_entry_observations"], 1)
        with self.assertRaises(ConformanceTransportError):
            transport.send(self.request())
        self.assertEqual(len(self.delegate.requests), 1)

    def test_send_guard_refusal_has_no_intent_and_can_release(self):
        def guard(stage, ordinal):
            return stage == "preinvoke"
        transport = self.transport(guard)
        handle = self.journal.reserve(input_upper_tokens=20, output_upper_tokens=30)
        transport.arm(handle)
        transport.preinvoke()
        with self.assertRaises(ConformanceTransportError) as caught:
            transport.send(self.request())
        self.assertEqual(caught.exception.code, "guard-refused")
        self.assertFalse(transport.intent_attempted)
        self.journal.reject_before_send(handle)
        self.assertEqual(self.delegate.requests, [])
        self.assertEqual(self.journal.snapshot()["unresolved_reserved_tokens"], 0)

    def test_delayed_intent_crossing_deadline_retains_reservation_without_entry(self):
        transport = self.transport()
        handle = self.journal.reserve(input_upper_tokens=20, output_upper_tokens=30)
        transport.arm(handle)
        transport.preinvoke()
        persist = ConformanceUsageJournal.persist_send_intent
        def delayed_intent(journal, reservation):
            persist(journal, reservation)
            self.clock.value = 15.0
        with patch.object(ConformanceUsageJournal, "persist_send_intent", delayed_intent):
            with self.assertRaises(ConformanceTransportError) as caught:
                transport.send(self.request())
        self.assertEqual(caught.exception.code, "deadline-exhausted")
        self.assertEqual(transport.failure_code, "deadline-exhausted")
        self.assertTrue(transport.intent_attempted)
        self.assertTrue(transport.intent_durable)
        self.assertFalse(transport.entry_recorded)
        self.assertEqual(self.delegate.requests, [])
        snapshot = self.journal.snapshot()
        self.assertEqual(snapshot["durable_send_intents"], 1)
        self.assertEqual(snapshot["http_entry_observations"], 0)
        self.assertEqual(snapshot["unresolved_reserved_tokens"], 50)
        with self.assertRaises(ConformanceJournalError) as release:
            self.journal.reject_before_send(handle)
        self.assertEqual(release.exception.code, "cannot-release-send-intent")
        self.journal.record_uncertain_failure(handle)
        self.assertTrue(self.journal.snapshot()["blocked"])
        self.assertEqual(self.journal.snapshot()["unresolved_reserved_tokens"], 50)

    def test_post_intent_guard_refusal_retains_intent_and_no_entry(self):
        def guard(stage, ordinal):
            self.stages.append((stage, ordinal))
            return not self.journal.snapshot()["durable_send_intents"]
        transport = self.transport(guard)
        handle = self.journal.reserve(input_upper_tokens=20, output_upper_tokens=30)
        transport.arm(handle)
        transport.preinvoke()
        with self.assertRaises(ConformanceTransportError) as caught:
            transport.send(self.request())
        self.assertEqual(caught.exception.code, "guard-refused")
        self.assertEqual(self.stages, [("preinvoke", 1), ("send", 1), ("send", 1)])
        self.assertTrue(transport.intent_durable)
        self.assertFalse(transport.entry_recorded)
        self.assertEqual(self.delegate.requests, [])
        snapshot = self.journal.snapshot()
        self.assertEqual(snapshot["durable_send_intents"], 1)
        self.assertEqual(snapshot["http_entry_observations"], 0)
        self.assertEqual(snapshot["unresolved_reserved_tokens"], 50)
        self.journal.record_uncertain_failure(handle)
        self.assertTrue(self.journal.snapshot()["blocked"])

    def test_delayed_intent_reclips_timeout_to_current_remaining_time(self):
        transport = self.transport()
        handle = self.journal.reserve(input_upper_tokens=20, output_upper_tokens=30)
        transport.arm(handle)
        transport.preinvoke()
        persist = ConformanceUsageJournal.persist_send_intent
        def delayed_intent(journal, reservation):
            persist(journal, reservation)
            self.clock.value = 14.0
        with patch.object(ConformanceUsageJournal, "persist_send_intent", delayed_intent):
            transport.send(self.request())
        self.assertEqual(len(self.delegate.requests), 1)
        self.assertEqual(self.delegate.requests[0].timeout_seconds, 1.0)
        self.assertEqual(self.stages, [("preinvoke", 1), ("send", 1), ("send", 1)])
        self.assertTrue(transport.intent_durable)
        self.assertTrue(transport.entry_recorded)
        self.assertEqual(self.journal.snapshot()["http_entry_observations"], 1)

    def test_post_intent_guard_model_drift_refuses_without_entry(self):
        model = synthetic_request()
        policy = ConformanceBodyPolicy(max_output_tokens=32)
        body = prepare_body_admission(policy, "specific-tool", model).expected_body
        def guard(stage, ordinal):
            if self.journal.snapshot()["durable_send_intents"]:
                model.tools[0].input_schema["properties"]["a"]["enum"][0] = 9
            return True
        transport = GuardedConformanceTransport(self.delegate, self.journal, guard,
            deadline=15, clock=self.clock, body_policy=policy)
        handle = self.journal.reserve(input_upper_tokens=100, output_upper_tokens=32)
        transport.arm(handle, body_phase="specific-tool", model_request=model)
        transport.preinvoke()
        with self.assertRaises(ConformanceTransportError) as caught:
            transport.send(HttpRequest("POST", "https://synthetic.invalid", {}, body))
        self.assertEqual(caught.exception.code, "transport-protocol-failed")
        self.assertTrue(transport.intent_durable)
        self.assertFalse(transport.entry_recorded)
        self.assertEqual(self.delegate.requests, [])
        snapshot = self.journal.snapshot()
        self.assertEqual(snapshot["durable_send_intents"], 1)
        self.assertEqual(snapshot["http_entry_observations"], 0)
        self.assertEqual(snapshot["unresolved_reserved_tokens"], 132)

    def test_post_intent_guard_body_drift_refuses_without_reading_headers(self):
        model = synthetic_request()
        policy = ConformanceBodyPolicy(max_output_tokens=32)
        body = prepare_body_admission(policy, "specific-tool", model).expected_body
        class OpaqueHeaders:
            def __iter__(self):
                raise AssertionError("must not read headers")
        request = HttpRequest("POST", "https://synthetic.invalid", OpaqueHeaders(), body)
        def guard(stage, ordinal):
            if self.journal.snapshot()["durable_send_intents"]:
                object.__setattr__(request, "body", b'{}')
            return True
        transport = GuardedConformanceTransport(self.delegate, self.journal, guard,
            deadline=15, clock=self.clock, body_policy=policy)
        handle = self.journal.reserve(input_upper_tokens=100, output_upper_tokens=32)
        transport.arm(handle, body_phase="specific-tool", model_request=model)
        transport.preinvoke()
        with self.assertRaises(ConformanceTransportError) as caught:
            transport.send(request)
        self.assertEqual(caught.exception.code, "transport-protocol-failed")
        self.assertTrue(transport.intent_durable)
        self.assertFalse(transport.entry_recorded)
        self.assertEqual(self.delegate.requests, [])
        snapshot = self.journal.snapshot()
        self.assertEqual(snapshot["durable_send_intents"], 1)
        self.assertEqual(snapshot["http_entry_observations"], 0)
        self.assertEqual(snapshot["unresolved_reserved_tokens"], 132)

    def test_delegate_method_drift_is_rejected(self):
        transport = self.transport()
        handle = self.journal.reserve(input_upper_tokens=20, output_upper_tokens=30)
        self.delegate.send = lambda request: HttpResponse(200, {}, b"{}")
        with self.assertRaises(ConformanceTransportError):
            transport.arm(handle)
        self.journal.reject_before_send(handle)

    def test_delegate_maximum_drift_is_rejected(self):
        transport = self.transport()
        handle = self.journal.reserve(input_upper_tokens=20, output_upper_tokens=30)
        self.delegate.max_response_bytes = 123
        with self.assertRaises(ConformanceTransportError):
            transport.arm(handle)
        self.journal.reject_before_send(handle)

    def test_delegate_failure_observes_entry_without_claiming_socket(self):
        self.delegate.failure = True
        transport = self.transport()
        handle = self.journal.reserve(input_upper_tokens=20, output_upper_tokens=30)
        transport.arm(handle)
        with self.assertRaises(RuntimeError):
            transport.send(self.request())
        self.assertTrue(transport.entry_recorded)
        self.assertIsNone(transport.received_response)
        self.assertEqual(self.journal.snapshot()["http_entry_observations"], 1)

    def test_entry_storage_failure_retains_received_response_and_intent(self):
        transport = self.transport()
        handle = self.journal.reserve(input_upper_tokens=20, output_upper_tokens=30)
        transport.arm(handle)
        with patch.object(ConformanceUsageJournal, "record_http_entry", side_effect=OSError("synthetic storage error")):
            with self.assertRaises(OSError):
                transport.send(self.request())
        self.assertEqual(transport.received_response.body, b"{}")
        self.assertTrue(transport.intent_durable)
        self.assertTrue(transport.entry_observed)
        self.assertFalse(transport.entry_recorded)
        snapshot = self.journal.snapshot()
        self.assertEqual(snapshot["http_entry_observations"], 0)
        self.assertEqual(snapshot["unresolved_reserved_tokens"], 50)

    def test_deadline_and_frozen_identity_reject_before_delegate(self):
        transport = self.transport()
        with self.assertRaises(AttributeError):
            transport._delegate = FakeDelegate()
        handle = self.journal.reserve(input_upper_tokens=20, output_upper_tokens=30)
        transport.arm(handle)
        self.clock.value = 15
        with self.assertRaises(ConformanceTransportError) as caught:
            transport.preinvoke()
        self.assertEqual(caught.exception.code, "deadline-exhausted")
        self.assertEqual(self.delegate.requests, [])

    def test_backward_clock_and_deadline_drift_are_rejected(self):
        transport = self.transport()
        handle = self.journal.reserve(input_upper_tokens=20, output_upper_tokens=30)
        transport.arm(handle)
        self.clock.value = 9
        with self.assertRaises(ConformanceTransportError):
            transport.preinvoke()
        self.clock.value = 10
        object.__setattr__(transport, "_deadline", 100)
        with self.assertRaises(ConformanceTransportError):
            transport.preinvoke()
        self.assertEqual(self.delegate.requests, [])

    def test_explicit_model_request_guard_mutation_refuses_before_intent(self):
        model = synthetic_request()
        def guard(stage, ordinal):
            model.tools[0].input_schema["properties"]["a"]["enum"][0] = 9
            return True
        bounded = GuardedConformanceTransport(self.delegate, self.journal, guard, deadline=15, clock=self.clock,
                                              body_policy=ConformanceBodyPolicy(max_output_tokens=32))
        handle = self.journal.reserve(input_upper_tokens=100, output_upper_tokens=32)
        bounded.arm(handle, body_phase="specific-tool", model_request=model)
        with self.assertRaises(ConformanceTransportError):
            bounded.preinvoke()
        self.assertFalse(bounded.intent_attempted)
        self.assertEqual(0, self.journal.snapshot()["durable_send_intents"])
        self.assertEqual([], self.delegate.requests)

    def test_actual_body_guard_mutation_refuses_without_reading_headers(self):
        model = synthetic_request()
        policy = ConformanceBodyPolicy(max_output_tokens=32)
        body = prepare_body_admission(policy, "specific-tool", model).expected_body
        class OpaqueHeaders:
            def __iter__(self):
                raise AssertionError("must not read headers")
        request = HttpRequest("POST", "https://synthetic.invalid", OpaqueHeaders(), body)
        def guard(stage, ordinal):
            if stage == "send":
                object.__setattr__(request, "body", b'{}')
            return True
        bounded = GuardedConformanceTransport(self.delegate, self.journal, guard, deadline=15, clock=self.clock, body_policy=policy)
        handle = self.journal.reserve(input_upper_tokens=100, output_upper_tokens=32)
        bounded.arm(handle, body_phase="specific-tool", model_request=model)
        bounded.preinvoke()
        with self.assertRaises(ConformanceTransportError):
            bounded.send(request)
        self.assertFalse(bounded.intent_attempted)
        self.assertEqual(0, self.journal.snapshot()["durable_send_intents"])
        self.assertEqual([], self.delegate.requests)

    def test_policy_removal_by_guard_cannot_downgrade_explicit_admission(self):
        model = synthetic_request()
        def guard(stage, ordinal):
            object.__setattr__(bounded, "_body_policy", None)
            object.__setattr__(bounded, "_body_policy_pin", None)
            return True
        bounded = GuardedConformanceTransport(self.delegate, self.journal, guard, deadline=15, clock=self.clock,
                                              body_policy=ConformanceBodyPolicy(max_output_tokens=32))
        handle = self.journal.reserve(input_upper_tokens=100, output_upper_tokens=32)
        bounded.arm(handle, body_phase="specific-tool", model_request=model)
        with self.assertRaises(ConformanceTransportError):
            bounded.preinvoke()
        self.assertFalse(bounded.intent_attempted)
        self.assertEqual([], self.delegate.requests)

    def test_explicit_body_cannot_exceed_reserved_output_limit(self):
        bounded = GuardedConformanceTransport(self.delegate, self.journal, self.guard, deadline=15, clock=self.clock,
                                              body_policy=ConformanceBodyPolicy(max_output_tokens=32))
        handle = self.journal.reserve(input_upper_tokens=100, output_upper_tokens=16)
        with self.assertRaises(ConformanceTransportError):
            bounded.arm(handle, body_phase="specific-tool", model_request=synthetic_request())
        self.assertFalse(bounded.intent_attempted)


if __name__ == "__main__":
    unittest.main()
