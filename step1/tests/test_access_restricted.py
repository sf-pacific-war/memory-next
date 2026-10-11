"""Offline contract checks: synthetic responses and no real credentials or APIs."""

import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import archive_access
import access_dpla as dpla
import access_nara_catalog as nara
import access_tna as tna
import access_jacar as jacar
import access_iwm as iwm
import access_taiwan as taiwan


FAKE_KEY = "synthetic-unit-test-key"
PAYLOADS = {
    dpla: {"count": 7, "docs": [{"id": "synthetic-1", "sourceResource": {"title": "Fixture"}}]},
    nara: {"statusCode": 200, "body": {"hits": {"total": {"value": 7, "relation": "eq"},
            "hits": [{"_id": "123", "_source": {"record": {"naId": 123, "title": "Fixture"}}}]}}},
    tna: {"Count": 7, "Records": [{"Id": "C123", "Title": "Fixture", "Reference": "TEST 1"}]},
}
EMPTY_PAYLOADS = {
    dpla: {"count": 0, "docs": []},
    nara: {"body": {"hits": {"total": {"value": 0, "relation": "eq"}, "hits": []}}},
    tna: {"Count": 0, "Records": []},
}


def response(payload):
    return Mock(return_value=json.dumps(payload).encode("utf-8"))


class RestrictedApiTests(unittest.TestCase):
    def test_three_documented_search_shapes(self):
        for module, payload in PAYLOADS.items():
            with self.subTest(source=module.SOURCE.id):
                request = response(payload)
                result = module.probe("缅甸 Burma & 中国", 1, FAKE_KEY, request)
                self.assertEqual(result, {"sample_count": 1, "total_results": 7})
                request.assert_called_once()
                url = urlsplit(request.call_args.args[0])
                self.assertEqual(url.scheme + "://" + url.netloc + url.path, module.SOURCE.endpoint)
                params = parse_qs(url.query)
                key = "SearchQuery" if module is tna else "q"
                self.assertEqual(params[key], ["缅甸 Burma & 中国"])
                headers = request.call_args.kwargs["headers"]
                self.assertEqual(headers["Accept"], "application/json")
                if module is dpla:
                    self.assertEqual(params["api_key"], [FAKE_KEY])
                    self.assertEqual(params["page_size"], ["1"])
                    self.assertEqual(params["page"], ["1"])
                elif module is nara:
                    self.assertEqual(params["limit"], ["1"])
                    self.assertEqual(headers["x-api-key"], FAKE_KEY)
                    self.assertNotIn(FAKE_KEY, url.query)
                else:
                    self.assertEqual(params["ResultsPageSize"], ["1"])
                    self.assertEqual(params["Page"], ["0"])
                    self.assertNotIn(FAKE_KEY, json.dumps(request.call_args.args))
                    self.assertNotIn(FAKE_KEY, json.dumps(headers))

    def test_valid_empty_results_are_zero(self):
        for module, payload in EMPTY_PAYLOADS.items():
            with self.subTest(source=module.SOURCE.id):
                self.assertEqual(module.probe("Burma", 1, FAKE_KEY, response(payload)),
                                 {"sample_count": 0, "total_results": 0})

    def test_missing_and_non_json_responses_are_not_empty_results(self):
        for module in PAYLOADS:
            for raw in [b"not json", b"<html>Login required</html>", b"[]", b"null", b"{}", b"\xff"]:
                with self.subTest(source=module.SOURCE.id, raw=raw), self.assertRaises(ValueError):
                    module.probe("Burma", 1, FAKE_KEY, Mock(return_value=raw))

    def test_missing_total_or_records_are_invalid(self):
        for module in PAYLOADS:
            for missing in ["total", "records"]:
                payload = copy.deepcopy(EMPTY_PAYLOADS[module])
                target = payload["body"]["hits"] if module is nara else payload
                total_key, record_key = (("total", "hits") if module is nara else
                                         ("count", "docs") if module is dpla else ("Count", "Records"))
                del target[total_key if missing == "total" else record_key]
                with self.subTest(source=module.SOURCE.id, missing=missing), self.assertRaises(ValueError):
                    module.probe("Burma", 1, FAKE_KEY, response(payload))

    def test_counts_must_be_nonnegative_integers(self):
        for module in PAYLOADS:
            for total in [-1, True, "0", 0.0, None]:
                payload = copy.deepcopy(EMPTY_PAYLOADS[module])
                if module is nara:
                    payload["body"]["hits"]["total"]["value"] = total
                else:
                    payload["count" if module is dpla else "Count"] = total
                with self.subTest(source=module.SOURCE.id, total=total), self.assertRaises(ValueError):
                    module.probe("Burma", 1, FAKE_KEY, response(payload))

    def test_record_lists_and_sample_limits_are_checked(self):
        for module in PAYLOADS:
            for records in [None, {}, "bad", ["bad"], [{}, {}]]:
                payload = copy.deepcopy(PAYLOADS[module])
                if module is nara:
                    payload["body"]["hits"]["hits"] = records
                else:
                    payload["docs" if module is dpla else "Records"] = records
                with self.subTest(source=module.SOURCE.id, records=records), self.assertRaises(ValueError):
                    module.probe("Burma", 1, FAKE_KEY, response(payload))

    def test_api_reported_errors_are_rejected_even_with_zero_counts(self):
        for module in PAYLOADS:
            for name in ["error", "errors"]:
                payload = copy.deepcopy(EMPTY_PAYLOADS[module])
                payload[name] = "Synthetic API error"
                with self.subTest(source=module.SOURCE.id, error=name), self.assertRaises(ValueError):
                    module.probe("Burma", 1, FAKE_KEY, response(payload))
        for status in [401, 403, 429, 500, "200", 200.0]:
            payload = copy.deepcopy(EMPTY_PAYLOADS[nara])
            payload["statusCode"] = status
            with self.subTest(nara_status=status), self.assertRaises(ValueError):
                nara.probe("Burma", 1, FAKE_KEY, response(payload))

    def test_nara_lower_bound_is_not_reported_as_exact_total(self):
        payload = copy.deepcopy(PAYLOADS[nara])
        payload["body"]["hits"]["total"] = {"value": 10000, "relation": "gte"}
        self.assertEqual(nara.probe("Burma", 1, FAKE_KEY, response(payload)), {"sample_count": 1})
        for relation in [None, "unknown", [], {}]:
            payload["body"]["hits"]["total"]["relation"] = relation
            with self.subTest(relation=relation), self.assertRaises(ValueError):
                nara.probe("Burma", 1, FAKE_KEY, response(payload))

    def test_bad_nested_nara_responses_raise_value_error(self):
        for payload in [{"body": None}, {"body": "{}"}, {"body": {"hits": None}},
                        {"body": {"hits": {"total": 0, "hits": []}}},
                        {"body": {"error": "denied", "hits": {"total": {"value": 0}, "hits": []}}}]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                nara.probe("Burma", 1, FAKE_KEY, response(payload))

    def test_adapter_rows_bound_before_network(self):
        for module in PAYLOADS:
            for rows in [0, 6, True, "1"]:
                request = Mock()
                with self.subTest(source=module.SOURCE.id, rows=rows), self.assertRaises(ValueError):
                    module.probe("Burma", rows, FAKE_KEY, request)
                request.assert_not_called()

    def test_missing_credentials_are_gated_without_network(self):
        for module in [dpla, nara]:
            with self.subTest(source=module.SOURCE.id):
                request = Mock()
                result = archive_access.check_source(module.SOURCE, module.probe, live=True,
                                                      environ={}, request=request)
                self.assertEqual(result["status"], "missing_credential")
                self.assertFalse(result["request_sent"])
                request.assert_not_called()

    def test_tna_approval_is_not_an_api_key(self):
        request = response(EMPTY_PAYLOADS[tna])
        result = archive_access.check_source(tna.SOURCE, tna.probe, live=True, environ={}, request=request)
        self.assertEqual(result["status"], "permission_required")
        self.assertEqual(result["credential_state"], "not_required")
        request.assert_not_called()
        result = archive_access.check_source(tna.SOURCE, tna.probe, live=True, environ={},
                                              permission_confirmed=True, request=request)
        self.assertEqual(result["status"], "ok")
        request.assert_called_once()

    def test_configured_keys_and_dry_run_are_not_claimed_verified(self):
        for module in [dpla, nara]:
            request = Mock()
            result = archive_access.check_source(module.SOURCE, module.probe,
                                                  environ={module.SOURCE.credential_env: FAKE_KEY}, request=request)
            with self.subTest(source=module.SOURCE.id):
                self.assertEqual(result["status"], "ready")
                self.assertEqual(result["credential_state"], "configured")
                self.assertFalse(result["request_sent"])
                self.assertNotIn(FAKE_KEY, json.dumps(result))
                request.assert_not_called()

    def test_live_summaries_do_not_include_records_or_secrets(self):
        for module, payload in PAYLOADS.items():
            result = archive_access.check_source(module.SOURCE, module.probe, live=True, rows=1,
                                                  permission_confirmed=True,
                                                  environ={module.SOURCE.credential_env: FAKE_KEY}, request=response(payload))
            with self.subTest(source=module.SOURCE.id):
                self.assertEqual(result["status"], "ok")
                self.assertEqual(result["sample_count"], 1)
                self.assertNotIn("Fixture", json.dumps(result))
                self.assertNotIn(FAKE_KEY, json.dumps(result))


class PortalAccessTests(unittest.TestCase):
    def test_portals_never_send_requests_even_with_live(self):
        for module in [jacar, iwm, taiwan]:
            for live in [False, True]:
                request = Mock()
                result = archive_access.check_source(module.SOURCE, module.probe, live=live, request=request)
                with self.subTest(source=module.SOURCE.id, live=live):
                    self.assertEqual(result["status"], "manual_only")
                    self.assertEqual(result["credential_state"], "not_applicable")
                    self.assertEqual(result["access_mode"], "portal")
                    self.assertFalse(result["request_sent"])
                    self.assertIsNone(module.probe)
                    self.assertNotIn("sample_count", result)
                    self.assertEqual(urlsplit(result["portal_url"]).scheme, "https")
                    request.assert_not_called()

    def test_each_entrypoint_has_working_main(self):
        for module in [dpla, nara, tna, jacar, iwm, taiwan]:
            with self.subTest(source=module.SOURCE.id), patch.object(module, "run_cli", return_value=2) as cli:
                self.assertEqual(module.main(["--live"]), 2)
                cli.assert_called_once_with(module.SOURCE, module.probe, ["--live"])

    def test_portal_cli_outputs_manual_status(self):
        for module in [jacar, iwm, taiwan]:
            with self.subTest(source=module.SOURCE.id), patch("sys.stdout", new_callable=io.StringIO) as stdout:
                self.assertEqual(module.main([]), 0)
                self.assertEqual(json.loads(stdout.getvalue())["status"], "manual_only")


if __name__ == "__main__":
    unittest.main()
