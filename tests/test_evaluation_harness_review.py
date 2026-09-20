"""Blind package isolation and exact externally authorized freeze/reveal order.

Unit tests isolate the already-validated H4a seam. Integration tests below use
real synthetic H3 calls and independent H4a replay, including a cold process.
"""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

from research_workbench.evaluation import harness_review as review
from research_workbench.evaluation.harness_evidence import compile_harness_evidence
from research_workbench.evaluation.harness_execution import BOUNDARIES, execute_harness
from research_workbench.evaluation.harness_runtime import persist
from research_workbench.evaluation.pins import EvaluationInputs, EvaluationValidationError
from research_workbench.validation.document_kinds import infer_document_kind
from tests.harness_execution_fixtures import ExecutionFixture, FixedClock, LocalDriver, LocalProvider
from tests.system_evaluation_fixtures import ROOT, AT

CREATED = "2026-09-11T12:01:00+00:00"
RECEIVED = "2026-09-11T12:02:00+00:00"
FROZEN = "2026-09-11T12:03:00+00:00"
REVEALED = "2026-09-11T12:04:00+00:00"


def authority(payload):
    """Synthetic sequence fixture; this is not an actual Human acceptance."""
    if payload["operation"] == "human-review":
        return payload["review"]["reviewer"] == {"actor_id": "fixture-reviewer", "display_name": "Synthetic Reviewer"}
    return payload["operation"] in {"anonymize", "freeze", "reveal"}


AUTH = {"admission_verifier": lambda _: True, "projection_verifier": authority, "human_verifier": authority}
PACKAGE_AUTH = {k: v for k, v in AUTH.items() if k != "human_verifier"}


def artifact():
    return review._record("review_artifact", format="synthetic-integer-v1", answer=7,
                          transport_metadata={"skill": "private-treatment-label"})


class ReviewFixture:
    def inputs(self):
        return EvaluationInputs(self.root, ROOT / "schemas")

    def write(self, name, doc):
        return persist(self.root, self.root / name, doc)

    def review_document(self, package, package_ref):
        return review._record("human_review", package_ref=package_ref,
            reviewer={"actor_id": "fixture-reviewer", "display_name": "Synthetic Reviewer"},
            ratings=[{"anonymous_id": s["anonymous_id"],
                      "disposition": "scored" if s["availability"] == "reviewable" else "unreviewable",
                      # Fixture-authored score; production code never computes it.
                      "score": "correct" if s["availability"] == "reviewable" else None,
                      "reason": None if s["availability"] == "reviewable" else "No assessable output"}
                     for s in package["slots"]], boundaries=dict(BOUNDARIES))

    def package(self):
        return review.prepare_review_package(self.inputs(), context=self.context, **PACKAGE_AUTH)

    def store_package(self):
        self.public, self.private = self.package()
        self.package_ref = self.write("public/review.json", self.public)
        self.mapping_ref = self.write("private/mapping.json", self.private)
        self.human = self.review_document(self.public, self.package_ref)
        self.human_ref = self.write("private/human.json", self.human)
        self.freeze = review.FreezeContext(self.package_ref, self.mapping_ref,
            ({"review_ref": self.human_ref, "received_at": RECEIVED},), FROZEN)

    def freeze_reviews(self, **changes):
        return review.freeze_human_reviews(self.inputs(), context=self.context, freeze=self.freeze,
                                          **{**AUTH, **changes})

    def validate_package(self, **changes):
        return review.validate_review_package(self.inputs(), context=self.context,
            **{"expected_package_ref": self.package_ref, "expected_mapping_ref": self.mapping_ref,
               **PACKAGE_AUTH, **changes})


class HarnessReviewTests(ReviewFixture, unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.plan_ref = self.write("plan.json", {"cases": [{"case_id": "C1"}]})
        protocol = self.write("protocol.json", {"frozen_at": AT})
        policy = review._record("review_policy", protocol_ref=protocol, registered_at=AT,
            cases=[{"case_id": "C1", "reference_integer": 7}], projection_rule="synthetic-integer-v1",
            review_unit="every-planned-slice-including-unstarted", instruction=review.INSTRUCTION,
            rubric=review.RUBRIC, boundaries=dict(BOUNDARIES))
        self.policy_ref = self.write("policy.json", policy)
        response = asdict(LocalProvider().generate(type("Request", (), {"tools": []})()))
        m6 = self.write("m6.json", response)
        m11 = self.write("m11.json", artifact())
        self.evidence = {"slots": [{"case_id": "C1", "arm_id": arm, "slices": [
            {"attempt_id": f"attempt-{n}", "slice_index": 0, "lifecycle": lifecycle,
             "evidence": None if lifecycle == "not-started" else {"artifact_refs": refs}}]}
            for n, (arm, lifecycle, refs) in enumerate([
                ("plain-agent", "completed", [m6]), ("plain-agent-tool", "completed", [m6]),
                ("mode-no-skill", "completed", [m11, m11]),
                ("mode-candidate-skill", "post-call-failed", [m11]),
                ("plain-agent", "preflight-blocked", []), ("plain-agent-tool", "not-started", [])])]}
        evidence_ref = self.write("evidence.json", self.evidence)
        from research_workbench.evaluation.harness_execution import HarnessContext
        harness = HarnessContext(self.plan_ref, self.plan_ref, protocol, protocol, AT, "SYNTHETIC", AT)
        self.context = review.ReviewContext(harness, evidence_ref, evidence_ref, "H4B", self.policy_ref, AT, CREATED)
        self.seam = patch.object(review, "validate_harness_evidence", return_value=self.evidence)
        self.replay = self.seam.start()
        self.addCleanup(self.seam.stop)
        self.store_package()

    def test_public_projection_is_closed_and_fresh_private_mapping_covers_all_slices(self):
        public, mapping = self.validate_package()
        self.assertEqual(len(public["slots"]), 6)
        self.assertEqual(len(mapping["entries"]), 6)
        self.assertEqual(len(mapping["entries"][2]["source_refs"]), 2)
        for forbidden in ("plain-agent", "skill", "attempt", "response", "tokens", ".json", "C1", "12:"):
            self.assertNotIn(forbidden, json.dumps(public))
        second, _ = self.package()
        self.assertTrue(set(s["anonymous_id"] for s in public["slots"]).isdisjoint(
            s["anonymous_id"] for s in second["slots"]))
        self.replay.assert_called()
        self.assertEqual(infer_document_kind(public), public["record_kind"])

    def test_freeze_and_reveal_require_complete_named_reviews(self):
        frozen = self.freeze_reviews()
        frozen_ref = self.write("private/freeze.json", frozen)
        kwargs = dict(expected_freeze_ref=frozen_ref, revealed_at=REVEALED, context=self.context, freeze=self.freeze, **AUTH)
        revealed = review.reveal_human_reviews(self.inputs(), **kwargs)
        ref = self.write("private/reveal.json", revealed)
        self.assertEqual(review.validate_review_reveal(self.inputs(), expected_reveal_ref=ref, **kwargs), revealed)
        self.assertTrue(all(value is False for value in revealed["boundaries"].values()))
        with self.assertRaisesRegex(EvaluationValidationError, "follow"):
            review.reveal_human_reviews(self.inputs(), **{**kwargs, "revealed_at": FROZEN})
        with self.assertRaisesRegex(EvaluationValidationError, "externally selected"):
            review.validate_review_reveal(self.inputs(), expected_reveal_ref=ref,
                **{**kwargs, "revealed_at": "2026-09-11T12:05:00+00:00"})

    def test_mapping_package_and_source_substitution_are_rejected(self):
        for index, (target, field, value) in enumerate([
            ("private", "arm_id", "plain-agent-tool"), ("private", "projection_sha256", "0" * 64),
            ("private", "attempt_id", "other-attempt"), ("public", "answer", 3)]):
            with self.subTest(field=field):
                doc = copy.deepcopy(self.private if target == "private" else self.public)
                rows = doc["entries" if target == "private" else "slots"]
                row = rows[0] if target == "private" else next(s for s in rows if s["answer"] is not None)
                row[field] = value
                ref = self.write(f"tamper-{index}.json", doc)
                with self.assertRaisesRegex(EvaluationValidationError, "differs"):
                    self.validate_package(**{("expected_mapping_ref" if target == "private" else "expected_package_ref"): ref})
        (self.root / "m6.json").write_text('{}', encoding="utf-8")
        with self.assertRaisesRegex(EvaluationValidationError, "hash mismatch"):
            self.validate_package()

    def test_opaque_alias_duplicate_missing_and_invalid_rejected(self):
        for aliases in (["a" * 32] * 6, ["b" * 32], [str(n) for n in range(6)]):
            with self.subTest(aliases=aliases), self.assertRaisesRegex(EvaluationValidationError, "opaque aliases"):
                review._materialize(self.inputs(), self.evidence, {"cases": [{"case_id": "C1"}]}, aliases)
        with patch.object(review.secrets, "token_hex", return_value="a" * 32), self.assertRaisesRegex(EvaluationValidationError, "opaque aliases"):
            self.package()

    def test_partial_duplicate_unknown_and_unscorable_reviews_are_rejected(self):
        for index, mode in enumerate(["partial", "duplicate", "unknown", "unscorable", "unnamed", "untrusted", "package", "reason"]):
            human = copy.deepcopy(self.human)
            if mode == "partial": human["ratings"].pop()
            if mode == "duplicate": human["ratings"].append(human["ratings"][0])
            if mode == "unknown": human["ratings"][0]["anonymous_id"] = "0" * 32
            if mode == "unscorable":
                row = next(r for r in human["ratings"] if r["disposition"] == "unreviewable")
                row.update(disposition="scored", score="correct", reason=None)
            if mode == "unnamed": human["reviewer"]["display_name"] = " "
            if mode == "untrusted": human["reviewer"]["actor_id"] = "self-approved"
            if mode == "package": human["package_ref"] = self.mapping_ref
            if mode == "reason": next(r for r in human["ratings"] if r["reason"])["reason"] = " "
            ref = self.write(f"human-{index}.json", human)
            freeze = replace(self.freeze, submissions=({"review_ref": ref, "received_at": RECEIVED},))
            with self.subTest(mode=mode), self.assertRaises(EvaluationValidationError):
                review.freeze_human_reviews(self.inputs(), context=self.context, freeze=freeze, **AUTH)
        with self.assertRaisesRegex(EvaluationValidationError, "all anonymous"):
            review.freeze_human_reviews(self.inputs(), context=self.context,
                                        freeze=replace(self.freeze, submissions=()), **AUTH)

    def test_reviewable_output_can_be_explicitly_unreviewable_with_reason(self):
        for rating in self.human["ratings"]:
            rating.update(disposition="unreviewable", score=None, reason="Reviewer cannot assess this output")
        ref = self.write("all-unreviewable.json", self.human)
        self.freeze = replace(self.freeze, submissions=({"review_ref": ref, "received_at": RECEIVED},))
        self.assertEqual(self.freeze_reviews()["submissions"][0]["review_ref"], ref)

    def test_multiple_external_review_documents_cover_one_exact_set(self):
        submissions = []
        for index, rows in enumerate((self.human["ratings"][:3], self.human["ratings"][3:])):
            human = {**self.human, "ratings": rows}
            ref = self.write(f"partition-{index}.json", human)
            submissions.append({"review_ref": ref, "received_at": RECEIVED})
        self.freeze = replace(self.freeze, submissions=tuple(submissions))
        self.assertEqual(self.freeze_reviews()["submissions"], submissions)

    def test_authority_is_required_at_every_boundary_and_cannot_mutate_results(self):
        for verifier in (None, lambda _: False, lambda _: "approved"):
            with self.subTest(verifier=verifier), self.assertRaises(EvaluationValidationError):
                self.validate_package(projection_verifier=verifier)
            with self.assertRaises(EvaluationValidationError): self.freeze_reviews(human_verifier=verifier)
        for operation in ("freeze", "reveal"):
            verifier = lambda p: p["operation"] != operation
            if operation == "freeze":
                with self.assertRaisesRegex(EvaluationValidationError, "rejected freeze"):
                    self.freeze_reviews(human_verifier=verifier)
            else:
                ref = self.write("freeze-auth.json", self.freeze_reviews())
                with self.assertRaisesRegex(EvaluationValidationError, "rejected reveal"):
                    review.reveal_human_reviews(self.inputs(), expected_freeze_ref=ref, revealed_at=REVEALED,
                        context=self.context, freeze=self.freeze, **{**AUTH, "human_verifier": verifier})
        def mutator(payload):
            payload["mapping"]["entries"].clear()
            return True
        self.assertEqual(len(self.validate_package(projection_verifier=mutator)[1]["entries"]), 6)

    def test_preregistration_and_observation_times_are_external(self):
        for context in (replace(self.context, policy_registered_at=CREATED),
                        replace(self.context, package_created_at="2000-01-01T00:00:00Z")):
            with self.assertRaises(EvaluationValidationError):
                review.prepare_review_package(self.inputs(), context=context, **PACKAGE_AUTH)
        for freeze in (replace(self.freeze, frozen_at="2000-01-01T00:00:00Z"),
                       replace(self.freeze, submissions=({"review_ref": self.human_ref, "received_at": REVEALED},)),
                       replace(self.freeze, submissions=({"review_ref": self.human_ref, "received_at": AT},))):
            with self.assertRaises(EvaluationValidationError):
                review.freeze_human_reviews(self.inputs(), context=self.context, freeze=freeze, **AUTH)
        policy = self.inputs().read(self.policy_ref)
        for index, changed in enumerate([{**policy, "protocol_ref": self.mapping_ref}, {**policy, "cases": policy["cases"] * 2}]):
            ref = self.write(f"policy-{index}.json", changed)
            with self.assertRaises(EvaluationValidationError):
                review.prepare_review_package(self.inputs(), context=replace(self.context, expected_policy_ref=ref), **PACKAGE_AUTH)

    def test_score_or_mapping_replacement_cannot_reuse_freeze_or_reveal(self):
        frozen_ref = self.write("frozen.json", self.freeze_reviews())
        for row in self.human["ratings"]:
            if row["score"] is not None: row["score"] = "incorrect"
        ref = self.write("rescored.json", self.human)
        changed = replace(self.freeze, submissions=({"review_ref": ref, "received_at": RECEIVED},))
        with self.assertRaisesRegex(EvaluationValidationError, "frozen Human Review"):
            review.reveal_human_reviews(self.inputs(), expected_freeze_ref=frozen_ref, revealed_at=REVEALED,
                                        context=self.context, freeze=changed, **AUTH)
        duplicate_map = self.write("mapping-copy.json", self.private)
        with self.assertRaisesRegex(EvaluationValidationError, "frozen Human Review"):
            review.validate_review_freeze(self.inputs(), expected_freeze_ref=frozen_ref, context=self.context,
                freeze=replace(self.freeze, expected_mapping_ref=duplicate_map), **AUTH)

    def test_projector_rejects_free_text_hidden_content_unknown_fields_and_multiple_artifacts(self):
        response = self.inputs().read(self.evidence["slots"][0]["slices"][0]["evidence"]["artifact_refs"][0])
        variants = []
        for key, value in [("extra", "arm"), ("tool_calls", [{}]), ("output", []), ("output", None),
                           ("finish_reason", "tool_call")]:
            variants.append({**response, key: value})
        for key, value in [("text", "7 A4 skill"), ("reference", "private/trace"), ("data", {"arm": "A4"}),
                           ("kind", "image"), ("text", 7), ("mime_type", "text/private"), ("extra", "label")]:
            variants.append({**response, "output": [{**response["output"][0], key: value}]})
        variants.extend([{**artifact(), "unexpected": "RWB"}, {**artifact(), "answer": "7 Skill"}])
        for index, doc in enumerate(variants):
            ref = self.write(f"bad-artifact-{index}.json", doc)
            with self.subTest(index=index), self.assertRaises(EvaluationValidationError):
                review._project(self.inputs(), {"lifecycle": "completed", "evidence": {"artifact_refs": [ref]}})
        for refs in ([], [self.package_ref, self.mapping_ref]):
            with self.assertRaisesRegex(EvaluationValidationError, "one unique artifact"):
                review._project(self.inputs(), {"lifecycle": "completed", "evidence": {"artifact_refs": refs}})

    def test_input_and_validator_drift_during_authorization_are_rejected(self):
        identity = review.validator_identity(self.inputs())
        with patch.object(review, "validator_identity", side_effect=[identity, {**identity, "version": "changed"}]), \
                self.assertRaisesRegex(EvaluationValidationError, "validator changed"):
            self.package()
        def mutate(_):
            (self.root / "m11.json").write_text('{}', encoding="utf-8")
            return True
        with self.assertRaises(EvaluationValidationError):
            self.validate_package(projection_verifier=mutate)


class HarnessReviewIntegrationTests(ReviewFixture, unittest.TestCase):
    def test_four_arm_evidence_to_review_freeze_and_fresh_process_reveal(self):
        with tempfile.TemporaryDirectory() as directory:
            self.root = Path(directory)
            fixture = ExecutionFixture(self.root).build_execution()
            ports = fixture.ports()
            def driver(view, recorder, destination, skill=False):
                return LocalDriver(view, recorder, destination, skill=skill, output=artifact())
            ports = replace(ports, core_driver=driver,
                skill_driver=lambda *args: driver(*args, skill=True))
            execution_ref = execute_harness(fixture.inputs(), context=fixture.context, ports=ports,
                                           clock=FixedClock(), admission_verifier=lambda _: True)
            evidence = compile_harness_evidence(fixture.inputs(), execution_ref=execution_ref,
                context=fixture.context, evidence_id="H4B-INTEGRATION", admission_verifier=lambda _: True)
            evidence_ref = self.write("evidence.json", evidence)
            policy_ref = self.write("policy.json", review._record("review_policy",
                protocol_ref=fixture.protocol_ref, registered_at=AT,
                cases=[{"case_id": c["case_id"], "reference_integer": 7} for c in fixture.plan["cases"]],
                projection_rule="synthetic-integer-v1", review_unit="every-planned-slice-including-unstarted",
                instruction=review.INSTRUCTION, rubric=review.RUBRIC, boundaries=dict(BOUNDARIES)))
            self.context = review.ReviewContext(fixture.context, execution_ref, evidence_ref,
                                                "H4B-INTEGRATION", policy_ref, AT, CREATED)
            self.store_package()
            self.assertEqual(len(self.public["slots"]), sum(len(s["slices"]) for s in evidence["slots"]))
            frozen_ref = self.write("private/frozen.json", self.freeze_reviews())
            context_path = self.write("private/context.json", {"context": asdict(self.context),
                                                               "freeze": asdict(self.freeze), "frozen_ref": frozen_ref})
            script = r'''
import json, sys
from pathlib import Path
from unittest.mock import patch
from research_workbench.evaluation.harness_execution import HarnessContext
from research_workbench.evaluation.harness_review import ReviewContext, FreezeContext, reveal_human_reviews, validate_review_reveal
from research_workbench.evaluation.harness_runtime import persist
from research_workbench.evaluation.pins import EvaluationInputs
from tests.test_evaluation_harness_review import AUTH, REVEALED
root, schemas, context_ref = sys.argv[1:]
def audit(event, args):
    if event in {'subprocess.Popen', 'socket.connect'}: raise AssertionError('execution during review replay')
    if event == 'exec' and args[0].co_filename.replace('\\','/').startswith(root.replace('\\','/')+'/'):
        raise AssertionError('project code during review replay')
sys.addaudithook(audit)
inputs=EvaluationInputs(root,schemas)
data=inputs.read(json.loads(context_ref)); ctx=data['context']; ctx['harness']=HarnessContext(**ctx['harness'])
context=ReviewContext(**ctx); freeze=FreezeContext(**data['freeze'])
kwargs=dict(expected_freeze_ref=data['frozen_ref'], revealed_at=REVEALED,context=context,freeze=freeze,**AUTH)
with patch('research_workbench.evaluation.harness_execution.run_baseline_session',side_effect=AssertionError('M6 called')), patch('research_workbench.evaluation.harness_runtime.execute_frozen_view',side_effect=AssertionError('Host called')):
    revealed=reveal_human_reviews(inputs,**kwargs)
    ref=persist(Path(root),Path(root)/'private/revealed.json',revealed)
    assert validate_review_reveal(EvaluationInputs(root,schemas),expected_reveal_ref=ref,**kwargs)==revealed
print('cold review replay PASS')
'''
            result = subprocess.run([sys.executable, "-c", script, str(self.root), str(ROOT / "schemas"),
                                     json.dumps(context_path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "cold review replay PASS")
            # A newly pinned forged H4a summary must still fail independent reconstruction.
            evidence["slots"].pop()
            bad_ref = self.write("forged-evidence.json", evidence)
            with self.assertRaisesRegex(EvaluationValidationError, "actual evidence differs"):
                review.prepare_review_package(self.inputs(),
                    context=replace(self.context, expected_evidence_ref=bad_ref), **PACKAGE_AUTH)


if __name__ == "__main__":
    unittest.main()
