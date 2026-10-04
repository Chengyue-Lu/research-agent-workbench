"""Metadata binds an exact content plan; it never supplies a green test result."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'.github/scripts'))
import ci_component_metadata as metadata
import run_component_ci as runner


class ComponentAPI:
    repository = 'Example/repo'

    def __init__(self, plan, pr):
        self.pr = copy.deepcopy(pr)
        self.run = dict(id=41, workflow_id=12, path=metadata.WORKFLOW, event='pull_request',
                        head_sha=pr['head']['sha'], repository={'full_name': self.repository},
                        head_repository=pr['head']['repo'], pull_requests=[copy.deepcopy(pr)],
                        run_attempt=1, status='completed', conclusion='success')
        self.workflow = dict(id=12, name='CI components', path=metadata.WORKFLOW)
        self.set_plan(plan)

    def set_plan(self, plan, members=None):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as bundle:
            for name, value in (members or {'plan.json': runner.canonical(plan)}).items():
                bundle.writestr(name, value)
        self.raw = buffer.getvalue()
        self.artifact = dict(id=51, name='component-plan', expired=False, workflow_run={'id': 41},
                             size_in_bytes=len(self.raw), digest='sha256:'+hashlib.sha256(self.raw).hexdigest())

    def get(self, path):
        if path == 'actions/workflows/ci_components.yml': return self.workflow
        if path.startswith('actions/workflows/ci_components.yml/runs?'): return {'workflow_runs': [self.run]}
        if path == 'actions/runs/41': return copy.deepcopy(self.run)
        if path == 'pulls/5': return self.pr
        raise AssertionError('unexpected API request: '+path)

    def pages(self, path, key):
        assert path == 'actions/runs/41/artifacts' and key == 'artifacts'
        return [self.artifact]

    def download(self, artifact_id):
        assert artifact_id == 51
        return self.raw


class ComponentMetadataTests(unittest.TestCase):
    def wait_clock(self):
        state = {'now': 0, 'sleeps': []}
        def sleep(seconds):
            state['sleeps'].append(seconds)
            state['now'] += seconds
        return state, lambda: state['now'], sleep

    def test_late_plan_is_bound_without_claiming_running_execution_success(self):
        self.api.run.update(status='in_progress', conclusion=None)
        state, clock, sleep = self.wait_clock()
        pages = self.api.pages
        def delayed(path, key):
            return [] if state['now'] == 0 else pages(path, key)
        with patch.object(self.api, 'pages', side_effect=delayed), \
             patch.object(metadata.time, 'monotonic', side_effect=clock), \
             patch.object(metadata.time, 'sleep', side_effect=sleep):
            value = metadata.bind_plan(self.api, self.pr, self.plan, wait_seconds=7)
        self.assertEqual([5], state['sleeps'])
        self.assertEqual('in_progress', value['content_status'])
        self.assertFalse(value['execution_success_asserted'])

    def test_plan_wait_is_bounded_and_completed_missing_or_ambiguous_plan_never_waits(self):
        self.api.run.update(status='in_progress', conclusion=None)
        state, clock, sleep = self.wait_clock()
        with patch.object(self.api, 'pages', return_value=[]), \
             patch.object(metadata.time, 'monotonic', side_effect=clock), \
             patch.object(metadata.time, 'sleep', side_effect=sleep), \
             self.assertRaises(metadata.PlanNotReady):
            metadata.bind_plan(self.api, self.pr, self.plan, wait_seconds=7)
        self.assertEqual([5, 2], state['sleeps'])
        for artifacts, status in (([], 'completed'), ([self.api.artifact, self.api.artifact], 'in_progress'),
                                  ([dict(self.api.artifact, expired=True)], 'in_progress')):
            with self.subTest(status=status, artifacts=len(artifacts)), \
                 patch.object(self.api, 'pages', return_value=artifacts), \
                 patch.object(metadata.time, 'sleep') as paused, self.assertRaises(ValueError):
                self.api.run['status'] = status
                metadata.bind_plan(self.api, self.pr, self.plan, wait_seconds=7)
            paused.assert_not_called()

    def test_head_or_attempt_changes_during_wait_refuse_instead_of_borrowing_new_plan(self):
        for mutation in ('head', 'attempt'):
            self.api = ComponentAPI(self.plan, self.pr)
            self.api.run.update(status='in_progress', conclusion=None)
            state, clock, advance = self.wait_clock()
            def sleep(seconds):
                advance(seconds)
                if mutation == 'head':
                    self.api.pr['head']['sha'] = 'e'*40
                else:
                    self.api.run['run_attempt'] = 2
            with self.subTest(mutation=mutation), patch.object(self.api, 'pages', return_value=[]), \
                 patch.object(metadata.time, 'monotonic', side_effect=clock), \
                 patch.object(metadata.time, 'sleep', side_effect=sleep), self.assertRaisesRegex(ValueError, 'changed'):
                metadata.bind_plan(self.api, self.pr, self.plan, wait_seconds=7)
            self.assertEqual([5], state['sleeps'])
        for seconds in (-1, 181, True, float('inf'), float('nan')):
            with self.subTest(seconds=seconds), self.assertRaisesRegex(ValueError, 'budget'):
                metadata.bind_plan(self.api, self.pr, self.plan, wait_seconds=seconds)

    def setUp(self):
        self.pr = dict(number=5, base=dict(ref='develop', sha='a'*40, repo={'full_name':'Example/repo'}),
                       head=dict(sha='b'*40, repo={'full_name':'Example/repo'}))
        self.plan = dict(profile='component', base_sha='a'*40, head_sha='c'*40,
                         plan_sha256='d'*64, selected_tests=['test_documentation'])
        self.api = ComponentAPI(self.plan,self.pr)

    def test_failed_or_running_execution_is_not_relabelled_by_metadata(self):
        self.api.workflow['name'] = 'CI components candidate'
        for status, conclusion in [('in_progress',None),('completed','success'),
                                    ('completed','failure'),('completed','cancelled')]:
            with self.subTest(status=status,conclusion=conclusion):
                self.api.run.update(status=status,conclusion=conclusion)
                result = metadata.bind_plan(self.api,self.pr,self.plan)
                self.assertFalse(result['execution_success_asserted'])
                self.assertEqual('plan-reference-only',result['authority'])
                self.assertEqual(conclusion,result['content_conclusion'])
                self.assertNotIn('conclusion',result)

    def test_foreign_run_or_forged_missing_expired_plan_is_rejected(self):
        cases = [
            lambda a:a.workflow.update(path='.github/workflows/ci.yml'),
            lambda a:a.workflow.update(id=90),
            lambda a:a.run.update(event='workflow_dispatch'),
            lambda a:a.run.update(workflow_id=90),
            lambda a:a.run.update(path='.github/workflows/ci.yml'),
            lambda a:a.run.update(repository={'full_name':'Foreign/repo'}),
            lambda a:a.run.update(head_repository={'full_name':'Foreign/repo'}),
            lambda a:a.run.update(head_sha='e'*40),
            lambda a:a.run.update(pull_requests=[]),
            lambda a:a.run['pull_requests'][0]['base'].update(sha='e'*40),
            lambda a:a.artifact.update(expired=True),
            lambda a:a.artifact.update(name='ci-plan'),
            lambda a:a.artifact.update(workflow_run={'id':99}),
            lambda a:a.artifact.update(digest='sha256:'+'0'*64),
            lambda a:a.artifact.update(size_in_bytes=metadata.MAX_BYTES+1),
            lambda a:a.set_plan({**self.plan,'selected_tests':[]}),
            lambda a:a.set_plan(self.plan,{'../plan.json':b'{}'}),
        ]
        for i, mutate in enumerate(cases):
            with self.subTest(case=i):
                api=ComponentAPI(self.plan,self.pr);mutate(api)
                with self.assertRaises(ValueError): metadata.bind_plan(api,self.pr,self.plan)

    def test_observed_run_attempt_or_pr_change_is_rejected(self):
        for mode in ('attempt','head','base'):
            api=ComponentAPI(self.plan,self.pr)
            original=api.get
            def changing(path):
                value=copy.deepcopy(original(path))
                if mode=='attempt' and path=='actions/runs/41': value['run_attempt']=2
                if mode in ('head','base') and path=='pulls/5': value[mode]['sha']='e'*40
                return value
            with self.subTest(mode=mode),patch.object(api,'get',side_effect=changing),self.assertRaises(ValueError):
                metadata.bind_plan(api,self.pr,self.plan)

    def test_real_git_merge_and_metadata_entrypoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE).decode().strip()
            git('init','-q');git('config','user.name','Metadata fixture');git('config','user.email','ci@example.invalid')
            (root/'tests').mkdir()
            (root/'tests/ci_components.json').write_bytes((ROOT/'tests/ci_components.json').read_bytes())
            (root/'tests/test_documentation.py').write_text('fixture=True\n',encoding='utf-8')
            (root/'README.md').write_text('before\n',encoding='utf-8')
            git('add','.');git('commit','-qm','base');base=git('rev-parse','HEAD')
            git('checkout','-qb','candidate');(root/'README.md').write_text('after\n',encoding='utf-8')
            git('add','.');git('commit','-qm','head');head=git('rev-parse','HEAD')
            git('checkout','-q','--detach',base);git('merge','--no-ff','candidate','-m','test merge')
            target=git('rev-parse','HEAD')
            pr=copy.deepcopy(self.pr);pr['base']['sha']=base;pr['head']['sha']=head
            event={'repository':{'full_name':'Example/repo'},'pull_request':pr}
            plan=runner.make_plan(root,base,target)
            api=ComponentAPI(plan,pr)
            result=metadata.check_metadata(root,event,api)
            self.assertEqual(target,result['target_sha'])
            event_file=root/'event.json';event_file.write_text(json.dumps(event),encoding='utf-8')
            output=root/'metadata.json'
            with patch.object(metadata,'GitHub',return_value=api),patch.object(metadata.Path,'cwd',return_value=root),\
                 patch.dict('os.environ',GITHUB_EVENT_NAME='pull_request',GITHUB_REPOSITORY='Example/repo'):
                self.assertEqual(0,metadata.main(['--event',str(event_file),'--output',str(output)]))
            self.assertEqual(result,json.loads(output.read_bytes()))
            git('checkout','-q','--detach',head)
            with self.assertRaisesRegex(ValueError,'test merge'): metadata.check_metadata(root,event,api)
            changed=copy.deepcopy(event);changed['pull_request']['head']['sha']='f'*40
            with self.assertRaisesRegex(ValueError,'stale'): metadata.check_metadata(root,changed,api)
