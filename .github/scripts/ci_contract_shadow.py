"""Typed input/contract audit beside the accepted plan; never an execution plan.

P1 deliberately retains every accepted worker obligation. Syntax observations and
input roles identify what needs a reviewed boundary, not permission to skip tests.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import time

import plan_ci as planner
import ci_input_facts
import ci_consumer_contracts

def input_facts(path, versions):
    return ci_input_facts.describe(path, versions, selection_authority=planner.SELECTION_AUTHORITY,
                          coverage_authority=planner.COVERAGE_AUTHORITY, policy_path=planner.POLICY)


def input_role(path, versions):
    facts = input_facts(path, versions)
    return facts['role'], facts['reason']



def reference_observations(path, raw):
    """Explain bare-name edges without treating a syntactic write as a safe exclusion."""
    try:
        tree = ast.parse(raw)
    except (SyntaxError, UnicodeError):
        return [{'line': None, 'literal': None, 'context': 'unparseable-consumer'}]
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    observations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if node.value not in {path, PurePosixPath(path).name}:
            continue
        context = 'name-literal'
        ancestor = node
        for _ in range(6):
            ancestor = parents.get(ancestor)
            if ancestor is None:
                break
            if isinstance(ancestor, ast.Call) and isinstance(ancestor.func, ast.Attribute):
                method = ancestor.func.attr
                receiver_nodes = set(ast.walk(ancestor.func.value))
                if node in receiver_nodes and method in {'write_text', 'write_bytes'}:
                    context = 'write-target-syntax'
                    break
                if node in receiver_nodes and method in {'read_text', 'read_bytes', 'open', 'glob', 'rglob'}:
                    context = 'read-target-syntax'
                    break
        observations.append({'line': node.lineno, 'literal': node.value, 'context': context})
    return observations


def verify_observed_plan(repo, plan):
    """Recompute Git-bound accepted minimum, also permitting immutable historical replay."""
    unsigned = dict(plan)
    signature = unsigned.pop('plan_id')
    planner.require(planner.digest(unsigned) == signature, 'observed plan digest mismatch')
    binding = plan['binding']
    if binding['target'] != binding['head']:
        planner.require(planner.git(repo, 'show', '-s', '--format=%P', binding['target']).decode().split()
                        == [binding['base'], binding['head']], 'observed merge target parents mismatch')
    body = '- **Risk tier**: ' + plan['risk'] + '\n- **Shared contract**: no\n- **Authority impact**: no'
    minimum = planner.make_plan(repo, base=binding['base'], head=binding['head'], target=binding['target'],
        repository=binding['repository'], body=body, integration=binding['base'] == binding['head'])
    planner.require(binding == minimum['binding'] and plan['changes'] == minimum['changes'],
                    'observed plan Git facts mismatch')
    planner.require(plan['selection'].get('witness_version') == minimum['selection'].get('witness_version'),
                    'selection witness format changed; regenerate the plan from exact Git snapshots')
    planner.require_obligations(plan, minimum)
    reasons = plan.get('obligation_reasons')
    planner.require(isinstance(reasons, dict) and reasons.keys() == minimum['obligation_reasons'].keys(),
                    'observed obligation reason shape mismatch')
    for obligation, expected in minimum['obligation_reasons'].items():
        actual = reasons[obligation]
        planner.require(isinstance(actual, list) and all(isinstance(item, str) for item in actual),
                        'observed obligation reasons must be strings')
        prefix = 'unclassified dependency surface: '
        planner.require({item for item in actual if item.startswith(prefix)} ==
                        {item for item in expected if item.startswith(prefix)},
                        'observed unclassified obligation reasons mismatch')


def smoke_review(plan, policy):
    """Expose the actual affected source witnesses used by independent smoke flags."""
    selection = plan['selection']
    witnesses = selection.get('affected_witnesses', {})
    review = {}
    for obligation, group_flag in (('package_smoke', 'package'), ('repository_smoke', 'repository')):
        consumers = []
        for path in selection.get('affected_paths', []):
            relevant = (path in {'src/research_workbench/cli.py', 'src/research_workbench/__main__.py'}
                        if obligation == 'package_smoke' else path.startswith('src/research_workbench/validation/'))
            if relevant:
                planner.require(path in witnesses, 'affected smoke consumer is missing its path witness')
                witness = witnesses[path]
                consumers.append({'path': path, **witness, 'contains_fallback_edge':
                                  any(kind != 'syntax-reference' for kind in witness['edge_kinds'])})
        review[obligation] = {'required': plan[obligation], 'accepted_reasons': plan['obligation_reasons'][obligation],
            'accepted_groups': sorted(name for name in plan['test_groups'] if policy['groups'][name][group_flag]),
            'affected_consumers': consumers}
    return review


def propagation_review(repo, plan, inputs):
    """Separate obligation fallbacks from graph reachability and retained witnesses.

    Isolated ordinary closures deliberately omit reviewed overrides. They expose
    overlapping propagation, never a minimum execution set or an exclusion proof.
    Each selected module still has only one diagnostic path witness per seed.
    """
    selection = plan['selection']
    paths = selection.get('affected_witnesses', {})
    rows = []
    for item in inputs:
        path = item['path']
        reason = 'unclassified dependency surface: ' + path
        fallback = [name for name, reasons in sorted(plan['obligation_reasons'].items()) if reason in reasons]
        retained = sorted(test for test, chain in selection.get('selected', {}).items() if chain[0] == path)
        seed = paths.get(path, {}).get('chain') == [path]
        isolated = None
        if seed:
            graph, *_ = planner.dependencies.select(repo, plan['binding']['merge_base'], plan['binding']['head'], {path})
            isolated = {'selected_modules': sorted(graph['selected']),
                'witness_modules': {kind: sorted(test for test, kinds in graph['selected_edge_kinds'].items()
                                                if kind in kinds)
                                    for kind in ('unbounded-resource', 'opaque-execution')},
                'errors': graph['errors']}
        mechanisms = (['unclassified-obligation'] if fallback else [])
        if isolated is not None:
            mechanisms.extend(kind for kind, modules in isolated['witness_modules'].items() if modules)
        rows.append({'path': path, 'input_role': item['role'], 'accepted_graph_seed': seed,
                     'unclassified_obligations': fallback, 'retained_witness_modules': retained,
                     'isolated_ordinary_closure': isolated, 'review_mechanisms': mechanisms})
    return {'execution_authority': False,
            'basis': 'per-input ordinary merge-base/head closure without reviewed overrides; not an execution minimum',
            'graph_binding': {key: plan['binding'][key] for key in ('merge_base', 'head')},
            'path_limit': 'one path per module and input; edge kinds are witnesses, not exhaustive or exclusive causes',
            'count_unit': 'test module; overlapping sets must not be summed or treated as runtime cases or cost',
            'inputs': rows}


def invocation_evidence(repo, plan):
    """Bind effect observations to both graph snapshots, retaining unknown causes.

    A fallback edge is not proof that its source is read by any particular call.
    Non-Python and non-regular entries retain Git identity without interpreting
    their contents as Python. This catalog never participates in make_plan.
    """
    consumers = set(plan['selection'].get('affected_paths', []))
    consumers.update(change['path'] for change in plan['changes'])
    for chain in plan['selection'].get('selected', {}).values():
        consumers.update(chain[1:])
    records, sources, details = [], {}, {}
    for label in ('merge_base', 'head'):
        commit = plan['binding'][label]
        inventory, blobs = planner.dependencies.snapshot(repo, commit)
        for consumer in sorted(consumers & inventory.keys()):
            mode, _, object_id = inventory[consumer]
            raw = blobs.get(consumer)
            legacy = planner.dependencies._file_facts(consumer, raw) if raw is not None else None
            source_sha = hashlib.sha256(raw).hexdigest() if raw is not None else None
            source = {'consumer': consumer, 'source_sha256': source_sha}
            source_id = planner.digest(source) if raw is not None else None
            if source_id is not None and source_id not in sources:
                sites = planner.dependencies.invocation_sites(consumer, raw)
                calls = []
                for row in sites or ():
                    fact = ci_input_facts.describe_invocation(consumer, raw, row['call'],
                           callee=row['callee'], binding=row['binding'], scope=row['scope'])
                    detail = {key: fact[key] for key in ('resolution', 'unresolved', 'execution_authority')}
                    if fact['operation'] == 'unknown':
                        planner.require(not any(fact[key] for key in ('dimensions', 'inputs', 'outputs')),
                                        'unknown call acquired input semantics; update report projection')
                    else:
                        detail.update({key: fact[key] for key in ('dimensions', 'invocation', 'inputs', 'outputs')})
                    detail_id = planner.digest(detail)
                    details[detail_id] = detail
                    site = fact['callsite']
                    calls.append([site['span'], site['scope'], site['ast_sha256'], row['callee'],
                                  row['binding'], fact['operation'], detail_id])
                sources[source_id] = {**source, 'calls': calls}
            record = {'snapshot': label, 'commit': commit, 'consumer': consumer,
                'mode': mode, 'object_id': object_id,
                'source_sha256': source_sha, 'source_id': source_id,
                'analysis_status': ('parsed' if legacy is not None else 'unparseable')
                                   if raw is not None else 'non-regular-python',
                'fallback': {'opaque': legacy[4] if legacy is not None else None,
                    'resources': legacy[5] if legacy is not None else None,
                    'unlocated_causes': legacy is None or bool(legacy[4] or legacy[5])}}
            records.append({'id': planner.digest(record), **record})
    return {'execution_authority': False,
        'basis': 'merge-base/head effect syntax; fallback causes may remain unlocated; not input closure or source-to-call attribution',
        'unknown_argument_policy': 'unclassified context omitted from details; exact call AST/source remains bound; never means absent inputs',
        'site_columns': ['span', 'scope', 'ast_sha256', 'callee', 'binding', 'operation', 'detail_id'],
        'sources': sources, 'details': details,
        'consumers': records}


def _evidence_references(catalog):
    references = {}
    for record in catalog['consumers']:
        references.setdefault(record['consumer'], []).append(record['id'])
    return references


def verify_invocation_evidence(repo, plan, report):
    """Recompute exact Git observations, including omissions and edge associations.

    This verifies report/source consistency, not independent closure certification.
    Re-signing a report cannot legitimize removed unknown sites or changed inputs.
    """
    verify_observed_plan(repo, plan)
    expected = invocation_evidence(repo, plan)
    planner.require(planner.canonical(report.get('invocation_evidence')) == planner.canonical(expected),
                    'invocation evidence does not match exact Git snapshots')
    planner.require(report.get('binding') == plan['binding'] and report.get('observed_plan_id') == plan['plan_id']
                    and report.get('execution_authority') is False,
                    'invocation report binding or authority mismatch')
    references = _evidence_references(expected)
    actual = []
    for row in report.get('dependency_review', []):
        actual.append({'test': row.get('test'), 'edges': [
            {key: edge.get(key) for key in ('source', 'consumer', 'accepted_kind', 'invocation_evidence_ids')}
            for edge in row.get('edges', [])]})
    chains = []
    for test, chain in plan['selection'].get('selected', {}).items():
        chains.append({'test': test, 'edges': [
            {'source': source, 'consumer': consumer, 'accepted_kind': kind,
             'invocation_evidence_ids': references.get(consumer, [])}
            for source, consumer, kind in zip(chain, chain[1:], plan['selection']['selected_edge_kinds'][test])]})
    planner.require(planner.canonical(actual) == planner.canonical(chains),
                    'invocation evidence references do not match accepted dependency witnesses')


def build_report(repo, plan):
    verify_observed_plan(repo, plan)
    binding = plan['binding']
    policy = json.loads(planner.read_at(repo, binding['base'], planner.POLICY),
                        object_pairs_hook=planner.unique_object)
    planner.validate_policy(policy)
    candidate_policy = json.loads(planner.read_at(repo, binding['head'], planner.POLICY),
                                  object_pairs_hook=planner.unique_object)
    planner.validate_policy(candidate_policy)
    contract_snapshots = {key: planner.dependencies.snapshot(repo, binding[key])[0] for key in ('base', 'head')}
    consumer_contracts = ci_consumer_contracts.review(policy.get('consumer_contracts', []),
        candidate_policy.get('consumer_contracts', []), contract_snapshots,
        lambda label, path: planner.read_at(repo, binding[label], path))
    snapshots = [planner.dependencies.snapshot(repo, binding[key]) for key in ('merge_base', 'head')]
    inputs = []
    for change in plan['changes']:
        path = change['path']
        versions = [(key, inventory[path], planner.read_at(repo, binding[key], path)
                     if inventory[path][1] == 'blob' else None)
                    for key, (inventory, _) in zip(('merge_base', 'head'), snapshots) if path in inventory]
        facts = input_facts(path, [(meta[0], raw if raw is not None else b'') for _, meta, raw in versions])
        inputs.append({**change, **facts,
                       'versions': [{'snapshot': label, 'mode': meta[0], 'object_type': meta[1], 'object_id': meta[2],
                                     'content_available': raw is not None,
                                     'sha256': hashlib.sha256(raw).hexdigest() if raw is not None else None}
                                    for label, meta, raw in versions]})
    by_path = {row['path']: row for row in inputs}
    invocations = invocation_evidence(repo, plan)
    invocation_references = _evidence_references(invocations)
    observations = {}
    chains = []
    for test, chain in plan['selection'].get('selected', {}).items():
        kinds = plan['selection']['selected_edge_kinds'][test]
        edges = []
        for source, consumer, kind in zip(chain, chain[1:], kinds):
            key = (source, consumer)
            if key not in observations:
                versions = []
                for label, (_, blobs) in zip(('merge_base', 'head'), snapshots):
                    versions.append({'snapshot': label, 'present': consumer in blobs,
                                     'observations': reference_observations(source, blobs.get(consumer, b''))})
                observations[key] = versions
            edges.append({'source': source, 'consumer': consumer, 'accepted_kind': kind,
                          'syntax_evidence': observations[key],
                          'invocation_evidence_ids': invocation_references.get(consumer, [])})
        role = by_path.get(chain[0], {}).get('role', 'transitive-input')
        concern = ('unbounded-resource' if 'unbounded-resource' in kinds else
                   'opaque-execution' if 'opaque-execution' in kinds else
                   'data-instance-to-code-consumers' if role in {'document', 'evidence-data', 'archive-attributes'}
                   else 'accepted-dependency')
        chains.append({'test': test, 'input_role': role, 'review_reason': concern,
                       'fallback_edge_kinds': sorted(set(kinds) & {'unbounded-resource', 'opaque-execution'}),
                       'edges': edges})
    unknowns = [row['path'] for row in inputs if row['role'] == 'unknown']
    conflicts = [row['path'] for row in inputs if row['role'] in {'document', 'evidence-data', 'archive-attributes'}
                 and any('unclassified dependency surface: ' + row['path'] == reason
                         for reason in plan['obligation_reasons']['behavioral_scope'])]
    contracts = [{'id': name, 'source': 'accepted-base-impact-policy',
                  'tests': group['tests'], 'coverage_subjects': group['coverage'],
                  'downstream': group['downstream']}
                 for name, group in sorted(policy['groups'].items())]
    report = {
        'report_kind': 'ci-contract-shadow', 'schema_version': 5, 'execution_authority': False,
        'binding': binding, 'observed_plan_id': plan['plan_id'], 'policy_sha256': plan['policy_sha256'],
        'engine_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'producer_sources': {'.github/scripts/' + Path(path).name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                             for path in (__file__, ci_input_facts.__file__, ci_consumer_contracts.__file__, planner.__file__, planner.dependencies.__file__,
                                          Path(planner.__file__).with_name('check_pr_governance.py'))},
        'inputs': inputs, 'accepted_contracts': contracts, 'dependency_review': chains,
        'invocation_evidence': invocations,
        'consumer_contract_review': consumer_contracts,
        'smoke_review': smoke_review(plan, policy),
        'propagation_review': propagation_review(repo, plan, inputs),
        'summary': {'input_roles': dict(sorted(Counter(row['role'] for row in inputs).items())),
            'available_test_modules': plan['selection'].get('scope_summary', {}).get('available_test_modules'),
            'dependency_selected_test_modules': len(chains), 'plan_test_selectors': len(plan['tests']),
            'coverage_test_selectors': len(plan['coverage_tests']),
            'review_reasons': dict(sorted(Counter(row['review_reason'] for row in chains).items())),
            'classification_conflicts': conflicts, 'unknown_inputs': unknowns},
        'accepted_obligations': {key: plan[key] for key in ('risk', 'behavioral_scope', 'coverage_obligations',
            'package_smoke', 'repository_smoke')},
        'activation': {'eligible': False, 'reason': 'P1 audit only; input roles and syntax do not authorize exclusions',
                       'required': ['reviewed input/consumer contracts', 'independent witness acceptance',
                                    'real failing-consumer and precision corpus']},
    }
    report['report_id'] = planner.digest(report)
    verify_invocation_evidence(repo, plan, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=planner.ROOT)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    planner.require(args.output.resolve() != args.plan.resolve(), 'shadow output cannot overwrite execution plan')
    started = time.monotonic()
    plan = json.loads(args.plan.read_bytes(), object_pairs_hook=planner.unique_object)
    report = build_report(args.repo, plan)
    args.output.write_bytes(planner.canonical(report))
    print(json.dumps({'report_id': report['report_id'], 'execution_authority': False,
                      'summary': report['summary'], 'analysis_seconds': round(time.monotonic() - started, 6)}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
