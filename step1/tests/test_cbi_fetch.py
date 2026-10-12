"""Offline regression tests for the bounded CBI archive metadata refresh."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import fetch_cbi_archives as api


FAKE_KEY = "synthetic-cbi-test-credential-only"
OLD = "2026-10-09T00:00:00Z"
NEW = "2026-10-12T00:00:00Z"


def record(identity="loc:demo", title="CBI map", retrieved_at=OLD):
    source = "Europeana" if identity.startswith("europeana:") else "LoC"
    return {"id": identity, "source": source, "title": title,
            "retrieved_at": retrieved_at, "query_used": "Burma",
            "source_url": "https://www.loc.gov/item/" + identity.split(":", 1)[1] + "/"}


def snapshot(records):
    return {"records": records, "returned_count": len(records),
            "total_results": 9, "fetched_at": NEW}


class CbiFetchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "report.json"
        # Tests fail closed if a mock is accidentally omitted.
        self.addCleanup(patch.stopall)
        patch.object(api.public, "fetch_bytes", side_effect=AssertionError("Unexpected network request")).start()
        patch.object(api.europeana, "fetch_metadata", side_effect=AssertionError("Unexpected Europeana request")).start()
        patch.object(api.time, "sleep").start()

    def run_main(self, arguments):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["fetch_cbi_archives.py"] + arguments), redirect_stdout(output), redirect_stderr(errors):
            code = api.main()
        return code, output.getvalue(), errors.getvalue()

    def seed_fixture(self, base, previous):
        data = self.root / "data"
        data.mkdir(exist_ok=True)
        (data / "review-notes.json").write_text('{"excluded": []}', encoding="utf-8")
        source = {"id": "LoC", "file": "loc.json", "prefix": "loc:"}
        (data / source["file"]).write_text(json.dumps({"source": "LoC", "records": base, "fetched_at": OLD, "effective_query": "Burma"}), encoding="utf-8")
        self.output.write_text(json.dumps({"records": previous}), encoding="utf-8")
        with patch.object(api, "PROJECT_ROOT", self.root), patch.object(api, "SOURCE_CONFIG", {"LoC": source}):
            return api.seed_records(self.output)

    def test_newer_previous_overlap_keeps_latest_metadata_and_date(self):
        records, queries, _ = self.seed_fixture(
            [record(title="Old metadata")],
            [record(title="Refreshed metadata", retrieved_at="2026-10-11T20:00:00-04:00")],
        )
        self.assertEqual(records["loc:demo"]["title"], "Refreshed metadata")
        self.assertEqual(records["loc:demo"]["retrieved_at"], "2026-10-11T20:00:00-04:00")
        retained = [q for q in queries if q["status"] == "retained_previous_candidate"]
        self.assertEqual(retained[0]["record_ids"], ["loc:demo"])
        self.assertEqual(retained[0]["retrieved_at"], records["loc:demo"]["retrieved_at"])

    def test_older_invalid_or_naive_previous_date_cannot_replace_known_newer_snapshot(self):
        for stamp in (OLD, "invalid", None, "2027-01-01T00:00:00"):
            with self.subTest(stamp=stamp):
                records, queries, _ = self.seed_fixture(
                    [record(title="Latest seed", retrieved_at=NEW)],
                    [record(title="Stale previous output", retrieved_at=stamp)],
                )
                self.assertEqual(records["loc:demo"]["title"], "Latest seed")
                self.assertFalse(any(q["status"] == "retained_previous_candidate" for q in queries))

    def test_known_previous_date_wins_when_seed_date_is_absent(self):
        records, _, _ = self.seed_fixture([record(retrieved_at=None)], [record(title="Known date", retrieved_at=NEW)])
        self.assertEqual(records["loc:demo"]["title"], "Known date")

    def test_previous_unique_record_is_retained_without_inventing_a_date(self):
        records, queries, _ = self.seed_fixture([], [record(retrieved_at=None)])
        self.assertIsNone(records["loc:demo"]["retrieved_at"])
        self.assertIsNone(queries[-1]["retrieved_at"])

    def test_identical_loc_titles_do_not_share_format_enrichment(self):
        payload = {"pagination": {"of": 2}, "results": [
            {"url": "http://www.loc.gov/item/text/?fo=json", "title": "China and Burma", "original_format": ["book"]},
            {"url": "https://www.loc.gov/item/other/", "title": "China and Burma", "original_format": ["web archive"]},
        ]}
        with patch.object(api.public, "fetch_bytes", return_value=json.dumps(payload).encode()):
            result = api.fetch("LoC", "Burma", "https://www.loc.gov/search/", 3, None)
        formats = {r["id"]: r["format"] for r in result["records"]}
        self.assertEqual(formats, {"loc:text": "TEXT", "loc:other": None})

    def test_dry_run_does_not_load_credentials_read_snapshots_or_write(self):
        with patch.object(api, "seed_records", side_effect=AssertionError("Unexpected file read")), patch.object(api.europeana, "load_key", side_effect=AssertionError("Unexpected credential read")):
            code, output, _ = self.run_main(["--output", str(self.output)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["mode"], "dry_run")
        self.assertFalse(self.output.exists())

    def test_refresh_plan_only_requests_supported_api_sources(self):
        self.assertEqual({entry[0] for entry in api.PLAN}, {"LoC", "Europeana"})
        self.assertEqual(set(api.SOURCE_CONFIG), {"LoC", "Europeana", "NARA", "Taiwan NAA"})
        with self.assertRaises(api.public.FetchError):
            api.fetch("unsupported", "Burma", "https://example.org/api", 1, None)
        api.public.fetch_bytes.assert_not_called()

    def test_rate_limit_stops_that_platform_but_allows_next_platform(self):
        plan = (("LoC", "q1", "https://www.loc.gov/search/"), ("LoC", "q2", "https://www.loc.gov/search/"), ("Europeana", "q3", api.europeana.ENDPOINT))
        replies = [api.public.FetchError("Upstream HTTP 429; no automatic retry."), snapshot([record("europeana:book")])]
        with patch.object(api, "PLAN", plan), patch.object(api, "seed_records", return_value=({}, [], set())), patch.object(api, "fetch", side_effect=replies) as fetch, patch.object(api.europeana, "load_key", return_value=FAKE_KEY):
            code, _, _ = self.run_main(["--live", "--sources", "LoC", "Europeana", "--output", str(self.output)])
        result = json.loads(self.output.read_text())
        self.assertEqual(code, 1)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual([q["status"] for q in result["queries"]], ["error", "skipped_rate_limit", "ok"])
        self.assertEqual(result["records"][0]["id"], "europeana:book")

    def test_missing_credential_sends_no_request_and_records_reason(self):
        with patch.object(api, "PLAN", (("Europeana", "Burma", api.europeana.ENDPOINT),)), patch.object(api, "seed_records", return_value=({}, [], set())), patch.object(api.europeana, "load_key", side_effect=api.europeana.FetchError("Missing credential; no request sent.")):
            code, _, _ = self.run_main(["--live", "--sources", "Europeana", "--output", str(self.output)])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(self.output.read_text())["queries"][0]["status"], "missing_credential")

    def test_credential_echo_in_metadata_preserves_existing_file_and_stays_out_of_logs(self):
        self.output.write_text("previous content", encoding="utf-8")
        with patch.object(api, "PLAN", ()), patch.object(api, "seed_records", return_value=({"loc:demo": record(title=FAKE_KEY)}, [], set())), patch.object(api.europeana, "load_key", return_value=FAKE_KEY):
            code, output, errors = self.run_main(["--live", "--sources", "Europeana", "--output", str(self.output)])
        self.assertEqual(code, 1)
        self.assertEqual(self.output.read_text(), "previous content")
        self.assertNotIn(FAKE_KEY, output + errors)

    def test_credential_url_parameters_are_removed_before_public_output(self):
        candidate = record()
        candidate["source_url"] += "?wskey=" + FAKE_KEY
        with patch.object(api, "PLAN", (("LoC", "Burma", "https://www.loc.gov/search/"),)), patch.object(api, "seed_records", return_value=({}, [], set())), patch.object(api, "fetch", return_value=snapshot([candidate])):
            code, output, errors = self.run_main(["--live", "--sources", "LoC", "--output", str(self.output)])
        saved = self.output.read_text()
        self.assertEqual(code, 0)
        self.assertNotIn(FAKE_KEY, saved + output + errors)
        self.assertEqual(json.loads(saved)["records"][0]["source_url"], "https://www.loc.gov/item/demo/")


if __name__ == "__main__":
    unittest.main()
