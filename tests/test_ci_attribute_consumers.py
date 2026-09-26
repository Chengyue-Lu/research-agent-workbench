"""Real checkout/Trace observations; neither a selector nor an execution receipt."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

from research_workbench.observability import trace

SOURCE = Path(__file__).resolve().parents[1]
ATTEMPT = 'work/ATTRIBUTE-PROBE/AT-0001'
METHODS = {
    'base_binary': 'test_baselines_are_hash_valid', 'base_lf': 'test_baselines_are_hash_valid',
    'whitespace': 'test_whitespace_is_byte_stable',
    'crlf': 'test_crlf_breaks_hash_and_repair_restores', 'repair': 'test_crlf_breaks_hash_and_repair_restores',
    'outside': 'test_scope_and_nested_override_controls', 'nested': 'test_scope_and_nested_override_controls',
    'missing': 'test_missing_and_renamed_refs_block', 'renamed': 'test_missing_and_renamed_refs_block',
    'unknown': 'test_unknown_attribute_stops_before_clone',
    'scale': 'test_explicit_invocation_is_stable_with_unrelated_attempts',
}


def signature(data):
    return hashlib.sha256(data).hexdigest()


def run_probe(root: Path, attempt: str = ATTEMPT, scales=(1, 10, 100)):
    """Create only our own tiny fixture under a new root; never accept a repository."""
    root = Path(root).absolute()
    relative = PurePosixPath(attempt)
    if root.exists() or relative.is_absolute() or any(p in ('.', '..') or not re.fullmatch(r'[A-Za-z0-9_.-]+', p) for p in attempt.split('/')):
        raise ValueError('probe requires a new root and a contained relative attempt path')
    if tuple(scales) not in ((), (1, 10, 100)):
        raise ValueError('only the declared 1/10/100 size controls are supported')
    if Path(trace.__file__).resolve() != SOURCE/'src/research_workbench/observability/trace.py':
        raise ValueError('trace import must belong to this source checkout')
    root.mkdir(parents=True)
    empty = root/'empty-config'; empty.write_bytes(b'')
    home = root/'isolated-home'; home.mkdir()
    template = root/'empty-template'; template.mkdir()
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=str(empty), GIT_CONFIG_SYSTEM=str(empty),
               GIT_ATTR_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0', HOME=str(home), USERPROFILE=str(home), XDG_CONFIG_HOME=str(home/'xdg'))
    report = {'status': 'PASS', 'scope': 'explicit Trace invocation observations; no exclusion authority',
              'root': str(root), 'attempt': attempt, 'observations': {}, 'commands': [], 'setup_seconds': {},
              'isolation': {'environment': {key: env[key] for key in env if key.startswith('GIT_') or key in ('HOME', 'USERPROFILE', 'XDG_CONFIG_HOME')},
                            'core.autocrlf': 'false', 'core.eol': 'lf', 'core.attributesFile': str(empty),
                            'init.templateDir': str(template), 'core.hooksPath': str(template),
                            'clone': '--no-local --no-checkout'}, 'python': sys.version}
    paths = ['tests/test_ci_attribute_consumers.py', 'src/research_workbench/observability/trace.py',
             'src/research_workbench/artifacts/integrity.py', 'src/research_workbench/validation/schemas.py',
             'src/research_workbench/io.py', 'src/research_workbench/resources.py',
             'src/research_workbench/_runtime_pin.py', 'src/research_workbench/_runtime_data/manifest.json']
    report['source_pins'] = {path: signature((SOURCE/path).read_bytes()) for path in paths}

    def git(repo, *args):
        command = ['git', '--no-replace-objects', '-c', 'core.autocrlf=false', '-c', 'core.eol=lf',
                   '-c', 'core.attributesFile='+str(empty), '-c', 'init.templateDir='+str(template),
                   '-c', 'core.hooksPath='+str(template), '-C', str(repo), *args]
        start = time.perf_counter()
        result = subprocess.run(command, env=env, capture_output=True)
        report['commands'].append({'argv': command, 'seconds': time.perf_counter()-start,
                                  'exit_code': result.returncode, 'stdout': result.stdout.decode('utf-8', 'replace'),
                                  'stderr': result.stderr.decode('utf-8', 'replace')})
        if result.returncode:
            raise RuntimeError(f'Git failed ({result.returncode}): {result.stderr.decode("utf-8", "replace")}')
        return result.stdout

    def observe(label, clone, setup_seconds=0):
        start = time.perf_counter()
        result = trace.validate_attempt_trace(clone, clone/attempt)
        duration = time.perf_counter()-start
        payload = clone/attempt/'events.jsonl'
        data = payload.read_bytes() if payload.is_file() else None
        row = {'root': str(clone), 'attempt': str(clone/attempt), 'blocked': result.blocked,
               'risks': [asdict(risk) for risk in result.risks], 'consumer_seconds': duration,
               'setup_seconds': setup_seconds, 'payload_sha256': signature(data) if data is not None else None,
               'crlf_count': data.count(b'\r\n') if data is not None else None,
               'index_sha256': signature((clone/attempt/'INDEX.yaml').read_bytes()),
               'index_git_blob': git(clone, 'rev-parse', 'HEAD:'+attempt+'/INDEX.yaml').decode().strip(),
               'payload_git_blob': git(clone, 'rev-parse', 'HEAD:'+attempt+'/events.jsonl').decode().strip(),
               'canonical_test_id': 'test_ci_attribute_consumers.AttributeConsumerTests.'+METHODS.get(label, METHODS['scale']),
               'test_id_role': 'assertion owner; this probe is not a native test execution receipt'}
        report['observations'][label] = row
        return row

    try:
        report['git_version'] = git(root, '--version').decode().strip()
        report['source_head'] = git(SOURCE, 'rev-parse', 'HEAD').decode().strip()
        seed = root/'seed'; seed.mkdir()
        git(seed, 'init', '-q', '--template='+str(template), '-b', 'probe')
        git(seed, 'config', 'user.name', 'CI attribute fixture')
        git(seed, 'config', 'user.email', 'fixture@example.invalid')
        start = time.perf_counter()
        recorder = trace.AgentTraceRecorder(seed/attempt, task_id='ATTRIBUTE-PROBE', task_revision=1,
            attempt_id='AT-0001', task_snapshot={'task_id': 'ATTRIBUTE-PROBE', 'revision': 1},
            accountable_owner='Chengyue-Lu', actor_id='attribute-probe', runtime_identity='local-fixture',
            provider='fixture', read_allowlist=('inputs/**',), write_scope=('outputs/**',),
            tool_allowlist=('read_file',), created_at='2026-09-26T00:00:00Z')
        recorder.seal('safe-paused')
        report['setup_seconds']['record_attempt'] = time.perf_counter()-start
        initial = trace.validate_attempt_trace(seed, seed/attempt)
        report['initial'] = {'blocked': initial.blocked, 'risks': [asdict(risk) for risk in initial.risks]}
        if initial.blocked:
            raise RuntimeError('generated fixture failed its real Trace validator')
        original = (seed/attempt/'events.jsonl').read_bytes()
        payload = attempt+'/events.jsonl'
        (seed/'.gitattributes').write_bytes(b'* -text\n')
        git(seed, 'add', '.'); git(seed, 'commit', '-qm', 'frozen valid Attempt')
        report['fixture_commit'] = git(seed, 'rev-parse', 'HEAD').decode().strip()
        report['fixture_blob'] = git(seed, 'rev-parse', 'HEAD:'+payload).decode().strip()
        report['fixture_index_blob'] = git(seed, 'rev-parse', 'HEAD:'+attempt+'/INDEX.yaml').decode().strip()
        report['fixture_index_sha256'] = signature((seed/attempt/'INDEX.yaml').read_bytes())
        variants = [('base_binary', '-text'), ('base_lf', 'text eol=lf'),
                    ('whitespace', 'text eol=lf whitespace=trailing-space'), ('crlf', 'text eol=crlf'), ('repair', 'text eol=lf'),
                    ('outside', 'text eol=lf'), ('nested', 'text eol=crlf'),
                    ('missing', 'text eol=lf'), ('renamed', 'text eol=lf'), ('unknown', 'text eol=lf rwb-probe=unknown')]
        variants += [('scale-'+str(size), 'text eol=lf') for size in scales]
        for label, attributes in variants:
            try:
                start = time.perf_counter()
                for extra in (seed/attempt/'.gitattributes', seed/'outside/.gitattributes'):
                    extra.unlink(missing_ok=True)
                (seed/'.gitattributes').write_text('* -text\n'+payload+' '+attributes+'\n', encoding='utf-8', newline='\n')
                if label == 'nested':
                    (seed/attempt/'.gitattributes').write_bytes(b'events.jsonl text eol=lf\n')
                if label == 'outside':
                    (seed/'outside').mkdir(exist_ok=True)
                    (seed/'outside/.gitattributes').write_bytes(b'* text eol=crlf\n')
                git(seed, 'add', '-A')
                raw = git(seed, 'check-attr', '--cached', '-z', '--all', '--', payload).decode().split('\0')[:-1]
                attrs = {raw[i+1]: raw[i+2] for i in range(0, len(raw), 3)}
                unknown = sorted(set(attrs)-{'text', 'eol', 'whitespace'})
                if unknown:
                    report['observations'][label] = {'status': 'unsupported', 'unknown_attributes': unknown,
                        'attributes': attrs, 'checkout_performed': False, 'setup_seconds': time.perf_counter()-start,
                        'canonical_test_id': 'test_ci_attribute_consumers.AttributeConsumerTests.'+METHODS['unknown']}
                    continue
                git(seed, 'commit', '--allow-empty', '-qm', label)
                clone = root/label
                git(root, 'clone', '-q', '--no-local', '--no-checkout', '-c', 'init.templateDir='+str(template), str(seed), str(clone))
                git(clone, 'checkout', '-q', 'HEAD')
                effective = git(clone, 'check-attr', '-z', '--all', '--', payload).decode().split('\0')[:-1]
                effective = {effective[i+1]: effective[i+2] for i in range(0, len(effective), 3)}
                if label.startswith('scale-'):
                    for number in range(int(label.split('-')[1])):
                        shutil.copytree(clone/attempt, clone/'unrelated'/str(number)/attempt)
                if label == 'missing':
                    (clone/payload).unlink()
                if label == 'renamed':
                    (clone/payload).rename(clone/attempt/'renamed-events.jsonl')
                row = observe(label, clone, time.perf_counter()-start)
                row['attributes'] = attrs
                row['effective_attributes'] = effective
                row['checkout_performed'] = True
            except Exception as error:
                report['status'] = 'FAIL'
                report['observations'][label] = {'error': repr(error)}
        for label, row in report['observations'].items():
            if 'error' in row:
                continue
            if label == 'unknown':
                valid = row['status'] == 'unsupported' and not row['checkout_performed']
            elif label in ('crlf', 'missing', 'renamed'):
                token = '[event-ledger-ref-hash]' if label == 'crlf' else '[event-ledger-ref-missing]'
                code = 'TRACE-HASH-MISMATCH' if label == 'crlf' else 'TRACE-EVENT-MISSING'
                blocks = [risk for risk in row['risks'] if risk['level'] == 'block']
                exact = [risk for risk in blocks if risk['code'] == code and token in risk['message']]
                valid = row['blocked'] and bool(exact) and (label != 'crlf' or len(blocks) == len(exact) == 1)
                if label != 'crlf':
                    allowed = {'[event-ledger-ref-missing]', '[event-count-drift]',
                               '[attempt-status-missing]', '[attempt-status-index-drift]'}
                    valid = valid and all(risk['code'] == code and any(risk['message'].startswith(detail) for detail in allowed) for risk in blocks)
            else:
                valid = not row['blocked'] and row['payload_sha256'] == signature(original) and row['risks'] == report['initial']['risks']
            if label != 'unknown':
                valid = valid and row['payload_git_blob'] == report['fixture_blob'] and row['index_git_blob'] == report['fixture_index_blob']
                valid = valid and row['index_sha256'] == report['fixture_index_sha256'] and row['attributes'] == row['effective_attributes']
                if label == 'crlf':
                    valid = valid and row['crlf_count'] > 0 and row['payload_sha256'] != signature(original)
                if label in ('missing', 'renamed'):
                    valid = valid and row['payload_sha256'] is None
            row['expectation_met'] = valid
            if not valid:
                report['status'] = 'FAIL'
        report['source_unchanged'] = report['source_pins'] == {path: signature((SOURCE/path).read_bytes()) for path in paths}
        if not report['source_unchanged']:
            report['status'] = 'FAIL'
    except Exception as error:
        report.update(status='FAIL', error=repr(error))
    return report


class AttributeConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.report = run_probe(Path(cls.temp.name)/'probe')
        if cls.report['status'] != 'PASS':
            print(json.dumps(cls.report, indent=2, default=str))

    def row(self, label):
        row = self.report['observations'][label]
        self.assertNotIn('error', row, row)
        self.assertTrue(row['expectation_met'], row)
        return row

    def test_baselines_are_hash_valid(self):
        self.assertEqual('PASS', self.report['status'], self.report)
        self.assertFalse(self.report['initial']['blocked'])
        for label in ('base_binary', 'base_lf'):
            self.assertFalse(self.row(label)['blocked'])

    def test_whitespace_is_byte_stable(self):
        base, candidate = self.row('base_lf'), self.row('whitespace')
        self.assertEqual(base['payload_sha256'], candidate['payload_sha256'])
        self.assertEqual(base['risks'], candidate['risks'])
        self.assertIn('whitespace', candidate['attributes'])

    def test_crlf_breaks_hash_and_repair_restores(self):
        base, broken, repaired = self.row('base_lf'), self.row('crlf'), self.row('repair')
        self.assertEqual(base['payload_git_blob'], broken['payload_git_blob'])
        self.assertEqual(base['index_sha256'], broken['index_sha256'])
        self.assertGreater(broken['crlf_count'], 0)
        self.assertNotEqual(base['payload_sha256'], broken['payload_sha256'])
        self.assertTrue(any(risk['code'] == 'TRACE-HASH-MISMATCH' for risk in broken['risks']))
        self.assertEqual(base['index_sha256'], repaired['index_sha256'])
        self.assertEqual(base['payload_sha256'], repaired['payload_sha256'])
        self.assertNotEqual(broken['root'], repaired['root'])
        self.assertEqual('lf', repaired['effective_attributes']['eol'])

    def test_scope_and_nested_override_controls(self):
        base = self.row('base_lf')
        for label in ('outside', 'nested'):
            self.assertEqual(base['payload_sha256'], self.row(label)['payload_sha256'])
            self.assertEqual(base['risks'], self.row(label)['risks'])

    def test_missing_and_renamed_refs_block(self):
        for label in ('missing', 'renamed'):
            self.assertTrue(self.row(label)['blocked'])
            self.assertIsNone(self.row(label)['payload_sha256'])

    def test_unknown_attribute_stops_before_clone(self):
        row = self.row('unknown')
        self.assertEqual(['rwb-probe'], row['unknown_attributes'])
        self.assertFalse((Path(self.report['root'])/'unknown').exists())

    def test_explicit_invocation_is_stable_with_unrelated_attempts(self):
        base = self.row('base_lf')
        for size in (1, 10, 100):
            row = self.row('scale-'+str(size))
            self.assertEqual(base['payload_sha256'], row['payload_sha256'])
            self.assertEqual(base['risks'], row['risks'])
            self.assertEqual(ATTEMPT, Path(row['attempt']).relative_to(row['root']).as_posix())

    def test_helper_refuses_existing_roots_and_escaping_attempts(self):
        for attempt in ('../escape', '/absolute', 'C:/absolute', 'work\\escape', 'work//gap'):
            with self.subTest(attempt=attempt), self.assertRaises(ValueError):
                run_probe(Path(self.temp.name)/'unused', attempt)
        with self.assertRaises(ValueError):
            run_probe(Path(self.report['root']))


if __name__ == '__main__':
    if '--probe-output' in sys.argv:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--probe-output', required=True)
        parser.add_argument('--root', required=True, type=Path)
        parser.add_argument('--attempt', default=ATTEMPT)
        args = parser.parse_args()
        try:
            result = run_probe(args.root, args.attempt)
        except Exception as error:
            result = {'status': 'FAIL', 'error': repr(error)}
        encoded = json.dumps(result, indent=2, default=str)+'\n'
        print(encoded, end='')
        if args.probe_output != '-':
            with Path(args.probe_output).open('x', encoding='utf-8') as output:
                output.write(encoded)
        raise SystemExit(0 if result['status'] == 'PASS' else 1)
    unittest.main()
