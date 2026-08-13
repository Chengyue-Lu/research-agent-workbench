import unittest
from pathlib import Path

from research_workbench.io import iter_documents
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
        _, issues = load_and_validate(paths)
        errors = [issue for issue in issues if issue.severity == Severity.ERROR]
        self.assertEqual([], errors)

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
