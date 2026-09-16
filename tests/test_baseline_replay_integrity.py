"""Mutate one real A2 archive and rehash every enclosing reference."""

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import yaml

from research_workbench.evaluation.pins import EvaluationValidationError, digest
from research_workbench.execution.baseline_closeout import verify_baseline_receipt
from research_workbench.observability.trace import _parse_message, validate_attempt_trace
from tests import test_baseline_execution as execution
from tests.baseline_fixtures import A2, ROOT, BaselineFixture


class BaselineReplayIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        harness = execution.BaselineExecutionTests()
        harness.f = BaselineFixture(Path(temporary.name))
        harness.f.build()
        provider = execution.ScriptedProvider(execution.response('call', tool=True), execution.response('final'))
        harness.freeze(provider, A2)
        cls.result = harness.run_arm(provider, tools=(harness.load_tool(),))
        assert cls.result['replay_valid'], cls.result['replay_error']
        cls.template = harness.f

    def setUp(self):
        self.reset()

    def reset(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.f = copy.deepcopy(self.template)
        self.f.root = Path(temporary.name)
        shutil.copytree(self.template.root, self.f.root, dirs_exist_ok=True)
        self.load_result(self.result)

    def load_result(self, result):
        self.receipt_path = result['receipt_ref']['path']
        self.receipt = copy.deepcopy(result['receipt'])
        self.trace = self.f.doc(self.receipt['trace_index_ref']['path'])
        self.directory = Path(self.receipt['trace_index_ref']['path']).parent
        self.events_path = (self.directory / self.trace['event_ledger']['path']).as_posix()
        self.events = [json.loads(line) for line in (self.f.root / self.events_path).read_text().splitlines()]
        self.facts = [self.f.doc(ref['path']) for ref in self.receipt['fact_refs']]

    def change_request(self, position, mutate):
        self.change_message('provider-request', position, lambda content: mutate(content['request']))

    def change_final_response(self, mutate):
        content = self.change_message('provider-response', -1, lambda content: mutate(content['response']))
        ref = self.receipt['artifact_refs'][0]
        ref.update(self.f.write(ref['path'], content['response']))

    def change_message(self, kind, position, mutate):
        entry = [row for row in self.trace['messages'] if row['kind'] == kind][position]
        path = self.directory / entry['path']
        header, body = _parse_message(self.f.root / path)
        content = json.loads(body)
        mutate(content)
        raw = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
        header['content_sha256'] = entry['content_sha256'] = hashlib.sha256(raw).hexdigest()
        data = b'---\n' + yaml.safe_dump(header, sort_keys=False, allow_unicode=True).encode() + b'---\n' + raw + b'\n'
        entry['sha256'] = self.f.raw(path.as_posix(), data)['sha256']
        return content

    def resign(self, *, update_creation_pins=True):
        for reference, fact in zip(self.receipt['fact_refs'], self.facts):
            fact['event_sha256'] = digest(self.events[fact['event_sequence'] - 1])
            reference.update(self.f.write(reference['path'], fact))
            entry = next(row for row in self.trace['decision_refs'] if self.directory / row['path'] == Path(reference['path']))
            entry['sha256'] = reference['sha256']
            for event in self.events:
                if update_creation_pins and event['event_type'] == 'file-revision' and self.directory / event['payload']['path'] == Path(reference['path']):
                    event['payload']['new_sha256'] = reference['sha256']
        raw = ''.join(json.dumps(event, sort_keys=True, ensure_ascii=False) + '\n' for event in self.events).encode()
        self.trace['event_ledger']['sha256'] = self.f.raw(self.events_path, raw)['sha256']
        self.trace['event_ledger']['event_count'] = len(self.events)
        self.receipt['trace_index_ref'] = self.f.write(self.receipt['trace_index_ref']['path'], self.trace)
        validation = self.f.doc(self.receipt['validation_ref']['path'])
        for ref in validation['subject_refs']:
            for actual in [self.receipt['trace_index_ref'], *self.receipt['artifact_refs']]:
                if ref['path'] == actual['path']:
                    ref.update(actual)
        self.receipt['validation_ref'] = self.f.write(self.receipt['validation_ref']['path'], validation)
        self.receipt_ref = self.f.write(self.receipt_path, self.receipt)
        report = validate_attempt_trace(self.f.root, self.f.root / self.receipt['trace_index_ref']['path'])
        self.assertFalse(report.blocked, report.risks)

    def replay(self):
        return verify_baseline_receipt(self.f.root, self.receipt_ref, expected_envelope_ref=self.f.envelope_ref, schema_root=ROOT / 'schemas')

    def test_unchanged_archive_replays(self):
        self.resign()
        with patch('research_workbench.execution.baseline_envelope.compiler_reference',
                   return_value={'path': 'historical/compiler.py', 'sha256': '0' * 64}):
            self.assertEqual(self.replay()['status'], 'completed')

    def test_completed_rejects_unexecuted_final_tool_call(self):
        self.change_final_response(lambda response: response['tool_calls'].append({
            'call_id': 'never-executed-final-call', 'name': 'bounded_operation',
            'arguments': {'value': '7'},
        }))
        self.resign()
        with self.assertRaisesRegex(EvaluationValidationError, 'completed baseline'):
            self.replay()

    def test_completed_rejects_tool_result_without_final_provider_response(self):
        harness = execution.BaselineExecutionTests()
        self.f = harness.f = BaselineFixture(self.f.root / 'turn-limited')
        self.f.build()
        manifest = self.f.doc(self.f.manifest_ref['path'])
        manifest['frozen_conditions']['budget']['max_turns'] = 1
        self.f.manifest_ref = self.f.write(self.f.manifest_ref['path'], manifest)
        provider = execution.ScriptedProvider(execution.response('tool', tool=True))
        harness.freeze(provider, A2)
        result = harness.run_arm(provider, tools=(harness.load_tool(),))
        harness.assert_preserved_failure(result, replay_valid=True)
        self.load_result(result)
        self.trace['attempt_status'] = 'completed'
        self.events[self.facts[-1]['event_sequence'] - 1]['payload']['to_status'] = 'completed'
        self.receipt['status'] = 'completed'
        validation = self.f.doc(self.receipt['validation_ref']['path'])
        validation['status'] = 'pass'
        for check in validation['checks']:
            check['status'] = 'pass'
        self.f.write(self.receipt['validation_ref']['path'], validation)
        self.resign()
        with self.assertRaisesRegex(EvaluationValidationError, 'completed baseline'):
            self.replay()

    def test_completed_requires_elapsed_below_frozen_deadline(self):
        limit = self.f.envelope['transport_enforcement_metadata']['budget']['max_seconds']
        for elapsed in (limit, limit + 1):
            with self.subTest(elapsed=elapsed):
                self.reset()
                self.facts[-1]['elapsed_seconds'] = self.receipt['elapsed_seconds'] = elapsed
                self.resign()
                with self.assertRaisesRegex(EvaluationValidationError, 'completed baseline'):
                    self.replay()

    def test_completed_requires_a_successful_terminal_response(self):
        for reason in ('length', 'refusal', 'paused', 'context_limit', 'error', 'unknown', 'tool_call'):
            with self.subTest(reason=reason):
                self.reset()
                self.change_final_response(lambda response: response.update(finish_reason=reason))
                self.resign()
                with self.assertRaisesRegex(EvaluationValidationError, 'completed baseline'):
                    self.replay()

    def test_stop_response_within_deadline_remains_completed(self):
        self.change_final_response(lambda response: response.update(finish_reason='stop'))
        self.facts[-1]['elapsed_seconds'] = self.receipt['elapsed_seconds'] = (
            self.f.envelope['transport_enforcement_metadata']['budget']['max_seconds'] - 0.001)
        self.resign()
        self.assertEqual(self.replay()['status'], 'completed')

    def test_before_fact_backfilled_after_response_is_rejected(self):
        bound = [self.events[fact['event_sequence'] - 1] for fact in self.facts]
        late = next(e for e in self.events if e['event_type'] == 'file-revision'
                    and self.directory / e['payload']['path'] == Path(self.receipt['fact_refs'][0]['path']))
        self.events.remove(late)
        self.events.insert(self.events.index(bound[1]) + 1, late)
        for sequence, event in enumerate(self.events, 1):
            event.update(sequence=sequence, event_id=f'EVT-{sequence:04d}')
        for fact, event in zip(self.facts, bound):
            fact['event_sequence'] = event['sequence']
        self.resign()
        with self.assertRaisesRegex(EvaluationValidationError, 'fact creation'):
            self.replay()

    def test_validation_checker_path_or_hash_drift_is_rejected(self):
        for field, value in (('path', self.f.public_input_ref['path']), ('sha256', '0' * 64)):
            with self.subTest(field=field):
                self.reset()
                validation = self.f.doc(self.receipt['validation_ref']['path'])
                validation['checker']['source_ref'][field] = value
                self.f.write(self.receipt['validation_ref']['path'], validation)
                self.resign()
                with self.assertRaises(EvaluationValidationError):
                    self.replay()

    def test_each_fact_requires_one_exact_creation_before_further_activity(self):
        for index in range(len(self.facts)):
            for mutation in ('missing', 'duplicate', 'late'):
                with self.subTest(fact=index, mutation=mutation):
                    self.reset()
                    bound = [self.events[fact['event_sequence'] - 1] for fact in self.facts]
                    creation = next(e for e in self.events if e['event_type'] == 'file-revision'
                                    and self.directory / e['payload']['path'] == Path(self.receipt['fact_refs'][index]['path']))
                    if mutation == 'duplicate':
                        self.events.insert(self.events.index(creation), copy.deepcopy(creation))
                    else:
                        self.events.remove(creation)
                        if mutation == 'late':
                            self.events.append(creation)
                    for sequence, event in enumerate(self.events, 1):
                        event.update(sequence=sequence, event_id=f'EVT-{sequence:04d}')
                    for fact, event in zip(self.facts, bound):
                        fact['event_sequence'] = event['sequence']
                    # The terminal fact is already last; relocating it there
                    # preserves the genuine lifecycle and must remain valid.
                    self.resign()
                    if index == len(self.facts) - 1 and mutation == 'late':
                        self.assertEqual(self.replay()['status'], 'completed')
                    else:
                        with self.assertRaises(EvaluationValidationError):
                            self.replay()

    def test_checker_source_bytes_must_match_pin(self):
        validation = self.f.doc(self.receipt['validation_ref']['path'])
        path = self.f.root / validation['checker']['source_ref']['path']
        path.write_bytes(path.read_bytes() + b'\n# drift\n')
        self.resign()
        with self.assertRaisesRegex(EvaluationValidationError, 'hash mismatch'):
            self.replay()

    def test_creation_path_hash_and_action_are_authoritative(self):
        for target in ('decisions/BASELINE-FACT-0001.yaml', 'checker-source.py'):
            for field, value in (('path', 'decisions/unbound.yaml'), ('new_sha256', '0' * 64), ('action', 'modified')):
                with self.subTest(target=target, field=field):
                    self.reset()
                    self.resign()
                    creation = next(e for e in self.events if e['event_type'] == 'file-revision' and e['payload']['path'] == target)
                    creation['payload'][field] = value
                    self.resign(update_creation_pins=False)
                    with self.assertRaisesRegex(EvaluationValidationError, 'fact creation'):
                        self.replay()

    def test_tool_implementation_must_match_qualification(self):
        for fact in self.facts:
            if fact['operation'] == 'tool':
                self.assertIn(self.f.public_input_ref, fact['use_refs'])
                fact['tool_ref'] = copy.deepcopy(self.f.public_input_ref)
        self.resign()
        with self.assertRaisesRegex(EvaluationValidationError, 'qualified Tool'):
            self.replay()

    def test_scalar_and_list_tool_results_replay_from_observed_bytes(self):
        for value in ('7', [7], None):
            with self.subTest(value=value):
                self.reset()
                event = next(e for e in self.events if e['event_type'] == 'tool-call'
                             and e['payload']['status'] == 'succeeded')
                ref = event['payload']['result_ref']
                path = self.directory / ref['path']
                ref['sha256'] = self.f.raw(path.as_posix(), json.dumps(value).encode())['sha256']
                entry = next(r for r in self.trace['tool_event_refs'] if r['path'] == ref['path'])
                entry['sha256'] = ref['sha256']
                self.change_request(1, lambda r: r['messages'][-1]['content'][0]['data'].update(output=value))
                self.resign()
                self.assertEqual(self.replay()['status'], 'completed')

    def test_first_request_must_match_public_payload_and_tool_surface(self):
        mutations = (
            lambda r: r['messages'][0]['content'][0].update(text='Injected Method control'),
            lambda r: r.update(tools=[]),
            lambda r: r.update(max_output_tokens=r['max_output_tokens'] + 1),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                self.reset()
                self.change_request(0, mutate)
                self.resign()
                with self.assertRaisesRegex(EvaluationValidationError, 'provider request'):
                    self.replay()

    def test_later_request_must_preserve_observed_tool_history(self):
        self.change_request(1, lambda r: r['messages'][-1]['content'][0]['data'].update(output={'value': '999'}))
        self.resign()
        with self.assertRaisesRegex(EvaluationValidationError, 'provider request'):
            self.replay()

    def test_each_invocation_requires_its_own_complete_use_refs(self):
        before = [i for i, fact in enumerate(self.facts) if fact['phase'] == 'before']
        for index in before:
            with self.subTest(fact=index):
                self.reset()
                self.facts[index]['use_refs'] = [copy.deepcopy(self.f.envelope_ref)]
                self.resign()
                with self.assertRaisesRegex(EvaluationValidationError, 'use.boundary'):
                    self.replay()

    def test_collectively_omitted_qualification_input_is_rejected(self):
        omitted = self.f.bindings[A2]['interface_ref']
        for fact in self.facts:
            fact['use_refs'] = [r for r in fact['use_refs'] if r != omitted]
        self.resign()
        with self.assertRaisesRegex(EvaluationValidationError, 'use.boundary'):
            self.replay()

    def test_tool_arguments_must_match_the_observed_provider_call(self):
        for event in self.events:
            if event['event_type'] == 'tool-call':
                event['payload']['arguments'] = {'value': '999'}
        self.resign()
        with self.assertRaisesRegex(EvaluationValidationError, 'Tool call'):
            self.replay()

    def test_validation_cannot_include_an_unrelated_subject(self):
        validation = self.f.doc(self.receipt['validation_ref']['path'])
        validation['subject_refs'].append(self.f.public_input_ref)
        self.f.write(self.receipt['validation_ref']['path'], validation)
        self.resign()
        with self.assertRaisesRegex(EvaluationValidationError, 'subject'):
            self.replay()
