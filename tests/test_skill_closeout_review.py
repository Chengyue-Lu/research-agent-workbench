"""Independent regression cases for PR81's two-stage execution review."""

import copy
import contextlib
import hashlib
import io
import json
import runpy
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research_workbench.execution import (
    GenericCloseoutValidationError, SKILL_CLOSEOUT_CONTRACT, execute_frozen_view,
)
from research_workbench.execution.generic_closeout import _validate_trace_execution_records
from research_workbench.validation import SchemaCatalog
from research_workbench.io import load_document
from tests.execution_fixtures import RecordingDriver, SequenceClock
from tests.skill_closeout_fixtures import ROOT, SkillCloseoutFixture, write
from tests import test_generic_execution_closeout as core_tests
from tests import test_skill_execution_closeout as skill_tests


class SkillCloseoutReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def rewrite(self, fixture, mutate):
        skill_tests.SkillExecutionCloseoutTests.rewrite_trace(SimpleNamespace(root=fixture.root), fixture, mutate)

    def test_consumption_fact_never_predicts_post_call_binding(self):
        fixture = SkillCloseoutFixture(self.root, lifecycle='failed', drift='model')
        index = load_document(fixture.trace_dir / 'INDEX.yaml')
        facts = [load_document(fixture.trace_dir / ref['path']) for ref in index['decision_refs']]
        consumption = next(f for f in facts if f.get('execution_phase') == 'use-boundary')
        self.assertNotIn('actual_binding', consumption)
        self.assertNotIn('actual_supply_report_ref', consumption)
        actual = [f for f in facts if f.get('record_kind') == 'actual-execution-binding']
        self.assertEqual(1, len(actual))
        self.assertEqual('post-call', actual[0]['execution_phase'])
        self.assertEqual('observed-drift-model', actual[0]['actual_binding']['model']['ref'])
        receipt = fixture.build()
        self.assertEqual('failed', receipt['status'])
        self.assertEqual('none', receipt['completion_claim'])

    def test_wrong_kind_contract_blocks_before_any_driver_call(self):
        helper = core_tests.GenericExecutionCloseoutTests()
        for kind in ('direct-tool', 'no-skill'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                _, view = helper._bundle_and_view(root, kind)
                driver = RecordingDriver(root, view.document['binding'],
                                         supply_ref=view.document['selected_supply_report_ref']['ref'])
                report = execute_frozen_view(view, driver, report_id='HOST', attempt_id='ATTEMPT',
                    clock=SequenceClock('2026-08-26T00:00:01Z', '2026-08-26T00:00:02Z'),
                    closeout_contract=SKILL_CLOSEOUT_CONTRACT, schema_root=ROOT / 'schemas')
                self.assertEqual(0, driver.calls)
                self.assertEqual('preflight-blocked', report['execution_phase'])
                self.assertEqual('HOST-SKILL-CLOSURE-INVALID', report['diagnostic']['code'])
                self.assertEqual(0, report['actual_facts']['provider_invocations'])
                self.assertEqual(0, report['actual_facts']['tool_invocations'])
                self.assertNotIn('actual_binding', report)
                self.assertNotIn('actual_skill_consumption', report)

    def test_invalid_projection_closure_blocks_before_call(self):
        fixture = SkillCloseoutFixture(self.root)
        (self.root / 'bundle/skill-projection.yaml').write_text('{}', encoding='utf-8')
        driver = RecordingDriver(self.root, fixture.view.document['binding'],
                                 supply_ref=fixture.view.document['selected_supply_report_ref']['ref'])
        report = execute_frozen_view(fixture.view, driver, report_id='HOST', attempt_id='ATTEMPT',
            clock=SequenceClock('2026-08-26T00:00:01Z', '2026-08-26T00:00:02Z'),
            closeout_contract=SKILL_CLOSEOUT_CONTRACT, schema_root=ROOT / 'schemas')
        self.assertEqual(0, driver.calls)
        self.assertEqual('preflight-blocked', report['execution_phase'])
        self.assertNotIn('actual_binding', report)
        self.assertNotIn('actual_skill_consumption', report)

    def test_later_conflicting_reread_cannot_be_hidden_by_restored_file(self):
        fixture = SkillCloseoutFixture(self.root)
        def mutate(index, events):
            read = copy.deepcopy(next(e for e in events if e['event_type'] == 'content-read'))
            read['event_id'] = 'EVT-9999'
            read['payload']['content_sha256'] = '0' * 64
            at = next(i for i, e in enumerate(events) if e['event_type'] == 'file-revision') + 1
            events.insert(at, read)
            for sequence, event in enumerate(events, 1):
                event['sequence'] = sequence
        self.rewrite(fixture, mutate)
        # The live file has its original bytes; replay must still reject the ledger.
        with self.assertRaisesRegex(GenericCloseoutValidationError, 'exactly one.*Trace read'):
            fixture.build()

    def test_missing_duplicate_or_misattributed_consumption_fact_is_rejected(self):
        for fault in ('missing', 'duplicate', 'other-attempt'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                fixture = SkillCloseoutFixture(Path(directory))
                def mutate(index, events):
                    ref = index['decision_refs'][1]
                    if fault == 'missing':
                        index['decision_refs'].remove(ref)
                    elif fault == 'duplicate':
                        other = write(fixture.root, 'closeout/trace/decisions/duplicate.yaml',
                                      load_document(fixture.trace_dir / ref['path']))
                        index['decision_refs'].append({'path': 'decisions/duplicate.yaml', 'sha256': other.sha256})
                    else:
                        path = fixture.trace_dir / ref['path']
                        doc = load_document(path); doc['attempt_id'] = 'OTHER-ATTEMPT'
                        ref['sha256'] = write(fixture.root, path.relative_to(fixture.root).as_posix(), doc).sha256
                self.rewrite(fixture, mutate)
                with self.assertRaisesRegex(GenericCloseoutValidationError, 'consumption fact'):
                    fixture.build()

    def test_post_call_fact_cannot_be_missing_or_created_before_execution_finishes(self):
        for fault in ('missing-creation', 'before-input', 'before-response', 'before-tool'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                fixture = SkillCloseoutFixture(Path(directory), with_tool=True)
                def mutate(index, events):
                    pin = index['decision_refs'][-1]
                    post = next(e for e in events if e['event_type']=='file-revision'
                                and e['payload']['new_sha256']==pin['sha256'])
                    events.remove(post)
                    if fault == 'before-input':
                        at = next(i for i,e in enumerate(events) if e['event_type']=='file-revision')
                        events.insert(at, post)
                    elif fault == 'before-response':
                        response = next(m['message_id'] for m in index['messages'] if m['kind']=='provider-response')
                        at = next(i for i,e in enumerate(events) if e.get('payload',{}).get('message_id')==response)
                        events.insert(at, post)
                    elif fault == 'before-tool':
                        at = next(i for i,e in enumerate(events) if e['event_type']=='tool-call')
                        events.insert(at, post)
                    for sequence,event in enumerate(events,1): event['sequence']=sequence
                self.rewrite(fixture, mutate)
                with self.assertRaisesRegex(GenericCloseoutValidationError, 'after execution activity'):
                    fixture.build()

    def test_consumption_fact_schema_rejects_predeclared_actual_binding(self):
        fixture = SkillCloseoutFixture(self.root)
        index = load_document(fixture.trace_dir / 'INDEX.yaml')
        fact = load_document(fixture.trace_dir / index['decision_refs'][1]['path'])
        fact['actual_binding'] = fixture.host['actual_binding']
        self.assertTrue(SchemaCatalog(ROOT/'schemas').validate('skill_execution_trace_fact',fact))
        with self.assertRaisesRegex(GenericCloseoutValidationError, 'requires Skill closeout'):
            _validate_trace_execution_records(self.root, fixture.trace_dir/'INDEX.yaml', index, fixture.host,
                                              catalog=SchemaCatalog(ROOT/'schemas'))

    def test_preflight_trace_cannot_include_a_consumption_fact(self):
        fixture = SkillCloseoutFixture(self.root, lifecycle='blocked')
        with tempfile.TemporaryDirectory() as directory:
            other = SkillCloseoutFixture(Path(directory))
            index = load_document(other.trace_dir/'INDEX.yaml')
            fact = load_document(other.trace_dir/index['decision_refs'][1]['path'])
        def mutate(index, events):
            ref = write(self.root, 'closeout/trace/decisions/pre-use.yaml', fact)
            index['decision_refs'].append({'path':'decisions/pre-use.yaml','sha256':ref.sha256})
        self.rewrite(fixture,mutate)
        with self.assertRaisesRegex(GenericCloseoutValidationError, 'pre-call Trace'):
            fixture.build()

    def test_duplicate_read_via_canonical_alias_is_rejected(self):
        fixture = SkillCloseoutFixture(self.root)
        def mutate(index, events):
            read = copy.deepcopy(next(e for e in events if e['event_type']=='content-read'))
            read['event_id']='EVT-9999'
            read['payload']['path']=read['payload']['path'].replace('bundle/','bundle/./')
            events.insert(-1,read)
            for sequence,event in enumerate(events,1): event['sequence']=sequence
        self.rewrite(fixture,mutate)
        with self.assertRaisesRegex(GenericCloseoutValidationError, 'exactly one.*Trace read'):
            fixture.build()

    def test_repaired_archive_replays_and_its_checkers_reject_bad_subjects(self):
        archive = ROOT / 'work/M11-007/A-20260915-003'
        proof = json.loads((archive/'checks/vertical-proof.json').read_bytes())
        with zipfile.ZipFile(ROOT / 'tests/fixtures/skill_closeout_sources/sources.zip') as sources:
            for ref in proof['source_refs']:
                content = sources.read(ref['sha256'] + '.txt')
                self.assertEqual(ref['sha256'], hashlib.sha256(content).hexdigest())
        for case in proof['cases']:
            with self.subTest(case=case['case']):
                for ref in case['files']:
                    self.assertEqual(ref['sha256'],hashlib.sha256((ROOT/ref['path']).read_bytes()).hexdigest())
                root = ROOT/case['project_root']
                output = io.StringIO()
                with patch.object(sys,'argv',[str(archive/'replay.py'),str(ROOT/case['receipt']['path']),
                                              case['receipt']['sha256'],str(root)]),contextlib.redirect_stdout(output):
                    runpy.run_path(str(archive/'replay.py'),run_name='__main__')
                self.assertEqual(case['result'],json.loads(output.getvalue()))
                check = runpy.run_path(str(root/'closeout/checker.py'))['check']
                self.assertTrue(check(root,load_document(root/'closeout/validation.yaml')['subject_refs']))
                for path in ('missing.yaml','../outside.yaml','closeout/host.yaml'):
                    self.assertFalse(check(root,[{'path':path,'sha256':'0'*64}]))
