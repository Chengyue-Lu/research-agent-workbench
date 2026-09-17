"""Input facts for CI contract review. Classification never authorizes a skip."""
from pathlib import PurePosixPath

DATA = {'.json', '.jsonl', '.yaml', '.yml', '.txt', '.log', '.trace'}
SCRIPTS = {'.py', '.sh', '.bash', '.ps1', '.bat', '.cmd', '.js', '.mjs'}
PACKAGING = {'build_backend.py', 'pyproject.toml', 'runtime-resources.json', 'MANIFEST.in'}
WHITESPACE = {'blank-at-eol', 'blank-at-eof', 'space-before-tab', 'indent-with-non-tab',
              'tab-in-indent', 'trailing-space', 'cr-at-eol'}


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
