#!/usr/bin/env python3
"""Build a small CBI demonstration metadata set from official archive APIs.

Run without --live to inspect the plan without networking or writing files.
Use --live --env-file .env.europeana for the complete credentialed refresh.
Only metadata is requested: no media downloads, retries, or pagination. Each
platform has three fixed topic queries, at most five results per request, with
five seconds between requests. A platform stops after a rate-limit response.
Existing normalized snapshots remain labelled with their actual retrieval dates.
These are keyword candidates, not verified matches to items on cbi-theater.com.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.parse import urlencode

import build_site_data as site_data
import fetch_europeana_metadata as europeana
import fetch_public_metadata as public


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "cbi" / "archive-records.json"
PLAN = (
    ("LoC", '"Flying Tigers"', "https://www.loc.gov/search/"),
    ("LoC", '"Ledo Road"', "https://www.loc.gov/photos/"),
    ("LoC", "Burma 1944", "https://www.loc.gov/maps/"),
    ("Europeana", "Chindits", europeana.ENDPOINT),
    ("Europeana", 'Burma AND "1944"', europeana.ENDPOINT),
    ("Europeana", '"Ledo Road"', europeana.ENDPOINT),
)
SOURCE_CONFIG = {source["id"]: source for source in site_data.SOURCES}
# Reviewed locality/date collisions from this pilot. Preserve query evidence,
# but do not present herbarium specimens or zoological research as war material.
EXCLUDED_CANDIDATES = {
    "europeana:/08711/https___www_biodiversitylibrary_org_item_332331": "Zoological publication on earthworms; no CBI wartime connection established.",
    "europeana:/11614/KXHERBARIUMXK001080675": "Herbarium specimen; Ledo Road is a collecting locality, not evidence of wartime relevance.",
    "europeana:/519/catalognumber_mnhn_p_p04423951": "Herbarium specimen; Ledo Road is a collecting locality, not evidence of wartime relevance.",
    "europeana:/11614/KXHERBARIUMXK001142966": "Herbarium specimen; Ledo Road is a collecting locality, not evidence of wartime relevance.",
}


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def retrieval_time(record):
    """Compare explicit timezone-aware retrieval dates; absent/invalid dates lose."""
    try:
        value = datetime.fromisoformat(record.get("retrieved_at", "").replace("Z", "+00:00"))
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc)
    except (AttributeError, TypeError, ValueError):
        pass
    return datetime.min.replace(tzinfo=timezone.utc)


def seed_records(output):
    """Retain allowlisted old candidates and their original retrieval evidence."""
    excluded = site_data.load_exclusions(PROJECT_ROOT) | set(EXCLUDED_CANDIDATES)
    records, queries = {}, []
    for source in SOURCE_CONFIG.values():
        path = PROJECT_ROOT / "data" / source["file"]
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        retained = []
        for raw in snapshot.get("records", []):
            record = site_data.public_record(raw, source)
            if record and record["id"] not in excluded:
                records[record["id"]] = record
                retained.append(record["id"])
        queries.append({
            "source": source["id"], "query": snapshot.get("effective_query"),
            "status": "existing_snapshot", "retrieved_at": snapshot.get("fetched_at"),
            "total_results": snapshot.get("total_results"), "returned_count": len(retained),
            "record_ids": retained, "snapshot_file": "data/" + source["file"],
            "note": "Previously retrieved metadata; this seed was not requested again in this run.",
        })
    if output.exists():
        previous = json.loads(output.read_text(encoding="utf-8"))
        for raw in previous.get("records", []):
            source = SOURCE_CONFIG.get(raw.get("source")) if isinstance(raw, dict) else None
            record = site_data.public_record(raw, source) if source else None
            current = records.get(record["id"]) if record else None
            if record and record["id"] not in excluded and (
                current is None or retrieval_time(record) > retrieval_time(current)
            ):
                records[record["id"]] = record
                queries.append({
                    "source": record["source"], "query": record.get("query_used"),
                    "status": "retained_previous_candidate", "retrieved_at": record.get("retrieved_at"),
                    "returned_count": 1, "record_ids": [record["id"]],
                    "note": "Retained from the previous demo metadata file; not evidence of current access.",
                })
    return records, queries, excluded


def fetch(source, query, endpoint, rows, key):
    if source == "Europeana":
        return europeana.fetch_metadata(query, rows, key)
    if source != "LoC":
        raise public.FetchError("Unsupported source; no request sent.")
    params = {"q": query, "fo": "json", "c": rows}
    body = public.fetch_bytes(endpoint + "?" + urlencode(params))
    retrieved_at = now()
    payload = json.loads(body)
    result = public.normalize_loc_response(payload, query, retrieved_at)
    if result["returned_count"] > rows:
        raise public.FetchError("LoC returned more records than requested.")
    # The shared photo normalizer leaves text formats unknown; only use an
    # explicit original_format value from the same official search response.
    formats = {public.source_url(item.get("url") or item.get("id"), {"www.loc.gov", "loc.gov"}): public.strings(item.get("original_format"))
               for item in payload.get("results", []) if isinstance(item, dict)}
    for record in result["records"]:
        if record["format"] is None and any(value in {"book", "newspaper", "periodical"}
                                              for value in formats.get(record["source_url"], [])):
            record["format"] = "TEXT"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Send the bounded requests and write the metadata report.")
    parser.add_argument("--env-file", help="Explicit Git-ignored Europeana credential file; never printed or copied.")
    parser.add_argument("--rows", type=int, default=3, choices=range(1, 6), help="Records per query, 1–5; default 3.")
    parser.add_argument("--sources", nargs="+", choices=("LoC", "Europeana"), default=["LoC", "Europeana"])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    plan = [entry for entry in PLAN if entry[0] in args.sources]
    if not args.live:
        print(json.dumps({"mode": "dry_run", "requests": [
            {"source": source, "query": query, "endpoint": endpoint, "rows": args.rows}
            for source, query, endpoint in plan
        ]}, ensure_ascii=False, indent=2))
        return 0
    try:
        records, queries, excluded = seed_records(args.output)
    except (OSError, ValueError, site_data.BuildError):
        print("Cannot read existing metadata safely; no requests sent and no file changed.")
        return 1
    key, key_error = None, None
    if "Europeana" in args.sources:
        try:
            key = europeana.load_key(args.env_file)
        except europeana.FetchError as exc:
            key_error = str(exc)
    failed, last_request, stopped = False, None, set()
    for source, query, endpoint in plan:
        result = {"source": source, "query": query, "endpoint": endpoint,
                  "requested_rows": args.rows, "checked_at": now(), "record_ids": []}
        if source in stopped:
            result.update(status="skipped_rate_limit", note="No request sent after this platform's rate limit.")
        elif source == "Europeana" and not key:
            result.update(status="missing_credential", note=key_error)
            failed = True
        else:
            if last_request is not None:
                time.sleep(max(0, 5 - (time.monotonic() - last_request)))
            result["checked_at"] = now()
            last_request = time.monotonic()
            try:
                snapshot = fetch(source, query, endpoint, args.rows, key)
                for raw in snapshot["records"]:
                    record = site_data.public_record(raw, SOURCE_CONFIG[source])
                    if record and record["id"] not in excluded:
                        records[record["id"]] = record
                        if record["id"] not in result["record_ids"]:
                            result["record_ids"].append(record["id"])
                    elif record and record["id"] in EXCLUDED_CANDIDATES:
                        result.setdefault("excluded_records", []).append({
                            "id": record["id"], "title": record["title"], "source_url": record["source_url"],
                            "reason": EXCLUDED_CANDIDATES[record["id"]],
                        })
                result.update(status="ok", total_results=snapshot["total_results"],
                              returned_count=snapshot["returned_count"], imported_count=len(result["record_ids"]),
                              retrieved_at=snapshot["fetched_at"])
            except (public.FetchError, europeana.FetchError, ValueError, UnicodeError, OSError) as exc:
                note = str(exc) if isinstance(exc, (public.FetchError, europeana.FetchError)) else "Response could not be parsed; no records imported."
                result.update(status="error", note=note)
                if "429" in note or "rate limit" in note.lower():
                    stopped.add(source)
                failed = True
        queries.append(result)
        print(source + ": " + result["status"] + "; imported " + str(len(result["record_ids"])) + " candidate records.", flush=True)
    report = {"generated_at": now(), "scope": "Bounded official metadata candidates for the CBI demo; no exact-item match is asserted.",
              "queries": queries, "records": list(records.values())}
    try:
        if key:
            europeana.serialize_without_key(report, key)
        public.atomic_save(args.output, report)
    except (europeana.FetchError, OSError, ValueError):
        print("Output could not be saved safely; previous file retained.")
        return 1
    print("Metadata report saved: " + str(len(records)) + " unique candidates; original retrieval dates retained.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
