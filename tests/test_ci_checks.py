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
    p = {'version': 4, 'selection': {}, 'binding': {'repository':'Example/repo','base':'a'*40,'head':'b'*40,
         'merge_base':'a'*40,'target':'c'*40}, 'change_class':level, 'risk':'R1', 'changes':[], 'surfaces':[],
         'test_groups':['example'], 'tests':['test_example'], 'coverage_modules':[MODULE],
         'impact_evidence':{'positive_tests':[POS],'negative_tests':[NEG]}, 'changed_lines':{MODULE:[1]},
         'coverage_lines':{MODULE:[1]}, 'coverage_tests':['test_example'],
         'behavioral_scope': {'fast':'none','focused':'focused','full':'full'}[level], 'obligation_reasons':{},
         'policy_sha256':'d'*64,'python_versions':['3.11','3.13'], 'coverage_scope':'impact',
         'package_smoke':False,'repository_smoke':False,'reasons':[], 'blocked_reasons':[]}
    if level == 'full': p.update(coverage_scope='repository',package_smoke=True,repository_smoke=True)
    if level == 'fast': p.update(coverage_scope='none',coverage_modules=[],changed_lines={},coverage_lines={},python_versions=[],impact_evidence={})
    p['coverage_obligations'] = [] if p['coverage_scope'] == 'none' else [p['coverage_scope']]
    return signed(p)


def signed(p):
    p['plan_id'] = planner.digest({k:v for k,v in p.items() if k != 'plan_id'})
    return p


class CollectionTests(unittest.TestCase):
    def test_sources_retain_canonical_roots_and_cover_external_subject_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ('src/research_workbench/unexecuted.py', 'tests/test_unrelated.py', 'tests/run_unittest_suite.py',
                         'build_backend.py', 'work/task/checks/oracle.py', 'work/task/checks/unrelated.py'):
                target = root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_text('VALUE=1\n')
            config = checks.coverage_config({'coverage_modules': ['build_backend.py', 'work/task/checks/oracle.py']}, root)
            for path in ('src/research_workbench', 'build_backend.py', 'work/task/checks/oracle.py', 'tests/run_unittest_suite.py'):
                self.assertNotIn('    ' + path, config.split('omit =')[1])
            self.assertIn('    tests/test_unrelated.py', config)
            self.assertIn('    work/task/checks/unrelated.py', config)
        for path in ('../outside.py', '/outside.py', 'C:/outside.py', 'a\\b.py', 'bad,name.py',
                     'bad[name].py', 'bad\nname.py', 'bad\rname.py', 'a//b.py', 'data.json'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                checks.coverage_config({'coverage_modules': [path]}, ROOT)

    def test_root_backend_loaded_by_file_alias_is_actually_measured(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'build_backend.py').write_text('def calculate(value):\n    return value + 1\n', encoding='utf-8')
            (root / 'src/research_workbench').mkdir(parents=True)
            (root / 'src/research_workbench/unexecuted.py').write_text('VALUE=1\n')
            (root / 'probe.py').write_text(
                'import importlib.util\n'
                'spec=importlib.util.spec_from_file_location("backend_alias","build_backend.py")\n'
                'module=importlib.util.module_from_spec(spec)\nspec.loader.exec_module(module)\n'
                'assert module.calculate(1)==2\n', encoding='utf-8')
            (root / 'coverage.ini').write_text(checks.coverage_config({'coverage_modules': ['build_backend.py']}, root))
            result = subprocess.run([sys.executable, '-m', 'coverage', 'run', '--rcfile=coverage.ini', 'probe.py'],
                                    cwd=root, capture_output=True)
            self.assertEqual(0, result.returncode, result.stderr.decode(errors='replace'))
            subprocess.run([sys.executable, '-m', 'coverage', 'json', '--rcfile=coverage.ini', '-o', 'coverage.json'], cwd=root,
                           capture_output=True, check=True)
            measured = {p.replace('\\', '/'): value for p, value in json.loads((root / 'coverage.json').read_text())['files'].items()}
            item = measured['build_backend.py']
            self.assertEqual([], item['missing_lines'])
            self.assertEqual([1, 2], item['executed_lines'])
            self.assertEqual([1], measured['src/research_workbench/unexecuted.py']['missing_lines'])
            self.assertNotIn('probe.py', measured)

    def test_collector_rejects_unrepresentable_filters_and_aliased_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            odd = root / 'ambiguous[name].py'; odd.write_text('VALUE=1\n')
            with self.assertRaisesRegex(ValueError, 'filter path'):
                checks.coverage_config({'coverage_modules': []}, root)
            odd.unlink()
            blocked = root / 'src'; blocked.write_text('not a directory')
            with self.assertRaisesRegex(ValueError, 'ancestor'):
                checks.coverage_config({'coverage_modules': []}, root)
            blocked.unlink(); (root / 'src/research_workbench').mkdir(parents=True)
            with patch.object(Path, 'is_symlink', return_value=True), self.assertRaises(ValueError):
                checks.coverage_config({'coverage_modules': []}, root)
            (root / 'build_backend.py').write_text('VALUE=1\n')
            with patch.object(Path, 'is_symlink', side_effect=lambda: True), self.assertRaises(ValueError):
                checks.coverage_config({'coverage_modules': ['build_backend.py']}, root)


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
    return {'suite':'coverage-quality' if 'repository' in p['coverage_obligations'] else 'impact',
            'coverage_obligations':p['coverage_obligations'],
            'successful':True,'test_count':2,'plan_id':p['plan_id'],'target':p['binding']['target'],
            'tests':[{'id':name,'outcome':'passed'} for name in (POS,NEG)]}


class ImpactCoverageTests(unittest.TestCase):
    def test_workflow_measurement_includes_the_executing_runner(self):
        import shlex
        workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_bytes())
        step = next(s for s in workflow['jobs']['coverage_quality']['steps'] if s.get('name') == 'Run required coverage test union')
        command = shlex.split(step['run'].splitlines()[-1])
        command[0] = sys.executable
        with tempfile.TemporaryDirectory() as directory:
            env = {**os.environ, 'COVERAGE_FILE': str(Path(directory) / 'coverage-data')}
            config = Path(directory) / 'coverage.ini'
            config.write_text(checks.coverage_config({'coverage_modules': []}, ROOT))
            command[command.index('--rcfile=.rwb/ci-coverage.ini')] = '--rcfile=' + str(config)
            subprocess.run(command[:command.index('--suite')] + ['--help'], cwd=ROOT, env=env, check=True, capture_output=True)
            output = Path(directory) / 'coverage.json'
            subprocess.run([sys.executable, '-m', 'coverage', 'json', '--rcfile=' + str(config), '-o', str(output)], cwd=ROOT, env=env, check=True, capture_output=True)
            measured = json.loads(output.read_bytes())
            names = {p.replace('\\', '/') for p in measured['files']}
            self.assertIn('tests/run_unittest_suite.py', names)
            self.assertTrue(measured['meta']['branch_coverage'])

    def test_ordinary_impact_does_not_invent_critical_evidence_and_critical_cannot_drop_mapping(self):
        p, pol = plan(), policy()
        p['impact_evidence'] = {'positive_tests': [], 'negative_tests': []}
        pol['critical_modules'] = []
        pol['negative_acceptance'][0]['modules'] = ['another.py']
        signed(p)
        self.assertFalse(checks.impact_coverage(p, pol, coverage(), results(p))['repository_coverage_proved'])
        pol['critical_modules'] = [MODULE]
        p['impact_evidence'] = {'positive_tests': [POS], 'negative_tests': [NEG]}
        signed(p)
        with self.assertRaisesRegex(ValueError, 'critical acceptance mapping missing'):
            checks.impact_coverage(p, pol, coverage(), results(p))

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

    def test_repository_floor_does_not_cover_changed_line_or_branch_obligations(self):
        p = plan(); p.update(coverage_obligations=['impact', 'repository'], coverage_scope='impact+repository'); signed(p)
        checks.impact_coverage(p, policy(), coverage(), results(p))
        for key, missing in [('missing_lines', 1), ('missing_branches', [1, -1])]:
            cov = coverage()
            # Unchanged 95/90 whole-file totals do not prove 100/100 at changed statements.
            cov['files'][MODULE][key].append(missing)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'uncovered changed'):
                checks.impact_coverage(p, policy(), cov, results(p))
        evidence = results(p); evidence['coverage_obligations'] = ['repository']
        with self.assertRaises(ValueError): checks.impact_coverage(p, policy(), coverage(), evidence)

    def test_ordinary_files_require_changed_lines_and_branches_not_global(self):
        p=plan(); pol=policy(); cov=coverage(); pol['critical_modules']=[]
        cov['files'][MODULE]['summary']['covered_lines']=20
        self.assertFalse(checks.impact_coverage(p,pol,cov,results(p))['repository_coverage_proved'])

    def test_r2_full_behavior_retains_impact_thresholds_and_pass_evidence(self):
        p = plan(); p.update(risk='R2', behavioral_scope='full', change_class='full'); signed(p)
        checks.impact_coverage(p, policy(), coverage(), results(p))
        for line, branch in ((94, 90), (95, 89)):
            cov = coverage(); cov['files'][MODULE]['summary'].update(covered_lines=line, covered_branches=branch)
            with self.assertRaises(ValueError): checks.impact_coverage(p, policy(), cov, results(p))
        for index in (0, 1):
            evidence = results(p); evidence['tests'][index]['outcome'] = 'skipped'
            with self.assertRaises(ValueError): checks.impact_coverage(p, policy(), coverage(), evidence)

    def test_missing_wrong_and_lower_quality_evidence_is_rejected(self):
        cases=[('plan',lambda x:x.update(coverage_scope='none')),('plan',lambda x:x.update(coverage_modules=[])),
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
    def test_independent_obligations_and_required_coverage_failure_matrix(self):
        for scope in ('none', 'impact', 'repository', 'impact+repository'):
            p = plan('full'); p.update(coverage_scope=scope, package_smoke=False, repository_smoke=False)
            p['coverage_obligations'] = [] if scope == 'none' else scope.split('+')
            for python in ('3.11', '3.13'):
                required = checks.required_jobs(p, python)
                self.assertEqual(scope != 'none', 'coverage_quality' in required)
                self.assertNotIn('package_smoke', required)
                self.assertNotIn('repository_smoke', required)
                needs = {name: {'result': 'success'} for name in required}
                if scope == 'none': needs['coverage_quality'] = {'result': 'skipped'}
                checks.aggregate(p, needs, python)
                if scope != 'none':
                    for state in ('skipped', 'cancelled', 'failure', None):
                        bad = copy.deepcopy(needs)
                        if state is None: bad.pop('coverage_quality')
                        else: bad['coverage_quality']['result'] = state
                        with self.assertRaises(ValueError): checks.aggregate(p, bad, python)
        p['coverage_scope'] = 'unknown'
        with self.assertRaises(ValueError): checks.required_jobs(p, '3.11')

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
    def test_full_behavior_cannot_substitute_for_required_coverage_or_smokes(self):
        previous = plan('full'); previous.update(coverage_scope='none', package_smoke=False, repository_smoke=False); signed(previous)
        previous['coverage_obligations'] = []; signed(previous)
        current = copy.deepcopy(previous)
        self.assertTrue(checks.covers(previous, current))
        for key, value in [('coverage_scope', 'impact'), ('coverage_scope', 'repository'),
                           ('package_smoke', True), ('repository_smoke', True), ('risk', 'R2')]:
            current = copy.deepcopy(previous); current[key] = value
            if key == 'coverage_scope': current['coverage_obligations'] = [value]
            signed(current)
            self.assertFalse(checks.covers(previous, current))
        previous['version'] = 1; signed(previous)
        self.assertFalse(checks.covers(previous, plan()))

    def test_same_binding_can_reuse_stronger_content_obligations(self):
        self.assertTrue(checks.covers(plan(),plan()))
        self.assertFalse(checks.covers(plan('full'),plan()))
        previous = plan('full'); previous.update(coverage_obligations=['impact', 'repository'], coverage_scope='impact+repository'); signed(previous)
        self.assertTrue(checks.covers(previous, plan()))
        repository = plan('full')
        repository.update(coverage_modules=[], coverage_tests=[], coverage_lines={}, changed_lines={}, impact_evidence={}); signed(repository)
        self.assertTrue(checks.covers(previous, repository))
        self.assertTrue(checks.covers(previous, plan('fast')))
        for version in (1, 2):
            legacy = copy.deepcopy(previous); legacy['version'] = version; signed(legacy)
            self.assertFalse(checks.covers(legacy, plan()))
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
            self.assertIn('outputs.behavioral', content['jobs']['compatibility_' + suffix]['if'])
        self.assertIn('outputs.coverage', content['jobs']['coverage_quality']['if'])
        self.assertNotIn('outputs.class', (ROOT / '.github/workflows/ci.yml').read_text())
        self.assertIn('ci_checks.py configure --plan ci-plan.json',
                      (ROOT / '.github/workflows/ci.yml').read_text())
        self.assertIn('--rcfile=.rwb/ci-coverage.ini', (ROOT / '.github/workflows/ci.yml').read_text())
        self.assertIn('--suite coverage-plan', (ROOT / '.github/workflows/ci.yml').read_text())
        self.assertIn('ci_checks.py coverage --plan', (ROOT / '.github/workflows/ci.yml').read_text())


class EntryPointTests(unittest.TestCase):
    def test_coverage_entry_enforces_each_required_checker_and_propagates_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'tests').mkdir()
            (root / 'tests/coverage_policy.yaml').write_text(yaml.safe_dump(policy()))
            for obligations in (['impact'], ['repository'], ['impact', 'repository'], []):
                p = plan(); p.update(coverage_obligations=obligations, coverage_scope='+'.join(obligations) or 'none'); signed(p)
                for name, data in [('plan',p), ('coverage',coverage()), ('results',results(p))]:
                    (root / (name + '.json')).write_bytes(planner.canonical(data))
                args = ['coverage', '--plan', str(root / 'plan.json'), '--coverage', str(root / 'coverage.json'),
                        '--results', str(root / 'results.json')]
                with patch.object(checks, 'verify_plan') as verify, patch.object(checks, 'ROOT', root), \
                     patch.object(checks, 'impact_coverage', return_value={}) as impact, \
                     patch.object(checks.subprocess, 'run') as repository, \
                     patch.dict(os.environ, {}, clear=True), redirect_stdout(io.StringIO()):
                    if not obligations:
                        with self.assertRaises(ValueError): checks.main(args)
                        continue
                    self.assertEqual(0, checks.main(args))
                    verify.assert_called_once()
                    self.assertEqual('impact' in obligations, impact.called)
                    self.assertEqual('repository' in obligations, repository.called)
                    if repository.called:
                        self.assertTrue(repository.call_args.kwargs['check'])
                        repository.side_effect = subprocess.CalledProcessError(1, 'repository checker')
                        with self.assertRaises(subprocess.CalledProcessError): checks.main(args)
                    repository.reset_mock(); repository.side_effect = None
                    if 'impact' in obligations:
                        impact.side_effect = ValueError('changed branch missing')
                        with self.assertRaises(ValueError): checks.main(args)
                        repository.assert_not_called()

    def test_cli_aggregate_metadata_and_impact_route_through_plan_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=plan();(root/'plan.json').write_bytes(planner.canonical(p))
            (root/'coverage.json').write_bytes(planner.canonical(coverage()))
            (root/'results.json').write_bytes(planner.canonical(results(p)))
            (root/'tests').mkdir();(root/'tests/coverage_policy.yaml').write_text(yaml.safe_dump(policy()))
            with patch.object(checks,'verify_plan') as verify, patch.object(checks,'metadata_continuity',return_value={}),\
                 patch.object(checks,'aggregate',return_value={}),patch.object(checks,'impact_coverage',return_value={}),\
                 patch.object(checks,'ROOT',root),patch.dict(os.environ,{'CI_NEEDS':'{}'},clear=True),redirect_stdout(io.StringIO()):
                for operation in ('aggregate','metadata','impact','configure'):
                    self.assertEqual(0,checks.main([operation,'--plan',str(root/'plan.json'),'--python','3.11',
                        '--coverage',str(root/'coverage.json'),'--results',str(root/'results.json'), '--config', str(root/'coverage.ini')]))
                self.assertEqual(4,verify.call_count)
                with self.assertRaisesRegex(ValueError, 'configuration output'):
                    checks.main(['configure', '--plan', str(root/'plan.json')])
                p.update(coverage_obligations=[], coverage_scope='none')
                (root/'plan.json').write_bytes(planner.canonical(p))
                with self.assertRaisesRegex(ValueError, 'coverage obligations'):
                    checks.main(['configure', '--plan', str(root/'plan.json')])


if __name__=='__main__':
    unittest.main()
