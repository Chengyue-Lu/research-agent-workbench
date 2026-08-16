"""Pure, bounded capture contract for one future Docker proxy audit attach.

This Huang Yi-owned Runtime Adapter module validates bytes supplied by a
caller.  It does not start or inspect Docker, read an environment, open a
socket, access a credential, write a file, or update the shared Trace/CLI
contracts.  Live attach remains disabled until a reviewed supervisor supplies
the container lifecycle facts and the bounded byte stream.

Only one canonical, already-redacted :class:`EgressAuditRecord` JSONL line is
accepted.  Raw JSON text is held only in bounded memory until that line is
validated, then released.  The returned evidence contains the redacted record,
binding/lifecycle facts, counters, and hashes; it never contains raw stdout.
"""

from __future__ import annotations

import codecs
import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Self

from research_workbench.adapters.codex_egress_proxy import (
    CODEX_EGRESS_AUDIT_SCHEMA,
    CODEX_EGRESS_DESTINATION_ID,
    CODEX_EGRESS_MAX_CLIENT_TO_UPSTREAM_BYTES,
    CODEX_EGRESS_MAX_UPSTREAM_TO_CLIENT_BYTES,
    CODEX_EGRESS_MAX_WALL_TIMEOUT_MS,
    EgressAuditRecord,
)

CODEX_PROXY_AUDIT_CAPTURE_SCHEMA = "rwb-codex-proxy-audit-capture/0.1"
CODEX_PROXY_AUDIT_CAPTURE_LIVE_READY = False
CODEX_PROXY_AUDIT_CAPTURE_OWNER_BOUNDARY = "huang-yi-runtime-adapter"

CODEX_PROXY_AUDIT_CAPTURE_MAX_TOTAL_BYTES = 16_384
CODEX_PROXY_AUDIT_CAPTURE_MAX_LINE_BYTES = 16_383
CODEX_PROXY_AUDIT_CAPTURE_MAX_DEADLINE_SECONDS = 180.0

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_CONTAINER_ID = re.compile(r"[0-9a-f]{64}\Z")
_SENSITIVE_FIELD_NAME = re.compile(
    r"(?:api[_-]?key|authorization|credential|password|secret|token|"
    r"access[_-]?key|bearer|cookie|raw|payload|transcript|request|response|"
    r"header|body|peer|literal[_-]?ip|server[_-]?name)",
    flags=re.IGNORECASE,
)
_AUDIT_FIELDS = frozenset(
    {
        "capture_complete",
        "client_hello_sha256",
        "client_to_upstream_bytes",
        "client_to_upstream_sha256",
        "connection_sequence",
        "destination_id",
        "duration_ms",
        "failure_code",
        "outcome",
        "policy_sha256",
        "resolution_sha256",
        "schema",
        "selected_address_index",
        "sni_verified",
        "upstream_to_client_bytes",
        "upstream_to_client_sha256",
    }
)
_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
_PRODUCER_OUTCOMES = frozenset({"completed", "blocked", "failed"})
_PRODUCER_FAILURE_CODES = frozenset(
    {
        "connect-authority-not-allowed",
        "connect-client-closed",
        "connect-header-byte-limit-exceeded",
        "connect-header-control-character",
        "connect-header-count-exceeded",
        "connect-header-duplicate",
        "connect-header-folding-forbidden",
        "connect-header-incomplete",
        "connect-header-name-invalid",
        "connect-header-not-allowed",
        "connect-header-not-ascii",
        "connect-header-value-empty",
        "connect-host-mismatch",
        "connect-host-missing",
        "connect-line-ending-invalid",
        "connect-pipelined-data-forbidden",
        "connect-request-empty",
        "connect-request-line-invalid",
        "connect-request-line-limit-exceeded",
        "connect-request-not-bytes",
        "egress-activity-time-invalid",
        "egress-actual-peer-invalid",
        "egress-actual-peer-mismatch",
        "egress-address-index-invalid",
        "egress-attestation-binding-invalid",
        "egress-attestation-target-mismatch",
        "egress-client-byte-limit-exceeded",
        "egress-client-relay-closed",
        "egress-clock-regressed",
        "egress-concurrent-limit-exceeded",
        "egress-connection-limit-exceeded",
        "egress-controller-state-invalid",
        "egress-dial-failed",
        "egress-frozen-address-invalid",
        "egress-idle-time-limit-exceeded",
        "egress-meter-contract-error",
        "egress-policy-hash-mismatch",
        "egress-relay-capture-incomplete",
        "egress-resolution-address-limit-exceeded",
        "egress-resolution-empty",
        "egress-resolution-failed",
        "egress-resolution-invalid",
        "egress-resolution-mixed-or-non-global",
        "egress-resolution-no-global-address",
        "egress-runtime-peer-mismatch",
        "egress-server-audit-finalization-failed",
        "egress-server-audit-missing",
        "egress-server-internal-failure",
        "egress-server-io-failed",
        "egress-server-recv-invalid",
        "egress-server-send-failed",
        "egress-server-shutdown-failed",
        "egress-server-socket-invalid",
        "egress-server-timeout",
        "egress-sni-verification-required",
        "egress-tunnel-already-closed",
        "egress-tunnel-payload-not-bytes",
        "egress-upstream-byte-limit-exceeded",
        "egress-upstream-relay-closed",
        "egress-wall-time-limit-exceeded",
        "tls-client-hello-ciphers-invalid",
        "tls-client-hello-client-closed",
        "tls-client-hello-compression-invalid",
        "tls-client-hello-extension-truncated",
        "tls-client-hello-extensions-length-invalid",
        "tls-client-hello-extra-data-forbidden",
        "tls-client-hello-handshake-invalid",
        "tls-client-hello-handshake-length-invalid",
        "tls-client-hello-not-bytes",
        "tls-client-hello-record-count-exceeded",
        "tls-client-hello-record-invalid",
        "tls-client-hello-record-length-invalid",
        "tls-client-hello-size-invalid",
        "tls-client-hello-sni-duplicate",
        "tls-client-hello-sni-invalid",
        "tls-client-hello-sni-missing",
        "tls-client-hello-sni-not-allowed",
    }
)


class CodexProxyAuditCaptureError(RuntimeError):
    """Stable failure that never contains captured stdout or field values."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class CodexProxyAuditCaptureLimits:
    """Fixed upper bounds for one injected Docker attach byte stream."""

    max_total_bytes: int = CODEX_PROXY_AUDIT_CAPTURE_MAX_TOTAL_BYTES
    max_line_bytes: int = CODEX_PROXY_AUDIT_CAPTURE_MAX_LINE_BYTES

    def __post_init__(self) -> None:
        _bounded_positive_int(
            "max_total_bytes",
            self.max_total_bytes,
            CODEX_PROXY_AUDIT_CAPTURE_MAX_TOTAL_BYTES,
        )
        _bounded_positive_int(
            "max_line_bytes",
            self.max_line_bytes,
            CODEX_PROXY_AUDIT_CAPTURE_MAX_LINE_BYTES,
        )
        if self.max_line_bytes + 1 > self.max_total_bytes:
            raise ValueError("max_total_bytes must include the JSONL newline")

    def to_mapping(self) -> dict[str, int]:
        return {
            "max_line_bytes": self.max_line_bytes,
            "max_total_bytes": self.max_total_bytes,
        }


@dataclass(frozen=True, slots=True)
class CodexProxyAuditCaptureBinding:
    """Immutable expected identity for one proxy container and DNS policy."""

    container_id: str
    policy_sha256: str
    resolution_sha256: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.container_id, str)
            or _CONTAINER_ID.fullmatch(self.container_id) is None
        ):
            raise ValueError("container_id must be a lowercase Docker identity")
        _validate_sha256("policy_sha256", self.policy_sha256)
        _validate_sha256("resolution_sha256", self.resolution_sha256)

    def to_mapping(self) -> dict[str, str]:
        return {
            "container_id": self.container_id,
            "policy_sha256": self.policy_sha256,
            "resolution_sha256": self.resolution_sha256,
        }

    @property
    def sha256(self) -> str:
        return hashlib.sha256(_canonical_json_bytes(self.to_mapping())).hexdigest()


@dataclass(frozen=True, slots=True)
class CodexProxyAuditCaptureLifecycle:
    """Supervisor-observed terminal facts; this class performs no observation."""

    container_id: str
    exit_code: int
    container_terminal: bool
    stdout_eof: bool
    capture_complete: bool
    capture_closed_after_terminal: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(self.container_id, str)
            or _CONTAINER_ID.fullmatch(self.container_id) is None
        ):
            raise ValueError("container_id must be a lowercase Docker identity")
        if (
            isinstance(self.exit_code, bool)
            or not isinstance(self.exit_code, int)
            or not 0 <= self.exit_code <= 255
        ):
            raise ValueError("exit_code must be an unsigned process exit code")
        for name in (
            "container_terminal",
            "stdout_eof",
            "capture_complete",
            "capture_closed_after_terminal",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be boolean")

    def to_mapping(self) -> dict[str, object]:
        return {
            "capture_closed_after_terminal": self.capture_closed_after_terminal,
            "capture_complete": self.capture_complete,
            "container_id": self.container_id,
            "container_terminal": self.container_terminal,
            "exit_code": self.exit_code,
            "stdout_eof": self.stdout_eof,
        }

    @property
    def sha256(self) -> str:
        return hashlib.sha256(_canonical_json_bytes(self.to_mapping())).hexdigest()


@dataclass(frozen=True, slots=True, init=False)
class CodexProxyAuditCaptureEvidence:
    """Hash-bound redacted projection returned by in-process validation.

    This Python value is not a cross-process trust root.  A future supervisor
    must persist and revalidate the canonical stream plus lifecycle evidence.
    """

    binding: CodexProxyAuditCaptureBinding
    lifecycle: CodexProxyAuditCaptureLifecycle
    audit_record: EgressAuditRecord
    limits: CodexProxyAuditCaptureLimits
    stream_sha256: str
    audit_record_sha256: str
    captured_bytes: int
    line_bytes: int
    deadline_ms: int
    elapsed_ms: int

    def __new__(cls, *args: object, **kwargs: object) -> Self:
        del args, kwargs
        raise TypeError("capture evidence is produced only by validation")

    @property
    def schema(self) -> str:
        return CODEX_PROXY_AUDIT_CAPTURE_SCHEMA

    @property
    def owner_boundary(self) -> str:
        return CODEX_PROXY_AUDIT_CAPTURE_OWNER_BOUNDARY

    @property
    def live_ready(self) -> bool:
        return CODEX_PROXY_AUDIT_CAPTURE_LIVE_READY

    @property
    def record_count(self) -> int:
        return 1

    @property
    def stream_capture_complete(self) -> bool:
        return self.lifecycle.capture_complete

    @property
    def audit_capture_complete(self) -> bool:
        return self.audit_record.capture_complete

    @property
    def lifecycle_assurance(self) -> str:
        return "caller-attested"

    @property
    def terminal(self) -> bool:
        return self.lifecycle.container_terminal

    def to_mapping(self) -> dict[str, object]:
        """Return the complete durable projection; no raw stdout is included."""

        return {
            "audit_record": self.audit_record.to_mapping(),
            "audit_record_sha256": self.audit_record_sha256,
            "binding": self.binding.to_mapping(),
            "binding_sha256": self.binding.sha256,
            "audit_capture_complete": self.audit_capture_complete,
            "captured_bytes": self.captured_bytes,
            "deadline_ms": self.deadline_ms,
            "elapsed_ms": self.elapsed_ms,
            "lifecycle": self.lifecycle.to_mapping(),
            "lifecycle_assurance": self.lifecycle_assurance,
            "lifecycle_sha256": self.lifecycle.sha256,
            "limits": self.limits.to_mapping(),
            "line_bytes": self.line_bytes,
            "live_ready": self.live_ready,
            "owner_boundary": self.owner_boundary,
            "record_count": self.record_count,
            "schema": self.schema,
            "stream_sha256": self.stream_sha256,
            "stream_capture_complete": self.stream_capture_complete,
            "terminal": self.terminal,
        }

    @property
    def sha256(self) -> str:
        return hashlib.sha256(_canonical_json_bytes(self.to_mapping())).hexdigest()


class CodexProxyAuditCapture:
    """Incrementally validate exactly one bounded canonical audit JSONL line."""

    __slots__ = (
        "_binding",
        "_closed",
        "_deadline_at",
        "_decoder",
        "_last_now",
        "_limits",
        "_line_bytes",
        "_record",
        "_started_at",
        "_stream_hash",
        "_text_parts",
        "_total_bytes",
    )

    def __init__(
        self,
        binding: CodexProxyAuditCaptureBinding,
        *,
        started_at: float,
        deadline_seconds: float,
        limits: CodexProxyAuditCaptureLimits | None = None,
    ) -> None:
        if not isinstance(binding, CodexProxyAuditCaptureBinding):
            raise TypeError("binding must be CodexProxyAuditCaptureBinding")
        _validate_clock_value(started_at, "started_at")
        _validate_deadline_seconds(deadline_seconds)
        active_limits = limits or CodexProxyAuditCaptureLimits()
        if not isinstance(active_limits, CodexProxyAuditCaptureLimits):
            raise TypeError("limits must be CodexProxyAuditCaptureLimits")
        self._binding = binding
        self._started_at = float(started_at)
        self._deadline_at = self._started_at + float(deadline_seconds)
        self._last_now = self._started_at
        self._limits = active_limits
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        self._text_parts: list[str] = []
        self._stream_hash = hashlib.sha256()
        self._total_bytes = 0
        self._line_bytes = 0
        self._record: EgressAuditRecord | None = None
        self._closed = False

    def feed(self, chunk: bytes, *, now: float) -> None:
        """Consume one caller-supplied stdout chunk without retaining raw bytes."""

        self._check_open()
        self._check_time(now)
        if not isinstance(chunk, bytes):
            self._fail("proxy-audit-capture-chunk-invalid")
        if self._record is not None:
            if chunk:
                canonical_frame = f"{self._record.to_json()}\n".encode(
                    "ascii", errors="strict"
                )
                code = (
                    "proxy-audit-capture-record-duplicate"
                    if chunk == canonical_frame
                    else "proxy-audit-capture-extra-record"
                )
                self._fail(code)
            return
        if self._total_bytes + len(chunk) > self._limits.max_total_bytes:
            self._fail("proxy-audit-capture-total-byte-limit-exceeded")

        newline_index = chunk.find(b"\n")
        line_fragment = chunk if newline_index < 0 else chunk[:newline_index]
        if self._line_bytes + len(line_fragment) > self._limits.max_line_bytes:
            self._fail("proxy-audit-capture-line-byte-limit-exceeded")
        if newline_index >= 0 and newline_index + 1 != len(chunk):
            first_frame = chunk[: newline_index + 1]
            surplus = chunk[newline_index + 1 :]
            code = (
                "proxy-audit-capture-record-duplicate"
                if surplus == first_frame
                else "proxy-audit-capture-extra-record"
            )
            self._fail(code)

        self._stream_hash.update(chunk)
        self._total_bytes += len(chunk)
        self._line_bytes += len(line_fragment)
        try:
            decoded = self._decoder.decode(
                line_fragment,
                final=newline_index >= 0,
            )
        except UnicodeDecodeError:
            self._fail("proxy-audit-capture-utf8-invalid")
        self._text_parts.append(decoded)
        if newline_index < 0:
            return

        text = "".join(self._text_parts)
        self._text_parts.clear()
        self._decoder = None
        if not text:
            self._fail("proxy-audit-capture-blank-line")
        self._record = self._parse_record(text)

    def finalize(
        self,
        lifecycle: CodexProxyAuditCaptureLifecycle,
        *,
        now: float,
    ) -> CodexProxyAuditCaptureEvidence:
        """Seal one complete terminal capture and return only redacted evidence."""

        self._check_open()
        self._check_time(now)
        self._closed = True
        if not isinstance(lifecycle, CodexProxyAuditCaptureLifecycle):
            self._release_raw_state()
            raise CodexProxyAuditCaptureError("proxy-audit-capture-lifecycle-invalid")
        if self._record is None:
            try:
                self._decoder.decode(b"", final=True)
            except UnicodeDecodeError:
                self._release_raw_state()
                raise CodexProxyAuditCaptureError(
                    "proxy-audit-capture-utf8-invalid"
                ) from None
            self._release_raw_state()
            if self._total_bytes:
                raise CodexProxyAuditCaptureError(
                    "proxy-audit-capture-terminal-newline-missing"
                )
            raise CodexProxyAuditCaptureError("proxy-audit-capture-record-missing")
        self._release_raw_state()
        _validate_terminal_matrix(self._binding, lifecycle, self._record)

        canonical_record = self._record.to_json().encode("ascii", errors="strict")
        evidence = object.__new__(CodexProxyAuditCaptureEvidence)
        object.__setattr__(evidence, "binding", self._binding)
        object.__setattr__(evidence, "lifecycle", lifecycle)
        object.__setattr__(evidence, "audit_record", self._record)
        object.__setattr__(evidence, "limits", self._limits)
        object.__setattr__(
            evidence,
            "stream_sha256",
            self._stream_hash.hexdigest(),
        )
        object.__setattr__(
            evidence,
            "audit_record_sha256",
            hashlib.sha256(canonical_record).hexdigest(),
        )
        object.__setattr__(evidence, "captured_bytes", self._total_bytes)
        object.__setattr__(evidence, "line_bytes", self._line_bytes)
        object.__setattr__(
            evidence,
            "deadline_ms",
            int((self._deadline_at - self._started_at) * 1_000),
        )
        object.__setattr__(
            evidence,
            "elapsed_ms",
            max(0, int((float(now) - self._started_at) * 1_000)),
        )
        return evidence

    def _parse_record(self, text: str) -> EgressAuditRecord:
        try:
            document = json.loads(
                text,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_json_constant,
            )
        except _DuplicateJsonKeyError:
            self._fail("proxy-audit-capture-json-key-duplicate")
        except (json.JSONDecodeError, RecursionError, TypeError, ValueError):
            self._fail("proxy-audit-capture-json-invalid")
        if not isinstance(document, dict):
            self._fail("proxy-audit-capture-record-not-object")

        observed_fields = set(document)
        unknown_fields = observed_fields - _AUDIT_FIELDS
        if any(_SENSITIVE_FIELD_NAME.search(name) for name in unknown_fields):
            self._fail("proxy-audit-capture-sensitive-field")
        if unknown_fields:
            self._fail("proxy-audit-capture-unknown-field")
        if observed_fields != _AUDIT_FIELDS:
            self._fail("proxy-audit-capture-field-set-invalid")
        if document.get("schema") != CODEX_EGRESS_AUDIT_SCHEMA:
            self._fail("proxy-audit-capture-schema-mismatch")
        if document.get("destination_id") != CODEX_EGRESS_DESTINATION_ID:
            self._fail("proxy-audit-capture-destination-mismatch")

        try:
            record = EgressAuditRecord(
                policy_sha256=document["policy_sha256"],
                resolution_sha256=document["resolution_sha256"],
                selected_address_index=document["selected_address_index"],
                client_hello_sha256=document["client_hello_sha256"],
                connection_sequence=document["connection_sequence"],
                outcome=document["outcome"],
                client_to_upstream_bytes=document["client_to_upstream_bytes"],
                upstream_to_client_bytes=document["upstream_to_client_bytes"],
                client_to_upstream_sha256=document["client_to_upstream_sha256"],
                upstream_to_client_sha256=document["upstream_to_client_sha256"],
                duration_ms=document["duration_ms"],
                sni_verified=document["sni_verified"],
                capture_complete=document["capture_complete"],
                failure_code=document["failure_code"],
            )
        except (KeyError, TypeError, ValueError):
            self._fail("proxy-audit-capture-record-invalid")
        if record.connection_sequence != 1:
            self._fail("proxy-audit-capture-sequence-mismatch")
        if record.policy_sha256 != self._binding.policy_sha256:
            self._fail("proxy-audit-capture-policy-mismatch")
        if record.resolution_sha256 != self._binding.resolution_sha256:
            self._fail("proxy-audit-capture-resolution-mismatch")
        _validate_producer_record(record)
        if record.to_json() != text:
            self._fail("proxy-audit-capture-record-noncanonical")
        return record

    def _check_open(self) -> None:
        if self._closed:
            raise CodexProxyAuditCaptureError("proxy-audit-capture-already-closed")

    def _check_time(self, now: float) -> None:
        try:
            _validate_clock_value(now, "now")
        except (TypeError, ValueError):
            self._fail("proxy-audit-capture-clock-invalid")
        active_now = float(now)
        if active_now < self._last_now:
            self._fail("proxy-audit-capture-clock-regressed")
        if active_now >= self._deadline_at:
            self._fail("proxy-audit-capture-deadline-exceeded")
        self._last_now = active_now

    def _release_raw_state(self) -> None:
        self._text_parts.clear()
        self._decoder = None

    def _fail(self, code: str) -> None:
        self._closed = True
        self._release_raw_state()
        raise CodexProxyAuditCaptureError(code)


def reject_live_proxy_audit_attach(*args: object, **kwargs: object) -> None:
    """Fail before inspecting future live attach inputs."""

    del args, kwargs
    raise CodexProxyAuditCaptureError("proxy-audit-capture-live-disabled")


class _DuplicateJsonKeyError(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise _DuplicateJsonKeyError()
        document[key] = value
    return document


def _reject_json_constant(_value: str) -> None:
    raise ValueError("non-finite JSON constants are forbidden")


def _validate_terminal_matrix(
    binding: CodexProxyAuditCaptureBinding,
    lifecycle: CodexProxyAuditCaptureLifecycle,
    record: EgressAuditRecord,
) -> None:
    if lifecycle.container_id != binding.container_id:
        raise CodexProxyAuditCaptureError(
            "proxy-audit-capture-container-identity-mismatch"
        )
    if lifecycle.container_terminal is not True:
        raise CodexProxyAuditCaptureError("proxy-audit-capture-terminal-unverified")
    if lifecycle.stdout_eof is not True:
        raise CodexProxyAuditCaptureError("proxy-audit-capture-stdout-eof-unverified")
    if lifecycle.capture_complete is not True:
        raise CodexProxyAuditCaptureError("proxy-audit-capture-incomplete")
    if lifecycle.capture_closed_after_terminal is not True:
        raise CodexProxyAuditCaptureError("proxy-audit-capture-close-order-unverified")
    expected_exit_code = (
        0 if record.outcome == "completed" and record.capture_complete else 1
    )
    if lifecycle.exit_code != expected_exit_code:
        raise CodexProxyAuditCaptureError("proxy-audit-capture-exit-mismatch")


def _validate_producer_record(record: EgressAuditRecord) -> None:
    if record.outcome not in _PRODUCER_OUTCOMES:
        raise CodexProxyAuditCaptureError("proxy-audit-capture-outcome-unreachable")
    if record.selected_address_index != 0:
        raise CodexProxyAuditCaptureError(
            "proxy-audit-capture-address-index-unreachable"
        )
    if (
        record.client_to_upstream_bytes > CODEX_EGRESS_MAX_CLIENT_TO_UPSTREAM_BYTES
        or record.upstream_to_client_bytes > CODEX_EGRESS_MAX_UPSTREAM_TO_CLIENT_BYTES
        or record.duration_ms > CODEX_EGRESS_MAX_WALL_TIMEOUT_MS
    ):
        raise CodexProxyAuditCaptureError("proxy-audit-capture-producer-limit-exceeded")
    for byte_count, digest in (
        (record.client_to_upstream_bytes, record.client_to_upstream_sha256),
        (record.upstream_to_client_bytes, record.upstream_to_client_sha256),
    ):
        if (byte_count == 0) is not (digest == _EMPTY_SHA256):
            raise CodexProxyAuditCaptureError(
                "proxy-audit-capture-byte-hash-inconsistent"
            )

    if record.outcome == "completed":
        if (
            record.failure_code is not None
            or record.sni_verified is not True
            or record.capture_complete is not True
            or record.client_to_upstream_bytes <= 0
            or record.client_hello_sha256 == _EMPTY_SHA256
        ):
            raise CodexProxyAuditCaptureError(
                "proxy-audit-capture-completed-matrix-invalid"
            )
        return

    if (
        record.failure_code not in _PRODUCER_FAILURE_CODES
        or record.capture_complete is not False
    ):
        raise CodexProxyAuditCaptureError("proxy-audit-capture-failure-matrix-invalid")
    if not record.sni_verified and (
        record.client_to_upstream_bytes != 0 or record.upstream_to_client_bytes != 0
    ):
        raise CodexProxyAuditCaptureError(
            "proxy-audit-capture-pre-attestation-bytes-invalid"
        )


def _bounded_positive_int(name: str, value: int, ceiling: int) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value > ceiling
    ):
        raise ValueError(f"{name} must be a positive integer within its ceiling")


def _validate_sha256(name: str, value: str) -> None:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256")


def _validate_clock_value(value: float, name: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{name} must be a finite monotonic value")


def _validate_deadline_seconds(value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
        or value > CODEX_PROXY_AUDIT_CAPTURE_MAX_DEADLINE_SECONDS
    ):
        raise ValueError("deadline_seconds is outside the fixed ceiling")


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii", errors="strict")


__all__ = [
    "CODEX_PROXY_AUDIT_CAPTURE_LIVE_READY",
    "CODEX_PROXY_AUDIT_CAPTURE_MAX_DEADLINE_SECONDS",
    "CODEX_PROXY_AUDIT_CAPTURE_MAX_LINE_BYTES",
    "CODEX_PROXY_AUDIT_CAPTURE_MAX_TOTAL_BYTES",
    "CODEX_PROXY_AUDIT_CAPTURE_OWNER_BOUNDARY",
    "CODEX_PROXY_AUDIT_CAPTURE_SCHEMA",
    "CodexProxyAuditCapture",
    "CodexProxyAuditCaptureBinding",
    "CodexProxyAuditCaptureError",
    "CodexProxyAuditCaptureEvidence",
    "CodexProxyAuditCaptureLifecycle",
    "CodexProxyAuditCaptureLimits",
    "reject_live_proxy_audit_attach",
]
