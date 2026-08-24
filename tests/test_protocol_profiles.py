import copy
import json
import unittest
from pathlib import Path

from research_workbench.io import load_document
from research_workbench.protocol import ProtocolProfile, ProtocolProfileSet
from research_workbench.validation import SchemaCatalog, validate_documents


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "registry/protocol-profiles.json"
PROFILE_ROOT = ROOT / "registry/protocol-profiles"
MODE_ROOT = ROOT / "registry/modes"
ACTION_REGISTRY = ROOT / "registry/modes/actions.json"


class ProtocolProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = SchemaCatalog(ROOT / "schemas")
        cls.index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        cls.paths = sorted(PROFILE_ROOT.glob("*.yaml"))
        cls.profiles = {path: load_document(path) for path in cls.paths}
        cls.action_registry = json.loads(ACTION_REGISTRY.read_text(encoding="utf-8"))
        cls.validation_documents = {
            INDEX_PATH: cls.index,
            **cls.profiles,
            ACTION_REGISTRY: cls.action_registry,
            **{
                ROOT / entry["document_path"]: load_document(ROOT / entry["document_path"])
                for entry in cls.action_registry["entries"]
            },
            **{
                path: load_document(path)
                for path in sorted([*MODE_ROOT.glob("*.yaml"), *MODE_ROOT.glob("v*/*.yaml")])
            },
        }

    def test_two_bounded_profiles_are_schema_valid_and_parseable(self) -> None:
        self.assertEqual(2, len(self.paths))
        self.assertEqual(
            {
                "prisma-systematic-review-reporting@1.0.0",
                "simulation-vv-assurance@1.0.0",
            },
            {
                ProtocolProfile.from_mapping(document).reference
                for document in self.profiles.values()
            },
        )
        for path, document in self.profiles.items():
            with self.subTest(path=path.name):
                self.assertEqual([], self.catalog.validate("protocol_profile", document))
                parsed = ProtocolProfile.from_mapping(document)
                self.assertTrue(parsed.applicability.applicable_when)
                self.assertTrue(parsed.applicability.not_applicable_when)
                self.assertEqual("bounded-subset", parsed.method_standard.profile_scope)
                self.assertEqual("not-established", parsed.method_standard.compliance_claim)

    def test_integrity_index_closes_identity_path_and_hash(self) -> None:
        self.assertEqual([], self.catalog.validate("protocol_profile_index", self.index))
        self.assertEqual([], validate_documents(self.validation_documents))
        loaded = ProtocolProfileSet.load(project_root=ROOT)
        self.assertEqual(
            {entry["profile_ref"] for entry in self.index["entries"]},
            {entry.profile_ref for entry in loaded.entries},
        )

    def test_profiles_add_obligations_without_owning_workflow_or_execution(self) -> None:
        forbidden_keys = {
            "steps",
            "sequence",
            "workflow",
            "global_dag",
            "skill_ref",
            "tool_ref",
            "provider_ref",
            "adapter_ref",
            "runtime_ref",
            "fallback",
            "route",
            "claim_effects",
            "required_artifacts",
        }

        def keys(value):
            if isinstance(value, dict):
                yield from value.keys()
                for nested in value.values():
                    yield from keys(nested)
            elif isinstance(value, list):
                for nested in value:
                    yield from keys(nested)

        for path, document in self.profiles.items():
            with self.subTest(path=path.name):
                self.assertFalse(forbidden_keys.intersection(keys(document)))
                self.assertTrue(all(value is False for value in document["boundaries"].values()))
                self.assertTrue(
                    all(gate["effect"] == "additive-only" for gate in document["gate_expectations"])
                )

    def test_obligation_references_are_closed_and_do_not_encode_order(self) -> None:
        for path, document in self.profiles.items():
            with self.subTest(path=path.name):
                actions = {item["action_ref"] for item in document["scoped_actions"]}
                evidence = {
                    item["expectation_id"] for item in document["evidence_expectations"]
                }
                gates = {item["gate_ref"] for item in document["gate_expectations"]}
                covered: set[str] = set()
                for obligation in document["method_obligations"]:
                    self.assertLessEqual(set(obligation["applies_to_action_refs"]), actions)
                    self.assertLessEqual(set(obligation["evidence_expectation_refs"]), evidence)
                    self.assertLessEqual(set(obligation["gate_expectation_refs"]), gates)
                    covered.update(obligation["applies_to_action_refs"])
                self.assertEqual(actions, covered)
                self.assertNotIn("order", document)
                self.assertNotIn("depends_on", document)

    def test_schema_rejects_supply_routing_claim_and_sequence_fields(self) -> None:
        source = next(iter(self.profiles.values()))
        for key in (
            "steps",
            "workflow",
            "skill_ref",
            "tool_ref",
            "provider_ref",
            "runtime_ref",
            "fallback_order",
            "claim_effects",
            "permission_grant",
        ):
            with self.subTest(key=key):
                document = copy.deepcopy(source)
                document[key] = "forbidden"
                self.assertTrue(self.catalog.validate("protocol_profile", document))

    def test_wrong_index_hash_and_unindexed_document_are_blocking(self) -> None:
        documents = copy.deepcopy(self.validation_documents)
        documents[INDEX_PATH]["entries"][0]["content_hash"] = "sha256:" + "0" * 64
        self.assertIn(
            "PROTOCOL-PROFILE-HASH-MISMATCH",
            {issue.code for issue in validate_documents(documents)},
        )

        documents = copy.deepcopy(self.validation_documents)
        documents[INDEX_PATH]["entries"].pop()
        self.assertIn(
            "PROTOCOL-PROFILE-UNINDEXED",
            {issue.code for issue in validate_documents(documents)},
        )

    def test_unknown_mode_action_and_hash_drift_are_blocking(self) -> None:
        source_path = self.paths[0]
        cases = (
            (
                lambda profile: profile.__setitem__(
                    "compatible_mode_refs", ["unknown-mode@9.9.9"]
                ),
                "PROTOCOL-PROFILE-MODE-MISSING",
            ),
            (
                lambda profile: profile["scoped_actions"][0].__setitem__(
                    "action_ref", "UNKNOWN-A1@9.9.9"
                ),
                "PROTOCOL-PROFILE-ACTION-MISSING",
            ),
            (
                lambda profile: profile["scoped_actions"][0].__setitem__(
                    "content_hash", "sha256:" + "0" * 64
                ),
                "PROTOCOL-PROFILE-ACTION-HASH-MISMATCH",
            ),
        )
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                documents = copy.deepcopy(self.validation_documents)
                mutate(documents[source_path])
                self.assertIn(expected, {issue.code for issue in validate_documents(documents)})

    def test_unknown_obligation_references_and_uncovered_action_are_blocking(self) -> None:
        source_path = self.paths[0]
        mutations = (
            (
                lambda profile: profile["method_obligations"][0].__setitem__(
                    "applies_to_action_refs", ["UNKNOWN-A1@9.9.9"]
                ),
                "PROTOCOL-PROFILE-OBLIGATION-ACTION-MISSING",
            ),
            (
                lambda profile: profile["method_obligations"][0].__setitem__(
                    "evidence_expectation_refs", ["UNKNOWN-EVIDENCE"]
                ),
                "PROTOCOL-PROFILE-OBLIGATION-EVIDENCE-MISSING",
            ),
            (
                lambda profile: profile["method_obligations"][0].__setitem__(
                    "gate_expectation_refs", ["unknown-gate"]
                ),
                "PROTOCOL-PROFILE-OBLIGATION-GATE-MISSING",
            ),
        )
        for mutate, expected in mutations:
            with self.subTest(expected=expected):
                documents = copy.deepcopy(self.validation_documents)
                mutate(documents[source_path])
                codes = {issue.code for issue in validate_documents(documents)}
                self.assertIn(expected, codes)
                if expected == "PROTOCOL-PROFILE-OBLIGATION-ACTION-MISSING":
                    self.assertIn("PROTOCOL-PROFILE-ACTION-UNCOVERED", codes)


if __name__ == "__main__":
    unittest.main()
