"""Join actual component producers into a small, versioned CI result."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from run_component_ci import (canonical, canonical_record_id, execution_matrix,
                              execution_names, load_plan, save, shard_inventory)

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
    matrix = execution_matrix(plan)
    if any(row['shard_count'] > 1 for row in matrix):
        expected = {row['artifact_name'] for row in matrix}
        observed = {path.name for path in Path(directory).glob('component-result-*') if path.is_dir()}
        require(observed == expected, 'missing or unexpected native shard producers')
    for version in plan['python_versions']:
        rows = [row for row in matrix if row['python'] == version]
        behaviors, smoke_durations, inventory = [], [], None
        for producer in rows:
            root = Path(directory) / producer['artifact_name']
            value = json.loads((root / 'result.json').read_text(encoding='utf-8'))
            sharded = producer['shard_count'] > 1
            require(value.get('kind') == 'component_ci_result'
                    and value.get('schema_version') == ('0.2.0' if sharded else '0.1.0')
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
            if sharded:
                require(type(value.get('shard_index')) is int and type(value.get('shard_count')) is int
                        and value['shard_index'] == producer['shard_index']
                        and value['shard_count'] == producer['shard_count'],
                        'foreign shard identity')
                require(value.get('selections') == execution_names(plan, version),
                        'shard selection differs from plan')
                current_inventory = behavior['inventory']
                assigned = shard_inventory(current_inventory, producer['shard_index'], producer['shard_count'])
                require(current_inventory
                        and behavior['inventory_sha256'] == hashlib.sha256(canonical(current_inventory)).hexdigest(),
                        'missing or forged collected inventory')
                require(inventory is None or current_inventory == inventory, 'shard inventories differ')
                inventory = current_inventory
                received = [canonical_record_id(row['id']) for row in behavior['records']]
                require(len(received) == len(set(received)) and sorted(received) == assigned,
                        'missing, repeated or foreign shard test results')
            if plan['smoke']:
                smoke = json.loads((root / 'smoke.json').read_text(encoding='utf-8'))
                require(smoke['status'] == 'success' and len(smoke['steps']) == 8
                        and all(row['status'] == 'success' for row in smoke['steps']), 'installed smoke failed')
                smoke_durations.append(smoke['elapsed_seconds'])
            behaviors.append(behavior)
        result = {'python': version, 'tests_run': sum(item['tests_run'] for item in behaviors),
                  'skipped': sum(item['skipped'] for item in behaviors),
                  'test_seconds': sum(item['elapsed_seconds'] for item in behaviors),
                  'smoke_seconds': sum(smoke_durations) if plan['smoke'] else None,
                  'conclusion': 'success'}
        if len(rows) > 1:
            require(result['tests_run'] == len(inventory), 'incomplete collected suite')
            result.update(shards=len(rows), max_shard_test_seconds=max(item['elapsed_seconds'] for item in behaviors))
        results.append(result)
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
