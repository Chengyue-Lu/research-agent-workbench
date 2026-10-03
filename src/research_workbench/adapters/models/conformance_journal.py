"""Durable, caller-attested conformance token accounting, without Provider I/O.

One SQLite file binds one explicit nonsecret UUID budget namespace and limits.
Default journals are caller-attested. An explicit retained anchor adds local
event-history checks under a trusted local user; coherent DB+anchor rollback,
another selected anchor, input proof and HTTP truth remain caller boundaries.
"""

from __future__ import annotations

import json
import hashlib
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, NoReturn
from uuid import UUID

from research_workbench.adapters.models.conformance_budget_anchor import (
    ConformanceBudgetAnchor, ConformanceBudgetAnchorError,
)
from research_workbench.adapters.models.conformance_ledger import (
    ConformanceLedgerError, ConformanceUsageLedger, ConformanceUsageLimits,
)
from research_workbench.adapters.models.port import Usage
import research_workbench.adapters.models.conformance_budget_grant as grant_policy

_APPLICATION_ID = 0x52574243
_MAX_EVENTS = 128
_META_SQL = "CREATE TABLE meta (id INTEGER PRIMARY KEY CHECK(id=1), namespace TEXT NOT NULL, limits TEXT NOT NULL)"
_EVENT_SQL = "CREATE TABLE events (seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL)"
# Explicit opt-in SQLite schema v2; legacy v1 has only meta and events.
_IDENTITY_SQL = "CREATE TABLE budget_identity (id INTEGER PRIMARY KEY CHECK(id=1), identity TEXT NOT NULL)"


class ConformanceJournalError(ValueError):
    """A fixed code, never raw SQL/path/Provider values or exception chains."""

    def __init__(self, code: str):
        self.code = code
        super().__init__("conformance journal: " + code)


def _fail(code: str) -> NoReturn:
    error = ConformanceJournalError(code)
    try:
        raise error from None
    finally:
        error.__cause__ = None
        error.__context__ = None
        error.__suppress_context__ = True


def _anchor_call(operation):
    result = None
    issue = None
    try:
        result = operation()
    except ConformanceBudgetAnchorError as error:
        issue = error.code if type(error.code) is str and error.code in {
            "budget-anchor-conflict", "budget-anchor-corrupt", "budget-anchor-drift",
            "budget-anchor-unavailable",
        } else "budget-anchor-unavailable"
    except (OSError, ValueError, TypeError, RuntimeError):
        issue = "budget-anchor-unavailable"
    if issue is not None:
        _fail(issue)
    return result


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _parse(text: object) -> dict[str, object]:
    failed = False
    value = None
    try:
        if type(text) is str and len(text) <= 2048:
            def constant(_: str) -> None:
                raise ValueError("nonfinite")

            def unique(pairs):
                result = {}
                for key, item in pairs:
                    if key in result:
                        raise ValueError("duplicate")
                    result[key] = item
                return result

            value = json.loads(text, parse_constant=constant, object_pairs_hook=unique)
        failed = type(value) is not dict
    except (ValueError, TypeError, RecursionError):
        failed = True
    if failed:
        _fail("invalid-journal-state")
    return value


def _limit_mapping(limits: ConformanceUsageLimits) -> dict[str, int]:
    return {
        "total_token_limit": limits.total_token_limit,
        "max_attempts": limits.max_attempts,
        "max_invocations_per_attempt": limits.max_invocations_per_attempt,
        "max_output_tokens_per_invocation": limits.max_output_tokens_per_invocation,
    }


def _limits(total: int, attempts: int, calls: int, output: int) -> ConformanceUsageLimits:
    result = None
    try:
        result = ConformanceUsageLimits(total, attempts, calls, output)
    except ConformanceLedgerError:
        pass
    if result is None or result.total_token_limit > 10_000_000:
        _fail("invalid-limits")
    return result


def _namespace(value: object) -> str:
    accepted = False
    try:
        accepted = type(value) is str and str(UUID(value)) == value
    except (ValueError, AttributeError):
        pass
    if not accepted:
        _fail("invalid-budget-namespace")
    return value


def _tokens(value: Usage | None) -> tuple[dict[str, object] | None, str | None]:
    # Read token fields once; monetary fields are not read or retained. Their
    # absence/malformed values cannot block legitimate token accounting.
    if type(value) is not Usage:
        return None, "usage-unavailable"
    inputs, outputs = value.input_tokens, value.output_tokens
    cached, reasoning = value.cached_input_tokens, value.reasoning_tokens
    if any(type(item) is not int or not 0 <= item <= 2**63 - 1 for item in (inputs, outputs)):
        return None, "invalid-token-usage"
    if any(item is not None and (type(item) is not int or not 0 <= item <= total)
           for item, total in ((cached, inputs), (reasoning, outputs))):
        return None, "invalid-token-subset"
    return {"input_tokens": inputs, "output_tokens": outputs,
            "cached_input_tokens": cached, "reasoning_tokens": reasoning}, None


@dataclass(frozen=True, slots=True)
class ConformanceJournalReservation:
    reservation_ordinal: int
    attempt_ordinal: int
    input_upper_tokens: int
    output_upper_tokens: int


@dataclass
class _Replay:
    ledger: ConformanceUsageLedger
    handles: dict[int, object]
    intents: set[int]
    uncertain: set[int]
    failed_attempts: set[int]
    usage_issues: dict[int, str]
    event_count: int = 0
    grant: dict[str, object] | None = None

    def snapshot(self) -> dict[str, Any]:
        result = self.ledger.snapshot()
        for attempt in result["attempts"]:
            if attempt["ordinal"] in self.failed_attempts:
                attempt["status"] = "failed"
        for call in result["calls"]:
            ordinal = call["ordinal"]
            call["send_intent_durable"] = ordinal in self.intents
            call["http_entry_observed"] = call["send_attempted"]
            call["may_have_sent"] = ordinal in self.intents
            call["token_usage_failure"] = self.usage_issues.get(ordinal)
            if ordinal in self.uncertain:
                call["settled"] = True
                call["outcome"] = "failed"
                call["accounting_status"] = "unresolved"
                call["may_have_sent"] = True
        if self.uncertain:
            result["blocked"] = True
            result["blocked_reason"] = "uncertain-http-outcome"
            result["failed_invocations"] += len(self.uncertain)
        pending = any(not call["settled"] for call in result["calls"])
        if pending and not result["blocked"]:
            result["blocked"] = True
            result["blocked_reason"] = "pending-reservation"
        result["durable_send_intents"] = len(self.intents)
        result["http_entry_observations"] = result["http_send_attempts"]
        result["cost"] = {
            "status": "unknown", "requirement": "not-required",
            "provider_reported_cost": None, "currency": None,
            "estimated_cost_computed": False, "billing_settlement_verified": False,
        }
        return result


class ConformanceUsageJournal:
    """Serial, durable budget state; HTTP-entry observations are caller assertions.

    Reopen retains unfinished reservations and never returns their process-local
    handles. Such calls block all new sends/Attempts; this slice has no automatic
    recovery, reconciliation or retry. Close never releases a reservation.
    """

    def __init__(self, connection: sqlite3.Connection, namespace: str, limits: ConformanceUsageLimits, *, anchor=None):
        if type(connection) is not sqlite3.Connection or type(limits) is not ConformanceUsageLimits:
            _fail("invalid-journal-construction")
        if anchor is not None and type(anchor) is not ConformanceBudgetAnchor:
            _fail("invalid-journal-construction")
        self._connection = connection
        self._namespace = _namespace(namespace)
        self._limits = _limits(limits.total_token_limit, limits.max_attempts,
                               limits.max_invocations_per_attempt, limits.max_output_tokens_per_invocation)
        self._lock = RLock()
        self._owned: dict[int, ConformanceJournalReservation] = {}
        self._closed = False
        self._anchor = anchor
        self._grant_selection = None
        self._extension_metadata = None

    @classmethod
    def create(
        cls, path: str | Path, *, namespace: str, total_token_limit: int,
        max_attempts: int = 3, max_invocations_per_attempt: int = 3,
        max_output_tokens_per_invocation: int = 256,
        anchor_path: str | Path | None = None,
    ) -> ConformanceUsageJournal:
        """Explicit first creation, refusing every existing target file."""
        namespace = _namespace(namespace)
        limits = _limits(total_token_limit, max_attempts, max_invocations_per_attempt, max_output_tokens_per_invocation)
        anchor = None
        if anchor_path is not None:
            anchor = _anchor_call(lambda: ConformanceBudgetAnchor.create(anchor_path,
                database_path=path, namespace=namespace, limits=_limit_mapping(limits)))
        failed = False
        try:
            target = Path(path).absolute()
            descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        except (OSError, TypeError, ValueError):
            failed = True
        if failed:
            _fail("journal-create-refused")
        connection = cls._connect(target)
        journal = cls(connection, namespace, limits, anchor=anchor)
        issue = None
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(_META_SQL)
            connection.execute(_EVENT_SQL)
            connection.execute("INSERT INTO meta VALUES (1, ?, ?)", (namespace, _json(_limit_mapping(limits))))
            connection.execute(f"PRAGMA application_id={_APPLICATION_ID}")
            if anchor is None:
                connection.execute("PRAGMA user_version=1")
            else:
                connection.execute(_IDENTITY_SQL)
                connection.execute("INSERT INTO budget_identity VALUES (1, ?)", (anchor.identity,))
                connection.execute("PRAGMA user_version=2")
                _anchor_call(lambda: anchor.verify([]))
            connection.commit()
        except ConformanceJournalError:
            journal.close()
            raise
        except sqlite3.Error:
            issue = "journal-storage-unavailable"
        if issue is not None:
            journal.close()
            _fail(issue)
        return journal

    @classmethod
    def open(
        cls, path: str | Path, *, namespace: str, total_token_limit: int,
        max_attempts: int = 3, max_invocations_per_attempt: int = 3,
        max_output_tokens_per_invocation: int = 256,
        anchor_path: str | Path | None = None,
        grant_root: str | Path | None = None, expected_grant_sha256: str | None = None,
    ) -> ConformanceUsageJournal:
        """Open an established file; SQLite mode=rw forbids implicit recreation."""
        namespace = _namespace(namespace)
        limits = _limits(total_token_limit, max_attempts, max_invocations_per_attempt, max_output_tokens_per_invocation)
        anchor = None
        if anchor_path is not None:
            anchor = _anchor_call(lambda: ConformanceBudgetAnchor.open(anchor_path,
                database_path=path, namespace=namespace, limits=_limit_mapping(limits)))
        connection = cls._connect(path)
        journal = cls(connection, namespace, limits, anchor=anchor)
        if (grant_root is None) != (expected_grant_sha256 is None):
            journal.close()
            _fail("attempt-limit-grant-refused")
        if grant_root is not None:
            journal._grant_selection = (Path(grant_root).resolve(), expected_grant_sha256)
        try:
            snapshot = journal.snapshot()
            if snapshot["journal_version"] == "1.1.0":
                journal._extension_metadata = {key: snapshot[key] for key in
                    ("baseline_limits", "effective_limits", "attempt_limit_grant")}
        except ConformanceJournalError:
            journal.close()
            raise
        return journal

    @staticmethod
    def _connect(path: str | Path) -> sqlite3.Connection:
        connection = None
        failed = False
        try:
            target = Path(path).absolute()
            connection = sqlite3.connect(target.as_uri() + "?mode=rw", uri=True, timeout=1.0,
                                         isolation_level=None, check_same_thread=False)
            connection.execute("PRAGMA trusted_schema=OFF")
            mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            connection.execute("PRAGMA synchronous=FULL")
            if mode != "wal" or connection.execute("PRAGMA synchronous").fetchone()[0] != 2:
                failed = True
        except (sqlite3.Error, OSError, ValueError, TypeError):
            failed = True
        if failed:
            if connection is not None:
                connection.close()
            _fail("journal-storage-unavailable")
        return connection

    @property
    def limits(self) -> ConformanceUsageLimits:
        return ConformanceUsageLimits(**_limit_mapping(self._limits))

    def _transaction(self, action):
        issue = None
        result = None
        with self._lock:
            if self._closed:
                _fail("journal-closed")
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                state = self._read()
                previous_count = state.event_count
                result = action(state)
                if self._anchor is not None:
                    # Validate fresh transaction contents before making its
                    # high-water checkpoint durable. Never rewind a checkpoint
                    # if the following commit fails or has unknown outcome.
                    self._read(check_anchor=False)
                    events = self._events()
                    _anchor_call(lambda: self._anchor.checkpoint(events, previous_count=previous_count))
                    # Re-read after checkpoint I/O; a callback or local edit
                    # during that I/O cannot silently change pending DB bytes.
                    self._read()
                self._connection.commit()
            except ConformanceJournalError:
                self._rollback()
                raise
            except sqlite3.Error:
                self._rollback()
                issue = "journal-storage-unavailable"
        if issue is not None:
            _fail(issue)
        return result

    def _rollback(self) -> None:
        try:
            self._connection.rollback()
        except sqlite3.Error:
            pass

    def _events(self):
        return self._connection.execute("SELECT seq, kind, payload FROM events ORDER BY seq LIMIT ?", (_MAX_EVENTS + 1,)).fetchall()

    def _read(self, *, check_anchor=True) -> _Replay:
        if self._connection.execute("PRAGMA journal_mode").fetchone()[0] != "wal" or self._connection.execute("PRAGMA synchronous").fetchone()[0] != 2:
            _fail("journal-durability-settings-drift")
        schema = self._connection.execute("SELECT name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
        expected_schema = {"meta": _META_SQL, "events": _EVENT_SQL}
        if self._anchor is not None:
            expected_schema["budget_identity"] = _IDENTITY_SQL
        if dict(schema) != expected_schema:
            _fail("invalid-journal-schema")
        if self._connection.execute("PRAGMA application_id").fetchone()[0] != _APPLICATION_ID:
            _fail("invalid-journal-schema")
        if self._connection.execute("PRAGMA user_version").fetchone()[0] != (1 if self._anchor is None else 2):
            _fail("invalid-journal-schema")
        if self._anchor is not None:
            identity = self._connection.execute("SELECT id, identity FROM budget_identity").fetchall()
            if identity != [(1, self._anchor.identity)]:
                _fail("budget-anchor-conflict")
        metadata = self._connection.execute("SELECT id, namespace, limits FROM meta").fetchall()
        if len(metadata) != 1 or metadata[0][0] != 1:
            _fail("invalid-journal-state")
        if metadata[0][1] != self._namespace or metadata[0][2] != _json(_limit_mapping(self._limits)):
            _fail("budget-binding-conflict")
        events = self._events()
        if len(events) > _MAX_EVENTS:
            _fail("invalid-journal-state")
        state = _Replay(ConformanceUsageLedger(**_limit_mapping(self._limits)), {}, set(), set(), set(), {})
        for seq, kind, payload in events:
            if type(seq) is not int or seq != state.event_count + 1 or type(kind) is not str:
                _fail("invalid-journal-state")
            parsed = _parse(payload)
            if kind == "attempt-limit-grant":
                if self._anchor is None or self._grant_selection is None or state.grant is not None:
                    _fail("attempt-limit-grant-refused")
                grant_root, selected_hash = self._grant_selection
                if grant_policy.digest(parsed) != selected_hash:
                    _fail("attempt-limit-grant-refused")
                self._validate_grant(state, parsed, root=grant_root, events=events[:state.event_count])
            self._apply(state, kind, parsed)
            state.event_count += 1
        if self._grant_selection is not None and state.grant is None:
            _fail("attempt-limit-grant-refused")
        if self._anchor is not None and check_anchor:
            _anchor_call(lambda: self._anchor.verify(events))
        return state

    @staticmethod
    def _apply(state: _Replay, kind: str, payload: dict[str, object]) -> str | None:
        if kind == "attempt-limit-grant":
            if state.grant is not None or set(payload) != grant_policy.GRANT_FIELDS:
                _fail("attempt-limit-grant-refused")
            state.ledger._extend_attempt_limit(maximum=payload["new_max_attempts"])
            state.grant = json.loads(_json(payload))
            return None
        fields = {
            "attempt": {"ordinal", "refreeze"}, "reserve": {"ordinal", "attempt", "input", "output"},
            "intent": {"ordinal"}, "entry": {"ordinal"}, "release": {"ordinal"},
            "uncertain": {"ordinal"}, "finish": {"attempt"}, "failure": {"attempt"},
            "settle": {"ordinal", "usage", "usage_issue", "successful", "response_received"},
        }
        if kind not in fields or set(payload) != fields[kind]:
            _fail("invalid-journal-state")
        snapshot = state.snapshot()
        attempt = snapshot["attempts"][-1] if snapshot["attempts"] else None
        ordinal = payload.get("ordinal")
        if ordinal is not None and (type(ordinal) is not int or ordinal <= 0):
            _fail("invalid-journal-state")
        call = next((item for item in snapshot["calls"] if item["ordinal"] == ordinal), None)
        issue = None
        try:
            if kind == "attempt":
                if type(payload["refreeze"]) is not bool or ordinal != len(snapshot["attempts"]) + 1:
                    _fail("invalid-journal-state")
                if attempt is not None and attempt["status"] != "failed":
                    _fail("failed-attempt-required")
                if snapshot["blocked"]:
                    _fail("accounting-blocked")
                state.ledger.start_attempt(repair_refreeze_confirmed=payload["refreeze"])
            elif kind == "reserve":
                if attempt is None or attempt["status"] != "open" or snapshot["blocked"]:
                    _fail("reservation-admission-refused")
                if type(payload["attempt"]) is not int or payload["attempt"] != attempt["ordinal"]:
                    _fail("invalid-journal-state")
                if ordinal != len(snapshot["calls"]) + 1:
                    _fail("invalid-journal-state")
                state.handles[ordinal] = state.ledger.reserve(input_upper_tokens=payload["input"], output_upper_tokens=payload["output"])
            elif kind in {"finish", "failure"}:
                if type(payload["attempt"]) is not int or attempt is None or payload["attempt"] != attempt["ordinal"]:
                    _fail("invalid-journal-state")
                if attempt["status"] != "open" or snapshot["blocked"]:
                    _fail("attempt-not-finishable")
                if kind == "finish" and not attempt["provider_invocations"]:
                    _fail("empty-attempt-not-complete")
                state.ledger.finish_attempt()
                if kind == "failure":
                    state.failed_attempts.add(attempt["ordinal"])
            else:
                if call is None or call["settled"] or attempt is None or attempt["status"] != "open":
                    _fail("reservation-already-settled-or-inactive")
                handle = state.handles[ordinal]
                if kind == "intent":
                    if ordinal in state.intents:
                        _fail("send-intent-already-recorded")
                    state.intents.add(ordinal)
                elif kind == "entry":
                    if ordinal not in state.intents:
                        _fail("send-intent-required")
                    state.ledger.mark_send_attempt(handle)
                elif kind == "release":
                    if ordinal in state.intents:
                        _fail("cannot-release-send-intent")
                    state.ledger.reject_before_send(handle)
                elif kind == "uncertain":
                    if ordinal not in state.intents or call["send_attempted"]:
                        _fail("uncertain-intent-required")
                    state.uncertain.add(ordinal)
                    state.failed_attempts.add(attempt["ordinal"])
                elif kind == "settle":
                    if type(payload["successful"]) is not bool or type(payload["response_received"]) is not bool:
                        _fail("invalid-response-outcome")
                    usage, reason = payload["usage"], payload["usage_issue"]
                    if usage is None:
                        if type(reason) is not str or reason not in {"usage-unavailable", "invalid-token-usage", "invalid-token-subset"}:
                            _fail("invalid-journal-state")
                        parsed_usage = None
                    else:
                        if type(usage) is not dict or set(usage) != {"input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens"} or reason is not None:
                            _fail("invalid-journal-state")
                        parsed_usage = Usage(**usage)
                        normalized, token_issue = _tokens(parsed_usage)
                        if token_issue is not None or normalized != usage:
                            _fail("invalid-journal-state")
                    try:
                        state.ledger.settle(handle, usage=parsed_usage, successful=payload["successful"], response_received=payload["response_received"])
                    except ConformanceLedgerError as error:
                        if error.code not in {"usage-unavailable", "reservation-exceeded", "total-token-limit-exceeded"}:
                            _fail(error.code)
                        issue = reason if reason is not None else error.code
                    if reason is not None:
                        state.usage_issues[ordinal] = reason
        except ConformanceLedgerError as error:
            issue = error.code
        if issue is not None and kind != "settle":
            _fail(issue)
        return issue

    def _append(self, state: _Replay, kind: str, payload: dict[str, object]) -> str | None:
        if state.event_count >= _MAX_EVENTS:
            _fail("journal-event-ceiling")
        issue = self._apply(state, kind, payload)
        self._connection.execute("INSERT INTO events VALUES (?, ?, ?)", (state.event_count + 1, kind, _json(payload)))
        state.event_count += 1
        return issue

    def start_attempt(self, *, repair_refreeze_confirmed: bool = False) -> int:
        if type(repair_refreeze_confirmed) is not bool:
            _fail("invalid-refreeze-assertion")
        def action(state):
            if state.grant is not None and state.event_count + 14 > _MAX_EVENTS:
                _fail("journal-event-ceiling")
            ordinal = len(state.snapshot()["attempts"]) + 1
            self._append(state, "attempt", {"ordinal": ordinal, "refreeze": repair_refreeze_confirmed})
            return ordinal
        return self._transaction(action)

    def reserve(self, *, input_upper_tokens: int, output_upper_tokens: int) -> ConformanceJournalReservation:
        def action(state):
            snapshot = state.snapshot()
            attempts = snapshot["attempts"]
            if not attempts or attempts[-1]["status"] != "open" or snapshot["blocked"]:
                _fail("reservation-admission-refused")
            payload = {"ordinal": len(snapshot["calls"]) + 1, "attempt": attempts[-1]["ordinal"],
                       "input": input_upper_tokens, "output": output_upper_tokens}
            # Preflight on a throwaway ledger replay; failed admission closes
            # this Attempt durably without persisting any invalid caller value.
            candidate = self._read()
            refusal = None
            try:
                self._apply(candidate, "reserve", payload)
            except ConformanceJournalError as error:
                refusal = error.code
            if refusal is not None:
                self._append(state, "failure", {"attempt": attempts[-1]["ordinal"]})
                return None, refusal
            self._append(state, "reserve", payload)
            return ConformanceJournalReservation(payload["ordinal"], payload["attempt"], input_upper_tokens, output_upper_tokens), None
        handle, issue = self._transaction(action)
        if issue is not None:
            _fail(issue)
        with self._lock:
            self._owned[handle.reservation_ordinal] = handle
        return handle

    def _owned_values(self, handle: ConformanceJournalReservation) -> tuple[int, int, int, int]:
        if type(handle) is not ConformanceJournalReservation:
            _fail("invalid-reservation")
        values = (handle.reservation_ordinal, handle.attempt_ordinal,
                  handle.input_upper_tokens, handle.output_upper_tokens)
        if any(type(value) is not int for value in values):
            _fail("reservation-integrity-failed")
        if self._owned.get(values[0]) is not handle:
            _fail("foreign-reservation")
        return values

    def _call_event(self, handle: ConformanceJournalReservation, kind: str, extra: dict[str, object] | None = None):
        ordinal, attempt, input_upper, output_upper = self._owned_values(handle)
        def action(state):
            call = next((item for item in state.snapshot()["calls"] if item["ordinal"] == ordinal), None)
            if call is None or (attempt, input_upper, output_upper) != (
                call["attempt_ordinal"], call["input_upper_tokens"], call["output_upper_tokens"]
            ):
                _fail("reservation-integrity-failed")
            return self._append(state, kind, {"ordinal": ordinal, **(extra or {})})
        issue = self._transaction(action)
        if issue is not None:
            _fail(issue)

    def persist_send_intent(self, handle: ConformanceJournalReservation) -> None:
        """Commit intent before I/O, without claiming any actual HTTP entry."""
        self._call_event(handle, "intent")

    def record_http_entry(self, handle: ConformanceJournalReservation) -> None:
        """Commit a caller-observed actual HTTP boundary, independently of intent."""
        self._call_event(handle, "entry")

    def reject_before_send(self, handle: ConformanceJournalReservation) -> None:
        """Release only a process-owned call with no durable send intent."""
        self._call_event(handle, "release")

    def record_uncertain_failure(self, handle: ConformanceJournalReservation) -> None:
        """Close an intent-only failure; retain reservation, never fabricate entry."""
        self._call_event(handle, "uncertain")

    def settle(self, handle: ConformanceJournalReservation, *, usage: Usage | None,
               successful: bool, response_received: bool) -> None:
        if type(successful) is not bool or type(response_received) is not bool or (successful and not response_received):
            _fail("invalid-response-outcome")
        normalized, issue = _tokens(usage)
        self._call_event(handle, "settle", {"usage": normalized, "usage_issue": issue,
                                           "successful": successful, "response_received": response_received})

    def fail_attempt(self) -> None:
        """Record a business failure after known settled calls, without retry."""
        self._end("failure")

    def finish_attempt(self) -> None:
        self._end("finish")

    def _end(self, kind: str) -> None:
        def action(state):
            attempts = state.snapshot()["attempts"]
            if not attempts:
                _fail("attempt-required")
            return self._append(state, kind, {"attempt": attempts[-1]["ordinal"]})
        self._transaction(action)

    def snapshot(self) -> dict[str, Any]:
        def action(state):
            result = state.snapshot()
            result["ledger_version"] = "1.0.0"
            result["journal_version"] = "1.0.0"
            result["scope"] = "durable-caller-attested"
            result["budget_namespace"] = self._namespace
            result["events_committed"] = state.event_count
            result["recovery_required"] = any(
                not call["settled"] and call["ordinal"] not in self._owned
                for call in result["calls"]
            )
            if state.grant is not None:
                result.update(ledger_version="1.1.0", journal_version="1.1.0",
                    baseline_limits=_limit_mapping(self._limits), effective_limits=dict(result["limits"]),
                    attempt_limit_grant={"payload": state.grant, "sha256": grant_policy.digest(state.grant)})
            return result
        return self._transaction(action)

    @staticmethod
    def _grant_read_bytes(root, reference):
        """Verify exact referenced bytes without interpreting the user original."""
        result = None
        try:
            grant_policy.reference(reference)
            project = Path(root).resolve()
            target = (project / reference["path"]).resolve()
            if not target.is_relative_to(project):
                _fail("attempt-limit-grant-refused")
            with target.open("rb") as stream:
                raw = stream.read(262145)
            if len(raw) > 262144 or hashlib.sha256(raw).hexdigest() != reference["sha256"]:
                _fail("attempt-limit-grant-refused")
            result = raw
        except Exception:
            pass
        if result is None:
            _fail("attempt-limit-grant-refused")
        return result

    @staticmethod
    def _grant_read(root, reference):
        """Prefix and decision retain their canonical JSON contract."""
        result = None
        try:
            raw = ConformanceUsageJournal._grant_read_bytes(root, reference)
            candidate = json.loads(raw)
            if raw != (grant_policy.canonical(candidate) + "\n").encode("ascii"):
                _fail("attempt-limit-grant-refused")
            result = candidate
        except Exception:
            pass
        if result is None:
            _fail("attempt-limit-grant-refused")
        return result

    def _validate_grant(self, state, grant, *, root, events):
        valid = False
        try:
            prefix = self._grant_read(root, grant["prefix_ref"])
            decision = self._grant_read(root, grant["decision_ref"])
            self._grant_read_bytes(root, decision["user_input_ref"])
            if (prefix["anchor_header"] == json.loads(self._anchor._header_bytes)
                    and prefix["events"] == [list(event) for event in events]):
                grant_policy.validate_grant(grant, namespace=self._namespace, identity=self._anchor.identity,
                    snapshot=state.snapshot(), event_count=state.event_count,
                    chain=grant_policy.prefix_chain(prefix), decision=decision)
                valid = True
        except Exception:
            pass
        if not valid:
            _fail("attempt-limit-grant-refused")

    def budget_extension_prefix(self):
        """Nonsecret, caller-selected archive input; this does not grant capacity."""
        def action(state):
            if self._anchor is None or state.grant is not None:
                _fail("attempt-limit-grant-refused")
            return {"record_kind": "conformance_budget_prefix", "version": "1.0.0",
                "budget_namespace": self._namespace, "journal_identity": self._anchor.identity,
                "anchor_header": json.loads(self._anchor._header_bytes),
                "events": [list(event) for event in self._events()]}
        return self._transaction(action)

    def extend_attempt_limit(self, *, root, decision_ref, prefix_ref):
        """Append one selected 3-to-10 grant; no history rewrite or automatic retry."""
        def action(state):
            if self._anchor is None or state.grant is not None or self._grant_selection is not None:
                _fail("attempt-limit-grant-refused")
            prefix = self._grant_read(root, prefix_ref)
            chain = None
            try:
                chain = grant_policy.prefix_chain(prefix)
            except Exception:
                pass
            if chain is None:
                _fail("attempt-limit-grant-refused")
            grant = {"record_kind": "conformance_attempt_limit_grant", "grant_version": "1.0.0",
                "budget_namespace": self._namespace, "journal_identity": self._anchor.identity,
                "previous_events": state.event_count, "previous_chain_sha256": chain,
                "baseline_limits": _limit_mapping(self._limits), "new_max_attempts": 10,
                "decision_ref": decision_ref, "prefix_ref": prefix_ref,
                "retained_state_sha256": grant_policy.digest(grant_policy.retained_state(state.snapshot()))}
            self._validate_grant(state, grant, root=root, events=self._events())
            self._grant_selection = (Path(root).resolve(), grant_policy.digest(grant))
            self._append(state, "attempt-limit-grant", grant)
            return {"payload": grant, "sha256": grant_policy.digest(grant)}
        with self._lock:
            previous_selection = self._grant_selection
            try:
                receipt = self._transaction(action)
            except Exception:
                self._grant_selection = previous_selection
                raise
            self._extension_metadata = {"baseline_limits": dict(grant_policy.BASELINE),
                "effective_limits": {**grant_policy.BASELINE, "max_attempts": 10}, "attempt_limit_grant": receipt}
            return receipt

    def extension_metadata(self):
        """Previously verified grant facts survive a later unavailable snapshot."""
        with self._lock:
            if self._closed:
                _fail("journal-closed")
            return None if self._extension_metadata is None else json.loads(_json(self._extension_metadata))

    def close(self) -> None:
        failed = False
        with self._lock:
            if not self._closed:
                try:
                    self._connection.close()
                except sqlite3.Error:
                    failed = True
                self._closed = True
                self._owned.clear()
        if failed:
            _fail("journal-storage-unavailable")

    def __enter__(self) -> ConformanceUsageJournal:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
