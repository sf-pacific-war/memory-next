#!/usr/bin/env python3
"""Fetch one small Europeana metadata page without persisting credentials.

Python standard library only. No pagination, retries, redirects, media downloads,
or raw-response files. Dates are source-supplied discovery values, not event dates.

Field reference: https://europeana.atlassian.net/wiki/spaces/EF/pages/2385739812
Metadata licence: https://www.europeana.eu/en/rights/usage-guidelines-for-metadata
"""

import argparse
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, quote_plus, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


ENDPOINT = "https://api.europeana.eu/record/v2/search.json"
KEY_NAME = "EUROPEANA_API_KEY"
TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"


class FetchError(Exception):
    """An error with a fixed, credential-free public message."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the URL credential to another endpoint, even on HTTPS.
        return None


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's original message may echo user-supplied argument values.
        self.exit(2, "Invalid command-line arguments. Use --help.\n")


def load_key(env_file=None):
    """Prefer the process environment; otherwise read an explicitly named file.

    The file must be inside this project and ignored by Git. Values are literal:
    there is no shell execution, expansion, interpolation, or automatic dotenv load.
    """
    key = os.environ.get(KEY_NAME, "")
    if not key and env_file:
        try:
            path = Path(env_file).resolve(strict=True)
            relative = path.relative_to(PROJECT_ROOT)
            ignored = subprocess.run(
                ["git", "check-ignore", "--quiet", "--", str(relative)],
                cwd=PROJECT_ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
            if ignored.returncode != 0 or not path.is_file():
                raise FetchError("Credential file must be a Git-ignored project file.")
            if path.stat().st_size > 64 * 1024:
                raise FetchError("Credential file is too large.")
            matches = []
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith(KEY_NAME + "="):
                    value = line.partition("=")[2].strip()
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                        value = value[1:-1]
                    matches.append(value)
            if len(matches) != 1:
                raise FetchError("Credential file must contain exactly one key assignment.")
            key = matches[0]
        except FetchError:
            raise
        except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
            raise FetchError("Cannot read the credential file securely.") from None
    if not key:
        raise FetchError("Missing EUROPEANA_API_KEY; no request was sent.")
    if len(key) > 512 or any(char.isspace() or ord(char) < 32 for char in key):
        raise FetchError("Invalid credential format; no request was sent.")
    return key


def strings(value):
    """Keep only nonempty strings; absent optional metadata stays absent."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(item.strip() for item in value if isinstance(item, str) and item.strip()))


def safe_http_url(value):
    """Accept public-looking HTTP links, removing credential query parameters.

    This only validates a link's syntax; it does not fetch or verify its availability.
    """
    if not isinstance(value, str) or not value or any(c.isspace() or ord(c) < 32 for c in value):
        return None
    if "\\" in value:
        return None
    try:
        parts = urlsplit(value)
        host = parts.hostname
        if parts.scheme not in {"https", "http"} or not host or parts.username is not None or parts.password is not None:
            return None
        if parts.port is not None and not 1 <= parts.port <= 65535:
            return None
        if host == "localhost" or host.endswith((".localhost", ".local")) or "." not in host:
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            pass
        sensitive = {"wskey", "apikey", "api_key", "key", "access_token", "token"}
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in sensitive]
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))
    except ValueError:
        return None


def normalize_item(item, query, retrieved_at):
    if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip():
        raise FetchError("Invalid record identifier in the upstream response.")
    record_id = item["id"].strip()
    aggregator = None
    for candidate in strings(item.get("guid")):
        safe = safe_http_url(candidate)
        if safe and urlsplit(safe).hostname in {"www.europeana.eu", "europeana.eu"}:
            parts = urlsplit(safe)
            aggregator = urlunsplit(("https", parts.netloc, parts.path, "", ""))
            break
    if not aggregator:
        aggregator = "https://www.europeana.eu/item/" + quote(record_id.lstrip("/"), safe="/")
    source_url = next((safe for value in strings(item.get("edmIsShownAt")) if (safe := safe_http_url(value))), aggregator)
    years = strings(item.get("year"))
    return {
        "id": "europeana:" + record_id,
        "source_id": record_id,
        "source": "Europeana",
        "title": " / ".join(strings(item.get("title"))) or None,
        "description": "\n".join(strings(item.get("dcDescription"))) or None,
        "holding_institution": strings(item.get("dataProvider")),
        "metadata_provider": strings(item.get("provider")),
        "date_display": "; ".join(years) or None,
        "date_kind": "source_supplied",
        "year": years,
        "format": " / ".join(strings(item.get("type"))) or None,
        "language": strings(item.get("dcLanguage")),
        "metadata_language": strings(item.get("language")),
        "source_url": source_url,
        "aggregator_url": aggregator,
        "access_status": "unverified",
        "review_status": "candidate",
        "metadata_rights": CC0,
        "content_rights": strings(item.get("rights")),
        "retrieved_at": retrieved_at,
        "query_used": query,
    }


def normalize_response(payload, query, retrieved_at):
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise FetchError("Europeana reported an unsuccessful response.")
    total = payload.get("totalResults")
    items = payload.get("items")
    if type(total) is not int or total < 0 or not isinstance(items, list) or total < len(items):
        raise FetchError("Invalid result structure in the upstream response.")
    records = [normalize_item(item, query, retrieved_at) for item in items]
    return {
        "source": "Europeana",
        "effective_query": query,
        "fetched_at": retrieved_at,
        "total_results": total,
        "returned_count": len(records),
        "records": records,
    }


def fetch_metadata(query, rows, key):
    if not isinstance(query, str) or not query.strip() or not 1 <= rows <= 100:
        raise FetchError("Query and row limit are invalid; no request was sent.")
    if not key:
        raise FetchError("Missing EUROPEANA_API_KEY; no request was sent.")
    query = query.strip()
    request = Request(
        ENDPOINT + "?" + urlencode({"query": query, "rows": rows, "profile": "rich", "wskey": key}),
        headers={"Accept": "application/json", "User-Agent": "sf-pacific-war-harness-discovery-demo/1.0"},
    )
    try:
        with build_opener(NoRedirect()).open(request, timeout=TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise FetchError("Europeana returned an unexpected HTTP status.")
            body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise FetchError("Europeana response exceeded the size limit.")
        payload = json.loads(body)
    except HTTPError as exc:
        status = exc.code
        exc.close()
        if status in {401, 403}:
            raise FetchError("Europeana rejected the credential or access permission.") from None
        if 300 <= status < 400:
            raise FetchError("Europeana redirected the request; redirect was blocked.") from None
        if status == 429:
            raise FetchError("Europeana rate limit reached; no retry was attempted.") from None
        raise FetchError("Europeana returned an HTTP error; no retry was attempted.") from None
    except (TimeoutError, socket.timeout):
        raise FetchError("Europeana request timed out; no retry was attempted.") from None
    except URLError:
        raise FetchError("Europeana could not be reached; no retry was attempted.") from None
    except (ValueError, UnicodeError):
        raise FetchError("Europeana returned invalid JSON.") from None
    except OSError:
        raise FetchError("Europeana response could not be read.") from None
    result = normalize_response(payload, query, datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    if result["returned_count"] > rows:
        raise FetchError("Europeana returned more records than requested.")
    return result


def serialize_without_key(result, key):
    text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    # Scan the entire normalized document, including upstream strings and URLs.
    variants = {key, quote(key, safe=""), quote_plus(key), json.dumps(key, ensure_ascii=False)[1:-1]}
    if any(secret and secret in text for secret in variants):
        raise FetchError("Credential detected in normalized output; nothing was written.")
    return text


def write_atomic(output, text):
    path = Path(output)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".europeana-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        raise FetchError("Cannot write the normalized metadata file.") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = SafeArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="Europeana search query")
    parser.add_argument("--rows", type=int, default=3, help="1–100 records; default: 3")
    parser.add_argument("--output", required=True, help="Normalized JSON file to write on success")
    parser.add_argument("--env-file", help="Explicit Git-ignored project credential file")
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.rows <= 100 or not args.query.strip():
            raise FetchError("Use a nonempty query and a row limit from 1 to 100.")
        if args.env_file and Path(args.output).resolve() == Path(args.env_file).resolve():
            raise FetchError("Output must not overwrite the credential file.")
        key = load_key(args.env_file)
        result = fetch_metadata(args.query, args.rows, key)
        text = serialize_without_key(result, key)
        write_atomic(args.output, text)
    except FetchError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Request cancelled.", file=sys.stderr)
        return 130
    except Exception:
        # Even unexpected errors must never expose a request URL or upstream body.
        print("Metadata fetch failed; details were suppressed to protect credentials.", file=sys.stderr)
        return 1
    print("Europeana metadata saved: {} records.".format(result["returned_count"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
