"""One bounded, independently selected Pilot journal; no execution or grant.

The old M6 history is a verified prefix. This file does not modify that journal
or its successful-finish policy. HTTP observations are caller attestations;
Driver guards and input-bound proof remain required at the actual boundary.
Local anchors detect individual history rollback, not coherent replacement of
both trusted files or consumption through another independently chosen ledger.
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from uuid import UUID

from research_workbench.adapters.models.port import Usage
from research_workbench.evaluation.harness_plan import validate_harness_plan
from research_workbench.evaluation.live_preflight import FrozenLiveContext, VerifiedBudgetCheckpoint
from research_workbench.evaluation.live_verification import VerifiedPilotReservation
from research_workbench.evaluation.pins import digest, timestamp
from research_workbench.evaluation.system_protocol import validate_protocol

_APPLICATION = 0x52574250
_META = "CREATE TABLE meta (id INTEGER PRIMARY KEY CHECK(id=1), header TEXT NOT NULL)"
_EVENTS = "CREATE TABLE events (seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL)"
_MAX_EVENTS = 16384
_CODES = frozenset("""pilot-budget-invalid-state pilot-budget-prior-unverified
pilot-budget-binding-required pilot-budget-context-mismatch pilot-budget-size-unsupported
pilot-budget-retry-run-unsupported pilot-budget-slots-invalid pilot-budget-storage-failed
pilot-budget-clock-required pilot-budget-path-conflict pilot-budget-create-refused
pilot-budget-clock-invalid pilot-budget-anchor-drift pilot-budget-identity-drift
pilot-budget-event-limit pilot-budget-clock-regressed pilot-budget-slot-order-denied
pilot-budget-reservation-denied pilot-budget-request-bound-denied pilot-budget-token-limit
pilot-budget-call-invalid pilot-budget-send-reused pilot-budget-release-after-intent
pilot-budget-settlement-invalid pilot-budget-usage-invalid pilot-budget-closeout-invalid
pilot-budget-event-invalid pilot-budget-time-exhausted pilot-budget-closed
pilot-budget-handle-required pilot-budget-foreign-handle pilot-budget-handle-drift
pilot-budget-current-attempt-denied pilot-budget-tool-before-settlement""".split())


class PilotBudgetError(ValueError):
    """Fixed diagnostics without Provider values, paths or exception context."""


def _need(value, code):
    if not value:
        raise PilotBudgetError(code)


def _safe(operation):
    result, code = None, None
    try:
        result = operation()
    except PilotBudgetError as error:
        args = error.args if type(error) is PilotBudgetError else ()
        code = args[0] if len(args) == 1 and type(args[0]) is str and args[0] in _CODES else "pilot-budget-operation-failed"
    except Exception:
        code = "pilot-budget-operation-failed"
    if code is not None:
        # An exception handler in the caller can still supply implicit context.
        error = PilotBudgetError(code)
        try:
            raise error from None
        finally:
            error.__cause__ = None
            error.__context__ = None
            error.__suppress_context__ = True
    return result


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def _parse(raw):
    def unique(pairs):
        result = {}
        for name, item in pairs:
            _need(name not in result, "pilot-budget-invalid-state")
            result[name] = item
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    _need(type(value) is dict and _json(value) == raw, "pilot-budget-invalid-state")
    return value


def _count(value, *, positive=False):
    return type(value) is int and (0 < value if positive else 0 <= value) and value <= 2**63 - 1


def _prior(reader, context, limits):
    result = reader()
    _need(type(result) is VerifiedBudgetCheckpoint and result.usage_complete
          and dict(result.checkpoint_ref) == dict(context.budget_checkpoint_ref)
          and result.held_total_tokens == 0 and result.known_total_tokens == limits["prior_tokens"]
          and limits["cumulative_token_limit"] <= result.cumulative_token_limit
          and limits["cumulative_token_limit"] <= min(context.cumulative_token_ceiling, 10_000_000),
          "pilot-budget-prior-unverified")


def _binding(inputs, context, prior_reader, identity):
    _need(type(context) is FrozenLiveContext and callable(prior_reader)
          and type(identity) is str and str(UUID(identity)) == identity, "pilot-budget-binding-required")
    scope = inputs.read(context.scope_ref, "evaluation_live_scope")
    protocol = validate_protocol(inputs, dict(context.protocol_ref))
    plan = inputs.read(context.plan_ref, "evaluation_harness_plan")
    validate_harness_plan(inputs, plan, expected_protocol_ref=dict(context.protocol_ref),
        expected_case_closure_ref=dict(context.case_closure_ref),
        case_selection_frozen_at=context.case_selection_frozen_at, expected_run_id=context.run_id)
    _need(protocol["live_scope_ref"] == dict(context.scope_ref)
          and scope["source_commit"] == context.source_commit
          and scope["input_closure_ref"] == dict(context.case_closure_ref)
          and all(scope[name] == dict(getattr(context, name)) for name in
              ("provider_config_ref", "provider_applicability_ref", "windows_context_ref", "budget_checkpoint_ref")),
          "pilot-budget-context-mismatch")
    limits = scope["budget"]
    _need(0 < limits["max_calls_per_attempt"] <= 3 and limits["max_attempts"] <= 1000
          and limits["max_provider_calls"] <= 3000, "pilot-budget-size-unsupported")
    slots = []
    for block in plan["blocks"]:
        if block["phase"] != "pilot":
            continue
        for arm in block["arms"]:
            # This first live run stops on every failure. Manual repair/refreeze
            # needs a fresh accepted run and a prefix including this entire run.
            _need(len(arm["attempt_slots"]) == 1, "pilot-budget-retry-run-unsupported")
            slots.append(arm["attempt_slots"][0]["attempt_id"])
    _need(0 < len(slots) <= limits["max_attempts"] and len(set(slots)) == len(slots),
          "pilot-budget-slots-invalid")
    _prior(prior_reader, context, limits)
    inputs.recheck()
    return {"record_kind": "evaluation_live_budget", "version": "2.0.0", "purpose": "live-pilot",
            "journal_identity": identity, "context": context.value(), "limits": dict(limits), "slots": slots}


def _write(path, raw, *, exclusive=False):
    flags = os.O_WRONLY | getattr(os, "O_BINARY", 0) | (os.O_CREAT | os.O_EXCL if exclusive else os.O_APPEND)
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(raw)
        while view:
            count = os.write(descriptor, view)
            _need(count > 0, "pilot-budget-storage-failed")
            view = view[count:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@dataclass(frozen=True, slots=True, repr=False)
class PilotReservation:
    ordinal: int
    attempt_id: str
    input_upper_tokens: int
    output_upper_tokens: int


class PilotUsageJournal:
    """Serial, single-use accounting for one frozen run, with retained failures.

    Success permits the next preregistered Pilot slot. Any failure stops this
    run; there is no retry/recovery/reconciliation operation. Closing or reopening
    never releases a hold and cannot recover an old process-owned handle.
    The required prior reader is trusted executable authority, not file metadata.
    """

    def __init__(self, connection, database, anchor, inputs, context, prior_reader, clock, header):
        self._connection, self._database, self._anchor = connection, database, anchor
        self._inputs, self._context, self._prior_reader, self._clock = inputs, context, prior_reader, clock
        self._header = _json(header)
        self._anchor_header = _json({"kind": "pilot-budget-anchor", "version": "2.0.0",
            "database": os.path.normcase(str(database)), "anchor": os.path.normcase(str(anchor)),
            "binding_sha256": digest(header), "journal_identity": header["journal_identity"]})
        self._owned, self._lock, self._closed = {}, RLock(), False

    def __repr__(self):
        return "<independently selected bounded Pilot journal>"

    @classmethod
    def _establish(cls, database, anchor, *, inputs, context, prior_reader, clock, journal_identity, create):
        def operation():
            _need(callable(clock), "pilot-budget-clock-required")
            header = _binding(inputs, context, prior_reader, journal_identity)
            target, retained = Path(database).resolve(), Path(anchor).resolve()
            _need(os.path.normcase(str(retained)) not in {os.path.normcase(str(target) + suffix)
                  for suffix in ("", "-wal", "-shm", "-journal")}, "pilot-budget-path-conflict")
            if create:
                _need(not target.exists() and not retained.exists(), "pilot-budget-create-refused")
                _write(target, b"", exclusive=True)
            connection = sqlite3.connect(target.as_uri() + "?mode=rw", uri=True, timeout=1.0,
                                         isolation_level=None, check_same_thread=False)
            journal = cls(connection, target, retained, inputs, context, prior_reader, clock, header)
            try:
                connection.execute("PRAGMA trusted_schema=OFF")
                _need(connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal",
                      "pilot-budget-storage-failed")
                connection.execute("PRAGMA synchronous=FULL")
                if create:
                    _write(retained, (journal._anchor_header + "\n").encode("ascii"), exclusive=True)
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute(_META)
                    connection.execute(_EVENTS)
                    connection.execute("INSERT INTO meta VALUES (1, ?)", (journal._header,))
                    connection.execute(f"PRAGMA application_id={_APPLICATION}")
                    connection.execute("PRAGMA user_version=1")
                    connection.commit()
                journal.snapshot()
                return journal
            except Exception:
                connection.close()
                raise
        return _safe(operation)

    @classmethod
    def create(cls, database, anchor, **options):
        return cls._establish(database, anchor, **options, create=True)

    @classmethod
    def open(cls, database, anchor, **options):
        return cls._establish(database, anchor, **options, create=False)

    def _now(self):
        value = self._clock()
        _need(type(value) is str, "pilot-budget-clock-invalid")
        timestamp(value)
        return value

    def _chains(self, events):
        chain, rows = digest(_parse(self._anchor_header)), []
        for seq, kind, payload in events:
            chain = digest({"previous": chain, "seq": seq, "kind": kind, "payload": payload})
            rows.append(_json({"seq": seq, "chain": chain}))
        return rows

    def _verify_anchor(self, events):
        with self._anchor.open("rb") as stream:
            raw = stream.read(2_097_153)
        _need(len(raw) <= 2_097_152 and raw.endswith(b"\n"), "pilot-budget-anchor-drift")
        lines = raw.decode("ascii").splitlines()
        _need(lines == [self._anchor_header, *self._chains(events)], "pilot-budget-anchor-drift")

    def _read(self):
        connection = self._connection
        _need(connection.execute("PRAGMA application_id").fetchone()[0] == _APPLICATION
              and connection.execute("PRAGMA user_version").fetchone()[0] == 1
              and connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
              and connection.execute("PRAGMA synchronous").fetchone()[0] == 2
              and connection.execute("SELECT type, name, sql FROM sqlite_master ORDER BY name").fetchall()
                  == [("table", "events", _EVENTS), ("table", "meta", _META)]
              and connection.execute("SELECT id, header FROM meta").fetchall() == [(1, self._header)],
              "pilot-budget-identity-drift")
        events = connection.execute("SELECT seq, kind, payload FROM events ORDER BY seq LIMIT ?",
                                    (_MAX_EVENTS + 1,)).fetchall()
        _need(len(events) <= _MAX_EVENTS, "pilot-budget-event-limit")
        self._verify_anchor(events)
        return events, self._replay(events)

    def _replay(self, events):
        header = _parse(self._header)
        state = {"attempts": [], "calls": [], "stopped": False, "last_at": None}
        limits = header["limits"]
        for number, (seq, kind, text) in enumerate(events, 1):
            _need(type(seq) is int and seq == number and type(text) is str and len(text) <= 16384,
                  "pilot-budget-invalid-state")
            payload = _parse(text)
            _need(type(payload.get("at")) is str and (state["last_at"] is None
                  or timestamp(payload["at"]) >= timestamp(state["last_at"])), "pilot-budget-clock-regressed")
            state["last_at"] = payload["at"]
            attempt = state["attempts"][-1] if state["attempts"] else None
            held = [c for c in state["calls"] if c["status"] in {"reserved", "intent", "entered", "unknown"}]
            if kind == "start":
                _need(set(payload) == {"at", "attempt_id"} and not state["stopped"] and not held
                      and (attempt is None or attempt["status"] == "completed")
                      and len(state["attempts"]) < len(header["slots"])
                      and payload["attempt_id"] == header["slots"][len(state["attempts"])],
                      "pilot-budget-slot-order-denied")
                state["attempts"].append({"attempt_id": payload["attempt_id"], "started_at": payload["at"],
                                          "status": "open", "ended_at": None})
                self._time_check(state, payload["at"])
            elif kind == "reserve":
                _need(set(payload) == {"at", "ordinal", "input_upper_tokens", "output_upper_tokens"}
                      and type(payload["ordinal"]) is int and payload["ordinal"] == len(state["calls"]) + 1
                      and attempt is not None and attempt["status"] == "open" and not state["stopped"]
                      and not held and len(state["calls"]) < limits["max_provider_calls"]
                      and sum(c["attempt_id"] == attempt["attempt_id"] for c in state["calls"])
                          < limits["max_calls_per_attempt"], "pilot-budget-reservation-denied")
                for name, maximum in (("input_upper_tokens", "max_request_input_tokens"),
                                      ("output_upper_tokens", "max_request_output_tokens")):
                    _need(_count(payload[name], positive=True) and payload[name] <= limits[maximum],
                          "pilot-budget-request-bound-denied")
                self._time_check(state, payload["at"])
                _need(self._known(state) + payload["input_upper_tokens"] + payload["output_upper_tokens"]
                      <= limits["cumulative_token_limit"], "pilot-budget-token-limit")
                state["calls"].append({**payload, "attempt_id": attempt["attempt_id"], "status": "reserved",
                    "intent_at": None, "entry_at": None, "usage": None, "response_received": False,
                    "successful": False, "bound_exceeded": False, "time_exhausted": False})
            elif kind in {"intent", "entry", "release", "settle"}:
                expected_keys = {"at", "ordinal"} | ({"usage", "response_received", "successful"} if kind == "settle" else set())
                _need(set(payload) == expected_keys and type(payload["ordinal"]) is int
                      and 1 <= payload["ordinal"] <= len(state["calls"]), "pilot-budget-call-invalid")
                call = state["calls"][payload["ordinal"] - 1]
                _need(attempt is not None and call["attempt_id"] == attempt["attempt_id"]
                      and attempt["status"] == "open", "pilot-budget-call-invalid")
                if kind == "intent":
                    _need(call["status"] == "reserved" and not state["stopped"], "pilot-budget-send-reused")
                    self._time_check(state, payload["at"])
                    call.update(status="intent", intent_at=payload["at"])
                elif kind == "entry":
                    _need(call["status"] == "intent" and not state["stopped"], "pilot-budget-send-reused")
                    self._time_check(state, payload["at"])
                    call.update(status="entered", entry_at=payload["at"])
                elif kind == "release":
                    _need(call["status"] == "reserved", "pilot-budget-release-after-intent")
                    call["status"] = "released-before-send"
                    state["stopped"] = True
                else:
                    _need(call["status"] in {"intent", "entered"}
                          and type(payload["successful"]) is type(payload["response_received"]) is bool
                          and (not payload["successful"] or payload["response_received"])
                          and (not payload["response_received"] or call["entry_at"] is not None),
                          "pilot-budget-settlement-invalid")
                    usage = payload["usage"]
                    _need(usage is None or (type(usage) is dict and set(usage) == {"input_tokens", "output_tokens"}
                          and all(v is None or _count(v) for v in usage.values())), "pilot-budget-usage-invalid")
                    known = usage is not None and all(_count(v) for v in usage.values())
                    _need(payload["response_received"] or usage is None, "pilot-budget-settlement-invalid")
                    call.update(usage=usage, response_received=payload["response_received"],
                                successful=payload["successful"], status="known" if known else "unknown")
                    oversize = known and (usage["input_tokens"] > call["input_upper_tokens"]
                                          or usage["output_tokens"] > call["output_upper_tokens"])
                    expired = ((timestamp(payload["at"]) - timestamp(attempt["started_at"])).total_seconds()
                                    >= limits["max_attempt_seconds"] or
                               (timestamp(payload["at"]) - timestamp(state["attempts"][0]["started_at"])).total_seconds()
                                    >= limits["max_run_seconds"])
                    call.update(bound_exceeded=oversize, time_exhausted=expired)
                    if not known or not payload["successful"] or oversize or expired:
                        state["stopped"] = True
            elif kind in {"finish", "fail"}:
                _need(set(payload) == {"at", "attempt_id"} and attempt is not None
                      and attempt["status"] == "open" and payload["attempt_id"] == attempt["attempt_id"],
                      "pilot-budget-closeout-invalid")
                if kind == "finish":
                    calls = [c for c in state["calls"] if c["attempt_id"] == attempt["attempt_id"]]
                    _need(not held and not state["stopped"] and calls
                          and all(c["status"] == "known" and c["successful"] for c in calls),
                          "pilot-budget-closeout-invalid")
                    attempt["status"] = "completed"
                else:
                    attempt["status"], state["stopped"] = "failed", True
                attempt["ended_at"] = payload["at"]
            else:
                _need(False, "pilot-budget-event-invalid")
        return state

    def _known(self, state):
        return _parse(self._header)["limits"]["prior_tokens"] + sum(
            v for c in state["calls"] for v in (c["usage"] or {}).values() if _count(v))

    def _time_check(self, state, at):
        limits = _parse(self._header)["limits"]
        _need(state["attempts"] and timestamp(at) >= timestamp(state["last_at"])
              and (timestamp(at) - timestamp(state["attempts"][-1]["started_at"])).total_seconds()
                    < limits["max_attempt_seconds"]
              and (timestamp(at) - timestamp(state["attempts"][0]["started_at"])).total_seconds()
                    < limits["max_run_seconds"], "pilot-budget-time-exhausted")

    def _transaction(self, operation, *, mutation=None, current=True):
        def run():
            with self._lock:
                _need(not self._closed, "pilot-budget-closed")
                if current:
                    _prior(self._prior_reader, self._context, _parse(self._header)["limits"])
                    self._inputs.recheck()
                try:
                    self._connection.execute("BEGIN IMMEDIATE")
                    events, state = self._read()
                    result = operation(state)
                    if mutation is not None:
                        kind, payload = mutation(state)
                        pending = [*events, (len(events) + 1, kind, _json(payload))]
                        _need(len(pending) <= _MAX_EVENTS, "pilot-budget-event-limit")
                        self._replay(pending)
                        self._connection.execute("INSERT INTO events VALUES (?, ?, ?)", pending[-1])
                        self._verify_anchor(events)
                        _write(self._anchor, (self._chains(pending)[-1] + "\n").encode("ascii"))
                        self._read()
                    if current:
                        self._inputs.recheck()
                    self._connection.commit()
                    return result
                except Exception:
                    self._connection.rollback()
                    raise
        return _safe(run)

    def start_attempt(self, attempt_id):
        self._transaction(lambda _: None, mutation=lambda _: ("start", {"at": self._now(), "attempt_id": attempt_id}))

    def reserve(self, *, input_upper_tokens, output_upper_tokens):
        with self._lock:
            values = self._transaction(lambda state: (len(state["calls"]) + 1,
                state["attempts"][-1]["attempt_id"] if state["attempts"] else None),
                mutation=lambda state: ("reserve", {"at": self._now(), "ordinal": len(state["calls"]) + 1,
                    "input_upper_tokens": input_upper_tokens, "output_upper_tokens": output_upper_tokens}))
            handle = PilotReservation(*values, input_upper_tokens, output_upper_tokens)
            self._owned[handle.ordinal] = (handle, (handle.attempt_id, input_upper_tokens, output_upper_tokens))
            return handle

    def _owned_call(self, state, handle):
        _need(type(handle) is PilotReservation and type(handle.ordinal) is int, "pilot-budget-handle-required")
        selected = self._owned.get(handle.ordinal)
        _need(selected is not None and selected[0] is handle
              and selected[1] == (handle.attempt_id, handle.input_upper_tokens, handle.output_upper_tokens),
              "pilot-budget-foreign-handle")
        call = state["calls"][handle.ordinal - 1]
        _need((call["attempt_id"], call["input_upper_tokens"], call["output_upper_tokens"]) == selected[1],
              "pilot-budget-handle-drift")
        return call

    def _call_event(self, handle, kind, extra=None, *, current=True):
        self._transaction(lambda state: self._owned_call(state, handle), mutation=lambda _: (
            kind, {"at": self._now(), "ordinal": handle.ordinal, **(extra or {})}), current=current)

    def persist_send_intent(self, handle):
        """Durably consume this handle before any I/O; never proof of a send."""
        self._call_event(handle, "intent")

    def record_http_entry(self, handle):
        """One caller-observed HTTP entry, after the durable intent."""
        self._call_event(handle, "entry")

    def reject_before_send(self, handle):
        self._call_event(handle, "release", current=False)

    def settle(self, handle, *, usage, successful, response_received):
        def normalized():
            values = None
            if type(usage) is Usage:
                values = {name: getattr(usage, name) for name in ("input_tokens", "output_tokens")}
                values = {name: v if _count(v) else None for name, v in values.items()}
            self._call_event(handle, "settle", {"usage": values, "successful": successful,
                                                "response_received": response_received}, current=False)
        _safe(normalized)

    def finish_attempt(self, attempt_id):
        self._transaction(lambda _: None, mutation=lambda _: ("finish", {"at": self._now(), "attempt_id": attempt_id}))

    def fail_attempt(self, attempt_id):
        """Business/capture failure; already known responses stay accounted."""
        self._transaction(lambda _: None, mutation=lambda _: ("fail", {"at": self._now(), "attempt_id": attempt_id}),
                          current=False)

    def snapshot(self):
        def read(state):
            header = _parse(self._header)
            held = [c for c in state["calls"] if c["status"] in {"reserved", "intent", "entered", "unknown"}]
            attempts = {a["attempt_id"]: a for a in state["attempts"]}
            return {"record_kind": "evaluation_live_budget_snapshot", "version": "2.0.0", "purpose": "live-pilot",
                "journal_identity": header["journal_identity"], "context": header["context"], "limits": header["limits"],
                "known_total_tokens": self._known(state), "held_total_tokens": sum(
                    c["input_upper_tokens"] + c["output_upper_tokens"] for c in held),
                "usage_complete": not any(c["status"] == "unknown" for c in state["calls"]),
                "stopped": state["stopped"], "recovery_required": any(c["ordinal"] not in self._owned for c in held),
                "attempts": [attempts.get(s, {"attempt_id": s, "status": "not-started", "started_at": None,
                                             "ended_at": None}) for s in header["slots"]],
                "calls": state["calls"], "events_committed": self._connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]}
        # Historical reporting remains possible after external provenance fails.
        # It is never the current-use permission port (observe rechecks it).
        return self._transaction(read, current=False)

    def observe(self, *, attempt_id, surface, handle=None):
        """Trusted ledger port for LiveUseGuard; not a deserialized permit."""
        def read(state):
            _need(surface in {"provider", "tool"} and not state["stopped"] and state["attempts"]
                  and state["attempts"][-1]["attempt_id"] == attempt_id
                  and state["attempts"][-1]["status"] == "open", "pilot-budget-current-attempt-denied")
            now = self._now()
            _need(timestamp(now) >= timestamp(state["last_at"]), "pilot-budget-clock-regressed")
            self._time_check(state, now)
            held = [c for c in state["calls"] if c["status"] in {"reserved", "intent", "entered", "unknown"}]
            call = None
            if surface == "provider":
                call = self._owned_call(state, handle)
                _need(call["status"] == "reserved", "pilot-budget-send-reused")
            else:
                _need(handle is None and not held, "pilot-budget-tool-before-settlement")
            limits = _parse(self._header)["limits"]
            selected = call["ordinal"] if call else None
            return VerifiedPilotReservation(attempt_id, self._known(state),
                call["input_upper_tokens"] if call else 0, call["output_upper_tokens"] if call else 0,
                sum(c["input_upper_tokens"] + c["output_upper_tokens"] for c in held if c["ordinal"] != selected),
                limits["cumulative_token_limit"], len(state["calls"]),
                sum(c["attempt_id"] == attempt_id for c in state["calls"]),
                int((timestamp(now) - timestamp(state["attempts"][-1]["started_at"])).total_seconds()),
                int((timestamp(now) - timestamp(state["attempts"][0]["started_at"])).total_seconds()),
                not any(c["status"] == "unknown" for c in state["calls"]), selected)
        return self._transaction(read)

    def use_verifier(self, *, executor_id, current_handle):
        """Bind the guard's exact context/executor to this owned request port.

        current_handle is an explicit trusted Driver callback, never a handle
        decoded from a file or chosen by a remote response.
        """
        def establish():
            _need(type(executor_id) is str and bool(executor_id.strip()) and callable(current_handle),
                  "pilot-budget-binding-required")
            def verify(argument):
                def read():
                    _need(argument["context"] == self._context.value()
                          and argument["executor_id"] == executor_id and argument["slot"]["phase"] == "pilot"
                          and argument["surface"] in {"provider", "tool"}, "pilot-budget-context-mismatch")
                    _need(timestamp(argument["checked_at"]) <= timestamp(self._now()), "pilot-budget-clock-invalid")
                    attempt_id, surface = argument["slot"]["attempt_id"], argument["surface"]
                    return self.observe(attempt_id=attempt_id, surface=surface,
                                        handle=current_handle(attempt_id) if surface == "provider" else None)
                return _safe(read)
            return verify
        return _safe(establish)

    def close(self):
        def operation():
            with self._lock:
                if not self._closed:
                    self._connection.close()
                    self._owned.clear()
                    self._closed = True
        _safe(operation)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
