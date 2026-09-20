"""Compare a diagnostic consumer proposal with ordered, observed CI execution.

This offline tool never executes consumers or issues a usable execution plan.
Coverage and smoke requirements remain intact; behavioral exclusions are proposals.
"""
from __future__ import annotations

import argparse
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path
import re

import ci_domain_audit as domains
import ci_contract_shadow
import plan_ci as planner

FAILURES = {'failed', 'error', 'unexpected_success'}
OUTCOMES = FAILURES | {'passed', 'skipped', 'passed_with_skips', 'expected_failure', 'missing'}
REQUIREMENTS = ('coverage_scope', 'coverage_obligations', 'coverage_modules', 'changed_lines',
                'coverage_lines', 'impact_evidence', 'package_smoke', 'repository_smoke')


def portable(value):
    planner.require(isinstance(value, str) and value and
                    not any(c in value for c in ('\\', ':', '\x00', '\n', '\r', '[', ']')) and
                    all(p not in {'', '.', '..'} for p in value.split('/')), 'unsafe declaration path')


def identities(values, label):
    domains.strings(values, label)
    for value in values:
        path, separator, method = value.partition('::')
        portable(path)
        planner.require(separator and not any(c in path for c in '*?') and path.startswith('tests/test_') and path.endswith('.py') and
                        re.fullmatch(r'[\w]+(?:\.[\w]+)+', method), 'invalid canonical test identity')


def validate_proposal(proposal):
    planner.require(isinstance(proposal, dict) and set(proposal) ==
                    {'version', 'execution_authority', 'baseline', 'consumers'}, 'unsupported proposal shape')
    planner.require(type(proposal['version']) is int and proposal['version'] == 1 and
                    proposal['execution_authority'] is False, 'unsupported proposal authority/version')
    planner.require(isinstance(proposal['baseline'], str) and re.fullmatch('[0-9a-f]{40}', proposal['baseline']),
                    'exact proposal baseline required')
    planner.require(isinstance(proposal['consumers'], list), 'consumer list required')
    ids = []
    for consumer in proposal['consumers']:
        fields = {'id', 'owner', 'invocation', 'tests', 'input_patterns', 'pins', 'assumptions', 'unknowns'}
        planner.require(isinstance(consumer, dict) and set(consumer) in (fields, fields | {'changed_path_patterns'}),
                        'unsupported consumer fields')
        for field in ('id', 'owner', 'invocation'):
            planner.require(isinstance(consumer[field], str) and consumer[field].strip(), 'named consumer required')
        ids.append(consumer['id'])
        identities(consumer['tests'], 'consumer tests')
        planner.require(consumer['tests'], 'empty consumer tests')
        for field in ('input_patterns', 'assumptions', 'unknowns'):
            domains.strings(consumer[field], field)
        planner.require(consumer['assumptions'], 'unproved closure assumptions must be explicit')
        for pattern in consumer['input_patterns']:
            portable(pattern)
        if 'changed_path_patterns' in consumer:
            domains.strings(consumer['changed_path_patterns'], 'changed path scope')
            planner.require(consumer['changed_path_patterns'], 'empty changed path scope')
            for pattern in consumer['changed_path_patterns']:
                portable(pattern)
        pins = consumer['pins']
        planner.require(isinstance(pins, dict) and pins, 'source pins required')
        for path, signature in pins.items():
            portable(path)
            planner.require(not any(c in path for c in '*?') and isinstance(signature, str) and
                            re.fullmatch('[0-9a-f]{64}', signature), 'invalid source pin')
        planner.require(all(identity.split('::')[0] in pins for identity in consumer['tests']),
                        'every declared test source must be pinned')
    domains.strings(ids, 'consumer identities')


def ordered_union(behavioral, coverage):
    seen = set(behavioral)
    return behavioral + [identity for identity in coverage if identity not in seen]


def validate_inventory(plan, inventory):
    planner.require(isinstance(inventory, dict) and set(inventory) ==
                    {'version', 'plan_id', 'target', 'source', 'scope', 'python_version', 'behavioral_order', 'coverage_order', 'runtime_ids'},
                    'unsupported inventory shape')
    planner.require(type(inventory['version']) is int and inventory['version'] == 1, 'unsupported inventory version')
    planner.require(inventory['scope'] in {'plan-collection', 'observed-subset'}, 'unsupported inventory scope')
    planner.require(inventory['plan_id'] == plan['plan_id'] and inventory['target'] == plan['binding']['target'],
                    'inventory plan/target mismatch')
    planner.require(isinstance(inventory['source'], str) and inventory['source'].strip() and
                    isinstance(inventory['python_version'], str) and
                    re.fullmatch(r'3\.(11|13)\.\d+', inventory['python_version']), 'inventory provenance missing')
    for key in ('behavioral_order', 'coverage_order'):
        identities(inventory[key], key)
    expected = ordered_union(inventory['behavioral_order'], inventory['coverage_order'])
    aliases = inventory['runtime_ids']
    planner.require(isinstance(aliases, dict) and set(aliases) == set(expected), 'inventory aliases incomplete')
    domains.strings(list(aliases.values()), 'runtime IDs')
    planner.require(bool(inventory['behavioral_order']) == (plan['behavioral_scope'] != 'none'),
                    'behavioral inventory scope mismatch')
    planner.require(inventory['scope'] == 'observed-subset' or
                    bool(inventory['coverage_order']) == bool(plan['coverage_obligations']),
                    'coverage inventory scope mismatch')


def candidate_selection(repo, plan, proposal, inventory):
    """Evaluate declared invocation inputs, with conservative unknown fallback.

    Only modified existing, regular Markdown is eligible for this first pilot.
    A matching pin is necessary, never proof that an input declaration is complete.
    """
    binding = plan['binding']
    snapshots = {key: planner.dependencies.snapshot(repo, binding[key])[0]
                 for key in ('base', 'merge_base', 'head', 'target')}
    paths = sorted({row['path'] for row in plan['changes']} |
                   {row['path'] for row in planner.changes(repo, binding['base'], binding['target'])})
    fallback = []
    if not paths:
        fallback.append('empty Git delta is outside the modified Markdown pilot')
    if proposal['baseline'] != binding['base']:
        fallback.append('proposal baseline differs from accepted base')
    if binding['base'] == binding['head']:
        fallback.append('integration requires fresh accepted baseline')
    for path in paths:
        if (not (path == 'README.md' or path.startswith('docs/')) or not path.endswith('.md') or
                any(path not in snapshot or list(snapshot[path][:2]) != ['100644', 'blob'] for snapshot in snapshots.values())):
            fallback.append(path + ': outside modified regular Markdown pilot')
            continue
        if any(planner.read_at(repo, binding[key], path).startswith(b'#!') for key in snapshots):
            fallback.append(path + ': executable document')
    decisions = []
    for consumer in proposal['consumers']:
        reasons = list(fallback) + list(consumer['unknowns'])
        if 'changed_path_patterns' in consumer and any(not any(fnmatchcase(path, pattern)
                for pattern in consumer['changed_path_patterns']) for path in paths):
            reasons.append('changed paths outside declared invocation pilot scope')
        drift = []
        for path, signature in consumer['pins'].items():
            for key, snapshot in snapshots.items():
                entry = snapshot.get(path)
                if not entry or entry[0] not in {'100644', '100755'} or entry[1] != 'blob':
                    drift.append(key + ':' + path + ': absent or unsupported mode')
                elif hashlib.sha256(planner.read_at(repo, binding[key], path)).hexdigest() != signature:
                    drift.append(key + ':' + path + ': pin changed')
        reasons += drift
        affected = [path for path in paths if any(fnmatchcase(path, pattern) for pattern in consumer['input_patterns'])]
        decisions.append({'id': consumer['id'], 'tests': consumer['tests'], 'invocation': consumer['invocation'],
                          'input_matches': affected, 'pin_drift': drift, 'assumptions': consumer['assumptions'],
                          'decision': 'unknown' if reasons else 'select' if affected else 'proposed-skip',
                          'reasons': reasons or (affected if affected else ['no declared invocation input changed'])})
    rows = []
    for identity in inventory['behavioral_order']:
        owners = [row for row in decisions if identity in row['tests']]
        skip = bool(owners) and all(row['decision'] == 'proposed-skip' for row in owners)
        rows.append({'id': identity, 'decision': 'proposed-skip' if skip else 'select',
                     'consumers': [row['id'] for row in owners],
                     'reason': 'all declared consumers propose exclusion' if skip else
                               'affected or unresolved consumer' if owners else 'unknown consumer; retain accepted test'})
    behavioral = [row['id'] for row in rows if row['decision'] == 'select']
    coverage = inventory['coverage_order'][:]
    return {'behavioral_order': behavioral, 'coverage_order': coverage,
            'execution_order': ordered_union(behavioral, coverage), 'decisions': rows,
            'consumers': decisions, 'fallback': fallback,
            'unobserved_declared_tests': sorted({test for c in proposal['consumers'] for test in c['tests']} -
                                              set(inventory['runtime_ids']))}


def compare_receipt(plan, inventory, candidate, receipt, *, suite_label=None):
    expected = ordered_union(inventory['behavioral_order'], inventory['coverage_order'])
    actual, extras, blockers = {}, [], []
    if inventory['scope'] == 'observed-subset':
        blockers.append('observed subset is not complete accepted plan execution')
    if receipt is not None:
        planner.require(isinstance(receipt, dict) and receipt.get('schema_version') == '1.2.0' and
                        receipt.get('plan_id') == plan['plan_id'] and receipt.get('target') == plan['binding']['target'] and
                        receipt.get('python_version') == inventory['python_version'] and
                        receipt.get('coverage_obligations') == plan['coverage_obligations'], 'receipt binding mismatch')
        planner.require(isinstance(receipt.get('tests'), list), 'receipt tests missing')
        seen, runtime = set(), set()
        for row in receipt['tests']:
            planner.require(isinstance(row, dict) and isinstance(row.get('canonical_id'), str) and
                            isinstance(row.get('id'), str) and row.get('outcome', 'missing') in OUTCOMES,
                            'invalid receipt record')
            key = row['canonical_id']
            planner.require(key not in seen and row['id'] not in runtime, 'duplicate receipt identity')
            seen.add(key)
            runtime.add(row['id'])
            if key not in inventory['runtime_ids']:
                extras.append(row)
                continue
            planner.require(row['id'] == inventory['runtime_ids'][key], 'receipt runtime alias mismatch')
            if 'duration_seconds' in row:
                duration = row['duration_seconds']
                planner.require(type(duration) in {int, float} and 0 <= duration < float('inf'), 'invalid duration')
            points = row.get('checkpoints', [])
            planner.require(isinstance(points, list) and all(isinstance(p, dict) and
                            p.get('outcome') in {'passed', 'failed', 'error', 'skipped'} for p in points), 'invalid checkpoints')
            actual[key] = row
        events = receipt.get('events')
        if (not isinstance(events, dict) or any(type(events.get(key)) is not int or events[key] < 0
                                               for key in ('failures', 'errors', 'skips')) or
                events['failures'] or events['errors'] or receipt.get('successful') is not True):
            blockers.append('accepted execution has missing or unsuccessful suite/fixture events')
        if receipt.get('execution_order') != expected:
            blockers.append('accepted execution order incomplete or different from collected inventory')
        if plan['coverage_obligations']:
            contract = {'contract': 'ordered-behavioral-v1', 'behavioral_order': inventory['behavioral_order'],
                        'coverage_order': inventory['coverage_order']}
            if receipt.get('suite') != (suite_label or 'coverage-execution') or receipt.get('execution') != contract:
                blockers.append('source ordered coverage execution contract missing or mismatched')
        elif receipt.get('suite') != (suite_label or plan['behavioral_scope']):
            blockers.append('behavioral receipt suite differs from plan')
        if receipt.get('test_count') != len(actual) or extras:
            blockers.append('receipt inventory count or fixture/unexpected records require review')
    else:
        blockers.append('accepted execution receipt missing')
    retained = set(candidate['execution_order'])
    coverage_unknown = bool(plan['coverage_obligations']) and inventory['scope'] == 'observed-subset'
    rows = []
    for identity in expected:
        row = actual.get(identity, {})
        checkpoint_failure = any(p['outcome'] in FAILURES for p in row.get('checkpoints', []))
        rows.append({'id': identity, 'candidate_execution': 'select' if identity in retained else 'unknown' if coverage_unknown else 'skip',
                     'accepted_outcome': row.get('outcome', 'missing'), 'checkpoint_failure': checkpoint_failure,
                     'checkpoint_skip': any(p['outcome'] == 'skipped' for p in row.get('checkpoints', [])),
                     'duration_seconds': row.get('duration_seconds')})
    failing = [row['id'] for row in rows if row['accepted_outcome'] in FAILURES or row['checkpoint_failure']]
    if failing:
        blockers.append('accepted execution contains failing cases or checkpoints')
    excluded_failures = sorted(set(failing) - retained)
    missed = [] if coverage_unknown else excluded_failures
    inconclusive = [row['id'] for row in rows if row['accepted_outcome'] not in FAILURES | {'passed'} or row['checkpoint_skip']]
    if missed:
        blockers.append('candidate would omit an observed failure')
    if inconclusive:
        blockers.append('accepted cases missing, skipped or otherwise inconclusive')
    removed = [row for row in rows if row['candidate_execution'] == 'skip']
    durations_complete = all(row['duration_seconds'] is not None for row in removed)
    return {'rows': rows, 'failing_ids': failing, 'missed_failure_ids': missed, 'inconclusive_ids': inconclusive,
            'failure_exclusion_unknown_ids': excluded_failures if coverage_unknown else [],
            'unexpected_or_fixture_records': extras, 'blockers': blockers,
            'status': 'missed-failure' if missed else 'inconclusive' if blockers else 'observed-no-missed-failure',
            'excluded_case_seconds_estimate': sum(row['duration_seconds'] for row in removed)
                if durations_complete and receipt and not coverage_unknown else None,
            'duration_missing_ids': [row['id'] for row in removed if row['duration_seconds'] is None]}


def build_report(repo, plan, proposal, inventory, receipt=None):
    validate_proposal(proposal)
    ci_contract_shadow.verify_observed_plan(repo, plan)
    validate_inventory(plan, inventory)
    candidate = candidate_selection(repo, plan, proposal, inventory)
    comparison = compare_receipt(plan, inventory, candidate, receipt)
    behavioral, coverage = inventory['behavioral_order'], inventory['coverage_order']
    execution = ordered_union(behavioral, coverage)
    candidate_set = set(candidate['execution_order'])
    selected_b = set(candidate['behavioral_order'])
    requirements = {key: plan[key] for key in REQUIREMENTS}
    coverage_unknown = bool(plan['coverage_obligations']) and inventory['scope'] == 'observed-subset'
    blockers = ['proposal input closure and independent exclusion witness unproved',
                'inventory and offline receipt provenance not authenticated',
                'candidate execution and same-environment paired timings not performed', *comparison['blockers']]
    if candidate['unobserved_declared_tests']:
        blockers.append('declared tests absent from observed inventory')
    report = {'report_kind': 'ci-consumer-shadow', 'version': 1, 'execution_authority': False,
              'binding': plan['binding'], 'observed_plan_id': plan['plan_id'],
              'proposal_sha256': planner.digest(proposal), 'inventory_sha256': planner.digest(inventory),
              'receipt_sha256': planner.digest(receipt) if receipt else None,
              'producer_sources': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                   (Path(__file__), Path(domains.__file__), Path(ci_contract_shadow.__file__),
                    Path(domains.ci_input_facts.__file__), Path(ci_contract_shadow.ci_consumer_contracts.__file__),
                    Path(planner.__file__), Path(planner.dependencies.__file__),
                    Path(planner.__file__).with_name('check_pr_governance.py'))},
              'observation_scope': inventory['scope'],
              'accepted': {'behavioral_order': behavioral, 'coverage_order': coverage, 'execution_order': execution,
                           'intersection': [i for i in behavioral if i in set(coverage)],
                           'coverage_only': [i for i in coverage if i not in set(behavioral)], 'requirements': requirements},
              'candidate': {**candidate, 'requirements': requirements},
              'behavioral_skips': [i for i in behavioral if i not in selected_b],
              'effective_execution_skips': None if coverage_unknown else [i for i in execution if i not in candidate_set],
              'effective_execution_scope': 'unknown until coverage inventory is complete' if coverage_unknown else 'supplied inventory only',
              'moved_to_coverage_phase': [i for i in behavioral if i not in selected_b and i in set(coverage)],
              'comparison': comparison,
              'coverage_comparison': {'requirements_equal': True, 'candidate_result': 'not-run',
                  'subjects': requirements, 'reason': 'accepted union coverage cannot prove changed candidate lifecycle coverage'},
              'smoke_comparison': {key: {'required': plan[key], 'accepted_result': 'missing' if plan[key] else 'not-required',
                                           'candidate_result': 'not-run' if plan[key] else 'not-required'}
                                   for key in ('package_smoke', 'repository_smoke')},
              'activation': {'eligible': False, 'blockers': blockers},
              'performance': {'savings_proved': False, 'candidate_execution_performed': False,
                              'cost_scope': 'excluded observed case durations only; not job wall, CPU or lifecycle-equivalent savings'}}
    report['report_id'] = planner.digest(report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.'))
    for name in ('plan', 'proposal', 'inventory', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args(argv)
    for source in (args.plan, args.proposal, args.inventory, args.receipt):
        if source is not None:
            planner.require(source.resolve() != args.output.resolve() and not
                            (args.output.exists() and source.exists() and args.output.samefile(source)), 'output would overwrite input')
    def read(path):
        return json.loads(path.read_bytes(), object_pairs_hook=planner.unique_object)
    report = build_report(args.repo.resolve(), read(args.plan), read(args.proposal), read(args.inventory),
                          read(args.receipt) if args.receipt else None)
    args.output.write_bytes(planner.canonical(report))
    print(json.dumps({'report_id': report['report_id'], 'execution_authority': False,
                      'comparison': report['comparison']['status']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
