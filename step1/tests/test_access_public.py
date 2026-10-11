"""Offline access checks for the three public sources; no credentials or network."""

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import access_loc as loc
import access_nara as nara
import access_ndl as ndl


def loc_payload(total=1, items=None):
    if items is None:
        items = [{"id": "https://www.loc.gov/item/123/", "title": "Synthetic metadata"}]
    return json.dumps({"results": items, "pagination": {"of": total}}).encode()


def ndl_payload(total="1", links=None):
    if links is None:
        links = ["https://ndlsearch.ndl.go.jp/books/R100000002-I000001"]
    items = "".join("<item><title>Synthetic metadata</title><link>" + link + "</link></item>" for link in links)
    return ('<rss xmlns:opensearch="http://a9.com/-/spec/opensearchrss/1.0/">'
            '<channel><opensearch:totalResults>' + total + '</opensearch:totalResults>'
            + items + '</channel></rss>').encode()


def nara_payload(count=1, record_group=493):
    return ("\n".join(json.dumps({"record": {
        "naId": index + 1, "title": "Synthetic China-Burma-India record", "levelOfDescription": "fileUnit",
        "ancestors": [{"naId": 559459, "recordGroupNumber": record_group,
                       "title": "Synthetic record group", "levelOfDescription": "recordGroup"}],
    }}) for index in range(count)) + "\n").encode()


class PublicSourceConfigurationTests(unittest.TestCase):
    def test_public_sources_need_no_credentials(self):
        for module in (loc, ndl, nara):
            with self.subTest(source=module.SOURCE.id):
                self.assertIsNone(module.SOURCE.credential_env)
                self.assertFalse(module.SOURCE.requires_permission)
                self.assertTrue(module.SOURCE.endpoint.startswith("https://"))


class LoCAccessTests(unittest.TestCase):
    def test_one_request_uses_encoded_query_and_small_row_limit(self):
        request = Mock(return_value=loc_payload(total=17))
        result = loc.probe("Burma Road & China", 3, None, request)
        self.assertEqual(result, {"sample_count": 1, "total_results": 17})
        request.assert_called_once()
        url = urlsplit(request.call_args.args[0])
        self.assertEqual(url.scheme + "://" + url.netloc + url.path, loc.SOURCE.endpoint)
        self.assertEqual(parse_qs(url.query), {"q": ["Burma Road & China"], "fo": ["json"], "c": ["3"]})

    def test_valid_empty_search_is_success(self):
        self.assertEqual(loc.probe("missing", 2, None, Mock(return_value=loc_payload(0, []))),
                         {"sample_count": 0, "total_results": 0})

    def test_catalog_url_with_canonical_item_id_is_a_valid_result(self):
        payload = loc_payload(1, [{"url": "//lccn.loc.gov/2004674327",
                                   "id": "http://www.loc.gov/item/2004674327/"}])
        request = Mock(return_value=payload)
        self.assertEqual(loc.probe("Flying Tigers", 3, None, request),
                         {"sample_count": 1, "total_results": 1})
        request.assert_called_once()

    def test_count_never_exceeds_requested_rows(self):
        items = [{"id": "https://www.loc.gov/item/" + str(i) + "/"} for i in range(4)]
        self.assertEqual(loc.probe("Burma", 2, None, Mock(return_value=loc_payload(9, items)))["sample_count"], 2)

    def test_malformed_structure_or_record_is_rejected(self):
        payloads = [b"not JSON", b"[]", b"{}", b'{"results": [], "pagination": []}',
                    loc_payload(True, []), loc_payload(-1, []), loc_payload(0),
                    loc_payload(1, [None]), loc_payload(1, [{"id": "https://example.org/item/1/"}])]
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                loc.probe("Burma", 1, None, Mock(return_value=payload))

    def test_optional_credential_is_never_sent_or_returned(self):
        request = Mock(return_value=loc_payload())
        result = loc.probe("Burma", 1, "synthetic-unused-secret", request)
        self.assertNotIn("synthetic-unused-secret", repr(request.call_args))
        self.assertNotIn("Synthetic metadata", json.dumps(result))


class NDLAccessTests(unittest.TestCase):
    def test_one_request_limits_provider_and_encodes_japanese(self):
        request = Mock(return_value=ndl_payload("12"))
        result = ndl.probe("ビルマ & 中国", 3, None, request)
        self.assertEqual(result, {"sample_count": 1, "total_results": 12})
        request.assert_called_once()
        url = urlsplit(request.call_args.args[0])
        self.assertEqual(url.scheme + "://" + url.netloc + url.path, ndl.SOURCE.endpoint)
        self.assertEqual(parse_qs(url.query), {"any": ["ビルマ & 中国"], "dpid": ["iss-ndl-opac"], "cnt": ["3"]})

    def test_valid_empty_search_is_success(self):
        self.assertEqual(ndl.probe("missing", 2, None, Mock(return_value=ndl_payload("0", []))),
                         {"sample_count": 0, "total_results": 0})

    def test_count_never_exceeds_requested_rows(self):
        payload = ndl_payload("5", ["https://ndlsearch.ndl.go.jp/books/" + str(i) for i in range(4)])
        self.assertEqual(ndl.probe("ビルマ", 2, None, Mock(return_value=payload))["sample_count"], 2)

    def test_malformed_xml_counts_and_records_are_rejected(self):
        payloads = [b"not XML", b"\xff", b"<html></html>", b"<rss></rss>", b"<rss><channel/></rss>",
                    ndl_payload("-1", []), ndl_payload("1.5", []), ndl_payload("true", []),
                    ndl_payload("0"), ndl_payload("1", ["https://example.org/record/1"])]
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                ndl.probe("ビルマ", 1, None, Mock(return_value=payload))

    def test_xml_entity_declarations_rejected(self):
        for declaration in (b'<!DOCTYPE rss>', b'<!ENTITY name "value">'):
            with self.subTest(declaration=declaration), self.assertRaises(ValueError):
                ndl.probe("ビルマ", 1, None, Mock(return_value=declaration + ndl_payload()))
        utf16 = ('<!DOCTYPE rss [<!ENTITY secret "expanded">]>' + ndl_payload().decode()).encode("utf-16")
        with self.assertRaises(ValueError):
            ndl.probe("ビルマ", 1, None, Mock(return_value=utf16))

    def test_optional_credential_is_never_sent_or_returned(self):
        request = Mock(return_value=ndl_payload())
        result = ndl.probe("ビルマ", 1, "synthetic-unused-secret", request)
        self.assertNotIn("synthetic-unused-secret", repr(request.call_args))
        self.assertNotIn("Synthetic metadata", json.dumps(result))


class NARAAccessTests(unittest.TestCase):
    def test_fixed_shard_request_returns_bounded_sample_without_total(self):
        request = Mock(return_value=nara_payload(4))
        result = nara.probe("ignored search text", 2, None, request)
        request.assert_called_once_with(nara.SOURCE.endpoint)
        self.assertEqual(result, {"sample_count": 2})
        self.assertEqual(nara.SOURCE.access_mode, "dataset")
        self.assertIn("not keyword search results", nara.SOURCE.notes)
        self.assertIn("rg_493/rg_493-1.jsonl", nara.SOURCE.endpoint)

    def test_actual_sample_may_be_smaller_than_limit(self):
        self.assertEqual(nara.probe("", 5, None, Mock(return_value=nara_payload())), {"sample_count": 1})

    def test_empty_or_malformed_fixed_shard_is_rejected(self):
        for payload in (b"", b"\n", b"not JSON", b"[]", b'{"record": {}}', nara_payload(1, 338)):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                nara.probe("", 1, None, Mock(return_value=payload))

    def test_duplicate_records_are_counted_once(self):
        payload = nara_payload() * 2
        self.assertEqual(nara.probe("", 5, None, Mock(return_value=payload)), {"sample_count": 1})

    def test_optional_credential_is_never_sent_or_returned(self):
        request = Mock(return_value=nara_payload())
        result = nara.probe("", 1, "synthetic-unused-secret", request)
        self.assertNotIn("synthetic-unused-secret", repr(request.call_args))
        self.assertNotIn("Synthetic China-Burma-India record", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
