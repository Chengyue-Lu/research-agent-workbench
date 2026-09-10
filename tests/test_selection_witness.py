from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import runpy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import selection_witness as w


class WitnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git('init', '-q'); self.git('config', 'user.name', 'witness fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.write('.github/scripts/plan_ci.py', b'RULE=True\n')
        self.write('.github/workflows/ci.yml', b'name: CI\njobs: {}\n')
        self.write('src/product.py', b'VALUE=1\n')
        self.base = self.commit()

    def git(self, *args):
        return w.git(self.repo, *args).decode().strip()

    def write(self, path, raw):
        p=self.repo/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(raw)

    def commit(self):
        self.git('add', '.'); self.git('commit', '-qm', 'fixture')
        return self.git('rev-parse', 'HEAD')

    def plan(self, head=None, scope='full'):
        head=head or self.git('rev-parse','HEAD')
        p={'version':4,'binding':dict(repository='Example/repo',base=self.base,head=head,
            merge_base=self.git('merge-base',self.base,head),target=head),
            'behavioral_scope':scope,'change_class':scope,'python_versions':['3.11','3.13']}
        return self.sign(p)

    def sign(self,p):
        p.pop('plan_id',None);p['plan_id']=hashlib.sha256(w.canonical(p)).hexdigest();return p

    def check(self,p):
        return w.witness(self.repo,'Example/repo',self.base,p['binding']['head'],p)

    def test_authority_floor_is_independent_of_plan_claims(self):
        self.write('.github/scripts/plan_ci.py',b'RULE=False\n'); self.commit()
        self.assertEqual('full',self.check(self.plan())['required_behavioral'])
        for scope in ('none','focused'):
            with self.subTest(scope=scope),self.assertRaisesRegex(ValueError,'requires FULL'):
                self.check(self.plan(scope=scope))
        p=self.plan();p['python_versions']=['3.11'];self.sign(p)
        with self.assertRaisesRegex(ValueError,'both Python'):self.check(p)

    def test_product_and_comments_do_not_acquire_full_floor(self):
        self.write('src/product.py',b'VALUE=2\n')
        self.write('.github/scripts/plan_ci.py',b'RULE = True # ordinary comment\n')
        self.write('.github/workflows/ci.yml',b'{name: CI, jobs: {}} # layout\n');self.commit()
        self.assertEqual('none',self.check(self.plan(scope='focused'))['required_behavioral'])
        self.assertIsNone(w.semantic('ci.yml',b'# empty\n'))

    def test_new_removed_modes_invalid_syntax_and_workflow_types_fail_closed(self):
        for path,raw in [('.github/scripts/ci_checks.py',b'pass\n'),('.github/scripts/plan_ci.py',b'if ['),
                         ('.github/workflows/ci.yml',b'key: ['),('.github/workflows/ci.yml',b'jobs: true\n')]:
            self.git('reset','--hard',self.base);self.write(path,raw);self.commit()
            self.assertEqual('full',self.check(self.plan())['required_behavioral'])
        self.git('reset','--hard',self.base);self.git('rm','.github/scripts/plan_ci.py');self.commit()
        self.assertEqual('full',self.check(self.plan())['required_behavioral'])
        self.git('reset','--hard',self.base);self.git('update-index','--chmod=+x','.github/scripts/plan_ci.py')
        self.git('commit','-qm','mode')
        self.assertEqual('full',self.check(self.plan())['required_behavioral'])
        self.assertNotEqual(w.semantic('ci.yml',b'flag: true'),w.semantic('ci.yml',b'flag: "true"'))

    def test_bindings_digest_shape_and_refs_are_not_candidate_authority(self):
        self.write('.github/scripts/plan_ci.py',b'RULE=False\n');self.commit()
        for mutate in [lambda p:p['binding'].update(repository='Other/repo'),
                       lambda p:p.update(version=3),lambda p:p.update(behavioral_scope='invalid'),
                       lambda p:p['binding'].update(target=self.base)]:
            p=self.plan();mutate(p);self.sign(p)
            with self.assertRaises(ValueError):self.check(p)
        p=self.plan();p['plan_id']='forged'
        with self.assertRaises(ValueError):self.check(p)
        for value in ('--help','main','a'*39,None):
            with self.assertRaises(ValueError):w.sha(value)
        with self.assertRaises(ValueError):w.read_json(b'{"a":1,"a":2}')
        with self.assertRaises(ValueError):w.read_json(b' '* (w.LIMIT+1))
        with patch.object(w,'LIMIT',1),self.assertRaises(ValueError):w.blob(self.repo,self.base,'.github/scripts/plan_ci.py')
        with patch.object(w,'git',return_value=b'120000 blob deadbeef\tfile'),self.assertRaises(ValueError):
            w.blob(self.repo,self.base,'.github/scripts/plan_ci.py')

    def test_exact_merge_target_and_stale_base(self):
        self.write('src/product.py',b'VALUE=2');head=self.commit()
        self.git('checkout','-q','--detach',self.base);self.write('base.md',b'base');base=self.commit()
        self.base=base
        tree=self.git('rev-parse',head+'^{tree}')
        target=subprocess.check_output(['git','-C',str(self.repo),'commit-tree',tree,'-p',base,'-p',head],input=b'merge\n').decode().strip()
        p=self.plan(head);p['binding']['target']=target;self.sign(p)
        self.assertEqual('full',self.check(p)['required_behavioral'])

    def hosted(self, mutate=None, names=None):
        head=self.base
        pr={'state':'open','base':{'sha':self.base,'repo':{'full_name':'Example/repo'}},
            'head':{'sha':head,'repo':{'full_name':'Example/repo'}}}
        run={'id':7,'head_sha':head,'path':'.github/workflows/ci.yml','event':'pull_request',
             'head_repository':{'full_name':'Example/repo'},'status':'in_progress','conclusion':None}
        artifacts={'artifacts':[{'id':9,'name':'ci-plan','expired':False}]}
        if mutate:mutate(pr,run,artifacts)
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:
            for name in names or ['ci-plan.json']:z.writestr(name,w.canonical(self.plan()))
        responses=[w.canonical(pr),w.canonical(run),w.canonical(artifacts),buf.getvalue()]
        with patch.object(w,'api',side_effect=responses):return w.hosted_inputs('Example/repo',66,7)

    def test_hosted_artifact_is_data_and_bound_to_live_pr(self):
        self.assertEqual(7,self.hosted()[1]['id'])
        for mutate in [lambda p,r,a:p.update(state='closed'),lambda p,r,a:r.update(head_sha='0'*40),
                       lambda p,r,a:r.update(path='other.yml'),lambda p,r,a:r.update(event='push'),
                       lambda p,r,a:r['head_repository'].update(full_name='Other/repo'),
                       lambda p,r,a:a.update(artifacts=[]),lambda p,r,a:a['artifacts'][0].update(expired=True)]:
            with self.assertRaises(ValueError):self.hosted(mutate)
        with self.assertRaises(ValueError):self.hosted(names=['../selection_witness.py'])
        with self.assertRaises(ValueError):w.hosted_inputs('../Other/repo',1,1)
        with self.assertRaises(ValueError):w.hosted_inputs('Example/repo',0,1)
        with patch.object(w,'subprocess') as sub:
            sub.check_output.return_value=b'{}'; self.assertEqual(b'{}',w.api('Example/repo','/pulls/1'))

    def test_cli_pin_drift_success_and_failures(self):
        source=Path(w.__file__).read_bytes(); trusted=self.repo/'trusted'
        path=trusted/'.github/scripts/selection_witness.py';path.parent.mkdir(parents=True);path.write_bytes(source)
        output=self.repo/'receipt.json';planfile=self.repo/'plan.json';planfile.write_bytes(w.canonical(self.plan()))
        argv=['--repository','Example/repo','--repo',str(self.repo),'--base',self.base,'--head',self.base,
              '--plan',str(planfile),'--expected-witness',self.base,'--output',str(output)]
        real_git=w.git
        def git(repo,*args):
            if Path(repo)==trusted:return self.base.encode() if args[0]=='rev-parse' else source
            return real_git(repo,*args)
        with patch.object(w,'__file__',str(path)),patch.object(w,'git',side_effect=git):
            self.assertEqual(0,w.main(argv))
            path.write_bytes(source+b'# drift')
            self.assertEqual(1,w.main(argv))
            path.write_bytes(source)
            argv[argv.index('--expected-witness')+1]='0'*40
            self.assertEqual(1,w.main(argv))
        self.assertEqual('BLOCK',json.loads(output.read_bytes())['status'])

    def test_deleted_candidate_bootstrap_cannot_change_external_witness(self):
        # Load fixture construction only; all candidate planning/verification runs
        # in new processes using the actual modified checkout.
        from tests import test_ci_plan as fixture
        fixture.PlannerTests.setUpClass()
        self.addCleanup(fixture.PlannerTests.tearDownClass)
        candidate = fixture.PlannerTests()
        candidate.setUp(); self.addCleanup(candidate.doCleanups)
        planner_path = '.github/scripts/plan_ci.py'
        original = (candidate.repo / planner_path).read_text(encoding='utf-8')
        guard = 'if semantic_change and path in SELECTION_AUTHORITY:'
        self.assertIn(guard, original)
        fixture.write(candidate.repo, planner_path, original.replace(guard, 'if False:'))
        selector = '.github/scripts/ci_dependencies.py'
        source = (candidate.repo / selector).read_bytes() + b'''
original_select = select
def select(*args, **kwargs):
    result = original_select(*args, **kwargs)
    result[0]['selected'] = {}
    return result
'''
        head = candidate.commit(selector, source)
        event = self.repo / 'event.json'; planfile = self.repo / 'attack-plan.json'
        event.write_bytes(w.canonical({'pull_request': {
            'base': {'sha': candidate.base, 'ref': 'develop', 'repo': {'full_name': 'Example/repo'}},
            'head': {'sha': head}, 'body': fixture.BODY.replace('R0', 'R2')}}))
        env = {**os.environ, 'GITHUB_OUTPUT': ''}
        result = subprocess.run([sys.executable, planner_path, '--event', str(event),
            '--event-name', 'pull_request', '--output', str(planfile)],
            cwd=candidate.repo, env=env, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        plan = json.loads(planfile.read_bytes())
        self.assertEqual('focused', plan['behavioral_scope'])
        self.assertEqual({}, plan['selection']['selected'])
        worker = "import json,sys;sys.path.insert(0,'.github/scripts');import plan_ci as p;p.verify_plan(p.ROOT,json.load(open(sys.argv[1])),json.load(open(sys.argv[2])))"
        result = subprocess.run([sys.executable, '-c', worker, str(planfile), str(event)],
            cwd=candidate.repo, env=env, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        # Freeze a separately committed witness; never execute its candidate copy.
        self.write('.github/scripts/selection_witness.py', Path(w.__file__).read_bytes())
        trusted = self.commit()
        output = self.repo / 'receipt.json'
        # A candidate-side module must not enter the isolated witness process.
        fixture.write(candidate.repo, 'yaml.py', 'raise RuntimeError("candidate imported")\n')
        result = subprocess.run([sys.executable, '-I', str(self.repo / '.github/scripts/selection_witness.py'),
            '--repository', 'Example/repo', '--repo', str(candidate.repo), '--base', candidate.base,
            '--head', head, '--plan', str(planfile), '--expected-witness', trusted, '--output', str(output)],
            cwd=candidate.repo, env=env, capture_output=True, text=True)
        self.assertEqual(1, result.returncode, result.stderr)
        receipt = json.loads(output.read_bytes())
        self.assertEqual(trusted, receipt['witness_commit'])
        self.assertIn('requires FULL', receipt['reason'])
        self.attack_evidence = {'candidate_planner_exit': 0, 'candidate_verifier_exit': 0,
                                'candidate_behavioral_scope': plan['behavioral_scope'],
                                'candidate_selected': plan['selection']['selected'],
                                'external_witness_exit': result.returncode, 'receipt': receipt}

    def test_hosted_main_checks_external_inputs_and_fetches_only_git_data(self):
        pr, run, plan = self.hosted()
        output = self.repo / 'hosted-receipt.json'
        argv = ['--repository','Example/repo','--pr','66','--run','7',
                '--expected-witness',self.base,'--output',str(output)]
        real_git = w.git; source = Path(w.__file__).read_bytes()
        def git(repo,*args):
            if Path(repo) == ROOT:
                return self.base.encode() if args[0] == 'rev-parse' else source
            if args[0] in ('init','fetch'): return b''
            return real_git(self.repo,*args)
        with patch.object(w,'hosted_inputs',return_value=(pr,run,plan)),patch.object(w,'git',side_effect=git):
            self.assertEqual(0,w.main(argv))
        self.assertEqual(7,json.loads(output.read_bytes())['content_run'])
        with patch.object(w,'hosted_inputs',side_effect=zipfile.BadZipFile('invalid zip')),patch.object(w,'git',side_effect=git):
            self.assertEqual(1,w.main(argv))

    def test_script_entrypoint_blocks_an_unpinned_checkout(self):
        output = self.repo / 'entrypoint.json'
        with patch.object(sys, 'argv', [w.__file__, '--repository', 'Example/repo',
                '--expected-witness', '0' * 40, '--output', str(output)]), self.assertRaises(SystemExit) as error:
            runpy.run_path(w.__file__, run_name='__main__')
        self.assertEqual(1, error.exception.code)
        self.assertEqual('BLOCK', json.loads(output.read_bytes())['status'])


if __name__=='__main__':unittest.main()
