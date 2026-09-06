from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import plan_ci as planner

BODY = '- **Risk tier**: R0\n- **Shared contract**: no\n- **Authority impact**: no'
LEAVES = ['src/research_workbench/adapters/models/' + name + '.py' for name in ('openai', 'anthropic', 'gemini')]


def command(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE).decode().strip()


def write(repo, path, data):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data if isinstance(data, bytes) else data.encode())


class PlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed_temp = tempfile.TemporaryDirectory()
        cls.seed = Path(cls.seed_temp.name)
        command(cls.seed, 'init', '-q', '-b', 'develop')
        command(cls.seed, 'config', 'user.name', 'CI fixture')
        command(cls.seed, 'config', 'user.email', 'fixture@example.invalid')
        command(cls.seed, 'config', 'core.autocrlf', 'false')
        cls.policy = yaml.safe_load((ROOT / planner.POLICY).read_bytes())
        write(cls.seed, '.gitattributes', '* text eol=lf\n')
        write(cls.seed, '.gitignore', '__pycache__/\n')
        for path in planner.TRUST_FILES:
            write(cls.seed, path, (ROOT / path).read_bytes())
        for name in {t.split('.')[0] for g in cls.policy['groups'].values() for t in g['tests']}:
            write(cls.seed, 'tests/' + name + '.py', 'import unittest\nclass Example(unittest.TestCase):\n    def test_ok(self): pass\n')
        for path in LEAVES:
            write(cls.seed, path, 'VALUE = 1\n')
        for path in ('README.md', 'docs/TASKS.md', 'docs/ARCHITECTURE.md', 'docs/workstreams/example.md'):
            write(cls.seed, path, 'baseline\n')
        write(cls.seed, 'src/consumer.py', 'VALUE = 1\n')
        command(cls.seed, 'add', '.')
        command(cls.seed, 'commit', '-qm', 'baseline')
        cls.policy['consumer_fingerprint'] = planner.consumer_fingerprint(cls.seed, 'HEAD', LEAVES)
        write(cls.seed, planner.POLICY, planner.canonical(cls.policy))
        command(cls.seed, 'add', planner.POLICY)
        command(cls.seed, 'commit', '-qm', 'accepted impact policy')

    @classmethod
    def tearDownClass(cls):
        cls.seed_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'
        command(Path(self.temp.name), 'clone', '-q', '--no-hardlinks', str(self.seed), str(self.repo))
        command(self.repo, 'config', 'user.name', 'CI fixture')
        command(self.repo, 'config', 'user.email', 'fixture@example.invalid')
        command(self.repo, 'config', 'core.autocrlf', 'false')
        self.base = command(self.repo, 'rev-parse', 'HEAD')

    def commit(self, path='README.md', data='changed\n'):
        write(self.repo, path, data)
        command(self.repo, 'add', '.')
        command(self.repo, 'commit', '-qm', 'candidate')
        return command(self.repo, 'rev-parse', 'HEAD')

    def plan(self, **kwargs):
        head = command(self.repo, 'rev-parse', 'HEAD')
        return planner.make_plan(self.repo, **{'base': self.base, 'head': head, 'target': head,
                                 'repository': 'Example/repo', 'body': BODY, **kwargs})

    def test_docs_fast_plan_is_explainable_and_replayable(self):
        self.commit()
        plan = self.plan()
        self.assertEqual('fast', plan['change_class'])
        self.assertEqual(['documentation'], plan['test_groups'])
        self.assertFalse(plan['package_smoke'])
        self.assertEqual(plan, planner.verify_plan(self.repo, plan))

    def test_new_markdown_is_fast_but_document_data_is_full(self):
        self.commit('docs/workstreams/new.md')
        self.assertEqual('fast',self.plan()['change_class'])
        self.commit('docs/workstreams/input.yaml')
        self.assertEqual('full',self.plan()['change_class'])

    def test_provider_change_selects_downstream_groups_and_both_pythons(self):
        self.commit(LEAVES[0], 'VALUE = 2\n')
        plan = self.plan()
        self.assertEqual('focused', plan['change_class'])
        self.assertEqual(['provider-cli', 'provider-conformance', 'provider-session', 'provider-wire'], plan['test_groups'])
        self.assertEqual(['3.11', '3.13'], plan['python_versions'])
        self.assertTrue(plan['package_smoke'] and plan['repository_smoke'])
        planner.verify_plan(self.repo, plan)

    def test_mixed_docs_and_provider_keeps_full_impact_closure(self):
        write(self.repo, 'README.md', 'docs\n')
        self.commit(LEAVES[1], 'VALUE = 2\n')
        plan = self.plan()
        self.assertEqual('focused', plan['change_class'])
        self.assertIn('documentation', plan['test_groups'])

    def test_r2_shared_and_unknown_paths_cannot_be_docs_fast(self):
        for path in ('docs/ARCHITECTURE.md', 'schemas/new.json', 'unknown.txt', '.github/new.py'):
            with self.subTest(path=path):
                command(self.repo, 'reset', '--hard', self.base)
                self.commit(path)
                self.assertEqual('full', self.plan()['change_class'])
        command(self.repo, 'reset', '--hard', self.base)
        self.commit()
        for body in (BODY.replace('R0', 'R2'), BODY.replace('impact**: no', 'impact**: yes'), '',
                     BODY.replace('R0', 'invalid')):
            with self.subTest(body=body):
                self.assertEqual('full', self.plan(body=body)['change_class'])
        self.assertEqual('fast', self.plan(body=BODY.replace('R0', 'R1'))['change_class'])

    def test_integration_release_force_and_empty_diff_are_full(self):
        self.assertEqual('full', self.plan()['change_class'])
        self.commit()
        for extra in ({'integration': True}, {'base_ref': 'main'}, {'force_full': True}):
            self.assertEqual('full', self.plan(**extra)['change_class'])

    def test_self_modified_policy_or_runner_cannot_authorize_less(self):
        for path in planner.TRUST_FILES:
            with self.subTest(path=path):
                command(self.repo, 'reset', '--hard', self.base)
                self.commit(path, (self.repo / path).read_bytes() + b'\n')
                self.assertEqual('full', self.plan()['change_class'])

    def test_missing_or_malformed_base_policy_falls_back_full(self):
        self.commit()
        original = planner.read_at
        for replacement in (b'[]', b'not: [yaml', b'{}', b'{"version":1,"version":2}'):
            with patch.object(planner, 'read_at', side_effect=lambda r,c,p: replacement if p == planner.POLICY else original(r,c,p)):
                self.assertEqual('full', self.plan()['change_class'])

    def test_deleted_renamed_and_new_paths_require_full(self):
        (self.repo / 'README.md').rename(self.repo / 'CHANGED.md')
        self.commit('docs/TASKS.md')
        plan = self.plan()
        self.assertEqual('full', plan['change_class'])
        self.assertIn({'path': 'README.md', 'status': 'D'}, plan['changes'])
        self.assertIn({'path': 'CHANGED.md', 'status': 'A'}, plan['changes'])

    def test_consumer_inventory_or_new_import_requires_full(self):
        self.commit('src/consumer.py', 'VALUE = 2\n')
        self.base = command(self.repo, 'rev-parse', 'HEAD')
        self.commit(LEAVES[0], 'VALUE = 2\n')
        self.assertEqual('full', self.plan()['change_class'])
        command(self.repo, 'reset', '--hard', self.base)
        self.commit(LEAVES[0], 'import os\nVALUE = 2\n')
        with patch.object(planner, 'consumer_fingerprint', return_value=self.policy['consumer_fingerprint']):
            self.assertEqual('full', self.plan()['change_class'])

    def test_stale_base_requires_full_merge_validation(self):
        self.commit()
        head = command(self.repo, 'rev-parse', 'HEAD')
        command(self.repo, 'checkout', '-qb', 'other', self.base)
        newer = self.commit('docs/TASKS.md')
        self.assertEqual('full', self.plan(base=newer, head=head, target=head)['change_class'])

    def test_agent_can_add_groups_but_cannot_remove_minimum(self):
        self.commit(LEAVES[0], 'VALUE = 2\n')
        plan = self.plan(extra_groups=['documentation'])
        self.assertIn('documentation', plan['test_groups'])
        planner.verify_plan(self.repo, plan)
        for key, value in [('test_groups', []), ('tests', []), ('coverage_modules', []), ('python_versions', []),
                           ('package_smoke', False), ('repository_smoke', False), ('coverage_mode', 'none'),
                           ('policy_sha256', 'fake'), ('impact_evidence', {})]:
            tampered = copy.deepcopy(plan)
            tampered[key] = value
            tampered['plan_id'] = planner.digest({k:v for k,v in tampered.items() if k != 'plan_id'})
            with self.subTest(key=key), self.assertRaises(ValueError):
                planner.verify_plan(self.repo, tampered)

    def test_wrong_digest_target_and_lowered_class_are_rejected(self):
        self.commit()
        plan = self.plan(force_full=True)
        for mutate in (lambda p: p.update(plan_id='fake'), lambda p: p['binding'].update(target=self.base),
                       lambda p: p.update(coverage_mode='none')):
            bad = copy.deepcopy(plan)
            mutate(bad)
            if bad['plan_id'] != 'fake':
                bad['plan_id'] = planner.digest({k:v for k,v in bad.items() if k != 'plan_id'})
            with self.assertRaises(ValueError): planner.verify_plan(self.repo, bad)
        self.commit('docs/ARCHITECTURE.md')
        bad = self.plan()
        bad['change_class'] = 'fast'
        bad['plan_id'] = planner.digest({k:v for k,v in bad.items() if k != 'plan_id'})
        with self.assertRaisesRegex(ValueError, 'minimum'): planner.verify_plan(self.repo, bad)

    def test_event_binds_actual_head_or_exact_merge_candidate(self):
        head = self.commit()
        event = {'pull_request': {'base': {'sha': self.base, 'ref': 'develop', 'repo': {'full_name': 'Example/repo'}},
                                 'head': {'sha': head}, 'body': BODY}}
        plan = planner.event_plan(self.repo, event, 'pull_request')
        planner.verify_plan(self.repo, plan, event)
        tree = command(self.repo, 'rev-parse', head + '^{tree}')
        merge = subprocess.check_output(['git','-C',str(self.repo),'commit-tree',tree,'-p',self.base,'-p',head],input=b'merge\n').decode().strip()
        command(self.repo, 'checkout', '--detach', merge)
        self.assertEqual(merge, planner.event_plan(self.repo, event, 'pull_request')['binding']['target'])
        command(self.repo, 'checkout', '--detach', self.base)
        with self.assertRaisesRegex(ValueError, 'checkout'): planner.event_plan(self.repo, event, 'pull_request')
        integration = planner.event_plan(self.repo, {'repository': {'full_name': 'Example/repo'}}, 'push')
        self.assertEqual('full', integration['change_class'])

    def test_full_fallback_on_missing_tests_and_git_fact_errors(self):
        self.commit()
        original = planner.read_at
        with patch.object(planner, 'read_at', side_effect=lambda r,c,p: (_ for _ in ()).throw(ValueError('missing test')) if p == 'tests/test_documentation.py' else original(r,c,p)):
            self.assertEqual('full', self.plan()['change_class'])
        with self.assertRaises(ValueError): planner.git(self.repo, 'show', 'missing:unknown')
        with self.assertRaises(ValueError): planner.exact_commit(self.repo, 'HEAD')
        with patch.object(planner, 'git', return_value=b'0'*40):
            with self.assertRaises(ValueError): planner.exact_commit(self.repo, self.base)

    def test_nul_diff_rejects_ambiguous_paths_and_preserves_spaces(self):
        with patch.object(planner, 'git', return_value=b'M\0docs/a b.md\0'):
            self.assertEqual('docs/a b.md', planner.changes(self.repo,self.base,self.base)[0]['path'])
        for raw in (b'M\0x', b'M\0../x\0', b'M\0a\\b\0', b'R100\0x\0', b'M\0\xff\0'):
            with patch.object(planner, 'git', return_value=raw), self.assertRaises((ValueError, UnicodeError)):
                planner.changes(self.repo,self.base,self.base)

    def test_invalid_policy_groups_and_evidence_fail_closed(self):
        mutations = [lambda p:p.update(version=2), lambda p:p.update(version=True), lambda p:p.update(groups={}),
            lambda p:p['groups']['documentation'].update(unknown=True),
            lambda p:p['groups']['documentation'].update(tests=[]),
            lambda p:p['groups']['documentation'].update(tests=['bad']),
            lambda p:p['groups']['documentation'].update(downstream=['missing']),
            lambda p:p['groups']['documentation'].update(downstream=['documentation']),
            lambda p:p['groups']['documentation'].update(package='false'),
            lambda p:p['groups']['documentation'].update(coverage=['same','same']),
            lambda p:p.update(surfaces={}), lambda p:p['surfaces']['documentation'].update(unknown=True),
            lambda p:p['surfaces']['documentation'].update(paths=['*']),
            lambda p:p['surfaces']['documentation'].update(groups=[]),
            lambda p:p['impact_evidence'].update(other=[]),
            lambda p:p['impact_evidence'].update(positive_tests=[]),
            lambda p:p['impact_evidence'].update(negative_tests=p['impact_evidence']['positive_tests'])]
        for mutate in mutations:
            policy = copy.deepcopy(self.policy); mutate(policy)
            with self.subTest(policy=policy), self.assertRaises((ValueError, TypeError)):
                planner.validate_policy(policy)

    def test_cli_emits_canonical_plan_and_workflow_outputs(self):
        head = self.commit()
        event = Path(self.temp.name)/'event.json'
        event.write_text(json.dumps({'pull_request': {'base': {'sha':self.base,'ref':'develop','repo':{'full_name':'Example/repo'}},'head':{'sha':head},'body':BODY}}))
        output = Path(self.temp.name)/'plan.json'
        ghout = Path(self.temp.name)/'outputs'
        with patch.object(planner,'ROOT',self.repo), patch.dict(os.environ,{'GITHUB_OUTPUT':str(ghout)}):
            self.assertEqual(0,planner.main(['--event',str(event),'--output',str(output)]))
        self.assertIn('class=fast',ghout.read_text())
        self.assertEqual(output.read_bytes(), planner.canonical(json.loads(output.read_bytes())))

    def test_changed_lines_and_deleted_only_hunks(self):
        head=self.commit(LEAVES[0],'VALUE = 2\n')
        self.assertEqual({LEAVES[0]:[1]},planner.changed_lines(self.repo,self.base,head,[LEAVES[0],'README.md']))
        self.assertEqual({LEAVES[0]:[1]},self.plan()['changed_lines'])
        self.commit(LEAVES[0],'')
        self.assertEqual('full',self.plan()['change_class'])

    def test_source_mode_change_requires_full(self):
        command(self.repo,'update-index','--chmod=+x',LEAVES[0])
        command(self.repo,'commit','-qm','source mode change')
        self.assertEqual('full',self.plan()['change_class'])

    def test_dirty_or_untracked_source_cannot_consume_clean_head_plan(self):
        self.commit();p=self.plan()
        write(self.repo,'README.md','uncommitted\n')
        with self.assertRaisesRegex(ValueError,'checkout drift'):planner.verify_plan(self.repo,p)
        command(self.repo,'checkout','--','README.md')
        write(self.repo,'src/injected.py','untracked\n')
        with self.assertRaisesRegex(ValueError,'untracked'):planner.verify_plan(self.repo,p)

    def test_manual_full_rerun_uses_current_pr_facts(self):
        head=self.commit()
        pr={'base':{'sha':self.base,'ref':'develop','repo':{'full_name':'Example/repo'}},'head':{'sha':head},'body':BODY}
        with patch.object(planner.subprocess,'check_output',return_value=json.dumps(pr).encode()):
            p=planner.event_plan(self.repo,{'inputs':{'pr':60},'repository':{'full_name':'Example/repo'}},'workflow_dispatch')
            self.assertEqual('full',p['change_class'])
            self.assertEqual(head,p['binding']['head'])
        with self.assertRaises(ValueError):
            planner.event_plan(self.repo,{'inputs':{'pr':'bad'},'repository':{'full_name':'Example/repo'}},'workflow_dispatch')

    def test_runner_consumes_valid_plan_and_rejects_full_as_focused(self):
        from tests import run_unittest_suite as runner
        from contextlib import redirect_stdout
        import io
        self.commit()
        p=self.plan();path=Path(self.temp.name)/'ci-plan.json';path.write_bytes(planner.canonical(p))
        args=argparse.Namespace(suite='focused',plan=path)
        with patch.object(runner,'ROOT',self.repo),patch.object(runner,'TESTS',self.repo/'tests'),\
             patch.object(runner,'SOURCE',self.repo/'src'),patch.dict(os.environ,{'GITHUB_EVENT_PATH':''}),\
             patch.dict(sys.modules),patch.object(sys,'path',list(sys.path)):
            suite=runner._suite_for(args)
            self.assertGreater(suite.countTestCases(),0)
            with self.assertRaisesRegex(ValueError,'requires --plan'):
                runner._suite_for(argparse.Namespace(suite='focused',plan=None))
            for spec in (None, argparse.Namespace(loader=None)):
                with patch.object(runner.importlib.util,'spec_from_file_location',return_value=spec):
                    with self.assertRaisesRegex(ValueError,'could not be loaded'):
                        runner._suite_for(args)
            with patch.object(unittest.TestLoader,'loadTestsFromNames',return_value=unittest.TestSuite()):
                with self.assertRaises(ValueError):runner._suite_for(args)
            path.write_bytes(planner.canonical(self.plan(force_full=True)))
            with self.assertRaises(ValueError):runner._suite_for(args)


if __name__ == '__main__':
    unittest.main()
