"""Failures and identity boundaries for the fixed component aggregate."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import ci_component_result as aggregate


class ComponentResultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = dict(profile='component', head_sha='a'*40, base_sha='b'*40,
                         plan_sha256='c'*64, python_versions=['3.11'], smoke=False,
                         components=['docs'], selected_tests=['test_documentation'], unknown_paths=[])
        self.context = dict(repository='Example/repo', event='pull_request', ref='refs/pull/5/merge',
                            run_id=501, run_attempt=1, workflow_path='.github/workflows/ci_components.yml')
        self.native = dict(kind='component_ci_result', schema_version='0.1.0', python='3.11',
                           head_sha='a'*40, plan_sha256='c'*64, profile='component',
                           behavior=dict(success=True, errors=0, failures=0, tests_run=1, skipped=0,
                                         elapsed_seconds=0.1, records=[dict(id='test_a.A.test_b', outcome='passed')]))
        self.write(self.native)

    def write(self, value):
        path = self.root / ('component-result-' + value['python']) / 'result.json'
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')

    def summary(self, **statuses):
        return aggregate.summarize(self.plan, self.root, dict(plan='success', execute='success', **statuses), self.context)

    def test_documentation_success_does_not_claim_product_smoke(self):
        value = self.summary()
        self.assertEqual('components-v1', value['contract_version'])
        self.assertIsNone(value['results'][0]['smoke_seconds'])
        self.assertFalse(value['merge_eligible'])

    def test_missing_skipped_cancelled_failed_jobs_never_pass(self):
        for producer in ('plan', 'execute'):
            for state in (None, 'skipped', 'cancelled', 'failure', 'timed_out'):
                statuses = dict(plan='success', execute='success'); statuses[producer] = state
                with self.subTest(producer=producer, state=state), self.assertRaises(ValueError):
                    aggregate.summarize(self.plan, self.root, statuses, self.context)

    def test_foreign_receipt_empty_result_failed_subtest_or_missing_smoke_blocks(self):
        cases = [('python', '3.13'), ('head_sha', 'b'*40), ('plan_sha256', 'd'*64),
                 ('profile', 'release-checkpoint'), ('schema_version', 'unknown')]
        for key, value in cases:
            native = copy.deepcopy(self.native); native[key] = value
            # Keep the expected filename to exercise contents, not just absence.
            path = self.root/'component-result-3.11/result.json'
            path.write_text(json.dumps(native), encoding='utf-8')
            with self.subTest(key=key), self.assertRaises(ValueError): self.summary()
        for change in ({'success': False}, {'errors': 1}, {'records': []},
                       {'records': [{'outcome': 'passed', 'checkpoints': [{'outcome': 'failed'}]}]}):
            native = copy.deepcopy(self.native); native['behavior'].update(change); self.write(native)
            with self.subTest(change=change), self.assertRaises(ValueError): self.summary()
        self.write(self.native); self.plan['smoke'] = True
        with self.assertRaises(FileNotFoundError): self.summary()

    def test_release_needs_both_versions_smoke_governance_and_canonical_context(self):
        self.plan.update(profile='release-checkpoint', python_versions=['3.11', '3.13'], smoke=True)
        self.context.update(event='workflow_dispatch', ref='refs/heads/develop',
                            workflow_path=aggregate.CHECKPOINT_WORKFLOW)
        for version in self.plan['python_versions']:
            self.write({**self.native, 'python': version, 'profile': 'release-checkpoint'})
            (self.root/f'component-result-{version}/smoke.json').write_text(json.dumps(dict(
                status='success', steps=[{'status': 'success'}]*8, elapsed_seconds=2)), encoding='utf-8')
        self.assertEqual(2, len(self.summary(governance='success')['results']))
        for state in ('skipped', 'failure', 'cancelled'):
            with self.subTest(state=state), self.assertRaises(ValueError): self.summary(governance=state)
        for key, wrong in [('event', 'schedule'), ('ref', 'refs/heads/main'),
                           ('workflow_path', '.github/workflows/ci_components.yml')]:
            original = self.context[key]; self.context[key] = wrong
            with self.subTest(key=key), self.assertRaises(ValueError): self.summary(governance='success')
            self.context[key] = original
