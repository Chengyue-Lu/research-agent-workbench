"""Real Git and isolated-process acceptance for the independent CI minimum."""
from __future__ import annotations

import copy
from contextlib import contextmanager, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import runpy
import zlib

from tests import test_ci_plan as fixture
import ci_minimum_witness as witness

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = '.github/scripts/ci_minimum_witness.py'


class MinimumWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.PlannerTests.setUpClass()
        cls.workspace = tempfile.TemporaryDirectory()
        cls.trusted_seed = Path(cls.workspace.name) / 'trusted'
        fixture.command(Path(cls.workspace.name), 'clone', '-q', '--no-hardlinks',
                        '-c', 'core.autocrlf=false', '-c', 'user.name=CI fixture',
                        '-c', 'user.email=fixture@example.invalid',
                        str(fixture.PlannerTests.seed), str(cls.trusted_seed))
        fixture.write(cls.trusted_seed, SCRIPT, (ROOT / SCRIPT).read_bytes())
        fixture.command(cls.trusted_seed, 'add', SCRIPT)
        fixture.command(cls.trusted_seed, 'commit', '-qm', 'externally pinned checker fixture')
        cls.witness_commit = fixture.command(cls.trusted_seed, 'rev-parse', 'HEAD')

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()
        fixture.PlannerTests.tearDownClass()

    def setUp(self):
        self.case = fixture.PlannerTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.repo = self.case.repo
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.files = Path(self.temporary.name)
        self.calls = 0

    def plan(self, path='tests/test_unselected.py', data='import unittest\nclass Other(unittest.TestCase):\n    def test_existing(self): assert True\n'):
        self.head = self.case.commit(path, data)
        return self.case.plan()

    def invoke(self, candidate, *, trusted=None, env=None, isolated=True, **overrides):
        self.calls += 1
        self.plan_path = self.files / ('plan-' + str(self.calls) + '.json')
        self.body_path = self.files / ('body-' + str(self.calls) + '.txt')
        self.output_path = self.files / ('receipt-' + str(self.calls) + '.json')
        self.plan_path.write_bytes(fixture.planner.canonical(candidate))
        self.body_path.write_text(fixture.BODY, encoding='utf-8')
        values = {'repository': 'Example/repo', 'repo': self.repo, 'base': self.case.base,
                  'head': self.head, 'target': self.head, 'body': self.body_path, 'plan': self.plan_path,
                  'expected-witness': self.witness_commit, 'output': self.output_path, **overrides}
        args = [sys.executable, *(['-I'] if isolated else []), str((trusted or self.trusted_seed) / SCRIPT)]
        for key, value in values.items():
            args.extend(['--' + key, str(value)])
        process = subprocess.run(args, cwd=self.repo, env=env, capture_output=True, text=True)
        output = Path(values['output'])
        receipt = json.loads(output.read_bytes()) if output.exists() and output != self.plan_path else None
        return process, receipt

    def resign(self, plan):
        unsigned = dict(plan)
        unsigned.pop('plan_id')
        plan['plan_id'] = fixture.planner.digest(unsigned)
        return plan

    def assert_block(self, result, reason):
        process, receipt = result
        self.assertEqual(1, process.returncode, process.stderr)
        self.assertEqual('BLOCK', receipt['status'])
        self.assertIn(reason, receipt['reason'])

    def test_real_accepted_minimum_and_isolated_candidate_shadow_modules(self):
        plan = self.plan()
        self.assertEqual('focused', plan['behavioral_scope'])
        for name in ('yaml.py', 'plan_ci.py', 'ci_dependencies.py', 'sitecustomize.py'):
            fixture.write(self.repo, name, 'raise RuntimeError("candidate executed")\n')
        process, receipt = self.invoke(plan, env={**os.environ, 'PYTHONPATH': str(self.repo),
                                                'PYTHONSTARTUP': str(self.repo / 'yaml.py')})
        self.assertEqual(0, process.returncode, process.stderr)
        self.assertEqual('PASS', receipt['status'])
        self.assertEqual(plan, receipt['minimum_plan'])
        self.assertEqual(self.witness_commit, receipt['witness_commit'])
        self.assertEqual(self.case.base, receipt['accepted_planner_base'])
        self.assertEqual(3, len(receipt['loaded_project_helpers']))
        self.assertFalse(receipt['checker_acceptance_proved'])
        self.assertFalse(receipt['execution_authority'])
        self.assertFalse(Path(receipt['yaml_runtime']['origin']).is_relative_to(self.repo))

    def test_resigned_plan_cannot_remove_required_tests(self):
        plan = self.plan()
        plan['tests'] = []
        self.assert_block(self.invoke(self.resign(plan)), 'drops required tests')

    def test_resigned_plan_cannot_remove_coverage_or_smokes(self):
        plan = self.plan('src/consumer.py', 'VALUE = 2\n')
        self.assertTrue(plan['coverage_obligations'])
        self.assertTrue(plan['package_smoke'])
        self.assertTrue(plan['repository_smoke'])
        for key in ('coverage', 'package_smoke', 'repository_smoke'):
            with self.subTest(obligation=key):
                reduced = copy.deepcopy(plan)
                if key == 'coverage':
                    reduced.update(coverage_scope='none', coverage_obligations=[])
                    reason = 'coverage obligations'
                else:
                    reduced[key] = False
                    reason = key
                self.assert_block(self.invoke(self.resign(reduced)), reason)

    def test_candidate_policy_and_bootstrap_rewrite_do_not_choose_minimum(self):
        source = (self.repo / '.github/scripts/plan_ci.py').read_text(encoding='utf-8')
        self.assertIn('if semantic_change and path in SELECTION_AUTHORITY:', source)
        fixture.write(self.repo, '.github/scripts/plan_ci.py',
                      source.replace('if semantic_change and path in SELECTION_AUTHORITY:', 'if False:'))
        fixture.write(self.repo, fixture.planner.POLICY, '{}\n')
        plan = self.plan()
        self.assertEqual('full', plan['behavioral_scope'])
        # Accepted planner reads only the base policy despite a candidate rewrite.
        process, receipt = self.invoke(plan)
        self.assertEqual(0, process.returncode, process.stderr)
        self.assertEqual(plan['policy_sha256'], receipt['minimum_plan']['policy_sha256'])
        reduced = copy.deepcopy(plan)
        reduced.update(behavioral_scope='focused', change_class='focused', tests=[],
                       coverage_scope='none', coverage_obligations=[], package_smoke=False, repository_smoke=False)
        self.assert_block(self.invoke(self.resign(reduced)), 'behavioral_scope')

    def test_external_binding_and_metadata_are_not_taken_from_plan(self):
        plan = self.plan()
        reduced = copy.deepcopy(plan)
        reduced['binding']['repository'] = 'Attacker/repo'
        self.assert_block(self.invoke(self.resign(reduced)), 'binding mismatch')
        self.assert_block(self.invoke(plan, target=self.case.base), 'target is not exact PR merge candidate')
        self.assert_block(self.invoke(plan, base='0' * 40), 'returned non-zero exit status')
        body = self.files / 'authoritative-body.txt'
        body.write_text(fixture.BODY.replace('R0', 'R2'), encoding='utf-8')
        self.assert_block(self.invoke(plan, body=body), 'lowers governance risk')

    def test_dirty_pinned_checker_helpers_and_wrong_identity_block(self):
        plan = self.plan()
        trusted = self.files / 'trusted'
        fixture.command(self.files, 'clone', '-q', '--no-hardlinks', '-c', 'core.autocrlf=false',
                        str(self.trusted_seed), str(trusted))
        for path in (SCRIPT, '.github/scripts/ci_dependencies.py'):
            with self.subTest(path=path):
                original = (trusted / path).read_bytes()
                fixture.write(trusted, path, original + b'\n# dirty\n')
                self.assert_block(self.invoke(plan, trusted=trusted), 'source drift')
                fixture.write(trusted, path, original)
        self.assert_block(self.invoke(plan, **{'expected-witness': self.case.base}), 'caller-pinned commit')
        self.assert_block(self.invoke(plan, isolated=False), 'Python -I')

    def test_missing_and_nonregular_accepted_helper_block(self):
        # An otherwise coherent caller pin cannot make absent/nonregular accepted
        # source executable. Test accepted-side facts, not candidate file reads.
        for mode in ('deleted', '100755'):
            with self.subTest(mode=mode):
                if mode == 'deleted':
                    fixture.command(self.repo, 'rm', '.github/scripts/ci_dependencies.py')
                else:
                    fixture.command(self.repo, 'reset', '--hard', self.case.base)
                    fixture.command(self.repo, 'update-index', '--chmod=+x', '.github/scripts/ci_dependencies.py')
                fixture.command(self.repo, 'commit', '-qm', 'unsupported accepted helper')
                base = fixture.command(self.repo, 'rev-parse', 'HEAD')
                self.head = self.case.commit()
                plan = fixture.planner.make_plan(self.repo, base=base, head=self.head, target=self.head,
                                                repository='Example/repo', body=fixture.BODY)
                self.assert_block(self.invoke(plan, base=base), 'trusted blob')

    def test_existing_outputs_and_input_alias_are_never_overwritten(self):
        plan = self.plan()
        output = self.files / 'existing.json'
        output.write_bytes(b'{"historic":true}')
        process, _ = self.invoke(plan, output=output)
        self.assertNotEqual(0, process.returncode)
        self.assertEqual(b'{"historic":true}', output.read_bytes())
        # The same path supplied as both candidate input and output is refused.
        plan_path = self.files / 'input-plan.json'
        raw = fixture.planner.canonical(plan)
        plan_path.write_bytes(raw)
        process, _ = self.invoke(plan, plan=plan_path, output=plan_path)
        self.assertNotEqual(0, process.returncode)
        self.assertEqual(raw, plan_path.read_bytes())


class MinimumWitnessPathTests(unittest.TestCase):
    """Measure real source paths; independent acceptance stays in the CLI class.

    A sys proxy lets these in-process path tests exercise the isolation guard.
    Git authentication, copied bytes, planner calculations and child execution
    remain real; this proxy is never an independent isolation certificate.
    """
    setUpClass = classmethod(MinimumWitnessTests.setUpClass.__func__)
    tearDownClass = classmethod(MinimumWitnessTests.tearDownClass.__func__)
    setUp = MinimumWitnessTests.setUp
    plan = MinimumWitnessTests.plan
    resign = MinimumWitnessTests.resign

    def overwrite(self, path, raw):
        # Git may create read-only objects and hidden Windows .git markers.
        path.chmod(path.stat().st_mode | 0o200)
        with path.open('r+b') as stream:
            stream.write(raw)
            stream.truncate()

    @contextmanager
    def outer(self, isolated=1):
        proxy = SimpleNamespace(flags=SimpleNamespace(isolated=isolated), executable=sys.executable)
        with patch.object(witness, '__file__', str(self.trusted_seed / SCRIPT)), patch.object(witness, 'sys', proxy):
            yield

    def call(self, plan, **overrides):
        return witness.witness(self.repo, **{'repository': 'Example/repo', 'base': self.case.base,
            'head': self.head, 'target': self.head, 'body': fixture.BODY, 'plan': plan,
            'expected_witness': self.witness_commit, **overrides})

    def request(self, plan):
        trusted = self.files / 'worker-tree'
        records = {}
        for path in witness.HELPERS:
            raw, record = witness.blob(self.repo, self.case.base, path)
            fixture.write(trusted, path, raw)
            records[path] = record
        return {'trusted': str(trusted), 'repo': str(self.repo), 'plan': plan, 'sources': records,
                'inputs': {'repository': 'Example/repo', 'base': self.case.base, 'head': self.head,
                           'target': self.head, 'body': fixture.BODY, 'base_ref': 'develop'}}

    @contextmanager
    def loaded_helpers(self):
        names = ('plan_ci', 'ci_dependencies', 'ci_governance')
        modules = {name: sys.modules.pop(name, None) for name in names}
        paths = list(sys.path)
        try:
            yield
        finally:
            sys.path[:] = paths
            for name in names:
                sys.modules.pop(name, None)
                if modules[name] is not None:
                    sys.modules[name] = modules[name]

    def test_json_environment_and_exact_input_contract(self):
        raw = witness.canonical({'unicode': '路径', 'value': [1, False]})
        self.assertEqual({'unicode': '路径', 'value': [1, False]}, witness.read_json(raw))
        self.assertEqual(64, len(witness.digest(raw)))
        for raw in (b'{"x":1,"x":2}', b' ' * (witness.LIMIT + 1)):
            with self.subTest(size=len(raw)), self.assertRaises(ValueError):
                witness.read_json(raw)
        for value in ('HEAD', 'a' * 39, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                witness.exact(value)
        self.assertEqual('a' * 40, witness.exact('a' * 40))
        with patch.dict(os.environ, {'PYTHONPATH': 'bad', 'GIT_CONFIG_COUNT': '1', 'KEEP_WITNESS_INPUT': 'yes'}):
            result = witness.environment()
            self.assertNotIn('PYTHONPATH', result)
            self.assertNotIn('GIT_CONFIG_COUNT', result)
            self.assertEqual('yes', result['KEEP_WITNESS_INPUT'])

    def test_filesystem_git_transport_guards_and_worktree_resolution(self):
        common = self.repo / '.git'
        self.assertEqual(common, witness.database_path(self.repo))
        for name in ('objects/info/alternates', 'info/grafts', 'shallow', 'objects/pack/payload.promisor'):
            path = common / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('untrusted', encoding='utf-8')
            try:
                with self.subTest(path=name), self.assertRaisesRegex(ValueError, 'unsupported'):
                    witness.database_path(self.repo)
            finally:
                path.unlink()
        config = common / 'config'
        original = config.read_bytes()
        for extra in (b'\n[include]\n path = secret\n', b'\n[remote "partial"]\n promisor = true\n'):
            config.write_bytes(original + extra)
            try:
                with self.assertRaisesRegex(ValueError, 'nonstandard'):
                    witness.database_path(self.repo)
            finally:
                config.write_bytes(original)
        linked = self.files / 'linked'
        fixture.command(self.repo, 'worktree', 'add', '-q', '--detach', str(linked), self.case.base)
        self.assertEqual(common.resolve(), witness.database_path(linked))
        marker = linked / '.git'
        original = marker.read_bytes()
        self.overwrite(marker, b'unrecognized marker')
        with self.assertRaisesRegex(ValueError, 'marker'):
            witness.database_path(linked)
        self.overwrite(marker, original)
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            witness.database_path(self.files / 'absent')

    def test_blob_mode_missing_size_and_real_corruption(self):
        path = '.github/scripts/ci_dependencies.py'
        raw, record = witness.blob(self.repo, self.case.base, path)
        self.assertEqual('100644', record['mode'])
        with self.assertRaisesRegex(ValueError, 'missing'):
            witness.blob(self.repo, self.case.base, 'absent.py')
        with patch.object(witness, 'LIMIT', 1), self.assertRaisesRegex(ValueError, 'oversized'):
            witness.blob(self.repo, self.case.base, path)
        fixture.command(self.repo, 'update-index', '--chmod=+x', path)
        fixture.command(self.repo, 'commit', '-qm', 'unsupported executable mode')
        changed = fixture.command(self.repo, 'rev-parse', 'HEAD')
        with self.assertRaisesRegex(ValueError, 'mode'):
            witness.blob(self.repo, changed, path)
        oid = record['git_blob']
        object_path = self.repo / '.git/objects' / oid[:2] / oid[2:]
        payload = raw.replace(b'import ast', b'import sys', 1)
        self.overwrite(object_path, zlib.compress(b'blob ' + str(len(payload)).encode() + b'\0' + payload))
        with self.assertRaisesRegex(ValueError, 'identity'):
            witness.blob(self.repo, self.case.base, path)

    def test_full_object_check_refuses_corrupt_intermediate_tree_and_grafts(self):
        self.plan()
        oid = fixture.command(self.repo, 'rev-parse', self.case.base + '^{tree}')
        raw = subprocess.check_output(['git', '-C', str(self.repo), 'cat-file', 'tree', oid])
        corrupt = raw.replace(b'README.md', b'READMX.md', 1)
        self.assertNotEqual(raw, corrupt)
        object_path = self.repo / '.git/objects' / oid[:2] / oid[2:]
        self.overwrite(object_path, zlib.compress(b'tree ' + str(len(corrupt)).encode() + b'\0' + corrupt))
        with self.assertRaises(subprocess.CalledProcessError):
            witness.copy_database(self.repo, self.files / 'corrupt-copy.git')
        graft = self.repo / '.git/info/grafts'
        graft.write_text(self.head + '\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'grafts'):
            witness.copy_database(self.repo, self.files / 'graft-copy.git')
        self.assertFalse((self.files / 'graft-copy.git').exists())

    def test_input_topology_uses_real_raw_commits(self):
        self.plan()
        witness.input_commits(self.repo, self.case.base, self.head, self.head)
        tree = fixture.command(self.repo, 'rev-parse', self.head + '^{tree}')
        target = subprocess.check_output(['git', '-C', str(self.repo), 'commit-tree', tree,
            '-p', self.case.base, '-p', self.head], input=b'actual merge candidate\n').decode().strip()
        witness.input_commits(self.repo, self.case.base, self.head, target)
        with self.assertRaisesRegex(ValueError, 'target'):
            witness.input_commits(self.repo, self.case.base, self.head, self.case.base)
        raw = subprocess.check_output(['git', '-C', str(self.repo), 'cat-file', 'commit', target])
        corrupt = raw + b'changed commit message\n'
        object_path = self.repo / '.git/objects' / target[:2] / target[2:]
        self.overwrite(object_path, zlib.compress(b'commit ' + str(len(corrupt)).encode() + b'\0' + corrupt))
        with self.assertRaisesRegex(ValueError, 'commit identity'):
            witness.input_commits(self.repo, self.case.base, self.head, target)
        (self.repo / 'info').mkdir()
        (self.repo / 'info/grafts').write_text('untrusted', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'grafts'):
            witness.input_commits(self.repo, self.case.base, self.head, self.head)

    def test_inprocess_outer_measurement_keeps_real_git_and_child_execution(self):
        plan = self.plan()
        with self.outer():
            receipt = self.call(plan)
            self.assertEqual(('ci-minimum-witness', 'PASS'), (receipt['kind'], receipt['status']))
            self.assertEqual(plan, receipt['minimum_plan'])
            self.assertEqual(4, len(receipt['accepted_sources']))
            signed = dict(receipt)
            self.assertEqual(signed.pop('receipt_id'), witness.digest(witness.canonical(signed)))
            for fields, reason in (({'repository': 'bad'}, 'repository'), ({'body': None}, 'metadata'),
                                   ({'base_ref': 'feature'}, 'base ref'), ({'head': 'HEAD'}, 'exact Git SHA')):
                with self.subTest(fields=fields), self.assertRaisesRegex(ValueError, reason):
                    self.call(plan, **fields)
            bad = copy.deepcopy(plan)
            bad['plan_id'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'isolated accepted planner failed'):
                self.call(bad)
        with self.outer(isolated=0), self.assertRaisesRegex(ValueError, 'Python -I'):
            self.call(plan)

    def test_worker_comparison_and_source_proofs_use_actual_accepted_helpers(self):
        plan = self.plan()
        request = self.request(plan)
        with self.loaded_helpers():
            result = witness.worker(request)
            self.assertEqual('internal-planner-comparison', result['kind'])
            self.assertEqual('PASS', result['comparison'])
            self.assertNotIn('status', result)
            reduced = copy.deepcopy(request)
            reduced['plan']['tests'] = []
            reduced['plan'] = self.resign(reduced['plan'])
            result = witness.worker(reduced)
            self.assertEqual('BLOCK', result['comparison'])
            self.assertIn('drops required tests', result['reason'])
            for key, reason in (('signature', 'digest'), ('shape', 'shape'), ('binding', 'binding'), ('sources', 'helper identity')):
                bad = copy.deepcopy(request)
                if key == 'signature':
                    bad['plan']['plan_id'] = '0' * 64
                elif key == 'shape':
                    bad['plan']['extra'] = True
                    bad['plan'] = self.resign(bad['plan'])
                elif key == 'binding':
                    bad['plan']['binding']['head'] = self.case.base
                    bad['plan'] = self.resign(bad['plan'])
                else:
                    bad['sources']['.github/scripts/plan_ci.py']['sha256'] = '0' * 64
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, reason):
                    witness.worker(bad)

    def test_worker_loaded_module_containment_and_required_governance(self):
        plan = self.plan()
        request = self.request(plan)
        with self.loaded_helpers():
            witness.worker(request)
            outside = copy.deepcopy(request)
            outside['trusted'] = str(self.files / 'different-tree')
            with self.assertRaisesRegex(ValueError, 'escaped'):
                witness.worker(outside)
            module = sys.modules['ci_dependencies']
            original = module.__file__
            module.__file__ = str(Path(request['trusted']) / 'unknown.py')
            try:
                with self.assertRaisesRegex(ValueError, 'unexpected project helper'):
                    witness.worker(request)
            finally:
                module.__file__ = original
        integration = copy.deepcopy(request)
        integration['inputs']['integration'] = True
        integration['plan'] = fixture.planner.make_plan(self.repo, **integration['inputs'])
        with self.loaded_helpers(), self.assertRaisesRegex(ValueError, 'was not loaded'):
            witness.worker(integration)

    def test_cli_paths_preserve_output_identity_and_worker_transport_kind(self):
        plan = self.plan()
        request = self.request(plan)
        inputs = self.files / 'candidate.json'
        body = self.files / 'metadata.txt'
        output = self.files / 'receipt.json'
        inputs.write_bytes(witness.canonical(plan))
        body.write_text(fixture.BODY, encoding='utf-8')
        args = ['--repository', 'Example/repo', '--repo', str(self.repo), '--base', self.case.base,
                '--head', self.head, '--target', self.head, '--body', str(body), '--plan', str(inputs),
                '--expected-witness', self.witness_commit, '--output', str(output)]
        with self.outer(), redirect_stdout(io.StringIO()):
            self.assertEqual(0, witness.main(args))
            preserved = output.read_bytes()
            with self.assertRaises(FileExistsError):
                witness.main(args)
            self.assertEqual(preserved, output.read_bytes())
            bad_output = self.files / 'blocked.json'
            args[-1] = str(bad_output)
            inputs.write_bytes(b'{"duplicate":1,"duplicate":2}')
            self.assertEqual(1, witness.main(args))
            self.assertIn('duplicate', json.loads(bad_output.read_bytes())['reason'])
        proxy = SimpleNamespace(argv=['checker', '--worker'], flags=SimpleNamespace(isolated=1),
                                stdin=SimpleNamespace(buffer=io.BytesIO(witness.canonical(request))),
                                path=sys.path, modules=sys.modules)
        with self.loaded_helpers(), patch.object(witness, 'sys', proxy), redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(0, witness.entrypoint())
            self.assertEqual('internal-planner-comparison', json.loads(stdout.getvalue())['kind'])
        with patch.object(sys, 'argv', ['checker', '--help']), redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as exit:
            runpy.run_path(str(ROOT / SCRIPT), run_name='__main__')
        self.assertEqual(0, exit.exception.code)


if __name__ == '__main__':
    unittest.main()
