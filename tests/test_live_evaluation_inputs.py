"""Version/pin/plan attacks on preparation only; no live grant or ports."""
import copy
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from research_workbench.evaluation.harness_plan import compile_harness_plan
from research_workbench.evaluation.live_inputs import LiveEvaluationInputs
from research_workbench.evaluation.pins import EvaluationInputs, EvaluationValidationError
from research_workbench.evaluation.system_protocol import validate_protocol
from research_workbench.validation.schemas import SchemaCatalog
from tests.system_evaluation_fixtures import AT, ROOT, OverlapFixtureMixin


class LiveInputTests(OverlapFixtureMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.admission_ref = self.f.write('live/admission-case-closure.json',self.f.admission_closure)
        self.scope = {
            'schema_version':'0.2.0','record_kind':'evaluation_live_scope','version':'2.0.0',
            'purpose':'live-pilot','scope_id':'FIXTURE-LIVE-INPUTS',
            'status':'frozen-inputs-not-authorized','frozen_at':AT,'source_commit':'0'*40,
            'source_artifact_refs':[self.f.raw('live/source.txt',b'fixture, not source qualification')],
            'provider_config_ref':self.f.write('live/config.json',{'fixture-only':True}),
            'provider_applicability_ref':self.f.write('live/applicability.json',{'qualified':False}),
            'windows_context_ref':self.f.write('live/windows.json',{'fixture-only':True}),
            'budget_checkpoint_ref':self.f.write('live/checkpoint.json',{'fixture-only':True}),
            'input_closure_ref':self.f.case_closure_ref,'tool_configuration_refs':[],
            'execution_phase_allowlist':['pilot'],
            'output_contract':{'format':'bounded-evidence-relations-v1','max_body_bytes':16384,
                'max_json_depth':5,'cases':[{'case_id':c['case']['identity'],'claim_ids':['C01'],
                    'source_ids':['S01']} for c in self.f.case_closure['cases']]},
            'budget':{'cumulative_token_limit':10000000,'prior_tokens':1744,
                'max_provider_calls':24,'max_attempts':8,'max_calls_per_attempt':3,
                'max_request_input_tokens':512,'max_request_output_tokens':64,
                'max_attempt_seconds':120,'max_run_seconds':1800,'automatic_retry':False,'fallback':False},
            'window':{'time_zone':'Asia/Shanghai','not_before':'2026-09-11T10:00:00Z',
                'not_after':'2026-09-11T12:00:00Z',
                'official_window_ref':self.f.raw('live/window.txt',b'fixture, not an official fact')},
            'boundaries':dict.fromkeys(('runtime_input','execution_authority','supply_selection',
                'human_decision','task_completion','analysis_eligibility'),False)}
        self.protocol = copy.deepcopy(self.f.protocol)
        self.protocol.update(schema_version='0.2.0',version='2.0.0',purpose='live-pilot',
                             admission_case_closure_ref=self.admission_ref)
        self.protocol['design']['retry'].update(max_retries=0,eligible_failures=[])

    def inputs(self, **kw):
        return LiveEvaluationInputs(self.f.root,ROOT/'schemas',cumulative_token_ceiling=10000000,**kw)

    def write_protocol(self):
        self.protocol['live_scope_ref'] = self.f.write('live/scope.json',self.scope)
        return self.f.write('live/protocol.json',self.protocol)

    def reject(self):
        with self.assertRaises(EvaluationValidationError):
            validate_protocol(self.inputs(),self.write_protocol())

    def test_explicit_v2_reuses_protocol_invariants_without_granting_anything(self):
        inputs = self.inputs()
        actual = validate_protocol(inputs,self.write_protocol())
        self.assertEqual(actual['purpose'],'live-pilot')
        scope = inputs.read(actual['live_scope_ref'],'evaluation_live_scope')
        self.assertEqual(scope['status'],'frozen-inputs-not-authorized')
        self.assertFalse(any(scope['boundaries'].values()))
        self.assertEqual(inputs.read(scope['provider_applicability_ref'])['qualified'],False)
        self.assertNotIn('evaluation_live_scope', inputs.catalog.document_kinds)

    def test_old_default_rejects_new_protocol_and_scope(self):
        ref = self.write_protocol()
        with self.assertRaises(EvaluationValidationError):
            validate_protocol(EvaluationInputs(self.f.root,ROOT/'schemas'),ref)
        with self.assertRaises(KeyError):
            EvaluationInputs(self.f.root,ROOT/'schemas').read(self.protocol['live_scope_ref'],'evaluation_live_scope')

    def test_v2_catalog_is_standalone_without_private_cross_version_registration(self):
        self.write_protocol()
        with tempfile.TemporaryDirectory() as d:
            schemas = Path(d)/'schemas'
            shutil.copytree(ROOT/'schemas/v0.2.0',schemas/'v0.2.0')
            catalog = SchemaCatalog(schemas,version='0.2.0')
            self.assertEqual(catalog.validate('system_evaluation_protocol',self.protocol),[])
            self.assertEqual(catalog.validate('evaluation_live_scope',self.scope),[])
            self.protocol['execution_binding']['provider']['content_hash'] = 'invalid'
            self.assertTrue(catalog.validate('system_evaluation_protocol',self.protocol))

    def test_new_route_rejects_both_old_purposes_and_old_versions(self):
        original = copy.deepcopy(self.protocol)
        for key, value in [('purpose','synthetic-contract-proof'),('purpose','confirmatory-protocol'),
                           ('version','1.0.0'),('schema_version','0.1.0')]:
            with self.subTest(key=key,value=value):
                self.protocol = copy.deepcopy(original)
                self.protocol[key] = value
                self.reject()

    def test_old_downstream_records_are_never_accepted_through_live_reader(self):
        for kind in ['evaluation_harness_preflight','evaluation_harness_execution',
                     'evaluation_harness_evidence','evaluation_harness_review_package',
                     'evaluation_harness_analysis_input','evaluation_measurement']:
            with self.subTest(kind=kind),self.assertRaisesRegex(EvaluationValidationError,'nonexecuting H1'):
                self.inputs().validate(kind,{'purpose':'synthetic-contract-proof'})

    def compile_plan(self, case_closure_ref=None):
        # Build only positive whitelist inputs, without the H2/H3 fixture runner.
        manifest = self.f.doc(self.f.manifest_ref['path'])
        public = []
        context = manifest['frozen_conditions']['context']['initial_context_refs']
        for c in self.f.case_closure['cases']:
            case_id = c['case']['identity']
            refs = [i['ref'] for i in c['formal_inputs']]
            projection = {'task_ref':c['task']['ref'],'instruction':'Use the supplied public inputs.',
                          'input_refs':refs,'required_outputs':['plain-text-answer']}
            ref = self.f.write('public/' + case_id + '.json',projection)
            context.extend([*refs,ref])
            public.append({'case_id':case_id,'public_payload_ref':ref})
        self.protocol['manifest_ref'] = self.f.write('live/manifest.json',manifest)
        protocol_ref = self.write_protocol()
        return compile_harness_plan(self.inputs(),protocol_ref=protocol_ref,
            case_closure_ref=case_closure_ref or self.f.case_closure_ref,case_selection_frozen_at=AT,
            public_cases=public,plan_id='FIXTURE-V2-PLAN',run_id='FIXTURE-NONEXECUTING-RUN')

    def test_generic_h1_reuse_retains_nonexecution_and_phase_inventory(self):
        plan = self.compile_plan()
        self.assertEqual(plan['status'],'compiled-not-executed')
        self.assertFalse(any(plan['boundaries'].values()))
        self.assertEqual({b['phase'] for b in plan['blocks']},{'pilot','confirmatory'})
        self.assertEqual(sum(b['phase']=='pilot' for b in plan['blocks']),2)

    def test_h1_cannot_substitute_a_same_byte_case_closure_alias(self):
        alias = self.f.write('live/aliased-input-closure.json',self.f.case_closure)
        self.assertEqual(alias['sha256'],self.f.case_closure_ref['sha256'])
        with self.assertRaisesRegex(EvaluationValidationError,'exact scope input closure'):
            self.compile_plan(alias)

    def test_protocol_case_count_must_equal_unique_input_cases(self):
        self.protocol['design']['stopping'].update(case_count=3,completed_blocks=3)
        self.reject()

    def test_missing_changed_and_escaping_scope_references_stop_reads(self):
        original = copy.deepcopy(self.scope)
        for ref in [{'path':'absent.json','sha256':'0'*64},
                    {'path':'../outside.json','sha256':'0'*64},
                    {**original['provider_config_ref'],'sha256':'0'*64}]:
            with self.subTest(ref=ref):
                self.scope = copy.deepcopy(original)
                self.scope['provider_config_ref'] = ref
                self.reject()

    def test_callback_free_reader_does_not_claim_checkpoint_or_conformance_qualification(self):
        inputs = self.inputs()
        ref = self.write_protocol()
        doc = validate_protocol(inputs,ref)
        self.assertNotIn('authorization_ref',doc)
        self.assertNotIn('admission_verifier',vars(inputs))
        self.assertFalse(inputs.read(self.scope['provider_applicability_ref'])['qualified'])

    def test_history_and_reserve_must_fit_external_ceiling(self):
        original = copy.deepcopy(self.scope)
        for changes in [{'cumulative_token_limit':10000001},{'prior_tokens':9999999},
                        {'cumulative_token_limit':2000},{'max_request_input_tokens':500000}]:
            with self.subTest(changes=changes):
                self.scope = copy.deepcopy(original)
                self.scope['budget'].update(changes)
                self.reject()

    def test_attempt_call_full_pilot_and_shared_time_bounds(self):
        original = copy.deepcopy(self.scope)
        for changes in [{'max_attempts':7},{'max_provider_calls':7},{'max_provider_calls':25},
                        {'max_attempt_seconds':121},{'max_run_seconds':119}]:
            with self.subTest(changes=changes):
                self.scope = copy.deepcopy(original)
                self.scope['budget'].update(changes)
                self.reject()

    def test_no_automatic_retry_or_fallback(self):
        original = copy.deepcopy(self.scope)
        for key in ['automatic_retry','fallback']:
            self.scope = copy.deepcopy(original)
            self.scope['budget'][key] = True
            self.reject()
        self.scope = copy.deepcopy(original)
        self.protocol['design']['retry'].update(max_retries=1,eligible_failures=['provider-transient'])
        self.reject()

    def test_window_requires_evening_aware_nonregressing_sufficient_time(self):
        original = copy.deepcopy(self.scope)
        for changes in [{'not_before':'2026-09-11T09:59:00Z'},
                        {'not_after':'2026-09-12T01:00:00Z'},
                        {'not_after':'2026-09-11T10:01:00Z'},
                        {'not_before':'2026-09-11T18:00:00'},
                        {'not_after':'2026-09-11T09:00:00Z'}]:
            with self.subTest(changes=changes):
                self.scope = copy.deepcopy(original)
                self.scope['window'].update(changes)
                self.reject()

    def test_scope_and_protocol_freeze_must_precede_window(self):
        self.scope['frozen_at'] = '2026-09-11T00:00:01Z'
        self.reject()
        self.scope['frozen_at'] = AT
        self.protocol['frozen_at'] = '2026-09-11T10:01:00Z'
        self.reject()

    def test_missing_admission_closure_still_rejects_planning(self):
        self.protocol['admission_case_closure_ref'] = None
        self.reject()

    def test_output_cases_are_exact_and_aliases_finite(self):
        original = copy.deepcopy(self.scope)
        mutations = [lambda s:s['output_contract']['cases'].pop(),
            lambda s:s['output_contract']['cases'].append(copy.deepcopy(s['output_contract']['cases'][0])),
            lambda s:s['output_contract']['cases'][0].update(case_id='FOREIGN'),
            lambda s:s['output_contract']['cases'][0].update(claim_ids=['C01','C01']),
            lambda s:s['output_contract']['cases'][0].update(source_ids=['source-metadata']),
            lambda s:s['output_contract'].update(max_body_bytes=999999),
            lambda s:s['output_contract'].update(max_json_depth=6)]
        for mutation in mutations:
            with self.subTest(mutation=mutations.index(mutation)):
                self.scope = copy.deepcopy(original)
                mutation(self.scope)
                self.reject()

    def test_schema_rejects_grant_fields_source_duplicates_and_wrong_types(self):
        original = copy.deepcopy(self.scope)
        for changes in [{'authorization_ref':original['provider_config_ref']},
                        {'budget':{**original['budget'],'prior_tokens':False}},
                        {'boundaries':{**original['boundaries'],'execution_authority':True}},
                        {'source_artifact_refs':[original['source_artifact_refs'][0]]*2}]:
            with self.subTest(changes=changes):
                self.scope = copy.deepcopy(original)
                self.scope.update(changes)
                self.reject()

    def test_external_ceiling_is_required_and_positive(self):
        for value in [None,0,-1,True,1.5]:
            with self.subTest(value=value),self.assertRaises(EvaluationValidationError):
                LiveEvaluationInputs(self.f.root,ROOT/'schemas',cumulative_token_ceiling=value)

    def test_nonfinite_data_and_raw_values_are_not_diagnostics(self):
        original = copy.deepcopy(self.scope)
        for value in [float('nan'),float('inf')]:
            self.scope = copy.deepcopy(original)
            self.scope['budget']['prior_tokens'] = value
            with self.assertRaisesRegex(EvaluationValidationError,'finite JSON'):
                self.inputs().validate('evaluation_live_scope',self.scope)
        self.scope = copy.deepcopy(original)
        self.scope['budget']['prior_tokens'] = 'private-opaque-value'
        with self.assertRaises(EvaluationValidationError) as caught:
            self.inputs().validate('evaluation_live_scope',self.scope)
        self.assertNotIn('private-opaque-value',str(caught.exception))

    def test_scope_cannot_promote_run_phase(self):
        for phases in [['confirmatory'],['pilot','confirmatory'],[]]:
            with self.subTest(phases=phases):
                self.scope['execution_phase_allowlist'] = phases
                self.reject()

    def test_fresh_process_loads_opt_in_schema_and_hash_closure(self):
        ref = self.write_protocol()
        code = '''import sys
from research_workbench.evaluation.live_inputs import LiveEvaluationInputs
from research_workbench.evaluation.system_protocol import validate_protocol
doc=validate_protocol(LiveEvaluationInputs(sys.argv[1],sys.argv[2],cumulative_token_ceiling=10000000),{'path':sys.argv[3],'sha256':sys.argv[4]})
assert doc['purpose']=='live-pilot' and doc['version']=='2.0.0'
print('READ-ONLY-INPUT-CLOSURE')'''
        environment = dict(os.environ)
        environment['PYTHONPATH'] = str(ROOT/'src')
        result = subprocess.run([sys.executable,'-B','-c',code,str(self.f.root),str(ROOT/'schemas'),
                                 ref['path'],ref['sha256']],capture_output=True,text=True,
                                encoding='utf-8',env=environment,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'READ-ONLY-INPUT-CLOSURE')

    def test_cached_protocol_still_rechecks_scope_and_reference_bytes(self):
        inputs = self.inputs()
        ref = self.write_protocol()
        validate_protocol(inputs,ref)
        (self.f.root/self.scope['budget_checkpoint_ref']['path']).write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(EvaluationValidationError,'hash mismatch'):
            validate_protocol(inputs,ref)

    def test_new_schema_identity_is_namespaced_and_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            schemas = Path(d)/'schemas'
            shutil.copytree(ROOT/'schemas',schemas)
            inputs = LiveEvaluationInputs(self.f.root,schemas,cumulative_token_ceiling=10000000)
            ref = self.write_protocol()
            validate_protocol(inputs,ref)
            identity = inputs.schema_identity()
            self.assertIn('v0.1.0/system-evaluation-protocol.schema.json',identity)
            self.assertIn('v0.2.0/system-evaluation-protocol.schema.json',identity)
            (schemas/'v0.2.0/evaluation-live-scope.schema.json').write_text('{}',encoding='utf-8')
            with self.assertRaisesRegex(EvaluationValidationError,'live Schema bytes'):
                inputs.recheck()


if __name__ == '__main__':
    unittest.main()
