"""Opt-in retained local checkpoints for one explicitly selected budget file.

The caller selects one anchor path for the whole execution. This is not a global
namespace registry or authentication against coherent DB+anchor replacement.
Durable checkpoint-before-DB-commit deliberately halts on an uncertain commit;
there is no automatic truncation, reconciliation or rollback recovery.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
from uuid import UUID, uuid4

_MAX_BYTES = 131072
_MAX_EVENTS = 128


class ConformanceBudgetAnchorError(ValueError):
    """Fixed failure code without caller values, paths or exception chains."""

    def __init__(self, code):
        self.code = code
        super().__init__("conformance budget anchor: " + code)


def _fail(code):
    error = ConformanceBudgetAnchorError(code)
    try:
        raise error from None
    finally:
        error.__cause__ = None
        error.__context__ = None
        error.__suppress_context__ = True


def _json(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _canonical_path(value):
    result = None
    try:
        result = os.path.normcase(str(Path(value).resolve(strict=False)))
    except (OSError, ValueError, TypeError, RuntimeError):
        pass
    if result is None:
        _fail("budget-anchor-conflict")
    return result


def _parse(raw):
    value = None
    try:
        def unique(pairs):
            result = {}
            for key, item in pairs:
                if key in result:
                    raise ValueError("duplicate")
                result[key] = item
            return result

        def constant(_):
            raise ValueError("nonfinite")

        value = json.loads(raw, object_pairs_hook=unique, parse_constant=constant)
        if type(value) is not dict or _json(value).encode("ascii") != raw:
            value = None
    except (ValueError, TypeError, UnicodeError, RecursionError):
        pass
    if value is None:
        _fail("budget-anchor-corrupt")
    return value


def _read(path):
    raw = None
    try:
        with open(path, "rb") as stream:
            raw = stream.read(_MAX_BYTES + 1)
    except (OSError, TypeError, ValueError):
        pass
    if raw is None:
        _fail("budget-anchor-unavailable")
    if not raw or len(raw) > _MAX_BYTES or not raw.endswith(b"\n"):
        _fail("budget-anchor-corrupt")
    lines = raw[:-1].split(b"\n")
    if any(not line for line in lines) or len(lines) > _MAX_EVENTS + 1:
        _fail("budget-anchor-corrupt")
    return lines


def _write_durable(path, raw, *, exclusive):
    descriptor = None
    failed = False
    try:
        flags = os.O_WRONLY | getattr(os, "O_BINARY", 0) | (os.O_CREAT | os.O_EXCL if exclusive else os.O_APPEND)
        descriptor = os.open(path, flags, 0o600)
        view = memoryview(raw)
        while view:
            count = os.write(descriptor, view)
            if count <= 0:
                raise OSError("incomplete")
            view = view[count:]
        os.fsync(descriptor)
    except (OSError, TypeError, ValueError):
        failed = True
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                failed = True
    if failed:
        _fail("budget-anchor-unavailable")


def _header(database, anchor, namespace, limits, identity):
    return {"record_kind": "conformance_budget_anchor", "anchor_version": "1.0.0",
            "database_schema_version": 2, "database_path": database,
            "anchor_path": anchor, "budget_namespace": namespace,
            "limits": dict(limits), "journal_identity": identity}


class ConformanceBudgetAnchor:
    """Private local retained-anchor binding; snapshots never export paths."""

    __slots__ = ("_path", "_header_bytes", "_identity")

    def __init__(self, path, header):
        object.__setattr__(self, "_path", path)
        object.__setattr__(self, "_header_bytes", _json(header).encode("ascii"))
        object.__setattr__(self, "_identity", header["journal_identity"])

    def __setattr__(self, name, value):
        raise AttributeError("budget anchor binding is frozen")

    def __repr__(self):
        return "<retained conformance budget anchor>"

    @property
    def identity(self):
        return self._identity

    @classmethod
    def create(cls, path, *, database_path, namespace, limits):
        anchor, database = _canonical_path(path), _canonical_path(database_path)
        if anchor in {database, database + "-wal", database + "-shm", database + "-journal"}:
            _fail("budget-anchor-conflict")
        header = _header(database, anchor, namespace, limits, str(uuid4()))
        raw = _json(header).encode("ascii") + b"\n"
        if len(raw) > _MAX_BYTES:
            _fail("budget-anchor-conflict")
        _write_durable(anchor, raw, exclusive=True)
        result = cls(anchor, header)
        result.verify([])
        return result

    @classmethod
    def open(cls, path, *, database_path, namespace, limits):
        anchor, database = _canonical_path(path), _canonical_path(database_path)
        lines = _read(anchor)
        header = _parse(lines[0])
        identity = header.get("journal_identity")
        valid_identity = False
        try:
            valid_identity = type(identity) is str and str(UUID(identity)) == identity
        except (ValueError, AttributeError):
            pass
        if not valid_identity or _json(header) != _json(_header(database, anchor, namespace, limits, identity)):
            _fail("budget-anchor-conflict")
        return cls(anchor, header)

    def _chains(self, events):
        if type(events) is not list or len(events) > _MAX_EVENTS:
            _fail("budget-anchor-drift")
        chain = hashlib.sha256(self._header_bytes).hexdigest()
        result = [chain]
        for ordinal, event in enumerate(events, 1):
            if (type(event) is not tuple or len(event) != 3 or type(event[0]) is not int
                    or event[0] != ordinal or type(event[1]) is not str or type(event[2]) is not str):
                _fail("budget-anchor-drift")
            body = _json({"previous": chain, "seq": ordinal, "kind": event[1], "payload": event[2]})
            chain = hashlib.sha256(body.encode("ascii")).hexdigest()
            result.append(chain)
        return result

    def verify(self, events):
        chains = self._chains(events)
        lines = _read(self._path)
        if lines[0] != self._header_bytes:
            _fail("budget-anchor-conflict")
        if len(lines) != len(chains):
            _fail("budget-anchor-drift")
        for sequence, line in enumerate(lines[1:], 1):
            checkpoint = _parse(line)
            if (set(checkpoint) != {"seq", "chain"} or type(checkpoint["seq"]) is not int
                    or checkpoint["seq"] != sequence or type(checkpoint["chain"]) is not str
                    or re.fullmatch("[0-9a-f]{64}", checkpoint["chain"]) is None
                    or checkpoint["chain"] != chains[sequence]):
                _fail("budget-anchor-drift")

    def checkpoint(self, events, *, previous_count):
        if type(previous_count) is not int or not 0 <= previous_count <= len(events):
            _fail("budget-anchor-drift")
        # Re-read every old checkpoint just before appending; changed history
        # cannot be incorporated into a new apparently valid head.
        self.verify(events[:previous_count])
        if len(events) == previous_count:
            return
        chains = self._chains(events)
        raw = b"".join((_json({"seq": n, "chain": chains[n]}).encode("ascii") + b"\n")
                       for n in range(previous_count + 1, len(events) + 1))
        _write_durable(self._path, raw, exclusive=False)
        self.verify(events)
