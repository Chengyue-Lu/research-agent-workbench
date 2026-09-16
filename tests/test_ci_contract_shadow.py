"""P1 input roles and consumer evidence never replace the accepted execution plan."""
from __future__ import annotations

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
        self.assertEqual(5, len(report['producer_sources']))
        self.assertEqual(2, report['schema_version'])


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
