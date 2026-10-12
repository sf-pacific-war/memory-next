"""Offline publishing-boundary and local HTTP isolation tests; no real keys."""

from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import unittest


TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import build_site_data as builder
import serve


def record(identity="loc:one", source="LoC", **extra):
    return {"id": identity, "source_id": identity.split(":", 1)[1], "source": source,
            "title": "Burma Road", "source_url": "https://www.loc.gov/item/" + identity.split(":", 1)[1] + "/", **extra}


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "data").mkdir()
        (self.root / "data/review-notes.json").write_text(json.dumps({"excluded": [{"id": "europeana:excluded"}]}))

    def tearDown(self):
        self.temp.cleanup()

    def snapshot(self, source, records):
        filename = next(s["file"] for s in builder.SOURCES if s["id"] == source)
        (self.root / "data" / filename).write_text(json.dumps({"source": source, "records": records, "fetched_at": "2026-10-09T00:00:00Z"}))

    def test_deduplicates_and_applies_review_without_altering_raw_data(self):
        self.snapshot("LoC", [record(), record(title="Duplicate")])
        self.snapshot("Europeana", [record("europeana:excluded", "Europeana"), record("europeana:keep", "Europeana")])
        before = {p.name: p.read_bytes() for p in (self.root / "data").glob("*.json")}
        catalog = builder.write_catalog(self.root)
        self.assertEqual([r["id"] for r in catalog["records"]], ["loc:one", "europeana:keep"])
        self.assertEqual(catalog["excluded_count"], 1)
        self.assertEqual(catalog["records"][0]["title"], "Burma Road")
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.root / "data").glob("*.json")})
        self.assertEqual(json.loads((self.root / "site/data/catalog.json").read_text()), catalog)

    def test_missing_and_invalid_sources_are_visible_as_unavailable(self):
        (self.root / "data/europeana-discovery-candidates.json").write_text("not json")
        catalog = builder.build_catalog(self.root)
        self.assertEqual([s["id"] for s in catalog["sources"]], ["LoC", "Europeana", "NARA", "Taiwan NAA"])
        self.assertTrue(all(s["status"] == "unavailable" and s["count"] == 0 for s in catalog["sources"]))

    def test_empty_successful_snapshot_is_available(self):
        self.snapshot("Europeana", [])
        source = builder.build_catalog(self.root)["sources"][1]
        self.assertEqual((source["status"], source["count"]), ("available", 0))

    def test_nara_retains_public_dataset_provenance_and_archival_context(self):
        self.snapshot("NARA", [record("nara:123", "NARA", source_url="https://catalog.archives.gov/id/123",
            dataset_url="https://nara-national-archives-catalog.s3.us-east-2.amazonaws.com/descriptions/record-groups/rg_493/rg_493-1.jsonl",
            dataset_updated_at="2026-09-28T20:13:00Z", level_of_description="series", record_group="493",
            archival_context=["Records of U.S. Army Forces in the China-Burma-India Theaters of Operations"])])
        catalog = builder.build_catalog(self.root)
        item = catalog["records"][0]
        self.assertEqual(item["source"], "NARA")
        self.assertEqual(item["record_group"], "493")
        self.assertEqual(item["level_of_description"], "series")
        self.assertEqual(item["dataset_updated_at"], "2026-09-28T20:13:00Z")
        self.assertTrue(item["dataset_url"].endswith("rg_493-1.jsonl"))
        self.assertIn("China-Burma-India", item["archival_context"][0])
        self.assertEqual(next(source for source in catalog["sources"] if source["id"] == "NARA")["count"], 1)

    def test_shared_taiwan_portal_does_not_merge_distinct_archival_cases(self):
        common = {"source_url": "https://aa.archives.gov.tw/", "aggregator_url": "https://data.gov.tw/dataset/95315",
                  "source_url_kind": "catalogue_search", "archival_id": "B/0031/001", "dataset_generated_at": "2026-10-01",
                  "date_display": None, "year": [], "level_of_description": "fileUnit"}
        self.snapshot("Taiwan NAA", [record("taiwan:a", "Taiwan NAA", **common),
            record("taiwan:b", "Taiwan NAA", **{**common, "archival_id": "B/0032/002"}),
            record("taiwan:a", "Taiwan NAA", **common)])
        output = builder.build_catalog(self.root)
        self.assertEqual([r["id"] for r in output["records"]], ["taiwan:a", "taiwan:b"])
        self.assertTrue(all(r["record_origin"] == "dataset" for r in output["records"]))
        self.assertEqual(output["records"][0]["archival_id"], "B/0031/001")
        self.assertEqual(output["records"][0]["dataset_generated_at"], "2026-10-01")
        self.assertIsNone(output["records"][0]["date_display"])
        self.assertEqual(output["records"][0]["year"], [])

    def test_selected_taiwan_reading_links_keep_original_case_provenance(self):
        self.snapshot("Taiwan NAA", [record("taiwan:a", "Taiwan NAA", source_url="https://aa.archives.gov.tw/", source_url_kind="catalogue_search"),
                                      record("taiwan:b", "Taiwan NAA", source_url="https://aa.archives.gov.tw/", source_url_kind="catalogue_search")])
        (self.root / "data/topics.json").write_text(json.dumps({"reading_links": {
            "taiwan:a": "https://art.archives.gov.tw/tw/art/1632-15619.html",
            "taiwan:b": "https://art.archives.gov.tw.example.org/not-an-archive"}}))
        a, b = builder.build_catalog(self.root)["records"]
        self.assertEqual(a["source_url"], "https://aa.archives.gov.tw/")
        self.assertTrue(a["reading_url"].endswith("1632-15619.html"))
        self.assertIsNone(a["date_display"])
        self.assertNotIn("reading_url", b)

    def test_output_allowlist_drops_raw_credentials_and_nested_values(self):
        self.snapshot("LoC", [record(api_key="synthetic-secret", raw={"secret": "synthetic-secret"},
                                         holding_institution=["LoC", {"secret": "synthetic-secret"}],
                                         source_url="https://www.loc.gov/item/one/?wskey=synthetic-secret&id=1")])
        catalog = builder.build_catalog(self.root)
        self.assertNotIn("synthetic-secret", json.dumps(catalog))
        self.assertEqual(catalog["records"][0]["holding_institution"], ["LoC"])
        self.assertEqual(catalog["records"][0]["source_url"], "https://www.loc.gov/item/one/?id=1")

    def test_source_mismatch_and_bad_ids_are_not_published(self):
        self.snapshot("LoC", [record("europeana:wrong"), record(source="Europeana"), {"id": 3}, record()])
        self.assertEqual(len(builder.build_catalog(self.root)["records"]), 1)

    def test_unknown_access_and_unsafe_url_are_conservative(self):
        self.snapshot("LoC", [record(access_status="free", source_url="http://127.0.0.1/private", thumbnail_url="javascript:alert(1)")])
        r = builder.build_catalog(self.root)["records"][0]
        self.assertEqual(r["access_status"], "unverified")
        self.assertIsNone(r["source_url"])
        self.assertIsNone(r["thumbnail_url"])

    def extra_records(self, records, queries=None):
        (self.root / "data/cbi").mkdir(exist_ok=True)
        (self.root / "data/cbi/archive-records.json").write_text(json.dumps({"records": records, "queries": queries or []}))

    def curated(self, records):
        (self.root / "data/cbi").mkdir(exist_ok=True)
        (self.root / "data/cbi/verified-matches.json").write_text(json.dumps({"records": records}))

    def manual_record(self, **extra):
        return {"id": "cbi-match-internal", "source": "NARA", "archival_url": "https://catalog.archives.gov/id/535531",
                "archival_title": "P-40 fighter aircraft", "material_type": "photograph",
                "checked_at": "2026-10-12T00:25:50Z", "access_note": "Official gallery accessible.",
                "rights_note": "Public domain gallery selection.",
                "cbi_page_url": "https://cbi-theater.com/flyingtigers/index.html",
                "evidence": "Internal comparison evidence must remain private.",
                "next_step": "Internal work note must remain private.", **extra}

    def test_combines_snapshots_and_curated_native_ids_without_changing_retrieval_date(self):
        self.snapshot("LoC", [record(retrieved_at="2026-10-01T00:00:00Z")])
        self.extra_records([record(title="Newer duplicate", retrieved_at="2026-10-12T00:00:00Z"), record("loc:two")])
        self.curated([self.manual_record(), self.manual_record(id="another-internal-id", archival_url="http://catalog.archives.gov/id/535531/?utm_source=test")])
        output = builder.build_catalog(self.root)
        self.assertEqual([r["id"] for r in output["records"]], ["loc:one", "loc:two", "nara:535531"])
        self.assertEqual(output["records"][0]["retrieved_at"], "2026-10-01T00:00:00Z")
        curated = output["records"][-1]
        self.assertIsNone(curated["retrieved_at"])
        self.assertIsNone(curated["date_display"])
        self.assertIsNone(curated["description"])
        self.assertEqual(curated["checked_at"], "2026-10-12T00:25:50Z")
        self.assertEqual(curated["record_origin"], "curated")
        serialized = json.dumps(output)
        for private in ("cbi-theater.com", "cbi-match-internal", "evidence", "next_step", "Internal work note"):
            self.assertNotIn(private, serialized)

    def test_exclusion_propagates_to_canonical_duplicates_in_all_inputs(self):
        self.snapshot("LoC", [record(), record("loc:separate")])
        self.extra_records([record("loc:alias", source_url="http://loc.gov/item/one/?utm_medium=link")])
        (self.root / "data/review-notes.json").write_text(json.dumps({"excluded": [{"id": "loc:alias"}]}))
        self.assertEqual([r["id"] for r in builder.build_catalog(self.root)["records"]], ["loc:separate"])

    def test_internal_manual_exclusion_suppresses_existing_api_record(self):
        self.snapshot("NARA", [record("nara:535531", "NARA", source_url="https://catalog.archives.gov/id/535531")])
        self.curated([self.manual_record()])
        (self.root / "data/review-notes.json").write_text(json.dumps({"excluded": [{"id": "cbi-match-internal"}]}))
        self.assertEqual(builder.build_catalog(self.root)["records"], [])

    def test_query_exclusions_apply_to_base_and_extra_snapshots(self):
        self.snapshot("LoC", [record()])
        self.extra_records([record()], [{"excluded_records": [{"id": "loc:one"}]}])
        self.assertEqual(builder.build_catalog(self.root)["records"], [])

    def test_curated_metadata_cannot_substitute_reference_site_or_unverified_preview(self):
        self.curated([self.manual_record(archival_url="https://cbi-theater.com/id/535531"),
                      self.manual_record(thumbnail_url="https://www.archives.gov/image.jpg", thumbnail_verified_http_status=403)])
        records = builder.build_catalog(self.root)["records"]
        self.assertEqual(len(records), 1)
        self.assertIsNone(records[0]["thumbnail_url"])
        self.assertEqual(records[0]["access_status"], "unverified")
        self.snapshot("LoC", [record(thumbnail_url="https://cbi-theater.com/photo.jpg")])
        self.assertIsNone(builder.build_catalog(self.root)["records"][0]["thumbnail_url"])
        self.assertIsNone(builder.archival_thumbnail("https://loc.gov.example.org/photo.jpg"))
        self.assertIsNone(builder.archival_thumbnail("http://tile.loc.gov/photo.jpg"))
        self.assertEqual(builder.archival_thumbnail("https://tile.loc.gov/photo.jpg"), "https://tile.loc.gov/photo.jpg")

    def test_topics_use_published_ids_only_and_do_not_overwrite_archive_description(self):
        self.snapshot("LoC", [record(description="Original archive description.")])
        self.curated([self.manual_record()])
        (self.root / "data/topics.json").write_text(json.dumps({
            "curator_notes": {"nara:535531": {"en": "Editorial note.", "zh-CN": "策展说明。"}},
            "topics": [{"id": "flying-tigers", "title": {"en": "Flying Tigers", "zh-CN": "飞虎队"},
                        "description": {"en": "Selected material.", "zh-CN": "精选资料。"},
                        "keywords": {"en": ["P-40"], "zh-CN": ["飛虎隊"]},
                        "record_ids": ["loc:one", "nara:535531", "unknown:excluded"]}]}))
        result = builder.build_catalog(self.root)
        self.assertEqual(result["topics"][0]["record_ids"], ["loc:one", "nara:535531"])
        self.assertEqual(result["records"][0]["description"], "Original archive description.")
        self.assertIsNone(result["records"][1]["description"])
        self.assertEqual(result["records"][1]["curator_note"]["en"], "Editorial note.")
        self.assertIn("飞虎队", result["records"][1]["topic_keywords"])
        self.assertIn("P-40", result["records"][1]["topic_keywords"])

    def test_source_summaries_distinguish_curated_from_api_with_separate_check_dates(self):
        self.snapshot("NARA", [record("nara:123", "NARA", source_url="https://catalog.archives.gov/id/123", retrieved_at="2026-10-09T00:00:00Z")])
        self.curated([self.manual_record(), self.manual_record(source="Internet Archive", archival_url="https://archive.org/details/Guide1943")])
        sources = {r["id"]: r for r in builder.build_catalog(self.root)["sources"]}
        self.assertEqual(sources["NARA"]["counts_by_origin"], {"dataset": 1, "curated": 1})
        self.assertEqual(sources["NARA"]["fetched_at"], "2026-10-09T00:00:00Z")
        self.assertEqual(sources["NARA"]["checked_at"], "2026-10-12T00:25:50Z")
        self.assertEqual(sources["Internet Archive"]["access_modes"], ["curated"])
        self.assertIsNone(sources["Internet Archive"]["fetched_at"])
        self.assertEqual(sources["Internet Archive"]["label"], "互联网档案馆")

    def test_missing_review_notes_blocks_publish(self):
        (self.root / "data/review-notes.json").unlink()
        with self.assertRaises(builder.BuildError):
            builder.write_catalog(self.root)

    def test_site_symlink_cannot_redirect_generated_catalogue(self):
        (self.root / "outside").mkdir()
        (self.root / "site").symlink_to(self.root / "outside", target_is_directory=True)
        with self.assertRaises(builder.BuildError):
            builder.write_catalog(self.root)
        self.assertEqual(list((self.root / "outside").iterdir()), [])


class PublishedTopicCorpusTests(unittest.TestCase):
    """Check actual editorial memberships and provenance, without networking."""

    def test_public_corpus_contains_all_topics_and_no_reference_site_evidence(self):
        catalog = builder.build_catalog()
        self.assertEqual(len(catalog["records"]), 55)
        self.assertEqual(len(catalog["topics"]), 10)
        self.assertEqual(len(catalog["sources"]), 10)
        self.assertEqual(sum(s["count"] for s in catalog["sources"]), len(catalog["records"]))
        indexed = {r["id"]: r for r in catalog["records"]}
        self.assertEqual(len(indexed), len(catalog["records"]))
        self.assertTrue(all(r["topic_ids"] for r in catalog["records"]))
        for topic in catalog["topics"]:
            self.assertTrue(all(identity in indexed for identity in topic["record_ids"]))
        self.assertEqual(indexed["loc:afc2001001.82964"]["record_origin"], "api")
        self.assertIsNone(indexed["iwm:2992"]["retrieved_at"])
        self.assertEqual(indexed["iwm:2992"]["access_status"], "unverified")
        self.assertIn("currently unavailable", indexed["iwm:2992"]["curator_note"]["en"])
        self.assertNotIn("cbi-theater.com", json.dumps(catalog))
        for record in catalog["records"]:
            self.assertNotIn("cbi_page_url", record)
            self.assertNotIn("match_status", record)
            self.assertNotIn("next_step", record)
            self.assertNotIn("evidence", record)
            if record["record_origin"] == "curated":
                self.assertEqual(set(record["curator_note"]), {"en", "zh-CN"})
                self.assertIsNone(record["description"])


class ServerIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.site = cls.root / "site"
        cls.site.mkdir()
        (cls.site / "index.html").write_text("<h1>Public demo</h1>")
        (cls.site / "data").mkdir()
        (cls.site / "data/catalog.json").write_text('{"records":[]}')
        (cls.root / ".env.europeana").write_text("SYNTHETIC_SECRET_OUTSIDE_SITE")
        (cls.site / ".hidden").write_text("SYNTHETIC_HIDDEN_INSIDE_SITE")
        (cls.site / "leak.txt").symlink_to(cls.root / ".env.europeana")
        (cls.site / "escape").symlink_to(cls.root, target_is_directory=True)
        (cls.site / "bad-index").mkdir()
        (cls.site / "bad-index/index.html").symlink_to(cls.root / ".env.europeana")
        handler = serve.make_handler(cls.site)
        # Suppress expected 403 access logs for these synthetic security probes.
        handler.func.log_message = lambda self, *args: None
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temp.cleanup()

    def request(self, path, method="GET"):
        client = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            client.request(method, path)
            response = client.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            client.close()

    def test_public_index_and_catalogue_are_available(self):
        self.assertEqual(self.request("/")[0], 200)
        status, body, headers = self.request("/data/catalog.json")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"records": []})
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_credentials_dotfiles_traversal_and_symlinks_are_denied(self):
        paths = ["/.env.europeana", "/../.env.europeana", "/%2e%2e/.env.europeana",
                 "/%252e%252e/%252eenv.europeana", "/data/../../.env.europeana",
                 "/.hidden", "/%2ehidden", "/leak.txt", "/escape/.env.europeana",
                 "/bad-index/", "/data%5c..%5c.env.europeana"]
        for path in paths:
            with self.subTest(path=path):
                status, body, _ = self.request(path)
                self.assertEqual(status, 403)
                self.assertNotIn(b"SYNTHETIC_", body)

    def test_directory_listing_and_head_of_secret_are_denied(self):
        self.assertEqual(self.request("/data/")[0], 403)
        self.assertEqual(self.request("/leak.txt", "HEAD")[0], 403)


if __name__ == "__main__":
    unittest.main()
