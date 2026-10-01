"""Real Git release governance with controlled, non-authorizing API observations."""
from __future__ import annotations

from contextlib import redirect_stdout
import copy
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from tests.test_pr_governance import valid_body
from tests import test_release_surface as fixtures

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import release_governance as release
sys.path.pop(0)


class API:
    repository = 'Example/workbench'

    def __init__(self, pr):
        self.pr = pr
        self.calls = []

    def get(self, path):
        self.calls.append(path)
        if path != 'pulls/7':
            raise AssertionError(path)
        return copy.deepcopy(self.pr)


class ReleaseGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.ReleaseSurfaceTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.ReleaseSurfaceTests.tearDownClass()

    def setUp(self):
        self.fixture = fixtures.ReleaseSurfaceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.repo
        tasks = ('| ID | 状态 | 任务 | 依赖 | 验收 |\n|---|---|---|---|---|\n'
                 '| M14-005 | READY | Curated release | none | Trusted source release |\n'
                 '| M14-004 | DONE | Public documentation | none | Public closure |\n')
        fixtures.write(self.root, 'docs/TASKS.md', tasks.encode('utf-8'))
        self.workstream = 'docs/workstreams/chengyue-lu/M14-CURATED-RELEASE'
        for name in ('README.md', 'RISK_LEDGER.md'):
            fixtures.write(self.root, f'{self.workstream}/{name}', b'Fixture source evidence\n')
        self.fixture.update_source()
        self.expected = self.fixture.expected
        files = fixtures.release.project(self.root, self.expected)
        self.candidate, _ = self.fixture.candidate(files)
        source, parent = self.expected['source'], self.expected['parent']
        self.digest = fixtures.release.digest(files[fixtures.release.MANIFEST][1])
        body = valid_body(pr_class='release', task_ids='M14-005', risk='R2',
            workstream=self.workstream, shared_contract='yes', authority_impact='yes',
            authority_basis='Issue 57, ADR-0021 and the named M14-005 decision.',
            adversarial_evidence='Source, parent, branch and metadata drift are rejected.')
        self.pr = {'number': 7, 'state': 'open', 'merged': False, 'body': body, 'mergeable': True,
            'base': {'ref': 'main', 'sha': parent, 'repo': {'full_name': API.repository, 'id': 42}},
            'head': {'ref': 'release/v1.0.0', 'sha': self.candidate,
                     'repo': {'full_name': API.repository, 'id': 42}}}
        self.api = API(self.pr)
        self.preflight = {'source': source, 'parent': parent, 'candidate': self.candidate,
            'source_ci': self.expected['source_ci'], 'projection': {'manifest_sha256': self.digest},
            'observation': {'repository_id': 42}, 'merge_eligible': False}
        self.kwargs = dict(number=7, source=source, parent=parent, candidate=self.candidate,
            release_version='1.0.0', manifest_sha256=self.digest, preflight=self.preflight)
        root_patch = patch.object(release.governance, 'ROOT', self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def check(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            return release.check(self.api, **(self.kwargs | kwargs))

    def test_real_git_candidate_uses_live_metadata_and_development_source(self):
        result = self.check()
        self.assertEqual('success', result['governance'])
        self.assertEqual('R2', result['effective_risk'])
        self.assertFalse(result['merge_eligible'])
        self.assertEqual(['pulls/7'], self.api.calls)
        candidate_paths = fixtures.command(self.root, 'ls-tree', '-r', '--name-only', self.candidate)
        self.assertNotIn(b'docs/TASKS.md', candidate_paths)
        self.assertNotIn(b'docs/workstreams/', candidate_paths)
        release.reobserve(self.api, result, release_version='1.0.0', repository_id=42)

    def test_direct_develop_fork_bad_version_parent_or_closed_pr_fail(self):
        mutations = [
            lambda p: p['head'].update(ref='develop'),
            lambda p: p['head'].update(ref='release/v01.0.0'),
            lambda p: p['head']['repo'].update(full_name='Fork/workbench'),
            lambda p: p['head']['repo'].update(id=43),
            lambda p: p['base'].update(sha='a' * 40),
            lambda p: p['head'].update(sha='b' * 40),
            lambda p: p.update(number=8),
            lambda p: p.update(state='closed'),
            lambda p: p.update(merged=True),
            lambda p: p.update(mergeable=False),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.api.pr = copy.deepcopy(self.pr)
                mutate(self.api.pr)
                with self.assertRaises(ValueError):
                    self.check()

    def test_underdeclared_risk_is_upgraded_without_losing_r2_requirements(self):
        self.api.pr['body'] = self.pr['body'].replace('R2', 'R0')
        self.assertEqual('R2', self.check()['effective_risk'])
        self.api.pr['body'] = self.api.pr['body'].replace('Issue 57, ADR-0021 and the named M14-005 decision.', 'none')
        with self.assertRaisesRegex(ValueError, 'governance rejected'):
            self.check()

    def test_unknown_task_or_missing_authority_metadata_fail(self):
        for before, after in [('M14-005', 'M14-999'),
                              ('Issue 57, ADR-0021 and the named M14-005 decision.', 'none'),
                              (self.workstream, 'none')]:
            with self.subTest(before=before):
                self.api.pr = copy.deepcopy(self.pr)
                self.api.pr['body'] = self.pr['body'].replace(before, after)
                with self.assertRaisesRegex(ValueError, 'governance rejected'):
                    self.check()

    def test_dormant_policy_and_mismatched_fresh_preflight_fail(self):
        with patch.object(release.governance, 'CURATED_RELEASE_TOPOLOGY',
                          {**release.governance.CURATED_RELEASE_TOPOLOGY, 'activation_state': 'dormant'}):
            with self.assertRaisesRegex(ValueError, 'dormant'):
                self.check()
        for key, value in [('source', 'c' * 40), ('parent', 'd' * 40),
                           ('candidate', 'e' * 40), ('manifest_sha256', '0' * 64)]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'binding mismatch'):
                self.check(**{key: value})

    def test_other_known_task_cannot_replace_release_activation_task(self):
        self.api.pr['body'] = self.pr['body'].replace('M14-005', 'M14-004')
        with self.assertRaisesRegex(ValueError, 'declare activation Task'):
            self.check()

    def test_body_or_ref_changes_after_build_invalidate_receipt(self):
        receipt = self.check()
        for mutate in [lambda p: p.update(body=p['body'] + '\nchanged'),
                       lambda p: p['head'].update(sha='f' * 40),
                       lambda p: p.update(state='closed')]:
            with self.subTest(mutation=mutate):
                self.api.pr = copy.deepcopy(self.pr)
                mutate(self.api.pr)
                with self.assertRaises(ValueError):
                    release.reobserve(self.api, receipt, release_version='1.0.0', repository_id=42)

    def test_unrelated_repository_counters_do_not_change_governance_inputs(self):
        receipt = self.check()
        self.api.pr['head']['repo'].update(updated_at='later', size=999)
        release.reobserve(self.api, receipt, release_version='1.0.0', repository_id=42)


if __name__ == '__main__':
    unittest.main()
