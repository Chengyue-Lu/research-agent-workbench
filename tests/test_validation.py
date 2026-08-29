import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_workbench.io import iter_documents, load_document
from research_workbench.validation.documents import Severity, load_and_validate, validate_documents
from research_workbench.validation.schemas import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]


class ValidationTests(unittest.TestCase):
    def test_rfc3339_validation_is_available_in_clean_install(self) -> None:
        errors = SchemaCatalog().validate(
            "research_object",
            {
                "schema_version": "0.1.0",
                "object_type": "decision",
                "object_id": "D-BAD-TIME",
                "revision": 1,
                "status": "accepted",
                "decision": "Reject invalid timestamps deterministically.",
                "scope": [],
                "reason_refs": [],
                "actor": "human",
                "timestamp": "not-a-timestamp",
            },
        )

        self.assertTrue(any(error.validator == "format" for error in errors))

    def test_repository_examples_and_registries_have_no_errors(self) -> None:
        paths = iter_documents([ROOT / "examples", ROOT / "registry"])
        with patch(
            "research_workbench.validation.document_core.hash_file",
            side_effect=AssertionError("loaded validation must not re-read document paths"),
        ):
            _, issues = load_and_validate(paths)
        errors = [issue for issue in issues if issue.severity == Severity.ERROR]
        self.assertEqual([], errors)

    def test_loaded_reference_hash_uses_the_same_bytes_as_its_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            capability_root = temp_root / "registry" / "capabilities"
            shutil.copytree(ROOT / "registry" / "capabilities", capability_root)
            target = capability_root / "requirements" / "document-read.yaml"
            paths = iter_documents([capability_root])

            from research_workbench.validation import documents as document_validation

            parse_bytes = document_validation.load_document_bytes

            def parse_then_change_path(path: Path, content: bytes):
                parsed = parse_bytes(path, content)
                if Path(path) == target:
                    target.write_bytes(content + b"\n# changed after the validator captured bytes\n")
                return parsed

            with patch(
                "research_workbench.validation.documents.load_document_bytes",
                side_effect=parse_then_change_path,
            ):
                _, issues = load_and_validate(paths)
            self.assertEqual([], issues)

    def test_loaded_reference_cannot_skip_hash_check_if_path_disappears(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            capability_root = temp_root / "registry" / "capabilities"
            shutil.copytree(ROOT / "registry" / "capabilities", capability_root)
            index_path = capability_root / "requirements.json"
            index = load_document(index_path)
            entry = next(
                item for item in index["entries"] if item["requirement_id"] == "document-read"
            )
            entry["content_hash"] = "sha256:" + "0" * 64
            index_path.write_text(
                json.dumps(index, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            target = capability_root / "requirements" / "document-read.yaml"
            paths = iter_documents([capability_root])

            from research_workbench.validation import documents as document_validation

            parse_bytes = document_validation.load_document_bytes

            def parse_then_remove_path(path: Path, content: bytes):
                parsed = parse_bytes(path, content)
                if Path(path) == target:
                    target.unlink()
                return parsed

            with patch(
                "research_workbench.validation.documents.load_document_bytes",
                side_effect=parse_then_remove_path,
            ):
                _, issues = load_and_validate(paths)
            self.assertIn(
                "CAPABILITY-REQUIREMENT-HASH-MISMATCH",
                {issue.code for issue in issues},
            )

    def test_required_and_forbidden_skill_conflict_is_an_error(self) -> None:
        document = {
            "schema_version": "0.1.0",
            "task_id": "T-1",
            "goal": "test",
            "required_capabilities": [],
            "required_skills": ["same"],
            "forbidden_skills": ["same"],
            "agent_profile": "test",
            "input_refs": [],
            "write_scope": ["work/T-1/**"],
            "required_outputs": [],
            "permissions": {},
            "delegation": {"allowed": False},
            "stop_conditions": ["done"],
        }
        issues = validate_documents({Path("task.json"): document})
        self.assertIn("SKILL-CONFLICT", {issue.code for issue in issues})

    def test_unversioned_forbidden_skill_conflicts_with_exact_required_version(self) -> None:
        document = {
            "schema_version": "0.1.0",
            "task_id": "T-1",
            "goal": "test",
            "required_capabilities": [],
            "required_skills": ["same@1.2.3"],
            "forbidden_skills": ["same"],
            "agent_profile": "test",
            "input_refs": [],
            "write_scope": ["work/T-1/**"],
            "required_outputs": [],
            "permissions": {},
            "delegation": {"allowed": False},
            "stop_conditions": ["done"],
        }
        issues = validate_documents({Path("task.json"): document})
        self.assertIn("SKILL-CONFLICT", {issue.code for issue in issues})

    def test_invalid_skill_selector_is_an_error(self) -> None:
        document = {
            "schema_version": "0.1.0",
            "task_id": "T-1",
            "goal": "test",
            "required_capabilities": [],
            "required_skills": ["same@latest"],
            "forbidden_skills": [],
            "agent_profile": "test",
            "input_refs": [],
            "write_scope": ["work/T-1/**"],
            "required_outputs": [],
            "permissions": {},
            "delegation": {"allowed": False},
            "stop_conditions": ["done"],
        }
        issues = validate_documents({Path("task.json"): document})
        self.assertIn("SKILL-SELECTOR-INVALID", {issue.code for issue in issues})

    def test_absolute_write_scope_is_an_error_on_any_host(self) -> None:
        document = {
            "schema_version": "0.1.0",
            "task_id": "T-1",
            "goal": "test",
            "required_capabilities": [],
            "required_skills": [],
            "agent_profile": "test",
            "input_refs": [],
            "write_scope": ["C:\\research\\**"],
            "required_outputs": [],
            "permissions": {},
            "delegation": {"allowed": False},
            "stop_conditions": ["done"],
        }
        issues = validate_documents({Path("task.json"): document})
        self.assertIn("SCOPE-ABSOLUTE", {issue.code for issue in issues})


if __name__ == "__main__":
    unittest.main()
