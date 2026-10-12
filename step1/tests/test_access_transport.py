"""Offline tests of the shared access transport's network and response bounds."""

from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError
from urllib.request import Request


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import archive_access as access


SOURCE = access.Source(
    id="fixture", name="Synthetic archive", access_mode="api",
    endpoint="https://archive.example/api/search",
    portal_url="https://archive.example/",
)


class RequestBytesTests(unittest.TestCase):
    def response(self, data=b"metadata", status=200):
        opener = MagicMock()
        response = opener.open.return_value.__enter__.return_value
        response.status = status
        response.read.return_value = data
        return opener, response

    def test_get_has_thirty_second_timeout_and_bounded_read(self):
        opener, response = self.response()
        with patch.object(access, "build_opener", return_value=opener) as build:
            self.assertEqual(access.request_bytes(SOURCE.endpoint, {"Accept": "application/json"}), b"metadata")
        build.assert_called_once()
        self.assertIsInstance(build.call_args.args[0], access.NoRedirect)
        opener.open.assert_called_once()
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, SOURCE.endpoint)
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertEqual(opener.open.call_args.kwargs, {"timeout": 30})
        response.read.assert_called_once_with(2 * 1024 * 1024 + 1)
        opener.open.return_value.__exit__.assert_called_once()

    def test_response_exactly_at_two_mib_limit_is_allowed(self):
        data = b"x" * (2 * 1024 * 1024)
        opener, _ = self.response(data)
        with patch.object(access, "build_opener", return_value=opener):
            self.assertEqual(access.request_bytes(SOURCE.endpoint), data)

    def test_oversized_response_is_rejected_and_response_closed(self):
        opener, response = self.response(b"x" * (2 * 1024 * 1024 + 1))
        with patch.object(access, "build_opener", return_value=opener), self.assertRaises(ValueError):
            access.request_bytes(SOURCE.endpoint)
        response.read.assert_called_once()
        opener.open.return_value.__exit__.assert_called_once()

    def test_non_200_status_is_not_parsed_as_metadata(self):
        opener, response = self.response(b"partial metadata", status=206)
        with patch.object(access, "build_opener", return_value=opener), self.assertRaises(HTTPError) as caught:
            access.request_bytes(SOURCE.endpoint)
        self.assertEqual(caught.exception.code, 206)
        response.read.assert_not_called()

    def test_redirect_handler_never_creates_a_followup_request(self):
        handler = access.NoRedirect()
        request = Request(SOURCE.endpoint)
        for code in (301, 302, 303, 307, 308):
            with self.subTest(code=code):
                self.assertIsNone(handler.redirect_request(
                    request, None, code, "Redirect", {}, "https://different.example/target"
                ))

    def test_redirect_http_error_is_reported_without_retry(self):
        opener = MagicMock()
        opener.open.side_effect = HTTPError(SOURCE.endpoint, 302, "Redirect", {}, None)

        def probe(query, rows, credential, request):
            request(SOURCE.endpoint)
            return {"sample_count": 1}

        with patch.object(access, "build_opener", return_value=opener):
            result = access.check_source(SOURCE, probe, live=True)
        self.assertEqual(result["status"], "redirect_blocked")
        self.assertEqual(result["http_status"], 302)
        self.assertTrue(result["request_sent"])
        opener.open.assert_called_once()


class BoundedSourceRequestTests(unittest.TestCase):
    def check(self, probe, transport):
        return access.check_source(SOURCE, probe, live=True, request=transport)

    def test_same_endpoint_with_query_is_allowed_once(self):
        transport = Mock(return_value=b"metadata")

        def probe(query, rows, credential, request):
            request(SOURCE.endpoint + "?q=Burma", headers={"Accept": "application/json"})
            return {"sample_count": 1, "total_results": 12}

        result = self.check(probe, transport)
        self.assertEqual(result["status"], "ok")
        transport.assert_called_once_with(SOURCE.endpoint + "?q=Burma", headers={"Accept": "application/json"})

    def test_second_request_is_rejected_before_transport(self):
        transport = Mock(return_value=b"metadata")

        def probe(query, rows, credential, request):
            request(SOURCE.endpoint + "?page=1")
            request(SOURCE.endpoint + "?page=2")
            return {"sample_count": 1}

        result = self.check(probe, transport)
        self.assertEqual(result["status"], "invalid_response")
        self.assertTrue(result["request_sent"])
        transport.assert_called_once_with(SOURCE.endpoint + "?page=1", headers=None)

    def test_endpoint_host_path_protocol_and_credentials_cannot_be_changed(self):
        forbidden_urls = (
            "https://different.example/api/search",
            "https://archive.example.evil.example/api/search",
            "https://archive.example/other/path",
            "https://archive.example/api/search/",
            "https://archive.example/api/../api/search",
            "http://archive.example/api/search",
            "https://archive.example:444/api/search",
            "https://user:password@archive.example/api/search",
            SOURCE.endpoint + "#fragment",
            "file:///api/search",
        )
        for target in forbidden_urls:
            with self.subTest(target=target):
                transport = Mock(return_value=b"metadata")

                def probe(query, rows, credential, request):
                    request(target)
                    return {"sample_count": 1}

                result = self.check(probe, transport)
                self.assertEqual(result["status"], "invalid_response")
                self.assertFalse(result["request_sent"])
                transport.assert_not_called()

    def test_injected_transport_must_return_bytes_within_size_limit(self):
        for data in ("text instead of bytes", None, b"x" * (2 * 1024 * 1024 + 1)):
            with self.subTest(kind=type(data).__name__):
                transport = Mock(return_value=data)

                def probe(query, rows, credential, request):
                    request(SOURCE.endpoint)
                    return {"sample_count": 1}

                result = self.check(probe, transport)
                self.assertEqual(result["status"], "invalid_response")
                transport.assert_called_once()

    def test_success_cannot_be_claimed_without_any_request(self):
        transport = Mock(return_value=b"metadata")
        result = self.check(lambda query, rows, credential, request: {"sample_count": 1}, transport)
        self.assertEqual(result["status"], "invalid_response")
        self.assertFalse(result["request_sent"])
        transport.assert_not_called()


if __name__ == "__main__":
    unittest.main()
