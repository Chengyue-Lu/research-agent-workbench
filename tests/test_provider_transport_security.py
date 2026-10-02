"""Synthetic regressions for transport egress and public error boundaries."""

import io
import json
import socket
import traceback
import unittest
import urllib.error
import urllib.request
import urllib.response
from dataclasses import replace
from email.message import Message as Headers
from types import SimpleNamespace
from unittest import mock

from research_workbench.adapters.models import (
    AnthropicMessagesProvider,
    ContentBlock,
    FinishReason,
    GeminiGenerateContentProvider,
    Message,
    ModelRequest,
    ModelResponse,
    OpenAIResponsesProvider,
    ProviderError,
    ProviderErrorCategory,
    ResponseFormat,
    ToolCall,
    ToolDefinition,
)
from research_workbench.adapters.models.base import (
    perform_json_request,
    raise_provider_http_error,
    validate_response_contract,
    validate_structured_response,
)
from research_workbench.adapters.models.configuration import ProviderAdapterConfig
from research_workbench.adapters.models.http import (
    CredentialUnavailable,
    HttpRequest,
    HttpResponse,
    HttpTransportError,
    UrllibTransport,
    decode_json_object,
    validate_https_endpoint,
)


SENTINEL = "SYNTHETIC_CREDENTIAL_AND_RESEARCH_BODY"


class FakeCredential:
    def __init__(self, error=None):
        self.resolve_count = 0
        self.error = error

    def resolve(self):
        self.resolve_count += 1
        if self.error is not None:
            raise self.error
        return SENTINEL


class FakeTransport:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.response


class MemoryHTTPSHandler(urllib.request.HTTPSHandler):
    """Exercise real opener/error/redirect handlers without creating a socket."""

    def __init__(self, status, *, location=None, body=b'{}'):
        super().__init__()
        self.status = status
        self.location = location
        self.body = body
        self.requests = []

    def https_open(self, request):
        self.requests.append(request)
        headers = Headers()
        if self.location:
            headers["Location"] = self.location
        response = urllib.response.addinfourl(
            io.BytesIO(self.body), headers, request.full_url, self.status
        )
        response.msg = SENTINEL
        return response


def request(url="https://provider.invalid/v1/respond"):
    return HttpRequest(
        "POST", url,
        {"Authorization": f"Bearer {SENTINEL}", "X-api-key": SENTINEL, "X-goog-api-key": SENTINEL},
        SENTINEL.encode(), 1,
    )


def perform(credential, transport, *, url="https://provider.invalid/v1/respond"):
    return perform_json_request(
        provider="openai", transport=transport, credential=credential, url=url,
        headers={"Authorization": "Bearer {API_KEY}"}, payload={"synthetic": "input"},
        timeout_seconds=1,
    )


class TransportSecurityTests(unittest.TestCase):
    def setUp(self):
        # Any accidental wire path or implicit proxy environment lookup fails.
        self.patches = (
            mock.patch.object(socket, "socket", side_effect=AssertionError("network is forbidden")),
            mock.patch.object(socket, "create_connection", side_effect=AssertionError("network is forbidden")),
            mock.patch.object(urllib.request, "getproxies", side_effect=AssertionError("proxy lookup is forbidden")),
        )
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def assert_safe(self, error):
        rendered = str(error) + repr(error) + "".join(traceback.format_exception(error))
        self.assertNotIn(SENTINEL, rendered)
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        self.assertNotIn(SENTINEL, repr(vars(error)))

    def memory_opener(self, handler):
        original = urllib.request.build_opener
        return mock.patch.object(
            urllib.request, "build_opener",
            side_effect=lambda *handlers: original(urllib.request.ProxyHandler({}), handler, *handlers),
        )

    def test_every_redirect_is_terminal_with_no_second_request(self):
        targets = (
            "https://provider.invalid/next",
            "https://other.invalid/next",
            "http://other.invalid/next",
        )
        for status in (301, 302, 303, 307, 308):
            for target in targets:
                with self.subTest(status=status, target=target):
                    handler = MemoryHTTPSHandler(status, location=target, body=SENTINEL.encode())
                    with self.memory_opener(handler):
                        with self.assertRaises(HttpTransportError) as caught:
                            UrllibTransport().send(request())
                    self.assertEqual(1, len(handler.requests))
                    self.assertEqual("POST", handler.requests[0].get_method())
                    self.assertEqual(status, caught.exception.status_code)
                    self.assertFalse(caught.exception.retryable)
                    self.assert_safe(caught.exception)

    def test_normal_https_post_preserves_fake_auth_body_and_json(self):
        handler = MemoryHTTPSHandler(200, body=b'{"ok":true}')
        with self.memory_opener(handler):
            result = UrllibTransport().send(request("https://custom.invalid:8443/nested/path?api-version=v1"))
        self.assertEqual(200, result.status_code)
        self.assertEqual({"ok": True}, decode_json_object(result.body, provider="openai"))
        self.assertEqual(1, len(handler.requests))
        sent = handler.requests[0]
        self.assertEqual("POST", sent.get_method())
        self.assertEqual(SENTINEL.encode(), sent.data)
        for name in ("Authorization", "X-api-key", "X-goog-api-key"):
            self.assertIn(SENTINEL, sent.get_header(name))

    def test_unsafe_urls_fail_before_credentials_and_transport(self):
        invalid = (
            f"https://user:{SENTINEL}@provider.invalid/v1",
            f"https://{SENTINEL}@provider.invalid/v1",
            "http://provider.invalid/v1", "https:///v1", "https://:443/v1",
            "https://provider.invalid:not-a-port/v1", "https://provider.invalid:65536/v1",
            "https://provider.invalid:0/v1", "https://provider.invalid:/v1",
            "https://provider.invalid../v1", "https://bad_host.invalid/v1",
            "https://provider.invalid\\other/v1", "https://provider.invalid/v1#fragment",
            "https://provider.invalid/\nsecret", "https://[invalid-ip]/v1",
            "https://[::1]suffix/v1", "https://[::1][other]/v1",
        )
        for url in invalid:
            with self.subTest(url=url):
                credential = FakeCredential()
                transport = FakeTransport()
                with self.assertRaises(ProviderError) as caught:
                    perform(credential, transport, url=url)
                self.assertEqual(0, credential.resolve_count)
                self.assertEqual([], transport.requests)
                self.assertEqual(ProviderErrorCategory.INVALID_REQUEST, caught.exception.category)
                self.assert_safe(caught.exception)
                with self.assertRaises(HttpTransportError) as caught:
                    UrllibTransport().send(request(url))
                self.assert_safe(caught.exception)
                self.assertNotIn(SENTINEL, repr(request(url)))

    def test_config_and_direct_constructor_reject_non_secret_url_violations(self):
        values = dict(
            adapter_id="synthetic", provider="openai", enabled=False,
            base_url="https://custom.invalid:8443/nested/%20path", credential_env="SYNTHETIC_KEY",
            model_env="SYNTHETIC_MODEL", capabilities=["text"], live_conformance="pending",
        )
        with mock.patch("research_workbench.adapters.models.configuration._present", side_effect=AssertionError):
            config = ProviderAdapterConfig.from_mapping(values)
            self.assertEqual(values["base_url"], config.probe(check_environment=False)["base_url"])
            for url in (f"https://user:{SENTINEL}@custom.invalid/v1", "https://custom.invalid:bad/v1", "https://custom.invalid/v1?key=x"):
                with self.subTest(url=url):
                    with self.assertRaises(ValueError) as caught:
                        ProviderAdapterConfig.from_mapping(dict(values, base_url=url))
                    self.assert_safe(caught.exception)
                    with self.assertRaises(ValueError) as caught:
                        replace(config, base_url=url)
                    self.assert_safe(caught.exception)

    def test_legitimate_custom_https_endpoint_syntax_is_preserved(self):
        for url in (
            "https://localhost:8443/v1", "https://127.0.0.1/v1", "https://[::1]:8443/v1",
            "https://custom.invalid./prefix/v1", "https://xn--bcher-kva.invalid/v1",
            "https://custom.invalid/a%20b?api-version=v1",
        ):
            with self.subTest(url=url):
                validate_https_endpoint(url)

    def test_http_status_body_bound_and_transport_reasons_have_safe_diagnostics(self):
        errors = (
            urllib.error.URLError(SENTINEL), TimeoutError(SENTINEL), OSError(SENTINEL),
            urllib.error.HTTPError("https://provider.invalid/v1", 400, SENTINEL, {}, io.BytesIO(SENTINEL.encode())),
            urllib.error.HTTPError("https://provider.invalid/v1", SENTINEL, SENTINEL, {}, io.BytesIO(b'{}')),
        )
        for original in errors:
            with self.subTest(kind=type(original).__name__):
                opener = SimpleNamespace(open=mock.Mock(side_effect=original))
                with mock.patch.object(urllib.request, "build_opener", return_value=opener):
                    with self.assertRaises(HttpTransportError) as caught:
                        UrllibTransport(max_response_bytes=4).send(request())
                self.assert_safe(caught.exception)
                self.assertEqual(1, opener.open.call_count)
                self.assertEqual(isinstance(original, (urllib.error.URLError, TimeoutError, OSError)) and not isinstance(original, urllib.error.HTTPError), caught.exception.retryable)
        handler = MemoryHTTPSHandler(200, body=SENTINEL.encode())
        with self.memory_opener(handler):
            with self.assertRaises(HttpTransportError) as caught:
                UrllibTransport(max_response_bytes=4).send(request())
        self.assert_safe(caught.exception)
        original = HttpTransportError("synthetic", retryable=True)
        original.retryable = SENTINEL
        original.status_code = SENTINEL
        opener = SimpleNamespace(open=mock.Mock(side_effect=original))
        with mock.patch.object(urllib.request, "build_opener", return_value=opener):
            with self.assertRaises(HttpTransportError) as caught:
                UrllibTransport().send(request())
        self.assertFalse(caught.exception.retryable)
        self.assertIsNone(caught.exception.status_code)
        self.assert_safe(caught.exception)

    def test_public_provider_wrapping_discards_credential_and_transport_exceptions(self):
        for original in (CredentialUnavailable(SENTINEL), RuntimeError(SENTINEL)):
            with self.subTest(kind=type(original).__name__):
                credential = FakeCredential(original)
                transport = FakeTransport()
                with self.assertRaises(ProviderError) as caught:
                    perform(credential, transport)
                self.assertEqual(ProviderErrorCategory.AUTHENTICATION, caught.exception.category)
                self.assertEqual([], transport.requests)
                self.assert_safe(caught.exception)
        for original in (HttpTransportError(SENTINEL, retryable=True), RuntimeError(SENTINEL)):
            with self.subTest(kind=type(original).__name__):
                transport = FakeTransport(error=original)
                with self.assertRaises(ProviderError) as caught:
                    perform(FakeCredential(), transport)
                self.assertEqual(1, len(transport.requests))
                self.assert_safe(caught.exception)
        unsafe_fields = HttpTransportError("synthetic", retryable=SENTINEL, status_code=SENTINEL)
        self.assertFalse(unsafe_fields.retryable)
        self.assertIsNone(unsafe_fields.status_code)
        unsafe_fields.retryable = SENTINEL
        unsafe_fields.status_code = SENTINEL
        with self.assertRaises(ProviderError) as caught:
            perform(FakeCredential(), FakeTransport(error=unsafe_fields))
        self.assertFalse(caught.exception.retryable)
        self.assertIsNone(caught.exception.status_code)
        self.assertEqual(ProviderErrorCategory.INVALID_REQUEST, caught.exception.category)
        self.assert_safe(caught.exception)
        for unsafe_status in (SENTINEL, True, 0, 999):
            with self.subTest(status=unsafe_status):
                with self.assertRaises(ProviderError) as caught:
                    perform(FakeCredential(), FakeTransport(HttpResponse(unsafe_status, {}, b'{}')))
                self.assertEqual(ProviderErrorCategory.CONTRACT_VIOLATION, caught.exception.category)
                self.assertIsNone(caught.exception.status_code)
                self.assert_safe(caught.exception)

    def test_http_error_read_and_close_failures_cannot_escape_raw_diagnostics(self):
        for fail_read in (False, True):
            original = urllib.error.HTTPError("https://provider.invalid/v1", 429, SENTINEL, {}, io.BytesIO(b'{}'))
            original.close = mock.Mock(side_effect=RuntimeError(SENTINEL))
            if fail_read:
                original.read = mock.Mock(side_effect=RuntimeError(SENTINEL))
            opener = SimpleNamespace(open=mock.Mock(side_effect=original))
            with mock.patch.object(urllib.request, "build_opener", return_value=opener):
                if fail_read:
                    with self.assertRaises(HttpTransportError) as caught:
                        UrllibTransport().send(request())
                    self.assert_safe(caught.exception)
                    self.assertEqual(429, caught.exception.status_code)
                else:
                    result = UrllibTransport().send(request())
                    self.assertEqual(429, result.status_code)
            original.close.assert_called_once()

    def test_json_decoding_and_response_error_categories_hide_raw_bodies(self):
        for status in (200, 401, 403, 429, 503):
            for body in (SENTINEL.encode(), b"\xff" + SENTINEL.encode(), json.dumps(SENTINEL).encode()):
                with self.subTest(status=status, body_kind=body[:1]):
                    transport = FakeTransport(HttpResponse(status, {}, body))
                    with self.assertRaises(ProviderError) as caught:
                        perform(FakeCredential(), transport)
                    self.assertEqual(status, caught.exception.status_code)
                    expected = {200: ProviderErrorCategory.CONTRACT_VIOLATION, 401: ProviderErrorCategory.AUTHENTICATION, 403: ProviderErrorCategory.PERMISSION, 429: ProviderErrorCategory.RATE_LIMIT, 503: ProviderErrorCategory.TRANSIENT}[status]
                    self.assertEqual(expected, caught.exception.category)
                    self.assertEqual(status in (429, 503), caught.exception.retryable)
                    self.assert_safe(caught.exception)
        for body in (SENTINEL.encode(), b"\xff" + SENTINEL.encode()):
            with self.assertRaises(ValueError) as caught:
                decode_json_object(body, provider="openai")
            self.assert_safe(caught.exception)

    def test_redirect_from_injected_transport_is_also_terminal(self):
        for status in (301, 302, 303, 307, 308):
            transport = FakeTransport(HttpResponse(status, {}, b'{}'))
            with self.assertRaises(ProviderError) as caught:
                perform(FakeCredential(), transport)
            self.assertEqual(status, caught.exception.status_code)
            self.assertFalse(caught.exception.retryable)
            self.assert_safe(caught.exception)

    def test_provider_error_helper_and_real_decoders_discard_echoed_messages_and_codes(self):
        with self.assertRaises(ProviderError) as caught:
            raise_provider_http_error(provider="openai", status_code=400, message=SENTINEL, provider_code=SENTINEL)
        self.assertIsNone(caught.exception.provider_code)
        self.assert_safe(caught.exception)
        for provider_type, field, safe_code, category in (
            (OpenAIResponsesProvider, "code", "context_length_exceeded", ProviderErrorCategory.CONTEXT_LIMIT),
            (AnthropicMessagesProvider, "type", "rate_limit_error", ProviderErrorCategory.RATE_LIMIT),
            (GeminiGenerateContentProvider, "status", "UNAVAILABLE", ProviderErrorCategory.TRANSIENT),
        ):
            provider = provider_type(model="synthetic", credential=FakeCredential(), transport=FakeTransport())
            for code in (safe_code, SENTINEL):
                with self.subTest(provider=provider.provider_name, known_code=code == safe_code):
                    with self.assertRaises(ProviderError) as caught:
                        provider._raise_api_error(400, {"error": {field: code, "message": SENTINEL}})
                    self.assert_safe(caught.exception)
                    self.assertEqual(safe_code if code == safe_code else None, caught.exception.provider_code)
                    self.assertEqual(category if code == safe_code else ProviderErrorCategory.INVALID_REQUEST, caught.exception.category)

    def test_structured_and_tool_validation_diagnostics_do_not_echo_response_values(self):
        base_request = ModelRequest("synthetic", (Message("user", (ContentBlock("text", text="synthetic"),)),))
        model_response = ModelResponse("synthetic", "openai", "synthetic", (), FinishReason.COMPLETE)
        structured = replace(base_request, response_format=ResponseFormat("json_schema", "synthetic", {"type": "integer"}))
        for text in (SENTINEL, json.dumps(SENTINEL)):
            with self.assertRaises(ProviderError) as caught:
                validate_structured_response(structured, replace(model_response, output=(ContentBlock("text", text=text),)))
            self.assert_safe(caught.exception)
        tool = ToolDefinition("synthetic", "synthetic", {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]})
        tool_request = replace(base_request, tools=(tool,))
        for calls in (
            (ToolCall(SENTINEL, "synthetic", {"n": SENTINEL}),),
            (ToolCall("call", SENTINEL, {}),),
            (ToolCall(SENTINEL, "synthetic", {"n": 1}), ToolCall(SENTINEL, "synthetic", {"n": 2})),
        ):
            with self.assertRaises(ProviderError) as caught:
                validate_response_contract(tool_request, replace(model_response, tool_calls=calls))
            self.assert_safe(caught.exception)
        provider = OpenAIResponsesProvider(model="synthetic", credential=FakeCredential(), transport=FakeTransport())
        for arguments in (SENTINEL, [SENTINEL]):
            with self.assertRaises(ProviderError) as caught:
                provider._parse_tool_call({"call_id": SENTINEL, "name": "synthetic", "arguments": arguments}, 0)
            self.assert_safe(caught.exception)


if __name__ == "__main__":
    unittest.main()
