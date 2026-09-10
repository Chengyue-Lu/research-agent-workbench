"""Validate selective CI coverage, execution obligations and metadata continuity."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import yaml

from plan_ci import ROOT, canonical, coverage_requirements, digest, require, require_obligations, verify_plan


def coverage_config(plan, root):
    """Measure canonical roots and planned files by path, including import aliases.

    Coverage's module-name source filter misses spec_from_file_location aliases.
    A repository source root with a complementary path filter retains unexecuted
    canonical files while avoiding instrumentation of unrelated tests and archives.
    """
    directories = {'src/research_workbench', '.github/scripts'}
    files = {'tests/run_unittest_suite.py'}
    for path in plan['coverage_modules']:
        require(isinstance(path, str) and path.endswith('.py') and not path.startswith('/')
                and all(part not in {'', '.', '..'} for part in path.split('/'))
                and not any(character in path for character in ('\\', ',', '\n', '\r', ':', '*', '?', '[', ']')),
                'unsafe coverage subject path')
        files.add(path)
    omitted = []
    def visit(directory):
        for entry in sorted(directory.iterdir()):
            path = entry.relative_to(root).as_posix()
            if path in directories | files:
                require(not entry.is_symlink(), 'coverage input symlink')
            elif any(p.startswith(path + '/') for p in directories | files):
                require(entry.is_dir() and not entry.is_symlink(), 'coverage ancestor is not a directory')
                visit(entry)
            else:
                require(not any(c in path for c in '\n\r[]*?'), 'unsupported coverage filter path')
                omitted.append(path + '/*' if entry.is_dir() else path)
    visit(root)
    return ('[run]\nbranch = True\nsource =\n    src/research_workbench\n    .github/scripts\n    .\nomit =\n'
            + ''.join('    ' + p + '\n' for p in omitted))


def impact_coverage(plan, policy, coverage, results):
    obligations = coverage_requirements(plan)
    require('impact' in obligations, 'impact plan required')
    require(results.get('plan_id') == plan['plan_id'] and results.get('target') == plan['binding']['target'],
            'impact result binding mismatch')
    expected_suite = 'coverage-quality' if 'repository' in obligations else 'impact'
    require(results.get('coverage_obligations') == plan['coverage_obligations'], 'impact execution obligations mismatch')
    require(results.get('suite') == expected_suite and results.get('successful') is True
            and results.get('test_count', 0) > 0, 'successful impact results required')
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
        affected = set(plan['coverage_lines'].get(path, []))
        require(not affected & set(files[path]['missing_lines']), 'uncovered changed lines: ' + path)
        require('executed_branches' in files[path] and 'missing_branches' in files[path], 'missing branch detail')
        require(not any(source in affected for source, _ in files[path]['missing_branches']),
                'uncovered changed branches: ' + path)
    evidence = plan['impact_evidence']
    positives, negatives = set(evidence['positive_tests']), set(evidence['negative_tests'])
    critical = set(modules) & set(policy['critical_modules'])
    require(not positives & negatives and ((positives and negatives) or (not critical and not positives and not negatives)),
            'distinct positive/negative evidence required')
    passed = {row['id'] for row in results['tests'] if row['outcome'] == 'passed'}
    require(positives | negatives <= passed, 'missing positive/negative PASS evidence')
    # Existing critical files in the impacted closure retain their own mappings.
    require(critical <= {p for m in policy['negative_acceptance'] for p in m['modules']},
            'critical acceptance mapping missing')
    for mapping in policy['negative_acceptance']:
        if set(mapping['modules']) & set(modules):
            require(set(mapping['positive_tests'] + mapping['negative_tests']) <= passed,
                    'missing critical surface PASS evidence: ' + mapping['surface'])
    return {'coverage_scope': 'impact', 'modules': modules, 'repository_coverage_proved': False}


def required_jobs(plan, python):
    require(python in {'3.11', '3.13'}, 'unknown Python gate')
    required = {'plan', 'documentation'}
    require(plan['behavioral_scope'] in {'none', 'focused', 'full'}, 'unknown obligation scope')
    coverage = coverage_requirements(plan)
    if plan['behavioral_scope'] != 'none':
        required.add('compatibility_' + python.replace('.', ''))
    if coverage:
        required.add('coverage_quality')
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
    try:
        require_obligations(previous, current)
    except (ValueError, KeyError, TypeError):
        return False
    return True


def metadata_continuity(plan):
    binding = plan['binding']
    repository = binding['repository']
    response = subprocess.check_output(['gh', 'api', f'repos/{repository}/actions/workflows/ci.yml/runs',
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
    parser.add_argument('operation', choices=('impact', 'coverage', 'configure', 'aggregate', 'metadata'))
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--coverage', type=Path)
    parser.add_argument('--results', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--python', choices=('3.11', '3.13'))
    args = parser.parse_args(argv)
    plan = json.loads(args.plan.read_bytes())
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    event = json.loads(Path(event_path).read_bytes()) if event_path else None
    verify_plan(ROOT, plan, event, os.environ.get('GITHUB_EVENT_NAME', 'pull_request'))
    if args.operation == 'configure':
        require(coverage_requirements(plan), 'coverage obligations required')
        require(args.config is not None, 'coverage configuration output required')
        args.config.parent.mkdir(parents=True, exist_ok=True)
        args.config.write_text(coverage_config(plan, ROOT), encoding='utf-8')
        return 0
    if args.operation in {'impact', 'coverage'}:
        obligations = coverage_requirements(plan)
        require(obligations, 'coverage obligations required')
        result = {}
        if args.operation == 'impact' or 'impact' in obligations:
            result['impact'] = impact_coverage(plan, yaml.safe_load((ROOT / 'tests/coverage_policy.yaml').read_bytes()),
                                              json.loads(args.coverage.read_bytes()), json.loads(args.results.read_bytes()))
        if args.operation == 'coverage' and 'repository' in obligations:
            subprocess.run([sys.executable, str(ROOT / '.github/scripts/check_coverage_policy.py'),
                            '--policy', str(ROOT / 'tests/coverage_policy.yaml'), '--coverage', str(args.coverage),
                            '--test-results', str(args.results)], check=True)
            result['repository'] = 'passed'
    elif args.operation == 'aggregate':
        result = aggregate(plan, json.loads(os.environ['CI_NEEDS']), args.python)
    else:
        result = metadata_continuity(plan)
    print(canonical(result).decode())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
