import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from research_workbench.capability import CapabilityRequirement, CapabilityRequirementSet
from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog, validate_documents


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "registry/capabilities/requirements.json"
REQUIREMENT_ROOT = ROOT / "registry/capabilities/requirements"
RESOLUTION_ROOT = ROOT / "examples/method-resolutions"


class CapabilityRequirementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = SchemaCatalog(ROOT / "schemas")
        cls.index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        cls.paths = sorted(REQUIREMENT_ROOT.glob("*.yaml"))
        cls.requirements = {path: load_document(path) for path in cls.paths}
        cls.documents = {INDEX_PATH: cls.index, **cls.requirements}
        cls.resolutions = {
            path: load_document(path)
            for path in sorted(RESOLUTION_ROOT.glob("*.yaml"))
        }

    def test_four_reused_demands_are_schema_valid_and_parseable(self) -> None:
        self.assertEqual(4, len(self.paths))
        for path, document in self.requirements.items():
            with self.subTest(path=path.name):
                self.assertEqual([], self.catalog.validate("capability_requirement", document))
                parsed = CapabilityRequirement.from_mapping(document)
                self.assertEqual(document["requirement_id"], parsed.requirement_id)
                self.assertFalse(parsed.constraints.permission_ceiling.external_write)

    def test_integrity_index_closes_identity_path_and_hash(self) -> None:
        self.assertEqual([], self.catalog.validate("capability_requirement_index", self.index))
        self.assertEqual([], validate_documents(self.documents))
        requirement_set = CapabilityRequirementSet.load(project_root=ROOT)
        self.assertEqual(
            {
                "bounded-compute",
                "document-read",
                "literature-search",
                "research-contract-check",
            },
            {entry.requirement_id for entry in requirement_set.entries},
        )

    def test_all_m8_references_resolve_without_changing_resolution_shape(self) -> None:
        references = Counter(
            requirement_id
            for document in self.resolutions.values()
            for decision in document["action_decisions"]
            for requirement_id in decision["capability_requirements"]
        )
        indexed = {entry["requirement_id"] for entry in self.index["entries"]}
        self.assertEqual(indexed, set(references))
        self.assertGreater(references["document-read"], 1)
        self.assertGreater(references["bounded-compute"], 1)
        for document in self.resolutions.values():
            for decision in document["action_decisions"]:
                self.assertTrue(
                    all(isinstance(item, str) for item in decision["capability_requirements"])
                )

    def test_demand_contract_has_no_supply_or_routing_fields(self) -> None:
        forbidden = {
            "provider",
            "model",
            "adapter",
            "tool",
            "skill",
            "availability",
            "available",
            "gap",
            "blocked",
            "fallback",
            "price",
        }

        def keys(value):
            if isinstance(value, dict):
                yield from value
                for nested in value.values():
                    yield from keys(nested)
            elif isinstance(value, list):
                for nested in value:
                    yield from keys(nested)

        for path, document in self.requirements.items():
            with self.subTest(path=path.name):
                self.assertFalse(forbidden.intersection(keys(document)))

    def test_schema_rejects_supply_status_and_concrete_binding_fields(self) -> None:
        source = next(iter(self.requirements.values()))
        for key in (
            "provider",
            "model",
            "adapter",
            "tool_ref",
            "skill_ref",
            "availability",
            "gap",
            "blocked",
            "fallback_order",
            "price_route",
        ):
            with self.subTest(key=key):
                document = copy.deepcopy(source)
                document[key] = "forbidden-supply-state"
                self.assertTrue(self.catalog.validate("capability_requirement", document))

    def test_unsatisfied_demand_remains_stable_without_supply(self) -> None:
        requirement_set = CapabilityRequirementSet.load(project_root=ROOT)
        selected = requirement_set.require(["literature-search", "document-read"])
        self.assertEqual(
            ["literature-search", "document-read"],
            [requirement.requirement_id for requirement in selected],
        )
        for requirement in selected:
            self.assertEqual("unchanged", requirement.unsatisfied_requirement.method_contract)
            self.assertEqual("prohibited", requirement.unsatisfied_requirement.supply_binding)
            self.assertEqual("capability-resolution", requirement.unsatisfied_requirement.next_stage)

    def test_wrong_index_hash_is_blocking(self) -> None:
        documents = copy.deepcopy(self.documents)
        documents[INDEX_PATH]["entries"][0]["content_hash"] = "sha256:" + "0" * 64
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("CAPABILITY-REQUIREMENT-HASH-MISMATCH", codes)

    def test_index_identity_mismatch_is_blocking(self) -> None:
        documents = copy.deepcopy(self.documents)
        documents[INDEX_PATH]["entries"][0]["requirement_id"] = "renamed-demand"
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("CAPABILITY-REQUIREMENT-IDENTITY-MISMATCH", codes)
        self.assertIn("CAPABILITY-REQUIREMENT-UNINDEXED", codes)

    def test_unindexed_requirement_document_is_blocking(self) -> None:
        documents = copy.deepcopy(self.documents)
        removed = documents[INDEX_PATH]["entries"].pop()
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("CAPABILITY-REQUIREMENT-UNINDEXED", codes)
        self.assertIn(removed["requirement_id"], {doc["requirement_id"] for doc in self.requirements.values()})

    def test_public_loader_rejects_unknown_fields_even_after_hash_is_recomputed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project_root = Path(temp)
            shutil.copytree(ROOT / "schemas", project_root / "schemas")
            shutil.copytree(
                ROOT / "registry/capabilities",
                project_root / "registry/capabilities",
            )
            document_path = project_root / "registry/capabilities/requirements/document-read.yaml"
            document = load_document(document_path)
            document["provider"] = "forbidden-supply-injection"
            import yaml

            document_path.write_text(
                yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            digest = hashlib.sha256(document_path.read_bytes()).hexdigest()
            index_path = project_root / "registry/capabilities/requirements.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            next(
                entry for entry in index["entries"] if entry["requirement_id"] == "document-read"
            )["content_hash"] = f"sha256:{digest}"
            index_path.write_text(
                json.dumps(index, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "schema invalid"):
                CapabilityRequirementSet.load(project_root=project_root)


if __name__ == "__main__":
    unittest.main()
