import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("fetch_nara_metadata", Path(__file__).resolve().parents[1] / "tools" / "fetch_nara_metadata.py")
nara = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(nara)
FETCHED = "2026-10-10T00:00:00Z"
MODIFIED = "2026-09-28T20:13:03Z"


def record():
    return {
        "naId": 123, "title": "Original file title", "levelOfDescription": "fileUnit",
        "ancestors": [{"naId": 559459, "recordGroupNumber": 493, "levelOfDescription": "recordGroup",
                       "title": "Records of U.S. Army Forces in the China-Burma-India Theaters of Operations",
                       "inclusiveStartDate": {"year": 1942}, "inclusiveEndDate": {"year": 1947}}],
        "accessRestriction": {"status": "Unrestricted"},
        "useRestriction": {"status": "Unrestricted"}, "generalRecordsTypes": ["Textual Records"],
    }


def encoded(*records):
    return ("\n".join(json.dumps({"record": item}) for item in records) + "\n").encode()


class NaraMetadataTests(unittest.TestCase):
    def test_invalid_jsonl_fails_closed(self):
        for data in [b"not json", b"\xff", b"", b"[]", b'{"record": null}', b'{"record": {}}']:
            with self.subTest(data=data), self.assertRaises(nara.FetchError):
                nara.normalize_jsonl(data, FETCHED, MODIFIED)

    def test_identifier_and_rg_ancestry_must_be_verified(self):
        for bad_id in [True, 0, -1, "12/../13", "https://example.org", "0123"]:
            item = record()
            item["naId"] = bad_id
            with self.subTest(identifier=bad_id), self.assertRaises(nara.FetchError):
                nara.normalize_record(item, FETCHED, MODIFIED)
        item = record()
        item["ancestors"][0]["recordGroupNumber"] = 338
        with self.assertRaises(nara.FetchError):
            nara.normalize_record(item, FETCHED, MODIFIED)

    def test_missing_dates_are_not_inherited_from_title_or_ancestor(self):
        item = record()
        item["title"] = "Messages: June 1943 to January 1944"
        result = nara.normalize_record(item, FETCHED, MODIFIED)
        self.assertIsNone(result["date_display"])
        self.assertEqual(result["year"], [])
        self.assertEqual(result["date_kind"], "not_supplied")
        self.assertEqual(result["level_of_description"], "fileUnit")
        self.assertEqual(result["archival_context"], [item["ancestors"][0]["title"]])
        self.assertEqual(result["archival_ancestors"][0]["title"], item["ancestors"][0]["title"])
        self.assertEqual(result["archival_ancestors"][0]["source_url"], "https://catalog.archives.gov/id/559459")

    def test_inclusive_dates_preserve_year_precision_and_meaning(self):
        item = record()
        item.update({"levelOfDescription": "series", "inclusiveStartDate": {"year": 1944, "logicalDate": "1944-01-01"},
                     "inclusiveEndDate": {"year": 1946, "logicalDate": "1946-12-31"}})
        result = nara.normalize_record(item, FETCHED, MODIFIED)
        self.assertEqual(result["date_display"], "1944 – 1946")
        self.assertEqual(result["year"], ["1944", "1946"])
        self.assertEqual(result["date_kind"], "archival_inclusive")
        self.assertEqual(result["level_of_description"], "series")

    def test_invalid_calendar_date_rejected(self):
        item = record()
        item["productionDates"] = [{"year": 1944, "month": 2, "day": 30}]
        with self.assertRaises(nara.FetchError):
            nara.normalize_record(item, FETCHED, MODIFIED)

    def test_online_requires_both_object_and_unrestricted_access(self):
        item = record()
        self.assertEqual(nara.normalize_record(item, FETCHED, MODIFIED)["access_status"], "unverified")
        item["digitalObjects"] = [{"objectUrl": "https://s3.amazonaws.com/NARAprodstorage/test.tif"}]
        self.assertEqual(nara.normalize_record(item, FETCHED, MODIFIED)["access_status"], "online")
        item["accessRestriction"] = {"status": "Restricted - Partly"}
        self.assertEqual(nara.normalize_record(item, FETCHED, MODIFIED)["access_status"], "unverified")
        item["accessRestriction"] = {"status": "Unrestricted"}
        item["digitalObjects"] = [{"objectUrl": "javascript:alert(1)"}]
        self.assertEqual(nara.normalize_record(item, FETCHED, MODIFIED)["access_status"], "unverified")

    def test_sample_prioritizes_direct_matches_and_does_not_claim_total(self):
        generic = record()
        direct = copy.deepcopy(generic)
        direct.update({"naId": 456, "title": "Register Regarding Chinese Replacements"})
        payload = nara.normalize_jsonl(encoded(generic, direct), FETCHED, MODIFIED, limit=1)
        self.assertEqual(payload["returned_count"], 1)
        self.assertEqual(payload["records"][0]["source_id"], "456")
        self.assertNotIn("total_results", payload)
        self.assertEqual(payload["shard_record_count"], 2)
        result = payload["records"][0]
        self.assertEqual(result["dataset_url"], nara.DATASET_URL)
        self.assertEqual(result["content_rights"], ["NARA use restriction: Unrestricted"])
        self.assertEqual(result["metadata_rights"], nara.DATASET_DOCUMENTATION)

    def test_last_modified_is_separate_from_record_date(self):
        self.assertEqual(nara.last_modified_iso("Mon, 28 Sep 2026 20:13:03 GMT"), MODIFIED)
        for value in [None, "bad date", "28 Sep 2026 20:13:03"]:
            with self.subTest(value=value), self.assertRaises(nara.FetchError):
                nara.last_modified_iso(value)

    def test_atomic_save_replaces_valid_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.json"
            path.write_text("old")
            payload = nara.normalize_jsonl(encoded(record()), FETCHED, MODIFIED)
            nara.atomic_save(path, payload)
            self.assertEqual(json.loads(path.read_text())["returned_count"], 1)
            self.assertEqual([item.name for item in Path(directory).iterdir()], ["sample.json"])

    def test_failed_normalization_leaves_previous_snapshot_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.json"
            path.write_text('{"previous": true}')
            with patch.object(nara, "fetch_bytes", return_value=(b"invalid", MODIFIED)):
                with self.assertRaises(nara.FetchError):
                    nara.refresh(path)
            self.assertEqual(path.read_text(), '{"previous": true}')

    def test_failed_atomic_write_leaves_previous_snapshot_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.json"
            path.write_text("previous")
            with patch.object(nara.json, "dump", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    nara.atomic_save(path, {"new": True})
            self.assertEqual(path.read_text(), "previous")
            self.assertEqual([item.name for item in Path(directory).iterdir()], ["sample.json"])

    def test_redirect_is_not_followed(self):
        self.assertIsNone(nara.NoRedirect().redirect_request(None, None, 302, None, None, "https://example.org"))


if __name__ == "__main__":
    unittest.main()
