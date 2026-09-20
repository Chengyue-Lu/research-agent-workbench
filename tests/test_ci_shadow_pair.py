"""Paired observations require separate executions and preserve actual quality gates."""
import copy
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import runpy
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'.github/scripts'))
import ci_consumer_shadow as shadow
import ci_shadow_pair as pair
from tests.test_ci_consumer_shadow import A, B, inputs
from tests.test_ci_checks import policy as coverage_policy, coverage as coverage_data, MODULE


def example(measure=False):
    plan, inventory, receipt, proposed = inputs(False)
    plan.update(coverage_scope='impact' if measure else 'none', coverage_modules=[MODULE] if measure else [],
                coverage_obligations=['impact'] if measure else [], coverage_lines={MODULE:[1]},
                impact_evidence={'positive_tests':['test_reader.C.test_a'], 'negative_tests':['test_reader.C.test_b']},
                package_smoke=False, repository_smoke=False)
    if measure:
        inventory['coverage_order'] = [A, B]
        receipt.update(suite='coverage-execution', coverage_obligations=['impact'])
        receipt['execution']['coverage_order'] = [A, B]
        proposed['execution_order'] = [A, B]
    proposed.update(behavioral_order=[A], coverage_order=inventory['coverage_order'])
    receipt['wall_seconds'] = 10.0
    policy = coverage_policy()
    policy['negative_acceptance'][0].update(positive_tests=['test_reader.C.test_a'], negative_tests=['test_reader.C.test_b'])
    environment={'python_version':inventory['python_version'],'platform':'test-os','machine':'x86_64',
                 'dependencies_sha256':'a'*64,'runner_sha256':'b'*64,'coverage_config_sha256':'c'*64,
                 'invocation_context_sha256':'d'*64}
    accepted={'version':1,'role':'accepted','run_id':'A','environment':environment,'receipt':receipt,
              'driver':{'sha256':'e'*64,'invocation':['python','experiment.py','--role','accepted']},
              'coverage':coverage_data() if measure else None,'coverage_binding':None,'smokes':{}}
    candidate=copy.deepcopy(accepted)
    candidate.update(role='candidate',run_id='B')
    candidate['driver']['invocation'][-1]='candidate'
    candidate['receipt'].update(suite='shadow-candidate',wall_seconds=6.0,execution_order=proposed['execution_order'])
    candidate['receipt']['tests']=[row for row in candidate['receipt']['tests'] if row['canonical_id'] in proposed['execution_order']]
    candidate['receipt']['test_count']=len(candidate['receipt']['tests'])
    candidate['receipt']['execution']['behavioral_order']=[A]
    for bundle in (accepted,candidate):bind_coverage(plan,bundle)
    comparison=shadow.compare_receipt(plan,inventory,proposed,receipt)
    report={'report_id':'report','candidate':proposed,'comparison':comparison,'behavioral_skips':[B],
            'effective_execution_skips':[] if measure else [B], 'moved_to_coverage_phase':[B] if measure else []}
    return plan,inventory,policy,report,accepted,candidate


def bind_coverage(plan,bundle):
    if bundle['coverage'] is not None:
        bundle['coverage_binding']={'plan_id':plan['plan_id'],'target':plan['binding']['target'],'run_id':bundle['run_id'],
                                    'receipt_sha256':pair.planner.digest(bundle['receipt']),
                                    'coverage_sha256':pair.planner.digest(bundle['coverage'])}


class PairedExecutionTests(unittest.TestCase):
    def test_cli_binds_real_git_producers_and_keeps_input_files_read_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo=Path(temporary)
            def git(*args):
                return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE).decode().strip()
            def write(path,data):
                file=repo/path;file.parent.mkdir(parents=True,exist_ok=True)
                file.write_bytes(data.encode() if isinstance(data,str) else data)
            git('init','-q','-b','develop');git('config','user.name','CI fixture');git('config','user.email','fixture@example.invalid')
            git('config','core.autocrlf','false')
            for path in (*pair.planner.TRUST_FILES,'.github/scripts/check_coverage_policy.py'):
                write(path,(ROOT/path).read_bytes())
            write('tests/test_reader.py','import unittest\nclass C(unittest.TestCase):\n def test_a(self): pass\n def test_b(self): pass\n')
            write('docs/note.md','original\n')
            git('add','.');git('commit','-qm','base');base=git('rev-parse','HEAD')
            write('docs/note.md','changed\n');git('add','docs/note.md');git('commit','-qm','document');head=git('rev-parse','HEAD')
            plan=pair.planner.make_plan(repo,base=base,head=head,target=head,repository='Example/repo')
            _,inventory,_,_,a,b=example(True)
            inventory.update(plan_id=plan['plan_id'],target=head)
            proposal={'version':1,'execution_authority':False,'baseline':base,'consumers':[]}
            for bundle in (a,b):
                bundle['receipt'].update(plan_id=plan['plan_id'],target=head,coverage_obligations=plan['coverage_obligations'])
                bundle['receipt']['execution']['behavioral_order']=inventory['behavioral_order']
                bundle.update(coverage=None,coverage_binding=None)
                bundle['environment']['runner_sha256']=hashlib.sha256((repo/'tests/run_unittest_suite.py').read_bytes()).hexdigest()
            b['receipt']['suite']='coverage-execution' # unchanged candidate uses native CLI
            report=pair.build_report(repo,plan,proposal,inventory,a,b)
            self.assertEqual('inconclusive',report['pair_status'])
            self.assertEqual('missing',report['coverage']['candidate']['status'])
            self.assertFalse(report['activation']['eligible'])
            signature=report.pop('report_id');self.assertEqual(signature,pair.planner.digest(report))
            values={'plan':plan,'proposal':proposal,'inventory':inventory,'accepted':a,'candidate':b}
            args=['--repo',str(repo)]
            for name,value in values.items():
                write(name+'.json',pair.planner.canonical(value));args += ['--'+name,str(repo/(name+'.json'))]
            args += ['--output',str(repo/'report.json')]
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(0,pair.main(args))
            with self.assertRaisesRegex(ValueError,'overwrite'):pair.main([*args[:-1],str(repo/'plan.json')])
            saved=sys.argv
            try:
                sys.argv=['ci_shadow_pair',*args]
                with contextlib.redirect_stdout(io.StringIO()),self.assertRaises(SystemExit) as stopped:
                    runpy.run_path(str(ROOT/'.github/scripts/ci_shadow_pair.py'),run_name='__main__')
                self.assertEqual(0,stopped.exception.code)
            finally:sys.argv=saved
            b['environment']['runner_sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'runner pin'):pair.build_report(repo,plan,proposal,inventory,a,b)

    def test_real_fixture_phase_move_fails_even_with_complete_line_and_branch_coverage(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo=Path(temporary)
            (repo/'tests').mkdir();(repo/'src/research_workbench').mkdir(parents=True)
            (repo/'tests/__init__.py').write_text('')
            (repo/'src/research_workbench/__init__.py').write_text('')
            shutil.copyfile(ROOT/'tests/run_unittest_suite.py',repo/'tests/run_unittest_suite.py')
            (repo/MODULE).write_text('def classify(value):\n    if value:\n        return "yes"\n    return "no"\n')
            (repo/'tests/test_lifecycle.py').write_text('import unittest\nfrom research_workbench.example import classify\n'
                'class C(unittest.TestCase):\n @classmethod\n def setUpClass(cls): cls.count=0\n'
                ' def test_a(self):\n  self.assertEqual(classify(True),"yes")\n  type(self).count+=1\n'
                ' def test_b(self):\n  self.assertEqual(classify(False),"no")\n  self.assertEqual(type(self).count,1)\n')
            plan,_,policy,_,a,b=example(True)
            ids=['tests/test_lifecycle.py::C.test_a','tests/test_lifecycle.py::C.test_b']
            aliases=dict(zip(ids,['test_lifecycle.C.test_a','test_lifecycle.C.test_b']))
            inventory={'version':1,'scope':'plan-collection','plan_id':'p','target':'t','source':'fresh experiment collection',
                       'python_version':a['environment']['python_version'],'behavioral_order':ids,'coverage_order':ids,'runtime_ids':aliases}
            plan['impact_evidence']={'positive_tests':[aliases[ids[0]]],'negative_tests':[aliases[ids[1]]]}
            plan['coverage_lines']={MODULE:[1,2,3,4]}
            policy['negative_acceptance'][0].update(**plan['impact_evidence'])
            (repo/'plan.json').write_text(json.dumps(plan))
            (repo/'experiment.py').write_text('import json,sys,time,unittest\nfrom pathlib import Path\n'
                'sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/"src"),str(Path.cwd()/"tests")]\n'
                'from tests import run_unittest_suite as r\n'
                'role=sys.argv[1]; names=["test_lifecycle.C.test_a","test_lifecycle.C.test_b"]\n'
                'loader=unittest.TestLoader()\n'
                'suite=r.OrderedCoverageExecution(loader.loadTestsFromNames(names if role=="accepted" else names[:1]),'
                'lambda:loader.loadTestsFromNames(names))\n'
                'start=time.perf_counter();result=unittest.TextTestRunner(resultclass=r.TimedTextResult).run(suite)\n'
                'r._write_summary(Path(role+".json"),"coverage-execution" if role=="accepted" else "shadow-candidate",'
                'time.perf_counter()-start,result,2,json.loads(Path("plan.json").read_text()),suite.contract())\n'
                'sys.exit(not result.wasSuccessful())\n')
            for role,bundle in [('accepted',a),('candidate',b)]:
                env={**os.environ,'PYTHONPATH':str(repo/'src')+';'+str(repo),
                     'COVERAGE_FILE':str(repo/(role+'.coverage')),'PYTHONUTF8':'1'}
                process=subprocess.run([sys.executable,'-m','coverage','run','--branch','--source=src/research_workbench',
                                        'experiment.py',role],cwd=repo,env=env,capture_output=True)
                self.assertEqual(0 if role=='accepted' else 1,process.returncode,process.stderr.decode(errors='replace'))
                subprocess.run([sys.executable,'-m','coverage','json','-o',role+'-coverage.json'],cwd=repo,env=env,
                               check=True,capture_output=True)
                bundle['receipt']=json.loads((repo/(role+'.json')).read_bytes())
                inventory['python_version']=bundle['receipt']['python_version']
                bundle['environment']['python_version']=inventory['python_version']
                bundle['coverage']=json.loads((repo/(role+'-coverage.json')).read_bytes())
                bundle['coverage']['files']={path.replace('\\','/'):value for path,value in bundle['coverage']['files'].items()}
                bind_coverage(plan,bundle)
                self.assertEqual([],bundle['coverage']['files'][MODULE]['missing_lines'])
                self.assertEqual([],bundle['coverage']['files'][MODULE]['missing_branches'])
            proposed={'behavioral_order':ids[:1],'coverage_order':ids,'execution_order':ids}
            report={'report_id':'real-lifecycle','candidate':proposed,'comparison':shadow.compare_receipt(plan,inventory,proposed,a['receipt']),
                    'behavioral_skips':ids[1:],'effective_execution_skips':[],'moved_to_coverage_phase':ids[1:]}
            result=pair.compare_pair(plan,report,inventory,policy,a,b)
            self.assertEqual('inconclusive',result['pair_status'])
            self.assertEqual('observed-pass',result['coverage']['accepted']['status'])
            self.assertEqual('inconclusive',result['coverage']['candidate']['status'])
            self.assertEqual(ids[1:],result['candidate_execution']['failing_ids'])

    def test_actual_wall_pair_keeps_coverage_and_distinguishes_phase_movement(self):
        for measure in (False,True):
            plan,inventory,policy,report,a,b=example(measure)
            result=pair.compare_pair(plan,report,inventory,policy,a,b)
            self.assertEqual('observed-matching-pair',result['pair_status'])
            self.assertEqual(4,result['timing']['difference_seconds'])
            self.assertEqual(40,result['timing']['difference_percent'])
            self.assertFalse(result['savings_proved'])
            self.assertFalse(result['activation']['eligible'])
            self.assertEqual('observed-pass' if measure else 'not-required',result['coverage']['candidate']['status'])
            self.assertEqual([B] if measure else [],result['moved_to_coverage_phase'])
            self.assertEqual([] if measure else [B],result['effective_execution_skips'])

    def test_binding_identity_environment_and_coverage_association_are_checked(self):
        plan,inventory,policy,report,a,b=example(True)
        mutations=[lambda r:r.update(role='accepted'),lambda r:r.update(run_id='A'),
                   lambda r:r['environment'].update(platform='other'),lambda r:r['environment'].update(python_version='3.13.1'),
                   lambda r:r['environment'].update(runner_sha256='bad'),lambda r:r['receipt'].update(target='old'),
                   lambda r:r['receipt'].update(wall_seconds=float('nan')),lambda r:r['receipt'].update(suite='coverage-execution'),
                   lambda r:r['coverage_binding'].update(run_id='old'),lambda r:r['coverage'].update(meta={}),
                   lambda r:r.update(coverage=None),lambda r:r.update(smokes={'unrecognized':{}}),
                   lambda r:r.update(smokes={'package_smoke':{'target':'old'}})]
        for mutation in mutations:
            broken=copy.deepcopy(b);mutation(broken)
            with self.subTest(bundle=broken),self.assertRaises(ValueError):
                pair.compare_pair(plan,report,inventory,policy,a,broken)
        broken=copy.deepcopy(b);broken['receipt']=copy.deepcopy(a['receipt']);bind_coverage(plan,broken)
        with self.assertRaisesRegex(ValueError,'same execution'):
            pair.compare_pair(plan,report,inventory,policy,a,broken)
        b['driver']['sha256']='f'*64
        self.assertEqual('inconclusive',pair.compare_pair(plan,report,inventory,policy,a,b)['pair_status'])
        b['driver']['invocation']=[]
        with self.assertRaisesRegex(ValueError,'driver'):
            pair.compare_pair(plan,report,inventory,policy,a,b)

    def test_role_only_invocations_and_smoke_membership_cannot_hide_other_execution(self):
        plan,inventory,policy,report,a,b=example(False)
        for argv in ([*b['driver']['invocation'],'--fixtures','cached-success'],
                     ['python','experiment.py','candidate','--role','candidate'],
                     ['python','other.py','candidate'],['python','experiment.py','accepted','extra']):
            broken=copy.deepcopy(b);broken['driver']['invocation']=argv
            with self.subTest(argv=argv):
                self.assertEqual('inconclusive',pair.compare_pair(plan,report,inventory,policy,a,broken)['pair_status'])
        for left,right in ((['accepted','x'],['candidate','x']),
                           (['python','accepted'],['python','candidate']),
                           (['python','experiment.py','accepted'],['python','experiment.py','candidate']),
                           (['python','experiment.py','--input','accepted'],['python','experiment.py','--input','candidate']),
                           (['python','experiment.py','--role','accepted','--role','fixed'],
                            ['python','experiment.py','--role','candidate','--role','fixed']),
                           (['python','experiment.py','--role','accepted'],['python','experiment.py','--role','other'])):
            original,broken=copy.deepcopy(a),copy.deepcopy(b)
            original['driver']['invocation']=left;broken['driver']['invocation']=right
            with self.subTest(left=left,right=right):
                self.assertEqual('inconclusive',pair.compare_pair(plan,report,inventory,policy,original,broken)['pair_status'])
        b['driver']['invocation']=a['driver']['invocation'][:]
        self.assertEqual('observed-matching-pair',pair.compare_pair(plan,report,inventory,policy,a,b)['pair_status'])
        plan['package_smoke']=True
        for bundle in (a,b):
            bundle['smokes']['package_smoke']={'plan_id':'p','target':'t','run_id':bundle['run_id'],
                'execution_receipt_sha256':pair.planner.digest(bundle['receipt']),
                'artifact_sha256':'a'*64,
                'conclusion':'success','source':bundle['run_id']+' original smoke log'}
        self.assertEqual('observed-matching-pair',pair.compare_pair(plan,report,inventory,policy,a,b)['pair_status'])
        b['smokes']=copy.deepcopy(a['smokes'])
        with self.assertRaisesRegex(ValueError,'smoke artifact binding'):
            pair.compare_pair(plan,report,inventory,policy,a,b)
        b['smokes']['package_smoke']['run_id']=b['run_id']
        with self.assertRaisesRegex(ValueError,'smoke artifact binding'):
            pair.compare_pair(plan,report,inventory,policy,a,b)
        b['smokes']['package_smoke']['execution_receipt_sha256']=pair.planner.digest(b['receipt'])
        b['smokes']['package_smoke']['artifact_sha256']='invalid'
        with self.assertRaisesRegex(ValueError,'smoke artifact binding'):
            pair.compare_pair(plan,report,inventory,policy,a,b)

    def test_failed_skipped_missing_lifecycle_and_smoke_proofs_stay_inconclusive(self):
        plan,inventory,policy,report,a,b=example(True)
        mutations=[lambda r:r['receipt']['tests'][0].update(outcome='failed'),
                   lambda r:r['receipt']['tests'][0].update(checkpoints=[{'outcome':'skipped'}]),
                   lambda r:r['receipt'].update(execution_order=[B,A]),lambda r:r['receipt'].pop('execution'),
                   lambda r:r['receipt']['events'].update(errors=1),
                   lambda r:r['receipt']['events'].update(skips=1),
                   lambda r:r['coverage']['files'][MODULE].update(missing_lines=[1]),
                   lambda r:r['coverage']['files'][MODULE].update(missing_branches=[[1,-1]]),
                   lambda r:r['coverage'].update(files={})]
        for mutation in mutations:
            broken=copy.deepcopy(b);mutation(broken);bind_coverage(plan,broken)
            with self.subTest(bundle=broken):
                self.assertEqual('inconclusive',pair.compare_pair(plan,report,inventory,policy,a,broken)['pair_status'])
        b.update(coverage=None,coverage_binding=None)
        self.assertEqual('missing',pair.compare_pair(plan,report,inventory,policy,a,b)['coverage']['candidate']['status'])
        plan,inventory,policy,report,a,b=example(False)
        plan['package_smoke']=True
        plan['repository_smoke']=True
        a['smokes']['package_smoke']={'plan_id':'p','target':'t','run_id':'A',
            'execution_receipt_sha256':pair.planner.digest(a['receipt']),'artifact_sha256':'a'*64,
            'conclusion':'success','source':'retained job log'}
        a['smokes']['repository_smoke']=copy.deepcopy(a['smokes']['package_smoke'])
        for status in ('missing','failure','cancelled','skipped'):
            b['smokes']['package_smoke']={'plan_id':'p','target':'t','run_id':'B',
                'execution_receipt_sha256':pair.planner.digest(b['receipt']),'artifact_sha256':'b'*64,
                'conclusion':status,'source':'retained candidate log'}
            b['smokes']['repository_smoke']=copy.deepcopy(b['smokes']['package_smoke'])
            self.assertEqual('inconclusive',pair.compare_pair(plan,report,inventory,policy,a,b)['pair_status'])
        b['smokes']['package_smoke']['conclusion']='success'
        self.assertEqual('inconclusive',pair.compare_pair(plan,report,inventory,policy,a,b)['pair_status'])
        b['smokes']['repository_smoke']['conclusion']='success'
        self.assertEqual('observed-matching-pair',pair.compare_pair(plan,report,inventory,policy,a,b)['pair_status'])
        a['receipt']['wall_seconds']=0
        a['smokes']['package_smoke']['execution_receipt_sha256']=pair.planner.digest(a['receipt'])
        a['smokes']['repository_smoke']['execution_receipt_sha256']=pair.planner.digest(a['receipt'])
        self.assertIsNone(pair.compare_pair(plan,report,inventory,policy,a,b)['timing']['difference_percent'])

    def test_repository_thresholds_and_acceptance_mapping_are_still_enforced(self):
        plan,inventory,policy,report,a,b=example(True)
        plan['coverage_obligations']=['impact','repository']
        plan['coverage_scope']='impact+repository'
        for bundle in (a,b):
            bundle['receipt']['coverage_obligations']=plan['coverage_obligations'];bind_coverage(plan,bundle)
        self.assertEqual('observed-matching-pair',pair.compare_pair(plan,report,inventory,policy,a,b)['pair_status'])
        b['coverage']['files'][MODULE]['summary']['covered_lines']=89
        bind_coverage(plan,b)
        self.assertEqual('failed',pair.compare_pair(plan,report,inventory,policy,a,b)['coverage']['candidate']['status'])
        plan['coverage_obligations']=['repository']
        plan['coverage_scope']='repository'
        for bundle in (a,b):
            bundle['receipt']['coverage_obligations']=['repository'];bind_coverage(plan,bundle)
        self.assertEqual('failed',pair.compare_pair(plan,report,inventory,policy,a,b)['coverage']['candidate']['status'])
        policy['thresholds']['global']['line']=85
        self.assertEqual('failed',pair.compare_pair(plan,report,inventory,policy,a,b)['coverage']['accepted']['status'])


if __name__=='__main__':unittest.main()
