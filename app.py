#!/usr/bin/env python3
"""Local Archive Collection System demo.

The app intentionally uses only Python standard-library modules so the demo can
run on a clean machine without npm, pip, Docker, or cloud credentials.
"""

from __future__ import annotations

import cgi
import errno
import hashlib
import http.cookies
import json
import mimetypes
import os
import secrets
import shutil
import sqlite3
import sys
import time
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "archive.db"
STORAGE_DIR = ROOT / "storage" / "archive-master"
INTAKE_DIR = ROOT / "storage" / "intake"
BACKUP_DIR = ROOT / "backups"

APP_NAME = "Archive Collection System"
SESSION_COOKIE = "archive_session"

EXTENDED_OBJECT_FIELDS: List[Tuple[str, str]] = [
    ("alternative_title", "TEXT DEFAULT ''"),
    ("publisher", "TEXT DEFAULT ''"),
    ("contributors", "TEXT DEFAULT ''"),
    ("source", "TEXT DEFAULT ''"),
    ("relation", "TEXT DEFAULT ''"),
    ("coverage_spatial", "TEXT DEFAULT ''"),
    ("coverage_temporal", "TEXT DEFAULT ''"),
    ("physical_description", "TEXT DEFAULT ''"),
    ("extent", "TEXT DEFAULT ''"),
    ("medium", "TEXT DEFAULT ''"),
    ("citation", "TEXT DEFAULT ''"),
    ("external_identifier", "TEXT DEFAULT ''"),
    ("ark", "TEXT DEFAULT ''"),
    ("item_url", "TEXT DEFAULT ''"),
    ("thumbnail_url", "TEXT DEFAULT ''"),
    ("iiif_manifest_url", "TEXT DEFAULT ''"),
    ("license_uri", "TEXT DEFAULT ''"),
    ("access_rights", "TEXT DEFAULT ''"),
    ("primary_source", "INTEGER DEFAULT 1"),
    ("resource_type", "TEXT DEFAULT ''"),
    ("genre_form", "TEXT DEFAULT ''"),
    ("series_title", "TEXT DEFAULT ''"),
    ("subcollection", "TEXT DEFAULT ''"),
    ("theater", "TEXT DEFAULT ''"),
    ("campaign", "TEXT DEFAULT ''"),
    ("battle", "TEXT DEFAULT ''"),
    ("military_unit", "TEXT DEFAULT ''"),
    ("vessel_aircraft", "TEXT DEFAULT ''"),
    ("modern_country", "TEXT DEFAULT ''"),
    ("wartime_jurisdiction", "TEXT DEFAULT ''"),
    ("subject_source", "TEXT DEFAULT ''"),
    ("metadata_profile", "TEXT DEFAULT ''"),
    ("display_note", "TEXT DEFAULT ''"),
    ("internal_note", "TEXT DEFAULT ''"),
    ("preservation_note", "TEXT DEFAULT ''"),
    ("metadata_json", "TEXT DEFAULT ''"),
    ("formal_test_data", "INTEGER DEFAULT 0"),
]

EXTENDED_FIELD_NAMES = [field for field, _ in EXTENDED_OBJECT_FIELDS]
BOOLEAN_OBJECT_FIELDS = {"primary_source", "formal_test_data"}
VIEWER_HIDDEN_OBJECT_FIELDS = {
    "storage_location_id",
    "storage_location_path",
    "internal_note",
    "preservation_note",
    "metadata_json",
}
VIEWER_HIDDEN_MEDIA_FIELDS = {"original_filename", "local_path", "checksum_sha256"}
VIEWER_HIDDEN_SEARCH_FIELDS = {"internal_note", "preservation_note", "metadata_json"}


def is_admin_user(user: Optional[Dict[str, Any]]) -> bool:
    return bool(user and user.get("role") == "admin")


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    INTAKE_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def password_hash(password: str) -> str:
    return hashlib.sha256(("archive-demo:" + password).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_filename(value: str) -> str:
    keep = []
    for char in value.strip().replace(" ", "_"):
        if char.isalnum() or char in "._-":
            keep.append(char)
    name = "".join(keep).strip("._")
    return name or "file"


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def object_field_value(field: str, data: Dict[str, Any]) -> Any:
    if field in BOOLEAN_OBJECT_FIELDS:
        return 1 if truthy(data.get(field)) else 0
    if field == "metadata_json":
        value = clean_text(data.get(field))
        if not value:
            return ""
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        return json.dumps(parsed, ensure_ascii=True, sort_keys=True)
    return clean_text(data.get(field))


def init_db() -> None:
    ensure_dirs()
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              role TEXT NOT NULL CHECK(role IN ('admin', 'viewer')),
              display_name TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
              token TEXT PRIMARY KEY,
              user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              created_at TEXT NOT NULL,
              expires_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS collections (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              description TEXT DEFAULT '',
              parent_id INTEGER REFERENCES collections(id)
            );

            CREATE TABLE IF NOT EXISTS taxonomy_terms (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              vocabulary TEXT NOT NULL,
              term TEXT NOT NULL,
              parent_id INTEGER REFERENCES taxonomy_terms(id),
              UNIQUE(vocabulary, term)
            );

            CREATE TABLE IF NOT EXISTS authorities (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              type TEXT NOT NULL CHECK(type IN ('Person', 'Organization', 'Place', 'Event')),
              name TEXT NOT NULL,
              description TEXT DEFAULT '',
              aliases TEXT DEFAULT '',
              external_uri TEXT DEFAULT '',
              UNIQUE(type, name)
            );

            CREATE TABLE IF NOT EXISTS storage_locations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              location_type TEXT NOT NULL,
              code TEXT DEFAULT '',
              parent_id INTEGER REFERENCES storage_locations(id)
            );

            CREATE TABLE IF NOT EXISTS objects (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              permanent_id TEXT NOT NULL UNIQUE,
              title TEXT NOT NULL,
              description TEXT DEFAULT '',
              object_type TEXT NOT NULL,
              date_label TEXT DEFAULT '',
              date_start INTEGER,
              date_end INTEGER,
              language TEXT DEFAULT '',
              rights TEXT DEFAULT '',
              provenance TEXT DEFAULT '',
              condition TEXT DEFAULT '',
              digitization_status TEXT DEFAULT '',
              collection_id INTEGER REFERENCES collections(id),
              storage_location_id INTEGER REFERENCES storage_locations(id),
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS object_authorities (
              object_id INTEGER NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
              authority_id INTEGER NOT NULL REFERENCES authorities(id) ON DELETE CASCADE,
              role TEXT NOT NULL,
              PRIMARY KEY(object_id, authority_id, role)
            );

            CREATE TABLE IF NOT EXISTS object_terms (
              object_id INTEGER NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
              term_id INTEGER NOT NULL REFERENCES taxonomy_terms(id) ON DELETE CASCADE,
              PRIMARY KEY(object_id, term_id)
            );

            CREATE TABLE IF NOT EXISTS digital_media (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              object_id INTEGER NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
              filename TEXT NOT NULL,
              original_filename TEXT NOT NULL,
              media_type TEXT DEFAULT '',
              derivative_type TEXT NOT NULL,
              storage_provider TEXT NOT NULL CHECK(storage_provider IN ('local', 'google_drive_demo')),
              local_path TEXT DEFAULT '',
              google_drive_url TEXT DEFAULT '',
              checksum_sha256 TEXT DEFAULT '',
              size_bytes INTEGER DEFAULT 0,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS movements (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              object_id INTEGER NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
              from_location_id INTEGER REFERENCES storage_locations(id),
              to_location_id INTEGER REFERENCES storage_locations(id),
              moved_at TEXT NOT NULL,
              note TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              actor TEXT NOT NULL,
              action TEXT NOT NULL,
              entity_type TEXT NOT NULL,
              entity_id TEXT NOT NULL,
              details TEXT DEFAULT '',
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS intake_items (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              status TEXT NOT NULL CHECK(status IN ('needs_review', 'submitted', 'rejected', 'error')),
              filename TEXT NOT NULL,
              original_filename TEXT NOT NULL,
              media_type TEXT DEFAULT '',
              local_path TEXT NOT NULL,
              checksum_sha256 TEXT DEFAULT '',
              size_bytes INTEGER DEFAULT 0,
              suggested_json TEXT NOT NULL,
              edited_json TEXT NOT NULL,
              submitted_object_id INTEGER REFERENCES objects(id),
              error_message TEXT DEFAULT '',
              reject_reason TEXT DEFAULT '',
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              submitted_at TEXT DEFAULT ''
            );
            """
        )
        migrate_schema(conn)
        seed(conn)


def migrate_schema(conn: sqlite3.Connection) -> None:
    existing = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(objects)").fetchall()
    }
    for field, definition in EXTENDED_OBJECT_FIELDS:
        if field not in existing:
            conn.execute(f"ALTER TABLE objects ADD COLUMN {field} {definition}")


def get_or_create(
    conn: sqlite3.Connection,
    table: str,
    lookup: Dict[str, Any],
    values: Optional[Dict[str, Any]] = None,
) -> int:
    clauses = []
    params = []
    for key, value in lookup.items():
        if value is None:
            clauses.append(f"{key} IS NULL")
        else:
            clauses.append(f"{key}=?")
            params.append(value)
    where = " AND ".join(clauses)
    row = conn.execute(f"SELECT id FROM {table} WHERE {where}", params).fetchone()
    if row:
        return int(row["id"])
    data = dict(lookup)
    if values:
        data.update(values)
    keys = list(data.keys())
    placeholders = ", ".join("?" for _ in keys)
    conn.execute(
        f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({placeholders})",
        [data[key] for key in keys],
    )
    return int(conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])


def seed(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"] == 0:
        conn.executemany(
            "INSERT INTO users (username, password_hash, role, display_name) VALUES (?, ?, ?, ?)",
            [
                ("admin", password_hash("admin"), "admin", "Archive Admin"),
                ("viewer", password_hash("viewer"), "viewer", "Read-only Viewer"),
            ],
        )

    seed_reference_taxonomy(conn)

    if conn.execute("SELECT COUNT(*) AS count FROM objects").fetchone()["count"] > 0:
        seed_formal_test_data(conn)
        return

    pacific_collection = get_or_create(
        conn,
        "collections",
        {"name": "Pacific War Collection"},
        {"description": "Materials documenting Pacific Theater people, places, events, and collections."},
    )
    manila_collection = get_or_create(
        conn,
        "collections",
        {"name": "Battle of Manila Field Materials"},
        {"description": "Photographs, maps, and field records associated with Manila in 1945.", "parent_id": pacific_collection},
    )

    vocab_terms = [
        ("Object Type", "Photograph", None),
        ("Object Type", "Map", None),
        ("Object Type", "Letter", None),
        ("Subject", "WWII", None),
        ("Subject", "Pacific Theater", None),
        ("Subject", "Civilian Experience", None),
        ("Historical Period", "1941-1945", None),
        ("Language", "English", None),
        ("Language", "Japanese", None),
        ("Rights", "Public Domain", None),
        ("Rights", "Research Use", None),
        ("Rights", "Restricted", None),
        ("Condition", "Good", None),
        ("Condition", "Fragile", None),
        ("Digitization Status", "Complete", None),
        ("Digitization Status", "Needs OCR Review", None),
    ]
    term_ids: Dict[Tuple[str, str], int] = {}
    for vocabulary, term, parent in vocab_terms:
        parent_id = term_ids.get((vocabulary, parent)) if parent else None
        term_ids[(vocabulary, term)] = get_or_create(
            conn,
            "taxonomy_terms",
            {"vocabulary": vocabulary, "term": term},
            {"parent_id": parent_id},
        )

    authorities = {
        "John Smith": ("Person", "Photographer credited on the Manila field print.", "J. Smith", ""),
        "U.S. Army": ("Organization", "United States Army records and field photography.", "US Army", ""),
        "Manila": ("Place", "City in the Philippines and key Pacific War location.", "Manila, Philippines", ""),
        "Battle of Manila": ("Event", "Battle in Manila during February-March 1945.", "Manila 1945", ""),
        "USS Enterprise": ("Organization", "U.S. Navy aircraft carrier associated with Pacific operations.", "CV-6", ""),
        "Leyte Gulf": ("Place", "Gulf in the Philippines associated with major naval action.", "Leyte", ""),
        "Battle of Leyte Gulf": ("Event", "Major naval battle in October 1944.", "Leyte Gulf Naval Battle", ""),
        "San Francisco Port of Embarkation": ("Place", "San Francisco wartime transport and logistics hub.", "SF Port", ""),
    }
    authority_ids = {
        name: get_or_create(
            conn,
            "authorities",
            {"type": authority_type, "name": name},
            {"description": description, "aliases": aliases, "external_uri": uri},
        )
        for name, (authority_type, description, aliases, uri) in authorities.items()
    }

    repo = get_or_create(conn, "storage_locations", {"name": "Main Repository"}, {"location_type": "Repository", "code": "REPO"})
    room = get_or_create(conn, "storage_locations", {"name": "Room 1"}, {"location_type": "Room", "code": "R1", "parent_id": repo})
    cabinet = get_or_create(conn, "storage_locations", {"name": "Cabinet A"}, {"location_type": "Cabinet", "code": "CA", "parent_id": room})
    shelf = get_or_create(conn, "storage_locations", {"name": "Shelf 2"}, {"location_type": "Shelf", "code": "S2", "parent_id": cabinet})
    box_12 = get_or_create(conn, "storage_locations", {"name": "Box 12"}, {"location_type": "Box", "code": "B12", "parent_id": shelf})
    folder_7 = get_or_create(conn, "storage_locations", {"name": "Folder 7"}, {"location_type": "Folder", "code": "F7", "parent_id": box_12})

    records = [
        {
            "permanent_id": "MNA-000123",
            "title": "Soldier portrait, Manila",
            "description": "Photograph of a U.S. Army soldier in Manila after urban combat in 1945.",
            "object_type": "Photograph",
            "date_label": "1945",
            "date_start": 1945,
            "date_end": 1945,
            "language": "English",
            "rights": "Public Domain",
            "provenance": "Donated by the Smith family; accession batch PW-2026-001.",
            "condition": "Good",
            "digitization_status": "Complete",
            "collection_id": manila_collection,
            "storage_location_id": folder_7,
            "authorities": [
                ("creator", "John Smith"),
                ("organization", "U.S. Army"),
                ("place", "Manila"),
                ("event", "Battle of Manila"),
            ],
            "terms": [("Subject", "WWII"), ("Subject", "Pacific Theater"), ("Object Type", "Photograph")],
            "media": [
                ("master.tif", "Preservation master placeholder for MNA-000123.", "preservation_master", "image/tiff"),
                ("access.jpg", "Access derivative placeholder for MNA-000123.", "access_derivative", "image/jpeg"),
                ("ocr.txt", "OCR transcript: Soldier portrait, Manila, 1945.", "ocr", "text/plain"),
            ],
        },
        {
            "permanent_id": "MNA-000221",
            "title": "Leyte Gulf operations map",
            "description": "Annotated naval operations map associated with the Battle of Leyte Gulf.",
            "object_type": "Map",
            "date_label": "1944",
            "date_start": 1944,
            "date_end": 1944,
            "language": "English",
            "rights": "Research Use",
            "provenance": "Acquired from a private collector; source file pending rights review.",
            "condition": "Fragile",
            "digitization_status": "Needs OCR Review",
            "collection_id": pacific_collection,
            "storage_location_id": box_12,
            "authorities": [
                ("organization", "USS Enterprise"),
                ("place", "Leyte Gulf"),
                ("event", "Battle of Leyte Gulf"),
            ],
            "terms": [("Subject", "WWII"), ("Subject", "Pacific Theater"), ("Object Type", "Map")],
            "media": [
                ("master.tif", "Preservation map master placeholder for MNA-000221.", "preservation_master", "image/tiff"),
                ("metadata.json", '{"scale":"unknown","projection":"wartime operational chart"}', "metadata_export", "application/json"),
            ],
        },
        {
            "permanent_id": "MNA-000302",
            "title": "Letter from San Francisco embarkation",
            "description": "Personal letter describing embarkation logistics and departure for the Pacific.",
            "object_type": "Letter",
            "date_label": "1942",
            "date_start": 1942,
            "date_end": 1942,
            "language": "English",
            "rights": "Restricted",
            "provenance": "Family archive loan; private information review required before publication.",
            "condition": "Good",
            "digitization_status": "Complete",
            "collection_id": pacific_collection,
            "storage_location_id": folder_7,
            "authorities": [
                ("place", "San Francisco Port of Embarkation"),
                ("organization", "U.S. Army"),
            ],
            "terms": [("Subject", "WWII"), ("Subject", "Civilian Experience"), ("Object Type", "Letter")],
            "media": [
                ("transcript.txt", "Restricted transcript placeholder for MNA-000302.", "transcript", "text/plain"),
            ],
        },
    ]

    for record in records:
        now = utc_now()
        conn.execute(
            """
            INSERT INTO objects (
              permanent_id, title, description, object_type, date_label, date_start, date_end,
              language, rights, provenance, condition, digitization_status, collection_id,
              storage_location_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record["permanent_id"],
                record["title"],
                record["description"],
                record["object_type"],
                record["date_label"],
                record["date_start"],
                record["date_end"],
                record["language"],
                record["rights"],
                record["provenance"],
                record["condition"],
                record["digitization_status"],
                record["collection_id"],
                record["storage_location_id"],
                now,
                now,
            ],
        )
        object_id = int(conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])
        for role, authority_name in record["authorities"]:
            conn.execute(
                "INSERT INTO object_authorities (object_id, authority_id, role) VALUES (?, ?, ?)",
                [object_id, authority_ids[authority_name], role],
            )
        for term_key in record["terms"]:
            conn.execute(
                "INSERT INTO object_terms (object_id, term_id) VALUES (?, ?)",
                [object_id, term_ids[term_key]],
            )
        write_seed_media(conn, object_id, record["permanent_id"], record["media"])
        conn.execute(
            "INSERT INTO movements (object_id, from_location_id, to_location_id, moved_at, note) VALUES (?, NULL, ?, ?, ?)",
            [object_id, record["storage_location_id"], now, "Initial V1 ingest location."],
        )

    conn.execute(
        "INSERT INTO audit_logs (actor, action, entity_type, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ["system", "seed", "database", "archive", "Initial demo dataset created.", utc_now()],
    )
    seed_formal_test_data(conn)


def seed_reference_taxonomy(conn: sqlite3.Connection) -> None:
    collections = [
        ("Pacific War Collection", "Local root collection for Pacific Theater materials."),
        ("National Museum of the Pacific War Digital Archive Reference", "Reference collection inspired by NMPWA public holdings and metadata patterns."),
        ("Pearl Harbor Collection", "Reference/demo collection for Pearl Harbor materials."),
        ("Women in War Collection", "Reference/demo collection for women's wartime service and home-front materials."),
        ("WWII Documents Collection", "Reference/demo collection for official documents and textual records."),
        ("Nimitz Family Collection", "Reference/demo collection for Nimitz-related material."),
        ("National Museum of the Pacific War Oral History Collection", "Reference/demo collection for interviews, transcripts, and sound recordings."),
        ("Fleet Radio Unit Pacific Map Collection", "Reference/demo collection for intelligence and map materials."),
        ("Pacific War Reference Materials", "Reference/demo collection for secondary and contextual material."),
    ]
    for name, description in collections:
        get_or_create(conn, "collections", {"name": name}, {"description": description})

    terms = [
        ("Object Type", "Photograph"),
        ("Object Type", "Text"),
        ("Object Type", "Letter"),
        ("Object Type", "Sound"),
        ("Object Type", "Map"),
        ("Object Type", "Video"),
        ("Object Type", "Pamphlet"),
        ("Object Type", "Postcard"),
        ("Object Type", "Newspaper"),
        ("Object Type", "Book"),
        ("Object Type", "Artwork"),
        ("Object Type", "Clipping"),
        ("Object Type", "Image"),
        ("Object Type", "Journal/Magazine/Newsletter"),
        ("Object Type", "Musical Score/Notation"),
        ("Object Type", "Report"),
        ("Object Type", "Poem"),
        ("Object Type", "Physical Object"),
        ("Object Type", "Technical Drawing"),
        ("Object Type", "Poster"),
        ("Object Type", "Article"),
        ("Object Type", "Legal Document"),
        ("Object Type", "Script"),
        ("Object Type", "Reference Material"),
        ("Object Type", "Oral History"),
        ("Resource Type", "Photograph"),
        ("Resource Type", "Text"),
        ("Resource Type", "Letter"),
        ("Resource Type", "Sound"),
        ("Resource Type", "Map"),
        ("Resource Type", "Video"),
        ("Resource Type", "Physical Object"),
        ("Genre/Form", "Oral histories"),
        ("Genre/Form", "Interviews"),
        ("Genre/Form", "Personal narratives"),
        ("Genre/Form", "Biographies"),
        ("Genre/Form", "Correspondence"),
        ("Genre/Form", "Military maps"),
        ("Genre/Form", "Photographic prints"),
        ("Subject", "WWII"),
        ("Subject", "World War, 1939-1945"),
        ("Subject", "Pacific Theater"),
        ("Subject", "Military and War"),
        ("Subject", "People - Individuals"),
        ("Subject", "United States Armed Forces"),
        ("Subject", "Veterans"),
        ("Subject", "Pearl Harbor"),
        ("Subject", "Women in War"),
        ("Subject", "Nimitz"),
        ("Subject", "Oral histories"),
        ("Subject", "Letters"),
        ("Subject", "Photographs"),
        ("Subject", "Maps"),
        ("Subject", "Home Front"),
        ("Subject", "Naval operations"),
        ("Subject", "Marine Corps"),
        ("Subject", "Army Air Forces"),
        ("Subject", "Prisoners of war"),
        ("Subject", "Civilian Experience"),
        ("Subject", "Japanese Incarceration"),
        ("Subject", "Military intelligence"),
        ("Subject", "Fleet Radio Unit Pacific"),
        ("Subject", "Medical care"),
        ("Subject", "War bonds"),
        ("Subject", "Censorship"),
        ("Subject", "Occupation"),
        ("Theater", "Pacific Theater"),
        ("Theater", "Asiatic-Pacific Theater"),
        ("Theater", "China Burma India Theater"),
        ("Campaign", "Pearl Harbor"),
        ("Campaign", "Guadalcanal Campaign"),
        ("Campaign", "Central Pacific Campaign"),
        ("Campaign", "Philippines Campaign"),
        ("Campaign", "Okinawa Campaign"),
        ("Campaign", "China Burma India Campaign"),
        ("Battle", "Attack on Pearl Harbor"),
        ("Battle", "Battle of Midway"),
        ("Battle", "Guadalcanal Campaign"),
        ("Battle", "Battle of Iwo Jima"),
        ("Battle", "Battle of Okinawa"),
        ("Battle", "Battle of Leyte Gulf"),
        ("Battle", "Battle of Manila"),
        ("Language", "English"),
        ("Language", "No Language"),
        ("Language", "Japanese"),
        ("Language", "French"),
        ("Language", "Chinese"),
        ("Language", "Spanish"),
        ("Language", "Italian"),
        ("Language", "Hindi"),
        ("Language", "Latin"),
        ("Language", "Other"),
        ("Rights", "Public Domain"),
        ("Rights", "Research Use"),
        ("Rights", "Restricted"),
        ("Rights", "Attribution Non-commercial No Derivatives"),
        ("Rights", "Unknown"),
        ("Access Rights", "Public"),
        ("Access Rights", "Reading Room Only"),
        ("Access Rights", "Restricted"),
        ("Access Rights", "Metadata Only"),
        ("Condition", "Excellent"),
        ("Condition", "Good"),
        ("Condition", "Fair"),
        ("Condition", "Fragile"),
        ("Condition", "Poor"),
        ("Digitization Status", "Not Started"),
        ("Digitization Status", "In Progress"),
        ("Digitization Status", "Complete"),
        ("Digitization Status", "Needs OCR Review"),
        ("Digitization Status", "Needs Rights Review"),
        ("Metadata Standard", "Dublin Core"),
        ("Metadata Standard", "DCMI Terms"),
        ("Metadata Standard", "UNTL"),
        ("Metadata Standard", "MODS"),
        ("Metadata Standard", "METS"),
        ("Metadata Standard", "PREMIS"),
        ("Metadata Standard", "IIIF Presentation"),
        ("Metadata Standard", "Schema.org CreativeWork"),
        ("Data Source", "Local Demo"),
        ("Data Source", "NMPWA Reference"),
        ("Formal Test Data", "True"),
        ("Formal Test Data", "False"),
        ("Historical Period", "1941-1945"),
        ("Historical Period", "Into Modern Times, 1939-Present"),
    ]
    for vocabulary, term in terms:
        get_or_create(conn, "taxonomy_terms", {"vocabulary": vocabulary, "term": term}, {"parent_id": None})

    authorities = {
        "National Museum of the Pacific War": ("Organization", "Reference organization for NMPWA-style records.", "NMPW; Admiral Nimitz Foundation", "https://www.pacificwarmuseum.org/"),
        "University of North Texas Libraries": ("Organization", "Host of The Portal to Texas History.", "UNT Libraries", "https://texashistory.unt.edu/"),
        "U.S. Navy": ("Organization", "United States Navy.", "US Navy", ""),
        "U.S. Marine Corps": ("Organization", "United States Marine Corps.", "USMC", ""),
        "U.S. Army": ("Organization", "United States Army.", "US Army", ""),
        "U.S. Army Air Forces": ("Organization", "United States Army Air Forces.", "USAAF", ""),
        "Women's Army Auxiliary Corps": ("Organization", "Women's Army Auxiliary Corps.", "WAAC", ""),
        "Imperial Japanese Navy": ("Organization", "Japanese naval force during World War II.", "IJN", ""),
        "Fleet Radio Unit Pacific": ("Organization", "U.S. Navy signals intelligence unit in the Pacific.", "FRUPAC", ""),
        "Chester W. Nimitz": ("Person", "Fleet Admiral Chester W. Nimitz.", "Nimitz, Chester William", ""),
        "Doris Miller": ("Person", "U.S. Navy sailor awarded the Navy Cross for actions at Pearl Harbor.", "Miller, Doris", ""),
        "Grace Hopper": ("Person", "Computer scientist and U.S. Navy officer; included for women-in-war reference testing.", "Hopper, Grace", ""),
        "Norman Hatch": ("Person", "Marine Corps combat cameraman associated with Pacific War photography.", "Norm Hatch", ""),
        "Pearl Harbor": ("Place", "Harbor and naval base in Hawaii.", "Pearl Harbor, Hawaii", ""),
        "Guadalcanal": ("Place", "Island in the Solomon Islands.", "Guadalcanal Island", ""),
        "Iwo Jima": ("Place", "Island battle site in the Pacific.", "Iwo To", ""),
        "Okinawa": ("Place", "Island battle site in Japan.", "Okinawa Island", ""),
        "Leyte Gulf": ("Place", "Gulf in the Philippines.", "Leyte", ""),
        "Manila": ("Place", "City in the Philippines.", "Manila, Philippines", ""),
        "Saipan": ("Place", "Island in the Northern Mariana Islands.", "Saipan Island", ""),
        "Tinian": ("Place", "Island in the Northern Mariana Islands.", "Tinian Island", ""),
        "Fredericksburg": ("Place", "Texas city where the National Museum of the Pacific War is located.", "Fredericksburg, Texas", ""),
        "Attack on Pearl Harbor": ("Event", "Japanese attack on Pearl Harbor on December 7, 1941.", "Pearl Harbor attack", ""),
        "Battle of Midway": ("Event", "Carrier battle in June 1942.", "Midway", ""),
        "Guadalcanal Campaign": ("Event", "Campaign in the Solomon Islands from 1942 to 1943.", "Guadalcanal", ""),
        "Battle of Iwo Jima": ("Event", "Battle for Iwo Jima in 1945.", "Iwo Jima", ""),
        "Battle of Okinawa": ("Event", "Battle for Okinawa in 1945.", "Okinawa", ""),
        "Battle of Leyte Gulf": ("Event", "Naval battle in October 1944.", "Leyte Gulf Naval Battle", ""),
        "Battle of Manila": ("Event", "Battle in Manila during 1945.", "Manila 1945", ""),
        "Women in War Home Front Mobilization": ("Event", "Wartime mobilization and public service by women.", "Women in War", ""),
    }
    for name, (authority_type, description, aliases, uri) in authorities.items():
        get_or_create(
            conn,
            "authorities",
            {"type": authority_type, "name": name},
            {"description": description, "aliases": aliases, "external_uri": uri},
        )


def seed_formal_test_data(conn: sqlite3.Connection) -> None:
    existing = conn.execute(
        "SELECT COUNT(*) AS count FROM objects WHERE permanent_id LIKE 'TEST-PW-%'"
    ).fetchone()["count"]
    if existing >= 100:
        return

    collections = [
        "Pearl Harbor Collection",
        "Women in War Collection",
        "WWII Documents Collection",
        "Nimitz Family Collection",
        "National Museum of the Pacific War Oral History Collection",
        "Fleet Radio Unit Pacific Map Collection",
        "Pacific War Reference Materials",
        "National Museum of the Pacific War Digital Archive Reference",
    ]
    object_types = [
        ("Photograph", "Photographic prints", "image/jpeg", "6,926 NMPWA photographs benchmark"),
        ("Letter", "Correspondence", "text/plain", "4,579 NMPWA letters benchmark"),
        ("Sound", "Oral histories", "audio/mpeg", "3,784 NMPWA sound records benchmark"),
        ("Map", "Military maps", "image/tiff", "873 NMPWA maps benchmark"),
        ("Text", "Military documents", "application/pdf", "WWII Documents reference"),
        ("Video", "Interviews", "video/mp4", "NMPWA video reference"),
        ("Pamphlet", "Pamphlets", "application/pdf", "wartime printed material reference"),
        ("Reference Material", "Reference works", "application/json", "cross-platform metadata test reference"),
    ]
    places = [
        ("Pearl Harbor", "United States", "Territory of Hawaii"),
        ("Guadalcanal", "Solomon Islands", "British Solomon Islands Protectorate"),
        ("Iwo Jima", "Japan", "Empire of Japan"),
        ("Okinawa", "Japan", "Empire of Japan"),
        ("Leyte Gulf", "Philippines", "Commonwealth of the Philippines"),
        ("Manila", "Philippines", "Commonwealth of the Philippines"),
        ("Saipan", "Northern Mariana Islands", "Japanese Mandate"),
        ("Tinian", "Northern Mariana Islands", "Japanese Mandate"),
        ("San Francisco Port of Embarkation", "United States", "United States"),
        ("Fredericksburg", "United States", "United States"),
    ]
    events = [
        ("Attack on Pearl Harbor", "Pearl Harbor"),
        ("Battle of Midway", "Central Pacific Campaign"),
        ("Guadalcanal Campaign", "Guadalcanal Campaign"),
        ("Battle of Iwo Jima", "Central Pacific Campaign"),
        ("Battle of Okinawa", "Okinawa Campaign"),
        ("Battle of Leyte Gulf", "Philippines Campaign"),
        ("Battle of Manila", "Philippines Campaign"),
        ("Women in War Home Front Mobilization", "Pacific Theater"),
    ]
    organizations = [
        "U.S. Navy",
        "U.S. Marine Corps",
        "U.S. Army",
        "U.S. Army Air Forces",
        "Women's Army Auxiliary Corps",
        "Imperial Japanese Navy",
        "Fleet Radio Unit Pacific",
        "National Museum of the Pacific War",
    ]
    people = [
        "Chester W. Nimitz",
        "Doris Miller",
        "Grace Hopper",
        "Norman Hatch",
        "Raymond Bower",
        "Florence Bower",
        "Joseph Yaklowich",
        "MJ Cotter",
        "Floyd R. Thomas",
        "Glenn G. Morgan",
    ]
    languages = ["English", "English", "English", "Japanese", "No Language", "French", "Chinese", "Spanish"]
    rights_values = ["Research Use", "Public Domain", "Attribution Non-commercial No Derivatives", "Restricted"]

    for index in range(1, 101):
        permanent_id = f"TEST-PW-{index:04d}"
        if conn.execute("SELECT id FROM objects WHERE permanent_id=?", [permanent_id]).fetchone():
            continue
        obj_type, genre, media_type, benchmark_note = object_types[(index - 1) % len(object_types)]
        place, modern_country, wartime_jurisdiction = places[(index - 1) % len(places)]
        event, campaign = events[(index - 1) % len(events)]
        organization = organizations[(index - 1) % len(organizations)]
        person = people[(index - 1) % len(people)]
        collection = collections[(index - 1) % len(collections)]
        year = 1941 + ((index - 1) % 5)
        language = languages[(index - 1) % len(languages)]
        rights = rights_values[(index - 1) % len(rights_values)]
        title = f"{obj_type} formal test record {index:03d}: {event}"
        data = {
            "permanent_id": permanent_id,
            "title": title,
            "alternative_title": f"NMPWA-style {obj_type.lower()} test fixture {index:03d}",
            "description": f"Formal test data record for Pacific War metadata, modeled after NMPWA browse and OAI patterns. Covers {event}, {place}, and {organization}.",
            "object_type": obj_type,
            "collection": collection,
            "date_label": str(year),
            "date_start": str(year),
            "date_end": str(year),
            "language": language,
            "rights": rights,
            "provenance": "Generated local formal test data for metadata, taxonomy, and search verification.",
            "condition": ["Excellent", "Good", "Fair", "Fragile"][(index - 1) % 4],
            "digitization_status": ["Complete", "Needs OCR Review", "Needs Rights Review"][(index - 1) % 3],
            "storage_location": f"Main Repository / Test Data Room / Cabinet {(index - 1) % 5 + 1} / Box {(index - 1) % 20 + 1}",
            "creators": person if obj_type in {"Photograph", "Letter", "Sound", "Video"} else "",
            "people": person,
            "organizations": organization,
            "places": place,
            "events": event,
            "subjects": f"WWII, Pacific Theater, {event}, {genre}",
            "publisher": "National Museum of the Pacific War / local demo seed",
            "contributors": "University of North Texas Libraries metadata pattern reference",
            "source": "https://texashistory.unt.edu/explore/collections/NMPWA/",
            "relation": f"Related to {collection}; benchmark note: {benchmark_note}.",
            "coverage_spatial": place,
            "coverage_temporal": f"{year}/{year}",
            "physical_description": f"Dummy {obj_type.lower()} fixture for metadata testing.",
            "extent": ["1 photograph", "4 pages", "1 audio file", "1 map", "12 pages"][(index - 1) % 5],
            "medium": ["paper", "photographic print", "digital audio", "map sheet", "typescript"][(index - 1) % 5],
            "citation": f"{title}. Archive Collection System formal test data, {permanent_id}.",
            "external_identifier": f"NMPWA-REF-{index:04d}",
            "ark": f"ark:/99999/testpw{index:04d}",
            "item_url": "https://texashistory.unt.edu/explore/collections/NMPWA/",
            "thumbnail_url": "https://texashistory.unt.edu/explore/collections/NMPWA/",
            "iiif_manifest_url": f"http://127.0.0.1:8787/iiif/3/{permanent_id}/manifest",
            "license_uri": "https://creativecommons.org/licenses/by-nc-nd/4.0/" if rights == "Attribution Non-commercial No Derivatives" else "",
            "access_rights": "Restricted" if rights == "Restricted" else "Public",
            "primary_source": "true",
            "resource_type": obj_type,
            "genre_form": genre,
            "series_title": collection,
            "subcollection": ["Pearl Harbor", "Women in War", "WWII Documents", "Nimitz", "Oral History"][(index - 1) % 5],
            "theater": "Pacific Theater",
            "campaign": campaign,
            "battle": event,
            "military_unit": organization,
            "vessel_aircraft": ["USS Enterprise", "USS Maryland", "USS Indianapolis", "B-24 Liberator", ""][(index - 1) % 5],
            "modern_country": modern_country,
            "wartime_jurisdiction": wartime_jurisdiction,
            "subject_source": "Local; UNTL-BS; LCSH-inspired; LCGFT-inspired",
            "metadata_profile": "Dublin Core + DCMI Terms + UNTL-inspired local profile",
            "display_note": "Formal test data: not a real archival item.",
            "internal_note": "Generated to exercise Pacific War search, taxonomy, and metadata fields.",
            "preservation_note": "Dummy media/checksum fixture only; not preservation content.",
            "metadata_json": json.dumps(
                {
                    "formal_test_data": True,
                    "reference_collection": "NMPWA",
                    "nmpwa_observed_counts": {
                        "items": "about 22.8k and growing",
                        "photographs": "about 6.9k",
                        "letters": "about 4.6k",
                        "sound": "3,784",
                        "maps": "873",
                    },
                    "standards": ["Dublin Core", "DCMI Terms", "UNTL", "IIIF", "PREMIS-ready"],
                },
                ensure_ascii=True,
            ),
            "formal_test_data": "true",
        }
        object_id = save_object(conn, data, "system")
        extension = {
            "Photograph": "jpg",
            "Letter": "txt",
            "Sound": "mp3",
            "Map": "tif",
            "Text": "pdf",
            "Video": "mp4",
            "Pamphlet": "pdf",
            "Reference Material": "json",
        }.get(obj_type, "txt")
        write_seed_media(
            conn,
            object_id,
            permanent_id,
            [
                (
                    f"{permanent_id}_access.{extension}",
                    f"{permanent_id} formal test media placeholder for {obj_type}.",
                    "access_derivative",
                    media_type,
                ),
                (
                    f"{permanent_id}_metadata.json",
                    data["metadata_json"],
                    "metadata_export",
                    "application/json",
                ),
            ],
        )

    conn.execute(
        "INSERT INTO audit_logs (actor, action, entity_type, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ["system", "seed_formal_test_data", "database", "archive", "Ensured 100 formal Pacific War test records.", utc_now()],
    )


def write_seed_media(
    conn: sqlite3.Connection,
    object_id: int,
    permanent_id: str,
    media: Iterable[Tuple[str, str, str, str]],
) -> None:
    item_dir = STORAGE_DIR / permanent_id
    item_dir.mkdir(parents=True, exist_ok=True)
    for filename, content, derivative_type, media_type in media:
        path = item_dir / filename
        if not path.exists():
            path.write_text(content + "\n", encoding="utf-8")
        checksum = sha256_file(path)
        conn.execute(
            """
            INSERT INTO digital_media (
              object_id, filename, original_filename, media_type, derivative_type,
              storage_provider, local_path, checksum_sha256, size_bytes, created_at
            )
            VALUES (?, ?, ?, ?, ?, 'local', ?, ?, ?, ?)
            """,
            [
                object_id,
                filename,
                filename,
                media_type,
                derivative_type,
                str(path.relative_to(ROOT)),
                checksum,
                path.stat().st_size,
                utc_now(),
            ],
        )


def location_path(conn: sqlite3.Connection, location_id: Optional[int]) -> str:
    if not location_id:
        return ""
    pieces: List[str] = []
    current = location_id
    while current:
        row = conn.execute("SELECT id, name, parent_id FROM storage_locations WHERE id=?", [current]).fetchone()
        if not row:
            break
        pieces.append(row["name"])
        current = row["parent_id"]
    return " / ".join(reversed(pieces))


def get_relationships(conn: sqlite3.Connection, object_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT a.id, a.type, a.name, a.description, a.aliases, a.external_uri, oa.role
        FROM object_authorities oa
        JOIN authorities a ON a.id = oa.authority_id
        WHERE oa.object_id=?
        ORDER BY a.type, a.name
        """,
        [object_id],
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def get_terms(conn: sqlite3.Connection, object_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT t.id, t.vocabulary, t.term, t.parent_id
        FROM object_terms ot
        JOIN taxonomy_terms t ON t.id = ot.term_id
        WHERE ot.object_id=?
        ORDER BY t.vocabulary, t.term
        """,
        [object_id],
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def get_media(conn: sqlite3.Connection, object_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM digital_media WHERE object_id=? ORDER BY derivative_type, filename",
        [object_id],
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def parse_json_field(value: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def intake_payload(row: sqlite3.Row) -> Dict[str, Any]:
    payload = row_to_dict(row)
    payload["suggested"] = parse_json_field(payload.pop("suggested_json", "{}"))
    payload["edited"] = parse_json_field(payload.pop("edited_json", "{}"))
    return payload


def analyze_intake_file(filename: str, media_type: str, checksum: str, size_bytes: int) -> Dict[str, Any]:
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    lowered = stem.lower()
    object_type = "Photograph"
    if "map" in lowered:
        object_type = "Map"
    elif "letter" in lowered or "memo" in lowered or "document" in lowered:
        object_type = "Letter"
    elif "poster" in lowered:
        object_type = "Poster"
    year = ""
    for token in stem.replace("_", " ").replace("-", " ").split():
        if token.isdigit() and 1900 <= int(token) <= 2100:
            year = token
            break
    ai_metadata = {
        "analyzer": "mock_intake_analyzer_v1",
        "source": "local_batch_upload",
        "confidence": {
            "title": 0.55,
            "object_type": 0.5,
            "date_label": 0.35 if year else 0.0,
        },
        "file": {
            "filename": filename,
            "media_type": media_type,
            "checksum_sha256": checksum,
            "size_bytes": size_bytes,
        },
        "review_required": True,
    }
    return {
        "permanent_id": "",
        "title": stem.title() or filename,
        "description": f"AI intake draft generated from uploaded file {filename}. Review and revise before submitting.",
        "object_type": object_type,
        "collection": "Pacific War Collection",
        "date_label": year,
        "date_start": year,
        "date_end": year,
        "language": "No Language" if object_type in {"Photograph", "Map", "Poster"} else "English",
        "rights": "Unknown",
        "provenance": "Local AI intake upload; provenance requires curator review.",
        "condition": "",
        "digitization_status": "Needs OCR Review",
        "storage_location": "",
        "creators": "",
        "people": "",
        "organizations": "",
        "places": "",
        "events": "",
        "subjects": "WWII, Pacific Theater",
        "resource_type": object_type,
        "genre_form": "Photographic prints" if object_type == "Photograph" else "",
        "theater": "Pacific Theater",
        "metadata_profile": "Dublin Core + DCMI Terms + UNTL-inspired local profile",
        "display_note": "Draft metadata generated by mock AI intake analyzer.",
        "internal_note": "Review every AI-suggested field before submit.",
        "preservation_note": "Original uploaded through AI intake; checksum captured before formal ingest.",
        "metadata_json": json.dumps(ai_metadata, ensure_ascii=True, sort_keys=True),
        "primary_source": "true",
        "formal_test_data": "false",
    }


def insert_local_media_from_path(
    conn: sqlite3.Connection,
    object_id: int,
    source_path: Path,
    original_filename: str,
    derivative_type: str,
) -> Dict[str, Any]:
    row = conn.execute("SELECT id, permanent_id FROM objects WHERE id=?", [object_id]).fetchone()
    if not row:
        raise ValueError("Object not found")
    item_dir = STORAGE_DIR / row["permanent_id"]
    item_dir.mkdir(parents=True, exist_ok=True)
    original_name = clean_filename(original_filename)
    filename = original_name
    target = item_dir / filename
    counter = 2
    while target.exists():
        stem = Path(original_name).stem
        suffix = Path(original_name).suffix
        filename = f"{stem}_{counter}{suffix}"
        target = item_dir / filename
        counter += 1
    shutil.copy2(source_path, target)
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    conn.execute(
        """
        INSERT INTO digital_media (
          object_id, filename, original_filename, media_type, derivative_type, storage_provider,
          local_path, checksum_sha256, size_bytes, created_at
        )
        VALUES (?, ?, ?, ?, ?, 'local', ?, ?, ?, ?)
        """,
        [
            object_id,
            filename,
            original_filename,
            media_type,
            derivative_type,
            str(target.relative_to(ROOT)),
            sha256_file(target),
            target.stat().st_size,
            utc_now(),
        ],
    )
    return {"filename": filename, "local_path": str(target.relative_to(ROOT))}


def object_payload(conn: sqlite3.Connection, row: sqlite3.Row) -> Dict[str, Any]:
    payload = row_to_dict(row)
    payload["collection_name"] = row["collection_name"] if "collection_name" in row.keys() else ""
    payload["storage_location_path"] = location_path(conn, payload.get("storage_location_id"))
    payload["relationships"] = get_relationships(conn, int(payload["id"]))
    payload["terms"] = get_terms(conn, int(payload["id"]))
    payload["media"] = get_media(conn, int(payload["id"]))
    return payload


def sanitize_object_for_user(obj: Dict[str, Any], user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if is_admin_user(user):
        return obj
    payload = dict(obj)
    for field in VIEWER_HIDDEN_OBJECT_FIELDS:
        payload.pop(field, None)
    payload["media"] = [sanitize_media_for_viewer(media) for media in payload.get("media", [])]
    return payload


def sanitize_media_for_viewer(media: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(media)
    for field in VIEWER_HIDDEN_MEDIA_FIELDS:
        payload.pop(field, None)
    return payload


def all_objects(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT o.*, c.name AS collection_name
        FROM objects o
        LEFT JOIN collections c ON c.id = o.collection_id
        ORDER BY o.permanent_id
        """
    ).fetchall()
    return [object_payload(conn, row) for row in rows]


def matches_query(obj: Dict[str, Any], query: str, include_internal: bool = True) -> bool:
    if not query:
        return True
    searchable_fields = [
        "permanent_id",
        "title",
        "description",
        "object_type",
        "date_label",
        "language",
        "rights",
        "provenance",
        "collection_name",
    ]
    if include_internal:
        searchable_fields.append("storage_location_path")
    haystack = [obj.get(field, "") for field in searchable_fields]
    for field in EXTENDED_FIELD_NAMES:
        if not include_internal and field in VIEWER_HIDDEN_SEARCH_FIELDS:
            continue
        value = obj.get(field, "")
        if field in BOOLEAN_OBJECT_FIELDS:
            haystack.append("true" if value else "false")
            if field == "formal_test_data" and value:
                haystack.append("formal test data true")
        else:
            haystack.append(value)
    for rel in obj.get("relationships", []):
        haystack.extend([rel.get("name", ""), rel.get("aliases", ""), rel.get("type", ""), rel.get("role", "")])
    for term in obj.get("terms", []):
        haystack.extend([term.get("vocabulary", ""), term.get("term", "")])
    for media in obj.get("media", []):
        haystack.extend([media.get("filename", ""), media.get("derivative_type", ""), media.get("google_drive_url", "")])
    value = " ".join(str(part) for part in haystack).lower()
    return query.lower() in value


def relation_names(obj: Dict[str, Any], authority_type: str) -> List[str]:
    return [rel["name"] for rel in obj.get("relationships", []) if rel["type"] == authority_type]


def term_names(obj: Dict[str, Any], vocabulary: Optional[str] = None) -> List[str]:
    return [
        term["term"]
        for term in obj.get("terms", [])
        if vocabulary is None or term["vocabulary"] == vocabulary
    ]


def filter_objects(
    objects: List[Dict[str, Any]],
    filters: Dict[str, str],
    include_internal: bool = True,
) -> List[Dict[str, Any]]:
    query = filters.get("query", "").strip()
    results: List[Dict[str, Any]] = []
    for obj in objects:
        if not matches_query(obj, query, include_internal=include_internal):
            continue
        if filters.get("collection") and obj.get("collection_name") != filters["collection"]:
            continue
        if filters.get("object_type") and obj.get("object_type") != filters["object_type"]:
            continue
        if filters.get("rights") and obj.get("rights") != filters["rights"]:
            continue
        if filters.get("language") and obj.get("language") != filters["language"]:
            continue
        if filters.get("digitization_status") and obj.get("digitization_status") != filters["digitization_status"]:
            continue
        if filters.get("person") and filters["person"] not in relation_names(obj, "Person"):
            continue
        if filters.get("organization") and filters["organization"] not in relation_names(obj, "Organization"):
            continue
        if filters.get("place") and filters["place"] not in relation_names(obj, "Place"):
            continue
        if filters.get("event") and filters["event"] not in relation_names(obj, "Event"):
            continue
        if filters.get("subject") and filters["subject"] not in term_names(obj, "Subject"):
            continue
        if filters.get("resource_type") and obj.get("resource_type") != filters["resource_type"]:
            continue
        if filters.get("genre_form") and obj.get("genre_form") != filters["genre_form"]:
            continue
        if filters.get("campaign") and obj.get("campaign") != filters["campaign"]:
            continue
        if filters.get("battle") and obj.get("battle") != filters["battle"]:
            continue
        if filters.get("formal_test_data"):
            requested = filters["formal_test_data"].lower()
            is_formal = bool(obj.get("formal_test_data"))
            if requested == "true" and not is_formal:
                continue
            if requested == "false" and is_formal:
                continue
        date_from = int(filters["date_from"]) if filters.get("date_from") else None
        date_to = int(filters["date_to"]) if filters.get("date_to") else None
        if date_from and obj.get("date_end") and int(obj["date_end"]) < date_from:
            continue
        if date_to and obj.get("date_start") and int(obj["date_start"]) > date_to:
            continue
        results.append(obj)
    return results


def facet_values(objects: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    facets: Dict[str, set] = {
        "collection": set(),
        "object_type": set(),
        "rights": set(),
        "language": set(),
        "digitization_status": set(),
        "person": set(),
        "organization": set(),
        "place": set(),
        "event": set(),
        "subject": set(),
        "resource_type": set(),
        "genre_form": set(),
        "campaign": set(),
        "battle": set(),
        "formal_test_data": set(),
    }
    for obj in objects:
        for key in [
            "collection_name",
            "object_type",
            "rights",
            "language",
            "digitization_status",
            "resource_type",
            "genre_form",
            "campaign",
            "battle",
        ]:
            map_key = "collection" if key == "collection_name" else key
            value = obj.get(key)
            if value:
                facets[map_key].add(value)
        facets["formal_test_data"].add("True" if obj.get("formal_test_data") else "False")
        for rel in obj.get("relationships", []):
            key = rel["type"].lower()
            if key in facets:
                facets[key].add(rel["name"])
        for term in obj.get("terms", []):
            if term["vocabulary"] == "Subject":
                facets["subject"].add(term["term"])
    return {key: sorted(values) for key, values in facets.items()}


def create_backup(actor: str) -> Dict[str, Any]:
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_dir = BACKUP_DIR / f"archive_backup_{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    with connect() as conn:
        shutil.copy2(DB_PATH, backup_dir / "archive.db")
        objects = all_objects(conn)
        (backup_dir / "metadata_export.json").write_text(
            json.dumps(objects, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        taxonomy = [row_to_dict(row) for row in conn.execute("SELECT * FROM taxonomy_terms ORDER BY vocabulary, term")]
        authorities = [row_to_dict(row) for row in conn.execute("SELECT * FROM authorities ORDER BY type, name")]
        (backup_dir / "taxonomy_export.json").write_text(
            json.dumps({"taxonomy_terms": taxonomy, "authorities": authorities}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        checksums = [row_to_dict(row) for row in conn.execute("SELECT id, object_id, filename, local_path, checksum_sha256, size_bytes FROM digital_media WHERE storage_provider='local' ORDER BY id")]
        (backup_dir / "checksums.json").write_text(json.dumps(checksums, indent=2), encoding="utf-8")
        conn.execute(
            "INSERT INTO audit_logs (actor, action, entity_type, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            [actor, "backup", "backup", backup_dir.name, "Generated database, metadata, taxonomy, and checksum exports.", utc_now()],
        )
    return {"backup": backup_dir.name, "path": str(backup_dir.relative_to(ROOT))}


class ArchiveHandler(BaseHTTPRequestHandler):
    server_version = "ArchiveCollectionDemo/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        if path == "/" or path == "/index.html":
            return self.serve_static(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        if path.startswith("/static/"):
            return self.serve_static(STATIC_DIR / path.removeprefix("/static/"))
        if path.startswith("/local-media/"):
            return self.handle_media_download(path)
        if path.startswith("/api/"):
            return self.handle_api_get(path, query)
        self.respond_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/"):
            return self.handle_api_post(parsed.path)
        self.respond_json({"error": "Not found"}, 404)

    def do_PUT(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/"):
            return self.handle_api_put(parsed.path)
        self.respond_json({"error": "Not found"}, 404)

    def serve_static(self, path: Path, content_type: Optional[str] = None) -> None:
        try:
            resolved = path.resolve()
            if STATIC_DIR.resolve() not in resolved.parents and resolved != (STATIC_DIR / "index.html").resolve():
                self.respond_json({"error": "Forbidden"}, 403)
                return
            if not resolved.exists() or not resolved.is_file():
                self.respond_json({"error": "Not found"}, 404)
                return
            if content_type is None:
                content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
            data = resolved.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            self.respond_json({"error": str(exc)}, 500)

    def parse_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        body = self.rfile.read(length)
        return json.loads(body.decode("utf-8"))

    def respond_json(self, payload: Any, status: int = 200, headers: Optional[Dict[str, str]] = None) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def cookie_token(self) -> Optional[str]:
        raw = self.headers.get("Cookie", "")
        cookies = http.cookies.SimpleCookie(raw)
        morsel = cookies.get(SESSION_COOKIE)
        return morsel.value if morsel else None

    def current_user(self) -> Optional[Dict[str, Any]]:
        token = self.cookie_token()
        if not token:
            return None
        with connect() as conn:
            row = conn.execute(
                """
                SELECT u.id, u.username, u.role, u.display_name
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token=? AND s.expires_at>?
                """,
                [token, int(time.time())],
            ).fetchone()
            return row_to_dict(row) if row else None

    def require_user(self) -> Optional[Dict[str, Any]]:
        user = self.current_user()
        if not user:
            self.respond_json({"error": "Authentication required"}, 401)
            return None
        return user

    def require_admin(self) -> Optional[Dict[str, Any]]:
        user = self.require_user()
        if not user:
            return None
        if user["role"] != "admin":
            self.respond_json({"error": "Admin permission required"}, 403)
            return None
        return user

    def handle_api_get(self, path: str, query: Dict[str, List[str]]) -> None:
        if path == "/api/me":
            user = self.current_user()
            return self.respond_json({"authenticated": bool(user), "user": user})
        user = self.require_user()
        if not user:
            return
        with connect() as conn:
            if path == "/api/summary":
                objects = all_objects(conn)
                return self.respond_json(
                    {
                        "app": APP_NAME,
                        "counts": {
                            "objects": len(objects),
                            "collections": conn.execute("SELECT COUNT(*) AS c FROM collections").fetchone()["c"],
                            "authorities": conn.execute("SELECT COUNT(*) AS c FROM authorities").fetchone()["c"],
                            "digital_media": conn.execute("SELECT COUNT(*) AS c FROM digital_media").fetchone()["c"],
                            "storage_locations": conn.execute("SELECT COUNT(*) AS c FROM storage_locations").fetchone()["c"],
                            "formal_test_data": conn.execute("SELECT COUNT(*) AS c FROM objects WHERE formal_test_data=1").fetchone()["c"],
                            "intake_needs_review": conn.execute("SELECT COUNT(*) AS c FROM intake_items WHERE status='needs_review'").fetchone()["c"],
                        },
                        "facets": facet_values(objects),
                    }
                )
            if path == "/api/objects":
                filters = {key: values[0] for key, values in query.items() if values and values[0]}
                objects = filter_objects(all_objects(conn), filters, include_internal=is_admin_user(user))
                response_objects = [sanitize_object_for_user(obj, user) for obj in objects]
                return self.respond_json({"objects": response_objects, "count": len(objects), "facets": facet_values(objects)})
            if path.startswith("/api/objects/"):
                object_id = path.split("/")[-1]
                row = conn.execute(
                    """
                    SELECT o.*, c.name AS collection_name
                    FROM objects o
                    LEFT JOIN collections c ON c.id = o.collection_id
                    WHERE o.id=? OR o.permanent_id=?
                    """,
                    [object_id, object_id],
                ).fetchone()
                if not row:
                    return self.respond_json({"error": "Object not found"}, 404)
                return self.respond_json({"object": sanitize_object_for_user(object_payload(conn, row), user)})
            if path == "/api/collections":
                rows = conn.execute("SELECT * FROM collections ORDER BY name").fetchall()
                return self.respond_json({"collections": [row_to_dict(row) for row in rows]})
            if path == "/api/authorities":
                rows = conn.execute("SELECT * FROM authorities ORDER BY type, name").fetchall()
                return self.respond_json({"authorities": [row_to_dict(row) for row in rows]})
            if path == "/api/taxonomy":
                rows = conn.execute("SELECT * FROM taxonomy_terms ORDER BY vocabulary, term").fetchall()
                return self.respond_json({"terms": [row_to_dict(row) for row in rows]})
            if path == "/api/storage-locations":
                user = self.require_admin()
                if not user:
                    return
                rows = conn.execute("SELECT * FROM storage_locations ORDER BY id").fetchall()
                payload = []
                for row in rows:
                    item = row_to_dict(row)
                    item["path"] = location_path(conn, item["id"])
                    payload.append(item)
                return self.respond_json({"locations": payload})
            if path == "/api/audit":
                user = self.require_admin()
                if not user:
                    return
                rows = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 50").fetchall()
                return self.respond_json({"logs": [row_to_dict(row) for row in rows]})
            if path == "/api/admin/intake":
                user = self.require_admin()
                if not user:
                    return
                status = query.get("status", [""])[0]
                if status:
                    rows = conn.execute(
                        "SELECT * FROM intake_items WHERE status=? ORDER BY id DESC",
                        [status],
                    ).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM intake_items ORDER BY id DESC").fetchall()
                return self.respond_json({"items": [intake_payload(row) for row in rows]})
            if path.startswith("/api/admin/intake/"):
                user = self.require_admin()
                if not user:
                    return
                return self.get_intake_item(path)
        self.respond_json({"error": "Not found"}, 404)

    def handle_api_post(self, path: str) -> None:
        if path == "/api/login":
            return self.login()
        if path == "/api/logout":
            return self.logout()
        if path == "/api/objects":
            return self.create_object()
        if path.endswith("/media"):
            return self.upload_media(path)
        if path.endswith("/media-link"):
            return self.add_media_link(path)
        if path == "/api/admin/backup":
            user = self.require_admin()
            if not user:
                return
            return self.respond_json(create_backup(user["username"]))
        if path == "/api/admin/intake/upload":
            return self.upload_intake()
        if path.startswith("/api/admin/intake/") and path.endswith("/submit"):
            return self.submit_intake(path)
        if path.startswith("/api/admin/intake/") and path.endswith("/reject"):
            return self.reject_intake(path)
        self.respond_json({"error": "Not found"}, 404)

    def handle_api_put(self, path: str) -> None:
        if path.startswith("/api/objects/"):
            return self.update_object(path)
        if path.startswith("/api/admin/intake/"):
            return self.update_intake(path)
        self.respond_json({"error": "Not found"}, 404)

    def login(self) -> None:
        data = self.parse_json_body()
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", ""))
        with connect() as conn:
            row = conn.execute(
                "SELECT id, username, role, display_name FROM users WHERE username=? AND password_hash=?",
                [username, password_hash(password)],
            ).fetchone()
            if not row:
                return self.respond_json({"error": "Invalid username or password"}, 401)
            token = secrets.token_urlsafe(32)
            expires = int(time.time()) + 60 * 60 * 8
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                [token, row["id"], utc_now(), expires],
            )
            cookie = f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={60 * 60 * 8}"
            return self.respond_json({"user": row_to_dict(row)}, headers={"Set-Cookie": cookie})

    def logout(self) -> None:
        token = self.cookie_token()
        if token:
            with connect() as conn:
                conn.execute("DELETE FROM sessions WHERE token=?", [token])
        cookie = f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
        self.respond_json({"ok": True}, headers={"Set-Cookie": cookie})

    def object_id_from_media_path(self, path: str, suffix: str) -> Optional[int]:
        parts = path.split("/")
        if len(parts) != 5 or parts[1] != "api" or parts[2] != "objects" or parts[4] != suffix:
            return None
        try:
            return int(parts[3])
        except ValueError:
            return None

    def create_object(self) -> None:
        user = self.require_admin()
        if not user:
            return
        data = self.parse_json_body()
        try:
            with connect() as conn:
                object_id = save_object(conn, data, user["username"])
                row = conn.execute(
                    """
                    SELECT o.*, c.name AS collection_name
                    FROM objects o
                    LEFT JOIN collections c ON c.id = o.collection_id
                    WHERE o.id=?
                    """,
                    [object_id],
                ).fetchone()
                return self.respond_json({"object": object_payload(conn, row)}, 201)
        except sqlite3.IntegrityError as exc:
            return self.respond_json({"error": str(exc)}, 400)
        except ValueError as exc:
            return self.respond_json({"error": str(exc)}, 400)

    def update_object(self, path: str) -> None:
        user = self.require_admin()
        if not user:
            return
        parts = path.split("/")
        if len(parts) != 4:
            return self.respond_json({"error": "Invalid object path"}, 404)
        data = self.parse_json_body()
        data["id"] = parts[-1]
        try:
            with connect() as conn:
                object_id = save_object(conn, data, user["username"], update=True)
                row = conn.execute(
                    """
                    SELECT o.*, c.name AS collection_name
                    FROM objects o
                    LEFT JOIN collections c ON c.id = o.collection_id
                    WHERE o.id=?
                    """,
                    [object_id],
                ).fetchone()
                return self.respond_json({"object": object_payload(conn, row)})
        except sqlite3.IntegrityError as exc:
            return self.respond_json({"error": str(exc)}, 400)
        except ValueError as exc:
            return self.respond_json({"error": str(exc)}, 400)

    def intake_id_from_path(self, path: str) -> Optional[int]:
        parts = [part for part in path.split("/") if part]
        try:
            index = parts.index("intake")
            return int(parts[index + 1])
        except (ValueError, IndexError):
            return None

    def get_intake_item(self, path: str) -> None:
        intake_id = self.intake_id_from_path(path)
        if not intake_id:
            return self.respond_json({"error": "Invalid intake path"}, 404)
        with connect() as conn:
            row = conn.execute("SELECT * FROM intake_items WHERE id=?", [intake_id]).fetchone()
            if not row:
                return self.respond_json({"error": "Intake item not found"}, 404)
            return self.respond_json({"item": intake_payload(row)})

    def upload_intake(self) -> None:
        user = self.require_admin()
        if not user:
            return
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            return self.respond_json({"error": "multipart/form-data required"}, 400)
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            },
        )
        fields = form["files"] if "files" in form else form["file"] if "file" in form else []
        file_fields = fields if isinstance(fields, list) else [fields]
        file_fields = [field for field in file_fields if getattr(field, "filename", "")]
        if not file_fields:
            return self.respond_json({"error": "At least one file is required"}, 400)

        created = []
        with connect() as conn:
            for file_field in file_fields:
                original_filename = clean_filename(file_field.filename)
                now = utc_now()
                conn.execute(
                    """
                    INSERT INTO intake_items (
                      status, filename, original_filename, media_type, local_path,
                      checksum_sha256, size_bytes, suggested_json, edited_json,
                      created_by, created_at, updated_at
                    )
                    VALUES ('needs_review', ?, ?, '', '', '', 0, '{}', '{}', ?, ?, ?)
                    """,
                    [original_filename, file_field.filename, user["username"], now, now],
                )
                intake_id = int(conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])
                item_dir = INTAKE_DIR / str(intake_id)
                item_dir.mkdir(parents=True, exist_ok=True)
                target = item_dir / original_filename
                with target.open("wb") as output:
                    shutil.copyfileobj(file_field.file, output)
                media_type = mimetypes.guess_type(original_filename)[0] or "application/octet-stream"
                checksum = sha256_file(target)
                size_bytes = target.stat().st_size
                suggestion = analyze_intake_file(original_filename, media_type, checksum, size_bytes)
                suggestion_json = json.dumps(suggestion, ensure_ascii=True, sort_keys=True)
                conn.execute(
                    """
                    UPDATE intake_items
                    SET media_type=?, local_path=?, checksum_sha256=?, size_bytes=?,
                        suggested_json=?, edited_json=?, updated_at=?
                    WHERE id=?
                    """,
                    [
                        media_type,
                        str(target.relative_to(ROOT)),
                        checksum,
                        size_bytes,
                        suggestion_json,
                        suggestion_json,
                        utc_now(),
                        intake_id,
                    ],
                )
                conn.execute(
                    "INSERT INTO audit_logs (actor, action, entity_type, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    [user["username"], "intake_upload", "intake_item", str(intake_id), original_filename, utc_now()],
                )
                row = conn.execute("SELECT * FROM intake_items WHERE id=?", [intake_id]).fetchone()
                created.append(intake_payload(row))
        return self.respond_json({"ok": True, "items": created}, 201)

    def update_intake(self, path: str) -> None:
        user = self.require_admin()
        if not user:
            return
        intake_id = self.intake_id_from_path(path)
        if not intake_id:
            return self.respond_json({"error": "Invalid intake path"}, 404)
        data = self.parse_json_body()
        edited = data.get("edited")
        if not isinstance(edited, dict):
            return self.respond_json({"error": "edited object is required"}, 400)
        with connect() as conn:
            row = conn.execute("SELECT * FROM intake_items WHERE id=?", [intake_id]).fetchone()
            if not row:
                return self.respond_json({"error": "Intake item not found"}, 404)
            if row["status"] != "needs_review":
                return self.respond_json({"error": "Only needs_review intake items can be edited"}, 400)
            conn.execute(
                "UPDATE intake_items SET edited_json=?, updated_at=? WHERE id=?",
                [json.dumps(edited, ensure_ascii=True, sort_keys=True), utc_now(), intake_id],
            )
            conn.execute(
                "INSERT INTO audit_logs (actor, action, entity_type, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                [user["username"], "intake_update", "intake_item", str(intake_id), row["filename"], utc_now()],
            )
            updated = conn.execute("SELECT * FROM intake_items WHERE id=?", [intake_id]).fetchone()
        return self.respond_json({"ok": True, "item": intake_payload(updated)})

    def submit_intake(self, path: str) -> None:
        user = self.require_admin()
        if not user:
            return
        intake_id = self.intake_id_from_path(path)
        if not intake_id:
            return self.respond_json({"error": "Invalid intake path"}, 404)
        data = self.parse_json_body()
        mode = str(data.get("mode") or "").strip()
        derivative_type = clean_text(data.get("derivative_type")) or "preservation_master"
        with connect() as conn:
            row = conn.execute("SELECT * FROM intake_items WHERE id=?", [intake_id]).fetchone()
            if not row:
                return self.respond_json({"error": "Intake item not found"}, 404)
            if row["status"] != "needs_review":
                return self.respond_json({"error": "Only needs_review intake items can be submitted"}, 400)
            source_path = ROOT / row["local_path"]
            if not source_path.exists() or not source_path.is_file():
                return self.respond_json({"error": "Intake source file is missing"}, 404)

            edited = parse_json_field(row["edited_json"])
            if isinstance(data.get("edited"), dict):
                edited.update(data["edited"])
            try:
                if mode == "create_object":
                    if not clean_text(edited.get("permanent_id")):
                        edited["permanent_id"] = f"AI-INTAKE-{intake_id:06d}"
                    object_id = save_object(conn, edited, user["username"])
                    details = f"created {edited['permanent_id']} from {row['filename']}"
                elif mode == "attach_existing":
                    object_id = int(data.get("object_id") or 0)
                    if not conn.execute("SELECT id FROM objects WHERE id=?", [object_id]).fetchone():
                        return self.respond_json({"error": "Target object not found"}, 404)
                    details = f"attached {row['filename']} to object {object_id}"
                else:
                    return self.respond_json({"error": "mode must be create_object or attach_existing"}, 400)

                insert_local_media_from_path(conn, object_id, source_path, row["original_filename"], derivative_type)
                now = utc_now()
                conn.execute(
                    """
                    UPDATE intake_items
                    SET status='submitted', edited_json=?, submitted_object_id=?,
                        updated_at=?, submitted_at=?
                    WHERE id=?
                    """,
                    [json.dumps(edited, ensure_ascii=True, sort_keys=True), object_id, now, now, intake_id],
                )
                conn.execute(
                    "UPDATE objects SET digitization_status=COALESCE(NULLIF(digitization_status, ''), ?), updated_at=? WHERE id=?",
                    ["Complete", utc_now(), object_id],
                )
                conn.execute(
                    "INSERT INTO audit_logs (actor, action, entity_type, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    [user["username"], "intake_submit", "intake_item", str(intake_id), details, utc_now()],
                )
                object_row = conn.execute(
                    """
                    SELECT o.*, c.name AS collection_name
                    FROM objects o
                    LEFT JOIN collections c ON c.id = o.collection_id
                    WHERE o.id=?
                    """,
                    [object_id],
                ).fetchone()
            except (sqlite3.IntegrityError, ValueError) as exc:
                return self.respond_json({"error": str(exc)}, 400)
            return self.respond_json({"ok": True, "object": object_payload(conn, object_row)})

    def reject_intake(self, path: str) -> None:
        user = self.require_admin()
        if not user:
            return
        intake_id = self.intake_id_from_path(path)
        if not intake_id:
            return self.respond_json({"error": "Invalid intake path"}, 404)
        data = self.parse_json_body()
        reason = clean_text(data.get("reason"))
        with connect() as conn:
            row = conn.execute("SELECT * FROM intake_items WHERE id=?", [intake_id]).fetchone()
            if not row:
                return self.respond_json({"error": "Intake item not found"}, 404)
            if row["status"] != "needs_review":
                return self.respond_json({"error": "Only needs_review intake items can be rejected"}, 400)
            conn.execute(
                "UPDATE intake_items SET status='rejected', reject_reason=?, updated_at=? WHERE id=?",
                [reason, utc_now(), intake_id],
            )
            conn.execute(
                "INSERT INTO audit_logs (actor, action, entity_type, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                [user["username"], "intake_reject", "intake_item", str(intake_id), reason or row["filename"], utc_now()],
            )
            updated = conn.execute("SELECT * FROM intake_items WHERE id=?", [intake_id]).fetchone()
        return self.respond_json({"ok": True, "item": intake_payload(updated)})

    def upload_media(self, path: str) -> None:
        user = self.require_admin()
        if not user:
            return
        object_id = self.object_id_from_media_path(path, "media")
        if not object_id:
            return self.respond_json({"error": "Invalid media path"}, 404)
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            return self.respond_json({"error": "multipart/form-data required"}, 400)
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            },
        )
        if "file" not in form:
            return self.respond_json({"error": "Missing file field"}, 400)
        file_field = form["file"]
        if not getattr(file_field, "filename", ""):
            return self.respond_json({"error": "Uploaded file has no filename"}, 400)
        derivative_type = str(form.getfirst("derivative_type", "access_derivative"))
        original_name = clean_filename(file_field.filename)
        with connect() as conn:
            row = conn.execute("SELECT id, permanent_id FROM objects WHERE id=?", [object_id]).fetchone()
            if not row:
                return self.respond_json({"error": "Object not found"}, 404)
            item_dir = STORAGE_DIR / row["permanent_id"]
            item_dir.mkdir(parents=True, exist_ok=True)
            filename = original_name
            target = item_dir / filename
            counter = 2
            while target.exists():
                stem = Path(original_name).stem
                suffix = Path(original_name).suffix
                filename = f"{stem}_{counter}{suffix}"
                target = item_dir / filename
                counter += 1
            with target.open("wb") as output:
                shutil.copyfileobj(file_field.file, output)
            media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            conn.execute(
                """
                INSERT INTO digital_media (
                  object_id, filename, original_filename, media_type, derivative_type, storage_provider,
                  local_path, checksum_sha256, size_bytes, created_at
                )
                VALUES (?, ?, ?, ?, ?, 'local', ?, ?, ?, ?)
                """,
                [
                    object_id,
                    filename,
                    file_field.filename,
                    media_type,
                    derivative_type,
                    str(target.relative_to(ROOT)),
                    sha256_file(target),
                    target.stat().st_size,
                    utc_now(),
                ],
            )
            conn.execute(
                "UPDATE objects SET digitization_status=?, updated_at=? WHERE id=?",
                ["Complete", utc_now(), object_id],
            )
            conn.execute(
                "INSERT INTO audit_logs (actor, action, entity_type, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                [user["username"], "upload_media", "object", str(object_id), filename, utc_now()],
            )
            return self.respond_json({"ok": True, "media": get_media(conn, object_id)})

    def add_media_link(self, path: str) -> None:
        user = self.require_admin()
        if not user:
            return
        object_id = self.object_id_from_media_path(path, "media-link")
        if not object_id:
            return self.respond_json({"error": "Invalid media link path"}, 404)
        data = self.parse_json_body()
        url = str(data.get("google_drive_url", "")).strip()
        if not url:
            return self.respond_json({"error": "Google Drive demo URL is required"}, 400)
        filename = clean_filename(str(data.get("filename") or "google-drive-file"))
        derivative_type = str(data.get("derivative_type") or "working_copy")
        with connect() as conn:
            if not conn.execute("SELECT id FROM objects WHERE id=?", [object_id]).fetchone():
                return self.respond_json({"error": "Object not found"}, 404)
            conn.execute(
                """
                INSERT INTO digital_media (
                  object_id, filename, original_filename, media_type, derivative_type,
                  storage_provider, google_drive_url, created_at
                )
                VALUES (?, ?, ?, ?, ?, 'google_drive_demo', ?, ?)
                """,
                [
                    object_id,
                    filename,
                    filename,
                    str(data.get("media_type") or "application/octet-stream"),
                    derivative_type,
                    url,
                    utc_now(),
                ],
            )
            conn.execute(
                "INSERT INTO audit_logs (actor, action, entity_type, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                [user["username"], "add_google_drive_link", "object", str(object_id), url, utc_now()],
            )
            return self.respond_json({"ok": True, "media": get_media(conn, object_id)})

    def handle_media_download(self, path: str) -> None:
        user = self.require_user()
        if not user:
            return
        try:
            media_id = int(path.removeprefix("/local-media/"))
        except ValueError:
            return self.respond_json({"error": "Invalid media id"}, 400)
        with connect() as conn:
            row = conn.execute(
                """
                SELECT m.*, o.rights, o.permanent_id
                FROM digital_media m
                JOIN objects o ON o.id = m.object_id
                WHERE m.id=?
                """,
                [media_id],
            ).fetchone()
            if not row:
                return self.respond_json({"error": "Media not found"}, 404)
            if row["rights"] == "Restricted" and user["role"] != "admin":
                return self.respond_json({"error": "Restricted media requires admin permission"}, 403)
            if row["storage_provider"] != "local":
                return self.respond_json({"error": "Media is not stored locally"}, 400)
            media_path = (ROOT / row["local_path"]).resolve()
            if ROOT not in media_path.parents:
                return self.respond_json({"error": "Forbidden"}, 403)
            if not media_path.exists():
                return self.respond_json({"error": "Local file missing"}, 404)
            data = media_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", row["media_type"] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f'attachment; filename="{row["filename"]}"')
            self.end_headers()
            self.wfile.write(data)


def save_object(
    conn: sqlite3.Connection,
    data: Dict[str, Any],
    actor: str,
    update: bool = False,
) -> int:
    required = ["permanent_id", "title", "object_type"]
    for key in required:
        if not str(data.get(key, "")).strip():
            raise ValueError(f"{key} is required")

    now = utc_now()
    collection_id = ensure_named_collection(conn, data.get("collection"))
    storage_location_id = ensure_storage_location_path(conn, data.get("storage_location"))
    date_start = int(data["date_start"]) if str(data.get("date_start", "")).strip() else None
    date_end = int(data["date_end"]) if str(data.get("date_end", "")).strip() else date_start

    base_columns = [
        "permanent_id",
        "title",
        "description",
        "object_type",
        "date_label",
        "date_start",
        "date_end",
        "language",
        "rights",
        "provenance",
        "condition",
        "digitization_status",
        "collection_id",
        "storage_location_id",
    ]
    base_values = [
        clean_text(data["permanent_id"]),
        clean_text(data["title"]),
        clean_text(data.get("description")),
        clean_text(data["object_type"]),
        clean_text(data.get("date_label")),
        date_start,
        date_end,
        clean_text(data.get("language")),
        clean_text(data.get("rights")),
        clean_text(data.get("provenance")),
        clean_text(data.get("condition")),
        clean_text(data.get("digitization_status")),
        collection_id,
        storage_location_id,
    ]
    all_columns = base_columns + EXTENDED_FIELD_NAMES
    values = base_values + [object_field_value(field, data) for field in EXTENDED_FIELD_NAMES]

    previous_location_id = None
    if update:
        object_id = int(data["id"])
        row = conn.execute("SELECT storage_location_id FROM objects WHERE id=?", [object_id]).fetchone()
        if not row:
            raise ValueError("Object not found")
        previous_location_id = row["storage_location_id"]
        set_clause = ", ".join(f"{column}=?" for column in all_columns)
        conn.execute(
            f"UPDATE objects SET {set_clause}, updated_at=? WHERE id=?",
            values + [now, object_id],
        )
        conn.execute("DELETE FROM object_authorities WHERE object_id=?", [object_id])
        conn.execute("DELETE FROM object_terms WHERE object_id=?", [object_id])
        action = "update_object"
    else:
        insert_columns = all_columns + ["created_at", "updated_at"]
        placeholders = ", ".join("?" for _ in insert_columns)
        conn.execute(
            f"INSERT INTO objects ({', '.join(insert_columns)}) VALUES ({placeholders})",
            values + [now, now],
        )
        object_id = int(conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])
        action = "create_object"

    if storage_location_id and previous_location_id != storage_location_id:
        conn.execute(
            "INSERT INTO movements (object_id, from_location_id, to_location_id, moved_at, note) VALUES (?, ?, ?, ?, ?)",
            [object_id, previous_location_id, storage_location_id, now, "Location set from catalog form."],
        )

    save_relationship_inputs(conn, object_id, data)
    save_term_inputs(conn, object_id, data)
    conn.execute(
        "INSERT INTO audit_logs (actor, action, entity_type, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        [actor, action, "object", str(object_id), str(data.get("permanent_id")), now],
    )
    return object_id


def ensure_named_collection(conn: sqlite3.Connection, name: Any) -> Optional[int]:
    value = str(name or "").strip()
    if not value:
        return None
    return get_or_create(conn, "collections", {"name": value}, {"description": ""})


def ensure_storage_location_path(conn: sqlite3.Connection, path_value: Any) -> Optional[int]:
    value = str(path_value or "").strip()
    if not value:
        return None
    parent_id = None
    location_type_order = ["Repository", "Room", "Cabinet", "Shelf", "Box", "Folder"]
    parts = [part.strip() for part in value.replace("\u2192", "/").replace("->", "/").split("/") if part.strip()]
    for index, part in enumerate(parts):
        location_type = location_type_order[min(index, len(location_type_order) - 1)]
        parent_id = get_or_create(
            conn,
            "storage_locations",
            {"name": part, "parent_id": parent_id},
            {"location_type": location_type, "code": ""},
        )
    return parent_id


def split_values(value: Any) -> List[str]:
    if isinstance(value, list):
        values = value
    else:
        values = str(value or "").replace(";", ",").split(",")
    return [str(item).strip() for item in values if str(item).strip()]


def save_relationship_inputs(conn: sqlite3.Connection, object_id: int, data: Dict[str, Any]) -> None:
    mapping = [
        ("creators", "Person", "creator"),
        ("people", "Person", "person"),
        ("organizations", "Organization", "organization"),
        ("places", "Place", "place"),
        ("events", "Event", "event"),
    ]
    for field, authority_type, role in mapping:
        for name in split_values(data.get(field)):
            authority_id = get_or_create(
                conn,
                "authorities",
                {"type": authority_type, "name": name},
                {"description": "", "aliases": "", "external_uri": ""},
            )
            conn.execute(
                "INSERT OR IGNORE INTO object_authorities (object_id, authority_id, role) VALUES (?, ?, ?)",
                [object_id, authority_id, role],
            )


def save_term_inputs(conn: sqlite3.Connection, object_id: int, data: Dict[str, Any]) -> None:
    mapping = [
        ("object_type", "Object Type"),
        ("resource_type", "Resource Type"),
        ("genre_form", "Genre/Form"),
        ("subjects", "Subject"),
        ("language", "Language"),
        ("rights", "Rights"),
        ("access_rights", "Access Rights"),
        ("condition", "Condition"),
        ("digitization_status", "Digitization Status"),
        ("metadata_profile", "Metadata Standard"),
        ("theater", "Theater"),
        ("campaign", "Campaign"),
        ("battle", "Battle"),
    ]
    for field, vocabulary in mapping:
        for term in split_values(data.get(field)):
            term_id = get_or_create(
                conn,
                "taxonomy_terms",
                {"vocabulary": vocabulary, "term": term},
                {"parent_id": None},
            )
            conn.execute(
                "INSERT OR IGNORE INTO object_terms (object_id, term_id) VALUES (?, ?)",
                [object_id, term_id],
            )
    formal_term = "True" if truthy(data.get("formal_test_data")) else "False"
    term_id = get_or_create(
        conn,
        "taxonomy_terms",
        {"vocabulary": "Formal Test Data", "term": formal_term},
        {"parent_id": None},
    )
    conn.execute(
        "INSERT OR IGNORE INTO object_terms (object_id, term_id) VALUES (?, ?)",
        [object_id, term_id],
    )


def main() -> None:
    init_db()
    port = int(os.environ.get("ARCHIVE_PORT", "8787"))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), ArchiveHandler)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            print(
                f"Port {port} is already in use. If the demo is already running, open "
                f"http://127.0.0.1:{port}. To start a second copy, run "
                f"ARCHIVE_PORT={port + 1} python3 app.py",
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        if exc.errno == errno.EPERM:
            print(
                f"Could not bind to http://127.0.0.1:{port}. Check local security or sandbox "
                "settings, or run the command from a normal terminal.",
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        raise
    print(f"{APP_NAME} running at http://127.0.0.1:{port}")
    print("Demo accounts: admin/admin and viewer/viewer")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down")
        server.server_close()


if __name__ == "__main__":
    main()
