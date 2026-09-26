"""Input facts for CI contract review. Classification never authorizes a skip."""
import ast
import hashlib
import json
from pathlib import PurePosixPath

DATA = {'.json', '.jsonl', '.yaml', '.yml', '.txt', '.log', '.trace'}
SCRIPTS = {'.py', '.sh', '.bash', '.ps1', '.bat', '.cmd', '.js', '.mjs'}
PACKAGING = {'build_backend.py', 'pyproject.toml', 'runtime-resources.json', 'MANIFEST.in'}
WHITESPACE = {'blank-at-eol', 'blank-at-eof', 'space-before-tab', 'indent-with-non-tab',
              'tab-in-indent', 'trailing-space', 'cr-at-eol'}

PROCESS_CALLS = {'subprocess.' + name for name in ('run', 'check_output', 'check_call', 'call', 'Popen')}
PATH_READS = {'pathlib.Path.' + name for name in ('read_text', 'read_bytes', 'open')}
PATH_MEMBERS = {'pathlib.Path.' + name for name in ('glob', 'rglob', 'iterdir')}
PATH_WRITES = {'pathlib.Path.' + name for name in ('write_text', 'write_bytes')}


def _ast_sha(node):
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode('utf-8')).hexdigest()


def _expression(node, *, private=False):
    """Describe syntax without evaluating it; private payloads retain only shape/hash."""
    if node is None:
        return {'kind': 'missing'}
    if private:
        return {'kind': 'expression', 'node': type(node).__name__, 'ast_sha256': _ast_sha(node)}
    if isinstance(node, ast.Constant) and type(node.value) in (str, int, float, bool, type(None)):
        # Non-finite floats cannot originate from a numeric literal in parsed Python.
        if isinstance(node.value, float) and not (-float('inf') < node.value < float('inf')):
            return _expression(node, private=True)
        return {'kind': 'literal', 'value': node.value}
    return {'kind': 'expression', 'node': type(node).__name__, 'ast_sha256': _ast_sha(node)}


def _argv_shape(node):
    """Retain token positions and identity without publishing argument payloads."""
    if isinstance(node, (ast.List, ast.Tuple)):
        return {'kind': 'sequence', 'ast_sha256': _ast_sha(node),
                'items': [{'position': index, **_expression(item, private=True)}
                          for index, item in enumerate(node.elts)]}
    return _expression(node, private=True)


def _argument(call, name, position=None):
    values = [item.value for item in call.keywords if item.arg == name]
    if values:
        return values[0]
    return call.args[position] if position is not None and len(call.args) > position else None


def _fixed_strings(node):
    if isinstance(node, (ast.List, ast.Tuple)) and node.elts and all(
            isinstance(item, ast.Constant) and type(item.value) is str for item in node.elts):
        return [item.value for item in node.elts]
    return None


def _process_operation(argv, facts):
    """Recognize a bounded command shape, not its executable or materialized inputs."""
    fixed = _fixed_strings(argv)
    if fixed is None:
        facts['unresolved'].append('dynamic-argv')
        return
    facts['resolution']['target_shape'] = 'known'
    facts['inputs'].append({'role': 'executable-name', 'argv_index': 0})
    name = fixed[0].replace('\\', '/').rsplit('/', 1)[-1]
    facts['unresolved'].append('external-executable-identity')
    if name in {'git', 'git.exe'}:
        facts['unresolved'].extend(['git-configuration', 'git-ref-and-worktree-state'])
        index = 1
        while index < len(fixed) and fixed[index] in {'-C', '-c', '--git-dir', '--work-tree'}:
            index += 2
        if index >= len(fixed) or fixed[index].startswith('-'):
            facts['unresolved'].append('unsupported-git-options')
            return
        command, arguments = fixed[index], fixed[index + 1:]
        operations = {
            'rev-parse': ('git-identity', ['identity']),
            'show': ('git-content', ['content', 'identity']),
            'ls-tree': ('git-membership', ['membership', 'identity']),
            'ls-files': ('git-membership', ['membership']),
            'merge-tree': ('git-merge', ['content', 'membership', 'identity']),
        }
        if command not in operations:
            facts['unresolved'].append('unsupported-git-operation')
            return
        facts['inputs'].append({'role': 'git-command', 'name': command, 'argv_index': index})
        facts['inputs'].append({'role': 'git-arguments', 'argv_start': index + 1, 'count': len(arguments)})
        facts['operation'], dimensions = operations[command]
        facts['dimensions'].extend(dimensions)
        if command == 'ls-tree':
            # A names-only listing still depends on a tree identity, but its output
            # does not expose each member's blob identity as the default form does.
            facts['outputs'].append({'role': 'tree-entry-names' if '--name-only' in arguments
                                     else 'tree-entry-identities'})
        if command == 'show':
            facts['unresolved'].append('git-show-format-and-object-kind')
        if command == 'ls-files':
            facts['unresolved'].append('git-index-and-untracked-membership')
        if command == 'merge-tree':
            facts['unresolved'].append('git-attributes-and-merge-drivers')
    elif name in {'python', 'python.exe', 'python3', 'python3.11', 'python3.13'}:
        facts['unresolved'].extend(['python-startup-and-environment', 'python-import-closure'])
        if len(fixed) >= 3 and fixed[1] == '-m':
            facts['operation'] = 'python-module'
            facts['inputs'].append({'role': 'module-name', 'argv_index': 2})
        elif len(fixed) >= 3 and fixed[1] == '-c':
            facts['operation'] = 'python-inline'
            facts['inputs'].append({'role': 'inline-source', 'argv_index': 2, 'sha256': hashlib.sha256(
                fixed[2].encode('utf-8')).hexdigest()})
            facts['unresolved'].append('inline-execution-closure')
        elif len(fixed) >= 2 and not fixed[1].startswith('-'):
            facts['operation'] = 'python-script'
            facts['inputs'].append({'role': 'script-path', 'argv_index': 1})
        else:
            facts['unresolved'].append('unsupported-python-options')
        facts['dimensions'].append('content')


def describe_invocation(consumer, raw, call, *, callee, binding, scope=''):
    """Classify one parser-supplied callsite without resolving or executing inputs.

    The caller must supply the call and binding from its fresh/cached source
    analysis. A proven import is a lexical observation, not proof against runtime
    monkeypatching or proof of a complete input closure. This API never selects
    tests, removes fallback edges, or grants execution authority.
    """
    if (not isinstance(consumer, str) or not consumer or consumer.startswith('/') or '\\' in consumer
            or ':' in consumer or any(part in {'', '.', '..'} for part in consumer.split('/'))):
        raise ValueError('unsafe consumer path')
    if not isinstance(raw, bytes) or not isinstance(call, ast.Call) or not isinstance(scope, str):
        raise ValueError('invalid invocation source or call')
    if binding not in {'proven-import', 'unresolved', 'escaped'} or not (
            callee is None or isinstance(callee, str) and callee):
        raise ValueError('invalid invocation binding')
    span = [getattr(call, name, None) for name in ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')]
    if (any(type(value) is not int for value in span) or span[0] < 1 or span[1] < 0
            or (span[2], span[3]) <= (span[0], span[1])):
        raise ValueError('callsite has no valid source span')
    argv = _argument(call, 'args', 0)
    cwd, env = _argument(call, 'cwd'), _argument(call, 'env')
    shell, stdin = _argument(call, 'shell'), _argument(call, 'stdin')
    input_value = _argument(call, 'input')
    executable = _argument(call, 'executable')
    result = {
        'schema_version': 1, 'consumer': consumer, 'source_sha256': hashlib.sha256(raw).hexdigest(),
        'callsite': {'scope': scope, 'span': span, 'ast_sha256': _ast_sha(call)},
        'callee': {'resolved': callee, 'binding': binding}, 'operation': 'unknown', 'dimensions': [],
        'invocation': {'argv': _argv_shape(argv), 'cwd': _expression(cwd),
                       'env': _expression(env, private=True), 'shell': _expression(shell),
                       'stdin': _expression(stdin, private=True), 'input': _expression(input_value, private=True),
                       'executable': _expression(executable, private=True)},
        'inputs': [], 'outputs': [],
        'resolution': {'target_shape': 'unknown', 'input_closure': 'unproved'},
        'unresolved': ['input-closure-unproved'], 'execution_authority': False,
    }
    if any(item.arg is None for item in call.keywords):
        result['unresolved'].append('dynamic-keywords')
    if any(isinstance(item, ast.Starred) for item in call.args):
        result['unresolved'].append('dynamic-positional-arguments')
    if binding != 'proven-import':
        result['unresolved'].append('callable-escape' if binding == 'escaped' else 'untrusted-callee-binding')
    elif callee in PROCESS_CALLS:
        result['operation'] = 'subprocess'
        result['dimensions'] = ['execution', 'output']
        result['outputs'].append({'role': 'process-result'})
        result['unresolved'].extend(['runtime-binding-unproved', 'ambient-environment' if env is None or
            isinstance(env, ast.Constant) and env.value is None else 'explicit-environment-unproved',
            'inherited-cwd' if cwd is None else 'explicit-cwd-unproved'])
        if executable is not None:
            result['unresolved'].append('explicit-executable-override')
        if len(call.args) > 1:
            # Popen's later positional parameters can replace executable, shell,
            # cwd, env and streams. Do not guess those version-specific signatures.
            result['unresolved'].append('unsupported-positional-process-options')
        supported = {'args', 'cwd', 'env', 'shell', 'stdin', 'input', 'executable', 'stdout', 'stderr',
                     'capture_output', 'check', 'encoding', 'errors', 'text', 'universal_newlines', 'timeout'}
        if any(item.arg is not None and item.arg not in supported for item in call.keywords):
            result['unresolved'].append('unsupported-process-options')
        shell_false = shell is None or isinstance(shell, ast.Constant) and shell.value is False
        overrides = {'dynamic-keywords', 'dynamic-positional-arguments',
                     'explicit-executable-override', 'unsupported-positional-process-options',
                     'unsupported-process-options'}
        if shell_false and not overrides & set(result['unresolved']):
            _process_operation(argv, result)
        elif not shell_false:
            result['unresolved'].append('shell-execution' if isinstance(shell, ast.Constant) and
                                         shell.value is True else 'unknown-shell')
            result['resolution']['target_shape'] = 'unknown'
        if stdin is not None or input_value is not None:
            result['inputs'].append({'role': 'process-input'})
            result['dimensions'].append('content')
    elif callee in {'os.system', 'os.popen'}:
        result['operation'], result['dimensions'] = 'shell', ['execution', 'content']
        result['unresolved'].extend(['shell-execution', 'ambient-environment', 'inherited-cwd'])
    elif callee in {'runpy.run_module', 'runpy.run_path', 'importlib.import_module', 'builtins.__import__'}:
        result['operation'] = 'python-script' if callee == 'runpy.run_path' else 'python-module'
        result['dimensions'] = ['execution', 'content']
        result['inputs'].append({'role': 'python-target', 'expression': _expression(argv, private=True)})
        result['resolution']['target_shape'] = 'known' if isinstance(argv, ast.Constant) and type(argv.value) is str else 'unknown'
        result['unresolved'].extend(['python-import-closure', 'python-startup-and-environment', 'runtime-binding-unproved'])
    elif callee in {'builtins.exec', 'builtins.eval', 'builtins.compile'}:
        result['operation'], result['dimensions'] = 'python-inline', ['execution', 'content']
        result['unresolved'].extend(['inline-execution-closure', 'runtime-binding-unproved'])
    elif callee in PATH_READS | PATH_MEMBERS | PATH_WRITES | {'builtins.open'}:
        operation, dimensions = ('resource-membership', ['membership']) if callee in PATH_MEMBERS else (
            ('resource-output', ['output']) if callee in PATH_WRITES else ('resource-content', ['content']))
        if callee in {'builtins.open', 'pathlib.Path.open'}:
            # Open modes and later reads/writes require dataflow; do not infer read-only.
            operation, dimensions = 'resource-open', ['content', 'output']
        result['operation'], result['dimensions'] = operation, dimensions
        result['unresolved'].extend(['resource-path-and-symlink-resolution', 'runtime-binding-unproved'])
        result['inputs'].append({'role': 'resource-expression', 'ast_sha256': _ast_sha(call)})
        if 'output' in dimensions:
            result['outputs'].append({'role': 'resource-write'})
    else:
        result['unresolved'].append('unsupported-call-target')
    if {'dynamic-keywords', 'dynamic-positional-arguments'} & set(result['unresolved']):
        result['resolution']['target_shape'] = 'unknown'
    result['dimensions'] = sorted(set(result['dimensions']))
    result['unresolved'] = sorted(set(result['unresolved']))
    return result


def verify_invocation(record, consumer, raw, call, *, callee, binding, scope=''):
    """Reject every report-field drift against freshly supplied parser facts."""
    expected = describe_invocation(consumer, raw, call, callee=callee, binding=binding, scope=scope)
    try:
        actual_json = json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (ValueError, TypeError) as error:
        raise ValueError('invalid invocation record') from error
    if actual_json != json.dumps(expected, sort_keys=True, separators=(',', ':'), allow_nan=False):
        raise ValueError('invocation record differs from recomputed source facts')


def archive_attributes(raw):
    """Recognize scoped text/whitespace rules; preserve order, reject other semantics.

    This is a deliberately bounded grammar, not a replacement for Git's attribute
    evaluator. Macros, quoting, escape syntax and additional attributes stay unknown.
    """
    try:
        lines = raw.decode('utf-8').splitlines()
    except UnicodeError:
        return None
    rules = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        pattern, *attributes = parts
        if (not attributes or pattern.startswith(('/', '!', '[', '"', '\ufeff'))
                or '\\' in pattern or ':' in pattern or '"' in pattern
                or any(p in {'', '.', '..'} for p in pattern.split('/'))):
            return None
        seen = set()
        for attribute in attributes:
            name = attribute.split('=', 1)[0].lstrip('-')
            valid = attribute in {'text', '-text', 'text=auto', 'eol=lf', 'eol=crlf'}
            if attribute.startswith('whitespace='):
                flags = attribute.split('=', 1)[1].split(',')
                valid = all(flag.removeprefix('-') in WHITESPACE for flag in flags)
            if not valid or name in seen:
                return None
            seen.add(name)
        rules.append({'pattern': pattern, 'attributes': attributes})
    return rules


def describe(path, versions, *, selection_authority, coverage_authority, policy_path):
    """Keep directory purpose, executable facts and concurrent authority dimensions."""
    if not versions:
        raise ValueError('input has no Git version')
    if (not path or path.startswith('/') or '\\' in path or ':' in path
            or any(p in {'', '.', '..'} for p in path.split('/'))):
        raise ValueError('unsafe input path')
    archive = path.startswith('work/') or path.startswith('docs/workstreams/') and '/attempts/' in path
    domain = ('test' if path.startswith('tests/') else
              'runtime' if path.startswith(('schemas/', 'registry/', 'examples/', '.agents/skills/', 'src/')) else
              'archive' if archive else 'document' if path.endswith('.md') else 'repository')
    authorities = set()
    if path in selection_authority or path.startswith('.github/workflows/'):
        authorities.add('selection')
    if path in coverage_authority or path.startswith('.github/workflows/'):
        authorities.add('coverage')
    if path == policy_path:
        authorities.add('selection-policy')
    if path in PACKAGING:
        authorities.add('packaging')
    if path.startswith('.github/') or path == '.gitattributes':
        authorities.add('repository')
    modes = {mode for mode, _ in versions}
    executable = '100755' in modes or PurePosixPath(path).suffix in SCRIPTS or any(
        raw.startswith(b'#!') for _, raw in versions)
    facts = {'domain': domain, 'authorities': sorted(authorities), 'executable': executable,
             'attribute_rules': [], 'unresolved': [], 'execution_authority': False}
    role, reason = 'unknown', 'no supported input category'
    if not modes <= {'100644', '100755'} or len(modes) > 1:
        facts['executable'] = None
        reason = 'Git type/mode boundary requires review'
    elif authorities:
        display = next(name for name in ('selection', 'selection-policy', 'packaging', 'coverage', 'repository')
                       if name in authorities)
        role = 'selection-policy-metadata' if display == 'selection-policy' else display + '-authority'
        reason = 'all authority dimensions retained; display role does not choose obligations'
    elif executable:
        role = 'test-code' if domain == 'test' else 'executable'
        reason = 'executable bytes/mode retained independently of directory purpose'
    elif domain == 'runtime':
        role, reason = 'runtime-input', 'schema/registry/Skill/package input requires consumer closure'
    elif domain == 'test':
        role, reason = 'test-input', 'fixture data requires test consumer closure'
    elif archive and PurePosixPath(path).name == '.gitattributes':
        rules = [archive_attributes(raw) for _, raw in versions]
        if all(value is not None for value in rules):
            facts['attribute_rules'] = rules
            role, reason = 'archive-attributes', 'scoped text/whitespace rules; consumer closure still required'
        else:
            reason = 'archive attributes have unsupported syntax or additional Git semantics'
    elif archive and PurePosixPath(path).suffix in DATA:
        role, reason = 'evidence-data', 'archive data instance; content/hash validation and real readers still required'
    elif path.endswith('.md'):
        role, reason = 'document', 'document bytes; actual runtime readers still required'
    if role == 'unknown':
        facts['unresolved'].append(reason)
    return {'role': role, 'reason': reason, **facts}
