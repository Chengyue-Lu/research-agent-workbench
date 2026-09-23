from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import os
import runpy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import release_source_ci as source
from tests.test_pr_governance import valid_body

REPO = 'Example/repo'
SHA = 'a' * 40
RUN = 501
ATTEMPT = 2


class API(source.GitHub):
    def __init__(self, responses):
        super().__init__(REPO)
        self.responses = deepcopy(responses)
        self.calls = []
        self.final_run = None

    def get(self, path):
        repeated_run = path == f'actions/runs/{RUN}' and path in self.calls
        self.calls.append(path)
        if repeated_run and self.final_run is not None:
            return deepcopy(self.final_run)
        return deepcopy(self.responses[path])


def fixture():
    repository = {'id': 73, 'full_name': REPO}
    run = {'id': RUN, 'workflow_id': 81, 'path': source.WORKFLOW, 'name': 'CI',
           'repository': repository, 'head_repository': repository, 'event': 'push',
           'head_branch': 'develop', 'head_sha': SHA, 'status': 'completed', 'conclusion': 'success',
           'run_attempt': ATTEMPT, 'check_suite_id': 71}
    result = {'': repository,
              'actions/workflows/ci.yml': {'id': 81, 'path': source.WORKFLOW, 'name': 'CI', 'state': 'active'},
              f'actions/runs/{RUN}': run,
              'branches/develop': {'name': 'develop', 'protected': True, 'commit': {'sha': SHA}}}
    jobs = []
    for index, name in enumerate(source.SOURCE_JOBS, 101):
        jobs.append({'id': index, 'run_id': RUN, 'run_attempt': ATTEMPT, 'head_sha': SHA,
                     'head_branch': 'develop', 'workflow_name': 'CI', 'name': name,
                     'status': 'completed', 'conclusion': 'success',
                     'check_run_url': f'https://api.github.com/repos/{REPO}/check-runs/{index}'})
        result[f'check-runs/{index}'] = {'id': index, 'name': name, 'head_sha': SHA,
            'check_suite': {'id': 71}, 'app': {'id': 15368, 'slug': 'github-actions'},
            'status': 'completed', 'conclusion': 'success'}
    result[f'actions/runs/{RUN}/attempts/{ATTEMPT}/jobs?per_page=100&page=1'] = {'total_count': len(jobs), 'jobs': jobs}
    return result


JOBS = f'actions/runs/{RUN}/attempts/{ATTEMPT}/jobs?per_page=100&page=1'


class AttestationTests(unittest.TestCase):
    def test_exact_push_attempt_and_app_bound_checks_produce_existing_source_ci_shape(self):
        api = API(fixture())
        result = source.attest(api, SHA, RUN)
        self.assertEqual({'repository': REPO, 'sha': SHA, 'workflow': 'CI', 'run_id': RUN,
                          'conclusion': 'success', 'required_checks': ['governance', 'test (3.11)', 'test (3.13)']}, result['source_ci'])
        self.assertEqual(ATTEMPT, result['observation']['run_attempt'])
        self.assertEqual(set(source.SOURCE_JOBS), set(result['observation']['jobs']))
        self.assertFalse(result['merge_eligible'])
        self.assertEqual(2, api.calls.count(f'actions/runs/{RUN}'))

    def test_wrong_repository_workflow_event_sha_or_incomplete_run_is_rejected(self):
        cases = [('', 'full_name', 'Foreign/repo'), ('', 'id', 0)]
        cases += [('actions/workflows/ci.yml', key, value) for key, value in
                  [('path', 'other.yml'), ('name', 'CI governance'), ('state', 'disabled_manually'), ('id', False)]]
        cases += [(f'actions/runs/{RUN}', key, value) for key, value in
                  [('id', 77), ('workflow_id', 77), ('path', 'other.yml'), ('name', 'CI governance'),
                   ('event', 'pull_request'), ('event', 'workflow_dispatch'), ('head_branch', 'main'),
                   ('head_sha', 'b' * 40), ('status', 'in_progress'), ('conclusion', 'failure'),
                   ('run_attempt', 0), ('check_suite_id', False),
                   ('repository', {'id': 74, 'full_name': REPO}),
                   ('head_repository', {'id': 73, 'full_name': 'Foreign/repo'})]]
        for path, key, value in cases:
            with self.subTest(path=path, key=key, value=value), self.assertRaises(ValueError):
                rows = fixture(); rows[path][key] = value
                source.attest(API(rows), SHA, RUN)

    def test_missing_duplicate_foreign_skipped_or_failed_jobs_cannot_attest(self):
        for name in source.SOURCE_JOBS:
            with self.subTest(missing=name), self.assertRaises(ValueError):
                rows = fixture(); rows[JOBS]['jobs'] = [j for j in rows[JOBS]['jobs'] if j['name'] != name]
                rows[JOBS]['total_count'] -= 1
                source.attest(API(rows), SHA, RUN)
        rows = fixture(); rows[JOBS]['jobs'].append(deepcopy(rows[JOBS]['jobs'][0])); rows[JOBS]['total_count'] += 1
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            source.attest(API(rows), SHA, RUN)
        for key, value in [('id', False), ('run_id', 502), ('run_attempt', 1), ('head_sha', 'b' * 40),
                           ('head_branch', 'main'), ('workflow_name', 'Other'), ('status', 'queued'),
                           ('conclusion', 'skipped'), ('conclusion', 'cancelled'), ('conclusion', 'failure'),
                           ('check_run_url', 'https://evil.invalid/check-runs/101'),
                           ('check_run_url', f'https://api.github.com/repos/{REPO}/check-runs/../101'),
                           ('check_run_url', f'https://api.github.com/repos/{REPO}/check-runs/0'),
                           ('check_run_url', None)]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                rows = fixture(); rows[JOBS]['jobs'][0][key] = value
                source.attest(API(rows), SHA, RUN)

    def test_check_names_alone_or_other_apps_suites_and_sources_are_not_evidence(self):
        for key, value in [('id', 1), ('name', 'Unrelated'), ('head_sha', 'b' * 40),
                           ('check_suite', {'id': 99}), ('app', {'id': 1, 'slug': 'github-actions'}),
                           ('app', {'id': 15368, 'slug': 'other-app'}),
                           ('status', 'in_progress'), ('conclusion', 'neutral')]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                rows = fixture(); rows['check-runs/101'][key] = value
                source.attest(API(rows), SHA, RUN)

    def test_rerun_races_and_final_state_drift_fail_closed(self):
        for key, value in [('run_attempt', 3), ('check_suite_id', 99), ('status', 'queued'), ('conclusion', 'cancelled')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                api = API(fixture()); api.final_run = deepcopy(api.responses[f'actions/runs/{RUN}'])
                api.final_run[key] = value
                source.attest(api, SHA, RUN)

    def test_invalid_input_identity_is_rejected_before_api_read(self):
        for value in ['', 'A' * 40, 'a' * 39, None, []]:
            with self.subTest(sha=value), self.assertRaises(ValueError):
                source.attest(API({}), value, RUN)
        for value in [0, -1, True, None, '501']:
            with self.subTest(run_id=value), self.assertRaises(ValueError):
                source.attest(API({}), SHA, value)


class TransportTests(unittest.TestCase):
    def test_transport_is_fixed_host_get_and_does_not_embed_credentials(self):
        with patch.object(source.subprocess, 'check_output', return_value='{"id":73}') as call:
            self.assertEqual({'id': 73}, source.GitHub(REPO).get('actions/runs/501'))
        args = call.call_args.args[0]
        self.assertEqual(['gh', 'api', '--hostname', 'github.com', '--method', 'GET'], args[:6])
        self.assertEqual('repos/Example/repo/actions/runs/501', args[-1])
        self.assertNotIn('Authorization', ' '.join(args))
        with patch.object(source.subprocess, 'check_output', return_value='{"id":73}') as call:
            source.GitHub(REPO).get('')
        self.assertEqual('repos/Example/repo', call.call_args.args[0][-1])
        for value in ['../repo', 'Example/..', 'Example/repo/extra', 'https://host/repo', '', None]:
            with self.subTest(repository=value), self.assertRaises(ValueError):
                source.GitHub(value)

    def test_pagination_completes_and_rejects_gaps_count_drift_and_unbounded_lists(self):
        api = API({'items?per_page=100&page=1': {'total_count': 101, 'jobs': list(range(100))},
                   'items?per_page=100&page=2': {'total_count': 101, 'jobs': [100]}})
        self.assertEqual(list(range(101)), api.pages('items', 'jobs'))
        api = API({'items?per_page=100&page=1': list(range(100)), 'items?per_page=100&page=2': [100]})
        self.assertEqual(list(range(101)), api.pages('items'))
        for response in [{'total_count': 2, 'jobs': [1]}, {'total_count': True, 'jobs': []},
                         {'total_count': 0, 'jobs': {}}, {'total_count': -1, 'jobs': []}]:
            with self.subTest(response=response), self.assertRaises(ValueError):
                API({'items?per_page=100&page=1': response}).pages('items', 'jobs')
        api = API({'items?per_page=100&page=1': {'total_count': 101, 'jobs': list(range(100))},
                   'items?per_page=100&page=2': {'total_count': 102, 'jobs': [100, 101]}})
        with self.assertRaisesRegex(ValueError, 'changed'):
            api.pages('items', 'jobs')
        with patch.object(source.GitHub, 'get', return_value=list(range(100))):
            with self.assertRaisesRegex(ValueError, 'limit'):
                source.GitHub(REPO).pages('items')


class MergedSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.command('init', '-q')
        self.command('config', 'user.name', 'Source CI fixture')
        self.command('config', 'user.email', 'fixture@example.invalid')
        self.command('config', 'core.autocrlf', 'false')
        self.command('remote', 'add', 'origin', f'https://github.com/{REPO}.git')
        tool = self.root / source.TOOL; tool.parent.mkdir(parents=True)
        tool.write_bytes((ROOT / source.TOOL).read_bytes())
        (self.root / 'docs').mkdir(); (self.root / 'docs/TASKS.md').write_text('# Tasks\n')
        (self.root / 'README.md').write_text('before\n')
        self.command('add', '.'); self.command('commit', '-qm', 'base')
        self.base = self.command('rev-parse', 'HEAD')
        (self.root / 'README.md').write_text('after\n')
        self.command('add', '.'); self.command('commit', '-qm', 'squash')
        self.head = self.command('rev-parse', 'HEAD'); tree = self.command('rev-parse', 'HEAD^{tree}')
        self.reviewed = self.command('commit-tree', tree, '-p', self.base, '-m', 'reviewed feature')
        repo = {'full_name': REPO, 'id': 73}
        self.pr = {'number': 17, 'state': 'closed', 'merged': True, 'merged_at': '2026-09-15T00:00:00Z',
                   'merge_commit_sha': self.head, 'body': valid_body(),
                   'base': {'repo': repo, 'ref': 'develop', 'sha': self.base},
                   'head': {'repo': repo, 'ref': 'feature/test', 'sha': self.reviewed}}
        self.rows = {'': repo, f'commits/{self.head}/pulls?per_page=100&page=1': [self.pr],
                     'pulls/17': self.pr, f'git/commits/{self.reviewed}': {'sha': self.reviewed, 'tree': {'sha': tree}}}

    def command(self, *args):
        return source.git(self.root, *args).decode().strip()

    def replay(self, rows=None):
        with patch.dict(source.check_pull_request.__globals__, {'ROOT': self.root}), redirect_stdout(io.StringIO()):
            return source.merged_governance(self.root, API(self.rows if rows is None else rows), self.head)

    def test_real_squash_delta_is_checked_with_actual_parent_and_authenticated_metadata(self):
        result = self.replay()
        self.assertEqual(self.base, result['parent'])
        self.assertEqual(self.reviewed, result['reviewed_head'])
        self.assertEqual('success', result['governance'])
        self.assertFalse(result['merge_eligible'])

    def test_versioned_transport_preserves_the_required_merge_identity(self):
        # GitHub 2026-03-10 removes merge_commit_sha from both PR endpoints.
        # Exercise the real transport plus producer, rather than bypassing the
        # request header in the in-memory API fixture.
        real_output = subprocess.check_output
        requests = []

        def respond(args, **kwargs):
            if args[0] != 'gh':
                return real_output(args, **kwargs)
            requests.append(args)
            header = args[args.index('-H') + 1]
            self.assertIn(header, ['X-GitHub-Api-Version: 2022-11-28',
                                   'X-GitHub-Api-Version: 2026-03-10'])
            path = args[-1].removeprefix(f'repos/{REPO}').lstrip('/')
            response = deepcopy(self.rows[path])
            if header.endswith('2026-03-10'):
                for item in response if isinstance(response, list) else [response]:
                    item.pop('merge_commit_sha', None)
            return json.dumps(response)

        with patch.object(source.subprocess, 'check_output', side_effect=respond), \
             patch.dict(source.check_pull_request.__globals__, {'ROOT': self.root}), redirect_stdout(io.StringIO()):
            result = source.merged_governance(self.root, source.GitHub(REPO), self.head)
        self.assertEqual('success', result['governance'])
        self.assertEqual(self.head, result['source'])
        self.assertTrue(any(args[-1] == f'repos/{REPO}/pulls/17' for args in requests))

    def test_unassociated_ambiguous_unmerged_foreign_or_tree_drifted_source_is_rejected(self):
        endpoint = f'commits/{self.head}/pulls?per_page=100&page=1'
        for prs in [[], [self.pr, self.pr], [{**self.pr, 'merge_commit_sha': 'b' * 40}],
                    [{key: value for key, value in self.pr.items() if key != 'merge_commit_sha'}],
                    [{**self.pr, 'merged_at': None}], [{**self.pr, 'number': False}]]:
            with self.subTest(prs=prs), self.assertRaises(ValueError):
                rows = deepcopy(self.rows); rows[endpoint] = prs; self.replay(rows)
        for key, value in [('number', 18), ('state', 'open'), ('merged', False), ('merged_at', None),
                           ('merge_commit_sha', 'b' * 40), ('body', 'invalid metadata')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                rows = deepcopy(self.rows); rows['pulls/17'] = {**rows['pulls/17'], key: value}; self.replay(rows)
        for ref, key, value in [('base', 'ref', 'main'), ('base', 'sha', 'b' * 40),
                                ('head', 'repo', {'full_name': 'Foreign/repo', 'id': 73}),
                                ('base', 'repo', {'full_name': REPO, 'id': 74}), ('head', 'sha', 'bad')]:
            with self.subTest(ref=ref, key=key), self.assertRaises(ValueError):
                rows = deepcopy(self.rows); rows['pulls/17'][ref][key] = value; self.replay(rows)
        for key, value in [('sha', 'b' * 40), ('tree', {'sha': 'b' * 40})]:
            with self.subTest(commit=key), self.assertRaises(ValueError):
                rows = deepcopy(self.rows); rows[f'git/commits/{self.reviewed}'][key] = value; self.replay(rows)
        with patch.object(source, 'git', side_effect=lambda root, *args: b'a b\n' if args[:2] == ('show', '-s')
                          else subprocess.check_output(['git', *args], cwd=root)):
            with self.assertRaisesRegex(ValueError, 'one parent'):
                self.replay()

    def test_dirty_wrong_source_remote_shallow_or_observer_drift_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'exact source'):
            source.local_source(self.root, REPO, self.base)
        (self.root / 'untracked.txt').write_text('dirty')
        with self.assertRaisesRegex(ValueError, 'clean'):
            source.local_source(self.root, REPO, self.head)
        (self.root / 'untracked.txt').unlink()
        self.command('remote', 'set-url', 'origin', 'https://github.com/Foreign/repo')
        with self.assertRaisesRegex(ValueError, 'origin'):
            source.local_source(self.root, REPO, self.head)
        self.command('remote', 'set-url', 'origin', f'git@github.com:{REPO}.git')
        source.local_source(self.root, REPO, self.head)
        real = source.git
        with patch.object(source, 'git', side_effect=lambda root, *args: b'true' if args == ('rev-parse', '--is-shallow-repository') else real(root, *args)):
            with self.assertRaisesRegex(ValueError, 'complete source history'):
                source.local_source(self.root, REPO, self.head)
        with patch.object(source, 'git', side_effect=lambda root, *args: b'changed' if args[0] == 'show' else real(root, *args)):
            with self.assertRaisesRegex(ValueError, 'observer byte drift'):
                source.local_source(self.root, REPO, self.head)


class EntrypointTests(unittest.TestCase):
    def test_script_entrypoint_help_requires_no_remote_access(self):
        with patch.object(sys, 'argv', [str(ROOT / source.TOOL), '--help']), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as exited:
                runpy.run_path(str(ROOT / source.TOOL), run_name='__main__')
        self.assertEqual(0, exited.exception.code)

    def test_cli_publishes_live_observation_exclusively_and_rejects_stale_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'proof.json'
            args = ['attest', '--repository', REPO, '--source', SHA, '--run-id', str(RUN), '--output', str(output)]
            api = API(fixture())
            with patch.object(source, 'GitHub', return_value=api), patch.object(source, 'local_source'), \
                 patch.object(source, 'git', return_value=SHA.encode()), redirect_stdout(io.StringIO()):
                self.assertEqual(0, source.main(args))
                self.assertEqual(ATTEMPT, json.loads(output.read_text())['observation']['run_attempt'])
                with self.assertRaisesRegex(ValueError, 'output already exists'):
                    source.main(args)
                output.unlink()
                api.responses['branches/develop']['protected'] = False
                with self.assertRaisesRegex(ValueError, 'protected'):
                    source.main(args)
                api.responses['branches/develop']['protected'] = True
                api.responses['branches/develop']['commit']['sha'] = 'b' * 40
                with self.assertRaisesRegex(ValueError, 'fetch current'):
                    source.main(args)
                self.assertFalse(output.exists())

    def test_producer_only_runs_for_exact_develop_push_and_never_writes_failed_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'proof.json'
            args = ['governance', '--repository', REPO, '--source', SHA, '--output', str(output)]
            env = {'GITHUB_EVENT_NAME': 'push', 'GITHUB_REF': 'refs/heads/develop',
                   'GITHUB_SHA': SHA, 'GITHUB_REPOSITORY': REPO}
            with patch.dict(os.environ, env), patch.object(source, 'merged_governance', return_value={'governance': 'success'}), redirect_stdout(io.StringIO()):
                self.assertEqual(0, source.main(args))
            output.unlink()
            for key, value in [('GITHUB_EVENT_NAME', 'pull_request'), ('GITHUB_REF', 'refs/heads/main'),
                               ('GITHUB_SHA', 'b' * 40), ('GITHUB_REPOSITORY', 'Foreign/repo')]:
                with self.subTest(key=key), patch.dict(os.environ, {**env, key: value}), self.assertRaises(ValueError):
                    source.main(args)
                self.assertFalse(output.exists())
            with patch.dict(os.environ, env), patch.object(source, 'merged_governance', side_effect=ValueError('blocked')):
                with self.assertRaisesRegex(ValueError, 'blocked'):
                    source.main(args)
            self.assertFalse(output.exists())

    def test_workflow_preserves_pr_gate_identity_and_runs_real_source_governance(self):
        workflow = yaml.load((ROOT / source.WORKFLOW).read_bytes(), Loader=yaml.BaseLoader)
        job = workflow['jobs']['source_governance']
        self.assertEqual("github.event_name == 'push' && github.ref == 'refs/heads/develop'", job['if'])
        self.assertIn("&& 'governance' || 'source governance (inactive)'", job['name'])
        self.assertIn("github.event_name == 'push' && github.ref == 'refs/heads/develop'", job['name'])
        self.assertEqual('${{ github.sha }}', job['steps'][0]['with']['ref'])
        commands = '\n'.join(step.get('run', '') for step in job['steps'])
        self.assertIn('release_source_ci.py governance', commands)
        self.assertNotIn('check_pr_governance.py', commands)  # non-PR CLI is a no-op
        self.assertEqual('read', workflow['permissions']['pull-requests'])
        self.assertEqual('read', workflow['permissions']['contents'])
        self.assertNotIn('pull_request_target', workflow['on'])
        self.assertEqual('error', job['steps'][-1]['with']['if-no-files-found'])
