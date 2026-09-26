"""Fresh real H3/H4a/H4b closure, with honestly unavailable H4c measurements."""

from dataclasses import replace

from research_workbench.evaluation import harness_analysis as analysis, harness_review as review
from research_workbench.evaluation.harness_evidence import compile_harness_evidence
from research_workbench.evaluation.harness_execution import BOUNDARIES, execute_harness
from research_workbench.evaluation.manifest import FIXED_METRIC_SET
from tests.harness_analysis_data import AUTH, CREATED, RECEIVED, FROZEN, REVEALED, CHECKED, ANALYZED
from tests.harness_execution_fixtures import ExecutionFixture, FixedClock, LocalDriver
from tests.system_evaluation_fixtures import AT, BOUNDARIES as MEASUREMENT_BOUNDARIES, record


def missing_associations(fixture, evidence):
    requests = []
    for index, block in enumerate(fixture.plan["blocks"]):
        for arm in block["arms"]:
            for metric in FIXED_METRIC_SET:
                unit = {"characters-or-tokens": "tokens", "currency": "USD"}.get(metric.unit, metric.unit)
                name = f"measurements/{index}-{arm['arm_id']}-{metric.metric_id}.json"
                ref = fixture.write(name, record("evaluation_measurement", "measurement_id", name,
                    protocol_ref=fixture.protocol_ref, case_id=block["case_id"], arm_id=arm["arm_id"],
                    metric_id=metric.metric_id, status="unavailable", unit=unit, value=None,
                    reason="Synthetic integer rubric and execution archives do not establish this whole-arm metric.",
                    evidence_refs=[], estimation_method=None, boundaries=dict(MEASUREMENT_BOUNDARIES)))
                requests.append({"block_index": index, "arm_id": arm["arm_id"], "metric_id": metric.metric_id,
                    "measurement_ref": ref, "method_ref": None, "observation_ref": None,
                    "method_registered_at": None, "observed_at": None})
    return tuple(requests)


def build_analysis_chain(root):
    fixture = ExecutionFixture(root).build_execution()
    ports = fixture.ports()
    def driver(view, recorder, destination, skill=False):
        return LocalDriver(view, recorder, destination, skill=skill,
                           output=review._record("review_artifact", format="synthetic-integer-v1",
                                                answer=7, transport_metadata={"skill": "private-synthetic-treatment"}))
    ports = replace(ports, core_driver=driver, skill_driver=lambda *args: driver(*args, skill=True))
    execution_ref = execute_harness(fixture.inputs(), context=fixture.context, ports=ports,
                                   clock=FixedClock(), admission_verifier=AUTH["admission_verifier"])
    evidence = compile_harness_evidence(fixture.inputs(), execution_ref=execution_ref,
        context=fixture.context, evidence_id="H4C-SYNTHETIC", admission_verifier=AUTH["admission_verifier"])
    evidence_ref = fixture.write("evidence.json", evidence)
    policy_ref = fixture.write("policy.json", review._record("review_policy", protocol_ref=fixture.protocol_ref,
        registered_at=AT, cases=[{"case_id": c["case_id"], "reference_integer": 7} for c in fixture.plan["cases"]],
        projection_rule="synthetic-integer-v1", review_unit="every-planned-slice-including-unstarted",
        instruction=review.INSTRUCTION, rubric=review.RUBRIC, boundaries=dict(BOUNDARIES)))
    context = review.ReviewContext(fixture.context, execution_ref, evidence_ref,
                                  "H4C-SYNTHETIC", policy_ref, AT, CREATED)
    package, mapping = review.prepare_review_package(fixture.inputs(), context=context,
        admission_verifier=AUTH["admission_verifier"], projection_verifier=AUTH["projection_verifier"])
    package_ref = fixture.write("public/review.json", package)
    mapping_ref = fixture.write("private/mapping.json", mapping)
    human_ref = fixture.write("private/human.json", review._record("human_review", package_ref=package_ref,
        reviewer={"actor_id": "synthetic-h4c-reviewer", "display_name": "Synthetic Reviewer"},
        ratings=[{"anonymous_id": s["anonymous_id"], "disposition": "scored" if s["availability"] == "reviewable" else "unreviewable",
                  "score": "correct" if s["availability"] == "reviewable" else None,
                  "reason": None if s["availability"] == "reviewable" else "No assessable output"} for s in package["slots"]],
        boundaries=dict(BOUNDARIES)))
    freeze = review.FreezeContext(package_ref, mapping_ref, ({"review_ref": human_ref, "received_at": RECEIVED},), FROZEN)
    review_auth = {k: v for k, v in AUTH.items() if k != "measurement_verifier"}
    frozen_ref = fixture.write("private/frozen.json", review.freeze_human_reviews(
        fixture.inputs(), context=context, freeze=freeze, **review_auth))
    reveal_ref = fixture.write("private/reveal.json", review.reveal_human_reviews(
        fixture.inputs(), context=context, freeze=freeze, expected_freeze_ref=frozen_ref,
        revealed_at=REVEALED, **review_auth))
    metric_context = analysis.MetricContext(context, freeze, frozen_ref, reveal_ref,
        REVEALED, CHECKED, missing_associations(fixture, evidence))
    metrics = analysis.compile_harness_metrics(fixture.inputs(), context=metric_context,
                                              metrics_id="H4C-METRICS", **AUTH)
    metrics_ref = fixture.write("analysis/metrics.json", metrics)
    pairwise = {**fixture.pairwise, "stage": "analysis-input", "checked_at": ANALYZED,
                "preregistered_record_ref": fixture.pairwise_ref}
    pairwise_ref = fixture.write("analysis/pairwise.json", pairwise)
    analysis_context = analysis.AnalysisContext(metric_context, metrics_ref, "H4C-METRICS", ANALYZED,
        tuple({"case_id": b["case_id"], "ref": pairwise_ref} for b in fixture.case_bindings))
    document = analysis.compile_harness_analysis(fixture.inputs(), context=analysis_context,
                                                analysis_id="H4C-ANALYSIS", **AUTH)
    analysis_ref = fixture.write("analysis/paired.json", document)
    return fixture, analysis_context, analysis_ref, document
