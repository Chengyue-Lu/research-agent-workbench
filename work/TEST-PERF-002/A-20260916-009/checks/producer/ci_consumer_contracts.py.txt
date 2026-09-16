"""Review records for consumer boundaries; no record authorizes CI exclusions."""
from __future__ import annotations

import ast
import hashlib
import json
import re


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(records):
    require(isinstance(records, list), 'consumer contracts must be a list')
    ids = set()
    for record in records:
        require(isinstance(record, dict) and set(record) == {
            'id', 'owner', 'consumer', 'pins', 'entrypoints', 'inputs', 'outputs',
            'invariants', 'unresolved', 'positive_tests', 'negative_tests', 'execution_authority'},
            'consumer contract shape')
        require(isinstance(record['id'], str) and re.fullmatch(r'[a-z][a-z0-9-]+', record['id'])
                and record['id'] not in ids, 'consumer contract identity')
        ids.add(record['id'])
        require(isinstance(record['owner'], str) and bool(record['owner'].strip()), 'consumer contract owner')
        require(record['execution_authority'] is False, 'consumer contracts cannot authorize execution')
        pins = record['pins']
        require(isinstance(pins, dict) and pins, 'consumer contract pins')
        for path, sha in pins.items():
            require(isinstance(path, str) and path.startswith(('src/', 'tests/', 'registry/', 'schemas/'))
                    and '\\' not in path and ':' not in path
                    and all(part not in {'', '.', '..'} for part in path.split('/')),
                    'consumer contract pin path')
            require(isinstance(sha, str) and re.fullmatch('[0-9a-f]{64}', sha), 'consumer contract pin digest')
        require(isinstance(record['consumer'], str) and record['consumer'].startswith('src/')
                and record['consumer'].endswith('.py') and record['consumer'] in pins,
                'consumer contract source pin')
        for key in ('entrypoints', 'inputs', 'outputs', 'invariants', 'unresolved', 'positive_tests', 'negative_tests'):
            values = record[key]
            require(isinstance(values, list) and values and all(isinstance(v, str) and v.strip() for v in values)
                    and len(values) == len(set(values)), 'consumer contract list: ' + key)
        require(not set(record['positive_tests']) & set(record['negative_tests']), 'consumer evidence reuse')
        for test in record['positive_tests'] + record['negative_tests']:
            require(re.fullmatch(r'test_\w+\.\w+\.test_\w+', test)
                    and 'tests/' + test.split('.')[0] + '.py' in pins, 'consumer evidence pin')


def source_observations(raw):
    """Report call syntax, including caller expressions, without resolving capabilities."""
    tree = ast.parse(raw)
    names, calls = [], []
    effects = {'run', 'Popen', 'system', 'popen', 'read', 'read_text', 'read_bytes', 'open',
               'glob', 'rglob', 'iterdir', 'write_text', 'write_bytes', 'exec', 'eval'}

    def visit(node, prefix=''):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            prefix += node.name + '.'
            names.append(prefix.rstrip('.'))
        if isinstance(node, ast.Call):
            target = ast.unparse(node.func)
            if target.rsplit('.', 1)[-1] in effects:
                calls.append({'entrypoint': prefix.rstrip('.'), 'line': node.lineno,
                              'call': ast.unparse(node), 'resolution': 'syntax-only'})
        for child in ast.iter_child_nodes(node):
            visit(child, prefix)
    visit(tree)
    return {'definitions': names, 'effect_syntax': calls}


def inspect_record(record, inventory, read):
    """Check only explicitly declared file pins and identifiers, not complete closure."""
    drift = []
    observations = {}
    for path, expected in record['pins'].items():
        if path not in inventory or inventory[path][0] != '100644':
            drift.append(path + ': missing or non-regular/non-data mode')
            continue
        raw = read(path)
        if hashlib.sha256(raw).hexdigest() != expected:
            drift.append(path + ': bytes changed')
        if path.endswith('.py'):
            try:
                observations[path] = source_observations(raw)
            except (SyntaxError, UnicodeError, ValueError):
                drift.append(path + ': unparseable source')
    source = observations.get(record['consumer'], {'definitions': [], 'effect_syntax': []})
    for name in record['entrypoints']:
        if name not in source['definitions']:
            drift.append('missing entrypoint: ' + name)
    for test in record['positive_tests'] + record['negative_tests']:
        module, _, method = test.partition('.')
        if method not in observations.get('tests/' + module + '.py', {}).get('definitions', []):
            drift.append('missing evidence identifier: ' + test)
    return {'declared_pins_match': not drift, 'drift': sorted(drift),
            'effect_syntax': source['effect_syntax'], 'evidence_executed': False,
            'complete_input_closure_proved': False, 'execution_authority': False}


def review(base_records, candidate_records, snapshots, read):
    """Candidate additions/rewrites remain proposals, even when all their pins match."""
    validate(base_records)
    validate(candidate_records)
    old = {r['id']: r for r in base_records}
    new = {r['id']: r for r in candidate_records}
    result = []
    for identity in sorted(old.keys() | new.keys()):
        accepted = old.get(identity)
        proposed = new.get(identity)
        record = accepted if accepted is not None else proposed
        status = ('candidate-proposed' if accepted is None else 'candidate-removed' if proposed is None
                  else 'candidate-revised' if proposed != accepted else 'base-recorded')
        checks = {label: inspect_record(record, snapshots[label], lambda path, label=label: read(label, path))
                  for label in ('base', 'head')}
        canonical = json.dumps(record, sort_keys=True, separators=(',', ':')).encode()
        result.append({'id': identity, 'status': status, 'record_source': 'base' if accepted is not None else 'candidate',
                       'definition_sha256': hashlib.sha256(canonical).hexdigest(), 'definition': record,
                       'checks': checks, 'execution_authority': False,
                       'activation_blockers': ['diagnostic record only', 'complete invocation/input closure unproved',
                           'independent exclusion witness not implemented', *record['unresolved']]})
    return result
