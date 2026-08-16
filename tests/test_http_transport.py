import io
import unittest
import urllib.request
import urllib.response
from email.message import Message
from unittest.mock import patch

from research_workbench.adapters.models.http import HttpRequest, UrllibTransport


REDIRECT_STATUSES = (301, 302, 303, 307, 308)


def redirect_response(request: urllib.request.Request, status: int, location: str):
    headers = Message()
    headers["Location"] = location
    response = urllib.response.addinfourl(
        io.BytesIO(b"redirect response"),
        headers,
        request.full_url,
        status,
    )
    response.msg = "Redirect"
    return response


def success_response(request: urllib.request.Request):
    response = urllib.response.addinfourl(
        io.BytesIO(b"followed response"),
        Message(),
        request.full_url,
        200,
    )
    response.msg = "OK"
    return response


class UrllibTransportRedirectTests(unittest.TestCase):
    def test_cross_origin_redirects_are_returned_without_forwarding_authorization(self) -> None:
        for status in REDIRECT_STATUSES:
            with self.subTest(status=status):
                observed: list[tuple[str, dict[str, str]]] = []

                def fake_https_open(_handler, request):
                    observed.append((request.full_url, dict(request.header_items())))
                    if len(observed) == 1:
                        return redirect_response(
                            request,
                            status,
                            "https://credential-sink.invalid/collect",
                        )
                    return success_response(request)

                transport = UrllibTransport()
                method = "POST" if status in (301, 302, 303) else "GET"
                request = HttpRequest(
                    method=method,
                    url="https://provider.invalid/v1/models",
                    headers={"Authorization": "Bearer provider-secret"},
                    body=b"{}" if method == "POST" else b"",
                )
                with patch.object(
                    urllib.request.HTTPSHandler,
                    "https_open",
                    new=fake_https_open,
                ):
                    response = transport.send(request)

                self.assertEqual(status, response.status_code)
                self.assertEqual(b"redirect response", response.body)
                self.assertEqual(
                    "https://credential-sink.invalid/collect",
                    response.headers["Location"],
                )
                self.assertEqual(1, len(observed))
                self.assertEqual("https://provider.invalid/v1/models", observed[0][0])
                self.assertEqual("Bearer provider-secret", observed[0][1]["Authorization"])

    def test_same_origin_redirects_are_also_returned_without_following(self) -> None:
        for status in REDIRECT_STATUSES:
            with self.subTest(status=status):
                observed: list[str] = []

                def fake_https_open(_handler, request):
                    observed.append(request.full_url)
                    if len(observed) == 1:
                        return redirect_response(request, status, "/v2/models")
                    return success_response(request)

                transport = UrllibTransport()
                request = HttpRequest(
                    method="GET",
                    url="https://provider.invalid/v1/models",
                    headers={"Authorization": "Bearer provider-secret"},
                    body=b"",
                )
                with patch.object(
                    urllib.request.HTTPSHandler,
                    "https_open",
                    new=fake_https_open,
                ):
                    response = transport.send(request)

                self.assertEqual(status, response.status_code)
                self.assertEqual(b"redirect response", response.body)
                self.assertEqual("/v2/models", response.headers["Location"])
                self.assertEqual(["https://provider.invalid/v1/models"], observed)


if __name__ == "__main__":
    unittest.main()
