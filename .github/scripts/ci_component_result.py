"""Join actual component producers into a small, versioned CI result."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from run_component_ci import load_plan, save

CONTRACT = 'components-v1'
CHECKPOINT_WORKFLOW = '.github/workflows/ci_checkpoint.yml'
CHECKPOINT_JOBS = ['checkpoint-plan', 'checkpoint (3.11)', 'checkpoint (3.13)',
                   'checkpoint-governance', 'CI checkpoint result']
CHECKPOINT_REQUIRED = ['checkpoint-governance', 'CI checkpoint result']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def summarize(plan, directory, statuses, context):
    """A job's skip is not evidence that a planned producer was unnecessary."""
    require(statuses.get('plan') == statuses.get('execute') == 'success',
            'plan or execution producer did not succeed: ' + str(statuses))
    release = plan['profile'] == 'release-checkpoint'
    if release:
        require(statuses.get('governance') == 'success', 'checkpoint governance did not succeed')
        require(context['event'] == 'workflow_dispatch' and context['ref'] == 'refs/heads/develop'
                and context['workflow_path'] == CHECKPOINT_WORKFLOW, 'invalid release checkpoint context')
    elif 'governance' in statuses:
        require(statuses['governance'] == 'skipped', 'unexpected governance producer')
    results = []
    for version in plan['python_versions']:
        root = Path(directory) / ('component-result-' + version)
        value = json.loads((root / 'result.json').read_text(encoding='utf-8'))
        require(value.get('kind') == 'component_ci_result' and value.get('schema_version') == '0.1.0'
                and value.get('python') == version and value.get('head_sha') == plan['head_sha']
                and value.get('profile') == plan['profile']
                and value.get('plan_sha256') == plan['plan_sha256'], 'foreign or missing native result')
        behavior = value['behavior']
        require(behavior['success'] is True and behavior['errors'] == behavior['failures'] == 0,
                'native tests failed')
        require(behavior['tests_run'] == len(behavior['records']), 'incomplete native test results')
        require(all(row['outcome'] in ('passed', 'passed_with_skips', 'skipped', 'expected_failure')
                    for row in behavior['records']), 'failed native test outcome')
        require(all(point['outcome'] in ('passed', 'skipped') for row in behavior['records']
                    for point in row.get('checkpoints', [])), 'failed native subtest')
        smoke_seconds = None
        if plan['smoke']:
            smoke = json.loads((root / 'smoke.json').read_text(encoding='utf-8'))
            require(smoke['status'] == 'success' and len(smoke['steps']) == 8
                    and all(row['status'] == 'success' for row in smoke['steps']), 'installed smoke failed')
            smoke_seconds = smoke['elapsed_seconds']
        results.append({'python': version, 'tests_run': behavior['tests_run'],
                        'skipped': behavior['skipped'], 'test_seconds': behavior['elapsed_seconds'],
                        'smoke_seconds': smoke_seconds, 'conclusion': 'success'})
    return dict(schema_version=1, contract_version=CONTRACT, profile=plan['profile'],
                head_sha=plan['head_sha'], base_sha=plan['base_sha'], plan_sha256=plan['plan_sha256'],
                context=context, components=plan['components'], selected_tests=plan['selected_tests'],
                unknown_paths=plan['unknown_paths'], producers=statuses, results=results,
                coverage='diagnostic-only', conclusion='success', merge_eligible=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--plan-status', required=True)
    parser.add_argument('--execution-status', required=True)
    parser.add_argument('--governance-status')
    args = parser.parse_args(argv)
    statuses = dict(plan=args.plan_status, execute=args.execution_status)
    if args.governance_status is not None:
        statuses['governance'] = args.governance_status
    context = {'repository': os.environ['GITHUB_REPOSITORY'], 'event': os.environ['GITHUB_EVENT_NAME'],
               'ref': os.environ['GITHUB_REF'], 'run_id': int(os.environ['GITHUB_RUN_ID']),
               'run_attempt': int(os.environ['GITHUB_RUN_ATTEMPT']),
               'workflow_path': os.environ['GITHUB_WORKFLOW_REF'].split('@')[0].split('/', 2)[2]}
    value = summarize(load_plan(args.plan, Path.cwd()), args.directory, statuses, context)
    save(args.output, value)
    print(json.dumps(value, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
