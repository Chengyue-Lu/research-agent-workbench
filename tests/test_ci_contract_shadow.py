"""P1 input roles and consumer evidence never replace the accepted execution plan."""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import ci_contract_shadow as shadow
import plan_ci as planner


def command(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE).decode().strip()


def write(repo, path, data):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data if isinstance(data, bytes) else data.encode())


class InputRoleTests(unittest.TestCase):
    def test_typed_inputs_preserve_runtime_test_and_archive_boundaries(self):
        rows = {
            'docs/README.md': 'document', 'README.md': 'document',
            'docs/workstreams/a/attempts/A/INDEX.yaml': 'evidence-data',
            'work/A/checks/report.json': 'evidence-data',
            'docs/workstreams/a/attempts/A/.gitattributes': 'archive-attributes',
            'tests/test_a.py': 'test-code', 'tests/fixtures/a.json': 'test-input',
            'schemas/v1/a.json': 'runtime-input', 'registry/a.yaml': 'runtime-input',
            'examples/a.md': 'runtime-input', '.agents/skills/a/SKILL.md': 'runtime-input',
            'src/research_workbench/template.txt': 'runtime-input',
            '.github/scripts/plan_ci.py': 'selection-authority', '.github/workflows/new.yml': 'selection-authority',
            'tests/coverage_policy.yaml': 'coverage-authority', 'pyproject.toml': 'packaging-authority',
            '.gitattributes': 'repository-authority', '.github/governance-policy.json': 'repository-authority',
            'docs/workstreams/input.yaml': 'unknown', 'unknown.bin': 'unknown',
        }
        for path, expected in rows.items():
            with self.subTest(path=path):
                raw = b'* -text\n' if path.endswith('.gitattributes') else b'data'
                self.assertEqual(expected, shadow.input_role(path, [('100644', raw)])[0])
        self.assertEqual('archive-attributes', shadow.input_role('work/A/.gitattributes',
            [('100644', b'* -text\n'), ('100644', b'* -text whitespace=cr-at-eol\r\n')])[0])
        self.assertEqual('unknown', shadow.input_role('work/A/.gitattributes', [('100644', b'* filter=custom')])[0])

    def test_scripts_modes_and_unsafe_paths_cannot_hide_as_documents(self):
        for path, versions in (
            ('work/A/oracle.py', [('100644', b'pass')]),
            ('docs/a.md', [('100644', b'#!/bin/sh\n')]),
            ('work/A/README.md', [('100755', b'text')]),
            ('docs/a.ps1', [('100644', b'Write-Output ok')]),
        ):
            with self.subTest(path=path):
                self.assertEqual('executable', shadow.input_role(path, versions)[0])
        for versions in ([('120000', b'target')], [('160000', b'')], [('100644', b'a'), ('100755', b'a')]):
            self.assertEqual('unknown', shadow.input_role('docs/a.md', versions)[0])
        for path in ('', '/absolute', '../escape', 'docs/../a.md', 'docs\\a.md', 'C:/a.md', 'docs//a.md'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                shadow.input_role(path, [('100644', b'data')])
        with self.assertRaisesRegex(ValueError, 'no Git version'):
            shadow.input_role('docs/a.md', [])

    def test_reference_evidence_distinguishes_read_write_and_bare_names(self):
        source = b'''(root / "README.md").write_text("body")
(root / "README.md").read_bytes()
names = {"README.md": "generated text"}
ignored = 3
(root / "README.md").exists()
consume((((((("README.md",),),),),),))
'''
        observations = shadow.reference_observations('docs/README.md', source)
        contexts = [row['context'] for row in observations]
        self.assertIn('write-target-syntax', contexts)
        self.assertIn('read-target-syntax', contexts)
        self.assertIn('name-literal', contexts)
        self.assertEqual([], shadow.reference_observations('docs/OTHER.md', source))
        self.assertEqual('unparseable-consumer', shadow.reference_observations('a', b'not python (')[0]['context'])


class ContractShadowGitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.seed = Path(cls.temp.name) / 'seed'
        cls.seed.mkdir()
        command(cls.seed, 'init', '-q', '-b', 'develop')
        command(cls.seed, 'config', 'user.name', 'CI fixture')
        command(cls.seed, 'config', 'user.email', 'fixture@example.invalid')
        command(cls.seed, 'config', 'core.autocrlf', 'false')
        for path in planner.TRUST_FILES:
            write(cls.seed, path, (ROOT / path).read_bytes())
        write(cls.seed, '.gitignore', '__pycache__/\n')
        policy = {'policy_id':'rwb-ci-impact','version':1,'consumer_fingerprint':'0'*64,
            'surfaces': {'docs': {'paths':['docs/**','work/**'],'class':'fast','groups':['documentation']}},
            'groups': {'documentation': {'tests':['test_documentation','test_pr_governance'],
                'downstream':[],'coverage':[],'package':False,'repository':False}},
            'impact_evidence': {'positive_tests':['test_reader.Reader.test_ok'],
                                'negative_tests':['test_reader.Reader.test_bad']}}
        write(cls.seed, planner.POLICY, planner.canonical(policy))
        for name in ('test_documentation','test_pr_governance'):
            write(cls.seed, 'tests/'+name+'.py', 'import unittest\nclass Check(unittest.TestCase):\n def test_ok(self): pass\n')
        write(cls.seed, 'tests/test_reader.py', 'import unittest\nfrom pathlib import Path\n'
            'ROOT=Path(__file__).resolve().parents[1]\nclass Reader(unittest.TestCase):\n'
            ' def test_ok(self): self.assertEqual((ROOT / "docs/input.md").read_text(), "good")\n'
            ' def test_bad(self): self.assertNotEqual((ROOT / "docs/input.md").read_text(), "bad")\n')
        write(cls.seed, 'tests/test_unknown.py', 'from pathlib import Path\n'
            'def reader(root, name): return (Path(root) / name).read_bytes()\n')
        write(cls.seed, 'docs/input.md', 'good')
        command(cls.seed, 'add', '.')
        command(cls.seed, 'commit', '-qm', 'accepted fixture')

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name) / 'repo'
        command(Path(temp.name), 'clone', '-q', '--no-hardlinks', str(self.seed), str(self.repo))
        command(self.repo, 'config', 'user.name', 'CI fixture')
        command(self.repo, 'config', 'user.email', 'fixture@example.invalid')
        self.base = command(self.repo, 'rev-parse', 'HEAD')

    def commit(self, path, data):
        write(self.repo, path, data)
        command(self.repo, 'add', '.')
        command(self.repo, 'commit', '-qm', 'candidate')
        return command(self.repo, 'rev-parse', 'HEAD')

    def plan(self):
        head = command(self.repo, 'rev-parse', 'HEAD')
        return planner.make_plan(self.repo, base=self.base, head=head, target=head, repository='Example/repo',
            body='- **Risk tier**: R2\n- **Shared contract**: no\n- **Authority impact**: no')

    def invocation_fixture(self):
        consumer = 'tests/test_invocations.py'
        source = (b'import subprocess as child\ndef probe(executor, argv):\n'
                  b' child.run(["git", "rev-parse", "HEAD"])\n return executor(argv)\n')
        write(self.repo, 'src/research_workbench/leaf.py', 'VALUE=1\n')
        self.base = self.commit(consumer, source)
        self.commit('src/research_workbench/leaf.py', 'VALUE=2\n')
        plan = self.plan()
        return consumer, source, plan, shadow.build_report(self.repo, plan)

    def test_invocation_catalog_binds_every_call_and_snapshot_without_changing_plan(self):
        consumer, source, plan, report = self.invocation_fixture()
        before = planner.canonical(plan)
        catalog = report['invocation_evidence']
        self.assertFalse(catalog['execution_authority'])
        self.assertIn('never means absent inputs', catalog['unknown_argument_policy'])
        columns = catalog['site_columns']
        self.assertEqual(['span', 'scope', 'ast_sha256', 'callee', 'binding', 'operation', 'detail_id'], columns)
        records = [row for row in catalog['consumers'] if row['consumer'] == consumer]
        self.assertEqual({'merge_base', 'head'}, {row['snapshot'] for row in records})
        self.assertEqual(2, len({row['id'] for row in records}))
        self.assertEqual(1, len({row['source_id'] for row in records}))
        for record in records:
            self.assertEqual(plan['binding'][record['snapshot']], record['commit'])
            self.assertEqual('100644', record['mode'])
            self.assertEqual(hashlib.sha256(source).hexdigest(), record['source_sha256'])
            self.assertEqual('parsed', record['analysis_status'])
            self.assertNotIn('sites', record)
            shared = catalog['sources'][record['source_id']]
            self.assertEqual(consumer, shared['consumer'])
            self.assertEqual(record['source_sha256'], shared['source_sha256'])
            sites = [dict(zip(columns, row, strict=True)) for row in shared['calls']]
            self.assertEqual(2, len(sites))
            self.assertEqual(1, sum(site['operation'] == 'unknown' for site in sites))
            self.assertTrue(record['fallback']['opaque'])
            for site in sites:
                detail = catalog['details'][site['detail_id']]
                self.assertFalse(detail['execution_authority'])
                self.assertEqual('unproved', detail['resolution']['input_closure'])
                if site['operation'] == 'unknown':
                    self.assertEqual({'resolution', 'unresolved', 'execution_authority'}, set(detail))
                else:
                    self.assertEqual({'dimensions', 'invocation', 'inputs', 'outputs', 'resolution',
                                      'unresolved', 'execution_authority'}, set(detail))
        linked = [edge for row in report['dependency_review'] for edge in row['edges']
                  if edge['consumer'] == consumer]
        self.assertTrue(linked)
        for edge in linked:
            self.assertEqual({row['id'] for row in records}, set(edge['invocation_evidence_ids']))
        shadow.verify_invocation_evidence(self.repo, plan, report)
        self.assertEqual(before, planner.canonical(plan))
        self.assertFalse(report['activation']['eligible'])
        # Dirty source cannot rewrite source-bound observations at either Git ref.
        write(self.repo, consumer, 'pass\n')
        self.assertEqual(catalog, shadow.build_report(self.repo, plan)['invocation_evidence'])
        # A future classifier must not silently lose newly understood unknown-call
        # inputs through this compact projection. This tests the schema boundary,
        # not a mocked program execution or a substitute for dependency evidence.
        describe = shadow.ci_input_facts.describe_invocation
        def future_unknown_inputs(*args, **kwargs):
            fact = describe(*args, **kwargs)
            if fact['operation'] == 'unknown':
                fact['inputs'] = [{'role': 'future-input-semantics'}]
            return fact
        with patch.object(shadow.ci_input_facts, 'describe_invocation', side_effect=future_unknown_inputs):
            with self.assertRaisesRegex(ValueError, 'unknown call acquired input semantics'):
                shadow.invocation_evidence(self.repo, plan)

    def test_resigned_invocation_omission_forgery_and_dangling_links_are_rejected(self):
        consumer, _, plan, original = self.invocation_fixture()
        def catalog(report):
            return report['invocation_evidence']
        def target(report):
            return next(row for row in catalog(report)['consumers']
                        if row['consumer'] == consumer and row['snapshot'] == 'head')
        def source(report):
            return catalog(report)['sources'][target(report)['source_id']]
        def unknown(report):
            index = catalog(report)['site_columns'].index('operation')
            return next(row for row in source(report)['calls'] if row[index] == 'unknown')
        def detail(report):
            index = catalog(report)['site_columns'].index('detail_id')
            return catalog(report)['details'][unknown(report)[index]]
        def change_site(report, column, value):
            unknown(report)[catalog(report)['site_columns'].index(column)] = value
        def omitted(report):
            catalog(report)['consumers'].remove(target(report))
        def duplicated(report):
            catalog(report)['consumers'].append(copy.deepcopy(target(report)))
        def missing_site(report):
            source(report)['calls'].remove(unknown(report))
        def dangling_edge(report):
            edge = next(edge for row in report['dependency_review'] for edge in row['edges']
                        if edge['consumer'] == consumer)
            edge['invocation_evidence_ids'] = ['0' * 64]
        def omitted_chain(report):
            chain = next(row for row in report['dependency_review']
                         if any(edge['consumer'] == consumer for edge in row['edges']))
            report['dependency_review'].remove(chain)
        def orphan_source(report):
            extra = copy.deepcopy(source(report))
            extra['consumer'] = 'tests/orphaned_source.py'
            catalog(report)['sources']['pending-orphan'] = extra
        def orphan_detail(report):
            extra = copy.deepcopy(detail(report))
            extra['unresolved'].append('orphaned-detail')
            catalog(report)['details']['pending-orphan'] = extra
        def reordered_columns(report):
            columns = catalog(report)['site_columns']
            columns[0], columns[1] = columns[1], columns[0]
            # Even a consistently reordered encoding must not redefine the schema.
            for shared in catalog(report)['sources'].values():
                for row in shared['calls']:
                    row[0], row[1] = row[1], row[0]
        def wrong_source_binding(report):
            other = next(row for row in catalog(report)['consumers']
                         if row['source_id'] is not None and row['consumer'] != consumer)
            target(report)['source_id'] = other['source_id']
        mutations = {
            'omitted-consumer': omitted,
            'duplicated-consumer': duplicated,
            'omitted-unknown-site': missing_site,
            'dangling-edge': dangling_edge,
            'omitted-chain': omitted_chain,
            'wrong-path': lambda r: target(r).__setitem__('consumer', 'tests/elsewhere.py'),
            'wrong-snapshot': lambda r: target(r).__setitem__('snapshot', 'merge_base'),
            'wrong-source-hash': lambda r: target(r).__setitem__('source_sha256', '0' * 64),
            'wrong-git-object': lambda r: target(r).__setitem__('object_id', '0' * 40),
            'wrong-mode': lambda r: target(r).__setitem__('mode', '120000'),
            'forged-classification': lambda r: change_site(r, 'operation', 'git-identity'),
            'forged-site': lambda r: change_site(r, 'span', [999, 0, 999, 1]),
            'forged-closure': lambda r: detail(r)['resolution'].__setitem__('input_closure', 'proved'),
            'forged-authority': lambda r: r.__setitem__('execution_authority', True),
            'wrong-plan': lambda r: r.__setitem__('observed_plan_id', '0' * 64),
            'wrong-report-binding': lambda r: r['binding'].__setitem__('head', self.base),
            'orphan-source': orphan_source,
            'orphan-detail': orphan_detail,
            'reordered-columns': reordered_columns,
            'duplicated-column': lambda r: catalog(r)['site_columns'].__setitem__(0, 'scope'),
            'wrong-source-binding': wrong_source_binding,
            'dangling-source': lambda r: target(r).__setitem__('source_id', '0' * 64),
            'dangling-detail': lambda r: change_site(r, 'detail_id', '0' * 64),
        }
        for name, mutate in mutations.items():
            with self.subTest(mutation=name):
                report = copy.deepcopy(original)
                mutate(report)
                # Re-sign all content-addressed tables and references so rejection
                # must reconstruct evidence rather than only notice stale digests.
                evidence = catalog(report)
                detail_ids = {old_id: planner.digest(value) for old_id, value in evidence['details'].items()}
                evidence['details'] = {detail_ids[old_id]: value for old_id, value in evidence['details'].items()}
                detail_index = evidence['site_columns'].index('detail_id')
                for shared in evidence['sources'].values():
                    for row in shared['calls']:
                        row[detail_index] = detail_ids.get(row[detail_index], row[detail_index])
                source_ids = {old_id: planner.digest({'consumer': value['consumer'],
                                                     'source_sha256': value['source_sha256']})
                              for old_id, value in evidence['sources'].items()}
                evidence['sources'] = {source_ids[old_id]: value for old_id, value in evidence['sources'].items()}
                ids = {}
                for row in evidence['consumers']:
                    row['source_id'] = source_ids.get(row['source_id'], row['source_id'])
                    old_id = row['id']
                    unsigned = dict(row); unsigned.pop('id')
                    row['id'] = planner.digest(unsigned)
                    ids[old_id] = row['id']
                for row in report['dependency_review']:
                    for edge in row['edges']:
                        edge['invocation_evidence_ids'] = [ids.get(value, value)
                                                          for value in edge['invocation_evidence_ids']]
                unsigned = dict(report); unsigned.pop('report_id')
                report['report_id'] = planner.digest(unsigned)
                with self.assertRaises(ValueError):
                    shadow.verify_invocation_evidence(self.repo, plan, report)

    def test_invocation_old_removed_calls_and_same_bytes_new_path_remain_distinct(self):
        consumer, source, _, _ = self.invocation_fixture()
        # Keep the original accepted two-call consumer, but remove its unknown
        # call from head and add identical bytes at another consumer path.
        relocated = 'tests/test_relocated_invocations.py'
        write(self.repo, consumer, source.replace(b' return executor(argv)\n', b' return None\n'))
        self.commit(relocated, source)
        plan = self.plan()
        report = shadow.build_report(self.repo, plan)
        catalog = report['invocation_evidence']
        rows = catalog['consumers']
        def sites(record):
            return [dict(zip(catalog['site_columns'], row, strict=True))
                    for row in catalog['sources'][record['source_id']]['calls']]
        old = next(row for row in rows if row['consumer'] == consumer and row['snapshot'] == 'merge_base')
        current = next(row for row in rows if row['consumer'] == consumer and row['snapshot'] == 'head')
        moved = next(row for row in rows if row['consumer'] == relocated and row['snapshot'] == 'head')
        self.assertEqual((2, 1, 2), (len(sites(old)), len(sites(current)), len(sites(moved))))
        self.assertEqual(old['source_sha256'], moved['source_sha256'])
        self.assertNotEqual(old['id'], moved['id'])
        self.assertEqual(3, len({row['source_id'] for row in (old, current, moved)}))
        self.assertNotEqual(catalog['sources'][old['source_id']]['consumer'],
                            catalog['sources'][moved['source_id']]['consumer'])
        self.assertEqual(sites(old), sites(moved))
        self.assertFalse(any(row['consumer'] == relocated and row['snapshot'] == 'merge_base' for row in rows))
        self.assertIn('test_invocations', plan['selection']['selected'])
        self.assertTrue(any(site['operation'] == 'unknown' for site in sites(old)))
        shadow.verify_invocation_evidence(self.repo, plan, report)

    def test_invocation_parse_and_git_mode_failures_remain_explicit(self):
        consumer, _, _, _ = self.invocation_fixture()
        self.commit(consumer, 'def incomplete(')
        plan = self.plan()
        with self.assertRaisesRegex(ValueError, 'unproved executable impact obligations'):
            shadow.build_report(self.repo, plan)
        catalog = shadow.invocation_evidence(self.repo, plan)
        row = next(row for row in catalog['consumers']
                   if row['consumer'] == consumer and row['snapshot'] == 'head')
        self.assertEqual('unparseable', row['analysis_status'])
        self.assertNotIn('sites', row)
        self.assertEqual([], catalog['sources'][row['source_id']]['calls'])
        self.assertTrue(row['fallback']['unlocated_causes'])
        self.assertEqual(hashlib.sha256(b'def incomplete(').hexdigest(), row['source_sha256'])
        self.assertFalse(catalog['execution_authority'])
        # A real Git symlink entry need not be creatable by the Windows filesystem.
        write(self.repo, consumer, '../tools/unknown.py')
        blob = command(self.repo, 'hash-object', '-w', consumer)
        command(self.repo, 'update-index', '--cacheinfo', '120000,' + blob + ',' + consumer)
        command(self.repo, 'commit', '-qm', 'candidate symlink input')
        plan = self.plan()
        catalog = shadow.invocation_evidence(self.repo, plan)
        row = next(row for row in catalog['consumers']
                   if row['consumer'] == consumer and row['snapshot'] == 'head')
        self.assertEqual(('120000', blob, 'non-regular-python'),
                         (row['mode'], row['object_id'], row['analysis_status']))
        self.assertIsNone(row['source_sha256'])
        self.assertNotIn('sites', row)
        self.assertIsNone(row['source_id'])
        self.assertTrue(row['fallback']['unlocated_causes'])
        self.assertFalse(catalog['execution_authority'])

    def test_archive_classification_is_separate_from_execution_authority(self):
        self.commit('docs/workstreams/a/attempts/A/INDEX.yaml', 'schema_version: 1\n')
        plan = self.plan()
        before = planner.canonical(plan)
        report = shadow.build_report(self.repo, plan)
        self.assertEqual('evidence-data', report['inputs'][0]['role'])
        self.assertEqual(1, len(report['summary']['classification_conflicts']))
        self.assertIn('unbounded-resource', report['summary']['review_reasons'])
        self.assertFalse(report['activation']['eligible'])
        self.assertEqual('full', report['accepted_obligations']['behavioral_scope'])
        self.assertEqual(before, planner.canonical(plan))
        unsigned = dict(report); signature = unsigned.pop('report_id')
        self.assertEqual(planner.digest(unsigned), signature)

    def test_git_bound_consumer_record_cannot_refresh_its_own_failed_pin(self):
        source = 'src/research_workbench/reader.py'
        write(self.repo, 'src/research_workbench/__init__.py', '')
        for name in ('test_ci_plan.py', 'test_ci_checks.py'):
            write(self.repo, 'tests/' + name, (ROOT/'tests'/name).read_bytes())
        write(self.repo, source, 'def read(path):\n return path.read_bytes()\n')
        write(self.repo, 'tests/test_reader.py', 'import unittest\nfrom pathlib import Path\n'
            'from research_workbench.reader import read\nROOT=Path(__file__).resolve().parents[1]\n'
            'class Reader(unittest.TestCase):\n'
            ' def test_ok(self): self.assertEqual(read(ROOT / "docs/input.md"), b"good")\n'
            ' def test_bad(self): self.assertNotEqual(read(ROOT / "docs/input.md"), b"bad")\n')
        def execute_reader():
            return subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_reader.py'],
                cwd=self.repo, env={**os.environ, 'PYTHONPATH':str(self.repo/'src')}, capture_output=True, text=True)
        policy = json.loads((self.repo / planner.POLICY).read_bytes())
        record = {'id':'reader-input','owner':'Chengyue-Lu','consumer':source,
            'pins':{p:hashlib.sha256((self.repo/p).read_bytes()).hexdigest()
                    for p in (source, 'tests/test_reader.py')},
            'entrypoints':['read'],'inputs':['caller paths'],'outputs':['bytes'],
            'invariants':['same input bytes'],'unresolved':['caller instances'],
            'positive_tests':['test_reader.Reader.test_ok'],'negative_tests':['test_reader.Reader.test_bad'],
            'execution_authority':False}
        policy.update(version=2, consumer_contracts=[record])
        self.base = self.commit(planner.POLICY, planner.canonical(policy))
        good = execute_reader()
        self.assertEqual(0, good.returncode, good.stderr)
        old = copy.deepcopy(record)
        write(self.repo, source, 'def read(path):\n return b"wrong"\n')
        record['pins'][source] = hashlib.sha256((self.repo/source).read_bytes()).hexdigest()
        self.commit(planner.POLICY, planner.canonical(policy))
        failed = execute_reader()
        self.assertNotEqual(0, failed.returncode)
        self.assertIn('FAIL: test_ok', failed.stderr)
        plan = self.plan()
        self.assertFalse(plan['blocked_reasons'], plan['blocked_reasons'])
        before = planner.canonical(plan)
        report = shadow.build_report(self.repo, plan)
        row = report['consumer_contract_review'][0]
        self.assertEqual('candidate-revised', row['status'])
        self.assertEqual(old, row['definition'])
        self.assertTrue(row['checks']['base']['declared_pins_match'])
        self.assertFalse(row['checks']['head']['declared_pins_match'])
        self.assertIn(source + ': bytes changed', row['checks']['head']['drift'])
        self.assertFalse(row['execution_authority'])
        self.assertEqual(before, planner.canonical(plan))
        # Uncommitted worktree bytes cannot repair the immutable candidate's drift.
        write(self.repo, source, 'def read(path):\n return path.read_bytes()\n')
        self.assertEqual(row, shadow.build_report(self.repo, plan)['consumer_contract_review'][0])
        self.assertTrue(all(c['source']=='accepted-base-impact-policy' for c in report['accepted_contracts']))
        with self.assertRaises((KeyError, ValueError)):
            planner.verify_plan(self.repo, report)

    def test_real_failing_document_consumer_remains_selected(self):
        self.commit('docs/input.md', 'bad')
        plan = self.plan()
        report = shadow.build_report(self.repo, plan)
        consumers = {item['test']: item for item in report['dependency_review']}
        self.assertIn('test_reader', consumers)
        self.assertEqual('data-instance-to-code-consumers', consumers['test_reader']['review_reason'])
        run = subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_reader.py'],
                             cwd=self.repo,capture_output=True,text=True)
        self.assertNotEqual(0,run.returncode)
        self.assertIn('FAILED',run.stderr)

    def test_old_consumers_and_removed_inputs_are_retained(self):
        (self.repo/'docs/input.md').unlink()
        self.commit('docs/note.md', 'record removed input')
        report = shadow.build_report(self.repo, self.plan())
        self.assertEqual({'document'}, {r['role'] for r in report['inputs']})
        deleted = next(r for r in report['inputs'] if r['path']=='docs/input.md')
        self.assertEqual(['merge_base'], [v['snapshot'] for v in deleted['versions']])
        self.assertIn('test_reader',{c['test'] for c in report['dependency_review']})
        self.assertTrue(any(edge['syntax_evidence'] for chain in report['dependency_review'] for edge in chain['edges']))
        self.assertTrue(all([v['snapshot'] for v in edge['syntax_evidence']] == ['merge_base', 'head']
                            for chain in report['dependency_review'] for edge in chain['edges']))

    def test_tampered_or_weakened_plan_and_wrong_merge_are_rejected(self):
        self.commit('docs/workstreams/a/attempts/A/report.json', '{}')
        plan = self.plan()
        bad = copy.deepcopy(plan); bad['risk']='R0'
        with self.assertRaisesRegex(ValueError,'digest'):
            shadow.build_report(self.repo,bad)
        for field, value in (('coverage_scope','none'),('selection',{}),('changes',[])):
            bad=copy.deepcopy(plan); bad[field]=value
            unsigned=dict(bad); unsigned.pop('plan_id'); bad['plan_id']=planner.digest(unsigned)
            with self.subTest(field=field), self.assertRaises(ValueError):
                shadow.build_report(self.repo,bad)
        bad=copy.deepcopy(plan); bad['binding']['target']=self.base
        unsigned=dict(bad); unsigned.pop('plan_id'); bad['plan_id']=planner.digest(unsigned)
        with self.assertRaisesRegex(ValueError,'parents'):
            shadow.build_report(self.repo,bad)

    def test_candidate_policy_never_becomes_report_contract_authority(self):
        data=json.loads((self.repo/planner.POLICY).read_bytes())
        data['groups']['forged']={'tests':['test_reader'],'coverage':[],'downstream':[],'package':False,'repository':False}
        self.commit(planner.POLICY,planner.canonical(data))
        report=shadow.build_report(self.repo,self.plan())
        self.assertNotIn('forged',{c['id'] for c in report['accepted_contracts']})
        self.assertEqual('selection-policy-metadata',report['inputs'][0]['role'])
        row = report['propagation_review']['inputs'][0]
        self.assertFalse(row['accepted_graph_seed'])
        self.assertIsNone(row['isolated_ordinary_closure'])
        self.assertEqual([], row['unclassified_obligations'])

    def test_each_archive_input_retains_its_overlapping_resource_closure(self):
        paths = ['docs/workstreams/a/attempts/A/first.json', 'docs/workstreams/a/attempts/A/second.yaml']
        write(self.repo, paths[0], '{}')
        self.commit(paths[1], 'version: 1\n')
        plan = self.plan()
        original = planner.canonical(plan)
        report = shadow.build_report(self.repo, plan)
        review = report['propagation_review']
        self.assertFalse(review['execution_authority'])
        rows = {row['path']: row for row in review['inputs']}
        for path in paths:
            row = rows[path]
            self.assertEqual(['behavioral_scope', 'coverage_scope', 'package_smoke', 'repository_smoke'],
                             row['unclassified_obligations'])
            self.assertEqual(['unclassified-obligation', 'unbounded-resource'], row['review_mechanisms'])
            self.assertIn('test_unknown', row['isolated_ordinary_closure']['selected_modules'])
            self.assertEqual([], row['isolated_ordinary_closure']['errors'])
        self.assertEqual(rows[paths[0]]['isolated_ordinary_closure'], rows[paths[1]]['isolated_ordinary_closure'])
        # A single accepted BFS witness cannot credit both roots; neither root is safe to discard.
        self.assertNotEqual(rows[paths[0]]['retained_witness_modules'], rows[paths[1]]['retained_witness_modules'])
        self.assertEqual(original, planner.canonical(plan))
        self.assertEqual(report, shadow.build_report(self.repo, plan))

    def test_mixed_executable_and_archive_inputs_keep_three_mechanisms(self):
        source = 'src/research_workbench/leaf.py'
        write(self.repo, source, 'VALUE=1\n')
        write(self.repo, 'tests/test_leaf.py', 'from research_workbench import leaf\n')
        self.base = self.commit('tests/test_dynamic.py', 'import runpy\ndef replay(path): return runpy.run_path(path)\n')
        write(self.repo, source, 'VALUE=2\n')
        archive = 'docs/workstreams/a/attempts/A/run.log'
        self.commit(archive, 'captured execution')
        plan = self.plan()
        before = planner.canonical(plan)
        report = shadow.build_report(self.repo, plan)
        rows = {row['path']: row for row in report['propagation_review']['inputs']}
        self.assertIn('opaque-execution', rows[source]['review_mechanisms'])
        self.assertEqual([], rows[source]['unclassified_obligations'])
        self.assertIn('test_dynamic', rows[source]['isolated_ordinary_closure']['witness_modules']['opaque-execution'])
        self.assertIn('unclassified-obligation', rows[archive]['review_mechanisms'])
        self.assertIn('unbounded-resource', rows[archive]['review_mechanisms'])
        self.assertTrue(any(row['fallback_edge_kinds'] for row in report['dependency_review']))
        self.assertEqual(before, planner.canonical(plan))
        self.assertFalse(report['activation']['eligible'])

    def test_gitlink_reports_object_identity_without_inventing_blob_bytes(self):
        path = 'vendor/submodule'
        command(self.repo, 'update-index', '--add', '--cacheinfo', '160000,' + self.base + ',' + path)
        command(self.repo, 'commit', '-qm', 'candidate gitlink')
        report = shadow.build_report(self.repo, self.plan())
        row = report['inputs'][0]
        self.assertEqual(path, row['path'])
        self.assertEqual('unknown', row['role'])
        self.assertIsNone(row['executable'])
        version = row['versions'][0]
        self.assertEqual(('160000', 'commit', self.base), (version['mode'], version['object_type'], version['object_id']))
        self.assertFalse(version['content_available'])
        self.assertIsNone(version['sha256'])
        self.assertFalse(report['execution_authority'])

    def test_resigned_unclassified_reasons_cannot_change_attribution(self):
        self.commit('docs/workstreams/a/attempts/A/run.log', 'evidence')
        plan = self.plan()
        for obligation in plan['obligation_reasons']:
            bad = copy.deepcopy(plan)
            bad['obligation_reasons'][obligation] = []
            unsigned = dict(bad); unsigned.pop('plan_id'); bad['plan_id'] = planner.digest(unsigned)
            with self.subTest(obligation=obligation), self.assertRaisesRegex(ValueError, 'unclassified obligation'):
                shadow.build_report(self.repo, bad)
        for value in (None, {}, {**plan['obligation_reasons'], 'behavioral_scope': [3]},
                      {**plan['obligation_reasons'], 'coverage_scope': ['unclassified dependency surface: invented.bin']}):
            bad = copy.deepcopy(plan)
            bad['obligation_reasons'] = value
            unsigned = dict(bad); unsigned.pop('plan_id'); bad['plan_id'] = planner.digest(unsigned)
            with self.subTest(value=value), self.assertRaises(ValueError):
                shadow.build_report(self.repo, bad)
        extra = copy.deepcopy(plan)
        extra['obligation_reasons']['behavioral_scope'].append('Agent requested additional complete regression')
        unsigned = dict(extra); unsigned.pop('plan_id'); extra['plan_id'] = planner.digest(unsigned)
        report = shadow.build_report(self.repo, extra)
        self.assertEqual('full', report['accepted_obligations']['behavioral_scope'])

    def test_isolated_graph_uses_merge_base_when_both_sides_remove_a_reader(self):
        path = 'docs/workstreams/a/attempts/A/input.json'
        reader = 'tests/test_retired.py'
        write(self.repo, path, '{}')
        self.base = self.commit(reader, 'INPUT = ' + repr(path) + '\n')
        ancestor = self.base
        write(self.repo, reader, 'VALUE = 0\n')
        head = self.commit(path, '{"changed": true}')
        command(self.repo, 'checkout', '-qb', 'base-side', ancestor)
        base = self.commit(reader, 'VALUE = 0\n')
        command(self.repo, 'merge', '--no-ff', '-m', 'merge', head)
        target = command(self.repo, 'rev-parse', 'HEAD')
        plan = planner.make_plan(self.repo, base=base, head=head, target=target, repository='Example/repo')
        report = shadow.build_report(self.repo, plan)
        review = report['propagation_review']
        self.assertEqual({'merge_base': ancestor, 'head': head}, review['graph_binding'])
        row = next(item for item in review['inputs'] if item['path'] == path)
        self.assertIn('test_retired', row['isolated_ordinary_closure']['selected_modules'])
        wrong, *_ = planner.dependencies.select(self.repo, base, head, {path})
        self.assertNotIn('test_retired', wrong['selected'])

    def test_executable_keeps_ordinary_and_opaque_consumers(self):
        write(self.repo,'src/research_workbench/leaf.py','VALUE=1\n')
        write(self.repo,'tests/test_leaf.py','from research_workbench import leaf\n')
        write(self.repo,'tests/test_leaf_consumer.py','from test_leaf import leaf\n')
        self.base=self.commit('tests/test_dynamic.py','import runpy\ndef replay(path): return runpy.run_path(path)\n')
        self.commit('src/research_workbench/leaf.py','VALUE=2\n')
        report=shadow.build_report(self.repo,self.plan())
        reasons={r['review_reason'] for r in report['dependency_review']}
        self.assertIn('opaque-execution',reasons)
        self.assertIn('accepted-dependency',reasons)
        self.assertEqual('executable', next(r['role'] for r in report['inputs'] if r['path'].endswith('leaf.py') and r['path'].startswith('src/')))

    def test_cli_preserves_plan_and_never_writes_github_outputs(self):
        self.commit('unknown.dat','bytes')
        plan=self.plan()
        plan_path=self.repo/'plan.json'; output=self.repo/'report.json'; github_output=self.repo/'outputs.txt'
        plan_path.write_bytes(planner.canonical(plan))
        args=['--repo',str(self.repo),'--plan',str(plan_path),'--output',str(output)]
        with patch.dict('os.environ',{'GITHUB_OUTPUT':str(github_output)}), contextlib.redirect_stdout(io.StringIO()):
            with patch.object(sys,'argv',[str(ROOT/'.github/scripts/ci_contract_shadow.py'),*args]):
                with self.assertRaises(SystemExit) as exited:
                    runpy.run_path(str(ROOT/'.github/scripts/ci_contract_shadow.py'),run_name='__main__')
            self.assertEqual(0,exited.exception.code)
        report=json.loads(output.read_bytes())
        self.assertEqual(['unknown.dat'],report['summary']['unknown_inputs'])
        self.assertFalse(github_output.exists())
        self.assertEqual(plan,json.loads(plan_path.read_bytes()))
        with self.assertRaisesRegex(ValueError,'overwrite'):
            shadow.main(['--repo',str(self.repo),'--plan',str(plan_path),'--output',str(plan_path)])

    def test_actual_merge_target_and_integration_are_bound(self):
        head=self.commit('docs/input.md','updated')
        command(self.repo,'checkout','-qb','base-side',self.base)
        base=self.commit('docs/base.md','base')
        command(self.repo,'merge','--no-ff','-m','merge',head)
        target=command(self.repo,'rev-parse','HEAD')
        plan=planner.make_plan(self.repo,base=base,head=head,target=target,repository='Example/repo')
        report=shadow.build_report(self.repo,plan)
        self.assertEqual(target,report['binding']['target'])
        integration=planner.make_plan(self.repo,base=target,head=target,target=target,repository='Example/repo',integration=True)
        report=shadow.build_report(self.repo,integration)
        self.assertFalse(report['execution_authority'])
        self.assertEqual([],report['inputs'])

    def test_smoke_witness_reaches_actual_source_consumer_not_just_a_test_name(self):
        write(self.repo, '.github/scripts/tool.py', 'VALUE=1\n')
        write(self.repo, 'registry/runner.py', 'import runpy\ndef run(path): return runpy.run_path(path)\n')
        write(self.repo, 'src/research_workbench/cli.py', 'RUNNER="registry/runner.py"\n')
        write(self.repo, 'src/research_workbench/validation/check.py', 'from research_workbench import cli\n')
        self.base = self.commit('tests/test_consumer.py', 'from research_workbench.validation import check\n')
        self.commit('.github/scripts/tool.py', 'VALUE=2\n')
        plan = self.plan()
        report = shadow.build_report(self.repo, plan)
        for flag in ('package_smoke', 'repository_smoke'):
            row = report['smoke_review'][flag]
            self.assertTrue(row['required'])
            self.assertTrue(row['affected_consumers'])
            for consumer in row['affected_consumers']:
                self.assertEqual('.github/scripts/tool.py', consumer['chain'][0])
                self.assertEqual(consumer['path'], consumer['chain'][-1])
                self.assertIn('opaque-execution', consumer['edge_kinds'])
                self.assertTrue(consumer['contains_fallback_edge'])
        altered = copy.deepcopy(plan)
        altered['selection']['affected_witnesses'].pop('src/research_workbench/cli.py')
        with self.assertRaisesRegex(ValueError, 'missing its path witness'):
            shadow.smoke_review(altered, json.loads((self.repo/planner.POLICY).read_bytes()))
        unsigned = dict(altered); unsigned.pop('plan_id'); altered['plan_id'] = planner.digest(unsigned)
        with self.assertRaisesRegex(ValueError, 'selection proof mismatch'):
            shadow.build_report(self.repo, altered)

    def test_static_smoke_witness_and_base_group_reasons_stay_distinct(self):
        write(self.repo, 'src/research_workbench/leaf.py', 'VALUE=1\n')
        write(self.repo, 'src/research_workbench/cli.py', 'from research_workbench import leaf\n')
        write(self.repo, 'tests/test_consumer.py', 'from research_workbench import cli\n')
        policy = json.loads((self.repo/planner.POLICY).read_bytes())
        policy['groups']['documentation']['package'] = True
        policy['surfaces']['leaf'] = {'paths': ['src/research_workbench/leaf.py'], 'class': 'focused',
                                      'groups': ['documentation']}
        self.base = self.commit(planner.POLICY, planner.canonical(policy))
        self.commit('src/research_workbench/leaf.py', 'VALUE=2\n')
        report = shadow.build_report(self.repo, self.plan())
        package = report['smoke_review']['package_smoke']
        self.assertEqual(['documentation'], package['accepted_groups'])
        self.assertFalse(package['affected_consumers'][0]['contains_fallback_edge'])
        self.assertEqual(6, len(report['producer_sources']))
        self.assertEqual(5, report['schema_version'])


class ShadowWorkflowTests(unittest.TestCase):
    def test_shadow_job_has_no_execution_outputs_or_aggregate_consumers(self):
        import yaml
        workflow=yaml.safe_load((ROOT/'.github/workflows/ci.yml').read_bytes())
        diagnostic=workflow['jobs']['contract_shadow']
        self.assertNotIn('outputs',diagnostic)
        for name,job in workflow['jobs'].items():
            if name!='contract_shadow':
                self.assertNotIn('contract_shadow',job.get('needs',[]))
        self.assertEqual('test (3.11)',workflow['jobs']['required_test_311']['name'])
        self.assertEqual('test (3.13)',workflow['jobs']['required_test_313']['name'])
