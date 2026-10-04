"""Finite body integrity and metadata isolation, not simulated live admission."""

import copy
from dataclasses import FrozenInstanceError, asdict, replace
import hashlib
import json
import unittest

from research_workbench.adapters.models.port import ContentBlock, FinishReason, ModelResponse, ToolCall, Usage
from research_workbench.evaluation.bounded_evidence import (
    BoundedEvidenceError, EvidenceOutputSpec, FORMAT, MAX_BODY_BYTES,
    parse_evidence_answer, project_evidence_response,
)


SPEC = EvidenceOutputSpec(("C01", "C02"), ("S01", "S02"))


def answer():
    return {"format": FORMAT, "claims": [
        {"claim_id": "C02", "verdict": "insufficient", "relations": []},
        {"claim_id": "C01", "verdict": "contradicted", "relations": [
            {"source_id": "S02", "relation": "counters", "scope_status": "matched"},
            {"source_id": "S01", "relation": "limits", "scope_status": "different"},
            {"source_id": "S01", "relation": "supports", "scope_status": "matched"},
        ]},
    ]}


def body(document=None):
    return json.dumps(answer() if document is None else document, separators=(",", ":"))


def response(text=None, **overrides):
    fields = dict(response_id="private-response", provider="private-provider", model="private-model",
                  output=(ContentBlock("text", body() if text is None else text),),
                  finish_reason=FinishReason.COMPLETE, usage=Usage(17, 8),
                  warnings=("private transport diagnostic",), provider_metadata={"private": "A4-marker"})
    return ModelResponse(**(fields | overrides))


class BoundedEvidenceParsingTests(unittest.TestCase):
    def reject(self, value, code=None):
        with self.assertRaises(BoundedEvidenceError) as caught:
            parse_evidence_answer(value, spec=SPEC)
        if code is not None:
            self.assertEqual(code, str(caught.exception))

    def test_preserves_competing_relations_and_unknown_without_semantic_scoring(self):
        result = parse_evidence_answer(body(), spec=SPEC).to_dict()
        self.assertEqual(["C01", "C02"], [row["claim_id"] for row in result["claims"]])
        self.assertEqual(["limits", "supports", "counters"],
                         [row["relation"] for row in result["claims"][0]["relations"]])
        self.assertEqual([], result["claims"][1]["relations"])
        # Structurally valid overclaims must be judged by Human, not this codec.
        document = answer()
        document["claims"][0]["verdict"] = "supported"
        self.assertEqual("supported", parse_evidence_answer(body(document), spec=SPEC).to_dict()["claims"][1]["verdict"])

    def test_immutable_result_and_canonical_order_do_not_rewrite_original_body(self):
        original = body()
        parsed = parse_evidence_answer(original, spec=SPEC)
        with self.assertRaises(FrozenInstanceError):
            parsed.claims[0].verdict = "supported"
        view = parsed.to_dict()
        view["claims"][0]["relations"].clear()
        self.assertEqual(3, len(parsed.claims[0].relations))
        self.assertEqual(original, body())
        reversed_rows = answer()
        reversed_rows["claims"].reverse()
        for row in reversed_rows["claims"]:
            row["relations"].reverse()
        self.assertEqual(parsed, parse_evidence_answer(body(reversed_rows), spec=SPEC))

    def test_frozen_identifiers_reject_mutability_duplicates_and_identity_channels(self):
        for claims, sources in [(["C01"], ("S01",)), (("C01", "C01"), ("S01",)),
                               (("A4-skill",), ("S01",)), (("C01",), ("provider-token",)),
                               ((), ("S01",)), (("C01",), ()), (("C05",), ("S01",)),
                               (("C01",), ("S09",)), ((True,), ("S01",))]:
            with self.subTest(claims=claims, sources=sources):
                with self.assertRaises(BoundedEvidenceError):
                    EvidenceOutputSpec(claims, sources)

    def test_duplicate_json_keys_at_each_level_are_rejected(self):
        raw = body()
        for candidate in [raw.replace('"format":', '"format":"unused","format":', 1),
                          raw.replace('"claim_id":', '"claim_id":"C01","claim_id":', 1),
                          raw.replace('"relation":', '"relation":"unknown","relation":', 1)]:
            self.reject(candidate, "duplicate-key")

    def test_rejects_prefix_suffix_fences_and_bom(self):
        raw = body()
        for candidate in ["answer: " + raw, raw + " trailing note", "```json\n" + raw + "\n```",
                          "\ufeff" + raw, "{", ""]:
            with self.subTest(size=len(candidate)):
                self.reject(candidate, "invalid-json")

    def test_depth_limit_is_explicit_and_respects_escaped_string_content(self):
        self.reject("[" * 2000 + "0" + "]" * 2000, "too-deep-json")
        document = answer()
        document["noise"] = '\\"' + "[{}]" * 100
        self.reject(body(document), "unexpected-fields")
        escaped_ids = body().replace('"C02"', '"C\\u00302"')
        self.assertEqual(parse_evidence_answer(body(), spec=SPEC), parse_evidence_answer(escaped_ids, spec=SPEC))

    def test_nonfinite_and_numeric_payloads_do_not_escape_as_runtime_errors(self):
        for token, code in [("NaN", "non-finite-json"), ("Infinity", "non-finite-json"),
                            ("-Infinity", "non-finite-json"), ("1e99999", "unexpected-number"),
                            ("9" * 6000, "unexpected-number"), ("1", "unexpected-number")]:
            self.reject('{"format":' + token + ',"claims":[]}', code)

    def test_utf8_and_exact_byte_limit_are_enforced_without_truncation(self):
        raw = body().encode("utf-8")
        padded = raw + b" " * (MAX_BODY_BYTES - len(raw))
        self.assertEqual(parse_evidence_answer(raw, spec=SPEC), parse_evidence_answer(padded, spec=SPEC))
        self.reject(padded + b" ", "oversized-body")
        self.reject(b"\xff" + raw, "invalid-utf8")
        self.reject("\ud800", "invalid-utf8")
        self.reject("中" * (MAX_BODY_BYTES // 2), "oversized-body")
        self.reject({}, "unsupported-body")

    def test_extra_fields_cannot_publish_transport_or_treatment_metadata(self):
        for level in ("root", "claim", "relation"):
            document = answer()
            target = document if level == "root" else document["claims"][1]
            if level == "relation":
                target = target["relations"][0]
            target["arm_or_api_key"] = "private sentinel"
            self.reject(body(document), "unexpected-fields")

    def test_missing_duplicate_extra_and_foreign_claims_are_rejected(self):
        for mode in ("missing", "duplicate", "extra", "foreign"):
            document = answer()
            if mode == "missing":
                document["claims"].pop()
            elif mode == "duplicate":
                document["claims"][0]["claim_id"] = "C01"
            elif mode == "extra":
                document["claims"].append(copy.deepcopy(document["claims"][0]))
            else:
                document["claims"][0]["claim_id"] = "C03"
            self.reject(body(document), "invalid-claim-set")

    def test_closed_enums_and_types_reject_unknown_alternatives(self):
        cases = [("verdict", "likely", "invalid-verdict"), ("verdict", True, "invalid-verdict"),
                 ("source_id", "S03", "invalid-source-id"), ("source_id", None, "invalid-source-id"),
                 ("relation", "explains-scientific-truth", "invalid-relation"),
                 ("scope_status", "accepted", "invalid-scope-status")]
        for field, value, code in cases:
            document = answer()
            target = document["claims"][1] if field == "verdict" else document["claims"][1]["relations"][0]
            target[field] = value
            self.reject(body(document), code)
        document = answer()
        document["format"] = "synthetic-integer-v1"
        self.reject(body(document), "wrong-format")

    def test_per_source_bound_and_duplicate_relations_cannot_hide_competing_scope_labels(self):
        document = answer()
        rows = document["claims"][1]["relations"]
        duplicate = copy.deepcopy(rows[0])
        duplicate["scope_status"] = "unknown"
        rows.append(duplicate)
        self.reject(body(document), "duplicate-relation")
        document = answer()
        document["claims"][1]["relations"].append(
            {"source_id": "S01", "relation": "unknown", "scope_status": "unknown"})
        self.reject(body(document), "too-many-source-relations")

    def test_aggregate_relation_bound_and_wrong_container_are_rejected(self):
        document = answer()
        document["claims"][1]["relations"] *= 2
        self.reject(body(document), "too-many-relations")
        document = answer()
        document["claims"][1]["relations"] = None
        self.reject(body(document), "too-many-relations")


class BoundedEvidenceProjectionTests(unittest.TestCase):
    def test_legacy_integer_projector_keeps_its_own_format_and_rejects_the_new_body(self):
        from research_workbench.evaluation.harness_review import _project
        from research_workbench.evaluation.pins import EvaluationValidationError

        class Inputs:
            def __init__(self, model):
                self.document = json.loads(json.dumps(asdict(model)))

            def read(self, _ref):
                return self.document

        ref = {"path": "output.json", "sha256": "0" * 64}
        row = {"lifecycle": "completed", "evidence": {"artifact_refs": [ref]}}
        value, refs = _project(Inputs(response("5")), row)
        self.assertEqual({"answer": 5, "availability": "reviewable"}, value)
        self.assertEqual([ref], refs)
        with self.assertRaises(EvaluationValidationError):
            _project(Inputs(response()), row)

    def test_projection_publishes_only_finite_answer_and_retains_usage_privately(self):
        model = response()
        projection = project_evidence_response(model, lifecycle="completed", spec=SPEC)
        public = projection.public_value()
        self.assertEqual({"availability", "answer"}, set(public))
        self.assertEqual("reviewable", public["availability"])
        self.assertEqual(hashlib.sha256(body().encode()).hexdigest(), projection.body_sha256)
        self.assertIsNone(projection.reason)
        encoded = json.dumps(public)
        for marker in ("private-provider", "private-model", "A4-marker", "private-response", "usage", "warnings", "body_sha256"):
            self.assertNotIn(marker, encoded)
        self.assertEqual(25, model.usage.total_tokens)
        self.assertEqual(body(), model.output[0].text)
        self.assertEqual({"private": "A4-marker"}, model.provider_metadata)

    def test_projection_never_reads_provider_metadata_or_diagnostics(self):
        class ForbiddenMetadata(dict):
            def __iter__(self):
                raise AssertionError("metadata was read")

            def items(self):
                raise AssertionError("metadata was read")

        model = response(provider_metadata=ForbiddenMetadata(private="must-stay-private"))
        self.assertEqual("reviewable", project_evidence_response(model, lifecycle="completed", spec=SPEC).public_value()["availability"])

    def test_noncompleted_lifecycles_are_unreviewable_without_discarding_response(self):
        model = response()
        for lifecycle in ("post-call-failed", "preflight-blocked", "not-started"):
            projected = project_evidence_response(model, lifecycle=lifecycle, spec=SPEC)
            self.assertEqual({"availability": "unreviewable", "answer": None}, projected.public_value())
            self.assertEqual("execution-not-completed", projected.reason)
            self.assertEqual(25, model.usage.total_tokens)
            self.assertEqual(body(), model.output[0].text)

    def test_every_noncomplete_finish_stays_unreviewable_with_original_usage(self):
        for finish in FinishReason:
            if finish == FinishReason.COMPLETE:
                continue
            model = response(finish_reason=finish)
            projected = project_evidence_response(model, lifecycle="completed", spec=SPEC)
            self.assertIsNone(projected.answer)
            self.assertEqual("response-not-complete", projected.reason)
            self.assertEqual(25, model.usage.total_tokens)

    def test_tool_calls_and_multiple_outputs_cannot_be_selected_or_combined(self):
        models = [response(tool_calls=(ToolCall("call", "lookup", {}),)),
                  response(output=(ContentBlock("text", body()), ContentBlock("text", body()))),
                  response(output=()), response(output=[ContentBlock("text", body())])]
        for model in models:
            self.assertIsNone(project_evidence_response(model, lifecycle="completed", spec=SPEC).answer)

    def test_embedded_content_metadata_is_rejected_at_the_block_boundary(self):
        for block in [ContentBlock("image", body()), ContentBlock("text", body(), data={}),
                      ContentBlock("text", body(), mime_type="application/json"),
                      ContentBlock("text", body(), reference="private-path"), ContentBlock("text", None)]:
            projected = project_evidence_response(response(output=(block,)), lifecycle="completed", spec=SPEC)
            self.assertEqual("unsupported-content", projected.reason)
            self.assertEqual({"availability": "unreviewable", "answer": None}, projected.public_value())

    def test_malformed_final_body_has_private_hash_and_stable_safe_diagnostic(self):
        invalid = body() + " private sentinel"
        model = response(invalid)
        projected = project_evidence_response(model, lifecycle="completed", spec=SPEC)
        self.assertEqual("invalid-json", projected.reason)
        self.assertEqual(hashlib.sha256(invalid.encode()).hexdigest(), projected.body_sha256)
        self.assertNotIn("sentinel", json.dumps(projected.public_value()))
        self.assertEqual(25, model.usage.total_tokens)
        self.assertEqual(invalid, model.output[0].text)

    def test_untrusted_spec_lifecycle_and_response_types_fail_without_authority_defaults(self):
        for spec in ({"claim_ids": ["C01"]}, None):
            with self.assertRaises(BoundedEvidenceError):
                project_evidence_response(response(), lifecycle="completed", spec=spec)
        for lifecycle in ("accepted", "live-pass", None, []):
            with self.assertRaises(BoundedEvidenceError):
                project_evidence_response(response(), lifecycle=lifecycle, spec=SPEC)
        with self.assertRaises(BoundedEvidenceError):
            project_evidence_response({}, lifecycle="completed", spec=SPEC)
        projected = project_evidence_response(replace(response(), finish_reason="complete"), lifecycle="completed", spec=SPEC)
        self.assertEqual("response-not-complete", projected.reason)


if __name__ == "__main__":
    unittest.main()
