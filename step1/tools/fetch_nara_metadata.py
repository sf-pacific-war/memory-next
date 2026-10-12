#!/usr/bin/env python3
"""Fetch one small shard of NARA's official, anonymous public dataset.

This uses the published S3 dataset, not the authenticated Catalog API. Only
catalog metadata is requested: no images, full text, pagination, retries,
redirects, credentials, or environment files. The fixed shard is in RG 493,
Records of U.S. Army Forces in the China-Burma-India Theaters of Operations.
Every result retains its description level and the shard's provenance.

References:
  https://www.archives.gov/developer/national-archives-catalog-dataset
  https://registry.opendata.aws/nara-national-archives-catalog/
"""

import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import socket
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_URL = (
    "https://nara-national-archives-catalog.s3.us-east-2.amazonaws.com/"
    "descriptions/record-groups/rg_493/rg_493-1.jsonl"
)
DATASET_DOCUMENTATION = "https://www.archives.gov/developer/national-archives-catalog-dataset"
DATASET_REGISTRY = "https://registry.opendata.aws/nara-national-archives-catalog/"
TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
DEFAULT_LIMIT = 15
SELECTION = "RG 493; one official public JSONL shard; locally selected metadata sample"
TOPIC = re.compile(r"\b(?:burma|china|chinese|cbi|india)\b", re.IGNORECASE)


class FetchError(Exception):
    """An upstream failure safe to display without response content."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def text(value):
    if not isinstance(value, str):
        return None
    parser = PlainText()
    parser.feed(value)
    return " ".join(" ".join(parser.parts).split()) or None


def strings(value):
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(clean for item in value if (clean := text(item))))


def naid(value):
    if type(value) is int and value > 0:
        return str(value)
    if isinstance(value, str) and re.fullmatch(r"[1-9][0-9]*", value):
        return value
    raise FetchError("NARA returned an invalid numeric record identifier.")


def dictionaries(value):
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def date_part(value):
    """Use explicit catalog precision, not synthetic logical-date day/month."""
    if not isinstance(value, dict):
        return None, None
    year = value.get("year")
    if type(year) is not int or not 1000 <= year <= 2100:
        return None, None
    month, day = value.get("month"), value.get("day")
    if month is None:
        if day is not None:
            raise FetchError("NARA returned an invalid source date.")
        return str(year), str(year)
    try:
        if type(month) is not int or (day is not None and type(day) is not int):
            raise ValueError
        datetime(year, month, 1 if day is None else day)
    except ValueError:
        raise FetchError("NARA returned an invalid source date.") from None
    return (f"{year:04d}-{month:02d}" if day is None else f"{year:04d}-{month:02d}-{day:02d}"), str(year)


def record_dates(record):
    # A description's inclusive/coverage dates are catalog ranges, never
    # automatically event dates. Never borrow dates from ancestors or titles.
    for prefix, kind in (("inclusive", "archival_inclusive"), ("coverage", "archival_coverage")):
        start, start_year = date_part(record.get(prefix + "StartDate"))
        end, end_year = date_part(record.get(prefix + "EndDate"))
        if start or end:
            display = " – ".join(dict.fromkeys(part for part in [start, end] if part))
            return display, kind, list(dict.fromkeys(y for y in [start_year, end_year] if y))
    production = [date_part(value) for value in dictionaries(record.get("productionDates"))]
    if any(part[0] for part in production):
        return "; ".join(dict.fromkeys(part[0] for part in production if part[0])), "production", list(dict.fromkeys(part[1] for part in production if part[1]))
    return None, "not_supplied", []


def digital_object_url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value) or "\\" in value:
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username and not parsed.password and parsed.port in {None, 80, 443}
    except ValueError:
        return False


def normalize_record(record, fetched_at, dataset_updated_at):
    record_id = naid(record.get("naId"))
    ancestors = dictionaries(record.get("ancestors"))
    is_rg493 = str(record.get("recordGroupNumber")) == "493" or any(str(item.get("recordGroupNumber")) == "493" for item in ancestors)
    if not is_rg493:
        raise FetchError("NARA shard contains a record without verified RG 493 provenance.")
    title = text(record.get("title"))
    level = text(record.get("levelOfDescription"))
    if not title or not level:
        raise FetchError("NARA record lacks a title or description level.")
    contexts = []
    for ancestor in ancestors:
        ancestor_id = naid(ancestor.get("naId"))
        if text(ancestor.get("title")):
            contexts.append({"id": ancestor_id, "title": text(ancestor["title"]),
                             "level_of_description": text(ancestor.get("levelOfDescription")),
                             "source_url": "https://catalog.archives.gov/id/" + ancestor_id})
    institutions = []
    for occurrence in dictionaries(record.get("physicalOccurrences")):
        institutions.extend(text(unit.get("name")) for unit in dictionaries(occurrence.get("referenceUnits")))
    date_display, date_kind, years = record_dates(record)
    materials = strings(record.get("generalRecordsTypes"))
    material_map = {"Textual Records": "TEXT", "Photographs and other Graphic Materials": "IMAGE",
                    "Maps and Charts": "MAP", "Sound Recordings": "SOUND", "Moving Images": "VIDEO"}
    formats = list(dict.fromkeys(material_map[item] for item in materials if item in material_map))
    restriction = record.get("accessRestriction")
    unrestricted = isinstance(restriction, dict) and restriction.get("status") == "Unrestricted"
    digital_objects = dictionaries(record.get("digitalObjects"))
    has_online_object = any(digital_object_url(item.get("objectUrl")) for item in digital_objects)
    use = record.get("useRestriction")
    rights = []
    if isinstance(use, dict):
        if text(use.get("status")):
            rights.append("NARA use restriction: " + text(use["status"]))
        rights.extend(strings(use.get("note")))
        rights.extend(strings(use.get("specificUseRestriction")))
    link = "https://catalog.archives.gov/id/" + record_id
    return {
        "id": "nara:" + record_id, "source_id": record_id, "source": "NARA",
        "title": title, "description": text(record.get("scopeAndContentNote")),
        "holding_institution": list(dict.fromkeys(item for item in institutions if item)) or ["National Archives and Records Administration"],
        "metadata_provider": ["NARA National Archives Catalog — official public dataset"],
        "date_display": date_display, "date_kind": date_kind, "year": years,
        "format": formats[0] if len(formats) == 1 else "MIXED" if len(formats) > 1 else None,
        "language": [], "metadata_language": ["en"],
        "source_url": link, "aggregator_url": link,
        "access_status": "online" if unrestricted and has_online_object else "unverified",
        "review_status": "candidate", "metadata_rights": DATASET_DOCUMENTATION,
        "content_rights": list(dict.fromkeys(rights)),
        "retrieved_at": fetched_at, "query_used": SELECTION,
        "level_of_description": level, "record_group": "493",
        "archival_context": list(dict.fromkeys(item["title"] for item in contexts)),
        "archival_ancestors": contexts,
        "dataset_url": DATASET_URL, "dataset_updated_at": dataset_updated_at,
    }


def normalize_jsonl(data, fetched_at, dataset_updated_at, limit=DEFAULT_LIMIT):
    if not 1 <= limit <= 100:
        raise FetchError("The sample limit must be between 1 and 100.")
    if len(data) > MAX_RESPONSE_BYTES:
        raise FetchError("NARA public dataset shard exceeded the size limit.")
    try:
        lines = data.decode("utf-8-sig").splitlines()
        rows = [json.loads(line) for line in lines if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise FetchError("NARA public dataset is not valid UTF-8 JSONL.") from None
    if not rows or any(not isinstance(row, dict) or not isinstance(row.get("record"), dict) for row in rows):
        raise FetchError("NARA public dataset has an unexpected JSONL structure.")
    records = [normalize_record(row["record"], fetched_at, dataset_updated_at) for row in rows]
    unique = list({record["id"]: record for record in records}.values())
    unique.sort(key=lambda item: not bool(TOPIC.search((item["title"] or "") + " " + (item["description"] or ""))))
    selected = unique[:limit]
    return {
        "source": "NARA", "effective_query": SELECTION, "fetched_at": fetched_at,
        "returned_count": len(selected), "records": selected,
        "dataset_url": DATASET_URL, "dataset_updated_at": dataset_updated_at,
        "dataset_documentation": DATASET_DOCUMENTATION, "dataset_registry": DATASET_REGISTRY,
        "shard_record_count": len(rows),
        "selection_note": "A small sample from one public RG 493 metadata shard, not a search of the full NARA Catalog or a count of the record group. Direct China/Burma/India title or description matches are prioritized; remaining records have verified RG 493 ancestry. Description dates retain their source meaning. No digital objects were downloaded.",
    }


def last_modified_iso(value):
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OverflowError):
        raise FetchError("NARA public dataset is missing a valid Last-Modified header.") from None


def fetch_bytes():
    request = Request(DATASET_URL, headers={"User-Agent": "PacificWarDiscoveryDemo/0.1 (small public metadata pilot)"})
    try:
        with build_opener(NoRedirect).open(request, timeout=TIMEOUT_SECONDS) as response:
            data = response.read(MAX_RESPONSE_BYTES + 1)
            modified = last_modified_iso(response.headers.get("Last-Modified"))
        if len(data) > MAX_RESPONSE_BYTES:
            raise FetchError("NARA public dataset shard exceeded the size limit.")
        return data, modified
    except HTTPError as exc:
        raise FetchError("NARA public dataset HTTP " + str(exc.code) + "; no automatic retry.") from None
    except (URLError, TimeoutError, socket.timeout, OSError):
        raise FetchError("NARA public dataset connection failed or timed out; no automatic retry.") from None


def atomic_save(path, payload):
    path = Path(path)
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
        if temporary is not None and temporary.exists():
            temporary.unlink()


def refresh(output, limit=DEFAULT_LIMIT):
    data, modified = fetch_bytes()
    fetched_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = normalize_jsonl(data, fetched_at, modified, limit)
    atomic_save(output, payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Maximum sample records (1–100; default 15)")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "nara-discovery.json")
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
    try:
        payload = refresh(args.output, args.limit)
    except (FetchError, OSError) as exc:
        print("NARA refresh failed: " + (str(exc) if isinstance(exc, FetchError) else "Could not safely write the metadata snapshot."))
        return 1
    print("Saved " + str(payload["returned_count"]) + " NARA metadata candidates from one official public dataset shard.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
