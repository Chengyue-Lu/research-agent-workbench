"""Domain routing cannot attest exclusions or silently reinterpret missing evidence."""
import contextlib
import copy
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import ci_domain_audit as audit
import plan_ci as planner


def model():
    def domain(identity, sources, tests, inputs):
        return {'id': identity, 'owner': 'Chengyue-Lu', 'source_patterns': sources,
                'test_patterns': tests, 'input_patterns': inputs,
                'consumer_ids': [], 'unknowns': ['invocation closure unproved']}
    return {'version': 1, 'execution_authority': False, 'pilots': [], 'domains': [
        domain('docs', [], ['tests/test_documentation.py'], ['docs/**', 'work/**']),
        domain('runtime', ['src/**'], ['tests/test_reader.py'], ['docs/runtime.md'])]}


class DomainModelTests(unittest.TestCase):
    def test_named_repository_model_satisfies_official_validator(self):
        """Bind the real default input to the same strict parser and validator as the CLI."""
        value = json.loads((ROOT / audit.MODEL).read_bytes(), object_pairs_hook=planner.unique_object)
        audit.validate_model(value)

    def test_overlapping_runtime_document_is_not_collapsed_into_docs(self):
        value = model()
        audit.validate_model(value)
        self.assertEqual(['docs', 'runtime'], [r['domain'] for r in audit.routes('docs/runtime.md', value)])
        self.assertEqual([], audit.routes('unmapped.bin', value))
        report = audit.inventory_report({'docs/runtime.md': None, 'unmapped.bin': None,
                                         'tests/test_reader.py': None}, value)
        self.assertEqual(['unmapped.bin'], report['unassigned_paths'])
        self.assertFalse(report['membership_proved'])
        self.assertEqual(['docs', 'runtime'], report['overlapping_paths'][0]['domains'])

    def test_declarations_cannot_add_authority_or_hide_unknown_protocols(self):
        mutations = [lambda m: m.update(execution_authority=True), lambda m: m.update(version=True),
                     lambda m: m.update(version=2), lambda m: m.update(pilots=[{'skip': '*'}]),
                     lambda m: m.update(extra=True), lambda m: m.update(domains=[]),
                     lambda m: m['domains'].append(copy.deepcopy(m['domains'][0])),
                     lambda m: m['domains'][0].update(coverage_scope='none'),
                     lambda m: m['domains'][0].update(unknowns=[]),
                     lambda m: m['domains'][0].update(owner=' '),
                     lambda m: m['domains'][0].update(consumer_ids=['bad/consumer'])]
        for pattern in ('/docs/**', '../docs/**', 'docs//**', 'docs/../**', 'C:/docs/**', 'docs\\**', '[ab]/**', 'docs/\n**'):
            mutations.append(lambda m, p=pattern: m['domains'][0].update(input_patterns=[p]))
        for change in mutations:
            candidate = model()
            change(candidate)
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                audit.validate_model(candidate)
        with self.assertRaises(ValueError):
            audit.strings(['same', 'same'], 'ids')
        with self.assertRaises(ValueError):
            audit.strings([False], 'ids')

    def test_outcomes_remain_bound_and_missing_skipped_are_inconclusive(self):
        plan = {'plan_id': 'plan', 'binding': {'target': 'target'}}
        self.assertEqual('missing', audit.receipt_observation(plan, None)['status'])
        receipt = {'plan_id': 'plan', 'target': 'target', 'tests': [
            {'id': 'test_a.C.good', 'outcome': 'passed', 'duration_seconds': 2},
            {'id': 'test_a.C.bad', 'outcome': 'failed', 'duration_seconds': 1},
            {'id': 'test_b.C.skip', 'outcome': 'skipped'}, {'id': 'test_b.C.missing'}]}
        report = audit.receipt_observation(plan, receipt)
        self.assertEqual(['test_a.C.bad'], report['failing_ids'])
        self.assertEqual(['test_b.C.missing', 'test_b.C.skip'], report['inconclusive_ids'])
        self.assertEqual(3, report['module_case_seconds']['test_a'])
        self.assertFalse(report['execution_proved'])
        for change in (lambda r: r.update(target='stale'), lambda r: r.update(plan_id='different'),
                       lambda r: r['tests'].append(r['tests'][0]), lambda r: r.update(tests=None),
                       lambda r: r['tests'][0].update(outcome='success'),
                       lambda r: r['tests'][0].update(duration_seconds=float('nan')),
                       lambda r: r['tests'][0].update(duration_seconds=-1)):
            bad = copy.deepcopy(receipt)
            change(bad)
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                audit.receipt_observation(plan, bad)


class DomainGitTests(unittest.TestCase):
    def test_real_git_archive_routing_keeps_execution_and_ignores_worktree_rewrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            def git(*args):
                return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE).decode().strip()
            def write(path, raw):
                file = repo / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(raw.encode() if isinstance(raw, str) else raw)
            git('init', '-q', '-b', 'develop')
            git('config', 'user.name', 'CI fixture')
            git('config', 'user.email', 'fixture@example.invalid')
            git('config', 'core.autocrlf', 'false')
            for path in planner.TRUST_FILES:
                write(path, (ROOT / path).read_bytes())
            policy = {'policy_id': 'rwb-ci-impact', 'version': 1, 'consumer_fingerprint': '0' * 64,
                      'surfaces': {'docs': {'paths': ['docs/**', 'work/**'], 'class': 'fast', 'groups': ['documentation']}},
                      'groups': {'documentation': {'tests': ['test_documentation', 'test_pr_governance'],
                                'downstream': [], 'coverage': [], 'package': False, 'repository': False}},
                      'impact_evidence': {'positive_tests': ['test_reader.C.test_ok'], 'negative_tests': ['test_reader.C.test_bad']}}
            write(planner.POLICY, planner.canonical(policy))
            for name in ('test_documentation', 'test_pr_governance', 'test_reader'):
                write('tests/' + name + '.py', 'import unittest\nclass C(unittest.TestCase):\n def test_ok(self): pass\n def test_bad(self): pass\n')
            write('tests/test_reader.py', 'import unittest\nfrom pathlib import Path\n'
                  'ROOT = Path(__file__).resolve().parents[1]\nclass C(unittest.TestCase):\n'
                  ' def test_ok(self): self.assertTrue((ROOT / "work/A/capture.py").read_text())\n'
                  ' def test_bad(self): self.assertNotEqual((ROOT / "work/A/capture.py").read_text(), "bad")\n')
            write('docs/note.md', 'original')
            git('add', '.')
            git('commit', '-qm', 'base')
            base = git('rev-parse', 'HEAD')
            write('work/A/report.json', '{}')
            write('work/A/capture.py', 'print("actual executable")\n')
            git('add', '.')
            git('commit', '-qm', 'archive with executable')
            head = git('rev-parse', 'HEAD')
            plan = planner.make_plan(repo, base=base, head=head, target=head, repository='Example/repo',
                                     body='- **Risk tier**: R2\n- **Shared contract**: no\n- **Authority impact**: no')
            self.assertFalse(plan['blocked_reasons'], plan['reasons'])
            original = planner.canonical(plan)
            value = model()
            value['domains'][0]['consumer_ids'] = ['absent-historical-record']
            report = audit.build_report(repo, plan, value)
            self.assertFalse(report['execution_authority'])
            self.assertFalse(report['activation']['eligible'])
            self.assertFalse(report['performance']['savings_proved'])
            self.assertEqual(['absent-historical-record'], report['consumer_records']['absent_from_accepted_base'])
            capture = next(row for row in report['inputs'] if row['path'].endswith('capture.py'))
            self.assertEqual('executable', capture['facts']['role'])
            self.assertEqual(['docs'], [r['domain'] for r in capture['routes']])
            self.assertEqual(plan['tests'], report['accepted_execution']['tests'])
            self.assertEqual(original, planner.canonical(plan))
            write('work/A/capture.py', '# rewritten worktree cannot erase Git executable facts\n')
            self.assertEqual(report, audit.build_report(repo, plan, value))
            signature = report.pop('report_id')
            self.assertEqual(signature, planner.digest(report))
            with self.assertRaises((KeyError, ValueError)):
                planner.verify_plan(repo, report)
            write('plan.json', original)
            write('model.json', planner.canonical(value))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, audit.main(['--repo', str(repo), '--plan', str(repo/'plan.json'),
                                  '--model', str(repo/'model.json'), '--output', str(repo/'report.json')] ))
            self.assertEqual(signature, json.loads((repo/'report.json').read_bytes())['report_id'])
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                audit.main(['--repo', str(repo), '--plan', str(repo/'plan.json'),
                            '--model', str(repo/'model.json'), '--output', str(repo/'plan.json')])
            self.assertEqual(original, (repo/'plan.json').read_bytes())
            # A known docs-only Git change has no unresolved executable input.
            git('reset', '--hard', base)
            write('docs/note.md', 'changed documentation')
            git('add', 'docs/note.md')
            git('commit', '-qm', 'docs-only control')
            head = git('rev-parse', 'HEAD')
            docs_plan = planner.make_plan(repo, base=base, head=head, target=head, repository='Example/repo')
            write('plan.json', planner.canonical(docs_plan))
            write('model.json', planner.canonical(model()))
            write('receipt.json', planner.canonical({'plan_id': docs_plan['plan_id'], 'target': head, 'tests': []}))
            argv = sys.argv
            try:
                sys.argv = ['ci_domain_audit', '--repo', str(repo), '--plan', str(repo/'plan.json'),
                            '--model', str(repo/'model.json'), '--receipt', str(repo/'receipt.json'),
                            '--output', str(repo/'report.json')]
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as stopped:
                    runpy.run_path(str(ROOT/'.github/scripts/ci_domain_audit.py'), run_name='__main__')
                self.assertEqual(0, stopped.exception.code)
            finally:
                sys.argv = argv
            report = json.loads((repo/'report.json').read_bytes())
            self.assertEqual(3, len(report['activation']['blockers']))
            self.assertIn('check_pr_governance.py', report['producer_sources'])
            # A foreign submodule commit need not exist in this Git object store.
            git('update-index', '--add', '--cacheinfo', '160000,' + 'a' * 40 + ',docs/foreign')
            git('commit', '-qm', 'foreign gitlink')
            head = git('rev-parse', 'HEAD')
            linked = planner.make_plan(repo, base=base, head=head, target=head, repository='Example/repo')
            report = audit.build_report(repo, linked, model())
            row = next(row for row in report['inputs'] if row['path'] == 'docs/foreign')
            self.assertEqual('unknown', row['facts']['role'])
            self.assertFalse(row['versions'][0]['content_available'])
            self.assertIsNone(row['versions'][0]['sha256'])


if __name__ == '__main__':
    unittest.main()
