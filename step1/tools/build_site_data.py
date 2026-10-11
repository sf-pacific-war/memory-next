#!/usr/bin/env python3
"""Build a public, allowlisted catalogue from local metadata snapshots only.

No networking, environment files, credentials, or image downloads. Raw source
snapshots remain unchanged. Run this again after refreshing source metadata.
"""

from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import tempfile
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
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
     "description": "NARA 官方开放数据集 · RG 493 中缅印战区档案目录样本。无需 key；使用已发布的数据快照，并非实时 Catalog API。"},
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


def build_catalog(project_root=PROJECT_ROOT):
    project_root = Path(project_root)
    exclusions = load_exclusions(project_root)
    records, sources = [], []
    seen, excluded = set(), set()
    for source in SOURCES:
        summary = {key: source[key] for key in ("id", "label", "url", "description")}
        summary.update({"status": "unavailable", "count": 0, "fetched_at": None})
        try:
            payload = json.loads((project_root / "data" / source["file"]).read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("source") != source["id"] or not isinstance(payload.get("records"), list):
                raise ValueError
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            sources.append(summary)
            continue
        summary["status"] = "available"
        summary["fetched_at"] = payload.get("fetched_at") if isinstance(payload.get("fetched_at"), str) else None
        for raw in payload["records"]:
            record = public_record(raw, source)
            if not record:
                continue
            if record["id"] in exclusions:
                excluded.add(record["id"])
                continue
            if record["id"] in seen:
                continue
            seen.add(record["id"])
            records.append(record)
            summary["count"] += 1
        sources.append(summary)
    return {"generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "records": records, "sources": sources, "excluded_count": len(excluded)}


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
