#!/usr/bin/env python3
"""Inventory linked CBI reference pages without fetching or copying their media.

Only page titles, link labels, image URL/alt attributes and provenance are saved.
Article bodies, image/PDF bytes and audio/video are never retained or requested.
This is a reference inventory, not an archival identity or copyright verification.
"""

import argparse
from collections import Counter, deque
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser


HOME_URL = "https://cbi-theater.com/menu/cbi_home.html"
HOSTS = {"cbi-theater.com", "www.cbi-theater.com"}
USER_AGENT = "WWIIPacificWarReferenceInventory/1.0 (metadata-only; one request per second)"
ROOT = Path(__file__).resolve().parents[1]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".gif", ".png", ".webp", ".bmp", ".tif", ".tiff", ".svg"}
HTML_EXTENSIONS = {".html", ".htm", ".shtml", ".xhtml", ""}
ARCHIVAL_DOMAINS = {
    "loc.gov", "archives.gov", "archive.org", "europeana.eu", "nationalarchives.gov.uk",
    "iwm.org.uk", "jacar.go.jp", "archives.gov.tw", "si.edu", "dp.la",
    "history.army.mil", "history.navy.mil", "afhistory.af.mil", "digitalcollections.nypl.org",
    "collections.ushmm.org", "catalog.archives.gov", "awm.gov.au", "iwm.org.uk",
}
MENU_CATEGORIES = {
    "FEATURED SITES", "CBI PUBLICATIONS", "YANK - THE ARMY WEEKLY", "POCKET GUIDES",
    "GOVERNMENT BOOKLETS", "REMEMBERING", "MISCELLANEOUS", "CBI VETERAN'S STORIES",
    "CBI VETERAN'S PHOTOS", "HISTORIES", "LEDO ROAD", "CBI PIPELINES", "THE CBI THEATER",
    "A UNIQUE LOOK", "LIFE MAGAZINE", "LIFE PHOTO COLLECTION", "ARTISTIC VIEWS",
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def compact(value, limit=240):
    return re.sub(r"\s+", " ", value or "").strip()[:limit]


def public_url(value, base):
    """Resolve only HTTP(S), without credentials, control bytes or fragments."""
    if not isinstance(value, str) or "\\" in value or re.search(r"[\x00-\x1f\x7f]", value):
        return None
    try:
        parts = urlsplit(urljoin(base, value.strip()))
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            return None
        if parts.port not in {None, 80, 443}:
            return None
        host = parts.hostname.lower()
        if host in HOSTS:
            return urlunsplit(("https", "cbi-theater.com", parts.path or "/", parts.query, ""))
        return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))
    except ValueError:
        return None


def internal_page(url):
    parts = urlsplit(url)
    return (parts.scheme == "https" and parts.hostname == "cbi-theater.com" and not parts.query
            and not parts.username and not parts.password
            and Path(parts.path).suffix.lower() in HTML_EXTENSIONS)


def archive_link(url):
    host = (urlsplit(url).hostname or "").lower()
    return any(host == domain or host.endswith("." + domain) for domain in ARCHIVAL_DOMAINS)


def request_url(url):
    """Encode legacy spaces/non-ASCII for HTTP while keeping inventory keys intact."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc,
                       quote(parts.path, safe="/%:@!$&'()*+,;=-._~"),
                       quote(parts.query, safe="/%?:@!$&'()*+,;=-._~"), ""))


class ReferenceParser(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.title_parts = []
        self.in_title = False
        self.ignored = 0
        self.links = []
        self.images = []
        self.current_link = None
        self.category = None
        self.menu_started = base != HOME_URL

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag in {"script", "style"}:
            self.ignored += 1
        if self.ignored:
            return
        if tag == "title":
            self.in_title = True
        if tag == "base" and attrs.get("href"):
            target = public_url(attrs["href"], self.base)
            if target:
                self.base = target
        # This legacy site often links the real article via an HTML refresh.
        # Resolve the declared URL as data; never execute JavaScript redirects.
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            match = re.search(r"(?:^|;)\s*url\s*=\s*['\"]?([^'\"]+)", attrs.get("content", ""), re.I)
            if match:
                self.add_embedded_page(match.group(1).strip(), "meta_refresh")
        if tag in {"frame", "iframe"} and attrs.get("src"):
            self.add_embedded_page(attrs["src"], tag)
        if tag == "a":
            self.finish_link()
            url = public_url(attrs.get("href", ""), self.base) if attrs.get("href") else None
            self.current_link = {"url": url, "label_parts": [], "image_labels": [], "category": self.category,
                                 "title": compact(attrs.get("title"))} if url else None
        if tag == "img":
            url = public_url(attrs.get("src", ""), self.base) if attrs.get("src") else None
            if url:
                entry = {"url": url, "alt": compact(attrs.get("alt")), "title": compact(attrs.get("title"))}
                self.images.append(entry)
                if self.current_link and entry["alt"]:
                    self.current_link["image_labels"].append(entry["alt"])

    def add_embedded_page(self, value, kind):
        target = public_url(value, self.base)
        if target:
            self.links.append({"url": target, "label": "", "label_from": kind,
                               "category": self.category, "link_type": kind})

    def handle_startendtag(self, tag, attributes):
        self.handle_starttag(tag, attributes)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.ignored = max(0, self.ignored - 1)
        if self.ignored:
            return
        if tag == "title":
            self.in_title = False
        if tag == "a":
            self.finish_link()

    def handle_data(self, data):
        if self.ignored:
            return
        if self.in_title:
            self.title_parts.append(data)
        if self.current_link:
            self.current_link["label_parts"].append(data)
        elif compact(data) == "FEATURED SITES":
            self.menu_started = True
            self.category = "FEATURED SITES"
        elif self.menu_started and compact(data) in MENU_CATEGORIES:
            self.category = compact(data)

    def finish_link(self):
        if self.current_link:
            entry = self.current_link
            text_label = compact(" ".join(entry.pop("label_parts")))
            entry["label"] = text_label or compact(" ".join(entry.pop("image_labels"))) or entry.pop("title", "")
            entry.pop("image_labels", None)
            entry["label_from"] = "text" if text_label else "image_alt_or_title"
            entry.pop("title", None)
            self.links.append(entry)
            self.current_link = None

    def result(self):
        self.finish_link()
        # Repeated navigation and image links do not become separate items.
        unique_links = {}
        for entry in self.links:
            existing = unique_links.get(entry["url"])
            if existing is None or (not existing["label"] and entry["label"]):
                unique_links[entry["url"]] = entry
            elif entry["label_from"] == "text" and existing["label_from"] != "text":
                unique_links[entry["url"]] = entry
        unique_images = {}
        for entry in self.images:
            unique_images.setdefault(entry["url"], entry)
        return {"title": compact(" ".join(self.title_parts), 300),
                "links": list(unique_links.values()), "images": list(unique_images.values()),
                "link_occurrences": len(self.links), "image_occurrences": len(self.images)}


class RequestPacer:
    def __init__(self, delay):
        self.delay = delay
        self.last_request = time.monotonic()

    def wait(self):
        time.sleep(max(0, self.delay - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()


class SameSiteRedirect(HTTPRedirectHandler):
    def __init__(self, robots=None, pacer=None):
        super().__init__()
        self.robots = robots
        self.pacer = pacer

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = public_url(newurl, req.full_url)
        if not target or urlsplit(target).hostname != "cbi-theater.com":
            raise HTTPError(req.full_url, code, "External redirect not followed", headers, fp)
        if urlsplit(target).path != "/robots.txt" and not internal_page(target):
            raise HTTPError(req.full_url, code, "Non-HTML redirect not followed", headers, fp)
        if self.robots is not None and not self.robots.can_fetch(USER_AGENT, target):
            raise HTTPError(req.full_url, code, "Redirect target disallowed by robots.txt", headers, fp)
        if self.pacer is not None:
            self.pacer.wait()
        return super().redirect_request(req, fp, code, msg, headers, request_url(target))


def fetch(url, timeout, max_bytes, robots=None, pacer=None):
    request = Request(request_url(url), headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.8"})
    try:
        with build_opener(SameSiteRedirect(robots, pacer)).open(request, timeout=timeout) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
                return {"status": "not_html", "http_status": response.status, "content_type": content_type}
            payload = response.read(max_bytes + 1)
            if len(payload) > max_bytes:
                return {"status": "size_limit", "http_status": response.status}
            charset = response.headers.get_content_charset() or "utf-8"
            try:
                html = payload.decode(charset, errors="replace")
            except LookupError:
                html = payload.decode("utf-8", errors="replace")
            return {"status": "ok", "http_status": response.status, "final_url": public_url(response.url, url),
                    "content_type": content_type, "html": html, "bytes_read": len(payload)}
    except HTTPError as exc:
        result = {"status": "http_error", "http_status": exc.code, "error": compact(str(exc))}
        exc.close()
        return result
    except (OSError, URLError, ValueError) as exc:
        return {"status": "network_error", "error": compact(str(exc))}


def robots_policy(timeout, max_bytes):
    url = "https://cbi-theater.com/robots.txt"
    result = fetch(url, timeout, max_bytes)
    checked = now()
    policy = RobotFileParser(url)
    if result["status"] == "ok":
        policy.parse(result.pop("html").splitlines())
        state = "read"
    elif result.get("http_status") in {404, 410}:
        policy.parse([])
        state = "not_present"
    else:
        policy.parse(["User-agent: *", "Disallow: /"])
        state = "unavailable_stop"
    return policy, {"url": url, "checked_at": checked, "policy": state, **result}


def menu_items(parsed):
    return [{"url": item["url"], "title": item["label"], "category": ("SITE NAVIGATION" if
             urlsplit(item["url"]).path.startswith(("/menu/", "/links/")) else item["category"]),
             "item_type": "reference_page", "archival_match_status": "not_verified"}
            for item in parsed["links"] if internal_page(item["url"]) and item["url"] != HOME_URL]


def prioritize_content(queue, pages):
    """At each BFS depth, visit declared article targets before directory aliases."""
    declared = {link["url"] for page in pages for link in page.get("links", [])
                if link.get("link_type") in {"meta_refresh", "frame", "iframe"}}
    return deque(sorted(queue, key=lambda item: (item["depth"], item["url"] not in declared)))


def summarize(state):
    pages = state["pages"]
    visited = {page["url"] for page in pages}
    okay = {page["url"] for page in pages if page["status"] == "ok"}
    discovered = {entry["url"] for page in pages for entry in page.get("links", []) if internal_page(entry["url"])}
    discovered.add(HOME_URL)
    asset_map = {}
    image_occurrences = 0
    for page in pages:
        for item in page.get("images", []):
            image_occurrences += 1
            asset = asset_map.setdefault(item["url"], {"url": item["url"], "kind": "image", "alt": item["alt"],
                  "title": item["title"], "referenced_by": [], "access_status": "discovered_not_requested",
                  "archival_match_status": "not_verified"})
            asset["referenced_by"].append(page["url"])
        for link in page.get("links", []):
            path = urlsplit(link["url"]).path
            if not internal_page(link["url"]) and urlsplit(link["url"]).hostname == "cbi-theater.com":
                ext = Path(path).suffix.lower()
                kind = "image" if ext in IMAGE_EXTENSIONS else "document" if ext == ".pdf" else "other_link"
                asset = asset_map.setdefault(link["url"], {"url": link["url"], "kind": kind, "alt": "", "title": link["label"],
                      "referenced_by": [], "access_status": "discovered_not_requested", "archival_match_status": "not_verified"})
                if page["url"] not in asset["referenced_by"]:
                    asset["referenced_by"].append(page["url"])
    unvisited = sorted(discovered - visited)
    state["updated_at"] = now()
    state["assets"] = list(asset_map.values())
    state["unvisited_urls"] = unvisited
    state["summary"] = {
        "menu_items": len(state["menu_items"]), "menu_pages_attempted": sum(item["url"] in visited for item in state["menu_items"]),
        "menu_pages_successful": sum(item["url"] in okay for item in state["menu_items"]),
        "pages_attempted": len(pages), "pages_successful": len(okay),
        "page_status_counts": dict(Counter(page["status"] for page in pages)), "discovered_page_urls": len(discovered),
        "unvisited_pages": len(unvisited), "unique_image_urls": sum(asset["kind"] == "image" for asset in asset_map.values()),
        "unique_document_urls": sum(asset["kind"] == "document" for asset in asset_map.values()),
        "embedded_image_references": image_occurrences,
        "reused_asset_urls": sum(len(asset["referenced_by"]) > 1 for asset in asset_map.values()),
        "external_archival_links": sum(len(page.get("external_archival_links", [])) for page in pages),
        "media_files_requested": 0, "verified_archival_item_matches": 0,
        "crawl_complete": not unvisited and state["run_status"] == "complete" and len(okay) == len(pages),
    }
    return state


def save(state, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    summarize(state)
    for filename, content in [("inventory.json", state), ("menu.json", {
        "source_url": HOME_URL, "fetched_at": state.get("menu_fetched_at"),
        "scope": "Distinct internal HTML-page links from the supplied CBI homepage; reference only.",
        "items": state["menu_items"],
    })]:
        destination = output_dir / filename
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(destination)
    summary = state["summary"]
    lines = ["# CBI Theater 参考网站盘点 / Reference inventory", "",
        f"来源：[China–Burma–India Theater]({HOME_URL})。更新时间：{state['updated_at']}。", "",
        "CBI Theater 仅作为查找线索。此工具只请求 HTML 与 robots.txt；不请求、下载或显示该站照片、扫描件、PDF 或其他媒体。",
        "保存的图片 URL、alt/title 和链接文字仅用于溯源；页面正文不保存。图片数量可能包括图标、装饰图片和重复扫描的不同 URL，不能视为已识别的历史物件数量。",
        "照片/文章/实物与官方档案的逐件对应尚未核实；本盘点不能证明来源相同、开放授权或可重用。Demo 预览只能使用另外实际获取的档案平台记录。", "",
        "| 指标 / Metric | 数量 / Count |", "| --- | ---: |",
        f"| 首页独立内部页面链接 | {summary['menu_items']} |",
        f"| 首页链接已请求 / 成功 | {summary['menu_pages_attempted']} / {summary['menu_pages_successful']} |",
        f"| 全部页面已请求 / 成功 | {summary['pages_attempted']} / {summary['pages_successful']} |",
        f"| 已发现页面 URL / 尚未请求 | {summary['discovered_page_urls']} / {summary['unvisited_pages']} |",
        f"| 独立图片 URL（未请求媒体） | {summary['unique_image_urls']} |",
        f"| PDF URL（未请求文件） | {summary['unique_document_urls']} |",
        f"| 多个页面引用的相同媒体 URL | {summary['reused_asset_urls']} |",
        f"| 对外档案平台链接出现次数 | {summary['external_archival_links']} |",
        "| 已验证的逐件档案对应 | 0 |", "",
        f"运行状态：`{state['run_status']}`。完整抓取：`{str(summary['crawl_complete']).lower()}`。",
        f"本次限制：最多 {state['config']['max_pages']} 个页面、深度 {state['config']['max_depth']}、请求间隔至少 {state['config']['delay']} 秒。",
        "若达到限制、网络失败或中断，`inventory.json` 的 `unvisited_urls`、`frontier` 和各页面 `status` 保留缺口。失败页面不会在恢复抓取时被自动重试。", "",
        "robots.txt：`" + state["robots"]["policy"] + "`（HTTP " + str(state["robots"].get("http_status", "unknown")) + "）。404 表示未提供规则，不代表版权许可。", "",
        "## 重现与继续", "", "```bash", "cd /Users/jingxugao/Documents/sf-pacific-war-harness/step1-discovery",
        "python3 tools/inventory_cbi.py --max-pages 1200 --max-depth 6 --delay 1",
        "# 继续已有队列（例如扩大页面上限）", "python3 tools/inventory_cbi.py --resume --max-pages 3000 --max-depth 6 --delay 1",
        "python3 -m unittest discover -s tests -p 'test_inventory_cbi.py'", "```", "",
        "当前包含 14 项离线单元测试，覆盖链接解析、HTML 跳转、robots 限制、媒体排除、请求限速及中断后继续。", "",
        "下一步：继续未请求 HTML 页面；按题名、人物、日期与官方档案 ID 逐项比对；将候选、确认和无法确认分开；在档案平台授权允许时才使用其官方预览。", "",
        "数据结构：`menu.json` 为首页目录；`inventory.json` 的 `pages` 为页面访问状态/链接/图片 URL，`assets` 为去重媒体引用，`frontier` 为可恢复队列。所有 URL 只是线索，不能据此声称媒体可访问。", ""]
    (output_dir / "coverage.md").write_text("\n".join(lines), encoding="utf-8")


def crawl(args):
    output = args.output_dir
    if args.resume:
        state = json.loads((output / "inventory.json").read_text(encoding="utf-8"))
        queue = deque(state["frontier"])
    else:
        state = {"schema_version": 1, "source_url": HOME_URL, "started_at": now(), "pages": [], "menu_items": [],
                 "limitations": ["Reference metadata only; no media requested or embedded in demo.",
                                 "No individual item, author, archive identity or rights verification.",
                                 "Only reachable same-site HTML links; query-string URLs and external sites excluded."]}
        queue = deque([{"url": HOME_URL, "depth": 0, "discovered_from": None}])
    state["config"] = {"max_pages": args.max_pages, "max_depth": args.max_depth, "delay": args.delay,
                       "timeout": args.timeout, "max_bytes": args.max_bytes}
    state["limitations"] = [
        "Reference metadata only; no media requested or embedded in demo.",
        "No individual item, author, archive identity or rights verification.",
        "Only reachable same-site HTML links; query-string URLs and external sites excluded.",
        "Image references come from img/src and linked media URLs, not CSS backgrounds, JavaScript or OCR.",
        "HTML refresh and frame URLs are followed as declared links; JavaScript is never executed.",
    ]
    policy, state["robots"] = robots_policy(args.timeout, args.max_bytes)
    state["run_status"] = "running"
    seen = {page["url"] for page in state["pages"]}
    queued = {item["url"] for item in queue} | seen
    prioritized = False
    if state["robots"]["policy"] == "unavailable_stop":
        state["run_status"] = "robots_unavailable"
        state["frontier"] = list(queue)
        save(state, output)
        return 2
    delay = max(args.delay, policy.crawl_delay(USER_AGENT) or 0, policy.crawl_delay("*") or 0)
    pacer = RequestPacer(delay)
    try:
        while queue and len(state["pages"]) < args.max_pages:
            if not prioritized and state["menu_items"] and all(item["url"] in seen for item in state["menu_items"]):
                queue = prioritize_content(queue, state["pages"])
                prioritized = True
            pending = queue.popleft()
            url = pending["url"]
            if url in seen:
                continue
            if pending["depth"] > args.max_depth:
                queue.appendleft(pending)
                state["run_status"] = "depth_limit"
                break
            pacer.wait()
            if policy.can_fetch(USER_AGENT, url):
                result = fetch(url, args.timeout, args.max_bytes, policy, pacer)
            else:
                result = {"status": "robots_disallowed"}
            parsed = None
            if result["status"] == "ok":
                parser = ReferenceParser(result.get("final_url") or url)
                parser.feed(result.pop("html"))
                parsed = parser.result()
            page = {**pending, "fetched_at": now(), **result, **(parsed or {})}
            page["external_archival_links"] = [link for link in page.get("links", []) if archive_link(link["url"])]
            state["pages"].append(page)
            seen.add(url)
            if url == HOME_URL and parsed:
                state["menu_items"] = menu_items(parsed)
                state["menu_fetched_at"] = page["fetched_at"]
            if parsed:
                for link in parsed["links"]:
                    target = link["url"]
                    if internal_page(target) and target not in queued:
                        queue.append({"url": target, "depth": pending["depth"] + 1, "discovered_from": url})
                        queued.add(target)
            state["frontier"] = list(queue)
            if len(state["pages"]) == 1 or len(state["pages"]) % 25 == 0:
                save(state, output)
                print(json.dumps({"pages_attempted": len(state["pages"]), "frontier": len(queue),
                                  "menu_items": len(state["menu_items"]), "last_status": page["status"]}), flush=True)
        if state["run_status"] == "running":
            state["run_status"] = "page_limit" if queue else "complete"
    except KeyboardInterrupt:
        state["run_status"] = "interrupted"
        if "pending" in locals() and pending["url"] not in seen:
            queue.appendleft(pending)
    state["frontier"] = list(queue)
    save(state, output)
    print(json.dumps(state["summary"], ensure_ascii=False), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "cbi")
    parser.add_argument("--max-pages", type=int, default=1200)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--max-bytes", type=int, default=2_000_000)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.max_pages < 1 or args.max_depth < 0 or args.delay < 1 or args.timeout <= 0 or args.max_bytes < 1024:
        parser.error("Use positive limits and at least one second between requests.")
    raise SystemExit(crawl(args))


if __name__ == "__main__":
    main()
