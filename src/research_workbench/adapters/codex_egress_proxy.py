"""Fail-closed transport contract for a future Codex Coding Plan proxy.

This policy module deliberately contains no automatic network action, Docker
integration, or credential handling.  It freezes the narrow policy and parsing
boundaries used by the separate, explicitly started socket host:

* one exact CONNECT authority (``open.bigmodel.cn:443``);
* a host-side, injectable resolver whose complete answer set must be public;
* a dialer that receives a validated literal IP rather than a hostname;
* mandatory exact TLS ClientHello SNI verification without terminating TLS; and
* bounded, redacted tunnel accounting over opaque TLS ciphertext.

It is a Huang Yi-owned API/runtime adapter slice.  It is not a ModelProvider,
does not make the Coding Plan runtime live-ready, and does not create or mutate
Task, Mode, Skill, Trace, Handoff, Receipt, or Main State objects.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import re
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

CODEX_EGRESS_POLICY_SCHEMA = "rwb-codex-egress-policy/0.1"
CODEX_EGRESS_AUDIT_SCHEMA = "rwb-codex-egress-audit/0.1"
CODEX_EGRESS_HOST = "open.bigmodel.cn"
CODEX_EGRESS_PORT = 443
CODEX_EGRESS_AUTHORITY = f"{CODEX_EGRESS_HOST}:{CODEX_EGRESS_PORT}"
CODEX_EGRESS_DESTINATION_ID = "zhipu-coding-plan"
CODEX_EGRESS_ATTESTATION_LIMITATIONS = (
    "CONNECT and visible SNI constrain transport destination, not encrypted HTTP path.",
    "The proxy cannot inspect encrypted Host or HTTP/2 :authority without TLS termination.",
    "Ciphertext hashes prove capture integrity only; they do not attest request semantics.",
    "The explicit socket host is not packaged, supervised, or wired to Docker/netfilter live execution.",
    "A successful tunnel does not attest the serving provider, actual model, cost, or research correctness.",
)

CODEX_EGRESS_MAX_CONNECTIONS = 4
CODEX_EGRESS_MAX_CONCURRENT_CONNECTIONS = 1
CODEX_EGRESS_MAX_REQUEST_HEADER_BYTES = 8_192
CODEX_EGRESS_MAX_REQUEST_LINE_BYTES = 2_048
CODEX_EGRESS_MAX_HEADER_COUNT = 16
CODEX_EGRESS_MAX_RESOLVED_ADDRESSES = 16
CODEX_EGRESS_MAX_CLIENT_TO_UPSTREAM_BYTES = 1_048_576
CODEX_EGRESS_MAX_UPSTREAM_TO_CLIENT_BYTES = 4_194_304
CODEX_EGRESS_MAX_CONNECT_TIMEOUT_MS = 5_000
CODEX_EGRESS_MAX_IDLE_TIMEOUT_MS = 35_000
CODEX_EGRESS_MAX_WALL_TIMEOUT_MS = 130_000
CODEX_EGRESS_MAX_CLIENT_HELLO_BYTES = 65_535

_HTTP_TOKEN = re.compile(rb"[!#$%&'*+\-.^_`|~0-9A-Za-z]+\Z")
_ALLOWED_CONNECT_HEADERS = frozenset(
    {"host", "connection", "proxy-connection", "user-agent"}
)
_FORBIDDEN_CONNECT_HEADERS = frozenset(
    {"content-length", "transfer-encoding", "proxy-authorization"}
)
_AUDIT_OUTCOMES = frozenset(
    {"completed", "client-closed", "upstream-closed", "blocked", "failed"}
)


class CodexEgressProxyError(RuntimeError):
    """Stable fail-closed error that never includes request or tunnel bytes."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class EgressLimits:
    """Hard ceilings for one short-lived Coding Plan proxy process."""

    max_connections: int = 2
    max_concurrent_connections: int = 1
    max_request_header_bytes: int = CODEX_EGRESS_MAX_REQUEST_HEADER_BYTES
    max_request_line_bytes: int = CODEX_EGRESS_MAX_REQUEST_LINE_BYTES
    max_header_count: int = CODEX_EGRESS_MAX_HEADER_COUNT
    max_resolved_addresses: int = CODEX_EGRESS_MAX_RESOLVED_ADDRESSES
    max_client_to_upstream_bytes: int = 262_144
    max_upstream_to_client_bytes: int = 1_048_576
    connect_timeout_ms: int = CODEX_EGRESS_MAX_CONNECT_TIMEOUT_MS
    idle_timeout_ms: int = 30_000
    wall_timeout_ms: int = 120_000

    def __post_init__(self) -> None:
        _bounded_positive_int(
            "max_connections", self.max_connections, CODEX_EGRESS_MAX_CONNECTIONS
        )
        _bounded_positive_int(
            "max_concurrent_connections",
            self.max_concurrent_connections,
            CODEX_EGRESS_MAX_CONCURRENT_CONNECTIONS,
        )
        if self.max_concurrent_connections > self.max_connections:
            raise ValueError(
                "max_concurrent_connections must not exceed max_connections"
            )
        _bounded_positive_int(
            "max_request_header_bytes",
            self.max_request_header_bytes,
            CODEX_EGRESS_MAX_REQUEST_HEADER_BYTES,
        )
        _bounded_positive_int(
            "max_request_line_bytes",
            self.max_request_line_bytes,
            CODEX_EGRESS_MAX_REQUEST_LINE_BYTES,
        )
        _bounded_positive_int(
            "max_header_count", self.max_header_count, CODEX_EGRESS_MAX_HEADER_COUNT
        )
        _bounded_positive_int(
            "max_resolved_addresses",
            self.max_resolved_addresses,
            CODEX_EGRESS_MAX_RESOLVED_ADDRESSES,
        )
        _bounded_positive_int(
            "max_client_to_upstream_bytes",
            self.max_client_to_upstream_bytes,
            CODEX_EGRESS_MAX_CLIENT_TO_UPSTREAM_BYTES,
        )
        _bounded_positive_int(
            "max_upstream_to_client_bytes",
            self.max_upstream_to_client_bytes,
            CODEX_EGRESS_MAX_UPSTREAM_TO_CLIENT_BYTES,
        )
        _bounded_positive_int(
            "connect_timeout_ms",
            self.connect_timeout_ms,
            CODEX_EGRESS_MAX_CONNECT_TIMEOUT_MS,
        )
        _bounded_positive_int(
            "idle_timeout_ms",
            self.idle_timeout_ms,
            CODEX_EGRESS_MAX_IDLE_TIMEOUT_MS,
        )
        _bounded_positive_int(
            "wall_timeout_ms",
            self.wall_timeout_ms,
            CODEX_EGRESS_MAX_WALL_TIMEOUT_MS,
        )

    def to_mapping(self) -> dict[str, int]:
        """Return the canonical JSON-ready limits projection."""

        return {
            "connect_timeout_ms": self.connect_timeout_ms,
            "idle_timeout_ms": self.idle_timeout_ms,
            "max_client_to_upstream_bytes": self.max_client_to_upstream_bytes,
            "max_concurrent_connections": self.max_concurrent_connections,
            "max_connections": self.max_connections,
            "max_header_count": self.max_header_count,
            "max_request_header_bytes": self.max_request_header_bytes,
            "max_request_line_bytes": self.max_request_line_bytes,
            "max_resolved_addresses": self.max_resolved_addresses,
            "max_upstream_to_client_bytes": self.max_upstream_to_client_bytes,
            "wall_timeout_ms": self.wall_timeout_ms,
        }


@dataclass(frozen=True, slots=True)
class EgressPolicy:
    """Immutable single-destination policy; arbitrary hosts are not supported."""

    authority: str = CODEX_EGRESS_AUTHORITY
    destination_id: str = CODEX_EGRESS_DESTINATION_ID
    require_tls_sni: bool = True
    limits: EgressLimits = field(default_factory=EgressLimits)

    def __post_init__(self) -> None:
        if self.authority != CODEX_EGRESS_AUTHORITY:
            raise ValueError("authority must be the fixed Coding Plan authority")
        if self.destination_id != CODEX_EGRESS_DESTINATION_ID:
            raise ValueError("destination_id must be the fixed redacted identifier")
        if self.require_tls_sni is not True:
            raise ValueError("require_tls_sni is fixed true for production policy")
        if not isinstance(self.limits, EgressLimits):
            raise TypeError("limits must be EgressLimits")

    def to_mapping(self) -> dict[str, object]:
        """Return the complete canonical policy projection."""

        return {
            "authority": self.authority,
            "destination_id": self.destination_id,
            "limits": self.limits.to_mapping(),
            "require_tls_sni": self.require_tls_sni,
            "schema": CODEX_EGRESS_POLICY_SCHEMA,
        }

    def canonical_bytes(self) -> bytes:
        """Serialize deterministically without platform-specific whitespace."""

        return json.dumps(
            self.to_mapping(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")

    @property
    def sha256(self) -> str:
        """Return the lowercase SHA-256 of the canonical policy."""

        return hashlib.sha256(self.canonical_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class ConnectRequest:
    """Validated CONNECT metadata; raw headers are intentionally discarded."""

    authority: str
    header_count: int
    consumed_bytes: int


class EgressResolver(Protocol):
    """Injectable control-plane resolver; production use requires review."""

    def __call__(self, host: str, port: int) -> Sequence[str]: ...


class EgressDialer(Protocol):
    """Dial only a validated literal address; no hostname parameter exists."""

    def __call__(
        self,
        literal_ip: str,
        port: int,
        timeout_ms: int,
    ) -> object: ...


@dataclass(frozen=True, slots=True)
class ResolvedEgressTarget:
    """Canonical, public-only result from exactly one resolver invocation."""

    policy_sha256: str
    literal_ips: tuple[str, ...]
    resolution_sha256: str

    def __post_init__(self) -> None:
        _validate_sha256("policy_sha256", self.policy_sha256)
        _validate_sha256("resolution_sha256", self.resolution_sha256)
        if not isinstance(self.literal_ips, tuple) or not self.literal_ips:
            raise ValueError("literal_ips must be a non-empty canonical tuple")
        canonical: list[str] = []
        for value in self.literal_ips:
            if not isinstance(value, str) or "%" in value:
                raise ValueError("literal_ips must contain global address literals")
            try:
                address = ipaddress.ip_address(value)
            except ValueError:
                raise ValueError(
                    "literal_ips must contain global address literals"
                ) from None
            if (
                isinstance(address, ipaddress.IPv6Address)
                and address.ipv4_mapped is not None
            ) or not _is_public_address(address):
                raise ValueError("literal_ips must contain global address literals")
            canonical.append(address.compressed)
        expected = tuple(sorted(set(canonical), key=_address_sort_key))
        if self.literal_ips != expected:
            raise ValueError("literal_ips must be unique and canonically sorted")
        if self.resolution_sha256 != _resolution_sha256(
            self.policy_sha256, self.literal_ips
        ):
            raise ValueError("resolution_sha256 must bind the frozen addresses")


@dataclass(frozen=True, slots=True, init=False)
class DialedEgressTarget:
    """Opaque dial result plus non-sensitive attestation references."""

    connection: object
    policy_sha256: str
    resolution_sha256: str
    selected_address_index: int
    selected_literal_ip: str

    def __init__(
        self,
        *,
        connection: object,
        policy_sha256: str,
        resolution_sha256: str,
        selected_address_index: int,
        selected_literal_ip: str,
        _issuer: object,
    ) -> None:
        if _issuer is not _DIAL_TARGET_ISSUER:
            raise TypeError("dialed target must be issued by the bounded dialer")
        _validate_sha256("policy_sha256", policy_sha256)
        _validate_sha256("resolution_sha256", resolution_sha256)
        _non_negative_int("selected_address_index", selected_address_index)
        canonical_literal = _canonical_public_literal(selected_literal_ip)
        object.__setattr__(self, "connection", connection)
        object.__setattr__(self, "policy_sha256", policy_sha256)
        object.__setattr__(self, "resolution_sha256", resolution_sha256)
        object.__setattr__(self, "selected_address_index", selected_address_index)
        object.__setattr__(self, "selected_literal_ip", canonical_literal)


_DIAL_TARGET_ISSUER = object()
_ATTESTATION_ISSUER = object()


@dataclass(frozen=True, slots=True, init=False)
class TlsClientHelloAttestation:
    """Unforgeable-by-public-API binding from dial result to visible TLS SNI."""

    dialed_target: DialedEgressTarget
    policy_sha256: str
    resolution_sha256: str
    selected_address_index: int
    actual_peer_literal: str
    client_hello_sha256: str
    server_name: str
    record_count: int

    def __init__(
        self,
        *,
        dialed_target: DialedEgressTarget,
        actual_peer_literal: str,
        client_hello_sha256: str,
        server_name: str,
        record_count: int,
        _issuer: object,
    ) -> None:
        if _issuer is not _ATTESTATION_ISSUER:
            raise TypeError("TLS attestation must be issued by the validator")
        object.__setattr__(self, "dialed_target", dialed_target)
        object.__setattr__(self, "policy_sha256", dialed_target.policy_sha256)
        object.__setattr__(self, "resolution_sha256", dialed_target.resolution_sha256)
        object.__setattr__(
            self, "selected_address_index", dialed_target.selected_address_index
        )
        object.__setattr__(self, "actual_peer_literal", actual_peer_literal)
        object.__setattr__(self, "client_hello_sha256", client_hello_sha256)
        object.__setattr__(self, "server_name", server_name)
        object.__setattr__(self, "record_count", record_count)


def parse_connect_request(
    payload: bytes,
    *,
    policy: EgressPolicy | None = None,
) -> ConnectRequest:
    """Parse one strict HTTP/1.1 CONNECT header block.

    The function accepts no request body or optimistic TLS bytes.  A live
    server must first read a bounded header block, return 200, and only then
    accept a separately bounded ClientHello.
    """

    active_policy = policy or EgressPolicy()
    limits = active_policy.limits
    if not isinstance(payload, bytes):
        raise CodexEgressProxyError("connect-request-not-bytes")
    if not payload:
        raise CodexEgressProxyError("connect-request-empty")
    if len(payload) > limits.max_request_header_bytes:
        raise CodexEgressProxyError("connect-header-byte-limit-exceeded")
    terminator = payload.find(b"\r\n\r\n")
    if terminator < 0:
        raise CodexEgressProxyError("connect-header-incomplete")
    if terminator != len(payload) - 4:
        raise CodexEgressProxyError("connect-pipelined-data-forbidden")
    if b"\x00" in payload:
        raise CodexEgressProxyError("connect-header-control-character")

    lines = payload[:-4].split(b"\r\n")
    if not lines or not lines[0]:
        raise CodexEgressProxyError("connect-request-line-invalid")
    if any(b"\n" in line or b"\r" in line for line in lines):
        raise CodexEgressProxyError("connect-line-ending-invalid")
    if len(lines[0]) > limits.max_request_line_bytes:
        raise CodexEgressProxyError("connect-request-line-limit-exceeded")

    request_line = lines[0]
    expected = f"CONNECT {active_policy.authority} HTTP/1.1".encode("ascii")
    if request_line != expected:
        raise CodexEgressProxyError("connect-authority-not-allowed")

    raw_headers = lines[1:]
    if len(raw_headers) > limits.max_header_count:
        raise CodexEgressProxyError("connect-header-count-exceeded")
    seen: set[str] = set()
    host_value: str | None = None
    for line in raw_headers:
        if not line or line[:1] in (b" ", b"\t"):
            raise CodexEgressProxyError("connect-header-folding-forbidden")
        name_bytes, separator, value_bytes = line.partition(b":")
        if not separator or _HTTP_TOKEN.fullmatch(name_bytes) is None:
            raise CodexEgressProxyError("connect-header-name-invalid")
        try:
            name = name_bytes.decode("ascii").casefold()
            value = value_bytes.decode("ascii")
        except UnicodeError:
            raise CodexEgressProxyError("connect-header-not-ascii") from None
        if name in seen:
            raise CodexEgressProxyError("connect-header-duplicate")
        seen.add(name)
        if name in _FORBIDDEN_CONNECT_HEADERS:
            raise CodexEgressProxyError(f"connect-{name}-forbidden")
        if name not in _ALLOWED_CONNECT_HEADERS:
            raise CodexEgressProxyError("connect-header-not-allowed")
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise CodexEgressProxyError("connect-header-control-character")
        normalized_value = value.strip(" \t")
        if not normalized_value:
            raise CodexEgressProxyError("connect-header-value-empty")
        if name == "host":
            host_value = normalized_value

    if host_value is None:
        raise CodexEgressProxyError("connect-host-missing")
    if host_value != active_policy.authority:
        raise CodexEgressProxyError("connect-host-mismatch")
    return ConnectRequest(
        authority=active_policy.authority,
        header_count=len(raw_headers),
        consumed_bytes=len(payload),
    )


def resolve_egress_target(
    resolver: EgressResolver,
    *,
    policy: EgressPolicy | None = None,
) -> ResolvedEgressTarget:
    """Resolve once, reject unsafe/mixed answers, and freeze literal IPs."""

    active_policy = policy or EgressPolicy()
    try:
        answers = resolver(CODEX_EGRESS_HOST, CODEX_EGRESS_PORT)
    except Exception:  # noqa: BLE001 - raw resolver details must cross no boundary
        raise CodexEgressProxyError("egress-resolution-failed") from None
    if isinstance(answers, (str, bytes)) or not isinstance(answers, Sequence):
        raise CodexEgressProxyError("egress-resolution-invalid")
    if not answers:
        raise CodexEgressProxyError("egress-resolution-empty")
    if len(answers) > active_policy.limits.max_resolved_addresses:
        raise CodexEgressProxyError("egress-resolution-address-limit-exceeded")

    canonical: set[str] = set()
    unsafe_seen = False
    for answer in answers:
        if not isinstance(answer, str) or not answer or "%" in answer:
            unsafe_seen = True
            continue
        try:
            address = ipaddress.ip_address(answer)
        except ValueError:
            unsafe_seen = True
            continue
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            unsafe_seen = True
            continue
        if not _is_public_address(address):
            unsafe_seen = True
            continue
        canonical.add(address.compressed)

    if unsafe_seen:
        raise CodexEgressProxyError("egress-resolution-mixed-or-non-global")
    if not canonical:
        raise CodexEgressProxyError("egress-resolution-no-global-address")
    literal_ips = tuple(sorted(canonical, key=_address_sort_key))
    return ResolvedEgressTarget(
        policy_sha256=active_policy.sha256,
        literal_ips=literal_ips,
        resolution_sha256=_resolution_sha256(active_policy.sha256, literal_ips),
    )


def dial_egress_target(
    target: ResolvedEgressTarget,
    dialer: EgressDialer,
    *,
    policy: EgressPolicy | None = None,
    address_index: int = 0,
) -> DialedEgressTarget:
    """Dial one frozen literal IP exactly once; never pass a hostname."""

    active_policy = policy or EgressPolicy()
    if target.policy_sha256 != active_policy.sha256:
        raise CodexEgressProxyError("egress-policy-hash-mismatch")
    if (
        isinstance(address_index, bool)
        or not isinstance(address_index, int)
        or address_index < 0
        or address_index >= len(target.literal_ips)
    ):
        raise CodexEgressProxyError("egress-address-index-invalid")
    literal_ip = target.literal_ips[address_index]
    try:
        address = ipaddress.ip_address(literal_ip)
    except ValueError:
        raise CodexEgressProxyError("egress-frozen-address-invalid") from None
    if not _is_public_address(address):
        raise CodexEgressProxyError("egress-frozen-address-invalid")
    try:
        connection = dialer(
            address.compressed,
            CODEX_EGRESS_PORT,
            active_policy.limits.connect_timeout_ms,
        )
    except Exception:  # noqa: BLE001 - raw socket details must cross no boundary
        raise CodexEgressProxyError("egress-dial-failed") from None
    return DialedEgressTarget(
        connection=connection,
        policy_sha256=target.policy_sha256,
        resolution_sha256=target.resolution_sha256,
        selected_address_index=address_index,
        selected_literal_ip=address.compressed,
        _issuer=_DIAL_TARGET_ISSUER,
    )


def validate_tls_client_hello_sni(
    payload: bytes,
    *,
    policy: EgressPolicy | None = None,
) -> bool:
    """Require one bounded TLS ClientHello with one exact visible SNI.

    This performs metadata inspection only.  The caller must forward the exact
    original bytes after validation; this module never decrypts TLS.
    """

    active_policy = policy or EgressPolicy()
    if active_policy.require_tls_sni is not True:
        raise CodexEgressProxyError("egress-sni-verification-required")
    server_name, _ = _parse_tls_client_hello(payload)
    if server_name != CODEX_EGRESS_HOST:
        raise CodexEgressProxyError("tls-client-hello-sni-not-allowed")
    return True


def attest_tls_client_hello(
    dialed_target: DialedEgressTarget,
    payload: bytes,
    *,
    actual_peer_literal: str,
    policy: EgressPolicy | None = None,
) -> TlsClientHelloAttestation:
    """Bind validated ClientHello bytes to the exact selected and actual peer."""

    active_policy = policy or EgressPolicy()
    if not isinstance(dialed_target, DialedEgressTarget):
        raise TypeError("dialed_target must be DialedEgressTarget")
    if dialed_target.policy_sha256 != active_policy.sha256:
        raise CodexEgressProxyError("egress-policy-hash-mismatch")
    canonical_peer = _canonical_public_literal(actual_peer_literal)
    if canonical_peer != dialed_target.selected_literal_ip:
        raise CodexEgressProxyError("egress-actual-peer-mismatch")
    server_name, record_count = _parse_tls_client_hello(payload)
    if server_name != CODEX_EGRESS_HOST:
        raise CodexEgressProxyError("tls-client-hello-sni-not-allowed")
    return TlsClientHelloAttestation(
        dialed_target=dialed_target,
        actual_peer_literal=canonical_peer,
        client_hello_sha256=hashlib.sha256(payload).hexdigest(),
        server_name=server_name,
        record_count=record_count,
        _issuer=_ATTESTATION_ISSUER,
    )


def _parse_tls_client_hello(payload: bytes) -> tuple[str, int]:
    """Assemble one ClientHello from at most three bounded handshake records."""

    if not isinstance(payload, bytes):
        raise CodexEgressProxyError("tls-client-hello-not-bytes")
    if not payload or len(payload) > CODEX_EGRESS_MAX_CLIENT_HELLO_BYTES:
        raise CodexEgressProxyError("tls-client-hello-size-invalid")

    offset = 0
    fragments: list[bytes] = []
    while offset < len(payload):
        if len(fragments) >= 3:
            raise CodexEgressProxyError("tls-client-hello-record-count-exceeded")
        if len(payload) - offset < 5:
            raise CodexEgressProxyError("tls-client-hello-record-length-invalid")
        content_type = payload[offset]
        major = payload[offset + 1]
        record_length = int.from_bytes(payload[offset + 3 : offset + 5], "big")
        record_end = offset + 5 + record_length
        if record_end > len(payload):
            raise CodexEgressProxyError("tls-client-hello-record-length-invalid")
        if content_type != 22 or major != 3:
            raise CodexEgressProxyError("tls-client-hello-extra-data-forbidden")
        if record_length == 0:
            raise CodexEgressProxyError("tls-client-hello-record-invalid")
        fragments.append(payload[offset + 5 : record_end])
        offset = record_end

    handshake = b"".join(fragments)
    if len(handshake) < 4 or handshake[0] != 1:
        raise CodexEgressProxyError("tls-client-hello-handshake-invalid")
    handshake_length = int.from_bytes(handshake[1:4], "big")
    if handshake_length != len(handshake) - 4:
        raise CodexEgressProxyError("tls-client-hello-handshake-length-invalid")

    hello = memoryview(handshake)[4:]
    offset = 0
    offset = _consume(hello, offset, 2 + 32, "tls-client-hello-truncated")
    session_length, offset = _read_u8(hello, offset, "tls-client-hello-truncated")
    offset = _consume(hello, offset, session_length, "tls-client-hello-truncated")
    cipher_length, offset = _read_u16(hello, offset, "tls-client-hello-truncated")
    if cipher_length < 2 or cipher_length % 2:
        raise CodexEgressProxyError("tls-client-hello-ciphers-invalid")
    offset = _consume(hello, offset, cipher_length, "tls-client-hello-truncated")
    compression_length, offset = _read_u8(hello, offset, "tls-client-hello-truncated")
    if compression_length < 1:
        raise CodexEgressProxyError("tls-client-hello-compression-invalid")
    offset = _consume(hello, offset, compression_length, "tls-client-hello-truncated")
    extensions_length, offset = _read_u16(
        hello, offset, "tls-client-hello-extensions-missing"
    )
    if extensions_length != len(hello) - offset:
        raise CodexEgressProxyError("tls-client-hello-extensions-length-invalid")
    extensions_end = offset + extensions_length
    server_name: str | None = None
    while offset < extensions_end:
        extension_type, offset = _read_u16(
            hello, offset, "tls-client-hello-extension-truncated"
        )
        extension_length, offset = _read_u16(
            hello, offset, "tls-client-hello-extension-truncated"
        )
        extension_end = _consume(
            hello,
            offset,
            extension_length,
            "tls-client-hello-extension-truncated",
        )
        if extension_type == 0:
            if server_name is not None:
                raise CodexEgressProxyError("tls-client-hello-sni-duplicate")
            server_name = _parse_server_name_extension(hello[offset:extension_end])
        offset = extension_end
    if offset != extensions_end:
        raise CodexEgressProxyError("tls-client-hello-extension-truncated")
    if server_name is None:
        raise CodexEgressProxyError("tls-client-hello-sni-missing")
    return server_name, len(fragments)


@dataclass(frozen=True, slots=True)
class EgressAuditRecord:
    """Redacted accounting record; it cannot contain headers or tunnel bytes."""

    policy_sha256: str
    resolution_sha256: str
    selected_address_index: int
    client_hello_sha256: str
    connection_sequence: int
    outcome: str
    client_to_upstream_bytes: int
    upstream_to_client_bytes: int
    client_to_upstream_sha256: str
    upstream_to_client_sha256: str
    duration_ms: int
    sni_verified: bool
    capture_complete: bool
    failure_code: str | None = None

    def __post_init__(self) -> None:
        _validate_sha256("policy_sha256", self.policy_sha256)
        _validate_sha256("resolution_sha256", self.resolution_sha256)
        _validate_sha256("client_hello_sha256", self.client_hello_sha256)
        _non_negative_int("selected_address_index", self.selected_address_index)
        _validate_sha256("client_to_upstream_sha256", self.client_to_upstream_sha256)
        _validate_sha256("upstream_to_client_sha256", self.upstream_to_client_sha256)
        _non_negative_int(
            "connection_sequence", self.connection_sequence, positive=True
        )
        _non_negative_int("client_to_upstream_bytes", self.client_to_upstream_bytes)
        _non_negative_int("upstream_to_client_bytes", self.upstream_to_client_bytes)
        _non_negative_int("duration_ms", self.duration_ms)
        if self.outcome not in _AUDIT_OUTCOMES:
            raise ValueError("outcome must be a stable audit outcome")
        if not isinstance(self.sni_verified, bool):
            raise TypeError("sni_verified must be boolean")
        if not isinstance(self.capture_complete, bool):
            raise TypeError("capture_complete must be boolean")
        _validate_failure_code(self.failure_code)
        if self.outcome in {"blocked", "failed"} and self.failure_code is None:
            raise ValueError("blocked or failed audits require a failure_code")
        if self.outcome == "completed" and self.failure_code is not None:
            raise ValueError("completed audits must not carry a failure_code")

    def to_mapping(self) -> dict[str, object]:
        """Return the fixed, non-sensitive audit projection."""

        return {
            "capture_complete": self.capture_complete,
            "client_to_upstream_bytes": self.client_to_upstream_bytes,
            "client_to_upstream_sha256": self.client_to_upstream_sha256,
            "client_hello_sha256": self.client_hello_sha256,
            "connection_sequence": self.connection_sequence,
            "destination_id": CODEX_EGRESS_DESTINATION_ID,
            "duration_ms": self.duration_ms,
            "failure_code": self.failure_code,
            "outcome": self.outcome,
            "policy_sha256": self.policy_sha256,
            "resolution_sha256": self.resolution_sha256,
            "schema": CODEX_EGRESS_AUDIT_SCHEMA,
            "selected_address_index": self.selected_address_index,
            "sni_verified": self.sni_verified,
            "upstream_to_client_bytes": self.upstream_to_client_bytes,
            "upstream_to_client_sha256": self.upstream_to_client_sha256,
        }

    def to_json(self) -> str:
        """Serialize as one deterministic JSON record."""

        return json.dumps(
            self.to_mapping(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )


class EgressConnectionController:
    """Enforce total/concurrent connection ceilings for one proxy process."""

    def __init__(
        self,
        target: DialedEgressTarget,
        *,
        policy: EgressPolicy | None = None,
    ) -> None:
        self._policy = policy or EgressPolicy()
        if not isinstance(target, DialedEgressTarget):
            raise TypeError("target must be DialedEgressTarget")
        if target.policy_sha256 != self._policy.sha256:
            raise CodexEgressProxyError("egress-policy-hash-mismatch")
        self._target = target
        self._opened = 0
        self._active = 0
        self._audits: list[EgressAuditRecord] = []
        self._finalized_sequences: set[int] = set()
        self._lock = threading.RLock()

    @property
    def opened_connections(self) -> int:
        with self._lock:
            return self._opened

    @property
    def active_connections(self) -> int:
        with self._lock:
            return self._active

    @property
    def audit_records(self) -> tuple[EgressAuditRecord, ...]:
        """Return an immutable snapshot; every admitted connection yields one."""

        with self._lock:
            return tuple(self._audits)

    def open(
        self,
        *,
        now: float,
        attestation: TlsClientHelloAttestation,
        last_activity_at: float | None = None,
    ) -> EgressTunnelMeter:
        """Admit one connection and create its bounded ciphertext meter."""

        _validate_monotonic_time(now)
        activity_at = now if last_activity_at is None else last_activity_at
        _validate_monotonic_time(activity_at)
        if activity_at < now:
            raise CodexEgressProxyError("egress-activity-time-invalid")
        if not isinstance(attestation, TlsClientHelloAttestation):
            raise TypeError("attestation must be TlsClientHelloAttestation")
        if attestation.dialed_target is not self._target:
            raise CodexEgressProxyError("egress-attestation-target-mismatch")
        if (
            attestation.policy_sha256 != self._policy.sha256
            or attestation.resolution_sha256 != self._target.resolution_sha256
            or attestation.selected_address_index != self._target.selected_address_index
            or attestation.actual_peer_literal != self._target.selected_literal_ip
            or attestation.server_name != CODEX_EGRESS_HOST
        ):
            raise CodexEgressProxyError("egress-attestation-binding-invalid")
        with self._lock:
            if self._opened >= self._policy.limits.max_connections:
                raise CodexEgressProxyError("egress-connection-limit-exceeded")
            if self._active >= self._policy.limits.max_concurrent_connections:
                raise CodexEgressProxyError("egress-concurrent-limit-exceeded")
            self._opened += 1
            self._active += 1
            sequence = self._opened
        return EgressTunnelMeter(
            controller=self,
            policy=self._policy,
            target=self._target,
            attestation=attestation,
            sequence=sequence,
            started_at=now,
            last_activity_at=activity_at,
        )

    def _finalize(self, sequence: int, record: EgressAuditRecord) -> None:
        with self._lock:
            if sequence in self._finalized_sequences:
                return
            if self._active <= 0:
                raise CodexEgressProxyError("egress-controller-state-invalid")
            self._finalized_sequences.add(sequence)
            self._active -= 1
            self._audits.append(record)


class EgressTunnelMeter:
    """Incrementally bound and hash opaque TLS bytes using an injected clock."""

    def __init__(
        self,
        *,
        controller: EgressConnectionController,
        policy: EgressPolicy,
        target: DialedEgressTarget,
        attestation: TlsClientHelloAttestation,
        sequence: int,
        started_at: float,
        last_activity_at: float,
    ) -> None:
        self._controller = controller
        self._policy = policy
        self._target = target
        self._attestation = attestation
        self._sequence = sequence
        self._started_at = started_at
        self._last_activity_at = last_activity_at
        self._client_bytes = 0
        self._upstream_bytes = 0
        self._client_hash = hashlib.sha256()
        self._upstream_hash = hashlib.sha256()
        self._client_relay_closed = False
        self._upstream_relay_closed = False
        self._closed = False
        self._lock = threading.RLock()

    def observe(
        self,
        direction: Literal["client-to-upstream", "upstream-to-client"],
        payload: bytes,
        *,
        now: float,
    ) -> None:
        """Account one opaque ciphertext chunk before a live relay forwards it."""

        with self._lock:
            try:
                self._ensure_open()
                _validate_monotonic_time(now)
                violation = self._time_violation(now)
                if violation is not None:
                    raise CodexEgressProxyError(violation)
                if not isinstance(payload, bytes):
                    raise CodexEgressProxyError("egress-tunnel-payload-not-bytes")
                if direction == "client-to-upstream":
                    if self._client_relay_closed:
                        raise CodexEgressProxyError("egress-client-relay-closed")
                    proposed = self._client_bytes + len(payload)
                    if proposed > self._policy.limits.max_client_to_upstream_bytes:
                        raise CodexEgressProxyError("egress-client-byte-limit-exceeded")
                    self._client_bytes = proposed
                    self._client_hash.update(payload)
                elif direction == "upstream-to-client":
                    if self._upstream_relay_closed:
                        raise CodexEgressProxyError("egress-upstream-relay-closed")
                    proposed = self._upstream_bytes + len(payload)
                    if proposed > self._policy.limits.max_upstream_to_client_bytes:
                        raise CodexEgressProxyError(
                            "egress-upstream-byte-limit-exceeded"
                        )
                    self._upstream_bytes = proposed
                    self._upstream_hash.update(payload)
                else:
                    raise ValueError("direction must name one tunnel direction")
                self._last_activity_at = now
            except Exception as error:
                self._abort_for_exception(error, now)
                raise

    def check_time(self, *, now: float) -> None:
        """Fail before forwarding when wall or idle time has been exceeded."""

        with self._lock:
            try:
                self._ensure_open()
                _validate_monotonic_time(now)
                violation = self._time_violation(now)
                if violation is not None:
                    raise CodexEgressProxyError(violation)
            except Exception as error:
                self._abort_for_exception(error, now)
                raise

    def mark_forward_progress(self, *, now: float) -> None:
        """Refresh the idle clock after a bounded ciphertext write succeeds."""

        with self._lock:
            try:
                self._ensure_open()
                _validate_monotonic_time(now)
                violation = self._time_violation(now)
                if violation is not None:
                    raise CodexEgressProxyError(violation)
                self._last_activity_at = now
            except Exception as error:
                self._abort_for_exception(error, now)
                raise

    def mark_relay_closed(
        self,
        direction: Literal["client-to-upstream", "upstream-to-client"],
        *,
        now: float,
    ) -> None:
        """Record an observed clean EOF for one relay direction."""

        with self._lock:
            try:
                self._ensure_open()
                _validate_monotonic_time(now)
                violation = self._time_violation(now)
                if violation is not None:
                    raise CodexEgressProxyError(violation)
                if direction == "client-to-upstream":
                    if self._client_relay_closed:
                        raise CodexEgressProxyError("egress-client-relay-closed")
                    self._client_relay_closed = True
                elif direction == "upstream-to-client":
                    if self._upstream_relay_closed:
                        raise CodexEgressProxyError("egress-upstream-relay-closed")
                    self._upstream_relay_closed = True
                else:
                    raise ValueError("direction must name one tunnel direction")
                self._last_activity_at = now
            except Exception as error:
                self._abort_for_exception(error, now)
                raise

    def close(
        self,
        *,
        outcome: str,
        now: float,
        failure_code: str | None = None,
        **forbidden: object,
    ) -> EgressAuditRecord:
        """Release the connection and emit one fixed redacted record."""

        with self._lock:
            try:
                self._ensure_open()
                if forbidden:
                    raise TypeError("capture completeness is derived from relay state")
                _validate_monotonic_time(now)
                violation = self._time_violation(now)
                if violation is not None:
                    raise CodexEgressProxyError(violation)
                if outcome not in _AUDIT_OUTCOMES:
                    raise ValueError("outcome must be a stable audit outcome")
                _validate_failure_code(failure_code)
                capture_complete = (
                    self._client_relay_closed and self._upstream_relay_closed
                )
                if outcome == "completed" and not capture_complete:
                    raise CodexEgressProxyError("egress-relay-capture-incomplete")
                record = self._build_record(
                    outcome=outcome,
                    now=now,
                    capture_complete=capture_complete,
                    failure_code=failure_code,
                )
            except Exception as error:
                self._abort_for_exception(error, now)
                raise
            self._closed = True
            self._controller._finalize(self._sequence, record)
            return record

    def _build_record(
        self,
        *,
        outcome: str,
        now: float,
        capture_complete: bool,
        failure_code: str | None,
    ) -> EgressAuditRecord:
        return EgressAuditRecord(
            policy_sha256=self._policy.sha256,
            resolution_sha256=self._target.resolution_sha256,
            selected_address_index=self._target.selected_address_index,
            client_hello_sha256=self._attestation.client_hello_sha256,
            connection_sequence=self._sequence,
            outcome=outcome,
            client_to_upstream_bytes=self._client_bytes,
            upstream_to_client_bytes=self._upstream_bytes,
            client_to_upstream_sha256=self._client_hash.hexdigest(),
            upstream_to_client_sha256=self._upstream_hash.hexdigest(),
            duration_ms=_elapsed_ms(self._started_at, now),
            sni_verified=True,
            capture_complete=capture_complete,
            failure_code=failure_code,
        )

    def _ensure_open(self) -> None:
        if self._closed:
            raise CodexEgressProxyError("egress-tunnel-already-closed")

    def _abort_for_exception(self, error: Exception, now: object) -> None:
        if self._closed:
            return
        failure_code = (
            error.code
            if isinstance(error, CodexEgressProxyError)
            else "egress-meter-contract-error"
        )
        safe_now = self._last_activity_at
        if (
            not isinstance(now, bool)
            and isinstance(now, (int, float))
            and math.isfinite(now)
            and now >= self._started_at
        ):
            safe_now = max(self._last_activity_at, float(now))
        record = self._build_record(
            outcome="blocked",
            now=safe_now,
            capture_complete=False,
            failure_code=failure_code,
        )
        self._closed = True
        self._controller._finalize(self._sequence, record)

    def _time_violation(self, now: float) -> str | None:
        if now < self._last_activity_at:
            return "egress-clock-regressed"
        wall_ms = _elapsed_ms(self._started_at, now)
        idle_ms = _elapsed_ms(self._last_activity_at, now)
        if wall_ms > self._policy.limits.wall_timeout_ms:
            return "egress-wall-time-limit-exceeded"
        if idle_ms > self._policy.limits.idle_timeout_ms:
            return "egress-idle-time-limit-exceeded"
        return None


def _is_public_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        address.is_global
        and not address.is_private
        and not address.is_loopback
        and not address.is_link_local
        and not address.is_multicast
        and not address.is_reserved
        and not address.is_unspecified
    )


def _canonical_public_literal(value: str) -> str:
    if not isinstance(value, str) or not value or "%" in value:
        raise CodexEgressProxyError("egress-actual-peer-invalid")
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        raise CodexEgressProxyError("egress-actual-peer-invalid") from None
    if (
        isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None
    ) or not _is_public_address(address):
        raise CodexEgressProxyError("egress-actual-peer-invalid")
    return address.compressed


def _address_sort_key(value: str) -> tuple[int, int]:
    address = ipaddress.ip_address(value)
    return (address.version, int(address))


def _resolution_sha256(policy_sha256: str, literal_ips: tuple[str, ...]) -> str:
    document = {
        "literal_ips": list(literal_ips),
        "policy_sha256": policy_sha256,
    }
    payload = json.dumps(
        document,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _parse_server_name_extension(extension: memoryview) -> str:
    offset = 0
    names_length, offset = _read_u16(extension, offset, "tls-client-hello-sni-invalid")
    if names_length != len(extension) - offset:
        raise CodexEgressProxyError("tls-client-hello-sni-invalid")
    names: list[str] = []
    end = offset + names_length
    while offset < end:
        name_type, offset = _read_u8(extension, offset, "tls-client-hello-sni-invalid")
        name_length, offset = _read_u16(
            extension, offset, "tls-client-hello-sni-invalid"
        )
        name_end = _consume(
            extension, offset, name_length, "tls-client-hello-sni-invalid"
        )
        if name_type != 0 or name_length == 0:
            raise CodexEgressProxyError("tls-client-hello-sni-invalid")
        try:
            name = bytes(extension[offset:name_end]).decode("ascii")
        except UnicodeError:
            raise CodexEgressProxyError("tls-client-hello-sni-invalid") from None
        names.append(name)
        offset = name_end
    if len(names) != 1:
        raise CodexEgressProxyError("tls-client-hello-sni-invalid")
    return names[0]


def _read_u8(data: memoryview, offset: int, error_code: str) -> tuple[int, int]:
    end = _consume(data, offset, 1, error_code)
    return int(data[offset]), end


def _read_u16(data: memoryview, offset: int, error_code: str) -> tuple[int, int]:
    end = _consume(data, offset, 2, error_code)
    return int.from_bytes(data[offset:end], "big"), end


def _consume(data: memoryview, offset: int, length: int, error_code: str) -> int:
    if length < 0 or offset < 0 or offset + length > len(data):
        raise CodexEgressProxyError(error_code)
    return offset + length


def _elapsed_ms(start: float, end: float) -> int:
    return math.floor((end - start) * 1_000 + 1e-9)


def _validate_monotonic_time(value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError("monotonic time must be finite and non-negative")


def _bounded_positive_int(name: str, value: int, ceiling: int) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value > ceiling
    ):
        raise ValueError(f"{name} must be within the fixed egress ceiling")


def _non_negative_int(name: str, value: int, *, positive: bool = False) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or (positive and value == 0)
    ):
        qualifier = "positive" if positive else "non-negative"
        raise ValueError(f"{name} must be a {qualifier} integer")


def _validate_sha256(name: str, value: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256")


def _validate_failure_code(value: str | None) -> None:
    if value is not None and (
        not isinstance(value, str)
        or not value
        or re.fullmatch(r"[a-z0-9-]+", value) is None
    ):
        raise ValueError("failure_code must be a stable lowercase code")


def audit_contains_only_allowed_fields(document: Mapping[str, object]) -> bool:
    """Return whether a decoded audit record has exactly the public field set."""

    return set(document) == set(
        EgressAuditRecord(
            policy_sha256="0" * 64,
            resolution_sha256="0" * 64,
            selected_address_index=0,
            client_hello_sha256="0" * 64,
            connection_sequence=1,
            outcome="completed",
            client_to_upstream_bytes=0,
            upstream_to_client_bytes=0,
            client_to_upstream_sha256=hashlib.sha256(b"").hexdigest(),
            upstream_to_client_sha256=hashlib.sha256(b"").hexdigest(),
            duration_ms=0,
            sni_verified=True,
            capture_complete=True,
        ).to_mapping()
    )
