# Archive Collection System — Local V1 Demo

This repository contains a locally hosted archive collection management demo based on the V1 technical design.

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

If nothing is running yet, start the server:

```bash
python3 app.py
```

Then open:

```text
http://127.0.0.1:8787
```

If port `8787` is already in use, the demo is probably already running at the link above. To run a second copy, choose another port:

```bash
ARCHIVE_PORT=8788 python3 app.py
```

## Demo Accounts

| Username | Password | Role |
| --- | --- | --- |
| `admin` | `admin` | Can create/edit records, upload local media, attach Google Drive demo links, and generate backups |
| `viewer` | `viewer` | Read-only catalog/search/view access with internal storage, audit, and preservation metadata hidden |

## Local Data

Runtime data is created on first launch:

```text
data/archive.db
storage/archive-master/{Permanent ID}/
storage/intake/{Intake ID}/
backups/archive_backup_{timestamp}/
```

The seed dataset includes Pacific War example records, NMPWA-inspired reference collections, authority entities, taxonomy terms, physical storage locations, placeholder digital media, and 100 generated formal test records tagged with `Formal Test Data = True`.

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

- [Metadata User Manual](docs/metadata-user-manual.md)
- [Taxonomy And Metadata Reference](docs/taxonomy-metadata-reference.md)
- [Feature Test Cases](docs/feature-test-cases.md)
