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
import tomllib

import yaml

ROOT = Path(__file__).resolve().parents[2]
POLICY = 'tests/ci_impact_policy.yaml'
TRUST_FILES = ('.github/scripts/plan_ci.py', '.github/scripts/ci_checks.py',
               '.github/scripts/check_pr_governance.py', '.github/governance-policy.json',
               'tests/run_unittest_suite.py', 'tests/coverage_policy.yaml', POLICY)
LEVELS = {'fast': 0, 'focused': 1, 'full': 2}
BEHAVIOR = {'none': 0, 'focused': 1, 'full': 2}
COVERAGE = {'impact', 'repository'}
# These bounded validators already have base-side critical inventory and acceptance mappings.
CI_EXECUTABLES = {'.github/scripts/plan_ci.py', '.github/scripts/ci_checks.py',
                  '.github/scripts/check_pr_governance.py'}
COVERAGE_AUTHORITY = {'tests/coverage_policy.yaml', '.github/scripts/check_coverage_policy.py',
                      'tests/run_unittest_suite.py', 'pyproject.toml', '.coveragerc', 'setup.cfg', 'tox.ini',
                      '.github/workflows/ci.yml'}
METADATA = {'edited', 'labeled', 'unlabeled'}


def consumer_fingerprint(repo, commit, leaves):
    records = git(repo, 'ls-tree', '-r', '-z', commit).decode().split('\0')
    inventory = []
    for record in filter(None, records):
        metadata, path = record.split('\t')
        if path not in leaves and (path.startswith(('src/', 'schemas/', 'registry/')) or path == 'pyproject.toml'
                                   or (path.startswith('tests/') and path.endswith('.py'))):
            inventory.append([path, metadata])
    return digest(sorted(inventory))


def imports(raw):
    tree = ast.parse(raw)
    return sorted(ast.dump(node, include_attributes=False) for node in ast.walk(tree)
                  if isinstance(node, (ast.Import, ast.ImportFrom)))


def changed_lines(repo, base, head, paths, uncertainties=None):
    result = {}
    for path in paths:
        if not path.endswith('.py'):
            continue
        patch = git(repo, 'diff', '--no-ext-diff', '--no-textconv', '--unified=0', base, head, '--', path).decode()
        lines = set()
        for match in re.finditer(r'(?m)^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', patch):
            start, count = int(match[1]), int(match[2]) if match[2] is not None else 1
            if count == 0:
                require(uncertainties is not None, 'deleted-only source hunk requires FULL')
                uncertainties.append('deleted-only source hunk requires FULL: ' + path)
            lines.update(range(start, start + count))
        result[path] = sorted(lines)
    return result


def coverage_lines(repo, head, physical_lines, uncertainties=None):
    """Conservatively cover the enclosing statement, including multiline branch origins."""
    result = {}
    for path, lines in physical_lines.items():
        source = read_at(repo, head, path).decode()
        tree = ast.parse(source)
        statements = [node for node in ast.walk(tree) if isinstance(node, ast.stmt)]
        # Decorator expressions execute before the definition's own statement span.
        statements.extend(decorator for node in ast.walk(tree)
                          for decorator in getattr(node, 'decorator_list', []))
        affected = set()
        for line in lines:
            owners = [node for node in statements if node.lineno <= line <= node.end_lineno]
            if not owners:
                require(uncertainties is not None and (not source.splitlines()[line - 1].strip()
                        or source.splitlines()[line - 1].lstrip().startswith('#')),
                        'changed line has no executable statement mapping; requires FULL')
                # AST parsing succeeded: module-level blank/comment lines have no executable owner.
                uncertainties.append('changed line has no executable statement mapping; requires FULL: ' + path)
                continue
            # The smallest enclosing statement excludes unrelated outer suites. Expanding its
            # complete span also covers continuation lines and branch sources within expressions.
            owner = min(owners, key=lambda node: (node.end_lineno - node.lineno, -node.col_offset))
            affected.update(range(owner.lineno, owner.end_lineno + 1))
        result[path] = sorted(affected)
    return result


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')) + '\n').encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate policy key: ' + key)
        result[key] = value
    return result


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
            and policy['policy_id'] == 'rwb-ci-impact' and type(policy['version']) is int
            and policy['version'] == 1, 'impact policy shape/version')
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


def non_executable(path):
    """Only data/document/test surfaces; test infrastructure is classified first."""
    return (path.endswith('.md') or path.startswith('work/')
            or (path.startswith('tests/') and (Path(path).name.startswith('test_') and path.endswith('.py')
                or path.endswith(('.json', '.yaml', '.yml', '.txt', '.toml')))))


def validator_evidence(repo, base, modules):
    policy = yaml.safe_load(read_at(repo, base, 'tests/coverage_policy.yaml'))
    require(set(modules) <= set(policy['critical_modules']), 'validator absent from base critical inventory')
    mappings = [m for m in policy['negative_acceptance'] if set(m['modules']) & set(modules)]
    require(set(modules) <= {p for m in mappings for p in m['modules']}, 'validator acceptance mapping missing')
    evidence = {key: sorted({t for m in mappings for t in m[key]})
                for key in ('positive_tests', 'negative_tests')}
    require(all(evidence.values()) and not set(evidence['positive_tests']) & set(evidence['negative_tests']),
            'validator positive/negative evidence invalid')
    return evidence


def coverage_authority_changed(repo, base, head, path):
    before, after = (read_at(repo, commit, path) for commit in (base, head))
    if path == 'tests/coverage_policy.yaml':
        return yaml.safe_load(before) != yaml.safe_load(after)
    if path == 'pyproject.toml':
        configs = [tomllib.loads(raw.decode()) for raw in (before, after)]
        for config in configs:
            for key in ('name', 'version', 'description', 'readme', 'authors', 'maintainers',
                        'urls', 'classifiers', 'keywords', 'license', 'license-files'):
                config.get('project', {}).pop(key, None)
        # Dependencies, interpreter requirements, entrypoints, build configuration and
        # measurement configuration can change executable/coverage semantics.
        return configs[0] != configs[1]
    return before != after


def coverage_requirements(plan):
    obligations = plan['coverage_obligations']
    require(isinstance(obligations, list) and all(isinstance(v, str) and v in COVERAGE for v in obligations)
            and obligations == sorted(set(obligations)), 'invalid coverage obligation set')
    require(plan['coverage_scope'] == ('+'.join(obligations) or 'none'), 'coverage scope/set mismatch')
    return set(obligations)


def require_obligations(plan, minimum):
    """Compare dimensions independently, also used for authenticated metadata continuity."""
    require(plan['version'] == minimum['version'] == 3, 'plan version mismatch')
    require(not plan['blocked_reasons'] and not minimum['blocked_reasons'], 'unproved executable impact obligations')
    ranks = {'R0': 0, 'R1': 1, 'R2': 2}
    require(ranks.get(plan['risk'], -1) >= ranks[minimum['risk']], 'plan lowers governance risk')
    require(BEHAVIOR.get(plan['behavioral_scope'], -1) >= BEHAVIOR[minimum['behavioral_scope']],
            'plan below machine minimum: behavioral_scope')
    required_coverage = coverage_requirements(minimum)
    require(coverage_requirements(plan) >= required_coverage, 'plan below machine minimum: coverage obligations')
    require(plan['change_class'] == {'none': 'fast', 'focused': 'focused', 'full': 'full'}[plan['behavioral_scope']],
            'change class disagrees with behavioral minimum')
    require(plan['risk'] != 'R2' or plan['behavioral_scope'] == 'full', 'R2 requires full behavioral regression')
    require(plan['python_versions'] == ([] if plan['behavioral_scope'] == 'none' else ['3.11', '3.13']),
            'plan drops required python_versions')
    for key in ('package_smoke', 'repository_smoke'):
        require(type(plan[key]) is bool and (plan[key] or not minimum[key]), 'plan drops required ' + key)
    require(plan['policy_sha256'] == minimum['policy_sha256'], 'plan policy mismatch')
    if plan['behavioral_scope'] != 'full':
        for key in ('tests', 'test_groups'):
            require(set(plan[key]) >= set(minimum[key]), 'plan drops required ' + key)
    if 'impact' in required_coverage:
        for key in ('coverage_modules', 'coverage_tests'):
            require(set(plan[key]) >= set(minimum[key]) and plan[key], 'plan drops required ' + key)
        require(plan['impact_evidence'] == minimum['impact_evidence'], 'plan evidence mismatch')
        require(plan['changed_lines'] == minimum['changed_lines'], 'plan changed-line mismatch')
        require(plan['coverage_lines'] == minimum['coverage_lines'], 'plan executable-line mapping mismatch')


def make_plan(repo, *, base, head, target, repository, base_ref='develop', body='', integration=False,
              force_full=False, extra_groups=()):
    for sha in (base, head, target):
        exact_commit(repo, sha)
    merge_base = git(repo, 'merge-base', base, head).decode().strip()
    binding = {'repository': repository, 'base': base, 'head': head, 'merge_base': merge_base, 'target': target}
    plan = {'version': 3, 'binding': binding, 'change_class': 'full', 'risk': 'R2', 'changes': [],
            'surfaces': [], 'test_groups': [], 'tests': [], 'coverage_modules': [], 'impact_evidence': {},
            'changed_lines': {}, 'coverage_lines': {}, 'coverage_tests': [],
            'policy_sha256': '', 'python_versions': ['3.11', '3.13'],
            'behavioral_scope': 'full', 'coverage_scope': 'repository', 'coverage_obligations': ['repository'],
            'blocked_reasons': [],
            'package_smoke': True, 'repository_smoke': True, 'reasons': [], 'obligation_reasons': {}}
    reasons = plan['reasons']
    try:
        require(git(repo, 'rev-parse', '--is-shallow-repository').strip() == b'false', 'shallow history')
        rows = changes(repo, merge_base, head)
        plan['changes'] = rows
        paths = [row['path'] for row in rows]
        coverage_reasons = []
        try:
            risk, risk_reasons = risk_at(repo, base, paths, body) if not integration else ('R2', ['integration boundary'])
        except ValueError as error:
            risk, risk_reasons = 'R2', [str(error)]
            coverage_reasons.append(str(error))
        plan['risk'] = risk
        reasons.extend(risk_reasons)
        raw = read_at(repo, base, POLICY)
        plan['policy_sha256'] = hashlib.sha256(raw).hexdigest()
        policy = json.loads(raw, object_pairs_hook=unique_object)
        validate_policy(policy)
        require(not integration, 'integration/release boundary')
        for condition, reason in ((base_ref != 'develop', 'integration/release boundary'),
                                  (base != merge_base, 'stale base requires complete merge regression'),
                                  (force_full, 'explicit complete-evidence request')):
            if condition:
                coverage_reasons.append(reason)
        require(rows, 'empty diff requires full evidence')
        if any(row['status'] == 'T' for row in rows):
            coverage_reasons.append('type change requires FULL')
        selected, matched = set(), set()
        validators, executable = set(), set()
        package_reasons, repository_reasons = [], []
        level = 'fast'
        for path in paths:
            if path in COVERAGE_AUTHORITY:
                level = 'full'
                if coverage_authority_changed(repo, base, head, path):
                    coverage_reasons.append('coverage authority changed: ' + path)
                if path in {'pyproject.toml', 'setup.cfg'}:
                    package_reasons.append('package metadata changed: ' + path)
                continue
            if path in CI_EXECUTABLES:
                validators.add(path)
                executable.add(path)
                level = 'full'
                continue
            if path in {POLICY, '.github/governance-policy.json'}:
                # Candidate metadata never supplies this PR's selection authority.
                level = 'full'
                reasons.append('base-side selection retained; policy metadata changed: ' + path)
                continue
            hits = [(name, s) for name, s in policy['surfaces'].items()
                    if any(fnmatch.fnmatchcase(path, pattern) for pattern in s['paths'])]
            if not hits:
                level = 'full'
                if non_executable(path):
                    reasons.append('test/document/archive data: ' + path)
                    continue
                if path.startswith(('schemas/', 'registry/', 'examples/')) and path.endswith(('.json', '.yaml', '.yml')):
                    repository_reasons.append('repository validation surface: ' + path)
                    if path.startswith('schemas/'):
                        package_reasons.append('installed schema resources: ' + path)
                    continue
                reason = 'unknown/high-fanout executable or surface: ' + path
                coverage_reasons.append(reason)
                package_reasons.append(reason)
                repository_reasons.append(reason)
                continue
            for name, surface in hits:
                if surface['class'] == 'fast' and not path.endswith('.md'):
                    coverage_reasons.append('non-Markdown documentation requires FULL')
                matched.add(name)
                selected.update(surface['groups'])
                level = max((level, surface['class']), key=LEVELS.get)
                reasons.append(path + ' -> ' + name)
            if path.endswith('.py'):
                executable.add(path)
        groups = closure(policy, selected | set(extra_groups))
        records = [policy['groups'][name] for name in groups]
        tests = sorted({t for g in records for t in g['tests']})
        modules = sorted({p for g in records for p in g['coverage']})
        if modules:
            level = max((level, 'focused'), key=LEVELS.get)
        # Record a known impact minimum before fallible mapping/guard work. Failure cannot erase it.
        if modules or validators:
            plan['coverage_obligations'] = ['impact', 'repository']
            plan['coverage_scope'] = 'impact+repository'
        evidence = policy['impact_evidence'] if modules else {'positive_tests': [], 'negative_tests': []}
        uncertainties = []

        def guard(condition, reason):
            if not condition:
                uncertainties.append(reason)

        if modules or validators:
            guard(all(row['status'] == 'M' for row in rows if row['path'] in executable),
                    'source add/delete/rename requires FULL')
            guard(not git(repo, 'diff', '--no-ext-diff', '--summary', merge_base, head, '--',
                            *sorted(executable)).strip(), 'source mode drift requires FULL')
            if modules:
                guard(consumer_fingerprint(repo, base, modules) == policy['consumer_fingerprint'],
                        'consumer inventory changed; impact closure needs review')
                # Test-only changes do not need coverage, but cannot silently expand a leaf closure.
                guard(consumer_fingerprint(repo, head, modules) == policy['consumer_fingerprint'],
                        'candidate consumer inventory changed; impact closure needs review')
            for path in executable:
                guard(imports(read_at(repo, merge_base, path)) == imports(read_at(repo, head, path)),
                        'source imports changed; dependency closure uncertain')
                guard([line for line in read_at(repo, merge_base, path).splitlines() if b'pragma:' in line]
                        == [line for line in read_at(repo, head, path).splitlines() if b'pragma:' in line],
                        'coverage exclusion semantics changed: ' + path)
            if validators:
                validator_mapping = validator_evidence(repo, base, validators)
                evidence = {key: sorted(set(evidence[key]) | set(validator_mapping[key])) for key in evidence}
                tests = sorted(set(tests) | {t.split('.')[0] for names in validator_mapping.values() for t in names})
                modules = sorted(set(modules) | validators)
        for name in tests:
            read_at(repo, head, 'tests/' + name.split('.')[0] + '.py')
        require(executable <= set(modules), 'changed source lacks coverage obligation')
        for path in executable:
            require(read_at(repo, head, path) == read_at(repo, target, path),
                    'merge candidate changed impact line coordinates; rebase required: ' + path)
        affected_lines = changed_lines(repo, merge_base, head, sorted(executable), uncertainties) if modules else {}
        executable_lines = coverage_lines(repo, head, affected_lines, uncertainties)
        coverage_reasons.extend(sorted(set(uncertainties)))
        reasons.extend(sorted(set(uncertainties)))
        if risk == 'R2' or coverage_reasons:
            level = 'full'
        obligations = (['impact'] if modules else []) + (['repository'] if coverage_reasons else [])
        behavioral = {'fast': 'none', 'focused': 'focused', 'full': 'full'}[level]
        package_reasons.extend('affected dependency group: ' + name for name in groups if policy['groups'][name]['package'])
        repository_reasons.extend('affected dependency group: ' + name for name in groups if policy['groups'][name]['repository'])
        plan.update(change_class=level, surfaces=sorted(matched), test_groups=groups, tests=tests,
                    changed_lines=affected_lines, coverage_lines=executable_lines,
                    coverage_modules=modules, impact_evidence=evidence if modules else {},
                    coverage_tests=tests if modules else [], behavioral_scope=behavioral,
                    python_versions=['3.11', '3.13'] if behavioral != 'none' else [],
                    coverage_scope='+'.join(obligations) or 'none', coverage_obligations=obligations,
                    package_smoke=bool(package_reasons) or force_full, repository_smoke=bool(repository_reasons) or force_full,
                    obligation_reasons={
                        'behavioral_scope': ['authority-sensitive PR requires complete behavioral regression' if risk == 'R2'
                                             else 'exact diff and base-side dependency closure require ' + behavioral],
                        'coverage_scope': (['bounded executable change requires impact 100/100 and base-side acceptance'] if modules else [])
                                           + coverage_reasons or ['no production/critical executable or coverage authority changed'],
                        'package_smoke': package_reasons or ['no packaging/install surface changed'],
                        'repository_smoke': repository_reasons or ['no repository validation surface changed']})
        reasons.extend(name + ' -> ' + ','.join(policy['groups'][name]['downstream']) for name in groups)
    except (ValueError, KeyError, TypeError, UnicodeError, SyntaxError, yaml.YAMLError) as error:
        reasons.append('FULL fallback: ' + str(error))
        if 'impact' in plan['coverage_obligations']:
            plan['blocked_reasons'].append(str(error))
        plan['obligation_reasons'] = {key: ['fail-safe complete evidence: ' + str(error)] for key in
                                      ('behavioral_scope', 'coverage_scope', 'package_smoke', 'repository_smoke')}
    plan['plan_id'] = digest(plan)
    return plan


def event_plan(repo, event, event_name, *, force_full=False):
    if event_name == 'workflow_dispatch':
        number = str(event['inputs']['pr'])
        require(re.fullmatch(r'[1-9][0-9]*', number), 'dispatch requires an exact PR number')
        repository = event['repository']['full_name']
        response = subprocess.check_output(['gh', 'api', f'repos/{repository}/pulls/{number}'])
        event = {'pull_request': json.loads(response)}
        require(os.environ.get('GITHUB_SHA') == event['pull_request']['head']['sha'],
                'dispatch trigger SHA must equal current PR head; start a new dispatch with --ref <current-pr-branch>')
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
    require(not git(repo, 'status', '--porcelain', '--untracked-files=no'), 'tracked checkout drift')
    require(not git(repo, 'status', '--porcelain', '--untracked-files=all', '--', '.github', 'src', 'tests'),
            'untracked CI/source/test input')
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
    require_obligations(plan, minimum)
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
            for name, value in {'class': plan['change_class'], 'behavioral': plan['behavioral_scope'],
                                'package': str(plan['package_smoke']).lower(), 'coverage': plan['coverage_scope'],
                                'repository': str(plan['repository_smoke']).lower()}.items():
                stream.write(name + '=' + value + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
