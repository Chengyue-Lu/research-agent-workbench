"""Small injectable JSON-over-HTTPS transport for provider adapters.

The request representation suppresses headers and body from repr so credentials
and research inputs do not leak through routine exception or debug formatting.
"""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Mapping, Protocol, runtime_checkable
from urllib.parse import urlparse


DEFAULT_MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class CredentialUnavailable(RuntimeError):
    pass


@runtime_checkable
class CredentialProvider(Protocol):
    @property
    def label(self) -> str:
        """Return a non-secret source label suitable for diagnostics."""

    def available(self) -> bool:
        """Check whether a credential exists without returning it."""

    def resolve(self) -> str:
        """Resolve the credential only at the outbound-call boundary."""


@dataclass(frozen=True, slots=True)
class EnvironmentCredential:
    env_var: str

    def __post_init__(self) -> None:
        if not self.env_var or not self.env_var.replace("_", "").isalnum():
            raise ValueError("credential environment variable must contain letters, digits, and underscores")

    @property
    def label(self) -> str:
        return f"env:{self.env_var}"

    def available(self) -> bool:
        return self.env_var in os.environ and bool(os.environ[self.env_var])

    def resolve(self) -> str:
        value = os.environ.get(self.env_var)
        if not value:
            raise CredentialUnavailable(f"credential is unavailable from {self.label}")
        return value


@dataclass(frozen=True, slots=True)
class HttpRequest:
    method: str
    url: str
    headers: Mapping[str, str] = field(repr=False)
    body: bytes = field(repr=False)
    timeout_seconds: float = 60.0


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status_code: int
    headers: Mapping[str, str] = field(repr=False)
    body: bytes = field(repr=False)


class HttpTransportError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool):
        self.retryable = retryable
        super().__init__(message)


@runtime_checkable
class HttpTransport(Protocol):
    def send(self, request: HttpRequest) -> HttpResponse:
        """Send one bounded request. HTTP error statuses are returned, not raised."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Surface redirects to the caller without issuing another request."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class UrllibTransport:
    def __init__(self, *, max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES) -> None:
        if max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be positive")
        self.max_response_bytes = max_response_bytes

    def send(self, request: HttpRequest) -> HttpResponse:
        parsed = urlparse(request.url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise HttpTransportError("provider endpoint must be an absolute HTTPS URL", retryable=False)
        native = urllib.request.Request(
            request.url,
            data=request.body,
            headers=dict(request.headers),
            method=request.method,
        )
        opener = urllib.request.build_opener(_NoRedirectHandler())
        try:
            with opener.open(native, timeout=request.timeout_seconds) as response:
                body = self._read_bounded(response)
                return HttpResponse(int(response.status), dict(response.headers.items()), body)
        except urllib.error.HTTPError as exc:
            body = exc.read(self.max_response_bytes + 1)
            if len(body) > self.max_response_bytes:
                raise HttpTransportError("provider error response exceeded size limit", retryable=False) from exc
            return HttpResponse(int(exc.code), dict(exc.headers.items()) if exc.headers else {}, body)
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            raise HttpTransportError("provider transport failed", retryable=True) from exc

    def _read_bounded(self, response) -> bytes:
        body = response.read(self.max_response_bytes + 1)
        if len(body) > self.max_response_bytes:
            raise HttpTransportError("provider response exceeded size limit", retryable=False)
        return body


def json_body(document: Mapping[str, object]) -> bytes:
    return json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def decode_json_object(body: bytes, *, provider: str) -> Mapping[str, object]:
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{provider} returned a non-JSON response") from exc
    if not isinstance(value, Mapping):
        raise ValueError(f"{provider} returned a non-object JSON response")
    return value
