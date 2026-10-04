"""Finite evidence-answer bodies for the M5 live Pilot implementation candidate.

This is a structural codec, not an execution, admission, scoring or anonymization
authority. Callers retain original artifacts and all usage/failure records, and
independently validate live receipts and frozen inputs before using a projection.
Only ``public_value()`` is a distributable finite body; private diagnostic/hash
fields and the original ModelResponse must remain in the evaluation archive.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass

from research_workbench.adapters.models.port import ContentBlock, FinishReason, ModelResponse

FORMAT = "bounded-evidence-relations-v1"
MAX_BODY_BYTES = 16_384
MAX_JSON_DEPTH = 5
VERDICTS = frozenset({"supported", "contradicted", "insufficient"})
RELATIONS = frozenset({"supports", "counters", "limits", "unknown"})
SCOPES = frozenset({"matched", "different", "unknown", "not-applicable"})
LIFECYCLES = frozenset({"completed", "post-call-failed", "preflight-blocked", "not-started"})


class BoundedEvidenceError(ValueError):
    """Stable diagnostic codes contain no response text, identifiers or metadata."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise BoundedEvidenceError(code)


@dataclass(frozen=True, slots=True)
class EvidenceOutputSpec:
    """Externally frozen closed sets; this value grants no execution permission."""

    claim_ids: tuple[str, ...]
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for ids, pattern, limit in (
            (self.claim_ids, r"C0[1-4]", 4),
            (self.source_ids, r"S0[1-8]", 8),
        ):
            _require(type(ids) is tuple and 0 < len(ids) <= limit, "invalid-frozen-ids")
            _require(all(type(item) is str and re.fullmatch(pattern, item) for item in ids),
                     "invalid-frozen-ids")
            _require(len(set(ids)) == len(ids), "invalid-frozen-ids")


@dataclass(frozen=True, slots=True)
class SourceRelation:
    source_id: str
    relation: str
    scope_status: str

    def to_dict(self) -> dict:
        return {"source_id": self.source_id, "relation": self.relation,
                "scope_status": self.scope_status}


@dataclass(frozen=True, slots=True)
class ClaimAnswer:
    claim_id: str
    verdict: str
    relations: tuple[SourceRelation, ...]

    def to_dict(self) -> dict:
        return {"claim_id": self.claim_id, "verdict": self.verdict,
                "relations": [row.to_dict() for row in self.relations]}


@dataclass(frozen=True, slots=True)
class EvidenceAnswer:
    claims: tuple[ClaimAnswer, ...]

    def to_dict(self) -> dict:
        return {"format": FORMAT, "claims": [row.to_dict() for row in self.claims]}


def _body_bytes(body: str | bytes) -> bytes:
    _require(type(body) in (str, bytes), "unsupported-body")
    _require(len(body) <= MAX_BODY_BYTES, "oversized-body")
    try:
        raw = body.encode("utf-8") if type(body) is str else body
        raw.decode("utf-8")
    except UnicodeError as exc:
        raise BoundedEvidenceError("invalid-utf8") from exc
    _require(len(raw) <= MAX_BODY_BYTES, "oversized-body")
    return raw


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate-key")
        result[key] = value
    return result


def _constant(_value: str) -> None:
    raise BoundedEvidenceError("non-finite-json")


def _number(_value: str) -> None:
    # The closed answer vocabulary contains no numeric fields. Reject before
    # Python integer limits or floating-point overflow can escape the codec.
    raise BoundedEvidenceError("unexpected-number")


def _keys(value: object, expected: set[str]) -> None:
    _require(type(value) is dict and set(value) == expected, "unexpected-fields")


def _bounded_depth(raw: bytes) -> None:
    # Cap the grammar's five containers before decoding, independent of the
    # process recursion limit. Brackets in strings/escaped quotes are data.
    depth, in_string, escaped = 0, False, False
    for char in raw:
        if in_string:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                in_string = False
        elif char == 34:
            in_string = True
        elif char in (91, 123):
            depth += 1
            _require(depth <= MAX_JSON_DEPTH, "too-deep-json")
        elif char in (93, 125):
            depth -= 1


def parse_evidence_answer(body: str | bytes, *, spec: EvidenceOutputSpec) -> EvidenceAnswer:
    """Parse one complete body without extraction, repair, retries or judging it.

    Relations are sorted for a deterministic finite projection. Empty relations
    and competing support/counterevidence remain representable for Human review;
    structural validity cannot establish provenance adequacy or semantic truth.
    """
    _require(type(spec) is EvidenceOutputSpec, "invalid-frozen-spec")
    raw = _body_bytes(body)
    _bounded_depth(raw)
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                              parse_constant=_constant, parse_int=_number, parse_float=_number)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise BoundedEvidenceError("invalid-json") from exc
    _keys(document, {"format", "claims"})
    _require(document["format"] == FORMAT, "wrong-format")
    rows = document["claims"]
    _require(type(rows) is list and len(rows) == len(spec.claim_ids), "invalid-claim-set")
    seen_claims: set[str] = set()
    claims = []
    for row in rows:
        _keys(row, {"claim_id", "verdict", "relations"})
        claim_id = row["claim_id"]
        _require(type(claim_id) is str and claim_id in spec.claim_ids and claim_id not in seen_claims,
                 "invalid-claim-set")
        seen_claims.add(claim_id)
        _require(type(row["verdict"]) is str and row["verdict"] in VERDICTS, "invalid-verdict")
        values = row["relations"]
        _require(type(values) is list and len(values) <= 2 * len(spec.source_ids), "too-many-relations")
        counts: Counter[str] = Counter()
        seen_relations: set[tuple[str, str]] = set()
        relations = []
        for value in values:
            _keys(value, {"source_id", "relation", "scope_status"})
            source_id, relation, scope = value["source_id"], value["relation"], value["scope_status"]
            _require(type(source_id) is str and source_id in spec.source_ids, "invalid-source-id")
            _require(type(relation) is str and relation in RELATIONS, "invalid-relation")
            _require(type(scope) is str and scope in SCOPES, "invalid-scope-status")
            counts[source_id] += 1
            _require(counts[source_id] <= 2, "too-many-source-relations")
            _require((source_id, relation) not in seen_relations, "duplicate-relation")
            seen_relations.add((source_id, relation))
            relations.append(SourceRelation(source_id, relation, scope))
        claims.append(ClaimAnswer(claim_id, row["verdict"],
            tuple(sorted(relations, key=lambda item: (item.source_id, item.relation, item.scope_status)))))
    _require(seen_claims == set(spec.claim_ids), "invalid-claim-set")
    return EvidenceAnswer(tuple(sorted(claims, key=lambda item: item.claim_id)))


@dataclass(frozen=True, slots=True)
class EvidenceProjection:
    """Private outcome; a reviewable body is not a valid live receipt or score."""

    answer: EvidenceAnswer | None
    reason: str | None
    body_sha256: str | None

    def public_value(self) -> dict:
        return {"availability": "reviewable" if self.answer is not None else "unreviewable",
                "answer": None if self.answer is None else self.answer.to_dict()}


def project_evidence_response(response: ModelResponse, *, lifecycle: str,
                              spec: EvidenceOutputSpec) -> EvidenceProjection:
    """Project the single final text only; never touch usage or Provider metadata.

    Lifecycle must come from independently validated execution evidence upstream.
    Even a malformed/nonfinal response remains archived there with its original
    usage. No output is scored, combined, corrected or selected from alternatives.
    """
    _require(type(spec) is EvidenceOutputSpec, "invalid-frozen-spec")
    _require(type(lifecycle) is str and lifecycle in LIFECYCLES, "invalid-lifecycle")
    _require(type(response) is ModelResponse, "unsupported-response")
    if lifecycle != "completed":
        return EvidenceProjection(None, "execution-not-completed", None)
    if type(response.finish_reason) is not FinishReason or response.finish_reason != FinishReason.COMPLETE:
        return EvidenceProjection(None, "response-not-complete", None)
    if response.tool_calls != ():
        return EvidenceProjection(None, "response-tool-calls", None)
    if type(response.output) is not tuple or len(response.output) != 1:
        return EvidenceProjection(None, "unsupported-content", None)
    block = response.output[0]
    if (type(block) is not ContentBlock or block.kind != "text" or type(block.text) is not str
            or block.data is not None or block.mime_type is not None or block.reference is not None):
        return EvidenceProjection(None, "unsupported-content", None)
    body_hash = None
    try:
        raw = _body_bytes(block.text)
        body_hash = hashlib.sha256(raw).hexdigest()
        answer = parse_evidence_answer(raw, spec=spec)
    except BoundedEvidenceError as exc:
        return EvidenceProjection(None, str(exc), body_hash)
    return EvidenceProjection(answer, None, body_hash)
