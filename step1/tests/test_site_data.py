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
            "title": "Burma Road", "source_url": "https://www.loc.gov/item/one/", **extra}


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
        (self.root / "data/ndl-discovery.json").write_text("not json")
        catalog = builder.build_catalog(self.root)
        self.assertEqual([s["id"] for s in catalog["sources"]], ["LoC", "NDL", "Europeana", "NARA"])
        self.assertTrue(all(s["status"] == "unavailable" and s["count"] == 0 for s in catalog["sources"]))

    def test_empty_successful_snapshot_is_available(self):
        self.snapshot("NDL", [])
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
        self.assertEqual(catalog["sources"][-1]["count"], 1)

    def test_output_allowlist_drops_raw_credentials_and_nested_values(self):
        self.snapshot("LoC", [record(api_key="synthetic-secret", raw={"secret": "synthetic-secret"},
                                         holding_institution=["LoC", {"secret": "synthetic-secret"}],
                                         source_url="https://www.loc.gov/item/one/?wskey=synthetic-secret&id=1")])
        catalog = builder.build_catalog(self.root)
        self.assertNotIn("synthetic-secret", json.dumps(catalog))
        self.assertEqual(catalog["records"][0]["holding_institution"], ["LoC"])
        self.assertEqual(catalog["records"][0]["source_url"], "https://www.loc.gov/item/one/?id=1")

    def test_source_mismatch_and_bad_ids_are_not_published(self):
        self.snapshot("LoC", [record("ndl:wrong"), record(source="NDL"), {"id": 3}, record()])
        self.assertEqual(len(builder.build_catalog(self.root)["records"]), 1)

    def test_unknown_access_and_unsafe_url_are_conservative(self):
        self.snapshot("LoC", [record(access_status="free", source_url="http://127.0.0.1/private", thumbnail_url="javascript:alert(1)")])
        r = builder.build_catalog(self.root)["records"][0]
        self.assertEqual(r["access_status"], "unverified")
        self.assertIsNone(r["source_url"])
        self.assertIsNone(r["thumbnail_url"])

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
