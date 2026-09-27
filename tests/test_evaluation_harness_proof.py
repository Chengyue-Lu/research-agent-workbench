"""H5 persistent four-arm proof, failed/retry closure and cold adversarial replay."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from research_workbench.evaluation.pins import EvaluationValidationError
from tests.harness_analysis_data import AUTH
from tests.harness_proof import build_proof, ref, replay_proof, save
from tests.system_evaluation_fixtures import ROOT


class HarnessProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive = tempfile.TemporaryDirectory()
        cls.source = Path(cls.archive.name) / 'proof'
        cls.inventory_ref = build_proof(cls.source, ROOT / 'schemas')

    @classmethod
    def tearDownClass(cls):
        cls.archive.cleanup()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / 'proof'
        shutil.copytree(self.source, self.root)
        self.inventory = self.read(self.inventory_ref)
        self.request = self.read(self.inventory['request_ref'])

    def read(self, item):
        return json.loads((self.root / item['path']).read_text(encoding='utf-8'))

    def resign(self):
        # Simulate an author replacing every outer byte pin; semantic validation must still reject.
        self.inventory['request_ref'] = save(self.root, 'analysis/replay-request.json', self.request)
        self.inventory['files'] = [ref(self.root, self.root / r['path']) for r in self.inventory['files']]
        return save(self.root, 'proof-inventory.json', self.inventory)

    def replay(self, item=None, **kwargs):
        return replay_proof(self.root, ROOT / 'schemas', item or self.inventory_ref, **kwargs)

    def test_cold_persistent_replay_retains_four_arms_failure_retry_and_null_metrics(self):
        result = subprocess.run([sys.executable, '-m', 'tests.harness_proof', 'replay',
            '--root', str(self.root), '--schemas', str(ROOT / 'schemas'),
            '--inventory-ref', json.dumps(self.inventory_ref)], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['arms'], ['mode-candidate-skill', 'mode-no-skill', 'plain-agent', 'plain-agent-tool'])
        protocol = self.read(self.request['context']['metrics']['review']['harness']['expected_protocol_ref'])
        contrast_count = 1 + len(protocol['rules']['secondary'])
        self.assertEqual((data['cells'], data['pairs']), (8, 2 * contrast_count))
        self.assertEqual(data['lifecycles'], {'completed': 8, 'post-call-failed': 1, 'not-started': 7})
        self.assertTrue(data['all_metrics_unavailable'])
        self.assertFalse(data['primary_confirmatory_eligible'])
        metrics = self.read(self.request['context']['expected_metrics_ref'])
        self.assertTrue(all(len(c['metrics']) == 13 for c in metrics['cells']))
        failed = next(c for c in metrics['cells'] if any(a['lifecycle'] == 'post-call-failed' for a in c['attempts']))
        self.assertEqual([a['retry_index'] for a in failed['attempts']], [0, 1])
        self.assertEqual(len(set(failed['target']['attempt_ids'])), 2)

    def test_inventory_pin_drift_and_unrelated_file_drift_fail_before_replay(self):
        for path in ('proof-inventory.json', 'analysis/replay-request.json',
                     self.request['context']['metrics']['review']['harness']['expected_protocol_ref']['path']):
            with self.subTest(path=path):
                target = self.root / path
                original = target.read_bytes()
                target.write_bytes(original + b'\n')
                try:
                    with self.assertRaisesRegex(EvaluationValidationError, 'hash mismatch'):
                        self.replay()
                finally:
                    target.write_bytes(original)

    def test_resigned_metric_zero_and_confirmatory_upgrade_are_independently_rejected(self):
        document = self.read(self.request['analysis_ref'])
        document['pairs'][0]['metrics'][0].update(status='measured', value=0)
        self.request['analysis_ref'] = save(self.root, self.request['analysis_ref']['path'], document)
        with self.assertRaisesRegex(EvaluationValidationError, 'independently rebuilt'):
            self.replay(self.resign())
        document['pairs'][0]['primary_confirmatory_eligible'] = True
        self.request['analysis_ref'] = save(self.root, self.request['analysis_ref']['path'], document)
        with self.assertRaisesRegex(EvaluationValidationError, 'schema'):
            self.replay(self.resign())

    def test_resigned_failed_attempt_deletion_cannot_be_hidden_by_successful_retry(self):
        review = self.request['context']['metrics']['review']
        execution = self.read(review['expected_execution_ref'])
        failed = next(r for r in execution['attempt_refs'] if self.read(r)['lifecycle'] == 'post-call-failed')
        execution['attempt_refs'].remove(failed)
        review['expected_execution_ref'] = save(self.root, review['expected_execution_ref']['path'], execution)
        evidence = self.read(review['expected_evidence_ref'])
        evidence['execution_ref'] = copy.deepcopy(review['expected_execution_ref'])
        review['expected_evidence_ref'] = save(self.root, review['expected_evidence_ref']['path'], evidence)
        with self.assertRaisesRegex(EvaluationValidationError, 'omitted or unfinished'):
            self.replay(self.resign())

    def test_resigned_reveal_time_and_external_authority_remain_caller_owned(self):
        original = copy.deepcopy(self.request)
        self.request['context']['metrics']['revealed_at'] = '2026-09-11T12:02:00Z'
        with self.assertRaises(EvaluationValidationError):
            self.replay(self.resign())
        self.request = original
        pinned = self.resign()
        for name in ('admission_verifier', 'human_verifier', 'measurement_verifier'):
            with self.subTest(authority=name), self.assertRaisesRegex(EvaluationValidationError, 'authority|admission'):
                self.replay(pinned, verifiers={**AUTH, name: lambda _: False})

    def test_resigned_inventory_cannot_replace_trusted_sources_or_omit_request(self):
        for kind in ('source', 'request'):
            with self.subTest(kind=kind):
                inventory = copy.deepcopy(self.inventory)
                if kind == 'source':
                    inventory['replay_sources']['tests/harness_analysis_data.py'] = '0' * 64
                else:
                    inventory['files'].remove(inventory['request_ref'])
                forged = save(self.root, 'forged-inventory.json', inventory)
                with self.assertRaisesRegex(EvaluationValidationError, 'source identity drift|request omitted'):
                    self.replay(forged)
        with self.assertRaisesRegex(EvaluationValidationError, 'destination must be empty'):
            build_proof(self.root, ROOT / 'schemas')

    def test_schema_drift_fails_closed(self):
        schemas = Path(self.directory.name) / 'schemas'
        shutil.copytree(ROOT / 'schemas', schemas)
        target = schemas / 'v0.1.0/evaluation-harness-analysis-input.schema.json'
        target.write_bytes(target.read_bytes() + b'\n')
        with self.assertRaisesRegex(EvaluationValidationError, 'validator identity drift'):
            replay_proof(self.root, schemas, self.inventory_ref)


class HarnessProofGuardTests(unittest.TestCase):
    def test_cold_execution_guards_fail_closed(self):
        script = '''
import os, socket, subprocess, sys
from pathlib import Path
from tests.harness_proof import deny_execution
assert 'tests.harness_execution_fixtures' not in sys.modules
deny_execution(sys.argv[1])
for operation in (
    lambda: socket.getaddrinfo('example.invalid', 80),
    lambda: socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
    lambda: os.system('echo untrusted-process'),
    lambda: subprocess.run([sys.executable, '-c', 'pass']),
    lambda: exec(compile('raise RuntimeError("untrusted code ran")', str(Path(sys.argv[1])/'tools/evil.py'), 'exec')),
):
    try: operation()
    except AssertionError: pass
    else: raise AssertionError('execution guard did not reject')
print('cold guards PASS')
'''
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-c', script, directory],
                                    cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'cold guards PASS')


if __name__ == '__main__':
    unittest.main()
