"""Live source-CI v2: only the dedicated release checkpoint can qualify."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import zipfile

from ci_component_result import CONTRACT, CHECKPOINT_WORKFLOW, CHECKPOINT_JOBS, CHECKPOINT_REQUIRED
import release_source_ci as legacy

TOOL = '.github/scripts/release_checkpoint_ci.py'
require = legacy.require


def binding(run, api, identity, workflow_id, source, run_id):
    require(run['id'] == run_id and run['workflow_id'] == workflow_id
            and run['path'] == CHECKPOINT_WORKFLOW and run['name'] == 'CI checkpoint',
            'checkpoint workflow identity mismatch')
    for key in ('repository', 'head_repository'):
        legacy.same_repository(run[key], api.repository, identity)
    require(run['event'] == 'workflow_dispatch' and run['head_branch'] == 'develop'
            and run['head_sha'] == source, 'exact develop checkpoint dispatch required')
    require(run['status'] == 'completed' and run['conclusion'] == 'success', 'checkpoint is not successful')
    return legacy.positive(run['run_attempt']), legacy.positive(run['check_suite_id'])


def validate_result(value, *, repository, source, run_id, attempt):
    require(value.get('schema_version') == 1 and value.get('contract_version') == CONTRACT
            and value.get('profile') == 'release-checkpoint', 'unsupported checkpoint result version/profile')
    require(value.get('head_sha') == value.get('base_sha') == source
            and value.get('conclusion') == 'success' and value.get('coverage') == 'diagnostic-only'
            and value.get('merge_eligible') is False, 'invalid checkpoint result')
    require(value.get('context') == dict(repository=repository, event='workflow_dispatch',
            ref='refs/heads/develop', run_id=run_id, run_attempt=attempt,
            workflow_path=CHECKPOINT_WORKFLOW), 'foreign checkpoint result context')
    require(value.get('producers') == dict(plan='success', execute='success', governance='success'),
            'incomplete checkpoint producers')
    results = value.get('results', [])
    require([r.get('python') for r in results] == ['3.11', '3.13'], 'both checkpoint versions required')
    require(all(r.get('conclusion') == 'success' and type(r.get('tests_run')) is int
                and r['tests_run'] > 0 and isinstance(r.get('smoke_seconds'), (int, float))
                for r in results), 'checkpoint tests or installed smoke missing')
    require(isinstance(value.get('selected_tests'), list) and value['selected_tests'], 'empty checkpoint')
    require(isinstance(value.get('plan_sha256'), str)
            and re.fullmatch('[0-9a-f]{64}', value['plan_sha256']), 'invalid checkpoint plan digest')


def attest(api, source, run_id):
    legacy.sha(source)
    legacy.positive(run_id)
    identity = legacy.repository_id(api)
    workflow = api.get('actions/workflows/ci_checkpoint.yml')
    require(workflow['path'] == CHECKPOINT_WORKFLOW and workflow['name'] == 'CI checkpoint'
            and workflow['state'] == 'active', 'active canonical checkpoint required')
    workflow_id = legacy.positive(workflow['id'])
    run = api.get(f'actions/runs/{run_id}')
    attempt, suite = binding(run, api, identity, workflow_id, source, run_id)
    jobs = api.pages(f'actions/runs/{run_id}/attempts/{attempt}/jobs', 'jobs')
    observed = {}
    for name in CHECKPOINT_JOBS:
        matches = [j for j in jobs if j['name'] == name]
        require(len(matches) == 1, 'missing or ambiguous checkpoint job: ' + name)
        job = matches[0]
        require(job['run_id'] == run_id and job['run_attempt'] == attempt and job['head_sha'] == source
                and job['head_branch'] == 'develop' and job['workflow_name'] == 'CI checkpoint'
                and job['status'] == 'completed' and job['conclusion'] == 'success', 'failed/foreign checkpoint job')
        prefix = f'https://api.github.com/repos/{api.repository}/check-runs/'
        url = job['check_run_url']
        require(isinstance(url, str) and url.startswith(prefix)
                and re.fullmatch('[1-9][0-9]*', url[len(prefix):]), 'foreign checkpoint check URL')
        check_id = int(url[len(prefix):])
        check = api.get(f'check-runs/{check_id}')
        require(check['id'] == check_id and check['name'] == name and check['head_sha'] == source
                and check['check_suite']['id'] == suite and check['app']['id'] == legacy.APP_ID
                and check['app']['slug'] == 'github-actions' and check['status'] == 'completed'
                and check['conclusion'] == 'success', 'untrusted checkpoint check')
        observed[name] = dict(job_id=legacy.positive(job['id']), check_run_id=check_id)
    artifacts = api.pages(f'actions/runs/{run_id}/artifacts', 'artifacts')
    matches = [a for a in artifacts if a['name'] == 'checkpoint-result']
    require(len(matches) == 1 and matches[0].get('expired') is False, 'checkpoint result artifact missing/ambiguous')
    artifact = matches[0]
    artifact_id = legacy.positive(artifact['id'])
    raw = api.download(artifact_id)
    digest = hashlib.sha256(raw).hexdigest()
    require(len(raw) == artifact['size_in_bytes'] and artifact['digest'] == 'sha256:' + digest,
            'checkpoint artifact digest mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        require(bundle.namelist() == ['ci-result.json'] and bundle.infolist()[0].file_size <= 2_000_000,
                'unexpected checkpoint artifact files')
        value = json.loads(bundle.read('ci-result.json'))
    validate_result(value, repository=api.repository, source=source, run_id=run_id, attempt=attempt)
    final = api.get(f'actions/runs/{run_id}')
    require(binding(final, api, identity, workflow_id, source, run_id) == (attempt, suite),
            'checkpoint attempt changed during observation')
    return dict(source_ci=dict(schema_version=2, contract_version=CONTRACT, profile='release-checkpoint',
                repository=api.repository, sha=source, workflow='CI checkpoint', workflow_path=CHECKPOINT_WORKFLOW,
                workflow_id=workflow_id, event='workflow_dispatch', ref='refs/heads/develop',
                run_id=run_id, run_attempt=attempt, result_artifact_id=artifact_id,
                result_artifact_sha256=digest, conclusion='success', required_checks=CHECKPOINT_REQUIRED.copy()),
                observation=dict(repository_id=identity, workflow_id=workflow_id, run_attempt=attempt,
                                 check_suite_id=suite, jobs=observed), merge_eligible=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Produce source governance in a real checkpoint context')
    parser.add_argument('--source', required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    require(os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
            and os.environ.get('GITHUB_REF') == 'refs/heads/develop'
            and os.environ.get('GITHUB_SHA') == args.source
            and os.environ.get('GITHUB_REPOSITORY') == args.repository
            and os.environ.get('GITHUB_WORKFLOW_REF') ==
            f'{args.repository}/{CHECKPOINT_WORKFLOW}@refs/heads/develop', 'exact checkpoint context required')
    result = legacy.merged_governance(legacy.ROOT, legacy.GitHub(args.repository), args.source)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
