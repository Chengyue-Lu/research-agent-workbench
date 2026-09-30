"""M14-005 cutover preparation must preserve protection and refuse drift."""
import copy
import contextlib
import io
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import release_ruleset_cutover as cutover


REPOSITORY = 'Chengyue-Lu/research-agent-workbench'
SOURCE = 'a' * 40
PARENT = 'b' * 40
IDS = {'develop': {'hard': 11, 'review': 12}, 'main': {'hard': 21, 'review': 22}}


def fixture(branch, layer):
    hard = layer == 'hard'
    method = 'merge' if branch == 'main' else 'squash'
    pr = {'allowed_merge_methods': [method], 'required_review_thread_resolution': True,
          'required_approving_review_count': 0 if hard or branch == 'develop' else 1,
          'require_code_owner_review': not hard,
          'dismiss_stale_reviews_on_push': not hard,
          'require_last_push_approval': not hard and branch == 'main'}
    rules = [{'type': 'deletion'}, {'type': 'non_fast_forward'}] if hard else []
    rules.append({'type': 'pull_request', 'parameters': pr})
    if hard:
        names = cutover.OLD_MAIN if branch == 'main' else cutover.DEVELOP
        rules.append({'type': 'required_status_checks', 'parameters': {
            'strict_required_status_checks_policy': True,
            'do_not_enforce_on_create': False,
            'required_status_checks': cutover.checks(names)}})
    return {'id': IDS[branch][layer], 'source_type': 'Repository',
            'source': REPOSITORY, 'name': f'{branch} {layer}', 'target': 'branch',
            'enforcement': 'active',
            'bypass_actors': [] if hard else cutover.OWNER_BYPASS,
            'conditions': {'ref_name': {'include': [f'refs/heads/{branch}'], 'exclude': []}},
            'rules': rules}


class FakeAPI:
    repository = REPOSITORY

    def __init__(self):
        self.layers = {branch: {layer: fixture(branch, layer) for layer in ('hard', 'review')}
                       for branch in ('develop', 'main')}
        self.calls = []
        self.drift = False

    def get(self, path):
        self.calls.append(path)
        if path == '':
            return {'full_name': REPOSITORY, 'default_branch': 'main'}
        if path.startswith('branches/'):
            branch = path.split('/')[1]
            value = SOURCE if branch == 'develop' else PARENT
            if self.drift and self.calls.count(path) > 1:
                value = 'c' * 40
            return {'protected': True, 'commit': {'sha': value}}
        if path.startswith('rulesets/'):
            identity = int(path.split('/')[1])
            return copy.deepcopy(next(value for layers in self.layers.values()
                                      for value in layers.values() if value['id'] == identity))
        if path.startswith('rules/branches/'):
            branch = path.split('/')[2]
            return [{**copy.deepcopy(rule), 'ruleset_id': value['id'],
                     'ruleset_source': REPOSITORY, 'ruleset_source_type': 'Repository'}
                    for value in self.layers[branch].values() for rule in value['rules']]
        raise AssertionError(path)


class ReleaseRulesetCutoverTests(unittest.TestCase):
    def test_module_entrypoint_exposes_cli_help(self):
        script = ROOT / cutover.TOOL
        output = io.StringIO()
        with (mock.patch.object(sys, 'argv', [str(script), '--help']),
              contextlib.redirect_stdout(output),
              self.assertRaises(SystemExit) as exit_status):
            runpy.run_path(str(script), run_name='__main__')
        self.assertEqual(0, exit_status.exception.code)
        self.assertIn('--main-hard-ruleset', output.getvalue())

    def prepare(self, api=None):
        api = api or FakeAPI()
        with (mock.patch.object(cutover.source_ci, 'active_contract', return_value='legacy-ci-v1'),
              mock.patch.object(cutover.source_ci, 'attest_contract', return_value={
                  'source_ci': 'PASS', 'observation': {'run_attempt': 1}})):
            return cutover.prepare(api, source=SOURCE, parent=PARENT, run_id=123, ids=IDS)

    def test_single_payload_swaps_only_main_checks_after_source_ci_and_four_layer_readback(self):
        api = FakeAPI()
        result = self.prepare(api)
        self.assertEqual(result['before']['rules'][-1]['parameters']['required_status_checks'],
                         cutover.checks(cutover.OLD_MAIN))
        self.assertEqual(result['cutover']['rules'][-1]['parameters']['required_status_checks'],
                         cutover.checks(cutover.NEW_MAIN))
        unchanged = copy.deepcopy(result['cutover'])
        unchanged['rules'][-1]['parameters']['required_status_checks'] = cutover.checks(cutover.OLD_MAIN)
        self.assertEqual(unchanged, result['before'])
        self.assertEqual(result['manifest']['main_hard_payload_sha256'], cutover.digest(result['before']))
        self.assertEqual(result['manifest']['cutover_payload_sha256'], cutover.digest(result['cutover']))
        self.assertFalse(result['manifest']['applied'])
        self.assertFalse(result['manifest']['merge_eligible'])
        self.assertEqual(result['source_ci']['source_ci'], 'PASS')
        self.assertTrue(all(path in api.calls for path in ('rules/branches/main',
                         'rules/branches/develop', 'branches/main', 'branches/develop')))
        self.assertTrue(all(not path.startswith(('PATCH ', 'POST ', 'PUT ')) for path in api.calls))

    def test_mutated_scope_bypass_review_or_old_checks_block(self):
        mutations = [
            lambda a: a.layers['main']['hard'].update(enforcement='disabled'),
            lambda a: a.layers['main']['hard'].update(bypass_actors=cutover.OWNER_BYPASS),
            lambda a: a.layers['main']['hard']['conditions']['ref_name']['include'].append('refs/heads/develop'),
            lambda a: a.layers['main']['hard']['rules'].pop(0),
            lambda a: a.layers['main']['hard']['rules'][-1]['parameters'].update(
                strict_required_status_checks_policy=False),
            lambda a: a.layers['main']['hard']['rules'][-1]['parameters']['required_status_checks'][0].update(
                integration_id=1),
            lambda a: a.layers['main']['review']['rules'][0]['parameters'].update(
                required_approving_review_count=0),
            lambda a: a.layers['develop']['review'].update(bypass_actors=[]),
            lambda a: a.layers['develop']['hard']['rules'][-1]['parameters']['required_status_checks'].pop(),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                api = FakeAPI()
                mutate(api)
                with self.assertRaises(ValueError):
                    self.prepare(api)

    def test_foreign_ruleset_effective_mismatch_and_tip_drift_block(self):
        api = FakeAPI()
        api.layers['main']['hard']['source'] = 'foreign/repo'
        with self.assertRaises(ValueError):
            self.prepare(api)
        api = FakeAPI()
        original_get = api.get
        def changed_effective(path):
            value = original_get(path)
            if path == 'rules/branches/main':
                return value[:-1]
            return value
        api.get = changed_effective
        with self.assertRaises(ValueError):
            self.prepare(api)
        api = FakeAPI()
        api.drift = True
        with self.assertRaises(ValueError):
            self.prepare(api)

    def test_missing_source_ci_or_bad_sha_blocks_before_payload(self):
        api = FakeAPI()
        with self.assertRaises(ValueError):
            cutover.prepare(api, source='short', parent=PARENT, run_id=123, ids=IDS)
        with (mock.patch.object(cutover.source_ci, 'active_contract', return_value='legacy-ci-v1'),
              mock.patch.object(cutover.source_ci, 'attest_contract', side_effect=ValueError('CI failed'))):
            with self.assertRaisesRegex(ValueError, 'CI failed'):
                cutover.prepare(api, source=SOURCE, parent=PARENT, run_id=123, ids=IDS)
        self.assertFalse(any(path.startswith('rulesets/') for path in api.calls))

    def test_ci_attempt_change_during_readback_blocks(self):
        api = FakeAPI()
        with (mock.patch.object(cutover.source_ci, 'active_contract', return_value='legacy-ci-v1'),
              mock.patch.object(cutover.source_ci, 'attest_contract', side_effect=[
                  {'observation': {'run_attempt': 1}},
                  {'observation': {'run_attempt': 2}}])):
            with self.assertRaisesRegex(ValueError, 'source CI changed'):
                cutover.prepare(api, source=SOURCE, parent=PARENT, run_id=123, ids=IDS)

    def test_cli_writes_new_non_authorizing_artifacts_only(self):
        result = self.prepare()
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'plan'
            args = ['--repository', REPOSITORY, '--source', SOURCE, '--parent', PARENT,
                    '--run-id', '123', '--develop-hard-ruleset', '11',
                    '--develop-review-ruleset', '12', '--main-hard-ruleset', '21',
                    '--main-review-ruleset', '22', '--output', str(output)]
            with (mock.patch.object(cutover.source_ci, 'local_source'),
                  mock.patch.object(cutover.source_ci, 'git', return_value=(ROOT / cutover.TOOL).read_bytes()),
                  mock.patch.object(cutover.source_ci, 'GitHub', return_value=FakeAPI()),
                  mock.patch.object(cutover, 'prepare', return_value=result)):
                self.assertEqual(0, cutover.main(args))
                self.assertEqual(result['manifest'], json.loads((output / 'manifest.json').read_text(encoding='utf-8')))
                with self.assertRaises(ValueError):
                    cutover.main(args)


if __name__ == '__main__':
    unittest.main()
