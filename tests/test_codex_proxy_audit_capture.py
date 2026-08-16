from __future__ import annotations

import hashlib
import json
import unittest

from research_workbench.adapters.codex_egress_proxy import EgressAuditRecord
from research_workbench.adapters.codex_proxy_audit_capture import (
    CODEX_PROXY_AUDIT_CAPTURE_LIVE_READY,
    CODEX_PROXY_AUDIT_CAPTURE_OWNER_BOUNDARY,
    CODEX_PROXY_AUDIT_CAPTURE_SCHEMA,
    CodexProxyAuditCapture,
    CodexProxyAuditCaptureBinding,
    CodexProxyAuditCaptureError,
    CodexProxyAuditCaptureEvidence,
    CodexProxyAuditCaptureLifecycle,
    CodexProxyAuditCaptureLimits,
    reject_live_proxy_audit_attach,
)

CONTAINER_ID = "a" * 64
OTHER_CONTAINER_ID = "b" * 64
POLICY_SHA256 = "c" * 64
RESOLUTION_SHA256 = "d" * 64
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def audit_record(
    *,
    policy_sha256: str = POLICY_SHA256,
    resolution_sha256: str = RESOLUTION_SHA256,
    connection_sequence: int = 1,
    outcome: str = "completed",
    capture_complete: bool = True,
    failure_code: str | None = None,
) -> EgressAuditRecord:
    completed = outcome == "completed"
    client_payload = b"client" if completed else b""
    upstream_payload = b"upstream" if completed else b""
    return EgressAuditRecord(
        policy_sha256=policy_sha256,
        resolution_sha256=resolution_sha256,
        selected_address_index=0,
        client_hello_sha256="e" * 64,
        connection_sequence=connection_sequence,
        outcome=outcome,
        client_to_upstream_bytes=len(client_payload),
        upstream_to_client_bytes=len(upstream_payload),
        client_to_upstream_sha256=hashlib.sha256(client_payload).hexdigest(),
        upstream_to_client_sha256=hashlib.sha256(upstream_payload).hexdigest(),
        duration_ms=4,
        sni_verified=completed,
        capture_complete=capture_complete,
        failure_code=(None if completed else failure_code or "egress-server-timeout"),
    )


def audit_jsonl(**kwargs: object) -> bytes:
    return f"{audit_record(**kwargs).to_json()}\n".encode("ascii")


def binding() -> CodexProxyAuditCaptureBinding:
    return CodexProxyAuditCaptureBinding(
        container_id=CONTAINER_ID,
        policy_sha256=POLICY_SHA256,
        resolution_sha256=RESOLUTION_SHA256,
    )


def lifecycle(
    *,
    container_id: str = CONTAINER_ID,
    exit_code: int = 0,
    container_terminal: bool = True,
    stdout_eof: bool = True,
    capture_complete: bool = True,
    capture_closed_after_terminal: bool = True,
) -> CodexProxyAuditCaptureLifecycle:
    return CodexProxyAuditCaptureLifecycle(
        container_id=container_id,
        exit_code=exit_code,
        container_terminal=container_terminal,
        stdout_eof=stdout_eof,
        capture_complete=capture_complete,
        capture_closed_after_terminal=capture_closed_after_terminal,
    )


def new_capture(
    *,
    active_binding: CodexProxyAuditCaptureBinding | None = None,
    limits: CodexProxyAuditCaptureLimits | None = None,
    deadline_seconds: float = 10.0,
) -> CodexProxyAuditCapture:
    return CodexProxyAuditCapture(
        active_binding or binding(),
        started_at=100.0,
        deadline_seconds=deadline_seconds,
        limits=limits,
    )


class PoisonValue:
    def __getattribute__(self, name: str) -> object:
        raise AssertionError(f"live input inspected: {name}")


class CodexProxyAuditCaptureSuccessTests(unittest.TestCase):
    def test_fragmented_exact_one_record_produces_hash_bound_redacted_evidence(
        self,
    ) -> None:
        payload = audit_jsonl()
        capture = new_capture()
        offsets = (1, 2, 7, 19, len(payload) - 1, len(payload))
        start = 0
        for index, end in enumerate(offsets, start=1):
            capture.feed(payload[start:end], now=100.0 + index / 10)
            start = end

        evidence = capture.finalize(lifecycle(), now=101.0)

        self.assertIsInstance(evidence, CodexProxyAuditCaptureEvidence)
        self.assertEqual(CODEX_PROXY_AUDIT_CAPTURE_SCHEMA, evidence.schema)
        self.assertEqual(
            CODEX_PROXY_AUDIT_CAPTURE_OWNER_BOUNDARY,
            evidence.owner_boundary,
        )
        self.assertFalse(evidence.live_ready)
        self.assertTrue(evidence.stream_capture_complete)
        self.assertTrue(evidence.audit_capture_complete)
        self.assertEqual("caller-attested", evidence.lifecycle_assurance)
        self.assertTrue(evidence.terminal)
        self.assertEqual(1, evidence.record_count)
        self.assertEqual(len(payload), evidence.captured_bytes)
        self.assertEqual(len(payload) - 1, evidence.line_bytes)
        self.assertEqual(10_000, evidence.deadline_ms)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), evidence.stream_sha256)
        self.assertEqual(
            hashlib.sha256(payload[:-1]).hexdigest(),
            evidence.audit_record_sha256,
        )
        self.assertEqual(POLICY_SHA256, evidence.audit_record.policy_sha256)
        projection = evidence.to_mapping()
        self.assertNotIn("raw", projection)
        self.assertNotIn("stdout", projection)
        self.assertEqual(
            hashlib.sha256(
                json.dumps(
                    projection,
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("ascii")
            ).hexdigest(),
            evidence.sha256,
        )

    def test_blocked_record_requires_and_accepts_exit_one(self) -> None:
        capture = new_capture()
        capture.feed(
            audit_jsonl(outcome="blocked", capture_complete=False),
            now=100.1,
        )
        evidence = capture.finalize(lifecycle(exit_code=1), now=100.2)
        self.assertEqual("blocked", evidence.audit_record.outcome)
        self.assertFalse(evidence.audit_record.capture_complete)
        self.assertFalse(evidence.audit_capture_complete)
        self.assertTrue(evidence.stream_capture_complete)

    def test_live_attach_is_disabled_before_inspecting_inputs(self) -> None:
        self.assertFalse(CODEX_PROXY_AUDIT_CAPTURE_LIVE_READY)
        with self.assertRaisesRegex(
            CodexProxyAuditCaptureError,
            "proxy-audit-capture-live-disabled",
        ):
            reject_live_proxy_audit_attach(PoisonValue(), environment=PoisonValue())

    def test_evidence_cannot_be_constructed_by_a_caller(self) -> None:
        with self.assertRaisesRegex(TypeError, "produced only by validation"):
            CodexProxyAuditCaptureEvidence()


class CodexProxyAuditCaptureStreamFailureTests(unittest.TestCase):
    def assert_feed_error(
        self,
        payloads: tuple[bytes, ...],
        code: str,
        *,
        limits: CodexProxyAuditCaptureLimits | None = None,
    ) -> CodexProxyAuditCapture:
        capture = new_capture(limits=limits)
        with self.assertRaisesRegex(CodexProxyAuditCaptureError, code):
            for index, payload in enumerate(payloads, start=1):
                capture.feed(payload, now=100.0 + index / 10)
        with self.assertRaisesRegex(
            CodexProxyAuditCaptureError,
            "proxy-audit-capture-already-closed",
        ):
            capture.feed(b"", now=101.0)
        return capture

    def test_invalid_utf8_across_chunks_and_invalid_json_fail_closed(self) -> None:
        self.assert_feed_error(
            (b'{"schema":"', b"\xc3", b"(\n"),
            "proxy-audit-capture-utf8-invalid",
        )
        self.assert_feed_error(
            (b"{not-json}\n",),
            "proxy-audit-capture-json-invalid",
        )

    def test_blank_duplicate_key_duplicate_and_extra_record_fail_closed(self) -> None:
        self.assert_feed_error(
            (b"\n",),
            "proxy-audit-capture-blank-line",
        )
        self.assert_feed_error(
            (b'{"schema":"one","schema":"two"}\n',),
            "proxy-audit-capture-json-key-duplicate",
        )
        payload = audit_jsonl()
        self.assert_feed_error(
            (payload + payload,),
            "proxy-audit-capture-record-duplicate",
        )
        self.assert_feed_error(
            (payload + b"{}\n",),
            "proxy-audit-capture-extra-record",
        )

    def test_unknown_schema_unknown_field_and_missing_field_fail_closed(self) -> None:
        document = audit_record().to_mapping()
        document["schema"] = "unknown-audit/9.9"
        self.assert_feed_error(
            (_canonical_line(document),),
            "proxy-audit-capture-schema-mismatch",
        )

        document = audit_record().to_mapping()
        document["unexpected"] = False
        self.assert_feed_error(
            (_canonical_line(document),),
            "proxy-audit-capture-unknown-field",
        )

        document = audit_record().to_mapping()
        del document["duration_ms"]
        self.assert_feed_error(
            (_canonical_line(document),),
            "proxy-audit-capture-field-set-invalid",
        )

    def test_sensitive_field_is_rejected_without_value_in_error_or_state(self) -> None:
        secret = "must-not-escape"
        document = audit_record().to_mapping()
        document["authorization"] = secret
        capture = new_capture()
        with self.assertRaises(CodexProxyAuditCaptureError) as caught:
            capture.feed(_canonical_line(document), now=100.1)
        self.assertEqual("proxy-audit-capture-sensitive-field", caught.exception.code)
        visible = repr(caught.exception) + repr(capture)
        self.assertNotIn(secret, visible)
        self.assertNotIn("authorization", visible)

    def test_line_total_and_deadline_limits_fail_closed(self) -> None:
        self.assert_feed_error(
            (b"12345678",),
            "proxy-audit-capture-line-byte-limit-exceeded",
            limits=CodexProxyAuditCaptureLimits(
                max_total_bytes=8,
                max_line_bytes=7,
            ),
        )
        self.assert_feed_error(
            (b"1234567", b"\nX"),
            "proxy-audit-capture-total-byte-limit-exceeded",
            limits=CodexProxyAuditCaptureLimits(
                max_total_bytes=8,
                max_line_bytes=7,
            ),
        )

        capture = new_capture(deadline_seconds=1.0)
        with self.assertRaisesRegex(
            CodexProxyAuditCaptureError,
            "proxy-audit-capture-deadline-exceeded",
        ):
            capture.feed(b"", now=101.0)

    def test_missing_record_and_terminal_newline_are_distinct(self) -> None:
        capture = new_capture()
        with self.assertRaisesRegex(
            CodexProxyAuditCaptureError,
            "proxy-audit-capture-record-missing",
        ):
            capture.finalize(lifecycle(), now=100.1)

        capture = new_capture()
        capture.feed(audit_jsonl()[:-1], now=100.1)
        with self.assertRaisesRegex(
            CodexProxyAuditCaptureError,
            "proxy-audit-capture-terminal-newline-missing",
        ):
            capture.finalize(lifecycle(), now=100.2)

        capture = new_capture()
        capture.feed(b"\xc3", now=100.1)
        with self.assertRaisesRegex(
            CodexProxyAuditCaptureError,
            "proxy-audit-capture-utf8-invalid",
        ):
            capture.finalize(lifecycle(), now=100.2)


class CodexProxyAuditCaptureBindingAndTerminalTests(unittest.TestCase):
    def assert_record_error(self, document: dict[str, object], code: str) -> None:
        capture = new_capture()
        with self.assertRaisesRegex(CodexProxyAuditCaptureError, code):
            capture.feed(_canonical_line(document), now=100.1)

    def test_policy_resolution_and_sequence_must_match_binding(self) -> None:
        cases = (
            (
                audit_jsonl(policy_sha256="f" * 64),
                "proxy-audit-capture-policy-mismatch",
            ),
            (
                audit_jsonl(resolution_sha256="f" * 64),
                "proxy-audit-capture-resolution-mismatch",
            ),
            (
                audit_jsonl(connection_sequence=2),
                "proxy-audit-capture-sequence-mismatch",
            ),
        )
        for payload, code in cases:
            with self.subTest(code=code):
                capture = new_capture()
                with self.assertRaisesRegex(CodexProxyAuditCaptureError, code):
                    capture.feed(payload, now=100.1)

    def test_terminal_capture_and_identity_matrix_is_fail_closed(self) -> None:
        cases = (
            (
                lifecycle(container_id=OTHER_CONTAINER_ID),
                "proxy-audit-capture-container-identity-mismatch",
            ),
            (
                lifecycle(container_terminal=False),
                "proxy-audit-capture-terminal-unverified",
            ),
            (
                lifecycle(stdout_eof=False),
                "proxy-audit-capture-stdout-eof-unverified",
            ),
            (
                lifecycle(capture_complete=False),
                "proxy-audit-capture-incomplete",
            ),
            (
                lifecycle(capture_closed_after_terminal=False),
                "proxy-audit-capture-close-order-unverified",
            ),
            (
                lifecycle(exit_code=1),
                "proxy-audit-capture-exit-mismatch",
            ),
        )
        for observed_lifecycle, code in cases:
            with self.subTest(code=code):
                capture = new_capture()
                capture.feed(audit_jsonl(), now=100.1)
                with self.assertRaisesRegex(CodexProxyAuditCaptureError, code):
                    capture.finalize(observed_lifecycle, now=100.2)

    def test_failed_record_cannot_claim_zero_exit(self) -> None:
        capture = new_capture()
        capture.feed(
            audit_jsonl(outcome="failed", capture_complete=False),
            now=100.1,
        )
        with self.assertRaisesRegex(
            CodexProxyAuditCaptureError,
            "proxy-audit-capture-exit-mismatch",
        ):
            capture.finalize(lifecycle(exit_code=0), now=100.2)

    def test_known_producer_clock_failure_is_preserved_as_blocked(self) -> None:
        capture = new_capture()
        capture.feed(
            audit_jsonl(
                outcome="blocked",
                capture_complete=False,
                failure_code="egress-clock-regressed",
            ),
            now=100.1,
        )
        evidence = capture.finalize(lifecycle(exit_code=1), now=100.2)
        self.assertEqual("blocked", evidence.audit_record.outcome)
        self.assertEqual("egress-clock-regressed", evidence.audit_record.failure_code)

    def test_producer_matrix_limits_and_failure_codes_are_closed(self) -> None:
        document = audit_record().to_mapping()
        document["sni_verified"] = False
        self.assert_record_error(
            document,
            "proxy-audit-capture-completed-matrix-invalid",
        )

        document = audit_record(
            outcome="client-closed",
            capture_complete=False,
            failure_code="egress-client-relay-closed",
        ).to_mapping()
        self.assert_record_error(
            document,
            "proxy-audit-capture-outcome-unreachable",
        )

        document = audit_record(
            outcome="blocked",
            capture_complete=False,
            failure_code="mustnotescape",
        ).to_mapping()
        self.assert_record_error(
            document,
            "proxy-audit-capture-failure-matrix-invalid",
        )

        document = audit_record().to_mapping()
        document["client_to_upstream_bytes"] = 10**100
        self.assert_record_error(
            document,
            "proxy-audit-capture-producer-limit-exceeded",
        )

        document = audit_record().to_mapping()
        document["client_to_upstream_bytes"] = 0
        self.assert_record_error(
            document,
            "proxy-audit-capture-byte-hash-inconsistent",
        )


def _canonical_line(document: object) -> bytes:
    return (
        json.dumps(
            document,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        + b"\n"
    )


if __name__ == "__main__":
    unittest.main()
