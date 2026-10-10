"""Package factory checks with test-only external observations, never live grants."""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from research_workbench.artifacts.integrity import hash_file
from research_workbench.entry.binding import EntryBindingError
from research_workbench.entry.driver import ObservedExecutionBinding
from research_workbench.entry.executor import FrozenRoleExecutor
from research_workbench.execution import (
    GenericCloseoutValidationError, load_runtime_bundle,
    load_resolved_execution_view, validate_generic_execution_receipt,
)
from research_workbench.execution.host import ExecutionHostValidationError
from research_workbench.io import load_document
from research_workbench.validation.schemas import SchemaCatalog
from tests.entry_chain_support import write_document
from tests.entry_factory_support import FactoryTestInputs, make_factory
from tests.test_entry_driver import observe
from tests.execution_fixtures import SequenceClock, plain


class EntryFactoryTests(unittest.TestCase):
    def test_default_packaged_schema_freezes_exact_external_inputs_and_record_pins(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs, factory = make_factory(root)
            prior_refs = factory.record_refs
            binding = factory(inputs.invocation())
            self.assertIsNone(factory.catalog_root)
            self.assertIsNone(binding.schema_root)
            self.assertEqual((), prior_refs)
            self.assertIsInstance(factory.record_refs, tuple)
            self.assertEqual(1, len(factory.record_refs))
            pin = factory.record_refs[0]
            self.assertEqual(pin.sha256, hash_file(root / pin.path))
            self.assertEqual(factory.records[0], load_document(root / pin.path))
            self.assertEqual(inputs.task_pin.path, factory.records[0]["task"]["path"])
            self.assertEqual(inputs.method_pin.sha256, factory.records[0]["method"]["sha256"])
            load_runtime_bundle(binding.bundle_ref.path, project_root=root)
            manifest = load_document(root / binding.bundle_ref.path)
            self.assertEqual(inputs.options["action_ref"], manifest["execution_scope"]["action_ref"])
            self.assertNotIn("planning_action_id", manifest["execution_scope"])
            self.assertFalse(manifest["execution_scope"]["task_capability_closure"]["task_completion"])
            self.assertFalse(manifest["skill_extension"]["enabled"])
            self.assertEqual([], inputs.provider.requests)
            self.assertFalse((root / binding.output_dir).exists())
            with self.assertRaises(AttributeError):
                factory.record_refs = ()
            with self.assertRaises(FileExistsError):
                factory(inputs.invocation())
            self.assertEqual((pin,), factory.record_refs)

    def test_child_reuses_actual_parent_obligations_and_consuming_main_keeps_root_pins(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs, factory = make_factory(root)
            factory(inputs.invocation())
            child = inputs.child(1)
            factory(inputs.invocation("child", child, ordinal=2, depth=1))
            factory(inputs.invocation(ordinal=3))
            self.assertEqual(["main", "child", "main"], [item["role"] for item in factory.records])
            child_record = factory.records[1]
            self.assertEqual(inputs.method_pin.sha256, child_record["parent_method"]["sha256"])
            child_method = load_document(root / child_record["method"]["path"])
            self.assertEqual(inputs.method["action_decisions"], child_method["action_decisions"])
            self.assertEqual(child["task_id"], child_method["task_ref"]["task_id"])
            self.assertEqual(factory.records[0]["task"], factory.records[2]["task"])
            self.assertEqual(factory.records[0]["method"], factory.records[2]["method"])
            self.assertEqual(3, len(factory.record_refs))
            self.assertEqual([], inputs.provider.requests)

    def test_no_mode_planning_selector_freezes_executes_and_cold_replays_exact_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = FactoryTestInputs(root)
            method = copy.deepcopy(load_document(Path(__file__).resolve().parents[1]
                / "examples/method-resolutions/ROUTE-NO-MODE-FORMAT-007.yaml"))
            task = copy.deepcopy(inputs.task)
            task["active_modes"] = []
            # This test declares a local contract-check demand explicitly. The
            # original formatting example has none; no product default is added.
            requirement_id = inputs.requirement["requirement_id"]
            task["required_capabilities"] = [requirement_id]
            task["safe_pause_conditions"] = [
                "An exact input identity/hash or the authorized output write scope cannot be verified."
            ]
            task_pin = write_document(root, "controls/planning-task.json", task)
            method["task_ref"] = {"task_id": task["task_id"], "revision": task["revision"],
                                  "sha256": task_pin.sha256}
            method["action_decisions"][0]["capability_requirements"] = [requirement_id]
            # The lightweight routing fixture has no execution pause condition;
            # this explicitly execution-bound test Method carries its Task limit.
            method["action_decisions"][0]["blocked_conditions"] = copy.deepcopy(task["safe_pause_conditions"])
            method_pin = write_document(root, "controls/planning-method.json", method)
            catalog = SchemaCatalog()
            self.assertEqual([], catalog.validate("task_packet", task))
            self.assertEqual([], catalog.validate("method_resolution", method))
            self.assertEqual("no-new-mode", method["mode_resolution"]["status"])
            self.assertEqual([], method["mode_resolution"]["selected_mode_refs"])
            self.assertEqual([], task["required_skills"])
            factory = inputs.build_factory(task_pin=task_pin, method_pin=method_pin,
                action_ref=None, planning_action_id="output-format",
                schema_root=Path(__file__).resolve().parents[1] / "schemas",
                host_clock=SequenceClock("2026-08-26T00:00:01Z", "2026-08-26T00:00:02Z", "2026-08-26T00:00:03Z"))
            self.assertEqual("planning_action_id", factory.action_field)
            invocation = inputs.invocation(task=task)
            binding = factory(invocation)
            bundle = load_runtime_bundle(binding.bundle_ref.path, project_root=root,
                                         schema_root=factory.catalog_root)
            view = load_resolved_execution_view(binding.view_ref.path,
                expected_sha256=binding.view_ref.sha256, bundle=bundle, schema_root=factory.catalog_root)
            scope = plain(bundle.manifest["execution_scope"])
            self.assertEqual("planning-capability-slice", scope["kind"])
            self.assertEqual("output-format", scope["planning_action_id"])
            self.assertNotIn("action_ref", scope)
            self.assertEqual([requirement_id], scope["task_capability_closure"]["required"])
            self.assertFalse(scope["task_capability_closure"]["task_completion"])
            self.assertEqual(scope, plain(view.document["execution_scope"]))
            self.assertEqual(method_pin.sha256, view.document["method_resolution_ref"]["sha256"])
            self.assertEqual(method["action_decisions"][0]["stop_conditions"],
                             plain(view.document["stop_conditions"]))
            self.assertEqual(task["safe_pause_conditions"], plain(view.document["safe_pause_conditions"]))
            self.assertEqual(1, len(factory.record_refs))
            self.assertEqual(factory.record_refs[0].sha256, hash_file(root / factory.record_refs[0].path))
            self.assertEqual(method_pin.sha256, factory.records[0]["method"]["sha256"])
            self.assertEqual(task_pin.sha256, factory.records[0]["task"]["sha256"])
            self.assertEqual([], inputs.provider.requests)
            executor = FrozenRoleExecutor(root, binding_factory=lambda actual: binding,
                                           accountable_owner="offline planning identity test owner")
            observation = executor(invocation)
            self.assertEqual("completed", observation.status)
            self.assertEqual(1, len(inputs.provider.requests))
            result = executor.results[0]
            self.assertEqual(scope, result.host_report["execution_scope"])
            self.assertIsNotNone(result.receipt_ref, result.closeout_error)
            cold_bundle = load_runtime_bundle(binding.bundle_ref.path, project_root=root,
                                               schema_root=factory.catalog_root)
            receipt = validate_generic_execution_receipt(result.receipt_ref.path,
                expected_sha256=result.receipt_ref.sha256, bundle=cold_bundle, schema_root=factory.catalog_root)
            self.assertEqual(scope, receipt.document["execution_scope"])
            self.assertEqual("planning-capability-slice-only", receipt.document["completion_claim"])
            self.assertFalse(receipt.document["boundaries"]["task_completion"])

            # A fresh file hash cannot replace the Method namespace or scope.
            changed_view = plain(view.document)
            changed_view["method_resolution_ref"]["sha256"] = "0" * 64
            changed_pin = write_document(root, "tamper/view.json", changed_view)
            with self.assertRaises(ExecutionHostValidationError):
                load_resolved_execution_view(changed_pin.path, expected_sha256=changed_pin.sha256,
                    bundle=cold_bundle, schema_root=factory.catalog_root)
            changed_host = copy.deepcopy(result.host_report)
            changed_host["execution_scope"]["planning_action_id"] = "other-planning-id"
            host_pin = write_document(root, "tamper/host.json", changed_host)
            changed_receipt = copy.deepcopy(receipt.document)
            changed_receipt["host_report_ref"].update(path=host_pin.path, sha256=host_pin.sha256)
            receipt_pin = write_document(root, "tamper/receipt.json", changed_receipt)
            with self.assertRaises(GenericCloseoutValidationError):
                validate_generic_execution_receipt(receipt_pin.path, expected_sha256=receipt_pin.sha256,
                    bundle=cold_bundle, schema_root=factory.catalog_root)
            for claim in ("action-capability-slice-only", "none"):
                bad = copy.deepcopy(receipt.document)
                bad["completion_claim"] = claim
                self.assertTrue(SchemaCatalog(factory.catalog_root).validate("generic_execution_receipt", bad))
            bad = copy.deepcopy(receipt.document)
            bad["status"] = "failed"
            self.assertTrue(SchemaCatalog(factory.catalog_root).validate("generic_execution_receipt", bad))
            self.assertEqual(1, len(inputs.provider.requests))
            # Scripted external observations prove this offline consumer path,
            # not production qualification or scientific/Human acceptance.

    def test_mutated_requirement_cache_cannot_replace_the_actual_pinned_requirement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs, factory = make_factory(root)
            original_digest = hash_file(root / factory.requirement_pin.path)
            factory.requirement["requirement_id"] = "mutated-cache"
            with self.assertRaisesRegex(EntryBindingError, "actual Requirement changed before freeze"):
                factory(inputs.invocation())
            self.assertEqual(original_digest, hash_file(root / factory.requirement_pin.path))
            self.assertEqual((), factory.record_refs)
            self.assertEqual([], inputs.provider.requests)
            self.assertFalse((root / inputs.options["output_directory"]).exists())

    def test_explicit_selector_callbacks_and_external_evidence_are_mandatory(self):
        with tempfile.TemporaryDirectory() as temporary:
            inputs = FactoryTestInputs(Path(temporary))
            for override in ({"action_ref": None}, {"planning_action_id": "PLAN-1"},
                             {"supplies": ()}, {"conformance_refs": ()},
                             {"evidence_check": None}, {"observed_binding": None},
                             {"timestamp": None}):
                with self.subTest(override=override), self.assertRaises(EntryBindingError):
                    inputs.build_factory(**override)
            planning = inputs.build_factory(action_ref=None, planning_action_id="PLAN-1")
            with self.assertRaisesRegex(EntryBindingError, "selector"):
                planning(inputs.invocation())
            self.assertEqual([], inputs.provider.requests)

    def test_task_identity_required_skill_and_profile_permission_expansion_stop(self):
        with tempfile.TemporaryDirectory() as temporary:
            inputs, factory = make_factory(Path(temporary))
            for change in ({"objective": "changed actual content"},
                           {"task_id": "SUBSTITUTED-ROOT"},
                           {"required_skills": ["unavailable-skill@1.0.0"]}):
                task = copy.deepcopy(inputs.task)
                task.update(change)
                with self.subTest(change=change), self.assertRaises(EntryBindingError):
                    factory(inputs.invocation(task=task))
            task = copy.deepcopy(inputs.task)
            task["permissions"]["filesystem"] = "workspace-write"
            with self.assertRaisesRegex(EntryBindingError, "permissions"):
                factory(inputs.invocation(task=task))
            self.assertEqual((), factory.record_refs)
            self.assertEqual([], inputs.provider.requests)

    def test_exact_pin_drift_before_freeze_is_not_repaired(self):
        for field in ("task_pin", "method_pin", "profile_pin", "requirement_pin"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                inputs, factory = make_factory(root)
                pin = getattr(factory, field)
                with (root / pin.path).open("a", encoding="utf-8") as stream:
                    stream.write("\n")
                with self.assertRaisesRegex(EntryBindingError, "pin drift"):
                    factory(inputs.invocation())
                self.assertEqual((), factory.record_refs)
                self.assertEqual([], inputs.provider.requests)
                if field == "requirement_pin":
                    self.assertFalse((root / inputs.options["output_directory"]).exists())

    def test_child_without_parent_or_changed_capability_demand_stops(self):
        with tempfile.TemporaryDirectory() as temporary:
            inputs, factory = make_factory(Path(temporary))
            child = inputs.child(1)
            with self.assertRaisesRegex(EntryBindingError, "parent"):
                factory(inputs.invocation("child", child, ordinal=1, depth=1))
            factory(inputs.invocation())
            child["required_capabilities"].append("unrequested-capability")
            with self.assertRaisesRegex(EntryBindingError, "new actual Method"):
                factory(inputs.invocation("child", child, ordinal=2, depth=1))
            self.assertEqual(1, len(factory.record_refs))
            self.assertEqual([], inputs.provider.requests)

    def test_fixture_evidence_fixture_supply_and_skill_supply_are_not_promoted(self):
        for variant in ("evidence", "supply", "skill"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                inputs = FactoryTestInputs(root)
                if variant == "evidence":
                    document = load_document(root / "bundle/conformance.yaml")
                    document["evidence_kind"] = "deterministic-fixture"
                    document["scope"]["scope_kind"] = "synthetic-bounded-fixture"
                    pin = write_document(root, "controls/fixture-evidence.json", document)
                    factory = inputs.build_factory(conformance_refs=(pin,))
                else:
                    document = load_document(root / "bundle/supply.yaml")
                    if variant == "skill":
                        document["supply_identity"]["supply_kind"] = "skill"
                    else:
                        document["observation_scope"] = "synthetic-bounded-fixture"
                        document["availability"]["scope"]["scope_kind"] = "fixture-only"
                    pin = write_document(root, "controls/unsupported-supply.json", document)
                    factory = inputs.build_factory(supplies=(pin,))
                with self.assertRaises(EntryBindingError):
                    factory(inputs.invocation())
                self.assertEqual((), factory.record_refs)
                self.assertEqual([], inputs.provider.requests)

    def test_verifier_failure_keeps_blocked_selection_without_success_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs, factory = make_factory(root, evidence_check=lambda *args: "fail")
            with self.assertRaisesRegex(EntryBindingError, "capability freeze blocked"):
                factory(inputs.invocation())
            self.assertEqual((), factory.record_refs)
            self.assertEqual([], inputs.provider.requests)
            self.assertTrue(list(root.glob("work/**/selection/SUMMARY.md")))

    def test_method_lineage_and_nonproceed_disposition_are_preserved(self):
        for variant in ("lineage", "blocked"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                inputs = FactoryTestInputs(root)
                method = copy.deepcopy(inputs.method)
                if variant == "lineage":
                    method["task_ref"]["sha256"] = "0" * 64
                else:
                    method["resolution_status"] = "blocked"
                pin = write_document(root, "controls/nonexecuting-method.json", method)
                factory = inputs.build_factory(method_pin=pin)
                with self.assertRaises(EntryBindingError):
                    factory(inputs.invocation())
                self.assertEqual((), factory.record_refs)
                self.assertEqual([], inputs.provider.requests)

    def test_independent_observer_provider_and_selected_supply_must_agree(self):
        for variant in ("fields", "provider", "supply"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                inputs = FactoryTestInputs(Path(temporary))

                def wrong(provider):
                    actual = observe(provider)
                    binding = copy.deepcopy(actual.binding)
                    selected = actual.supply_report_ref
                    if variant == "fields":
                        binding.pop("host")
                    elif variant == "provider":
                        binding["provider"]["ref"] = "wrong-provider"
                    else:
                        selected = "wrong-supply@1.0.0"
                    return ObservedExecutionBinding(binding, selected)

                factory = inputs.build_factory(observed_binding=wrong)
                with self.assertRaises(EntryBindingError):
                    factory(inputs.invocation())
                self.assertEqual((), factory.record_refs)
                self.assertEqual([], inputs.provider.requests)

    def test_archive_paths_tools_and_independent_guide_boundary_are_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            inputs = FactoryTestInputs(Path(temporary))
            for override in ({"output_directory": "../outside"},
                             {"tools": (SimpleNamespace(side_effect="write"),)},
                             {"tools": (SimpleNamespace(side_effect="read-only"),)}):
                with self.subTest(override=override), self.assertRaises(EntryBindingError):
                    inputs.build_factory(**override)
            factory = inputs.build_factory(archive_scope=lambda invocation: "outside-task")
            with self.assertRaisesRegex(EntryBindingError, "archive scope"):
                factory(inputs.invocation())
            for role in ("intake", "guide"):
                with self.subTest(role=role), self.assertRaisesRegex(EntryBindingError, "intake or independent Guide"):
                    factory(inputs.invocation(role))
            self.assertEqual((), factory.record_refs)
            self.assertEqual([], inputs.provider.requests)


if __name__ == "__main__":
    unittest.main()
