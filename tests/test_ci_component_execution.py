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
            self.assertEqual(value['execution_authority'], 'candidate-unaccepted')
        with self.assertRaises(ValueError):
            runner.make_plan(self.root, '--bad', self.head)
