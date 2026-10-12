# Step 0 — Archive Collection System Local V1 Demo

This folder preserves the earlier archive collection management prototype based on the V1 technical design. It remains an independently runnable local demo. The separate [Step 1 discovery app](../step1/README.md) handles cross-platform archival discovery; it does not depend on this app or its database.

Use Python **3.9–3.12** for this legacy app. It imports the standard-library `cgi` module, which is no longer available in Python 3.13; Python 3.13+ is not currently supported here.

It uses only Python standard-library modules:

- `http.server` backend
- `sqlite3` catalog database
- local folders for canonical demo digital storage
- Google Drive URL fields as a no-cloud demo adapter
- static HTML/CSS/JavaScript frontend

## Run

First check whether the demo is already running:

```bash
curl -s http://127.0.0.1:8787/api/me
```

If this returns JSON, open the app directly:

```text
http://127.0.0.1:8787
```

If nothing is running yet, start the server from the repository root:

```bash
python3 step0/app.py
```

Alternatively, enter this app's folder first:

```bash
cd step0
python3 app.py
```

Then open:

```text
http://127.0.0.1:8787
```

If port `8787` is already in use, check the service at the link above. To run on another port, use this command from the repository root:

```bash
ARCHIVE_PORT=8788 python3 step0/app.py
```

The server binds to `127.0.0.1` for local use. Stop it with **Ctrl+C**. Step 0's default port `8787` and Step 1's default port `8000` can run at the same time. Paths in the documentation below are relative to `step0/` unless stated otherwise.

## Demo Accounts

| Username | Password | Role |
| --- | --- | --- |
| `admin` | `admin` | Can create/edit records, upload local media, attach Google Drive demo links, and generate backups |
| `viewer` | `viewer` | Read-only catalog/search/view access with internal storage, audit, and preservation metadata hidden |

## Local Data

Runtime data is created under `step0/` on first launch, regardless of the shell's working directory:

```text
data/archive.db
storage/archive-master/{Permanent ID}/
storage/intake/{Intake ID}/
backups/archive_backup_{timestamp}/
```

The seed dataset includes Pacific War example records, NMPWA-inspired reference collections, authority entities, taxonomy terms, physical storage locations, placeholder digital media, and 100 generated formal test records tagged with `Formal Test Data = True`.

### Existing local data after the folder move

This repository reorganization moves committed application files only. Existing local `data/`, `storage/`, and `backups/` directories are ignored by Git and are not included or automatically moved. A fresh launch without the old database creates the demo seed data rather than loading the previous catalog.

To retain an existing local catalog:

1. Stop the old server and any Step 0 server so the database and media remain consistent.
2. Back up the complete old `data/`, `storage/`, and `backups/` directories together to a separate location.
3. Copy those directories into `step0/`, retaining their names and internal paths. The result should include `step0/data/archive.db`, `step0/storage/archive-master/`, `step0/storage/intake/`, and `step0/backups/`. The database stores media paths relative to the app folder, so the database and storage directories must stay together.
4. If Step 0 has already been launched, keep a separate backup of its new runtime directories before restoring the old set. Do not merge or overwrite two catalogs without first deciding which data to retain.
5. Start Step 0, verify familiar records and local media, and keep the original backup until verification is complete.

The folder move does not migrate local data into Step 1 or change the old database schema.

## V1 Scope

Supported in this demo:

- Physical object records
- Digital media attachments
- AI Intake review queue for batch local uploads and curator approval before submit
- Local canonical file storage
- Local intake staging storage with mock AI metadata suggestions
- Google Drive link references without cloud credentials
- Permanent identifiers
- Collection membership
- People, organizations, places, and events as authority records
- Taxonomy terms
- Dublin Core / DCMI Terms fields
- UNTL-inspired Pacific War metadata fields
- Formal test data filter for generated fixtures
- Physical storage hierarchy
- Structured metadata search and filters
- Role-based admin/viewer permissions, including viewer-safe catalog payloads
- Backup export containing database copy, metadata JSON, taxonomy JSON, and checksums

Deferred:

- Real Google Drive API sync
- Real OCR or vision-model analysis for intake drafts
- AWS S3
- CollectiveAccess import/export mappings
- Public discovery portal
- IIIF image server
- Preservation workflow integrations

## Documentation

- [Repository overview](../README.md)
- [V1 Technical Design](pacific-war-dam-product-technical-design.html)
- [Metadata User Manual](docs/metadata-user-manual.md)
- [Taxonomy And Metadata Reference](docs/taxonomy-metadata-reference.md)
- [Feature Test Cases](docs/feature-test-cases.md)
