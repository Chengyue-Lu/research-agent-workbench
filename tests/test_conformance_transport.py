"""Zero-Provider guarded transport observations and durable conservative failures."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_workbench.adapters.models.conformance_journal import ConformanceUsageJournal
from research_workbench.adapters.models.conformance_transport import GuardedConformanceTransport, ConformanceTransportError
from research_workbench.adapters.models.http import HttpRequest, HttpResponse


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
        self.assertEqual(self.stages, [("preinvoke", 1), ("send", 1)])
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


if __name__ == "__main__":
    unittest.main()
