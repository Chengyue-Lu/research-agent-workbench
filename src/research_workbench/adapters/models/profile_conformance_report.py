"""Validate and publish a new, redacted profile conformance report file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from research_workbench.adapters.models.provider_binding import CONFORMANCE_ROOTS, GRAPH_POLICY, read_provider_binding_manifest
from research_workbench.adapters.models.provider_source_closure import read_source_closure
from research_workbench.evaluation.pins import EvaluationInputs
from research_workbench.validation.schemas import SchemaCatalog


_TOKEN_FIELDS = ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens")


def _valid_token_subsets(usage):
    return all(usage[subset] is None or usage[subset] <= usage[parent]
               for subset, parent in (("cached_input_tokens", "input_tokens"),
                                      ("reasoning_tokens", "output_tokens")))


def _verify_accounting_usage(accounting):
    # The durable report contract has no reconciled receipts. Unknown/partial
    # usage remains unresolved; only complete reported receipts enter totals.
    receipts = []
    for call in accounting["calls"]:
        usage = call["reported_usage"]
        if usage is None:
            if call["accounting_status"] in {"known", "reservation-exceeded", "total-limit-exceeded"}:
                return False
        elif not _valid_token_subsets(usage):
            return False
        else:
            receipts.append(usage)
    inputs = sum(usage["input_tokens"] for usage in receipts)
    outputs = sum(usage["output_tokens"] for usage in receipts)
    return (accounting["known_input_tokens"] == inputs
            and accounting["known_output_tokens"] == outputs
            and accounting["known_total_tokens"] == inputs + outputs)


def _verify_call_usage(reservation, call):
    # An unsettled write failure can retain observed facts without a durable
    # receipt. A settled receipt must agree with the current Attempt's report.
    if reservation["settled"] and reservation["response_received"] != call["response_received"]:
        return False
    usage = reservation["reported_usage"]
    if usage is not None:
        return all(call[field] == usage[field] for field in _TOKEN_FIELDS)
    if not reservation["settled"]:
        return True
    issue = reservation["token_usage_failure"]
    if issue == "invalid-token-usage":
        return call["input_tokens"] is None or call["output_tokens"] is None
    if issue == "invalid-token-subset":
        # Invalid auxiliary values may be redacted to None by the producer.
        # Preserve those failed observations without treating them as known.
        return (call["input_tokens"] is None or call["output_tokens"] is None
                or call["cached_input_tokens"] is None or call["reasoning_tokens"] is None
                or not _valid_token_subsets(call))
    return all(call[field] is None for field in _TOKEN_FIELDS)


def _verify_extended_accounting(accounting):
    """Derive cumulative facts from every retained reservation, including STOPs."""
    calls, attempts = accounting["calls"], accounting["attempts"]
    if (len(attempts) > 10 or len(calls) > 30
            or [attempt["ordinal"] for attempt in attempts] != list(range(1, len(attempts) + 1))
            or [call["ordinal"] for call in calls] != list(range(1, len(calls) + 1))
            or any(type(attempt["ordinal"]) is not int for attempt in attempts)
            or any(type(call["ordinal"]) is not int or type(call["attempt_ordinal"]) is not int
                   or not 1 <= call["attempt_ordinal"] <= len(attempts) for call in calls)
            or [call["attempt_ordinal"] for call in calls] != sorted(call["attempt_ordinal"] for call in calls)
            or not _verify_accounting_usage(accounting)):
        return False
    for attempt in attempts:
        selected = [call for call in calls if call["attempt_ordinal"] == attempt["ordinal"]]
        if (len(selected) > 3 or type(attempt["provider_invocations"]) is not int
                or attempt["provider_invocations"] != len(selected)):
            return False
    for call in calls:
        if (call["http_entry_observed"] != call["send_attempted"]
                or call["may_have_sent"] != call["send_intent_durable"]
                or call["send_attempted"] and not call["send_intent_durable"]
                or call["response_received"] and not call["send_attempted"]
                or call["successful_reported"] and not call["response_received"]):
            return False
    counts = {"provider_invocations": len(calls),
        "http_send_attempts": sum(call["send_attempted"] for call in calls),
        "responses_received": sum(call["response_received"] for call in calls),
        "successful_responses": sum(call["successful_reported"] and call["response_received"] for call in calls),
        "failed_invocations": sum(call["outcome"] in {"failed", "failed-before-send"} for call in calls),
        "durable_send_intents": sum(call["send_intent_durable"] for call in calls),
        "http_entry_observations": sum(call["http_entry_observed"] for call in calls)}
    if any(type(accounting[key]) is not int or accounting[key] != value for key, value in counts.items()):
        return False
    held = 0
    for call in calls:
        if call["accounting_status"] in {"reserved", "unresolved", "reservation-exceeded", "total-limit-exceeded"}:
            usage = call["reported_usage"]
            known = 0 if usage is None else usage["input_tokens"] + usage["output_tokens"]
            held += max(0, call["input_upper_tokens"] + call["output_upper_tokens"] - known)
    return (type(accounting["unresolved_reserved_tokens"]) is int
            and accounting["unresolved_reserved_tokens"] == held
            and type(accounting["remaining_token_capacity"]) is int
            and accounting["remaining_token_capacity"] == max(0,
                accounting["limits"]["total_token_limit"] - accounting["known_total_tokens"] - held))


def _verify_extension(report, inputs):
    """Replay the original prefix under3 before deriving the single grant10."""
    import research_workbench.adapters.models.conformance_budget_grant as policy
    from research_workbench.adapters.models.conformance_journal import ConformanceUsageJournal, _Replay, _parse
    from research_workbench.adapters.models.conformance_ledger import ConformanceUsageLedger
    extension = report["budget_extension"]
    receipt = extension["attempt_limit_grant"]
    grant = receipt["payload"]
    prefix = inputs.read(grant["prefix_ref"])
    decision = inputs.read(grant["decision_ref"])
    if (inputs.read_bytes(grant["prefix_ref"]) != (policy.canonical(prefix) + "\n").encode("ascii")
            or inputs.read_bytes(grant["decision_ref"]) != (policy.canonical(decision) + "\n").encode("ascii")):
        return False
    inputs.read_bytes(decision["user_input_ref"])
    chain = policy.prefix_chain(prefix)
    state = _Replay(ConformanceUsageLedger(**policy.BASELINE), {}, set(), set(), set(), {})
    for sequence, kind, payload in prefix["events"]:
        if kind == "attempt-limit-grant" or sequence != state.event_count + 1:
            return False
        ConformanceUsageJournal._apply(state, kind, _parse(payload))
        state.event_count += 1
    retained = state.snapshot()
    policy.validate_grant(grant, namespace=prefix["budget_namespace"], identity=prefix["journal_identity"],
        snapshot=retained, event_count=state.event_count, chain=chain, decision=decision)
    if (receipt["sha256"] != policy.digest(grant) or extension["baseline_limits"] != policy.BASELINE
            or extension["effective_limits"] != {**policy.BASELINE, "max_attempts": 10}):
        return False
    accounting = report["accounting"]
    if accounting is not None:
        if (any(accounting[key] != extension[key] for key in extension)
                or accounting["limits"] != extension["effective_limits"]
                or accounting["budget_namespace"] != prefix["budget_namespace"]
                or accounting["events_committed"] < state.event_count + 1
                or accounting["attempts"][:3] != retained["attempts"]
                or accounting["calls"][:len(retained["calls"])] != retained["calls"]):
            return False
        if not _verify_extended_accounting(accounting):
            return False
    inputs.recheck()
    return True


def _verify_binding(report, *, root, schema_root):
    """Derive archived pins without loading archived code or resolving a Key."""
    inputs = EvaluationInputs(root, schema_root)
    if report["report_version"] == "1.2.0" and not _verify_extension(report, inputs):
        return False
    binding = report["binding"]
    manifest = read_provider_binding_manifest(inputs, binding["manifest_ref"]).to_mapping()
    if (manifest["version"] != "1.1.0" or manifest["binding_policy_version"] != GRAPH_POLICY
            or not set(CONFORMANCE_ROOTS) <= set(manifest["source_roots"])
            or manifest["implementation_closure_ref"] != binding["implementation_closure_ref"]
            or manifest["resolved_config_ref"] != report["config_ref"]
            or manifest["transport_identity"]["class"] !=
            "research_workbench.adapters.models.conformance_transport.GuardedConformanceTransport"):
        return False
    config = inputs.read(manifest["resolved_config_ref"])
    profile = inputs.read(manifest["profile_ref"], "provider_api_profile")
    if (config["profile_ref"] != report["profile_ref"]
            or profile["identity"]["provider"] != report["provider"]
            or profile["profile_id"] != report["profile_id"]
            or profile["profile_id"] != "deepseek-responses-nonthinking-v1"
            or config["model"] != report["requested_model"]
            or profile["identity"]["provider"] != "deepseek"
            or profile["protocol"]["family"] != "responses"
            or profile["model"]["requested_id"] != "deepseek-flash"
            or profile["generation"]["mode"] != "nonthinking"
            or any(model not in profile["model"]["allowed_observed_ids"] for model in report["observed_models"])
            or binding["body_policy"]["max_output_tokens"] != report["limits"]["max_output_tokens"]):
        return False
    accounting = report["accounting"]
    if accounting is not None and not _verify_accounting_usage(accounting):
        return False
    attempt_ordinal = binding["attempt_ordinal"]
    if attempt_ordinal is None:
        if report["calls"]:
            return False
    elif accounting is not None:
        if len([attempt for attempt in accounting["attempts"] if attempt["ordinal"] == attempt_ordinal]) != 1:
            return False
        reservations = [call for call in accounting["calls"] if call["attempt_ordinal"] == attempt_ordinal]
        if len(reservations) != len(report["calls"]):
            return False
        for ordinal, (reservation, call) in enumerate(zip(reservations, report["calls"]), 1):
            if (call["ordinal"] != ordinal
                    or reservation["input_upper_tokens"] != binding["input_upper_tokens"][ordinal - 1]
                    or reservation["output_upper_tokens"] != report["limits"]["max_output_tokens"]
                    or not _verify_call_usage(reservation, call)):
                return False
    graph = read_source_closure(inputs, binding["implementation_closure_ref"])
    for reference in report["source_refs"]:
        module = graph["modules"].get(reference["module"])
        if module is None or module["source_ref"]["sha256"] != reference["source_sha256"]:
            return False
    # The surrounding report cannot acquire human/Windows/API authority from a
    # source graph. Preserve these qualifications on every bound receipt.
    if not {"caller-attested-gates", "input-bound-proof-unverified", "windows-run-unaccepted",
            "remote-strict-unclaimed"} <= set(report["warnings"]):
        return False
    inputs.recheck()
    return True


def verify_profile_conformance_report(
    report: Mapping[str, object], *, schema_root: str | Path | None = None,
    root: str | Path | None = None,
) -> dict:
    """Cold-check a closed report; the result grants no execution acceptance."""
    serialized = None
    try:
        serialized = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    except (TypeError, ValueError, OverflowError, RecursionError):
        pass
    if serialized is None:
        raise ValueError("profile conformance report requires finite JSON primitives")
    detached = json.loads(serialized)
    if SchemaCatalog(schema_root).validate("profile_conformance_report", detached):
        raise ValueError("profile conformance report violates its closed contract")
    if detached["report_version"] in {"1.1.0", "1.2.0"}:
        if root is None:
            raise ValueError("bound profile conformance report requires its archive root")
        valid = False
        try:
            valid = _verify_binding(detached, root=root, schema_root=schema_root)
        except Exception:
            pass
        if not valid:
            raise ValueError("profile conformance report binding validation failed")
    return detached


def write_profile_conformance_report(
    report: Mapping[str, object], destination: str | Path, *, schema_root: str | Path | None = None,
    root: str | Path | None = None,
) -> None:
    """No overwrite or credential access; structural validity is not acceptance."""
    detached = verify_profile_conformance_report(report, schema_root=schema_root, root=root)
    serialized = json.dumps(detached, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    # 'x' refuses every existing target, including symlinks and directories.
    # An interrupted first write remains visible; retry must choose a fresh path.
    with Path(destination).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized)
