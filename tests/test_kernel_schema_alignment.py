import json
import unittest
from pathlib import Path

from research_workbench.contracts.common import ContractError
from research_workbench.io import load_document
from research_workbench.kernel import Claim, Decision, Evidence, Method, Proposition, Question, Run
from research_workbench.kernel.objects import CLAIM_STRENGTHS


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "v0.1.0" / "research-object.schema.json").read_text(encoding="utf-8"))

OBJECT_CLASSES = {
    "question": Question,
    "proposition": Proposition,
    "method": Method,
    "run": Run,
    "evidence": Evidence,
    "claim": Claim,
    "decision": Decision,
}

OBJECT_TYPES = {
    "question": Question,
    "hypothesis": Proposition,
    "proposition": Proposition,
    "method": Method,
    "run": Run,
    "evidence": Evidence,
    "claim": Claim,
    "decision": Decision,
}

CONTENT_HASH = "a" * 64


def _definition(name: str) -> dict:
    merged: dict = {"required": [], "properties": {}}
    for part in SCHEMA["$defs"][name]["allOf"]:
        if "$ref" in part:
            continue
        merged["required"].extend(part.get("required", []))
        merged["properties"].update(part.get("properties", {}))
    return merged


def _allowed_object_types(name: str) -> set:
    constraint = _definition(name)["properties"]["object_type"]
    if "const" in constraint:
        return {constraint["const"]}
    return set(constraint["enum"])


def _minimal_document(object_type: str) -> dict:
    document = {
        "schema_version": "0.1.0",
        "object_type": object_type,
        "object_id": "X-001",
        "revision": 1,
        "status": "draft",
    }
    document.update(
        {
            "question": {"text": "What changed?", "scope": [], "known_ambiguities": []},
            "hypothesis": {"statement": "S", "assumptions": [], "applicability": []},
            "proposition": {"statement": "S", "assumptions": [], "applicability": []},
            "method": {"kind": "k", "spec_ref": "SPEC-1@1", "version": "0.1.0", "limitations": []},
            "run": {
                "method_ref": "METH-1@1",
                "input_refs": [],
                "environment_ref": "ENV-1@1",
                "started_at": "2026-01-01T00:00:00Z",
                "output_refs": [],
            },
            "evidence": {
                "kind": "k",
                "source_ref": "SRC-1@1",
                "locator": "lines 1-2",
                "statement": "s",
                "quality_flags": [],
                "content_hash": CONTENT_HASH,
            },
            "claim": {
                "statement": "c",
                "strength": "unresolved",
                "support_refs": [],
                "counterevidence_refs": [],
                "limitations": [],
            },
            "decision": {
                "decision": "d",
                "scope": [],
                "reason_refs": [],
                "actor": "human",
                "timestamp": "2026-01-01T00:00:00Z",
            },
        }[object_type]
    )
    return document


class ObjectTypeAlignmentTests(unittest.TestCase):
    def test_schema_covers_exactly_the_kernel_object_types(self) -> None:
        covered = {entry["$ref"].split("/")[-1] for entry in SCHEMA["oneOf"]}
        self.assertEqual(set(OBJECT_CLASSES), covered)

    def test_object_type_constants_stay_within_schema_constraints(self) -> None:
        for name, cls in OBJECT_CLASSES.items():
            with self.subTest(object_type=name):
                instance = cls(object_id="X-001")
                self.assertIn(instance.object_type, _allowed_object_types(name))

    def test_proposition_accepts_every_schema_object_type(self) -> None:
        allowed = _allowed_object_types("proposition")
        self.assertEqual({"hypothesis", "proposition"}, allowed)
        for object_type in allowed:
            with self.subTest(object_type=object_type):
                parsed = Proposition.from_mapping(_minimal_document(object_type))
                self.assertEqual(object_type, parsed.object_type)
                self.assertEqual(object_type, parsed.to_mapping()["object_type"])

    def test_wrong_object_type_is_rejected(self) -> None:
        document = _minimal_document("question")
        document["object_type"] = "claim"
        with self.assertRaises(ContractError):
            Question.from_mapping(document)


class RequiredFieldAlignmentTests(unittest.TestCase):
    def test_from_mapping_enforces_every_schema_required_field(self) -> None:
        base_required = SCHEMA["$defs"]["base"]["required"]
        for name, cls in OBJECT_CLASSES.items():
            object_type = "proposition" if name == "proposition" else name
            required = set(base_required) | set(_definition(name)["required"])
            for field in sorted(required):
                with self.subTest(object_type=name, field=field):
                    document = _minimal_document(object_type)
                    del document[field]
                    with self.assertRaises(ContractError):
                        cls.from_mapping(document)

    def test_evidence_content_hash_is_required_like_the_schema(self) -> None:
        self.assertIn("content_hash", _definition("evidence")["required"])
        document = _minimal_document("evidence")
        del document["content_hash"]
        with self.assertRaises(ContractError):
            Evidence.from_mapping(document)
        parsed = Evidence.from_mapping(_minimal_document("evidence"))
        self.assertEqual(CONTENT_HASH, parsed.content_hash)


class ClaimStrengthAlignmentTests(unittest.TestCase):
    def test_strength_enum_matches_the_schema(self) -> None:
        schema_enum = set(_definition("claim")["properties"]["strength"]["enum"])
        self.assertEqual(schema_enum, set(CLAIM_STRENGTHS))

    def test_from_mapping_accepts_every_schema_strength(self) -> None:
        for strength in _definition("claim")["properties"]["strength"]["enum"]:
            with self.subTest(strength=strength):
                document = _minimal_document("claim")
                document["strength"] = strength
                self.assertEqual(strength, Claim.from_mapping(document).strength)

    def test_from_mapping_rejects_strength_outside_the_schema(self) -> None:
        document = _minimal_document("claim")
        document["strength"] = "proven"
        with self.assertRaises(ContractError):
            Claim.from_mapping(document)


class ExampleRoundTripTests(unittest.TestCase):
    def test_example_objects_parse_and_roundtrip(self) -> None:
        paths = sorted((ROOT / "examples" / "objects").rglob("*.yaml"))
        self.assertTrue(paths, "expected example research objects")
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                document = load_document(path)
                cls = OBJECT_TYPES[document["object_type"]]
                parsed = cls.from_mapping(document)
                self.assertEqual(document["object_id"], parsed.object_id)
                self.assertEqual(document["object_type"], parsed.object_type)
                reparsed = cls.from_mapping(parsed.to_mapping())
                self.assertEqual(parsed.to_mapping(), reparsed.to_mapping())


if __name__ == "__main__":
    unittest.main()
