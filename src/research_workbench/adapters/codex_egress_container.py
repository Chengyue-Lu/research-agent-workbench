"""Credential-free container entry point for the bounded Codex egress proxy.

This module is an additive Huang Yi-owned runtime adapter.  Importing it does
not inspect the environment, create a socket, resolve a name, or write output.
The only executable mode is the explicit ``--serve`` mode.

The outer Docker topology is intentionally not made live-ready here.  A caller
must freeze and pass the exact internal listener IPv4 address and the one
runtime-container peer IPv4 address.  Every operating-system accepted socket,
including a rejected peer, is handed to the existing server so it produces one
redacted audit record.
"""

from __future__ import annotations

import ipaddress
import os
import re
import socket
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from research_workbench.adapters.codex_egress_proxy import (
    CodexEgressProxyError,
    EgressAuditRecord,
    EgressDialer,
    EgressResolver,
)
from research_workbench.adapters.codex_egress_server import (
    run_codex_egress_server,
)

CODEX_EGRESS_PROXY_CONTAINER_SCHEMA = "rwb-codex-egress-proxy-container/0.1"
CODEX_EGRESS_PROXY_CONTAINER_LIVE_READY = False
CODEX_EGRESS_PROXY_LISTEN_PORT = 3128

_FORBIDDEN_CREDENTIAL_ENV_NAME = re.compile(
    r"(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)",
    flags=re.IGNORECASE,
)
_ALLOWED_ENV_NAMES = frozenset(
    {
        "GPG_KEY",
        "HOME",
        "HOSTNAME",
        "LANG",
        "PATH",
        "PYTHON_SHA256",
        "PYTHON_VERSION",
        "TERM",
        "TZ",
    }
)
_RFC1918_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)


class CodexEgressContainerError(RuntimeError):
    """Stable fail-closed error that never includes arguments or peer data."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class _AcceptedSocket(Protocol):
    def close(self) -> None: ...


class _ListeningSocket(Protocol):
    def accept(self) -> tuple[_AcceptedSocket, object]: ...

    def bind(self, address: tuple[str, int]) -> None: ...

    def close(self) -> None: ...

    def getsockname(self) -> object: ...

    def listen(self, backlog: int) -> None: ...

    def setsockopt(self, level: int, option: int, value: int) -> None: ...

    def settimeout(self, timeout: float) -> None: ...


@dataclass(frozen=True, slots=True)
class CodexEgressContainerConfig:
    """Frozen, non-secret addresses for one single-connection proxy process."""

    listen_ip: str
    runtime_peer_ip: str
    listen_port: int = CODEX_EGRESS_PROXY_LISTEN_PORT
    connection_budget: int = 1

    def __post_init__(self) -> None:
        listen_ip = _canonical_rfc1918_ipv4(self.listen_ip)
        runtime_peer_ip = _canonical_rfc1918_ipv4(self.runtime_peer_ip)
        if listen_ip == runtime_peer_ip:
            raise ValueError("listen_ip and runtime_peer_ip must be distinct")
        if self.listen_port != CODEX_EGRESS_PROXY_LISTEN_PORT:
            raise ValueError("listen_port is fixed to the internal proxy port")
        if self.connection_budget != 1:
            raise ValueError("connection_budget is fixed to one")


class _RejectedRuntimePeer:
    """Closed placeholder that converts a peer mismatch into one server audit."""

    __slots__ = ()

    def settimeout(self, _timeout: float) -> None:
        return None

    def recv(self, _size: int) -> bytes:
        raise CodexEgressProxyError("egress-runtime-peer-mismatch")

    def close(self) -> None:
        return None


class RuntimePeerBoundListener:
    """Expose only the one frozen runtime peer to the existing socket host."""

    __slots__ = ("_listener", "_runtime_peer_ip")

    def __init__(self, listener: _ListeningSocket, runtime_peer_ip: str) -> None:
        self._listener = listener
        self._runtime_peer_ip = _canonical_rfc1918_ipv4(runtime_peer_ip)

    def accept(self) -> tuple[object, tuple[str, int]]:
        client, raw_peer = self._listener.accept()
        if _accepted_peer_ip(raw_peer) == self._runtime_peer_ip:
            return client, ("runtime-peer", 0)
        _safe_close(client)
        return _RejectedRuntimePeer(), ("rejected-peer", 0)

    def settimeout(self, timeout: float) -> None:
        self._listener.settimeout(timeout)

    def close(self) -> None:
        self._listener.close()


class JsonlAuditSink:
    """Write one canonical ASCII JSONL payload for each unique audit sequence."""

    __slots__ = ("_seen", "_write")

    def __init__(self, write: Callable[[bytes], int]) -> None:
        self._write = write
        self._seen: set[int] = set()

    @property
    def record_count(self) -> int:
        return len(self._seen)

    def __call__(self, record: EgressAuditRecord) -> None:
        if not isinstance(record, EgressAuditRecord):
            raise CodexEgressContainerError("proxy-audit-record-invalid")
        if record.connection_sequence in self._seen:
            raise CodexEgressContainerError("proxy-audit-sequence-duplicate")
        payload = f"{record.to_json()}\n".encode("ascii", errors="strict")
        try:
            written = self._write(payload)
        except Exception:  # noqa: BLE001 - output details must not escape
            raise CodexEgressContainerError("proxy-audit-write-failed") from None
        if isinstance(written, bool) or written != len(payload):
            raise CodexEgressContainerError("proxy-audit-write-incomplete")
        self._seen.add(record.connection_sequence)


def parse_container_arguments(argv: Sequence[str]) -> CodexEgressContainerConfig:
    """Parse the one exact explicit mode without argparse echoing raw values."""

    if isinstance(argv, (str, bytes)) or not isinstance(argv, Sequence):
        raise CodexEgressContainerError("proxy-arguments-invalid")
    if not argv or argv[0] != "--serve":
        raise CodexEgressContainerError("proxy-mode-invalid")
    values: dict[str, str] = {}
    index = 1
    allowed = {"--listen-ip": "listen_ip", "--runtime-peer-ip": "runtime_peer_ip"}
    while index < len(argv):
        flag = argv[index]
        field_name = allowed.get(flag)
        if field_name is None or field_name in values or index + 1 >= len(argv):
            raise CodexEgressContainerError("proxy-arguments-invalid")
        value = argv[index + 1]
        if not isinstance(value, str) or not value:
            raise CodexEgressContainerError("proxy-arguments-invalid")
        values[field_name] = value
        index += 2
    if set(values) != {"listen_ip", "runtime_peer_ip"}:
        raise CodexEgressContainerError("proxy-arguments-invalid")
    try:
        return CodexEgressContainerConfig(**values)
    except (TypeError, ValueError):
        raise CodexEgressContainerError("proxy-address-policy-invalid") from None


def validate_credential_free_environment(environ: Mapping[str, str]) -> None:
    """Accept only the frozen non-secret base-image environment names."""

    if not isinstance(environ, Mapping):
        raise CodexEgressContainerError("proxy-environment-invalid")
    for name, value in environ.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise CodexEgressContainerError("proxy-environment-invalid")
        if name not in _ALLOWED_ENV_NAMES or _FORBIDDEN_CREDENTIAL_ENV_NAME.search(
            name
        ):
            raise CodexEgressContainerError("proxy-credential-environment-forbidden")


def create_bound_listener(
    config: CodexEgressContainerConfig,
    *,
    socket_factory: Callable[[int, int, int], _ListeningSocket] = socket.socket,
) -> RuntimePeerBoundListener:
    """Bind only the frozen internal address and verify the resulting endpoint."""

    if not isinstance(config, CodexEgressContainerConfig):
        raise TypeError("config must be CodexEgressContainerConfig")
    listener: _ListeningSocket | None = None
    try:
        listener = socket_factory(
            socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP
        )
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        listener.bind((config.listen_ip, config.listen_port))
        listener.listen(1)
        endpoint = listener.getsockname()
        if _bound_endpoint(endpoint) != (config.listen_ip, config.listen_port):
            raise CodexEgressContainerError("proxy-listener-bind-attestation-failed")
        return RuntimePeerBoundListener(listener, config.runtime_peer_ip)
    except CodexEgressContainerError:
        _safe_close(listener)
        raise
    except Exception:  # noqa: BLE001 - bind details must not escape
        _safe_close(listener)
        raise CodexEgressContainerError("proxy-listener-create-failed") from None


def serve_codex_egress_proxy(
    config: CodexEgressContainerConfig,
    *,
    environ: Mapping[str, str],
    audit_write: Callable[[bytes], int],
    socket_factory: Callable[[int, int, int], _ListeningSocket] = socket.socket,
    resolver: EgressResolver | None = None,
    dialer: EgressDialer | None = None,
) -> tuple[EgressAuditRecord, ...]:
    """Explicitly serve one accepted socket and emit exactly its one audit."""

    validate_credential_free_environment(environ)
    if resolver is None or dialer is None:
        raise CodexEgressContainerError("proxy-live-network-boundary-unavailable")
    listener = create_bound_listener(config, socket_factory=socket_factory)
    sink = JsonlAuditSink(audit_write)
    records = run_codex_egress_server(
        listener,
        resolver=resolver,
        dialer=dialer,
        audit_sink=sink,
        connection_budget=config.connection_budget,
    )
    if (
        len(records) != 1
        or sink.record_count != 1
        or records[0].connection_sequence != 1
    ):
        raise CodexEgressContainerError("proxy-audit-exactly-one-unverified")
    return records


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    audit_write: Callable[[bytes], int] | None = None,
    error_write: Callable[[bytes], int] | None = None,
    serve: Callable[..., tuple[EgressAuditRecord, ...]] | None = None,
) -> int:
    """Run the explicit container mode and return a stable process exit code."""

    # This image is a buildable, inspectable contract only.  The production
    # entrypoint must remain inert until a versioned topology freezes the two
    # internal addresses and a supervisor captures the exactly-one audit.
    # Keep this check before argv, environment, socket, resolver, or serve is
    # touched.  Unit tests exercise ``serve_codex_egress_proxy`` directly.
    if not CODEX_EGRESS_PROXY_CONTAINER_LIVE_READY:
        active_error_write = (
            (lambda payload: os.write(2, payload))
            if error_write is None
            else error_write
        )
        _write_stable_error(active_error_write, "proxy-live-not-ready")
        return 2

    active_argv = tuple(sys.argv[1:] if argv is None else argv)
    active_environ = os.environ if environ is None else environ
    active_audit_write = (
        (lambda payload: os.write(1, payload)) if audit_write is None else audit_write
    )
    active_error_write = (
        (lambda payload: os.write(2, payload)) if error_write is None else error_write
    )
    active_serve = serve_codex_egress_proxy if serve is None else serve
    try:
        config = parse_container_arguments(active_argv)
        records = active_serve(
            config,
            environ=active_environ,
            audit_write=active_audit_write,
        )
        if len(records) != 1:
            raise CodexEgressContainerError("proxy-audit-exactly-one-unverified")
        record = records[0]
        return 0 if record.outcome == "completed" and record.capture_complete else 1
    except (CodexEgressContainerError, CodexEgressProxyError) as error:
        _write_stable_error(active_error_write, error.code)
        return 1
    except Exception:  # noqa: BLE001 - no raw error crosses the process boundary
        _write_stable_error(active_error_write, "proxy-container-internal-failure")
        return 1


def _canonical_rfc1918_ipv4(value: str) -> str:
    if not isinstance(value, str) or not value or "%" in value:
        raise ValueError("address must be a canonical RFC1918 IPv4 literal")
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        raise ValueError("address must be a canonical RFC1918 IPv4 literal") from None
    if not isinstance(address, ipaddress.IPv4Address) or address.compressed != value:
        raise ValueError("address must be a canonical RFC1918 IPv4 literal")
    if not any(address in network for network in _RFC1918_NETWORKS):
        raise ValueError("address must be a canonical RFC1918 IPv4 literal")
    return address.compressed


def _accepted_peer_ip(raw_peer: object) -> str | None:
    if not isinstance(raw_peer, tuple) or len(raw_peer) != 2:
        return None
    raw_ip, raw_port = raw_peer
    if (
        not isinstance(raw_ip, str)
        or isinstance(raw_port, bool)
        or not isinstance(raw_port, int)
        or not 0 < raw_port <= 65_535
    ):
        return None
    try:
        return _canonical_rfc1918_ipv4(raw_ip)
    except ValueError:
        return None


def _bound_endpoint(raw_endpoint: object) -> tuple[str, int] | None:
    if not isinstance(raw_endpoint, tuple) or len(raw_endpoint) != 2:
        return None
    raw_ip, raw_port = raw_endpoint
    if (
        not isinstance(raw_ip, str)
        or isinstance(raw_port, bool)
        or not isinstance(raw_port, int)
    ):
        return None
    try:
        return _canonical_rfc1918_ipv4(raw_ip), raw_port
    except ValueError:
        return None


def _safe_close(endpoint: object | None) -> None:
    if endpoint is None:
        return
    try:
        endpoint.close()
    except Exception:  # noqa: BLE001 - cleanup is best-effort and non-reporting
        return


def _write_stable_error(write: Callable[[bytes], int], code: str) -> None:
    payload = f"{code}\n".encode("ascii", errors="strict")
    try:
        write(payload)
    except Exception:  # noqa: BLE001 - no recursive diagnostics on stderr failure
        return


if __name__ == "__main__":
    raise SystemExit(main())
