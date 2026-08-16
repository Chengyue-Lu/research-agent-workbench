"""Explicit, short-lived socket host for the bounded Codex egress contract.

Importing this module performs no resolution, bind, listen, accept, or dial.
The caller must inject an already-listening socket and explicitly call
``CodexEgressServer.run``.  The server is deliberately limited to the one
CONNECT destination frozen by :mod:`codex_egress_proxy`.

Raw CONNECT headers, address literals, TLS bytes, credentials, and exception
messages never enter an audit record.  The only retained transport material is
the bounded counters and SHA-256 digests defined by the public proxy contract.
"""

from __future__ import annotations

import hashlib
import ipaddress
import selectors
import socket
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from research_workbench.adapters.codex_egress_proxy import (
    CODEX_EGRESS_MAX_CLIENT_HELLO_BYTES,
    CodexEgressProxyError,
    DialedEgressTarget,
    EgressAuditRecord,
    EgressConnectionController,
    EgressDialer,
    EgressPolicy,
    EgressResolver,
    EgressTunnelMeter,
    ResolvedEgressTarget,
    attest_tls_client_hello,
    dial_egress_target,
    parse_connect_request,
    resolve_egress_target,
)

_CONNECT_ESTABLISHED = b"HTTP/1.1 200 Connection Established\r\n\r\n"
_IO_CHUNK_BYTES = 16_384
_RELAY_BUFFER_BYTES = 65_536
_MAX_TLS_RECORDS = 3
_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


class AuditSink(Protocol):
    """Receive exactly one already-redacted record per accepted connection."""

    def __call__(self, record: EgressAuditRecord) -> None: ...


class RelayWaiter(Protocol):
    """Injectable readiness boundary used by the single-threaded relay."""

    def wait(
        self,
        readable: tuple[object, ...],
        writable: tuple[object, ...],
        timeout_seconds: float,
    ) -> tuple[tuple[object, ...], tuple[object, ...]]: ...


class StdlibEgressResolver:
    """Resolve the fixed authority once and return the complete answer set.

    Public-address filtering, canonicalization, answer-count limits, and mixed
    answer rejection remain centralized in ``resolve_egress_target``.
    """

    def __call__(self, host: str, port: int) -> Sequence[str]:
        answers = socket.getaddrinfo(
            host,
            port,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
        return tuple(answer[4][0] for answer in answers)


class StdlibLiteralDialer:
    """Dial one validated numeric address without a second name lookup."""

    def __call__(self, literal_ip: str, port: int, timeout_ms: int) -> object:
        address = ipaddress.ip_address(literal_ip)
        if address.compressed != literal_ip or "%" in literal_ip:
            raise ValueError("literal_ip must be canonical")
        family = socket.AF_INET6 if address.version == 6 else socket.AF_INET
        connection = socket.socket(family, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        try:
            connection.settimeout(timeout_ms / 1_000)
            endpoint: tuple[object, ...]
            if address.version == 6:
                endpoint = (literal_ip, port, 0, 0)
            else:
                endpoint = (literal_ip, port)
            # CPython's family-specific socket path consumes this already
            # validated numeric literal; no getaddrinfo call is made here.
            connection.connect(endpoint)
            return connection
        except BaseException:
            connection.close()
            raise


class SelectorRelayWaiter:
    """One-shot stdlib selector wait with no worker thread."""

    def wait(
        self,
        readable: tuple[object, ...],
        writable: tuple[object, ...],
        timeout_seconds: float,
    ) -> tuple[tuple[object, ...], tuple[object, ...]]:
        masks: dict[object, int] = {}
        for endpoint in readable:
            masks[endpoint] = masks.get(endpoint, 0) | selectors.EVENT_READ
        for endpoint in writable:
            masks[endpoint] = masks.get(endpoint, 0) | selectors.EVENT_WRITE
        with selectors.DefaultSelector() as selector:
            for endpoint, mask in masks.items():
                selector.register(endpoint, mask)
            events = selector.select(timeout_seconds)
        ready_read: list[object] = []
        ready_write: list[object] = []
        for key, mask in events:
            if mask & selectors.EVENT_READ:
                ready_read.append(key.fileobj)
            if mask & selectors.EVENT_WRITE:
                ready_write.append(key.fileobj)
        return tuple(ready_read), tuple(ready_write)


@dataclass(frozen=True, slots=True)
class _HandshakeCapture:
    client_hello: bytes
    surplus: bytes
    last_activity_at: float


class CodexEgressServer:
    """A serial, one-shot process host for the fixed CONNECT policy.

    Ownership of ``listen_socket`` transfers to this object.  ``run`` closes
    it in all terminal paths.  Connections are handled serially, so the fixed
    concurrency ceiling of one cannot be bypassed by the socket host.
    """

    def __init__(
        self,
        listen_socket: object,
        *,
        resolver: EgressResolver | None = None,
        dialer: EgressDialer | None = None,
        policy: EgressPolicy | None = None,
        clock: Callable[[], float] = time.monotonic,
        relay_waiter: RelayWaiter | None = None,
        audit_sink: AuditSink | None = None,
        connection_budget: int = 1,
    ) -> None:
        self._listen_socket = listen_socket
        self._resolver = resolver or StdlibEgressResolver()
        self._dialer = dialer or StdlibLiteralDialer()
        self._policy = policy or EgressPolicy()
        self._clock = clock
        self._relay_waiter = relay_waiter or SelectorRelayWaiter()
        self._audit_sink = audit_sink
        if (
            isinstance(connection_budget, bool)
            or not isinstance(connection_budget, int)
            or connection_budget <= 0
            or connection_budget > self._policy.limits.max_connections
        ):
            raise ValueError("connection_budget must fit the fixed policy")
        self._connection_budget = connection_budget
        self._audit_records: list[EgressAuditRecord] = []
        self._started = False

    @property
    def audit_records(self) -> tuple[EgressAuditRecord, ...]:
        return tuple(self._audit_records)

    def run(self) -> tuple[EgressAuditRecord, ...]:
        """Resolve once, serve the explicit budget, and close the listener."""

        if self._started:
            raise CodexEgressProxyError("egress-server-already-started")
        self._started = True
        try:
            frozen_target = resolve_egress_target(
                self._resolver,
                policy=self._policy,
            )
            _set_timeout(
                self._listen_socket,
                self._policy.limits.wall_timeout_ms / 1_000,
            )
            for sequence in range(1, self._connection_budget + 1):
                try:
                    client, _ = self._listen_socket.accept()
                except TimeoutError:
                    break
                record = self._serve_connection(client, frozen_target, sequence)
                self._audit_records.append(record)
                if self._audit_sink is not None:
                    self._audit_sink(record)
            return self.audit_records
        finally:
            _safe_close(self._listen_socket)

    def _serve_connection(
        self,
        client: object,
        frozen_target: ResolvedEgressTarget,
        sequence: int,
    ) -> EgressAuditRecord:
        started_at = self._clock()
        last_activity_at = started_at
        dialed: DialedEgressTarget | None = None
        upstream: object | None = None
        controller: EgressConnectionController | None = None
        meter: object | None = None
        captured_hello = b""
        record: EgressAuditRecord | None = None
        try:
            request, last_activity_at = self._read_connect_request(
                client,
                started_at=started_at,
                last_activity_at=last_activity_at,
            )
            parse_connect_request(request, policy=self._policy)

            # Exactly one address and one dial attempt.  No retry or fallback
            # address is attempted when this connection fails.
            dialed = dial_egress_target(
                frozen_target,
                self._dialer,
                policy=self._policy,
                address_index=0,
            )
            upstream = dialed.connection
            actual_peer_literal = _verified_peer_literal(
                upstream,
                expected=dialed.selected_literal_ip,
            )

            last_activity_at = self._send_blocking(
                client,
                _CONNECT_ESTABLISHED,
                started_at=started_at,
                last_activity_at=last_activity_at,
            )
            capture = self._read_client_hello(
                client,
                started_at=started_at,
                last_activity_at=last_activity_at,
            )
            captured_hello = capture.client_hello
            attestation = attest_tls_client_hello(
                dialed,
                capture.client_hello,
                actual_peer_literal=actual_peer_literal,
                policy=self._policy,
            )
            controller = EgressConnectionController(dialed, policy=self._policy)
            # The tunnel meter inherits the connection start, so CONNECT,
            # dial, ClientHello and relay share one absolute wall ceiling.
            meter = controller.open(
                now=started_at,
                attestation=attestation,
                last_activity_at=capture.last_activity_at,
            )
            record = self._relay(
                client,
                upstream,
                meter,
                # TCP packetization is not a policy boundary. Bytes coalesced
                # after the exact ClientHello are forwarded only after the
                # peer and SNI attestation, in their original order.
                initial_client_bytes=capture.client_hello + capture.surplus,
                started_at=started_at,
            )
        except Exception as error:  # noqa: BLE001 - raw I/O details terminate here
            failure_code, outcome = _stable_failure(error)
            if controller is not None and meter is not None:
                record = _close_or_recover_meter(
                    meter,
                    controller,
                    now=self._clock(),
                    outcome=outcome,
                    failure_code=failure_code,
                )
            if record is None:
                record = _pre_attestation_failure_record(
                    policy=self._policy,
                    frozen_target=frozen_target,
                    dialed=dialed,
                    sequence=sequence,
                    started_at=started_at,
                    now=self._clock(),
                    captured_hello=captured_hello,
                    outcome=outcome,
                    failure_code=failure_code,
                )
        finally:
            _safe_close(upstream)
            _safe_close(client)
        if record is None:  # defensive fail-closed guard
            raise CodexEgressProxyError("egress-server-audit-missing")
        return _with_connection_sequence(record, sequence)

    def _read_connect_request(
        self,
        client: object,
        *,
        started_at: float,
        last_activity_at: float,
    ) -> tuple[bytes, float]:
        payload = bytearray()
        ceiling = self._policy.limits.max_request_header_bytes
        while b"\r\n\r\n" not in payload:
            if len(payload) >= ceiling:
                raise CodexEgressProxyError("connect-header-byte-limit-exceeded")
            timeout = _remaining_timeout(
                self._policy,
                self._clock(),
                started_at,
                last_activity_at,
            )
            _set_timeout(client, timeout)
            chunk = client.recv(min(_IO_CHUNK_BYTES, ceiling - len(payload)))
            if not isinstance(chunk, bytes):
                raise CodexEgressProxyError("egress-server-recv-invalid")
            if not chunk:
                raise CodexEgressProxyError("connect-client-closed")
            payload.extend(chunk)
            last_activity_at = self._clock()
        return bytes(payload), last_activity_at

    def _send_blocking(
        self,
        endpoint: object,
        payload: bytes,
        *,
        started_at: float,
        last_activity_at: float,
    ) -> float:
        offset = 0
        while offset < len(payload):
            timeout = _remaining_timeout(
                self._policy,
                self._clock(),
                started_at,
                last_activity_at,
            )
            _set_timeout(endpoint, timeout)
            sent = endpoint.send(payload[offset:])
            if isinstance(sent, bool) or not isinstance(sent, int) or sent <= 0:
                raise CodexEgressProxyError("egress-server-send-failed")
            offset += sent
            last_activity_at = self._clock()
        return last_activity_at

    def _read_client_hello(
        self,
        client: object,
        *,
        started_at: float,
        last_activity_at: float,
    ) -> _HandshakeCapture:
        payload = bytearray()
        read_ceiling = CODEX_EGRESS_MAX_CLIENT_HELLO_BYTES + _IO_CHUNK_BYTES
        while True:
            boundary = _client_hello_boundary(payload)
            if boundary is not None:
                return _HandshakeCapture(
                    client_hello=bytes(payload[:boundary]),
                    surplus=bytes(payload[boundary:]),
                    last_activity_at=last_activity_at,
                )
            if len(payload) >= read_ceiling:
                raise CodexEgressProxyError("tls-client-hello-size-invalid")
            timeout = _remaining_timeout(
                self._policy,
                self._clock(),
                started_at,
                last_activity_at,
            )
            _set_timeout(client, timeout)
            chunk = client.recv(min(_IO_CHUNK_BYTES, read_ceiling - len(payload)))
            if not isinstance(chunk, bytes):
                raise CodexEgressProxyError("egress-server-recv-invalid")
            if not chunk:
                raise CodexEgressProxyError("tls-client-hello-client-closed")
            payload.extend(chunk)
            last_activity_at = self._clock()

    def _relay(
        self,
        client: object,
        upstream: object,
        meter: EgressTunnelMeter,
        *,
        initial_client_bytes: bytes,
        started_at: float,
    ) -> EgressAuditRecord:
        client_to_upstream = bytearray()
        upstream_to_client = bytearray()
        client_read_open = True
        upstream_read_open = True
        upstream_write_closed = False
        client_write_closed = False
        client_seen = 0
        upstream_seen = 0
        last_activity_at = started_at

        _set_blocking(client, False)
        _set_blocking(upstream, False)
        if initial_client_bytes:
            observed_at = self._clock()
            meter.observe(
                "client-to-upstream",
                initial_client_bytes,
                now=observed_at,
            )
            last_activity_at = observed_at
            client_seen = len(initial_client_bytes)
            client_to_upstream.extend(initial_client_bytes)

        while True:
            meter.check_time(now=self._clock())
            if (
                not client_read_open
                and not client_to_upstream
                and not upstream_write_closed
            ):
                _shutdown_write(upstream)
                upstream_write_closed = True
            if (
                not upstream_read_open
                and not upstream_to_client
                and not client_write_closed
            ):
                _shutdown_write(client)
                client_write_closed = True
            if (
                not client_read_open
                and not upstream_read_open
                and not client_to_upstream
                and not upstream_to_client
            ):
                return meter.close(outcome="completed", now=self._clock())

            readable: list[object] = []
            if client_read_open and len(client_to_upstream) < _RELAY_BUFFER_BYTES:
                readable.append(client)
            if upstream_read_open and len(upstream_to_client) < _RELAY_BUFFER_BYTES:
                readable.append(upstream)
            writable: list[object] = []
            if client_to_upstream:
                writable.append(upstream)
            if upstream_to_client:
                writable.append(client)
            timeout = _remaining_timeout(
                self._policy,
                self._clock(),
                started_at,
                last_activity_at,
            )
            ready_read, ready_write = self._relay_waiter.wait(
                tuple(readable),
                tuple(writable),
                timeout,
            )

            for endpoint in ready_write:
                if endpoint is upstream and client_to_upstream:
                    sent = _send_nonblocking(upstream, client_to_upstream)
                    if sent:
                        observed_at = self._clock()
                        meter.mark_forward_progress(now=observed_at)
                        last_activity_at = observed_at
                elif endpoint is client and upstream_to_client:
                    sent = _send_nonblocking(client, upstream_to_client)
                    if sent:
                        observed_at = self._clock()
                        meter.mark_forward_progress(now=observed_at)
                        last_activity_at = observed_at

            for endpoint in ready_read:
                if endpoint is client and client_read_open:
                    remaining = (
                        self._policy.limits.max_client_to_upstream_bytes - client_seen
                    )
                    buffer_room = _RELAY_BUFFER_BYTES - len(client_to_upstream)
                    chunk = _recv_nonblocking(
                        client,
                        min(_IO_CHUNK_BYTES, remaining + 1, buffer_room),
                    )
                    if chunk is None:
                        continue
                    if not chunk:
                        observed_at = self._clock()
                        meter.mark_relay_closed(
                            "client-to-upstream",
                            now=observed_at,
                        )
                        last_activity_at = observed_at
                        client_read_open = False
                    else:
                        if len(chunk) > remaining:
                            raise CodexEgressProxyError(
                                "egress-client-byte-limit-exceeded"
                            )
                        observed_at = self._clock()
                        meter.observe(
                            "client-to-upstream",
                            chunk,
                            now=observed_at,
                        )
                        last_activity_at = observed_at
                        client_seen += len(chunk)
                        client_to_upstream.extend(chunk)
                elif endpoint is upstream and upstream_read_open:
                    remaining = (
                        self._policy.limits.max_upstream_to_client_bytes - upstream_seen
                    )
                    buffer_room = _RELAY_BUFFER_BYTES - len(upstream_to_client)
                    chunk = _recv_nonblocking(
                        upstream,
                        min(_IO_CHUNK_BYTES, remaining + 1, buffer_room),
                    )
                    if chunk is None:
                        continue
                    if not chunk:
                        observed_at = self._clock()
                        meter.mark_relay_closed(
                            "upstream-to-client",
                            now=observed_at,
                        )
                        last_activity_at = observed_at
                        upstream_read_open = False
                    else:
                        if len(chunk) > remaining:
                            raise CodexEgressProxyError(
                                "egress-upstream-byte-limit-exceeded"
                            )
                        observed_at = self._clock()
                        meter.observe(
                            "upstream-to-client",
                            chunk,
                            now=observed_at,
                        )
                        last_activity_at = observed_at
                        upstream_seen += len(chunk)
                        upstream_to_client.extend(chunk)


def run_codex_egress_server(
    listen_socket: object,
    *,
    resolver: EgressResolver | None = None,
    dialer: EgressDialer | None = None,
    policy: EgressPolicy | None = None,
    clock: Callable[[], float] = time.monotonic,
    relay_waiter: RelayWaiter | None = None,
    audit_sink: AuditSink | None = None,
    connection_budget: int = 1,
) -> tuple[EgressAuditRecord, ...]:
    """Explicit convenience entry point; never called at module import time."""

    return CodexEgressServer(
        listen_socket,
        resolver=resolver,
        dialer=dialer,
        policy=policy,
        clock=clock,
        relay_waiter=relay_waiter,
        audit_sink=audit_sink,
        connection_budget=connection_budget,
    ).run()


def _client_hello_boundary(payload: bytearray) -> int | None:
    """Return the exact TLS-record boundary containing one ClientHello."""

    offset = 0
    handshake_bytes = bytearray()
    expected_handshake_bytes: int | None = None
    for record_index in range(_MAX_TLS_RECORDS):
        if len(payload) - offset < 5:
            return None
        if payload[offset] != 22 or payload[offset + 1] != 3:
            raise CodexEgressProxyError("tls-client-hello-extra-data-forbidden")
        record_length = int.from_bytes(payload[offset + 3 : offset + 5], "big")
        if record_length <= 0:
            raise CodexEgressProxyError("tls-client-hello-record-invalid")
        record_end = offset + 5 + record_length
        if record_end > CODEX_EGRESS_MAX_CLIENT_HELLO_BYTES:
            raise CodexEgressProxyError("tls-client-hello-size-invalid")
        if record_end > len(payload):
            return None
        handshake_bytes.extend(payload[offset + 5 : record_end])
        if expected_handshake_bytes is None and len(handshake_bytes) >= 4:
            if handshake_bytes[0] != 1:
                raise CodexEgressProxyError("tls-client-hello-handshake-invalid")
            expected_handshake_bytes = 4 + int.from_bytes(handshake_bytes[1:4], "big")
        if (
            expected_handshake_bytes is not None
            and len(handshake_bytes) > expected_handshake_bytes
        ):
            raise CodexEgressProxyError("tls-client-hello-handshake-length-invalid")
        if (
            expected_handshake_bytes is not None
            and len(handshake_bytes) == expected_handshake_bytes
        ):
            return record_end
        offset = record_end
    raise CodexEgressProxyError("tls-client-hello-record-count-exceeded")


def _verified_peer_literal(endpoint: object, *, expected: str) -> str:
    try:
        peer = endpoint.getpeername()
        literal = peer[0]
        address = ipaddress.ip_address(literal)
    except (AttributeError, IndexError, OSError, TypeError, ValueError):
        raise CodexEgressProxyError("egress-actual-peer-invalid") from None
    if "%" in literal or address.compressed != expected:
        raise CodexEgressProxyError("egress-actual-peer-mismatch")
    return address.compressed


def _remaining_timeout(
    policy: EgressPolicy,
    now: float,
    started_at: float,
    last_activity_at: float,
) -> float:
    wall = policy.limits.wall_timeout_ms / 1_000 - (now - started_at)
    idle = policy.limits.idle_timeout_ms / 1_000 - (now - last_activity_at)
    remaining = min(wall, idle)
    if remaining <= 0:
        if wall <= idle:
            raise CodexEgressProxyError("egress-wall-time-limit-exceeded")
        raise CodexEgressProxyError("egress-idle-time-limit-exceeded")
    return remaining


def _stable_failure(error: Exception) -> tuple[str, str]:
    if isinstance(error, CodexEgressProxyError):
        return error.code, "blocked"
    if isinstance(error, (TimeoutError, socket.timeout)):
        return "egress-server-timeout", "blocked"
    if isinstance(error, OSError):
        return "egress-server-io-failed", "failed"
    return "egress-server-internal-failure", "failed"


def _close_or_recover_meter(
    meter: EgressTunnelMeter,
    controller: EgressConnectionController,
    *,
    now: float,
    outcome: str,
    failure_code: str,
) -> EgressAuditRecord:
    existing = controller.audit_records
    if existing:
        return existing[-1]
    try:
        return meter.close(
            outcome=outcome,
            now=now,
            failure_code=failure_code,
        )
    except (CodexEgressProxyError, TypeError, ValueError):
        existing = controller.audit_records
        if existing:
            return existing[-1]
        raise CodexEgressProxyError("egress-server-audit-finalization-failed") from None


def _pre_attestation_failure_record(
    *,
    policy: EgressPolicy,
    frozen_target: ResolvedEgressTarget,
    dialed: DialedEgressTarget | None,
    sequence: int,
    started_at: float,
    now: float,
    captured_hello: bytes,
    outcome: str,
    failure_code: str,
) -> EgressAuditRecord:
    duration_ms = max(0, int((now - started_at) * 1_000))
    return EgressAuditRecord(
        policy_sha256=policy.sha256,
        resolution_sha256=frozen_target.resolution_sha256,
        selected_address_index=(dialed.selected_address_index if dialed else 0),
        client_hello_sha256=hashlib.sha256(captured_hello).hexdigest(),
        connection_sequence=sequence,
        outcome=outcome,
        client_to_upstream_bytes=0,
        upstream_to_client_bytes=0,
        client_to_upstream_sha256=_EMPTY_SHA256,
        upstream_to_client_sha256=_EMPTY_SHA256,
        duration_ms=duration_ms,
        sni_verified=False,
        capture_complete=False,
        failure_code=failure_code,
    )


def _with_connection_sequence(
    record: EgressAuditRecord,
    sequence: int,
) -> EgressAuditRecord:
    if record.connection_sequence == sequence:
        return record
    return EgressAuditRecord(
        policy_sha256=record.policy_sha256,
        resolution_sha256=record.resolution_sha256,
        selected_address_index=record.selected_address_index,
        client_hello_sha256=record.client_hello_sha256,
        connection_sequence=sequence,
        outcome=record.outcome,
        client_to_upstream_bytes=record.client_to_upstream_bytes,
        upstream_to_client_bytes=record.upstream_to_client_bytes,
        client_to_upstream_sha256=record.client_to_upstream_sha256,
        upstream_to_client_sha256=record.upstream_to_client_sha256,
        duration_ms=record.duration_ms,
        sni_verified=record.sni_verified,
        capture_complete=record.capture_complete,
        failure_code=record.failure_code,
    )


def _recv_nonblocking(endpoint: object, size: int) -> bytes | None:
    try:
        payload = endpoint.recv(size)
    except (BlockingIOError, InterruptedError):
        return None
    if not isinstance(payload, bytes):
        raise CodexEgressProxyError("egress-server-recv-invalid")
    return payload


def _send_nonblocking(endpoint: object, pending: bytearray) -> int:
    try:
        sent = endpoint.send(pending)
    except (BlockingIOError, InterruptedError):
        return 0
    if isinstance(sent, bool) or not isinstance(sent, int) or sent <= 0:
        raise CodexEgressProxyError("egress-server-send-failed")
    del pending[:sent]
    return sent


def _set_timeout(endpoint: object, timeout_seconds: float) -> None:
    try:
        endpoint.settimeout(timeout_seconds)
    except AttributeError:
        raise CodexEgressProxyError("egress-server-socket-invalid") from None


def _set_blocking(endpoint: object, value: bool) -> None:
    try:
        endpoint.setblocking(value)
    except AttributeError:
        raise CodexEgressProxyError("egress-server-socket-invalid") from None


def _shutdown_write(endpoint: object) -> None:
    try:
        endpoint.shutdown(socket.SHUT_WR)
    except OSError:
        raise CodexEgressProxyError("egress-server-shutdown-failed") from None


def _safe_close(endpoint: object | None) -> None:
    if endpoint is None:
        return
    try:
        endpoint.close()
    except Exception:  # noqa: BLE001 - cleanup must not mask the audit outcome
        return


__all__ = [
    "CodexEgressServer",
    "RelayWaiter",
    "SelectorRelayWaiter",
    "StdlibEgressResolver",
    "StdlibLiteralDialer",
    "run_codex_egress_server",
]
