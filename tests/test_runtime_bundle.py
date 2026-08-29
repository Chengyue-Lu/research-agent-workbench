import copy
import inspect
import tempfile
import unittest
from pathlib import Path

from research_workbench.artifacts.integrity import hash_file
from research_workbench.execution.runtime_bundle import (
    RuntimeBundleValidationError,
    load_runtime_bundle,
)
from research_workbench.io import load_document
from tests.execution_fixtures import RuntimeBundleFixture


ROOT = Path(__file__).resolve().parents[1]


class RuntimeBundleTests(RuntimeBundleFixture, unittest.TestCase):
    def _codes(self, raised: object) -> set[str]:
        return {issue.code for issue in raised.exception.issues}

    def _rewrite_method_chain(self, root: Path, mutate) -> Path:
        manifest_path = root / "bundle/manifest.yaml"
        method = load_document(root / "bundle/method.yaml")
        mutate(method)
        method_hash = self._write(root, "bundle/method.yaml", method)

        resolution = load_document(root / "bundle/resolution.yaml")
        resolution["method_resolution_ref"]["content_hash"] = "sha256:" + method_hash
        resolution_hash = self._write(root, "bundle/resolution.yaml", resolution)

        snapshot = load_document(root / "bundle/snapshot.yaml")
        snapshot["method_resolution_ref"]["content_hash"] = "sha256:" + method_hash
        snapshot["resolution_ref"]["content_hash"] = "sha256:" + resolution_hash
        snapshot_hash = self._write(root, "bundle/snapshot.yaml", snapshot)

        manifest = load_document(manifest_path)
        manifest["entrypoint"]["sha256"] = snapshot_hash
        changed = {
            "bundle/method.yaml": method_hash,
            "bundle/resolution.yaml": resolution_hash,
            "bundle/snapshot.yaml": snapshot_hash,
        }
        for item in manifest["documents"]:
            if item["path"] in changed:
                item["sha256"] = changed[item["path"]]
        self._write(root, "bundle/manifest.yaml", manifest)
        return manifest_path

    def test_zero_skill_bundle_uses_only_explicit_exact_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self._build_bundle(root)
            unrelated = root / "unrelated/broken.yaml"
            unrelated.parent.mkdir()
            unrelated.write_text("not: [valid", encoding="utf-8")
            validated = load_runtime_bundle(
                manifest.relative_to(root), project_root=root, schema_root=ROOT / "schemas"
            )
            self.assertEqual(7, len(validated.documents))
            self.assertFalse((root / "registry").exists())
            self.assertNotIn(unrelated.resolve(), validated.documents)
            self.assertEqual((root / "bundle/snapshot.yaml").resolve(), validated.entrypoint_path)
            with self.assertRaises(TypeError):
                validated.manifest["profile"] = "maintainer-full"

    def test_directory_manifest_and_document_inputs_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(RuntimeBundleValidationError) as raised:
                load_runtime_bundle(root, project_root=root, schema_root=ROOT / "schemas")
            self.assertEqual({"RUNTIME-BUNDLE-DIRECTORY-INPUT"}, self._codes(raised))

            manifest_path = self._build_bundle(root)
            manifest = load_document(manifest_path)
            manifest["documents"][0]["path"] = "bundle"
            self._write(root, "bundle/manifest.yaml", manifest)
            with self.assertRaises(RuntimeBundleValidationError) as raised:
                load_runtime_bundle(manifest_path, project_root=root, schema_root=ROOT / "schemas")
            self.assertIn("RUNTIME-BUNDLE-DIRECTORY-INPUT", self._codes(raised))

    def test_hash_drift_and_undeclared_import_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest_path = self._build_bundle(root)
            (root / "bundle/task.yaml").write_text("changed: true\n", encoding="utf-8")
            with self.assertRaises(RuntimeBundleValidationError) as raised:
                load_runtime_bundle(manifest_path, project_root=root, schema_root=ROOT / "schemas")
            self.assertIn("RUNTIME-BUNDLE-HASH-MISMATCH", self._codes(raised))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest_path = self._build_bundle(root)
            manifest = load_document(manifest_path)
            orphan = copy.deepcopy(load_document(root / "bundle/conformance.yaml"))
            orphan["evidence_id"] = "CONF-RUNTIME-ORPHAN"
            orphan_hash = self._write(root, "bundle/orphan-conformance.yaml", orphan)
            for item in manifest["documents"]:
                if item["kind"] == "capability_conformance_evidence":
                    item["path"] = "bundle/orphan-conformance.yaml"
                    item["sha256"] = orphan_hash
            self._write(root, "bundle/manifest.yaml", manifest)
            with self.assertRaises(RuntimeBundleValidationError) as raised:
                load_runtime_bundle(manifest_path, project_root=root, schema_root=ROOT / "schemas")
            self.assertIn("RUNTIME-BUNDLE-UNDECLARED-IMPORT", self._codes(raised))

    def test_structural_replay_and_import_graph_drift_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest_path = self._build_bundle(root)
            resolution_path = root / "bundle/resolution.yaml"
            resolution = load_document(resolution_path)
            resolution["qualification"] = "structural-replay"
            new_hash = self._write(root, "bundle/resolution.yaml", resolution)
            manifest = load_document(manifest_path)
            for item in manifest["documents"]:
                if item["path"] == "bundle/resolution.yaml":
                    item["sha256"] = new_hash
            self._write(root, "bundle/manifest.yaml", manifest)
            with self.assertRaises(RuntimeBundleValidationError) as raised:
                load_runtime_bundle(manifest_path, project_root=root, schema_root=ROOT / "schemas")
            self.assertIn("RUNTIME-BUNDLE-STRUCTURAL-REPLAY", self._codes(raised))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest_path = self._build_bundle(root)
            manifest = load_document(manifest_path)
            manifest["imports"].pop()
            self._write(root, "bundle/manifest.yaml", manifest)
            with self.assertRaises(RuntimeBundleValidationError) as raised:
                load_runtime_bundle(manifest_path, project_root=root, schema_root=ROOT / "schemas")
            self.assertIn("RUNTIME-BUNDLE-IMPORT-GRAPH-MISMATCH", self._codes(raised))

    def test_hash_valid_identity_and_supply_fact_substitution_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest_path = self._build_bundle(root)
            snapshot_path = root / "bundle/snapshot.yaml"
            snapshot = load_document(snapshot_path)
            snapshot["task_ref"]["ref"] = "TASK-SUBSTITUTED@r1"
            snapshot["supply_required_permissions"]["network"] = "search-and-fetch"
            new_hash = self._write(root, "bundle/snapshot.yaml", snapshot)
            manifest = load_document(manifest_path)
            manifest["entrypoint"]["sha256"] = new_hash
            for item in manifest["documents"]:
                if item["path"] == "bundle/snapshot.yaml":
                    item["sha256"] = new_hash
            self._write(root, "bundle/manifest.yaml", manifest)
            with self.assertRaises(RuntimeBundleValidationError) as raised:
                load_runtime_bundle(manifest_path, project_root=root, schema_root=ROOT / "schemas")
            self.assertIn("RUNTIME-BUNDLE-SNAPSHOT-IDENTITY-MISMATCH", self._codes(raised))
            self.assertIn("RUNTIME-BUNDLE-SUPPLY-FACT-DRIFT", self._codes(raised))

    def test_multi_candidate_resolution_loads_only_selected_runtime_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest_path = self._build_bundle(root)
            resolution_path = root / "bundle/resolution.yaml"
            resolution = load_document(resolution_path)
            resolution["candidate_supply_report_refs"].append(
                {
                    "ref": "supply-not-selected@1.0.0",
                    "document_path": "maintainer-history/not-selected.yaml",
                    "content_hash": "sha256:" + "9" * 64,
                }
            )
            rejected_checks = copy.deepcopy(resolution["comparisons"][0]["checks"])
            rejected_checks[0] = {
                **rejected_checks[0],
                "status": "fail",
                "reason": "The upstream candidate was compared but not selected.",
            }
            resolution["comparisons"].append(
                {
                    "supply_report_ref": "supply-not-selected@1.0.0",
                    "checks": rejected_checks,
                    "eligible": False,
                }
            )
            resolution_hash = self._write(root, "bundle/resolution.yaml", resolution)
            snapshot = load_document(root / "bundle/snapshot.yaml")
            snapshot["resolution_ref"]["content_hash"] = "sha256:" + resolution_hash
            snapshot_hash = self._write(root, "bundle/snapshot.yaml", snapshot)
            manifest = load_document(manifest_path)
            manifest["entrypoint"]["sha256"] = snapshot_hash
            for item in manifest["documents"]:
                if item["path"] == "bundle/resolution.yaml":
                    item["sha256"] = resolution_hash
                elif item["path"] == "bundle/snapshot.yaml":
                    item["sha256"] = snapshot_hash
            self._write(root, "bundle/manifest.yaml", manifest)

            validated = load_runtime_bundle(
                manifest_path, project_root=root, schema_root=ROOT / "schemas"
            )
            self.assertEqual(7, len(validated.documents))
            self.assertFalse((root / "maintainer-history/not-selected.yaml").exists())

    def test_satisfied_resolution_with_two_eligible_candidates_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest_path = self._build_bundle(root)
            resolution = load_document(root / "bundle/resolution.yaml")
            resolution["candidate_supply_report_refs"].append(
                {
                    "ref": "supply-also-eligible@1.0.0",
                    "document_path": "maintainer-history/also-eligible.yaml",
                    "content_hash": "sha256:" + "8" * 64,
                }
            )
            comparison = copy.deepcopy(resolution["comparisons"][0])
            comparison["supply_report_ref"] = "supply-also-eligible@1.0.0"
            comparison["eligible"] = True
            resolution["comparisons"].append(comparison)
            resolution_hash = self._write(root, "bundle/resolution.yaml", resolution)
            snapshot = load_document(root / "bundle/snapshot.yaml")
            snapshot["resolution_ref"]["content_hash"] = "sha256:" + resolution_hash
            snapshot_hash = self._write(root, "bundle/snapshot.yaml", snapshot)
            manifest = load_document(manifest_path)
            manifest["entrypoint"]["sha256"] = snapshot_hash
            for item in manifest["documents"]:
                if item["path"] == "bundle/resolution.yaml":
                    item["sha256"] = resolution_hash
                elif item["path"] == "bundle/snapshot.yaml":
                    item["sha256"] = snapshot_hash
            self._write(root, "bundle/manifest.yaml", manifest)
            with self.assertRaises(RuntimeBundleValidationError) as raised:
                load_runtime_bundle(
                    manifest_path, project_root=root, schema_root=ROOT / "schemas"
                )
            self.assertIn(
                "RUNTIME-BUNDLE-RESOLUTION-COMPARISON-MISMATCH", self._codes(raised)
            )

    def test_unresolved_task_capability_cannot_claim_task_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest_path = self._build_bundle(root)
            manifest = load_document(manifest_path)
            manifest["execution_scope"]["task_capability_closure"]["task_completion"] = True
            self._write(root, "bundle/manifest.yaml", manifest)
            with self.assertRaises(RuntimeBundleValidationError) as raised:
                load_runtime_bundle(
                    manifest_path, project_root=root, schema_root=ROOT / "schemas"
                )
            self.assertIn("RUNTIME-BUNDLE-MANIFEST-SCHEMA", self._codes(raised))

    def test_blocked_or_split_method_resolution_cannot_enter_runtime(self) -> None:
        for status in ("blocked", "split-and-block"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self._build_bundle(root)
                manifest_path = self._rewrite_method_chain(
                    root, lambda method: method.update({"resolution_status": status})
                )
                with self.assertRaises(RuntimeBundleValidationError) as raised:
                    load_runtime_bundle(
                        manifest_path, project_root=root, schema_root=ROOT / "schemas"
                    )
                self.assertIn("RUNTIME-BUNDLE-METHOD-NOT-PROCEED", self._codes(raised))

    def test_task_capabilities_must_equal_method_action_requirement_union(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._build_bundle(root)

            def add_undeclared_requirement(method):
                method["action_decisions"][0]["capability_requirements"].append(
                    "undeclared-runtime-capability"
                )

            manifest_path = self._rewrite_method_chain(root, add_undeclared_requirement)
            with self.assertRaises(RuntimeBundleValidationError) as raised:
                load_runtime_bundle(
                    manifest_path, project_root=root, schema_root=ROOT / "schemas"
                )
            self.assertIn(
                "RUNTIME-BUNDLE-TASK-METHOD-CAPABILITY-MISMATCH", self._codes(raised)
            )

    def test_selected_supply_must_remain_in_resolution_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest_path = self._build_bundle(root)
            resolution = load_document(root / "bundle/resolution.yaml")
            resolution["candidate_supply_report_refs"][0]["ref"] = "supply-other@1.0.0"
            resolution["comparisons"][0]["supply_report_ref"] = "supply-other@1.0.0"
            resolution_hash = self._write(root, "bundle/resolution.yaml", resolution)
            snapshot = load_document(root / "bundle/snapshot.yaml")
            snapshot["resolution_ref"]["content_hash"] = "sha256:" + resolution_hash
            snapshot_hash = self._write(root, "bundle/snapshot.yaml", snapshot)
            manifest = load_document(manifest_path)
            manifest["entrypoint"]["sha256"] = snapshot_hash
            for item in manifest["documents"]:
                if item["path"] == "bundle/resolution.yaml":
                    item["sha256"] = resolution_hash
                elif item["path"] == "bundle/snapshot.yaml":
                    item["sha256"] = snapshot_hash
            # The selected-only import can no longer be derived.
            manifest["imports"] = [
                item
                for item in manifest["imports"]
                if item["relation"] != "resolution-candidate-supply"
            ]
            self._write(root, "bundle/manifest.yaml", manifest)
            with self.assertRaises(RuntimeBundleValidationError) as raised:
                load_runtime_bundle(
                    manifest_path, project_root=root, schema_root=ROOT / "schemas"
                )
            self.assertIn("RUNTIME-BUNDLE-SUPPLY-IDENTITY-MISMATCH", self._codes(raised))

    def test_runtime_module_has_no_recursive_or_evolution_imports(self) -> None:
        from research_workbench.execution import runtime_bundle

        source = inspect.getsource(runtime_bundle)
        self.assertNotIn(".rglob(", source)
        self.assertNotIn("validation.documents", source)
        self.assertNotIn("capability.skill_needs", source)
        self.assertNotIn("capability.lifecycle", source)
        self.assertNotIn("evaluation", source)


if __name__ == "__main__":
    unittest.main()
