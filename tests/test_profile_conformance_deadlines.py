"""Shared deadline regressions with fake responses and a controlled clock."""

import unittest
from unittest.mock import patch

from research_workbench.adapters.models import profile_conformance as driver
from research_workbench.adapters.models.conformance_transport import GuardedConformanceTransport
from research_workbench.adapters.models.http import HttpRequest
from research_workbench.adapters.models.port import Usage
from tests import test_profile_conformance as fixtures


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


class LateSequence(fixtures.NativeSequence):
    def __init__(self, model, clock, phase):
        super().__init__(model)
        self.clock = clock
        self.late_phase = phase

    def send(self, request):
        response = super().send(request)
        if len(self.requests) == self.late_phase:
            self.clock.value = 121.0
        return response


class ProfileConformanceDeadlineTests(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.ProfileConformanceTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.clock = Clock()

    def test_extended_plan_is_explicit_and_finite_default_unchanged(self):
        default = driver.profile_conformance_plan(self.case.config, root=self.case.helper.root)
        extended = driver.profile_conformance_plan(self.case.config, root=self.case.helper.root, max_seconds=360)
        self.assertEqual((default['plan_version'], default['max_seconds']), ('1.0.0', 120.0))
        self.assertEqual((extended['plan_version'], extended['max_seconds']), ('1.1.0', 360.0))
        self.assertFalse(extended['live_qualified'])
        for seconds in (361, 0, -1, True, float('nan'), float('inf')):
            with self.subTest(seconds=seconds), self.assertRaises(driver.ProfileConformanceError):
                driver.profile_conformance_plan(self.case.config, root=self.case.helper.root, max_seconds=seconds)
        self.assertEqual(0, self.case.helper.credential.resolutions)
        self.assertEqual([], self.case.journal.snapshot()['attempts'])

    def test_longer_execution_requires_selected_grant_before_credential_or_attempt(self):
        with self.assertRaises(driver.ProfileConformanceError) as caught:
            self.case.run_driver(max_seconds=360, clock=self.clock)
        self.assertEqual(caught.exception.code, 'attempt-admission-refused')
        self.assertEqual(0, self.case.helper.credential.resolutions)
        self.assertEqual([], self.case.transport.requests)
        self.assertEqual([], self.case.journal.snapshot()['attempts'])

    def test_provider_preparation_consumes_session_allowance(self):
        original_factory = driver.build_profile_provider
        original_run = driver.IsolatedApiSessionRunner.run
        seen = []

        def costly_factory(*args, **kwargs):
            result = original_factory(*args, **kwargs)
            self.clock.value = 80.0
            return result

        def observe_session(instance, *args, **kwargs):
            seen.append(kwargs['limits'].max_seconds)
            return original_run(instance, *args, **kwargs)

        with patch.object(driver, 'build_profile_provider', costly_factory), patch.object(
            driver.IsolatedApiSessionRunner, 'run', observe_session
        ):
            report = self.case.run_driver(clock=self.clock)
        self.assertEqual([40.0], seen)
        self.assertEqual('completed', report['stop_code'])
        self.assertEqual(3, len(self.case.transport.requests))
        self.assertEqual(21, report['accounting']['known_total_tokens'])

    def test_guard_exhaustion_releases_before_send_without_tool(self):
        def guard(stage, ordinal):
            if stage == 'preinvoke':
                self.clock.value = 120.0
            return True

        report = self.case.run_driver(clock=self.clock, guard=guard)
        self.assertEqual('deadline-exhausted', report['stop_code'])
        self.assertEqual([], self.case.transport.requests)
        self.assertEqual(0, report['actual_counts']['tool_executions'])
        self.assertEqual(0, report['accounting']['unresolved_reserved_tokens'])

    def test_socket_timeout_is_clipped_again_after_durable_intent(self):
        self.case.journal.start_attempt()
        reservation = self.case.journal.reserve(input_upper_tokens=100, output_upper_tokens=32)
        guards = []

        def guard(stage, ordinal):
            guards.append(stage)
            self.clock.value = 300.0 if guards.count('send') == 2 else 100.0
            return True

        bounded = GuardedConformanceTransport(self.case.transport, self.case.journal,
            guard, deadline=360.0, clock=self.clock)
        bounded.arm(reservation)
        bounded.preinvoke()
        bounded.send(HttpRequest('POST', 'https://synthetic.invalid/responses', {}, b'{}', 180.0))
        self.assertEqual(['preinvoke', 'send', 'send'], guards)
        self.assertEqual(60.0, self.case.transport.requests[0].timeout_seconds)
        self.case.journal.settle(reservation, usage=Usage(5, 2), successful=True, response_received=True)
        self.case.journal.finish_attempt()
        self.assertEqual(7, self.case.journal.snapshot()['known_total_tokens'])
        self.assertEqual(1, len(self.case.transport.requests))

    def test_late_schema_response_is_settled_without_timely_completion_claim(self):
        self.case.transport = LateSequence(self.case.transport.model, self.clock, 3)
        report = self.case.run_driver(clock=self.clock)
        self.assertEqual('deadline-exhausted', report['stop_code'])
        self.assertEqual('failed', report['status'])
        self.assertTrue(report['assertions']['schema_exact'])
        self.assertEqual(3, report['actual_counts']['responses_received'])
        self.assertEqual(21, report['accounting']['known_total_tokens'])
        self.assertEqual(0, report['accounting']['unresolved_reserved_tokens'])
        self.assertEqual('failed', report['accounting']['attempts'][-1]['status'])
        self.assertEqual(3, len(self.case.transport.requests))

    def test_completed_first_response_survives_wall_pause_without_tool(self):
        self.case.transport = LateSequence(self.case.transport.model, self.clock, 1)
        report = self.case.run_driver(clock=self.clock)
        self.assertNotEqual('completed', report['stop_code'])
        self.assertEqual(1, report['actual_counts']['responses_received'])
        self.assertEqual(0, report['actual_counts']['tool_executions'])
        self.assertEqual(7, report['accounting']['known_total_tokens'])
        self.assertEqual(0, report['accounting']['unresolved_reserved_tokens'])
        self.assertEqual(1, len(self.case.transport.requests))
