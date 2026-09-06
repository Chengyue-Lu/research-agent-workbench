from __future__ import annotations

import argparse
import copy
import hashlib
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
        write(cls.seed, 'pyproject.toml', (ROOT / 'pyproject.toml').read_bytes())
        for name in ('test_ci_plan', 'test_ci_checks', 'test_governance_helper_branches'):
            write(cls.seed, 'tests/' + name + '.py', 'import unittest\nclass Example(unittest.TestCase):\n    def test_ok(self): pass\n')
        for name in {t.split('.')[0] for g in cls.policy['groups'].values() for t in g['tests']}:
            write(cls.seed, 'tests/' + name + '.py', 'import unittest\nclass Example(unittest.TestCase):\n    def test_ok(self): pass\n')
        for path in LEAVES:
            write(cls.seed, path, 'VALUE = 1\n')
        for path in ('README.md', 'docs/TASKS.md', 'docs/ARCHITECTURE.md', 'docs/workstreams/example.md'):
            write(cls.seed, path, 'baseline\n')
        write(cls.seed, 'src/consumer.py', 'VALUE = 1\n')
        write(cls.seed, 'tests/test_unselected.py', 'import unittest\nclass Other(unittest.TestCase):\n    def test_existing(self): pass\n')
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

    def test_accepted_test_consumer_drift_invalidates_old_closure(self):
        original_base = self.base
        budget_test = ('import runpy, unittest\nclass Budget(unittest.TestCase):\n'
                       '    def test_limit(self):\n'
                       '        self.assertLessEqual(runpy.run_path("' + LEAVES[0] + '")["VALUE"], 1)\n')
        for action in ('added', 'modified', 'deleted'):
            with self.subTest(action=action):
                command(self.repo, 'reset', '--hard', original_base)
                name = 'test_new_budget' if action == 'added' else 'test_unselected'
                path = 'tests/' + name + '.py'
                if action == 'deleted':
                    command(self.repo, 'rm', path)
                    command(self.repo, 'commit', '-qm', 'accepted test deletion')
                else:
                    self.commit(path, budget_test)
                    before = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', name + '.py'],
                                            cwd=self.repo, capture_output=True)
                    self.assertEqual(0, before.returncode, before.stderr.decode(errors='replace'))
                self.base = command(self.repo, 'rev-parse', 'HEAD')
                self.commit(LEAVES[0], 'VALUE = 2\n')
                p = self.plan()
                self.assertEqual('full', p['change_class'])
                self.assertIn('consumer inventory changed', ' '.join(p['reasons']))
                if action != 'deleted':
                    after = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', name + '.py'],
                                           cwd=self.repo, capture_output=True)
                    self.assertNotEqual(0, after.returncode)
                    self.assertIn(b'AssertionError', after.stderr)
                command(self.repo, 'reset', '--hard', self.base)
                reviewed = copy.deepcopy(self.policy)
                if action != 'deleted':
                    reviewed['groups']['provider-wire']['tests'].append(name)
                reviewed['consumer_fingerprint'] = planner.consumer_fingerprint(self.repo, self.base, LEAVES)
                self.base = self.commit(planner.POLICY, planner.canonical(reviewed))
                self.commit(LEAVES[0], 'VALUE = 1  # reviewed consumer closure\n')
                restored = self.plan()
                self.assertEqual('focused', restored['change_class'])
                planner.verify_plan(self.repo, restored)
                if action != 'deleted': self.assertIn(name, restored['tests'])

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
                           ('package_smoke', False), ('repository_smoke', False), ('coverage_scope', 'none'),
                           ('policy_sha256', 'fake'), ('impact_evidence', {})]:
            tampered = copy.deepcopy(plan)
            tampered[key] = value
            tampered['plan_id'] = planner.digest({k:v for k,v in tampered.items() if k != 'plan_id'})
            with self.subTest(key=key), self.assertRaises(ValueError):
                planner.verify_plan(self.repo, tampered)

    def test_wrong_digest_target_and_lowered_class_are_rejected(self):
        self.commit('src/unknown.py', 'VALUE = 1\n')
        plan = self.plan()
        for mutate in (lambda p: p.update(plan_id='fake'), lambda p: p['binding'].update(target=self.base),
                       lambda p: p.update(coverage_scope='none')):
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
        for host_event in ('pull_request', 'push', 'workflow_dispatch'):
            with self.subTest(host_event=host_event), patch.object(planner,'ROOT',self.repo), \
                 patch.dict(os.environ,{'GITHUB_OUTPUT':str(ghout), 'GITHUB_EVENT_NAME':host_event}):
                self.assertEqual(0,planner.main(['--event',str(event),'--event-name','pull_request',
                                                '--output',str(output)]))
        self.assertIn('class=fast',ghout.read_text())
        self.assertEqual(output.read_bytes(), planner.canonical(json.loads(output.read_bytes())))

    def test_changed_lines_and_deleted_only_hunks(self):
        head=self.commit(LEAVES[0],'VALUE = 2\n')
        self.assertEqual({LEAVES[0]:[1]},planner.changed_lines(self.repo,self.base,head,[LEAVES[0],'README.md']))
        self.assertEqual({LEAVES[0]:[1]},self.plan()['changed_lines'])
        self.commit(LEAVES[0],'')
        self.assertEqual('full',self.plan()['change_class'])

    def test_executable_mapping_is_bound_and_unmapped_changes_require_full(self):
        self.commit(LEAVES[0], 'VALUE = (\n    1\n)\n')
        self.base = command(self.repo, 'rev-parse', 'HEAD')
        self.commit(LEAVES[0], 'VALUE = (\n    2\n)\n')
        p = self.plan()
        self.assertEqual([2], p['changed_lines'][LEAVES[0]])
        self.assertEqual([1, 2, 3], p['coverage_lines'][LEAVES[0]])
        planner.verify_plan(self.repo, p)
        p['coverage_lines'][LEAVES[0]] = [2]
        p['plan_id'] = planner.digest({k: v for k, v in p.items() if k != 'plan_id'})
        with self.assertRaisesRegex(ValueError, 'executable-line mapping'):
            planner.verify_plan(self.repo, p)
        self.commit(LEAVES[0], 'VALUE = (\n    2\n)\n# no executable owner\n')
        self.assertEqual('full', self.plan()['change_class'])

    def test_source_mode_change_requires_full(self):
        command(self.repo,'update-index','--chmod=+x',LEAVES[0])
        command(self.repo,'commit','-qm','source mode change')
        self.assertEqual('full',self.plan()['change_class'])

    def test_git_type_change_adds_repository_without_erasing_other_impact(self):
        # Construct an exact symlink tree entry without requiring Windows symlink privilege.
        self.commit(LEAVES[0], 'VALUE = 2\n')
        blob = subprocess.check_output(['git', '-C', str(self.repo), 'hash-object', '-w', '--stdin'],
                                       input=b'docs/TASKS.md').decode().strip()
        command(self.repo, 'update-index', '--cacheinfo', '120000,' + blob + ',README.md')
        command(self.repo, 'commit', '-qm', 'type change')
        p = self.plan()
        self.assertEqual(['impact', 'repository'], p['coverage_obligations'])
        self.assertIn('type change requires FULL', p['obligation_reasons']['coverage_scope'])
        self.assertIn(LEAVES[0], p['coverage_modules'])
        self.assertEqual([1], p['coverage_lines'][LEAVES[0]])

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
        event = {'inputs':{'pr':60},'repository':{'full_name':'Example/repo'}}
        tree = command(self.repo, 'rev-parse', 'HEAD^{tree}')
        with patch.object(planner.subprocess,'check_output',return_value=json.dumps(pr).encode()), \
             patch.dict(os.environ, {'GITHUB_SHA': head}):
            p=planner.event_plan(self.repo,event,'workflow_dispatch')
            self.assertEqual('full',p['change_class'])
            self.assertEqual(head,p['binding']['head'])
            planner.verify_plan(self.repo, p, event, 'workflow_dispatch')
            for trigger in (self.base, '', '0' * 40):
                with patch.dict(os.environ, {'GITHUB_SHA': trigger}):
                    with self.assertRaisesRegex(ValueError, 'start a new dispatch'):
                        planner.event_plan(self.repo, event, 'workflow_dispatch')
                    with self.assertRaisesRegex(ValueError, 'start a new dispatch'):
                        planner.verify_plan(self.repo, p, event, 'workflow_dispatch')
            # Use run here: the PR API mock must not intercept this Git fixture operation.
            merged = subprocess.run(['git', '-C', str(self.repo), 'commit-tree', tree, '-p', self.base, '-p', head],
                                    input=b'merge\n', capture_output=True, check=True).stdout.decode().strip()
            subprocess.run(['git', '-C', str(self.repo), 'checkout', '--detach', merged], capture_output=True, check=True)
            self.assertEqual(merged, planner.event_plan(self.repo, event, 'workflow_dispatch')['binding']['target'])
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
            with self.assertRaises(ValueError):
                runner._suite_for(argparse.Namespace(suite='impact', plan=path))
            source = (self.repo / '.github/scripts/plan_ci.py').read_text()
            self.commit('.github/scripts/plan_ci.py', source.replace("'fast': 0,", "'fast': 0 + 0,"))
            p = self.plan(body=BODY.replace('R0', 'R2'))
            path.write_bytes(planner.canonical(p))
            self.assertEqual('full', p['behavioral_scope'])
            self.assertGreater(runner._suite_for(argparse.Namespace(suite='impact', plan=path)).countTestCases(), 0)

    def test_r2_test_fixture_and_fingerprint_refresh_have_no_coverage_or_smokes(self):
        for path in ('tests/test_unselected.py', 'tests/fixtures/case.json', 'work/example/result.yaml'):
            with self.subTest(path=path):
                command(self.repo, 'reset', '--hard', self.base)
                self.commit(path, 'fixture change\n')
                p = self.plan(body=BODY.replace('R0', 'R2'))
                self.assertEqual(('full', 'none', False, False),
                    tuple(p[k] for k in ('behavioral_scope', 'coverage_scope', 'package_smoke', 'repository_smoke')))
                self.assertIn('no production/critical', p['obligation_reasons']['coverage_scope'][0])
        self.commit('tests/test_unselected.py', 'reviewed test change\n')
        reviewed = copy.deepcopy(self.policy)
        reviewed['consumer_fingerprint'] = planner.consumer_fingerprint(self.repo, 'HEAD', LEAVES)
        self.commit(planner.POLICY, planner.canonical(reviewed))
        self.assertEqual('none', self.plan(body=BODY.replace('R0', 'R2'))['coverage_scope'])

    def test_coverage_union_executes_repository_and_impact_tests_once(self):
        from tests import run_unittest_suite as runner
        authority = yaml.safe_load((self.repo / 'tests/coverage_policy.yaml').read_bytes())
        authority['suites']['coverage-quality'] = {'modules': ['test_unselected'],
                                                  'test_ids': ['test_ci_plan.Example.test_ok']}
        self.base = self.commit('tests/coverage_policy.yaml', yaml.safe_dump(authority))
        source = (self.repo / '.github/scripts/plan_ci.py').read_text()
        self.commit('.github/scripts/plan_ci.py', source.replace("'fast': 0,", "'fast': 0 + 0,"))
        p = self.plan(force_full=True)
        self.assertEqual(['impact', 'repository'], p['coverage_obligations'])
        path = Path(self.temp.name) / 'union-plan.json'; path.write_bytes(planner.canonical(p))
        args = argparse.Namespace(suite='coverage-plan', plan=path, policy=self.repo / 'tests/coverage_policy.yaml')
        with patch.object(runner, 'ROOT', self.repo), patch.object(runner, 'TESTS', self.repo / 'tests'), \
             patch.object(runner, 'SOURCE', self.repo / 'src'), patch.dict(os.environ, {'GITHUB_EVENT_PATH':''}), \
             patch.dict(sys.modules), patch.object(sys, 'path', list(sys.path)):
            for name in ('test_ci_plan', 'test_unselected'): sys.modules.pop(name, None)
            suite = runner._suite_for(args)
            self.assertEqual({'test_ci_plan.Example.test_ok', 'test_unselected.Other.test_existing'},
                             {test.id() for test in runner._iter_tests(suite)})
            result = unittest.TestResult(); suite.run(result)
            self.assertEqual(2, result.testsRun)
            self.assertTrue(result.wasSuccessful())
            with self.assertRaises(ValueError):
                runner._suite_for(argparse.Namespace(suite='impact', plan=path))
            with patch.object(unittest.TestLoader, 'loadTestsFromNames', return_value=unittest.TestSuite()):
                with self.assertRaisesRegex(ValueError, 'missing or empty'):
                    runner._suite_for(args)

    def test_decorators_are_executable_impact_and_comments_keep_repository_guard(self):
        path = LEAVES[0]
        source = 'def identity(f): return f\n@identity\ndef example(): return 1\n# review note\n'
        head = self.commit(path, source)
        uncertain = []
        mapped = planner.coverage_lines(self.repo, head, {path: [2, 4]}, uncertain)
        self.assertEqual([2], mapped[path])
        self.assertTrue(uncertain)
        with self.assertRaises(ValueError): planner.coverage_lines(self.repo, head, {path: [4]})

    def test_r2_bounded_critical_validator_requires_impact_with_base_acceptance(self):
        path = '.github/scripts/plan_ci.py'
        source = (self.repo / path).read_text()
        self.commit(path, source.replace("'fast': 0,", "'fast': 0 + 0,"))
        p = self.plan(body=BODY.replace('R0', 'R2'))
        self.assertEqual(('full', 'impact', False, False),
            tuple(p[k] for k in ('behavioral_scope', 'coverage_scope', 'package_smoke', 'repository_smoke')))
        self.assertEqual([path], p['coverage_modules'])
        self.assertTrue(p['impact_evidence']['positive_tests'] and p['impact_evidence']['negative_tests'])
        self.assertIn('test_ci_plan', p['coverage_tests'])
        planner.verify_plan(self.repo, p)
        event = {'pull_request': {'base': {'sha': self.base, 'ref': 'develop', 'repo': {'full_name': 'Example/repo'}},
            'head': {'sha': p['binding']['head']}, 'body': BODY + '\ncoverage_scope: none'}}
        self.assertEqual('impact', planner.event_plan(self.repo, event, 'pull_request')['coverage_scope'])
        for key, value in [('coverage_scope', 'none'), ('coverage_modules', []), ('coverage_tests', []),
                           ('impact_evidence', {}), ('behavioral_scope', 'focused')]:
            tampered = copy.deepcopy(p); tampered[key] = value
            tampered['plan_id'] = planner.digest({k:v for k,v in tampered.items() if k != 'plan_id'})
            with self.subTest(key=key), self.assertRaises(ValueError): planner.verify_plan(self.repo, tampered, event)

    def test_coverage_authority_semantics_require_repository_proof(self):
        path = 'tests/coverage_policy.yaml'
        initial = yaml.safe_load((self.repo / path).read_bytes())
        for mutate in (lambda p:p['thresholds']['global'].update(line=91),
                       lambda p:p.update(source_root='src'), lambda p:p['critical_modules'].append('new.py'),
                       lambda p:p['justified_exclusions'].clear(), lambda p:p['negative_acceptance'].pop()):
            command(self.repo, 'reset', '--hard', self.base)
            policy = copy.deepcopy(initial); mutate(policy)
            self.commit(path, yaml.safe_dump(policy))
            p = self.plan()
            self.assertEqual(('full', 'repository'), (p['behavioral_scope'], p['coverage_scope']))
            self.assertFalse(p['package_smoke'] or p['repository_smoke'])
        source = (self.repo / '.github/scripts/plan_ci.py').read_text()
        self.commit('.github/scripts/plan_ci.py', source + '\nimport fractions\n')
        p = self.plan()
        self.assertEqual(['impact', 'repository'], p['coverage_obligations'])
        self.assertEqual(['.github/scripts/plan_ci.py'], p['coverage_modules'])
        self.assertTrue(p['coverage_lines']['.github/scripts/plan_ci.py'])
        self.assertIn('imports changed', ' '.join(p['reasons']))
        self.assertTrue(p['impact_evidence']['positive_tests'] and p['impact_evidence']['negative_tests'])
        planner.verify_plan(self.repo, p)
        self.assertFalse(p['package_smoke'] or p['repository_smoke'])

    def test_repository_requirement_preserves_bounded_impact_and_rejects_downgrade(self):
        path = '.github/scripts/plan_ci.py'
        self.commit(path, (self.repo / path).read_text().replace("'fast': 0,", "'fast': 0 + 0,"))
        bounded = self.plan(body=BODY.replace('R0', 'R2'))
        authority = yaml.safe_load((self.repo / 'tests/coverage_policy.yaml').read_bytes())
        authority['thresholds']['global']['line'] = 91
        self.commit('tests/coverage_policy.yaml', yaml.safe_dump(authority))
        combined = self.plan(body=BODY.replace('R0', 'R2'))
        self.assertEqual(['impact', 'repository'], combined['coverage_obligations'])
        for key in ('coverage_modules', 'changed_lines', 'coverage_lines', 'impact_evidence', 'coverage_tests'):
            self.assertEqual(bounded[key], combined[key])
        planner.verify_plan(self.repo, combined)
        for obligations in (['repository'], ['impact'], []):
            reduced = copy.deepcopy(combined)
            reduced.update(coverage_obligations=obligations, coverage_scope='+'.join(obligations) or 'none')
            reduced['plan_id'] = planner.digest({k:v for k,v in reduced.items() if k != 'plan_id'})
            with self.subTest(obligations=obligations), self.assertRaises(ValueError):
                planner.verify_plan(self.repo, reduced)

    def test_unknown_executable_and_integration_are_complete_fail_safe(self):
        self.commit('src/consumer.py', 'VALUE = 2\n')
        for kwargs in ({}, {'integration': True}, {'base_ref': 'main'}, {'base_ref': 'release/v1.0.0'}):
            p = self.plan(**kwargs)
            self.assertEqual(('full', 'repository', True, True),
                tuple(p[k] for k in ('behavioral_scope', 'coverage_scope', 'package_smoke', 'repository_smoke')))

    def test_pr65_exact_git_diff_is_full_behavior_without_coverage_or_smokes(self):
        fixture = json.loads((ROOT / 'tests/fixtures/ci/pr65.json').read_bytes())
        self.assertEqual('09f96193845ee0e73a215d87ba188b5aa5569704', fixture['head'])
        for side in ('base', 'head'):
            for row in fixture['changes']:
                blob = row[side]
                if blob is None:
                    (self.repo / row['path']).unlink(missing_ok=True)
                else:
                    self.assertEqual(blob['sha256'], hashlib.sha256(blob['content'].encode()).hexdigest())
                    write(self.repo, row['path'], blob['content'])
            command(self.repo, 'add', '.')
            command(self.repo, 'commit', '-qm', 'exact PR 65 ' + side + ' blobs')
            if side == 'base': self.base = command(self.repo, 'rev-parse', 'HEAD')
        p = self.plan(body=BODY.replace('R0', 'R2').replace('impact**: no', 'impact**: yes'))
        self.assertEqual([{'status': r['status'], 'path': r['path']} for r in fixture['changes']], p['changes'])
        self.assertEqual(('R2', 'full', 'none', False, False),
            tuple(p[k] for k in ('risk', 'behavioral_scope', 'coverage_scope', 'package_smoke', 'repository_smoke')))

    def test_smokes_and_coverage_config_are_independent_of_full_behavior(self):
        cases = [('schemas/new.json', '{}', True, True), ('registry/new.yaml', 'version: 1', False, True),
                 ('examples/new.yaml', 'example: true', False, True),
                 ('pyproject.toml', (self.repo / 'pyproject.toml').read_text().replace('version = "0.1.0"', 'version = "0.1.1"'), True, False)]
        for path, content, package, repository in cases:
            command(self.repo, 'reset', '--hard', self.base)
            self.commit(path, content)
            p = self.plan(body=BODY.replace('R0', 'R2'))
            self.assertEqual(('full', 'none', package, repository),
                tuple(p[k] for k in ('behavioral_scope', 'coverage_scope', 'package_smoke', 'repository_smoke')))
        command(self.repo, 'reset', '--hard', self.base)
        self.commit('pyproject.toml', (self.repo / 'pyproject.toml').read_text().replace('branch = true', 'branch = false'))
        self.assertEqual('repository', self.plan()['coverage_scope'])
        for before, after in [('PyYAML>=6,<7', 'PyYAML>=6.1,<7'), ('setuptools>=69', 'setuptools>=70'),
                              ('requires-python = ">=3.11"', 'requires-python = ">=3.12"'),
                              ('research_workbench.cli:main', 'research_workbench.cli:another')]:
            command(self.repo, 'reset', '--hard', self.base)
            self.commit('pyproject.toml', (self.repo / 'pyproject.toml').read_text().replace(before, after))
            p = self.plan()
            self.assertEqual('repository', p['coverage_scope'])
            self.assertTrue(p['package_smoke'])

    def test_validator_inventory_mapping_and_new_import_fail_safe(self):
        path = '.github/scripts/plan_ci.py'
        original = (self.repo / path).read_text()
        self.commit(path, original.replace("'fast': 0,", "'fast': 0 + 0,"))
        raw = planner.read_at
        authority = yaml.safe_load((self.repo / 'tests/coverage_policy.yaml').read_bytes())
        for mutate in (lambda p:p['critical_modules'].remove(path), lambda p:p.update(negative_acceptance=[]),
                       lambda p:p['negative_acceptance'][0].update(positive_tests=[])):
            bad = copy.deepcopy(authority); mutate(bad)
            with patch.object(planner, 'read_at', side_effect=lambda r,c,p: yaml.safe_dump(bad).encode()
                              if p == 'tests/coverage_policy.yaml' else raw(r,c,p)):
                blocked = self.plan()
                self.assertEqual(['impact', 'repository'], blocked['coverage_obligations'])
                self.assertTrue(blocked['blocked_reasons'])
                with self.assertRaises(ValueError): planner.verify_plan(self.repo, blocked)
        self.commit(path, original + '\nimport fractions\n')
        p = self.plan()
        self.assertEqual(['impact', 'repository'], p['coverage_obligations'])
        planner.verify_plan(self.repo, p)

    def test_candidate_policy_and_fingerprint_cannot_approve_new_consumer_closure(self):
        write(self.repo, 'tests/test_new_consumer.py', 'new executable consumer\n')
        self.commit(LEAVES[0], 'VALUE = 2\n')
        candidate = copy.deepcopy(self.policy)
        candidate['consumer_fingerprint'] = planner.consumer_fingerprint(self.repo, 'HEAD', LEAVES)
        candidate['groups']['provider-wire']['tests'].append('test_new_consumer')
        self.commit(planner.POLICY, planner.canonical(candidate))
        p = self.plan()
        self.assertEqual(['impact', 'repository'], p['coverage_obligations'])
        self.assertIn('candidate consumer inventory changed', ' '.join(p['reasons']))


if __name__ == '__main__':
    unittest.main()
