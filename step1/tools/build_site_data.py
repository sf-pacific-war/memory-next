#!/usr/bin/env python3
"""Build a public, allowlisted catalogue from local metadata snapshots only.

No networking, environment files, credentials, or image downloads. Raw source
snapshots remain unchanged. Run this again after refreshing source metadata.
"""

from datetime import datetime, timezone
import ipaddress
import json
import re
from pathlib import Path
import tempfile
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
THUMBNAIL_HOSTS = ("loc.gov", "archives.gov", "si.edu", "archive.org", "iwm.org.uk")
SOURCE_NAMES = {
    "LoC": ("Library of Congress", "美国国会图书馆"),
    "NDL": ("National Diet Library", "日本国立国会图书馆"),
    "Europeana": ("Europeana", "欧洲数字文化遗产平台"),
    "NARA": ("National Archives and Records Administration", "美国国家档案馆"),
    "Internet Archive": ("Internet Archive", "互联网档案馆"),
    "Smithsonian": ("Smithsonian Institution", "史密森学会"),
    "CIA": ("Central Intelligence Agency Museum", "美国中央情报局博物馆"),
    "IWM": ("Imperial War Museums", "帝国战争博物馆"),
    "CARL": ("Ike Skelton Combined Arms Research Library", "艾克·斯凯尔顿联合兵种研究图书馆"),
    "Rice University": ("Woodson Research Center, Rice University", "莱斯大学伍德森研究中心"),
}
CURATED_SOURCES = (
    {"id": "Internet Archive", "prefix": "ia:", "url": "https://archive.org/", "hosts": ("archive.org",)},
    {"id": "Smithsonian", "prefix": "smithsonian:", "url": "https://www.si.edu/", "hosts": ("si.edu",)},
    {"id": "CIA", "prefix": "cia:", "url": "https://www.cia.gov/legacy/museum/", "hosts": ("cia.gov",)},
    {"id": "IWM", "prefix": "iwm:", "url": "https://www.iwm.org.uk/", "hosts": ("iwm.org.uk", "iwmcollections.org.uk")},
    {"id": "CARL", "prefix": "carl:", "url": "https://cgsc.contentdm.oclc.org/", "hosts": ("cgsc.contentdm.oclc.org",)},
    {"id": "Rice University", "prefix": "rice:", "url": "https://archives.library.rice.edu/", "hosts": ("rice.edu",)},
)
SOURCES = (
    {"id": "LoC", "file": "loc-discovery.json", "prefix": "loc:",
     "label": "美国国会图书馆", "url": "https://www.loc.gov/",
     "description": "照片、图像及相关档案目录。访问状态依据来源元数据，使用权仍需逐条核对。"},
    {"id": "NDL", "file": "ndl-discovery.json", "prefix": "ndl:",
     "label": "日本国会图书馆", "url": "https://ndlsearch.ndl.go.jp/",
     "description": "NDL Search API 书目元数据（CC BY 4.0）。包含战后出版物；出版日期不等于战役日期。"},
    {"id": "Europeana", "file": "europeana-discovery-candidates.json", "prefix": "europeana:",
     "label": "欧洲数字文化遗产", "url": "https://www.europeana.eu/",
     "description": "欧洲文化机构聚合目录。元数据为 CC0，原始内容使用权以来源说明为准。"},
    {"id": "NARA", "file": "nara-discovery.json", "prefix": "nara:",
     "label": "美国国家档案馆", "url": "https://www.archives.gov/developer/national-archives-catalog-dataset",
     "description": "NARA 官方开放数据集的 RG 493 目录样本，以及人工整理的官方照片记录。目录与照片分别保留来源和访问说明；并非实时 Catalog API。"},
)
TEXT_FIELDS = (
    "id", "source_id", "source", "title", "description", "date_display", "date_kind",
    "format", "access_status", "review_status", "retrieved_at", "query_used",
    "level_of_description", "record_group", "dataset_updated_at",
)
LIST_FIELDS = (
    "holding_institution", "metadata_provider", "year", "language", "metadata_language",
    "content_rights", "subjects", "archival_context",
)
URL_FIELDS = ("source_url", "aggregator_url", "thumbnail_url", "metadata_rights", "dataset_url")


class BuildError(Exception):
    pass


def public_url(value):
    if not isinstance(value, str) or "\\" in value or any(c.isspace() or ord(c) < 32 for c in value):
        return None
    try:
        parts = urlsplit(value)
        host = parts.hostname
        if parts.scheme not in {"https", "http"} or not host or parts.username or parts.password:
            return None
        if host == "localhost" or host.endswith((".localhost", ".local")) or "." not in host:
            return None
        if parts.port not in {None, 80, 443}:
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            pass
        sensitive = {"key", "wskey", "api_key", "apikey", "access_token", "token", "secret", "signature", "authorization"}
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if k.lower() not in sensitive and not k.lower().startswith("x-amz-")]
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))
    except ValueError:
        return None


def public_record(record, source):
    if not isinstance(record, dict):
        return None
    identity = record.get("id")
    if not isinstance(identity, str) or not identity.startswith(source["prefix"]):
        return None
    if record.get("source") != source["id"]:
        return None
    # Nested arbitrary upstream fields and extra raw API response properties
    # cannot cross this explicit publishing boundary.
    result = {key: record.get(key) if isinstance(record.get(key), str) else None for key in TEXT_FIELDS}
    for key in LIST_FIELDS:
        values = record.get(key)
        result[key] = list(dict.fromkeys(v for v in values if isinstance(v, str))) if isinstance(values, list) else []
    for key in URL_FIELDS:
        if key in record or key != "thumbnail_url":
            result[key] = public_url(record.get(key))
    if "thumbnail_url" in result:
        result["thumbnail_url"] = archival_thumbnail(result["thumbnail_url"])
    for key in URL_FIELDS:
        if result.get(key) and reference_host(urlsplit(result[key]).hostname):
            result[key] = None
    result["access_status"] = "online" if record.get("access_status") == "online" else "unverified"
    result["review_status"] = "candidate"
    return result


def load_exclusions(project_root):
    path = project_root / "data" / "review-notes.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = payload["excluded"]
        if not isinstance(entries, list):
            raise ValueError
        ids = set()
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not entry["id"]:
                raise ValueError
            ids.add(entry["id"])
        return ids
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise BuildError("Cannot read review-notes.json; catalogue was not rebuilt.") from None


def reference_host(host):
    return host == "cbi-theater.com" or (host or "").endswith(".cbi-theater.com")


def archival_thumbnail(value):
    url = public_url(value)
    if not url or urlsplit(url).scheme != "https":
        return None
    host = urlsplit(url).hostname
    return url if any(host == h or host.endswith("." + h) for h in THUMBNAIL_HOSTS) else None


def canonical_archival_url(value):
    """Normalize item identity without collapsing distinct resource pages."""
    url = public_url(value)
    if not url:
        return None
    parts = urlsplit(url)
    host = parts.hostname.lower().removeprefix("www.")
    path = parts.path.rstrip("/")
    # Viewer selectors (e.g. LoC ?sp=2) can distinguish an actual resource.
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query)
                             if not k.lower().startswith("utm_") and k.lower() not in {"ref", "fbclid"}))
    return host + path + ("?" + query if query else "")


def native_identity(source, url):
    """Use the institution's item identity, not the internal comparison ID."""
    parts = urlsplit(url)
    path = parts.path.rstrip("/")
    patterns = {
        "LoC": (r"/(?:item|resource)/([^/]+)$", "loc:"),
        "NDL": (r"/books/([^/]+)$", "ndl:"),
        "NARA": (r"/id/(\d+)$", "nara:"),
        "Europeana": (r"/item(/.+)$", "europeana:"),
        "Internet Archive": (r"/details/([^/]+)$", "ia:"),
        "Smithsonian": (r"/(?:object|editorial)/([^/]+)$", "smithsonian:"),
        "CIA": (r"/artifact/([^/]+)$", "cia:"),
        "IWM": (r"/record/(\d+)$", "iwm:"),
        "CARL": (r"/collection/([^/]+/id/\d+)$", "carl:"),
        "Rice University": (r"/archival_objects/(\d+)$", "rice:"),
    }
    pattern, prefix = patterns.get(source, (r"(?!)", ""))
    match = re.search(pattern, path)
    if not match:
        return None
    identity = prefix + match.group(1)
    if source == "LoC" and path.startswith("/resource/") and parts.query:
        identity += "?" + urlencode(sorted(parse_qsl(parts.query)))
    return identity


def curated_record(raw, source):
    if not isinstance(raw, dict) or raw.get("source") != source["id"]:
        return None
    url = public_url(raw.get("archival_url"))
    if not url:
        return None
    hosts = source.get("hosts") or {
        "LoC": ("loc.gov",), "NDL": ("ndl.go.jp",),
        "Europeana": ("europeana.eu",), "NARA": ("archives.gov",),
    }[source["id"]]
    host = urlsplit(url).hostname
    if not any(host == allowed or host.endswith("." + allowed) for allowed in hosts):
        return None
    identity = native_identity(source["id"], url)
    if not identity or not isinstance(raw.get("archival_title"), str):
        return None
    # Dates in manual notes describe a check, not a source retrieval or an
    # item's creation. Keep those distinct; never fill missing historical dates.
    clean = public_record({
        "id": identity, "source_id": identity.split(":", 1)[1], "source": source["id"],
        "title": raw["archival_title"], "source_url": url, "aggregator_url": url,
        "format": {"photograph": "IMAGE", "book": "TEXT", "map": "MAP", "personal_narrative": "MIXED",
                   "artifact": "OBJECT", "article": "TEXT", "film": "VIDEO", "newspaper": "TEXT",
                   "audio": "SOUND"}.get(raw.get("material_type"), "MIXED"),
        "date_kind": "not_supplied", "content_rights": [raw["rights_note"]] if isinstance(raw.get("rights_note"), str) else [],
        "metadata_provider": [SOURCE_NAMES[source["id"]][0]],
        "thumbnail_url": raw.get("thumbnail_url") if raw.get("thumbnail_verified_http_status") == 200 else None,
        "access_status": "online" if archival_thumbnail(raw.get("thumbnail_url")) and raw.get("thumbnail_verified_http_status") == 200 else "unverified",
    }, source)
    clean.update({"record_origin": "curated", "material_type": raw.get("material_type"),
                  "checked_at": raw.get("checked_at") if isinstance(raw.get("checked_at"), str) else None,
                  "access_note": raw.get("access_note") if isinstance(raw.get("access_note"), str) else None,
                  "archival_id": raw.get("archival_id") if isinstance(raw.get("archival_id"), str) else None,
                  "thumbnail_source_url": public_url(raw.get("thumbnail_source_url"))})
    if clean["thumbnail_source_url"] and reference_host(urlsplit(clean["thumbnail_source_url"]).hostname):
        clean["thumbnail_source_url"] = None
    return clean


def read_optional(path, default):
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError
        return payload
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        raise BuildError(f"Cannot read {path.name}; catalogue was not rebuilt.") from None


def bilingual(value):
    return {lang: value[lang] for lang in ("zh-CN", "en")
            if isinstance(value, dict) and isinstance(value.get(lang), str)}


def apply_topics(project_root, records):
    payload = read_optional(project_root / "data" / "topics.json", {})
    notes = payload.get("curator_notes", {})
    indexed = {r["id"]: r for r in records}
    for record in records:
        record.update({"topic_ids": [], "topic_keywords": []})
        note = bilingual(notes.get(record["id"])) if isinstance(notes, dict) else {}
        if note:
            record["curator_note"] = note
    topics = []
    seen = set()
    for raw in payload.get("topics", []):
        if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or raw["id"] in seen:
            raise BuildError("Invalid or duplicate topic ID; catalogue was not rebuilt.")
        title, description = bilingual(raw.get("title")), bilingual(raw.get("description"))
        if len(title) != 2 or len(description) != 2:
            raise BuildError("Topics require English and Chinese titles and descriptions.")
        keywords = {lang: list(dict.fromkeys(v for v in raw.get("keywords", {}).get(lang, [])
                                            if isinstance(v, str) and v)) for lang in ("zh-CN", "en")}
        identities = list(dict.fromkeys(identity for identity in raw.get("record_ids", []) if identity in indexed))
        seen.add(raw["id"])
        if not identities:
            continue
        topic = {"id": raw["id"], "title": title, "description": description, "keywords": keywords, "record_ids": identities}
        topics.append(topic)
        terms = list(dict.fromkeys([*title.values(), *keywords["zh-CN"], *keywords["en"]]))
        for identity in identities:
            indexed[identity]["topic_ids"].append(raw["id"])
            indexed[identity]["topic_keywords"] = list(dict.fromkeys([*indexed[identity]["topic_keywords"], *terms]))
    return topics


def build_catalog(project_root=PROJECT_ROOT):
    project_root = Path(project_root)
    exclusions = load_exclusions(project_root)
    source_index = {s["id"]: s for s in (*SOURCES, *CURATED_SOURCES)}
    source_state = {s["id"]: {"available": False, "fetched_at": None} for s in SOURCES}
    candidates = []
    for source in SOURCES:
        try:
            payload = json.loads((project_root / "data" / source["file"]).read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("source") != source["id"] or not isinstance(payload.get("records"), list):
                raise ValueError
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            continue
        source_state[source["id"]] = {"available": True, "fetched_at": payload.get("fetched_at") if isinstance(payload.get("fetched_at"), str) else None}
        for raw in payload["records"]:
            clean = public_record(raw, source)
            if clean:
                clean["record_origin"] = "dataset" if source["id"] == "NARA" else "api"
                candidates.append((clean, {clean["id"]}))
    extra = read_optional(project_root / "data" / "cbi" / "archive-records.json", {})
    for query in extra.get("queries", []):
        for entry in query.get("excluded_records", []) if isinstance(query, dict) else []:
            if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                exclusions.add(entry["id"])
    for raw in extra.get("records", []):
        source = source_index.get(raw.get("source")) if isinstance(raw, dict) else None
        clean = public_record(raw, source) if source else None
        if clean:
            clean["record_origin"] = "dataset" if source["id"] == "NARA" else "api"
            candidates.append((clean, {clean["id"]}))
    curated = read_optional(project_root / "data" / "cbi" / "verified-matches.json", {})
    for raw in curated.get("records", []):
        source = source_index.get(raw.get("source")) if isinstance(raw, dict) else None
        clean = curated_record(raw, source) if source else None
        if clean:
            candidates.append((clean, {clean["id"], raw.get("id")}))

    def identity_keys(record):
        keys = {(record["source"], "id", record["id"])}
        if record.get("source_id"):
            keys.add((record["source"], "native", record["source_id"]))
        for field in ("source_url", "aggregator_url"):
            url = canonical_archival_url(record.get(field))
            if url:
                keys.add((record["source"], "url", url))
        return keys

    # An exclusion on any duplicate, including an internal manual-review ID,
    # suppresses every copy of that institution's item across input snapshots.
    excluded_keys = set()
    for record, aliases in candidates:
        if aliases & exclusions:
            excluded_keys.update(identity_keys(record))
    records, indexed, excluded = [], {}, set()
    for record, aliases in candidates:
        keys = identity_keys(record)
        if keys & excluded_keys:
            excluded.add(record["id"])
            continue
        existing = next((indexed[k] for k in keys if k in indexed), None)
        if existing is not None:
            # Original API metadata and retrieval date have priority. Attach only
            # clearly labelled manual access notes, never comparison evidence.
            if record["record_origin"] == "curated":
                for key in ("checked_at", "access_note", "archival_id"):
                    if record.get(key):
                        existing[key] = record[key]
            for key in keys:
                indexed[key] = existing
            continue
        record.update({"source_name_en": SOURCE_NAMES[record["source"]][0],
                       "source_name_zh": SOURCE_NAMES[record["source"]][1]})
        records.append(record)
        for key in keys:
            indexed[key] = record
    topics = apply_topics(project_root, records)
    sources = []
    for source in (*SOURCES, *CURATED_SOURCES):
        members = [r for r in records if r["source"] == source["id"]]
        if not members and source["id"] not in source_state:
            continue
        state = source_state.get(source["id"], {})
        modes = list(dict.fromkeys(r["record_origin"] for r in members))
        dates = [r["retrieved_at"] for r in members if r.get("retrieved_at")]
        if state.get("fetched_at"):
            dates.append(state["fetched_at"])
        checks = [r["checked_at"] for r in members if r.get("checked_at")]
        english, chinese = SOURCE_NAMES[source["id"]]
        sources.append({"id": source["id"], "label": chinese, "label_en": english,
                        "source_name_en": english, "source_name_zh": chinese,
                        "url": source["url"],
                        "description": source.get("description", "人工整理的机构目录与研究线索。逐条保留访问说明；目录链接不等于可获取全文或媒体授权。"),
                        "status": "available" if members or state.get("available") else "unavailable",
                        "count": len(members), "fetched_at": max(dates) if dates else None,
                        "checked_at": max(checks) if checks else None,
                        "access_modes": modes,
                        "counts_by_origin": {mode: sum(r["record_origin"] == mode for r in members) for mode in modes}})
    return {"generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "records": records, "sources": sources, "topics": topics, "excluded_count": len(excluded)}


def write_catalog(project_root=PROJECT_ROOT):
    project_root = Path(project_root)
    catalog = build_catalog(project_root)
    site = project_root / "site"
    destination = site / "data" / "catalog.json"
    if site.is_symlink() or destination.parent.is_symlink() or destination.is_symlink():
        raise BuildError("Public catalogue destination must not be a symbolic link.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                         prefix=".catalog-", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(catalog, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return catalog


def main():
    try:
        result = write_catalog()
    except (BuildError, OSError) as exc:
        print(str(exc) if isinstance(exc, BuildError) else "Could not write public catalogue.")
        return 1
    print("Public catalogue built: " + str(len(result["records"])) + " records; "
          + str(result["excluded_count"]) + " review exclusions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
