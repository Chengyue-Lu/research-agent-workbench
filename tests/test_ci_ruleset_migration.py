"""Required-check migration changes no unrelated hard protection."""
import copy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.github/scripts'))
import ci_ruleset_migration as migration


class RulesetMigrationTests(unittest.TestCase):
    def fixture(self):
        return dict(name='develop hard gates',target='branch',enforcement='active',bypass_actors=[],
            conditions={'ref_name':{'include':['refs/heads/develop'],'exclude':[]}},
            rules=[{'type':'deletion'},{'type':'non_fast_forward'},
                   {'type':'pull_request','parameters':{'allowed_merge_methods':['squash'],'required_review_thread_resolution':True}},
                   {'type':'required_status_checks','parameters':{'strict_required_status_checks_policy':True,
                    'do_not_enforce_on_create':False,'required_status_checks':[
                        {'context':name,'integration_id':15368} for name in migration.OLD]}}])

    def test_payloads_preserve_all_protections_and_original_snapshot(self):
        original=self.fixture();before=copy.deepcopy(original)
        results=migration.payloads(original)
        self.assertEqual(original,before)
        self.assertEqual(results['rollback'],before)
        for name, expected in [('intersection',migration.OLD+['CI result']),('components',migration.NEW)]:
            value=results[name]
            checks=value['rules'][-1]['parameters'].pop('required_status_checks')
            comparison=copy.deepcopy(before);comparison['rules'][-1]['parameters'].pop('required_status_checks')
            self.assertEqual(value,comparison)
            self.assertEqual(checks,[{'context':item,'integration_id':15368} for item in expected])

    def test_unexpected_scope_bypass_and_weakened_or_changed_gates_are_rejected(self):
        cases=[lambda x:x.update(enforcement='disabled'),lambda x:x.update(bypass_actors=[{'actor_id':1}]),
               lambda x:x['conditions']['ref_name']['include'].append('refs/heads/main'),
               lambda x:x['rules'].pop(0),
               lambda x:x['rules'][-1]['parameters'].update(strict_required_status_checks_policy=False),
               lambda x:x['rules'][-1]['parameters']['required_status_checks'][0].update(integration_id=1),
               lambda x:x['rules'][-1]['parameters']['required_status_checks'].append({'context':'unexpected','integration_id':15368})]
        for i, mutate in enumerate(cases):
            with self.subTest(case=i):
                value=self.fixture();mutate(value)
                with self.assertRaises(ValueError):migration.payloads(value)
