"""H4c scope/method attacks and a real four-arm cold archive reconstruction.

Unit fixtures isolate previously validated H4b/Protocol/comparison boundaries.
Their manually authored numeric observations demonstrate contract arithmetic,
not measurement science or automatic interpretation of the integer rubric.
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

from research_workbench.evaluation import harness_analysis as analysis
from research_workbench.evaluation.harness_execution import BOUNDARIES, HarnessContext
from research_workbench.evaluation.harness_review import ReviewContext, FreezeContext
from research_workbench.evaluation.harness_runtime import persist
from research_workbench.evaluation.manifest import FIXED_METRIC_SET, PHASE_D_ARMS
from research_workbench.evaluation.pins import EvaluationInputs, EvaluationValidationError
from research_workbench.validation.document_kinds import infer_document_kind
from tests.harness_analysis_data import AUTH, CREATED, RECEIVED, FROZEN, REVEALED, OBSERVED, CHECKED, ANALYZED
from tests.harness_analysis_fixtures import build_analysis_chain
from tests.system_evaluation_fixtures import AT, ROOT, BOUNDARIES as MEASUREMENT_BOUNDARIES, record


class HarnessAnalysisTests(unittest.TestCase):
    def write(self, name, doc):
        path = self.root / name
        index = 1
        while path.exists():
            path = self.root / (name + f".{index}.json")
            index += 1
        return persist(self.root, path, doc)

    def inputs(self):
        return EvaluationInputs(self.root, ROOT / "schemas")

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        schema = json.loads((ROOT / "schemas/v0.1.0/system-evaluation-protocol.schema.json").read_bytes())
        protocol = {"rules": schema["properties"]["rules"]["const"], "design": {"analysis": {
            "unit": "case-replicate-paired-difference", "summary": "per-metric-paired-differences-and-intervals",
            "interval": "case-cluster-bootstrap", "confidence_level": .95, "resamples": 1000, "seed": 19,
            "missing": "report-by-status-no-imputation", "secondary": "descriptive-no-confirmatory-claim",
            "reveal_after": "all-blind-human-reviews-frozen"}}}
        self.protocol_ref = self.write("protocol.json", protocol)
        plan = {"blocks": [{"case_id": "C1", "phase": "confirmatory", "replicate": 1,
                            "arms": [{"arm_id": a} for a in PHASE_D_ARMS]}]}
        plan_ref = self.write("plan.json", plan)
        self.pairwise_ref = self.write("comparison.json", {})
        overlap_ref = self.write("overlap.json", {})
        preflight_ref = self.write("preflight.json", {"request": {"overlap_ref": overlap_ref,
            "case_bindings": [{"case_id": "C1", "pairwise_ref": self.pairwise_ref}]}})
        self.evidence, mapping = {"slots": []}, {"entries": []}
        ratings = []
        for a in PHASE_D_ARMS:
            for retry, lifecycle in enumerate(("post-call-failed", "completed", "not-started")):
                attempt = f"{a}-{retry}"
                journal = None if retry == 2 else self.write(f"{attempt}/journal.json", {"attempt": attempt})
                receipt = None if retry == 2 else self.write(f"{attempt}/receipt.json", {"attempt": attempt})
                source = None if retry == 2 else self.write(f"{attempt}/source.json", {"attempt": attempt})
                self.evidence["slots"].append({"block_index": 0, "case_id": "C1", "phase": "confirmatory",
                    "replicate": 1, "arm_id": a, "slot": {"attempt_id": attempt, "retry_index": retry},
                    "journal_ref": journal, "lifecycle": lifecycle, "slices": [{"attempt_id": attempt,
                        "slice_index": 0, "lifecycle": lifecycle, "comparison": "not-observed" if retry == 2 else "matches-frozen",
                        "receipt_ref": receipt, "evidence": None if retry == 2 else {"host_ref": source,
                            "trace_ref": source, "fact_refs": [source], "artifact_refs": [source], "validation_refs": [source]}}]})
                mapping["entries"].append({"anonymous_id": attempt, "attempt_id": attempt, "slice_index": 0})
                ratings.append({"anonymous_id": attempt, "score": None})
        evidence_ref = self.write("evidence.json", self.evidence)
        map_ref = self.write("mapping.json", mapping)
        human_ref = self.write("human.json", {"ratings": ratings})
        harness = HarnessContext(plan_ref, preflight_ref, self.protocol_ref, plan_ref, AT, "RUN-H4C", AT)
        review = ReviewContext(harness, evidence_ref, evidence_ref, "E1", plan_ref, AT, CREATED)
        freeze = FreezeContext(plan_ref, map_ref, ({"review_ref": human_ref, "received_at": RECEIVED},), FROZEN)
        self.context = analysis.MetricContext(review, freeze, map_ref, map_ref, REVEALED, CHECKED, ())
        # No execution or research judgement happens through these isolated seams.
        for target, name in ((analysis, "validate_review_reveal"),
            (sys.modules["research_workbench.evaluation.system_protocol"], "validate_protocol")):
            seam = patch.object(target, name)
            seam.start(); self.addCleanup(seam.stop)
        original_read = EvaluationInputs.read
        def boundary_read(inputs, ref, kind=None):
            return original_read(inputs, ref, None if kind in {
                "admission_evidence_overlap", "a3_a4_pairwise_comparability"} else kind)
        seam = patch.object(EvaluationInputs, "read", boundary_read)
        seam.start(); self.addCleanup(seam.stop)
        self.auth = {**AUTH, "measurement_verifier": lambda _: True}
        methods = {}
        for m in FIXED_METRIC_SET:
            unit = {"characters-or-tokens": "tokens", "currency": "USD"}.get(m.unit, m.unit)
            operation = {"count": "audit-count", "ratio": "audit-ratio", "characters-or-tokens": "context-ledger",
                         "currency": "cost-ledger", "minutes": "outer-wall-clock"}[m.unit]
            method = analysis._record("metric_method", method_id=m.metric_id, metric_id=m.metric_id, unit=unit,
                operation=operation, source="frozen-human-review" if m.metric_id in analysis.HUMAN_METRICS else "execution-observation",
                registered_at=AT, estimation_method=None, boundaries=dict(BOUNDARIES))
            methods[m.metric_id] = self.write(f"methods/{m.metric_id}.json", method), method
        requests = []
        for arm in PHASE_D_ARMS:
            slots = [s for s in self.evidence["slots"] if s["arm_id"] == arm]
            target, _, _ = analysis._cell(slots, "RUN-H4C")
            journals = [s["journal_ref"] for s in slots if s["journal_ref"]]
            for m in FIXED_METRIC_SET:
                method_ref, method = methods[m.metric_id]
                data = {"audit-count": {"count": 2}, "audit-ratio": {"numerator": 1, "denominator": 2},
                    "context-ledger": {"unit": "tokens", "attempts": [{"attempt_id": a, "value": 15} for a in target["attempt_ids"]]},
                    "cost-ledger": {"unit": "USD", "execution": [{"attempt_id": a, "value": 3} for a in target["attempt_ids"]],
                                    "human": dict.fromkeys(analysis.HUMAN_COST, 2)},
                    "outer-wall-clock": {"clock": "trusted-harness-whole-arm", "started_at": AT,
                                         "finished_at": "2026-09-11T00:01:00Z"}}[method["operation"]]
                observation = analysis._record("metric_observation", observation_id=m.metric_id + arm, method_ref=method_ref,
                    target=target, operation=method["operation"], observed_at=OBSERVED,
                    source_refs=[human_ref] if m.metric_id in analysis.HUMAN_METRICS else journals,
                    data=data, boundaries=dict(BOUNDARIES))
                observation_ref = self.write(f"observations/{arm}-{m.metric_id}.json", observation)
                value = {"count": 2, "ratio": .5, "characters-or-tokens": 30, "currency": 16, "minutes": 1}[m.unit]
                measurement = record("evaluation_measurement", "measurement_id", arm + m.metric_id,
                    protocol_ref=self.protocol_ref, case_id="C1", arm_id=arm, metric_id=m.metric_id,
                    status="measured", unit=method["unit"], value=value, reason="Manually authored synthetic contract observation.",
                    evidence_refs=[observation_ref], estimation_method=None, boundaries=dict(MEASUREMENT_BOUNDARIES))
                measurement_ref = self.write(f"measurements/{arm}-{m.metric_id}.json", measurement)
                requests.append({"block_index": 0, "arm_id": arm, "metric_id": m.metric_id,
                    "measurement_ref": measurement_ref, "method_ref": method_ref, "observation_ref": observation_ref,
                    "method_registered_at": AT, "observed_at": OBSERVED})
        self.context = replace(self.context, associations=tuple(requests))

    def compile(self, **auth):
        return analysis.compile_harness_metrics(self.inputs(), context=self.context, metrics_id="M1", **{**self.auth, **auth})

    def request(self, metric="cost", arm="plain-agent"):
        return next(r for r in self.context.associations if r["metric_id"] == metric and r["arm_id"] == arm)

    def alter(self, key, mutate, metric="cost", arm="plain-agent", revalue=None):
        request = self.request(metric, arm)
        document = self.inputs().read(request[key]); mutate(document)
        ref = self.write(f"changed-{key}-{metric}-{arm}.json", document)
        request[key] = ref
        if key == "observation_ref":
            measurement = self.inputs().read(request["measurement_ref"])
            measurement["evidence_refs"] = [ref]
            if revalue is not None: measurement["value"] = revalue
            request["measurement_ref"] = self.write(f"changed-measurement-{metric}-{arm}.json", measurement)
        return document

    def unavailable(self, metric, status="unavailable", arm="plain-agent"):
        request = self.request(metric, arm)
        document = self.inputs().read(request["measurement_ref"])
        document.update(status=status, value=None, evidence_refs=[], reason="Explicitly missing.", estimation_method=None)
        request.update(measurement_ref=self.write(f"missing-{metric}-{arm}.json", document),
                       method_ref=None, observation_ref=None, method_registered_at=None, observed_at=None)

    def analysis_context(self):
        metrics = self.compile(); ref = self.write("metrics.json", metrics)
        pairwise_ref = self.write("analysis-comparison.json", {"stage": "analysis-input", "checked_at": ANALYZED,
                                                            "preregistered_record_ref": self.pairwise_ref})
        return analysis.AnalysisContext(self.context, ref, "M1", ANALYZED, ({"case_id": "C1", "ref": pairwise_ref},))

    def paired(self, context=None, interpretation="skill-conditional-increment", overlap="held-out", validate_ref=None):
        context = context or self.analysis_context()
        result = {"status": {"skill-conditional-increment": "exact-skill-only", "skill-bearing-package-effect": "skill-bearing-package",
                  "unavailable": "not-comparable"}[interpretation], "interpretation": interpretation,
                  "mismatches": [], "comparison_digest": "0" * 64}
        with patch.object(analysis, "validate_overlap", return_value={"overlap_status": overlap, "overlap_refs": [],
            "unresolved_reasons": [], "primary_confirmatory_eligible": overlap == "held-out"}), \
             patch.object(analysis, "validate_comparability", return_value=result):
            if validate_ref is not None:
                return analysis.validate_harness_analysis(self.inputs(), expected_analysis_ref=validate_ref,
                    expected_analysis_id="A1", context=context, **self.auth)
            return analysis.compile_harness_analysis(self.inputs(), context=context, analysis_id="A1", **self.auth)

    def test_complete_metrics_and_pairing_reconstruct_without_authority(self):
        document = self.compile()
        self.assertEqual(len(document["cells"]), 4)
        for cell in document["cells"]:
            self.assertEqual(len(cell["metrics"]), 13)
            self.assertEqual([a["lifecycle"] for a in cell["attempts"]], ["post-call-failed", "completed", "not-started"])
            self.assertEqual(len(cell["target"]["attempt_ids"]), 2)
        ref = self.write("metric-valid.json", document)
        self.assertEqual(analysis.validate_harness_metrics(self.inputs(), expected_metrics_ref=ref,
            expected_metrics_id="M1", context=self.context, **self.auth), document)
        context = self.analysis_context(); paired = self.paired(context)
        paired_ref = self.write("analysis-roundtrip.json", paired)
        self.assertEqual(self.paired(context, validate_ref=paired_ref), paired)
        self.assertEqual(len(paired["pairs"]), 5)
        self.assertTrue(all(r["value"] == 0 for p in paired["pairs"] for r in p["metrics"]))
        self.assertTrue(all(p["primary_confirmatory_eligible"] is False for p in paired["pairs"]))
        self.assertEqual(infer_document_kind(document), document["record_kind"])
        self.assertTrue(all(v is False for v in document["boundaries"].values()))

    def test_missing_and_not_applicable_remain_null_and_diagnostic(self):
        for arm in PHASE_D_ARMS:
            self.unavailable("cost", "not-applicable", arm)
            self.unavailable("lookup-count", "not-applicable" if arm != "plain-agent" else "unavailable", arm)
        self.unavailable("context-loaded")
        pairs = self.paired()["pairs"]
        cost = next(r for r in pairs[0]["metrics"] if r["metric_id"] == "cost")
        self.assertEqual((cost["status"], cost["value"]), ("not-applicable", None))
        context = next(r for r in pairs[1]["metrics"] if r["metric_id"] == "context-loaded")
        self.assertEqual((context["status"], context["value"]), ("unavailable", None))

    def test_reviews_outside_target_aliases_cannot_supply_measurement_sources(self):
        unrelated = self.write("other-frozen-review.json", {"ratings": [{"anonymous_id": "other-block", "score": None}]})
        freeze = replace(self.context.freeze, submissions=(*self.context.freeze.submissions,
            {"review_ref": unrelated, "received_at": RECEIVED}))
        self.context = replace(self.context, freeze=freeze)
        self.assertEqual(len(self.compile()["cells"]), 4)
        self.alter("observation_ref", lambda d: d.update(source_refs=[unrelated]), "omission-rate")
        with self.assertRaisesRegex(EvaluationValidationError, "unrelated"): self.compile()

    def test_estimation_method_is_pinned_and_paired_status_retained(self):
        # Change all four associations to the same externally selected estimated method.
        request = self.request(); method = self.inputs().read(request["method_ref"])
        method["estimation_method"] = "synthetic-ledger-v1"
        ref = self.write("estimated-method.json", method)
        for arm in PHASE_D_ARMS:
            self.request(arm=arm)["method_ref"] = ref
            self.alter("observation_ref", lambda d: d.update(method_ref=ref), arm=arm)
            self.alter("measurement_ref", lambda d: d.update(status="estimated", estimation_method="synthetic-ledger-v1"), arm=arm)
        self.assertEqual(next(r for r in self.paired()["pairs"][0]["metrics"] if r["metric_id"] == "cost")["status"], "estimated")
        self.alter("measurement_ref", lambda d: d.update(estimation_method="unregistered"))
        with self.assertRaisesRegex(EvaluationValidationError, "estimation method"): self.compile()

    def test_missing_or_duplicate_associations_are_rejected(self):
        original = self.context
        for requests in (original.associations[:-1], original.associations + original.associations[:1]):
            self.context = replace(original, associations=requests)
            with self.assertRaisesRegex(EvaluationValidationError, "uniquely cover"): self.compile()

    def test_run_case_replicate_attempt_slice_and_phase_substitution_are_rejected(self):
        original = copy.deepcopy(self.context)
        for key, value in (("run_id", "OTHER"), ("case_id", "C2"), ("replicate", 2), ("arm_id", "mode-no-skill"),
                           ("phase", "pilot"), ("attempt_ids", ["unrelated"]), ("slices", [{"attempt_id": "unrelated", "slice_index": 1}])):
            self.context = copy.deepcopy(original)
            self.alter("observation_ref", lambda d: d["target"].update({key: value}))
            with self.subTest(key=key), self.assertRaisesRegex(EvaluationValidationError, "target substitution"): self.compile()

    def test_measurement_target_protocol_value_and_unit_forgery_are_rejected(self):
        original = copy.deepcopy(self.context)
        for key, value in (("case_id", "C2"), ("arm_id", "mode-no-skill"), ("metric_id", "lookup-count"),
                           ("protocol_ref", self.pairwise_ref), ("value", 999), ("unit", "usd")):
            self.context = copy.deepcopy(original)
            self.alter("measurement_ref", lambda d: d.update({key: value}))
            with self.subTest(key=key), self.assertRaises(EvaluationValidationError): self.compile()

    def test_method_operation_source_and_preregistration_substitution_are_rejected(self):
        original = copy.deepcopy(self.context)
        for key, value in (("metric_id", "lookup-count"), ("unit", "EUR"), ("operation", "audit-count"),
                           ("registered_at", OBSERVED), ("source", "frozen-human-review")):
            self.context = copy.deepcopy(original)
            method = self.alter("method_ref", lambda d: d.update({key: value}))
            self.alter("observation_ref", lambda d: d.update(method_ref=self.request()["method_ref"]))
            with self.subTest(key=key), self.assertRaises(EvaluationValidationError): self.compile()
        self.context = copy.deepcopy(original)
        self.alter("observation_ref", lambda d: d.update(operation="audit-count", data={"count": 16}))
        with self.assertRaisesRegex(EvaluationValidationError, "operation substitution"): self.compile()

    def test_observation_pin_time_and_source_forgery_are_rejected(self):
        original = copy.deepcopy(self.context)
        stranger = self.write("unrelated.json", {"value": 16})
        for key, value in (("method_ref", stranger), ("observed_at", REVEALED), ("source_refs", [stranger]), ("source_refs", [])):
            self.context = copy.deepcopy(original)
            self.alter("observation_ref", lambda d: d.update({key: value}))
            with self.subTest(key=key), self.assertRaises(EvaluationValidationError): self.compile()
        self.context = copy.deepcopy(original)
        self.alter("observation_ref", lambda d: d["source_refs"].pop())
        with self.assertRaisesRegex(EvaluationValidationError, "full source scope"): self.compile()

    def test_all_failed_attempts_and_human_cost_components_are_required(self):
        original = copy.deepcopy(self.context)
        for mutate in (lambda d: d["data"]["execution"].pop(0), lambda d: d["data"]["execution"].reverse(),
                       lambda d: d["data"]["execution"].append(d["data"]["execution"][0]),
                       lambda d: d["data"]["human"].pop("supervision"), lambda d: d["data"].update(unit="EUR")):
            self.context = copy.deepcopy(original); self.alter("observation_ref", mutate, revalue=13)
            with self.assertRaises(EvaluationValidationError): self.compile()

    def test_context_currency_and_method_mismatches_are_not_paired(self):
        self.alter("method_ref", lambda d: d.update(method_id="different-frozen-method"))
        self.alter("observation_ref", lambda d: d.update(method_ref=self.request()["method_ref"]))
        result = self.paired()
        row = next(r for r in result["pairs"][1]["metrics"] if r["metric_id"] == "cost")
        self.assertEqual((row["status"], row["value"]), ("unavailable", None))
        for metric in ("context-loaded", "cost"):
            a = copy.deepcopy(result["pairs"][0]["metrics"][0])
            left = {"complete": True, "metrics": [{**a, "metric_id": metric, "unit": "tokens", "method_ref": None,
                     "measurement_ref": self.pairwise_ref, "value": 1}]}
            right = copy.deepcopy(left); right["metrics"][0]["unit"] = "characters" if metric == "context-loaded" else "EUR"
            self.assertIsNone(analysis._pair(left, right, metric, "system-level-including-transport")["value"])

    def test_ratio_denominator_and_count_integrality_are_checked(self):
        original = copy.deepcopy(self.context)
        for data in ({"numerator": 1, "denominator": 0}, {"numerator": 3, "denominator": 2}):
            self.context = copy.deepcopy(original)
            self.alter("observation_ref", lambda d: d.update(data=data), "omission-rate")
            with self.assertRaises(EvaluationValidationError): self.compile()
        self.context = copy.deepcopy(original)
        self.alter("observation_ref", lambda d: d.update(data={"count": .5}), "lookup-count")
        with self.assertRaises(EvaluationValidationError): self.compile()

    def test_outer_clock_cannot_be_replaced_by_host_or_slice_time(self):
        original = copy.deepcopy(self.context)
        for change in ({"clock": "host-interval"}, {"started_at": "2000-01-01T00:00:00Z"},
                       {"finished_at": "2026-09-12T00:00:00Z"}, {"finished_at": "2026-09-10T00:00:00Z"}):
            self.context = copy.deepcopy(original)
            self.alter("observation_ref", lambda d: d["data"].update(change), "completion-time")
            with self.assertRaises(EvaluationValidationError): self.compile()

    def test_missing_measurement_cannot_hide_numeric_or_unrelated_evidence(self):
        self.unavailable("cost")
        self.request()["method_ref"] = self.pairwise_ref
        with self.assertRaisesRegex(EvaluationValidationError, "hide numeric"): self.compile()
        self.request()["method_ref"] = None
        self.alter("measurement_ref", lambda d: d.update(evidence_refs=[self.pairwise_ref]))
        with self.assertRaisesRegex(EvaluationValidationError, "unrelated missing"): self.compile()

    def test_numeric_needs_method_and_registered_fixed_operation(self):
        original = copy.deepcopy(self.context)
        self.request()["method_ref"] = None
        with self.assertRaisesRegex(EvaluationValidationError, "pinned method"): self.compile()
        self.context = copy.deepcopy(original)
        self.alter("method_ref", lambda d: d.update(operation="audit-count"))
        self.alter("observation_ref", lambda d: d.update(method_ref=self.request()["method_ref"],
                                                         operation="audit-count", data={"count": 16}))
        with self.assertRaisesRegex(EvaluationValidationError, "fixed metric"): self.compile()

    def test_measurement_check_cannot_precede_selected_reveal(self):
        self.context = replace(self.context, checked_at=FROZEN)
        with self.assertRaisesRegex(EvaluationValidationError, "precedes reveal"): self.compile()

    def test_no_execution_cannot_supply_loaded_context_or_whole_arm_time(self):
        for metric in ("context-loaded", "completion-time"):
            target = {"attempt_ids": []}
            request = self.request(metric)
            method = self.inputs().read(request["method_ref"])
            observation = self.inputs().read(request["observation_ref"])
            with self.assertRaisesRegex(EvaluationValidationError, "no execution"):
                analysis._value(method, observation, target, self.context)

    def test_human_source_cannot_be_replaced_by_execution_or_pre_freeze_review(self):
        self.alter("method_ref", lambda d: d.update(source="execution-observation"), "omission-rate")
        self.alter("observation_ref", lambda d: d.update(method_ref=self.request("omission-rate")["method_ref"]), "omission-rate")
        with self.assertRaisesRegex(EvaluationValidationError, "Human metric"): self.compile()

    def test_external_measurement_authority_rejects_resigned_arithmetic_forgery(self):
        trusted = {r["measurement_ref"]["sha256"] for r in self.context.associations}
        self.alter("observation_ref", lambda d: d["data"]["human"].update(review=8), revalue=22)
        with self.assertRaisesRegex(EvaluationValidationError, "rejected measurement"):
            self.compile(measurement_verifier=lambda p: p["measurement_ref"]["sha256"] in trusted)
        for authority in (None, lambda _: False, lambda _: "accepted"):
            with self.assertRaises(EvaluationValidationError): self.compile(measurement_verifier=authority)
        def mutator(payload):
            payload["measurement"]["value"] = 0
            return True
        self.assertEqual(self.compile(measurement_verifier=mutator)["cells"][0]["metrics"][-2]["value"], 22)

    def test_actual_drift_and_incomplete_blocks_fail_or_remain_diagnostic(self):
        original = copy.deepcopy(self.evidence)
        self.evidence["slots"][1]["lifecycle"] = "post-call-failed"
        self.context = replace(self.context, review=replace(self.context.review,
            expected_evidence_ref=self.write("incomplete.json", self.evidence)))
        # Missing values need no observation rewritten against changed target hash.
        for arm in PHASE_D_ARMS:
            for m in FIXED_METRIC_SET: self.unavailable(m.metric_id, arm=arm)
        self.assertTrue(all(p["complete_block"] is False and all(r["value"] is None for r in p["metrics"])
                            for p in self.paired()["pairs"]))
        original["slots"][0]["slices"][0]["comparison"] = "differs-from-frozen"
        self.context = replace(self.context, review=replace(self.context.review,
            expected_evidence_ref=self.write("drift.json", original)))
        with self.assertRaisesRegex(EvaluationValidationError, "actual identity drift"): self.paired()

    def test_pilot_overlap_unknown_and_package_comparison_never_upgrade_primary(self):
        for interpretation in ("skill-conditional-increment", "skill-bearing-package-effect", "unavailable"):
            for overlap in ("held-out", "admission-overlap", "unresolved"):
                result = self.paired(interpretation=interpretation, overlap=overlap)
                pair = next(p for p in result["pairs"] if p["contrast"] == "A4-A3")
                self.assertEqual(pair["interpretation"], interpretation)
                self.assertTrue(all(p["primary_confirmatory_eligible"] is False for p in result["pairs"]))
                if interpretation == "unavailable": self.assertTrue(all(r["value"] is None for r in pair["metrics"]))

    def test_analysis_requires_current_timed_preregistered_comparisons(self):
        original = self.analysis_context()
        for changes in ({"pairwise": ()}, {"pairwise": original.pairwise * 2}, {"checked_at": AT}):
            with self.assertRaises(EvaluationValidationError): self.paired(replace(original, **changes))
        document = self.inputs().read(original.pairwise[0]["ref"])
        for key, value in (("stage", "plan-pre-run"), ("checked_at", CHECKED), ("preregistered_record_ref", original.expected_metrics_ref)):
            ref = self.write(f"bad-comparison-{key}.json", {**document, key: value})
            with self.assertRaises(EvaluationValidationError): self.paired(replace(original, pairwise=({"case_id": "C1", "ref": ref},)))

    def test_resigned_result_or_validator_drift_cannot_reuse_validation(self):
        document = self.compile(); document["cells"][0]["metrics"][0]["value"] = 0
        ref = self.write("forged-metrics.json", document)
        with self.assertRaisesRegex(EvaluationValidationError, "independently selected"):
            analysis.validate_harness_metrics(self.inputs(), expected_metrics_ref=ref, expected_metrics_id="M1", context=self.context, **self.auth)
        identity = analysis.validator_identity(self.inputs())
        with patch.object(analysis, "validator_identity", side_effect=[identity, {**identity, "version": "changed"}]), \
             self.assertRaisesRegex(EvaluationValidationError, "validator changed"): self.compile()
        def drift(payload):
            (self.root / self.request()["measurement_ref"]["path"]).write_text('{}', encoding="utf-8")
            return True
        with self.assertRaises(EvaluationValidationError): self.compile(measurement_verifier=drift)


class HarnessAnalysisIntegrationTests(unittest.TestCase):
    def test_real_four_arm_chain_and_cold_analysis_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture, context, ref, document = build_analysis_chain(Path(directory))
            self.assertTrue(all(p["primary_confirmatory_eligible"] is False for p in document["pairs"]))
            self.assertTrue(all(r["status"] == "unavailable" and r["value"] is None for p in document["pairs"] for r in p["metrics"]))
            context_ref = fixture.write("analysis/context.json", {"context": asdict(context), "analysis_ref": ref})
            script = r'''
import json,sys
from pathlib import Path
from unittest.mock import patch
from research_workbench.evaluation.harness_analysis import MetricContext,AnalysisContext,validate_harness_analysis
from research_workbench.evaluation.harness_execution import HarnessContext
from research_workbench.evaluation.harness_review import ReviewContext,FreezeContext
from research_workbench.evaluation.pins import EvaluationInputs
from tests.harness_analysis_data import AUTH
assert 'tests.test_evaluation_harness_analysis' not in sys.modules
root, schemas, ref=sys.argv[1:]
def audit(event,args):
    if event in {'subprocess.Popen','socket.connect'}: raise AssertionError('execution during H4c replay')
    if event=='exec' and args[0].co_filename.replace('\\','/').startswith(root.replace('\\','/')+'/'):
        raise AssertionError('project code during H4c replay')
sys.addaudithook(audit)
inputs=EvaluationInputs(root,schemas); data=inputs.read(json.loads(ref)); ctx=data['context']; metric=ctx['metrics']
metric['review']['harness']=HarnessContext(**metric['review']['harness'])
metric['review']=ReviewContext(**metric['review']); metric['freeze']=FreezeContext(**metric['freeze'])
ctx['metrics']=MetricContext(**metric); context=AnalysisContext(**ctx)
with patch('research_workbench.evaluation.harness_execution.run_baseline_session',side_effect=AssertionError('M6 called')),patch('research_workbench.evaluation.harness_runtime.execute_frozen_view',side_effect=AssertionError('Host called')):
    doc=validate_harness_analysis(inputs,expected_analysis_ref=data['analysis_ref'],expected_analysis_id='H4C-ANALYSIS',context=context,**AUTH)
assert all(p['primary_confirmatory_eligible'] is False for p in doc['pairs'])
print('cold H4c replay PASS')
'''
            result = subprocess.run([sys.executable, "-c", script, directory, str(ROOT / "schemas"), json.dumps(context_ref)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "cold H4c replay PASS")
            document["pairs"][0]["metrics"][0].update(status="measured", value=0)
            forged = fixture.write("analysis/forged.json", document)
            with self.assertRaisesRegex(EvaluationValidationError, "independently rebuilt"):
                analysis.validate_harness_analysis(fixture.inputs(), expected_analysis_ref=forged,
                    expected_analysis_id="H4C-ANALYSIS", context=context, **AUTH)
            comparison = fixture.inputs().read(context.pairwise[0]["ref"])
            comparison["result"].update(status="exact-skill-only", interpretation="skill-conditional-increment")
            changed_ref = fixture.write("analysis/upgraded-comparison.json", comparison)
            changed = replace(context, pairwise=tuple({"case_id": r["case_id"], "ref": changed_ref} for r in context.pairwise))
            with self.assertRaises(EvaluationValidationError):
                analysis.compile_harness_analysis(fixture.inputs(), context=changed, analysis_id="FORGED", **AUTH)


if __name__ == "__main__": unittest.main()
