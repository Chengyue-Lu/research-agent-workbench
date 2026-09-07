from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import ci_dependencies as deps


class DependencyTests(unittest.TestCase):
    def selection(self, old, new, seeds, resources=()):
        def snapshot(repo, commit):
            blobs = old if commit == 'base' else new
            paths = {p: ['100644', 'blob', hashlib.sha1(raw).hexdigest()] for p, raw in blobs.items()}
            paths.update({p: ['100644', 'blob', '0' * 40] for p in resources})
            return paths, blobs
        deps.commit_graph.cache_clear()
        with patch.object(deps, 'snapshot', side_effect=snapshot):
            return deps.select('fixture', 'base', 'head', seeds)[0]

    def test_import_closure_keeps_consumers_and_excludes_independent_test(self):
        blobs = {'src/pkg/__init__.py': b'', 'src/pkg/leaf.py': b'VALUE=1',
                 'src/pkg/consumer.py': b'from .leaf import VALUE',
                 'tests/test_contract.py': b'from pkg.consumer import VALUE',
                 'tests/test_unrelated.py': b'import unittest'}
        p = self.selection(blobs, blobs, ['src/pkg/leaf.py'])
        self.assertEqual(['test_contract'], list(p['selected']))
        self.assertEqual(['test_unrelated'], p['excluded'])
        self.assertEqual(['src/pkg/leaf.py', 'src/pkg/consumer.py', 'tests/test_contract.py'], p['selected']['test_contract'])
        self.assertFalse(p['errors'])

    def test_removed_edge_cannot_hide_old_consumer(self):
        old = {'src/pkg/leaf.py': b'VALUE=1', 'tests/test_contract.py': b'import pkg.leaf'}
        new = {**old, 'tests/test_contract.py': b'import unittest'}
        p = self.selection(old, new, ['src/pkg/leaf.py'])
        self.assertIn('test_contract', p['selected'])
        p = self.selection(old, {'tests/test_contract.py': b'import unittest'}, ['src/pkg/leaf.py'])
        self.assertIn('test_contract', p['selected'])

    def test_opaque_execution_expands_instead_of_claiming_exclusion(self):
        blobs = {'src/pkg/leaf.py': b'VALUE=1', 'tests/test_dynamic.py': b'import importlib\nimportlib.import_module(name)',
                 'tests/test_subprocess.py': b'from subprocess import run as launch\nlaunch(command)',
                 'tests/test_eval.py': b'exec(source)', 'tests/test_other.py': b'pass'}
        p = self.selection(blobs, blobs, ['src/pkg/leaf.py'])
        self.assertEqual({'test_dynamic', 'test_subprocess', 'test_eval'}, set(p['selected']))
        self.assertEqual(3, len(p['opaque_consumers']))
        self.assertEqual(['test_other'], p['excluded'])

    def test_new_and_modified_test_do_not_select_independent_opaque_execution(self):
        old = {'tests/test_other.py': b'import subprocess\nsubprocess.run(command)', 'tests/test_one.py': b'pass'}
        new = {**old, 'tests/test_new.py': b'import unittest'}
        p = self.selection(old, new, ['tests/test_new.py', 'tests/test_one.py'])
        self.assertEqual({'test_new', 'test_one'}, set(p['selected']))
        self.assertEqual(['test_other'], p['excluded'])

    def test_test_helper_consumers_are_transitive(self):
        blobs = {'tests/helper.py': b'VALUE=1', 'tests/middle.py': b'from helper import VALUE',
                 'tests/test_one.py': b'from tests.middle import VALUE', 'tests/test_other.py': b'pass'}
        self.assertEqual(['test_one'], list(self.selection(blobs, blobs, ['tests/helper.py'])['selected']))

    def test_literals_and_resource_readers_preserve_fixture_contract(self):
        blobs = {'tests/test_schema.py': b'PATH="schemas/object.json"',
                 'tests/test_scan.py': b'list(root.rglob("*.json"))',
                 'tests/test_read.py': b'open(path).read()', 'tests/test_other.py': b'pass'}
        p = self.selection(blobs, blobs, ['schemas/object.json'], ['schemas/object.json'])
        self.assertEqual({'test_schema', 'test_scan', 'test_read'}, set(p['selected']))

    def test_literal_dynamic_import_and_run_path_resolve_without_opaque_fallback(self):
        blobs = {'src/pkg/leaf.py': b'VALUE=1', 'tests/test_path.py': b'import runpy\nrunpy.run_path("src/pkg/leaf.py")',
                 'tests/test_module.py': b'__import__("pkg.leaf")',
                 'tests/test_external.py': b'__import__("hashlib")'}
        p = self.selection(blobs, blobs, ['src/pkg/leaf.py'])
        self.assertEqual({'test_path', 'test_module'}, set(p['selected']))
        self.assertFalse(p['opaque_consumers'])

    def test_package_initialization_star_and_relative_imports(self):
        blobs = {'src/pkg/__init__.py': b'from .leaf import *', 'src/pkg/leaf.py': b'VALUE=1',
                 'tests/test_one.py': b'import pkg as p', 'tests/test_two.py': b'from pkg import leaf',
                 'tests/test_three.py': b'from pkg.leaf import *'}
        p = self.selection(blobs, blobs, ['src/pkg/leaf.py'])
        self.assertEqual({'test_one', 'test_two', 'test_three'}, set(p['selected']))

    def test_changed_inventory_is_bound_without_invalidating_independent_closure(self):
        old = {'src/pkg/leaf.py': b'VALUE=1', 'tests/test_one.py': b'import pkg.leaf'}
        first = self.selection(old, old, ['src/pkg/leaf.py'])
        new = {**old, 'tests/test_other.py': b'pass'}
        second = self.selection(old, new, ['src/pkg/leaf.py'])
        self.assertEqual(first['selected'], second['selected'])
        self.assertNotEqual(first['inventory_sha256'], second['inventory_sha256'])

    def test_invalid_python_is_explicit_uncertainty(self):
        p = self.selection({}, {'tests/test_bad.py': b'if ['}, ['tests/test_bad.py'])
        self.assertEqual(['unparseable Python dependency: tests/test_bad.py'], p['errors'])

    def test_semantic_comments_and_docstrings(self):
        self.assertEqual(deps.semantic(b'VALUE = 1\n'), deps.semantic(b'VALUE=1 # ordinary comment\n'))
        self.assertNotEqual(deps.semantic(b'"old doc"'), deps.semantic(b'"new doc"'))
        self.assertEqual('plan_ci', deps.module_name('.github/scripts/plan_ci.py'))
        self.assertEqual('pkg', deps.module_name('src/pkg/__init__.py'))
        self.assertNotEqual(deps.imports(b'import os'), deps.imports(b'import sys'))

    def test_importlib_loader_resource_methods_and_unknown_call_shapes(self):
        blobs = {'src/pkg/leaf.py': b'pass', 'tests/test_loader.py': b'import importlib.util as util\nutil.spec_from_file_location(name,path)',
                 'tests/test_calls.py': b'factory()()\nroot.read_bytes()\nroot.open()\nroot.iterdir()'}
        p = self.selection(blobs, blobs, ['src/pkg/leaf.py'])
        self.assertIn('test_loader', p['selected'])
        self.assertIn('test_calls', p['selected'])

    def test_ambiguous_import_alias_and_module_collision_keep_all_possible_consumers(self):
        blobs = {'src/worker.py': b'VALUE=1', '.github/scripts/worker.py': b'VALUE=1',
                 'tests/test_alias.py': b'import subprocess as invoke\ninvoke.run(command)\nimport json as invoke',
                 'tests/test_worker.py': b'import worker'}
        for seed in ('src/worker.py', '.github/scripts/worker.py'):
            p = self.selection(blobs, blobs, [seed])
            self.assertEqual({'test_alias', 'test_worker'}, set(p['selected']))

    def test_indirect_dynamic_call_and_bound_resource_reader_cannot_escape(self):
        blobs = {'src/pkg/leaf.py': b'VALUE=1',
                 'tests/test_indirect.py': b'getattr(__import__("importlib"), "import_module")(name)',
                 'tests/test_reader.py': b'reader = root.read_bytes\nreader()'}
        p = self.selection(blobs, blobs, ['src/pkg/leaf.py'])
        self.assertIn('test_indirect', p['selected'])
        p = self.selection(blobs, blobs, ['tests/fixtures/input.json'], ['tests/fixtures/input.json'])
        self.assertIn('test_reader', p['selected'])

    def test_path_expression_is_specific_and_metadata_keys_are_not_directory_reads(self):
        blobs = {'tests/test_changed.py': b'VALUE=1',
                 'tests/test_other.py': b'value = ROOT / "tests" / "fixtures" / "claim.json"',
                 '.github/scripts/report.py': b'value = report.get("tests", [])\nzones = ("src", ".github/scripts")',
                 'tests/test_report.py': b'import report'}
        p = self.selection(blobs, blobs, ['tests/test_changed.py'], ['tests/fixtures/claim.json'])
        self.assertEqual(['test_changed'], list(p['selected']))
        p = self.selection(blobs, blobs, ['tests/fixtures/claim.json'], ['tests/fixtures/claim.json'])
        self.assertEqual(['test_other'], list(p['selected']))

    def test_bound_and_passed_execution_capabilities_keep_dynamic_consumers(self):
        consumers = [
            b'loader = __import__\nloader(prefix + suffix)',
            b'invoke = exec\ninvoke(source)',
            b'calculate = eval\ncalculate(source)',
            b'import importlib\nloader = importlib.import_module\nloader(name)',
            b'import subprocess\nlaunch = subprocess.run\nlaunch(command)',
            b'import runpy\nexecute = runpy.run_path\nexecute(path)',
            b'execute = spec.loader.exec_module\nexecute(module)',
            b'factory(__import__)(name)',
            b'from builtins import __import__ as load\nload(name)',
            b'import builtins\nbuiltins.exec(source)',
            b'spec.loader.exec_module(module)',
        ]
        for raw in consumers:
            with self.subTest(raw=raw):
                blobs = {'src/pkg/leaf.py': b'VALUE=1', 'tests/test_direct.py': b'import pkg.leaf',
                         'tests/test_dynamic.py': raw, 'tests/test_other.py': b'pass'}
                plan = self.selection(blobs, blobs, ['src/pkg/leaf.py'])
                self.assertEqual({'test_direct', 'test_dynamic'}, set(plan['selected']))
                self.assertEqual(['tests/test_dynamic.py'], plan['opaque_consumers'])
                self.assertEqual(['test_other'], plan['excluded'])

    def test_getattr_execution_namespaces_retain_assigned_passed_stored_and_called_consumers(self):
        consumers = [
            b'import importlib\nloader = getattr(importlib, "import_module")\nloader(runtime_name)',
            b'import importlib as lib\nloader = getattr(lib, attribute)\nloader(runtime_name)',
            b'import subprocess\nfactory(getattr(subprocess, "run"))',
            b'import runpy\ncallbacks = [getattr(runpy, "run_module")]',
            b'import runpy\ngetattr(runpy, "run_path")(runtime_path)',
            b'from importlib import machinery as loaders\nload = getattr(loaders, attribute)',
            b'from builtins import getattr as lookup\nimport importlib\nload = lookup(importlib, "import_module")',
            b'import builtins\nimport importlib\nload = builtins.getattr(importlib, attribute)',
            b'callback = getattr(spec.loader, attribute)',
            b'callback = getattr(target, "exec_module")',
            b'callback = getattr(target, "spec_from_file_location")',
            b'callback = getattr(__import__("importlib"), attribute)',
            b'lookup = getattr\nimport importlib\ncallback = lookup(importlib, attribute)',
        ]
        for raw in consumers:
            with self.subTest(raw=raw):
                blobs = {'src/pkg/leaf.py': b'VALUE=1', 'tests/test_direct.py': b'import pkg.leaf',
                         'tests/test_dynamic.py': raw,
                         'tests/test_other.py': b'value = getattr(record, "title", None)'}
                plan = self.selection(blobs, blobs, ['src/pkg/leaf.py'])
                self.assertEqual({'test_direct', 'test_dynamic'}, set(plan['selected']))
                self.assertIn('tests/test_dynamic.py', plan['opaque_consumers'])
                self.assertEqual(['test_other'], plan['excluded'])

    def test_dynamic_path_tail_keeps_known_prefix_and_empty_prefix_is_not_a_reference(self):
        blobs = {'tests/test_prefix.py': b'path = ROOT / "fixtures" / name / "result.json"',
                 'tests/test_empty.py': b'value = left / right'}
        p = self.selection(blobs, blobs, ['fixtures/one/result.json'], ['fixtures/one/result.json'])
        self.assertIn('test_prefix', p['selected'])
        self.assertNotIn('test_empty', p['selected'])

    def test_snapshot_reads_exact_git_blobs_and_ignores_worktree_drift(self):
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', '-C', directory, *args], stderr=subprocess.PIPE).decode().strip()
            git('init', '-q'); git('config', 'user.name', 'fixture'); git('config', 'user.email', 'fixture@example.invalid')
            (root / 'test_x.py').write_bytes(b'VALUE=1\n'); (root / 'data.json').write_bytes(b'{}')
            git('add', 'test_x.py', 'data.json'); git('commit', '-qm', 'fixture'); head = git('rev-parse', 'HEAD')
            (root / 'test_x.py').write_bytes(b'VALUE=2\n')
            paths, blobs = deps.snapshot(root, head)
            self.assertIn('data.json', paths)
            self.assertEqual({'test_x.py': b'VALUE=1\n'}, blobs)


if __name__ == '__main__':
    unittest.main()
