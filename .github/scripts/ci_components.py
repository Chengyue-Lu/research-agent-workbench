"""Small path-based CI plan. Unknown ownership is visible; it never means FULL."""
import re

FLAGS = ('docs', 'smoke', 'install', 'contracts')
MODULE = re.compile(r'test_[A-Za-z0-9_]+\Z')


def _path(value, *, prefix=False):
    if not isinstance(value, str) or not value or any(c in value for c in ('\\', ':', '*', '?', '[')):
        raise ValueError('expected a literal repository-relative path')
    value = value[:-1] if prefix and value.endswith('/') else value
    if any(part in {'', '.', '..'} for part in value.split('/')):
        raise ValueError('unsafe repository-relative path')
    return value


def _tests(values):
    if not isinstance(values, list) or any(not isinstance(v, str) or not MODULE.fullmatch(v) for v in values):
        raise ValueError('policy tests must be exact test module names')
    return values


def _module(path):
    name = path.removeprefix('tests/').removesuffix('.py')
    return name if path.startswith('tests/') and path.endswith('.py') and MODULE.fullmatch(name) else None


def plan(changes, inventory, policy):
    """Return a deterministic version-1 plan from paths and explicit component maps.

    Test names are bare modules. python_versions applies to install/smoke checks;
    selected business modules run on the baseline Python 3.11 only. The caller
    retains the complete inventory for explicit checkpoint runs.
    """
    if not isinstance(policy, dict) or policy.get('version') != 1:
        raise ValueError('unsupported component policy')
    components = policy.get('components')
    direct = policy.get('direct_tests', {})
    nearest = policy.get('nearest_components', {})
    if not isinstance(components, dict) or not components or not isinstance(direct, dict) or not isinstance(nearest, dict):
        raise ValueError('invalid component maps')
    if not {'docs', 'build'} <= components.keys(): raise ValueError('missing docs/build categories')
    _tests(policy.get('install_docs_tests', []))
    for name, rule in components.items():
        if not isinstance(name, str) or not name or not isinstance(rule, dict):
            raise ValueError('invalid component')
        _tests(rule.get('tests'))
        for key in ('paths', 'prefixes'):
            if not isinstance(rule.get(key, []), list): raise ValueError('invalid component paths')
            for path in rule.get(key, []): _path(path, prefix=key == 'prefixes')
        if not isinstance(rule.get('flags', []), list) or any(flag not in FLAGS for flag in rule.get('flags', [])):
            raise ValueError('invalid component flags')
    for path, tests in direct.items():
        _path(path, prefix=True); _tests(tests)
    for prefix, name in nearest.items():
        _path(prefix, prefix=True)
        if name not in components: raise ValueError('unknown nearest component')
    for key in ('contract_prefixes', 'install_docs'):
        if not isinstance(policy.get(key, []), list): raise ValueError('invalid category paths')
        for path in policy.get(key, []): _path(path, prefix=key == 'contract_prefixes')
    if isinstance(inventory, (str, bytes)) or not isinstance(inventory, (list, tuple, set, frozenset)):
        raise ValueError('invalid candidate inventory')
    paths = {_path(path) for path in inventory}
    available = {module for path in paths if (module := _module(path))}
    if not isinstance(changes, (list, tuple)): raise ValueError('invalid changes')
    changed = set()
    for change in changes:
        if not isinstance(change, dict) or not isinstance(change.get('status'), str): raise ValueError('invalid change')
        status = change['status']
        if not re.fullmatch(r'[AMDT]|[RC](?:\d{1,3})?', status): raise ValueError('unsupported change status')
        changed.add(_path(change.get('path')))
        if status[0] in 'RC': changed.add(_path(change.get('old_path')))
        elif 'old_path' in change: raise ValueError('old_path requires rename or copy')
    selected, chosen, unknown, reasons = set(), set(), set(), []
    flags = {name: False for name in FLAGS}
    versions = ['3.11']
    def choose_tests(tests, path, kind, component=None):
        present = sorted(set(tests) & available)
        selected.update(present)
        reasons.append({'path': path, 'kind': kind, 'component': component, 'tests': present})
        for test in sorted(set(tests) - available):
            missing = 'tests/' + test + '.py'
            unknown.add(missing)
            reasons.append({'path': missing, 'kind': 'mapped-test-absent', 'component': component, 'tests': []})
    def choose(name, path, kind):
        chosen.add(name)
        rule = components[name]
        choose_tests(rule['tests'], path, kind, name)
        for flag in rule.get('flags', []): flags[flag] = True
    def matches(path, key):
        return path.startswith(key) if key.endswith('/') else path == key
    for path in sorted(changed):
        test = _module(path)
        if test:
            choose_tests([test], path, 'direct-test')
            if path not in paths:
                for name, rule in components.items():
                    if test in rule['tests']: choose(name, path, 'removed-test-owner')
            for key, tests in direct.items():
                if matches(path, key): choose_tests(tests, path, 'direct-map')
            continue
        if path.endswith('.md') or path.startswith('docs/'):
            choose('docs', path, 'documentation')
            if path in policy.get('install_docs', []):
                flags.update(install=True, smoke=True)
                choose_tests(policy.get('install_docs_tests', []), path, 'installation-documentation')
            continue
        hits = [(len(key), name) for name, rule in components.items()
                for key in rule.get('paths', []) if path == key]
        hits.extend((len(prefix.rstrip('/')) + 1, name) for name, rule in components.items()
                    for prefix in rule.get('prefixes', []) if path.startswith(prefix.rstrip('/') + '/'))
        direct_hits = [tests for key, tests in direct.items() if matches(path, key)]
        if hits:
            longest = max(length for length, _ in hits)
            for name in sorted({name for length, name in hits if length == longest}):
                choose(name, path, 'component')
                if name == 'build': versions = ['3.11', '3.13']
        for tests in direct_hits: choose_tests(tests, path, 'direct-map')
        if not hits and not direct_hits:
            unknown.add(path)
            reasons.append({'path': path, 'kind': 'unmapped-path', 'component': None, 'tests': []})
            fallback = [(len(key.rstrip('/')), name) for key, name in nearest.items()
                        if path.startswith(key.rstrip('/') + '/')]
            if fallback: choose(max(fallback)[1], path, 'nearest-component')
            flags['smoke'] = True
        if any(path.startswith(prefix.rstrip('/') + '/') for prefix in policy.get('contract_prefixes', [])):
            flags['contracts'] = True
        self_test = 'test_' + path.rsplit('/', 1)[-1].removesuffix('.py')
        if path.endswith('.py') and self_test in available:
            choose_tests([self_test], path, 'matching-test-module')
    return {'version': 1, 'selected_tests': sorted(selected), 'components': sorted(chosen),
            'reasons': sorted(reasons, key=lambda row: (row['path'], row['kind'], row['component'] or '', row['tests'])),
            'unknown_paths': sorted(unknown), **flags, 'python_versions': versions}
