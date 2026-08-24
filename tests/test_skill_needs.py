import copy
import json
import unittest
from collections import Counter
from pathlib import Path

from research_workbench.capability import SkillNeed, SkillNeedSet
from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog, validate_documents


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "registry/skill-needs.json"
NEED_ROOT = ROOT / "registry/skill-needs"
RESOLUTION_ROOT = ROOT / "examples/method-resolutions"
TASK_ROOT = ROOT / "examples/method-resolution-tasks"
MODE_ROOT = ROOT / "registry/modes"
ACTION_REGISTRY = ROOT / "registry/modes/actions.json"
CAPABILITY_INDEX = ROOT / "registry/capabilities/requirements.json"
CAPABILITY_ROOT = ROOT / "registry/capabilities/requirements"


class SkillNeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = SchemaCatalog(ROOT / "schemas")
        cls.index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        cls.paths = sorted(NEED_ROOT.glob("*.yaml"))
        cls.needs = {path: load_document(path) for path in cls.paths}
        cls.resolutions = {
            path: load_document(path)
            for path in sorted(RESOLUTION_ROOT.glob("*.yaml"))
        }
        cls.action_registry = json.loads(ACTION_REGISTRY.read_text(encoding="utf-8"))
        cls.capability_index = json.loads(CAPABILITY_INDEX.read_text(encoding="utf-8"))
        cls.validation_documents = {
            INDEX_PATH: cls.index,
            **cls.needs,
            **cls.resolutions,
            **{
                path: load_document(path)
                for path in sorted(TASK_ROOT.glob("*.yaml"))
            },
            ACTION_REGISTRY: cls.action_registry,
            **{
                ROOT / entry["document_path"]: load_document(ROOT / entry["document_path"])
                for entry in cls.action_registry["entries"]
            },
            CAPABILITY_INDEX: cls.capability_index,
            **{
                path: load_document(path)
                for path in sorted(CAPABILITY_ROOT.glob("*.yaml"))
            },
            **{
                path: load_document(path)
                for path in sorted([*MODE_ROOT.glob("*.yaml"), *MODE_ROOT.glob("v*/*.yaml")])
            },
        }

    def test_three_method_derived_needs_are_schema_valid_and_parseable(self) -> None:
        self.assertEqual(3, len(self.paths))
        for path, document in self.needs.items():
            with self.subTest(path=path.name):
                self.assertEqual([], self.catalog.validate("skill_need", document))
                parsed = SkillNeed.from_mapping(document)
                self.assertEqual(document["need_ref"], parsed.need_ref)
                self.assertFalse(parsed.boundaries.records_trial_results)
                self.assertFalse(parsed.boundaries.records_evaluation_results)
                self.assertFalse(parsed.boundaries.records_promotion_evidence)
                self.assertFalse(parsed.boundaries.records_runtime_eligibility)

    def test_integrity_index_closes_reference_identity_path_and_hash(self) -> None:
        self.assertEqual([], self.catalog.validate("skill_need_index", self.index))
        self.assertEqual([], validate_documents(self.validation_documents))
        need_set = SkillNeedSet.load(project_root=ROOT)
        self.assertEqual(
            {
                "NEED-ES-SEARCH-PLAN",
                "NEED-ES-CONFLICT-SYNTHESIS",
                "NEED-SIM-CONVERGENCE-STUDY",
            },
            {entry.need_ref for entry in need_set.entries},
        )

    def test_all_m8_need_refs_resolve_and_no_skill_remains_first_class(self) -> None:
        references = Counter(
            need_ref
            for resolution in self.resolutions.values()
            for decision in resolution["action_decisions"]
            for need_ref in decision["skill_need_refs"]
        )
        self.assertEqual(
            {
                "NEED-ES-SEARCH-PLAN": 1,
                "NEED-ES-CONFLICT-SYNTHESIS": 1,
                "NEED-SIM-CONVERGENCE-STUDY": 1,
            },
            dict(references),
        )
        indexed = {entry["need_ref"] for entry in self.index["entries"]}
        self.assertEqual(indexed, set(references))
        self.assertEqual(
            5,
            sum(
                resolution["skill_disposition"]["status"] == "no-skill"
                for resolution in self.resolutions.values()
            ),
        )

    def test_need_is_requirements_only_not_result_supply_or_admission(self) -> None:
        forbidden_keys = {
            "trial_result",
            "trial_results",
            "evaluation_result",
            "evaluation_results",
            "promotion_evidence",
            "runtime_eligibility",
            "admission",
            "candidate",
            "accepted",
            "provider",
            "model",
            "adapter_ref",
            "tool_ref",
            "skill_ref",
            "availability",
            "fallback",
        }

        def keys(value):
            if isinstance(value, dict):
                yield from value.keys()
                for nested in value.values():
                    yield from keys(nested)
            elif isinstance(value, list):
                for nested in value:
                    yield from keys(nested)

        for path, document in self.needs.items():
            with self.subTest(path=path.name):
                self.assertFalse(forbidden_keys.intersection(keys(document)))
                self.assertEqual("human", document["boundaries"]["promotion_owner"])
                self.assertFalse(document["boundaries"]["is_candidate"])
                self.assertFalse(document["boundaries"]["is_assignment"])

    def test_schema_rejects_actual_results_and_supply_fields(self) -> None:
        source = next(iter(self.needs.values()))
        for key in (
            "trial_results",
            "evaluation_result",
            "promotion_evidence",
            "runtime_eligibility",
            "provider",
            "tool_ref",
            "skill_ref",
            "availability",
            "fallback_order",
        ):
            with self.subTest(key=key):
                document = copy.deepcopy(source)
                document[key] = "forbidden-state"
                self.assertTrue(self.catalog.validate("skill_need", document))

    def test_evaluation_requirements_are_four_arm_and_reference_declared_classes(self) -> None:
        expected_arms = [
            "plain-agent",
            "plain-plus-capability",
            "mode-plus-no-skill",
            "mode-plus-candidate-skill",
        ]
        for path, document in self.needs.items():
            with self.subTest(path=path.name):
                evaluation = document["evaluation_requirements"]
                self.assertEqual(expected_arms, evaluation["comparison_arms"])
                evidence_classes = {
                    item["evidence_class_id"]
                    for item in evaluation["required_evidence_classes"]
                }
                self.assertTrue(evidence_classes)
                for criterion in evaluation["criteria"]:
                    self.assertLessEqual(set(criterion["evidence_class_refs"]), evidence_classes)

    def test_wrong_index_hash_is_blocking(self) -> None:
        documents = copy.deepcopy(self.validation_documents)
        documents[INDEX_PATH]["entries"][0]["content_hash"] = "sha256:" + "0" * 64
        self.assertIn(
            "SKILL-NEED-HASH-MISMATCH",
            {issue.code for issue in validate_documents(documents)},
        )

    def test_identity_mismatch_and_unindexed_document_are_blocking(self) -> None:
        documents = copy.deepcopy(self.validation_documents)
        documents[INDEX_PATH]["entries"][0]["need_ref"] = "NEED-RENAMED"
        codes = {issue.code for issue in validate_documents(documents)}
        self.assertIn("SKILL-NEED-IDENTITY-MISMATCH", codes)
        self.assertIn("SKILL-NEED-UNINDEXED", codes)

        documents = copy.deepcopy(self.validation_documents)
        documents[INDEX_PATH]["entries"].pop()
        self.assertIn(
            "SKILL-NEED-UNINDEXED",
            {issue.code for issue in validate_documents(documents)},
        )

    def test_unknown_method_need_and_missing_index_are_blocking(self) -> None:
        documents = copy.deepcopy(self.validation_documents)
        path = RESOLUTION_ROOT / "ROUTE-ES-SEARCH-002.yaml"
        documents[path]["action_decisions"][0]["skill_need_refs"] = ["NEED-UNKNOWN"]
        documents[path]["skill_disposition"]["need_refs"] = ["NEED-UNKNOWN"]
        self.assertIn(
            "METHOD-RESOLUTION-SKILL-NEED-MISSING",
            {issue.code for issue in validate_documents(documents)},
        )

        documents = copy.deepcopy(self.validation_documents)
        documents.pop(INDEX_PATH)
        self.assertIn(
            "SKILL-NEED-INDEX-MISSING",
            {issue.code for issue in validate_documents(documents)},
        )

    def test_action_mode_capability_and_evidence_class_drift_are_blocking(self) -> None:
        source_path = self.paths[0]
        cases = (
            (
                lambda need: need["origin_actions"][0].__setitem__(
                    "content_hash", "sha256:" + "0" * 64
                ),
                "SKILL-NEED-ACTION-HASH-MISMATCH",
            ),
            (
                lambda need: need.__setitem__("mode_refs", ["simulation@9.9.9"]),
                "SKILL-NEED-MODE-MISSING",
            ),
            (
                lambda need: need["baseline"].__setitem__(
                    "capability_requirement_refs", ["unknown-capability"]
                ),
                "SKILL-NEED-CAPABILITY-REQUIREMENT-MISSING",
            ),
            (
                lambda need: need["evaluation_requirements"]["criteria"][0].__setitem__(
                    "evidence_class_refs", ["unknown-evidence-class"]
                ),
                "SKILL-NEED-EVIDENCE-CLASS-MISSING",
            ),
        )
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                documents = copy.deepcopy(self.validation_documents)
                mutate(documents[source_path])
                self.assertIn(expected, {issue.code for issue in validate_documents(documents)})


if __name__ == "__main__":
    unittest.main()
