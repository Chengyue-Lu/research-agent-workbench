"""Loopback tests for the injectable HTTP transport and environment credentials.

UrllibTransport only accepts absolute HTTPS endpoints, so these tests wrap a
stdlib http.server in TLS with the static, test-only self-signed certificate
below and patch urlopen to skip client-side verification. No test leaves the
loopback interface.
"""

from __future__ import annotations

import http.server
import json
import os
import ssl
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from research_workbench.adapters.models import (
    CredentialUnavailable,
    EnvironmentCredential,
    HttpRequest,
    HttpTransportError,
    UrllibTransport,
)


# Test-only certificate for CN=localhost (SAN: localhost, 127.0.0.1), valid
# for 100 years; the private key guards nothing and never leaves this file.
_CERT_PEM = """-----BEGIN CERTIFICATE-----
MIIDJzCCAg+gAwIBAgIUAca6/N9EOETraQUldUxvzSGN3JkwDQYJKoZIhvcNAQEL
BQAwFDESMBAGA1UEAwwJbG9jYWxob3N0MCAXDTI2MDgxODEyMjkwNloYDzIxMjYw
NzI1MTIyOTA2WjAUMRIwEAYDVQQDDAlsb2NhbGhvc3QwggEiMA0GCSqGSIb3DQEB
AQUAA4IBDwAwggEKAoIBAQCTU2NfYQYBsnOw6nzs8RTVX7hMqfYUe2Kp3wYTMn+P
s6B8Vq3LsOLZGdopTB3WDogY2XUjWCR/0x3q0GZvxT1LAB8e52+fN932oMzqMTYJ
A/CoMBDWqMAZSADMvw4F7zdnP3peOhnNjORSr/bX8YCY9IvyaBGXFIEfQeM50yJw
B+7yZl3OA4POG+4WByvoczc0u7TCbHZ9a3F1WZHV5V/IWdd8KLjVL5siOW1ctpne
tCk7Fhv04Tz/PldczXA9s0pbgYh6pnvuNe6aOx8SBWEpRCgokKNkevI4D8gaYRt/
vtvTWOBVTGGJV/APecSLu+97oRhb7OkFs4U80TUgFxJXAgMBAAGjbzBtMB0GA1Ud
DgQWBBRzQfsE7qOa4KCTcPcw09ZE1FYcfTAfBgNVHSMEGDAWgBRzQfsE7qOa4KCT
cPcw09ZE1FYcfTAPBgNVHRMBAf8EBTADAQH/MBoGA1UdEQQTMBGCCWxvY2FsaG9z
dIcEfwAAATANBgkqhkiG9w0BAQsFAAOCAQEAKIfwuakVQJZsEKuJaa3X9QetuGHb
/7KN9/pmHkXM+fCzmV24L9dOIadm6S+Db5xCmgJ0D4Qr2zWjtwdZ9BFyzO4jiX7L
MGOr8pnBrYVm84VgaSgKVD3kk6YV3xdyb3kUZb4dczWaspLP1U1EQc4xDn4xDeyt
yncBg8FOykqQzyGzn8VEG4UXPPEKNCk0nOURmhMw3lE25DQ9MZRx+F1GqYLGEOJI
AsBCWDE+O1b288dkirPlEkBSJwrHs0t+Sh2xATJwpXjFm7zHCPCUQOxXVbY1UAPB
DFqQbVKbN3LqRp+CZPdrWqqMcFOza/TW0R3RU0jxSpMjlaBXLwlLA7dtDg==
-----END CERTIFICATE-----
"""
_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCTU2NfYQYBsnOw
6nzs8RTVX7hMqfYUe2Kp3wYTMn+Ps6B8Vq3LsOLZGdopTB3WDogY2XUjWCR/0x3q
0GZvxT1LAB8e52+fN932oMzqMTYJA/CoMBDWqMAZSADMvw4F7zdnP3peOhnNjORS
r/bX8YCY9IvyaBGXFIEfQeM50yJwB+7yZl3OA4POG+4WByvoczc0u7TCbHZ9a3F1
WZHV5V/IWdd8KLjVL5siOW1ctpnetCk7Fhv04Tz/PldczXA9s0pbgYh6pnvuNe6a
Ox8SBWEpRCgokKNkevI4D8gaYRt/vtvTWOBVTGGJV/APecSLu+97oRhb7OkFs4U8
0TUgFxJXAgMBAAECggEABLJ4bR6RS/WOFbpsMDvBf8oU/LDAjUefzi2zqmIGSiUe
fUhgMynZGbXmzEFGhEAjW7N3NiDFzSOEhSuO0Ip32U/QLjKPzwI/e/EFh4P5JpFv
F1Ws+8MWmNfAWsbOoibN2+dctethTjnrP62nj5v+DyJg4eIqiWgYc9Asd/gA1ZSG
xrZalFa9ZbacrBBQGls8ObVKCR/X11iEQ+xXvKEGNd+yIVJvS/ce8EIjkes4icU1
DPlWihP88EUzJ13mr8HIXKeCZ3rJncElBENf+0w70xAbRJVmMcdYuf2lJqCukgC8
Po1inEmXIydIOgOmO/X0jtDMSN3/x76j6Gy6X1heCQKBgQDLUaw40ggmf6MHLrIF
HvTMY8wrRYPsdY6CIp8zYitiCHfwjXobgij9h93RtC+tI54/AnCc+eH5dBS7lr4U
iKXW2DEC9A8P2MBOueORNPT55gC20fZ/tJAm7U5SuDXrmX7v4NoOoyf89ETuNR4s
Fp20tGGSXWzPZASJeh0Ips0DfwKBgQC5f6GqoIt6KkRq1VMMXSWktmitRgkSXo+8
PaRL1Tflv6Yc9ddl9W7EZP327TlBBhjwQ4C9OsOYiftOZVNo+yLgj6SvD3srksNE
ba3WbxQQXJJdWDxRfKN9BfpZuO50m+fNKP/uthlv0vSTjRCF8aI9YRYZqydhJt6f
vfhhJbP9KQKBgQCU3Qer0pwFFA7Zg2b0OOYjgC5MwGkHCEt/HLpTdN0uueSXS/7L
hVFdz8ypbbQ6oImMuMybIppBeqxzbLtfbW1/EGtSLj+Y6qpi+deUyaFUFwMO2EwS
1LF2zuk5x4YzKf+2wnrlnK/6lR6jCmE9BpIRbMDD2YOBlUl9HtuDKh2RIQKBgDwo
fj+dzV4TMxkKkeJimwCt/4iiO/LvI+JCg3PsdDJYUwD1YaO5UvDyZ8Ka8IR7+75/
xdKYqjJgHVYxWjmjqI33R8tWU/WvpRAeGdB/OZyMyRLouLccmtDDDYvng73hie1p
LIc4G0u+uH7ZstAdqyYIxGgSr7S8LFrV+yVWWubxAoGAV5u4+9P+8Swk5Bv3P07W
KzPtCh88sVHgHp/1YGApk9hGFI8sA0J/K2w/IAzli+fDYyYCzVfoLKBkNb1maOMf
x2/S0C5eFkRdpopCmFQ3Dwdhp0xRksnco2brfvtHHLKEHH/md47IfKyFdtKSKSWF
QRM+Lwam/Abc6mM2nbAX+kI=
-----END PRIVATE KEY-----
"""


class _Handler(http.server.BaseHTTPRequestHandler):
    def _respond(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _route(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        received = self.rfile.read(length) if length else b""
        if self.path == "/ok":
            self._respond(200, json.dumps({"received": len(received)}).encode("utf-8"))
        elif self.path == "/large":
            self._respond(200, b"x" * 4096)
        elif self.path == "/error":
            self._respond(500, b'{"error": "boom"}')
        elif self.path == "/error-large":
            self._respond(500, b"e" * 4096)
        elif self.path == "/slow":
            time.sleep(2)
            try:
                self._respond(200, b"{}")
            except ConnectionError:
                pass  # the timeout test has already hung up
        else:
            self._respond(404, b'{"error": "unknown"}')

    do_GET = _route
    do_POST = _route

    def log_message(self, format: str, *args: object) -> None:
        pass


class _Server(http.server.ThreadingHTTPServer):
    def handle_error(self, request: object, client_address: object) -> None:
        pass  # expected disconnects from the timeout test stay quiet


class UrllibTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        directory = Path(temporary.name)
        (directory / "cert.pem").write_text(_CERT_PEM, encoding="ascii")
        (directory / "key.pem").write_text(_KEY_PEM, encoding="ascii")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(directory / "cert.pem", directory / "key.pem")
        server = _Server(("127.0.0.1", 0), _Handler)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        cls.addClassCleanup(server.server_close)
        cls.addClassCleanup(server.shutdown)
        cls.base_url = f"https://127.0.0.1:{server.server_address[1]}"
        real_urlopen = urllib.request.urlopen
        unverified = ssl.create_default_context()
        unverified.check_hostname = False
        unverified.verify_mode = ssl.CERT_NONE

        def urlopen_without_verification(url, *args, **kwargs):
            kwargs.setdefault("context", unverified)
            return real_urlopen(url, *args, **kwargs)

        patcher = mock.patch("urllib.request.urlopen", urlopen_without_verification)
        patcher.start()
        cls.addClassCleanup(patcher.stop)

    def _request(self, path: str, body: bytes = b"{}", timeout: float = 5.0) -> HttpRequest:
        return HttpRequest(
            method="POST",
            url=f"{self.base_url}{path}",
            headers={"Content-Type": "application/json"},
            body=body,
            timeout_seconds=timeout,
        )

    def test_post_round_trip_returns_status_headers_and_body(self) -> None:
        response = UrllibTransport().send(self._request("/ok", body=b'{"claim": 1}'))
        self.assertEqual(200, response.status_code)
        self.assertEqual({"received": 12}, json.loads(response.body.decode("utf-8")))
        headers = {name.lower(): value for name, value in response.headers.items()}
        self.assertEqual("application/json", headers["content-type"])

    def test_response_over_size_limit_fails_closed(self) -> None:
        transport = UrllibTransport(max_response_bytes=16)
        with self.assertRaises(HttpTransportError) as caught:
            transport.send(self._request("/large"))
        self.assertFalse(caught.exception.retryable)

    def test_http_error_status_is_returned_with_body(self) -> None:
        response = UrllibTransport().send(self._request("/error"))
        self.assertEqual(500, response.status_code)
        self.assertIn(b"boom", response.body)

    def test_error_response_over_size_limit_fails_closed(self) -> None:
        transport = UrllibTransport(max_response_bytes=16)
        with self.assertRaises(HttpTransportError) as caught:
            transport.send(self._request("/error-large"))
        self.assertFalse(caught.exception.retryable)

    def test_timeout_is_retryable(self) -> None:
        with self.assertRaises(HttpTransportError) as caught:
            UrllibTransport().send(self._request("/slow", timeout=0.25))
        self.assertTrue(caught.exception.retryable)

    def test_non_https_endpoint_is_rejected_before_any_network(self) -> None:
        request = HttpRequest(
            method="GET",
            url="http://127.0.0.1:9/ok",
            headers={},
            body=b"",
            timeout_seconds=0.25,
        )
        with self.assertRaises(HttpTransportError) as caught:
            UrllibTransport().send(request)
        self.assertFalse(caught.exception.retryable)

    def test_non_positive_size_limit_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            UrllibTransport(max_response_bytes=0)


class EnvironmentCredentialTests(unittest.TestCase):
    def test_missing_variable_is_unavailable_and_refuses_resolution(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            credential = EnvironmentCredential("RWB_TEST_CREDENTIAL")
            self.assertFalse(credential.available())
            with self.assertRaises(CredentialUnavailable):
                credential.resolve()

    def test_empty_variable_counts_as_missing(self) -> None:
        with mock.patch.dict(os.environ, {"RWB_TEST_CREDENTIAL": ""}, clear=True):
            credential = EnvironmentCredential("RWB_TEST_CREDENTIAL")
            self.assertFalse(credential.available())
            with self.assertRaises(CredentialUnavailable):
                credential.resolve()

    def test_present_variable_resolves_to_its_value(self) -> None:
        with mock.patch.dict(
            os.environ, {"RWB_TEST_CREDENTIAL": "secret-token"}, clear=True
        ):
            credential = EnvironmentCredential("RWB_TEST_CREDENTIAL")
            self.assertTrue(credential.available())
            self.assertEqual("secret-token", credential.resolve())

    def test_label_identifies_the_source_without_the_secret(self) -> None:
        credential = EnvironmentCredential("RWB_TEST_CREDENTIAL")
        self.assertEqual("env:RWB_TEST_CREDENTIAL", credential.label)

    def test_invalid_variable_name_is_rejected(self) -> None:
        for name in ("", "NOT-A-VALID-NAME", "WITH SPACE"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                EnvironmentCredential(name)


if __name__ == "__main__":
    unittest.main()
