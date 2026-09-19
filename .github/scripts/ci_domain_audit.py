"""Offline domain/consumer inventory. Never imported by execution authorities.

Routing declarations describe review ownership, not safe exclusions. The report
preserves the observed plan and enumerates unresolved boundaries for shadow work.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path
import re

import ci_contract_shadow
import ci_input_facts
import plan_ci as planner


MODEL = 'docs/workstreams/chengyue-lu/TEST-PERF-002/domain-model.json'
PATTERNS = ('source_patterns', 'test_patterns', 'input_patterns')
DOMAIN_KEYS = {'id', 'owner', *PATTERNS, 'consumer_ids', 'unknowns'}


def strings(value, label):
    planner.require(isinstance(value, list) and all(isinstance(s, str) and s.strip() for s in value),
                    label + ' must contain nonempty strings')
    planner.require(len(value) == len(set(value)), label + ' contains duplicates')


def validate_model(model):
    planner.require(isinstance(model, dict) and set(model) == {'version', 'execution_authority', 'domains', 'pilots'},
                    'unsupported domain model shape')
    planner.require(type(model['version']) is int and model['version'] == 1, 'unsupported domain model version')
    planner.require(model['execution_authority'] is False, 'domain model cannot grant execution authority')
    planner.require(model['pilots'] == [], 'exclusion pilots require a separately reviewed protocol')
    planner.require(isinstance(model['domains'], list) and bool(model['domains']), 'domains required')
    identities = []
    for domain in model['domains']:
        planner.require(isinstance(domain, dict) and set(domain) == DOMAIN_KEYS, 'unsupported domain fields')
        planner.require(isinstance(domain['id'], str) and re.fullmatch(r'[a-z][a-z0-9-]*', domain['id']),
                        'invalid domain identity')
        planner.require(isinstance(domain['owner'], str) and domain['owner'].strip(), 'named owner required')
        identities.append(domain['id'])
        for key in (*PATTERNS, 'consumer_ids', 'unknowns'):
            strings(domain[key], key)
        planner.require(domain['unknowns'], 'unclosed domain boundaries must be explicit')
        for pattern in sum((domain[key] for key in PATTERNS), []):
            planner.require(not any(c in pattern for c in ('\\', ':', '\x00', '\n', '\r', '[', ']'))
                            and all(part not in {'', '.', '..'} for part in pattern.split('/')),
                            'unsafe or unsupported routing pattern')
        for identity in domain['consumer_ids']:
            planner.require(re.fullmatch(r'[a-z][a-z0-9-]*', identity), 'invalid consumer identity')
    planner.require(len(identities) == len(set(identities)), 'duplicate domain identity')


def routes(path, model):
    """Union overlapping declarations; never choose one role over another."""
    return [{'domain': domain['id'], 'roles': [key.removesuffix('_patterns') for key in PATTERNS
             if any(fnmatchcase(path, pattern) for pattern in domain[key])]} for domain in model['domains']
            if any(fnmatchcase(path, pattern) for key in PATTERNS for pattern in domain[key])]


def inventory_report(inventory, model):
    counts = Counter()
    unknown, overlaps, tests = [], [], {}
    for path in sorted(inventory):
        matches = routes(path, model)
        for match in matches:
            counts[match['domain']] += 1
        if not matches:
            unknown.append(path)
        if len(matches) > 1:
            overlaps.append({'path': path, 'domains': [r['domain'] for r in matches]})
        if path.startswith('tests/test_') and path.endswith('.py'):
            tests[path] = matches
    return {'tracked_count': len(inventory), 'domain_path_counts': dict(sorted(counts.items())),
            'unassigned_paths': unknown, 'overlapping_paths': overlaps, 'test_routes': tests,
            'membership_proved': False}


def receipt_observation(plan, receipt):
    """Summarize provided outcomes without authenticating or re-signing a CI run."""
    if receipt is None:
        return {'status': 'missing', 'execution_proved': False}
    planner.require(isinstance(receipt, dict), 'receipt must be an object')
    planner.require(receipt.get('plan_id') == plan['plan_id'] and receipt.get('target') == plan['binding']['target'],
                    'receipt plan/target mismatch')
    rows = receipt.get('tests')
    planner.require(isinstance(rows, list), 'receipt tests missing')
    ids = [row.get('id') for row in rows if isinstance(row, dict)]
    planner.require(len(ids) == len(rows) and all(isinstance(i, str) and i for i in ids)
                    and len(ids) == len(set(ids)), 'receipt test IDs missing or duplicate')
    counts = Counter(row.get('outcome', 'missing') for row in rows)
    planner.require(set(counts) <= {'passed', 'failed', 'error', 'skipped', 'passed_with_skips',
                                   'expected_failure', 'unexpected_success', 'missing'}, 'unknown receipt outcome')
    by_module = Counter()
    missing_durations = []
    for row in rows:
        if 'duration_seconds' not in row:
            missing_durations.append(row['id'])
            continue
        value = row['duration_seconds']
        planner.require(type(value) in {int, float} and value >= 0 and value < float('inf'), 'invalid duration')
        by_module[row['id'].split('.')[0]] += value
    return {'status': 'provided', 'execution_proved': False, 'authentication': 'not-established-by-offline-input',
            'receipt_sha256': planner.digest(receipt), 'suite': receipt.get('suite'),
            'test_count': len(rows), 'outcomes': dict(sorted(counts.items())),
            'duration_missing_ids': sorted(missing_durations), 'case_cost_complete': not missing_durations,
            'module_case_seconds': dict(sorted(by_module.items(), key=lambda item: (-item[1], item[0]))),
            'cost_scope': 'sum of supplied case durations; not job wall, CPU, or predicted savings',
            'failing_ids': sorted(row['id'] for row in rows if row.get('outcome') in {'failed', 'error', 'unexpected_success'}),
            'inconclusive_ids': sorted(row['id'] for row in rows if row.get('outcome') not in {'passed', 'failed', 'error', 'unexpected_success'})}


def build_report(repo, plan, model, receipt=None):
    validate_model(model)
    ci_contract_shadow.verify_observed_plan(repo, plan)
    binding = plan['binding']
    for key in ('base', 'merge_base', 'head', 'target'):
        planner.exact_commit(repo, binding[key])
    snapshots = {key: planner.dependencies.snapshot(repo, binding[key])[0] for key in ('base', 'merge_base', 'head')}
    accepted = json.loads(planner.read_at(repo, binding['base'], planner.POLICY), object_pairs_hook=planner.unique_object)
    consumer_ids = {record['id'] for record in accepted.get('consumer_contracts', [])}
    refs = sorted({identity for domain in model['domains'] for identity in domain['consumer_ids']})
    missing_refs = sorted(set(refs) - consumer_ids)
    inputs = []
    for change in plan['changes']:
        path = change['path']
        versions = [(key, snapshots[key][path],
                     planner.read_at(repo, binding[key], path) if snapshots[key][path][1] == 'blob' else None)
                    for key in ('merge_base', 'head') if path in snapshots[key]]
        facts = ci_input_facts.describe(path, [(meta[0], raw if raw is not None else b'') for _, meta, raw in versions],
                                       selection_authority=planner.SELECTION_AUTHORITY,
                                       coverage_authority=planner.COVERAGE_AUTHORITY, policy_path=planner.POLICY)
        inputs.append({**change, 'routes': routes(path, model), 'facts': facts,
                       'versions': [{'snapshot': key, 'mode': meta[0], 'object_type': meta[1], 'object_id': meta[2],
                                     'content_available': raw is not None,
                                     'sha256': hashlib.sha256(raw).hexdigest() if raw is not None else None}
                                    for key, meta, raw in versions]})
    domains = sorted({route['domain'] for row in inputs for route in row['routes']})
    inventories = {key: inventory_report(snapshots[key], model) for key in ('merge_base', 'head')}
    blockers = ['routing is not a complete consumer/invocation contract', 'independent exclusion witness unimplemented',
                'candidate selected/skipped and actual coverage/smoke comparison not yet implemented']
    if missing_refs:
        blockers.append('referenced consumer records absent from observed accepted base')
    if any(not row['routes'] or row['facts']['role'] in {'unknown', 'executable'} for row in inputs):
        blockers.append('changed input has unassigned or unresolved executable/membership facts')
    report = {'report_kind': 'ci-domain-audit', 'version': 1, 'execution_authority': False,
              'binding': binding, 'observed_plan_id': plan['plan_id'], 'model_sha256': planner.digest(model),
              'model_source': 'explicit diagnostic proposal; never accepted exclusion policy',
              'producer_sources': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in
                   (Path(__file__), Path(ci_contract_shadow.__file__), Path(ci_input_facts.__file__),
                    Path(ci_contract_shadow.ci_consumer_contracts.__file__), Path(planner.__file__),
                    Path(planner.dependencies.__file__), Path(planner.__file__).with_name('check_pr_governance.py'))},
              'inputs': inputs, 'affected_routing_domains': domains, 'inventories': inventories,
              'consumer_records': {'referenced': refs, 'absent_from_accepted_base': missing_refs},
              'accepted_execution': {key: plan[key] for key in ('risk', 'behavioral_scope', 'tests', 'coverage_tests',
                 'test_groups', 'python_versions', 'coverage_scope', 'coverage_modules', 'coverage_obligations',
                 'changed_lines', 'coverage_lines', 'impact_evidence', 'package_smoke', 'repository_smoke')},
              'observation': receipt_observation(plan, receipt),
              'activation': {'eligible': False, 'blockers': blockers},
              'performance': {'savings_proved': False, 'candidate_execution_performed': False}}
    report['report_id'] = planner.digest(report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('.'))
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--model', type=Path)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    args.model = args.model or args.repo / MODEL
    for source in (args.plan, args.model, args.receipt):
        if source is not None:
            planner.require(args.output.resolve() != source.resolve()
                            and not (args.output.exists() and source.exists() and args.output.samefile(source)),
                            'output must not overwrite plan, model or receipt input')
    def read(path):
        return json.loads(path.read_bytes(), object_pairs_hook=planner.unique_object)
    report = build_report(args.repo.resolve(), read(args.plan), read(args.model), read(args.receipt) if args.receipt else None)
    args.output.write_bytes(planner.canonical(report))
    print(json.dumps({'report_id': report['report_id'], 'execution_authority': False,
                      'affected_routing_domains': report['affected_routing_domains']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
