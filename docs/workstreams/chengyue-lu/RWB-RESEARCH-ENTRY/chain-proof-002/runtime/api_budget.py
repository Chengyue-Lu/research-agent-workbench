"""Caller-owned, one-Attempt budget gate for the current configured adapter.

This helper has no selection, retry, qualification, Tool, or closeout authority.
Construction and use perform I/O; merely loading this module does not.
The caller must own the output parent and supply a justified input-token bound,
validated authorization callback, monotonic deadline, and selected prior totals.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType

from research_workbench.adapters.models.configured import (
    ConfiguredProvider, ProviderAdapterConfigV2, _endpoint, build_profile_provider,
)
from research_workbench.adapters.models.http import (
    CredentialProvider, HttpRequest, HttpResponse, HttpTransport, json_body,
)
from research_workbench.adapters.models.port import ModelRequest, ModelResponse, Usage
from research_workbench.adapters.models.wire_codecs import (
    _profile, _usage, encode_profile_request,
)
from research_workbench.observability.trace import sanitize_trace_value


class ApiBudgetError(RuntimeError):
    """Safe failure text; underlying exception messages are never archived."""


def _integer(value: object, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ApiBudgetError(f"invalid {name}")
    return value


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value


def _json(value: object) -> bytes:
    return json.dumps(_plain(value), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _local_metadata(request: ModelRequest) -> dict[str, str]:
    allowed = ("entry_role", "task_id", "baseline_sha256",
               "input_snapshot_sha256", "qualification")
    if not isinstance(request.metadata, Mapping):
        raise ApiBudgetError("request metadata must be a mapping")
    if any(type(key) is not str or key not in allowed or type(value) is not str
           for key, value in request.metadata.items()):
        raise ApiBudgetError("unknown or non-string host-local metadata")
    return dict(request.metadata)


def _wire_request(request: ModelRequest) -> ModelRequest:
    """Remove only the five declared RWB local fields from a request copy.

    Unknown metadata is rejected. All other fields, including extensions,
    messages, Tools, data policy, and output limits retain their original value.
    """
    _local_metadata(request)
    return replace(request, metadata={})


@dataclass(frozen=True, slots=True)
class BudgetConfig:
    namespace: str
    prior_known_tokens: int
    prior_held_tokens: int
    deadline_monotonic: float
    input_reservation_tokens: int
    total_token_cap: int = 10_000_000
    max_calls: int = 6
    max_output_tokens: int = 1024
    max_body_bytes: int = 32768

    def __post_init__(self) -> None:
        if not isinstance(self.namespace, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", self.namespace):
            raise ApiBudgetError("invalid namespace")
        for name in ("prior_known_tokens", "prior_held_tokens", "input_reservation_tokens"):
            _integer(getattr(self, name), name)
        for name in ("total_token_cap", "max_calls", "max_output_tokens", "max_body_bytes"):
            _integer(getattr(self, name), name, minimum=1)
        if (self.total_token_cap > 10_000_000 or self.max_calls > 6
                or self.max_output_tokens > 1024 or self.max_body_bytes > 32768):
            raise ApiBudgetError("Attempt engineering ceiling exceeded")
        if self.prior_known_tokens + self.prior_held_tokens > self.total_token_cap:
            raise ApiBudgetError("prior totals exceed cap")
        if (type(self.deadline_monotonic) not in (int, float)
                or not math.isfinite(self.deadline_monotonic)):
            raise ApiBudgetError("invalid monotonic deadline")


@dataclass(frozen=True, slots=True)
class RequestMaterial:
    """Exact pre-credential body and non-secret configuration for authorization."""
    url: str = field(repr=False)
    wire_body: bytes = field(repr=False)
    profile: Mapping[str, object] = field(repr=False)
    provider: str
    model: str
    max_output_tokens: int
    reservation_tokens: int
    body_sha256: str


@dataclass(slots=True)
class _Call:
    number: int
    material: RequestMaterial
    transport: object = field(repr=False)
    sent: bool = False
    http_status: int | None = None
    received_document: Mapping[str, object] | None = field(default=None, repr=False)
    response_ref: dict[str, str] | None = None
    local_metadata_ref: dict[str, str] | None = None
    status: str = "reserved"
    known_tokens: int | None = None


class ApiBudgetFacade:
    """One explicitly selected Attempt; share this object across fresh Sessions.

    No restart/resume or cross-Attempt discovery is implemented. An existing
    directory is rejected. The caller selects prior totals and authorizes all
    materials. Calls are serial; reentrant/concurrent dispatch is rejected.
    """

    def __init__(self, directory: str | Path, config: BudgetConfig, *,
                 authorize: Callable[[ModelRequest, RequestMaterial], object],
                 clock: Callable[[], float] | None = None) -> None:
        if clock is None:
            clock = time.monotonic
        if type(config) is not BudgetConfig or not callable(authorize) or not callable(clock):
            raise ApiBudgetError("invalid facade configuration")
        self.config, self.authorize, self.clock = config, authorize, clock
        now = self._now()
        if not 0 < config.deadline_monotonic - now <= 120:
            raise ApiBudgetError("Attempt deadline must be within 120 seconds")
        target = Path(directory)
        if not target.parent.is_dir() or target.is_symlink():
            raise ApiBudgetError("caller-owned parent must already exist")
        target.mkdir(exist_ok=False)
        self.directory = target.resolve(strict=True)
        self._lock = threading.Lock()
        self._active: _Call | None = None
        self._calls: list[_Call] = []
        self._known = self._held = self._sequence = 0
        self._stopped = self._closed = self._archive_failed = False
        self._safe(config.namespace, stage="namespace", number=0)
        self._append("opened", {"namespace": config.namespace,
                               "config": {name: getattr(config, name) for name in config.__dataclass_fields__}})

    def _now(self) -> float:
        value = self.clock()
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ApiBudgetError("invalid clock value")
        return float(value)

    def _remaining_time(self) -> float:
        remaining = self.config.deadline_monotonic - self._now()
        if remaining <= 0:
            raise ApiBudgetError("Attempt deadline expired")
        return remaining

    def _exclusive(self, name: str, payload: bytes) -> dict[str, str]:
        try:
            with (self.directory / name).open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            self._archive_failed = self._stopped = True
            raise ApiBudgetError("exclusive archive write failed") from None
        return {"path": name, "sha256": hashlib.sha256(payload).hexdigest()}

    def _append(self, kind: str, value: Mapping[str, object]) -> None:
        # Fixed, internally constructed event fields only; never headers/errors.
        event = {"sequence": self._sequence + 1, "kind": kind, "monotonic": self._now(), **value}
        try:
            with (self.directory / "events.jsonl").open("ab") as stream:
                stream.write(_json(event) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            self._archive_failed = self._stopped = True
            raise ApiBudgetError("budget event archive failed") from None
        self._sequence += 1

    def _safe(self, value: object, *, stage: str, number: int) -> None:
        _, redactions = sanitize_trace_value(value)
        if redactions:
            self._append("capture-gap", {"call": number, "stage": stage,
                         "categories": sorted({item["category"] for item in redactions})})
            self._stopped = True
            raise ApiBudgetError("sensitive or hidden-reasoning material cannot be archived")

    def build_provider(self, config: ProviderAdapterConfigV2, *, root: str | Path,
                       credential: CredentialProvider, transport: HttpTransport,
                       model_environment: Mapping[str, str] | None = None,
                       implementation_closure_ref: Mapping[str, object] | None = None) -> BudgetedProvider:
        if self._closed or self._stopped or credential is None or transport is None:
            raise ApiBudgetError("explicit credential and transport required on open facade")
        guarded = _BudgetTransport(self, transport)
        configured = build_profile_provider(config, root=root, credential=credential,
                    transport=guarded, model_environment=model_environment,
                    implementation_closure_ref=implementation_closure_ref)
        return BudgetedProvider(self, configured)

    def _prepare(self, provider: ConfiguredProvider, request: ModelRequest) -> tuple[_Call, ModelRequest]:
        if self._closed or self._stopped:
            raise ApiBudgetError("Attempt is closed or stopped")
        self._remaining_time()
        if len(self._calls) >= self.config.max_calls:
            raise ApiBudgetError("Attempt call ceiling exceeded")
        output = _integer(request.max_output_tokens, "request output limit", minimum=1)
        if output > self.config.max_output_tokens or request.model != provider.model:
            raise ApiBudgetError("request output or model differs from admitted limits")
        if len(request.tools) > 2:
            raise ApiBudgetError("Attempt Tool declaration ceiling exceeded")
        local_metadata = _local_metadata(request)
        wire_request = _wire_request(request)
        profile = provider.profile.document
        payload = encode_profile_request(wire_request, profile)
        body = json_body(payload)
        if len(body) > self.config.max_body_bytes:
            raise ApiBudgetError("wire body ceiling exceeded")
        number = len(self._calls) + 1
        url = _endpoint(profile)
        # Public auth templates in the profile are not authenticated headers.
        # Do not archive headers or subject their key names to payload capture.
        self._safe({"url": url, "provider": provider.profile.provider,
                    "model": provider.model, "request": payload,
                    "local_metadata": local_metadata}, stage="request", number=number)
        reservation = self.config.input_reservation_tokens + output
        if self.config.prior_known_tokens + self.config.prior_held_tokens + self._known + self._held + reservation > self.config.total_token_cap:
            raise ApiBudgetError("cumulative token cap cannot admit reservation")
        # Freeze authorization material independently of mutable profile mappings.
        frozen_profile = json.loads(_json(profile))
        material = RequestMaterial(url, body, _freeze(frozen_profile), provider.profile.provider,
                                   provider.model, output, reservation, hashlib.sha256(body).hexdigest())
        if self.authorize(request, material) is not True:
            raise ApiBudgetError("material authorization did not return strict True")
        self._remaining_time()
        if (_local_metadata(request) != local_metadata or _wire_request(request) != wire_request
                or json_body(encode_profile_request(wire_request, profile)) != body
                or _endpoint(profile) != url):
            raise ApiBudgetError("request drift after authorization")
        request_ref = self._exclusive(f"call-{number:03d}-request.json", body)
        metadata_ref = self._exclusive(f"call-{number:03d}-local-metadata.json", _json(local_metadata))
        call = _Call(number, material, provider.transport)
        call.local_metadata_ref = metadata_ref
        self._append("reserved", {"call": number, "tokens": reservation, "request_ref": request_ref,
                                  "local_metadata_ref": metadata_ref,
                                  "provider": material.provider, "model": material.model, "url": material.url,
                                  "output_limit": output})
        self._calls.append(call)
        self._held += reservation
        self._active = call
        return call, wire_request

    def _finish(self, call: _Call, response: ModelResponse | None, *, failed: bool) -> None:
        usage = response.usage if response is not None else None
        if usage is None and call.received_document is not None:
            try:
                usage, _ = _usage(call.received_document, _profile(call.material.profile))
            except Exception:
                usage = None
        call.received_document = None
        incoming = usage.input_tokens if isinstance(usage, Usage) else None
        outgoing = usage.output_tokens if isinstance(usage, Usage) else None
        known = (incoming + outgoing if type(incoming) is int and incoming >= 0
                 and type(outgoing) is int and outgoing >= 0 else None)
        if not call.sent:
            status, held = "unsent-released", 0
        elif known is None:
            status, held = "sent-unknown-held", call.material.reservation_tokens
        else:
            status, held = "sent-known-settled", 0
        self._append("settled", {"call": call.number, "status": status, "failed": failed,
                     "http_status": call.http_status, "usage": None if known is None else
                     {"input_tokens": incoming, "output_tokens": outgoing}, "known_tokens": known,
                     "retained_tokens": held, "response_ref": call.response_ref})
        self._held -= call.material.reservation_tokens - held
        if call.sent and known is not None:
            self._known += known
        call.status, call.known_tokens = status, known if call.sent else None
        if failed or (call.sent and known is None):
            self._stopped = True
        if call.sent and known is not None and known > call.material.reservation_tokens:
            self._stopped = True
            self._append("reservation-exceeded", {"call": call.number, "actual_tokens": known,
                                                  "reservation_tokens": call.material.reservation_tokens})
            raise ApiBudgetError("actual usage exceeded caller supplied reservation")
        if not failed and call.sent and known is None:
            raise ApiBudgetError("received response has unknown usage; full hold retained")

    def snapshot(self) -> dict[str, object]:
        known = self.config.prior_known_tokens + self._known
        held = self.config.prior_held_tokens + self._held
        return {"namespace": self.config.namespace, "total_token_cap": self.config.total_token_cap,
                "known_tokens": known, "held_tokens": held,
                "remaining_tokens": max(0, self.config.total_token_cap - known - held),
                "cap_exceeded": known + held > self.config.total_token_cap,
                "admitted_calls": len(self._calls), "http_entries": sum(call.sent for call in self._calls),
                "stopped": self._stopped, "closed": self._closed, "archive_failed": self._archive_failed,
                "calls": [{"call": call.number, "sent": call.sent, "http_status": call.http_status,
                           "status": call.status, "known_tokens": call.known_tokens,
                           "reservation_tokens": call.material.reservation_tokens,
                           "response_ref": call.response_ref,
                           "local_metadata_ref": call.local_metadata_ref} for call in self._calls]}

    def close(self) -> dict[str, object]:
        if not self._lock.acquire(blocking=False):
            raise ApiBudgetError("cannot close during dispatch")
        try:
            if self._closed:
                if self._archive_failed:
                    raise ApiBudgetError("closed Attempt has an archive failure")
                return self.snapshot()
            self._closed = True
            result = self.snapshot()
            self._append("closed", {"snapshot": result})
            self._exclusive("snapshot.json", _json(result))
            return result
        finally:
            self._lock.release()


class BudgetedProvider:
    def __init__(self, facade: ApiBudgetFacade, configured_provider: ConfiguredProvider) -> None:
        self.facade, self.configured_provider = facade, configured_provider

    @property
    def model(self) -> str:
        return self.configured_provider.model

    def capabilities(self):
        return self.configured_provider.capabilities()

    def binding_descriptor(self) -> dict[str, object]:
        return self.configured_provider.binding_descriptor()

    def generate(self, request: ModelRequest) -> ModelResponse:
        facade = self.facade
        if not facade._lock.acquire(blocking=False):
            raise ApiBudgetError("concurrent or reentrant dispatch rejected")
        try:
            call, wire_request = facade._prepare(self.configured_provider, request)
            try:
                response = self.configured_provider.generate(wire_request)
            except BaseException:
                facade._finish(call, None, failed=True)
                raise
            facade._finish(call, response, failed=False)
            return response
        finally:
            facade._active = None
            facade._lock.release()


class _BudgetTransport:
    def __init__(self, facade: ApiBudgetFacade, transport: HttpTransport) -> None:
        self.facade, self.transport = facade, transport
        self.max_response_bytes = _integer(getattr(transport, "max_response_bytes", None),
                                           "transport response limit", minimum=1)

    def send(self, request: HttpRequest) -> HttpResponse:
        facade, call = self.facade, self.facade._active
        if (call is None or call.transport is not self or call.sent
                or facade._closed or facade._stopped):
            raise ApiBudgetError("HTTP entry requires one active unsent reservation")
        facade._remaining_time()
        if request.method != "POST" or request.url != call.material.url or request.body != call.material.wire_body:
            raise ApiBudgetError("actual HTTP body or endpoint drift")
        if type(request.timeout_seconds) not in (int, float) or not math.isfinite(request.timeout_seconds) or request.timeout_seconds <= 0:
            raise ApiBudgetError("invalid HTTP timeout")
        facade._append("send-intent", {"call": call.number, "body_sha256": call.material.body_sha256})
        facade._remaining_time()
        facade._append("http-entry", {"call": call.number})
        # Conservatively sent from delegate-entry intent onward, even if the
        # delegate raises before actual wire arrival. No network arrival claim.
        call.sent = True
        remaining = facade._remaining_time()
        response = self.transport.send(replace(request, timeout_seconds=min(request.timeout_seconds, remaining)))
        if type(response.status_code) is not int or not 100 <= response.status_code <= 599:
            raise ApiBudgetError("invalid received HTTP status")
        call.http_status = response.status_code
        if not isinstance(response.body, bytes) or len(response.body) > self.max_response_bytes:
            facade._append("capture-gap", {"call": call.number, "stage": "response-body-limit"})
            raise ApiBudgetError("received body cannot be archived within response bound")
        try:
            text = response.body.decode("utf-8")
        except UnicodeDecodeError:
            facade._append("capture-gap", {"call": call.number, "stage": "response-encoding"})
            raise ApiBudgetError("received body is not UTF-8") from None
        try:
            document = json.loads(text)
        except ValueError:
            document = text
        if isinstance(document, Mapping):
            call.received_document = document
        facade._safe(document, stage="response", number=call.number)
        call.response_ref = facade._exclusive(f"call-{call.number:03d}-response.body", response.body)
        facade._append("http-response", {"call": call.number, "status": response.status_code,
                                        "response_ref": call.response_ref})
        facade._remaining_time()
        return response
