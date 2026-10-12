"""Verify selected public mainland archival exhibit pages, without API claims."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SOURCES = {
    "shac": ("mainland-shac.json", "www.saac.gov.cn"),
    "yunnan": ("mainland-yunnan.json", "www.saac.gov.cn"),
}
MAX_BYTES = 1024 * 1024
TIMEOUT = 20


class CheckError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CheckError("redirect_blocked", "Redirects are not followed.")


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.titles = []
        self.hidden = 0
        self.in_title = False
        self.password_input = False
        self.html_tag = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"html", "body"}:
            self.html_tag = True
        if tag in {"script", "style"}:
            self.hidden += 1
        if not self.hidden:
            resource = attrs.get("src") if tag == "img" else attrs.get("href") if tag == "a" else None
            if resource:
                self.parts.append(resource)
        if tag == "title":
            self.in_title = True
        if tag == "input" and attrs.get("type", "").lower() == "password":
            self.password_input = True

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)
            if self.in_title:
                self.titles.append(data)


def normalized(text):
    return " ".join(str(text).split()).casefold()


def validate_url(source, url):
    try:
        parsed = urlsplit(url)
        valid = (source in SOURCES and parsed.scheme == "https"
                 and parsed.hostname == SOURCES[source][1]
                 and parsed.port in {None, 443} and not parsed.username
                 and not parsed.password and not parsed.fragment
                 and parsed.path.lower().endswith((".htm", ".html", ".shtml")))
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise CheckError("invalid_url", "Only selected HTTPS HTML pages on the exact official source host are allowed.")


def fetch_page(source, url, opener=None):
    validate_url(source, url)
    request = Request(url, headers={"Accept": "text/html, application/xhtml+xml", "User-Agent": "WWII-Pacific-War-discovery/1.0"})
    with (opener or build_opener(NoRedirects())).open(request, timeout=TIMEOUT) as response:
        status = response.status
        if response.geturl() != url or 300 <= status < 400:
            raise CheckError("redirect_blocked", "Redirects are not followed.")
        if status != 200:
            raise CheckError("http_error", "The page did not return HTTP 200.")
        content_type = response.headers.get("Content-Type", "")
        if content_type.split(";", 1)[0].strip().lower() not in {"text/html", "application/xhtml+xml"}:
            raise CheckError("invalid_content", "The response is not HTML.")
        content_length = response.headers.get("Content-Length")
        if content_length and content_length.isdigit() and int(content_length) > MAX_BYTES:
            raise CheckError("response_too_large", "HTML exceeds the 1 MiB limit.")
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise CheckError("response_too_large", "HTML exceeds the 1 MiB limit.")
    encoding_match = re.search(r"charset\s*=\s*[\"']?([\w-]+)", content_type, re.I)
    if encoding_match is None:
        encoding_match = re.search(r"charset\s*=\s*[\"']?([\w-]+)", body[:4096].decode("ascii", errors="ignore"), re.I)
    encoding = encoding_match.group(1) if encoding_match else "utf-8"
    try:
        page = body.decode(encoding)
    except (UnicodeError, LookupError):
        raise CheckError("invalid_content", "HTML character encoding could not be decoded.") from None
    parsed = PageText()
    parsed.feed(page)
    title = normalized(" ".join(parsed.titles))
    denied = r"access denied|forbidden|captcha|just a moment|security check|登录|登陆|访问受限|验证码|安全验证"
    if parsed.password_input or re.search(denied, title):
        raise CheckError("access_blocked", "A login, access restriction or verification page was returned.")
    if not parsed.html_tag:
        raise CheckError("invalid_content", "The response has no HTML document structure.")
    return normalized(" ".join(parsed.parts)), len(body)


def load_records(source="all", data_dir=DATA_DIR):
    records = []
    for key in SOURCES if source == "all" else [source]:
        payload = json.loads((Path(data_dir) / SOURCES[key][0]).read_text(encoding="utf-8"))
        if not isinstance(payload.get("records"), list):
            raise ValueError("Each source file must contain a records list.")
        records.extend((key, record) for record in payload["records"])
    return records


def check_records(records, *, live=False, query=None, opener=None):
    results = []
    cache = {}
    for source, record in records:
        search_text = json.dumps({key: record.get(key) for key in
                                  ("id", "title", "archival_context", "subjects")}, ensure_ascii=False)
        if query and normalized(query) not in normalized(search_text):
            continue
        result = {"source": source, "id": record.get("id"), "title": record.get("title"),
                  "source_url": record.get("source_url"), "credential": "not_required",
                  "request_sent": False, "status": "ready"}
        try:
            url = record.get("source_url")
            validate_url(source, url)
            markers = record.get("page_markers", [record.get("title")])
            if not isinstance(markers, list) or not markers or any(not isinstance(m, str) or not m.strip() for m in markers):
                raise CheckError("invalid_record", "Each record needs nonempty page markers or a title.")
            if live:
                if url not in cache:
                    result["request_sent"] = True
                    try:
                        cache[url] = fetch_page(source, url, opener=opener)
                    except Exception as exc:
                        cache[url] = exc
                response = cache[url]
                if isinstance(response, Exception):
                    raise response
                page, byte_count = response
                if any(normalized(marker) not in page for marker in markers):
                    raise CheckError("content_mismatch", "Expected archival content was not found; HTTP 200 alone is not sufficient.")
                result.update(status="ok", http_status=200, bytes_read=byte_count,
                              message="Selected archival exhibit HTML and all content markers verified.")
        except CheckError as exc:
            result.update(status=exc.status, message=str(exc))
        except HTTPError as exc:
            result.update(status="redirect_blocked" if 300 <= exc.code < 400 else "access_blocked" if exc.code in {401, 403} else "http_error", http_status=exc.code)
            if exc.fp is not None:
                exc.close()
        except (TimeoutError, socket.timeout):
            result["status"] = "timeout"
        except URLError as exc:
            result["status"] = "timeout" if isinstance(exc.reason, (TimeoutError, socket.timeout)) else "network_error"
        except OSError:
            result["status"] = "network_error"
        results.append(result)
    return {"mode": "selected_html_pages", "live": live, "query": query,
            "query_scope": "Local selection over saved titles, IDs, archival context and subjects; no remote catalogue query.",
            "checked_at": datetime.now(timezone.utc).isoformat() if live else None,
            "selected_count": len(results), "summary": dict(Counter(r["status"] for r in results)), "results": results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("all", *SOURCES), default="all")
    parser.add_argument("--live", action="store_true", help="Fetch selected HTML pages once; never fetch images/PDFs.")
    parser.add_argument("--query", help="Select saved records locally; this is not a remote archive search.")
    parser.add_argument("--format", choices=("json", "table"), default="json")
    args = parser.parse_args(argv)
    try:
        report = check_records(load_records(args.source), live=args.live, query=args.query)
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"status": "invalid_data", "message": "Could not load selected source records.", "live": args.live}))
        return 1
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(report["query_scope"])
        print("SOURCE\tSTATUS\tTITLE")
        for record in report["results"]:
            print("\t".join(str(record.get(key, "")) for key in ("source", "status", "title")))
        print(f"Selected: {report['selected_count']}; requests: {sum(r['request_sent'] for r in report['results'])}")
    return int(any(r["status"] not in {"ready", "ok"} for r in report["results"]))


if __name__ == "__main__":
    raise SystemExit(main())
