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


def build_report(repo, plan):
    verify_observed_plan(repo, plan)
    binding = plan['binding']
    policy = json.loads(planner.read_at(repo, binding['base'], planner.POLICY),
                        object_pairs_hook=planner.unique_object)
    planner.validate_policy(policy)
    snapshots = [planner.dependencies.snapshot(repo, binding[key]) for key in ('merge_base', 'head')]
    inputs = []
    for change in plan['changes']:
        path = change['path']
        versions = [(key, inventory[path][0], planner.read_at(repo, binding[key], path))
                    for key, (inventory, _) in zip(('merge_base', 'head'), snapshots) if path in inventory]
        facts = input_facts(path, [(mode, raw) for _, mode, raw in versions])
        inputs.append({**change, **facts,
                       'versions': [{'snapshot': label, 'mode': mode, 'sha256': hashlib.sha256(raw).hexdigest()}
                                    for label, mode, raw in versions]})
    by_path = {row['path']: row for row in inputs}
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
                          'syntax_evidence': observations[key]})
        role = by_path.get(chain[0], {}).get('role', 'transitive-input')
        concern = ('unbounded-resource' if 'unbounded-resource' in kinds else
                   'opaque-execution' if 'opaque-execution' in kinds else
                   'data-instance-to-code-consumers' if role in {'document', 'evidence-data', 'archive-attributes'}
                   else 'accepted-dependency')
        chains.append({'test': test, 'input_role': role, 'review_reason': concern, 'edges': edges})
    unknowns = [row['path'] for row in inputs if row['role'] == 'unknown']
    conflicts = [row['path'] for row in inputs if row['role'] in {'document', 'evidence-data', 'archive-attributes'}
                 and any('unclassified dependency surface: ' + row['path'] == reason
                         for reason in plan['obligation_reasons']['behavioral_scope'])]
    contracts = [{'id': name, 'source': 'accepted-base-impact-policy',
                  'tests': group['tests'], 'coverage_subjects': group['coverage'],
                  'downstream': group['downstream']}
                 for name, group in sorted(policy['groups'].items())]
    report = {
        'report_kind': 'ci-contract-shadow', 'schema_version': 2, 'execution_authority': False,
        'binding': binding, 'observed_plan_id': plan['plan_id'], 'policy_sha256': plan['policy_sha256'],
        'engine_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'producer_sources': {'.github/scripts/' + Path(path).name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                             for path in (__file__, ci_input_facts.__file__, planner.__file__, planner.dependencies.__file__,
                                          Path(planner.__file__).with_name('check_pr_governance.py'))},
        'inputs': inputs, 'accepted_contracts': contracts, 'dependency_review': chains,
        'smoke_review': smoke_review(plan, policy),
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
