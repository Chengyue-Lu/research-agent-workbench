"""Append-only three-to-ten synthetic grants; no real budget or Provider I/O."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from research_workbench.adapters.models import conformance_budget_grant as policy
from research_workbench.adapters.models.conformance_journal import ConformanceJournalError, ConformanceUsageJournal
from research_workbench.adapters.models.conformance_ledger import ConformanceLedgerError, ConformanceUsageLimits
from research_workbench.adapters.models.port import Usage
from research_workbench.adapters.models.profile_conformance_report import _verify_extension, verify_profile_conformance_report
from research_workbench.evaluation.pins import EvaluationInputs
from research_workbench.validation.schemas import SchemaCatalog
from tests import test_profile_conformance_reporting as reporting_helpers

ROOT = Path(__file__).resolve().parents[1]


class BudgetExtensionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'fake.sqlite'
        self.anchor = self.root / 'fake.anchor'
        self.namespace = str(uuid4())
        self.journal = ConformanceUsageJournal.create(self.db, anchor_path=self.anchor,
            namespace=self.namespace, total_token_limit=10000000)
        self.addCleanup(self.journal.close)

    def put(self, path, document):
        raw = (policy.canonical(document) + '\n').encode('ascii')
        target = self.root / path
        target.write_bytes(raw)
        return {'path': path, 'sha256': hashlib.sha256(raw).hexdigest()}

    def history(self):
        # 25 events, three failed Attempts, seven consumed slots, four actual
        # synthetic entry/response observations and 1205 known tokens.
        received = 0
        for attempt, responses in enumerate((2, 0, 2), 1):
            self.journal.start_attempt(repair_refreeze_confirmed=attempt > 1)
            for _ in range(responses):
                handle = self.journal.reserve(input_upper_tokens=500, output_upper_tokens=32)
                self.journal.persist_send_intent(handle)
                self.journal.record_http_entry(handle)
                received += 1
                self.journal.settle(handle, usage=Usage(300 if received < 4 else 305, 0),
                    successful=True, response_received=True)
            handle = self.journal.reserve(input_upper_tokens=500, output_upper_tokens=32)
            self.journal.reject_before_send(handle)
        snapshot = self.journal.snapshot()
        self.assertEqual((25, 7, 4, 1205, 0), (snapshot['events_committed'], snapshot['provider_invocations'],
            snapshot['responses_received'], snapshot['known_total_tokens'], snapshot['unresolved_reserved_tokens']))
        return snapshot

    def refs(self, decision_change=None):
        prefix = self.journal.budget_extension_prefix()
        source = self.put('user.json', {'user_authorized_total_attempts': 10, 'tokens': 10000000})
        decision = {'record_kind': 'conformance_attempt_limit_decision', 'version': '1.0.0',
            'budget_namespace': self.namespace, 'journal_identity': prefix['journal_identity'],
            'baseline_limits': dict(policy.BASELINE), 'new_max_attempts': 10, 'user_input_ref': source}
        if decision_change is not None:
            decision_change(decision)
        return self.put('decision.json', decision), self.put('prefix.json', prefix)

    def grant(self, **options):
        decision, prefix = self.refs(**options)
        return self.journal.extend_attempt_limit(root=self.root, decision_ref=decision, prefix_ref=prefix)

    def test_default_constructor_does_not_accept_ten(self):
        with self.assertRaises(ConformanceLedgerError):
            ConformanceUsageLimits(10000000, max_attempts=10)

    def test_grant_preserves_prefix_meta_header_identity_usage_and_requires_exact_reopen_pin(self):
        before = self.history()
        events = self.journal._events()
        meta = self.journal._connection.execute('SELECT * FROM meta').fetchall()
        identity = self.journal._connection.execute('SELECT * FROM budget_identity').fetchall()
        anchor = self.anchor.read_bytes()
        receipt = self.grant()
        after = self.journal.snapshot()
        self.assertEqual(events, self.journal._events()[:25])
        self.assertEqual(meta, self.journal._connection.execute('SELECT * FROM meta').fetchall())
        self.assertEqual(identity, self.journal._connection.execute('SELECT * FROM budget_identity').fetchall())
        self.assertTrue(self.anchor.read_bytes().startswith(anchor))
        for key in ('attempts', 'calls', 'known_total_tokens', 'responses_received', 'provider_invocations'):
            self.assertEqual(before[key], after[key])
        self.assertEqual((3, 10, 26), (after['baseline_limits']['max_attempts'], after['limits']['max_attempts'], after['events_committed']))
        self.assertEqual(receipt, after['attempt_limit_grant'])
        self.assertEqual('1.1.0', after['journal_version'])
        self.journal.close()
        for kwargs in ({}, {'grant_root': self.root, 'expected_grant_sha256': '0' * 64}):
            with self.assertRaises(ConformanceJournalError):
                ConformanceUsageJournal.open(self.db, anchor_path=self.anchor, namespace=self.namespace,
                    total_token_limit=10000000, **kwargs)
        reopened = ConformanceUsageJournal.open(self.db, anchor_path=self.anchor, namespace=self.namespace,
            total_token_limit=10000000, grant_root=self.root, expected_grant_sha256=receipt['sha256'])
        self.addCleanup(reopened.close)
        self.assertEqual(after, reopened.snapshot())

    def test_attempts_four_through_ten_without_slot_refund_and_eleventh_refused(self):
        self.history()
        self.grant()
        for ordinal in range(4, 11):
            self.assertEqual(ordinal, self.journal.start_attempt(repair_refreeze_confirmed=True))
            handle = self.journal.reserve(input_upper_tokens=100, output_upper_tokens=32)
            self.assertEqual(ordinal + 4, handle.reservation_ordinal)
            self.journal.reject_before_send(handle)
        with self.assertRaises(ConformanceJournalError):
            self.journal.start_attempt(repair_refreeze_confirmed=True)
        self.assertEqual(1205, self.journal.snapshot()['known_total_tokens'])

    def test_closed_wrong_types_missing_authority_and_repeated_grants_refuse_without_changes(self):
        self.history()
        mutations = (lambda d: d.update(new_max_attempts=True), lambda d: d.update(new_max_attempts=11),
            lambda d: d.update(new_max_attempts=10.0), lambda d: d.pop('user_input_ref'),
            lambda d: d['baseline_limits'].update(total_token_limit=10000001),
            lambda d: d.update(journal_identity=str(uuid4())), lambda d: d.update(extra='PRIVATE-FAKE-DETAIL'))
        for mutate in mutations:
            events, anchor = self.journal._events(), self.anchor.read_bytes()
            with self.assertRaises(ConformanceJournalError) as caught:
                self.grant(decision_change=mutate)
            self.assertIsNone(caught.exception.__context__)
            self.assertEqual(events, self.journal._events())
            self.assertEqual(anchor, self.anchor.read_bytes())
        self.grant()
        events = self.journal._events()
        with self.assertRaises(ConformanceJournalError):
            self.journal.extend_attempt_limit(root=self.root,
                decision_ref={'path': 'decision.json', 'sha256': '0' * 64}, prefix_ref={'path': 'prefix.json', 'sha256': '0' * 64})
        self.assertEqual(events, self.journal._events())

    def test_stale_prefix_and_active_or_held_refuse(self):
        decision, prefix = self.refs()
        self.journal.start_attempt()
        handle = self.journal.reserve(input_upper_tokens=100, output_upper_tokens=32)
        before = self.journal._events()
        with self.assertRaises(ConformanceJournalError):
            self.journal.extend_attempt_limit(root=self.root, decision_ref=decision, prefix_ref=prefix)
        self.assertEqual(before, self.journal._events())
        self.journal.persist_send_intent(handle)
        with self.assertRaises(ConformanceJournalError):
            self.grant()

    def test_interrupted_checkpoint_keeps_visible_stop_and_no_reset(self):
        self.history()
        decision, prefix = self.refs()
        original = self.journal._anchor.checkpoint
        def checkpoint_then_fail(events, *, previous_count):
            original(events, previous_count=previous_count)
            raise OSError('synthetic post-checkpoint failure')
        with patch.object(type(self.journal._anchor), 'checkpoint', side_effect=checkpoint_then_fail):
            with self.assertRaises(ConformanceJournalError):
                self.journal.extend_attempt_limit(root=self.root, decision_ref=decision, prefix_ref=prefix)
        self.assertEqual(25, len(self.journal._events()))
        with self.assertRaises(ConformanceJournalError):
            self.journal.snapshot()

    def test_next_attempt_capacity_preflight_refuses_before_reservation(self):
        self.history()
        self.grant()
        with patch('research_workbench.adapters.models.conformance_journal._MAX_EVENTS', 39):
            with self.assertRaises(ConformanceJournalError) as caught:
                self.journal.start_attempt(repair_refreeze_confirmed=True)
        self.assertEqual('journal-event-ceiling', caught.exception.code)
        self.assertEqual(26, self.journal.snapshot()['events_committed'])

    def test_extension_receipt_replays_original_three_and_rejects_false_provenance(self):
        self.history()
        self.grant()
        report = {'budget_extension': self.journal.extension_metadata(), 'accounting': self.journal.snapshot()}
        self.assertTrue(_verify_extension(report, EvaluationInputs(self.root, ROOT / 'schemas')))
        for mutation in (lambda d: d['budget_extension']['effective_limits'].update(max_attempts=11),
                lambda d: d['accounting']['calls'][0].update(input_upper_tokens=501),
                lambda d: d['budget_extension']['attempt_limit_grant'].update(sha256='0' * 64)):
            altered = copy.deepcopy(report)
            mutation(altered)
            self.assertFalse(_verify_extension(altered, EvaluationInputs(self.root, ROOT / 'schemas')))
        unavailable = copy.deepcopy(report)
        unavailable['accounting'] = None
        self.assertTrue(_verify_extension(unavailable, EvaluationInputs(self.root, ROOT / 'schemas')))

    def test_cumulative_counters_ordinals_attempt_counts_and_exposure_are_derived_from_all_calls(self):
        self.history()
        self.grant()
        self.journal.start_attempt(repair_refreeze_confirmed=True)
        handle = self.journal.reserve(input_upper_tokens=100, output_upper_tokens=32)
        self.journal.persist_send_intent(handle)
        self.journal.record_http_entry(handle)
        self.journal.settle(handle, usage=Usage(2, 3), successful=False, response_received=True)
        report = {'budget_extension': self.journal.extension_metadata(), 'accounting': self.journal.snapshot()}
        self.assertTrue(_verify_extension(report, EvaluationInputs(self.root, ROOT / 'schemas')))
        fields = ('provider_invocations', 'http_send_attempts', 'responses_received', 'successful_responses',
                  'failed_invocations', 'durable_send_intents', 'http_entry_observations')
        all_zero = copy.deepcopy(report)
        all_zero['accounting'].update({field: 0 for field in fields})
        self.assertFalse(_verify_extension(all_zero, EvaluationInputs(self.root, ROOT / 'schemas')))
        for field in fields:
            with self.subTest(field=field):
                altered = copy.deepcopy(report)
                altered['accounting'][field] = 0
                self.assertFalse(_verify_extension(altered, EvaluationInputs(self.root, ROOT / 'schemas')))
        mutations = (
            lambda d: d['accounting']['attempts'][-1].update(provider_invocations=0),
            lambda d: d['accounting']['attempts'][-1].update(ordinal=5),
            lambda d: d['accounting']['calls'][-1].update(ordinal=7),
            lambda d: d['accounting']['calls'][-1].update(attempt_ordinal=5),
            lambda d: d['accounting'].update(unresolved_reserved_tokens=1),
            lambda d: d['accounting'].update(remaining_token_capacity=10000000),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                altered = copy.deepcopy(report)
                mutate(altered)
                self.assertFalse(_verify_extension(altered, EvaluationInputs(self.root, ROOT / 'schemas')))

    def test_pending_and_uncertain_exposure_remains_held_in_extended_accounting(self):
        self.history()
        self.grant()
        self.journal.start_attempt(repair_refreeze_confirmed=True)
        handle = self.journal.reserve(input_upper_tokens=100, output_upper_tokens=32)
        for uncertain in (False, True):
            with self.subTest(uncertain=uncertain):
                if uncertain:
                    self.journal.persist_send_intent(handle)
                    self.journal.record_uncertain_failure(handle)
                report = {'budget_extension': self.journal.extension_metadata(), 'accounting': self.journal.snapshot()}
                self.assertEqual(132, report['accounting']['unresolved_reserved_tokens'])
                self.assertTrue(_verify_extension(report, EvaluationInputs(self.root, ROOT / 'schemas')))
                altered = copy.deepcopy(report)
                altered['accounting']['unresolved_reserved_tokens'] = 0
                altered['accounting']['remaining_token_capacity'] = 10000000 - 1205
                self.assertFalse(_verify_extension(altered, EvaluationInputs(self.root, ROOT / 'schemas')))

    def test_new_report_version_requires_extension_and_binding_and_keeps_old_closed_branches(self):
        self.history()
        self.grant()
        fixture = reporting_helpers.ProfileConformanceReportingTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        report = fixture.bound_report()
        report.update(report_version='1.2.0', accounting=self.journal.snapshot(),
            budget_extension=self.journal.extension_metadata())
        catalog = SchemaCatalog(ROOT / 'schemas')
        self.assertEqual([], catalog.validate('profile_conformance_report', report))
        # This structurally valid new version cannot bypass the unchanged
        # archived source/config binding checks via its newly allowed version.
        with self.assertRaises(ValueError):
            verify_profile_conformance_report(report, root=self.root, schema_root=ROOT / 'schemas')
        for version in ('1.0.0', '1.1.0'):
            altered = copy.deepcopy(report)
            altered['report_version'] = version
            self.assertNotEqual([], catalog.validate('profile_conformance_report', altered))
        for key in ('budget_extension', 'binding'):
            altered = copy.deepcopy(report)
            del altered[key]
            self.assertNotEqual([], catalog.validate('profile_conformance_report', altered))


if __name__ == '__main__':
    unittest.main()
