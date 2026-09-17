"""Consumer review pins do not attest execution, complete closure or safe exclusions."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import ci_consumer_contracts as contracts
import plan_ci as planner


class ConsumerContractTests(unittest.TestCase):
    def setUp(self):
        self.files = {
            'src/reader.py': b'def read(path):\n    return path.read_bytes()\n',
            'tests/test_reader.py': b'class Reader:\n    def test_ok(self): pass\n    def test_bad(self): pass\n',
            'registry/input.yaml': b'value: original\n',
        }
        self.record = {'id': 'reader-input', 'owner': 'Chengyue-Lu', 'consumer': 'src/reader.py',
            'pins': {p: hashlib.sha256(raw).hexdigest() for p, raw in self.files.items()},
            'entrypoints': ['read'], 'inputs': ['caller path'], 'outputs': ['parsed mapping'],
            'invariants': ['same bytes for hash and parse'], 'unresolved': ['caller instance closure'],
            'positive_tests': ['test_reader.Reader.test_ok'], 'negative_tests': ['test_reader.Reader.test_bad'],
            'execution_authority': False}

    def inspect(self, record=None, files=None, modes=None):
        files = self.files if files is None else files
        inventory = {p: ((modes or {}).get(p, '100644'), 'blob', 'unused') for p in files}
        return contracts.inspect_record(record or self.record, inventory, files.__getitem__)

    def test_matching_pins_and_call_syntax_are_review_evidence_only(self):
        contracts.validate([self.record])
        result = self.inspect()
        self.assertTrue(result['declared_pins_match'])
        self.assertEqual('path.read_bytes()', result['effect_syntax'][0]['call'])
        for key in ('execution_authority', 'evidence_executed', 'complete_input_closure_proved'):
            self.assertIs(False, result[key])
        raw = b'async def outer():\n    def inner():\n        subprocess.run(["git", "rev-parse", "HEAD"])\n    await f()\n'
        observed = contracts.source_observations(raw)
        self.assertIn('outer.inner', observed['definitions'])
        self.assertEqual('outer.inner', observed['effect_syntax'][0]['entrypoint'])

    def test_source_test_input_mode_and_identifier_drift_are_visible(self):
        for path in self.files:
            with self.subTest(path=path):
                changed = {**self.files, path: self.files[path] + b'\n# changed\n'}
                self.assertIn(path + ': bytes changed', self.inspect(files=changed)['drift'])
                removed = {p: raw for p, raw in self.files.items() if p != path}
                self.assertFalse(self.inspect(files=removed)['declared_pins_match'])
                for mode in ('100755', '120000', '160000'):
                    self.assertFalse(self.inspect(modes={path: mode})['declared_pins_match'])
        for raw in (b'not python (', b'\xff', b'def different(): pass\n'):
            self.assertFalse(self.inspect(files={**self.files, 'src/reader.py': raw})['declared_pins_match'])
        result = self.inspect(files={**self.files, 'tests/test_reader.py': b'class Reader: pass\n'})
        self.assertIn('missing evidence identifier: test_reader.Reader.test_bad', result['drift'])
        # An unpinned file is not silently claimed to be covered by the observed pins.
        result = self.inspect(files={**self.files, 'registry/new.yaml': b'new input'})
        self.assertTrue(result['declared_pins_match'])
        self.assertFalse(result['complete_input_closure_proved'])

    def test_candidate_rewrite_removal_and_new_record_never_become_base_authority(self):
        inventory = {p: ('100644', 'blob', 'unused') for p in self.files}
        revised = {**self.record, 'inputs': ['narrower unsupported claim']}
        for old, new, status in (([], [self.record], 'candidate-proposed'),
                                ([self.record], [], 'candidate-removed'),
                                ([self.record], [revised], 'candidate-revised'),
                                ([self.record], [self.record], 'base-recorded')):
            with self.subTest(status=status):
                row = contracts.review(old, new, {'base': inventory, 'head': inventory},
                    lambda label, path: self.files[path])[0]
                self.assertEqual(status, row['status'])
                self.assertEqual(self.record, row['definition'])
                self.assertFalse(row['execution_authority'])
                self.assertTrue(row['activation_blockers'])
                self.assertEqual({'base', 'head'}, set(row['checks']))
        self.assertEqual([], contracts.review([], [], {}, None))

    def test_contract_schema_rejects_authority_and_unbound_evidence(self):
        mutations = [lambda r:r.update(id=1), lambda r:r.update(id='Bad ID'), lambda r:r.update(owner=' '),
            lambda r:r.update(execution_authority=True), lambda r:r.update(execution_authority=0),
            lambda r:r.update(pins={}), lambda r:r.update(consumer='src/unpinned.py'),
            lambda r:r.update(consumer=1), lambda r:r.update(extra='unsupported'),
            lambda r:r.update(positive_tests=['bad-id']),
            lambda r:r.update(positive_tests=['test_missing.Reader.test_ok']),
            lambda r:r.update(negative_tests=r['positive_tests'])]
        for key in ('entrypoints', 'inputs', 'outputs', 'invariants', 'unresolved', 'positive_tests', 'negative_tests'):
            mutations.extend([lambda r,k=key:r.update({k:[]}), lambda r,k=key:r.update({k:['x','x']}),
                              lambda r,k=key:r.update({k:[False]})])
        for path in ('../src/a.py', 'src/../a.py', 'src//a.py', 'src/a\\b.py', 'src/a:b.py', '/src/a.py', ''):
            mutations.append(lambda r,p=path:r['pins'].update({p:'0'*64}))
        for digest in (None, '0'*63, 'A'*64):
            mutations.append(lambda r,d=digest:r['pins'].update({'src/reader.py': d}))
        for mutate in mutations:
            record = copy.deepcopy(self.record)
            mutate(record)
            with self.subTest(record=record), self.assertRaises(ValueError):
                contracts.validate([record])
        for records in (None, {}, [None], [self.record, self.record]):
            with self.assertRaises(ValueError):
                contracts.validate(records)

    def test_policy_v1_v2_and_live_records_preserve_explicit_version_boundary(self):
        policy = json.loads((ROOT / planner.POLICY).read_bytes())
        planner.validate_policy(policy)
        self.assertEqual(4, len(policy['consumer_contracts']))
        for record in policy['consumer_contracts']:
            files = {p: (ROOT/p).read_bytes() for p in record['pins']}
            result = self.inspect(record, files)
            self.assertTrue(result['declared_pins_match'], result['drift'])
        legacy = {k:v for k,v in policy.items() if k != 'consumer_contracts'}
        legacy['version'] = 1
        planner.validate_policy(legacy)
        for bad in ({**legacy, 'version':2}, {**policy, 'version':1}, {**policy, 'version':3}):
            with self.assertRaises(ValueError):
                planner.validate_policy(bad)
        invalid = {**policy, 'consumer_contracts':[dict(self.record, execution_authority=True)]}
        with self.assertRaises(ValueError):
            planner.validate_policy(invalid)

    def test_policy_authority_does_not_import_candidate_diagnostic_module(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('plan_ci.py', 'ci_dependencies.py'):
                (root/name).write_bytes((ROOT/'.github/scripts'/name).read_bytes())
            (root/'ci_consumer_contracts.py').write_text('raise RuntimeError("diagnostic entered authority")\n')
            code = ('import sys,json; sys.path.insert(0,sys.argv[1]); import plan_ci; '
                    'p=json.load(open(sys.argv[2])); plan_ci.validate_policy(p); '
                    'assert "ci_consumer_contracts" not in sys.modules; '
                    'p["consumer_contracts"][0]["execution_authority"]=True; '
                    'plan_ci.validate_policy(p)')
            result = subprocess.run([sys.executable, '-I', '-c', code, str(root), str(ROOT/planner.POLICY)],
                capture_output=True, text=True)
            self.assertNotEqual(0, result.returncode)
            self.assertIn('consumer contracts cannot authorize execution', result.stderr)
            self.assertNotIn('diagnostic entered authority', result.stderr)
