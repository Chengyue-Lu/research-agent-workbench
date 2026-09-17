"""Input classification preserves executable and simultaneous authority facts."""
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
