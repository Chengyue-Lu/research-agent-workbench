"""Offline request-fingerprint contract for Codex Coding Plan traffic.

This Huang Yi-owned adapter validates a *decrypted* request captured by a
localhost fake Responses upstream.  It performs no socket, subprocess,
credential, Provider, Task, Trace, Handoff, Receipt, or Main State action.

The contract is deliberately stricter than the request currently emitted by
Codex 0.124.0.  A no-tool Coding Plan turn must expose no tools and must use
``tool_choice=none``.  A 2026-08-17 loopback observation showed that Codex
0.124.0 still exposed ``update_plan``, ``request_user_input``, and
``view_image`` despite the surrounding runtime's disable flags.  Those native
tools can never be approved through this contract, so that observation fails
closed rather than making the runtime live-ready.

An opaque TLS CONNECT proxy cannot apply this validator because it cannot see
the encrypted HTTP request.  A future live design therefore needs an equally
isolated pre-TLS request guard or a localhost shim inside the runtime network.
Even a passing fingerprint attests only the client request: it does not attest
the serving provider, actual model, server-side fallback, billed cost, or
research correctness.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Self

from research_workbench.adapters.codex_coding_plan import (
    CODEX_CODING_PLAN_CLI_VERSION,
    CODEX_CODING_PLAN_MODEL,
    CODEX_CODING_PLAN_REASONING_EFFORT,
)

CODEX_REQUEST_FINGERPRINT_SCHEMA = "rwb-codex-request-fingerprint/0.1"
CODEX_REQUEST_FINGERPRINT_LIVE_READY = False
CODEX_RESPONSES_METHOD = "POST"
CODEX_RESPONSES_TARGET = "/api/v1/responses"
CODEX_RESPONSES_HTTP_VERSION = "HTTP/1.1"
CODEX_RESPONSES_MAX_BODY_BYTES = 131_072
CODEX_RESPONSES_MAX_INPUT_ITEMS = 8
CODEX_RESPONSES_MAX_INPUT_TEXT_BYTES = 65_536
CODEX_RESPONSES_MAX_TOOLS = 8

CODEX_0124_OBSERVED_FORBIDDEN_NATIVE_TOOLS = (
    "update_plan",
    "request_user_input",
    "view_image",
)
CODEX_FORBIDDEN_NATIVE_TOOL_NAMES = frozenset(
    {
        *CODEX_0124_OBSERVED_FORBIDDEN_NATIVE_TOOLS,
        "apply_patch",
        "computer",
        "exec_command",
        "image_generation",
        "multi_agent",
        "shell",
        "shell_command",
        "web_search",
    }
)

CODEX_REQUEST_FINGERPRINT_LIMITATIONS = (
    "A request fingerprint attests the captured client request, not the serving provider or actual model.",
    "Lifecycle facts are caller-attested in this pure offline module until a process supervisor binds them.",
    "Exactly one claimed-terminal fake-upstream capture does not independently prove that no later retry occurred.",
    "The full body hash is capture-integrity evidence; it is not a semantic or research-correctness verdict.",
    "An opaque TLS CONNECT proxy cannot validate encrypted HTTP request fields.",
    "Codex 0.124.0 currently exposes forbidden native tools and therefore does not pass this contract.",
)

_EXPECTED_TOP_LEVEL_FIELDS = frozenset(
    {
        "client_metadata",
        "include",
        "input",
        "model",
        "parallel_tool_calls",
        "prompt_cache_key",
        "reasoning",
        "store",
        "stream",
        "tool_choice",
        "tools",
    }
)
_EXPECTED_HEADER_NAMES = frozenset(
    {
        "accept",
        "authorization",
        "content-length",
        "content-type",
        "host",
        "originator",
        "session_id",
        "user-agent",
        "x-client-request-id",
        "x-codex-turn-metadata",
        "x-codex-window-id",
    }
)
_FUNCTION_TOOL_FIELDS = frozenset(
    {"description", "name", "parameters", "strict", "type"}
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_TOOL_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_-]{0,63}\Z")
_USER_AGENT = re.compile(
    rf"codex_exec/{re.escape(CODEX_CODING_PLAN_CLI_VERSION)} "
    rf"\([^\r\n()]{{1,128}}\) unknown "
    rf"\(codex_exec; {re.escape(CODEX_CODING_PLAN_CLI_VERSION)}\)\Z"
)
_BEARER_CREDENTIAL = re.compile(r"[A-Za-z0-9._~+/\-]+=*\Z")


class CodexRequestFingerprintError(RuntimeError):
    """Stable failure that never includes headers, prompt text, or body bytes."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True, repr=False)
class CapturedCodexRequest:
    """One raw fake-upstream request with a redacted representation."""

    method: str
    target: str
    http_version: str
    headers: tuple[tuple[str, str], ...] = field(repr=False)
    body: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.method, str):
            raise TypeError("method must be text")
        if not isinstance(self.target, str):
            raise TypeError("target must be text")
        if not isinstance(self.http_version, str):
            raise TypeError("http_version must be text")
        if isinstance(self.headers, (str, bytes)) or not isinstance(
            self.headers, Sequence
        ):
            raise TypeError("headers must be a sequence of text pairs")
        normalized: list[tuple[str, str]] = []
        for pair in self.headers:
            if (
                isinstance(pair, (str, bytes))
                or not isinstance(pair, Sequence)
                or len(pair) != 2
                or not isinstance(pair[0], str)
                or not isinstance(pair[1], str)
            ):
                raise TypeError("headers must be a sequence of text pairs")
            normalized.append((pair[0], pair[1]))
        if not isinstance(self.body, bytes):
            raise TypeError("body must be bytes")
        object.__setattr__(self, "headers", tuple(normalized))

    def __repr__(self) -> str:
        return (
            "CapturedCodexRequest("
            f"header_count={len(self.headers)}, body_bytes={len(self.body)}, redacted=True)"
        )


@dataclass(frozen=True, slots=True)
class ApprovedCodexTool:
    """Exact canonical fingerprint for one explicitly approved client tool."""

    name: str
    tool_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or _TOOL_NAME.fullmatch(self.name) is None:
            raise ValueError("name must be a portable tool name")
        if self.name in CODEX_FORBIDDEN_NATIVE_TOOL_NAMES:
            raise ValueError("native Codex tools cannot be approved")
        _validate_sha256("tool_sha256", self.tool_sha256)


@dataclass(frozen=True, slots=True)
class CodexCaptureLifecycle:
    """Supervisor-produced lifecycle facts for one fake-upstream capture.

    This value does not itself observe a process.  It gives the future
    supervisor a typed, hash-bound handoff into this pure validator so the
    fingerprint never invents terminal/capture facts from two free booleans.
    """

    process_identity_sha256: str
    observed_request_count: int
    client_terminal: bool
    capture_complete: bool
    capture_closed_after_client_terminal: bool
    close_reason: str

    def __post_init__(self) -> None:
        _validate_sha256("process_identity_sha256", self.process_identity_sha256)
        if (
            isinstance(self.observed_request_count, bool)
            or not isinstance(self.observed_request_count, int)
            or self.observed_request_count < 0
        ):
            raise ValueError("observed_request_count must be a non-negative integer")
        for name in (
            "client_terminal",
            "capture_complete",
            "capture_closed_after_client_terminal",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be boolean")
        if self.close_reason not in {"client-exited", "capture-failed", "unknown"}:
            raise ValueError("close_reason is not a recognized lifecycle outcome")

    @property
    def sha256(self) -> str:
        return hashlib.sha256(
            _canonical_json_bytes(
                {
                    "capture_closed_after_client_terminal": self.capture_closed_after_client_terminal,
                    "capture_complete": self.capture_complete,
                    "client_terminal": self.client_terminal,
                    "close_reason": self.close_reason,
                    "observed_request_count": self.observed_request_count,
                    "process_identity_sha256": self.process_identity_sha256,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True, init=False)
class CodexRequestFingerprint:
    """Redacted, deterministic evidence from one complete fake-upstream capture."""

    body_sha256: str
    semantic_sha256: str
    input_sha256: str
    turn_metadata_sha256: str
    lifecycle_sha256: str
    body_bytes: int
    header_names: tuple[str, ...]
    input_item_count: int
    input_text_bytes: int
    tool_names: tuple[str, ...]
    tool_choice: str
    schema: str = field(default=CODEX_REQUEST_FINGERPRINT_SCHEMA, init=False)
    method: str = field(default=CODEX_RESPONSES_METHOD, init=False)
    target: str = field(default=CODEX_RESPONSES_TARGET, init=False)
    http_version: str = field(default=CODEX_RESPONSES_HTTP_VERSION, init=False)
    requested_model: str = field(default=CODEX_CODING_PLAN_MODEL, init=False)
    reasoning_effort: str = field(
        default=CODEX_CODING_PLAN_REASONING_EFFORT, init=False
    )
    stream: bool = field(default=True, init=False)
    store: bool = field(default=False, init=False)
    parallel_tool_calls: bool = field(default=False, init=False)
    request_count: int = field(default=1, init=False)
    retry_observed: bool = field(default=False, init=False)
    fallback_observed: bool = field(default=False, init=False)
    capture_complete: bool = field(default=True, init=False)
    client_terminal: bool = field(default=True, init=False)
    lifecycle_assurance: str = field(default="caller-attested", init=False)
    live_ready: bool = field(default=CODEX_REQUEST_FINGERPRINT_LIVE_READY, init=False)
    limitations: tuple[str, ...] = field(
        default=CODEX_REQUEST_FINGERPRINT_LIMITATIONS, init=False
    )

    def __new__(cls, *args: object, **kwargs: object) -> Self:
        del args, kwargs
        raise TypeError("CodexRequestFingerprint is produced only by validation")

    def _validate_invariants(self) -> None:
        for name in (
            "body_sha256",
            "semantic_sha256",
            "input_sha256",
            "turn_metadata_sha256",
            "lifecycle_sha256",
        ):
            _validate_sha256(name, getattr(self, name))
        if (
            isinstance(self.body_bytes, bool)
            or not isinstance(self.body_bytes, int)
            or not 0 < self.body_bytes <= CODEX_RESPONSES_MAX_BODY_BYTES
        ):
            raise ValueError("body_bytes is outside the fixed ceiling")
        if (
            isinstance(self.input_item_count, bool)
            or not isinstance(self.input_item_count, int)
            or not 1 <= self.input_item_count <= CODEX_RESPONSES_MAX_INPUT_ITEMS
        ):
            raise ValueError("input_item_count is outside the fixed ceiling")
        if (
            isinstance(self.input_text_bytes, bool)
            or not isinstance(self.input_text_bytes, int)
            or not 0 < self.input_text_bytes <= CODEX_RESPONSES_MAX_INPUT_TEXT_BYTES
        ):
            raise ValueError("input_text_bytes is outside the fixed ceiling")
        if self.header_names != tuple(sorted(_EXPECTED_HEADER_NAMES)):
            raise ValueError("header_names must equal the frozen header set")
        if len(self.tool_names) > CODEX_RESPONSES_MAX_TOOLS or len(
            set(self.tool_names)
        ) != len(self.tool_names):
            raise ValueError("tool_names must be unique and bounded")
        if any(
            not isinstance(name, str)
            or _TOOL_NAME.fullmatch(name) is None
            or name in CODEX_FORBIDDEN_NATIVE_TOOL_NAMES
            for name in self.tool_names
        ):
            raise ValueError("tool_names contains an invalid tool")
        expected_choice = "auto" if self.tool_names else "none"
        if self.tool_choice != expected_choice:
            raise ValueError("tool_choice does not match the validated tool set")
        expected_constants = {
            "capture_complete": True,
            "client_terminal": True,
            "fallback_observed": False,
            "http_version": CODEX_RESPONSES_HTTP_VERSION,
            "lifecycle_assurance": "caller-attested",
            "limitations": CODEX_REQUEST_FINGERPRINT_LIMITATIONS,
            "live_ready": CODEX_REQUEST_FINGERPRINT_LIVE_READY,
            "method": CODEX_RESPONSES_METHOD,
            "parallel_tool_calls": False,
            "reasoning_effort": CODEX_CODING_PLAN_REASONING_EFFORT,
            "request_count": 1,
            "requested_model": CODEX_CODING_PLAN_MODEL,
            "retry_observed": False,
            "schema": CODEX_REQUEST_FINGERPRINT_SCHEMA,
            "store": False,
            "stream": True,
            "target": CODEX_RESPONSES_TARGET,
        }
        if any(
            getattr(self, name) != value for name, value in expected_constants.items()
        ):
            raise ValueError("validated fingerprint constants are inconsistent")

    def to_mapping(self) -> dict[str, object]:
        """Return the complete JSON-ready redacted projection."""

        return {
            "body_bytes": self.body_bytes,
            "body_sha256": self.body_sha256,
            "capture_complete": self.capture_complete,
            "client_terminal": self.client_terminal,
            "fallback_observed": self.fallback_observed,
            "header_names": list(self.header_names),
            "http_version": self.http_version,
            "input_sha256": self.input_sha256,
            "input_item_count": self.input_item_count,
            "input_text_bytes": self.input_text_bytes,
            "lifecycle_sha256": self.lifecycle_sha256,
            "lifecycle_assurance": self.lifecycle_assurance,
            "limitations": list(self.limitations),
            "live_ready": self.live_ready,
            "method": self.method,
            "parallel_tool_calls": self.parallel_tool_calls,
            "reasoning_effort": self.reasoning_effort,
            "request_count": self.request_count,
            "requested_model": self.requested_model,
            "retry_observed": self.retry_observed,
            "schema": self.schema,
            "semantic_sha256": self.semantic_sha256,
            "store": self.store,
            "stream": self.stream,
            "target": self.target,
            "tool_choice": self.tool_choice,
            "tool_names": list(self.tool_names),
            "turn_metadata_sha256": self.turn_metadata_sha256,
        }

    def to_json(self) -> str:
        """Serialize deterministically without captured values or prompt text."""

        return json.dumps(
            self.to_mapping(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )


def canonical_codex_tool_sha256(tool: Mapping[str, object]) -> str:
    """Hash one JSON-compatible tool definition without accepting it."""

    if not isinstance(tool, Mapping):
        raise TypeError("tool must be a mapping")
    try:
        payload = _canonical_json_bytes(dict(tool))
    except (TypeError, ValueError, UnicodeError):
        raise ValueError("tool must be canonical JSON-compatible data") from None
    return hashlib.sha256(payload).hexdigest()


def canonical_codex_input_sha256(value: object) -> str:
    """Hash the complete ordered Responses ``input`` value."""

    if not isinstance(value, list):
        raise TypeError("input must be a list")
    try:
        return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()
    except (TypeError, ValueError, UnicodeError):
        raise ValueError("input must be canonical JSON-compatible data") from None


def canonical_turn_metadata_sha256(value: Mapping[str, object]) -> str:
    """Hash the complete decoded Codex turn-metadata object."""

    if not isinstance(value, Mapping):
        raise TypeError("turn metadata must be a mapping")
    try:
        return hashlib.sha256(_canonical_json_bytes(dict(value))).hexdigest()
    except (TypeError, ValueError, UnicodeError):
        raise ValueError(
            "turn metadata must be canonical JSON-compatible data"
        ) from None


def validate_codex_responses_capture(
    requests: Sequence[CapturedCodexRequest],
    *,
    expected_authority: str,
    expected_prompt_sha256: str,
    expected_input_sha256: str,
    expected_turn_metadata_sha256: str,
    lifecycle: CodexCaptureLifecycle,
    expected_tools: Sequence[ApprovedCodexTool] = (),
) -> CodexRequestFingerprint:
    """Validate exactly one terminal, no-retry fake-upstream capture.

    ``capture_complete`` must mean that the fake upstream remained active until
    the Codex child terminated.  This rejects a premature one-request snapshot
    that could otherwise miss a later retry.  The caller is responsible for
    providing that process-lifecycle observation.
    """

    if not isinstance(lifecycle, CodexCaptureLifecycle):
        raise CodexRequestFingerprintError("request-lifecycle-invalid")
    if lifecycle.capture_complete is not True:
        raise CodexRequestFingerprintError("request-capture-incomplete")
    if lifecycle.client_terminal is not True:
        raise CodexRequestFingerprintError("request-client-not-terminal")
    if lifecycle.capture_closed_after_client_terminal is not True:
        raise CodexRequestFingerprintError("request-capture-close-order-invalid")
    if lifecycle.close_reason != "client-exited":
        raise CodexRequestFingerprintError("request-client-close-reason-invalid")
    if isinstance(requests, (str, bytes)) or not isinstance(requests, Sequence):
        raise CodexRequestFingerprintError("request-capture-invalid")
    if len(requests) != 1:
        raise CodexRequestFingerprintError("request-count-not-one")
    if lifecycle.observed_request_count != len(requests):
        raise CodexRequestFingerprintError("request-lifecycle-count-mismatch")
    request = requests[0]
    if not isinstance(request, CapturedCodexRequest):
        raise CodexRequestFingerprintError("request-capture-invalid")
    authority = _validate_authority(expected_authority)
    _validate_sha256("expected_prompt_sha256", expected_prompt_sha256)
    _validate_sha256("expected_input_sha256", expected_input_sha256)
    _validate_sha256("expected_turn_metadata_sha256", expected_turn_metadata_sha256)
    tools = _validate_expected_tools(expected_tools)

    if request.method != CODEX_RESPONSES_METHOD:
        raise CodexRequestFingerprintError("request-method-mismatch")
    if request.target != CODEX_RESPONSES_TARGET:
        raise CodexRequestFingerprintError("request-target-mismatch")
    if request.http_version != CODEX_RESPONSES_HTTP_VERSION:
        raise CodexRequestFingerprintError("request-http-version-mismatch")
    headers, credential, turn_metadata_sha256 = _validate_headers(
        request,
        expected_authority=authority,
        expected_turn_metadata_sha256=expected_turn_metadata_sha256,
    )
    document = _parse_body(request.body)
    if credential.encode("utf-8") in request.body or _contains_text(
        document, credential
    ):
        raise CodexRequestFingerprintError("request-credential-exposure-detected")
    if frozenset(document) != _EXPECTED_TOP_LEVEL_FIELDS:
        raise CodexRequestFingerprintError("request-top-level-fields-mismatch")

    _validate_exact_value(document, "model", CODEX_CODING_PLAN_MODEL)
    _validate_exact_value(document, "stream", True)
    _validate_exact_value(document, "store", False)
    _validate_exact_value(document, "parallel_tool_calls", False)
    _validate_reasoning(document.get("reasoning"))
    _validate_client_metadata(document.get("client_metadata"))
    _validate_prompt_cache_key(document.get("prompt_cache_key"))
    if document.get("include") != ["reasoning.encrypted_content"]:
        raise CodexRequestFingerprintError("request-include-mismatch")

    input_item_count, input_text_bytes, input_sha256 = _validate_input(
        document.get("input"),
        expected_prompt_sha256=expected_prompt_sha256,
        expected_input_sha256=expected_input_sha256,
    )
    tool_names, tool_hashes = _validate_tool_exposure(
        document.get("tools"), expected_tools=tools
    )
    expected_tool_choice = "auto" if tools else "none"
    if document.get("tool_choice") != expected_tool_choice:
        raise CodexRequestFingerprintError("request-tool-choice-mismatch")

    semantic_projection = {
        "http_version": CODEX_RESPONSES_HTTP_VERSION,
        "include": ["reasoning.encrypted_content"],
        "input_sha256": input_sha256,
        "lifecycle_sha256": lifecycle.sha256,
        "method": CODEX_RESPONSES_METHOD,
        "model": CODEX_CODING_PLAN_MODEL,
        "parallel_tool_calls": False,
        "reasoning": {"effort": CODEX_CODING_PLAN_REASONING_EFFORT},
        "store": False,
        "stream": True,
        "target": CODEX_RESPONSES_TARGET,
        "turn_metadata_sha256": turn_metadata_sha256,
        "tool_choice": expected_tool_choice,
        "tools": [
            {"name": name, "tool_sha256": digest}
            for name, digest in zip(tool_names, tool_hashes, strict=True)
        ],
    }
    return _build_validated_fingerprint(
        body_sha256=hashlib.sha256(request.body).hexdigest(),
        semantic_sha256=hashlib.sha256(
            _canonical_json_bytes(semantic_projection)
        ).hexdigest(),
        input_sha256=input_sha256,
        turn_metadata_sha256=turn_metadata_sha256,
        lifecycle_sha256=lifecycle.sha256,
        body_bytes=len(request.body),
        header_names=tuple(sorted(headers)),
        input_item_count=input_item_count,
        input_text_bytes=input_text_bytes,
        tool_names=tool_names,
        tool_choice=expected_tool_choice,
    )


def _validate_headers(
    request: CapturedCodexRequest,
    *,
    expected_authority: str,
    expected_turn_metadata_sha256: str,
) -> tuple[dict[str, str], str, str]:
    headers: dict[str, str] = {}
    for raw_name, value in request.headers:
        try:
            raw_name.encode("ascii")
            value.encode("ascii")
        except UnicodeError:
            raise CodexRequestFingerprintError("request-header-not-ascii") from None
        name = raw_name.casefold()
        if not name or name != raw_name.lower() or name in headers:
            raise CodexRequestFingerprintError("request-header-name-invalid")
        if not value or any(
            ord(character) < 32 or ord(character) == 127 for character in value
        ):
            raise CodexRequestFingerprintError("request-header-value-invalid")
        headers[name] = value
    if frozenset(headers) != _EXPECTED_HEADER_NAMES:
        raise CodexRequestFingerprintError("request-header-fields-mismatch")
    if headers["accept"] != "text/event-stream":
        raise CodexRequestFingerprintError("request-accept-mismatch")
    if headers["content-type"] != "application/json":
        raise CodexRequestFingerprintError("request-content-type-mismatch")
    if headers["host"] != expected_authority:
        raise CodexRequestFingerprintError("request-authority-mismatch")
    if headers["originator"] != "codex_exec":
        raise CodexRequestFingerprintError("request-originator-mismatch")
    if _USER_AGENT.fullmatch(headers["user-agent"]) is None:
        raise CodexRequestFingerprintError("request-user-agent-mismatch")
    try:
        content_length = int(headers["content-length"], 10)
    except ValueError:
        raise CodexRequestFingerprintError("request-content-length-invalid") from None
    if str(content_length) != headers["content-length"] or content_length != len(
        request.body
    ):
        raise CodexRequestFingerprintError("request-content-length-mismatch")
    for name in ("session_id", "x-client-request-id", "x-codex-window-id"):
        _validate_uuid(headers[name], code="request-header-uuid-invalid")
    turn_metadata = _parse_bounded_json_object(
        headers["x-codex-turn-metadata"],
        max_bytes=8_192,
        code="request-turn-metadata-invalid",
    )
    turn_metadata_sha256 = canonical_turn_metadata_sha256(turn_metadata)
    if turn_metadata_sha256 != expected_turn_metadata_sha256:
        raise CodexRequestFingerprintError("request-turn-metadata-hash-mismatch")
    scheme, separator, credential = headers["authorization"].partition(" ")
    if (
        scheme != "Bearer"
        or separator != " "
        or _BEARER_CREDENTIAL.fullmatch(credential) is None
    ):
        raise CodexRequestFingerprintError("request-authorization-invalid")
    if _contains_text(turn_metadata, credential):
        raise CodexRequestFingerprintError("request-credential-exposure-detected")
    if any(
        credential in value
        for name, value in headers.items()
        if name != "authorization"
    ):
        raise CodexRequestFingerprintError("request-credential-exposure-detected")
    return headers, credential, turn_metadata_sha256


def _build_validated_fingerprint(
    *,
    body_sha256: str,
    semantic_sha256: str,
    input_sha256: str,
    turn_metadata_sha256: str,
    lifecycle_sha256: str,
    body_bytes: int,
    header_names: tuple[str, ...],
    input_item_count: int,
    input_text_bytes: int,
    tool_names: tuple[str, ...],
    tool_choice: str,
) -> CodexRequestFingerprint:
    """Construct only from the validator's already-derived projection.

    The public class has no constructor and there is no module-visible marker
    that a caller can pass to claim validation.
    """

    result = object.__new__(CodexRequestFingerprint)
    values: dict[str, object] = {
        "body_sha256": body_sha256,
        "semantic_sha256": semantic_sha256,
        "input_sha256": input_sha256,
        "turn_metadata_sha256": turn_metadata_sha256,
        "lifecycle_sha256": lifecycle_sha256,
        "body_bytes": body_bytes,
        "header_names": header_names,
        "input_item_count": input_item_count,
        "input_text_bytes": input_text_bytes,
        "tool_names": tool_names,
        "tool_choice": tool_choice,
        "schema": CODEX_REQUEST_FINGERPRINT_SCHEMA,
        "method": CODEX_RESPONSES_METHOD,
        "target": CODEX_RESPONSES_TARGET,
        "http_version": CODEX_RESPONSES_HTTP_VERSION,
        "requested_model": CODEX_CODING_PLAN_MODEL,
        "reasoning_effort": CODEX_CODING_PLAN_REASONING_EFFORT,
        "stream": True,
        "store": False,
        "parallel_tool_calls": False,
        "request_count": 1,
        "retry_observed": False,
        "fallback_observed": False,
        "capture_complete": True,
        "client_terminal": True,
        "lifecycle_assurance": "caller-attested",
        "live_ready": CODEX_REQUEST_FINGERPRINT_LIVE_READY,
        "limitations": CODEX_REQUEST_FINGERPRINT_LIMITATIONS,
    }
    for name, value in values.items():
        object.__setattr__(result, name, value)
    result._validate_invariants()
    return result


def _parse_body(body: bytes) -> dict[str, object]:
    if not body:
        raise CodexRequestFingerprintError("request-body-empty")
    if len(body) > CODEX_RESPONSES_MAX_BODY_BYTES:
        raise CodexRequestFingerprintError("request-body-byte-limit-exceeded")
    try:
        text = body.decode("utf-8")
    except UnicodeError:
        raise CodexRequestFingerprintError("request-body-invalid-utf8") from None
    return _parse_bounded_json_object(
        text,
        max_bytes=CODEX_RESPONSES_MAX_BODY_BYTES,
        code="request-body-json-invalid",
    )


def _parse_bounded_json_object(
    text: str, *, max_bytes: int, code: str
) -> dict[str, object]:
    try:
        if len(text.encode("utf-8")) > max_bytes:
            raise CodexRequestFingerprintError(code)
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_non_finite_json,
        )
    except _DuplicateJsonKey:
        raise CodexRequestFingerprintError(f"{code}-duplicate-field") from None
    except (json.JSONDecodeError, UnicodeError, _NonFiniteJsonValue):
        raise CodexRequestFingerprintError(code) from None
    if not isinstance(value, dict):
        raise CodexRequestFingerprintError(code)
    return value


def _validate_reasoning(value: object) -> None:
    if not isinstance(value, dict) or frozenset(value) != {"effort"}:
        raise CodexRequestFingerprintError("request-reasoning-fields-mismatch")
    if value.get("effort") != CODEX_CODING_PLAN_REASONING_EFFORT:
        raise CodexRequestFingerprintError("request-reasoning-effort-mismatch")


def _validate_client_metadata(value: object) -> None:
    if not isinstance(value, dict) or frozenset(value) != {"x-codex-installation-id"}:
        raise CodexRequestFingerprintError("request-client-metadata-mismatch")
    _validate_uuid(
        value.get("x-codex-installation-id"),
        code="request-client-metadata-mismatch",
    )


def _validate_prompt_cache_key(value: object) -> None:
    _validate_uuid(value, code="request-prompt-cache-key-invalid")


def _validate_input(
    value: object, *, expected_prompt_sha256: str, expected_input_sha256: str
) -> tuple[int, int, str]:
    if (
        not isinstance(value, list)
        or not 1 <= len(value) <= CODEX_RESPONSES_MAX_INPUT_ITEMS
    ):
        raise CodexRequestFingerprintError("request-input-items-invalid")
    total_text_bytes = 0
    last_texts: list[str] | None = None
    for item in value:
        if not isinstance(item, dict) or frozenset(item) != {
            "content",
            "role",
            "type",
        }:
            raise CodexRequestFingerprintError("request-input-item-fields-mismatch")
        if item.get("type") != "message" or item.get("role") not in {
            "developer",
            "user",
        }:
            raise CodexRequestFingerprintError("request-input-item-type-invalid")
        content = item.get("content")
        if not isinstance(content, list) or not content:
            raise CodexRequestFingerprintError("request-input-content-invalid")
        item_texts: list[str] = []
        for part in content:
            if not isinstance(part, dict) or frozenset(part) != {"text", "type"}:
                raise CodexRequestFingerprintError(
                    "request-input-content-fields-mismatch"
                )
            text = part.get("text")
            if (
                part.get("type") != "input_text"
                or not isinstance(text, str)
                or not text
            ):
                raise CodexRequestFingerprintError("request-input-content-invalid")
            try:
                text_bytes = text.encode("utf-8")
            except UnicodeError:
                raise CodexRequestFingerprintError(
                    "request-input-content-invalid"
                ) from None
            total_text_bytes += len(text_bytes)
            if total_text_bytes > CODEX_RESPONSES_MAX_INPUT_TEXT_BYTES:
                raise CodexRequestFingerprintError(
                    "request-input-text-byte-limit-exceeded"
                )
            item_texts.append(text)
        last_texts = item_texts
    final_item = value[-1]
    if final_item.get("role") != "user" or last_texts is None or len(last_texts) != 1:
        raise CodexRequestFingerprintError("request-final-prompt-shape-invalid")
    final_hash = hashlib.sha256(last_texts[0].encode("utf-8")).hexdigest()
    if final_hash != expected_prompt_sha256:
        raise CodexRequestFingerprintError("request-final-prompt-hash-mismatch")
    input_sha256 = canonical_codex_input_sha256(value)
    if input_sha256 != expected_input_sha256:
        raise CodexRequestFingerprintError("request-input-hash-mismatch")
    return len(value), total_text_bytes, input_sha256


def _validate_expected_tools(
    value: Sequence[ApprovedCodexTool],
) -> tuple[ApprovedCodexTool, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError("expected_tools must be a sequence")
    if len(value) > CODEX_RESPONSES_MAX_TOOLS:
        raise ValueError("expected_tools exceeds the fixed ceiling")
    tools = tuple(value)
    if any(not isinstance(item, ApprovedCodexTool) for item in tools):
        raise TypeError("expected_tools must contain ApprovedCodexTool values")
    names = [item.name for item in tools]
    if len(names) != len(set(names)):
        raise ValueError("expected_tools names must be unique")
    return tools


def _validate_tool_exposure(
    value: object, *, expected_tools: tuple[ApprovedCodexTool, ...]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not isinstance(value, list) or len(value) > CODEX_RESPONSES_MAX_TOOLS:
        raise CodexRequestFingerprintError("request-tools-invalid")
    observed_names: list[str] = []
    observed_hashes: list[str] = []
    for item in value:
        if not isinstance(item, dict) or frozenset(item) != _FUNCTION_TOOL_FIELDS:
            raise CodexRequestFingerprintError("request-tool-fields-mismatch")
        name = item.get("name")
        if not isinstance(name, str) or _TOOL_NAME.fullmatch(name) is None:
            raise CodexRequestFingerprintError("request-tool-name-invalid")
        if name in CODEX_FORBIDDEN_NATIVE_TOOL_NAMES:
            raise CodexRequestFingerprintError("request-forbidden-native-tool-exposed")
        if item.get("type") != "function":
            raise CodexRequestFingerprintError("request-tool-type-mismatch")
        description = item.get("description")
        if not isinstance(description, str) or not description:
            raise CodexRequestFingerprintError("request-tool-description-invalid")
        try:
            if len(description.encode("utf-8")) > 4_096:
                raise CodexRequestFingerprintError("request-tool-description-invalid")
        except UnicodeError:
            raise CodexRequestFingerprintError(
                "request-tool-description-invalid"
            ) from None
        if item.get("strict") is not True or not isinstance(
            item.get("parameters"), dict
        ):
            raise CodexRequestFingerprintError("request-tool-contract-invalid")
        observed_names.append(name)
        observed_hashes.append(canonical_codex_tool_sha256(item))
    expected_names = tuple(item.name for item in expected_tools)
    expected_hashes = tuple(item.tool_sha256 for item in expected_tools)
    if tuple(observed_names) != expected_names:
        raise CodexRequestFingerprintError("request-tool-exposure-mismatch")
    if tuple(observed_hashes) != expected_hashes:
        raise CodexRequestFingerprintError("request-tool-schema-hash-mismatch")
    return tuple(observed_names), tuple(observed_hashes)


def _validate_exact_value(
    document: Mapping[str, object], field_name: str, expected: object
) -> None:
    if document.get(field_name) != expected or type(
        document.get(field_name)
    ) is not type(expected):
        raise CodexRequestFingerprintError(
            f"request-{field_name.replace('_', '-')}-mismatch"
        )


def _validate_authority(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 255
        or any(ord(character) < 33 or ord(character) > 126 for character in value)
        or "/" in value
        or "@" in value
    ):
        raise ValueError("expected_authority must be one exact HTTP authority")
    return value


def _validate_uuid(value: object, *, code: str) -> None:
    if not isinstance(value, str):
        raise CodexRequestFingerprintError(code)
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        raise CodexRequestFingerprintError(code) from None
    if str(parsed) != value or parsed.int == 0:
        raise CodexRequestFingerprintError(code)


def _validate_sha256(name: str, value: str) -> None:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _contains_text(value: object, needle: str) -> bool:
    if isinstance(value, str):
        return needle in value
    if isinstance(value, Mapping):
        return any(
            _contains_text(name, needle) or _contains_text(item, needle)
            for name, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_text(item, needle) for item in value)
    return False


class _DuplicateJsonKey(ValueError):
    pass


class _NonFiniteJsonValue(ValueError):
    pass


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    value: dict[str, object] = {}
    for name, item in pairs:
        if name in value:
            raise _DuplicateJsonKey
        value[name] = item
    return value


def _reject_non_finite_json(value: str) -> object:
    del value
    raise _NonFiniteJsonValue
