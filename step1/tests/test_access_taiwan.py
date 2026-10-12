"""Taiwan's public case-title CSV: offline contracts, provenance and scan limits."""

from contextlib import redirect_stdout, redirect_stderr
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import access_taiwan as adapter
import fetch_taiwan_metadata as taiwan


FETCHED_AT = "2026-10-11T12:34:56Z"
ROWS = [
    ("1", "國防部", "001/020", "駐印軍案", "114/01/02"),
    ("2", "國防部", "001/021", "中華民國駐印軍編制案", "114/01/02"),
    ("3", "外交部", "001/020", "飛虎隊與滇緬公路", "114/01/02"),
    ("4", "交通部", "002/019", "通信建設", "114/01/02"),
]


def fixture(rows=ROWS, columns=taiwan.COLUMNS, bom=True):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(columns)
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig" if bom else "utf-8")


def downloaded(data=None, complete=True):
    data = fixture() if data is None else data
    return taiwan.Download(data, complete, len(data), FETCHED_AT)


class TaiwanCsvTests(unittest.TestCase):
    def test_normalization_preserves_identity_and_dates_without_inventing_item_access(self):
        payload = taiwan.parse_csv(fixture(), "驻印军", fetched_at=FETCHED_AT)
        self.assertEqual((payload["total_results"], payload["scanned_rows"], payload["returned_count"]), (2, 4, 2))
        self.assertTrue(payload["scan_complete"])
        record = payload["records"][0]
        self.assertEqual(record["source"], "Taiwan NAA")
        self.assertTrue(record["id"].startswith("taiwan:"))
        self.assertEqual(record["archival_id"], "001/020")
        self.assertEqual(record["archival_context"], ["國防部"])
        self.assertEqual(record["dataset_generated_at"], "114/01/02")
        self.assertEqual(record["retrieved_at"], FETCHED_AT)
        self.assertIsNone(record["date_display"])
        self.assertEqual(record["year"], [])
        self.assertIsNone(record["description"])
        self.assertEqual(record["source_url"], "https://aa.archives.gov.tw/")
        self.assertEqual(record["source_url_kind"], "catalogue_search")
        self.assertEqual(record["metadata_rights"], "https://data.gov.tw/license")
        self.assertEqual(record["access_status"], "unverified")
        self.assertNotIn("thumbnail_url", record)
        self.assertNotIn("dataset_updated_at", record)
        self.assertEqual(record["record_origin"], "dataset")
        self.assertEqual(record["level_of_description"], "fileUnit")
        self.assertEqual(record["metadata_language"], ["zh-Hant"])
        self.assertEqual(record["language"], [])

    def test_ids_ignore_sequence_order_and_include_fonds(self):
        rows = [ROWS[0], ROWS[2]]
        first = taiwan.parse_csv(fixture(rows), "001/020")["records"]
        reordered = [tuple(["987", *ROWS[2][1:]]), tuple(["654", *ROWS[0][1:]])]
        second = taiwan.parse_csv(fixture(reordered), "001/020")["records"]
        self.assertEqual([item["id"] for item in first], [item["id"] for item in reversed(second)])
        self.assertNotEqual(first[0]["source_id"], first[1]["source_id"])
        self.assertEqual(first[0]["archival_id"], first[1]["archival_id"])

    def test_aliases_are_explicit_and_unknown_phrases_remain_literal(self):
        for query in ("飞虎队", "Flying Tigers", "Flying Tiger", "American Volunteer Group"):
            with self.subTest(query=query):
                payload = taiwan.parse_csv(fixture(), query)
                self.assertEqual(payload["total_results"], 1)
                self.assertEqual(payload["effective_query"], query)
                self.assertIn("飛虎隊", payload["effective_queries"])
        self.assertEqual(taiwan.parse_csv(fixture(), "Chinese Army in India")["total_results"], 2)
        self.assertEqual(taiwan.parse_csv(fixture(), "飛虎隊 駐印軍")["total_results"], 0)
        self.assertEqual(taiwan.expand_queries("unknown phrase"), ["unknown phrase"])
        self.assertEqual(taiwan.parse_csv(fixture(), "飞虎队 | 驻印军")["total_results"], 3)

    def test_sample_limit_does_not_stop_counting_matches(self):
        result = taiwan.parse_csv(fixture(), "驻印军", limit=1)
        self.assertEqual((result["returned_count"], result["matched_count"], result["total_results"]), (1, 2, 2))
        self.assertEqual(result["scanned_rows"], 4)

    def test_row_limit_never_reports_partial_matches_as_total(self):
        result = taiwan.parse_csv(fixture(), "飞虎队", max_scan_rows=2)
        self.assertEqual((result["scanned_rows"], result["matched_count"]), (2, 0))
        self.assertTrue(result["source_exhausted"])
        self.assertTrue(result["row_limit_reached"])
        self.assertFalse(result["scan_complete"])
        self.assertNotIn("total_results", result)
        exact = taiwan.parse_csv(fixture(), "飞虎队", max_scan_rows=4)
        self.assertTrue(exact["scan_complete"])
        self.assertFalse(exact["row_limit_reached"])

    def test_byte_prefix_discards_incomplete_row_and_reports_observed_only(self):
        raw = fixture(ROWS[:2])
        partial = raw[:raw.index("中華民國".encode()) + 1]
        result = taiwan.parse_csv(partial, "驻印军", source_exhausted=False)
        self.assertEqual((result["returned_count"], result["scanned_rows"]), (1, 1))
        self.assertFalse(result["scan_complete"])
        self.assertNotIn("total_results", result)
        with self.assertRaises(UnicodeError):
            taiwan.parse_csv(partial, "驻印军", source_exhausted=True)

    def test_quoted_commas_and_multiline_titles_survive_but_partial_quoted_tail_does_not(self):
        rows = [ROWS[0], ("2", "國防部", "002", "駐印軍,\n編制案", "1140102")]
        data = fixture(rows)
        complete = taiwan.parse_csv(data, "驻印军")
        self.assertEqual(complete["records"][1]["title"], "駐印軍,\n編制案")
        truncated = data[:data.index("編制案".encode())]
        partial = taiwan.parse_csv(truncated, "驻印军", source_exhausted=False)
        self.assertEqual(partial["scanned_rows"], 1)
        self.assertEqual(partial["matched_count"], 1)
        with self.assertRaises(ValueError):
            taiwan.parse_csv(truncated, "驻印军", source_exhausted=True)

    def test_bom_optional_and_columns_are_named_not_positional(self):
        fields = tuple(reversed(taiwan.COLUMNS))
        swapped = [tuple(reversed(row)) for row in ROWS]
        result = taiwan.parse_csv(fixture(swapped, fields, bom=False), "驻印军")
        self.assertEqual(result["records"][0]["title"], ROWS[0][3])
        self.assertEqual(result["total_results"], 2)

    def test_invalid_schema_rows_and_utf8_are_rejected(self):
        malformed = [b"<html>Access denied</html>", b"", b"\xff", fixture(columns=("title", "id")),
                     fixture(rows=[ROWS[0][:-1]]), fixture(rows=[("1", "", "001", "題名", "114")]),
                     fixture(rows=[("1", "全宗", "", "題名", "114")]),
                     fixture(rows=[("1", "全宗", "001", "", "114")]),
                     fixture(columns=("序號", "全宗名", "檔號", "案名", "案名"))]
        for data in malformed:
            with self.subTest(data=data[:30]), self.assertRaises(ValueError):
                taiwan.parse_csv(data, "驻印军")

    def test_duplicate_identity_counts_once_and_conflicts_fail(self):
        result = taiwan.parse_csv(fixture([ROWS[0], ROWS[0]]), "驻印军")
        self.assertEqual((result["scanned_rows"], result["duplicate_rows"], result["total_results"]), (2, 1, 1))
        conflict = (*ROWS[0][:3], "不同題名", ROWS[0][4])
        with self.assertRaises(ValueError):
            taiwan.parse_csv(fixture([ROWS[0], conflict]), "驻印军")

    def test_bounds_queries_and_retrieval_timestamps_validate(self):
        for options in ({"limit": 0}, {"limit": True}, {"limit": 101}, {"max_scan_rows": 0},
                        {"source_exhausted": 1}, {"fetched_at": "1942"}, {"fetched_at": "2026-10-11T12:00:00"}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                taiwan.parse_csv(fixture(), "驻印军", **options)
        for query in ("", " ", "x" * 201, "a||b", "|a", "|".join(["a"] * 9), None):
            with self.subTest(query=query), self.assertRaises(ValueError):
                taiwan.parse_csv(fixture(), query)


class TaiwanTransportTests(unittest.TestCase):
    def test_bounded_reader_detects_actual_eof_with_one_lookahead_byte(self):
        for data, complete, actual_read in ((b"123", True, 3), (b"1234", True, 4), (b"12345", False, 5),
                                            (b"123456789", False, 5)):
            with self.subTest(data=data):
                result = taiwan.read_bounded(io.BytesIO(data), 4)
                self.assertEqual(result.data, data[:4])
                self.assertEqual(result.source_exhausted, complete)
                self.assertEqual(result.bytes_read, actual_read)

    def test_reader_rejects_invalid_bounds_and_expired_budget(self):
        for bound in (0, -1, True, taiwan.MAX_BYTES + 1):
            with self.subTest(bound=bound), self.assertRaises(ValueError):
                taiwan.read_bounded(io.BytesIO(), bound)
        with patch.object(taiwan.time, "monotonic", return_value=100), self.assertRaises(TimeoutError):
            taiwan.read_bounded(io.BytesIO(b"test"), 10, deadline=99)

    def fake_response(self, data, status=200, content_type="text/csv; charset=utf-8"):
        response = io.BytesIO(data)
        response.status = status
        response.headers = {"Content-Type": content_type}
        return response

    def test_one_fixed_url_request_with_no_redirect_and_no_content_length_assumption(self):
        with patch.object(taiwan, "build_opener") as opener:
            opener.return_value.open.return_value = self.fake_response(fixture())
            result = taiwan.fetch_csv(128)
        self.assertEqual(result.bytes_read, 129)
        self.assertFalse(result.source_exhausted)
        self.assertIsInstance(opener.call_args.args[0], taiwan.NoRedirect)
        opener.return_value.open.assert_called_once()
        request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, taiwan.CSV_URL)
        self.assertEqual(request.get_method(), "GET")
        self.assertNotIn("Authorization", request.headers)
        self.assertIsNotNone(result.fetched_at)

    def test_http_wrong_type_and_encoded_response_fail(self):
        for response in (self.fake_response(b"", status=206), self.fake_response(b"<html>", content_type="text/html")):
            with self.subTest(status=response.status, headers=response.headers), patch.object(taiwan, "build_opener") as opener:
                opener.return_value.open.return_value = response
                with self.assertRaises((HTTPError, ValueError)):
                    taiwan.fetch_csv()
        response = self.fake_response(b"compressed")
        response.headers["Content-Encoding"] = "gzip"
        with patch.object(taiwan, "build_opener") as opener:
            opener.return_value.open.return_value = response
            with self.assertRaises(ValueError):
                taiwan.fetch_csv()


class TaiwanCommandsTests(unittest.TestCase):
    def capture(self, main, args):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(args)
        return code, json.loads(output.getvalue())

    def test_check_offline_is_ready_and_live_returns_counts_without_records(self):
        transport = Mock(return_value=downloaded())
        offline = adapter.check(query="驻印军", request=transport)
        self.assertEqual(offline["status"], "ready")
        self.assertEqual(offline["access_mode"], "csv")
        self.assertFalse(offline["request_sent"])
        self.assertNotIn("sample_count", offline)
        transport.assert_not_called()
        live = adapter.check(query="驻印军", rows=1, live=True, request=transport)
        transport.assert_called_once_with(taiwan.DEFAULT_MAX_BYTES)
        self.assertEqual((live["status"], live["sample_count"], live["total_results"]), ("ok", 1, 2))
        self.assertEqual(live["credential_state"], "not_required")
        self.assertNotIn("records", live)
        self.assertNotIn("駐印軍編制案", json.dumps(live, ensure_ascii=False))

    def test_check_partial_zero_is_success_but_not_zero_total(self):
        result = adapter.check(query="nothing", live=True, request=Mock(return_value=downloaded(complete=False)))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["sample_count"], 0)
        self.assertEqual(result["matched_count"], 0)
        self.assertNotIn("total_results", result)
        self.assertFalse(result["scan_complete"])
        self.assertIn("Partial", result["message"])

    def test_check_invalid_arguments_never_send_request(self):
        for options in ({"rows": 0}, {"rows": 6}, {"query": "|"}):
            request = Mock()
            with self.subTest(options=options):
                result = adapter.check(live=True, request=request, **options)
                self.assertEqual(result["status"], "invalid_input")
                self.assertFalse(result["request_sent"])
                request.assert_not_called()

    def test_check_failures_are_not_empty_results_and_do_not_leak_upstream_text(self):
        failures = [(HTTPError("https://example.invalid/secret", 403, "secret", {}, None), "access_denied"),
                    (HTTPError("https://example.invalid/secret", 302, "secret", {}, None), "redirect_blocked"),
                    (HTTPError("https://example.invalid/secret", 429, "secret", {}, None), "rate_limited"),
                    (URLError("secret"), "network_error"), (TimeoutError("secret"), "timeout"),
                    (ValueError("secret"), "invalid_response")]
        for failure, status in failures:
            with self.subTest(status=status):
                result = adapter.check(live=True, request=Mock(side_effect=failure))
                self.assertEqual(result["status"], status)
                self.assertNotIn("secret", json.dumps(result))
                self.assertNotIn("sample_count", result)
                self.assertTrue(result["request_sent"])

    def test_importer_default_is_no_network_and_no_file(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(taiwan, "fetch_csv") as transport:
            output = Path(directory) / "snapshot.json"
            code, result = self.capture(taiwan.main, ["--query", "驻印军", "--output", str(output)])
            self.assertEqual((code, result["status"]), (0, "ready"))
            self.assertFalse(output.exists())
            transport.assert_not_called()

    def test_local_partial_input_preserves_unknown_scope_and_original_retrieval_time(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(taiwan, "fetch_csv") as transport:
            source = Path(directory) / "input.csv"
            output = Path(directory) / "snapshot.json"
            source.write_bytes(fixture())
            args = ["--input", str(source), "--partial-input", "--fetched-at", FETCHED_AT,
                    "--query", "驻印军", "--rows", "1", "--output", str(output)]
            code, report = self.capture(taiwan.main, args)
            snapshot = json.loads(output.read_text())
            self.assertEqual((code, report["status"]), (0, "ok"))
            self.assertFalse(report["request_sent"])
            self.assertFalse(snapshot["scan_complete"])
            self.assertNotIn("total_results", snapshot)
            self.assertEqual(snapshot["fetched_at"], FETCHED_AT)
            self.assertEqual(snapshot["records"][0]["retrieved_at"], FETCHED_AT)
            self.assertEqual(snapshot["matched_count"], 2)
            transport.assert_not_called()

    def test_local_input_without_original_timestamp_does_not_invent_freshness(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "input.csv", Path(directory) / "output.json"
            source.write_bytes(fixture())
            self.capture(taiwan.main, ["--input", str(source), "--output", str(output)])
            snapshot = json.loads(output.read_text())
            self.assertIsNone(snapshot["fetched_at"])
            self.assertIsNone(snapshot["records"][0]["retrieved_at"])

    def test_failed_refresh_preserves_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(taiwan, "fetch_csv", return_value=downloaded(b"<html>bad</html>")):
            output = Path(directory) / "snapshot.json"
            output.write_text("previous snapshot\n")
            code, result = self.capture(taiwan.main, ["--live", "--output", str(output)])
            self.assertEqual((code, result["status"]), (1, "error"))
            self.assertEqual(output.read_text(), "previous snapshot\n")
            self.assertEqual(list(output.parent.iterdir()), [output])

    def test_importer_invalid_modes_fail_before_network_or_output(self):
        for args in (["--live", "--input", "fake.csv"], ["--partial-input"],
                     ["--fetched-at", FETCHED_AT], ["--rows", "101"], ["--max-bytes", "0"]):
            with self.subTest(args=args), patch.object(taiwan, "fetch_csv") as network, \
                    redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                taiwan.main(args)
            self.assertEqual(raised.exception.code, 2)
            network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
