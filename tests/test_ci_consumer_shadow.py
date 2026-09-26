"""A proposed behavioral exclusion cannot hide failures or erase coverage work."""
import contextlib
import copy
import hashlib
import io
import json
import runpy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import ci_consumer_shadow as shadow
import plan_ci as planner

A = 'tests/test_reader.py::C.test_a'
B = 'tests/test_reader.py::C.test_b'
C = 'tests/test_other.py::C.test_c'


def inputs(coverage=True):
    plan = {'plan_id': 'p', 'binding': {'target': 't'}, 'behavioral_scope': 'full',
            'coverage_obligations': ['repository'] if coverage else []}
    inventory = {'version': 1, 'plan_id': 'p', 'target': 't', 'source': 'independent collection fixture',
                 'scope': 'plan-collection', 'python_version': '3.11.16', 'behavioral_order': [A, B],
                 'coverage_order': [B, C] if coverage else [],
                 'runtime_ids': {A: 'test_reader.C.test_a', B: 'test_reader.C.test_b', **({C: 'test_other.C.test_c'} if coverage else {})}}
    order = shadow.ordered_union(inventory['behavioral_order'], inventory['coverage_order'])
    receipt = {'schema_version': '1.2.0', 'plan_id': 'p', 'target': 't', 'python_version': '3.11.16',
               'suite': 'coverage-execution' if coverage else 'full', 'coverage_obligations': plan['coverage_obligations'],
               'successful': True, 'events': {'failures': 0, 'errors': 0, 'skips': 0}, 'test_count': len(order),
               'execution_order': order, 'execution': {'contract': 'ordered-behavioral-v1',
               'behavioral_order': inventory['behavioral_order'], 'coverage_order': inventory['coverage_order']},
               'tests': [{'id': inventory['runtime_ids'][key], 'canonical_id': key, 'outcome': 'passed',
                          'duration_seconds': number + 1} for number, key in enumerate(order)]}
    candidate = {'execution_order': shadow.ordered_union([A], inventory['coverage_order'])}
    return plan, inventory, receipt, candidate


class ConsumerOutcomeTests(unittest.TestCase):
    def test_ordered_coverage_retains_behavioral_skip_and_missing_proof(self):
        plan, inventory, receipt, candidate = inputs()
        shadow.validate_inventory(plan, inventory)
        result = shadow.compare_receipt(plan, inventory, candidate, receipt)
        self.assertEqual('observed-no-missed-failure', result['status'])
        self.assertEqual(0, result['excluded_case_seconds_estimate'])
        self.assertEqual([A, B, C], candidate['execution_order'])
        self.assertIsNone(shadow.compare_receipt(plan, inventory, candidate, None)['excluded_case_seconds_estimate'])
        for mutation in (lambda r: r.update(execution_order=[B, A, C]), lambda r: r.pop('events'),
                         lambda r: r.update(suite='coverage-quality'), lambda r: r.pop('execution'),
                         lambda r: r.update(test_count=2), lambda r: r['events'].update(errors=1),
                         lambda r: r['events'].update(skips=1),
                         lambda r: r.update(successful=False), lambda r: r['tests'].pop()):
            broken = copy.deepcopy(receipt)
            mutation(broken)
            with self.subTest(receipt=broken):
                self.assertEqual('inconclusive', shadow.compare_receipt(plan, inventory, candidate, broken)['status'])
        # Record order is duration-sorted by the real runner, not execution order.
        receipt['tests'].reverse()
        self.assertEqual('observed-no-missed-failure', shadow.compare_receipt(plan, inventory, candidate, receipt)['status'])

    def test_failure_checkpoint_fixture_and_skip_cannot_disappear(self):
        plan, inventory, receipt, candidate = inputs(False)
        result = shadow.compare_receipt(plan, inventory, candidate, receipt)
        self.assertEqual(2, result['excluded_case_seconds_estimate'])
        for outcome in ('failed', 'error', 'unexpected_success'):
            receipt['tests'][1]['outcome'] = outcome
            result = shadow.compare_receipt(plan, inventory, candidate, receipt)
            self.assertEqual('missed-failure', result['status'])
            self.assertEqual([B], result['missed_failure_ids'])
        receipt['tests'][1]['outcome'] = 'passed'
        receipt['tests'][1]['checkpoints'] = [{'outcome': 'failed'}]
        self.assertEqual([B], shadow.compare_receipt(plan, inventory, candidate, receipt)['missed_failure_ids'])
        receipt['tests'][1]['checkpoints'] = []
        receipt['tests'][0]['checkpoints'] = [{'outcome': 'skipped'}]
        self.assertIn(A, shadow.compare_receipt(plan, inventory, candidate, receipt)['inconclusive_ids'])
        receipt['tests'][0]['checkpoints'] = [{'outcome': 'failed'}]
        self.assertEqual('inconclusive', shadow.compare_receipt(plan, inventory, candidate, receipt)['status'])
        receipt['tests'][0]['checkpoints'] = []
        for outcome in ('skipped', 'passed_with_skips', 'expected_failure', 'missing'):
            receipt['tests'][1]['outcome'] = outcome
            self.assertEqual([B], shadow.compare_receipt(plan, inventory, candidate, receipt)['inconclusive_ids'])
        receipt['tests'][1]['outcome'] = 'passed'
        receipt['tests'][1].pop('duration_seconds')
        self.assertIsNone(shadow.compare_receipt(plan, inventory, candidate, receipt)['excluded_case_seconds_estimate'])
        receipt['tests'].append({'id': 'setUpClass(C)', 'canonical_id': 'setUpClass(C)', 'outcome': 'error'})
        result = shadow.compare_receipt(plan, inventory, candidate, receipt)
        self.assertEqual(1, len(result['unexpected_or_fixture_records']))
        self.assertEqual('inconclusive', result['status'])

    def test_malformed_or_rebound_inputs_are_rejected(self):
        plan, inventory, receipt, candidate = inputs()
        for mutation in (lambda r: r.update(target='stale'), lambda r: r.update(plan_id='other'),
                         lambda r: r.update(python_version='3.13.7'), lambda r: r.update(coverage_obligations=[]),
                         lambda r: r['tests'].append(r['tests'][0]), lambda r: r['tests'][0].update(id='aliased'),
                         lambda r: r['tests'][0].update(duration_seconds=True),
                         lambda r: r['tests'][0].update(duration_seconds=float('nan')),
                         lambda r: r['tests'][0].update(outcome='success'),
                         lambda r: r['tests'][0].update(checkpoints=[{'outcome': 'success'}])):
            broken = copy.deepcopy(receipt)
            mutation(broken)
            with self.subTest(receipt=broken), self.assertRaises(ValueError):
                shadow.compare_receipt(plan, inventory, candidate, broken)
        for mutation in (lambda r: r.update(scope='complete'), lambda r: r.update(source=''),
                         lambda r: r.update(target='stale'), lambda r: r.update(coverage_order=[]),
                         lambda r: r.update(behavioral_order=[A, A]), lambda r: r['runtime_ids'].update({B: 'alias'})):
            broken = copy.deepcopy(inventory)
            mutation(broken)
            if broken['runtime_ids'].get(B) == 'alias':
                # A separate collector may choose runtime aliases; receipt must agree.
                with self.assertRaises(ValueError):
                    shadow.compare_receipt(plan, broken, candidate, receipt)
            else:
                with self.subTest(inventory=broken), self.assertRaises(ValueError):
                    shadow.validate_inventory(plan, broken)
        inventory['scope'] = 'observed-subset'
        self.assertEqual('inconclusive', shadow.compare_receipt(plan, inventory, candidate, receipt)['status'])
        inventory['coverage_order'] = []
        candidate['execution_order'] = [A]
        receipt['tests'][1]['outcome'] = 'failed'
        uncertain = shadow.compare_receipt(plan, inventory, candidate, receipt)
        self.assertEqual([], uncertain['missed_failure_ids'])
        self.assertEqual([B], uncertain['failure_exclusion_unknown_ids'])
        self.assertEqual('unknown', uncertain['rows'][1]['candidate_execution'])
        self.assertEqual('inconclusive', uncertain['status'])
        self.assertIsNone(uncertain['excluded_case_seconds_estimate'])
        plan, inventory, receipt, candidate = inputs(False)
        receipt['suite'] = 'observed-subset'
        self.assertEqual('inconclusive', shadow.compare_receipt(plan, inventory, candidate, receipt)['status'])


class ConsumerGitTests(unittest.TestCase):
    def test_real_git_proposal_drift_membership_and_overlapping_consumers(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE).decode().strip()
            def write(path, raw):
                target = repo / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw.encode() if isinstance(raw, str) else raw)
            git('init', '-q', '-b', 'develop')
            git('config', 'user.name', 'CI fixture')
            git('config', 'user.email', 'fixture@example.invalid')
            git('config', 'core.autocrlf', 'false')
            for path in planner.TRUST_FILES:
                write(path, (ROOT / path).read_bytes())
            policy = {'policy_id': 'rwb-ci-impact', 'version': 1, 'consumer_fingerprint': '0' * 64,
                      'surfaces': {'docs': {'paths': ['docs/**'], 'class': 'fast', 'groups': ['documentation']}},
                      'groups': {'documentation': {'tests': ['test_reader'], 'downstream': [], 'coverage': [],
                                                  'package': False, 'repository': False}},
                      'impact_evidence': {'positive_tests': ['test_reader.C.test_a'], 'negative_tests': ['test_reader.C.test_b']}}
            write(planner.POLICY, planner.canonical(policy))
            write('tests/test_reader.py', 'import unittest\nclass C(unittest.TestCase):\n def test_a(self): pass\n def test_b(self): pass\n')
            write('tests/test_documentation.py', 'import unittest\n')
            write('tests/test_pr_governance.py', 'import unittest\n')
            write('docs/note.md', 'original\n')
            git('add', '.')
            git('commit', '-qm', 'base')
            base = git('rev-parse', 'HEAD')
            consumer = {'id': 'reader', 'owner': 'Chengyue-Lu', 'invocation': 'in-memory reader fixture', 'tests': [B],
                        'input_patterns': ['fixtures/**'], 'pins': {'tests/test_reader.py': hashlib.sha256((repo/'tests/test_reader.py').read_bytes()).hexdigest()},
                        'assumptions': ['fixture uses no repository document; independent witness pending'], 'unknowns': []}
            proposal = {'version': 1, 'execution_authority': False, 'baseline': base, 'consumers': [consumer]}
            shadow.validate_proposal(proposal)
            for mutation in (lambda p: p.update(execution_authority=True), lambda p: p.update(version=True),
                             lambda p: p['consumers'][0].update(assumptions=[]),
                             lambda p: p['consumers'][0].update(pins={}),
                             lambda p: p['consumers'][0].update(input_patterns=['../docs/**']),
                             lambda p: p['consumers'][0].update(tests=[B, B])):
                broken = copy.deepcopy(proposal)
                mutation(broken)
                with self.subTest(proposal=broken), self.assertRaises(ValueError):
                    shadow.validate_proposal(broken)
            write('docs/note.md', 'changed\n')
            git('add', 'docs/note.md')
            git('commit', '-qm', 'document')
            head = git('rev-parse', 'HEAD')
            empty_plan = {'binding': {'base': base, 'merge_base': base, 'head': base, 'target': base}, 'changes': []}
            _, empty_inventory, _, _ = inputs(False)
            self.assertEqual([A, B], shadow.candidate_selection(repo, empty_plan, proposal, empty_inventory)['behavioral_order'])
            git('commit', '--allow-empty', '-qm', 'same-tree distinct commit')
            same_tree = git('rev-parse', 'HEAD')
            empty_plan['binding'].update(base=head, merge_base=head, head=same_tree, target=same_tree)
            proposal_copy = {**proposal, 'baseline': head}
            result = shadow.candidate_selection(repo, empty_plan, proposal_copy, empty_inventory)
            self.assertIn('empty Git delta is outside the modified Markdown pilot', result['fallback'])
            plan = planner.make_plan(repo, base=base, head=head, target=head, repository='Example/repo')
            _, inventory, receipt, _ = inputs(False)
            inventory.update(plan_id=plan['plan_id'], target=head)
            inventory['coverage_order'] = [B] if plan['coverage_obligations'] else []
            receipt.update(plan_id=plan['plan_id'], target=head,
                           suite='coverage-execution' if plan['coverage_obligations'] else plan['behavioral_scope'],
                           coverage_obligations=plan['coverage_obligations'])
            receipt['execution']['coverage_order'] = inventory['coverage_order']
            original = planner.canonical(plan)
            report = shadow.build_report(repo, plan, proposal, inventory, receipt)
            self.assertEqual([B], report['behavioral_skips'])
            self.assertEqual([] if plan['coverage_obligations'] else [B], report['effective_execution_skips'])
            self.assertFalse(report['activation']['eligible'])
            self.assertEqual(original, planner.canonical(plan))
            stale = {**proposal, 'baseline': 'a' * 40}
            self.assertEqual([A, B], shadow.candidate_selection(repo, plan, stale, inventory)['behavioral_order'])
            consumer['changed_path_patterns']=['docs/workstreams/**']
            shadow.validate_proposal(proposal)
            self.assertEqual([A, B],shadow.candidate_selection(repo,plan,proposal,inventory)['behavioral_order'])
            consumer['changed_path_patterns']=['docs/**']
            self.assertEqual([A],shadow.candidate_selection(repo,plan,proposal,inventory)['behavioral_order'])
            consumer['changed_path_patterns']=[]
            with self.assertRaisesRegex(ValueError,'empty changed path'):shadow.validate_proposal(proposal)
            consumer.pop('changed_path_patterns')
            consumer['pins']['tests/absent.py'] = 'a' * 64
            self.assertEqual([A, B], shadow.candidate_selection(repo, plan, proposal, inventory)['behavioral_order'])
            consumer['pins'].pop('tests/absent.py')
            consumer['tests'].append('tests/test_reader.py::C.test_future')
            self.assertIn('declared tests absent from observed inventory',
                          shadow.build_report(repo, plan, proposal, inventory)['activation']['blockers'])
            consumer['tests'].pop()
            write('tests/test_reader.py', '# worktree rewrite\n')
            self.assertEqual(report, shadow.build_report(repo, plan, proposal, inventory, receipt))
            signature = report.pop('report_id')
            self.assertEqual(signature, planner.digest(report))
            for name, payload in [('plan', plan), ('proposal', proposal), ('inventory', inventory), ('receipt', receipt)]:
                write(name + '.json', planner.canonical(payload))
            arguments = ['--repo', str(repo), '--plan', str(repo/'plan.json'), '--proposal', str(repo/'proposal.json'),
                         '--inventory', str(repo/'inventory.json'), '--receipt', str(repo/'receipt.json'), '--output', str(repo/'report.json')]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, shadow.main(arguments))
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                shadow.main([*arguments[:-1], str(repo/'receipt.json')])
            no_receipt = [*arguments[:8], *arguments[10:]]
            saved = sys.argv
            try:
                sys.argv = ['ci_consumer_shadow', *no_receipt]
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as stopped:
                    runpy.run_path(str(ROOT/'.github/scripts/ci_consumer_shadow.py'), run_name='__main__')
                self.assertEqual(0, stopped.exception.code)
            finally:
                sys.argv = saved
            overlapping = copy.deepcopy(consumer)
            overlapping.update(id='real-doc-reader', input_patterns=['docs/**'])
            proposal['consumers'].append(overlapping)
            self.assertEqual([A, B], shadow.candidate_selection(repo, plan, proposal, inventory)['behavioral_order'])
            proposal['consumers'].pop()
            consumer['unknowns'] = ['opaque resource read']
            self.assertEqual([A, B], shadow.candidate_selection(repo, plan, proposal, inventory)['behavioral_order'])
            consumer['unknowns'] = []
            # Committed helper/test drift defeats the old pin, even after a proposal baseline refresh.
            git('add', 'tests/test_reader.py')
            git('commit', '-qm', 'source mutation')
            newer = git('rev-parse', 'HEAD')
            altered = planner.make_plan(repo, base=base, head=newer, target=newer, repository='Example/repo')
            result = shadow.candidate_selection(repo, altered, proposal, inventory)
            self.assertEqual([A, B], result['behavioral_order'])
            self.assertTrue(result['consumers'][0]['pin_drift'])
            git('reset', '--hard', head)
            write('docs/note.md', '#!/usr/bin/python\nprint("executable document")\n')
            git('add', 'docs/note.md')
            git('commit', '-qm', 'executable markdown')
            newer = git('rev-parse', 'HEAD')
            altered = planner.make_plan(repo, base=base, head=newer, target=newer, repository='Example/repo')
            self.assertIn('docs/note.md: executable document',
                          shadow.candidate_selection(repo, altered, proposal, inventory)['fallback'])
            git('reset', '--hard', head)
            git('update-index', '--add', '--cacheinfo', '160000,' + 'a' * 40 + ',docs/foreign.md')
            git('commit', '-qm', 'gitlink membership')
            newer = git('rev-parse', 'HEAD')
            altered = planner.make_plan(repo, base=base, head=newer, target=newer, repository='Example/repo')
            result = shadow.candidate_selection(repo, altered, proposal, inventory)
            self.assertEqual([A, B], result['behavioral_order'])
            self.assertTrue(result['fallback'])
            # Explicitly unsupported identities never become wildcard exclusions.
            with self.assertRaises(ValueError):
                shadow.identities(['tests/test_*.py::C.test_a'], 'test')


class AcceptedTemplateTests(unittest.TestCase):
    """An explicit base supplies definitions; candidate data cannot replace them."""
    template_path = 'diagnostics/consumers.json'

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.git('init', '-q', '-b', 'develop')
        self.git('config', 'user.name', 'CI fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'core.autocrlf', 'false')
        for path in planner.TRUST_FILES:
            self.write(path, (ROOT / path).read_bytes())
        policy = {'policy_id': 'rwb-ci-impact', 'version': 1, 'consumer_fingerprint': '0' * 64,
                  'surfaces': {'docs': {'paths': ['docs/**'], 'class': 'fast', 'groups': ['documentation']}},
                  'groups': {'documentation': {'tests': ['test_reader'], 'downstream': [], 'coverage': [],
                                              'package': False, 'repository': False}},
                  'impact_evidence': {'positive_tests': ['test_reader.C.test_a'], 'negative_tests': ['test_reader.C.test_b']}}
        self.write(planner.POLICY, planner.canonical(policy))
        self.write('tests/test_reader.py', b'import unittest\nclass C(unittest.TestCase):\n def test_a(self): pass\n def test_b(self): pass\n')
        self.write('tests/test_documentation.py', b'import unittest\n')
        self.write('tests/test_pr_governance.py', b'import unittest\n')
        self.write('docs/note.md', b'original\n')
        self.template = {'version': 1, 'execution_authority': False, 'consumers': [{
            'id': 'reader', 'owner': 'Chengyue-Lu', 'invocation': 'in-memory reader fixture', 'tests': [B],
            'input_patterns': ['fixtures/**'],
            'pins': {'tests/test_reader.py': hashlib.sha256((self.repo / 'tests/test_reader.py').read_bytes()).hexdigest()},
            'assumptions': ['independent closure proof pending'], 'unknowns': ['unproved external input']}]}
        self.raw = planner.canonical(self.template)
        self.write(self.template_path, self.raw)
        self.base = self.commit('accepted fixture')
        self.write('docs/note.md', b'changed\n')
        self.head = self.commit('document change')
        self.plan = planner.make_plan(self.repo, base=self.base, head=self.head, target=self.head, repository='Example/repo')
        _, self.inventory, _, _ = inputs(False)
        self.inventory.update(plan_id=self.plan['plan_id'], target=self.head)
        self.inventory['coverage_order'] = [B] if self.plan['coverage_obligations'] else []

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.PIPE).decode().strip()

    def write(self, path, raw):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-qm', message)
        return self.git('rev-parse', 'HEAD')

    def load(self, *, plan=None, base=None, path=None):
        return shadow.accepted_proposal(self.repo, plan or self.plan, base or self.base, path or self.template_path)

    def test_dirty_template_cannot_rewrite_unknowns_pins_or_test_ownership(self):
        effective, provenance = self.load()
        expected = {**self.template, 'baseline': self.base}
        self.assertEqual(expected, effective)
        original = shadow.build_accepted_report(self.repo, self.plan, self.base, self.template_path, self.inventory)
        changed = copy.deepcopy(self.template)
        changed['consumers'][0].update(unknowns=[], tests=[A], owner='candidate', pins={'tests/test_reader.py': '0' * 64})
        self.write(self.template_path, planner.canonical(changed))
        self.assertEqual([{'status': 'M', 'path': 'docs/note.md'}], self.plan['changes'])
        self.assertEqual((effective, provenance), self.load())
        self.assertEqual(original, shadow.build_accepted_report(self.repo, self.plan, self.base, self.template_path, self.inventory))
        self.assertEqual('unknown', original['candidate']['consumers'][0]['decision'])
        self.assertIn('unproved external input', original['candidate']['consumers'][0]['reasons'])
        self.assertEqual(self.raw, planner.read_at(self.repo, self.base, self.template_path))

    def test_report_keeps_external_diagnostics_and_distinguishes_binding_identity(self):
        effective, provenance = self.load()
        external = shadow.build_report(self.repo, self.plan, effective, self.inventory)
        bound = shadow.build_accepted_report(self.repo, self.plan, self.base, self.template_path, self.inventory)
        for key in ('candidate', 'accepted', 'comparison', 'coverage_comparison', 'smoke_comparison', 'proposal_sha256'):
            self.assertEqual(external[key], bound[key], key)
        self.assertEqual(self.base, provenance['commit'])
        self.assertEqual(self.template_path, provenance['path'])
        self.assertEqual(self.git('rev-parse', self.base + ':' + self.template_path), provenance['git_blob'])
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), provenance['raw_sha256'])
        self.assertEqual(planner.digest(effective), provenance['effective_proposal_sha256'])
        self.assertEqual(provenance, bound['accepted_template'])
        self.assertNotEqual(external['report_id'], bound['report_id'])
        identity = bound.pop('report_id')
        self.assertEqual(identity, planner.digest(bound))
        self.assertFalse(bound['execution_authority'])
        self.assertFalse(bound['activation']['eligible'])
        self.assertIn('input closure and independent exclusion witness unproved', bound['activation']['blockers'][0])
        self.assertIn('checker/import dependencies', bound['activation']['blockers'][-1])
        rebound, new_source = self.load(plan={'binding': {'base': self.head}}, base=self.head)
        self.assertEqual(effective['consumers'], rebound['consumers'])
        self.assertEqual(provenance['raw_sha256'], new_source['raw_sha256'])
        self.assertEqual(provenance['git_blob'], new_source['git_blob'])
        self.assertNotEqual(provenance['effective_proposal_sha256'], new_source['effective_proposal_sha256'])

    def test_committed_rewrite_deletion_and_mode_cannot_replace_base(self):
        expected = self.load()
        changed = copy.deepcopy(self.template)
        changed['consumers'][0].update(unknowns=[], tests=[A], owner='candidate', pins={'tests/test_reader.py': '0' * 64})
        self.write(self.template_path, planner.canonical(changed))
        rewritten = self.commit('candidate redefines consumers')
        for mode in ('rewrite', 'delete', 'symlink'):
            if mode == 'delete':
                self.git('rm', self.template_path)
            elif mode == 'symlink':
                blob = self.git('rev-parse', rewritten + ':' + self.template_path)
                self.git('update-index', '--add', '--cacheinfo', '120000,' + blob + ',' + self.template_path)
            if mode != 'rewrite':
                self.git('commit', '-qm', 'candidate ' + mode)
            head = self.git('rev-parse', 'HEAD')
            plan = {'binding': {**self.plan['binding'], 'head': head, 'target': head}}
            with self.subTest(mode=mode):
                self.assertEqual(expected, self.load(plan=plan))
        self.write('diagnostics/candidate-only.json', self.raw)
        self.commit('candidate-only template')
        with self.assertRaisesRegex(ValueError, 'regular Git file'):
            self.load(path='diagnostics/candidate-only.json')

    def test_explicit_full_commit_and_safe_regular_json_path_are_required(self):
        with self.assertRaisesRegex(ValueError, 'differs from plan base'):
            self.load(base=self.head)
        blob = self.git('rev-parse', self.base + ':' + self.template_path)
        for invalid in (self.base[:12], 'HEAD', 'f' * 40, blob):
            with self.subTest(base=invalid), self.assertRaises(ValueError):
                self.load(plan={'binding': {'base': invalid}}, base=invalid)
        for invalid in ('../consumers.json', '/consumers.json', 'diagnostics/*.json', 'diagnostics/consumers.txt',
                        'diagnostics/missing.json', 'diagnostics\\consumers.json'):
            with self.subTest(path=invalid), self.assertRaises(ValueError):
                self.load(path=invalid)
        for mode in ('100755', '120000', '160000'):
            target = self.base if mode == '160000' else blob
            self.git('update-index', '--add', '--cacheinfo', mode + ',' + target + ',' + self.template_path)
            self.git('commit', '-qm', 'accepted invalid mode ' + mode)
            base = self.git('rev-parse', 'HEAD')
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'regular Git file'):
                self.load(plan={'binding': {'base': base}}, base=base)
        self.git('rm', '--cached', self.template_path)
        self.git('commit', '-qm', 'accepted template removed')
        removed = self.git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(ValueError, 'regular Git file'):
            self.load(plan={'binding': {'base': removed}}, base=removed)

    def test_invalid_frozen_template_and_duplicate_keys_are_rejected(self):
        versions = [b'[]', b'{', b'{"version":1,"version":1,"execution_authority":false,"consumers":[]}']
        for mutation in (lambda p: p.update(baseline=self.base), lambda p: p.update(version=True),
                         lambda p: p.update(execution_authority=True), lambda p: p.update(consumers=None),
                         lambda p: p['consumers'][0].update(pins={}), lambda p: p['consumers'][0].update(unknowns='erased')):
            broken = copy.deepcopy(self.template)
            mutation(broken)
            versions.append(planner.canonical(broken))
        versions.append(self.raw.replace(b'"owner":', b'"owner":"first","owner":'))
        for index, raw in enumerate(versions):
            self.write(self.template_path, raw)
            base = self.commit('invalid accepted template ' + str(index))
            with self.subTest(template=raw), self.assertRaises(ValueError):
                self.load(plan={'binding': {'base': base}}, base=base)

    def test_git_blob_content_must_match_tree_identity(self):
        blob = self.git('rev-parse', self.base + ':' + self.template_path)
        replacement = self.raw.replace(b'Chengyue-Lu', b'candidateXX')
        self.assertNotEqual(self.raw, replacement)
        loose_object = self.repo / '.git' / 'objects' / blob[:2] / blob[2:]
        loose_object.chmod(0o600)
        loose_object.write_bytes(zlib.compress(b'blob ' + str(len(replacement)).encode() + b'\0' + replacement))
        with self.assertRaisesRegex(ValueError, 'Git blob mismatch'):
            self.load()

    def test_cli_selects_one_source_and_protects_local_template_from_output(self):
        for name, data in (('plan', self.plan), ('inventory', self.inventory)):
            self.write(name + '.json', planner.canonical(data))
        args = ['--repo', str(self.repo), '--plan', str(self.repo / 'plan.json'),
                '--inventory', str(self.repo / 'inventory.json'), '--output', str(self.repo / 'report.json')]
        accepted = ['--accepted-proposal-template', self.template_path, '--accepted-base', self.base]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, shadow.main(args + accepted))
        result = json.loads((self.repo / 'report.json').read_bytes())
        self.assertEqual(shadow.build_accepted_report(self.repo, self.plan, self.base, self.template_path, self.inventory), result)
        for source in (self.repo / self.template_path, self.repo / 'plan.json', self.repo / 'inventory.json'):
            with self.subTest(output=source), self.assertRaisesRegex(ValueError, 'overwrite'):
                shadow.main(args[:-1] + [str(source)] + accepted)
        for selection in (accepted[:2], ['--proposal', 'proposal.json', '--accepted-base', self.base],
                          accepted + ['--proposal', 'proposal.json'], []):
            with self.subTest(selection=selection), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                shadow.main(args + selection)


if __name__ == '__main__':
    unittest.main()
