"""Run the component-CI candidate without claiming legacy full/coverage authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import unittest

from ci_components import plan as component_plan

PROFILES = ('component', 'integration-smoke', 'checkpoint', 'release-checkpoint')
SHORT_REGRESSIONS = (
    'test_integrity.IntegrityTests.test_directory_hash_uses_host_independent_posix_order',
    'test_critical_contract_branches.CriticalIntegrityBranchTests.test_reference_statuses_and_hash_guards_are_closed',
    'test_cli.CliTests.test_provider_conformance_execute_rejects_disabled_template_before_environment',
    'test_pr_governance.ReleaseTrustTopologyTests.test_branch_name_alone_cannot_supply_trusted_expectations',
    'test_research_state_candidate.FixtureContractTest.test_two_bounded_cases_pass_schema_and_closure',
    'test_research_state_candidate.RepositoryIntegrationTest.test_cli_consumes_only_explicit_closure',
    'test_research_state_candidate.RepositoryIntegrationTest.test_validate_documents_reports_state_closure_failure',
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, ensure_ascii=False, indent=2).encode() + b'\n')


def git(repo, *args):
    environment = dict(os.environ, GIT_NO_REPLACE_OBJECTS='1', GIT_OPTIONAL_LOCKS='0')
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          env=environment).stdout


def commit(repo, value):
    if not re.fullmatch('[0-9a-f]{40}', value):
        raise ValueError('an exact lowercase commit SHA is required')
    actual = git(repo, 'rev-parse', '--verify', value + '^{commit}').decode().strip()
    if actual != value:
        raise ValueError('commit identity changed')
    return actual


def changed_paths(raw):
    """Read Git -z records, including both paths of a rename/copy."""
    items = raw.decode('utf-8').split('\0')
    if items[-1] != '':
        raise ValueError('unterminated Git change records')
    items.pop()
    result = []
    while items:
        status = items.pop(0)
        if not re.fullmatch(r'[ACDMRTUXB](?:[0-9]+)?', status) or not items:
            raise ValueError('invalid Git change record')
        first = items.pop(0)
        row = {'status': status[0], 'path': first}
        if status[0] in 'RC':
            if not items:
                raise ValueError('missing renamed path')
            row['old_path'], row['path'] = first, items.pop(0)
        result.append(row)
    return result


def make_plan(repo, base, head, profile='component'):
    if profile not in PROFILES:
        raise ValueError('unknown execution profile')
    base, head = commit(repo, base), commit(repo, head)
    merge_base = git(repo, 'merge-base', base, head).decode().strip()
    paths = git(repo, 'ls-tree', '-rz', '--name-only', '--full-tree', head).decode().split('\0')[:-1]
    raw = git(repo, 'show', head + ':tests/ci_components.json')
    policy = json.loads(raw)
    changes = changed_paths(git(repo, 'diff', '--no-ext-diff', '--no-textconv', '--name-status', '-z',
                                '--find-renames', merge_base, head, '--'))
    value = component_plan(changes, paths, policy)
    if profile in ('checkpoint', 'release-checkpoint'):
        value.update(selected_tests=sorted(Path(p).stem for p in paths
                     if re.fullmatch(r'tests/test_[A-Za-z0-9_]+\.py', p)),
                     docs=True, contracts=True, smoke=True, install=True,
                     python_versions=['3.11', '3.13'] if profile == 'release-checkpoint' else ['3.11'])
    elif profile == 'integration-smoke':
        value.update(selected_tests=[], docs=False, contracts=False, smoke=True,
                     install=True, python_versions=['3.11'])
    value.update(kind='component_ci_plan', schema_version='0.1.0', profile=profile,
                 base_sha=base, merge_base_sha=merge_base, head_sha=head,
                 policy_sha256=hashlib.sha256(raw).hexdigest(), changes=changes,
                 execution_authority='candidate-unaccepted', coverage='diagnostic-only')
    value['plan_sha256'] = hashlib.sha256(canonical(value)).hexdigest()
    return value


def load_plan(path, repo):
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    supplied = value.pop('plan_sha256')
    if hashlib.sha256(canonical(value)).hexdigest() != supplied:
        raise ValueError('component plan digest mismatch')
    value['plan_sha256'] = supplied
    if value['kind'] != 'component_ci_plan' or value['schema_version'] != '0.1.0' or value['profile'] not in PROFILES:
        raise ValueError('unsupported component plan')
    if git(repo, 'rev-parse', 'HEAD').decode().strip() != value['head_sha']:
        raise ValueError('checkout differs from planned content')
    raw = git(repo, 'show', value['head_sha'] + ':tests/ci_components.json')
    if hashlib.sha256(raw).hexdigest() != value['policy_sha256']:
        raise ValueError('component policy differs from plan')
    names = value['selected_tests']
    if not isinstance(names, list) or names != sorted(set(names)) or not all(
            isinstance(n, str) and re.fullmatch('test_[A-Za-z0-9_]+', n) for n in names):
        raise ValueError('invalid component test modules')
    expected = make_plan(repo, value['base_sha'], value['head_sha'], value['profile'])
    if canonical(value) != canonical(expected):
        raise ValueError('component plan differs from its Git inputs')
    # The digest is integrity, not independent authority. The candidate check is
    # deliberately not the current protected branch's required result.
    return value


def execute_modules(repo, names, *, stream=None):
    """Reuse the existing timing recorder, not its selection/coverage machinery."""
    tests = Path(repo) / 'tests'
    original_path = sys.path[:]
    sys.path[:0] = [str(Path(repo)), str(tests)]
    try:
        from run_unittest_suite import TimedTextResult, _canonical_test_id, _iter_tests
        loader = unittest.TestLoader()
        unique = {}
        for name in names:
            suite = loader.loadTestsFromName(name)
            if loader.errors:
                raise ValueError('test collection failed: ' + '\n'.join(loader.errors))
            discovered = list(_iter_tests(suite))
            if not discovered:
                raise ValueError('declared selection collected no tests: ' + name)
            for test in discovered:
                unique.setdefault(_canonical_test_id(test), test)
        started = time.perf_counter()
        result = unittest.TextTestRunner(stream=stream or sys.stderr, verbosity=2,
                                        resultclass=TimedTextResult).run(unittest.TestSuite(unique.values()))
        return {'success': result.wasSuccessful(), 'tests_run': result.testsRun,
                'failures': len(result.failures), 'errors': len(result.errors),
                'skipped': len(result.skipped), 'elapsed_seconds': time.perf_counter() - started,
                'records': list(result.records.values())}
    finally:
        sys.path[:] = original_path


def execute_plan(repo, value, *, python_version=None, execute=execute_modules):
    current = python_version or f'{sys.version_info.major}.{sys.version_info.minor}'
    if current not in value['python_versions']:
        raise ValueError('Python version is outside plan')
    baseline = current == '3.11' or value['profile'] == 'release-checkpoint'
    names = set(value['selected_tests']) if baseline else set()
    if value['docs'] and baseline:
        names.add('test_documentation')
    if value['smoke'] and baseline:
        names.update(SHORT_REGRESSIONS)
    result = execute(repo, sorted(names))
    return dict(kind='component_ci_result', schema_version='0.1.0', profile=value['profile'],
                authority='candidate-unaccepted', python=current, head_sha=value['head_sha'],
                plan_sha256=value['plan_sha256'], selections=sorted(names), coverage='not-collected',
                behavior=result)


def aggregate(plan_status, execution_status):
    """Both jobs always exist, including an explicit successful no-op execution."""
    return plan_status == 'success' and execution_status == 'success'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('plan')
    p.add_argument('--repo', type=Path, default=Path.cwd())
    p.add_argument('--base', required=True)
    p.add_argument('--head', required=True)
    p.add_argument('--profile', choices=PROFILES, default='component')
    p.add_argument('--output', required=True)
    p.add_argument('--github-output')
    p = commands.add_parser('run')
    p.add_argument('--repo', type=Path, default=Path.cwd())
    p.add_argument('--plan', required=True)
    p.add_argument('--output', required=True)
    p = commands.add_parser('aggregate')
    p.add_argument('--plan-status', required=True)
    p.add_argument('--execution-status', required=True)
    args = parser.parse_args(argv)
    if args.command == 'plan':
        value = make_plan(args.repo, args.base, args.head, args.profile)
        save(args.output, value)
        if args.github_output:
            with open(args.github_output, 'a', encoding='utf-8', newline='\n') as stream:
                stream.write('python_versions=' + json.dumps(value['python_versions']) + '\n')
                stream.write('install=' + str(value['smoke'] or value['install'] or
                    bool(set(value['selected_tests']) - {'test_documentation'})).lower() + '\n')
                stream.write('smoke=' + str(value['smoke']).lower() + '\n')
        print(json.dumps({k: value[k] for k in ('profile', 'components', 'selected_tests', 'unknown_paths')}))
        return 0
    if args.command == 'run':
        result = execute_plan(args.repo, load_plan(args.plan, args.repo))
        save(args.output, result)
        return 0 if result['behavior']['success'] else 1
    return 0 if aggregate(args.plan_status, args.execution_status) else 1


if __name__ == '__main__':
    raise SystemExit(main())
