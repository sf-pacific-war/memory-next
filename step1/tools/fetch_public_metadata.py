#!/usr/bin/env python3
"""Fetch small, credential-free LoC and NDL metadata snapshots for the demo.

Only metadata is requested. No image/full-text download, pagination, retries,
redirects, credentials, or environment-file loading. A failed source leaves its
previous snapshot intact. Each source makes one request, with a 30-second socket
timeout and an 8 MiB response cap. Run refreshes serially and at least five
seconds apart; do not schedule bulk harvesting with this demonstration tool.

References:
  https://www.loc.gov/apis/json-and-yaml/requests/
  https://ndlsearch.ndl.go.jp/help/api/specifications
  https://ndlsearch.ndl.go.jp/help/api/provider
"""

import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import socket
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
DC = "http://purl.org/dc/elements/1.1/"
DCTERMS = "http://purl.org/dc/terms/"
OPENSEARCH = "http://a9.com/-/spec/opensearchrss/1.0/"
NDL_METADATA_RIGHTS = "https://creativecommons.org/licenses/by/4.0/"


class FetchError(Exception):
    """An upstream failure with a short, safe user-facing message."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value):
    parser = PlainText()
    parser.feed(value or "")
    return " ".join(" ".join(parser.parts).split())


def strings(value):
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(v.strip() for v in value if isinstance(v, str) and v.strip()))


def source_url(value, allowed_hosts):
    if not isinstance(value, str) or any(c.isspace() for c in value) or "\\" in value:
        return None
    try:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or parts.hostname not in allowed_hosts:
            return None
        if parts.username or parts.password or parts.port not in {None, 80, 443}:
            return None
        return urlunsplit(("https", parts.hostname, parts.path, "", ""))
    except ValueError:
        return None


def years(value):
    return list(dict.fromkeys(re.findall(r"\b(?:1[5-9]\d{2}|20\d{2})\b", value or "")))


def normalize_loc(item, query, fetched_at):
    detail = item.get("item") or {}
    if not isinstance(detail, dict):
        detail = {}
    link = source_url(item.get("url") or item.get("id"), {"www.loc.gov", "loc.gov"})
    if not link:
        raise FetchError("LoC returned an invalid record link.")
    # Keep the catalogue's date wording, including ranges and uncertainty.
    date = "; ".join(strings(detail.get("created_published"))) or item.get("date") or None
    description = strings(item.get("description"))
    if not description:
        description = strings(detail.get("notes"))
    original = strings(item.get("original_format"))
    if len(original) > 1:
        material = "MIXED"
    elif any("map" in value for value in original):
        material = "MAP"
    elif any("photo" in value for value in original):
        material = "IMAGE"
    elif any("audio" in value for value in original):
        material = "SOUND"
    else:
        material = None
    rights = strings(detail.get("rights")) + strings(detail.get("rights_advisory"))
    thumbnails = [source_url(value, {"tile.loc.gov"}) for value in strings(item.get("image_url"))]
    record_id = urlsplit(link).path.rstrip("/").split("/")[-1]
    record = {
        "id": "loc:" + record_id,
        "source_id": record_id,
        "source": "LoC",
        "title": item.get("title") or None,
        "description": "\n".join(description) or None,
        "holding_institution": strings(detail.get("repository")) or ["Library of Congress"],
        "metadata_provider": ["Library of Congress"],
        "date_display": date,
        "date_kind": "source_supplied",
        "year": years(date) or years(item.get("date")),
        "format": material,
        "language": strings(detail.get("language")) or strings(item.get("language")),
        "source_url": link,
        "aggregator_url": link,
        "access_status": "online" if item.get("digitized") is True and item.get("access_restricted") is False else "unverified",
        "review_status": "candidate",
        "metadata_rights": None,
        "content_rights": list(dict.fromkeys(rights)),
        "retrieved_at": fetched_at,
        "query_used": query,
        "subjects": strings(item.get("subject")),
    }
    thumbnail = next((value for value in thumbnails if value), None)
    if thumbnail:
        record["thumbnail_url"] = thumbnail
    return record


def normalize_loc_response(payload, query, fetched_at):
    items = payload.get("results") if isinstance(payload, dict) else None
    total = payload.get("pagination", {}).get("of") if isinstance(payload, dict) else None
    if not isinstance(items, list) or type(total) is not int:
        raise FetchError("LoC returned an unexpected response structure.")
    # These are known geographic/title collisions, not China/Burma materials.
    exclusions = ("conkey joe", "santa rosa island", "oakland army base")
    records = [normalize_loc(item, query, fetched_at) for item in items
               if isinstance(item, dict) and not any(term in str(item.get("title", "")).lower() for term in exclusions)]
    return snapshot("LoC", query, fetched_at, total, records,
                    "First API page; excludes known title collisions for Bahamian song cards and California roads. Other records remain candidates.")


def normalize_ndl(item, query, fetched_at):
    link = source_url(item.findtext("link"), {"ndlsearch.ndl.go.jp"})
    if not link:
        raise FetchError("NDL returned an invalid record link.")
    record_id = urlsplit(link).path.rstrip("/").split("/")[-1]
    # RSS pubDate is an index-update timestamp, NOT the publication date.
    date = item.findtext("{" + DCTERMS + "}issued") or item.findtext("{" + DC + "}date")
    categories = [node.text for node in item.findall("category") if node.text]
    return {
        "id": "ndl:" + record_id,
        "source_id": record_id,
        "source": "NDL",
        "title": item.findtext("title") or None,
        "description": plain_text(item.findtext("description")) or None,
        "holding_institution": ["国立国会図書館"],
        "metadata_provider": ["NDL Search API — 国立国会図書館作成書誌 (iss-ndl-opac)"],
        "date_display": date or None,
        "date_kind": "source_supplied",
        "year": years(date),
        "format": "TEXT" if "図書" in categories else None,
        "language": [node.text.strip() for node in item.findall("{" + DC + "}language") if node.text and node.text.strip()],
        "metadata_language": ["ja"],
        "source_url": link,
        "aggregator_url": link,
        "access_status": "unverified",
        "review_status": "candidate",
        "metadata_rights": NDL_METADATA_RIGHTS,
        "content_rights": [],
        "retrieved_at": fetched_at,
        "query_used": query,
        "subjects": [node.text.strip() for node in item.findall("{" + DC + "}subject") if node.text and node.text.strip()],
    }


def normalize_ndl_response(data, query, fetched_at):
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise FetchError("NDL response contains unsupported XML declarations.")
    try:
        root = ET.fromstring(data)
        total = int(root.findtext("./channel/{" + OPENSEARCH + "}totalResults"))
        if total < 0:
            raise ValueError
    except (ET.ParseError, TypeError, ValueError):
        raise FetchError("NDL returned an unexpected response structure.") from None
    records = [normalize_ndl(item, query, fetched_at) for item in root.findall("./channel/item")]
    if query == "ビルマ":
        terms = ("ビルマ", "ミャンマー", "インパール", "滇緬", "太平洋戦争", "日中戦争")
        records = [record for record in records if any(term in " ".join([
            record["title"] or "", record["description"] or "", " ".join(record["subjects"])
        ]) for term in terms)]
    return snapshot("NDL", query, fetched_at, total, records,
                    "NDL bibliographic metadata under CC BY 4.0; publication dates are not battle dates. Default Burma query excludes records without Burma/China/Pacific-war terms in visible metadata. Catalogue links do not establish public full-text access.")


def snapshot(source, query, fetched_at, total, records, note):
    unique = list({record["id"]: record for record in records}.values())
    return {"source": source, "effective_query": query, "fetched_at": fetched_at,
            "total_results": total, "returned_count": len(unique),
            "selection_note": note, "records": unique}


def fetch_bytes(url):
    request = Request(url, headers={"User-Agent": "PacificWarDiscoveryDemo/0.1 (small metadata pilot)"})
    try:
        with build_opener(NoRedirect).open(request, timeout=TIMEOUT_SECONDS) as response:
            data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise FetchError("Upstream response exceeded the size limit.")
        return data
    except HTTPError as exc:
        raise FetchError("Upstream HTTP " + str(exc.code) + "; no automatic retry.") from None
    except (URLError, TimeoutError, socket.timeout, OSError):
        raise FetchError("Upstream connection failed or timed out; no automatic retry.") from None


def atomic_save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name + ".", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["all", "loc", "ndl"], default="all")
    parser.add_argument("--rows", type=int, help="1–20 records per source (defaults: LoC 20, NDL 10).")
    parser.add_argument("--query", help="Optional query for one selected source; cannot be used with all.")
    args = parser.parse_args()
    if args.rows is not None and not 1 <= args.rows <= 20:
        parser.error("--rows must be between 1 and 20")
    if args.query and (args.source == "all" or not args.query.strip() or len(args.query) > 200):
        parser.error("--query needs one source and a nonempty value of at most 200 characters")
    failed = False
    for source in (["loc", "ndl"] if args.source == "all" else [args.source]):
        query = args.query or ('"Burma Road"' if source == "loc" else "ビルマ")
        count = args.rows or (20 if source == "loc" else 10)
        if source == "loc":
            url = "https://www.loc.gov/photos/?" + urlencode({"q": query, "fo": "json", "c": count})
        else:
            url = "https://ndlsearch.ndl.go.jp/api/opensearch?" + urlencode({"any": query, "dpid": "iss-ndl-opac", "cnt": count})
        try:
            data = fetch_bytes(url)
            fetched_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            if source == "loc":
                payload = normalize_loc_response(json.loads(data), query, fetched_at)
            else:
                payload = normalize_ndl_response(data, query, fetched_at)
            atomic_save(PROJECT_ROOT / "data" / (source + "-discovery.json"), payload)
            print(source.upper() + " metadata saved: " + str(payload["returned_count"]) + " candidate records.")
        except (FetchError, json.JSONDecodeError, UnicodeError, OSError) as exc:
            message = str(exc) if isinstance(exc, FetchError) else "Could not parse or save source metadata."
            print(source.upper() + ": " + message + " Previous snapshot retained.")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
