"""Path classifier controls; all policy modules must exist in the real inventory."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ci_components', ROOT / '.github/scripts/ci_components.py')
classifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(classifier)


class ComponentPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((ROOT / 'tests/ci_components.json').read_text(encoding='utf-8'))
        # Read repository membership without walking installed environments or
        # generated runtime resources. Include the new local candidate modules.
        cls.inventory = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')[:-1])
        cls.inventory.update(p.relative_to(ROOT).as_posix() for directory, pattern in
                             ((ROOT/'tests', 'test_*.py'), (ROOT/'.github/scripts', '*.py'))
                             for p in directory.glob(pattern))

    def plan(self, paths, *, inventory=None, policy=None):
        changes = [{'status': 'M', 'path': path} if isinstance(path, str) else path for path in paths]
        return classifier.plan(changes, self.inventory if inventory is None else inventory,
                               self.policy if policy is None else policy)

    def test_every_mapping_names_an_actual_test_module(self):
        modules = set(self.policy['install_docs_tests'])
        for rule in self.policy['components'].values(): modules.update(rule['tests'])
        for tests in self.policy['direct_tests'].values(): modules.update(tests)
        self.assertGreaterEqual(len(self.policy['components']), 10)
        # Entry adds one explicit owner; retain the existing bound for all
        # other components instead of allowing an arbitrary extra category.
        self.assertIn('entry', self.policy['components'])
        self.assertLessEqual(len(set(self.policy['components']) - {'entry'}), 15)
        for module in sorted(modules):
            with self.subTest(module=module):
                self.assertRegex(module, r'^test_[A-Za-z0-9_]+$')
                self.assertIn('tests/' + module + '.py', self.inventory)
        # Checkpoint remains the real test inventory, including retired daily diagnostics.
        self.assertIn('tests/test_selection_witness.py', self.inventory)
        self.assertIn('tests/test_ci_dependencies.py', self.inventory)

    def test_known_component_keeps_new_source_own_test(self):
        for source in ('.github/scripts/new_checker.py',
                       'src/research_workbench/evaluation/new_checker.py'):
            with self.subTest(source=source):
                report = self.plan([source], inventory=self.inventory | {'tests/test_new_checker.py'})
                self.assertIn('test_new_checker', report['selected_tests'])
                self.assertTrue(any(row['kind']=='matching-test-module' for row in report['reasons']))

    def test_component_source_selects_whole_group_on_baseline(self):
        report = self.plan(['src/research_workbench/adapters/models/gemini.py'])
        self.assertEqual(['adapters'], report['components'])
        self.assertEqual(sorted(self.policy['components']['adapters']['tests']), report['selected_tests'])
        self.assertEqual(['3.11'], report['python_versions'])
        self.assertTrue(report['smoke'])
        self.assertFalse(report['install'])
        self.assertEqual([], report['unknown_paths'])

    def test_entry_source_only_edit_selects_entry_consumers(self):
        expected = {
            'test_entry_binding', 'test_entry_bridge_flow', 'test_entry_caller',
            'test_entry_cli', 'test_entry_control_chain', 'test_entry_deadline',
            'test_entry_driver', 'test_entry_executor', 'test_entry_factory',
            'test_entry_guide', 'test_entry_handoff', 'test_entry_intake',
            'test_entry_intake_call', 'test_entry_intake_constraints',
            'test_entry_roles', 'test_entry_stage', 'test_entry_state',
            'test_entry_workflow',
        }
        for module in ('intake', 'caller', 'executor', 'driver', 'workflow', '__init__'):
            path = 'src/research_workbench/entry/' + module + '.py'
            with self.subTest(path=path):
                self.assertIn(path, self.inventory)
                report = self.plan([path])
                self.assertEqual(['entry'], report['components'])
                self.assertEqual(expected, set(report['selected_tests']))
                self.assertEqual([], report['unknown_paths'])
                self.assertEqual(['3.11'], report['python_versions'])
                self.assertTrue(report['smoke'])
                self.assertFalse(report['install'])
                self.assertFalse(report['contracts'])

    def test_entry_support_edits_select_their_declared_consumers(self):
        consumers = {
            'tests/entry_chain_support.py': {
                'test_entry_bridge_flow', 'test_entry_caller', 'test_entry_deadline',
                'test_entry_factory', 'test_entry_intake_call',
                'test_entry_intake_constraints',
            },
            'tests/entry_factory_support.py': {
                'test_entry_caller', 'test_entry_deadline', 'test_entry_factory',
                'test_entry_intake_constraints',
            },
        }
        for path, expected in consumers.items():
            with self.subTest(path=path):
                self.assertIn(path, self.inventory)
                report = self.plan([path])
                self.assertEqual(expected, set(report['selected_tests']))
                self.assertEqual([], report['components'])
                self.assertEqual([], report['unknown_paths'])
                self.assertTrue(any(row['kind'] == 'direct-map' for row in report['reasons']))
                self.assertFalse(report['smoke'])
                self.assertFalse(report['install'])

    def test_missing_entry_regression_is_visible_in_source_only_plan(self):
        missing = 'tests/test_entry_deadline.py'
        report = self.plan(['src/research_workbench/entry/intake.py'],
                           inventory=self.inventory - {missing})
        self.assertEqual(['entry'], report['components'])
        self.assertEqual([missing], report['unknown_paths'])
        self.assertNotIn('test_entry_deadline', report['selected_tests'])
        self.assertIn('test_entry_intake_constraints', report['selected_tests'])
        self.assertTrue(any(row['kind'] == 'mapped-test-absent' and row['path'] == missing
                            for row in report['reasons']))
        self.assertTrue(report['smoke'])

    def test_entry_test_helper_edits_select_self_and_explicit_consumers(self):
        consumers = {
            'test_api_session_runner': {'test_entry_deadline'},
            'test_conformance_session_policy': {'test_entry_deadline'},
            'test_entry_bridge_flow': {'test_entry_deadline'},
            'test_entry_caller': {'test_entry_deadline', 'test_entry_intake_constraints'},
            'test_entry_driver': {'test_entry_intake_constraints'},
            'test_entry_intake': {'test_entry_intake_constraints'},
            'test_entry_intake_call': {'test_entry_deadline'},
        }
        for module, expected in consumers.items():
            path = 'tests/' + module + '.py'
            with self.subTest(path=path):
                self.assertIn(path, self.inventory)
                report = self.plan([path])
                self.assertEqual({module} | expected, set(report['selected_tests']))
                self.assertEqual([], report['components'])
                self.assertEqual([], report['unknown_paths'])
                self.assertTrue(any(row['kind'] == 'direct-map' for row in report['reasons']))
                self.assertFalse(report['smoke'])
                self.assertFalse(report['install'])
                self.assertEqual(['3.11'], report['python_versions'])

    def test_existing_test_module_maps_select_self_and_declared_consumers(self):
        consumers = {
            'test_profile_conformance_binding': {
                'test_profile_conformance_usage_consistency',
                'test_profile_conformance_extended_binding',
            },
            'test_profile_conformance_reporting': {
                'test_profile_conformance_usage_consistency',
                'test_conformance_budget_extension',
            },
            'test_profile_conformance': {'test_profile_conformance_deadlines'},
            'test_conformance_budget_extension': {'test_profile_conformance_extended_binding'},
        }
        for module, expected in consumers.items():
            path = 'tests/' + module + '.py'
            with self.subTest(path=path):
                self.assertIn(path, self.inventory)
                report = self.plan([path])
                self.assertEqual({module} | expected, set(report['selected_tests']))
                self.assertEqual([], report['components'])
                self.assertEqual([], report['unknown_paths'])
                self.assertTrue(any(row['kind'] == 'direct-map' for row in report['reasons']))
                self.assertFalse(report['smoke'])
                self.assertFalse(report['install'])
                self.assertEqual(['3.11'], report['python_versions'])

    def test_deleted_mapped_test_keeps_owner_and_explicit_consumer(self):
        path = 'tests/test_api_session_runner.py'
        report = self.plan([{'status': 'D', 'path': path}], inventory=self.inventory - {path})
        self.assertEqual(['adapters'], report['components'])
        self.assertNotIn('test_api_session_runner', report['selected_tests'])
        self.assertIn('test_entry_deadline', report['selected_tests'])
        self.assertEqual([path], report['unknown_paths'])
        self.assertTrue(any(row['kind'] == 'removed-test-owner' for row in report['reasons']))
        self.assertTrue(any(row['kind'] == 'direct-map' for row in report['reasons']))
        self.assertTrue(report['smoke'])

    def test_missing_mapped_test_consumer_stays_visible(self):
        path = 'tests/test_entry_caller.py'
        missing = 'tests/test_entry_intake_constraints.py'
        report = self.plan([path], inventory=self.inventory - {missing})
        self.assertEqual({'test_entry_caller', 'test_entry_deadline'},
                         set(report['selected_tests']))
        self.assertEqual([], report['components'])
        self.assertEqual([missing], report['unknown_paths'])
        self.assertTrue(any(row['kind'] == 'mapped-test-absent' and row['path'] == missing
                            for row in report['reasons']))
        self.assertFalse(report['smoke'])

    def test_new_and_deleted_source_stay_with_their_components(self):
        added = 'src/research_workbench/evaluation/new_worker.py'
        deleted = 'src/research_workbench/execution/recovery.py'
        report = self.plan([{'status': 'A', 'path': added}, {'status': 'D', 'path': deleted}],
                           inventory=(self.inventory - {deleted}) | {added})
        self.assertEqual(['evaluation', 'execution'], report['components'])
        expected = set(self.policy['components']['evaluation']['tests']) | set(self.policy['components']['execution']['tests'])
        self.assertEqual(expected, set(report['selected_tests']))

    def test_rename_considers_old_and_new_component_paths(self):
        old = 'src/research_workbench/adapters/models/gemini.py'
        new = 'src/research_workbench/execution/provider.py'
        report = self.plan([{'status': 'R100', 'old_path': old, 'path': new}],
                           inventory=(self.inventory - {old}) | {new})
        self.assertEqual(['adapters', 'execution'], report['components'])
        self.assertEqual({old, new}, {reason['path'] for reason in report['reasons']})

    def test_tests_are_direct_and_deleted_tests_are_not_run(self):
        path = 'tests/test_provider_adapters.py'
        self.assertEqual(['test_provider_adapters'], self.plan([path])['selected_tests'])
        report = self.plan([{'status': 'D', 'path': path}], inventory=self.inventory - {path})
        self.assertNotIn('test_provider_adapters', report['selected_tests'])
        self.assertIn('adapters', report['components'])
        self.assertIn(path, report['unknown_paths'])

    def test_shared_fixture_uses_only_its_declared_direct_map(self):
        path = 'tests/harness_fixtures.py'
        report = self.plan([path])
        self.assertEqual(sorted(self.policy['direct_tests'][path]), report['selected_tests'])
        self.assertEqual([], report['components'])
        self.assertFalse(report['smoke'])
        self.assertEqual([], report['unknown_paths'])

    def test_pure_docs_skip_product_smoke_and_install_docs_are_explicit(self):
        pure = self.plan(['README.md', 'docs/ARCHITECTURE.md'])
        self.assertEqual(['test_documentation'], pure['selected_tests'])
        self.assertTrue(pure['docs'])
        self.assertFalse(pure['smoke'])
        self.assertFalse(pure['install'])
        install = self.plan(['docs/GETTING_STARTED.md'])
        self.assertTrue(install['smoke'])
        self.assertTrue(install['install'])
        self.assertEqual(['3.11'], install['python_versions'])

    def test_schema_and_registry_changes_request_contract_checks(self):
        report = self.plan(['schemas/task.schema.json', 'registry/capabilities/requirements.json'])
        self.assertTrue(report['contracts'])
        self.assertTrue(report['smoke'])
        self.assertEqual(['capability', 'validation_schema'], report['components'])
        self.assertEqual(['3.11'], report['python_versions'])

    def test_build_change_requests_install_compatibility_smokes(self):
        report = self.plan(['pyproject.toml'])
        self.assertEqual(['build'], report['components'])
        self.assertTrue(report['install'])
        self.assertTrue(report['smoke'])
        self.assertEqual(['3.11', '3.13'], report['python_versions'])
        self.assertEqual(sorted(self.policy['components']['build']['tests']), report['selected_tests'])

    def test_ci_scripts_keep_their_own_explicit_direct_tests(self):
        common = {'test_ci_components', 'test_ci_component_execution', 'test_ci_component_smoke'}
        own = {
            'check_coverage_policy': ['test_coverage_policy'],
            'check_pr_governance': ['test_pr_governance', 'test_governance_helper_branches', 'test_release_governance'],
            'ci_checks': ['test_ci_checks'], 'ci_component_smoke': ['test_ci_component_smoke'],
            'ci_component_metadata': ['test_ci_component_metadata'],
            'ci_ruleset_migration': ['test_ci_ruleset_migration'],
            'ci_components': ['test_ci_components'], 'ci_consumer_contracts': ['test_ci_consumer_contracts'],
            'ci_consumer_shadow': ['test_ci_consumer_shadow'], 'ci_contract_shadow': ['test_ci_contract_shadow'],
            'ci_dependencies': ['test_ci_dependencies'], 'ci_domain_audit': ['test_ci_domain_audit'],
            'ci_input_facts': ['test_ci_input_facts'], 'ci_shadow_pair': ['test_ci_shadow_pair'],
            'plan_ci': ['test_ci_plan'], 'portable_package_smoke': ['test_portable_build'],
            'release_preflight': ['test_release_preflight'], 'release_source_ci': ['test_release_source_ci'],
            'release_governance': ['test_pr_governance', 'test_release_governance', 'test_release_install'],
            'release_install': ['test_pr_governance', 'test_release_governance', 'test_release_install'],
            'release_surface': ['test_release_surface', 'test_release_oracle_replay'],
            'run_component_ci': ['test_ci_component_execution'], 'selection_witness': ['test_selection_witness'],
        }
        cases = {'.github/scripts/' + name + '.py': tests for name, tests in own.items()}
        cases['tests/run_unittest_suite.py'] = ['test_test_runner']
        for path, tests in cases.items():
            with self.subTest(path=path):
                self.assertIn(path, self.inventory)
                for module in common | set(tests): self.assertIn('tests/' + module + '.py', self.inventory)
                report = self.plan([path])
                self.assertEqual(common | set(tests), set(report['selected_tests']))
                self.assertEqual(['ci_tooling'], report['components'])
                self.assertTrue(any(row['kind'] == 'direct-map' for row in report['reasons']))
                self.assertEqual([], report['unknown_paths'])
                self.assertTrue(report['smoke'])
                self.assertEqual(['3.11'], report['python_versions'])
        workflow = self.plan(['.github/workflows/ci_components.yml'])
        self.assertEqual(common | {'test_ci_component_result', 'test_ci_checkpoint'}, set(workflow['selected_tests']))

    def test_protocol_and_exclusion_policy_changes_select_position_guard(self):
        for path in (
            'tests/coverage_policy.yaml',
            'src/research_workbench/adapters/models/session.py',
            'src/research_workbench/adapters/models/session_policy.py',
            'src/research_workbench/execution/host.py',
        ):
            with self.subTest(path=path):
                report = self.plan([path])
                self.assertIn('test_coverage_policy', report['selected_tests'])
                self.assertNotIn('full', report)
                if path == 'tests/coverage_policy.yaml':
                    self.assertEqual(['ci_tooling'], report['components'])
                    self.assertTrue(report['smoke'])
                    self.assertTrue({
                        'test_ci_components', 'test_ci_component_execution',
                        'test_ci_component_smoke',
                    }.issubset(report['selected_tests']))

    def test_registry_specific_prefixes_keep_domain_owners(self):
        cases = {
            'registry/providers/adapters.yaml': (['adapters'], 'test_provider_adapters'),
            'registry/models/pool.example.yaml': (['adapters'], 'test_model_pool'),
            'registry/agents/evidence-scout.yaml': (['adapters', 'capability'], 'test_m2_registry_runtime'),
            'registry/modes/actions.json': (['protocol'], 'test_mode_actions'),
            'registry/authority/decision-authority-matrix.yaml': (['protocol'], 'test_decision_authority'),
            'registry/protocol-profiles.json': (['protocol'], 'test_protocol_profiles'),
            'registry/skills/lifecycle-v2.json': (['capability'], 'test_skill_lifecycle'),
            'registry/skill-needs.json': (['capability'], 'test_skill_needs'),
            'registry/skills/release-projections.json': (['release'], 'test_skill_release_projection'),
        }
        for path, (owners, direct_test) in cases.items():
            with self.subTest(path=path):
                self.assertIn(path, self.inventory)
                report = self.plan([path])
                self.assertEqual(owners, report['components'])
                self.assertIn(direct_test, report['selected_tests'])
                self.assertTrue(report['contracts'])
                self.assertEqual([], report['unknown_paths'])

    def test_top_level_source_and_exact_override_keep_stable_owners(self):
        for name in ('__init__', '__main__', 'cli', 'io', 'resources', 'scaffold'):
            path = 'src/research_workbench/' + name + '.py'
            with self.subTest(path=path):
                self.assertIn(path, self.inventory)
                report = self.plan([path])
                self.assertEqual(['runtime_cli'], report['components'])
                self.assertIn('test_runtime_resources', report['selected_tests'])
                self.assertEqual([], report['unknown_paths'])
        report = self.plan(['src/research_workbench/capability/release_projection.py'])
        self.assertEqual(['release'], report['components'])
        self.assertIn('test_skill_release_projection', report['selected_tests'])
        generated = 'src/research_workbench/_runtime_pin.py'
        report = self.plan([generated])
        self.assertEqual(['runtime_cli'], report['components'])
        self.assertEqual([generated], report['unknown_paths'])

    def test_unknown_path_selects_nearest_and_self_test_without_full(self):
        path = 'src/research_workbench/new_area/public_surface.py'
        report = self.plan([{'status': 'A', 'path': path}], inventory=self.inventory | {path})
        self.assertEqual([path], report['unknown_paths'])
        self.assertEqual(['runtime_cli'], report['components'])
        self.assertIn('test_public_surface', report['selected_tests'])
        self.assertTrue(any(row['kind'] == 'matching-test-module' for row in report['reasons']))
        self.assertLess(len(report['selected_tests']), len([p for p in self.inventory if p.startswith('tests/test_')]))
        self.assertNotIn('full', report)
        outside = self.plan(['unregistered/new.txt'])
        self.assertEqual(['unregistered/new.txt'], outside['unknown_paths'])
        self.assertEqual([], outside['selected_tests'])

    def test_invalid_inputs_fail_and_planning_is_deterministic_without_mutation(self):
        for path in ('../escape.py', '/absolute.py', 'src\\file.py', 'C:/file.py'):
            with self.subTest(path=path), self.assertRaises(ValueError): self.plan([path])
        bad = copy.deepcopy(self.policy)
        bad['components']['adapters']['tests'] = ['test_provider_adapters.Class.noop']
        with self.assertRaises(ValueError): self.plan(['README.md'], policy=bad)
        with self.assertRaises(ValueError): self.plan([{'status': 'R', 'path': 'new.py'}])
        before = copy.deepcopy(self.policy)
        paths = ['README.md', 'pyproject.toml', 'src/research_workbench/evaluation/harness_review.py']
        first = self.plan(paths)
        self.assertEqual(first, self.plan(list(reversed(paths)), inventory=sorted(self.inventory, reverse=True)))
        self.assertEqual(before, self.policy)


if __name__ == '__main__':
    unittest.main()
