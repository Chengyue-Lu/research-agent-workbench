"""Pinned measurement associations and diagnostic paired inputs, never scoring.

Observation/method trust is external. Arithmetic reconstructs supplied typed
observations; it does not infer a research judgement from a response or Trace.
All records retain the bounded synthetic purpose and no analysis authority.
"""

from __future__ import annotations

import copy
import hashlib
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

from research_workbench.evaluation.comparability import validate_comparability
from research_workbench.evaluation.harness_execution import BOUNDARIES
from research_workbench.evaluation.harness_plan import validate_request
from research_workbench.evaluation.harness_review import (
    FreezeContext, ReviewContext, _authorize, validate_review_reveal,
    validator_identity as review_identity,
)
from research_workbench.evaluation.harness_runtime import plain
from research_workbench.evaluation.manifest import FIXED_METRIC_SET
from research_workbench.evaluation.overlap import validate_overlap
from research_workbench.evaluation.pins import digest, file_ref, require, timestamp
from research_workbench.evaluation.system_protocol import validate_measurement

PREFIX = "evaluation_harness_"
HUMAN_METRICS = frozenset({"method-violation", "claim-overreach", "counterevidence-omission",
    "human-correction-distance", "omission-rate", "h2-distortion-rate", "cascade-rate"})
ARMS = {"A1": "plain-agent", "A2": "plain-agent-tool", "A3": "mode-no-skill", "A4": "mode-candidate-skill"}
HUMAN_COST = ("preparation", "supervision", "review", "correction", "recovery")


@dataclass(frozen=True)
class MetricContext:
    review: ReviewContext
    freeze: FreezeContext
    expected_freeze_ref: dict
    expected_reveal_ref: dict
    revealed_at: str
    checked_at: str
    # Caller-selected complete (block_index, arm_id, metric_id) requests, each
    # with measurement_ref and optional method/observation refs + trusted times.
    associations: tuple[dict, ...]


@dataclass(frozen=True)
class AnalysisContext:
    metrics: MetricContext
    expected_metrics_ref: dict
    expected_metrics_id: str
    checked_at: str
    # Caller-selected case_id/ref pairs; each record has analysis-input stage.
    pairwise: tuple[dict, ...]


def validator_identity(inputs):
    identity = review_identity(inputs)
    sources = {**identity["sources"], "research_workbench/evaluation/harness_analysis.py":
               hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    return {**identity, "identity": "evaluation-harness-analysis", "sources": dict(sorted(sources.items()))}


def _record(kind, **fields):
    return {"schema_version": "0.1.0", "record_kind": PREFIX + kind, "version": "1.0.0",
            "purpose": "synthetic-contract-proof", **fields}


def _finish(inputs, identity, document):
    inputs.validate(document["record_kind"], document)
    require(identity == validator_identity(inputs), "analysis validator changed during validation")
    inputs.recheck()
    return document


def _load(inputs, context, admission_verifier, projection_verifier, human_verifier):
    validate_review_reveal(inputs, expected_reveal_ref=context.expected_reveal_ref,
        expected_freeze_ref=context.expected_freeze_ref, revealed_at=context.revealed_at,
        context=context.review, freeze=context.freeze, admission_verifier=admission_verifier,
        projection_verifier=projection_verifier, human_verifier=human_verifier)
    require(timestamp(context.revealed_at) <= timestamp(context.checked_at), "measurement check precedes reveal")
    return (inputs.read(context.review.expected_evidence_ref),
            inputs.read(context.review.harness.expected_plan_ref),
            inputs.read(context.freeze.expected_mapping_ref))


def _cell(slots, run_id):
    first = slots[0]
    attempts = [{"attempt_id": s["slot"]["attempt_id"], "retry_index": s["slot"]["retry_index"],
        "lifecycle": s["lifecycle"], "journal_ref": s["journal_ref"],
        "slices": [{k: row[k] for k in ("attempt_id", "slice_index", "lifecycle", "comparison", "receipt_ref")}
                   for row in s["slices"]]} for s in slots]
    executed = [a for a in attempts if a["journal_ref"] is not None]
    target = {k: first[k] for k in ("block_index", "case_id", "phase", "replicate", "arm_id")}
    target.update(run_id=run_id, attempts_sha256=digest(attempts),
        attempt_ids=[a["attempt_id"] for a in executed],
        slices=[{"attempt_id": row["attempt_id"], "slice_index": row["slice_index"]}
                for a in attempts for row in a["slices"]])
    return target, attempts, bool(executed and executed[-1]["lifecycle"] == "completed")


def _sources(inputs, slots, mapping, context):
    allowed, journals = {}, []
    def add(ref):
        if ref is not None:
            ref = file_ref(ref)
            allowed[digest(ref)] = ref
    for slot in slots:
        add(slot["journal_ref"])
        if slot["journal_ref"] is not None:
            journals.append(file_ref(slot["journal_ref"]))
        for row in slot["slices"]:
            add(row["receipt_ref"])
            if row["evidence"] is not None:
                evidence = row["evidence"]
                for key in ("host_ref", "trace_ref"):
                    add(evidence[key])
                for key in ("fact_refs", "artifact_refs", "validation_refs"):
                    for ref in evidence[key]:
                        add(ref)
    slice_ids = {(r["attempt_id"], r["slice_index"]) for s in slots for r in s["slices"]}
    aliases = {r["anonymous_id"] for r in mapping["entries"] if (r["attempt_id"], r["slice_index"]) in slice_ids}
    reviews, ratings = [], []
    for submission in context.freeze.submissions:
        doc = inputs.read(submission["review_ref"])
        selected = [r for r in doc["ratings"] if r["anonymous_id"] in aliases]
        if selected:
            reviews.append(file_ref(submission["review_ref"]))
            ratings.extend(selected)
            add(submission["review_ref"])
    return allowed, journals, reviews, ratings


def _ledger(rows, target):
    ids = [r["attempt_id"] for r in rows]
    require(len(ids) == len(set(ids)) and ids == target["attempt_ids"],
            "ledger must retain every executed Attempt including failures in order")
    return sum((Decimal(str(r["value"])) for r in rows), Decimal(0))


def _value(method, observation, target, context):
    data, operation = observation["data"], method["operation"]
    metric = method["metric_id"]
    definition = next(m for m in FIXED_METRIC_SET if m.metric_id == metric)
    expected = {"count": "audit-count", "ratio": "audit-ratio", "characters-or-tokens": "context-ledger",
                "currency": "cost-ledger", "minutes": "outer-wall-clock"}[definition.unit]
    require(operation == expected, "measurement method does not match fixed metric")
    if operation == "audit-count":
        return data["count"]
    if operation == "audit-ratio":
        require(data["numerator"] <= data["denominator"], "audit ratio numerator exceeds denominator")
        return float(Decimal(data["numerator"]) / Decimal(data["denominator"]))
    require(data.get("unit", method["unit"]) == method["unit"], "observation unit substitution")
    if operation == "context-ledger":
        require(bool(target["attempt_ids"]), "no execution supports loaded context")
        return float(_ledger(data["attempts"], target))
    if operation == "cost-ledger":
        return float(_ledger(data["execution"], target) + sum(
            (Decimal(str(data["human"][key])) for key in HUMAN_COST), Decimal(0)))
    require(bool(target["attempt_ids"]), "no execution supports outer wall time")
    start, finish = timestamp(data["started_at"]), timestamp(data["finished_at"])
    require(timestamp(context.review.harness.expected_preflight_checked_at) <= start <= finish
            <= timestamp(observation["observed_at"]), "outer wall-clock observations are unordered")
    return (finish - start).total_seconds() / 60


def _measurement(inputs, request, target, slots, mapping, context, measurement_verifier):
    document = inputs.read(request["measurement_ref"], "evaluation_measurement")
    validate_measurement(inputs, document, expected_protocol_ref=context.review.harness.expected_protocol_ref)
    require(document["case_id"] == target["case_id"] and document["arm_id"] == target["arm_id"]
            and document["metric_id"] == request["metric_id"], "measurement target substitution")
    allowed, journals, reviews, ratings = _sources(inputs, slots, mapping, context)
    method = observation = None
    numeric = document["status"] in {"measured", "estimated"}
    if numeric:
        require(request["method_ref"] is not None and request["observation_ref"] is not None,
                "numeric measurement needs pinned method and observation")
        method = inputs.read(request["method_ref"], PREFIX + "metric_method")
        observation = inputs.read(request["observation_ref"], PREFIX + "metric_observation")
        require(method["metric_id"] == document["metric_id"] and method["unit"] == document["unit"],
                "measurement method metric/unit substitution")
        require(method["registered_at"] == request["method_registered_at"] and
                timestamp(method["registered_at"]) <= timestamp(context.review.harness.case_selection_frozen_at),
                "measurement method must have independently trusted preregistration")
        require(observation["method_ref"] == file_ref(request["method_ref"]) and observation["target"] == target,
                "observation method or run/Attempt target substitution")
        require(observation["operation"] == method["operation"], "observation operation substitution")
        require(observation["observed_at"] == request["observed_at"] and
                timestamp(context.review.harness.expected_preflight_checked_at) <= timestamp(observation["observed_at"])
                <= timestamp(context.checked_at), "observation trusted time substitution")
        sources = [file_ref(ref) for ref in observation["source_refs"]]
        for ref in sources:
            inputs.read_bytes(ref)
        require(len(sources) == len({digest(ref) for ref in sources}) and
                all(digest(ref) in allowed for ref in sources), "unrelated or duplicate observation source")
        required = reviews if document["metric_id"] in HUMAN_METRICS else journals
        require(all(ref in sources for ref in required) and bool(sources), "observation does not cover its full source scope")
        if document["metric_id"] in HUMAN_METRICS:
            require(method["source"] == "frozen-human-review" and bool(reviews) and
                    timestamp(context.freeze.frozen_at) <= timestamp(observation["observed_at"]),
                    "Human metric must consume the selected frozen reviews")
        else:
            require(method["source"] == "execution-observation", "execution metric source substitution")
        require(document["evidence_refs"] == [file_ref(request["observation_ref"])],
                "measurement evidence must be its selected observation")
        require(document["estimation_method"] == method["estimation_method"], "estimation method substitution")
        require(document["value"] == _value(method, observation, target, context), "measurement value differs from method reconstruction")
    else:
        require(all(request[k] is None for k in ("method_ref", "observation_ref", "method_registered_at", "observed_at")),
                "missing measurement cannot hide numeric observations")
        require(all(digest(file_ref(ref)) in allowed for ref in document["evidence_refs"]), "unrelated missing-value evidence")
    _authorize(measurement_verifier, "measurement", target=target, measurement_ref=request["measurement_ref"],
        measurement=document, method=method, observation=observation, frozen_ratings=ratings)
    return {**{k: document[k] for k in ("metric_id", "status", "unit", "value", "reason", "estimation_method")},
            **{k: copy.deepcopy(request[k]) for k in ("measurement_ref", "method_ref", "observation_ref",
                                                     "method_registered_at", "observed_at")}}


def compile_harness_metrics(inputs, *, context: MetricContext, metrics_id: str,
                            admission_verifier, projection_verifier, human_verifier, measurement_verifier):
    context = copy.deepcopy(context)
    request = plain(asdict(context))
    validate_request(inputs, PREFIX + "metric_evidence", request)
    identity = validator_identity(inputs)
    evidence, plan, mapping = _load(inputs, context, admission_verifier, projection_verifier, human_verifier)
    requests = {(r["block_index"], r["arm_id"], r["metric_id"]): r for r in context.associations}
    expected = {(index, arm["arm_id"], metric.metric_id) for index, block in enumerate(plan["blocks"])
                for arm in block["arms"] for metric in FIXED_METRIC_SET}
    require(len(requests) == len(context.associations) and set(requests) == expected,
            "associations must uniquely cover every planned cell and all 13 metrics")
    cells = []
    for index, block in enumerate(plan["blocks"]):
        for arm in block["arms"]:
            slots = [s for s in evidence["slots"] if s["block_index"] == index and s["arm_id"] == arm["arm_id"]]
            target, attempts, complete = _cell(slots, context.review.harness.expected_run_id)
            rows = [_measurement(inputs, requests[index, arm["arm_id"], m.metric_id], target, slots, mapping,
                                 context, measurement_verifier) for m in FIXED_METRIC_SET]
            cells.append({"target": target, "attempts": attempts, "complete": complete, "metrics": rows})
    return _finish(inputs, identity, _record("metric_evidence", metrics_id=metrics_id, request=request,
        protocol_ref=file_ref(context.review.harness.expected_protocol_ref), evidence_ref=file_ref(context.review.expected_evidence_ref),
        reveal_ref=file_ref(context.expected_reveal_ref), checked_at=context.checked_at,
        cells=cells, validator=identity, boundaries=dict(BOUNDARIES)))


def validate_harness_metrics(inputs, *, expected_metrics_ref, expected_metrics_id, context, **verifiers):
    actual = inputs.read(expected_metrics_ref, PREFIX + "metric_evidence")
    expected = compile_harness_metrics(inputs, context=context, metrics_id=expected_metrics_id, **verifiers)
    require(actual == expected, "metric evidence differs from independently selected measurements")
    return expected


def _comparisons(inputs, context, admission_verifier):
    harness = context.metrics.review.harness
    preflight = inputs.read(harness.expected_preflight_ref)
    overlap = validate_overlap(inputs, inputs.read(preflight["request"]["overlap_ref"], "admission_evidence_overlap"),
        expected_protocol_ref=harness.expected_protocol_ref, expected_case_closure_ref=harness.expected_case_closure_ref,
        case_selection_frozen_at=harness.case_selection_frozen_at)
    selected = {r["case_id"]: r["ref"] for r in context.pairwise}
    bindings = preflight["request"]["case_bindings"]
    require(len(selected) == len(context.pairwise) and set(selected) == {b["case_id"] for b in bindings},
            "analysis comparisons must uniquely cover all frozen cases")
    results = []
    for binding in bindings:
        ref = selected[binding["case_id"]]
        document = inputs.read(ref, "a3_a4_pairwise_comparability")
        require(document["stage"] == "analysis-input" and document["checked_at"] == context.checked_at,
                "analysis needs externally timed analysis-input comparison")
        require(document["preregistered_record_ref"] == file_ref(binding["pairwise_ref"]), "analysis preregistration substitution")
        result = validate_comparability(inputs, document, expected_protocol_ref=harness.expected_protocol_ref,
            expected_case_closure_ref=harness.expected_case_closure_ref, case_selection_frozen_at=harness.case_selection_frozen_at,
            admission_verifier=admission_verifier)
        results.append({"case_id": binding["case_id"], "ref": file_ref(ref), "result": copy.deepcopy(result)})
    return overlap, results


def _pair(left, right, metric, interpretation):
    a, b = (next(row for row in cell["metrics"] if row["metric_id"] == metric) for cell in (left, right))
    status, value, reason = "unavailable", None, "incomplete block or missing/incompatible measurement"
    if (left["complete"] and right["complete"] and interpretation != "unavailable"
            and a["unit"] == b["unit"] and a["method_ref"] == b["method_ref"]):
        if a["value"] is not None and b["value"] is not None:
            status = "estimated" if "estimated" in (a["status"], b["status"]) else "measured"
            value, reason = float(Decimal(str(a["value"])) - Decimal(str(b["value"]))), "paired difference under frozen method/status"
        elif a["status"] == b["status"] == "not-applicable":
            status, reason = "not-applicable", "both sides explicitly not applicable"
    return {"metric_id": metric, "left_measurement_ref": a["measurement_ref"], "right_measurement_ref": b["measurement_ref"],
            "left_status": a["status"], "right_status": b["status"], "left_unit": a["unit"], "right_unit": b["unit"],
            "status": status, "value": value, "reason": reason}


def compile_harness_analysis(inputs, *, context: AnalysisContext, analysis_id: str, **verifiers):
    context = copy.deepcopy(context)
    request = plain(asdict(context))
    validate_request(inputs, PREFIX + "analysis_input", request)
    identity = validator_identity(inputs)
    require(timestamp(context.metrics.checked_at) <= timestamp(context.checked_at), "analysis precedes measurement check")
    metrics = validate_harness_metrics(inputs, expected_metrics_ref=context.expected_metrics_ref,
        expected_metrics_id=context.expected_metrics_id, context=context.metrics, **verifiers)
    require(all(r["comparison"] != "differs-from-frozen" for cell in metrics["cells"] for a in cell["attempts"] for r in a["slices"]),
            "analysis actual identity drift")
    overlap, comparisons = _comparisons(inputs, context, verifiers["admission_verifier"])
    protocol = inputs.read(context.metrics.review.harness.expected_protocol_ref)
    rules = protocol["rules"]
    by_case = {c["case_id"]: c["result"] for c in comparisons}
    pairs = []
    cells = {(c["target"]["block_index"], c["target"]["arm_id"]): c for c in metrics["cells"]}
    for index in sorted({key[0] for key in cells}):
        block_complete = all(c["complete"] for (block, _), c in cells.items() if block == index)
        for contrast in [rules["primary"]["contrast"], *rules["secondary"]]:
            left_id, right_id = contrast.split("-")
            left, right = cells[index, ARMS[left_id]], cells[index, ARMS[right_id]]
            interpretation = rules["primary"]["interpretation"] if contrast == rules["primary"]["contrast"] else rules["secondary"][contrast]
            if contrast == "A4-A3":
                interpretation = by_case[left["target"]["case_id"]]["interpretation"]
            rows = [_pair({**left, "complete": block_complete}, {**right, "complete": block_complete}, m.metric_id,
                          interpretation) for m in FIXED_METRIC_SET]
            pairs.append({**{k: left["target"][k] for k in ("block_index", "case_id", "phase", "replicate")},
                "contrast": contrast, "interpretation": interpretation, "complete_block": block_complete,
                "primary_confirmatory_eligible": False, "metrics": rows})
    return _finish(inputs, identity, _record("analysis_input", analysis_id=analysis_id, request=request,
        metrics_ref=file_ref(context.expected_metrics_ref), protocol_ref=file_ref(context.metrics.review.harness.expected_protocol_ref),
        reveal_ref=file_ref(context.metrics.expected_reveal_ref), checked_at=context.checked_at,
        overlap=copy.deepcopy(dict(overlap)), comparisons=comparisons,
        statistical_parameters=copy.deepcopy(protocol["design"]["analysis"]), decision_hierarchy=copy.deepcopy(rules["decision_hierarchy"]),
        pairs=pairs, validator=identity, boundaries=dict(BOUNDARIES)))


def validate_harness_analysis(inputs, *, expected_analysis_ref, expected_analysis_id, context, **verifiers):
    actual = inputs.read(expected_analysis_ref, PREFIX + "analysis_input")
    expected = compile_harness_analysis(inputs, context=context, analysis_id=expected_analysis_id, **verifiers)
    require(actual == expected, "analysis input differs from independently rebuilt pairing")
    return expected
