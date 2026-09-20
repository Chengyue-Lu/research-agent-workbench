"""Offline paired-execution observations; never authorizes reduced CI execution."""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import re

import yaml

import ci_checks
import check_coverage_policy
import ci_consumer_shadow as shadow
import plan_ci as planner

ENVIRONMENT = {'python_version', 'platform', 'machine', 'dependencies_sha256',
               'runner_sha256', 'coverage_config_sha256', 'invocation_context_sha256'}


def validate_bundle(plan, inventory, bundle, role):
    planner.require(isinstance(bundle, dict) and set(bundle) ==
                    {'version', 'role', 'run_id', 'environment', 'driver', 'receipt', 'coverage', 'coverage_binding', 'smokes'}, 'unsupported execution bundle')
    planner.require(type(bundle['version']) is int and bundle['version'] == 1 and bundle['role'] == role,
                    'execution bundle role/version mismatch')
    planner.require(isinstance(bundle['run_id'], str) and bundle['run_id'].strip(), 'distinct execution identity required')
    driver = bundle['driver']
    planner.require(isinstance(driver, dict) and set(driver) == {'sha256', 'invocation'} and
                    isinstance(driver['sha256'], str) and re.fullmatch('[0-9a-f]{64}', driver['sha256']) and
                    isinstance(driver['invocation'], list) and driver['invocation'] and
                    all(isinstance(arg, str) and arg for arg in driver['invocation']), 'execution driver identity missing')
    env = bundle['environment']
    planner.require(isinstance(env, dict) and set(env) == ENVIRONMENT and
                    all(isinstance(value, str) and value for value in env.values()), 'environment contract incomplete')
    for key in ('dependencies_sha256', 'runner_sha256', 'coverage_config_sha256', 'invocation_context_sha256'):
        planner.require(re.fullmatch('[0-9a-f]{64}', env[key]), 'invalid environment digest')
    planner.require(env['python_version'] == inventory['python_version'], 'bundle Python mismatch')
    receipt = bundle['receipt']
    planner.require(isinstance(receipt, dict) and receipt.get('plan_id') == plan['plan_id'] and
                    receipt.get('target') == plan['binding']['target'], 'execution bundle target/plan mismatch')
    duration = receipt.get('wall_seconds')
    planner.require(type(duration) in {int, float} and 0 <= duration < float('inf'), 'valid runner wall time required')
    planner.require(bundle['coverage'] is None or isinstance(bundle['coverage'], dict), 'invalid coverage artifact')
    if bundle['coverage'] is None:
        planner.require(bundle['coverage_binding'] is None, 'coverage binding without artifact')
    else:
        planner.require(bundle['coverage_binding'] == {'plan_id': plan['plan_id'], 'target': plan['binding']['target'],
                        'run_id': bundle['run_id'], 'receipt_sha256': planner.digest(receipt),
                        'coverage_sha256': planner.digest(bundle['coverage'])}, 'coverage/execution association mismatch')
    planner.require(isinstance(bundle['smokes'], dict) and
                    set(bundle['smokes']) <= {'package_smoke', 'repository_smoke'}, 'invalid smoke artifacts')
    for value in bundle['smokes'].values():
        planner.require(isinstance(value, dict) and set(value) ==
                        {'plan_id', 'target', 'run_id', 'execution_receipt_sha256', 'artifact_sha256', 'conclusion', 'source'} and
                        value['plan_id'] == plan['plan_id'] and value['target'] == plan['binding']['target'] and
                        value['run_id'] == bundle['run_id'] and value['execution_receipt_sha256'] == planner.digest(receipt) and
                        isinstance(value['artifact_sha256'], str) and re.fullmatch('[0-9a-f]{64}', value['artifact_sha256']) and
                        value['conclusion'] in {'success', 'failure', 'cancelled', 'skipped', 'missing'} and
                        isinstance(value['source'], str) and value['source'].strip(), 'smoke artifact binding/status invalid')


def candidate_observation(plan, inventory, proposed, receipt):
    """Validate a separate run against the proposed order, never an accepted receipt."""
    unchanged = all(proposed[key] == inventory[key] for key in ('behavioral_order', 'coverage_order'))
    native_suite = 'coverage-execution' if plan['coverage_obligations'] else plan['behavioral_scope']
    expected_suite = receipt.get('suite')
    planner.require(expected_suite == 'shadow-candidate' or unchanged and expected_suite == native_suite,
                    'changed candidate receipt must identify shadow execution')
    adapted = copy.deepcopy(inventory)
    adapted['behavioral_order'] = proposed['behavioral_order']
    adapted['coverage_order'] = proposed['coverage_order']
    adapted['runtime_ids'] = {key: inventory['runtime_ids'][key] for key in proposed['execution_order']}
    # Reuse the receipt integrity checks with an explicit diagnostic suite expectation.
    # The original artifact is unchanged, separately hashed and remains a shadow receipt.
    return shadow.compare_receipt(plan, adapted, proposed, receipt, suite_label=expected_suite)


def coverage_observation(plan, policy, inventory, bundle, execution):
    if not plan['coverage_obligations']:
        return {'status': 'not-required', 'failures': [], 'artifact_supplied': bundle['coverage'] is not None}
    if bundle['coverage'] is None:
        return {'status': 'missing', 'failures': ['required coverage artifact missing']}
    if execution['status'] != 'observed-no-missed-failure':
        return {'status': 'inconclusive', 'failures': ['coverage lacks complete successful ordered execution']}
    records = {row['canonical_id']: row for row in bundle['receipt']['tests']}
    # Checker-only view of measured cases, derived from the retained source receipt.
    results = {'suite': 'coverage-quality' if 'repository' in plan['coverage_obligations'] else 'impact',
               'successful': True, 'plan_id': plan['plan_id'], 'target': plan['binding']['target'],
               'coverage_obligations': plan['coverage_obligations'], 'test_count': len(inventory['coverage_order']),
               'tests': [records[key] for key in inventory['coverage_order']]}
    failures, output = [], io.StringIO()
    with contextlib.redirect_stdout(output):
        try:
            if 'impact' in plan['coverage_obligations']:
                ci_checks.impact_coverage(plan, policy, bundle['coverage'], results)
            if 'repository' in plan['coverage_obligations']:
                failures.extend(check_coverage_policy.check_policy(policy, bundle['coverage'], results))
        except (ValueError, KeyError, TypeError) as error:
            failures.append(str(error))
    return {'status': 'failed' if failures else 'observed-pass', 'failures': failures,
            'checker_output': output.getvalue(), 'coverage_sha256': planner.digest(bundle['coverage']),
            'source_receipt_sha256': planner.digest(bundle['receipt']), 'derived_view_kind': 'offline checker input only'}


def compare_pair(plan, proposal_report, inventory, policy, accepted, candidate):
    for role, bundle in (('accepted', accepted), ('candidate', candidate)):
        validate_bundle(plan, inventory, bundle, role)
    planner.require(accepted['run_id'] != candidate['run_id'] and accepted['receipt'] != candidate['receipt'],
                    'the same execution cannot serve as both members of a pair')
    planner.require(accepted['environment'] == candidate['environment'], 'paired execution environment differs')
    observed = proposal_report['comparison']
    proposed = proposal_report['candidate']
    candidate_result = candidate_observation(plan, inventory, proposed, candidate['receipt'])
    coverage = {role: coverage_observation(plan, policy, inventory, bundle, execution)
                for role, bundle, execution in (('accepted', accepted, observed), ('candidate', candidate, candidate_result))}
    smokes = {role: {name: {'required': plan[name],
                          'conclusion': bundle['smokes'].get(name, {}).get('conclusion', 'missing') if plan[name] else 'not-required'}
                     for name in ('package_smoke', 'repository_smoke')}
              for role, bundle in (('accepted', accepted), ('candidate', candidate))}
    blockers = []
    if accepted['driver']['sha256'] != candidate['driver']['sha256']:
        blockers.append('execution drivers differ; timing comparison has an uncontrolled code difference')
    left, right = accepted['driver']['invocation'], candidate['driver']['invocation']
    differences = [index for index, (a, b) in enumerate(zip(left, right)) if a != b]
    role_only = (len(left) == len(right) and len(differences) == 1 and differences[0] >= 3 and
                 left[differences[0]-1] == '--role' and left.count('--role') == 1 and
                 (left[differences[0]], right[differences[0]]) == ('accepted', 'candidate'))
    if left != right and not role_only:
        blockers.append('execution invocations differ beyond the single --role argument')
    for role, result in (('accepted', observed), ('candidate', candidate_result)):
        if result['status'] != 'observed-no-missed-failure':
            blockers.append(role + ' execution incomplete or unsuccessful')
        if coverage[role]['status'] not in {'not-required', 'observed-pass'}:
            blockers.append(role + ' coverage missing or unsuccessful')
        if any(row['conclusion'] not in {'success', 'not-required'} for row in smokes[role].values()):
            blockers.append(role + ' required smoke missing or unsuccessful')
    a, b = accepted['receipt']['wall_seconds'], candidate['receipt']['wall_seconds']
    return {'report_kind': 'ci-shadow-pair', 'version': 1, 'execution_authority': False,
            'binding': plan['binding'], 'observed_plan_id': plan['plan_id'],
            'proposal_report_id': proposal_report['report_id'], 'environment': accepted['environment'],
            'drivers': {'accepted': accepted['driver'], 'candidate': candidate['driver']},
            'bundles_sha256': {'accepted': planner.digest(accepted), 'candidate': planner.digest(candidate)},
            'behavioral_skips': proposal_report['behavioral_skips'],
            'effective_execution_skips': proposal_report['effective_execution_skips'],
            'moved_to_coverage_phase': proposal_report['moved_to_coverage_phase'],
            'accepted_execution': observed, 'candidate_execution': candidate_result,
            'coverage': coverage, 'smokes': smokes,
            'pair_status': 'inconclusive' if blockers else 'observed-matching-pair', 'blockers': blockers,
            'timing': {'accepted_runner_wall_seconds': a, 'candidate_runner_wall_seconds': b,
                       'difference_seconds': a-b, 'difference_percent': (a-b)/a*100 if a else None,
                       'scope': 'one supplied execution pair; excludes queue/setup; no statistical or hosted speed claim'},
            'activation': {'eligible': False, 'blockers': ['independent exclusion witness and input closure unproved',
                          'offline input provenance is not authentication', 'at least three fresh hosted pairs required']},
            'savings_proved': False}


def build_report(repo, plan, proposal, inventory, accepted, candidate):
    proposal_report = shadow.build_report(repo, plan, proposal, inventory, accepted['receipt'])
    runner_pin = hashlib.sha256(planner.read_at(repo, plan['binding']['target'], 'tests/run_unittest_suite.py')).hexdigest()
    for bundle in (accepted, candidate):
        planner.require(bundle['environment']['runner_sha256'] == runner_pin, 'runner pin differs from tested Git target')
    # Match the actual checker sources to the tested target; do not evaluate historical
    # coverage using a silently changed local threshold/algorithm implementation.
    for path in (Path(ci_checks.__file__), Path(check_coverage_policy.__file__)):
        expected = planner.read_at(repo, plan['binding']['target'], '.github/scripts/' + path.name)
        planner.require(path.read_bytes() == expected, 'coverage checker producer differs from observed target')
    policy = yaml.safe_load(planner.read_at(repo, plan['binding']['target'], 'tests/coverage_policy.yaml'))
    report = compare_pair(plan, proposal_report, inventory, policy, accepted, candidate)
    report['policy_sha256'] = planner.digest(policy)
    report['producer_sources'] = {**proposal_report['producer_sources'], **{
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in
        (Path(__file__), Path(ci_checks.__file__), Path(check_coverage_policy.__file__))}}
    report['report_id'] = planner.digest(report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.'))
    for name in ('plan', 'proposal', 'inventory', 'accepted', 'candidate', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(argv)
    inputs = [getattr(args, name) for name in ('plan', 'proposal', 'inventory', 'accepted', 'candidate')]
    for path in inputs:
        planner.require(args.output.resolve() != path.resolve() and not
                        (args.output.exists() and args.output.samefile(path)), 'output would overwrite input')
    values = [json.loads(path.read_bytes(), object_pairs_hook=planner.unique_object) for path in inputs]
    report = build_report(args.repo.resolve(), *values)
    args.output.write_bytes(planner.canonical(report))
    print(json.dumps({'report_id': report['report_id'], 'pair_status': report['pair_status'], 'execution_authority': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
