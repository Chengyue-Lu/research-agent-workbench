"""Closed, caller-selected attempt grants; no human authentication or I/O."""
from __future__ import annotations

import hashlib
import json
import re
from uuid import UUID

BASELINE = {"total_token_limit": 10000000, "max_attempts": 3,
            "max_invocations_per_attempt": 3, "max_output_tokens_per_invocation": 256}
GRANT_FIELDS = frozenset({"record_kind", "grant_version", "budget_namespace", "journal_identity",
    "previous_events", "previous_chain_sha256", "baseline_limits", "new_max_attempts",
    "decision_ref", "prefix_ref", "retained_state_sha256"})
PREFIX_FIELDS = frozenset({"record_kind", "version", "budget_namespace", "journal_identity", "anchor_header", "events"})
DECISION_FIELDS = frozenset({"record_kind", "version", "budget_namespace", "journal_identity",
                            "baseline_limits", "new_max_attempts", "user_input_ref"})


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("ascii")).hexdigest()


def _fail():
    raise ValueError("conformance attempt grant violates its closed contract")


def reference(value):
    if (type(value) is not dict or set(value) != {"path", "sha256"}
            or type(value["path"]) is not str or not value["path"] or "\\" in value["path"]
            or ":" in value["path"] or value["path"].startswith("/")
            or any(part in {"", ".", ".."} for part in value["path"].split("/"))
            or type(value["sha256"]) is not str or re.fullmatch("[a-f0-9]{64}", value["sha256"]) is None):
        _fail()
    return value


def retained_state(snapshot):
    keys = ("limits", "attempts", "calls", "known_input_tokens", "known_output_tokens", "known_total_tokens",
            "unresolved_reserved_tokens", "responses_received", "provider_invocations")
    return {key: snapshot[key] for key in keys}


def prefix_chain(prefix):
    if type(prefix) is not dict or set(prefix) != PREFIX_FIELDS or prefix["record_kind"] != "conformance_budget_prefix" or prefix["version"] != "1.0.0":
        _fail()
    header = prefix["anchor_header"]
    if (type(header) is not dict or set(header) != {"record_kind", "anchor_version", "database_schema_version", "database_path", "anchor_path", "budget_namespace", "limits", "journal_identity"}
            or header["record_kind"] != "conformance_budget_anchor" or header["anchor_version"] != "1.0.0"
            or type(header["database_schema_version"]) is not int or header["database_schema_version"] != 2
            or header["limits"] != BASELINE or any(type(value) is not int for value in header["limits"].values())
            or header["budget_namespace"] != prefix["budget_namespace"] or header["journal_identity"] != prefix["journal_identity"]):
        _fail()
    events = prefix["events"]
    if type(events) is not list or len(events) > 128:
        _fail()
    chain = digest(header)
    for ordinal, event in enumerate(events, 1):
        if (type(event) is not list or len(event) != 3 or type(event[0]) is not int or event[0] != ordinal
                or type(event[1]) is not str or type(event[2]) is not str):
            _fail()
        chain = digest({"previous": chain, "seq": ordinal, "kind": event[1], "payload": event[2]})
    return chain


def validate_grant(grant, *, namespace, identity, snapshot, event_count, chain, decision):
    if (type(grant) is not dict or set(grant) != GRANT_FIELDS
            or grant["record_kind"] != "conformance_attempt_limit_grant" or grant["grant_version"] != "1.0.0"
            or grant["budget_namespace"] != namespace or grant["journal_identity"] != identity
            or type(grant["previous_events"]) is not int or grant["previous_events"] != event_count
            or grant["previous_chain_sha256"] != chain or grant["baseline_limits"] != BASELINE
            or any(type(value) is not int for value in grant["baseline_limits"].values())
            or type(grant["new_max_attempts"]) is not int or grant["new_max_attempts"] != 10
            or grant["retained_state_sha256"] != digest(retained_state(snapshot))):
        _fail()
    for value in (namespace, identity):
        if type(value) is not str or str(UUID(value)) != value:
            _fail()
    reference(grant["decision_ref"])
    reference(grant["prefix_ref"])
    if (type(decision) is not dict or set(decision) != DECISION_FIELDS
            or decision["record_kind"] != "conformance_attempt_limit_decision" or decision["version"] != "1.0.0"
            or decision["budget_namespace"] != namespace or decision["journal_identity"] != identity
            or decision["baseline_limits"] != BASELINE or any(type(value) is not int for value in decision["baseline_limits"].values())
            or type(decision["new_max_attempts"]) is not int or decision["new_max_attempts"] != 10):
        _fail()
    reference(decision["user_input_ref"])
    if (snapshot["limits"] != BASELINE or snapshot["blocked"] or snapshot["unresolved_reserved_tokens"] != 0
            or len(snapshot["attempts"]) != 3 or any(attempt["status"] != "failed" for attempt in snapshot["attempts"])
            or any(not call["settled"] for call in snapshot["calls"])
            or event_count + 1 + 7 * 14 > 128):
        _fail()
