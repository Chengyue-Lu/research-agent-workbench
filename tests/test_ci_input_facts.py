"""Input classification preserves executable and simultaneous authority facts."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import ci_input_facts as facts
import plan_ci as planner


def describe(path, versions=None):
    return facts.describe(path, [('100644', b'data')] if versions is None else versions,
        selection_authority=planner.SELECTION_AUTHORITY, coverage_authority=planner.COVERAGE_AUTHORITY,
        policy_path=planner.POLICY)


class InputFactsTests(unittest.TestCase):
    def test_concurrent_authorities_are_not_lost_to_display_priority(self):
        workflow = describe('.github/workflows/new.yml')
        self.assertEqual(['coverage', 'repository', 'selection'], workflow['authorities'])
        self.assertEqual('selection-authority', workflow['role'])
        self.assertEqual(['coverage', 'packaging'], describe('pyproject.toml')['authorities'])
        self.assertEqual(['coverage', 'selection'], describe('tests/run_unittest_suite.py')['authorities'])
        self.assertTrue(describe('tests/run_unittest_suite.py')['executable'])
        self.assertEqual(['selection-policy'], describe(planner.POLICY)['authorities'])
        for path in ('.gitattributes', '.github/config.json'):
            self.assertEqual(['repository'], describe(path)['authorities'])
        self.assertEqual(['coverage'], describe('tests/coverage_policy.yaml')['authorities'])
        self.assertFalse(workflow['execution_authority'])

    def test_domains_and_executable_modes_remain_independent(self):
        for path, role, domain, executable in (
            ('tests/helpers/build.py', 'test-code', 'test', True),
            ('tests/fixtures/a.yaml', 'test-input', 'test', False),
            ('src/research_workbench/a.py', 'executable', 'runtime', True),
            ('registry/a.yaml', 'runtime-input', 'runtime', False),
            ('examples/a.md', 'runtime-input', 'runtime', False),
            ('.agents/skills/a/SKILL.md', 'runtime-input', 'runtime', False),
            ('work/A/file.py', 'executable', 'archive', True),
            ('work/A/file.py.txt', 'evidence-data', 'archive', False),
            ('work/A/result.log', 'evidence-data', 'archive', False),
            ('docs/workstreams/a/attempts/A/file.trace', 'evidence-data', 'archive', False),
            ('docs/workstreams/a/status.yaml', 'unknown', 'repository', False),
            ('docs/a.md', 'document', 'document', False),
            ('README.md', 'document', 'document', False),
            ('unknown.bin', 'unknown', 'repository', False),
        ):
            with self.subTest(path=path):
                result = describe(path)
                self.assertEqual((role, domain, executable), (result['role'], result['domain'], result['executable']))
                self.assertEqual(role == 'unknown', bool(result['unresolved']))

    def test_archive_suffix_cannot_hide_code_or_git_type_drift(self):
        for versions in ([('100755', b'log')], [('100644', b'#!/bin/sh\n')]):
            self.assertEqual('executable', describe('work/A/log.trace', versions)['role'])
        for versions in ([('120000', b'target')], [('160000', b'')], [('100644', b'a'), ('100755', b'a')]):
            result = describe('work/A/log.log', versions)
            self.assertEqual('unknown', result['role'])
            self.assertIsNone(result['executable'])
        drift = describe('.github/workflows/ci.yml', [('120000', b'target')])
        self.assertEqual(['coverage', 'repository', 'selection'], drift['authorities'])
        self.assertEqual('unknown', drift['role'])
        for path in ('', '/absolute', '../escape', 'docs/../a', 'docs\\a', 'C:/a', 'docs//a', 'docs/./a'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                describe(path)
        with self.assertRaisesRegex(ValueError, 'no Git version'):
            describe('docs/a.md', [])

    def test_scoped_attribute_grammar_handles_historical_variants(self):
        for raw in (b'* text eol=lf\n', b'** -text\n', b'* -text whitespace=cr-at-eol\n',
                    b'** -text\ntool-events/* whitespace=cr-at-eol,-blank-at-eof\n',
                    b'# archive\r\n\r\n*.json text=auto eol=crlf\r\n'):
            with self.subTest(raw=raw):
                result = describe('work/A/.gitattributes', [('100644', raw)])
                self.assertEqual('archive-attributes', result['role'])
                self.assertTrue(result['attribute_rules'])
        self.assertEqual([], facts.archive_attributes(b'\n# empty rules\n'))
        versions = [('100644', b'* text eol=lf'), ('100644', b'** -text')]
        rules = describe('work/A/.gitattributes', versions)['attribute_rules']
        self.assertEqual(['*', '**'], [version[0]['pattern'] for version in rules])

    def test_unknown_attributes_macros_and_escapes_stay_unresolved(self):
        invalid = (b'\xff', b'*', b'/root -text', b'!name -text', b'[attr]macro -text', b'"a b" -text',
                   b'\xef\xbb\xbf* -text', b'a\\b -text', b'C:foo -text', b'a"b -text', b'../a -text',
                   b'a//b -text', b'* filter=external', b'* export-ignore', b'* merge=ours',
                   b'* diff=custom', b'* working-tree-encoding=UTF-16', b'* text -text',
                   b'* whitespace=', b'* whitespace=--cr-at-eol', b'* whitespace=unknown',
                   b'* binary', b'* -text\n* export-subst')
        for raw in invalid:
            with self.subTest(raw=raw):
                self.assertIsNone(facts.archive_attributes(raw))
                result = describe('work/A/.gitattributes', [('100644', raw)])
                self.assertEqual('unknown', result['role'])
                self.assertTrue(result['unresolved'])
        result = describe('work/A/.gitattributes', [('100644', b'** -text'), ('100644', b'* filter=external')])
        self.assertEqual([], result['attribute_rules'])

    def test_accepted_attribute_order_matches_git_for_archive_paths(self):
        raw = b'** -text\n*.json text=auto eol=lf\ntool-events/* whitespace=cr-at-eol,-blank-at-eof\n'
        rules = facts.archive_attributes(raw)
        self.assertEqual(['**', '*.json', 'tool-events/*'], [rule['pattern'] for rule in rules])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / '.gitattributes').write_bytes(raw)
            output = subprocess.check_output(['git', '-C', str(root), 'check-attr', 'text', 'eol', 'whitespace',
                                               '--', 'report.json', 'tool-events/run.log']).decode()
        self.assertIn('report.json: text: auto', output)
        self.assertIn('report.json: eol: lf', output)
        self.assertIn('tool-events/run.log: text: unset', output)
        self.assertIn('tool-events/run.log: whitespace: cr-at-eol,-blank-at-eof', output)


class InvocationFactsTests(unittest.TestCase):
    """Call syntax is independently reproducible evidence, never a skip permission."""

    def fixture(self, source, callee='subprocess.run', binding='proven-import', consumer='tools/check.py'):
        raw = source.encode('utf-8')
        call = next(node for node in ast.walk(ast.parse(raw)) if isinstance(node, ast.Call))
        record = facts.describe_invocation(consumer, raw, call, callee=callee, binding=binding, scope='check')
        facts.verify_invocation(record, consumer, raw, call, callee=callee, binding=binding, scope='check')
        self.assertFalse(record['execution_authority'])
        self.assertEqual('unproved', record['resolution']['input_closure'])
        self.assertIn('input-closure-unproved', record['unresolved'])
        return record, raw, call

    def test_callsite_identity_binds_path_bytes_scope_span_and_ast(self):
        source = 'result = sp.run(["git", "rev-parse", "HEAD"])\n'
        record, raw, call = self.fixture(source)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), record['source_sha256'])
        self.assertEqual('tools/check.py', record['consumer'])
        self.assertEqual([1, 9, 1, 45], record['callsite']['span'])
        self.assertEqual(b'sp.run(["git", "rev-parse", "HEAD"])', raw[9:45])
        self.assertEqual('check', record['callsite']['scope'])
        comment, _, _ = self.fixture(source + '# independent bytes\n')
        self.assertNotEqual(record['source_sha256'], comment['source_sha256'])
        self.assertEqual(record['callsite'], comment['callsite'])
        moved, _, _ = self.fixture(source, consumer='other/check.py')
        self.assertNotEqual(record['consumer'], moved['consumer'])
        for kwargs in ({'consumer': 'other/check.py'}, {'raw': raw + b'# changed'},
                       {'scope': 'other'}, {'callee': 'subprocess.call'}, {'binding': 'escaped'},
                       {'call': ast.parse('sp.run(["git", "show", "HEAD"])').body[0].value}):
            inputs = dict(consumer='tools/check.py', raw=raw, call=call,
                          callee='subprocess.run', binding='proven-import', scope='check')
            inputs.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                facts.verify_invocation(record, **inputs)

    def test_git_operations_retain_content_membership_identity_and_configuration(self):
        cases = (
            (['git', '-C', 'checkout', 'rev-parse', 'HEAD'], 'git-identity', {'identity'}),
            (['git.exe', '-c', 'core.autocrlf=false', 'show', 'HEAD:path'], 'git-content', {'content', 'identity'}),
            (['git', '--git-dir', '.git', '--work-tree', '.', 'ls-tree', '-r', 'HEAD'],
             'git-membership', {'identity', 'membership'}),
            (['git', 'ls-tree', '--name-only', 'HEAD'], 'git-membership', {'identity', 'membership'}),
            (['git', 'ls-files', '--others'], 'git-membership', {'membership'}),
            (['git', 'merge-tree', 'base', 'left', 'right'], 'git-merge', {'content', 'identity', 'membership'}),
        )
        for argv, operation, dimensions in cases:
            with self.subTest(argv=argv):
                record, _, _ = self.fixture('run(' + repr(argv) + ')')
                self.assertEqual(operation, record['operation'])
                self.assertEqual(dimensions | {'execution', 'output'}, set(record['dimensions']))
                self.assertEqual('known', record['resolution']['target_shape'])
                self.assertIn('git-configuration', record['unresolved'])
                self.assertIn('git-ref-and-worktree-state', record['unresolved'])
        default, _, _ = self.fixture('run(["git", "ls-tree", "HEAD"])')
        names, _, _ = self.fixture('run(["git", "ls-tree", "--name-only", "HEAD"])')
        self.assertIn({'role': 'tree-entry-identities'}, default['outputs'])
        self.assertIn({'role': 'tree-entry-names'}, names['outputs'])
        for argv, reason in ((['git', '-C'], 'unsupported-git-options'),
                             (['git', '--unknown', 'show'], 'unsupported-git-options'),
                             (['git', 'status'], 'unsupported-git-operation')):
            record, _, _ = self.fixture('run(' + repr(argv) + ')')
            self.assertEqual('subprocess', record['operation'])
            self.assertIn(reason, record['unresolved'])

    def test_fixed_python_targets_do_not_prove_import_or_input_closure(self):
        for argv, operation, role in (
            (['python3', '-m', 'pkg.mod'], 'python-module', 'module-name'),
            (['python', '-c', 'import package; package.run()'], 'python-inline', 'inline-source'),
            (['C:\\Python\\python.exe', 'tools/run.py'], 'python-script', 'script-path'),
        ):
            with self.subTest(argv=argv):
                record, _, _ = self.fixture('run(' + repr(argv) + ')')
                self.assertEqual(operation, record['operation'])
                self.assertIn('python-import-closure', record['unresolved'])
                self.assertTrue(any(item['role'] == role for item in record['inputs']))
        for argv in (['python', '-I', '-m', 'pkg'], ['python']):
            record, _, _ = self.fixture('run(' + repr(argv) + ')')
            self.assertEqual('subprocess', record['operation'])
            self.assertIn('unsupported-python-options', record['unresolved'])
        dynamic, _, _ = self.fixture('run([sys.executable, "-m", "pkg"])')
        self.assertEqual('unknown', dynamic['resolution']['target_shape'])
        self.assertIn('dynamic-argv', dynamic['unresolved'])

    def test_ambient_cwd_env_and_explicit_values_remain_unproved_and_private(self):
        default, _, _ = self.fixture('run(["tool"])')
        self.assertIn('inherited-cwd', default['unresolved'])
        self.assertIn('ambient-environment', default['unresolved'])
        self.assertEqual({'kind': 'missing'}, default['invocation']['cwd'])
        inherited, _, _ = self.fixture('run(["tool"], env=None)')
        self.assertIn('ambient-environment', inherited['unresolved'])
        record, _, _ = self.fixture('run(args=("tool",), cwd="repo", env={"TOKEN": "private-env"}, '
                                    'stdin=stream, input="private-input", shell=False)')
        self.assertIn('explicit-environment-unproved', record['unresolved'])
        self.assertIn('explicit-cwd-unproved', record['unresolved'])
        self.assertEqual({'kind': 'literal', 'value': 'repo'}, record['invocation']['cwd'])
        self.assertIn({'role': 'process-input'}, record['inputs'])
        self.assertIn('content', record['dimensions'])
        serialized = json.dumps(record)
        self.assertNotIn('private-env', serialized)
        self.assertNotIn('private-input', serialized)
        self.assertNotIn('TOKEN', serialized)

    def test_shell_kwargs_and_starred_calls_never_acquire_git_target_semantics(self):
        cases = (
            ('run(["git", "show", "HEAD"], shell=True)', 'shell-execution'),
            ('run(["git", "show", "HEAD"], shell=flag)', 'unknown-shell'),
            ('run(["git", "show", "HEAD"], **options)', 'dynamic-keywords'),
            ('run(*commands)', 'dynamic-positional-arguments'),
        )
        for source, reason in cases:
            with self.subTest(source=source):
                record, _, _ = self.fixture(source)
                self.assertEqual('subprocess', record['operation'])
                self.assertEqual('unknown', record['resolution']['target_shape'])
                self.assertIn(reason, record['unresolved'])
                self.assertNotIn('identity', record['dimensions'])
        for source in ('run(command)', 'run([])', 'run(["git", *args])', 'run()'):
            record, _, _ = self.fixture(source)
            self.assertIn('dynamic-argv', record['unresolved'])
        record, _, _ = self.fixture('run(["tool"], cwd=1e999)')
        self.assertEqual('expression', record['invocation']['cwd']['kind'])

    def test_executable_and_positional_overrides_cannot_inherit_git_semantics(self):
        cases = (
            ('run(["git", "rev-parse", "HEAD"], executable="other-program")',
             'subprocess.run', 'explicit-executable-override'),
            ('run(["git", "rev-parse", "HEAD"], executable=None)',
             'subprocess.run', 'explicit-executable-override'),
            ('Popen(["git", "rev-parse", "HEAD"], -1, None, None, None, None, None, True, True)',
             'subprocess.Popen', 'unsupported-positional-process-options'),
            ('Popen(["git", "rev-parse", "HEAD"], preexec_fn=hook)',
             'subprocess.Popen', 'unsupported-process-options'),
        )
        for source, callee, reason in cases:
            with self.subTest(source=source):
                record, _, _ = self.fixture(source, callee=callee)
                self.assertEqual('subprocess', record['operation'])
                self.assertEqual('unknown', record['resolution']['target_shape'])
                self.assertIn(reason, record['unresolved'])
                self.assertNotIn('identity', record['dimensions'])
                self.assertFalse(any(item['role'] == 'git-command' for item in record['inputs']))
        # Real subprocess execution establishes why argv[0] is not executable identity.
        # The child runs Python despite the literal Git name in argv[0].
        completed = subprocess.run(['git', '-c', 'print("override-ran-python")'], executable=sys.executable,
                                   check=True, capture_output=True, text=True)
        self.assertEqual('override-ran-python', completed.stdout.strip())
        overridden, _, _ = self.fixture('run(["git"], executable="SYNTHETIC_EXE_SECRET")')
        self.assertEqual('expression', overridden['invocation']['executable']['kind'])
        self.assertNotIn('SYNTHETIC_EXE_SECRET', json.dumps(overridden))

    def test_argv_payloads_and_inline_source_never_leak_through_report_fields(self):
        cases = (
            ('run(["tool", "--token", "SYNTHETIC_ARG_SECRET"])', 'subprocess.run'),
            ('run(["python", "-c", "TOKEN = \'SYNTHETIC_INLINE_SECRET\'"])', 'subprocess.run'),
            ('run(["git", "-c", "TOKEN=SYNTHETIC_GIT_SECRET", "show", "SYNTHETIC_REF_SECRET"])',
             'subprocess.run'),
            ('run(["python", "-m", "SYNTHETIC_MODULE_SECRET"])', 'subprocess.run'),
            ('run(["python", "SYNTHETIC_SCRIPT_SECRET"])', 'subprocess.run'),
            ('run("SYNTHETIC_TARGET_SECRET")', 'runpy.run_module'),
            ('run(["SYNTHETIC_EXE_SECRET", "--token=SYNTHETIC_EQUALS_SECRET"])', 'subprocess.run'),
            ('run(["SYNTHETIC_UNKNOWN_SECRET"])', 'wrapper.unknown'),
        )
        for source, callee in cases:
            with self.subTest(source=source):
                record, _, _ = self.fixture(source, callee=callee)
                self.assertNotIn('SYNTHETIC_', json.dumps(record))
                self.assertNotIn('TOKEN', json.dumps(record))
                self.assertNotIn('value', json.dumps(record['invocation']['argv']))
        first, _, _ = self.fixture('run(["tool", "--token", "SYNTHETIC_FIRST_SECRET"])')
        second, _, _ = self.fixture('run(["tool", "--token", "SYNTHETIC_SECOND_SECRET"])')
        self.assertEqual([0, 1, 2], [item['position'] for item in first['invocation']['argv']['items']])
        self.assertNotEqual(first['invocation']['argv']['items'][2]['ast_sha256'],
                            second['invocation']['argv']['items'][2]['ast_sha256'])
        self.assertNotEqual(first['callsite']['ast_sha256'], second['callsite']['ast_sha256'])

    def test_import_binding_and_escape_are_not_guessed_from_spelling(self):
        for binding, reason in (('unresolved', 'untrusted-callee-binding'), ('escaped', 'callable-escape')):
            record, _, _ = self.fixture('subprocess.run(["git", "show", "HEAD"])', binding=binding)
            self.assertEqual('unknown', record['operation'])
            self.assertEqual([], record['dimensions'])
            self.assertIn(reason, record['unresolved'])
        for callee in ('local.run', 'wrapper.git', None):
            record, _, _ = self.fixture('wrapper(["git", "show", "HEAD"])', callee=callee)
            self.assertEqual('unknown', record['operation'])
            self.assertIn('unsupported-call-target', record['unresolved'])

    def test_runpy_import_inline_and_shell_sites_keep_unknown_runtime_inputs(self):
        for callee in ('runpy.run_module', 'runpy.run_path', 'importlib.import_module', 'builtins.__import__'):
            with self.subTest(callee=callee):
                record, _, _ = self.fixture('run("pkg.mod")', callee=callee)
                self.assertEqual('python-script' if callee == 'runpy.run_path' else 'python-module', record['operation'])
                self.assertEqual('known', record['resolution']['target_shape'])
                self.assertIn('python-import-closure', record['unresolved'])
        dynamic, _, _ = self.fixture('run(target)', callee='runpy.run_path')
        self.assertEqual('unknown', dynamic['resolution']['target_shape'])
        for callee in ('builtins.exec', 'builtins.eval', 'builtins.compile'):
            record, _, _ = self.fixture('run("code")', callee=callee)
            self.assertEqual('python-inline', record['operation'])
            self.assertIn('inline-execution-closure', record['unresolved'])
        for callee in ('os.system', 'os.popen'):
            record, _, _ = self.fixture('run("git show HEAD")', callee=callee)
            self.assertEqual('shell', record['operation'])
            self.assertIn('shell-execution', record['unresolved'])

    def test_resource_effects_are_concurrent_and_do_not_bind_paths(self):
        for callee, operation, dimensions in (
            ('pathlib.Path.read_text', 'resource-content', ['content']),
            ('pathlib.Path.read_bytes', 'resource-content', ['content']),
            ('pathlib.Path.glob', 'resource-membership', ['membership']),
            ('pathlib.Path.rglob', 'resource-membership', ['membership']),
            ('pathlib.Path.iterdir', 'resource-membership', ['membership']),
            ('pathlib.Path.write_text', 'resource-output', ['output']),
            ('pathlib.Path.write_bytes', 'resource-output', ['output']),
            ('pathlib.Path.open', 'resource-open', ['content', 'output']),
            ('builtins.open', 'resource-open', ['content', 'output']),
        ):
            with self.subTest(callee=callee):
                record, _, _ = self.fixture('handle("path")', callee=callee)
                self.assertEqual(operation, record['operation'])
                self.assertEqual(dimensions, record['dimensions'])
                self.assertEqual('unknown', record['resolution']['target_shape'])
                self.assertIn('resource-path-and-symlink-resolution', record['unresolved'])

    def test_recompute_rejects_all_record_fields_and_type_confusion(self):
        record, raw, call = self.fixture('run(["git", "rev-parse", "HEAD"])')
        replacements = {
            'schema_version': True, 'consumer': 'other.py', 'source_sha256': '0' * 64,
            'callsite': {}, 'callee': {}, 'operation': 'pure', 'dimensions': [],
            'invocation': {}, 'inputs': [], 'outputs': [], 'resolution': {'input_closure': 'complete'},
            'unresolved': [], 'execution_authority': 0,
        }
        for key, value in replacements.items():
            with self.subTest(key=key):
                changed = copy.deepcopy(record)
                changed[key] = value
                with self.assertRaisesRegex(ValueError, 'differs'):
                    facts.verify_invocation(changed, 'tools/check.py', raw, call,
                                            callee='subprocess.run', binding='proven-import', scope='check')
        for invalid in ({'extra': object()}, {'extra': float('nan')}):
            with self.assertRaisesRegex(ValueError, 'invalid invocation record'):
                facts.verify_invocation(invalid, 'tools/check.py', raw, call,
                                        callee='subprocess.run', binding='proven-import', scope='check')

    def test_invalid_source_paths_calls_spans_and_bindings_are_rejected(self):
        _, raw, call = self.fixture('run(["tool"])')
        inputs = dict(consumer='tools/check.py', raw=raw, call=call, callee='subprocess.run', binding='proven-import')
        for kwargs in ({'consumer': None}, {'consumer': ''}, {'consumer': '/abs'}, {'consumer': '../escape'},
                       {'consumer': 'C:/escape'}, {'consumer': 'path\\file'}, {'raw': 'text'},
                       {'call': ast.Constant(value=1)}, {'scope': None}, {'binding': 'trusted'},
                       {'callee': ''}, {'callee': 1}, {'call': ast.Call(func=ast.Name(id='run'), args=[], keywords=[])}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                facts.describe_invocation(**(inputs | kwargs))
