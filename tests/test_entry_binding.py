import copy
import tempfile
import unittest
from pathlib import Path

from research_workbench.artifacts.integrity import hash_file
from research_workbench.entry.binding import (
    EntryBindingError, freeze_capability_selection, freeze_execution_inputs,
)
from research_workbench.execution import PinnedExecutionInput, load_runtime_bundle, load_resolved_execution_view
from research_workbench.io import load_document
from tests.execution_fixtures import ExecutionViewFixture, RuntimeBundleFixture


ROOT = Path(__file__).resolve().parents[1]


class EntryBindingTests(RuntimeBundleFixture, unittest.TestCase):
    def _pin(self, root, relative):
        return PinnedExecutionInput(relative, hash_file(root / relative))

    def _selection(self, root, *, runtime=False, **changes):
        self._build_bundle(root)
        if not runtime:
            evidence = load_document(ROOT / "examples/capability-resolution/conformance/no-skill-contract-check.json")
            evidence_hash = self._write(root, "bundle/conformance.yaml", evidence)
            supply = load_document(ROOT / "examples/capability-resolution/supply-reports/no-skill-contract-check.yaml")
            supply["conformance_evidence"][0]["artifact_ref"] = {"path": "bundle/conformance.yaml", "sha256": evidence_hash}
            self._write(root, "bundle/supply.yaml", supply)

        def check(identity, evidence, capability):
            reference = evidence["artifact_ref"]
            self.assertEqual(reference["sha256"], hash_file(root / reference["path"]))
            artifact = load_document(root / reference["path"])
            self.assertEqual(identity.implementation_ref, artifact["implementation_ref"])
            self.assertIn(capability, artifact["capability_ids"])
            return artifact["result"]

        parameters = dict(task=self._pin(root, "bundle/task.yaml"),
            method=self._pin(root, "bundle/method.yaml"),
            requirement=self._pin(root, "bundle/requirement.yaml"),
            supplies=[self._pin(root, "bundle/supply.yaml")],
            supporting_documents=[{"kind": "capability_conformance_evidence", "path": "bundle/conformance.yaml",
                "sha256": hash_file(root / "bundle/conformance.yaml")}],
            evidence_check=check, output_directory="frozen/control", resolution_id="CR-ENTRY-001",
            snapshot_id="RCS-ENTRY-001", evaluated_at="2026-08-26T00:00:00Z",
            qualification="runtime-execution" if runtime else "structural-replay", schema_root=ROOT / "schemas")
        parameters.update(changes)
        return parameters

    def _execution(self, root, **changes):
        fixture = ExecutionViewFixture()
        selection = freeze_capability_selection(root, **self._selection(root, runtime=True))
        manifest = load_document(root / "bundle/manifest.yaml")
        replacements = {"bundle/resolution.yaml": selection.resolution,
                        "bundle/snapshot.yaml": selection.snapshot}
        for reference in manifest["documents"]:
            if reference["path"] in replacements:
                pin = replacements[reference["path"]]
                reference.update(path=pin.path, sha256=pin.sha256)
        manifest["entrypoint"].update(path=selection.snapshot.path, sha256=selection.snapshot.sha256)
        for edge in manifest["imports"]:
            for key in ("from_path", "to_path"):
                if edge[key] in replacements:
                    edge[key] = replacements[edge[key]].path
        parameters = dict(manifest=manifest, **fixture._inputs(root),
            output_directory="frozen/execution", execution_at="2026-08-26T00:00:00Z",
            view_id="VIEW-ENTRY-001", schema_root=ROOT / "schemas")
        parameters.update(changes)
        return parameters

    def test_structural_selection_preserves_inputs_and_has_no_runtime_authority(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._selection(root)
            before = {path: hash_file(path) for path in (root / "bundle").iterdir()}
            result = freeze_capability_selection(root, **params)
            self.assertEqual("satisfied", result.status)
            self.assertIsNotNone(result.resolution)
            snapshot = load_document(root / result.snapshot.path)
            self.assertEqual("structural-replay", snapshot["qualification"])
            self.assertFalse(snapshot["boundaries"]["execution_input"])
            self.assertEqual("supply-no-skill-contract-check@1.0.0", snapshot["selected_supply_report_ref"]["ref"])
            self.assertIn("conformance-evidence: pass", (root / result.summary_path).read_text(encoding="utf-8"))
            self.assertEqual(before, {path: hash_file(path) for path in (root / "bundle").iterdir()})

    def test_runtime_requires_explicit_nonfixture_evidence_and_never_promotes_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._selection(root, runtime=True)
            result = freeze_capability_selection(root, **params)
            self.assertEqual("satisfied", result.status)
            self.assertTrue(load_document(root / result.snapshot.path)["boundaries"]["execution_input"])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._selection(root)
            params["qualification"] = "runtime-execution"
            result = freeze_capability_selection(root, **params)
            self.assertEqual("gap", result.status)
            self.assertIsNone(result.snapshot)
            self.assertEqual("gap", load_document(root / result.resolution.path)["resolution_status"])

    def test_missing_trusted_verifier_is_readable_blocked_without_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._selection(root, evidence_check=None)
            result = freeze_capability_selection(root, **params)
            self.assertEqual("blocked", result.status)
            self.assertIsNone(result.resolution)
            self.assertIsNone(result.snapshot)
            self.assertIn("Trusted evidence verifier is missing", (root / result.summary_path).read_text())

    def test_gap_empty_candidates_keeps_resolution_and_no_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._selection(root, supplies=[], evidence_check=None)
            result = freeze_capability_selection(root, **params)
            self.assertEqual("gap", result.status)
            self.assertIsNone(result.snapshot)
            self.assertEqual([], load_document(root / result.resolution.path)["comparisons"])

    def test_two_eligible_reports_remain_ambiguous_and_unselected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._selection(root)
            second = load_document(root / "bundle/supply.yaml")
            second["report_id"] = "supply-another-report"
            self._write(root, "bundle/another-supply.yaml", second)
            params["supplies"].append(self._pin(root, "bundle/another-supply.yaml"))
            result = freeze_capability_selection(root, **params)
            self.assertEqual("ambiguous", result.status)
            self.assertIsNone(result.snapshot)
            self.assertNotIn("selected_supply_report_ref", load_document(root / result.resolution.path))

    def test_permission_failure_is_blocked_in_persisted_comparisons(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._selection(root)
            requirement = load_document(root / "bundle/requirement.yaml")
            requirement["constraints"]["permission_ceiling"]["filesystem"] = "read-only"
            self._write(root, "bundle/requirement.yaml", requirement)
            params["requirement"] = self._pin(root, "bundle/requirement.yaml")
            result = freeze_capability_selection(root, **params)
            self.assertEqual("blocked", result.status)
            self.assertIsNone(result.snapshot)
            self.assertIn("permission: fail", (root / result.summary_path).read_text(encoding="utf-8"))

    def test_bad_path_hash_kind_and_method_lineage_fail_before_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._selection(root)
            for invalid in [PinnedExecutionInput("../outside.yaml", "1" * 64),
                            PinnedExecutionInput("bundle/task.yaml", "0" * 64),
                            self._pin(root, "bundle/requirement.yaml")]:
                bad = dict(params, task=invalid)
                with self.subTest(invalid=invalid), self.assertRaises((EntryBindingError, ValueError)):
                    freeze_capability_selection(root, **bad)
                self.assertFalse((root / "frozen/control").exists())
            method = load_document(root / "bundle/method.yaml")
            method["task_ref"]["sha256"] = "2" * 64
            self._write(root, "bundle/method.yaml", method)
            params["method"] = self._pin(root, "bundle/method.yaml")
            with self.assertRaisesRegex(EntryBindingError, "Method Task lineage"):
                freeze_capability_selection(root, **params)
            self.assertFalse((root / "frozen/control").exists())

    def test_method_cannot_expand_the_pinned_task_capability_demand(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._selection(root)
            method = load_document(root / "bundle/method.yaml")
            method["action_decisions"][0]["capability_requirements"].append("unrequested-capability")
            self._write(root, "bundle/method.yaml", method)
            params["method"] = self._pin(root, "bundle/method.yaml")
            with self.assertRaisesRegex(EntryBindingError, "preserve the pinned Task demand"):
                freeze_capability_selection(root, **params)
            self.assertFalse((root / "frozen/control").exists())

    def test_unconfirmed_trust_is_preserved_without_forging_contract_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._selection(root, evidence_check=lambda *_: "unknown")
            result = freeze_capability_selection(root, **params)
            self.assertEqual("blocked", result.status)
            self.assertIsNone(result.resolution)
            self.assertIsNone(result.snapshot)
            self.assertIn("conformance-evidence: unknown", (root / result.summary_path).read_text(encoding="utf-8"))

    def test_callback_cannot_mutate_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._selection(root)
            def mutate(*_):
                with (root / "bundle/task.yaml").open("a", encoding="utf-8") as stream:
                    stream.write("\n# changed by untrusted verifier\n")
                return "pass"
            params["evidence_check"] = mutate
            with self.assertRaisesRegex(EntryBindingError, "changed during freeze"):
                freeze_capability_selection(root, **params)
            self.assertFalse((root / "frozen/control").exists())

    def test_failed_external_trust_is_readable_and_does_not_rewrite_pinned_proof(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._selection(root, evidence_check=lambda *_: "fail")
            before = hash_file(root / "bundle/conformance.yaml")
            result = freeze_capability_selection(root, **params)
            self.assertEqual("blocked", result.status)
            self.assertIsNone(result.resolution)
            self.assertIsNone(result.snapshot)
            self.assertIn("conformance-evidence: fail", (root / result.summary_path).read_text(encoding="utf-8"))
            self.assertEqual(before, hash_file(root / "bundle/conformance.yaml"))

    def test_callback_cannot_forge_unsupported_evidence_class_as_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._selection(root, runtime=True, evidence_check=lambda *_: "pass")
            params["qualification"] = "structural-replay"
            # The verifier is never asked to use live evidence for structural replay.
            result = freeze_capability_selection(root, **params)
            self.assertEqual("gap", result.status)
            self.assertIsNone(result.snapshot)

    def test_explicit_bundle_and_view_round_trip_without_reselection_or_host(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._execution(root)
            result = freeze_execution_inputs(root, **params)
            bundle = load_runtime_bundle(result.bundle.path, project_root=root, schema_root=ROOT / "schemas")
            view = load_resolved_execution_view(result.view.path, expected_sha256=result.view.sha256,
                bundle=bundle, schema_root=ROOT / "schemas")
            self.assertEqual("VIEW-ENTRY-001", view.document["view_id"])
            self.assertEqual(params["manifest"]["execution_scope"], load_document(root / result.bundle.path)["execution_scope"])
            self.assertFalse(load_document(root / result.bundle.path)["boundaries"]["execution_authority"])
            self.assertIn("does not run a Host", (root / result.summary_path).read_text())

    def test_execution_reselection_is_rejected_and_failure_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._execution(root)
            binding = load_document(root / params["execution_binding"].path)
            binding["selected_supply_report_ref"] = "another-supply@1.0.0"
            self._write(root, params["execution_binding"].path, binding)
            params["execution_binding"] = self._pin(root, params["execution_binding"].path)
            with self.assertRaisesRegex(EntryBindingError, "SUPPLY-RESELECTION"):
                freeze_execution_inputs(root, **params)
            self.assertTrue((root / "frozen/execution/runtime-bundle.json").is_file())
            self.assertFalse((root / "frozen/execution/execution-view.json").exists())
            self.assertIn("blocked", (root / "frozen/execution/SUMMARY.md").read_text())

    def test_incomplete_closure_drifted_pin_and_existing_run_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = self._execution(root)
            bad = copy.deepcopy(params)
            bad["manifest"]["documents"][0]["sha256"] = "f" * 64
            with self.assertRaisesRegex(EntryBindingError, "SHA-256 mismatch"):
                freeze_execution_inputs(root, **bad)
            self.assertFalse((root / "frozen/execution").exists())
            bad = copy.deepcopy(params)
            bad["manifest"]["imports"] = bad["manifest"]["imports"][:-1]
            with self.assertRaisesRegex(EntryBindingError, "freeze blocked"):
                freeze_execution_inputs(root, **bad)
            saved = (root / "frozen/execution/SUMMARY.md").read_bytes()
            with self.assertRaises(FileExistsError):
                freeze_execution_inputs(root, **params)
            self.assertEqual(saved, (root / "frozen/execution/SUMMARY.md").read_bytes())


if __name__ == "__main__":
    unittest.main()
