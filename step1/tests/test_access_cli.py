"""Exercise the user-facing per-source and combined commands without networking."""

from contextlib import redirect_stderr, redirect_stdout
import importlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import archive_access
import check_archives


API_IDS = ("loc", "ndl", "europeana", "nara_catalog", "dpla", "tna")
SYNTHETIC_KEYS = {
    "EUROPEANA_API_KEY": "synthetic-europeana-key",
    "NARA_API_KEY": "synthetic-nara-key",
    "DPLA_API_KEY": "synthetic-dpla-key",
}


def api_responses(empty=False):
    """Valid wire responses let combined-command tests exercise real adapters."""
    count = 0 if empty else 7
    payloads = {
        "loc": {"results": [] if empty else [{"id": "https://www.loc.gov/item/123/"}],
                "pagination": {"of": count}},
        "europeana": {"success": True, "totalResults": count,
                      "items": [] if empty else [{"id": "/synthetic/123"}]},
        "nara_catalog": {"body": {"hits": {"total": {"value": count, "relation": "eq"},
                                            "hits": [] if empty else [{"_id": "123"}]}}},
        "dpla": {"count": count, "docs": [] if empty else [{"id": "123"}]},
        "tna": {"Count": count, "Records": [] if empty else [{"Id": "C123"}]},
    }
    responses = {source: json.dumps(payload).encode("utf-8") for source, payload in payloads.items()}
    item = "" if empty else "<item><link>https://ndlsearch.ndl.go.jp/books/123</link></item>"
    responses["ndl"] = (
        '<rss xmlns:opensearch="http://a9.com/-/spec/opensearchrss/1.0/"><channel>'
        '<opensearch:totalResults>' + str(count) + '</opensearch:totalResults>'
        + item + '</channel></rss>'
    ).encode("utf-8")
    return responses


def transport_for(responses):
    endpoints = {importlib.import_module("access_" + source).SOURCE.endpoint: source for source in API_IDS}

    def transport(url, headers=None):
        parsed = urlsplit(url)
        endpoint = parsed.scheme + "://" + parsed.netloc + parsed.path
        # A dataset or portal request has no fixture and fails the command test.
        return responses[endpoints[endpoint]]

    return transport


class AccessCliTests(unittest.TestCase):
    def capture(self, main, args):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(args)
        return code, json.loads(output.getvalue())

    def test_every_independent_entry_without_credentials_is_offline(self):
        expected = {
            "loc": (0, "ready"), "ndl": (0, "ready"), "nara": (0, "ready"),
            "europeana": (2, "missing_credential"), "dpla": (2, "missing_credential"),
            "nara_catalog": (2, "missing_credential"), "tna": (2, "permission_required"),
            "jacar": (0, "manual_only"), "iwm": (0, "manual_only"),
            "taiwan": (0, "manual_only"),
        }
        with patch.dict(archive_access.os.environ, {}, clear=True), patch.object(archive_access, "request_bytes") as network:
            for source_id, (code, status) in expected.items():
                with self.subTest(source=source_id):
                    module = importlib.import_module("access_" + source_id)
                    actual, report = self.capture(module.main, [])
                    self.assertEqual((actual, report["status"]), (code, status))
                    self.assertFalse(report["request_sent"])
            network.assert_not_called()

    def test_all_inventory_distinguishes_configured_key_and_pending_access(self):
        with patch.dict(archive_access.os.environ, {"EUROPEANA_API_KEY": "synthetic-key"}, clear=True), patch.object(archive_access, "request_bytes") as network:
            code, report = self.capture(check_archives.main, [])
            self.assertEqual(code, 2)
            self.assertEqual(report["summary"], {"ready": 4, "missing_credential": 2, "permission_required": 1, "manual_only": 3})
            self.assertEqual(len(report["results"]), 10)
            self.assertEqual(report["mode"], "access")
            self.assertIsNone(report["query"])
            self.assertNotIn("synthetic-key", json.dumps(report))
            network.assert_not_called()

    def test_live_on_manual_or_unconfigured_sources_is_an_explicit_skip(self):
        with patch.dict(archive_access.os.environ, {}, clear=True), patch.object(archive_access, "request_bytes") as network:
            for source_id in ("europeana", "dpla", "nara_catalog", "tna", "jacar", "iwm", "taiwan"):
                with self.subTest(source=source_id):
                    code, report = self.capture(check_archives.main, ["--source", source_id, "--live"])
                    self.assertEqual(code, 2)
                    self.assertFalse(report["results"][0]["request_sent"])
            network.assert_not_called()

    def assert_api_requests(self, network, sources, query, rows):
        self.assertEqual(network.call_count, len(sources))
        query_keys = {"ndl": "any", "europeana": "query", "tna": "SearchQuery"}
        limit_keys = {"loc": "c", "ndl": "cnt", "europeana": "rows",
                      "nara_catalog": "limit", "dpla": "page_size", "tna": "ResultsPageSize"}
        for call, source in zip(network.call_args_list, sources):
            with self.subTest(request_source=source):
                parsed = urlsplit(call.args[0])
                endpoint = parsed.scheme + "://" + parsed.netloc + parsed.path
                self.assertEqual(endpoint, importlib.import_module("access_" + source).SOURCE.endpoint)
                params = parse_qs(parsed.query)
                self.assertEqual(params[query_keys.get(source, "q")], [query])
                self.assertEqual(params[limit_keys[source]], [str(rows)])

    def test_all_keyword_reaches_only_currently_permitted_apis_unchanged(self):
        query = '飞虎队 飛虎隊 & "Flying Tigers" + 中国'
        with patch.dict(archive_access.os.environ, {"EUROPEANA_API_KEY": SYNTHETIC_KEYS["EUROPEANA_API_KEY"]}, clear=True), \
                patch.object(archive_access, "request_bytes", side_effect=transport_for(api_responses())) as network:
            code, report = self.capture(check_archives.main, ["--source", "all", "--live", "--query", query, "--rows", "2"])
        self.assertEqual(code, 2)
        self.assertEqual(report["mode"], "keyword")
        self.assertEqual(report["query"], query)
        self.assertEqual(report["summary"], {"ok": 3, "query_not_supported": 1, "missing_credential": 2,
                                              "permission_required": 1, "manual_only": 3})
        self.assert_api_requests(network, ("loc", "ndl", "europeana"), query, 2)
        for result in report["results"]:
            self.assertEqual(result["request_sent"], result["source"] in {"loc", "ndl", "europeana"})
            if not result["request_sent"]:
                self.assertNotIn("sample_count", result)
                self.assertNotIn("total_results", result)
        self.assertNotIn(SYNTHETIC_KEYS["EUROPEANA_API_KEY"], json.dumps(report))

    def test_all_keyword_can_reach_six_apis_after_keys_and_permission_are_configured(self):
        query = "飞虎队 & Burma"
        with patch.dict(archive_access.os.environ, SYNTHETIC_KEYS, clear=True), \
                patch.object(archive_access, "request_bytes", side_effect=transport_for(api_responses())) as network:
            code, report = self.capture(check_archives.main, ["--live", "--query", query, "--rows", "1", "--permission-confirmed"])
        self.assertEqual(code, 2)
        self.assertEqual(report["summary"], {"ok": 6, "query_not_supported": 1, "manual_only": 3})
        self.assert_api_requests(network, API_IDS, query, 1)
        for key in SYNTHETIC_KEYS.values():
            self.assertNotIn(key, json.dumps(report))

    def test_all_keyword_offline_never_claims_network_or_measured_counts(self):
        with patch.dict(archive_access.os.environ, SYNTHETIC_KEYS, clear=True), \
                patch.object(archive_access, "request_bytes") as network:
            code, report = self.capture(check_archives.main, ["--query", "飞虎队", "--permission-confirmed"])
        self.assertEqual(code, 2)
        self.assertFalse(report["live"])
        self.assertEqual(report["summary"], {"ready": 6, "query_not_supported": 1, "manual_only": 3})
        for result in report["results"]:
            self.assertFalse(result["request_sent"])
            self.assertNotIn("sample_count", result)
            self.assertNotIn("total_results", result)
        network.assert_not_called()

    def test_all_keyword_zero_matches_are_success_not_unavailable(self):
        with patch.dict(archive_access.os.environ, SYNTHETIC_KEYS, clear=True), \
                patch.object(archive_access, "request_bytes", side_effect=transport_for(api_responses(empty=True))) as network:
            code, report = self.capture(check_archives.main, ["--live", "--query", "飞虎队", "--permission-confirmed"])
        self.assertEqual(code, 2)
        self.assertEqual(network.call_count, 6)
        for result in report["results"]:
            if result["source"] in API_IDS:
                self.assertEqual((result["status"], result["sample_count"], result["total_results"]), ("ok", 0, 0))

    def test_one_upstream_failure_does_not_stop_remaining_sources_and_exit_one_wins(self):
        working_transport = transport_for(api_responses())

        def partial_failure(url, headers=None):
            if urlsplit(url).netloc == "www.loc.gov":
                raise HTTPError(url + "&key=synthetic-upstream-secret", 403, "synthetic-upstream-secret", {}, None)
            return working_transport(url, headers)

        with patch.dict(archive_access.os.environ, SYNTHETIC_KEYS, clear=True), \
                patch.object(archive_access, "request_bytes", side_effect=partial_failure) as network:
            code, report = self.capture(check_archives.main, ["--live", "--query", "飞虎队", "--permission-confirmed"])
        self.assertEqual(code, 1)
        self.assertEqual(network.call_count, 6)
        self.assertEqual(report["summary"], {"access_denied": 1, "ok": 5, "query_not_supported": 1, "manual_only": 3})
        self.assertEqual(report["results"][-1]["source"], "taiwan")
        loc = report["results"][0]
        self.assertTrue(loc["request_sent"])
        self.assertEqual(loc["http_status"], 403)
        self.assertNotIn("sample_count", loc)
        self.assertNotIn("synthetic-upstream-secret", json.dumps(report))

    def test_all_keyword_invalid_inputs_fail_before_any_network(self):
        for invalid in (["--query", ""], ["--query", "   "], ["--query", "飞" * 201],
                        ["--query", "飞虎队", "--rows", "0"], ["--query", "飞虎队", "--rows", "6"]):
            with self.subTest(arguments=invalid), patch.dict(archive_access.os.environ, SYNTHETIC_KEYS, clear=True), \
                    patch.object(archive_access, "request_bytes") as network, redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit) as raised:
                check_archives.main(["--source", "all", "--live"] + invalid)
            self.assertEqual(raised.exception.code, 2)
            network.assert_not_called()

    def test_table_keeps_zero_matches_distinct_from_skips_and_redacts_keys(self):
        output = io.StringIO()
        with patch.dict(archive_access.os.environ, {"EUROPEANA_API_KEY": SYNTHETIC_KEYS["EUROPEANA_API_KEY"]}, clear=True), \
                patch.object(archive_access, "request_bytes", side_effect=transport_for(api_responses(empty=True))), \
                redirect_stdout(output):
            code = check_archives.main(["--live", "--query", "飞虎队", "--format", "table"])
        text = output.getvalue()
        self.assertEqual(code, 2)
        self.assertIn("飞虎队", text)
        self.assertIn("unchanged; no translation", text)
        rows = {fields[0]: fields[1:] for line in text.splitlines()
                if (fields := line.split()) and fields[0] in check_archives.SOURCE_IDS}
        self.assertEqual(len(rows), 10)
        for source in ("loc", "ndl", "europeana"):
            self.assertEqual(rows[source], ["ok", "yes", "0", "0"])
        for source in ("nara", "nara_catalog", "dpla", "tna", "jacar", "iwm", "taiwan"):
            self.assertEqual(rows[source][1:], ["no", "-", "-"])
        self.assertNotIn(SYNTHETIC_KEYS["EUROPEANA_API_KEY"], text)

    def test_parser_errors_do_not_echo_argument_secrets(self):
        for main in (check_archives.main, importlib.import_module("access_europeana").main):
            error = io.StringIO()
            with redirect_stderr(error), self.assertRaises(SystemExit) as raised:
                main(["--not-an-option", "synthetic-secret"])
            self.assertEqual(raised.exception.code, 2)
            self.assertNotIn("synthetic-secret", error.getvalue())

    def test_invalid_row_limit_exits_two_without_request(self):
        with patch.object(archive_access, "request_bytes") as network:
            code, report = self.capture(importlib.import_module("access_loc").main, ["--rows", "6"])
            self.assertEqual((code, report["status"]), (2, "invalid_input"))
            self.assertFalse(report["request_sent"])
            network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
