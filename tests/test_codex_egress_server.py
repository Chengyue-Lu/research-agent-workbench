import json
import socket
import threading
import unittest
from collections import deque
from unittest.mock import patch

import research_workbench.adapters.codex_egress_server as server_module
from research_workbench.adapters.codex_egress_proxy import (
    CODEX_EGRESS_AUTHORITY,
    CODEX_EGRESS_HOST,
    CodexEgressProxyError,
    EgressLimits,
    EgressPolicy,
)
from research_workbench.adapters.codex_egress_server import (
    CodexEgressServer,
    StdlibEgressResolver,
    StdlibLiteralDialer,
    run_codex_egress_server,
)


def connect_request(*, extra: bytes = b"") -> bytes:
    return (
        f"CONNECT {CODEX_EGRESS_AUTHORITY} HTTP/1.1\r\n"
        f"Host: {CODEX_EGRESS_AUTHORITY}\r\n\r\n"
    ).encode("ascii") + extra


def tls_client_hello(server_name: str = CODEX_EGRESS_HOST) -> bytes:
    encoded = server_name.encode("ascii")
    names = b"\x00" + len(encoded).to_bytes(2, "big") + encoded
    sni = len(names).to_bytes(2, "big") + names
    extensions = b"\x00\x00" + len(sni).to_bytes(2, "big") + sni
    hello = (
        b"\x03\x03"
        + b"R" * 32
        + b"\x00"
        + b"\x00\x02\x13\x01"
        + b"\x01\x00"
        + len(extensions).to_bytes(2, "big")
        + extensions
    )
    handshake = b"\x01" + len(hello).to_bytes(3, "big") + hello
    return b"\x16\x03\x01" + len(handshake).to_bytes(2, "big") + handshake


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class FakeSocket:
    def __init__(
        self,
        recv_chunks=(),
        *,
        peer: str = "8.8.8.8",
        send_limits=(),
    ) -> None:
        self.recv_chunks = deque(recv_chunks)
        self.peer = peer
        self.send_limits = deque(send_limits)
        self.sent = bytearray()
        self.recv_calls: list[int] = []
        self.send_calls = 0
        self.timeouts: list[float] = []
        self.blocking: list[bool] = []
        self.shutdown_calls: list[int] = []
        self.connect_calls: list[tuple[object, ...]] = []
        self.closed = False

    @property
    def read_ready(self) -> bool:
        return bool(self.recv_chunks)

    def recv(self, size: int) -> bytes:
        self.recv_calls.append(size)
        if not self.recv_chunks:
            raise BlockingIOError()
        value = self.recv_chunks.popleft()
        if isinstance(value, BaseException):
            raise value
        if len(value) > size:
            self.recv_chunks.appendleft(value[size:])
            return value[:size]
        return value

    def send(self, payload: bytes | bytearray) -> int:
        self.send_calls += 1
        limit = self.send_limits.popleft() if self.send_limits else len(payload)
        count = min(limit, len(payload))
        self.sent.extend(bytes(payload[:count]))
        return count

    def settimeout(self, value: float) -> None:
        self.timeouts.append(value)

    def setblocking(self, value: bool) -> None:
        self.blocking.append(value)

    def getpeername(self) -> tuple[str, int]:
        return self.peer, 443

    def shutdown(self, how: int) -> None:
        self.shutdown_calls.append(how)

    def connect(self, endpoint: tuple[object, ...]) -> None:
        self.connect_calls.append(endpoint)

    def close(self) -> None:
        self.closed = True


class AdvancingFakeSocket(FakeSocket):
    def __init__(self, *args, clock: FakeClock, recv_advance: float, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.clock = clock
        self.recv_advance = recv_advance

    def recv(self, size: int) -> bytes:
        self.clock.advance(self.recv_advance)
        return super().recv(size)


class PeerOverrideSocket:
    def __init__(self, wrapped: socket.socket, peer: str) -> None:
        self._wrapped = wrapped
        self._peer = peer

    def getpeername(self) -> tuple[str, int]:
        return self._peer, 443

    def __getattr__(self, name: str):
        return getattr(self._wrapped, name)


class FakeListenSocket:
    def __init__(self, clients: tuple[FakeSocket, ...]) -> None:
        self.clients = deque(clients)
        self.accept_calls = 0
        self.timeouts: list[float] = []
        self.closed = False

    def accept(self) -> tuple[FakeSocket, tuple[str, int]]:
        self.accept_calls += 1
        if not self.clients:
            raise TimeoutError()
        return self.clients.popleft(), ("172.20.0.2", 40000)

    def settimeout(self, value: float) -> None:
        self.timeouts.append(value)

    def close(self) -> None:
        self.closed = True


class FakeResolver:
    def __init__(self, answers=("8.8.8.8",)) -> None:
        self.answers = answers
        self.calls: list[tuple[str, int]] = []

    def __call__(self, host: str, port: int):
        self.calls.append((host, port))
        return self.answers


class FakeDialer:
    def __init__(self, connections: tuple[FakeSocket, ...]) -> None:
        self.connections = deque(connections)
        self.calls: list[tuple[str, int, int]] = []

    def __call__(self, literal_ip: str, port: int, timeout_ms: int) -> object:
        self.calls.append((literal_ip, port, timeout_ms))
        return self.connections.popleft()


class FakeRelayWaiter:
    def __init__(self, clock: FakeClock, *, advance: float = 0.0001) -> None:
        self.clock = clock
        self.advance = advance
        self.calls = 0

    def wait(self, readable, writable, timeout_seconds):
        self.calls += 1
        self.clock.advance(min(self.advance, timeout_seconds))
        ready_read = tuple(item for item in readable if item.read_ready)
        return ready_read, tuple(writable)


class NeverReadyWaiter:
    def __init__(self, clock: FakeClock, advance: float) -> None:
        self.clock = clock
        self.advance = advance

    def wait(self, readable, writable, timeout_seconds):
        self.clock.advance(min(self.advance, timeout_seconds))
        return (), ()


class CodexEgressServerTests(unittest.TestCase):
    def test_partial_io_relays_opaque_tls_and_emits_one_redacted_audit(self) -> None:
        clock = FakeClock()
        hello = tls_client_hello()
        request_secret = b"request-secret-ciphertext"
        response_secret = b"response-secret-ciphertext"
        request = connect_request()
        client = FakeSocket(
            (
                request[:11],
                request[11:],
                hello[:7],
                hello[7:21],
                hello[21:],
                request_secret,
                b"",
            ),
            send_limits=(2,) * 100,
        )
        upstream = FakeSocket(
            (response_secret[:5], response_secret[5:], b""),
            peer="1.1.1.1",
            send_limits=(3,) * 100,
        )
        listener = FakeListenSocket((client,))
        resolver = FakeResolver(("8.8.8.8", "1.1.1.1", "8.8.8.8"))
        dialer = FakeDialer((upstream,))
        audits = []

        records = run_codex_egress_server(
            listener,
            resolver=resolver,
            dialer=dialer,
            clock=clock,
            relay_waiter=FakeRelayWaiter(clock),
            audit_sink=audits.append,
        )

        self.assertEqual([(CODEX_EGRESS_HOST, 443)], resolver.calls)
        self.assertEqual([("1.1.1.1", 443, 5_000)], dialer.calls)
        self.assertEqual(1, len(records))
        self.assertEqual([records[0]], audits)
        self.assertEqual("completed", records[0].outcome)
        self.assertTrue(records[0].capture_complete)
        self.assertTrue(records[0].sni_verified)
        self.assertEqual(
            len(hello) + len(request_secret), records[0].client_to_upstream_bytes
        )
        self.assertEqual(len(response_secret), records[0].upstream_to_client_bytes)
        self.assertEqual(hello + request_secret, bytes(upstream.sent))
        self.assertEqual(
            b"HTTP/1.1 200 Connection Established\r\n\r\n" + response_secret,
            bytes(client.sent),
        )
        self.assertGreater(client.send_calls, 2)
        self.assertGreater(upstream.send_calls, 2)
        audit_json = records[0].to_json()
        self.assertNotIn("request-secret", audit_json)
        self.assertNotIn("response-secret", audit_json)
        self.assertNotIn("1.1.1.1", audit_json)
        self.assertNotIn("8.8.8.8", audit_json)
        self.assertEqual(set(json.loads(audit_json)), set(records[0].to_mapping()))
        self.assertTrue(listener.closed)
        self.assertTrue(client.closed)
        self.assertTrue(upstream.closed)
        self.assertEqual([False], client.blocking)
        self.assertEqual([False], upstream.blocking)
        self.assertEqual([socket.SHUT_WR], client.shutdown_calls)
        self.assertEqual([socket.SHUT_WR], upstream.shutdown_calls)

    def test_client_hello_stream_is_packetization_independent(self) -> None:
        hello = tls_client_hello()
        ciphertext = b"post-client-hello-ciphertext"
        observations = []
        for chunks in ((hello + ciphertext,), (hello, ciphertext)):
            clock = FakeClock()
            client = FakeSocket((connect_request(), *chunks, b""))
            upstream = FakeSocket((b"",), peer="1.1.1.1")

            (record,) = run_codex_egress_server(
                FakeListenSocket((client,)),
                resolver=FakeResolver(("1.1.1.1",)),
                dialer=FakeDialer((upstream,)),
                clock=clock,
                relay_waiter=FakeRelayWaiter(clock),
            )
            observations.append(
                (record.outcome, record.client_to_upstream_sha256, bytes(upstream.sent))
            )

        self.assertEqual(observations[0], observations[1])
        self.assertEqual("completed", observations[0][0])
        self.assertEqual(hello + ciphertext, observations[0][2])

    def test_pipelined_tls_is_blocked_before_dial_and_audited_once(self) -> None:
        clock = FakeClock()
        client = FakeSocket((connect_request(extra=tls_client_hello()),))
        listener = FakeListenSocket((client,))
        resolver = FakeResolver()
        dialer = FakeDialer(())
        audits = []

        records = CodexEgressServer(
            listener,
            resolver=resolver,
            dialer=dialer,
            clock=clock,
            relay_waiter=FakeRelayWaiter(clock),
            audit_sink=audits.append,
        ).run()

        self.assertEqual([], dialer.calls)
        self.assertEqual(1, len(records))
        self.assertEqual(1, len(audits))
        self.assertEqual("connect-pipelined-data-forbidden", records[0].failure_code)
        self.assertFalse(records[0].sni_verified)
        self.assertEqual(b"", bytes(client.sent))
        self.assertTrue(client.closed)

    def test_wrong_actual_peer_is_blocked_before_200_without_redial(self) -> None:
        clock = FakeClock()
        client = FakeSocket((connect_request(),))
        upstream = FakeSocket(peer="8.8.4.4")
        listener = FakeListenSocket((client,))
        dialer = FakeDialer((upstream,))

        (record,) = CodexEgressServer(
            listener,
            resolver=FakeResolver(),
            dialer=dialer,
            clock=clock,
            relay_waiter=FakeRelayWaiter(clock),
        ).run()

        self.assertEqual(1, len(dialer.calls))
        self.assertEqual("egress-actual-peer-mismatch", record.failure_code)
        self.assertFalse(record.sni_verified)
        self.assertEqual(b"", bytes(client.sent))
        self.assertTrue(client.closed)
        self.assertTrue(upstream.closed)

    def test_wrong_sni_is_blocked_after_200_and_never_forwarded(self) -> None:
        clock = FakeClock()
        hello = tls_client_hello("evil.example")
        client = FakeSocket((connect_request(), hello))
        upstream = FakeSocket()

        (record,) = CodexEgressServer(
            FakeListenSocket((client,)),
            resolver=FakeResolver(),
            dialer=FakeDialer((upstream,)),
            clock=clock,
            relay_waiter=FakeRelayWaiter(clock),
        ).run()

        self.assertEqual("tls-client-hello-sni-not-allowed", record.failure_code)
        self.assertFalse(record.sni_verified)
        self.assertEqual(b"", bytes(upstream.sent))
        self.assertEqual(
            b"HTTP/1.1 200 Connection Established\r\n\r\n",
            bytes(client.sent),
        )
        self.assertNotIn("evil.example", record.to_json())

    def test_blocking_timeout_closes_both_sides_and_emits_one_audit(self) -> None:
        clock = FakeClock()
        client = FakeSocket((connect_request(), TimeoutError("raw secret")))
        upstream = FakeSocket()
        audits = []

        records = CodexEgressServer(
            FakeListenSocket((client,)),
            resolver=FakeResolver(),
            dialer=FakeDialer((upstream,)),
            clock=clock,
            relay_waiter=FakeRelayWaiter(clock),
            audit_sink=audits.append,
        ).run()

        self.assertEqual(1, len(records))
        self.assertEqual(1, len(audits))
        self.assertEqual("egress-server-timeout", records[0].failure_code)
        self.assertNotIn("raw secret", records[0].to_json())
        self.assertTrue(client.closed)
        self.assertTrue(upstream.closed)

    def test_relay_idle_timeout_uses_meter_audit_and_cleans_up(self) -> None:
        clock = FakeClock()
        hello = tls_client_hello()
        client = FakeSocket((connect_request(), hello))
        upstream = FakeSocket()
        policy = EgressPolicy(
            limits=EgressLimits(
                max_connections=1,
                idle_timeout_ms=1,
                wall_timeout_ms=100,
            )
        )

        (record,) = CodexEgressServer(
            FakeListenSocket((client,)),
            resolver=FakeResolver(),
            dialer=FakeDialer((upstream,)),
            policy=policy,
            clock=clock,
            relay_waiter=NeverReadyWaiter(clock, 0.01),
        ).run()

        self.assertEqual("egress-idle-time-limit-exceeded", record.failure_code)
        self.assertEqual("blocked", record.outcome)
        self.assertTrue(record.sni_verified)
        self.assertFalse(record.capture_complete)
        self.assertTrue(client.closed)
        self.assertTrue(upstream.closed)

    def test_connect_and_relay_share_one_absolute_wall_deadline(self) -> None:
        clock = FakeClock()
        client = AdvancingFakeSocket(
            (connect_request(), tls_client_hello()),
            clock=clock,
            recv_advance=0.04,
        )
        upstream = FakeSocket(peer="8.8.8.8")
        policy = EgressPolicy(
            limits=EgressLimits(
                max_connections=1,
                idle_timeout_ms=50,
                wall_timeout_ms=100,
            )
        )

        (record,) = CodexEgressServer(
            FakeListenSocket((client,)),
            resolver=FakeResolver(),
            dialer=FakeDialer((upstream,)),
            policy=policy,
            clock=clock,
            relay_waiter=NeverReadyWaiter(clock, 1.0),
        ).run()

        self.assertEqual("egress-wall-time-limit-exceeded", record.failure_code)
        self.assertLessEqual(clock.value, 0.101)
        self.assertGreaterEqual(record.duration_ms, 99)

    def test_exact_directional_byte_ceilings_allow_clean_eof(self) -> None:
        hello = tls_client_hello()
        request_ciphertext = b"request-at-exact-ceiling"
        response_ciphertext = b"response-at-exact-ceiling"
        policy = EgressPolicy(
            limits=EgressLimits(
                max_connections=1,
                max_client_to_upstream_bytes=len(hello) + len(request_ciphertext),
                max_upstream_to_client_bytes=len(response_ciphertext),
            )
        )
        client = FakeSocket(
            (connect_request(), hello, request_ciphertext, b""),
        )
        upstream = FakeSocket((response_ciphertext, b""), peer="8.8.8.8")
        clock = FakeClock()

        (record,) = CodexEgressServer(
            FakeListenSocket((client,)),
            resolver=FakeResolver(),
            dialer=FakeDialer((upstream,)),
            policy=policy,
            clock=clock,
            relay_waiter=FakeRelayWaiter(clock),
        ).run()

        self.assertEqual("completed", record.outcome)
        self.assertEqual(
            len(hello) + len(request_ciphertext), record.client_to_upstream_bytes
        )
        self.assertEqual(len(response_ciphertext), record.upstream_to_client_bytes)

    def test_first_byte_over_directional_ceiling_is_blocked(self) -> None:
        clock = FakeClock()
        hello = tls_client_hello()
        client = FakeSocket((connect_request(), hello, b"x"))
        upstream = FakeSocket(peer="8.8.8.8")
        policy = EgressPolicy(
            limits=EgressLimits(
                max_connections=1,
                max_client_to_upstream_bytes=len(hello),
            )
        )

        (record,) = CodexEgressServer(
            FakeListenSocket((client,)),
            resolver=FakeResolver(),
            dialer=FakeDialer((upstream,)),
            policy=policy,
            clock=clock,
            relay_waiter=FakeRelayWaiter(clock),
        ).run()

        self.assertEqual("egress-client-byte-limit-exceeded", record.failure_code)
        self.assertFalse(record.capture_complete)

    def test_server_is_one_shot_and_does_nothing_before_explicit_run(self) -> None:
        listener = FakeListenSocket(())
        resolver = FakeResolver()
        server = CodexEgressServer(listener, resolver=resolver, dialer=FakeDialer(()))

        self.assertEqual([], resolver.calls)
        self.assertEqual(0, listener.accept_calls)
        self.assertFalse(listener.closed)
        self.assertEqual((), server.run())
        self.assertEqual(1, len(resolver.calls))
        self.assertTrue(listener.closed)
        with self.assertRaisesRegex(
            CodexEgressProxyError, "egress-server-already-started"
        ):
            server.run()


class StdlibBoundaryTests(unittest.TestCase):
    def test_real_socketpair_selector_relays_half_closes(self) -> None:
        client_app, proxy_client = socket.socketpair()
        proxy_upstream_raw, upstream_app = socket.socketpair()
        for endpoint in (client_app, upstream_app):
            endpoint.settimeout(5.0)
        proxy_upstream = PeerOverrideSocket(proxy_upstream_raw, "8.8.8.8")
        listener = FakeListenSocket((proxy_client,))
        server_result: list[object] = []
        server_error: list[BaseException] = []

        def serve() -> None:
            try:
                server_result.extend(
                    run_codex_egress_server(
                        listener,
                        resolver=FakeResolver(),
                        dialer=FakeDialer((proxy_upstream,)),
                    )
                )
            except BaseException as error:  # test boundary must surface thread errors
                server_error.append(error)

        received_by_upstream = bytearray()

        def upstream_peer() -> None:
            while True:
                chunk = upstream_app.recv(4096)
                if not chunk:
                    break
                received_by_upstream.extend(chunk)
            upstream_app.sendall(b"real-selector-response")
            upstream_app.shutdown(socket.SHUT_WR)

        server_thread = threading.Thread(target=serve)
        upstream_thread = threading.Thread(target=upstream_peer)
        server_thread.start()
        upstream_thread.start()
        try:
            client_app.sendall(connect_request())
            established = bytearray()
            while b"\r\n\r\n" not in established:
                established.extend(client_app.recv(4096))
            self.assertEqual(
                b"HTTP/1.1 200 Connection Established\r\n\r\n",
                bytes(established),
            )
            outbound = tls_client_hello() + b"real-selector-request"
            client_app.sendall(outbound)
            client_app.shutdown(socket.SHUT_WR)
            inbound = bytearray()
            while True:
                chunk = client_app.recv(4096)
                if not chunk:
                    break
                inbound.extend(chunk)
        finally:
            client_app.close()
            upstream_app.close()
            server_thread.join(5.0)
            upstream_thread.join(5.0)

        self.assertFalse(server_thread.is_alive())
        self.assertFalse(upstream_thread.is_alive())
        self.assertEqual([], server_error)
        self.assertEqual(outbound, bytes(received_by_upstream))
        self.assertEqual(b"real-selector-response", bytes(inbound))
        self.assertEqual(1, len(server_result))
        self.assertEqual("completed", server_result[0].outcome)

    def test_resolver_returns_every_getaddrinfo_answer_from_one_lookup(self) -> None:
        answers = [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("8.8.8.8", 443),
            ),
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("2606:4700:4700::1111", 443, 0, 0),
            ),
        ]
        with patch.object(
            server_module.socket, "getaddrinfo", return_value=answers
        ) as lookup:
            result = StdlibEgressResolver()(CODEX_EGRESS_HOST, 443)

        self.assertEqual(("8.8.8.8", "2606:4700:4700::1111"), result)
        lookup.assert_called_once_with(
            CODEX_EGRESS_HOST,
            443,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )

    def test_literal_dialer_uses_family_socket_without_getaddrinfo_or_retry(
        self,
    ) -> None:
        connection = FakeSocket()
        with (
            patch.object(
                server_module.socket, "socket", return_value=connection
            ) as factory,
            patch.object(
                server_module.socket,
                "getaddrinfo",
                side_effect=AssertionError("second resolution forbidden"),
            ),
        ):
            result = StdlibLiteralDialer()("8.8.8.8", 443, 1234)

        self.assertIs(connection, result)
        factory.assert_called_once_with(
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
        )
        self.assertEqual([("8.8.8.8", 443)], connection.connect_calls)
        self.assertEqual([1.234], connection.timeouts)
        self.assertFalse(connection.closed)


if __name__ == "__main__":
    unittest.main()
