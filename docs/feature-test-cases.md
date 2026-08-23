# Archive Collection System Feature Test Cases

Version: 0.1  
Target URL: `http://127.0.0.1:8787`  
Test accounts:

| Role | Username | Password |
| --- | --- | --- |
| Admin | `admin` | `admin` |
| Viewer | `viewer` | `viewer` |

Use this document for manual user acceptance testing and lightweight regression testing.

## 1. Authentication And Session

| ID | Feature | Steps | Expected Result |
| --- | --- | --- | --- |
| AUTH-01 | Admin login | Open site, enter `admin` / `admin`, click Sign in. | App opens to Catalog. User card shows `admin`. Admin actions are enabled. |
| AUTH-02 | Viewer login | Sign out, enter `viewer` / `viewer`, click Sign in. | App opens to Catalog. User card shows `viewer`. Edit, upload, Drive link, and backup controls are disabled. |
| AUTH-03 | Invalid login | Enter wrong password for `admin`. | Login stays visible and displays an invalid credentials error. |
| AUTH-04 | Logout | Log in, click Sign out. | Login screen appears; catalog UI is hidden. |
| AUTH-05 | Unauthenticated API protection | In a private session, request `/api/objects`. | API returns authentication required. |

## 2. Catalog Search And Browse

| ID | Feature | Steps | Expected Result |
| --- | --- | --- | --- |
| CAT-01 | Catalog loads | Log in as either account. | Catalog shows seeded records and summary metrics for Objects, Authorities, Media, and Locations. |
| CAT-02 | Keyword search | Search `Manila`. | Results include `Soldier portrait, Manila` and other records containing Manila in metadata. |
| CAT-03 | Object type filter | Select Object Type `Photograph`. | Results only show photograph records. |
| CAT-04 | Place filter | Select Place `Manila`. | Results only show records linked to Manila authority. |
| CAT-05 | Event filter | Select Event `Battle of Manila`. | Results only show records linked to that event. |
| CAT-06 | Subject filter | Select Subject `WWII`. | Results only show records tagged with WWII. |
| CAT-07 | Rights filter | Select Rights `Restricted`. | Results only show restricted records. |
| CAT-08 | Date range | Enter Date from `1941` and Date to `1945`. | Results only include records whose normalized date range overlaps 1941-1945. |
| CAT-09 | Combined filters | Search `Manila`, select Photograph, set 1941-1945. | Result set narrows to matching records only. |
| CAT-10 | Clear filters | Click Clear. | All filters reset and the full result set returns. |
| CAT-11 | Resource Type filter | Select Resource Type `Letter`. | Results only show records whose resource type is Letter. |
| CAT-12 | Campaign filter | Select Campaign `Philippines Campaign`. | Results only show records tagged to that campaign. |
| CAT-13 | Formal test data filter | Select Formal Test `Formal test data`. | Result count shows the generated `TEST-PW-*` fixture records. |
| CAT-14 | NMPWA reference search | Search `NMPWA`. | Results include generated records with NMPWA-inspired source, citation, and metadata JSON. |

## 3. Record Detail And Read-only Viewing

| ID | Feature | Steps | Expected Result |
| --- | --- | --- | --- |
| DETAIL-01 | Select record as admin | Log in as admin and click `MNA-000123` in the result list. | Detail panel displays title, description, rights, collection, physical location, relationships, taxonomy, and media. |
| DETAIL-02 | Relationship display | Open a record with Person, Organization, Place, and Event links. | Relationship pills show separate authority types, not just plain tags. |
| DETAIL-03 | Taxonomy display | Open a record with Subject and Object Type terms. | Taxonomy pills show vocabulary and term values. |
| DETAIL-04 | Viewer cannot edit | Log in as viewer and select any record. | No Edit button is visible, and Record tab form controls are disabled. |
| DETAIL-05 | Admin can edit from detail | Log in as admin, select a record, click Edit. | Record tab opens with that record's fields populated. |
| DETAIL-06 | Extended metadata display | Open `TEST-PW-0001` as admin. | Detail panel shows Dublin Core / DCMI fields, Pacific War fields, identifiers, notes, links, and metadata JSON. |
| DETAIL-07 | Viewer stewardship boundary | Log in as viewer and open a record with physical location, internal note, preservation note, metadata JSON, and checksums. | Viewer detail/API payload hides physical location, internal note, preservation note, metadata JSON, media local path, original filename, and checksum. |

## 4. Object Create And Edit

| ID | Feature | Steps | Expected Result |
| --- | --- | --- | --- |
| OBJ-01 | Create minimum record | As admin, open Record tab, click New, enter Permanent ID, Title, Object Type, click Save. | New object is saved and appears in Catalog. |
| OBJ-02 | Required validation | As admin, try saving with missing Permanent ID, Title, or Object Type. | Browser or API prevents save and indicates required fields. |
| OBJ-03 | Duplicate ID protection | Create a record using an existing Permanent ID, e.g. `MNA-000123`. | Save fails with uniqueness error. |
| OBJ-04 | Edit record | As admin, edit title or description of an existing record and save. | Updated metadata appears in Catalog and Detail. |
| OBJ-05 | Create new authority values | Create or edit a record with a new Place and Event. | New authority values appear in Authorities tab and search filters after refresh. |
| OBJ-06 | Create new taxonomy terms | Save a record with a new Subject or Rights value. | New term appears in Taxonomy tab and relevant filters. |
| OBJ-07 | Viewer write protection | As viewer, try to create a record through the disabled UI or POST `/api/objects`. | UI blocks interaction and API returns admin permission required. |
| OBJ-08 | Create extended metadata | As admin, create a record with Publisher, Source, Resource Type, Genre/Form, Campaign, Battle, ARK, IIIF Manifest URL, Access Rights, and Formal Test Data checked. | Record saves, extended fields appear in detail, search finds the values, and taxonomy terms are created where applicable. |

## 5. Authorities And Taxonomy

| ID | Feature | Steps | Expected Result |
| --- | --- | --- | --- |
| AUTHORITY-01 | Authority tab loads | Open Authorities tab. | People, Organizations, Places, and Events are grouped separately. |
| AUTHORITY-02 | Creator authority | Inspect `John Smith`. | It appears under Person, not Subject. |
| AUTHORITY-03 | Organization authority | Inspect `U.S. Army`. | It appears under Organization and is searchable through organization metadata. |
| TAX-01 | Taxonomy tab loads | Open Authorities tab and view Taxonomy panel. | Terms are grouped by vocabulary such as Object Type, Subject, Rights, Language, Condition, Digitization Status. |
| TAX-02 | Subject term quality | Confirm `WWII` and `Pacific Theater`. | They appear as Subject terms and can be used as search facets. |
| TAX-03 | Pacific War taxonomy | Inspect vocabularies for Resource Type, Genre/Form, Theater, Campaign, Battle, Metadata Standard, Data Source, and Formal Test Data. | NMPWA-inspired terms are available for filtering, display, and record creation. |

## 6. Physical Storage

| ID | Feature | Steps | Expected Result |
| --- | --- | --- | --- |
| STORAGE-01 | Storage tab loads for admin | Log in as admin and open Storage tab. | Storage locations display full hierarchical paths. |
| STORAGE-02 | Location path from form | As admin, save a record with `Main Repository / Room 1 / Cabinet B / Box 1`. | New path appears in Storage tab and record detail. |
| STORAGE-03 | Current location display | As admin, select a record with physical location. | Detail panel shows full path, not a flat note only. |
| STORAGE-04 | Viewer storage protection | Log in as viewer and open Storage tab or call `/api/storage-locations`. | UI shows admin access required and API returns admin permission required. |

## 7. Digital Media

| ID | Feature | Steps | Expected Result |
| --- | --- | --- | --- |
| MEDIA-01 | Media list display | Open `MNA-000123` as admin. | Detail panel lists local media files with derivative type, provider, size, and SHA-256 preview. |
| MEDIA-02 | Local file upload | As admin, open Admin tab, choose an object, select derivative type, upload a file. | File appears in the object's media list and is stored under `storage/archive-master/{Permanent ID}/`. |
| MEDIA-03 | Checksum generation | Upload a local file as admin. | Admin media row includes a SHA-256 checksum value. |
| MEDIA-04 | Local download allowed | As viewer, open a public or research-use media file and click Download. | File downloads or displays. |
| MEDIA-05 | Restricted download blocked | As viewer, open restricted object media, e.g. `MNA-000302` transcript. | Download is blocked with restricted permission error. |
| MEDIA-06 | Restricted download allowed for admin | As admin, open restricted object media. | Admin can download local file. |
| MEDIA-07 | Google Drive demo link | As admin, attach a Google Drive URL to an object. | Detail panel shows external Drive link as `google_drive_demo` media. |
| MEDIA-08 | Viewer can see Drive link metadata | As viewer, open a record with Drive demo link. | Link is visible as metadata. Access depends on Google Drive permissions outside this app. |
| MEDIA-09 | Viewer checksum protection | As viewer, open a record with local media. | Media row shows descriptive media metadata and allowed download action, but not SHA-256, local path, or original filename. |

## 8. AI Intake Review

| ID | Feature | Steps | Expected Result |
| --- | --- | --- | --- |
| INTAKE-01 | Batch upload for review | As admin, open Admin tab, choose one or more image/PDF files under AI Intake Review, and click Upload for Review. | Each file creates an intake draft in `needs_review` status and is staged under `storage/intake/{Intake ID}/`. |
| INTAKE-02 | Mock AI suggestions | Upload a file named with a year, e.g. `manila-photo-1945.jpg`. | Draft fields are prefilled with title, object type, date, rights, resource type, subjects, notes, and `metadata_json` analyzer metadata. |
| INTAKE-03 | Save review edits | Select an intake draft, change title, description, rights, or metadata fields, then click Save Draft. | Draft remains `needs_review`; refreshed draft shows the curator-edited values. |
| INTAKE-04 | Submit as new object | Select an intake draft, choose Create new object, revise fields, and submit. | A new object is created, the staged file is copied to `storage/archive-master/{Permanent ID}/`, media is attached, and intake status becomes `submitted`. |
| INTAKE-05 | Submit to existing object | Select an intake draft, choose Attach to existing object, select an object and derivative type, then submit. | No new object is created; the staged file is attached to the selected object as local digital media. |
| INTAKE-06 | Reject draft | Select a draft and click Reject with a reason. | Intake status becomes `rejected`; no object or media row is created. |
| INTAKE-07 | Viewer protection | Sign in as viewer and open Admin tab or call intake APIs directly. | Intake controls are disabled in the UI and API calls require admin permission. |
| INTAKE-08 | Intake audit | Upload, edit, submit, or reject an intake draft. | Audit includes `intake_upload`, `intake_update`, `intake_submit`, or `intake_reject`. |

## 9. Backup And Preservation

| ID | Feature | Steps | Expected Result |
| --- | --- | --- | --- |
| BACKUP-01 | Generate backup | As admin, open Admin tab and click Generate Backup. | A new backup folder appears under `backups/archive_backup_{timestamp}/`. |
| BACKUP-02 | Backup contents | Inspect the generated backup folder. | Folder contains `archive.db`, `metadata_export.json`, `taxonomy_export.json`, and `checksums.json`. |
| BACKUP-03 | Viewer backup protection | As viewer, open Admin tab. | Backup button is disabled and permission note is visible. |
| BACKUP-04 | Backup audit | Generate backup as admin, inspect Audit list. | Audit includes a `backup` event with timestamp and actor. |

## 10. Audit Log

| ID | Feature | Steps | Expected Result |
| --- | --- | --- | --- |
| AUDIT-01 | Seed audit | Open Admin tab as admin. | Audit includes initial `seed` event. |
| AUDIT-02 | Create audit | Create a new object. | Audit includes `create_object` with actor `admin`. |
| AUDIT-03 | Update audit | Edit an object. | Audit includes `update_object`. |
| AUDIT-04 | Media audit | Upload local file or attach Drive link. | Audit includes `upload_media` or `add_google_drive_link`. |
| AUDIT-05 | Intake audit | Use the AI Intake Review flow. | Audit includes intake actions with actor, entity ID, details, and timestamp. |

## 11. API Smoke Tests

Run these while the server is active.

```bash
curl -s http://127.0.0.1:8787/api/me
```

Expected: unauthenticated response when no cookie is present.

```bash
curl -s -c /tmp/archive-admin-cookie \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}' \
  http://127.0.0.1:8787/api/login
```

Expected: admin user payload.

```bash
curl -s -b /tmp/archive-admin-cookie \
  'http://127.0.0.1:8787/api/objects?query=Manila&object_type=Photograph&date_from=1941&date_to=1945'
```

Expected: records matching Manila, Photograph, and 1941-1945.

```bash
curl -s -b /tmp/archive-admin-cookie \
  'http://127.0.0.1:8787/api/objects?formal_test_data=true&resource_type=Letter'
```

Expected: generated `TEST-PW-*` records only, all with `formal_test_data` set to `true` and `resource_type` set to `Letter`.

```bash
curl -s -b /tmp/archive-admin-cookie \
  'http://127.0.0.1:8787/api/objects?query=NMPWA&campaign=Philippines%20Campaign'
```

Expected: formal test records with NMPWA-inspired source metadata and `campaign` set to `Philippines Campaign`.

```bash
curl -s -c /tmp/archive-viewer-cookie \
  -H 'Content-Type: application/json' \
  -d '{"username":"viewer","password":"viewer"}' \
  http://127.0.0.1:8787/api/login
```

Expected: viewer user payload.

```bash
curl -s -b /tmp/archive-viewer-cookie \
  'http://127.0.0.1:8787/api/objects/MNA-000123'
```

Expected: object payload does not include `storage_location_path`, `internal_note`, `preservation_note`, `metadata_json`, media `local_path`, media `original_filename`, or media `checksum_sha256`.

```bash
curl -s -b /tmp/archive-viewer-cookie \
  -H 'Content-Type: application/json' \
  -d '{"permanent_id":"MNA-999999","title":"Should Fail","object_type":"Photograph"}' \
  http://127.0.0.1:8787/api/objects
```

Expected: `Admin permission required`.

## 12. Suggested Release Acceptance Criteria

V1 is acceptable when:

| Requirement | Pass condition |
| --- | --- |
| Local hosting | Site runs at `http://127.0.0.1:8787` with `python3 app.py`. |
| Admin account | `admin/admin` can perform all write operations. |
| Viewer account | `viewer/viewer` can search and view but cannot write. |
| Metadata | Object records support ID, title, type, collection, dates, language, rights, provenance, condition, digitization status, authorities, subjects, admin-only location, Dublin Core / DCMI fields, identifiers, access fields, and Pacific War fields. |
| Physical storage | Hierarchical locations are visible and searchable for admins; viewer catalog/API responses hide storage paths. |
| Digital storage | Local files are stored under permanent-ID folders and have admin-visible checksums. |
| Google Drive demo | Drive URLs can be attached as non-canonical working links. |
| Search | Keyword, type, resource type, collection, place, event, subject, rights, campaign, formal test data, and date range filters work. |
| Seed fixtures | 100 generated `TEST-PW-*` records exist and are tagged `Formal Test Data = True`. |
| Backup | Admin can generate database, metadata, taxonomy, and checksum exports. |
| Audit | Important admin actions are logged. |
