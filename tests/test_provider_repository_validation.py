"""Provider candidates enter repository validation without replacing v1."""
import copy
import json
from pathlib import Path
import unittest

from research_workbench.io import load_document
from research_workbench.validation.document_kinds import infer_document_kind
from research_workbench.validation.documents import validate_documents
from research_workbench.validation.schemas import SchemaCatalog


ROOT = Path(__file__).resolve().parents[1]


class ProviderRepositoryValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = SchemaCatalog(ROOT / "schemas")

    def issues(self, document):
        return validate_documents({Path("provider-candidate.json"): document}, schema_catalog=self.catalog)

    def test_new_config_schema_preserves_legacy_hand_validation(self):
        self.assertEqual(self.catalog.schema("provider-adapters-v2"),
                         self.catalog.schema_for_kind("provider_adapters_v2"))
        # Legacy adapters have always used the repository's required-field
        # checks. Adding v2 must not redirect them into the new closed schema.
        self.assertNotIn("provider_adapters", self.catalog.document_kinds)

    def test_eleven_profiles_are_structurally_valid_without_live_acceptance(self):
        paths = sorted((ROOT / "registry/providers/profiles").glob("*.json"))
        self.assertEqual(11, len(paths))
        for path in paths:
            with self.subTest(path=path.name):
                document = json.loads(path.read_bytes())
                self.assertEqual("provider_api_profile", infer_document_kind(document))
                self.assertEqual([], self.issues(document))
                invalid = copy.deepcopy(document)
                invalid["unexpected_native_options"] = {}
                self.assertTrue(any(item.code == "SCHEMA-INVALID" for item in self.issues(invalid)))

    def test_disabled_v2_registry_and_unknown_versions_use_closed_new_schema(self):
        document = json.loads((ROOT / "registry/providers/adapters-v2.disabled.json").read_bytes())
        self.assertTrue(all(row["enabled"] is False for row in document["adapters"]))
        self.assertEqual("provider_adapters_v2", infer_document_kind(document))
        self.assertEqual([], self.issues(document))
        for version in ("1.0.0", "3.0.0", None, True):
            with self.subTest(version=version):
                invalid = copy.deepcopy(document)
                invalid["config_version"] = version
                issues = self.issues(invalid)
                self.assertTrue(any(item.code == "SCHEMA-INVALID" for item in issues))
                self.assertFalse(any(item.code == "FIELD-MISSING" for item in issues))

    def test_v2_duplicate_adapter_ids_are_rejected(self):
        document = json.loads((ROOT / "registry/providers/adapters-v2.disabled.json").read_bytes())
        document["adapters"].append(copy.deepcopy(document["adapters"][0]))
        self.assertTrue(any(item.code == "PROVIDER-ADAPTER-DUPLICATE" for item in self.issues(document)))

    def test_legacy_disabled_registry_keeps_original_required_fields(self):
        document = load_document(ROOT / "registry/providers/adapters.yaml")
        self.assertEqual("provider_adapters", infer_document_kind(document))
        self.assertEqual([], self.issues(document))
        invalid = copy.deepcopy(document)
        del invalid["adapters"][0]["provider"]
        self.assertTrue(any(item.code == "FIELD-MISSING" for item in self.issues(invalid)))

    def test_binding_and_explicit_session_policy_are_recognized(self):
        self.assertEqual("provider_binding_manifest", infer_document_kind({"record_kind": "provider_binding_manifest"}))
        self.assertTrue(any(item.code == "SCHEMA-INVALID" for item in self.issues({"record_kind": "provider_binding_manifest"})))
        policy = {"policy_id": "flash-tool-transition", "version": "1.0.0",
                  "initial_choice": {"kind": "specific", "name": "echo"},
                  "after_successful_tool_result": {"kind": "none", "name": None},
                  "expected_tool_name": "echo", "expected_tool_calls": 1,
                  "max_model_turns": 2, "max_tool_calls": 1}
        self.assertEqual("conformance_session_policy", infer_document_kind(policy))
        self.assertEqual([], self.issues(policy))
        policy["max_tool_calls"] = 2
        self.assertTrue(any(item.code == "SCHEMA-INVALID" for item in self.issues(policy)))


if __name__ == "__main__":
    unittest.main()
