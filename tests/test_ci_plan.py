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
        for name in ('test_ci_plan', 'test_ci_checks', 'test_ci_dependencies', 'test_coverage_policy', 'test_governance_helper_branches'):
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

    def test_markdown_resource_change_keeps_existing_failing_consumer(self):
        write(self.repo, 'tests/test_markdown_consumer.py',
              'from pathlib import Path\nimport unittest\n'
              'class MarkdownTest(unittest.TestCase):\n'
              '    def test_value(self):\n'
              '        value = (Path(__file__).parent / "fixtures" / "expected.md").read_text()\n'
              '        self.assertEqual(value, "expected\\n")\n')
        self.base = self.commit('tests/fixtures/expected.md', 'expected\n')
        def run():
            return subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests',
                                   '-p', 'test_markdown_consumer.py'], cwd=self.repo, capture_output=True)
        self.assertEqual(0, run().returncode)
        self.commit('tests/fixtures/expected.md', 'changed\n')
        self.assertEqual(1, run().returncode)
        plan = self.plan()
        self.assertEqual('focused', plan['behavioral_scope'])
        self.assertEqual('none', plan['coverage_scope'])
        self.assertIn('test_markdown_consumer', plan['tests'])
        planner.verify_plan(self.repo, plan)

    def test_assigned_execution_namespace_keeps_failing_reflective_consumer(self):
        write(self.repo, 'src/probe_package/__init__.py', '')
        for name, setup, assertion in (
            ('alias', 'import importlib\nnamespace = importlib\nattribute = "import_module"\n'
             'loader = getattr(namespace, attribute)\nmodule = loader("probe_package." + "value")\n',
             'self.assertEqual(module.VALUE, 1)'),
            ('direct', 'from probe_package import value as module\n', 'self.assertGreaterEqual(module.VALUE, 0)'),
        ):
            write(self.repo, 'tests/test_' + name + '_consumer.py',
                  'import unittest\n' + setup +
                  'class Consumer(unittest.TestCase):\n    def test_value(self): ' + assertion + '\n')
        self.base = self.commit('src/probe_package/value.py', 'VALUE = 1\n')
        def run(name):
            return subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests',
                                   '-p', 'test_' + name + '_consumer.py'], cwd=self.repo, capture_output=True,
                                  env={**os.environ, 'PYTHONPATH': str(self.repo / 'src')})
        self.assertEqual(0, run('alias').returncode)
        self.commit('src/probe_package/value.py', 'VALUE = 2\n')
        self.assertEqual(1, run('alias').returncode)
        self.assertEqual(0, run('direct').returncode)
        plan = self.plan()
        self.assertEqual('focused', plan['behavioral_scope'])
        self.assertEqual('impact', plan['coverage_scope'])
        self.assertTrue({'test_alias_consumer', 'test_direct_consumer'} <= set(plan['tests']))
        self.assertIn('tests/test_alias_consumer.py', plan['selection']['opaque_consumers'])
        planner.verify_plan(self.repo, plan)

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
        for path in ('unknown.txt', '.github/new.py'):
            with self.subTest(path=path):
                command(self.repo, 'reset', '--hard', self.base)
                self.commit(path)
                self.assertEqual('full', self.plan()['change_class'])
        command(self.repo, 'reset', '--hard', self.base)
        self.commit()
        for body in ('', BODY.replace('R0', 'invalid')):
            with self.subTest(body=body):
                self.assertEqual('full', self.plan(body=body)['change_class'])
        self.assertEqual('fast', self.plan(body=BODY.replace('R0', 'R1'))['change_class'])
        self.assertEqual('fast', self.plan(body=BODY.replace('R0', 'R2'))['change_class'])
        self.assertEqual('fast', self.plan(body=BODY.replace('impact**: no', 'impact**: yes'))['change_class'])

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
                p = self.plan()
                self.assertEqual('none', p['coverage_scope'])
                self.assertFalse(p['package_smoke'] or p['repository_smoke'])
        command(self.repo, 'reset', '--hard', self.base)
        candidate = copy.deepcopy(self.policy)
        candidate['groups']['provider-wire']['tests'] = ['test_unselected']
        write(self.repo, planner.POLICY, planner.canonical(candidate))
        self.commit(LEAVES[0], 'VALUE = 2\n')
        p = self.plan()
        self.assertIn('test_provider_adapters', p['tests'])
        self.assertNotIn('test_unselected', p['tests'])

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
        self.assertEqual('fast', plan['change_class'])
        self.assertIn({'path': 'README.md', 'status': 'D'}, plan['changes'])
        self.assertIn({'path': 'CHANGED.md', 'status': 'A'}, plan['changes'])

    def test_consumer_inventory_or_new_import_requires_full(self):
        self.commit('src/consumer.py', 'VALUE = 2\n')
        self.base = command(self.repo, 'rev-parse', 'HEAD')
        self.commit(LEAVES[0], 'VALUE = 2\n')
        self.assertEqual('focused', self.plan()['change_class'])
        command(self.repo, 'reset', '--hard', self.base)
        self.commit(LEAVES[0], 'import os\nVALUE = 2\n')
        with patch.object(planner, 'consumer_fingerprint', return_value=self.policy['consumer_fingerprint']):
            self.assertEqual('focused', self.plan()['change_class'])
        self.commit('tests/test_opaque_consumer.py', 'exec("unknown executable consumer")\n')
        p = self.plan()
        self.assertIn('test_opaque_consumer', p['tests'])
        self.assertNotIn('test_opaque_consumer', p['selection']['excluded'])

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
                self.assertEqual('focused', p['change_class'])
                if action != 'deleted': self.assertIn(name, p['tests'])
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
                self.commit(LEAVES[0], 'VALUE = 1 + 0  # reviewed consumer closure\n')
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
        self.assertEqual('focused',self.plan()['change_class'])
        self.assertEqual([], self.plan()['changed_lines'][LEAVES[0]])

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
        self.assertEqual('focused', self.plan()['change_class'])

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
                self.commit(path, 'VALUE = 2\n' if path.endswith('.py') else 'fixture change\n')
                p = self.plan(body=BODY.replace('R0', 'R2'))
                self.assertEqual(('focused' if path.endswith('.py') else 'none', 'none', False, False),
                    tuple(p[k] for k in ('behavioral_scope', 'coverage_scope', 'package_smoke', 'repository_smoke')))
                self.assertIn('no production/critical', p['obligation_reasons']['coverage_scope'][0])
        self.commit('tests/test_unselected.py', 'VALUE = 2\n')
        reviewed = copy.deepcopy(self.policy)
        reviewed['consumer_fingerprint'] = planner.consumer_fingerprint(self.repo, 'HEAD', LEAVES)
        self.commit(planner.POLICY, planner.canonical(reviewed))
        self.assertEqual('none', self.plan(body=BODY.replace('R0', 'R2'))['coverage_scope'])

    def test_provider_and_independent_test_do_not_force_repository_or_full(self):
        self.commit(LEAVES[0], 'VALUE = 2\n')
        bounded = self.plan()
        self.commit('tests/test_unselected.py', 'import unittest\nclass Other(unittest.TestCase):\n    def test_existing(self): self.assertEqual(1+1,2)\n')
        p = self.plan(body=BODY.replace('R0', 'R2'))
        self.assertEqual(('R2', 'focused', ['impact']), (p['risk'], p['behavioral_scope'], p['coverage_obligations']))
        self.assertEqual(bounded['coverage_modules'], p['coverage_modules'])
        self.assertTrue(set(bounded['tests']) | {'test_unselected'} <= set(p['tests']))
        self.assertNotIn('test_ci_checks', p['tests'])
        planner.verify_plan(self.repo, p)

    def test_test_only_planner_input_does_not_become_a_product_executable_change(self):
        write(self.repo, 'src/research_workbench/cli.py', 'import subprocess\ndef run(command): return subprocess.run(command)\n')
        self.base = self.commit('tests/test_runtime.py', 'from research_workbench.cli import run\n')
        self.commit('tests/test_ci_plan.py', 'import unittest\nclass Example(unittest.TestCase):\n    def test_ok(self): self.assertEqual(1+1,2)\n')
        p = self.plan(body=BODY.replace('R0', 'R2'))
        self.assertEqual(('focused', [], False, False), tuple(p[k] for k in
            ('behavioral_scope', 'coverage_obligations', 'package_smoke', 'repository_smoke')))
        self.assertIn('test_ci_plan', p['tests'])
        self.assertNotIn('test_runtime', p['tests'])
        # A new opaque runtime consumer since the reviewed fingerprint remains required.
        self.commit(LEAVES[0], 'VALUE=2\n')
        self.assertIn('test_runtime', self.plan()['tests'])

    def test_reviewed_opaque_contract_is_invalidated_per_consumer(self):
        runtime = 'src/research_workbench/opaque_runtime.py'
        write(self.repo, runtime, 'import subprocess\ndef run(command): return subprocess.run(command)\n')
        self.commit('tests/test_runtime.py', 'from research_workbench.opaque_runtime import run\n')
        reviewed = copy.deepcopy(self.policy)
        reviewed['consumer_fingerprint'] = planner.consumer_fingerprint(self.repo, 'HEAD', LEAVES)
        self.base = self.commit(planner.POLICY, planner.canonical(reviewed))
        self.commit(LEAVES[0], 'VALUE=2\n')
        p = self.plan()
        self.assertNotIn('test_runtime', p['tests'])
        self.assertEqual(self.base, p['selection']['reviewed_contract_anchor'])
        # A changed/new consumer is no longer covered by the unchanged reviewed boundary.
        self.commit(runtime, 'import subprocess\ndef run(command): return subprocess.run(command, check=True)\n')
        self.assertIn('test_runtime', self.plan()['tests'])
        with patch.object(planner, 'consumer_fingerprint', return_value='invalid'):
            p = self.plan()
            self.assertIn('test_runtime', p['tests'])
            self.assertIn('fingerprint anchor unavailable', ' '.join(p['reasons']))

    def test_new_source_domain_selects_reverse_consumer_and_test_only_is_scoped(self):
        write(self.repo, 'src/research_workbench/example.py', 'VALUE = 1\n')
        self.base = self.commit('tests/test_example.py', 'from research_workbench.example import VALUE\n')
        self.commit('src/research_workbench/example.py', 'VALUE = 2\n')
        p = self.plan(body=BODY.replace('R0', 'R2'))
        self.assertEqual(('focused', ['impact']), (p['behavioral_scope'], p['coverage_obligations']))
        self.assertEqual(['test_example'], p['tests'])
        self.assertEqual(['src/research_workbench/example.py'], p['coverage_modules'])
        self.assertFalse(p['package_smoke'] or p['repository_smoke'])
        self.assertEqual({'positive_tests': [], 'negative_tests': []}, p['impact_evidence'])
        planner.verify_plan(self.repo, p)

    def test_unrelated_test_edit_expands_behavior_but_not_executable_coverage(self):
        leaf = 'src/research_workbench/example.py'
        write(self.repo, leaf, 'VALUE=1\n')
        self.base = self.commit('tests/test_example.py', 'from research_workbench.example import VALUE\n')
        self.commit(leaf, 'VALUE=2\n')
        first = self.plan()
        self.commit('tests/test_unselected.py', 'import unittest\nVALUE=2\n')
        plan = self.plan()
        self.assertIn('test_unselected', plan['tests'])
        self.assertNotIn('test_unselected', plan['coverage_tests'])
        self.assertEqual(first['coverage_tests'], plan['coverage_tests'])
        self.assertEqual(['test_example'], plan['coverage_tests'])
        planner.verify_plan(self.repo, plan)

    def _proof_contract(self):
        leaf = 'src/research_workbench/proof_leaf.py'
        source = 'def value():\n    return 1 + 0\n'
        write(self.repo, 'src/research_workbench/__init__.py', '')
        write(self.repo, leaf, source)
        write(self.repo, 'tests/test_proof.py',
              'import unittest\nfrom research_workbench.proof_leaf import value\n'
              'class Proof(unittest.TestCase):\n'
              '    def test_positive(self): self.assertEqual(value(),1)\n'
              '    def test_negative(self): self.assertNotEqual(value(),0)\n'
              '    def test_behavioral(self): self.assertGreater(value(),0)\n')
        self.base = self.commit('tests/test_dynamic.py', 'import subprocess\nsubprocess.run(command)\n')
        policy = copy.deepcopy(self.policy)
        policy['surfaces']['proof'] = {'paths': [leaf], 'class': 'focused', 'groups': ['proof']}
        names = ['test_proof.Proof.test_positive', 'test_proof.Proof.test_negative']
        policy['groups']['proof'] = {'tests': ['test_proof'], 'downstream': [], 'coverage': [leaf],
            'coverage_tests': names, 'change_scope': 'function-body', 'package': False, 'repository': False,
            'impact_evidence': {'positive_tests': names[:1], 'negative_tests': names[1:]}}
        policy['consumer_fingerprint'] = planner.consumer_fingerprint(self.repo, 'HEAD', LEAVES + [leaf])
        return leaf, source, policy, names

    def test_exact_proof_contract_requires_base_acceptance_and_rejects_same_suite_mutant(self):
        leaf, source, policy, names = self._proof_contract()
        write(self.repo, planner.POLICY, planner.canonical(policy))
        self.commit(leaf, source.replace('1 + 0', '0 + 1'))
        self.assertIn('test_dynamic', self.plan()['coverage_tests'])
        self.base = command(self.repo, 'rev-parse', 'HEAD')
        self.commit(leaf, source)
        plan = self.plan()
        self.assertEqual(['test_proof'], plan['tests'])
        self.assertEqual(sorted(names), plan['coverage_tests'])
        self.assertEqual(set(names), set(plan['impact_evidence']['positive_tests'] + plan['impact_evidence']['negative_tests']))
        planner.verify_plan(self.repo, plan)
        def run():
            return subprocess.run([sys.executable, '-B', '-m', 'unittest', *names], cwd=self.repo,
                env={**os.environ, 'PYTHONPATH': str(self.repo / 'src') + os.pathsep + str(self.repo / 'tests')}, capture_output=True)
        self.assertEqual(0, run().returncode)
        self.commit(leaf, source.replace('1 + 0', '0 + 0'))
        self.assertEqual(sorted(names), self.plan()['coverage_tests'])
        self.assertNotEqual(0, run().returncode)

    def test_function_contract_restores_consumers_for_initialization_and_new_downstream(self):
        leaf, source, policy, names = self._proof_contract()
        self.base = self.commit(planner.POLICY, planner.canonical(policy))
        self.commit(leaf, source.replace('1 + 0', '0 + 1'))
        self.assertNotIn('test_dynamic', self.plan()['tests'])
        self.commit('tests/test_downstream.py', 'from research_workbench.proof_leaf import value\n')
        plan = self.plan()
        self.assertIn('test_downstream', plan['tests'])
        self.assertIn('test_downstream', plan['coverage_tests'])
        self.commit(leaf, source + '\nvalue()\n')
        plan = self.plan()
        self.assertIn('test_dynamic', plan['tests'])
        self.assertIn('test_dynamic', plan['coverage_tests'])
        self.assertIn('initialization/dependency', ' '.join(plan['reasons']))

    def test_function_contract_keeps_aliased_execution_opaque(self):
        leaf, source, policy, names = self._proof_contract()
        source = 'import subprocess as child\n' + source.replace('    return', '    child.run(command)\n    return')
        self.commit(leaf, source)
        policy['consumer_fingerprint'] = planner.consumer_fingerprint(self.repo, 'HEAD', LEAVES + [leaf])
        self.base = self.commit(planner.POLICY, planner.canonical(policy))
        self.commit(leaf, source.replace('1 + 0', '0 + 1'))
        plan = self.plan()
        self.assertIn('test_dynamic', plan['tests'])
        self.assertIn('test_dynamic', plan['coverage_tests'])
        self.assertIn('initialization/dependency', ' '.join(plan['reasons']))

    def test_proof_list_and_provenance_cannot_be_resigned_below_base_minimum(self):
        leaf, source, policy, names = self._proof_contract()
        self.base = self.commit(planner.POLICY, planner.canonical(policy))
        self.commit(leaf, source.replace('1 + 0', '0 + 1'))
        plan = self.plan()
        for key, value in [('coverage_tests', names[:1]), ('coverage_selection', {})]:
            forged = copy.deepcopy(plan)
            forged[key] = value
            forged.pop('plan_id')
            forged['plan_id'] = planner.digest(forged)
            with self.assertRaises(ValueError):
                planner.verify_plan(self.repo, forged)
        expanded = copy.deepcopy(plan)
        extra = 'test_proof.Proof.test_behavioral'
        expanded['coverage_tests'] = sorted(expanded['coverage_tests'] + [extra])
        expanded['coverage_selection'][extra] = ['agent requested additional proof']
        expanded.pop('plan_id'); expanded['plan_id'] = planner.digest(expanded)
        planner.verify_plan(self.repo, expanded)

    def test_critical_subject_uses_explicit_base_proof_and_keeps_all_acceptance(self):
        leaf, source, policy, names = self._proof_contract()
        authority = yaml.safe_load((self.repo / 'tests/coverage_policy.yaml').read_bytes())
        authority['critical_modules'].append(leaf)
        authority['negative_acceptance'].append({'surface': 'bounded-critical', 'modules': [leaf],
                                                 'positive_tests': names[:1], 'negative_tests': names[1:]})
        write(self.repo, 'tests/coverage_policy.yaml', yaml.safe_dump(authority))
        self.base = self.commit(planner.POLICY, planner.canonical(policy))
        self.commit(leaf, source.replace('1 + 0', '0 + 1'))
        plan = self.plan()
        self.assertEqual(sorted(names), plan['coverage_tests'])
        self.assertEqual([leaf], plan['coverage_modules'])
        self.assertEqual(names[:1], plan['impact_evidence']['positive_tests'])
        self.assertEqual(names[1:], plan['impact_evidence']['negative_tests'])
        planner.verify_plan(self.repo, plan)

    def test_accepted_deterministic_ids_avoid_reloading_mixed_behavioral_module(self):
        leaf = 'src/research_workbench/example.py'
        write(self.repo, leaf, 'VALUE=1\n')
        module = 'test_generic_execution_closeout'
        self.base = self.commit('tests/' + module + '.py', 'from research_workbench.example import VALUE\n')
        self.commit(leaf, 'VALUE=2\n')
        plan = self.plan()
        expected = [t for t in yaml.safe_load((self.repo / 'tests/coverage_policy.yaml').read_bytes())
                    ['suites']['coverage-quality']['test_ids'] if t.startswith(module + '.')]
        self.assertIn(module, plan['tests'])
        self.assertNotIn(module, plan['coverage_tests'])
        self.assertEqual(sorted(expected), plan['coverage_tests'])

    def test_ci_script_contract_requires_base_acceptance_and_keeps_new_consumers(self):
        leaf = '.github/scripts/check_leaf.py'
        write(self.repo, leaf, 'VALUE = 1\n')
        write(self.repo, 'tests/test_leaf.py', 'import runpy\nrunpy.run_path("' + leaf + '")\n')
        self.base = self.commit('tests/test_runtime.py', 'import subprocess\nsubprocess.run(command)\n')
        policy = copy.deepcopy(self.policy)
        policy['surfaces']['ci-leaf'] = {'paths': [leaf], 'class': 'focused', 'groups': ['ci-leaf']}
        policy['groups']['ci-leaf'] = {'tests': ['test_leaf'], 'downstream': [], 'coverage': [leaf],
                                       'package': False, 'repository': False}
        policy['consumer_fingerprint'] = planner.consumer_fingerprint(self.repo, self.base, LEAVES + [leaf])
        write(self.repo, planner.POLICY, planner.canonical(policy))
        self.commit(leaf, 'VALUE = 2\n')
        # A candidate cannot use its newly declared contract to approve its own exclusion.
        self.assertIn('test_runtime', self.plan()['tests'])
        # Only after that contract becomes the reviewed base may a subsequent leaf edit use it.
        self.base = command(self.repo, 'rev-parse', 'HEAD')
        self.commit(leaf, 'VALUE = 3\n')
        p = self.plan(body=BODY.replace('R0', 'R2'))
        self.assertEqual(('focused', 'impact', False, False), tuple(p[k] for k in
                         ('behavioral_scope', 'coverage_scope', 'package_smoke', 'repository_smoke')))
        self.assertEqual(['test_leaf'], p['tests'])
        self.assertEqual([leaf], p['coverage_modules'])
        self.assertEqual(self.base, p['selection']['reviewed_contract_anchor'])
        planner.verify_plan(self.repo, p)
        self.commit('tests/test_new_consumer.py', 'import runpy\nrunpy.run_path("' + leaf + '")\n')
        self.assertIn('test_new_consumer', self.plan()['tests'])
        # An import change invalidates the leaf boundary, retaining opaque execution again.
        self.commit(leaf, 'import subprocess\nVALUE = 3\n')
        self.assertIn('test_runtime', self.plan()['tests'])

    def test_monotonic_local_critical_addition_has_local_proof_and_cannot_remove_old_obligations(self):
        path = 'src/consumer.py'
        authority = yaml.safe_load((self.repo / 'tests/coverage_policy.yaml').read_bytes())
        before = copy.deepcopy(authority)
        authority['critical_modules'].append(path)
        authority['suites']['coverage-quality']['modules'].append('test_unselected')
        authority['negative_acceptance'].append({'surface': 'local-critical', 'modules': [path],
            'positive_tests': ['test_unselected.Other.test_existing'],
            'negative_tests': ['test_unselected.Other.test_negative']})
        self.commit('tests/coverage_policy.yaml', yaml.safe_dump(authority))
        p = self.plan(body=BODY.replace('R0', 'R2'))
        self.assertEqual(('focused', ['impact']), (p['behavioral_scope'], p['coverage_obligations']))
        self.assertEqual([path], p['coverage_modules'])
        self.assertEqual({}, p['changed_lines'])
        self.assertIn('test_unselected', p['tests'])
        self.assertFalse(p['package_smoke'] or p['repository_smoke'])
        planner.verify_plan(self.repo, p)
        for mutate in (lambda a:a['critical_modules'].pop(0), lambda a:a['negative_acceptance'].pop(0),
                       lambda a:a['suites']['coverage-quality']['modules'].pop(0)):
            bad = copy.deepcopy(authority); mutate(bad)
            self.assertFalse(planner.policy_delta(before, bad)[0])

    def test_comment_only_critical_change_has_no_executable_coverage_obligation(self):
        path = '.github/scripts/plan_ci.py'
        self.commit(path, (self.repo / path).read_text() + '\n# ordinary review comment\n')
        p = self.plan(body=BODY.replace('R0', 'R2'))
        self.assertEqual(('R2', 'none', []), (p['risk'], p['behavioral_scope'], p['coverage_obligations']))
        self.assertFalse(p['package_smoke'] or p['repository_smoke'])

    def test_selection_authority_semantics_require_full_behavior_independently(self):
        self.assertIsNone(planner.workflow_semantic(b'# empty workflow\n'))
        self.assertEqual(planner.workflow_semantic(b'flag: true\n'),
                         planner.workflow_semantic(b'{flag: true} # formatting\n'))
        self.assertNotEqual(planner.workflow_semantic(b'flag: true\n'),
                            planner.workflow_semantic(b'flag: "true"\n'))
        self.assertNotEqual(planner.workflow_semantic(b'flag: true\nflag: false\n'),
                            planner.workflow_semantic(b'flag: false\n'))
        workflow = '.github/workflows/ci.yml'
        write(self.repo, 'tests/test_runner_consumer.py', 'import run_unittest_suite\n')
        self.base = self.commit(workflow, 'name: CI\njobs: {}\n')
        paths = ['.github/scripts/plan_ci.py', '.github/scripts/ci_dependencies.py',
                 '.github/scripts/ci_checks.py', 'tests/run_unittest_suite.py', workflow]
        for path in paths:
            with self.subTest(path=path):
                command(self.repo, 'reset', '--hard', self.base)
                source = (self.repo / path).read_bytes()
                self.commit(path, source + b'\n# comment only\n')
                self.assertNotEqual('full', self.plan()['behavioral_scope'])
                command(self.repo, 'reset', '--hard', self.base)
                self.commit(path, source + (b'\nSELECTOR_FIXTURE = 1\n' if path.endswith('.py') else b'env: {REVISION: changed}\n'))
                p = self.plan(body=BODY.replace('R0', 'R2'))
                self.assertEqual('full', p['behavioral_scope'])
                self.assertIn('selection authority', ' '.join(p['obligation_reasons']['behavioral_scope']))
                expected = ['repository'] if path == workflow else ['impact', 'repository'] if path.startswith('tests/') else ['impact']
                self.assertEqual(expected, p['coverage_obligations'])
                self.assertFalse(p['package_smoke'] or p['repository_smoke'])
                self.assertFalse(p['blocked_reasons'])
                planner.verify_plan(self.repo, p)

    def test_candidate_selector_returning_no_tests_cannot_authorize_focused(self):
        path = '.github/scripts/ci_dependencies.py'
        defective = (self.repo / path).read_bytes() + b'''
original_select = select
def select(*args, **kwargs):
    result = original_select(*args, **kwargs)
    result[0]['selected'] = {}
    return result
'''
        head = self.commit(path, defective)
        event = Path(self.temp.name) / 'event.json'
        output = Path(self.temp.name) / 'plan.json'
        event.write_bytes(planner.canonical({'pull_request': {
            'base': {'sha': self.base, 'ref': 'develop', 'repo': {'full_name': 'Example/repo'}},
            'head': {'sha': head}, 'body': BODY.replace('R0', 'R2')}}))
        env = {**os.environ, 'GITHUB_OUTPUT': ''}
        process = subprocess.run([sys.executable, '.github/scripts/plan_ci.py', '--event', str(event),
            '--event-name', 'pull_request', '--output', str(output)], cwd=self.repo, env=env, capture_output=True, text=True)
        self.assertEqual(0, process.returncode, process.stderr)
        candidate = json.loads(output.read_bytes())
        self.assertEqual({}, candidate['selection']['selected'])
        self.assertEqual('full', candidate['behavioral_scope'])
        self.assertEqual(['impact'], candidate['coverage_obligations'])
        worker = '''
import json,sys
sys.path.insert(0,'.github/scripts')
import plan_ci as p
plan=json.load(open(sys.argv[1])); event=json.load(open(sys.argv[2]))
p.verify_plan(p.ROOT,plan,event)
plan.update(behavioral_scope='focused',change_class='focused')
plan['plan_id']=p.digest({k:v for k,v in plan.items() if k!='plan_id'})
try: p.verify_plan(p.ROOT,plan,event)
except ValueError as error:
    assert 'behavioral_scope' in str(error),str(error)
else: raise AssertionError('candidate worker accepted focused self-authorization')
'''
        checked = subprocess.run([sys.executable, '-c', worker, str(output), str(event)],
                                 cwd=self.repo, env=env, capture_output=True, text=True)
        self.assertEqual(0, checked.returncode, checked.stderr)

    def test_critical_syntax_error_blocks_instead_of_erasing_impact(self):
        self.commit('.github/scripts/plan_ci.py', 'if [')
        p = self.plan()
        self.assertEqual(['impact', 'repository'], p['coverage_obligations'])
        self.assertTrue(p['blocked_reasons'])
        with self.assertRaises(ValueError): planner.verify_plan(self.repo, p)

    def test_source_deletion_preserves_old_contract_consumers_without_candidate_lines(self):
        command(self.repo, 'rm', LEAVES[0])
        command(self.repo, 'commit', '-qm', 'delete source fixture')
        p = self.plan()
        self.assertEqual('focused', p['behavioral_scope'])
        self.assertIn('test_provider_adapters', p['tests'])
        self.assertNotIn(LEAVES[0], p['coverage_modules'])
        self.assertNotIn(LEAVES[0], p['changed_lines'])

    def test_actual_pragma_and_runner_semantics_keep_repository_obligation(self):
        self.commit(LEAVES[0], 'VALUE = 1  # pragma: no cover\n')
        p = self.plan()
        self.assertEqual(['impact', 'repository'], p['coverage_obligations'])
        self.assertEqual('focused', p['behavioral_scope'])
        self.assertTrue(planner.coverage_pragmas(b'VALUE=1 # pragma: no cover\n'))
        self.assertFalse(planner.coverage_pragmas(b'VALUE="pragma: no cover"\n'))
        command(self.repo, 'reset', '--hard', self.base)
        path = 'tests/run_unittest_suite.py'
        self.commit(path, (self.repo / path).read_text() + '\nSELECTOR_REVISION = 4\n')
        p = self.plan()
        self.assertEqual(['impact', 'repository'], p['coverage_obligations'])
        self.assertIn(path, p['coverage_modules'])
        self.assertIn('coverage authority changed: ' + path, p['obligation_reasons']['coverage_scope'])

    def test_public_cli_and_validation_consumers_independently_select_smokes(self):
        cli = 'src/research_workbench/cli.py'
        validator = 'src/research_workbench/validation/example.py'
        write(self.repo, cli, 'VALUE=1\n')
        write(self.repo, validator, 'VALUE=1\n')
        self.base = self.commit('tests/test_app.py', 'import research_workbench.cli\nimport research_workbench.validation.example\n')
        write(self.repo, cli, 'VALUE=2\n')
        self.commit(validator, 'VALUE=2\n')
        p = self.plan()
        self.assertEqual('focused', p['behavioral_scope'])
        self.assertEqual(['test_app'], p['tests'])
        self.assertTrue(p['package_smoke'] and p['repository_smoke'])

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

    def test_runner_main_executes_each_coverage_set_and_binds_real_results(self):
        from tests import run_unittest_suite as runner
        from contextlib import redirect_stdout, redirect_stderr
        import io
        authority = yaml.safe_load((self.repo / 'tests/coverage_policy.yaml').read_bytes())
        authority['suites']['coverage-quality'] = {'modules': ['test_unselected'],
                                                  'test_ids': ['test_ci_plan.Example.test_ok']}
        self.base = self.commit('tests/coverage_policy.yaml', yaml.safe_dump(authority))
        plan_path = Path(self.temp.name) / 'runner-plan.json'
        output = Path(self.temp.name) / 'runner-results.json'
        source = (self.repo / '.github/scripts/plan_ci.py').read_text()
        with patch.object(runner, 'ROOT', self.repo), patch.object(runner, 'TESTS', self.repo / 'tests'), \
             patch.object(runner, 'SOURCE', self.repo / 'src'), patch.dict(os.environ, {'GITHUB_EVENT_PATH':''}), \
             patch.dict(sys.modules), patch.object(sys, 'path', list(sys.path)), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            for name in ('test_ci_plan', 'test_unselected', 'test_documentation', 'test_pr_governance'):
                sys.modules.pop(name, None)
            for impact, repository in ((False, False), (False, True), (True, False), (True, True)):
                command(self.repo, 'reset', '--hard', self.base)
                self.commit('.github/scripts/plan_ci.py', source.replace("'fast': 0,", "'fast': 0 + 0,")) if impact else self.commit()
                p = self.plan(force_full=repository)
                plan_path.write_bytes(planner.canonical(p))
                argv = ['--suite', 'coverage-plan', '--plan', str(plan_path), '--policy', str(self.repo / 'tests/coverage_policy.yaml'),
                        '--json-output', str(output), '--verbosity', '0']
                if not impact and not repository:
                    with self.assertRaisesRegex(ValueError, 'coverage obligations'):
                        runner.main(argv)
                    argv[1] = 'focused'
                self.assertEqual(0, runner.main(argv))
                receipt = json.loads(output.read_bytes())
                self.assertTrue(receipt['successful'])
                self.assertEqual(p['plan_id'], receipt['plan_id'])
                self.assertEqual(p['coverage_obligations'], receipt['coverage_obligations'])
                self.assertEqual('coverage-quality' if repository else 'impact' if impact else 'focused', receipt['suite'])
                self.assertEqual(len({r['id'] for r in receipt['tests']}), receipt['test_count'])

    def test_decorators_are_executable_impact_and_comments_keep_repository_guard(self):
        path = LEAVES[0]
        source = 'def identity(f): return f\n@identity\ndef example(): return 1\n# review note\n'
        head = self.commit(path, source)
        uncertain = []
        mapped = planner.coverage_lines(self.repo, head, {path: [2, 4]}, uncertain)
        self.assertEqual([2], mapped[path])
        self.assertFalse(uncertain)
        self.assertEqual({path: []}, planner.coverage_lines(self.repo, head, {path: [4]}))

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
                           ('impact_evidence', {}), ('behavioral_scope', 'none'), ('selection', {})]:
            tampered = copy.deepcopy(p); tampered[key] = value
            tampered['plan_id'] = planner.digest({k:v for k,v in tampered.items() if k != 'plan_id'})
            with self.subTest(key=key), self.assertRaises(ValueError): planner.verify_plan(self.repo, tampered, event)

    def test_coverage_authority_semantics_require_repository_proof(self):
        path = 'tests/coverage_policy.yaml'
        initial = yaml.safe_load((self.repo / path).read_bytes())
        for mutate in (lambda p:p['thresholds']['global'].update(line=91),
                       lambda p:p.update(source_root='src'), lambda p:p['critical_modules'].pop(),
                       lambda p:p['justified_exclusions'].clear(), lambda p:p['negative_acceptance'].pop()):
            command(self.repo, 'reset', '--hard', self.base)
            policy = copy.deepcopy(initial); mutate(policy)
            self.commit(path, yaml.safe_dump(policy))
            p = self.plan()
            self.assertEqual(('focused', 'repository'), (p['behavioral_scope'], p['coverage_scope']))
            self.assertFalse(p['package_smoke'] or p['repository_smoke'])
        source = (self.repo / '.github/scripts/plan_ci.py').read_text()
        self.commit('.github/scripts/plan_ci.py', source + '\nimport fractions\n')
        p = self.plan()
        self.assertEqual(['impact', 'repository'], p['coverage_obligations'])
        self.assertEqual(['.github/scripts/plan_ci.py'], p['coverage_modules'])
        self.assertTrue(p['coverage_lines']['.github/scripts/plan_ci.py'])
        self.assertEqual('full', p['behavioral_scope'])
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
        for key in ('coverage_modules', 'changed_lines', 'coverage_lines', 'impact_evidence'):
            self.assertEqual(bounded[key], combined[key])
        self.assertTrue(set(bounded['coverage_tests']) <= set(combined['coverage_tests']))
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
            self.assertEqual(('full', 'repository' if kwargs.get('integration') else 'impact+repository', True, True),
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
        self.assertEqual(('R2', 'focused', 'none', False, False),
            tuple(p[k] for k in ('risk', 'behavioral_scope', 'coverage_scope', 'package_smoke', 'repository_smoke')))

    def test_smokes_and_coverage_config_are_independent_of_full_behavior(self):
        cases = [('schemas/new.json', '{}', True, True), ('registry/new.yaml', 'version: 1', False, True),
                 ('examples/new.yaml', 'example: true', False, True),
                 ('pyproject.toml', (self.repo / 'pyproject.toml').read_text().replace('version = "0.1.0"', 'version = "0.1.1"'), True, False)]
        for path, content, package, repository in cases:
            command(self.repo, 'reset', '--hard', self.base)
            self.commit(path, content)
            p = self.plan(body=BODY.replace('R0', 'R2'))
            self.assertEqual(('none', 'none', package, repository),
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
                       lambda p:next(m for m in p['negative_acceptance'] if path in m['modules']).update(positive_tests=[])):
            bad = copy.deepcopy(authority); mutate(bad)
            with patch.object(planner, 'read_at', side_effect=lambda r,c,p: yaml.safe_dump(bad).encode()
                              if p == 'tests/coverage_policy.yaml' else raw(r,c,p)):
                blocked = self.plan()
                self.assertEqual(['impact', 'repository'], blocked['coverage_obligations'])
                self.assertTrue(blocked['blocked_reasons'])
                with self.assertRaises(ValueError): planner.verify_plan(self.repo, blocked)
        self.commit(path, original + '\nimport fractions\n')
        p = self.plan()
        self.assertEqual(['impact'], p['coverage_obligations'])
        planner.verify_plan(self.repo, p)

    def test_candidate_policy_and_fingerprint_cannot_approve_new_consumer_closure(self):
        write(self.repo, 'tests/test_new_consumer.py', 'import runpy\nrunpy.run_path("' + LEAVES[0] + '")\n')
        self.commit(LEAVES[0], 'VALUE = 2\n')
        candidate = copy.deepcopy(self.policy)
        candidate['consumer_fingerprint'] = planner.consumer_fingerprint(self.repo, 'HEAD', LEAVES)
        candidate['groups']['provider-wire']['tests'].append('test_new_consumer')
        self.commit(planner.POLICY, planner.canonical(candidate))
        p = self.plan()
        self.assertEqual(['impact'], p['coverage_obligations'])
        self.assertIn('test_new_consumer', p['tests'])
        self.assertIn('test_provider_adapters', p['tests'])
        self.assertEqual('focused', p['behavioral_scope'])


if __name__ == '__main__':
    unittest.main()
