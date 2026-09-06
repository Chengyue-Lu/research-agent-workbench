from __future__ import annotations

import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import yaml
from coverage import Coverage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import ci_checks as checks
import plan_ci as planner
from tests import run_unittest_suite as runner

MODULE = 'src/research_workbench/example.py'
POS = 'test_example.Example.test_positive'
NEG = 'test_example.Example.test_negative'


def plan(level='focused'):
    p = {'version': 1, 'binding': {'repository':'Example/repo','base':'a'*40,'head':'b'*40,
         'merge_base':'a'*40,'target':'c'*40}, 'change_class':level, 'risk':'R1', 'changes':[], 'surfaces':[],
         'test_groups':['example'], 'tests':['test_example'], 'coverage_modules':[MODULE],
         'impact_evidence':{'positive_tests':[POS],'negative_tests':[NEG]}, 'changed_lines':{MODULE:[1]},
         'coverage_lines':{MODULE:[1]},
         'policy_sha256':'d'*64,'python_versions':['3.11','3.13'], 'coverage_mode':'impact',
         'package_smoke':False,'repository_smoke':False,'reasons':[]}
    if level == 'full': p.update(coverage_mode='repository',package_smoke=True,repository_smoke=True)
    if level == 'fast': p.update(coverage_mode='none',coverage_modules=[],changed_lines={},coverage_lines={},python_versions=[],impact_evidence={})
    return signed(p)


def signed(p):
    p['plan_id'] = planner.digest({k:v for k,v in p.items() if k != 'plan_id'})
    return p


def policy():
    return {'source_root':'src/research_workbench','thresholds':{'global':{'line':90},
        'critical':{'line':95,'branch':90},'impact':{'line':100,'branch':100}},
        'critical_modules':[MODULE],'justified_exclusions':[],
        'negative_acceptance':[{'surface':'example','modules':[MODULE],'positive_tests':[POS],'negative_tests':[NEG]}]}


def coverage():
    return {'meta':{'branch_coverage':True},'files':{MODULE:{'excluded_lines':[], 'executed_lines':[1],
        'missing_lines':[2], 'executed_branches':[[1,-1]],'missing_branches':[[2,-1]],
        'summary':{'num_statements':100,'covered_lines':95,'num_branches':100,'covered_branches':90}}}}


def results(p):
    return {'suite':'focused','successful':True,'test_count':2,'plan_id':p['plan_id'],'target':p['binding']['target'],
            'tests':[{'id':name,'outcome':'passed'} for name in (POS,NEG)]}


class ImpactCoverageTests(unittest.TestCase):
    def test_multiline_condition_uses_real_coverage_branch_origins(self):
        source = 'def decide(enabled, count):\n    if (\n        enabled and count >= 0\n    ):\n        return True\n    return False\n'
        p = plan(); p['changed_lines'] = {MODULE: [3]}
        with patch.object(planner, 'read_at', return_value=source.encode()):
            p['coverage_lines'] = planner.coverage_lines(None, 'head', p['changed_lines'])
        self.assertIn(2, p['coverage_lines'][MODULE])
        signed(p); pol = policy(); pol['critical_modules'] = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / 'example.py'; path.write_text(source, encoding='utf-8')
            for both_paths in (False, True):
                measured = Coverage(branch=True, source=[str(root)], config_file=False, data_file=None)
                measured.start()
                namespace = {}; exec(compile(source, str(path), 'exec'), namespace)
                self.assertTrue(namespace['decide'](True, 0))
                if both_paths:
                    self.assertFalse(namespace['decide'](False, 0))
                measured.stop(); measured.json_report(outfile=str(root / 'coverage.json'))
                report = json.loads((root / 'coverage.json').read_bytes())
                report['files'] = {MODULE: next(iter(report['files'].values()))}
                if both_paths:
                    self.assertEqual([], report['files'][MODULE]['missing_branches'])
                    checks.impact_coverage(p, pol, report, results(p))
                else:
                    self.assertIn([2, 6], report['files'][MODULE]['missing_branches'])
                    with self.assertRaisesRegex(ValueError, 'uncovered changed branches'):
                        checks.impact_coverage(p, pol, report, results(p))

    def test_impact_preserves_critical_floor_and_distinguishes_global(self):
        p=plan()
        result=checks.impact_coverage(p,policy(),coverage(),results(p))
        self.assertFalse(result['repository_coverage_proved'])
        self.assertEqual([MODULE],result['modules'])

    def test_ordinary_files_require_changed_lines_and_branches_not_global(self):
        p=plan(); pol=policy(); cov=coverage(); pol['critical_modules']=[]
        cov['files'][MODULE]['summary']['covered_lines']=20
        self.assertFalse(checks.impact_coverage(p,pol,cov,results(p))['repository_coverage_proved'])

    def test_missing_wrong_and_lower_quality_evidence_is_rejected(self):
        cases=[('plan',lambda x:x.update(change_class='fast')),('plan',lambda x:x.update(coverage_modules=[])),
          ('results',lambda x:x.update(plan_id='wrong')),('results',lambda x:x.update(target='wrong')),
          ('results',lambda x:x.update(successful=False)),('results',lambda x:x.update(test_count=0)),
          ('results',lambda x:x['tests'].pop()),('results',lambda x:x['tests'][0].update(outcome='skipped')),
          ('policy',lambda x:x.update(source_root='src')),
          ('policy',lambda x:x['thresholds']['global'].update(line=89)),
          ('policy',lambda x:x['thresholds']['critical'].update(line=94)),
          ('policy',lambda x:x['thresholds']['critical'].update(branch=89)),
          ('policy',lambda x:x['thresholds']['impact'].update(line=99)),
          ('policy',lambda x:x['negative_acceptance'][0]['positive_tests'].append('missing')),
          ('coverage',lambda x:x['meta'].update(branch_coverage=False)),
          ('coverage',lambda x:x['files'].clear()),
          ('coverage',lambda x:x['files'][MODULE]['summary'].update(covered_lines=94)),
          ('coverage',lambda x:x['files'][MODULE]['summary'].update(covered_branches=89)),
          ('coverage',lambda x:x['files'][MODULE]['excluded_lines'].append(1)),
          ('coverage',lambda x:x['files'][MODULE]['missing_lines'].append(1)),
          ('coverage',lambda x:x['files'][MODULE]['missing_branches'].append([1,-1])),
          ('coverage',lambda x:x['files'][MODULE].pop('executed_branches')),
          ('plan',lambda x:x['impact_evidence'].update(negative_tests=[POS]))]
        for kind,mutate in cases:
            data={'plan':plan(),'policy':policy(),'coverage':coverage()}
            data['results']=results(data['plan']);mutate(data[kind])
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                checks.impact_coverage(**data)


class AggregateTests(unittest.TestCase):
    def test_all_three_levels_require_only_proven_obligations(self):
        for level in ('fast','focused','full'):
            p=plan(level)
            for python in ('3.11','3.13'):
                needed=checks.required_jobs(p,python)
                needs={n:{'result':'success'} for n in needed}
                self.assertEqual(sorted(needed),checks.aggregate(p,needs,python)['required_jobs'])
                for name in needed:
                    for state in ('skipped','cancelled','failure','timed_out',None):
                        bad=copy.deepcopy(needs);bad[name]['result']=state
                        with self.subTest(level=level,name=name,state=state),self.assertRaises(ValueError):
                            checks.aggregate(p,bad,python)

    def test_optional_skips_are_allowed_but_unknown_failures_are_not(self):
        p=plan('fast');needs={n:{'result':'success'} for n in checks.required_jobs(p,'3.11')}
        needs['coverage_quality']={'result':'skipped'}
        checks.aggregate(p,needs,'3.11')
        needs['coverage_quality']={'result':'cancelled'}
        with self.assertRaises(ValueError): checks.aggregate(p,needs,'3.11')
        needs['unknown']={'result':'success'}
        with self.assertRaises(ValueError): checks.aggregate(p,needs,'3.11')
        with self.assertRaises(ValueError): checks.required_jobs(p,'3.14')


class MetadataTests(unittest.TestCase):
    def test_same_binding_can_reuse_stronger_content_obligations(self):
        self.assertTrue(checks.covers(plan(),plan()))
        self.assertTrue(checks.covers(plan('full'),plan()))
        self.assertFalse(checks.covers(plan('fast'),plan()))
        self.assertFalse(checks.covers(plan(),plan('full')))

    def test_stale_binding_tamper_risk_or_weaker_obligations_cannot_reuse(self):
        for mutation in (lambda p:p.update(plan_id='wrong'),lambda p:p['binding'].update(head='a'*40),
             lambda p:p.update(policy_sha256='wrong'),lambda p:p.update(tests=[]),
             lambda p:p.update(impact_evidence={}),lambda p:p.update(change_class='unknown')):
            previous=plan();mutation(previous)
            if previous['plan_id']!='wrong':signed(previous)
            self.assertFalse(checks.covers(previous,plan()))
        current=plan();current['package_smoke']=True
        self.assertFalse(checks.covers(plan(),current))

    def test_metadata_accepts_only_matching_content_run_artifact(self):
        p=plan()
        rows=[{'head_sha':'wrong','path':'.github/workflows/ci.yml','status':'in_progress'},
              {'head_sha':'b'*40,'path':'.github/workflows/ci-governance.yml','status':'in_progress'},
              {'head_sha':'b'*40,'path':'.github/workflows/ci.yml','status':'completed','conclusion':'failure'},
              {'head_sha':'b'*40,'path':'.github/workflows/ci.yml','status':'in_progress','id':42}]
        def download(args,**kwargs):
            (Path(args[-1])/'ci-plan.json').write_bytes(planner.canonical(p))
            return subprocess.CompletedProcess(args,0)
        with patch.object(checks.subprocess,'check_output',return_value=json.dumps({'workflow_runs':rows}).encode()) as query,\
             patch.object(checks.subprocess,'run',side_effect=download):
            self.assertEqual(42,checks.metadata_continuity(p)['content_run'])
            self.assertIn('/actions/workflows/ci.yml/runs',query.call_args.args[0][2])

    def test_missing_or_failed_content_evidence_requires_rerun(self):
        row={'head_sha':'b'*40,'path':'.github/workflows/ci.yml','status':'completed','conclusion':'success','id':1}
        with patch.object(checks.subprocess,'check_output',return_value=json.dumps({'workflow_runs':[row]}).encode()),\
             patch.object(checks.subprocess,'run',return_value=subprocess.CompletedProcess([],1)):
            with self.assertRaisesRegex(ValueError,'matching content'):checks.metadata_continuity(plan())


class WorkflowTests(unittest.TestCase):
    def test_metadata_isolation_concurrency_and_fixed_gate_names(self):
        content=yaml.load((ROOT/'.github/workflows/ci.yml').read_bytes(),Loader=yaml.BaseLoader)
        governance=yaml.load((ROOT/'.github/workflows/ci-governance.yml').read_bytes(),Loader=yaml.BaseLoader)
        self.assertFalse(set(content['on']['pull_request']['types']) & planner.METADATA)
        self.assertTrue(planner.METADATA <= set(governance['on']['pull_request']['types']))
        self.assertNotEqual(content['concurrency']['group'],governance['concurrency']['group'])
        self.assertIn('push',content['concurrency']['cancel-in-progress'])
        self.assertEqual('true',governance['concurrency']['cancel-in-progress'])
        self.assertEqual({'main','develop'},set(content['on']['push']['branches']))
        self.assertNotIn('governance',content['jobs'])
        self.assertIn('governance',governance['jobs'])
        self.assertEqual('read',content['permissions']['pull-requests'])
        for suffix,python in [('311','3.11'),('313','3.13')]:
            job=content['jobs']['required_test_'+suffix]
            self.assertEqual('test ('+python+')',job['name'])
            self.assertIn('always()',job['if'])
            self.assertIn('documentation',job['needs'])


class EntryPointTests(unittest.TestCase):
    def test_cli_aggregate_metadata_and_impact_route_through_plan_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=plan();(root/'plan.json').write_bytes(planner.canonical(p))
            (root/'coverage.json').write_bytes(planner.canonical(coverage()))
            (root/'results.json').write_bytes(planner.canonical(results(p)))
            (root/'tests').mkdir();(root/'tests/coverage_policy.yaml').write_text(yaml.safe_dump(policy()))
            with patch.object(checks,'verify_plan') as verify, patch.object(checks,'metadata_continuity',return_value={}),\
                 patch.object(checks,'aggregate',return_value={}),patch.object(checks,'impact_coverage',return_value={}),\
                 patch.object(checks,'ROOT',root),patch.dict(os.environ,{'CI_NEEDS':'{}'},clear=True),redirect_stdout(io.StringIO()):
                for operation in ('aggregate','metadata','impact'):
                    self.assertEqual(0,checks.main([operation,'--plan',str(root/'plan.json'),'--python','3.11',
                        '--coverage',str(root/'coverage.json'),'--results',str(root/'results.json')]))
                self.assertEqual(3,verify.call_count)


if __name__=='__main__':
    unittest.main()
