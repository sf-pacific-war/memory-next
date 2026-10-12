"""Offline checks for bounded verification of selected official HTML records."""

from contextlib import redirect_stdout
from email.message import Message
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import check_mainland_sources as mainland


URL = "https://www.saac.gov.cn/zt/2014-09/15/content_67020.htm"
RECORD = {"id": "shac:test", "title": "松山战役电报", "source_url": URL,
          "page_markers": ["松山战役", "中国第二历史档案馆"],
          "archival_context": ["中国远征军"], "subjects": ["Burma campaign"]}
HTML = "<html><title>档案展示</title><body>松山战役电报 中国第二历史档案馆</body></html>".encode()


class Response(io.BytesIO):
    def __init__(self, body=HTML, *, url=URL, status=200, content_type="text/html; charset=utf-8", length=None):
        super().__init__(body)
        self.url = url
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        if length is not None:
            self.headers["Content-Length"] = str(length)
        self.read_sizes = []

    def geturl(self):
        return self.url

    def read(self, size=-1):
        self.read_sizes.append(size)
        return super().read(size)


def run_record(response=None, **kwargs):
    opener = Mock()
    opener.open.return_value = response or Response()
    report = mainland.check_records([("shac", RECORD)], live=True, opener=opener, **kwargs)
    return report["results"][0], opener


class MainlandSourceTests(unittest.TestCase):
    def test_default_is_offline_ready_and_no_network(self):
        opener = Mock()
        report = mainland.check_records([("shac", RECORD)], opener=opener)
        self.assertEqual(report["summary"], {"ready": 1})
        self.assertEqual(report["results"][0]["credential"], "not_required")
        self.assertFalse(report["results"][0]["request_sent"])
        self.assertIsNone(report["checked_at"])
        opener.open.assert_not_called()

    def test_live_verifies_markers_and_exact_single_bounded_get(self):
        response = Response()
        result, opener = run_record(response)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["bytes_read"], len(HTML))
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, URL)
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(opener.open.call_args.kwargs, {"timeout": 20})
        self.assertEqual(opener.open.call_count, 1)
        self.assertEqual(response.read_sizes, [mainland.MAX_BYTES + 1])

    def test_local_query_selects_without_changing_request_url(self):
        for query in ("松山", "SHAC:TEST", "远征军", "burma"):
            with self.subTest(query=query):
                result, opener = run_record(query=query)
                self.assertEqual(result["status"], "ok")
                self.assertEqual(opener.open.call_args.args[0].full_url, URL)

    def test_no_local_matches_sends_no_request_and_reports_no_remote_total(self):
        opener = Mock()
        report = mainland.check_records([("shac", RECORD)], live=True, query="absent", opener=opener)
        self.assertEqual(report["selected_count"], 0)
        self.assertEqual(report["results"], [])
        self.assertIn("no remote catalogue query", report["query_scope"])
        self.assertNotIn("total_results", report)
        opener.open.assert_not_called()

    def test_unsafe_urls_are_rejected_before_network(self):
        urls = ["http://www.saac.gov.cn/test.htm", "https://saac.gov.cn/test.htm",
                "https://www.saac.gov.cn.evil.example/test.htm", "https://evil.example/test.htm",
                "https://www.saac.gov.cn:444/test.htm", "https://user:pass@www.saac.gov.cn/test.htm",
                "https://www.saac.gov.cn/test.jpg", "https://www.saac.gov.cn/test.pdf",
                "https://www.saac.gov.cn/test.htm#anchor", None]
        opener = Mock()
        for url in urls:
            with self.subTest(url=url):
                report = mainland.check_records([("shac", {**RECORD, "source_url": url})], live=True, opener=opener)
                self.assertEqual(report["results"][0]["status"], "invalid_url")
        opener.open.assert_not_called()

    def test_source_host_must_match_verified_host(self):
        report = mainland.check_records([("yunnan", {**RECORD, "source_url": "https://www.ynxc.gov.cn/example.shtml"})], live=True, opener=Mock())
        self.assertEqual(report["results"][0]["status"], "invalid_url")

    def test_yunnan_html_is_allowed(self):
        url = "https://www.saac.gov.cn/mowcn/example.shtml"
        opener = Mock()
        opener.open.return_value = Response(url=url)
        report = mainland.check_records([("yunnan", {**RECORD, "source_url": url})], live=True, opener=opener)
        self.assertEqual(report["results"][0]["status"], "ok")

    def test_no_redirect_handler_rejects_target_without_following_it(self):
        with self.assertRaises(mainland.CheckError) as raised:
            mainland.NoRedirects().redirect_request(None, None, 302, "redirect", {}, "https://example.com/")
        self.assertEqual(raised.exception.status, "redirect_blocked")

    def test_defensive_final_url_and_redirect_status_validation(self):
        for response in (Response(url="https://evil.example/test.htm"), Response(status=302)):
            with self.subTest(response=response):
                result, opener = run_record(response)
                self.assertEqual(result["status"], "redirect_blocked")
                self.assertEqual(opener.open.call_count, 1)
                self.assertEqual(response.read_sizes, [])

    def test_non_html_mime_is_rejected_before_read(self):
        for mime in ("application/pdf", "image/jpeg", "application/json"):
            response = Response(content_type=mime)
            result, _ = run_record(response)
            self.assertEqual(result["status"], "invalid_content")
            self.assertEqual(response.read_sizes, [])

    def test_declared_oversize_is_rejected_without_downloading_body(self):
        response = Response(length=mainland.MAX_BYTES + 1)
        result, _ = run_record(response)
        self.assertEqual(result["status"], "response_too_large")
        self.assertEqual(response.read_sizes, [])

    def test_actual_body_size_bound_does_not_trust_small_content_length(self):
        response = Response(b"x" * (mainland.MAX_BYTES + 2), length=10)
        result, _ = run_record(response)
        self.assertEqual(result["status"], "response_too_large")
        self.assertEqual(response.read_sizes, [mainland.MAX_BYTES + 1])

    def test_http_200_login_and_challenge_are_not_usable(self):
        pages = ["<html><title>登录</title><body>松山战役 中国第二历史档案馆</body></html>",
                 "<html><title>Just a moment</title><body>松山战役 中国第二历史档案馆</body></html>",
                 '<html><body>松山战役 中国第二历史档案馆<input type="password"></body></html>']
        for page in pages:
            with self.subTest(page=page):
                result, _ = run_record(Response(page.encode()))
                self.assertEqual(result["status"], "access_blocked")

    def test_all_expected_markers_are_required(self):
        result, _ = run_record(Response("<html><body>松山战役</body></html>".encode()))
        self.assertEqual(result["status"], "content_mismatch")

    def test_hidden_script_and_comment_markers_cannot_pass(self):
        result, _ = run_record(Response("<html><body>松山战役<!-- 中国第二历史档案馆 --><script>中国第二历史档案馆</script></body></html>".encode()))
        self.assertEqual(result["status"], "content_mismatch")

    def test_image_and_document_references_are_checked_without_fetching_them(self):
        record = {**RECORD, "page_markers": ["松山战役", "scan.jpg", "guide.pdf"]}
        page = '<html><body>松山战役<img src="/scan.jpg"><a href="/guide.pdf">档案</a></body></html>'
        opener = Mock()
        opener.open.return_value = Response(page.encode())
        report = mainland.check_records([("shac", record)], live=True, opener=opener)
        self.assertEqual(report["results"][0]["status"], "ok")
        self.assertEqual(opener.open.call_count, 1)
        self.assertEqual(opener.open.call_args.args[0].full_url, URL)

    def test_hidden_document_references_cannot_satisfy_markers(self):
        record = {**RECORD, "page_markers": ["松山战役", "guide.pdf"]}
        page = '<html><body>松山战役<!-- <a href="guide.pdf"> --><script>"<a href=guide.pdf>"</script></body></html>'
        opener = Mock()
        opener.open.return_value = Response(page.encode())
        report = mainland.check_records([("shac", record)], live=True, opener=opener)
        self.assertEqual(report["results"][0]["status"], "content_mismatch")

    def test_title_is_fallback_when_page_markers_absent(self):
        record = {key: value for key, value in RECORD.items() if key != "page_markers"}
        opener = Mock()
        opener.open.return_value = Response()
        report = mainland.check_records([("shac", record)], live=True, opener=opener)
        self.assertEqual(report["results"][0]["status"], "ok")

    def test_invalid_markers_block_network(self):
        opener = Mock()
        for markers in ([], [""], [None], "松山战役"):
            report = mainland.check_records([("shac", {**RECORD, "page_markers": markers})], live=True, opener=opener)
            self.assertEqual(report["results"][0]["status"], "invalid_record")
        opener.open.assert_not_called()

    def test_duplicate_page_is_fetched_only_once(self):
        opener = Mock()
        opener.open.return_value = Response()
        report = mainland.check_records([("shac", RECORD), ("shac", {**RECORD, "id": "shac:second"})], live=True, opener=opener)
        self.assertEqual(report["summary"], {"ok": 2})
        self.assertEqual(opener.open.call_count, 1)
        self.assertEqual([r["request_sent"] for r in report["results"]], [True, False])

    def test_network_failures_are_reported_without_retry_or_exception_text(self):
        errors = [(TimeoutError("private"), "timeout"), (URLError(socket.timeout()), "timeout"),
                  (URLError("private"), "network_error"), (HTTPError(URL, 302, "private", {}, None), "redirect_blocked"),
                  (HTTPError(URL, 403, "private", {}, None), "access_blocked"),
                  (HTTPError(URL, 500, "private", {}, None), "http_error")]
        for error, status in errors:
            with self.subTest(status=status):
                opener = Mock()
                opener.open.side_effect = error
                report = mainland.check_records([("shac", RECORD)], live=True, opener=opener)
                self.assertEqual(report["results"][0]["status"], status)
                self.assertNotIn("private", json.dumps(report))
                self.assertEqual(opener.open.call_count, 1)

    def test_bad_encoding_and_non_document_content_are_rejected(self):
        for response in (Response(b"\xff"), Response(content_type="text/html; charset=nonexistent"),
                         Response("松山战役 中国第二历史档案馆".encode())):
            result, _ = run_record(response)
            self.assertEqual(result["status"], "invalid_content")

    def test_fixtureless_source_loader_and_cli_json(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "mainland-shac.json").write_text(json.dumps({"source": "SHAC", "records": [RECORD]}))
            Path(directory, "mainland-yunnan.json").write_text(json.dumps({"source": "Yunnan", "records": []}))
            records = mainland.load_records(data_dir=directory)
            self.assertEqual(len(records), 1)
            output = io.StringIO()
            with patch.object(mainland, "load_records", return_value=records), patch.object(mainland, "build_opener") as network, redirect_stdout(output):
                code = mainland.main(["--source", "shac", "--query", "松山"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())["summary"], {"ready": 1})
            network.assert_not_called()

    def test_cli_table_and_error_exit(self):
        output = io.StringIO()
        with patch.object(mainland, "load_records", return_value=[("shac", {**RECORD, "source_url": "https://example.com/a.htm"})]), redirect_stdout(output):
            code = mainland.main(["--format", "table"])
        self.assertEqual(code, 1)
        self.assertIn("invalid_url", output.getvalue())
        self.assertIn("requests: 0", output.getvalue())

    def test_cli_missing_data_is_explicit_error(self):
        output = io.StringIO()
        with patch.object(mainland, "load_records", side_effect=FileNotFoundError()), redirect_stdout(output):
            code = mainland.main([])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())["status"], "invalid_data")


if __name__ == "__main__":
    unittest.main()
