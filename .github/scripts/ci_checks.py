"""Validate selective CI coverage, execution obligations and metadata continuity."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

import yaml

from plan_ci import ROOT, LEVELS, canonical, digest, require, verify_plan


def impact_coverage(plan, policy, coverage, results):
    require(plan['change_class'] == 'focused' and plan['coverage_mode'] == 'impact', 'impact plan required')
    require(results.get('plan_id') == plan['plan_id'] and results.get('target') == plan['binding']['target'],
            'impact result binding mismatch')
    require(results.get('suite') == 'focused' and results.get('successful') is True
            and results.get('test_count', 0) > 0, 'successful focused results required')
    spec = importlib.util.spec_from_file_location('coverage_policy', ROOT / '.github/scripts/check_coverage_policy.py')
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    thresholds = policy['thresholds']
    require(policy['source_root'] == checker.CANONICAL_SOURCE_ROOT
            and thresholds['global']['line'] >= 90 and thresholds['critical']['line'] >= 95
            and thresholds['critical']['branch'] >= 90, 'coverage policy floor/root drift')
    require(coverage.get('meta', {}).get('branch_coverage') is True, 'branch coverage required')
    files = {checker._normalized_path(path): item for path, item in coverage['files'].items()}
    failures = []
    declared = checker._declared_exclusions(policy, failures)
    require(not failures and checker._actual_exclusions(files) == declared, 'coverage exclusion mismatch')
    modules = plan['coverage_modules']
    require(modules, 'empty impact coverage')
    impact = thresholds['impact']
    require(impact['line'] == 100 and impact['branch'] == 100, 'impact thresholds require 100/100')
    for path in modules:
        require(path in files, 'impact module absent: ' + path)
        summary = files[path]['summary']
        if path in policy['critical_modules']:
            require(checker._line_percent(summary) + 1e-9 >= thresholds['critical']['line'], 'impact line coverage: ' + path)
            require(checker._branch_percent(summary) + 1e-9 >= thresholds['critical']['branch'], 'impact branch coverage: ' + path)
        affected = set(plan['changed_lines'].get(path, []))
        require(not affected & set(files[path]['missing_lines']), 'uncovered changed lines: ' + path)
        require('executed_branches' in files[path] and 'missing_branches' in files[path], 'missing branch detail')
        require(not any(source in affected for source, _ in files[path]['missing_branches']),
                'uncovered changed branches: ' + path)
    evidence = plan['impact_evidence']
    positives, negatives = set(evidence['positive_tests']), set(evidence['negative_tests'])
    require(positives and negatives and not positives & negatives, 'distinct positive/negative evidence required')
    passed = {row['id'] for row in results['tests'] if row['outcome'] == 'passed'}
    require(positives | negatives <= passed, 'missing positive/negative PASS evidence')
    # Existing critical files in the impacted closure retain their own mappings.
    for mapping in policy['negative_acceptance']:
        if set(mapping['modules']) & set(modules):
            require(set(mapping['positive_tests'] + mapping['negative_tests']) <= passed,
                    'missing critical surface PASS evidence: ' + mapping['surface'])
    return {'coverage_mode': 'impact', 'modules': modules, 'repository_coverage_proved': False}


def required_jobs(plan, python):
    require(python in {'3.11', '3.13'}, 'unknown Python gate')
    required = {'plan', 'documentation'}
    if plan['change_class'] != 'fast':
        required.update({'compatibility_' + python.replace('.', ''), 'coverage_quality'})
    if plan['package_smoke']:
        required.add('package_smoke')
    if plan['repository_smoke']:
        required.add('repository_smoke')
    return required


def aggregate(plan, needs, python):
    required = required_jobs(plan, python)
    for name in required:
        require(needs.get(name, {}).get('result') == 'success', 'required job did not succeed: ' + name)
    allowed = {'plan', 'documentation', 'compatibility_311', 'compatibility_313', 'coverage_quality',
               'package_smoke', 'repository_smoke'}
    require(set(needs) <= allowed, 'unknown CI job')
    for name, state in needs.items():
        require(state.get('result') in {'success', 'skipped'}, 'CI job failed or cancelled: ' + name)
    return {'plan_id': plan['plan_id'], 'required_jobs': sorted(required), 'python': python}


def covers(previous, current):
    unsigned = dict(previous)
    signature = unsigned.pop('plan_id', '')
    if digest(unsigned) != signature or previous.get('binding') != current['binding']:
        return False
    if previous.get('policy_sha256') != current['policy_sha256']:
        return False
    if LEVELS.get(previous.get('change_class'), -1) < LEVELS[current['change_class']]:
        return False
    if previous['change_class'] == 'full':
        return (previous.get('coverage_mode') == 'repository' and previous.get('package_smoke') is True
                and previous.get('repository_smoke') is True and previous.get('python_versions') == ['3.11', '3.13'])
    return (all(set(previous[key]) >= set(current[key]) for key in
                ('test_groups', 'tests', 'coverage_modules', 'python_versions'))
            and previous['impact_evidence'] == current['impact_evidence']
            and all(previous[key] or not current[key] for key in ('package_smoke', 'repository_smoke')))


def metadata_continuity(plan):
    binding = plan['binding']
    repository = binding['repository']
    response = subprocess.check_output(['gh', 'api', f'repos/{repository}/actions/runs',
                                        '--method', 'GET', '-f',
                                        'head_sha=' + binding['head'], '-f', 'per_page=30'])
    runs = json.loads(response)['workflow_runs']
    for run in runs:
        if run['head_sha'] != binding['head'] or run['path'] != '.github/workflows/ci.yml':
            continue
        if run['status'] == 'completed' and run['conclusion'] != 'success':
            continue
        with tempfile.TemporaryDirectory(prefix='rwb-ci-proof-') as directory:
            result = subprocess.run(['gh', 'run', 'download', str(run['id']), '--repo', repository,
                                     '--name', 'ci-plan', '--dir', directory], capture_output=True)
            artifact = Path(directory) / 'ci-plan.json'
            if result.returncode == 0 and artifact.is_file() and covers(json.loads(artifact.read_bytes()), plan):
                return {'content_run': run['id'], 'status': run['status'], 'plan_id': plan['plan_id']}
    raise ValueError('No matching content CI plan. Rerun CI with the current PR base/head and risk; metadata cannot substitute code evidence.')


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('impact', 'aggregate', 'metadata'))
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--coverage', type=Path)
    parser.add_argument('--results', type=Path)
    parser.add_argument('--python', choices=('3.11', '3.13'))
    args = parser.parse_args(argv)
    plan = json.loads(args.plan.read_bytes())
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    event = json.loads(Path(event_path).read_bytes()) if event_path else None
    verify_plan(ROOT, plan, event, os.environ.get('GITHUB_EVENT_NAME', 'pull_request'))
    if args.operation == 'impact':
        result = impact_coverage(plan, yaml.safe_load((ROOT / 'tests/coverage_policy.yaml').read_bytes()),
                                 json.loads(args.coverage.read_bytes()), json.loads(args.results.read_bytes()))
    elif args.operation == 'aggregate':
        result = aggregate(plan, json.loads(os.environ['CI_NEEDS']), args.python)
    else:
        result = metadata_continuity(plan)
    print(canonical(result).decode())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
