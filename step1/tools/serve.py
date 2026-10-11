#!/usr/bin/env python3
"""Build public data and serve only site/ on the local loopback interface."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

# Keep direct CLI execution and import-based tests equally predictable.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_site_data import BuildError, PROJECT_ROOT, write_catalog


def make_handler(site_directory):
    site = Path(site_directory)
    if site.is_symlink():
        raise ValueError("Site directory must not be a symbolic link.")
    site = site.resolve(strict=True)

    class SiteHandler(SimpleHTTPRequestHandler):
        def safe_target(self, request_path):
            try:
                value = urlsplit(request_path).path
                for _ in range(4):
                    decoded = unquote(value, errors="strict")
                    if decoded == value:
                        break
                    value = decoded
                if "%" in value or "\\" in value or any(ord(c) < 32 for c in value):
                    return None
                parts = [part for part in value.split("/") if part]
                if any(part.startswith(".") for part in parts):
                    return None
                target = site
                for part in parts:
                    target = target / part
                    if target.is_symlink():
                        return None
                target.resolve().relative_to(site)
                return target
            except (ValueError, UnicodeError, OSError, RuntimeError):
                return None

        def send_head(self):
            target = self.safe_target(self.path)
            if target is None:
                self.send_error(403, "Path is not public.")
                return None
            # Check directory index files too: the base class follows them.
            if target.is_dir():
                for filename in ("index.html", "index.htm"):
                    if (target / filename).is_symlink():
                        self.send_error(403, "Path is not public.")
                        return None
            return super().send_head()

        def translate_path(self, path):
            target = self.safe_target(path)
            # send_head rejects this case before reaching the base implementation.
            return str(target) if target is not None else str(site / "__not_public__")

        def list_directory(self, path):
            self.send_error(403, "Directory listing is disabled.")
            return None

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            super().end_headers()

    return partial(SiteHandler, directory=str(site))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    try:
        catalog = write_catalog()
        server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(PROJECT_ROOT / "site"))
    except (BuildError, OSError, ValueError) as exc:
        print(str(exc) if isinstance(exc, BuildError) else "Could not start local server; check the site directory and port.")
        return 1
    print("Serving " + str(len(catalog["records"])) + " public records at http://127.0.0.1:" + str(args.port), flush=True)
    print("Press Ctrl+C to stop. Only site/ is exposed.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
