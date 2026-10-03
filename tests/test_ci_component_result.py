"""Failures and identity boundaries for the fixed component aggregate."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import ci_component_result as aggregate
import run_component_ci as runner


class ComponentResultTests(unittest.TestCase):
    def shard_fixture(self):
        plan = dict(self.plan, selected_tests=['test_a', 'test_b', 'test_c', 'test_d'])
        root = self.root/'shards'
        root.mkdir()
        inventory = [f'test_{owner}.Case.test_{method}' for owner in 'abcd' for method in 'xy']
        for producer in runner.execution_matrix(plan):
            assigned = runner.shard_inventory(inventory, producer['shard_index'], producer['shard_count'])
            value = dict(self.native, schema_version='0.2.0', selections=runner.execution_names(plan, '3.11'),
                         shard_index=producer['shard_index'], shard_count=producer['shard_count'],
                         behavior=dict(success=True, errors=0, failures=0, tests_run=len(assigned), skipped=0,
                             elapsed_seconds=1.0, records=[dict(id=identity, outcome='passed') for identity in assigned],
                             inventory=inventory, inventory_sha256=hashlib.sha256(runner.canonical(inventory)).hexdigest()))
            directory = root/producer['artifact_name']
            directory.mkdir()
            (directory/'result.json').write_text(json.dumps(value), encoding='utf-8')
        return plan, root

    def test_sharded_success_requires_the_entire_inventory_exactly_once(self):
        plan, root = self.shard_fixture()
        value = aggregate.summarize(plan, root, dict(plan='success', execute='success'), self.context)
        self.assertEqual((8, 4), (value['results'][0]['tests_run'], value['results'][0]['shards']))
        self.assertEqual(1, value['results'][0]['max_shard_test_seconds'])
        self.assertEqual('components-v1', value['contract_version'])
        self.assertFalse(value['merge_eligible'])

    def test_missing_repeated_foreign_or_legacy_receipts_cannot_replace_a_shard(self):
        plan, root = self.shard_fixture()
        path = root/'component-result-3.11-shard-0/result.json'
        original = json.loads(path.read_bytes())
        mutations = [
            lambda v: v.update(shard_index=1),
            lambda v: v.update(shard_index=False),
            lambda v: v.update(shard_count=3),
            lambda v: v.update(schema_version='0.1.0'),
            lambda v: v.update(head_sha='d'*40),
            lambda v: v.update(plan_sha256='d'*64),
            lambda v: v.update(selections=['test_a']),
            lambda v: v['behavior'].update(records=[], tests_run=0),
            lambda v: v['behavior']['records'].append(copy.deepcopy(v['behavior']['records'][0])),
            lambda v: v['behavior']['records'][0].update(id='test_b.Case.test_x'),
            lambda v: v['behavior'].update(inventory_sha256='0'*64),
            lambda v: v['behavior'].update(success=False),
            lambda v: v['behavior']['records'][0].update(checkpoints=[{'outcome':'failed'}]),
        ]
        for index, mutation in enumerate(mutations):
            value = copy.deepcopy(original)
            mutation(value)
            path.write_text(json.dumps(value), encoding='utf-8')
            with self.subTest(index=index), self.assertRaises(ValueError):
                aggregate.summarize(plan, root, dict(plan='success', execute='success'), self.context)
        path.write_text(json.dumps(original), encoding='utf-8')
        path.rename(path.with_name('missing.json'))
        with self.assertRaises(FileNotFoundError):
            aggregate.summarize(plan, root, dict(plan='success', execute='success'), self.context)
        path.with_name('missing.json').rename(path)
        directory = root/'component-result-3.11-shard-0'
        foreign = root/'component-result-3.11-shard-copy'
        directory.rename(foreign)
        with self.assertRaisesRegex(ValueError, 'producers'):
            aggregate.summarize(plan, root, dict(plan='success', execute='success'), self.context)
        foreign.rename(directory)
        for state in ('failure', 'cancelled', 'skipped', 'timed_out'):
            with self.subTest(state=state), self.assertRaises(ValueError):
                aggregate.summarize(plan, root, dict(plan='success', execute=state), self.context)

    def test_inventory_changes_even_with_new_digest_and_matching_local_counts_are_rejected(self):
        plan, root = self.shard_fixture()
        path = root/'component-result-3.11-shard-3/result.json'
        value = json.loads(path.read_bytes())
        value['behavior']['inventory'].append('test_z.Case.test_extra')
        value['behavior']['inventory_sha256'] = hashlib.sha256(runner.canonical(value['behavior']['inventory'])).hexdigest()
        path.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'inventories'):
            aggregate.summarize(plan, root, dict(plan='success', execute='success'), self.context)

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
