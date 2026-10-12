#!/usr/bin/env python3
"""Search Taiwan NAA's official case-title CSV, with bounded I/O and no credentials.

One --live request downloads a bounded CSV prefix; matching happens locally,
not through an A+ search API. --input reuses a local CSV without networking.
A partial scan reports observed matches only, never a whole-dataset total.
"""

import codecs
import csv
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, build_opener

from archive_access import NoRedirect, SafeArgumentParser, TIMEOUT_SECONDS
from fetch_public_metadata import atomic_save


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = "Taiwan NAA"
INSTITUTION = "National Archives Administration, National Development Council (Taiwan)"
CSV_URL = "https://www.archives.gov.tw/opendata/" + quote("國家檔案案名清單.csv")
CATALOGUE_URL = "https://aa.archives.gov.tw/"
LICENSE_URL = "https://data.gov.tw/license"
COLUMNS = ("序號", "全宗名", "檔號", "案名", "資料產製日期")
DEFAULT_MAX_BYTES = 4 * 1024 * 1024
MAX_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_SCAN_ROWS = 200000
MAX_SCAN_ROWS = 1000000
MAX_SECONDS = 120
DEFAULT_QUERY = "駐印軍"

# Deliberately small, explicit equivalents. These are query aids, not translations
# of archival titles or claims that every phrase occurs in the source dataset.
QUERY_ALIASES = (
    ("飞虎队", "飛虎隊", "Flying Tigers", "Flying Tiger", "American Volunteer Group"),
    ("滇缅", "滇緬", "滇缅公路", "滇緬公路", "Burma Road"),
    ("远征军", "遠征軍", "Chinese Expeditionary Force"),
    ("驻印军", "駐印軍", "Chinese Army in India"),
    ("缅甸", "緬甸", "Burma", "Myanmar"),
    ("雷多", "雷多公路", "Ledo", "Ledo Road"),
    ("中缅印", "中緬印", "China Burma India", "China-Burma-India"),
    ("驼峰", "駝峰", "Hump", "Hump airlift"),
)


@dataclass(frozen=True)
class Download:
    data: bytes
    source_exhausted: bool
    bytes_read: int
    fetched_at: str = None


def positive_int(value, maximum):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError("Invalid bound")
    return value


def expand_queries(query):
    if not isinstance(query, str) or not query.strip() or len(query) > 200:
        raise ValueError("Invalid query")
    # A pipe explicitly means OR. Spaces are retained within a phrase.
    terms = [part.strip() for part in query.split("|")]
    if len(terms) > 8 or any(not term for term in terms):
        raise ValueError("Invalid query")
    expanded = []
    for term in terms:
        group = next((group for group in QUERY_ALIASES
                      if term.casefold() in [alias.casefold() for alias in group]), ())
        for alias in (term, *group):
            if alias.casefold() not in [previous.casefold() for previous in expanded]:
                expanded.append(alias)
    return expanded


def validate_fetched_at(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Invalid retrieval timestamp")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Retrieval timestamp needs timezone")
    return value


def read_bounded(stream, max_bytes, *, fetched_at=None, deadline=None):
    """Read at most the configured cap plus one lookahead byte to detect EOF."""
    positive_int(max_bytes, MAX_BYTES)
    chunks = []
    size = 0
    exhausted = False
    while size <= max_bytes:
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError
        chunk = stream.read(min(65536, max_bytes + 1 - size))
        if not isinstance(chunk, bytes):
            raise ValueError("Expected bytes")
        if not chunk:
            exhausted = True
            break
        size += len(chunk)
        if size > max_bytes + 1:
            raise ValueError("Reader exceeded bound")
        chunks.append(chunk)
    return Download(b"".join(chunks)[:max_bytes], exhausted, size, fetched_at)


def fetch_csv(max_bytes=DEFAULT_MAX_BYTES):
    """GET one fixed official URL, without redirects, retries or credentials."""
    positive_int(max_bytes, MAX_BYTES)
    fetched_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    request = Request(CSV_URL, headers={
        "Accept": "text/csv",
        "User-Agent": "PacificWarDiscoveryDemo/1.0 (bounded public catalogue metadata)",
    })
    with build_opener(NoRedirect()).open(request, timeout=TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise HTTPError(CSV_URL, response.status, "Unexpected status", {}, None)
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type not in {"text/csv", "application/csv", "application/octet-stream"}:
            raise ValueError("Expected CSV response")
        if response.headers.get("Content-Encoding", "identity").lower() != "identity":
            raise ValueError("Unexpected content encoding")
        return read_bounded(response, max_bytes, fetched_at=fetched_at,
                            deadline=time.monotonic() + MAX_SECONDS)


def normalize_row(row, query, fetched_at):
    fonds, archival_id, title = (row[field].strip() for field in ("全宗名", "檔號", "案名"))
    if not fonds or not archival_id or not title:
        raise ValueError("Missing archival identity or title")
    source_id = hashlib.sha256((fonds + "\0" + archival_id).encode("utf-8")).hexdigest()
    return {
        "id": "taiwan:" + source_id, "source_id": source_id, "source": SOURCE,
        "source_name_en": INSTITUTION, "source_name_zh": "台湾国家发展委员会档案管理局",
        "title": title, "description": None, "archival_id": archival_id,
        "archival_context": [fonds], "holding_institution": [INSTITUTION],
        "metadata_provider": [INSTITUTION], "date_display": None,
        "date_kind": "not_supplied", "year": [], "format": "TEXT",
        "language": [], "metadata_language": ["zh-Hant"],
        "level_of_description": "fileUnit", "source_url": CATALOGUE_URL,
        "source_url_kind": "catalogue_search", "dataset_url": CSV_URL,
        "dataset_generated_at": row["資料產製日期"].strip() or None,
        "access_status": "unverified", "review_status": "candidate",
        "metadata_rights": LICENSE_URL, "content_rights": [],
        "retrieved_at": fetched_at, "query_used": query, "record_origin": "dataset",
    }


def parse_csv(data, query, limit=20, source_exhausted=True,
              max_scan_rows=DEFAULT_MAX_SCAN_ROWS, fetched_at=None):
    """Validate and search complete records in a UTF-8/BOM CSV or bounded prefix.

    Dates in 資料產製日期 describe dataset generation, not the archival material.
    Identical fonds/call-number duplicates count once; conflicting titles fail.
    """
    positive_int(limit, 100)
    positive_int(max_scan_rows, MAX_SCAN_ROWS)
    effective_queries = expand_queries(query)
    validate_fetched_at(fetched_at)
    if not isinstance(data, bytes) or len(data) > MAX_BYTES or type(source_exhausted) is not bool:
        raise ValueError("Invalid CSV input")
    decoder = codecs.getincrementaldecoder("utf-8-sig")(errors="strict")
    text = decoder.decode(data, final=source_exhausted)
    if not source_exhausted:
        # Drop any unfinished physical line. csv.reader then discards a quoted
        # multiline record if this prefix ends before its closing quote.
        text = text[:max(text.rfind("\n"), text.rfind("\r")) + 1]
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader)
    except (StopIteration, csv.Error):
        raise ValueError("Missing CSV header") from None
    if len(header) != len(COLUMNS) or set(header) != set(COLUMNS):
        raise ValueError("Unexpected CSV schema")
    records = []
    seen = {}
    matches = set()
    scanned_rows = 0
    duplicate_rows = 0
    row_limit_reached = False
    try:
        for values in reader:
            if not values:
                continue
            if scanned_rows >= max_scan_rows:
                row_limit_reached = True
                break
            if len(values) != len(header):
                raise ValueError("Unexpected CSV row shape")
            row = dict(zip(header, values))
            record = normalize_row(row, query, fetched_at)
            scanned_rows += 1
            identity = record["id"]
            if identity in seen:
                if seen[identity] != record["title"]:
                    raise ValueError("Conflicting titles for one archival identity")
                duplicate_rows += 1
                continue
            seen[identity] = record["title"]
            searchable = "\n".join((record["title"], *record["archival_context"], record["archival_id"])).casefold()
            if any(term.casefold() in searchable for term in effective_queries):
                matches.add(identity)
                if len(records) < limit:
                    records.append(record)
    except csv.Error as exc:
        if source_exhausted or "unexpected end of data" not in str(exc):
            raise ValueError("Malformed CSV") from None
    scan_complete = source_exhausted and not row_limit_reached
    snapshot = {
        "source": SOURCE, "dataset_url": CSV_URL, "effective_query": query,
        "effective_queries": effective_queries, "fetched_at": fetched_at,
        "returned_count": len(records), "matched_count": len(matches),
        "scanned_rows": scanned_rows, "duplicate_rows": duplicate_rows,
        "bytes_read": len(data), "source_exhausted": source_exhausted,
        "row_limit_reached": row_limit_reached, "scan_complete": scan_complete,
        "selection_note": (
            "Local substring search over case title, fonds and archival number, with explicit query aliases. "
            "Records are case-level metadata; digitization, historical dates and item URLs are not supplied. "
            + ("Whole CSV scanned; matched_count is the exact deduplicated query count."
               if scan_complete else "Partial CSV scan; matched_count counts only observed matches and is not a dataset total.")
        ), "records": records,
    }
    if scan_complete:
        snapshot["total_results"] = len(matches)
    return snapshot


def snapshot_from_download(download, query, limit=20, max_scan_rows=DEFAULT_MAX_SCAN_ROWS):
    if (not isinstance(download, Download) or type(download.bytes_read) is not int
            or download.bytes_read < len(download.data) or download.bytes_read > MAX_BYTES + 1):
        raise ValueError("Invalid download")
    payload = parse_csv(download.data, query, limit, download.source_exhausted,
                        max_scan_rows, download.fetched_at)
    payload["bytes_read"] = download.bytes_read
    return payload


def main(argv=None):
    parser = SafeArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Make one bounded request to the official CSV")
    parser.add_argument("--input", type=Path, help="Reuse a local CSV without networking; cannot be combined with --live")
    parser.add_argument("--partial-input", action="store_true", help="The local CSV is only a source prefix; never claim a whole-dataset total")
    parser.add_argument("--fetched-at", help="Original ISO 8601 retrieval timestamp with timezone for --input; omitted means unknown")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Literal phrase or up to eight pipe-separated OR phrases; finite aliases are expanded")
    parser.add_argument("--rows", type=int, default=20, help="Save 1–100 matches (default 20); still scan to the configured bounds")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help="Byte cap, default 4194304; maximum 67108864 (one EOF lookahead byte)")
    parser.add_argument("--max-scan-rows", type=int, default=DEFAULT_MAX_SCAN_ROWS, help="Scan 1–1000000 CSV rows (default 200000)")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/taiwan-discovery.json")
    args = parser.parse_args(argv)
    try:
        positive_int(args.rows, 100)
        positive_int(args.max_bytes, MAX_BYTES)
        positive_int(args.max_scan_rows, MAX_SCAN_ROWS)
        aliases = expand_queries(args.query)
        validate_fetched_at(args.fetched_at)
        if (args.live and args.input) or ((args.fetched_at or args.partial_input) and not args.input):
            raise ValueError
    except ValueError:
        parser.error("Invalid arguments")
    if not args.live and not args.input:
        print(json.dumps({"status": "ready", "request_sent": False, "dataset_url": CSV_URL,
                          "effective_query": args.query, "effective_queries": aliases,
                          "max_bytes": args.max_bytes, "max_scan_rows": args.max_scan_rows,
                          "message": "Use --live for one CSV request or --input for local reuse; nothing saved."},
                         ensure_ascii=False, indent=2))
        return 0
    try:
        if args.input:
            with args.input.open("rb") as stream:
                download = read_bounded(stream, args.max_bytes, fetched_at=args.fetched_at)
            if args.partial_input:
                download = replace(download, source_exhausted=False)
        else:
            download = fetch_csv(args.max_bytes)
        payload = snapshot_from_download(download, args.query, args.rows, args.max_scan_rows)
        atomic_save(args.output, payload)
        report = {key: value for key, value in payload.items() if key != "records"}
        report.update(status="ok", request_sent=bool(args.live), output=str(args.output))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (HTTPError, URLError, TimeoutError, socket.timeout, OSError, ValueError, UnicodeError, csv.Error):
        print(json.dumps({"status": "error", "request_sent": bool(args.live),
                          "message": "CSV retrieval or validation failed; the previous snapshot was preserved. No retry was attempted."}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
