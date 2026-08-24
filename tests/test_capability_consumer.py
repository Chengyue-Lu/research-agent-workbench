import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.io import load_document
from research_workbench.validation import (
    CapabilitySnapshotValidationError,
    load_validated_capability_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = Path("examples/capability-resolution/snapshots/document-read-a.yaml")
NO_SKILL_SNAPSHOT = Path(
    "examples/capability-resolution/snapshots/no-skill-contract-check.yaml"
)


class CapabilitySnapshotConsumerTests(unittest.TestCase):
    def test_structural_snapshot_loads_only_after_repository_validation(self) -> None:
        validated = load_validated_capability_snapshot(SNAPSHOT, project_root=ROOT)
        self.assertEqual("structural-replay", validated.qualification)
        self.assertFalse(validated.runtime_execution_input)

    def test_validated_snapshot_and_closure_are_deep_read_only(self) -> None:
        validated = load_validated_capability_snapshot(SNAPSHOT, project_root=ROOT)
        with self.assertRaises(TypeError):
            validated.document["qualification"] = "runtime-execution"
        with self.assertRaises(TypeError):
            validated.document["boundaries"]["execution_input"] = True
        with self.assertRaises(AttributeError):
            validated.document["limitations"].append("mutated after validation")
        with self.assertRaises(TypeError):
            validated.documents[validated.path] = {}

    def test_runtime_consumer_rejects_structural_fixture(self) -> None:
        with self.assertRaises(CapabilitySnapshotValidationError) as raised:
            load_validated_capability_snapshot(
                SNAPSHOT,
                project_root=ROOT,
                require_runtime_execution=True,
                expected_sha256=hash_file(ROOT / SNAPSHOT),
            )
        self.assertEqual(
            {"CAPABILITY-SNAPSHOT-CONSUMER-NOT-RUNTIME-ELIGIBLE"},
            {issue.code for issue in raised.exception.issues},
        )

    def test_topic4_pin_and_execution_time_are_not_phase_b_requirements(self) -> None:
        with self.assertRaises(CapabilitySnapshotValidationError) as raised:
            load_validated_capability_snapshot(
                SNAPSHOT,
                project_root=ROOT,
                require_runtime_execution=True,
            )
        self.assertEqual(
            {"CAPABILITY-SNAPSHOT-CONSUMER-NOT-RUNTIME-ELIGIBLE"},
            {issue.code for issue in raised.exception.issues},
        )

    def test_external_hash_rejects_same_identity_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project_root = Path(temp)
            shutil.copytree(ROOT / "registry", project_root / "registry")
            shutil.copytree(ROOT / "examples", project_root / "examples")
            snapshot_path = project_root / SNAPSHOT
            expected = hash_file(snapshot_path)
            snapshot = load_document(snapshot_path)
            snapshot["limitations"].append(
                "Same identity and revision, but rewritten bytes must not replace the external pin."
            )
            snapshot_path.write_text(
                yaml.safe_dump(snapshot, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            with self.assertRaises(CapabilitySnapshotValidationError) as raised:
                load_validated_capability_snapshot(
                    SNAPSHOT,
                    project_root=project_root,
                    require_runtime_execution=True,
                    expected_sha256=expected,
                )
            self.assertEqual(
                {"CAPABILITY-SNAPSHOT-CONSUMER-HASH-MISMATCH"},
                {issue.code for issue in raised.exception.issues},
            )

    def test_external_hash_is_bound_to_the_bytes_parsed_by_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project_root = Path(temp)
            shutil.copytree(ROOT / "registry", project_root / "registry")
            shutil.copytree(ROOT / "examples", project_root / "examples")
            snapshot_path = project_root / SNAPSHOT
            expected = hash_file(snapshot_path)

            from research_workbench.validation import documents as document_validation

            load_documents = document_validation.load_and_validate

            def swap_then_load(paths):
                snapshot_path.write_bytes(
                    snapshot_path.read_bytes()
                    + b"\n# replaced after the caller supplied its external pin\n"
                )
                return load_documents(paths)

            with patch(
                "research_workbench.validation.capability.load_and_validate",
                side_effect=swap_then_load,
            ):
                with self.assertRaises(CapabilitySnapshotValidationError) as raised:
                    load_validated_capability_snapshot(
                        SNAPSHOT,
                        project_root=project_root,
                        require_runtime_execution=True,
                        expected_sha256=expected,
                    )
            self.assertEqual(
                {"CAPABILITY-SNAPSHOT-CONSUMER-HASH-MISMATCH"},
                {issue.code for issue in raised.exception.issues},
            )

    def test_unknown_field_is_rejected_even_when_parser_could_ignore_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project_root = Path(temp)
            shutil.copytree(ROOT / "registry", project_root / "registry")
            shutil.copytree(ROOT / "examples", project_root / "examples")
            snapshot_path = project_root / SNAPSHOT
            snapshot = load_document(snapshot_path)
            snapshot["fallback"] = "forbidden"
            snapshot_path.write_text(
                yaml.safe_dump(snapshot, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            with self.assertRaises(CapabilitySnapshotValidationError) as raised:
                load_validated_capability_snapshot(SNAPSHOT, project_root=project_root)
            self.assertIn("SCHEMA-INVALID", {issue.code for issue in raised.exception.issues})

    def test_no_skill_method_rejects_skill_component_after_closure_rehash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project_root = Path(temp)
            shutil.copytree(ROOT / "registry", project_root / "registry")
            shutil.copytree(ROOT / "examples", project_root / "examples")

            supply_path = project_root / Path(
                "examples/capability-resolution/supply-reports/no-skill-contract-check.yaml"
            )
            resolution_path = project_root / Path(
                "examples/capability-resolution/resolutions/no-skill-contract-check.yaml"
            )
            snapshot_path = project_root / NO_SKILL_SNAPSHOT

            supply = load_document(supply_path)
            supply["supply_identity"]["components"].append(
                {
                    "component_kind": "skill",
                    "component_ref": "forbidden-skill-component",
                    "version": "1.0.0",
                    "content_hash": "sha256:" + "4" * 64,
                }
            )
            supply_path.write_text(
                yaml.safe_dump(supply, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            supply_hash = hash_file(supply_path)

            resolution = load_document(resolution_path)
            resolution["candidate_supply_report_refs"][0]["content_hash"] = (
                "sha256:" + supply_hash
            )
            resolution_path.write_text(
                yaml.safe_dump(resolution, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            resolution_hash = hash_file(resolution_path)

            snapshot = load_document(snapshot_path)
            snapshot["selected_supply_report_ref"]["content_hash"] = (
                "sha256:" + supply_hash
            )
            snapshot["resolution_ref"]["content_hash"] = "sha256:" + resolution_hash
            snapshot["supply_identity"] = supply["supply_identity"]
            snapshot_path.write_text(
                yaml.safe_dump(snapshot, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            with self.assertRaises(CapabilitySnapshotValidationError) as raised:
                load_validated_capability_snapshot(
                    NO_SKILL_SNAPSHOT, project_root=project_root
                )
            self.assertIn(
                "CAPABILITY-RESOLUTION-NO-SKILL-SUPPLY",
                {issue.code for issue in raised.exception.issues},
            )


if __name__ == "__main__":
    unittest.main()
