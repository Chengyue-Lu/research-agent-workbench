from __future__ import annotations

import hashlib
import json
import socket
import unittest
from pathlib import Path

from research_workbench.adapters.codex_egress_container import (
    CODEX_EGRESS_PROXY_CONTAINER_LIVE_READY,
    CODEX_EGRESS_PROXY_LISTEN_PORT,
    CodexEgressContainerConfig,
    CodexEgressContainerError,
    JsonlAuditSink,
    RuntimePeerBoundListener,
    create_bound_listener,
    main,
    parse_container_arguments,
    serve_codex_egress_proxy,
    validate_credential_free_environment,
)
from research_workbench.adapters.codex_egress_proxy import (
    CodexEgressProxyError,
    EgressAuditRecord,
)


def audit_record(
    *, outcome: str = "completed", capture_complete: bool = True
) -> EgressAuditRecord:
    empty_hash = hashlib.sha256(b"").hexdigest()
    return EgressAuditRecord(
        policy_sha256="a" * 64,
        resolution_sha256="b" * 64,
        selected_address_index=0,
        client_hello_sha256="c" * 64,
        connection_sequence=1,
        outcome=outcome,
        client_to_upstream_bytes=0,
        upstream_to_client_bytes=0,
        client_to_upstream_sha256=empty_hash,
        upstream_to_client_sha256=empty_hash,
        duration_ms=1,
        sni_verified=outcome == "completed",
        capture_complete=capture_complete,
        failure_code=None if outcome == "completed" else "stable-failure",
    )


class BytesWriter:
    def __init__(self) -> None:
        self.payloads: list[bytes] = []

    def __call__(self, payload: bytes) -> int:
        self.payloads.append(payload)
        return len(payload)


class FakeClient:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeListener:
    def __init__(
        self,
        *,
        accepted: tuple[object, object] | BaseException | None = None,
        bound_endpoint: object = ("172.20.0.3", CODEX_EGRESS_PROXY_LISTEN_PORT),
    ) -> None:
        self.accepted = accepted
        self.bound_endpoint = bound_endpoint
        self.bind_calls: list[tuple[str, int]] = []
        self.listen_calls: list[int] = []
        self.options: list[tuple[int, int, int]] = []
        self.timeouts: list[float] = []
        self.closed = False

    def setsockopt(self, level: int, option: int, value: int) -> None:
        self.options.append((level, option, value))

    def bind(self, endpoint: tuple[str, int]) -> None:
        self.bind_calls.append(endpoint)

    def listen(self, backlog: int) -> None:
        self.listen_calls.append(backlog)

    def getsockname(self) -> object:
        return self.bound_endpoint

    def accept(self) -> tuple[object, object]:
        if isinstance(self.accepted, BaseException):
            raise self.accepted
        if self.accepted is None:
            raise TimeoutError()
        return self.accepted

    def settimeout(self, timeout: float) -> None:
        self.timeouts.append(timeout)

    def close(self) -> None:
        self.closed = True


class CodexEgressContainerTests(unittest.TestCase):
    def test_live_wiring_remains_explicitly_disabled(self) -> None:
        self.assertFalse(CODEX_EGRESS_PROXY_CONTAINER_LIVE_READY)

    def test_arguments_require_explicit_serve_and_both_frozen_addresses(self) -> None:
        config = parse_container_arguments(
            (
                "--serve",
                "--listen-ip",
                "172.20.0.3",
                "--runtime-peer-ip",
                "172.20.0.2",
            )
        )

        self.assertEqual("172.20.0.3", config.listen_ip)
        self.assertEqual("172.20.0.2", config.runtime_peer_ip)
        self.assertEqual(CODEX_EGRESS_PROXY_LISTEN_PORT, config.listen_port)
        for invalid in (
            (),
            ("--probe",),
            ("--serve",),
            ("--serve", "--listen-ip", "172.20.0.3"),
            (
                "--serve",
                "--listen-ip",
                "172.20.0.3",
                "--listen-ip",
                "172.20.0.4",
                "--runtime-peer-ip",
                "172.20.0.2",
            ),
            (
                "--serve",
                "--listen-ip=172.20.0.3",
                "--runtime-peer-ip",
                "172.20.0.2",
            ),
        ):
            with (
                self.subTest(invalid=invalid),
                self.assertRaises(CodexEgressContainerError),
            ):
                parse_container_arguments(invalid)

    def test_addresses_are_distinct_canonical_rfc1918_ipv4_literals(self) -> None:
        for invalid in (
            "0.0.0.0",
            "::",
            "::1",
            "127.0.0.1",
            "8.8.8.8",
            "169.254.1.1",
            "172.020.0.3",
            "172.32.0.3",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                CodexEgressContainerConfig(invalid, "172.20.0.2")
        with self.assertRaises(ValueError):
            CodexEgressContainerConfig("172.20.0.2", "172.20.0.2")

    def test_listener_binds_and_attests_only_the_frozen_internal_endpoint(self) -> None:
        raw = FakeListener()
        calls: list[tuple[int, int, int]] = []

        def factory(family: int, kind: int, protocol: int) -> FakeListener:
            calls.append((family, kind, protocol))
            return raw

        wrapped = create_bound_listener(
            CodexEgressContainerConfig("172.20.0.3", "172.20.0.2"),
            socket_factory=factory,
        )

        self.assertIsInstance(wrapped, RuntimePeerBoundListener)
        self.assertEqual(
            [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)], calls
        )
        self.assertEqual([("172.20.0.3", 3128)], raw.bind_calls)
        self.assertEqual([1], raw.listen_calls)
        self.assertEqual([(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)], raw.options)

    def test_bind_attestation_failure_closes_listener_without_raw_details(self) -> None:
        raw = FakeListener(bound_endpoint=("0.0.0.0", 3128))
        with self.assertRaisesRegex(
            CodexEgressContainerError, "proxy-listener-bind-attestation-failed"
        ):
            create_bound_listener(
                CodexEgressContainerConfig("172.20.0.3", "172.20.0.2"),
                socket_factory=lambda *_: raw,
            )
        self.assertTrue(raw.closed)

    def test_only_exact_runtime_peer_is_exposed_to_server(self) -> None:
        allowed_client = FakeClient()
        allowed = RuntimePeerBoundListener(
            FakeListener(accepted=(allowed_client, ("172.20.0.2", 49000))),
            "172.20.0.2",
        )
        observed, redacted_peer = allowed.accept()
        self.assertIs(allowed_client, observed)
        self.assertEqual(("runtime-peer", 0), redacted_peer)

        rejected_client = FakeClient()
        rejected = RuntimePeerBoundListener(
            FakeListener(accepted=(rejected_client, ("172.20.0.4", 49000))),
            "172.20.0.2",
        )
        placeholder, redacted_peer = rejected.accept()
        self.assertTrue(rejected_client.closed)
        self.assertEqual(("rejected-peer", 0), redacted_peer)
        with self.assertRaisesRegex(
            CodexEgressProxyError, "egress-runtime-peer-mismatch"
        ):
            placeholder.recv(1)

    def test_rejected_runtime_peer_emits_exactly_one_redacted_audit_without_dial(
        self,
    ) -> None:
        rejected_client = FakeClient()
        raw = FakeListener(
            accepted=(rejected_client, ("172.20.0.4", 49000)),
        )
        writer = BytesWriter()
        dial_calls: list[object] = []

        def dialer(*args: object) -> object:
            dial_calls.append(args)
            raise AssertionError("mismatched runtime peer must not dial")

        records = serve_codex_egress_proxy(
            CodexEgressContainerConfig("172.20.0.3", "172.20.0.2"),
            environ={"PATH": "/usr/local/bin:/usr/bin"},
            audit_write=writer,
            socket_factory=lambda *_: raw,
            resolver=lambda host, port: ("8.8.8.8",),
            dialer=dialer,
        )

        self.assertEqual(1, len(records))
        self.assertEqual("egress-runtime-peer-mismatch", records[0].failure_code)
        self.assertEqual([], dial_calls)
        self.assertTrue(rejected_client.closed)
        self.assertTrue(raw.closed)
        self.assertEqual(1, len(writer.payloads))
        self.assertEqual(1, writer.payloads[0].count(b"\n"))
        audit = json.loads(writer.payloads[0])
        self.assertEqual("blocked", audit["outcome"])
        self.assertNotIn("172.20.0.2", writer.payloads[0].decode("ascii"))
        self.assertNotIn("172.20.0.4", writer.payloads[0].decode("ascii"))
        self.assertNotIn("8.8.8.8", writer.payloads[0].decode("ascii"))

    def test_audit_sink_rejects_duplicate_or_partial_output(self) -> None:
        writer = BytesWriter()
        sink = JsonlAuditSink(writer)
        record = audit_record()
        sink(record)
        self.assertEqual(1, sink.record_count)
        self.assertEqual(1, len(writer.payloads))
        with self.assertRaisesRegex(
            CodexEgressContainerError, "proxy-audit-sequence-duplicate"
        ):
            sink(record)

        partial = JsonlAuditSink(lambda payload: len(payload) - 1)
        with self.assertRaisesRegex(
            CodexEgressContainerError, "proxy-audit-write-incomplete"
        ):
            partial(record)
        self.assertEqual(0, partial.record_count)

    def test_provider_credential_environment_is_rejected_without_name_or_value(
        self,
    ) -> None:
        validate_credential_free_environment({"PATH": "/usr/bin", "LANG": "C.UTF-8"})
        secret = "must-not-escape"
        socket_called = False

        def forbidden_socket(*args: object, **kwargs: object):
            nonlocal socket_called
            socket_called = True
            raise AssertionError("credential check must occur before socket creation")

        config = CodexEgressContainerConfig(
            listen_ip="172.20.0.3", runtime_peer_ip="172.20.0.2"
        )
        with self.assertRaisesRegex(
            CodexEgressContainerError, "proxy-credential-environment-forbidden"
        ):
            serve_codex_egress_proxy(
                config,
                environ={"RWB_CODEX_CODING_PLAN_CREDENTIAL": secret},
                audit_write=BytesWriter(),
                socket_factory=forbidden_socket,
            )
        self.assertFalse(socket_called)
        for name in ("OPENAI_AUTHORIZATION", "AWS_ACCESS_KEY_ID", "NO_COLOR"):
            with (
                self.subTest(name=name),
                self.assertRaisesRegex(
                    CodexEgressContainerError,
                    "proxy-credential-environment-forbidden",
                ),
            ):
                validate_credential_free_environment({name: secret})

    def test_direct_serve_requires_injected_resolver_and_dialer_before_socket(
        self,
    ) -> None:
        socket_called = False

        def forbidden_socket(*args: object, **kwargs: object):
            nonlocal socket_called
            socket_called = True
            raise AssertionError("missing network boundary must block before socket")

        with self.assertRaisesRegex(
            CodexEgressContainerError,
            "proxy-live-network-boundary-unavailable",
        ):
            serve_codex_egress_proxy(
                CodexEgressContainerConfig("172.20.0.3", "172.20.0.2"),
                environ={"PATH": "/usr/local/bin:/usr/bin"},
                audit_write=BytesWriter(),
                socket_factory=forbidden_socket,
            )
        self.assertFalse(socket_called)

    def test_main_blocks_before_reading_argv_environment_or_serve(self) -> None:
        errors = BytesWriter()

        class Poison:
            def __getattribute__(self, name: str) -> object:
                raise AssertionError(f"live-disabled entrypoint touched {name}")

        def poison_serve(*args: object, **kwargs: object):
            raise AssertionError("live-disabled entrypoint called serve")

        self.assertEqual(
            2,
            main(
                Poison(),  # type: ignore[arg-type]
                environ=Poison(),  # type: ignore[arg-type]
                audit_write=Poison(),  # type: ignore[arg-type]
                error_write=errors,
                serve=poison_serve,
            ),
        )
        self.assertEqual([b"proxy-live-not-ready\n"], errors.payloads)


class CodexEgressProxyContainerAssetTests(unittest.TestCase):
    def test_assets_pin_base_python_empty_dependency_set_and_every_source_hash(
        self,
    ) -> None:
        project = Path(__file__).resolve().parents[1]
        root = project / "docker" / "codex-egress-proxy"
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        lock = json.loads((root / "dependencies.lock.json").read_text("ascii"))
        manifest_path = root / "asset-manifest.sha256"
        manifest = manifest_path.read_text("ascii").splitlines()
        dockerignore = root / "Dockerfile.dockerignore"
        context_policy = root / "build-context-policy.sha256"

        self.assertIn(
            "FROM python@sha256:285a71327884a4d50efbea30104473b0fa43ecefa499458899670ca30dae76e5",
            dockerfile,
        )
        self.assertEqual([], lock["distributions"])
        self.assertEqual("CPython", lock["python"]["implementation"])
        self.assertEqual("3.12.14", lock["python"]["version"])
        self.assertIn('io.research-workbench.live-ready="false"', dockerfile)
        self.assertIn("USER 65532:65532", dockerfile)
        self.assertIn('ENTRYPOINT ["/usr/local/bin/python", "-I", "-S"', dockerfile)
        self.assertNotIn("CMD", dockerfile)
        for forbidden in ("curl ", "wget ", "apk ", "pip install", "API_KEY", "TOKEN"):
            self.assertNotIn(forbidden, dockerfile)

        expected_paths = {
            "Dockerfile": root / "Dockerfile",
            "dependencies.lock.json": root / "dependencies.lock.json",
            "build-context-policy.sha256": context_policy,
            "entrypoint.py": root / "entrypoint.py",
            "codex_egress_proxy.py": project
            / "src/research_workbench/adapters/codex_egress_proxy.py",
            "codex_egress_server.py": project
            / "src/research_workbench/adapters/codex_egress_server.py",
            "codex_egress_container.py": project
            / "src/research_workbench/adapters/codex_egress_container.py",
        }
        observed: set[str] = set()
        for line in manifest:
            digest, filename = line.split("  ", 1)
            observed.add(filename)
            self.assertEqual(64, len(digest))
            self.assertEqual(
                hashlib.sha256(expected_paths[filename].read_bytes()).hexdigest(),
                digest,
            )
        self.assertEqual(set(expected_paths), observed)
        expected_context_digest, expected_context_name = (
            context_policy.read_text("ascii").strip().split("  ", 1)
        )
        self.assertEqual("Dockerfile.dockerignore", expected_context_name)
        self.assertEqual(
            hashlib.sha256(dockerignore.read_bytes()).hexdigest(),
            expected_context_digest,
        )
        ignore_text = dockerignore.read_text("utf-8")
        self.assertTrue(ignore_text.startswith("**\n"))
        self.assertNotIn("!.git", ignore_text)
        self.assertNotIn("!流程图.pdf", ignore_text)
        self.assertIn("ARG RWB_ASSET_MANIFEST_SHA256", dockerfile)
        self.assertIn("sha256sum -c /runtime/asset-manifest.sha256", dockerfile)


if __name__ == "__main__":
    unittest.main()
