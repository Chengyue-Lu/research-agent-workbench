"""Compute an explainable minimum CI plan from exact Git facts and base policy."""
from __future__ import annotations

import argparse
import ast
import fnmatch
from functools import lru_cache
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
POLICY = 'tests/ci_impact_policy.yaml'
TRUST_FILES = ('.github/scripts/plan_ci.py', '.github/scripts/ci_checks.py',
               '.github/scripts/check_pr_governance.py', '.github/governance-policy.json',
               'tests/run_unittest_suite.py', 'tests/coverage_policy.yaml', POLICY)
LEVELS = {'fast': 0, 'focused': 1, 'full': 2}
METADATA = {'edited', 'labeled', 'unlabeled'}


def consumer_fingerprint(repo, commit, leaves):
    records = git(repo, 'ls-tree', '-r', '-z', commit).decode().split('\0')
    inventory = []
    for record in filter(None, records):
        metadata, path = record.split('\t')
        if path not in leaves and (path.startswith(('src/', 'schemas/', 'registry/')) or path == 'pyproject.toml'):
            inventory.append([path, metadata])
    return digest(sorted(inventory))


def imports(raw):
    tree = ast.parse(raw)
    return sorted(ast.dump(node, include_attributes=False) for node in ast.walk(tree)
                  if isinstance(node, (ast.Import, ast.ImportFrom)))


def changed_lines(repo, base, head, paths):
    result = {}
    for path in paths:
        if not path.endswith('.py'):
            continue
        patch = git(repo, 'diff', '--no-ext-diff', '--no-textconv', '--unified=0', base, head, '--', path).decode()
        lines = set()
        for match in re.finditer(r'(?m)^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', patch):
            start, count = int(match[1]), int(match[2]) if match[2] is not None else 1
            require(count > 0, 'deleted-only source hunk requires FULL')
            lines.update(range(start, start + count))
        result[path] = sorted(lines)
    return result


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')) + '\n').encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def git(repo, *args):
    result = subprocess.run(['git', '--no-replace-objects', '-C', str(repo), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(result.returncode == 0, 'Git fact unavailable: ' + ' '.join(args[:2]))
    return result.stdout


@lru_cache(maxsize=512)
def read_at(repo, commit, path):
    return git(repo, 'show', f'{commit}:{path}')


def exact_commit(repo, value):
    require(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{40}', value), 'exact SHA-1 commit required')
    require(git(repo, 'rev-parse', f'{value}^{{commit}}').decode().strip() == value, 'commit identity mismatch')
    return value


def changes(repo, base, head):
    # --no-renames makes both old and new paths explicit, including copies.
    raw = git(repo, 'diff', '--no-renames', '--name-status', '-z', base, head)
    fields = raw.decode('utf-8', errors='strict').split('\0')
    require(fields[-1] == '' and len(fields) % 2 == 1, 'invalid NUL diff')
    rows = []
    for status, path in zip(fields[:-1:2], fields[1:-1:2]):
        require(status in {'A', 'M', 'D', 'T'} and path and '\\' not in path
                and not any(part in {'', '.', '..'} for part in path.split('/')), 'unclassifiable path/status')
        rows.append({'status': status, 'path': path})
    return sorted(rows, key=lambda row: row['path'])


def closure(policy, seeds):
    groups = policy['groups']
    found, active = set(), set()

    def visit(name):
        require(name in groups, 'unknown impact group: ' + name)
        require(name not in active, 'cyclic impact groups')
        if name in found:
            return
        active.add(name)
        for downstream in groups[name]['downstream']:
            visit(downstream)
        active.remove(name)
        found.add(name)
    for seed in seeds:
        visit(seed)
    return sorted(found)


def validate_policy(policy):
    require(set(policy) == {'policy_id', 'version', 'surfaces', 'groups', 'impact_evidence', 'consumer_fingerprint'}
            and policy['policy_id'] == 'rwb-ci-impact' and policy['version'] == 1, 'impact policy shape/version')
    require(isinstance(policy['groups'], dict) and policy['groups'], 'empty groups')
    for group in policy['groups'].values():
        require(set(group) == {'tests', 'downstream', 'coverage', 'package', 'repository'}, 'group shape')
        for key in ('tests', 'downstream', 'coverage'):
            require(isinstance(group[key], list) and all(isinstance(v, str) and v for v in group[key])
                    and len(group[key]) == len(set(group[key])), 'invalid group list')
        require(group['tests'] and all(re.fullmatch(r'test_[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*', t)
                                     for t in group['tests']), 'invalid tests')
        require(all(p.startswith('src/research_workbench/') and p.endswith('.py')
                    and '..' not in p.split('/') and '\\' not in p for p in group['coverage']), 'coverage module paths')
        require(type(group['package']) is bool and type(group['repository']) is bool, 'invalid smoke flags')
    closure(policy, policy['groups'])
    require(isinstance(policy['surfaces'], dict) and policy['surfaces'], 'empty surfaces')
    for surface in policy['surfaces'].values():
        require(set(surface) == {'paths', 'class', 'groups'} and surface['class'] in {'fast', 'focused'}, 'surface shape')
        require(isinstance(surface['paths'], list) and surface['paths']
                and all(isinstance(p, str) and p and not p.startswith(('/', '*')) and '..' not in p.split('/')
                        for p in surface['paths']), 'surface paths')
        require(isinstance(surface['groups'], list) and surface['groups'], 'surface groups')
        closure(policy, surface['groups'])
    evidence = policy['impact_evidence']
    require(set(evidence) == {'positive_tests', 'negative_tests'}, 'impact evidence shape')
    for names in evidence.values():
        require(isinstance(names, list) and names and len(names) == len(set(names))
                and all(isinstance(n, str) and re.fullmatch(r'test_\w+\.\w+\.test_\w+', n) for n in names),
                'impact evidence IDs')
    require(not set(evidence['positive_tests']) & set(evidence['negative_tests']), 'positive/negative reuse')


def risk_at(repo, base, paths, body):
    # Reuse Governance v2's evaluator with its immutable base risk inventory.
    spec = importlib.util.spec_from_file_location('ci_governance', ROOT / '.github/scripts/check_pr_governance.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    policy = json.loads(read_at(repo, base, '.github/governance-policy.json'))
    module.MINIMUM_RISK_PATHS = policy['minimum_risk_paths']
    metadata = module.parse_metadata(body)
    declared = metadata.get('Risk tier', '')
    flags = [metadata.get(name, '').lower() for name in ('Shared contract', 'Authority impact')]
    require(declared in module.RISK_RANK and all(v in module.YES_VALUES | module.NO_VALUES for v in flags),
            'unknown governance risk metadata')
    inferred, reasons = module.infer_minimum_risk(paths, shared_contract=flags[0] in module.YES_VALUES,
                                                authority_impact=flags[1] in module.YES_VALUES)
    report = module.GovernanceReport()
    return module.resolve_effective_risk(declared, inferred, report), reasons


def make_plan(repo, *, base, head, target, repository, base_ref='develop', body='', integration=False,
              force_full=False, extra_groups=()):
    for sha in (base, head, target):
        exact_commit(repo, sha)
    merge_base = git(repo, 'merge-base', base, head).decode().strip()
    binding = {'repository': repository, 'base': base, 'head': head, 'merge_base': merge_base, 'target': target}
    plan = {'version': 1, 'binding': binding, 'change_class': 'full', 'risk': 'R2', 'changes': [],
            'surfaces': [], 'test_groups': [], 'tests': [], 'coverage_modules': [], 'impact_evidence': {},
            'changed_lines': {},
            'policy_sha256': '', 'python_versions': ['3.11', '3.13'], 'coverage_mode': 'repository',
            'package_smoke': True, 'repository_smoke': True, 'reasons': []}
    reasons = plan['reasons']
    try:
        require(git(repo, 'rev-parse', '--is-shallow-repository').strip() == b'false', 'shallow history')
        rows = changes(repo, merge_base, head)
        plan['changes'] = rows
        paths = [row['path'] for row in rows]
        risk, risk_reasons = risk_at(repo, base, paths, body) if not integration else ('R2', ['integration boundary'])
        plan['risk'] = risk
        reasons.extend(risk_reasons)
        raw = read_at(repo, base, POLICY)
        plan['policy_sha256'] = hashlib.sha256(raw).hexdigest()
        policy = yaml.safe_load(raw)
        validate_policy(policy)
        # New/modified infrastructure cannot authorize its own lighter execution.
        for path in TRUST_FILES:
            require(read_at(repo, base, path) == read_at(repo, head, path), 'CI authority changed: ' + path)
        require(not integration and base_ref == 'develop', 'integration/release boundary')
        require(base == merge_base, 'stale base requires complete merge regression')
        require(risk != 'R2' and not force_full, 'R2 or explicit FULL request')
        require(rows, 'empty diff requires full evidence')
        require(all(row['status'] != 'T' for row in rows), 'type change requires FULL')
        selected, matched = set(), set()
        level = 'fast'
        for path in paths:
            hits = [(name, s) for name, s in policy['surfaces'].items()
                    if any(fnmatch.fnmatchcase(path, pattern) for pattern in s['paths'])]
            require(hits, 'unclassified path: ' + path)
            for name, surface in hits:
                require(surface['class'] != 'fast' or path.endswith('.md'), 'non-Markdown documentation requires FULL')
                matched.add(name)
                selected.update(surface['groups'])
                level = max((level, surface['class']), key=LEVELS.get)
                reasons.append(path + ' -> ' + name)
        groups = closure(policy, selected | set(extra_groups))
        records = [policy['groups'][name] for name in groups]
        tests = sorted({t for g in records for t in g['tests']})
        for name in tests:
            read_at(repo, head, 'tests/' + name.split('.')[0] + '.py')
        modules = sorted({p for g in records for p in g['coverage']})
        if modules:
            level = 'focused'
            require(all(row['status'] == 'M' for row in rows if row['path'].endswith('.py')),
                    'source add/delete/rename requires FULL')
            require(consumer_fingerprint(repo, base, modules) == policy['consumer_fingerprint'],
                    'consumer inventory changed; impact closure needs review')
            for path in paths:
                if path.endswith('.py'):
                    require(imports(read_at(repo, base, path)) == imports(read_at(repo, head, path)),
                            'source imports changed; dependency closure uncertain')
        require(level != 'focused' or modules, 'focused scope lacks coverage obligations')
        require({p for p in paths if p.endswith('.py')} <= set(modules), 'changed source lacks coverage obligation')
        affected_lines = changed_lines(repo, base, head, paths) if modules else {}
        plan.update(change_class=level, surfaces=sorted(matched), test_groups=groups, tests=tests,
                    changed_lines=affected_lines,
                    coverage_modules=modules, impact_evidence=policy['impact_evidence'] if modules else {},
                    python_versions=['3.11', '3.13'] if level == 'focused' else [],
                    coverage_mode='impact' if modules else 'none',
                    package_smoke=any(g['package'] for g in records),
                    repository_smoke=any(g['repository'] for g in records))
        reasons.extend(name + ' -> ' + ','.join(policy['groups'][name]['downstream']) for name in groups)
    except (ValueError, KeyError, TypeError, UnicodeError, SyntaxError, yaml.YAMLError) as error:
        reasons.append('FULL fallback: ' + str(error))
    plan['plan_id'] = digest(plan)
    return plan


def event_plan(repo, event, event_name, *, force_full=False):
    if event_name == 'workflow_dispatch':
        number = str(event['inputs']['pr'])
        require(re.fullmatch(r'[1-9][0-9]*', number), 'dispatch requires an exact PR number')
        repository = event['repository']['full_name']
        response = subprocess.check_output(['gh', 'api', f'repos/{repository}/pulls/{number}'])
        event = {'pull_request': json.loads(response)}
        force_full = True
    pr = event.get('pull_request')
    if pr:
        require(event_name in {'pull_request', 'workflow_dispatch'}, 'unsupported PR event')
        base, head = pr['base']['sha'], pr['head']['sha']
        target = git(repo, 'rev-parse', 'HEAD').decode().strip()
        # Test the supplied merge candidate only when it has the exact PR parents.
        if target != head:
            parents = git(repo, 'show', '-s', '--format=%P', target).decode().split()
            require(parents == [base, head], 'checkout is not the exact PR head/merge candidate')
        return make_plan(repo, base=base, head=head, target=target, repository=pr['base']['repo']['full_name'],
                         base_ref=pr['base']['ref'], body=pr.get('body') or '', force_full=force_full)
    target = git(repo, 'rev-parse', 'HEAD').decode().strip()
    return make_plan(repo, base=target, head=target, target=target,
                     repository=event['repository']['full_name'], integration=True)


def verify_plan(repo, plan, event=None, event_name='pull_request'):
    expected = dict(plan)
    plan_id = expected.pop('plan_id')
    require(digest(expected) == plan_id, 'plan digest mismatch')
    require(git(repo, 'rev-parse', 'HEAD').decode().strip() == plan['binding']['target'], 'plan checkout mismatch')
    # Recompute the minimal obligations without allowing artifact fields to select tests.
    b = plan['binding']
    body = '- **Risk tier**: ' + plan['risk'] + '\n- **Shared contract**: no\n- **Authority impact**: no'
    minimum = (event_plan(repo, event, event_name) if event is not None else
               make_plan(repo, base=b['base'], head=b['head'], target=b['target'], repository=b['repository'], body=body,
                         integration=b['base'] == b['head']))
    require(set(plan) == set(minimum), 'plan shape mismatch')
    require(b == minimum['binding'], 'plan event binding mismatch')
    require(LEVELS[plan['change_class']] >= LEVELS[minimum['change_class']], 'plan below machine minimum')
    if plan['change_class'] != 'full':
        for key in ('test_groups', 'tests', 'coverage_modules', 'python_versions'):
            require(set(plan[key]) >= set(minimum[key]), 'plan drops required ' + key)
        for key in ('package_smoke', 'repository_smoke'):
            require(plan[key] or not minimum[key], 'plan drops required ' + key)
        require(plan['policy_sha256'] == minimum['policy_sha256']
                and plan['impact_evidence'] == minimum['impact_evidence'], 'plan policy/evidence mismatch')
        require(plan['changed_lines'] == minimum['changed_lines'], 'plan changed-line mismatch')
        require(plan['coverage_mode'] == minimum['coverage_mode'], 'plan coverage mode mismatch')
    else:
        require(plan['coverage_mode'] == 'repository' and plan['package_smoke'] is True
                and plan['repository_smoke'] is True and plan['python_versions'] == ['3.11', '3.13'],
                'FULL plan drops obligations')
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--event', type=Path, default=os.environ.get('GITHUB_EVENT_PATH'))
    parser.add_argument('--event-name', default=os.environ.get('GITHUB_EVENT_NAME', 'pull_request'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--force-full', action='store_true')
    args = parser.parse_args(argv)
    plan = event_plan(ROOT, json.loads(args.event.read_text(encoding='utf-8')), args.event_name, force_full=args.force_full)
    args.output.write_bytes(canonical(plan))
    print(json.dumps(plan, indent=2))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as stream:
            for name, value in {'class': plan['change_class'], 'package': str(plan['package_smoke']).lower(),
                                'coverage': plan['coverage_mode'], 'repository': str(plan['repository_smoke']).lower()}.items():
                stream.write(name + '=' + value + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
