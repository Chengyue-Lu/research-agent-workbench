"""Small injectable JSON-over-HTTPS transport for provider adapters.

The request representation suppresses headers and body from repr so credentials
and research inputs do not leak through routine exception or debug formatting.
"""

from __future__ import annotations

import json
import ipaddress
import os
import re
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
    url: str = field(repr=False)
    headers: Mapping[str, str] = field(repr=False)
    body: bytes = field(repr=False)
    timeout_seconds: float = 60.0


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status_code: int
    headers: Mapping[str, str] = field(repr=False)
    body: bytes = field(repr=False)


class HttpTransportError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool, status_code: int | None = None):
        self.retryable = retryable if type(retryable) is bool else False
        self.status_code = status_code if type(status_code) is int and 100 <= status_code <= 599 else None
        super().__init__(message)


@runtime_checkable
class HttpTransport(Protocol):
    def send(self, request: HttpRequest) -> HttpResponse:
        """Send one bounded request. HTTP error statuses are returned, not raised."""


def validate_https_endpoint(url: str, *, allow_query: bool = True) -> None:
    """Validate non-secret URL syntax without DNS or credential access.

    Explicit HTTPS origins and paths remain configurable. This is syntax
    admission, not an origin allowlist or an assertion about the remote host.
    """

    valid = False
    try:
        if isinstance(url, str) and not re.search(r"[\x00-\x20\x7f]", url):
            parsed = urlparse(url)
            hostname = parsed.hostname
            port = parsed.port
            if (
                parsed.scheme == "https"
                and hostname
                and parsed.username is None
                and parsed.password is None
                and not parsed.fragment
                and (allow_query or not parsed.query)
                and not parsed.netloc.endswith(":")
                and (port is None or 1 <= port <= 65535)
            ):
                if ":" in hostname:
                    if re.fullmatch(r"\[[^\]]+\](?::[0-9]+)?", parsed.netloc):
                        ipaddress.IPv6Address(hostname)
                        valid = True
                else:
                    ascii_host = hostname.encode("idna").decode("ascii")
                    if ascii_host.endswith("."):
                        ascii_host = ascii_host[:-1]
                    valid = len(ascii_host) <= 253 and all(
                        re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
                        for label in ascii_host.split(".")
                    )
    except (ValueError, UnicodeError):
        pass
    if not valid:
        # Raise outside the parse handler so a malformed URL cannot become a
        # retained exception cause/context or a rendered diagnostic.
        raise ValueError("provider endpoint must be a non-secret absolute HTTPS URL")


class _RejectRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Even a same-origin redirect is an additional unpinned request.
        return None


class UrllibTransport:
    def __init__(self, *, max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES) -> None:
        if max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be positive")
        self.max_response_bytes = max_response_bytes

    def send(self, request: HttpRequest) -> HttpResponse:
        invalid_endpoint = False
        try:
            validate_https_endpoint(request.url)
        except ValueError:
            invalid_endpoint = True
        if invalid_endpoint:
            raise HttpTransportError("provider endpoint must be an absolute HTTPS URL", retryable=False)
        failure: HttpTransportError | None = None
        try:
            native = urllib.request.Request(
                request.url,
                data=request.body,
                headers=dict(request.headers),
                method=request.method,
            )
            opener = urllib.request.build_opener(_RejectRedirectHandler())
            with opener.open(native, timeout=request.timeout_seconds) as response:
                body = self._read_bounded(response)
                return HttpResponse(int(response.status), dict(response.headers.items()), body)
        except urllib.error.HTTPError as exc:
            status = exc.code if type(exc.code) is int and 100 <= exc.code <= 599 else None
            try:
                if status is None:
                    failure = HttpTransportError("provider returned an invalid HTTP status", retryable=False)
                elif 300 <= status < 400:
                    failure = HttpTransportError(
                        "provider redirect was refused", retryable=False, status_code=status
                    )
                else:
                    body = exc.read(self.max_response_bytes + 1)
                    if len(body) > self.max_response_bytes:
                        failure = HttpTransportError(
                            "provider error response exceeded size limit", retryable=False, status_code=status
                        )
                    else:
                        return HttpResponse(status, dict(exc.headers.items()) if exc.headers else {}, body)
            except Exception:
                failure = HttpTransportError("provider transport failed", retryable=True, status_code=status)
            finally:
                try:
                    exc.close()
                except Exception:
                    # Cleanup must not export a raw stream/provider exception.
                    pass
        except HttpTransportError as exc:
            failure = HttpTransportError("provider response exceeded size limit", retryable=exc.retryable)
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
            failure = HttpTransportError("provider transport failed", retryable=True)
        except Exception:
            failure = HttpTransportError("provider request could not be sent", retryable=False)
        assert failure is not None
        # No raw urllib error, reason, headers or response stream is attached.
        # This bounds public diagnostics; it does not promise memory erasure.
        raise failure

    def _read_bounded(self, response) -> bytes:
        body = response.read(self.max_response_bytes + 1)
        if len(body) > self.max_response_bytes:
            raise HttpTransportError("provider response exceeded size limit", retryable=False)
        return body


def json_body(document: Mapping[str, object]) -> bytes:
    return json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def decode_json_object(body: bytes, *, provider: str) -> Mapping[str, object]:
    invalid_json = False
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        invalid_json = True
    if invalid_json:
        raise ValueError("provider returned a non-JSON response")
    if not isinstance(value, Mapping):
        raise ValueError("provider returned a non-object JSON response")
    return value
