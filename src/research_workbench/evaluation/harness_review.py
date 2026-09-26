"""Bounded synthetic blind review; all authority and trusted clocks are external.

Only the public package is distributable to reviewers. Context, policy, mapping,
reviews, freeze and reveal are private evaluation records. No execution or scoring
port exists here. Generic text anonymization is deliberately unsupported.
"""

from __future__ import annotations

import copy
import hashlib
import re
import secrets
from dataclasses import dataclass
from pathlib import Path

from research_workbench.evaluation.harness_evidence import (
    validate_harness_evidence, validator_identity as evidence_identity,
)
from research_workbench.evaluation.harness_execution import BOUNDARIES, HarnessContext
from research_workbench.evaluation.pins import digest, file_ref, require, timestamp

PREFIX = "evaluation_harness_"
RUBRIC = {"criterion": "synthetic-integer-equality", "choices": ["correct", "incorrect"]}
INSTRUCTION = "Review the integer answer against the supplied synthetic reference."


@dataclass(frozen=True)
class ReviewContext:
    harness: HarnessContext
    expected_execution_ref: dict
    expected_evidence_ref: dict
    expected_evidence_id: str
    expected_policy_ref: dict
    policy_registered_at: str
    package_created_at: str


@dataclass(frozen=True)
class FreezeContext:
    expected_package_ref: dict
    expected_mapping_ref: dict
    # Each entry is an independently selected review_ref and trusted received_at.
    submissions: tuple[dict, ...]
    frozen_at: str


def validator_identity(inputs):
    identity = evidence_identity(inputs)
    sources = {**identity["sources"], "research_workbench/evaluation/harness_review.py":
               hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    return {**identity, "identity": "evaluation-harness-review", "sources": dict(sorted(sources.items()))}


def _record(kind, **fields):
    return {"schema_version": "0.1.0", "record_kind": PREFIX + kind, "version": "1.0.0",
            "purpose": "synthetic-contract-proof", **fields}


def _authorize(verifier, operation, **fields):
    require(callable(verifier), "external named authority verifier is required")
    require(verifier(copy.deepcopy({"operation": operation, **fields})) is True,
            f"external authority rejected {operation}")


def _finish(inputs, identity, *documents):
    for document in documents:
        inputs.validate(document["record_kind"], document)
    require(identity == validator_identity(inputs), "review validator changed during validation")
    inputs.recheck()


def _evidence(inputs, context, admission_verifier):
    evidence = validate_harness_evidence(inputs, inputs.read(context.expected_evidence_ref),
        expected_execution_ref=context.expected_execution_ref, context=context.harness,
        expected_evidence_id=context.expected_evidence_id, admission_verifier=admission_verifier)
    policy = inputs.read(context.expected_policy_ref, PREFIX + "review_policy")
    require(policy["protocol_ref"] == file_ref(context.harness.expected_protocol_ref),
            "review policy Protocol substitution")
    require(policy["registered_at"] == context.policy_registered_at, "policy trusted time substitution")
    require(timestamp(context.policy_registered_at) <= timestamp(context.harness.case_selection_frozen_at)
            <= timestamp(context.harness.expected_preflight_checked_at) <= timestamp(context.package_created_at),
            "review policy must be preregistered before case freeze and execution")
    plan = inputs.read(context.harness.expected_plan_ref)
    require(sorted(c["case_id"] for c in policy["cases"]) == sorted(c["case_id"] for c in plan["cases"]),
            "review policy must cover all cases exactly once")
    return evidence, policy


def _project(inputs, slice_record):
    """Exact whitelist: no free text/metadata reaches the public package.

    Every unique artifact is retained privately. This initial format permits one
    evaluated integer artifact per slice. Duplicate output-contract references to
    identical bytes are retained in source_refs, but project to one answer.
    """
    sources = [] if slice_record["evidence"] is None else slice_record["evidence"]["artifact_refs"]
    if slice_record["lifecycle"] != "completed":
        return {"answer": None, "availability": "unreviewable"}, copy.deepcopy(sources)
    unique = {digest(file_ref(ref)): file_ref(ref) for ref in sources}
    require(len(unique) == 1, "bounded review requires exactly one unique artifact per completed slice")
    document = inputs.read(next(iter(unique.values())))
    if "response_id" in document:
        require(set(document) == {"response_id", "provider", "model", "output", "finish_reason",
                "tool_calls", "usage", "warnings", "provider_metadata"}, "unsupported response metadata fields")
        require(document["finish_reason"] == "complete" and document["tool_calls"] == []
                and isinstance(document["output"], list) and len(document["output"]) == 1,
                "unsupported response output")
        block = document["output"][0]
        require(isinstance(block, dict) and set(block) == {"kind", "text", "data", "mime_type", "reference"}
                and block["kind"] == "text" and block["data"] is None and block["mime_type"] is None
                and block["reference"] is None, "unsupported content or embedded metadata")
        require(isinstance(block["text"], str) and re.fullmatch(r"[0-9]", block["text"]) is not None,
                "only the bounded synthetic integer text is projectable")
        answer = int(block["text"])
    else:
        inputs.validate(PREFIX + "review_artifact", document)
        answer = document["answer"]
    return {"answer": answer, "availability": "reviewable"}, copy.deepcopy(sources)


def _materialize(inputs, evidence, policy, aliases):
    cases = {c["case_id"]: c for c in policy["cases"]}
    slices = [(slot, row) for slot in evidence["slots"] for row in slot["slices"]]
    require(len(aliases) == len(slices) and len(set(aliases)) == len(aliases)
            and all(isinstance(a, str) and re.fullmatch(r"[0-9a-f]{32}", a) for a in aliases),
            "opaque aliases must uniquely cover every planned slice")
    public, private = [], []
    for alias, (slot, row) in zip(aliases, slices):
        projection, sources = _project(inputs, row)
        item = {"anonymous_id": alias, "reference_integer": cases[slot["case_id"]]["reference_integer"], **projection}
        public.append(item)
        private.append({"anonymous_id": alias, "case_id": slot["case_id"], "arm_id": slot["arm_id"],
                        "attempt_id": row["attempt_id"], "slice_index": row["slice_index"],
                        "lifecycle": row["lifecycle"], "source_refs": sources, "projection_sha256": digest(item)})
    # Never publish execution order, arm grouping or the public plan seed.
    package = _record("review_package", instruction=INSTRUCTION, rubric=copy.deepcopy(RUBRIC),
                      slots=sorted(public, key=lambda r: r["anonymous_id"]))
    return package, private


def _mapping(identity, context, package, entries):
    return _record("review_mapping", evidence_ref=file_ref(context.expected_evidence_ref),
        policy_ref=file_ref(context.expected_policy_ref), created_at=context.package_created_at,
        package_sha256=digest(package), entries=entries, validator=identity, boundaries=dict(BOUNDARIES))


def prepare_review_package(inputs, *, context: ReviewContext, admission_verifier, projection_verifier):
    """Return (public package, private mapping), for separate exclusive storage.

    secrets supplies fresh private entropy, never a public run/plan/seed. External
    authorization binds the preregistered policy and exact source/projection map.
    """
    identity = validator_identity(inputs)
    evidence, policy = _evidence(inputs, context, admission_verifier)
    aliases = [secrets.token_hex(16) for slot in evidence["slots"] for _ in slot["slices"]]
    package, entries = _materialize(inputs, evidence, policy, aliases)
    mapping = _mapping(identity, context, package, entries)
    _authorize(projection_verifier, "anonymize", policy_ref=context.expected_policy_ref,
               registered_at=context.policy_registered_at, mapping=mapping)
    _finish(inputs, identity, package, mapping)
    return package, mapping


def validate_review_package(inputs, *, context: ReviewContext, expected_package_ref, expected_mapping_ref,
                            admission_verifier, projection_verifier):
    identity = validator_identity(inputs)
    package = inputs.read(expected_package_ref, PREFIX + "review_package")
    mapping = inputs.read(expected_mapping_ref, PREFIX + "review_mapping")
    evidence, policy = _evidence(inputs, context, admission_verifier)
    expected_package, entries = _materialize(inputs, evidence, policy,
                                            [row["anonymous_id"] for row in mapping["entries"]])
    require(package == expected_package and mapping == _mapping(identity, context, expected_package, entries),
            "anonymous package or private mapping differs from replayed evidence")
    _authorize(projection_verifier, "anonymize", policy_ref=context.expected_policy_ref,
               registered_at=context.policy_registered_at, mapping=mapping)
    _finish(inputs, identity, package, mapping)
    return package, mapping


def freeze_human_reviews(inputs, *, context: ReviewContext, freeze: FreezeContext,
                         admission_verifier, projection_verifier, human_verifier):
    """Validate externally authored reviews; never generate a Human score."""
    identity = validator_identity(inputs)
    package, _ = validate_review_package(inputs, context=context,
        expected_package_ref=freeze.expected_package_ref, expected_mapping_ref=freeze.expected_mapping_ref,
        admission_verifier=admission_verifier, projection_verifier=projection_verifier)
    require(timestamp(context.package_created_at) <= timestamp(freeze.frozen_at), "freeze precedes package")
    received, covered = [], []
    slots = {s["anonymous_id"]: s for s in package["slots"]}
    for submission in freeze.submissions:
        review = inputs.read(submission["review_ref"], PREFIX + "human_review")
        require(review["package_ref"] == file_ref(freeze.expected_package_ref), "Human Review package substitution")
        require(timestamp(context.package_created_at) <= timestamp(submission["received_at"])
                <= timestamp(freeze.frozen_at), "review receipt outside blind freeze interval")
        for row in review["ratings"]:
            alias = row["anonymous_id"]
            require(alias in slots and alias not in covered, "missing, duplicate or unknown review slot")
            require(slots[alias]["availability"] == "reviewable" or row["disposition"] == "unreviewable",
                    "unavailable output cannot receive a score")
            covered.append(alias)
        _authorize(human_verifier, "human-review", review_ref=submission["review_ref"], review=review,
                   received_at=submission["received_at"], frozen_at=freeze.frozen_at)
        received.append({"review_ref": file_ref(submission["review_ref"]), "received_at": submission["received_at"]})
    require(sorted(covered) == sorted(slots), "all anonymous review slots must be frozen")
    document = _record("review_freeze", package_ref=file_ref(freeze.expected_package_ref),
        mapping_ref=file_ref(freeze.expected_mapping_ref), evidence_ref=file_ref(context.expected_evidence_ref),
        submissions=received, frozen_at=freeze.frozen_at, validator=identity, boundaries=dict(BOUNDARIES))
    _authorize(human_verifier, "freeze", freeze=document)
    _finish(inputs, identity, document)
    return document


def validate_review_freeze(inputs, *, expected_freeze_ref, context, freeze, admission_verifier,
                           projection_verifier, human_verifier):
    actual = inputs.read(expected_freeze_ref, PREFIX + "review_freeze")
    expected = freeze_human_reviews(inputs, context=context, freeze=freeze,
        admission_verifier=admission_verifier, projection_verifier=projection_verifier, human_verifier=human_verifier)
    require(actual == expected, "frozen Human Review set substitution")
    return expected


def reveal_human_reviews(inputs, *, expected_freeze_ref, revealed_at: str, context, freeze,
                         admission_verifier, projection_verifier, human_verifier):
    identity = validator_identity(inputs)
    validate_review_freeze(inputs, expected_freeze_ref=expected_freeze_ref, context=context, freeze=freeze,
        admission_verifier=admission_verifier, projection_verifier=projection_verifier, human_verifier=human_verifier)
    require(timestamp(freeze.frozen_at) < timestamp(revealed_at), "reveal must follow the complete frozen review set")
    document = _record("review_reveal", freeze_ref=file_ref(expected_freeze_ref),
        package_ref=file_ref(freeze.expected_package_ref), mapping_ref=file_ref(freeze.expected_mapping_ref),
        evidence_ref=file_ref(context.expected_evidence_ref), revealed_at=revealed_at,
        validator=identity, boundaries=dict(BOUNDARIES))
    _authorize(human_verifier, "reveal", reveal=document)
    _finish(inputs, identity, document)
    return document


def validate_review_reveal(inputs, *, expected_reveal_ref, expected_freeze_ref, revealed_at, context, freeze,
                           admission_verifier, projection_verifier, human_verifier):
    actual = inputs.read(expected_reveal_ref, PREFIX + "review_reveal")
    expected = reveal_human_reviews(inputs, expected_freeze_ref=expected_freeze_ref, revealed_at=revealed_at,
        context=context, freeze=freeze, admission_verifier=admission_verifier,
        projection_verifier=projection_verifier, human_verifier=human_verifier)
    require(actual == expected, "reveal does not bind the externally selected frozen review set and time")
    return expected
