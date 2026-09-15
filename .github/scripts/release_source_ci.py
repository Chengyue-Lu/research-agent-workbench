"""Produce merged-source governance and observe authentic develop CI evidence.

Run this from an accepted source checkout. Neither candidate manifests nor saved
JSON receipts grant trust: attest reads GitHub again on every invocation.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from check_pr_governance import check_pull_request

ROOT = Path(__file__).resolve().parents[2]
TOOL = '.github/scripts/release_source_ci.py'
WORKFLOW = '.github/workflows/ci.yml'
REQUIRED = ['governance', 'test (3.11)', 'test (3.13)']
SOURCE_JOBS = REQUIRED + ['plan', 'documentation', 'repository_smoke',
                         'compatibility (3.11)', 'compatibility (3.13)',
                         'coverage-quality (3.11)', 'package-smoke (3.11)', 'package-smoke (3.13)']
APP_ID = 15368


def require(condition, message):
    if not condition:
        raise ValueError(message)


def positive(value):
    require(type(value) is int and value > 0, 'positive integer identity required')
    return value


def sha(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{40}', value), 'exact lowercase SHA required')
    return value


class GitHub:
    """Read-only, fixed-host transport; never follow URLs supplied by a response."""

    def __init__(self, repository):
        require(isinstance(repository, str) and re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]*/[A-Za-z0-9_-][A-Za-z0-9_.-]*', repository),
                'exact GitHub owner/repository required')
        self.repository = repository

    def get(self, path):
        response = subprocess.check_output([
            'gh', 'api', '--hostname', 'github.com', '--method', 'GET',
            '-H', 'X-GitHub-Api-Version: 2026-03-10', f'repos/{self.repository}' + (f'/{path}' if path else ''),
        ], text=True, encoding='utf-8')
        return json.loads(response)

    def pages(self, path, key=None):
        rows = []
        expected_count = None
        for page in range(1, 101):
            response = self.get(f'{path}?per_page=100&page={page}')
            batch = response[key] if key else response
            require(isinstance(batch, list), 'invalid paginated response')
            if key:
                count = response['total_count']
                require(type(count) is int and count >= 0, 'invalid pagination count')
                require(expected_count is None or count == expected_count, 'pagination changed during observation')
                expected_count = count
            rows.extend(batch)
            if len(batch) < 100:
                require(expected_count is None or len(rows) == expected_count, 'incomplete paginated response')
                return rows
        raise ValueError('pagination limit exceeded; evidence incomplete')


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root,
                                   env={**os.environ, 'GIT_NO_REPLACE_OBJECTS': '1'})


def local_source(root, repository, source):
    sha(source)
    require(git(root, 'rev-parse', 'HEAD').decode().strip() == source, 'checkout must be exact source')
    require(git(root, 'rev-parse', '--is-shallow-repository').strip() == b'false', 'complete source history required')
    require(not git(root, 'status', '--porcelain', '--untracked-files=all'), 'source checkout must be clean')
    remote = git(root, 'remote', 'get-url', 'origin').decode().strip()
    require(remote in (f'https://github.com/{repository}', f'https://github.com/{repository}.git',
                       f'git@github.com:{repository}.git'), 'source origin mismatch')
    require(git(root, 'show', f'{source}:{TOOL}') == (root / TOOL).read_bytes(), 'source observer byte drift')


def repository_id(api):
    identity = api.get('')
    require(identity['full_name'] == api.repository, 'repository identity mismatch')
    return positive(identity['id'])


def same_repository(value, repository, identity):
    require(value['full_name'] == repository and value['id'] == identity, 'foreign repository identity')


def merged_governance(root, api, source):
    """Recheck the actual squash delta, using metadata from its merged PR."""
    local_source(root, api.repository, source)
    identity = repository_id(api)
    associated = api.pages(f'commits/{source}/pulls')
    candidates = [pr for pr in associated if pr.get('merge_commit_sha') == source
                  and pr.get('merged_at') and pr.get('base', {}).get('ref') == 'develop']
    require(len(candidates) == 1, 'one exact merged develop PR required')
    number = positive(candidates[0]['number'])
    pr = api.get(f'pulls/{number}')
    require(pr['number'] == number and pr['state'] == 'closed' and pr['merged'] is True
            and pr['merged_at'] and pr['merge_commit_sha'] == source, 'merged PR binding mismatch')
    for ref in ('base', 'head'):
        same_repository(pr[ref]['repo'], api.repository, identity)
    require(pr['base']['ref'] == 'develop', 'source PR must target develop')
    parent = git(root, 'show', '-s', '--format=%P', source).decode().split()
    require(len(parent) == 1, 'develop source must be a squash commit with one parent')
    sha(parent[0])
    require(pr['base']['sha'] == parent[0], 'merged PR base differs from actual source parent')
    reviewed_head = sha(pr['head']['sha'])
    reviewed_commit = api.get(f'git/commits/{reviewed_head}')
    require(reviewed_commit['sha'] == reviewed_head and reviewed_commit['tree']['sha'] ==
            git(root, 'rev-parse', f'{source}^{{tree}}').decode().strip(), 'reviewed tree differs from integrated source')
    event = {'pull_request': {'body': pr['body'], 'base': {**pr['base'], 'sha': parent[0]},
                             'head': {**pr['head'], 'sha': source}}}
    report = check_pull_request(event)
    report.emit()
    require(not report.has_errors, 'merged source governance rejected')
    return {'repository': api.repository, 'source': source, 'parent': parent[0],
            'pull_request': number, 'reviewed_head': reviewed_head, 'governance': 'success',
            'metadata_observation': 'current merged PR body', 'merge_eligible': False}


def run_binding(run, api, identity, workflow_id, source, run_id):
    require(run['id'] == run_id and run['workflow_id'] == workflow_id and run['path'] == WORKFLOW
            and run['name'] == 'CI', 'CI workflow identity mismatch')
    for key in ('repository', 'head_repository'):
        same_repository(run[key], api.repository, identity)
    require(run['event'] == 'push' and run['head_branch'] == 'develop' and run['head_sha'] == source,
            'CI must be an exact develop push, not a PR or dispatch run')
    require(run['status'] == 'completed' and run['conclusion'] == 'success', 'successful completed CI required')
    return positive(run['run_attempt']), positive(run['check_suite_id'])


def attest(api, source, run_id):
    """Live producer/consumer binding; returned data is evidence, not a token."""
    sha(source)
    positive(run_id)
    identity = repository_id(api)
    workflow = api.get('actions/workflows/ci.yml')
    require(workflow['path'] == WORKFLOW and workflow['name'] == 'CI' and workflow['state'] == 'active',
            'active canonical CI workflow required')
    workflow_id = positive(workflow['id'])
    run = api.get(f'actions/runs/{run_id}')
    attempt, suite_id = run_binding(run, api, identity, workflow_id, source, run_id)
    jobs = api.pages(f'actions/runs/{run_id}/attempts/{attempt}/jobs', 'jobs')
    observed = {}
    for name in SOURCE_JOBS:
        matching = [job for job in jobs if job['name'] == name]
        require(len(matching) == 1, 'missing or ambiguous source job: ' + name)
        job = matching[0]
        job_id = positive(job['id'])
        require(job['run_id'] == run_id and job['run_attempt'] == attempt and job['head_sha'] == source
                and job['head_branch'] == 'develop' and job['workflow_name'] == 'CI', 'foreign job binding: ' + name)
        require(job['status'] == 'completed' and job['conclusion'] == 'success', 'unsuccessful source job: ' + name)
        prefix = f'https://api.github.com/repos/{api.repository}/check-runs/'
        url = job['check_run_url']
        require(isinstance(url, str) and url.startswith(prefix) and re.fullmatch('[1-9][0-9]*', url[len(prefix):]),
                'unexpected check-run URL')
        check_id = int(url[len(prefix):])
        check = api.get(f'check-runs/{check_id}')
        require(check['id'] == check_id and check['name'] == name and check['head_sha'] == source
                and check['check_suite']['id'] == suite_id, 'foreign check-run binding: ' + name)
        require(check['app']['id'] == APP_ID and check['app']['slug'] == 'github-actions', 'untrusted check App')
        require(check['status'] == 'completed' and check['conclusion'] == 'success', 'unsuccessful check: ' + name)
        observed[name] = {'job_id': job_id, 'check_run_id': check_id}
    # A rerun while collecting jobs/checks invalidates the entire observation.
    final = api.get(f'actions/runs/{run_id}')
    require(run_binding(final, api, identity, workflow_id, source, run_id) == (attempt, suite_id),
            'CI attempt changed during observation')
    return {'source_ci': {'repository': api.repository, 'sha': source, 'workflow': 'CI', 'run_id': run_id,
                          'conclusion': 'success', 'required_checks': REQUIRED.copy()},
            'observation': {'repository_id': identity, 'workflow_id': workflow_id, 'run_attempt': attempt,
                            'check_suite_id': suite_id, 'jobs': observed}, 'merge_eligible': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('governance', 'attest'))
    parser.add_argument('--repository', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--run-id', type=int)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    require(not args.output.exists(), 'output already exists')
    api = GitHub(args.repository)
    if args.operation == 'governance':
        require(os.environ.get('GITHUB_EVENT_NAME') == 'push' and os.environ.get('GITHUB_REF') == 'refs/heads/develop'
                and os.environ.get('GITHUB_SHA') == args.source and os.environ.get('GITHUB_REPOSITORY') == args.repository,
                'source governance requires the exact develop push context')
        result = merged_governance(ROOT, api, args.source)
    else:
        local_source(ROOT, api.repository, args.source)
        branch = api.get('branches/develop')
        require(branch['name'] == 'develop' and branch['protected'] is True, 'protected develop required')
        tip = sha(branch['commit']['sha'])
        require(git(ROOT, 'rev-parse', 'refs/remotes/origin/develop').decode().strip() == tip,
                'fetch current develop before attesting')
        git(ROOT, 'merge-base', '--is-ancestor', args.source, tip)
        result = attest(api, args.source, args.run_id)
    # Publication is last and exclusive; failures never create a success receipt.
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'operation': args.operation, 'source': args.source, 'result': 'PASS', 'merge_eligible': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
