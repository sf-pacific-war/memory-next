"""Exercise the relocated legacy demo using an isolated, freshly seeded copy.

Run from the repository root with Python 3.9–3.12:
    python3 -m unittest discover -s tests -v

The legacy app uses cgi, which was removed from Python 3.13. These tests never
start the user's working app or read its runtime data, and contact localhost only.
"""

from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Step0LayoutSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix="memory-step0-smoke-")
        cls.addClassCleanup(cls.scratch.cleanup)
        sandbox = Path(cls.scratch.name)
        app_dir = sandbox / "step0"
        shutil.copytree(
            ROOT / "step0",
            app_dir,
            ignore=shutil.ignore_patterns(
                "data", "storage", "backups", "__pycache__", "*.pyc", ".env*", ".git"
            ),
        )
        # The app should create all of these underneath its own copied location.
        for directory in ("data", "storage", "backups"):
            if (app_dir / directory).exists():
                raise AssertionError("Runtime data must not be copied into the test")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
            reservation.bind(("127.0.0.1", 0))
            cls.port = reservation.getsockname()[1]

        cls.log = tempfile.TemporaryFile(mode="w+b")
        cls.addClassCleanup(cls.log.close)
        environment = dict(os.environ, ARCHIVE_PORT=str(cls.port), PYTHONUNBUFFERED="1")
        cls.process = subprocess.Popen(
            [sys.executable, str(app_dir / "app.py")],
            # Starting outside step0 catches accidental reliance on the shell cwd.
            cwd=sandbox,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=cls.log,
            stderr=subprocess.STDOUT,
        )
        cls.addClassCleanup(cls.stop_server)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if cls.process.poll() is not None:
                cls.fail_startup("Step 0 exited during startup")
            try:
                status, _, body = cls.request("/api/me")
                if status == 200 and json.loads(body) == {
                    "authenticated": False, "user": None
                }:
                    break
            except (OSError, http.client.HTTPException):
                pass
            time.sleep(0.05)
        else:
            cls.fail_startup("Step 0 did not become ready within 20 seconds")
        if not (app_dir / "data" / "archive.db").is_file():
            raise AssertionError("The app did not create its database inside step0")
        if (sandbox / "data").exists():
            raise AssertionError("The app created runtime data in the shell cwd")

    @classmethod
    def stop_server(cls):
        """Class cleanup runs even when startup or an assertion fails."""
        try:
            if cls.process.poll() is None:
                cls.process.terminate()
            cls.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.process.kill()
        finally:
            cls.process.wait()

    @classmethod
    def fail_startup(cls, message):
        cls.log.flush()
        cls.log.seek(0)
        output = cls.log.read().decode("utf-8", errors="replace")
        raise AssertionError(f"{message}\n{output}")

    @classmethod
    def request(cls, path, *, method="GET", payload=None, cookie=None):
        # HTTPConnection uses this exact loopback address, without proxy settings
        # or redirect following that could accidentally make an external request.
        connection = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=3)
        headers = {}
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if cookie:
            headers["Cookie"] = cookie
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def login(self, role):
        status, headers, body = self.request(
            "/api/login", method="POST", payload={"username": role, "password": role}
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["user"]["role"], role)
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        return headers["Set-Cookie"].split(";", 1)[0]

    def get_json(self, path, *, cookie=None, status=200):
        actual_status, headers, body = self.request(path, cookie=cookie)
        self.assertEqual(actual_status, status)
        self.assertIn("application/json", headers["Content-Type"])
        return json.loads(body)

    def test_home_and_static_assets_resolve_after_move(self):
        for path, content_type in (
            ("/", "text/html"),
            ("/static/styles.css", "text/css"),
            ("/static/app.js", "javascript"),
        ):
            with self.subTest(path=path):
                status, headers, body = self.request(path)
                self.assertEqual(status, 200)
                self.assertIn(content_type, headers["Content-Type"])
                self.assertGreater(len(body), 100)
        self.assertIn(b"/static/styles.css", self.request("/")[2])

    def test_anonymous_session_and_catalog_permissions(self):
        self.assertEqual(
            self.get_json("/api/me"), {"authenticated": False, "user": None}
        )
        self.assertIn("error", self.get_json("/api/objects", status=401))

    def test_both_demo_accounts_have_persistent_sessions(self):
        for role in ("admin", "viewer"):
            with self.subTest(role=role):
                session = self.get_json("/api/me", cookie=self.login(role))
                self.assertTrue(session["authenticated"])
                self.assertEqual(session["user"]["username"], role)
                self.assertEqual(session["user"]["role"], role)

    def test_viewer_can_search_and_read_seeded_catalog(self):
        cookie = self.login("viewer")
        found = self.get_json("/api/objects?query=MNA-000123", cookie=cookie)
        self.assertEqual(found["count"], 1)
        record = found["objects"][0]
        self.assertEqual(record["permanent_id"], "MNA-000123")
        self.assertIn("Manila", record["title"])
        detail = self.get_json("/api/objects/MNA-000123", cookie=cookie)["object"]
        self.assertEqual(detail["id"], record["id"])
        empty = self.get_json("/api/objects?query=smoke-no-such-record-847362", cookie=cookie)
        self.assertEqual(empty["count"], 0)
        self.assertEqual(empty["objects"], [])

    def test_viewer_response_omits_internal_fields(self):
        record = self.get_json(
            "/api/objects/MNA-000123", cookie=self.login("viewer")
        )["object"]
        for field in (
            "storage_location_id", "storage_location_path", "internal_note",
            "preservation_note", "metadata_json",
        ):
            self.assertNotIn(field, record)
        self.assertTrue(record["media"])
        for media in record["media"]:
            for field in ("original_filename", "local_path", "checksum_sha256"):
                self.assertNotIn(field, media)

    def test_viewer_cannot_use_admin_routes_or_create_objects(self):
        cookie = self.login("viewer")
        before = self.get_json("/api/objects", cookie=cookie)["count"]
        for path in ("/api/storage-locations", "/api/audit", "/api/admin/intake"):
            with self.subTest(path=path):
                self.assertIn("error", self.get_json(path, cookie=cookie, status=403))
        status, _, body = self.request(
            "/api/objects", method="POST", payload={}, cookie=cookie
        )
        self.assertEqual(status, 403)
        self.assertIn("error", json.loads(body))
        self.assertEqual(self.get_json("/api/objects", cookie=cookie)["count"], before)

    def test_admin_can_read_admin_metadata(self):
        cookie = self.login("admin")
        self.assertTrue(self.get_json("/api/storage-locations", cookie=cookie)["locations"])
        self.assertIsInstance(self.get_json("/api/audit", cookie=cookie)["logs"], list)
        self.assertIsInstance(self.get_json("/api/admin/intake", cookie=cookie)["items"], list)
        record = self.get_json("/api/objects/MNA-000123", cookie=cookie)["object"]
        self.assertIn("storage_location_path", record)
        self.assertIn("internal_note", record)


if __name__ == "__main__":
    unittest.main()
