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

DATA = {'.json', '.jsonl', '.yaml', '.yml', '.txt'}
SCRIPTS = {'.py', '.sh', '.bash', '.ps1', '.bat', '.cmd', '.js', '.mjs'}
PACKAGING = {'build_backend.py', 'pyproject.toml', 'runtime-resources.json', 'MANIFEST.in'}


def input_role(path, versions):
    """One role inventory for the shadow model; roles do not prove independence."""
    require = planner.require
    parts = PurePosixPath(path).parts
    require(versions, 'input has no Git version')
    require(parts and not path.startswith('/') and '\\' not in path and ':' not in path
            and all(p not in {'', '.', '..'} for p in path.split('/')), 'unsafe input path')
    modes = {mode for mode, _ in versions}
    if not modes <= {'100644', '100755'} or len(modes) > 1:
        return 'unknown', 'Git type/mode boundary requires review'
    if path in planner.SELECTION_AUTHORITY or path.startswith('.github/workflows/'):
        return 'selection-authority', 'selection or workflow implementation'
    if path == planner.POLICY:
        return 'selection-policy-metadata', 'base policy retained; candidate declarations cannot reduce tests'
    if path in PACKAGING:
        return 'packaging-authority', 'build/install/runtime catalog contract'
    if path in planner.COVERAGE_AUTHORITY:
        return 'coverage-authority', 'coverage policy or measurement contract'
    if path.startswith('.github/') or path == '.gitattributes':
        return 'repository-authority', 'repository-wide configuration or CI tool'
    suffix = PurePosixPath(path).suffix
    if '100755' in modes or suffix in SCRIPTS or any(raw.startswith(b'#!') for _, raw in versions):
        if path.startswith('tests/test_') and suffix == '.py' and modes == {'100644'}:
            return 'test-code', 'test implementation; consumers still required'
        return 'executable', 'executable bytes/mode override directory labels'
    if path.startswith(('schemas/', 'registry/', 'examples/', '.agents/skills/', 'src/')):
        return 'runtime-input', 'schema/registry/Skill/package input needs consumer closure'
    if path.startswith('tests/'):
        return 'test-input', 'fixture/helper data needs test consumer closure'
    archive = path.startswith('work/') or path.startswith('docs/workstreams/') and '/attempts/' in path
    if archive and PurePosixPath(path).name == '.gitattributes':
        allowed = {b'* -text', b'* -text whitespace=cr-at-eol'}
        if all(raw.strip() in allowed for _, raw in versions):
            return 'archive-attributes', 'byte-preservation rule scoped to its directory'
        return 'unknown', 'archive attributes have additional Git semantics'
    if archive and suffix in DATA:
        return 'evidence-data', 'archive instance; validation/real reads remain obligations'
    if suffix == '.md':
        return 'document', 'document bytes; actual runtime readers remain obligations'
    return 'unknown', 'no accepted input category'


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
    planner.require_obligations(plan, minimum)


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
        role, reason = input_role(path, [(mode, raw) for _, mode, raw in versions])
        inputs.append({**change, 'role': role, 'reason': reason,
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
        'report_kind': 'ci-contract-shadow', 'schema_version': 1, 'execution_authority': False,
        'binding': binding, 'observed_plan_id': plan['plan_id'], 'policy_sha256': plan['policy_sha256'],
        'engine_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'inputs': inputs, 'accepted_contracts': contracts, 'dependency_review': chains,
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
