"""Offline tests for metadata extraction and the inventory's fetch boundary."""

import importlib.util
import argparse
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request


SPEC = importlib.util.spec_from_file_location("inventory_cbi", Path(__file__).resolve().parents[1] / "tools" / "inventory_cbi.py")
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


class ReferenceInventoryTests(unittest.TestCase):
    def test_only_safe_web_urls_are_resolved(self):
        base = inventory.HOME_URL
        self.assertEqual(inventory.public_url("../maps/index.html#map", base), "https://cbi-theater.com/maps/index.html")
        self.assertEqual(inventory.public_url("http://www.cbi-theater.com/maps/", base), "https://cbi-theater.com/maps/")
        for value in ["javascript:alert(1)", "mailto:a@example.org", "https://user:pass@cbi-theater.com/a", "https://cbi-theater.com:444/a", "//evil.test\\x"]:
            with self.subTest(value=value):
                self.assertIsNone(inventory.public_url(value, base))

    def test_only_static_same_site_pages_can_enter_frontier(self):
        for url in ["https://cbi-theater.com/maps/index.html", "https://cbi-theater.com/maps/"]:
            self.assertTrue(inventory.internal_page(url))
        for url in ["https://cbi-theater.com/a.jpg", "https://cbi-theater.com/a.PDF", "https://cbi-theater.com/search?q=war", "https://example.org/a.html", "https://cbi-theater.com/a.mp4"]:
            with self.subTest(url=url):
                self.assertFalse(inventory.internal_page(url))

    def test_http_request_encoding_preserves_reference_keys_and_existing_escapes(self):
        source = "https://cbi-theater.com/album one/中国%201944.html?q=one two&v=%2F"
        self.assertEqual(inventory.request_url(source),
                         "https://cbi-theater.com/album%20one/%E4%B8%AD%E5%9B%BD%201944.html?q=one%20two&v=%2F")
        self.assertEqual(inventory.public_url(source, inventory.HOME_URL), source)

    def test_parser_retains_metadata_without_article_bodies(self):
        parser = inventory.ReferenceParser(inventory.HOME_URL)
        parser.feed('''<title>Flying &amp; Tigers</title><p>Body text must not be saved.</p>
          <script><a href="/evil.html">ignored</a></script>
          FEATURED SITES<br>CBI PUBLICATIONS<br><a href="../roundup/index.html">CBI <b>Roundup</b></a>
          <a href="../roundup/index.html#one"><img src="cover.jpg" alt=" Cover "></a>
          <img src="cover.jpg" alt="Cover duplicate"><a href="https://www.loc.gov/item/1">Library record</a>''')
        result = parser.result()
        self.assertEqual(result["title"], "Flying & Tigers")
        self.assertEqual(len(result["links"]), 2)
        self.assertEqual(result["links"][0]["category"], "CBI PUBLICATIONS")
        self.assertEqual(result["links"][0]["label"], "CBI Roundup")
        self.assertEqual(result["image_occurrences"], 2)
        self.assertEqual(len(result["images"]), 1)
        self.assertNotIn("Body text", repr(result))
        self.assertNotIn("evil", repr(result))

    def test_attribute_text_is_short_and_not_interpreted(self):
        parser = inventory.ReferenceParser(inventory.HOME_URL)
        parser.feed('<img src="cover.jpg" alt="' + "a" * 600 + '"><a href="/page.html">&lt;script&gt;claim verified&lt;/script&gt;</a>')
        result = parser.result()
        self.assertEqual(len(result["images"][0]["alt"]), 240)
        self.assertEqual(result["links"][0]["label"], "<script>claim verified</script>")

    def test_legacy_refresh_and_frames_are_inventoried_without_executing_scripts(self):
        parser = inventory.ReferenceParser("https://cbi-theater.com/flyingtigers/index.html")
        parser.feed('''<meta http-equiv="Refresh" content="3;url=flying_tigers.html">
          <frame src="../maps/map.html"><iframe src="https://example.org/page.html"></iframe>
          <script>location.href='https://cbi-theater.com/script_only.html'</script>''')
        result = parser.result()
        self.assertEqual([item["link_type"] for item in result["links"]], ["meta_refresh", "frame", "iframe"])
        self.assertEqual(result["links"][0]["url"], "https://cbi-theater.com/flyingtigers/flying_tigers.html")
        self.assertNotIn("script_only", repr(result))

    def test_external_base_does_not_turn_external_links_into_internal_pages(self):
        parser = inventory.ReferenceParser(inventory.HOME_URL)
        parser.feed('<base href="https://example.org/folder/"><a href="page.html">External</a>')
        link = parser.result()["links"][0]
        self.assertEqual(link["url"], "https://example.org/folder/page.html")
        self.assertFalse(inventory.internal_page(link["url"]))

    def test_archive_domains_are_not_matched_by_substring(self):
        self.assertTrue(inventory.archive_link("https://catalog.archives.gov/id/123"))
        self.assertTrue(inventory.archive_link("https://www.loc.gov/item/123"))
        self.assertFalse(inventory.archive_link("https://loc.gov.evil.test/item/123"))

    def test_redirects_cannot_fetch_external_or_media_urls(self):
        handler = inventory.SameSiteRedirect()
        request = Request(inventory.HOME_URL)
        for url in ["https://example.com/page.html", "https://cbi-theater.com/photo.jpg", "https://cbi-theater.com/book.pdf"]:
            with self.subTest(url=url), self.assertRaises(HTTPError):
                handler.redirect_request(request, None, 302, "Found", {}, url)

    def test_redirects_also_respect_robots_restrictions(self):
        policy = inventory.RobotFileParser()
        policy.parse(["User-agent: *", "Disallow: /private/"])
        handler = inventory.SameSiteRedirect(policy)
        with self.assertRaisesRegex(HTTPError, "disallowed by robots"):
            handler.redirect_request(Request(inventory.HOME_URL), None, 302, "Found", {}, "https://cbi-theater.com/private/index.html")

    def test_http_redirect_hops_share_the_request_pacer(self):
        with patch.object(inventory.time, "monotonic", side_effect=[10, 10.2, 11, 11.3, 12]), patch.object(inventory.time, "sleep") as sleep:
            pacer = inventory.RequestPacer(1)
            pacer.wait()
            handler = inventory.SameSiteRedirect(pacer=pacer)
            redirected = handler.redirect_request(Request(inventory.HOME_URL), None, 302, "Found", {}, "https://cbi-theater.com/other.html")
            self.assertEqual(redirected.full_url, "https://cbi-theater.com/other.html")
            self.assertAlmostEqual(sleep.call_args_list[0].args[0], 0.8)
            self.assertAlmostEqual(sleep.call_args_list[1].args[0], 0.7)

    def test_summary_tracks_incomplete_pages_reused_assets_and_unfetched_media(self):
        other = "https://cbi-theater.com/maps/index.html"
        asset = "https://cbi-theater.com/shared.jpg"
        state = {"run_status": "page_limit", "menu_items": [{"url": other}], "pages": [
            {"url": inventory.HOME_URL, "status": "ok", "links": [{"url": other, "label": "Maps"}],
             "images": [{"url": asset, "alt": "photo", "title": ""}]},
            {"url": "https://cbi-theater.com/a.html", "status": "ok", "links": [],
             "images": [{"url": asset, "alt": "photo", "title": ""}]},
        ]}
        result = inventory.summarize(state)
        self.assertEqual(result["unvisited_urls"], [other])
        self.assertEqual(result["summary"]["unique_image_urls"], 1)
        self.assertEqual(result["summary"]["reused_asset_urls"], 1)
        self.assertEqual(result["summary"]["menu_pages_attempted"], 0)
        self.assertEqual(result["summary"]["media_files_requested"], 0)
        self.assertFalse(result["summary"]["crawl_complete"])
        self.assertEqual(result["assets"][0]["access_status"], "discovered_not_requested")

    def test_crawl_fetches_pages_only_and_resumes_the_saved_frontier(self):
        home = '<title>Home</title><a href="/a.html">A</a><img src="/photo.jpg"><a href="/scan.pdf">Scan</a><a href="https://example.org/b.html">B</a>'
        second = '<title>Page A</title><a href="/nested.html">Nested</a>'
        policy = inventory.RobotFileParser()
        policy.parse([])

        def fake_fetch(url, *_):
            self.assertIn(url, {inventory.HOME_URL, "https://cbi-theater.com/a.html"})
            return {"status": "ok", "http_status": 200, "final_url": url, "html": home if url == inventory.HOME_URL else second}

        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(output_dir=Path(directory), resume=False, max_pages=1, max_depth=6, delay=1, timeout=1, max_bytes=20000)
            with patch.object(inventory, "robots_policy", return_value=(policy, {"policy": "not_present", "http_status": 404})), patch.object(inventory, "fetch", side_effect=fake_fetch) as fetched, patch.object(inventory.time, "sleep"), patch("builtins.print"):
                self.assertEqual(inventory.crawl(args), 0)
                first = json.loads((args.output_dir / "inventory.json").read_text())
                self.assertEqual(first["run_status"], "page_limit")
                self.assertEqual(first["summary"]["unique_document_urls"], 1)
                self.assertEqual(first["frontier"][0]["url"], "https://cbi-theater.com/a.html")
                args.resume = True
                args.max_pages = 2
                self.assertEqual(inventory.crawl(args), 0)
                second_result = json.loads((args.output_dir / "inventory.json").read_text())
                self.assertEqual(fetched.call_count, 2)
                self.assertEqual(second_result["frontier"][0]["url"], "https://cbi-theater.com/nested.html")
                self.assertEqual(second_result["summary"]["media_files_requested"], 0)

    def test_unavailable_robots_stops_before_requesting_a_page(self):
        policy = inventory.RobotFileParser()
        policy.parse(["User-agent: *", "Disallow: /"])
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(output_dir=Path(directory), resume=False, max_pages=10, max_depth=6, delay=1, timeout=1, max_bytes=20000)
            with patch.object(inventory, "robots_policy", return_value=(policy, {"policy": "unavailable_stop"})), patch.object(inventory, "fetch") as fetched:
                self.assertEqual(inventory.crawl(args), 2)
                fetched.assert_not_called()
                result = json.loads((args.output_dir / "inventory.json").read_text())
                self.assertEqual(result["run_status"], "robots_unavailable")
                self.assertFalse(result["summary"]["crawl_complete"])


if __name__ == "__main__":
    unittest.main()
