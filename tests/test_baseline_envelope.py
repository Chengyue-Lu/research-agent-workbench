"""M6 public projection and the shared M5 A2 qualification producer."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from research_workbench.evaluation.pins import EvaluationValidationError
from research_workbench.evaluation.qualification import validate_qualification
from research_workbench.execution.baseline_envelope import (
    produce_a2_qualification,
    validate_baseline_envelope,
)
from tests.baseline_fixtures import A1, A2, AT, BaselineFixture


class BaselineEnvelopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.template = BaselineFixture(Path(temporary.name)).build_baseline(A2)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.f = copy.deepcopy(self.template)
        self.f.root = Path(temporary.name)
        shutil.copytree(self.template.root, self.f.root, dirs_exist_ok=True)

    def test_a1_a2_compile_the_same_public_bytes_with_only_the_tool_delta(self):
        a1 = self.f.compile(arm_id=A1, qualification_ref=None)
        a2 = self.f.compile()
        public = a2["provider_visible_payload"]
        self.assertEqual(public["inputs"], [{"ref": self.f.public_input_ref, "text": "数值输入：7\n"}])
        self.assertEqual(public["tools"], [self.f.tool_definition])
        self.assertEqual({**public, "tools": []}, a1["provider_visible_payload"])
        self.assertEqual(set(public), {"instruction", "inputs", "required_outputs", "tools"})
        self.assertEqual(public["required_outputs"], ["plain-text-answer"])
        self.assertIn("method-resolution", self.f.task["required_outputs"])
        self.assertNotIn("method-resolution", json.dumps(public))
        self.assertNotIn(self.f.task["agent_profile"], json.dumps(public))
        self.assertFalse(a1["boundaries"]["task_completion"])
        self.assertEqual(
            validate_baseline_envelope(self.f.inputs(), a2, expected_protocol_ref=self.f.protocol_ref),
            a2,
        )
        self.assertEqual(self.f.compile(), a2)

    def test_a2_producer_uses_the_shared_validator_and_keeps_runtime_identity(self):
        record = produce_a2_qualification(
            self.f.inputs(), protocol_ref=self.f.protocol_ref,
            qualification_id="REPRODUCED-A2", checked_at=AT,
            bindings=self.f.tool_bindings,
        )
        chains = validate_qualification(self.f.inputs(), record, expected_protocol_ref=self.f.protocol_ref)
        self.assertEqual(record["producer"], "m6-baseline-transport")
        self.assertEqual(record["arm_id"], A2)
        self.assertEqual(chains[0]["snapshot"]["qualification"], "runtime-execution")
        changed = copy.deepcopy(self.f.tool_bindings)
        changed[0]["implementation_ref"] = self.f.public_input_ref
        with self.assertRaisesRegex(EvaluationValidationError, "implementation_ref substitution"):
            produce_a2_qualification(
                self.f.inputs(), protocol_ref=self.f.protocol_ref,
                qualification_id="SUBSTITUTED-A2", checked_at=AT, bindings=changed,
            )

    def test_projection_is_explicitly_frozen_and_cannot_add_controls_or_replace_task(self):
        for field, value, message in (
            ("agent_profile", "some-control", "publicProjection schema"),
            ("task_ref", self.f.public_input_ref, "Task substitution"),
        ):
            projection = {**self.template.public_projection, field: value}
            self.f.freeze_public_projection(projection)
            with self.subTest(field=field), self.assertRaisesRegex(EvaluationValidationError, message):
                self.f.compile()
        ref = self.f.write("baseline/unfrozen-projection.json", self.template.public_projection)
        with self.assertRaisesRegex(EvaluationValidationError, "not frozen in Manifest"):
            self.f.compile(public_payload_ref=ref)

    def test_public_input_must_be_frozen_and_actual_utf8_bytes(self):
        other = self.f.raw("baseline/unfrozen.txt", b"not a frozen public input")
        projection = {**self.f.public_projection, "input_refs": [other]}
        self.f.freeze_public_projection(projection)
        with self.assertRaisesRegex(EvaluationValidationError, "outside frozen"):
            self.f.compile()
        # The reference remains pinned to the previous bytes; no stale payload
        # may be produced from a preexisting compilation after this change.
        self.f.raw(self.f.public_input_ref["path"], b"changed")
        with self.assertRaisesRegex(EvaluationValidationError, "hash mismatch"):
            self.f.compile()

    def test_envelope_recompute_rejects_payload_metadata_and_compiler_drift(self):
        changes = (
            ("provider_visible_payload", "instruction", "changed text"),
            ("transport_enforcement_metadata", "budget", {"max_turns": 99, "max_output_tokens": 2048, "max_parallel": 1, "max_seconds": 120}),
            ("transport_enforcement_metadata", "compiler_ref", {"path": "src/research_workbench/execution/baseline_envelope.py", "sha256": "0" * 64}),
        )
        for section, field, value in changes:
            changed = copy.deepcopy(self.f.envelope)
            changed[section][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(EvaluationValidationError, "differs from frozen"):
                validate_baseline_envelope(self.f.inputs(), changed, expected_protocol_ref=self.f.protocol_ref)

    def test_frozen_non_utf8_input_is_rejected_instead_of_silently_rewritten(self):
        old_ref = self.f.public_input_ref
        new_ref = self.f.raw(old_ref["path"], b"\xff\xfe")
        manifest = self.f.doc(self.f.manifest_ref["path"])
        refs = manifest["frozen_conditions"]["context"]["initial_context_refs"]
        refs[refs.index(old_ref)] = new_ref
        self.f.manifest_ref = self.f.write("evaluation/manifest.json", manifest)
        self.f.freeze_public_projection({**self.f.public_projection, "input_refs": [new_ref]})
        with self.assertRaisesRegex(EvaluationValidationError, "must be UTF-8"):
            self.f.compile()

    def test_frozen_tool_input_schema_must_be_a_valid_callable_contract(self):
        binding = self.f.bindings[A2]
        interface = self.f.doc(binding["interface_ref"]["path"])
        interface["provider_visible_interface"]["input_schema"]["required"] = "not-an-array"
        binding["interface_ref"] = self.f.write("arm-1/interface.json", interface)
        for item in self.f.protocol["execution_bindings"]:
            if item["arm_id"] == A2:
                item["interface_ref"] = binding["interface_ref"]
        self.f.protocol_ref = self.f.write("evaluation/protocol.json", self.f.protocol)
        qualification = self.f.doc(self.f.qualification_ref["path"])
        qualification["protocol_ref"] = self.f.protocol_ref
        qualification["bindings"][0]["interface_ref"] = binding["interface_ref"]
        self.f.qualification_ref = self.f.write("baseline/a2-qualification.json", qualification)
        with self.assertRaisesRegex(EvaluationValidationError, "invalid JSON Schema"):
            self.f.compile()

    def test_wrong_arm_or_missing_qualification_cannot_become_a_baseline(self):
        for arguments, message in (
            ({"arm_id": "mode-no-skill"}, "only A1/A2"),
            ({"arm_id": A1}, "must not carry"),
            ({"qualification_ref": None}, "qualification is required"),
            ({"accountable_owner": " "}, "owner is required"),
            ({"task_ref": self.f.public_input_ref}, "outside frozen Manifest"),
        ):
            with self.subTest(arguments=arguments), self.assertRaisesRegex(EvaluationValidationError, message):
                self.f.compile(**arguments)


if __name__ == "__main__":
    unittest.main()
