"""Real temporary retained archives; synthetic calls/authority only."""
import copy
import hashlib
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from research_workbench.adapters.models.conformance_budget_anchor import ConformanceBudgetAnchor
from research_workbench.adapters.models.conformance_journal import ConformanceUsageJournal
from research_workbench.adapters.models.conformance_ledger import ConformanceUsageLimits
from research_workbench.adapters.models.port import Usage
from research_workbench.evaluation.live_budget import PilotUsageJournal
from research_workbench.evaluation.live_budget_history import RetainedBudgetHistory, RetainedPilotBudget
from research_workbench.evaluation.live_preflight import (
    VerifiedBudgetCheckpoint, compile_live_preflight, validate_live_preflight, validator_identity,
)
from research_workbench.evaluation.live_verification import LiveEvidenceVerifiers, RetainedConformanceBudget
from research_workbench.evaluation.pins import EvaluationValidationError, timestamp
from tests import live_preflight_fixtures as fixtures
from tests import baseline_fixtures, harness_fixtures, system_evaluation_fixtures

NOW = '2026-09-11T10:00:00Z'
IDENTITY = '5a1d31b4-59df-429b-8c59-cc7196d74f73'
SECOND = 'd049d069-61ce-47c8-a9db-d53ac01755a9'


class NextRunFixture(fixtures.LivePreflightFixture):
    """Only this test's independently frozen prefix/run id, no shared fixture edits."""
    def __init__(self, root, prior, run_id, frozen_at=fixtures.AT):
        super().__init__(root)
        self.selected_prior, self.selected_run_id = prior, run_id
        self.selected_freeze = frozen_at

    def write(self, path, value):
        if path == 'live/checkpoint.json':
            value = copy.deepcopy(self.selected_prior)
        elif path == 'live/scope.json':
            value['budget']['prior_tokens'] = self.selected_prior['known_total_tokens']
            if timestamp(self.selected_freeze) > timestamp(value['window']['not_before']):
                value['window']['not_before'] = self.selected_freeze
        return super().write(path, value)

    def context(self):
        return replace(super().context(), run_id=self.selected_run_id,
                       case_selection_frozen_at=self.selected_freeze)

    def verify_fixture_scope(self, argument):
        return argument['context'] == self.trusted_context and argument['checked_at'] == self.selected_freeze

    def build_selected(self):
        original = fixtures.compile_harness_plan
        def selected(*args, **options):
            return original(*args, **{**options, 'run_id': self.selected_run_id})
        # Produce the fixture's entire upstream View/overlay qualification at
        # the new freeze time; retain their normal validators and byte closure.
        with ExitStack() as patches:
            patches.enter_context(patch.object(fixtures, 'compile_harness_plan', selected))
            for module in (fixtures, baseline_fixtures, harness_fixtures, system_evaluation_fixtures):
                patches.enter_context(patch.object(module, 'AT', self.selected_freeze))
            return self.build_live()


class LiveBudgetHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.template = fixtures.LivePreflightFixture(Path(temporary.name)).build_live()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.f = copy.deepcopy(self.template)
        self.f.root = self.root / 'first'
        shutil.copytree(self.template.root, self.f.root)
        database, anchor = self.root / 'm6.sqlite', self.root / 'm6.anchor'
        with ConformanceUsageJournal.create(database, anchor_path=anchor, **fixtures.JOURNAL_POLICY) as old:
            old.start_attempt()
            call = old.reserve(input_upper_tokens=1700, output_upper_tokens=44)
            old.persist_send_intent(call)
            old.record_http_entry(call)
            old.settle(call, usage=Usage(1700, 44), successful=True, response_received=True)
            old.fail_attempt()
        limits = ConformanceUsageLimits(fixtures.TOKEN_CEILING)
        selected = ConformanceBudgetAnchor.open(anchor, database_path=database,
            namespace=fixtures.JOURNAL_POLICY['namespace'], limits={
                'total_token_limit': fixtures.TOKEN_CEILING, 'max_attempts': 3,
                'max_invocations_per_attempt': 3, 'max_output_tokens_per_invocation': 256})
        self.base = RetainedConformanceBudget(database, anchor, fixtures.JOURNAL_POLICY['namespace'],
                                             selected.identity, limits)
        self.now = NOW
        self.book, self.retained = self.new_book(self.f, IDENTITY, self.base.snapshot())
        self.history = RetainedBudgetHistory(self.base, (self.retained,))

    def new_book(self, fixture, identity, prior):
        context, inputs = fixture.context(), fixture.live_inputs()
        checkpoint = VerifiedBudgetCheckpoint(context.budget_checkpoint_ref, prior['known_total_tokens'],
                                             0, fixtures.TOKEN_CEILING, True)
        database, anchor = fixture.root / 'pilot.sqlite', fixture.root / 'pilot.anchor'
        book = PilotUsageJournal.create(database, anchor, inputs=inputs, context=context,
            prior_reader=lambda: checkpoint, clock=lambda: self.now, journal_identity=identity)
        self.addCleanup(book.close)
        return book, RetainedPilotBudget(database, anchor, identity, fixture.live_inputs(), context)

    def finish_failed(self, book=None, usage=Usage(5, 2), *, sent=True):
        book = book or self.book
        slot = book.snapshot()['attempts'][0]['attempt_id']
        book.start_attempt(slot)
        handle = book.reserve(input_upper_tokens=32, output_upper_tokens=16)
        if sent:
            book.persist_send_intent(handle)
            book.record_http_entry(handle)
            book.settle(handle, usage=usage, successful=False, response_received=True)
        else:
            book.reject_before_send(handle)
        book.fail_attempt(slot)

    def freeze(self, value):
        reference = self.f.write('live/selected-prefix.json', value)
        return self.f.live_inputs(), replace(self.f.context(), budget_checkpoint_ref=reference)

    def test_failed_known_usage_and_all_not_started_slots_are_retained_and_not_double_counted(self):
        self.finish_failed()
        value = self.history.snapshot()
        self.assertEqual(1751, value['known_total_tokens'])
        self.assertEqual({'input_tokens': 5, 'output_tokens': 2}, value['runs'][0]['delta'])
        self.assertEqual(1744, value['base']['snapshot']['known_total_tokens'])
        slots = value['runs'][0]['snapshot']['attempts']
        self.assertEqual('failed', slots[0]['status'])
        self.assertTrue(all(a['status'] == 'not-started' for a in slots[1:]))
        inputs, context = self.freeze(value)
        self.assertEqual(1751, self.history.checkpoint(inputs, context).known_total_tokens)

    def test_successful_all_slots_prefix_is_closed(self):
        slots = [a['attempt_id'] for a in self.book.snapshot()['attempts']]
        for slot in slots:
            self.book.start_attempt(slot)
            handle = self.book.reserve(input_upper_tokens=32, output_upper_tokens=16)
            self.book.persist_send_intent(handle)
            self.book.record_http_entry(handle)
            self.book.settle(handle, usage=Usage(5, 2), successful=True, response_received=True)
            self.book.finish_attempt(slot)
        value = self.history.snapshot()
        self.assertTrue(value['closed'])
        self.assertEqual(1744 + 7 * len(slots), value['known_total_tokens'])
        self.assertFalse(value['runs'][0]['snapshot']['stopped'])

    def test_partial_known_response_survives_but_hold_denies_future_checkpoint(self):
        self.finish_failed(usage=Usage(5, None))
        value = self.history.snapshot()
        self.assertEqual(1749, value['known_total_tokens'])
        self.assertEqual(48, value['held_total_tokens'])
        self.assertFalse(value['usage_complete'])
        self.assertTrue(value['runs'][0]['snapshot']['recovery_required'])
        with self.assertRaises(EvaluationValidationError):
            self.history.checkpoint(*self.freeze(value))

    def test_open_crashed_or_unstarted_run_cannot_freeze_an_incomplete_prefix(self):
        for stage in ('not-started', 'open', 'intent'):
            if stage == 'open':
                self.book.start_attempt(self.book.snapshot()['attempts'][0]['attempt_id'])
            elif stage == 'intent':
                handle = self.book.reserve(input_upper_tokens=32, output_upper_tokens=16)
                self.book.persist_send_intent(handle)
            value = self.history.snapshot()
            self.assertFalse(value['closed'])
            with self.assertRaises(EvaluationValidationError):
                self.history.checkpoint(*self.freeze(value))

    def test_released_before_send_closed_failure_has_no_fabricated_usage(self):
        self.finish_failed(sent=False)
        value = self.history.snapshot()
        self.assertEqual(1744, value['known_total_tokens'])
        self.assertEqual(0, value['held_total_tokens'])
        self.assertEqual('released-before-send', value['runs'][0]['snapshot']['calls'][0]['status'])
        self.assertEqual(1744, self.history.checkpoint(*self.freeze(value)).known_total_tokens)

    def test_read_only_snapshot_never_opens_an_executable_journal_or_calls_a_clock(self):
        self.finish_failed()
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.retained.database, self.retained.anchor)]
        with patch.object(PilotUsageJournal, 'open', side_effect=AssertionError('executable open forbidden')):
            value = self.history.snapshot()
        after = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.retained.database, self.retained.anchor)]
        self.assertEqual(before, after)
        self.assertEqual(1751, value['known_total_tokens'])

    def test_duplicate_uuid_run_and_paths_are_not_counted_twice(self):
        self.finish_failed()
        with self.assertRaises(EvaluationValidationError):
            RetainedBudgetHistory(self.base, (self.retained, self.retained)).snapshot()
        for changed in (replace(self.retained, journal_identity=self.base.journal_identity),
                        replace(self.retained, database=self.base.database),
                        replace(self.retained, anchor=self.base.anchor)):
            with self.assertRaises(EvaluationValidationError):
                RetainedBudgetHistory(self.base, (changed,)).snapshot()

    def test_exact_prior_reference_and_original_source_must_still_replay(self):
        self.finish_failed()
        wrong = self.f.write('live/wrong-prior.json', {'known_total_tokens': 1744})
        changed = replace(self.retained, context=replace(self.retained.context, budget_checkpoint_ref=wrong))
        with self.assertRaises(EvaluationValidationError):
            RetainedBudgetHistory(self.base, (changed,)).snapshot()
        (self.f.root / self.retained.context.provider_config_ref['path']).write_bytes(b'synthetic drift')
        with self.assertRaises(EvaluationValidationError):
            self.history.snapshot()
        self.assertEqual(1751, self.book.snapshot()['known_total_tokens'])

    def test_anchor_identity_missing_path_and_changed_checkpoint_are_not_repaired(self):
        self.finish_failed()
        value = self.history.snapshot()
        altered = copy.deepcopy(value)
        altered['known_total_tokens'] = 1744
        with self.assertRaises(EvaluationValidationError):
            self.history.checkpoint(*self.freeze(altered))
        wrong = replace(self.retained, journal_identity=SECOND)
        with self.assertRaises(EvaluationValidationError):
            RetainedBudgetHistory(self.base, (wrong,)).snapshot()
        absent = self.root / 'absent.sqlite'
        with self.assertRaises(EvaluationValidationError):
            RetainedBudgetHistory(self.base, (replace(self.retained, database=absent),)).snapshot()
        self.assertFalse(absent.exists())
        saved = self.retained.anchor.read_bytes()
        self.retained.anchor.write_bytes(saved[:-1])
        with self.assertRaises(EvaluationValidationError):
            self.history.snapshot()
        self.assertEqual(saved[:-1], self.retained.anchor.read_bytes())

    def test_second_separately_frozen_run_inherits_prefix_and_only_adds_its_delta(self):
        self.finish_failed()
        first = self.history.snapshot()
        self.now = '2026-09-11T10:01:00Z'
        second = NextRunFixture(self.root / 'second', first, 'FIXTURE-LIVE-RUN-2',
                                '2026-09-11T10:00:30Z').build_selected()
        book, retained = self.new_book(second, SECOND, first)
        self.finish_failed(book=book, usage=Usage(3, 1))
        history = RetainedBudgetHistory(self.base, (self.retained, retained))
        value = history.snapshot()
        self.assertEqual(1755, value['known_total_tokens'])
        self.assertEqual([7, 4], [sum(r['delta'].values()) for r in value['runs']])
        self.assertEqual(1755, history.checkpoint(*self.freeze(value)).known_total_tokens)
        for selections in ((retained, self.retained), (retained,),
                           (self.retained, replace(retained, context=replace(retained.context,
                               run_id=self.retained.context.run_id)))):
            with self.assertRaises(EvaluationValidationError):
                RetainedBudgetHistory(self.base, selections).snapshot()

    def test_factory_uses_selected_cumulative_prefix_without_changing_m6_report_history(self):
        self.finish_failed()
        value = self.history.snapshot()
        self.f.scope['budget_checkpoint_ref'] = self.f.write('live/selected-prefix.json', value)
        # This test exercises the concrete port after its normal argument check.
        factory = LiveEvidenceVerifiers(self.f.live_inputs(), context=self.f.context(), admission_evidence={},
            need_ref=self.f.scope['provider_config_ref'], admission_closure_ref=self.f.scope['provider_config_ref'],
            pilot_owner='fixture-pilot-owner', executor_id='fixture-executor',
            applicability_decision_ref=self.f.scope['provider_config_ref'], provider_owner='fixture-provider-owner',
            binding_ref=self.f.scope['provider_config_ref'], provider=None, retained_budget=self.base,
            human_verifier=lambda _: False, runtime_observer=lambda _: None, cumulative_history=self.history)
        argument = {'context': self.f.context().value(), 'checked_at': fixtures.AT, 'scope': self.f.scope,
                    'protocol': self.f.protocol, 'plan': self.f.plan}
        # Restore the factory's input view to the original pinned scope argument;
        # budget checkpoint is an independent FrozenLiveContext pin in this unit.
        argument['scope'] = self.f.doc(self.f.context().scope_ref['path'])
        self.assertEqual(1751, factory.budget_checkpoint(argument).known_total_tokens)
        self.assertEqual(1744, factory.budget.snapshot()['known_total_tokens'])
        self.assertIn('research_workbench/evaluation/live_budget_history.py',
                      validator_identity(self.f.live_inputs())['sources'])
        with self.assertRaises(EvaluationValidationError):
            LiveEvidenceVerifiers(self.f.live_inputs(), context=self.f.context(), admission_evidence={},
                need_ref=self.f.scope['provider_config_ref'], admission_closure_ref=self.f.scope['provider_config_ref'],
                pilot_owner='fixture-pilot-owner', executor_id='fixture-executor',
                applicability_decision_ref=self.f.scope['provider_config_ref'], provider_owner='fixture-provider-owner',
                binding_ref=self.f.scope['provider_config_ref'], provider=None, retained_budget=self.base,
                human_verifier=lambda _: False, runtime_observer=lambda _: None,
                cumulative_history=RetainedBudgetHistory(replace(self.base, journal_identity=SECOND)))

    def test_fresh_frozen_plan_compiles_and_cold_replays_actual_factory_budget_port(self):
        self.finish_failed()
        value = self.history.snapshot()
        second = NextRunFixture(self.root / 'second', value, 'FIXTURE-LIVE-RUN-2',
                                '2026-09-11T10:00:30Z').build_selected()
        def factory():
            return LiveEvidenceVerifiers(second.live_inputs(), context=second.context(), admission_evidence={},
                need_ref=second.scope['provider_config_ref'], admission_closure_ref=second.scope['provider_config_ref'],
                pilot_owner='fixture-pilot-owner', executor_id='fixture-executor',
                applicability_decision_ref=second.scope['provider_config_ref'], provider_owner='fixture-provider-owner',
                binding_ref=second.scope['provider_config_ref'], provider=None, retained_budget=self.base,
                human_verifier=lambda _: False, runtime_observer=lambda _: None, cumulative_history=self.history)
        # Independent synthetic authority supplies the other three ports. The
        # real factory budget port must traverse the entire frozen H1 closure.
        verifiers = second.verifiers(budget_checkpoint=factory().budget_checkpoint)
        result = compile_live_preflight(second.live_inputs(), **second.arguments(
            checked_at=second.selected_freeze, verifiers=verifiers))
        self.assertEqual(1751, result['checkpoint']['known_total_tokens'])
        self.assertEqual(1744, self.base.snapshot()['known_total_tokens'])
        cold_verifiers = second.verifiers(budget_checkpoint=factory().budget_checkpoint)
        self.assertEqual(result, validate_live_preflight(second.live_inputs(), result, context=second.context(),
            expected_checked_at=second.selected_freeze, verifiers=cold_verifiers))
        # No sidecar context override: a fresh, internally pinned but false
        # scope is rejected at the same factory port through real H1.
        altered = NextRunFixture(self.root / 'altered', value | {'known_total_tokens': 1744},
                                 'FIXTURE-LIVE-RUN-3', second.selected_freeze).build_selected()
        wrong = LiveEvidenceVerifiers(altered.live_inputs(), context=altered.context(), admission_evidence={},
            need_ref=altered.scope['provider_config_ref'], admission_closure_ref=altered.scope['provider_config_ref'],
            pilot_owner='fixture-pilot-owner', executor_id='fixture-executor',
            applicability_decision_ref=altered.scope['provider_config_ref'], provider_owner='fixture-provider-owner',
            binding_ref=altered.scope['provider_config_ref'], provider=None, retained_budget=self.base,
            human_verifier=lambda _: False, runtime_observer=lambda _: None, cumulative_history=self.history)
        with self.assertRaises(EvaluationValidationError):
            compile_live_preflight(altered.live_inputs(), **altered.arguments(checked_at=altered.selected_freeze,
                verifiers=altered.verifiers(budget_checkpoint=wrong.budget_checkpoint)))

    def test_next_run_cannot_freeze_before_previous_run_closed_even_when_start_is_later(self):
        self.finish_failed()
        first = self.history.snapshot()
        second = NextRunFixture(self.root / 'second', first, 'FIXTURE-LIVE-RUN-2').build_selected()
        self.now = '2026-09-11T10:01:00Z'
        book, retained = self.new_book(second, SECOND, first)
        self.finish_failed(book=book)
        with self.assertRaises(EvaluationValidationError):
            RetainedBudgetHistory(self.base, (self.retained, retained)).snapshot()

    def test_run_cannot_start_before_its_frozen_case_selection(self):
        self.finish_failed()
        first = self.history.snapshot()
        second = NextRunFixture(self.root / 'second', first, 'FIXTURE-LIVE-RUN-2',
                                '2026-09-11T10:00:30Z').build_selected()
        self.now = '2026-09-11T10:00:20Z'
        book, retained = self.new_book(second, SECOND, first)
        self.finish_failed(book=book)
        with self.assertRaises(EvaluationValidationError):
            RetainedBudgetHistory(self.base, (self.retained, retained)).snapshot()

    def test_slow_pilot_read_cannot_hide_base_drift(self):
        self.finish_failed()
        original = RetainedPilotBudget.snapshot
        changed = False
        def read(run, prior):
            nonlocal changed
            actual = original(run, prior)
            if not changed:
                changed = True
                with ConformanceUsageJournal.open(self.base.database, anchor_path=self.base.anchor,
                                                  **fixtures.JOURNAL_POLICY) as journal:
                    journal.start_attempt(repair_refreeze_confirmed=True)
                    journal.fail_attempt()
            return actual
        with patch.object(RetainedPilotBudget, 'snapshot', read), self.assertRaises(EvaluationValidationError):
            self.history.snapshot()
        self.assertTrue(changed)
        self.assertEqual(2, len(self.base.snapshot()['attempts']))

    def test_slow_read_cannot_drop_later_pilot_facts(self):
        slot = self.book.snapshot()['attempts'][0]['attempt_id']
        self.book.start_attempt(slot)
        original = RetainedPilotBudget.snapshot
        changed = False
        def read(run, prior):
            nonlocal changed
            actual = original(run, prior)
            if not changed:
                changed = True
                handle = self.book.reserve(input_upper_tokens=32, output_upper_tokens=16)
                self.book.reject_before_send(handle)
                self.book.fail_attempt(slot)
            return actual
        with patch.object(RetainedPilotBudget, 'snapshot', read), self.assertRaises(EvaluationValidationError):
            self.history.snapshot()
        self.assertTrue(changed)
        self.assertEqual('released-before-send', self.book.snapshot()['calls'][0]['status'])

    def test_archive_change_inside_sqlite_read_rejects_inconsistent_anchor(self):
        slot = self.book.snapshot()['attempts'][0]['attempt_id']
        self.book.start_attempt(slot)
        original = PilotUsageJournal._snapshot
        changed = False
        def read(journal, state):
            nonlocal changed
            actual = original(journal, state)
            if not changed:
                changed = True
                self.book.fail_attempt(slot)
            return actual
        with patch.object(PilotUsageJournal, '_snapshot', read), self.assertRaises(EvaluationValidationError):
            self.history.snapshot()
        self.assertTrue(changed)

    def test_safe_failure_drops_caller_context_and_arbitrary_source_exception(self):
        self.finish_failed()
        try:
            raise RuntimeError('PRIVATE-CALLER-SENTINEL')
        except RuntimeError:
            with patch.object(RetainedConformanceBudget, 'snapshot', side_effect=OSError('PRIVATE-READER-SENTINEL')):
                try:
                    self.history.snapshot()
                except EvaluationValidationError as error:
                    self.assertIsNone(error.__context__)
                    self.assertIsNone(error.__cause__)
                    self.assertNotIn('SENTINEL', str(error))
                else:
                    self.fail('unverified read accepted')


if __name__ == '__main__':
    unittest.main()
