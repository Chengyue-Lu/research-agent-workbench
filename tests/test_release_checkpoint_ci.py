"""Versioned release-source boundaries with API rows and real Git projections."""
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import release_checkpoint_ci as checkpoint
import release_source_ci as legacy
import release_surface as surface
import release_preflight as preflight
import check_pr_governance as governance
from tests import test_release_source_ci as old
from tests import test_release_surface as surface_fixture


def result():
    return dict(schema_version=1, contract_version='components-v1', profile='release-checkpoint',
                head_sha=old.SHA, base_sha=old.SHA, plan_sha256='a'*64, coverage='diagnostic-only',
                conclusion='success', merge_eligible=False, selected_tests=['test_one'],
                producers=dict(plan='success', execute='success', governance='success'),
                context=dict(repository=old.REPO, event='workflow_dispatch', ref='refs/heads/develop',
                             run_id=old.RUN, run_attempt=old.ATTEMPT, workflow_path=checkpoint.CHECKPOINT_WORKFLOW),
                results=[dict(python=p, tests_run=3, smoke_seconds=1, conclusion='success') for p in ('3.11', '3.13')])


def fixture(value=None):
    rows = old.fixture()
    workflow = rows.pop('actions/workflows/ci.yml')
    workflow.update(path=checkpoint.CHECKPOINT_WORKFLOW, name='CI checkpoint')
    rows['actions/workflows/ci_checkpoint.yml'] = workflow
    run = rows[f'actions/runs/{old.RUN}']
    run.update(path=checkpoint.CHECKPOINT_WORKFLOW, name='CI checkpoint', event='workflow_dispatch')
    endpoint = f'actions/runs/{old.RUN}/attempts/{old.ATTEMPT}/jobs?per_page=100&page=1'
    jobs = rows[endpoint]['jobs'][:len(checkpoint.CHECKPOINT_JOBS)]
    for job, name in zip(jobs, checkpoint.CHECKPOINT_JOBS):
        job.update(name=name, workflow_name='CI checkpoint')
        rows['check-runs/' + job['check_run_url'].rsplit('/', 1)[1]]['name'] = name
    rows[endpoint] = dict(total_count=len(jobs), jobs=jobs)
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as bundle:
        bundle.writestr('ci-result.json', json.dumps(result() if value is None else value))
    raw = data.getvalue()
    artifact = dict(id=900, name='checkpoint-result', expired=False, size_in_bytes=len(raw),
                    digest='sha256:' + hashlib.sha256(raw).hexdigest())
    rows[f'actions/runs/{old.RUN}/artifacts?per_page=100&page=1'] = dict(total_count=1, artifacts=[artifact])
    api = old.API(rows)
    api.download = lambda artifact_id: raw
    return api


class CheckpointSourceTests(unittest.TestCase):
    def test_live_version_two_and_legacy_remain_distinct(self):
        value = checkpoint.attest(fixture(), old.SHA, old.RUN)
        self.assertEqual(2, value['source_ci']['schema_version'])
        self.assertEqual('release-checkpoint', value['source_ci']['profile'])
        self.assertFalse(value['merge_eligible'])
        old_value = legacy.attest_contract(old.API(old.fixture()), old.SHA, old.RUN, 'legacy-ci-v1')
        self.assertEqual({'repository', 'sha', 'workflow', 'run_id', 'conclusion', 'required_checks'},
                         set(old_value['source_ci']))
        with self.assertRaises(ValueError): legacy.attest_contract(fixture(), old.SHA, old.RUN, 'future')

    def test_ordinary_nightly_candidate_and_unknown_profiles_cannot_qualify(self):
        for profile in ('component', 'integration-smoke', 'checkpoint', 'nightly-baseline', None, 'future'):
            value = result(); value['profile'] = profile
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                checkpoint.attest(fixture(value), old.SHA, old.RUN)
        for key, wrong in [('schema_version', 2), ('schema_version', True), ('schema_version', 1.0),
                           ('contract_version', 'legacy-ci-v1'),
                           ('head_sha', 'b'*40), ('base_sha', 'b'*40), ('producers', {}), ('results', [])]:
            value = result(); value[key] = wrong
            with self.subTest(key=key), self.assertRaises(ValueError): checkpoint.attest(fixture(value), old.SHA, old.RUN)

    def test_wrong_event_workflow_job_app_attempt_and_missing_or_corrupt_artifact_rejected(self):
        run_path = f'actions/runs/{old.RUN}'
        jobs_path = f'{run_path}/attempts/{old.ATTEMPT}/jobs?per_page=100&page=1'
        artifact_path = f'{run_path}/artifacts?per_page=100&page=1'
        changes = [(run_path, 'event', 'push'), (run_path, 'head_branch', 'main'),
                   (run_path, 'path', '.github/workflows/ci_components.yml'),
                   (run_path, 'conclusion', 'failure')]
        for path, key, wrong in changes:
            api = fixture(); api.responses[path][key] = wrong
            with self.subTest(key=key), self.assertRaises(ValueError): checkpoint.attest(api, old.SHA, old.RUN)
        for state in ('skipped', 'failure', 'cancelled', 'timed_out', None):
            api = fixture(); api.responses[jobs_path]['jobs'][1]['conclusion'] = state
            with self.subTest(state=state), self.assertRaises(ValueError): checkpoint.attest(api, old.SHA, old.RUN)
        api = fixture(); first = api.responses[jobs_path]['jobs'][0]
        api.responses['check-runs/' + first['check_run_url'].rsplit('/', 1)[1]]['app']['id'] = 7
        with self.assertRaisesRegex(ValueError, 'untrusted'): checkpoint.attest(api, old.SHA, old.RUN)
        api = fixture(); api.responses[artifact_path] = dict(total_count=0, artifacts=[])
        with self.assertRaisesRegex(ValueError, 'artifact'): checkpoint.attest(api, old.SHA, old.RUN)
        api = fixture(); api.responses[artifact_path]['artifacts'][0]['digest'] = 'sha256:' + 'f'*64
        with self.assertRaisesRegex(ValueError, 'digest'): checkpoint.attest(api, old.SHA, old.RUN)
        api = fixture(); api.final_run = {**api.responses[run_path], 'run_attempt': old.ATTEMPT + 1}
        with self.assertRaisesRegex(ValueError, 'attempt changed'): checkpoint.attest(api, old.SHA, old.RUN)
        value = result(); value['context']['run_attempt'] += 1
        with self.assertRaisesRegex(ValueError, 'context'): checkpoint.attest(fixture(value), old.SHA, old.RUN)

    def test_checkpoint_governance_uses_real_squash_delta_and_its_real_event(self):
        harness = old.MergedSourceTests()
        harness.setUp(); self.addCleanup(harness.doCleanups)
        target = harness.root/'checkpoint.json'
        env = dict(GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REF='refs/heads/develop',
                   GITHUB_SHA=harness.head, GITHUB_REPOSITORY=old.REPO,
                   GITHUB_WORKFLOW_REF=f'{old.REPO}/{checkpoint.CHECKPOINT_WORKFLOW}@refs/heads/develop')
        args = ['--repository', old.REPO, '--source', harness.head, '--output', str(target)]
        with patch.dict(os.environ, env), patch.object(legacy, 'ROOT', harness.root), \
             patch.object(legacy, 'GitHub', return_value=old.API(harness.rows)), \
             patch.dict(legacy.check_pull_request.__globals__, {'ROOT': harness.root}):
            self.assertEqual(0, checkpoint.main(args))
        self.assertEqual(harness.base, json.loads(target.read_text())['parent'])
        target.unlink()
        for name, wrong in [('GITHUB_EVENT_NAME', 'push'), ('GITHUB_REF', 'refs/heads/main'),
                            ('GITHUB_SHA', 'b'*40), ('GITHUB_WORKFLOW_REF', 'candidate')]:
            with self.subTest(name=name), patch.dict(os.environ, {**env, name: wrong}), self.assertRaises(ValueError):
                checkpoint.main(args)
            self.assertFalse(target.exists())

    def test_versioned_governance_policy_keeps_dormant_topology(self):
        policy = deepcopy(governance.CURATED_RELEASE_TOPOLOGY)
        policy.update(schema_version=2, source_ci_workflow='CI checkpoint',
                      source_ci_required_checks=checkpoint.CHECKPOINT_REQUIRED)
        report = governance.GovernanceReport()
        self.assertTrue(governance.validate_curated_release_policy(policy, report))
        governance.validate_topology(base_ref='main', head_ref='release/v1.0.0',
            base_repository=old.REPO, head_repository=old.REPO, pr_class='release',
            report=report, release_policy=policy)
        self.assertTrue(report.has_errors)
        policy['activation_state'] = 'active'
        self.assertFalse(governance.validate_curated_release_policy(policy, governance.GovernanceReport()))


class ManifestVersionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): surface_fixture.ReleaseSurfaceTests.setUpClass()

    @classmethod
    def tearDownClass(cls): surface_fixture.ReleaseSurfaceTests.tearDownClass()

    def test_both_manifest_versions_project_and_new_shape_cannot_downgrade(self):
        harness = surface_fixture.ReleaseSurfaceTests()
        harness.setUp(); self.addCleanup(harness.doCleanups)
        for path in preflight.TRUSTED_FILES:
            surface_fixture.write(harness.repo, path, (ROOT/path).read_bytes())
        harness.update_source()
        expected = deepcopy(harness.expected)
        old_manifest = json.loads(surface.project(harness.repo, expected)[surface.MANIFEST][1])
        self.assertEqual('0.1.0', old_manifest['schema_version'])
        receipt = checkpoint.attest(fixture(), old.SHA, old.RUN)['source_ci']
        receipt.update(repository=expected['repository'], sha=expected['source'])
        expected['source_ci'] = receipt
        manifest = json.loads(surface.project(harness.repo, expected)[surface.MANIFEST][1])
        self.assertEqual('0.2.0', manifest['schema_version'])
        for mutation in (dict(schema_version=1), dict(profile='component'), dict(workflow='CI')):
            wrong = deepcopy(expected); wrong['source_ci'].update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(surface.ReleaseError): surface.expectations(harness.repo, wrong)
        wrong = deepcopy(expected); del wrong['source_ci']['schema_version']
        with self.assertRaises(surface.ReleaseError): surface.expectations(harness.repo, wrong)
        # Current source-owned policy still selects v1; a candidate cannot choose v2.
        self.assertEqual('legacy-ci-v1', legacy.active_contract(harness.repo, expected['source']))
        with patch.object(legacy, 'attest') as v1, patch.object(checkpoint, 'attest') as v2:
            legacy.attest_contract(None, expected['source'], 10, legacy.active_contract(harness.repo, expected['source']))
            v1.assert_called_once(); v2.assert_not_called()

    def test_preflight_uses_source_owned_v2_and_rejects_mixed_activation(self):
        harness = surface_fixture.ReleaseSurfaceTests()
        harness.setUp(); self.addCleanup(harness.doCleanups)
        for path in preflight.TRUSTED_FILES:
            surface_fixture.write(harness.repo, path, (ROOT/path).read_bytes())
        surface_fixture.write(harness.repo, legacy.CONTRACT_POLICY,
            b'{"schema_version":1,"active_contract":"components-v1"}\n')
        harness.update_source()
        with self.assertRaisesRegex(ValueError, 'versions differ'):
            legacy.active_contract(harness.repo, harness.expected['source'])
        policy = json.loads((ROOT/'.github/governance-policy.json').read_text())
        policy['curated_release_topology'].update(schema_version=2, source_ci_workflow='CI checkpoint',
            source_ci_required_checks=checkpoint.CHECKPOINT_REQUIRED)
        surface_fixture.write(harness.repo, '.github/governance-policy.json', json.dumps(policy).encode())
        harness.update_source()
        expected = deepcopy(harness.expected)
        observed = checkpoint.attest(fixture(), old.SHA, old.RUN)
        observed['source_ci'].update(repository=expected['repository'], sha=expected['source'])
        expected['source_ci'] = observed['source_ci']
        files = surface.project(harness.repo, expected)
        candidate, tree = harness.candidate(files)
        rows = {f'branches/{name}': dict(name=name, protected=True, commit={'sha': sha}) for name, sha in
                [('main', expected['parent']), ('develop', expected['source'])]}
        class API:
            repository = expected['repository']
            def get(self, path): return deepcopy(rows[path])
        with patch.object(preflight, 'ROOT', harness.repo), \
             patch.object(checkpoint, 'attest', return_value=observed) as v2, \
             patch.object(legacy, 'attest', side_effect=AssertionError('v1 downgrade')):
            value = preflight.check(harness.repo, API(), source=expected['source'], parent=expected['parent'],
                policy_version='1.0.0', release_version='1.0.0', run_id=old.RUN, candidate=candidate,
                manifest_sha256=surface.digest(files[surface.MANIFEST][1]))
        self.assertEqual(tree, value['projection']['tree'])
        self.assertEqual(2, v2.call_count)
        self.assertEqual('components-v1', value['source_ci']['contract_version'])
        self.assertFalse(value['merge_eligible'])
