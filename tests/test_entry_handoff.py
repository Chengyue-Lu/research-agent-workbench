"""Exact formal transfer checks; offline ports never establish live admission."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from research_workbench.entry.handoff import (
    EntryHandoffError, _receipt_evidence, consume_compact_handoff,
    publish_compact_handoff, workflow_handoff_observation,
)
from research_workbench.entry.roles import document_bytes
from research_workbench.tasks import FileReference
from research_workbench.validation.schemas import SchemaCatalog
from tests.test_entry_workflow import task


def pin(root, path, document):
    destination = root / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(document_bytes(document))
    return FileReference(path, hashlib.sha256(destination.read_bytes()).hexdigest())


def observation(**changes):
    value = dict(status="stage-completed", summary="Bounded actual observation.",
        limitations=["No scientific acceptance."], conflicts=[], unresolved=[],
        human_decision_required=[], next_actions=["Human review."],
        artifact_refs=[], receipt_refs=[], usage={"model_calls": 1, "known_tokens": 38, "held_tokens": 0})
    value.update(changes)
    return value


class EntryHandoffTests(unittest.TestCase):
    def publish(self, root, *, control=None, observed=None, directory="work/handoff"):
        # A schema-valid explicit zero-minimum contract proves no-Skill compact
        # transfer without claiming that a missing positive output was verified.
        control = control or task()
        if control["required_outputs"] == ["handoff-packet"]:
            control["required_outputs"] = [{"contract": "bounded-transfer", "min_count": 0}]
        observed = observed or observation()
        reference = publish_compact_handoff(root, task=control, attempt_id="ACTUAL-ATTEMPT",
            directory=directory, observation=observed)
        return control, observed, reference

    def test_real_typed_no_skill_transfer_and_independent_consumer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            control, observed, reference = self.publish(root)
            consumed = consume_compact_handoff(root, reference, expected_task=control,
                expected_attempt_id="ACTUAL-ATTEMPT", expected_observation=observed)
            self.assertEqual([], SchemaCatalog().validate("handoff_packet", consumed["document"]))
            self.assertEqual([], consumed["document"]["skill_lock"])
            self.assertEqual("stage-completed", consumed["document"]["status"])
            self.assertNotIn("revision", consumed["document"]["producer_ref"])
            self.assertFalse(consumed["task_completion"])
            self.assertFalse(consumed["human_acceptance"])

    def test_missing_positive_outputs_retains_partial_and_negative_facts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            control = task()
            control["required_outputs"] = [{"contract": "actual-report", "min_count": 2}]
            observed = observation(conflicts=[{"topic": "beta", "detail": "unknown"}],
                unresolved=["beta remains unknown"], human_decision_required=["Choose the next scope."])
            control, observed, reference = self.publish(root, control=control, observed=observed)
            consumed = consume_compact_handoff(root, reference, expected_task=control,
                expected_attempt_id="ACTUAL-ATTEMPT", expected_observation=observed)["document"]
            self.assertEqual("safe-paused", consumed["status"])
            self.assertIn("beta remains unknown", consumed["unresolved"])
            self.assertIn("actual-report", " ".join(consumed["unresolved"]))
            self.assertEqual(observed["conflicts"], consumed["conflicts"])
            self.assertEqual(observed["human_decision_required"], consumed["human_decision_required"])

    def test_unknown_usage_and_binary_output_pins_are_preserved_then_drift_blocks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "work/output.bin"
            output.parent.mkdir(parents=True)
            output.write_bytes(b"\x00\xff\x80")
            artifact = {"path": "work/output.bin", "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
            observed = observation(status="safe-paused", unresolved=["Actual usage is unknown."],
                artifact_refs=[artifact], usage={"model_calls": 1, "known_tokens": 0, "held_tokens": 228})
            control, observed, reference = self.publish(root, observed=observed)
            consumed = consume_compact_handoff(root, reference, expected_task=control,
                expected_attempt_id="ACTUAL-ATTEMPT", expected_observation=observed)
            source = json.loads((root / consumed["producer_ref"]["path"]).read_bytes())
            self.assertEqual(228, source["observation"]["usage"]["held_tokens"])
            output.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "HASH-DRIFT"):
                consume_compact_handoff(root, reference, expected_task=control,
                    expected_attempt_id="ACTUAL-ATTEMPT", expected_observation=observed)

    def test_jointly_replaced_producer_and_packet_cannot_replace_actual_observation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            control, observed, reference = self.publish(root)
            forged = copy.deepcopy(observed)
            forged["summary"] = "A different observation."
            _, _, replacement = self.publish(root, control=control, observed=forged, directory="work/replacement")
            with self.assertRaisesRegex(EntryHandoffError, "ACTUAL-OBSERVATION-MISMATCH"):
                consume_compact_handoff(root, replacement, expected_task=control,
                    expected_attempt_id="ACTUAL-ATTEMPT", expected_observation=observed)
            with self.assertRaisesRegex(EntryHandoffError, "TASK-ATTEMPT-MISMATCH"):
                consume_compact_handoff(root, reference, expected_task=control,
                    expected_attempt_id="ANOTHER-ATTEMPT", expected_observation=observed)

    def test_exact_input_revision_and_source_hash_drift_block(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_ref = pin(root, "inputs/revision.json", {"revision": 3, "data": "actual"})
            control = task()
            control["input_refs"] = [{"path": input_ref.path, "sha256": input_ref.sha256, "revision": 3}]
            control, observed, reference = self.publish(root, control=control)
            changed = copy.deepcopy(control)
            changed["input_refs"][0]["revision"] = 4
            with self.assertRaises(ValueError):
                consume_compact_handoff(root, reference, expected_task=changed,
                    expected_attempt_id="ACTUAL-ATTEMPT", expected_observation=observed)
            handoff = json.loads((root / reference.path).read_bytes())
            (root / handoff["producer_ref"]["path"]).write_bytes(b"{}")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                consume_compact_handoff(root, reference, expected_task=control,
                    expected_attempt_id="ACTUAL-ATTEMPT", expected_observation=observed)

    def test_required_skill_manifest_and_normalization_scope_escape_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for field, value, code in (
                    ("required_skills", ["required-skill@1.0.0"], "SKILL-LOADING"),
                    ("handoff_policy", {"require_transfer_manifest": True,
                        "semantic_review": "risk-triggered", "minimum_semantic_samples": 0}, "TRANSFER-AUDIT")):
                with self.subTest(field=field):
                    control = task()
                    control[field] = value
                    with self.assertRaisesRegex(EntryHandoffError, code):
                        self.publish(root, control=control)
                    self.assertFalse((root / "work/handoff").exists())
            control = task()
            control["write_scope"] = ["work/allowed/**"]
            control["permissions"]["allowed_roots"] = ["work/allowed"]
            for directory in ("work/allowed/../sibling", "work/allowed/./nested", "work//allowed/nested",
                              "work\\allowed\\nested", "/work/allowed", "C:/work/allowed"):
                with self.subTest(directory=directory), self.assertRaisesRegex(EntryHandoffError, "WRITE-SCOPE"):
                    self.publish(root, control=control, directory=directory)
            self.assertFalse((root / "work/sibling").exists())

    def test_actual_receipt_duplicate_rejected_and_shared_artifact_counted_once(self):
        from tests.test_entry_caller import EntryCallerTests
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            helper = EntryCallerTests()
            _, intake, factory, _ = helper.prepare(root)
            result = helper.run_caller(root, intake, factory)
            self.assertIsNotNone(result.handoff_ref, result.reason)
            report = json.loads((root / result.workflow.report_ref["path"]).read_bytes())
            actual = workflow_handoff_observation(report, root)
            receipt_ref = actual["receipt_refs"][0]
            duplicate = copy.deepcopy(actual)
            duplicate["receipt_refs"].append(dict(receipt_ref))
            with self.assertRaisesRegex(EntryHandoffError, "DUPLICATE-RECEIPT"):
                _receipt_evidence(root, report["task"], duplicate)
            # A second structurally valid Receipt of the same exact execution
            # is distinct evidence, not a second published output artifact.
            receipt = json.loads((root / receipt_ref["path"]).read_bytes())
            receipt["receipt_id"] += "-SECOND"
            second = pin(root, "work/shared-output-receipt.json", receipt)
            shared = copy.deepcopy(actual)
            shared["receipt_refs"].append({"path": second.path, "sha256": second.sha256})
            verified = _receipt_evidence(root, report["task"], shared)
            contract = receipt["artifact_refs"][0]["contract"]
            self.assertEqual(1, verified["output_contract_status"]["observed_counts"][contract])
            higher = copy.deepcopy(report["task"])
            higher["required_outputs"] = [{"contract": contract, "min_count": 2}]
            with self.assertRaisesRegex(EntryHandoffError, "RECEIPT-TASK-DRIFT"):
                _receipt_evidence(root, higher, shared)


if __name__ == "__main__":
    unittest.main()
