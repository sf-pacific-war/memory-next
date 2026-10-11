"""Exercise the user-facing per-source and combined commands without networking."""

from contextlib import redirect_stderr, redirect_stdout
import importlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import archive_access
import check_archives


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
            self.assertEqual(report["summary"], {"ready": 4, "missing_credential": 2, "permission_required": 1, "manual_only": 2})
            self.assertEqual(len(report["results"]), 9)
            self.assertNotIn("synthetic-key", json.dumps(report))
            network.assert_not_called()

    def test_live_on_manual_or_unconfigured_sources_is_an_explicit_skip(self):
        with patch.dict(archive_access.os.environ, {}, clear=True), patch.object(archive_access, "request_bytes") as network:
            for source_id in ("europeana", "dpla", "nara_catalog", "tna", "jacar", "iwm"):
                with self.subTest(source=source_id):
                    code, report = self.capture(check_archives.main, ["--source", source_id, "--live"])
                    self.assertEqual(code, 2)
                    self.assertFalse(report["results"][0]["request_sent"])
            network.assert_not_called()

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
