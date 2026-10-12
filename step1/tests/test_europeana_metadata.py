"""Credential-free unit tests; never connect to Europeana."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "fetch_europeana_metadata.py"
SPEC = importlib.util.spec_from_file_location("europeana_metadata", SCRIPT)
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)
FAKE_KEY = "synthetic-test-credential-only"
AT = "2026-10-09T00:00:00Z"


def fixture(**overrides):
    item = {
        "id": "/123/document",
        "title": ["Burma Road", "滇缅公路"],
        "dcDescription": ["A catalogued object."],
        "dataProvider": ["Example Museum"],
        "provider": ["Example Aggregator"],
        "year": ["1972"],
        "type": "TEXT",
        "dcLanguage": ["eng"],
        "language": ["en"],
        "edmIsShownAt": ["https://museum.example.org/object/123"],
        "guid": "https://www.europeana.eu/item/123/document?utm_campaign=" + FAKE_KEY,
        "link": "https://api.europeana.eu/record/v2/123/document.json?wskey=" + FAKE_KEY,
        "edmPreview": ["https://museum.example.org/image.jpg"],
        "rights": ["http://rightsstatements.org/vocab/InC/1.0/"],
    }
    item.update(overrides)
    return {"apikey": FAKE_KEY, "success": True, "totalResults": 12, "items": [item]}


class NormalizationTests(unittest.TestCase):
    def test_expected_fields_and_date_are_preserved(self):
        result = api.normalize_response(fixture(), "Burma Road", AT)
        item = result["records"][0]
        self.assertEqual(result["total_results"], 12)
        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(item["id"], "europeana:/123/document")
        self.assertEqual(item["source_id"], "/123/document")
        self.assertEqual(item["date_display"], "1972")
        self.assertEqual(item["date_kind"], "source_supplied")
        self.assertEqual(item["holding_institution"], ["Example Museum"])
        self.assertEqual(item["metadata_rights"], api.CC0)
        self.assertEqual(item["access_status"], "unverified")
        self.assertEqual(item["review_status"], "candidate")
        self.assertEqual(item["language"], ["eng"])
        self.assertEqual(item["metadata_language"], ["en"])
        self.assertEqual(item["source_url"], "https://museum.example.org/object/123")
        self.assertNotIn("start_year", item)
        self.assertNotIn("edmPreview", item)

    def test_optional_fields_missing_do_not_invent_values(self):
        item = api.normalize_item({"id": "/123/a"}, "Burma", AT)
        self.assertIsNone(item["title"])
        self.assertIsNone(item["description"])
        self.assertIsNone(item["date_display"])
        self.assertEqual(item["language"], [])
        self.assertEqual(item["metadata_language"], [])
        self.assertEqual(item["content_rights"], [])
        self.assertEqual(item["source_url"], "https://www.europeana.eu/item/123/a")

    def test_metadata_language_is_not_used_as_original_language(self):
        item = api.normalize_item({"id": "/123/a", "language": ["fr"]}, "Burma", AT)
        self.assertEqual(item["language"], [])
        self.assertEqual(item["metadata_language"], ["fr"])

    def test_original_and_metadata_language_are_kept_separately(self):
        item = api.normalize_item({"id": "/123/a", "dcLanguage": ["eng", "jpn"], "language": ["fr"]}, "Burma", AT)
        self.assertEqual(item["language"], ["eng", "jpn"])
        self.assertEqual(item["metadata_language"], ["fr"])

    def test_missing_id_rejects_entire_document(self):
        for value in [{}, {"id": ""}, {"id": 42}, None]:
            with self.subTest(value=value), self.assertRaises(api.FetchError):
                api.normalize_item(value, "Burma", AT)

    def test_date_is_not_interpreted_as_battle_date(self):
        item = api.normalize_item({"id": "/123/a", "year": ["1944", "1972", "unknown"]}, "Burma", AT)
        self.assertEqual(item["date_display"], "1944; 1972; unknown")
        self.assertEqual(item["year"], ["1944", "1972", "unknown"])

    def test_unsafe_links_fall_back_to_europeana(self):
        unsafe = ["javascript:alert(1)", "https://user:pass@example.org/a", "http://127.0.0.1/a", "https://localhost/a", "https://example.org/ bad"]
        for url in unsafe:
            with self.subTest(url=url):
                item = api.normalize_item({"id": "/123/a", "edmIsShownAt": [url], "guid": "https://attacker.example.org/a"}, "Burma", AT)
                self.assertEqual(item["source_url"], "https://www.europeana.eu/item/123/a")

    def test_valid_second_source_link_and_query_parameters(self):
        item = api.normalize_item({"id": "/123/a", "edmIsShownAt": ["javascript:bad", "https://museum.example.org/view?id=123&wskey=secret"]}, "Burma", AT)
        self.assertEqual(item["source_url"], "https://museum.example.org/view?id=123")

    def test_key_and_raw_api_link_never_appear_in_saved_metadata(self):
        text = api.serialize_without_key(api.normalize_response(fixture(), "Burma Road", AT), FAKE_KEY)
        self.assertNotIn(FAKE_KEY, text)
        self.assertNotIn("api.europeana.eu", text)
        self.assertNotIn("wskey", text)

    def test_key_echo_in_any_normalized_value_blocks_output(self):
        result = api.normalize_response(fixture(title=[FAKE_KEY]), "Burma Road", AT)
        with self.assertRaises(api.FetchError):
            api.serialize_without_key(result, FAKE_KEY)

    def test_invalid_response_structures(self):
        payloads = [None, [], {"success": False}, {"success": True, "totalResults": True, "items": []}, {"success": True, "totalResults": 1, "items": {}}, {"success": True, "totalResults": 0, "items": [{}]}]
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(api.FetchError):
                api.normalize_response(payload, "Burma", AT)

    def test_empty_success(self):
        result = api.normalize_response({"success": True, "totalResults": 0, "items": []}, "Burma", AT)
        self.assertEqual(result["returned_count"], 0)


class CredentialTests(unittest.TestCase):
    def test_environment_has_priority(self):
        with patch.dict(os.environ, {api.KEY_NAME: FAKE_KEY}, clear=True), patch.object(Path, "read_text") as read:
            self.assertEqual(api.load_key("missing-file"), FAKE_KEY)
            read.assert_not_called()

    def test_missing_key_never_requests(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(api, "build_opener") as opener, redirect_stderr(io.StringIO()):
            self.assertEqual(api.main(["--query", "Burma", "--output", "unused.json"]), 1)
            opener.assert_not_called()

    def test_literal_env_file_parsing_does_not_execute_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            env_file = root / ".env.europeana"
            literal = "$(do-not-execute)"
            env_file.write_text("# local\nEUROPEANA_API_KEY=" + literal + "\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True), patch.object(api, "PROJECT_ROOT", root), patch.object(api.subprocess, "run", return_value=MagicMock(returncode=0)) as run:
                self.assertEqual(api.load_key(env_file), literal)
                self.assertEqual(run.call_count, 1)
                self.assertEqual(run.call_args.args[0][:3], ["git", "check-ignore", "--quiet"])

    def test_unignored_env_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            env_file = root / "credential.txt"
            env_file.write_text("EUROPEANA_API_KEY=" + FAKE_KEY, encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True), patch.object(api, "PROJECT_ROOT", root), patch.object(api.subprocess, "run", return_value=MagicMock(returncode=1)), self.assertRaises(api.FetchError):
                api.load_key(env_file)

    def test_duplicate_or_empty_key_rejected(self):
        for contents in ["EUROPEANA_API_KEY=\n", "EUROPEANA_API_KEY=a\nEUROPEANA_API_KEY=b\n"]:
            with self.subTest(contents=contents), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                env_file = root / ".env.local"
                env_file.write_text(contents, encoding="utf-8")
                with patch.dict(os.environ, {}, clear=True), patch.object(api, "PROJECT_ROOT", root), patch.object(api.subprocess, "run", return_value=MagicMock(returncode=0)), self.assertRaises(api.FetchError):
                    api.load_key(env_file)


class RequestTests(unittest.TestCase):
    def response(self, payload):
        response = MagicMock()
        response.status = 200
        response.read.return_value = json.dumps(payload).encode()
        response.__enter__.return_value = response
        return response

    def test_one_request_fixed_timeout_and_profile(self):
        with patch.object(api, "build_opener") as builder:
            builder.return_value.open.return_value = self.response(fixture())
            result = api.fetch_metadata("Burma Road", 3, FAKE_KEY)
            self.assertEqual(result["returned_count"], 1)
            builder.return_value.open.assert_called_once()
            request = builder.return_value.open.call_args.args[0]
            self.assertEqual(builder.return_value.open.call_args.kwargs, {"timeout": 30})
            query = parse_qs(urlsplit(request.full_url).query)
            self.assertEqual(query, {"query": ["Burma Road"], "rows": ["3"], "profile": ["rich"], "wskey": [FAKE_KEY]})
            self.assertIsInstance(builder.call_args.args[0], api.NoRedirect)

    def test_redirect_handler_never_follows(self):
        self.assertIsNone(api.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.org/?wskey=" + FAKE_KEY))

    def test_failures_are_sanitized_and_preserve_old_output(self):
        errors = [
            HTTPError("https://example.org/?wskey=" + FAKE_KEY, 401, FAKE_KEY, {}, io.BytesIO(FAKE_KEY.encode())),
            HTTPError("https://example.org/?wskey=" + FAKE_KEY, 302, FAKE_KEY, {}, io.BytesIO(FAKE_KEY.encode())),
            TimeoutError(FAKE_KEY),
        ]
        for error in errors:
            with self.subTest(error_type=type(error).__name__), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "sample.json"
                output.write_text("previous-good-data", encoding="utf-8")
                stdout, stderr = io.StringIO(), io.StringIO()
                with patch.dict(os.environ, {api.KEY_NAME: FAKE_KEY}, clear=True), patch.object(api, "build_opener") as builder, redirect_stdout(stdout), redirect_stderr(stderr):
                    builder.return_value.open.side_effect = error
                    self.assertEqual(api.main(["--query", "Burma", "--output", str(output)]), 1)
                    builder.return_value.open.assert_called_once()
                self.assertNotIn(FAKE_KEY, stdout.getvalue() + stderr.getvalue())
                self.assertNotIn("https://", stderr.getvalue())
                self.assertEqual(output.read_text(), "previous-good-data")

    def test_invalid_json_preserves_old_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sample.json"
            output.write_text("previous-good-data", encoding="utf-8")
            response = self.response({})
            response.read.return_value = ("not-json " + FAKE_KEY).encode()
            stderr = io.StringIO()
            with patch.dict(os.environ, {api.KEY_NAME: FAKE_KEY}, clear=True), patch.object(api, "build_opener") as builder, redirect_stderr(stderr):
                builder.return_value.open.return_value = response
                self.assertEqual(api.main(["--query", "Burma", "--output", str(output)]), 1)
            self.assertEqual(output.read_text(), "previous-good-data")
            self.assertNotIn(FAKE_KEY, stderr.getvalue())

    def test_secret_echo_preserves_old_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sample.json"
            output.write_text("previous-good-data", encoding="utf-8")
            stderr = io.StringIO()
            with patch.dict(os.environ, {api.KEY_NAME: FAKE_KEY}, clear=True), patch.object(api, "build_opener") as builder, redirect_stderr(stderr):
                builder.return_value.open.return_value = self.response(fixture(title=[FAKE_KEY]))
                self.assertEqual(api.main(["--query", "Burma", "--output", str(output)]), 1)
            self.assertEqual(output.read_text(), "previous-good-data")
            self.assertNotIn(FAKE_KEY, stderr.getvalue())

    def test_success_atomically_replaces_output_with_no_raw_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sample.json"
            output.write_text("previous-good-data", encoding="utf-8")
            stdout = io.StringIO()
            with patch.dict(os.environ, {api.KEY_NAME: FAKE_KEY}, clear=True), patch.object(api, "build_opener") as builder, redirect_stdout(stdout):
                builder.return_value.open.return_value = self.response(fixture())
                self.assertEqual(api.main(["--query", "Burma", "--output", str(output)]), 0)
            self.assertEqual(json.loads(output.read_text())["returned_count"], 1)
            self.assertNotIn(FAKE_KEY, output.read_text() + stdout.getvalue())
            self.assertEqual(list(Path(directory).glob(".europeana-*.tmp")), [])

    def test_invalid_rows_never_requests(self):
        for rows in ["0", "101"]:
            with self.subTest(rows=rows), patch.object(api, "build_opener") as builder, redirect_stderr(io.StringIO()):
                self.assertEqual(api.main(["--query", "Burma", "--rows", rows, "--output", "unused.json"]), 1)
                builder.assert_not_called()


if __name__ == "__main__":
    unittest.main()
