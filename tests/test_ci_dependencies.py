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
    def test_cached_facts_resolve_added_and_removed_modules_against_each_inventory(self):
        consumer = {'tests/test_contract.py': b'from pkg import leaf'}
        self.assertEqual({}, deps.graph(consumer, consumer)[0])
        expanded = {**consumer, 'src/pkg/__init__.py': b'', 'src/pkg/leaf.py': b'VALUE=1'}
        edges = deps.graph(expanded, expanded)[0]
        self.assertEqual({'tests/test_contract.py'}, edges['src/pkg/leaf.py'])
        self.assertEqual({'tests/test_contract.py'}, edges['src/pkg/__init__.py'])
        self.assertEqual({}, deps.graph(consumer, consumer)[0])

    def test_cached_facts_keep_new_basename_and_directory_resource_matches(self):
        blobs = {'tests/test_contract.py': b'consume("README.md")\n'
                 b'(ROOT / "data").rglob("*")'}
        first = {*blobs, 'README.md', 'data/a.txt', 'database/unrelated.txt'}
        second = {*blobs, 'README.md', 'docs/README.md', 'data/b.txt'}
        self.assertEqual({'README.md', 'data/a.txt'}, set(deps.graph(blobs, first)[0]))
        self.assertEqual({'README.md', 'docs/README.md', 'data/b.txt'}, set(deps.graph(blobs, second)[0]))
        self.assertEqual({'README.md', 'data/a.txt'}, set(deps.graph(blobs, first)[0]))

    def test_cached_facts_bind_relative_import_and_file_root_to_consumer_path(self):
        raw = b'from . import helper\nfrom pathlib import Path\n(Path(__file__).parent / "data.txt").read_text()'
        helpers = {'tests/a/helper.py': b'', 'tests/b/helper.py': b''}
        paths = {*helpers, 'tests/a/test_local.py', 'tests/b/test_local.py',
                 'tests/a/data.txt', 'tests/b/data.txt'}
        for directory in ('a', 'b', 'a'):
            consumer = 'tests/' + directory + '/test_local.py'
            edges = deps.graph({**helpers, consumer: raw}, paths)[0]
            self.assertEqual({'tests/' + directory + '/helper.py', 'tests/' + directory + '/data.txt'}, set(edges))
            self.assertTrue(all(consumers == {consumer} for consumers in edges.values()))

    def test_cached_facts_invalidate_changed_bytes_and_invalid_python(self):
        path = 'tests/test_contract.py'
        for raw, expected, opaque, invalid in (
            (b'import pkg.a', {'src/pkg/a.py'}, False, False),
            (b'import pkg.b\nexec(code)', {'src/pkg/b.py'}, True, False),
            (b'def invalid(', set(), False, True),
            (b'import pkg.a', {'src/pkg/a.py'}, False, False),
        ):
            with self.subTest(raw=raw):
                blobs = {path: raw, 'src/pkg/a.py': b'', 'src/pkg/b.py': b''}
                edges, dynamic, _, errors = deps.graph(blobs, blobs)
                self.assertEqual(expected, set(edges))
                self.assertEqual({path} if opaque else set(), dynamic)
                self.assertEqual(['unparseable Python dependency: ' + path] if invalid else [], errors)

    def test_returned_graph_mutation_cannot_poison_cached_facts(self):
        blobs = {'tests/test_contract.py': b'import pkg.a\nexec(code)\nopen("fixture.txt")',
                 'src/pkg/a.py': b''}
        paths = {*blobs, 'fixture.txt'}
        result = deps.graph(blobs, paths)
        result[0]['src/pkg/a.py'].clear()
        result[1].clear()
        result[2].clear()
        result[3].append('injected')
        edges, opaque, resources, errors = deps.graph(blobs, paths)
        self.assertEqual({'tests/test_contract.py'}, edges['src/pkg/a.py'])
        self.assertEqual({'tests/test_contract.py'}, edges['fixture.txt'])
        self.assertEqual({'tests/test_contract.py'}, opaque)
        self.assertEqual(opaque, resources)
        self.assertFalse(errors)

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

    def test_document_names_and_directory_guards_do_not_create_runtime_input_edges(self):
        blobs = {
            'tests/test_release.py': b'paths = {item["path"] for item in includes}\n'
                b'assert paths.isdisjoint({"docs/STATUS.md"})',
            'work/a/oracle.py': b'from tests.test_release import paths',
            'src/pkg/reconstruct.py': b'from pathlib import Path\n'
                b'def check(root: Path, path: Path):\n'
                b'    return path.is_relative_to(root / "work") and path != root / "work"',
            'tests/test_runtime.py': b'import pkg.reconstruct',
            'tests/test_docs.py': b'(ROOT / "docs" / "STATUS.md").read_text()',
        }
        plan = self.selection(blobs, blobs, ['docs/STATUS.md'], ['docs/STATUS.md'])
        self.assertEqual({'test_docs'}, set(plan['selected']))
        plan = self.selection(blobs, blobs, ['work/a/oracle.py'])
        self.assertNotIn('test_runtime', plan['selected'])

    def test_qualified_paths_do_not_alias_same_basename_in_other_directories(self):
        blobs = {
            'tests/test_root.py': b'(ROOT / "README.md").read_text()',
            'tests/test_nested.py': b'(ROOT / "docs" / "README.md").read_text()',
            'tests/test_names.py': b'def docs_only(path):\n'
                b'    root_docs = {"README.md", "AGENTS.md"}\n'
                b'    return path in root_docs',
            'tests/test_fixture.py': b'p = ROOT / "tests" / "fixtures" / "README.md"',
        }
        blobs = {p: b'from pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\n' + raw
                 for p, raw in blobs.items()}
        paths = ['README.md', 'docs/README.md', 'tests/fixtures/README.md']
        plan = self.selection(blobs, blobs, ['docs/README.md'], paths)
        self.assertEqual({'test_nested'}, set(plan['selected']))
        plan = self.selection(blobs, blobs, ['tests/fixtures/README.md'], paths)
        self.assertEqual({'test_fixture'}, set(plan['selected']))

    def test_unresolved_bare_filenames_keep_relative_and_helper_consumers(self):
        blobs = {
            'tests/test_relative.py': b'filename = "README.md"\n'
                b'(Path(__file__).parent / filename).read_text()',
            'tests/test_helper.py': b'consume("README.md")',
            'tests/test_exported.py': b'FILES = ["README.md"]',
        }
        paths = ['README.md', 'docs/README.md']
        for seed in paths:
            with self.subTest(seed=seed):
                self.assertEqual({'test_relative', 'test_helper', 'test_exported'},
                                 set(self.selection(blobs, blobs, [seed], paths)['selected']))

    def test_fixed_module_relative_root_and_unresolved_path_tail_preserve_inputs(self):
        blobs = {
            'tests/test_relative.py': b'from pathlib import Path\nHERE = Path(__file__).resolve().parent\n'
                b'(HERE / "README.md").read_text()',
            'tests/test_dynamic.py': b'(root / name / "README.md").read_text()',
            'tests/test_other.py': b'pass',
        }
        paths = ['README.md', 'tests/README.md', 'docs/README.md']
        self.assertEqual({'test_dynamic'}, set(self.selection(blobs, blobs, ['docs/README.md'], paths)['selected']))
        self.assertEqual({'test_relative', 'test_dynamic'},
                         set(self.selection(blobs, blobs, ['tests/README.md'], paths)['selected']))

    def test_parent_segments_resolve_inside_root_and_escape_retains_ambiguity(self):
        header = b'from pathlib import Path\nROOT=Path(__file__).parents[1]\n'
        blobs = {'tests/test_inside.py': header + b'(ROOT / "docs" / ".." / "tests" / "README.md").read_text()',
                 'tests/test_outside.py': header + b'(ROOT / ".." / "checkout" / "docs" / "README.md").read_text()',
                 'tests/test_parent.py': header + b'directory=ROOT / ".."'}
        paths = ['docs/README.md', 'tests/README.md']
        self.assertEqual({'test_outside'}, set(self.selection(blobs, blobs, ['docs/README.md'], paths)['selected']))
        self.assertEqual({'test_inside', 'test_outside'},
                         set(self.selection(blobs, blobs, ['tests/README.md'], paths)['selected']))

    def test_scope_shadowing_export_and_unknown_predicates_retain_conservative_edges(self):
        cases = [
            'from pathlib import Path\ncustom.is_relative_to(ROOT / "docs")',
            'def check():\n global names\n names = ["docs/input.md"]\n return "x" in names',
            'def outer():\n names=[]\n def check():\n  nonlocal names\n  names=["docs/input.md"]\n  return "x" in names',
            'def check():\n names=["docs/input.md"]\n def inner(): return names\n return inner()',
            'def check():\n names={"x"}\n names=custom\n return names.isdisjoint({"docs/input.md"})',
            'def one():\n names={"x"}\ndef two(names):\n return names.isdisjoint({"docs/input.md"})',
            'from pathlib import Path\nROOT=Path(__file__).parents[1]\n'
                'def read(ROOT): return (ROOT / "input.md").read_text()',
            'from pathlib import Path\nPath=custom\nROOT=Path(__file__).parent\n(ROOT / "input.md").read_text()',
            'from pathlib import Path\ndef read(Path):\n root=Path(__file__).parent\n return (root / "input.md").read_text()',
            'def check():\n a=b\n b=a\n return a.is_relative_to(ROOT / "docs")',
            'from pathlib import Path\nroot=Path(__file__).parents[99]\n(root / "input.md").read_text()',
            'from pathlib import Path\nroot=Path(__file__, extra)\n(root / "input.md").read_text()',
            'root=alias\nalias=root\n(root / "input.md").read_text()',
            'def check():\n names=["docs/input.md"]\n alias=names\n names=alias\n return names',
            'from pathlib import Path\npath=factory()\npath.is_relative_to(ROOT / "docs")',
            'value = "docs" / "input.md"',
            'from pathlib import Path\ndef read(__file__):\n'
                ' return (Path(__file__).parent / "input.md").read_text()',
            'from pathlib import Path\n__file__=external\n'
                '(Path(__file__).parent / "input.md").read_text()',
            'from pathlib import Path\nPath=custom\ndef check(path: Path):\n'
                ' return path.is_relative_to(ROOT / "docs")',
            'from pathlib import Path\nROOT=Path(__file__).parents[1]\n'
                'def other():\n from custom import Path\n'
                '(ROOT / "input.md").read_text()',
            'from pathlib import Path\nROOT=Path(__file__).parents[1]\n'
                'def outer(ROOT):\n def inner(): return (ROOT / "input.md").read_text()\n return inner()',
            'from pathlib import Path\ndef outer(Path):\n'
                ' def inner(): return (Path(__file__).parent / "input.md").read_text()\n return inner()',
            'from pathlib import Path\nROOT=Path(__file__).parents[1]\n'
                'def mutate():\n global ROOT\n ROOT=other\n(ROOT / "input.md").read_text()',
            'from pathlib import Path\nROOT=Path(__file__).parent.parent.parent\n'
                '(ROOT / "checkout" / "docs" / "input.md").read_text()',
            'from pathlib import Path\ndef outer(*Path):\n'
                ' def inner(): return (Path(__file__).parent / "input.md").read_text()',
            'from pathlib import Path\ndef outer(**Path):\n'
                ' def inner(): return (Path(__file__).parent / "input.md").read_text()',
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                blobs = {'tests/test_input.py': raw.encode()}
                self.assertIn('test_input', self.selection(blobs, blobs, ['docs/input.md'], ['docs/input.md'])['selected'])

    def test_scoped_path_guards_follow_only_unambiguous_path_values(self):
        cases = [
            'from pathlib import Path\ndef check(root: Path, raw: Path):\n'
                ' path=(raw if flag else root / raw).resolve()\n return path.is_relative_to(root / "docs")',
            'from pathlib import Path as P\npath=P(__file__).absolute()\npath.is_relative_to(ROOT / "docs")',
            'names={"x"}\nnames.issubset({"docs/input.md"})',
            '{"x"}.issuperset({"docs/input.md"})',
            'def check():\n names=["docs/input.md"]\n alias=names\n return "x" in alias',
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                blobs = {'tests/test_guard.py': raw.encode()}
                self.assertNotIn('test_guard', self.selection(blobs, blobs, ['docs/input.md'], ['docs/input.md'])['selected'])

    def test_class_method_root_uses_module_binding_and_closure_uses_outer_binding(self):
        header = b'from pathlib import Path\nROOT=Path(__file__).parents[1]\n'
        blobs = {'tests/test_reader.py': header + b'class Reader:\n ROOT=other\n'
                 b' def read(self): return (ROOT / "docs/input.md").read_text()\n',
                 'tests/test_closure.py': header + b'def outer():\n ROOT=Path(__file__).parent\n'
                 b' def inner(): return (ROOT / "input.md").read_text()\n return inner()'}
        paths = ['docs/input.md', 'tests/input.md']
        self.assertEqual({'test_reader'}, set(self.selection(blobs, blobs, ['docs/input.md'], paths)['selected']))
        self.assertEqual({'test_closure'}, set(self.selection(blobs, blobs, ['tests/input.md'], paths)['selected']))

    def test_lexical_comparisons_skip_names_but_preserve_real_reads_and_escaped_values(self):
        blobs = {
            'tests/test_label.py': b'assert name == "docs/data.md"\n'
                b'assert name not in ["docs/data.md"]\n"docs/data.md"',
            'tests/test_reader.py': b'assert (ROOT / "docs/data.md").read_text() == "valid"',
            'tests/test_escape.py': b'INPUTS = ["docs/data.md"]\nconsume(INPUTS)',
            'tests/test_unknown.py': b'custom.isdisjoint({"docs/data.md"})',
        }
        plan = self.selection(blobs, blobs, ['docs/data.md'], ['docs/data.md'])
        self.assertEqual({'test_reader', 'test_escape', 'test_unknown'}, set(plan['selected']))

    def test_resource_changes_keep_real_archive_imports_and_directory_scans(self):
        blobs = {
            'work/a/oracle.py': b'from tests.helper import VALUE',
            'tests/helper.py': b'VALUE = 1',
            'tests/test_archive.py': b'import runpy\nrunpy.run_path("work/a/oracle.py")',
            'tests/test_scan.py': b'list((ROOT / "docs").rglob("*.md"))',
            'tests/test_independent.py': b'(ROOT / "other" / "README.md").read_text()',
        }
        plan = self.selection(blobs, blobs, ['tests/helper.py'])
        self.assertIn('test_archive', plan['selected'])
        plan = self.selection(blobs, blobs, ['docs/new.md'], ['docs/new.md', 'other/README.md'])
        self.assertEqual({'test_scan'}, set(plan['selected']))

    def test_evidence_closure_follows_test_helpers_packages_and_literal_inputs_only(self):
        blobs = {'tests/__init__.py': b'from .support import setup',
                 'tests/test_proof.py': b'from tests.support.helpers import expected\nimport pkg.subject',
                 'tests/support/__init__.py': b'from . import setup',
                 'tests/support/setup.py': b'from . import helpers',
                 'tests/support/helpers.py': b'from . import setup\nfrom pathlib import Path\n'
                     b'data=(ROOT / "tests" / "fixtures" / "expected.json").read_text()',
                 'src/pkg/subject.py': b'import tests.production_only',
                 'tests/production_only.py': b'pass', 'tests/unrelated.py': b'pass'}
        paths = set(blobs) | {'tests/fixtures/expected.json', 'tests/fixtures/unrelated.json'}
        deps.commit_graph.cache_clear()
        with patch.object(deps, 'snapshot', return_value=(paths, blobs)):
            found = deps.test_evidence_closure('evidence-fixture', 'base', ['test_proof.Proof.test_ok'])
            self.assertEqual({'tests/__init__.py', 'tests/test_proof.py', 'tests/support/__init__.py',
                              'tests/support/setup.py', 'tests/support/helpers.py', 'tests/fixtures/expected.json'}, found)
            # Missing roots remain visible to the caller's identity check, never disappearing silently.
            self.assertIn('tests/test_missing.py', deps.test_evidence_closure('evidence-fixture', 'base', ['test_missing']))

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

    def test_assigned_execution_namespace_is_opaque_but_stat_result_is_data(self):
        blobs = {'src/pkg/leaf.py': b'VALUE=1', 'tests/test_direct.py': b'import pkg.leaf',
                 'tests/test_dynamic.py': b'import importlib\nnamespace = importlib\nattribute = "import_module"\n'
                                         b'loader = getattr(namespace, attribute)\nloader("pkg." + "leaf")',
                 'src/pkg/resources.py': b'attributes = getattr(path.lstat(), "st_file_attributes", 0)',
                 'tests/test_resources.py': b'import pkg.resources'}
        p = self.selection(blobs, blobs, ['src/pkg/leaf.py'])
        self.assertEqual({'test_direct', 'test_dynamic'}, set(p['selected']))
        self.assertEqual(['test_resources'], p['excluded'])
        # The same accessor still participates when its real resource input changes.
        blobs['src/pkg/resources.py'] += b'\ndata = (ROOT / "fixtures" / "input.json").read_bytes()'
        p = self.selection(blobs, blobs, ['fixtures/input.json'], ['fixtures/input.json'])
        self.assertIn('test_resources', p['selected'])

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

    def test_function_contract_keeps_initialization_bindings_and_execution_inputs_fixed(self):
        before = b'import math\nLIMIT=1\ndef calculate(value):\n    return value + 1\n'
        self.assertTrue(deps.function_body_only(before, before.replace(b'value + 1', b'value + 2')))
        self.assertTrue(deps.function_body_only(before, before + b'# ordinary comment\n'))
        for after in (before.replace(b'LIMIT=1', b'LIMIT=2'), before.replace(b'calculate(value)', b'calculate(value=1)'),
                      before.replace(b'value + 1', b'other + 1'), before.replace(b'value + 1', b'math.sqrt(value)'),
                      before.replace(b'import math', b'import math\nimport subprocess'),
                      before.replace(b'def calculate', b'@decorator\ndef calculate'),
                      before + b'calculate(1)\n'):
            with self.subTest(after=after):
                self.assertFalse(deps.function_body_only(before, after))
        for before, after in (
            (b'class C:\n def f(self): return 1\n', b'class C:\n def f(self): return 2\n'),
            (b'async def f(): return 1\n', b'async def f(): return 2\n'),
        ):
            self.assertTrue(deps.function_body_only(before, after))

    def test_local_contract_rejects_opaque_or_resource_boundary_mutations(self):
        cases = [
            (b'def f():\n exec(code)\n return 1', b'def f():\n exec(code)\n return 2'),
            (b'def f():\n return reader("fixed")', b'def f():\n return reader("other")'),
            (b'def f():\n path="fixed"\n return reader(path)', b'def f():\n path="other"\n return reader(path)'),
            (b'def f(): return 1\ndef f(): return 2', b'def f(): return 1\ndef f(): return 3'),
            (b'class C:\n def f(self): return 1\n def f(self): return 2',
             b'class C:\n def f(self): return 1\n def f(self): return 3'),
        ]
        for before, after in cases:
            with self.subTest(before=before):
                self.assertFalse(deps.function_body_only(before, after))

    def test_local_contract_resolves_module_execution_aliases(self):
        for setup, call in (
            ('import subprocess as child', 'child.run(["tool"])'),
            ('from subprocess import run as launch', 'launch(["tool"])'),
            ('import runpy as loader', 'loader.run_path(path)'),
            ('import subprocess as child\nlaunch = child.run', 'launch(["tool"])'),
        ):
            before = (setup + '\ndef f():\n    ' + call + '\n    return 1\n').encode()
            with self.subTest(setup=setup):
                self.assertIn('subject.py', deps.graph({'subject.py': before}, {'subject.py'})[1])
                self.assertFalse(deps.function_body_only(before, before.replace(b'return 1', b'return 2')))
        before = b'import subprocess as child\ndef execute():\n child.run(["tool"])\ndef digest(value):\n return value[0:]\n'
        self.assertTrue(deps.function_body_only(before, before.replace(b'value[0:]', b'value[1:]')))


if __name__ == '__main__':
    unittest.main()
