"""Synthetic Europeana access checks: never read a real key or call the API."""

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import access_europeana as api
from archive_access import check_source


class EuropeanaAccessTests(unittest.TestCase):
    def check(self, payload, **kwargs):
        self.transport = Mock(return_value=json.dumps(payload).encode())
        return check_source(api.SOURCE, api.probe, live=True, rows=2,
                            environ={"EUROPEANA_API_KEY": "synthetic-key"},
                            request=self.transport, **kwargs)

    def test_authenticated_single_request_uses_documented_parameters(self):
        result = self.check({"success": True, "totalResults": 3, "items": [{"id": "/a/b"}]})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["sample_count"], 1)
        self.transport.assert_called_once()
        url = self.transport.call_args.args[0]
        params = parse_qs(urlsplit(url).query)
        self.assertEqual(params["wskey"], ["synthetic-key"])
        self.assertEqual(params["rows"], ["2"])
        self.assertEqual(params["query"], ['"Burma Road"'])
        self.assertEqual(params["profile"], ["rich"])
        self.assertNotIn("synthetic-key", json.dumps(result))

    def test_empty_success_is_distinct_from_access_error(self):
        result = self.check({"success": True, "totalResults": 0, "items": []})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["sample_count"], 0)

    def test_api_error_in_http_200_is_not_success(self):
        result = self.check({"success": False, "error": "synthetic-key"})
        self.assertEqual(result["status"], "invalid_response")
        self.assertNotIn("synthetic-key", json.dumps(result))

    def test_malformed_payloads_fail_closed(self):
        for payload in [[], {}, {"success": True, "totalResults": True, "items": []},
                        {"success": True, "totalResults": 1, "items": [{}]},
                        {"success": True, "totalResults": 0, "items": [{"id": "/a"}]},
                        {"success": True, "totalResults": 3, "items": [{"id": "/a"}]*3}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.check(payload)["status"], "invalid_response")

    def test_upstream_credential_echo_never_leaves_count_summary(self):
        result = self.check({"success": True, "totalResults": 1,
                             "items": [{"id": "/a", "title": "synthetic-key"}],
                             "requestUrl": "https://example.org/?wskey=synthetic-key"})
        self.assertEqual(result["status"], "ok")
        self.assertNotIn("synthetic-key", json.dumps(result))
        self.assertNotIn("items", result)

    def test_missing_key_never_calls_network(self):
        request = Mock()
        result = check_source(api.SOURCE, api.probe, live=True, environ={}, request=request)
        self.assertEqual(result["status"], "missing_credential")
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
