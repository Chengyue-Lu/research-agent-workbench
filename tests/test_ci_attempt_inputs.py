"""Fresh-process observations of real Attempt inputs; no CI exclusion authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

from research_workbench.observability import trace


SOURCE = Path(__file__).resolve().parents[1]
PACKAGE = SOURCE / 'src/research_workbench'
ATTEMPT = Path('work/INPUT-PROBE/AT-0001')
OWNER = 'test_ci_attempt_inputs.AttemptInputTests.'
METHODS = {
    'directory': 'test_directory_and_index_entrypoints_agree',
    'index': 'test_directory_and_index_entrypoints_agree',
    'message_orphan': 'test_top_level_message_membership_is_checked',
    'tool_orphan': 'test_nested_tool_result_membership_is_checked',
    'deleted_ref': 'test_deleted_reference_is_blocked',
    'renamed_ref': 'test_renamed_reference_is_blocked',
    'outside_ref': 'test_reference_outside_attempt_is_blocked',
    'sibling': 'test_unrelated_sibling_keeps_explicit_result',
    'runtime_orphan': 'test_unlisted_runtime_member_and_repair',
    'schema_drift': 'test_non_trace_schema_bytes_and_repair',
    'resource_drift': 'test_non_schema_resource_bytes_and_repair',
    'transcript': 'test_alternative_consumer_has_distinct_inputs',
    'transcript_schema_drift': 'test_alternative_consumer_has_distinct_inputs',
}

# Observation starts before importing the copied workbench. Python bootstrap and
# native/OS operations without these audit events remain outside this observation.
CHILD = r'''
import hashlib,json,os,sys,time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
config=json.loads(sys.argv[1])
sys.path.insert(0,config['site'])
phase='import'
events=Counter()
audit_errors=[]
def audit(event,args):
    if phase not in ('import','reader') or event not in ('open','os.scandir','os.listdir'):
        return
    try:
        raw=args[0]
        path=os.path.abspath(os.fsdecode(raw)) if isinstance(raw,(str,bytes,os.PathLike)) else 'fd:'+str(raw)
        mode=str(args[1]) if event=='open' and len(args)>1 else ''
        events[(phase,event,path,mode)]+=1
    except Exception as error:
        audit_errors.append(type(error).__name__+': '+str(error))
sys.addaudithook(audit)
started=None
module=None
try:
    from research_workbench.observability import trace
    module=str(Path(trace.__file__).resolve())
    expected=Path(config['site'])/'research_workbench/observability/trace.py'
    if Path(module)!=expected.resolve():
        raise ValueError('reader was not imported from the declared package copy')
    phase='reader'
    started=time.perf_counter()
    if config['entrypoint']=='derive_session_transcript':
        value=trace.derive_session_transcript(config['attempt'])
        outcome={'kind':'transcript','value':value}
    else:
        value=trace.validate_attempt_trace(config['root'],config['attempt'])
        outcome={'kind':'trace','blocked':value.blocked,'risks':[asdict(r) for r in value.risks]}
except Exception as error:
    outcome={'kind':'exception','type':type(error).__module__+'.'+type(error).__name__,
             'message':str(error),'phase':phase}
finally:
    reader_seconds=time.perf_counter()-started if started is not None else None
phase='closed'
from importlib.metadata import version
imported_modules={name:str(Path(value.__file__).resolve()) for name,value in list(sys.modules.items())
                  if (name=='research_workbench' or name.startswith('research_workbench.'))
                  and getattr(value,'__file__',None)}
report={'outcome':outcome,'reader_seconds':reader_seconds,'module':module,
        'module_sha256':hashlib.sha256(Path(module).read_bytes()).hexdigest() if module else None,
        'imported_modules':{name:{'path':path,'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
                            for name,path in imported_modules.items()},
        'python':sys.version,'executable':sys.executable,'isolated':sys.flags.isolated,
        'cwd':os.getcwd(),'dependencies':{name:version(name) for name in ('PyYAML','jsonschema','referencing')},
        'audit_errors':audit_errors,
        'observed_operations':[dict(phase=p,event=e,path=f,mode=m,count=n)
                               for (p,e,f,m),n in sorted(events.items())]}
print(json.dumps(report,sort_keys=True))
sys.exit(3 if outcome['kind']=='exception' else 0)
'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    """Materialized inventory, including empty directories; not a read receipt."""
    rows = []
    for path in sorted(root.rglob('*')):
        if '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        if path.is_symlink():
            raise ValueError('fixture/package inventory does not accept symlinks')
        row = {'path': path.relative_to(root).as_posix(), 'kind': 'directory' if path.is_dir() else 'file'}
        if path.is_file():
            raw = path.read_bytes()
            row.update(size=len(raw), sha256=digest(raw))
        rows.append(row)
    return rows


def run_probe(root: Path):
    """Build a new tiny fixture and package copies; never accept an existing root."""
    root = Path(root).absolute()
    if root.exists() or root.is_symlink():
        raise ValueError('probe root must be new')
    if Path(trace.__file__).resolve() != (PACKAGE/'observability/trace.py').resolve():
        raise ValueError('fixture recorder must belong to this source checkout')
    root.mkdir(parents=True)
    started = time.perf_counter()
    report = {'status': 'FAIL', 'report_kind': 'attempt-input-observations', 'schema_version': 1,
              'execution_authority': False, 'complete_input_closure_proved': False,
              'scope': 'explicit real invocations; observed operations are not safe-exclusion evidence',
              'root': str(root), 'observations': {}, 'package_copies': {}, 'errors': [],
              'limits': ['audit covers Python open/scandir/listdir after interpreter bootstrap only',
                         'audit records attempted operations before success; absence is not closure proof',
                         'materialized inventories are snapshots, not proof that all files were read',
                         'fresh subprocess reader timings include audit overhead; no hosted speedup claim',
                         'test identifiers name assertion owners, not native execution receipts']}
    source_files = inventory(PACKAGE)
    probe_hash = digest(Path(__file__).read_bytes())
    manifest = json.loads((PACKAGE/'_runtime_data/manifest.json').read_bytes())
    report['source'] = {'package': str(PACKAGE), 'package_inventory': source_files,
                        'probe_sha256': probe_hash, 'runtime_manifest': manifest,
                        'python': sys.version, 'executable': sys.executable,
                        'git_tree_proof': False, 'basis': 'actual source and generated package bytes'}
    env = {k: v for k, v in os.environ.items() if not k.startswith(('PYTHON', 'COVERAGE_', 'GIT_'))}
    env['GIT_OPTIONAL_LOCKS'] = '0'
    source_run = subprocess.run(['git', '--no-replace-objects', '-C', str(SOURCE), 'rev-parse', 'HEAD'],
                                capture_output=True, env=env, check=True)
    report['source']['git_head'] = source_run.stdout.decode().strip()

    def package_copy(name):
        start = time.perf_counter()
        site = root/'packages'/name
        shutil.copytree(PACKAGE, site/'research_workbench', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        actual = inventory(site/'research_workbench')
        if actual != source_files:
            raise ValueError('package copy differs from observed source')
        report['package_copies'][name] = {'site': str(site), 'setup_seconds': time.perf_counter()-start,
                                        'source_equal_before_fault': True}
        return site

    def scenario(label, site, mutate=None, entrypoint='validate_attempt_trace', index=False):
        setup = time.perf_counter()
        case_root = root/'cases'/label
        attempt = case_root/ATTEMPT
        shutil.copytree(seed, attempt)
        if mutate:
            mutate(case_root, attempt)
        attempt_before = inventory(attempt)
        package_before = inventory(site/'research_workbench')
        row = {'root': str(case_root), 'attempt': str(attempt), 'entrypoint': entrypoint,
               'argument': str(attempt/'INDEX.yaml' if index else attempt),
               'attempt_inventory': attempt_before,
               'runtime_inventory': inventory(site/'research_workbench/_runtime_data'),
               'runtime_manifest_sha256': digest((site/'research_workbench/_runtime_data/manifest.json').read_bytes()),
               'index_sha256': digest((attempt/'INDEX.yaml').read_bytes()),
               'canonical_test_id': OWNER+METHODS[label.removesuffix('_repair')],
               'test_id_role': 'assertion owner; not a native receipt',
               'setup_seconds': time.perf_counter()-setup}
        config = {'site': str(site), 'root': str(case_root), 'attempt': row['argument'], 'entrypoint': entrypoint}
        command = [sys.executable, '-I', '-X', 'utf8', '-B', '-c', CHILD, json.dumps(config)]
        start = time.perf_counter()
        process = subprocess.run(command, cwd=case_root, env=env, capture_output=True, timeout=60)
        row.update(child_wall_seconds=time.perf_counter()-start, command=command,
                   exit_code=process.returncode, stderr=process.stderr.decode('utf-8', 'replace'))
        if process.returncode not in (0, 3):
            raise RuntimeError('child observer failed: '+row['stderr'])
        row['reader'] = json.loads(process.stdout)
        if row['reader']['audit_errors'] or row['reader']['isolated'] != 1:
            raise ValueError('audit observation or process isolation failed')
        if row['reader']['module_sha256'] != digest((PACKAGE/'observability/trace.py').read_bytes()):
            raise ValueError('actual reader source differs')
        for imported in row['reader']['imported_modules'].values():
            relative = Path(imported['path']).relative_to(site/'research_workbench')
            if imported['sha256'] != digest((PACKAGE/relative).read_bytes()):
                raise ValueError('imported workbench module differs from declared source')
        if package_before != inventory(site/'research_workbench') or attempt_before != inventory(attempt):
            raise ValueError('reader changed observed materialized inputs')
        row['inputs_unchanged_by_reader'] = True
        report['observations'][label] = row
        return row

    try:
        seed = root/'seed'/ATTEMPT
        recorder = trace.AgentTraceRecorder(seed, task_id='INPUT-PROBE', task_revision=1, attempt_id='AT-0001',
            task_snapshot={'task_id': 'INPUT-PROBE', 'revision': 1}, accountable_owner='Chengyue-Lu',
            actor_id='input-probe', runtime_identity='local-fixture', provider='fixture',
            read_allowlist=('inputs/**',), write_scope=('outputs/**',), tool_allowlist=('read_file',),
            created_at='2026-09-26T00:00:00Z')
        recorder.record('provider-request', {'request': {'model': 'fixture', 'input': 'bounded question'}})
        recorder.record('provider-response', {'response': {'text': 'bounded response'}})
        recorder.record_tool_call(operation_id='observed-result', tool_name='read_file', status='delivered',
            arguments={'path': 'inputs/a.txt'}, result='bounded content', result_entered_context=True)
        decision = recorder.record_decision_snapshot('bounded-input', {'purpose': 'input-boundary fixture'})
        recorder.seal('safe-paused')
        report['fixture'] = {'attempt_inventory': inventory(seed), 'decision_ref': dict(decision),
                             'index_sha256': digest((seed/'INDEX.yaml').read_bytes())}
        site = package_copy('baseline')
        scenario('directory', site)
        scenario('index', site, index=True)
        scenario('transcript', site, entrypoint='derive_session_transcript')
        scenario('message_orphan', site, lambda r, a: (a/'messages/orphan.trace').write_bytes(b'orphan\n'))

        def orphan_tool(r, a):
            path = a/'tool-events/nested/orphan.json'
            path.parent.mkdir()
            path.write_bytes(b'{"orphan":true}\n')
        scenario('tool_orphan', site, orphan_tool)
        scenario('deleted_ref', site, lambda r, a: (a/decision['path']).unlink())
        scenario('renamed_ref', site, lambda r, a: (a/decision['path']).rename(a/'decisions/renamed.yaml'))

        def outside_ref(r, a):
            import yaml
            original = a/decision['path']
            (a.parent/'outside.yaml').write_bytes(original.read_bytes())
            index_path = a/'INDEX.yaml'
            index_value = yaml.safe_load(index_path.read_bytes())
            index_value['decision_refs'][0]['path'] = '../outside.yaml'
            index_path.write_text(yaml.safe_dump(index_value, sort_keys=False), encoding='utf-8', newline='\n')
        scenario('outside_ref', site, outside_ref)

        def sibling(r, a):
            path = r/'work/UNRELATED/invalid.json'
            path.parent.mkdir(parents=True)
            path.write_bytes(b'not valid JSON\n')
        scenario('sibling', site, sibling)
        schema_entry = next(e for e in manifest['entries'] if e['kind'] == 'schema'
                            and not Path(e['logical_path']).name.startswith('agent-trace-'))
        resource_entry = next(e for e in manifest['entries'] if e['kind'] != 'schema')
        report['runtime_fault_subjects'] = {'schema_drift': schema_entry, 'resource_drift': resource_entry}
        for label, entry in (('runtime_orphan', None), ('schema_drift', schema_entry), ('resource_drift', resource_entry)):
            fault_site = package_copy(label)
            runtime = fault_site/'research_workbench/_runtime_data'
            path = runtime/(entry['installed_path'] if entry else 'unlisted.bin')
            original = path.read_bytes() if entry else None
            path.write_bytes(original+b'\ninput-probe drift\n' if original is not None else b'unlisted\n')
            scenario(label, fault_site)
            if label == 'schema_drift':
                scenario('transcript_schema_drift', fault_site, entrypoint='derive_session_transcript')
            if original is None:
                path.unlink()
            else:
                path.write_bytes(original)
            scenario(label+'_repair', fault_site)

        expected_faults = {'message_orphan': [('TRACE-MESSAGE-MISSING', '[message-unindexed]')],
                           'tool_orphan': [('TRACE-TRANSIENT-RESULT-MISSING', '[tool-result-unindexed]')],
                           'deleted_ref': [('TRACE-EVENT-MISSING', '[decision_refs-ref-missing]')],
                           'renamed_ref': [('TRACE-EVENT-MISSING', '[decision_refs-ref-missing]')],
                           'outside_ref': [('TRACE-EVENT-MISSING', '[index-schema-invalid]'),
                                           ('TRACE-EVENT-MISSING', '[decision_refs-ref-path-escape]')]}
        required = set(METHODS) | {name+'_repair' for name in ('runtime_orphan','schema_drift','resource_drift')}
        if set(report['observations']) != required:
            raise ValueError('missing or unexpected observation')
        baseline = report['observations']['directory']['reader']['outcome']
        transcript = report['observations']['transcript']['reader']['outcome']
        for label, row in report['observations'].items():
            outcome = row['reader']['outcome']
            if label in expected_faults:
                expected = expected_faults[label]
                blocks = [r for r in outcome.get('risks', []) if r['level'] == 'block']
                actual = sorted((r['code'], r['message'].split(']', 1)[0]+']') for r in blocks)
                valid = outcome.get('kind') == 'trace' and outcome['blocked'] and actual == sorted(expected)
            elif label in ('runtime_orphan', 'schema_drift', 'resource_drift'):
                message = 'Runtime resource file closure mismatch' if label == 'runtime_orphan' else 'Runtime resource byte/hash drift'
                valid = outcome == {'kind': 'exception', 'type': 'research_workbench.resources.ResourceError',
                                    'message': message, 'phase': 'reader'} and row['exit_code'] == 3
            elif label.startswith('transcript'):
                valid = outcome.get('kind') == 'transcript' and bool(outcome['value']) and outcome == transcript
            else:
                valid = outcome.get('kind') == 'trace' and not outcome['blocked'] and outcome == baseline
            if label != 'outside_ref':
                valid = valid and row['index_sha256'] == report['fixture']['index_sha256']
            valid = valid and row['runtime_manifest_sha256'] == digest((PACKAGE/'_runtime_data/manifest.json').read_bytes())
            row['expectation_met'] = bool(valid)
            if not valid:
                report['errors'].append(label+': expected real consumer outcome was not obtained')
        report['source_unchanged'] = inventory(PACKAGE) == source_files and digest(Path(__file__).read_bytes()) == probe_hash
        if not report['source_unchanged']:
            raise ValueError('source changed during observations')
        report['status'] = 'PASS' if not report['errors'] else 'FAIL'
    except Exception as error:
        report['infrastructure_error'] = type(error).__name__+': '+str(error)
        report['errors'].append(report['infrastructure_error'])
    report['wall_seconds'] = time.perf_counter()-started
    return report


class AttemptInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.report = run_probe(Path(cls.temp.name)/'probe')
        if 'infrastructure_error' in cls.report:
            raise AssertionError(cls.report['infrastructure_error'])

    def row(self, label):
        row = self.report['observations'][label]
        self.assertTrue(row['expectation_met'], row['reader']['outcome'])
        return row

    def test_directory_and_index_entrypoints_agree(self):
        self.assertEqual(self.row('directory')['reader']['outcome'], self.row('index')['reader']['outcome'])

    def test_top_level_message_membership_is_checked(self):
        self.assertTrue(self.row('message_orphan')['reader']['outcome']['blocked'])

    def test_nested_tool_result_membership_is_checked(self):
        self.assertTrue(self.row('tool_orphan')['reader']['outcome']['blocked'])

    def test_deleted_reference_is_blocked(self):
        self.assertTrue(self.row('deleted_ref')['reader']['outcome']['blocked'])

    def test_renamed_reference_is_blocked(self):
        self.assertTrue(self.row('renamed_ref')['reader']['outcome']['blocked'])

    def test_reference_outside_attempt_is_blocked(self):
        self.assertNotEqual(self.report['fixture']['index_sha256'], self.row('outside_ref')['index_sha256'])

    def test_unrelated_sibling_keeps_explicit_result(self):
        self.assertEqual(self.row('directory')['attempt_inventory'], self.row('sibling')['attempt_inventory'])

    def test_unlisted_runtime_member_and_repair(self):
        self.assertEqual('exception', self.row('runtime_orphan')['reader']['outcome']['kind'])
        self.assertEqual(self.row('directory')['runtime_inventory'], self.row('runtime_orphan_repair')['runtime_inventory'])

    def test_non_trace_schema_bytes_and_repair(self):
        self.assertEqual('schema', self.report['runtime_fault_subjects']['schema_drift']['kind'])
        self.assertEqual('exception', self.row('schema_drift')['reader']['outcome']['kind'])
        self.assertEqual(self.row('directory')['runtime_inventory'], self.row('schema_drift_repair')['runtime_inventory'])

    def test_non_schema_resource_bytes_and_repair(self):
        self.assertNotEqual('schema', self.report['runtime_fault_subjects']['resource_drift']['kind'])
        self.assertEqual('exception', self.row('resource_drift')['reader']['outcome']['kind'])
        self.assertEqual(self.row('directory')['runtime_inventory'], self.row('resource_drift_repair')['runtime_inventory'])

    def test_alternative_consumer_has_distinct_inputs(self):
        self.assertEqual(self.row('transcript')['reader']['outcome'], self.row('transcript_schema_drift')['reader']['outcome'])
        self.assertEqual('exception', self.row('schema_drift')['reader']['outcome']['kind'])

    def test_observations_are_scoped_and_existing_roots_are_refused(self):
        self.assertEqual('PASS', self.report['status'], self.report['errors'])
        row = self.row('directory')
        observed = row['reader']['observed_operations']
        self.assertTrue(any(r['event'] == 'open' and r['phase'] == 'reader' and r['path'].endswith('events.jsonl') for r in observed))
        self.assertTrue(any(r['event'] == 'os.scandir' and r['phase'] == 'reader' for r in observed))
        self.assertFalse(self.report['execution_authority'])
        self.assertFalse(self.report['complete_input_closure_proved'])
        with self.assertRaises(ValueError):
            run_probe(Path(self.report['root']))


if __name__ == '__main__':
    if '--probe-output' in sys.argv:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--root', type=Path, required=True)
        parser.add_argument('--probe-output', required=True)
        args = parser.parse_args()
        try:
            result = run_probe(args.root)
        except Exception as error:
            result = {'status': 'FAIL', 'errors': [type(error).__name__+': '+str(error)]}
        encoded = json.dumps(result, indent=2)+'\n'
        print(encoded, end='')
        if args.probe_output != '-':
            with Path(args.probe_output).open('x', encoding='utf-8') as stream:
                stream.write(encoded)
        raise SystemExit(0 if result['status'] == 'PASS' else 1)
    unittest.main()
