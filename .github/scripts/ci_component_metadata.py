"""Bind PR metadata to its component plan without granting execution success."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import zipfile
import time

from release_source_ci import GitHub, positive, require, sha
from run_component_ci import canonical, git, make_plan, save

WORKFLOW = '.github/workflows/ci_components.yml'
MAX_BYTES = 2_000_000


class PlanNotReady(ValueError):
    """The matching run has not published its plan; no result is inferred."""


def identity(pr):
    return (positive(pr['number']), pr['base']['repo']['full_name'], pr['base']['ref'],
            sha(pr['base']['sha']), pr['head']['repo']['full_name'], sha(pr['head']['sha']))


def read_plan(api, run):
    artifacts = api.pages(f'actions/runs/{positive(run["id"])}/artifacts', 'artifacts')
    matches = [a for a in artifacts if a['name'] == 'component-plan' and not a['expired']]
    if not matches and not any(a['name'] == 'component-plan' for a in artifacts):
        raise PlanNotReady('current component plan is missing or ambiguous')
    require(len(matches) == 1, 'current component plan is missing or ambiguous')
    artifact = matches[0]
    require(artifact['workflow_run']['id'] == run['id'], 'foreign plan artifact')
    require(0 < artifact['size_in_bytes'] <= MAX_BYTES, 'component plan archive is too large')
    raw = api.download(positive(artifact['id']))
    require(len(raw) == artifact['size_in_bytes']
            and 'sha256:' + hashlib.sha256(raw).hexdigest() == artifact['digest'],
            'component plan artifact digest/size differs from API')
    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        require(bundle.namelist() == ['plan.json'], 'unexpected component plan archive members')
        require(bundle.getinfo('plan.json').file_size <= MAX_BYTES, 'component plan is too large')
        value = json.loads(bundle.read('plan.json'))
    return value, positive(artifact['id'])


def bind_plan(api, pr, plan, *, wait_seconds=0):
    require(type(wait_seconds) in (int, float) and math.isfinite(wait_seconds)
            and 0 <= wait_seconds <= 180, 'invalid component plan wait budget')
    expected_identity = identity(pr)
    number, repository, base_ref, base, head_repository, head = expected_identity
    require(repository == api.repository and base_ref == 'develop', 'component metadata requires develop PR')
    require(plan['profile'] == 'component' and plan['base_sha'] == base, 'wrong component metadata plan')
    workflow = api.get('actions/workflows/ci_components.yml')
    # GitHub may retain the display name from the workflow's first registration.
    # Its canonical path and numeric identity bind the current content runs.
    require(workflow['path'] == WORKFLOW, 'unexpected component workflow')
    workflow_id = positive(workflow['id'])
    runs = api.get(f'actions/workflows/ci_components.yml/runs?head_sha={head}&event=pull_request&per_page=30')['workflow_runs']
    matches = []
    for run in runs:
        if (run.get('workflow_id') != workflow_id or run.get('path') != WORKFLOW
                or run.get('event') != 'pull_request' or run.get('head_sha') != head
                or run.get('repository', {}).get('full_name') != repository
                or run.get('head_repository', {}).get('full_name') != head_repository):
            continue
        linked = [p for p in run.get('pull_requests', []) if p.get('number') == number
                  and p.get('base', {}).get('ref') == 'develop'
                  and p.get('base', {}).get('sha') == base and p.get('head', {}).get('sha') == head]
        if len(linked) == 1:
            matches.append(run)
    require(matches, 'no component content run for the current PR base/head')
    run = dict(max(matches, key=lambda row: positive(row['id'])))
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            observed, artifact_id = read_plan(api, run)
            break
        except PlanNotReady:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise
            fresh = api.get(f'actions/runs/{run["id"]}')
            require(fresh['id'] == run['id'] and fresh['run_attempt'] == run['run_attempt']
                    and fresh['head_sha'] == head and fresh['path'] == WORKFLOW,
                    'component run changed during plan wait')
            require(identity(api.get(f'pulls/{number}')) == expected_identity,
                    'PR base/head changed during plan wait')
            require(fresh['status'] in ('queued', 'in_progress'), 'component plan producer stopped without a plan')
            time.sleep(min(5, remaining))
    require(canonical(observed) == canonical(plan), 'component plan differs from current Git inputs')
    fresh = api.get(f'actions/runs/{run["id"]}')
    require(fresh['id'] == run['id'] and fresh['run_attempt'] == run['run_attempt']
            and fresh['head_sha'] == head and fresh['path'] == WORKFLOW, 'component run changed during observation')
    require(identity(api.get(f'pulls/{number}')) == expected_identity, 'PR base/head changed during metadata validation')
    # Failed/cancelled execution does not erase an authentic plan. CI result remains
    # the separate required execution gate; this record cannot replace it.
    return dict(schema_version=1, kind='component_metadata_binding', authority='plan-reference-only',
                repository=repository, pr=number, base_sha=base, head_sha=head,
                target_sha=plan['head_sha'], plan_sha256=plan['plan_sha256'],
                content_run=run['id'], run_attempt=positive(run['run_attempt']), artifact_id=artifact_id,
                content_status=fresh['status'], content_conclusion=fresh['conclusion'],
                execution_success_asserted=False)


def check_metadata(repo, event, api, *, wait_seconds=0):
    pr = event['pull_request']
    expected = identity(pr)
    require(event['repository']['full_name'] == api.repository == expected[1], 'foreign metadata repository')
    require(identity(api.get(f'pulls/{expected[0]}')) == expected, 'stale metadata event')
    target = git(repo, 'rev-parse', 'HEAD').decode().strip()
    parents = git(repo, 'show', '-s', '--format=%P', target).decode().split()
    require(parents == [expected[3], expected[5]], 'metadata checkout is not the current PR test merge')
    return bind_plan(api, pr, make_plan(repo, expected[3], target, 'component'), wait_seconds=wait_seconds)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event', type=Path, default=os.environ.get('GITHUB_EVENT_PATH'))
    parser.add_argument('--output', required=True)
    parser.add_argument('--wait-seconds', type=int, default=0)
    args = parser.parse_args(argv)
    require(os.environ.get('GITHUB_EVENT_NAME') == 'pull_request', 'metadata requires pull_request event')
    event = json.loads(args.event.read_bytes())
    api = GitHub(os.environ['GITHUB_REPOSITORY'])
    value = check_metadata(Path.cwd(), event, api, wait_seconds=args.wait_seconds)
    save(args.output, value)
    print(json.dumps(value, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
