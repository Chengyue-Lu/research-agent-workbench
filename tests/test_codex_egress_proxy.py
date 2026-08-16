import hashlib
import json
import threading
import unittest

from research_workbench.adapters.codex_egress_proxy import (
    CODEX_EGRESS_AUTHORITY,
    CODEX_EGRESS_HOST,
    CODEX_EGRESS_PORT,
    CodexEgressProxyError,
    EgressAuditRecord,
    EgressConnectionController,
    EgressLimits,
    EgressPolicy,
    ResolvedEgressTarget,
    TlsClientHelloAttestation,
    attest_tls_client_hello,
    audit_contains_only_allowed_fields,
    dial_egress_target,
    parse_connect_request,
    resolve_egress_target,
    validate_tls_client_hello_sni,
)


def connect_request(
    authority: str = CODEX_EGRESS_AUTHORITY,
    *,
    host: str | None = CODEX_EGRESS_AUTHORITY,
    extra_headers: tuple[str, ...] = (),
) -> bytes:
    lines = [f"CONNECT {authority} HTTP/1.1"]
    if host is not None:
        lines.append(f"Host: {host}")
    lines.extend(extra_headers)
    return ("\r\n".join(lines) + "\r\n\r\n").encode("ascii")


def tls_client_hello(
    server_name: str | None = CODEX_EGRESS_HOST,
    *,
    duplicate_sni: bool = False,
    two_names: bool = False,
) -> bytes:
    extensions: list[bytes] = []
    if server_name is not None:
        encoded = server_name.encode("ascii")
        names = b"\x00" + len(encoded).to_bytes(2, "big") + encoded
        if two_names:
            names += b"\x00" + len(encoded).to_bytes(2, "big") + encoded
        sni = len(names).to_bytes(2, "big") + names
        extension = b"\x00\x00" + len(sni).to_bytes(2, "big") + sni
        extensions.append(extension)
        if duplicate_sni:
            extensions.append(extension)
    else:
        supported_versions = b"\x00\x2b\x00\x03\x02\x03\x04"
        extensions.append(supported_versions)
    extension_bytes = b"".join(extensions)
    hello = (
        b"\x03\x03"
        + b"R" * 32
        + b"\x00"
        + b"\x00\x02\x13\x01"
        + b"\x01\x00"
        + len(extension_bytes).to_bytes(2, "big")
        + extension_bytes
    )
    handshake = b"\x01" + len(hello).to_bytes(3, "big") + hello
    return b"\x16\x03\x01" + len(handshake).to_bytes(2, "big") + handshake


def split_tls_records(payload: bytes, parts: tuple[int, ...]) -> bytes:
    handshake = payload[5:]
    if sum(parts) != len(handshake):
        raise ValueError("parts must cover the handshake")
    offset = 0
    records: list[bytes] = []
    for length in parts:
        fragment = handshake[offset : offset + length]
        records.append(b"\x16\x03\x01" + length.to_bytes(2, "big") + fragment)
        offset += length
    return b"".join(records)


class FakeResolver:
    def __init__(self, answers: object, error: Exception | None = None) -> None:
        self.answers = answers
        self.error = error
        self.calls: list[tuple[str, int]] = []

    def __call__(self, host: str, port: int):
        self.calls.append((host, port))
        if self.error is not None:
            raise self.error
        return self.answers


class FakeDialer:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, int, int]] = []
        self.connection = object()

    def __call__(self, literal_ip: str, port: int, timeout_ms: int) -> object:
        self.calls.append((literal_ip, port, timeout_ms))
        if self.error is not None:
            raise self.error
        return self.connection


def assert_error_code(
    case: unittest.TestCase,
    expected: str,
    function,
    *args,
    **kwargs,
) -> None:
    with case.assertRaises(CodexEgressProxyError) as raised:
        function(*args, **kwargs)
    case.assertEqual(expected, raised.exception.code)
    case.assertEqual(expected, str(raised.exception))


class EgressPolicyTests(unittest.TestCase):
    def test_policy_canonical_hash_is_deterministic_and_complete(self) -> None:
        first = EgressPolicy()
        second = EgressPolicy()

        self.assertEqual(first.canonical_bytes(), second.canonical_bytes())
        self.assertEqual(first.sha256, second.sha256)
        self.assertEqual(64, len(first.sha256))
        self.assertEqual(
            first.sha256,
            hashlib.sha256(first.canonical_bytes()).hexdigest(),
        )
        document = json.loads(first.canonical_bytes())
        self.assertEqual(CODEX_EGRESS_AUTHORITY, document["authority"])
        self.assertEqual("zhipu-coding-plan", document["destination_id"])
        self.assertTrue(document["require_tls_sni"])
        self.assertEqual(443, CODEX_EGRESS_PORT)

    def test_policy_hash_changes_when_a_bounded_limit_changes(self) -> None:
        default = EgressPolicy()
        smaller = EgressPolicy(limits=EgressLimits(max_connections=1))

        self.assertNotEqual(default.sha256, smaller.sha256)

    def test_policy_rejects_an_arbitrary_authority_or_destination(self) -> None:
        with self.assertRaises(ValueError):
            EgressPolicy(authority="example.com:443")
        with self.assertRaises(ValueError):
            EgressPolicy(destination_id="raw-host-name")

    def test_limits_reject_values_outside_fixed_ceilings(self) -> None:
        for arguments in (
            {"max_connections": 0},
            {"max_connections": 5},
            {"max_concurrent_connections": 2},
            {"max_request_header_bytes": 8_193},
            {"max_resolved_addresses": 17},
            {"max_client_to_upstream_bytes": 1_048_577},
            {"max_upstream_to_client_bytes": 4_194_305},
            {"connect_timeout_ms": 5_001},
            {"idle_timeout_ms": 35_001},
            {"wall_timeout_ms": 130_001},
        ):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                EgressLimits(**arguments)


class ConnectParserTests(unittest.TestCase):
    def test_accepts_only_the_exact_connect_shape_and_discards_headers(self) -> None:
        payload = connect_request(
            extra_headers=("User-Agent: bounded-test", "Proxy-Connection: keep-alive")
        )

        result = parse_connect_request(payload)

        self.assertEqual(CODEX_EGRESS_AUTHORITY, result.authority)
        self.assertEqual(3, result.header_count)
        self.assertEqual(len(payload), result.consumed_bytes)
        self.assertFalse(hasattr(result, "headers"))

    def test_rejects_authority_aliases_ips_userinfo_and_wrong_ports(self) -> None:
        forbidden = (
            "open.bigmodel.cn:80",
            "open.bigmodel.cn:444",
            "OPEN.BIGMODEL.CN:443",
            "open.bigmodel.cn.:443",
            "sub.open.bigmodel.cn:443",
            "open.bigmodel.cn.evil.example:443",
            "user@open.bigmodel.cn:443",
            "127.0.0.1:443",
            "[::1]:443",
            "https://open.bigmodel.cn:443",
        )
        for authority in forbidden:
            with self.subTest(authority=authority):
                assert_error_code(
                    self,
                    "connect-authority-not-allowed",
                    parse_connect_request,
                    connect_request(authority),
                )

    def test_rejects_missing_wrong_and_duplicate_host(self) -> None:
        assert_error_code(
            self,
            "connect-host-missing",
            parse_connect_request,
            connect_request(host=None),
        )
        assert_error_code(
            self,
            "connect-host-mismatch",
            parse_connect_request,
            connect_request(host="evil.example:443"),
        )
        assert_error_code(
            self,
            "connect-header-duplicate",
            parse_connect_request,
            connect_request(extra_headers=(f"hOsT: {CODEX_EGRESS_AUTHORITY}",)),
        )

    def test_rejects_content_framing_proxy_auth_and_unknown_headers(self) -> None:
        cases = (
            ("Content-Length: 0", "connect-content-length-forbidden"),
            ("Transfer-Encoding: chunked", "connect-transfer-encoding-forbidden"),
            (
                "Proxy-Authorization: Basic secret",
                "connect-proxy-authorization-forbidden",
            ),
            ("X-Forwarded-For: 127.0.0.1", "connect-header-not-allowed"),
        )
        for header, expected in cases:
            with self.subTest(header=header):
                assert_error_code(
                    self,
                    expected,
                    parse_connect_request,
                    connect_request(extra_headers=(header,)),
                )

    def test_rejects_obs_fold_controls_and_non_ascii(self) -> None:
        assert_error_code(
            self,
            "connect-header-folding-forbidden",
            parse_connect_request,
            connect_request(extra_headers=(" folded",)),
        )
        assert_error_code(
            self,
            "connect-header-control-character",
            parse_connect_request,
            connect_request(extra_headers=("User-Agent: bad\tvalue",)),
        )
        payload = connect_request()[:-4] + b"\r\nUser-Agent: \xff\r\n\r\n"
        assert_error_code(
            self,
            "connect-header-not-ascii",
            parse_connect_request,
            payload,
        )

    def test_rejects_non_connect_http_and_noncanonical_spacing(self) -> None:
        for request_line in (
            b"GET https://open.bigmodel.cn/ HTTP/1.1",
            b"POST /api/v1/responses HTTP/1.1",
            b"CONNECT  open.bigmodel.cn:443 HTTP/1.1",
            b"CONNECT open.bigmodel.cn:443 HTTP/1.0",
        ):
            payload = request_line + b"\r\nHost: open.bigmodel.cn:443\r\n\r\n"
            with self.subTest(request_line=request_line):
                assert_error_code(
                    self,
                    "connect-authority-not-allowed",
                    parse_connect_request,
                    payload,
                )

    def test_rejects_incomplete_oversize_many_headers_and_pipelining(self) -> None:
        assert_error_code(
            self,
            "connect-header-incomplete",
            parse_connect_request,
            connect_request()[:-2],
        )
        assert_error_code(
            self,
            "connect-pipelined-data-forbidden",
            parse_connect_request,
            connect_request() + b"TLS",
        )
        many = tuple(f"User-Agent: value-{index}" for index in range(17))
        assert_error_code(
            self,
            "connect-header-count-exceeded",
            parse_connect_request,
            connect_request(extra_headers=many),
        )
        assert_error_code(
            self,
            "connect-header-byte-limit-exceeded",
            parse_connect_request,
            connect_request(extra_headers=("User-Agent: " + "x" * 8_200,)),
        )


class ResolverAndDialerTests(unittest.TestCase):
    def test_resolves_once_and_canonicalizes_only_global_literals(self) -> None:
        resolver = FakeResolver(["2606:4700:4700::1111", "8.8.8.8", "8.8.8.8"])

        target = resolve_egress_target(resolver)

        self.assertEqual([(CODEX_EGRESS_HOST, 443)], resolver.calls)
        self.assertEqual(
            ("8.8.8.8", "2606:4700:4700::1111"),
            target.literal_ips,
        )
        self.assertEqual(EgressPolicy().sha256, target.policy_sha256)
        self.assertEqual(64, len(target.resolution_sha256))

    def test_rejects_every_non_global_address_class_and_mixed_answers(self) -> None:
        unsafe = (
            "127.0.0.1",
            "10.0.0.1",
            "169.254.1.1",
            "224.0.0.1",
            "0.0.0.0",
            "100.64.0.1",
            "192.0.2.1",
            "::1",
            "fe80::1",
            "ff02::1",
            "::",
            "::ffff:8.8.8.8",
            "fe80::1%eth0",
            "not-an-ip",
        )
        for address in unsafe:
            with self.subTest(address=address):
                assert_error_code(
                    self,
                    "egress-resolution-mixed-or-non-global",
                    resolve_egress_target,
                    FakeResolver([address]),
                )
        assert_error_code(
            self,
            "egress-resolution-mixed-or-non-global",
            resolve_egress_target,
            FakeResolver(["8.8.8.8", "127.0.0.1"]),
        )

    def test_rejects_resolver_errors_invalid_shapes_empty_and_address_floods(
        self,
    ) -> None:
        cases = (
            (
                FakeResolver([], error=OSError("raw resolver detail")),
                "egress-resolution-failed",
            ),
            (FakeResolver("8.8.8.8"), "egress-resolution-invalid"),
            (FakeResolver([]), "egress-resolution-empty"),
            (
                FakeResolver(["8.8.8.8"] * 17),
                "egress-resolution-address-limit-exceeded",
            ),
        )
        for resolver, expected in cases:
            with self.subTest(expected=expected):
                assert_error_code(
                    self,
                    expected,
                    resolve_egress_target,
                    resolver,
                )

    def test_dialer_receives_only_frozen_literal_ip_and_never_resolves_again(
        self,
    ) -> None:
        resolver = FakeResolver(["8.8.8.8", "2606:4700:4700::1111"])
        target = resolve_egress_target(resolver)
        dialer = FakeDialer()

        dialed = dial_egress_target(target, dialer, address_index=1)

        self.assertEqual([(CODEX_EGRESS_HOST, 443)], resolver.calls)
        self.assertEqual(
            [("2606:4700:4700::1111", 443, 5_000)],
            dialer.calls,
        )
        self.assertIs(dialer.connection, dialed.connection)
        self.assertEqual(1, dialed.selected_address_index)

    def test_dial_fails_closed_without_leaking_exception_detail(self) -> None:
        target = resolve_egress_target(FakeResolver(["8.8.8.8"]))
        dialer = FakeDialer(OSError("sensitive socket detail"))

        assert_error_code(
            self,
            "egress-dial-failed",
            dial_egress_target,
            target,
            dialer,
        )

    def test_dial_rejects_policy_drift_and_bad_index_before_calling_dialer(
        self,
    ) -> None:
        target = resolve_egress_target(FakeResolver(["8.8.8.8"]))
        dialer = FakeDialer()
        changed = EgressPolicy(limits=EgressLimits(max_connections=1))

        assert_error_code(
            self,
            "egress-policy-hash-mismatch",
            dial_egress_target,
            target,
            dialer,
            policy=changed,
        )
        assert_error_code(
            self,
            "egress-address-index-invalid",
            dial_egress_target,
            target,
            dialer,
            address_index=2,
        )
        self.assertEqual([], dialer.calls)

    def test_frozen_target_rejects_address_or_hash_tampering(self) -> None:
        policy_hash = EgressPolicy().sha256
        for literal_ips, resolution_hash in (
            (("127.0.0.1",), "0" * 64),
            (("8.8.8.8", "8.8.8.8"), "0" * 64),
            (("2606:4700:4700::1111", "8.8.8.8"), "0" * 64),
            (("8.8.8.8",), "0" * 64),
        ):
            with self.subTest(literal_ips=literal_ips), self.assertRaises(ValueError):
                ResolvedEgressTarget(
                    policy_sha256=policy_hash,
                    literal_ips=literal_ips,
                    resolution_sha256=resolution_hash,
                )


class TlsClientHelloTests(unittest.TestCase):
    def test_accepts_one_exact_visible_sni_without_mutating_bytes(self) -> None:
        payload = tls_client_hello()
        before = bytes(payload)

        self.assertTrue(validate_tls_client_hello_sni(payload))
        self.assertEqual(before, payload)

    def test_rejects_wrong_missing_duplicate_and_multiple_names(self) -> None:
        cases = (
            (tls_client_hello("evil.example"), "tls-client-hello-sni-not-allowed"),
            (tls_client_hello(None), "tls-client-hello-sni-missing"),
            (tls_client_hello(duplicate_sni=True), "tls-client-hello-sni-duplicate"),
            (tls_client_hello(two_names=True), "tls-client-hello-sni-invalid"),
        )
        for payload, expected in cases:
            with self.subTest(expected=expected):
                assert_error_code(
                    self,
                    expected,
                    validate_tls_client_hello_sni,
                    payload,
                )

    def test_rejects_truncated_malformed_and_non_tls_records(self) -> None:
        valid = tls_client_hello()
        cases = (
            (valid[:-1], "tls-client-hello-record-length-invalid"),
            (b"HTTP/1.1 200 OK", "tls-client-hello-record-length-invalid"),
            (
                valid[:3] + b"\x00\x01" + valid[5:],
                "tls-client-hello-record-length-invalid",
            ),
            (valid[:5] + b"\x02" + valid[6:], "tls-client-hello-handshake-invalid"),
        )
        for payload, expected in cases:
            with self.subTest(expected=expected):
                assert_error_code(
                    self,
                    expected,
                    validate_tls_client_hello_sni,
                    payload,
                )

    def test_policy_cannot_disable_sni_inspection(self) -> None:
        with self.assertRaisesRegex(ValueError, "fixed true"):
            EgressPolicy(require_tls_sni=False)

    def test_accepts_client_hello_split_across_two_or_three_records(self) -> None:
        payload = tls_client_hello()
        handshake_length = len(payload) - 5
        for parts in (
            (2, handshake_length - 2),
            (1, 2, handshake_length - 3),
        ):
            with self.subTest(parts=parts):
                self.assertTrue(
                    validate_tls_client_hello_sni(split_tls_records(payload, parts))
                )

    def test_rejects_four_records_extra_handshake_and_application_data(self) -> None:
        payload = tls_client_hello()
        handshake_length = len(payload) - 5
        cases = (
            (
                split_tls_records(payload, (1, 1, 1, handshake_length - 3)),
                "tls-client-hello-record-count-exceeded",
            ),
            (
                payload + b"\x16\x03\x01\x00\x01\x00",
                "tls-client-hello-handshake-length-invalid",
            ),
            (
                payload + b"\x17\x03\x03\x00\x01x",
                "tls-client-hello-extra-data-forbidden",
            ),
        )
        for candidate, expected in cases:
            with self.subTest(expected=expected):
                assert_error_code(
                    self,
                    expected,
                    validate_tls_client_hello_sni,
                    candidate,
                )
        assert_error_code(
            self,
            "tls-client-hello-size-invalid",
            validate_tls_client_hello_sni,
            b"x" * 65_536,
        )

    def test_attestation_binds_dial_target_peer_hash_sni_and_record_count(self) -> None:
        policy = EgressPolicy()
        resolved = resolve_egress_target(FakeResolver(["8.8.8.8"]), policy=policy)
        dialed = dial_egress_target(resolved, FakeDialer(), policy=policy)
        payload = split_tls_records(
            tls_client_hello(), (2, len(tls_client_hello()) - 7)
        )

        attestation = attest_tls_client_hello(
            dialed,
            payload,
            actual_peer_literal="8.8.8.8",
            policy=policy,
        )

        self.assertIs(dialed, attestation.dialed_target)
        self.assertEqual(dialed.policy_sha256, attestation.policy_sha256)
        self.assertEqual(dialed.resolution_sha256, attestation.resolution_sha256)
        self.assertEqual(0, attestation.selected_address_index)
        self.assertEqual("8.8.8.8", attestation.actual_peer_literal)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(), attestation.client_hello_sha256
        )
        self.assertEqual(CODEX_EGRESS_HOST, attestation.server_name)
        self.assertEqual(2, attestation.record_count)

    def test_attestation_rejects_actual_peer_mismatch_and_public_constructor(
        self,
    ) -> None:
        policy = EgressPolicy()
        resolved = resolve_egress_target(FakeResolver(["8.8.8.8"]), policy=policy)
        dialed = dial_egress_target(resolved, FakeDialer(), policy=policy)
        assert_error_code(
            self,
            "egress-actual-peer-mismatch",
            attest_tls_client_hello,
            dialed,
            tls_client_hello(),
            actual_peer_literal="1.1.1.1",
            policy=policy,
        )
        with self.assertRaises(TypeError):
            TlsClientHelloAttestation(
                dialed_target=dialed,
                actual_peer_literal="8.8.8.8",
                client_hello_sha256="0" * 64,
                server_name=CODEX_EGRESS_HOST,
                record_count=1,
                _issuer=object(),
            )


class TunnelBudgetAndAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = EgressPolicy()
        resolved = resolve_egress_target(
            FakeResolver(["8.8.8.8"]),
            policy=self.policy,
        )
        self.target = dial_egress_target(
            resolved,
            FakeDialer(),
            policy=self.policy,
        )
        self.attestation = attest_tls_client_hello(
            self.target,
            tls_client_hello(),
            actual_peer_literal="8.8.8.8",
            policy=self.policy,
        )

    def make_controller(
        self,
        *,
        policy: EgressPolicy | None = None,
    ) -> tuple[EgressConnectionController, object]:
        active_policy = policy or self.policy
        resolved = resolve_egress_target(
            FakeResolver(["8.8.8.8"]), policy=active_policy
        )
        dialed = dial_egress_target(resolved, FakeDialer(), policy=active_policy)
        attestation = attest_tls_client_hello(
            dialed,
            tls_client_hello(),
            actual_peer_literal="8.8.8.8",
            policy=active_policy,
        )
        return EgressConnectionController(dialed, policy=active_policy), attestation

    def test_enforces_concurrency_and_total_connection_limits(self) -> None:
        controller = EgressConnectionController(self.target, policy=self.policy)
        with self.assertRaises(TypeError):
            controller.open(now=9.9, attestation=True)
        first = controller.open(now=10.0, attestation=self.attestation)
        self.assertEqual(1, controller.active_connections)
        assert_error_code(
            self,
            "egress-concurrent-limit-exceeded",
            controller.open,
            now=10.1,
            attestation=self.attestation,
        )
        first.mark_relay_closed("client-to-upstream", now=10.1)
        first.mark_relay_closed("upstream-to-client", now=10.2)
        first.close(outcome="completed", now=10.2)
        second = controller.open(now=11.0, attestation=self.attestation)
        second.close(outcome="failed", now=11.2, failure_code="upstream-closed")
        assert_error_code(
            self,
            "egress-connection-limit-exceeded",
            controller.open,
            now=12.0,
            attestation=self.attestation,
        )
        self.assertEqual(2, controller.opened_connections)
        self.assertEqual(0, controller.active_connections)
        self.assertEqual(2, len(controller.audit_records))

    def test_hashes_opaque_bytes_and_emits_only_redacted_audit_fields(self) -> None:
        secret = b"Authorization: Bearer synthetic-secret"
        response = b"opaque tls response bytes"
        controller = EgressConnectionController(self.target, policy=self.policy)
        meter = controller.open(now=20.0, attestation=self.attestation)
        meter.observe("client-to-upstream", secret, now=20.1)
        meter.observe("upstream-to-client", response, now=20.2)
        meter.mark_relay_closed("client-to-upstream", now=20.21)
        meter.mark_relay_closed("upstream-to-client", now=20.22)

        record = meter.close(outcome="completed", now=20.3)
        document = json.loads(record.to_json())
        serialized = record.to_json()

        self.assertEqual(len(secret), document["client_to_upstream_bytes"])
        self.assertEqual(len(response), document["upstream_to_client_bytes"])
        self.assertEqual(
            hashlib.sha256(secret).hexdigest(),
            document["client_to_upstream_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(response).hexdigest(),
            document["upstream_to_client_sha256"],
        )
        self.assertTrue(audit_contains_only_allowed_fields(document))
        self.assertNotIn("synthetic-secret", serialized)
        self.assertNotIn("Authorization", serialized)
        self.assertNotIn(CODEX_EGRESS_HOST, serialized)
        self.assertNotIn("8.8.8.8", serialized)
        self.assertEqual("zhipu-coding-plan", document["destination_id"])
        self.assertEqual(0, document["selected_address_index"])
        self.assertEqual(
            self.attestation.client_hello_sha256,
            document["client_hello_sha256"],
        )
        self.assertEqual(0, controller.active_connections)
        self.assertEqual((record,), controller.audit_records)

    def test_byte_limit_exception_auto_releases_and_emits_one_incomplete_audit(
        self,
    ) -> None:
        policy = EgressPolicy(
            limits=EgressLimits(
                max_client_to_upstream_bytes=3,
                max_upstream_to_client_bytes=4,
            )
        )
        controller, attestation = self.make_controller(policy=policy)
        meter = controller.open(now=1.0, attestation=attestation)
        meter.observe("client-to-upstream", b"abc", now=1.1)
        assert_error_code(
            self,
            "egress-client-byte-limit-exceeded",
            meter.observe,
            "client-to-upstream",
            b"d",
            now=1.2,
        )
        self.assertEqual(0, controller.active_connections)
        self.assertEqual(1, len(controller.audit_records))
        record = controller.audit_records[0]
        self.assertFalse(record.capture_complete)
        self.assertEqual("egress-client-byte-limit-exceeded", record.failure_code)
        assert_error_code(
            self,
            "egress-tunnel-already-closed",
            meter.observe,
            "client-to-upstream",
            b"late",
            now=1.3,
        )
        self.assertEqual(1, len(controller.audit_records))
        self.assertEqual(3, record.client_to_upstream_bytes)
        self.assertEqual(0, record.upstream_to_client_bytes)

    def test_enforces_idle_wall_and_monotonic_clock_bounds(self) -> None:
        idle_policy = EgressPolicy(
            limits=EgressLimits(idle_timeout_ms=100, wall_timeout_ms=500)
        )
        idle_controller, idle_attestation = self.make_controller(policy=idle_policy)
        idle_meter = idle_controller.open(now=5.0, attestation=idle_attestation)
        idle_meter.check_time(now=5.1)
        assert_error_code(
            self,
            "egress-idle-time-limit-exceeded",
            idle_meter.check_time,
            now=5.101,
        )
        self.assertEqual(0, idle_controller.active_connections)
        self.assertEqual(1, len(idle_controller.audit_records))

        wall_policy = EgressPolicy(
            limits=EgressLimits(idle_timeout_ms=500, wall_timeout_ms=100)
        )
        wall_controller, wall_attestation = self.make_controller(policy=wall_policy)
        wall_meter = wall_controller.open(now=7.0, attestation=wall_attestation)
        wall_meter.observe("client-to-upstream", b"x", now=7.05)
        assert_error_code(
            self,
            "egress-wall-time-limit-exceeded",
            wall_meter.check_time,
            now=7.101,
        )
        self.assertEqual(0, wall_controller.active_connections)
        assert_error_code(
            self,
            "egress-tunnel-already-closed",
            wall_meter.check_time,
            now=7.04,
        )

    def test_capture_complete_is_derived_and_cannot_be_claimed_by_caller(self) -> None:
        controller = EgressConnectionController(self.target, policy=self.policy)
        meter = controller.open(now=3.0, attestation=self.attestation)
        with self.assertRaises(TypeError):
            meter.close(outcome="completed", now=3.1, capture_complete=True)
        self.assertEqual(0, controller.active_connections)
        self.assertEqual(1, len(controller.audit_records))
        self.assertFalse(controller.audit_records[0].capture_complete)

        controller2, attestation2 = self.make_controller()
        meter2 = controller2.open(now=4.0, attestation=attestation2)
        meter2.mark_relay_closed("client-to-upstream", now=4.1)
        assert_error_code(
            self,
            "egress-relay-capture-incomplete",
            meter2.close,
            outcome="completed",
            now=4.2,
        )
        self.assertFalse(controller2.audit_records[0].capture_complete)

    def test_audit_record_rejects_raw_or_malformed_manual_values(self) -> None:
        empty_hash = hashlib.sha256(b"").hexdigest()
        base = {
            "policy_sha256": "0" * 64,
            "resolution_sha256": "1" * 64,
            "selected_address_index": 0,
            "client_hello_sha256": "2" * 64,
            "connection_sequence": 1,
            "outcome": "failed",
            "client_to_upstream_bytes": 0,
            "upstream_to_client_bytes": 0,
            "client_to_upstream_sha256": empty_hash,
            "upstream_to_client_sha256": empty_hash,
            "duration_ms": 0,
            "sni_verified": True,
            "capture_complete": False,
            "failure_code": "safe-code",
        }
        for override in (
            {"policy_sha256": "bad"},
            {"connection_sequence": 0},
            {"client_to_upstream_bytes": -1},
            {"outcome": "raw provider failure"},
            {"failure_code": "raw detail: secret"},
            {"failure_code": None},
            {"outcome": "completed", "failure_code": "unexpected-failure"},
        ):
            arguments = {**base, **override}
            with self.subTest(override=override), self.assertRaises(ValueError):
                EgressAuditRecord(**arguments)

    def test_rejects_use_after_close_and_raw_failure_codes(self) -> None:
        controller = EgressConnectionController(self.target, policy=self.policy)
        meter = controller.open(now=1.0, attestation=self.attestation)
        with self.assertRaises(ValueError):
            meter.close(
                outcome="failed",
                now=1.1,
                failure_code="raw detail: secret",
            )
        self.assertEqual(0, controller.active_connections)
        self.assertEqual(1, len(controller.audit_records))
        self.assertEqual(
            "egress-meter-contract-error", controller.audit_records[0].failure_code
        )
        assert_error_code(
            self,
            "egress-tunnel-already-closed",
            meter.observe,
            "client-to-upstream",
            b"late",
            now=1.3,
        )
        self.assertEqual(1, len(controller.audit_records))

    def test_binding_rejects_attestation_for_another_dial(self) -> None:
        controller = EgressConnectionController(self.target, policy=self.policy)
        other_controller, other_attestation = self.make_controller()
        del other_controller
        assert_error_code(
            self,
            "egress-attestation-target-mismatch",
            controller.open,
            now=1.0,
            attestation=other_attestation,
        )
        self.assertEqual(0, controller.opened_connections)

    def test_concurrent_meter_failure_finalizes_exactly_once(self) -> None:
        policy = EgressPolicy(limits=EgressLimits(max_client_to_upstream_bytes=1))
        controller, attestation = self.make_controller(policy=policy)
        meter = controller.open(now=1.0, attestation=attestation)
        barrier = threading.Barrier(3)
        errors: list[str] = []

        def overflow() -> None:
            barrier.wait()
            try:
                meter.observe("client-to-upstream", b"xx", now=1.1)
            except CodexEgressProxyError as error:
                errors.append(error.code)

        threads = [threading.Thread(target=overflow) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join()

        self.assertEqual(0, controller.active_connections)
        self.assertEqual(1, len(controller.audit_records))
        self.assertFalse(controller.audit_records[0].capture_complete)
        self.assertCountEqual(
            ["egress-client-byte-limit-exceeded", "egress-tunnel-already-closed"],
            errors,
        )


if __name__ == "__main__":
    unittest.main()
