"""Typed v0.3.0 projection tests, executed only by the coordinating Root."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from research_workbench.entry.materials import read_material_inputs
from research_workbench.entry.working_inputs import WorkingInputError, project_working_input
from research_workbench.entry.working_material_inputs import project_working_material_input

ROOT = Path(__file__).resolve().parents[1]


def snapshot(path, text):
    return {"path": path, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "text": text}


def pin(value):
    return {key: value[key] for key in ("path", "sha256", "revision") if key in value}


def ordinary(value):
    return {**value, "material_provenance": {"kind": "ordinary-input", "source_relation": "not-declared",
        "scientific_qualification": "not-established", "gap": "No declared source relation."}}


def fixture(source=False, result=False):
    materials = [ordinary(snapshot("inputs/question.txt", "费用 budget / ledger 的问题。\r\n"))]
    if source:
        raw = snapshot("sources/raw/paper.txt", "raw synthetic bytes; fee discussion\r\n")
        derived = snapshot("derived/excerpt.txt", "selected derivative\r\n")
        acquisition = {"origin": {"device": "offline-fixture"},
                       "acquired_at": "2026-10-11T01:30:00+08:00", "operator": "test"}
        parser = {"name": "utf8", "version": "1"}
        admission_document = {"schema_version": "0.1.0", "admission_id": "ADMISSION-TEST",
            "original_filename": "paper.txt", "admitted_path": raw["path"], "sha256": raw["sha256"],
            "acquisition": acquisition, "parser": parser, "license_or_data_use": "synthetic fixture",
            "sensitivity": "synthetic", "egress_restriction": "no-external",
            "derivatives": [{**pin(derived), "relation": "text-excerpt"}]}
        sidecar = snapshot(raw["path"] + ".admission.yaml", json.dumps(admission_document, ensure_ascii=False))
        base = {"schema_version": "0.1.0", "admission_id": "ADMISSION-TEST",
            "raw_ref": pin(raw), "admission_ref": pin(sidecar), "acquisition": acquisition,
            "parser": parser, "license_or_data_use": "synthetic fixture", "sensitivity": "synthetic",
            "egress_restriction": "no-external",
            "verification_scope": "selected-input-bytes-and-declared-source-relation",
            "scientific_qualification": "not-established", "permission_grant": False}
        materials.extend([
            {**raw, "material_provenance": {"kind": "raw-source", **copy.deepcopy(base)}},
            {**sidecar, "material_provenance": {"kind": "source-admission", **copy.deepcopy(base)}},
            {**derived, "material_provenance": {"kind": "source-derivative", **copy.deepcopy(base),
                                          "derivative_ref": pin(derived), "relation": "text-excerpt"}},
        ])
    results = []
    if result:
        captured = snapshot("results/handoff.txt", "Result text discusses budget; status is unknown.\r\n")
        results.append({"kind": "formal-handoff", "source_ref": pin(captured), "text": captured["text"]})
    task = {"schema_version": "0.1.0", "task_id": "WORK-MATERIALS-TEST", "revision": 1,
        "goal": "Compare fee and budget assumptions.", "atomic_boundary": "One pinned comparison.",
        "question_refs": ["Q-FEE"], "active_modes": [], "agent_profile": "local-no-skill",
        "required_capabilities": [], "required_skills": [], "forbidden_skills": [],
        "input_refs": [pin(item) for item in materials] + [item["source_ref"] for item in results],
        "permissions": {"filesystem": "read-only", "network": "forbidden", "external_write": False},
        "delegation": {"allowed": False, "sub_budget": {"max_turns": 1}},
        "budget": {"max_turns": 4}, "write_scope": ["work/WORK-MATERIALS-TEST/**"],
        "required_outputs": ["comparison"], "completion_checks": ["Return a traceable comparison."]}
    args = {"role": "guide", "responsibilities": ["Read only the approved captures."],
        "materials": materials, "results": results,
        "stop_conditions": [{"kind": "human-gate", "condition": "Stop at required human decision."}],
        "necessary_decisions": [{"statement": "Keep fees in the user question.", "source_ref": pin(materials[0])}],
        "counterevidence": [{"statement": "Budget prose is not a quota.", "source_ref": pin(materials[0])}]}
    return task, args


class WorkingMaterialProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = Draft202012Validator(json.loads(
            (ROOT / "schemas/v0.3.0/model-working-input.schema.json").read_text(encoding="utf-8")))

    def test_ordinary_input_unknown_relation_and_cost_prose_are_preserved(self):
        task, args = fixture()
        value = project_working_material_input(task, **args)
        self.validator.validate(value)
        self.assertEqual("0.3.0", value["schema_version"])
        self.assertEqual(args["materials"], value["materials"])
        self.assertEqual(task["goal"], value["objective"]["goal"])
        self.assertEqual(args["necessary_decisions"], value["necessary_decisions"])
        self.assertEqual(args["counterevidence"], value["counterevidence"])
        self.assertEqual([], value["results"])
        self.assertNotIn("budget", value)
        self.assertTrue(all(flag is False for flag in value["boundaries"].values()))

    def test_complete_source_closure_from_actual_material_reader_is_consumed(self):
        task, args = fixture(source=True)
        with tempfile.TemporaryDirectory() as directory:
            for material in args["materials"]:
                path = Path(directory) / material["path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(material["text"].encode("utf-8"))
            captures = read_material_inputs(directory, task["input_refs"])
        value = project_working_material_input(task, **{**args, "materials": captures})
        self.validator.validate(value)
        self.assertEqual(["ordinary-input", "raw-source", "source-admission", "source-derivative"],
                         [item["material_provenance"]["kind"] for item in value["materials"]])
        self.assertEqual("text-excerpt", value["materials"][-1]["material_provenance"]["relation"])

    def test_result_is_a_separate_capture_without_contract_or_completion_acceptance(self):
        task, args = fixture(result=True)
        value = project_working_material_input(task, **args)
        self.validator.validate(value)
        self.assertEqual(1, len(value["materials"]))
        result = value["results"][0]
        self.assertEqual(args["results"][0]["text"], result["text"])
        self.assertEqual("not-established", result["contract_validation"])
        self.assertEqual("not-established", result["scientific_qualification"])
        self.assertIs(False, result["task_completion"])
        self.assertNotIn("material_provenance", result)

    def test_projection_is_deterministic_and_detached(self):
        task, args = fixture(source=True, result=True)
        before = copy.deepcopy((task, args))
        first = project_working_material_input(task, **args)
        self.assertEqual(first, project_working_material_input(task, **args))
        first["materials"][1]["material_provenance"]["parser"]["version"] = "changed"
        first["results"][0]["source_ref"]["path"] = "changed"
        self.assertEqual(before, (task, args))

    def test_material_and_result_hashes_and_task_membership_are_rechecked(self):
        task, args = fixture(source=True, result=True)
        variants = []
        changed = copy.deepcopy(args); changed["materials"][1]["text"] = "drift"; variants.append(changed)
        changed = copy.deepcopy(args); changed["results"][0]["text"] = "drift"; variants.append(changed)
        changed = copy.deepcopy(args); changed["results"][0]["source_ref"]["path"] = "ungranted.txt"; variants.append(changed)
        changed = copy.deepcopy(args); changed["results"][0]["source_ref"]["revision"] = 2; variants.append(changed)
        for changed in variants:
            with self.subTest(changed=changed), self.assertRaises(WorkingInputError):
                project_working_material_input(task, **changed)

    def test_material_and_result_slots_cannot_duplicate_a_capture(self):
        task, args = fixture()
        item = args["materials"][0]
        result = {"kind": "result-artifact", "source_ref": pin(item), "text": item["text"]}
        with self.assertRaises(WorkingInputError):
            project_working_material_input(task, **{**args, "results": [result]})

    def test_missing_or_mismatched_captured_source_edges_are_rejected(self):
        task, args = fixture(source=True)
        variants = []
        changed = copy.deepcopy(args); del changed["materials"][2]; variants.append(changed)
        changed = copy.deepcopy(args); changed["materials"][3]["material_provenance"]["derivative_ref"] = pin(changed["materials"][1]); variants.append(changed)
        changed = copy.deepcopy(args); changed["materials"][3]["material_provenance"]["raw_ref"]["sha256"] = "0" * 64; variants.append(changed)
        changed = copy.deepcopy(args); changed["materials"][3]["material_provenance"]["parser"]["version"] = "different"; variants.append(changed)
        changed = copy.deepcopy(args); changed["materials"][2]["material_provenance"]["kind"] = "raw-source"; variants.append(changed)
        for changed in variants:
            with self.subTest(changed=changed), self.assertRaises(WorkingInputError):
                project_working_material_input(task, **changed)

    def test_nested_provenance_extras_are_rejected(self):
        task, args = fixture(source=True)
        for location in ("root", "acquisition", "origin", "parser", "raw_ref"):
            changed = copy.deepcopy(args)
            target = changed["materials"][1]["material_provenance"]
            if location == "origin": target = target["acquisition"]["origin"]
            elif location != "root": target = target[location]
            target["caller_context"] = {"ledger": "should not enter work"}
            with self.subTest(location=location), self.assertRaises(WorkingInputError):
                project_working_material_input(task, **changed)

    def test_unknown_versions_and_false_qualification_claims_are_rejected(self):
        task, args = fixture(source=True)
        for field, value in (("schema_version", "0.3.0"), ("permission_grant", True),
                             ("scientific_qualification", "accepted"), ("verification_scope", "scientific-proof")):
            changed = copy.deepcopy(args)
            changed["materials"][1]["material_provenance"][field] = value
            with self.subTest(field=field), self.assertRaises(WorkingInputError):
                project_working_material_input(task, **changed)
        task["schema_version"] = "0.3.0"
        with self.assertRaises(WorkingInputError): project_working_material_input(task, **args)

    def test_ordinary_provenance_cannot_disguise_a_raw_source(self):
        task, args = fixture(source=True)
        changed = copy.deepcopy(args)
        changed["materials"][1] = ordinary(changed["materials"][1])
        with self.assertRaises(WorkingInputError): project_working_material_input(task, **changed)

    def test_result_input_rejects_qualification_claims_and_untyped_context(self):
        task, args = fixture(result=True)
        for field, value in (("scientific_qualification", "accepted"), ("permission_grant", True),
                             ("task_completion", True), ("caller_context", {"task": task})):
            changed = copy.deepcopy(args); changed["results"][0][field] = value
            with self.subTest(field=field), self.assertRaises(WorkingInputError):
                project_working_material_input(task, **changed)
        changed = copy.deepcopy(args); changed["results"][0]["kind"] = "unknown-result"
        with self.assertRaises(WorkingInputError): project_working_material_input(task, **changed)

    def test_schema_rejects_nested_extras_and_positive_authority_claims(self):
        task, args = fixture(source=True, result=True)
        value = project_working_material_input(task, **args)
        changes = []
        changed = copy.deepcopy(value); changed["materials"][1]["material_provenance"]["parser"]["ledger"] = {}; changes.append(changed)
        changed = copy.deepcopy(value); changed["results"][0]["contract_validation"] = "accepted"; changes.append(changed)
        changed = copy.deepcopy(value); changed["results"][0]["task_completion"] = True; changes.append(changed)
        changed = copy.deepcopy(value); changed["boundaries"]["permission_grant"] = True; changes.append(changed)
        for changed in changes:
            with self.subTest(changed=changed): self.assertTrue(list(self.validator.iter_errors(changed)))

    def test_frozen_v02_still_rejects_provenance_and_new_result_fields(self):
        task, args = fixture(result=True)
        legacy_args = {key: value for key, value in args.items() if key != "results"}
        with self.assertRaises(WorkingInputError): project_working_input(task, **legacy_args)
        legacy_args["materials"] = [{key: value for key, value in item.items() if key != "material_provenance"}
                                   for item in args["materials"]]
        legacy = project_working_input(task, **legacy_args)
        old_validator = Draft202012Validator(json.loads(
            (ROOT / "schemas/v0.2.0/model-working-input.schema.json").read_text(encoding="utf-8")))
        old_validator.validate(legacy)
        legacy["results"] = []
        self.assertTrue(list(old_validator.iter_errors(legacy)))

    def test_acquisition_timezone_and_explicit_nested_records_are_required(self):
        task, args = fixture(source=True)
        for field, replacement in (("acquisition", {"origin": {}, "acquired_at": "2026-10-11", "operator": "test"}),
                                   ("parser", {"name": "utf8"})):
            changed = copy.deepcopy(args); changed["materials"][1]["material_provenance"][field] = replacement
            with self.subTest(field=field), self.assertRaises(WorkingInputError):
                project_working_material_input(task, **changed)
