"""A closed redacted report is publishable once, without claiming live acceptance."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from research_workbench.adapters.models.conformance_journal import ConformanceUsageJournal
from research_workbench.adapters.models.profile_conformance_report import write_profile_conformance_report
from research_workbench.validation.schemas import SchemaCatalog
from tests import test_profile_conformance as driver_helpers

ROOT = Path(__file__).resolve().parents[1]


class ProfileConformanceReportingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.output = self.directory / 'report.json'
        self.catalog = SchemaCatalog(ROOT / 'schemas')
        journal = ConformanceUsageJournal.create(self.directory / 'usage.sqlite', namespace=str(uuid4()), total_token_limit=10000)
        self.addCleanup(journal.close)
        config = json.loads((ROOT / 'registry/providers/adapters-v2.disabled.json').read_text(encoding='utf-8'))
        adapter = next(item for item in config['adapters'] if 'deepseek' in item['adapter_id'])
        profile = json.loads((ROOT / adapter['profile_ref']['path']).read_text(encoding='utf-8'))
        self.report = {
            'schema_version': '0.1.0', 'record_kind': 'profile_conformance_report', 'report_version': '1.0.0',
            'status': 'blocked', 'stop_code': 'plan-blocked', 'provider': profile['identity']['provider'],
            'profile_id': profile['profile_id'], 'requested_model': profile['model']['requested_id'],
            'observed_models': [], 'profile_ref': adapter['profile_ref'], 'config_ref': None,
            'source_refs': [{'module': 'research_workbench.adapters.models.' + name,
                'source_sha256': hashlib.sha256((ROOT / ('src/research_workbench/adapters/models/' + name + '.py')).read_bytes()).hexdigest()}
                for name in ('profile_conformance', 'conformance_transport')],
            'limits': {'max_provider_invocations': 3, 'max_tool_executions': 1, 'max_output_tokens': 256, 'max_seconds': 120},
            'calls': [], 'actual_counts': {'provider_invocations': 0, 'http_entry_observations': 0, 'tool_executions': 0, 'responses_received': 0},
            'assertions': {'tool_call_shape': False, 'tool_executed_once': False, 'text_exact': False, 'schema_exact': False},
            'accounting': journal.snapshot(), 'remote_strict_claim': False, 'live_qualified': False,
            'qualification': 'external-accepted-run-gates-required', 'http_observation': 'delegate-entry-only-not-socket-proof',
            'warnings': ['caller-attested-gates', 'partial-source-closure', 'input-bound-proof-unverified', 'windows-run-unaccepted', 'remote-strict-unclaimed'],
        }

    def write(self, report=None, output=None):
        write_profile_conformance_report(self.report if report is None else report,
            self.output if output is None else output, schema_root=ROOT / 'schemas')

    def test_closed_failed_report_writes_once(self):
        self.assertEqual(self.catalog.validate('profile_conformance_report', self.report), [])
        self.write()
        original = self.output.read_bytes()
        self.assertEqual(json.loads(original), self.report)
        with self.assertRaises(FileExistsError):
            self.write()
        self.assertEqual(self.output.read_bytes(), original)

    def test_unknown_and_content_fields_rejected_before_file_creation(self):
        paths = [(), ('actual_counts',), ('assertions',), ('limits',), ('accounting',), ('accounting', 'cost')]
        for path in paths:
            with self.subTest(path=path):
                report = copy.deepcopy(self.report)
                target = report
                for key in path:
                    target = target[key]
                target['request_content'] = 'SYNTHETIC-SECRET-MARKER'
                with self.assertRaisesRegex(ValueError, 'closed contract'):
                    self.write(report)
                self.assertFalse(self.output.exists())

    def test_structural_report_does_not_grant_live_or_strict_authority(self):
        for field in ('live_qualified', 'remote_strict_claim'):
            report = copy.deepcopy(self.report)
            report[field] = True
            with self.assertRaises(ValueError):
                self.write(report)
            self.assertFalse(self.output.exists())

    def test_completed_requires_real_counts_and_all_local_assertions(self):
        report = copy.deepcopy(self.report)
        report.update(status='completed', stop_code='completed')
        with self.assertRaises(ValueError):
            self.write(report)
        self.assertFalse(self.output.exists())

    def test_two_different_modules_required_for_partial_source_receipt(self):
        report = copy.deepcopy(self.report)
        report['source_refs'][1]['module'] = report['source_refs'][0]['module']
        report['source_refs'][1]['source_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.write(report)
        self.assertFalse(self.output.exists())

    def test_nonfinite_and_non_json_values_have_content_free_errors(self):
        for value in (float('nan'), object()):
            report = copy.deepcopy(self.report)
            report['extra'] = value
            with self.assertRaises(ValueError) as raised:
                self.write(report)
            self.assertEqual(str(raised.exception), 'profile conformance report requires finite JSON primitives')
            self.assertIsNone(raised.exception.__context__)
            self.assertFalse(self.output.exists())

    def test_existing_directory_is_not_replaceable(self):
        with self.assertRaises(OSError):
            self.write(output=self.directory)

    def driver_fixture(self):
        fixture = driver_helpers.ProfileConformanceTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def test_genuine_completed_and_failed_driver_reports_are_publishable(self):
        for failure, expected in ((None, 'completed'), ('bad_text', 'text-assertion-failed'),
                ('unknown_usage', 'unknown-token-usage'), ('identity_drift', 'provider-invocation-failed')):
            with self.subTest(failure=failure):
                fixture = self.driver_fixture()
                if failure:
                    setattr(fixture.transport, failure, True)
                report = fixture.run_driver()
                self.assertEqual(report['stop_code'], expected)
                self.assertEqual(self.catalog.validate('profile_conformance_report', report), [])
                output = self.directory / (str(failure) + '.json')
                self.write(report, output)
                self.assertEqual(json.loads(output.read_bytes()), report)

    def test_completed_calls_with_unavailable_final_accounting_still_publish(self):
        fixture = self.driver_fixture()
        snapshot = fixture.journal.snapshot

        def fail_after_execution():
            if len(fixture.transport.requests) == 3:
                raise OSError('synthetic private final accounting detail')
            return snapshot()

        with patch.object(fixture.journal, 'snapshot', side_effect=fail_after_execution):
            report = fixture.run_driver()
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['stop_code'], 'accounting-failed')
        self.assertIsNone(report['accounting'])
        self.assertEqual(report['actual_counts']['responses_received'], 3)
        self.assertEqual(sum(row['input_tokens'] + row['output_tokens'] for row in report['calls']), 21)
        self.write(report)
        self.assertEqual(json.loads(self.output.read_bytes()), report)

    def test_guard_refusal_reports_publish_released_reservation_without_send(self):
        for refused_stage in ('preinvoke', 'send'):
            with self.subTest(refused_stage=refused_stage):
                fixture = self.driver_fixture()
                report = fixture.run_driver(guard=lambda stage, ordinal: stage != refused_stage)
                self.assertEqual(report['stop_code'], 'guard-refused')
                self.assertEqual(report['accounting']['calls'][0]['accounting_status'], 'released-before-send')
                self.assertEqual(report['accounting']['unresolved_reserved_tokens'], 0)
                self.assertEqual(fixture.transport.requests, [])
                self.assertEqual(fixture.helper.credential.resolutions, 0 if refused_stage == 'preinvoke' else 1)
                self.write(report, self.directory / (refused_stage + '.json'))


if __name__ == '__main__':
    unittest.main()
