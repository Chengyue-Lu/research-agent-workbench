"""Small execution/identity regressions for the component-CI candidate."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.github/scripts'
sys.path.insert(0, str(SCRIPTS))
import run_component_ci as runner


class ComponentExecutionTests(unittest.TestCase):
    def test_daily_matrix_splits_large_baseline_only_and_keeps_profiles_distinct(self):
        value = dict(profile='component', python_versions=['3.11', '3.13'], docs=False,
                     smoke=False, selected_tests=['test_a', 'test_b', 'test_c', 'test_d'])
        matrix = runner.execution_matrix(value)
        self.assertEqual([0, 1, 2, 3], [row['shard_index'] for row in matrix if row['python'] == '3.11'])
        self.assertEqual([1], [row['shard_count'] for row in matrix if row['python'] == '3.13'])
        self.assertEqual(len(matrix), len({row['artifact_name'] for row in matrix}))
        for profile in ('checkpoint', 'release-checkpoint', 'integration-smoke'):
            value['profile'] = profile
            self.assertTrue(all(row['shard_count'] == 1 for row in runner.execution_matrix(value)))
        value.update(profile='component', selected_tests=['test_documentation'])
        self.assertTrue(all(row['shard_count'] == 1 for row in runner.execution_matrix(value)))

    def test_four_real_shards_cover_collection_once_and_keep_module_fixture_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'tests').mkdir()
            names = [f'test_component_shard_probe_{index}' for index in range(4)]
            for name in names:
                (root/'tests'/f'{name}.py').write_text(
                    'from pathlib import Path\nimport unittest\nclass Probe(unittest.TestCase):\n'
                    '    @classmethod\n    def setUpClass(cls):\n'
                    '        path = Path(__file__).with_suffix(".fixture-count")\n'
                    '        with path.open("a") as output: output.write("setup\\n")\n'
                    '    def test_a(self): self.assertTrue(True)\n'
                    '    def test_b(self): self.assertEqual(1 + 1, 2)\n', encoding='utf-8')
            # Imported aliases are collected by unittest but belong to their
            # original class/module and must not cause repeated execution.
            with (root/'tests'/f'{names[-1]}.py').open('a', encoding='utf-8') as output:
                output.write(f'from {names[0]} import Probe as ImportedProbe\n')
            sys.path.insert(0, str(ROOT/'tests'))
            try:
                parts = [runner.execute_modules(root, names, stream=io.StringIO(),
                         shard_index=index, shard_count=4) for index in range(4)]
                inventory = parts[0]['inventory']
                self.assertEqual(8, len(inventory))
                self.assertTrue(all(part['success'] and part['inventory'] == inventory for part in parts))
                received = [runner.canonical_record_id(row['id']) for part in parts for row in part['records']]
                self.assertEqual(inventory, sorted(received))
                self.assertEqual(len(received), len(set(received)))
                for index, part in enumerate(parts):
                    self.assertEqual(runner.shard_inventory(inventory, index, 4),
                                     sorted(runner.canonical_record_id(row['id']) for row in part['records']))
                for name in names:
                    self.assertEqual(['setup'], (root/'tests'/f'{name}.fixture-count').read_text().splitlines())
            finally:
                sys.path.pop(0)
                for name in names:
                    sys.modules.pop(name, None)

    def test_matrix_identity_refuses_foreign_counts_and_incomplete_parameters_before_execution(self):
        value = dict(profile='component', python_versions=['3.11'], docs=False, smoke=False,
                     selected_tests=['test_a', 'test_b', 'test_c', 'test_d'],
                     head_sha='a'*40, plan_sha256='b'*64)
        calls = []
        def execute(*args, **kwargs):
            calls.append((args, kwargs))
            return {}
        for index, count in ((0, 1), (0, 3), (4, 4), (-1, 4), (True, 4), (0, True), (None, 4), (0, None)):
            with self.subTest(index=index, count=count), self.assertRaises(ValueError):
                runner.execute_plan(ROOT, value, python_version='3.11', execute=execute,
                                    shard_index=index, shard_count=count)
        self.assertEqual([], calls)
        for inventory in (['test_a.A.test_b', 'test_a.A.test_b'],
                          ['test_b.B.test_c', 'test_a.A.test_b'], ['outside'], 'test_a.A.test_b'):
            with self.subTest(inventory=inventory), self.assertRaises(ValueError):
                runner.shard_inventory(inventory, 0, 4)

    def test_rename_copy_and_deleted_git_paths_are_preserved(self):
        rows = runner.changed_paths(b'R100\0old name.py\0new name.py\0D\0removed.py\0C50\0source.py\0copy.py\0')
        self.assertEqual(rows, [{'status': 'R', 'old_path': 'old name.py', 'path': 'new name.py'},
                                {'status': 'D', 'path': 'removed.py'},
                                {'status': 'C', 'old_path': 'source.py', 'path': 'copy.py'}])
        for raw in (b'M\0file', b'R100\0old\0', b'???\0file\0'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                runner.changed_paths(raw)

    def test_aggregate_rejects_failed_skipped_cancelled_and_missing_jobs(self):
        for plan in ('success', 'failure', 'skipped', 'cancelled', ''):
            for executed in ('success', 'failure', 'skipped', 'cancelled', ''):
                with self.subTest(plan=plan, execution=executed):
                    self.assertEqual(runner.aggregate(plan, executed), plan == executed == 'success')

    def test_only_baseline_runs_business_except_release_checkpoint(self):
        value = dict(profile='component', python_versions=['3.11', '3.13'],
                     selected_tests=['test_ci_components'], docs=True, smoke=False,
                     head_sha='a'*40, plan_sha256='b'*64)
        calls = []
        def execute(repo, names):
            calls.append(names)
            return {'success': True, 'tests_run': len(names)}
        runner.execute_plan(ROOT, value, python_version='3.11', execute=execute)
        runner.execute_plan(ROOT, value, python_version='3.13', execute=execute)
        value['profile'] = 'release-checkpoint'
        runner.execute_plan(ROOT, value, python_version='3.13', execute=execute)
        self.assertEqual(calls, [['test_ci_components', 'test_documentation'], [],
                                 ['test_ci_components', 'test_documentation']])
        with self.assertRaises(ValueError):
            runner.execute_plan(ROOT, value, python_version='3.12', execute=execute)

    def test_real_test_failure_and_empty_collection_are_not_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'tests').mkdir()
            # Reuse the real recorder but run only these two temporary test cases.
            sys.path.insert(0, str(ROOT/'tests'))
            try:
                path = root/'tests/test_component_runner_probe.py'
                path.write_text('import unittest\nclass Probe(unittest.TestCase):\n'
                                '    def test_pass(self): self.assertTrue(True)\n'
                                '    def test_failure(self): self.fail("known failure")\n', encoding='utf-8')
                result = runner.execute_modules(root, ['test_component_runner_probe'], stream=io.StringIO())
                self.assertFalse(result['success'])
                self.assertEqual((result['tests_run'], result['failures']), (2, 1))
                self.assertEqual({row['outcome'] for row in result['records']}, {'passed', 'failed'})
                (root/'tests/test_component_empty_probe.py').write_text('value = 1\n', encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'no tests'):
                    runner.execute_modules(root, ['test_component_empty_probe'], stream=io.StringIO())
                with self.assertRaisesRegex(ValueError, 'no tests'):
                    runner.execute_modules(root, ['test_component_runner_probe', 'test_component_empty_probe'],
                                           stream=io.StringIO())
                with self.assertRaisesRegex(ValueError, 'collection failed'):
                    runner.execute_modules(root, ['test_no_such_component_probe'], stream=io.StringIO())
            finally:
                sys.path.pop(0)
                for name in ('test_component_runner_probe', 'test_component_empty_probe'):
                    sys.modules.pop(name, None)


class ComponentGitPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.git('init', '--quiet')
        cls.git('config', 'user.name', 'Component CI fixture')
        cls.git('config', 'user.email', 'fixture@example.invalid')
        for path in (ROOT/'tests').glob('test_*.py'):
            target = cls.root/'tests'/path.name
            target.parent.mkdir(exist_ok=True)
            target.write_text('fixture = True\n', encoding='utf-8')
        policy = ROOT/'tests/ci_components.json'
        (cls.root/'tests/ci_components.json').write_bytes(policy.read_bytes())
        cls.source = cls.root/'src/research_workbench/evaluation/harness_review.py'
        cls.source.parent.mkdir(parents=True)
        cls.source.write_text('value = 1\n', encoding='utf-8')
        cls.git('add', '.'); cls.git('commit', '--quiet', '-m', 'baseline')
        cls.base = cls.git('rev-parse', 'HEAD').strip()
        cls.source.write_text('value = 2\n', encoding='utf-8')
        cls.git('add', '.'); cls.git('commit', '--quiet', '-m', 'component change')
        cls.head = cls.git('rev-parse', 'HEAD').strip()

    @classmethod
    def git(cls, *args):
        return subprocess.check_output(['git', '-C', str(cls.root), *args], encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_exact_git_plan_roundtrip_and_resigned_scope_forgery_rejected(self):
        value = runner.make_plan(self.root, self.base, self.head)
        self.assertIn('evaluation', value['components'])
        self.assertTrue(value['selected_tests'])
        path = self.root/'plan.json'
        runner.save(path, value)
        self.assertEqual(runner.load_plan(path, self.root), value)
        forged = copy.deepcopy(value)
        forged['selected_tests'] = []
        forged.pop('plan_sha256')
        forged['plan_sha256'] = hashlib.sha256(runner.canonical(forged)).hexdigest()
        runner.save(path, forged)
        with self.assertRaisesRegex(ValueError, 'Git inputs'):
            runner.load_plan(path, self.root)

    def test_integration_and_checkpoint_use_distinct_meanings(self):
        smoke = runner.make_plan(self.root, self.base, self.head, 'integration-smoke')
        full = runner.make_plan(self.root, self.base, self.head, 'checkpoint')
        release = runner.make_plan(self.root, self.base, self.head, 'release-checkpoint')
        self.assertEqual(smoke['selected_tests'], [])
        self.assertTrue(smoke['smoke'])
        self.assertEqual(full['selected_tests'], sorted(p.stem for p in (self.root/'tests').glob('test_*.py')))
        self.assertEqual(full['python_versions'], ['3.11'])
        self.assertEqual(release['python_versions'], ['3.11', '3.13'])
        for value in (smoke, full, release):
            self.assertEqual(value['execution_authority'], 'profile-result-only')
        with self.assertRaises(ValueError):
            runner.make_plan(self.root, '--bad', self.head)

    def test_plan_cli_exports_the_same_matrix_used_by_result_consumers(self):
        output = self.root/'matrix-plan.json'
        github_output = self.root/'github-output.txt'
        self.assertEqual(0, runner.main(['plan', '--repo', str(self.root),
            '--base', self.base, '--head', self.head, '--output', str(output),
            '--github-output', str(github_output)]))
        plan = json.loads(output.read_bytes())
        rows = dict(line.split('=', 1) for line in github_output.read_text().splitlines())
        self.assertEqual(runner.execution_matrix(plan), json.loads(rows['execution_matrix']))
