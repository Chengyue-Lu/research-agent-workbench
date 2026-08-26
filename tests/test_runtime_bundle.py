import copy
import inspect
import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.execution.runtime_bundle import (
    RuntimeBundleValidationError,
    load_runtime_bundle,
)
from research_workbench.io import load_document


ROOT = Path(__file__).resolve().parents[1]


class RuntimeBundleTests(unittest.TestCase):
    def _write(self, root: Path, relative: str, document: object) -> str:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return hash_file(path)

    def _build_bundle(self, root: Path) -> Path:
        task_path = "bundle/task.yaml"
        method_path = "bundle/method.yaml"
        requirement_path = "bundle/requirement.yaml"
        evidence_path = "bundle/conformance.yaml"
        supply_path = "bundle/supply.yaml"
        resolution_path = "bundle/resolution.yaml"
        snapshot_path = "bundle/snapshot.yaml"

        task = copy.deepcopy(
            load_document(ROOT / "examples/method-resolution-tasks/TASK-MR-ES-FROZEN-001.yaml")
        )
        task_hash = self._write(root, task_path, task)

        method = copy.deepcopy(
            load_document(ROOT / "examples/method-resolutions/ROUTE-ES-FROZEN-001.yaml")
        )
        method["task_ref"]["sha256"] = task_hash
        method_hash = self._write(root, method_path, method)

        requirement = copy.deepcopy(
            load_document(ROOT / "registry/capabilities/requirements/research-contract-check.yaml")
        )
        requirement_hash = self._write(root, requirement_path, requirement)

        evidence = {
            "evidence_kind": "local-conformance",
            "evidence_id": "CONF-RUNTIME-NO-SKILL",
            "implementation_ref": "runtime-no-skill-contract-check",
            "implementation_version": "1.0.0",
            "capability_ids": ["research-contract-check"],
            "scope": {"scope_kind": "local-environment", "scope_ref": "test-runtime-host"},
            "checks": ["the bounded local procedure is available without a Skill package"],
            "result": "pass",
            "limitations": ["This test observation proves structural Runtime bundle closure only."],
        }
        evidence_hash = self._write(root, evidence_path, evidence)

        supply = copy.deepcopy(
            load_document(
                ROOT
                / "examples/capability-resolution/supply-reports/no-skill-contract-check.yaml"
            )
        )
        supply["observation_scope"] = "deterministic-local"
        supply["supply_identity"]["implementation_ref"] = "runtime-no-skill-contract-check"
        supply["supply_identity"]["components"][0]["component_ref"] = (
            "runtime-no-skill-contract-check"
        )
        supply["conformance_evidence"] = [
            {
                "evidence_id": evidence["evidence_id"],
                "evidence_class": "live",
                "artifact_kind": "capability-conformance-evidence",
                "artifact_ref": {"path": evidence_path, "sha256": evidence_hash},
            }
        ]
        supply["availability"] = {
            "status": "available",
            "scope": {"scope_kind": "local-environment", "scope_ref": "test-runtime-host"},
            "observed_at": "2026-08-26T00:00:00Z",
            "valid_until": "2099-12-31T23:59:59Z",
            "facts": ["The bounded no-Skill procedure is available in the named test host."],
        }
        supply["limitations"] = [
            "This local observation does not grant permission or scientific authority."
        ]
        supply_hash = self._write(root, supply_path, supply)

        resolution = copy.deepcopy(
            load_document(
                ROOT
                / "examples/capability-resolution/resolutions/no-skill-contract-check.yaml"
            )
        )
        resolution["qualification"] = "runtime-execution"
        resolution["method_resolution_ref"]["document_path"] = method_path
        resolution["method_resolution_ref"]["content_hash"] = "sha256:" + method_hash
        resolution["requirement_ref"]["document_path"] = requirement_path
        resolution["requirement_ref"]["content_hash"] = "sha256:" + requirement_hash
        resolution["candidate_supply_report_refs"][0]["document_path"] = supply_path
        resolution["candidate_supply_report_refs"][0]["content_hash"] = "sha256:" + supply_hash
        resolution_hash = self._write(root, resolution_path, resolution)

        snapshot = copy.deepcopy(
            load_document(
                ROOT
                / "examples/capability-resolution/snapshots/no-skill-contract-check.yaml"
            )
        )
        snapshot["qualification"] = "runtime-execution"
        snapshot["task_ref"]["document_path"] = task_path
        snapshot["task_ref"]["content_hash"] = "sha256:" + task_hash
        snapshot["method_resolution_ref"]["document_path"] = method_path
        snapshot["method_resolution_ref"]["content_hash"] = "sha256:" + method_hash
        snapshot["requirement_ref"]["document_path"] = requirement_path
        snapshot["requirement_ref"]["content_hash"] = "sha256:" + requirement_hash
        snapshot["resolution_ref"]["document_path"] = resolution_path
        snapshot["resolution_ref"]["content_hash"] = "sha256:" + resolution_hash
        snapshot["selected_supply_report_ref"]["document_path"] = supply_path
        snapshot["selected_supply_report_ref"]["content_hash"] = "sha256:" + supply_hash
        snapshot["supply_identity"] = copy.deepcopy(supply["supply_identity"])
        snapshot["conformance_evidence_refs"] = [
            {"path": evidence_path, "sha256": evidence_hash}
        ]
        snapshot["limitations"] = [
            "The Snapshot is qualified only for the bounded local Runtime bundle test."
        ]
        snapshot["boundaries"]["execution_input"] = True
        snapshot_hash = self._write(root, snapshot_path, snapshot)

        documents = [
            ("task_packet", task_path, task_hash),
            ("method_resolution", method_path, method_hash),
            ("capability_requirement", requirement_path, requirement_hash),
            ("capability_conformance_evidence", evidence_path, evidence_hash),
            ("capability_supply_report", supply_path, supply_hash),
            ("capability_resolution", resolution_path, resolution_hash),
            ("resolved_capability_snapshot", snapshot_path, snapshot_hash),
        ]
        imports = [
            (snapshot_path, task_path, "snapshot-task"),
            (snapshot_path, method_path, "snapshot-method"),
            (snapshot_path, requirement_path, "snapshot-requirement"),
            (snapshot_path, resolution_path, "snapshot-resolution"),
            (snapshot_path, supply_path, "snapshot-supply"),
            (snapshot_path, evidence_path, "snapshot-conformance"),
            (method_path, task_path, "method-task"),
            (resolution_path, method_path, "resolution-method"),
            (resolution_path, requirement_path, "resolution-requirement"),
            (resolution_path, supply_path, "resolution-candidate-supply"),
            (supply_path, evidence_path, "supply-conformance"),
        ]
        manifest = {
            "schema_version": "0.1.0",
            "bundle_id": "RB-NO-SKILL-LOCAL-001",
            "revision": 1,
            "profile": "runtime-bundle",
            "entrypoint": {
                "kind": "resolved_capability_snapshot",
                "path": snapshot_path,
                "sha256": snapshot_hash,
            },
            "documents": [
                {"kind": kind, "path": path, "sha256": digest}
                for kind, path, digest in documents
            ],
            "imports": [
                {"from_path": source, "to_path": target, "relation": relation}
                for source, target, relation in imports
            ],
            "skill_extension": {"enabled": False},
            "boundaries": {
                "supply_selection": False,
                "execution_authority": False,
                "permission_grant": False,
                "fallback_authority": False,
            },
        }
        manifest_path = root / "bundle/manifest.yaml"
        self._write(root, "bundle/manifest.yaml", manifest)
        return manifest_path

    def _codes(self, raised: object) -> set[str]:
        return {issue.code for issue in raised.exception.issues}

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
