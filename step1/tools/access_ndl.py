#!/usr/bin/env python3
"""Probe NDL Search OpenSearch for NDL-created bibliographic metadata."""

from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from archive_access import Source, run_cli
from fetch_public_metadata import OPENSEARCH, source_url


SOURCE = Source(
    id="ndl",
    name="National Diet Library Search",
    access_mode="api",
    endpoint="https://ndlsearch.ndl.go.jp/api/opensearch",
    portal_url="https://ndlsearch.ndl.go.jp/",
    default_query="ビルマ",
    notes="One request, restricted to iss-ndl-opac (NDL-created bibliographic metadata). No key is required for this subset. Full-text access is separate.",
    documentation_url="https://ndlsearch.ndl.go.jp/help/api/specifications",
)


def probe(query, rows, credential, request):
    url = SOURCE.endpoint + "?" + urlencode({"any": query, "dpid": "iss-ndl-opac", "cnt": rows})
    try:
        data = request(url).decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("Unexpected NDL response encoding.") from None
    if "<!DOCTYPE" in data.upper() or "<!ENTITY" in data.upper():
        raise ValueError("Unsupported NDL XML declaration.")
    try:
        root = ET.fromstring(data)
        channel = root.find("channel") if root.tag == "rss" else None
        if channel is None:
            raise ValueError("Unexpected NDL response structure.")
        raw_total = channel.findtext("{" + OPENSEARCH + "}totalResults")
        if not isinstance(raw_total, str) or not raw_total.strip().isascii() or not raw_total.strip().isdigit():
            raise ValueError("Unexpected NDL result count.")
        total = int(raw_total)
    except ET.ParseError:
        raise ValueError("Unexpected NDL XML structure.") from None
    items = channel.findall("item")
    if total < len(items):
        raise ValueError("Unexpected NDL result count.")
    for item in items:
        if not source_url(item.findtext("link"), {"ndlsearch.ndl.go.jp"}):
            raise ValueError("Unexpected NDL record structure.")
    return {"sample_count": min(len(items), rows), "total_results": total}


def main(argv=None):
    return run_cli(SOURCE, probe, argv)


if __name__ == "__main__":
    raise SystemExit(main())
