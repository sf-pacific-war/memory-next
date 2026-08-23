# Archive Collection System Taxonomy And Metadata Reference

Version: 0.1  
Audience: collection owner, archivist, metadata cataloger, researcher, product owner, and developer.

This document is the shared reference for the taxonomy and metadata layer of the Pacific War archive demo. It answers two related questions:

1. What can collection staff describe, browse, and maintain?
2. What should developers preserve in the data model, API, import/export code, and search logic?

The system is intentionally simple in V1, but the metadata profile is designed so it can grow toward a professional archive, digital humanities portal, or DAM-backed collection platform.

## 1. Current Capability Summary

The current system supports four major collection-management capabilities.

| Capability | Current status | User value | Developer note |
| --- | --- | --- | --- |
| Metadata fields | Enabled | Staff can describe letters, photos, maps, oral histories, documents, and reference materials with Dublin Core / DCMI and Pacific War-specific fields. | Fields are stored on `objects`; relationships and taxonomy stay normalized. |
| Thematic collections | Enabled | Staff can group records into Pearl Harbor, Women in War, WWII Documents, Nimitz, Oral History, maps, and reference collections. | Collections are separate records, not just text labels. |
| Search entry | Enabled | Users can search by keyword and filter by collection, object type, resource type, place, event, subject, rights, campaign, date, and formal test data. | Search currently uses SQLite-backed API filtering; future full-text/OCR search can layer on top. |
| Ongoing updates | Manual in V1 | Admin users can add, edit, upload, and update metadata over time. | Automated NMPWA/Portal harvest is a V1.1/V2 pipeline, not automatic yet. |

The seeded dataset includes 100 generated fixture records with IDs `TEST-PW-0001` through `TEST-PW-0100`. These are intentionally tagged `Formal Test Data = True` so QA, import/export work, and UI demos do not mix generated records with real holdings.

## 2. Audience-Specific Views

### For Collection Staff

Focus on stable cataloging practices:

| Task | Use these parts of the system |
| --- | --- |
| Add a new item | Record tab, Permanent ID, Title, Object Type, Collection, Description, Rights, Location |
| Describe a letter | Resource Type `Letter`, Genre/Form `Correspondence`, creator/recipient people, date, place, transcription/OCR media |
| Describe a photograph | Resource Type `Photograph`, visible people/places/events, physical description, rights, thumbnail/access image |
| Describe a map | Resource Type `Map`, coverage spatial, campaign, battle, scale/projection note in metadata JSON |
| Describe oral history | Resource Type `Sound`, person authority records, transcript media, interview event, access restrictions |
| Curate a topic | Collection, Series Title, Subcollection, Subject, Theater, Campaign, Battle |
| Control search quality | Use controlled vocabularies and authority records consistently |
| Separate real and test records | Leave real records unchecked; keep generated records checked as Formal Test Data |

### For Developers

Focus on data stability and interoperability:

| Concern | Design rule |
| --- | --- |
| Permanent IDs | Never derive identity from filenames, storage path, or external URLs. |
| Migrations | Add metadata fields without destructive schema changes. |
| Search | Keep structured filters distinct from free-text keyword matching. |
| Taxonomy | Store repeatable browse/filter values as terms, not hard-coded UI lists. |
| Authorities | Keep people, organizations, places, and events as entities, not loose tags. |
| Imports | Preserve raw source identifiers, item URLs, ARKs, and source metadata JSON. |
| Exports | Support simple Dublin Core and richer local JSON without losing internal fields. |
| Test data | Never let Formal Test Data records appear as production archival holdings by default in future public portals. |

## 3. Metadata Architecture

The system uses five metadata layers.

| Layer | Examples | Storage model | Why it exists |
| --- | --- | --- | --- |
| Core object metadata | Permanent ID, title, description, date, rights | `objects` columns | Fast display and editing |
| DCMI / interoperability metadata | publisher, source, relation, coverage, extent, medium, citation | `objects` columns | Cross-platform export and public discovery |
| Domain metadata | resource type, genre/form, theater, campaign, battle, unit, vessel | `objects` columns + taxonomy terms | Pacific War browse/search |
| Authority relationships | people, organizations, places, events | `authorities` + `object_authorities` | Reusable entities and relationship graph |
| Digital media metadata | filename, derivative type, MIME type, checksum, provider | `digital_media` | DAM, fixity, access control, preservation |

Recommended entity model:

```text
Object
  belongs to Collection
  has physical Storage Location
  has Digital Media
  links to Person / Organization / Place / Event authorities
  uses Taxonomy Terms for type, subject, rights, status, campaign, battle
```

Do not collapse all metadata into tags. Tags are useful for topical discovery, but they cannot reliably express creator roles, physical locations, source IDs, access policy, preservation status, or external interoperability fields.

## 4. Field Dictionary

### Required Fields

| Field | Required | Data type | Search/filter role | Export role |
| --- | --- | --- | --- | --- |
| Permanent ID | Yes | String | Exact ID lookup | `dc:identifier`, local ID |
| Title | Yes | String | Keyword, display title | `dc:title`, `dcterms:title` |
| Object Type | Yes | Controlled string | Facet/filter | `dc:type`, `dcterms:type` |

### Recommended Descriptive Fields

| Field | Data type | Example | Guidance |
| --- | --- | --- | --- |
| Description | Text | `Photograph of sailors on deck near Okinawa.` | Start with the item type when useful. Keep it factual. |
| Date Label | String | `circa 1944` | Human-readable display date. |
| Date Start | Integer year | `1944` | Normalized filtering start. |
| Date End | Integer year | `1945` | Normalized filtering end. |
| Language | Controlled string | `English`, `Japanese`, `No Language` | Language of the object content, not catalog UI. |
| Rights | Controlled string | `Public Domain`, `Research Use`, `Restricted` | Copyright/reuse summary. |
| Access Rights | Controlled string | `Public`, `Reading Room Only`, `Restricted` | Access/display policy. |
| Provenance | Text | `Donated by...` | Custodial history and acquisition note. |
| Citation | Text | `Pacific War Collection, MNA-000123.` | Preferred citation for researchers. |
| Physical Description | Text | `1 photograph : black-and-white ; 8 x 10 in.` | Physical format, dimensions, pages, or duration. |
| Extent | String | `4 pages`, `1 audio file` | Count, quantity, duration, or size. |
| Medium | String | `gelatin silver print`, `typescript` | Physical material or carrier. |

### DCMI / Cross-Platform Fields

| Local field | Dublin Core / DCMI mapping | Developer handling |
| --- | --- | --- |
| Alternative Title | `dcterms:alternative` | Repeatable later; V1 stores display text. |
| Publisher | `dc:publisher`, `dcterms:publisher` | Prefer Organization authority linkage in V2. |
| Contributors | `dc:contributor`, `dcterms:contributor` | Add roles later: interviewer, interviewee, donor, transcriber. |
| Source | `dc:source`, `dcterms:source` | Preserve source URL or donor/source collection text. |
| Relation | `dc:relation`, `dcterms:relation` | Use for related item, series, original/surrogate, or exhibit references. |
| Coverage Spatial | `dcterms:spatial` | Can duplicate Place authority for export text. |
| Coverage Temporal | `dcterms:temporal` | Use period labels such as `World War II, 1941-1945`. |
| License URI | `dcterms:license` | Store machine-readable rights URI when known. |
| ARK | `dc:identifier`, `dcterms:identifier` | Stable external persistent ID. |
| Item URL | `dc:identifier`, `schema:url` | Source item page or future public item page. |
| Thumbnail URL | UNTL identifier qualifier / schema image | Useful for public search cards. |
| IIIF Manifest URL | IIIF Presentation | Use for interoperable viewers. |

### Pacific War Domain Fields

| Field | Example values | Use |
| --- | --- | --- |
| Resource Type | Photograph, Letter, Sound, Map, Text, Video | Public-facing content category. |
| Genre/Form | Correspondence, Oral histories, Military maps, Photographic prints | More precise form or genre. |
| Series Title | Women in War Collection, Nimitz Family Collection | Intellectual grouping or series. |
| Subcollection | Pearl Harbor, WWII Documents, Oral History | Lower-level theme or source grouping. |
| Theater | Pacific Theater | High-level war theater. |
| Campaign | Philippines Campaign, Central Pacific Campaign, Okinawa Campaign | Campaign-level discovery facet. |
| Battle | Battle of Manila, Battle of Iwo Jima, Battle of Leyte Gulf | Battle or named operation. |
| Military Unit | U.S. Navy, U.S. Marine Corps, Fleet Radio Unit Pacific | Unit or military organization. |
| Vessel / Aircraft | USS Enterprise, B-24 Liberator | Named ship, aircraft, or vehicle. |
| Modern Country | Philippines, Japan, United States | Present-day geographic access. |
| Wartime Jurisdiction | Empire of Japan, Commonwealth of the Philippines | Period-accurate political context. |
| Subject Source | Local, UNTL-BS, LCSH-inspired, LCGFT-inspired | Metadata provenance for subject strings. |

## 5. Taxonomy Design

### Taxonomy Versus Authority

Use taxonomy terms for controlled categories. Use authority records for real-world entities.

| Should be taxonomy | Should be authority |
| --- | --- |
| Object Type | Person |
| Resource Type | Organization |
| Genre/Form | Place |
| Subject | Event |
| Theater | Military unit if it needs aliases or biography/history |
| Campaign | Ship or aircraft if it needs aliases and relationships |
| Rights | Donor or creator |
| Digitization Status | Interviewer or interviewee |

Good pattern:

```text
Object Type: Photograph
Resource Type: Photograph
Genre/Form: Photographic prints
Subject: WWII, Pacific Theater
People: Chester W. Nimitz
Organizations: U.S. Navy
Places: Pearl Harbor
Events: Attack on Pearl Harbor
```

Avoid:

```text
Subjects: Photograph, Chester W. Nimitz, U.S. Navy, Pearl Harbor, Attack on Pearl Harbor
```

### Seeded Vocabularies

| Vocabulary | Purpose | Example terms |
| --- | --- | --- |
| Object Type | Internal object category | Photograph, Letter, Map, Text, Sound, Physical Object |
| Resource Type | Public browse category modeled after portal-style discovery | Photograph, Text, Letter, Sound, Map, Video, Pamphlet |
| Genre/Form | Specific form/genre | Correspondence, Oral histories, Military maps |
| Subject | Topical discovery | WWII, Pacific Theater, Civilian Experience |
| Theater | Military theater | Pacific Theater |
| Campaign | Campaign facet | Philippines Campaign, Central Pacific Campaign, Okinawa Campaign |
| Battle | Named battle or operation | Battle of Manila, Battle of Midway |
| Language | Content language | English, Japanese, Chinese, No Language |
| Rights | Reuse/copyright status | Public Domain, Research Use, Restricted |
| Access Rights | Access/display policy | Public, Reading Room Only, Restricted |
| Condition | Physical condition | Good, Fair, Fragile |
| Digitization Status | Workflow state | Complete, Needs OCR Review, Needs Rights Review |
| Metadata Standard | Mapping/profile label | Dublin Core, DCMI Terms, UNTL-inspired local profile |
| Data Source | Origin/source system | NMPWA Reference, Local Accession, Donor Materials |
| Formal Test Data | Fixture marker | True, False |
| Historical Period | Broad era | World War II, 1941-1945 |

### Recommended Additions

Add these vocabularies when the project moves past V1:

| Vocabulary | Why |
| --- | --- |
| Relationship Role | Creator, donor, interviewer, interviewee, transcriber, publisher, subject, collector |
| Date Type | Creation, publication, coverage, digitization, acquisition, modification |
| Preservation Event Type | Ingest, checksum creation, fixity check, migration, derivative generation |
| Access Policy | Public metadata only, public download, reading room, staff only, embargoed |
| Rights Basis | Public domain, copyright owned, permission granted, fair use, unknown |
| OCR Status | Not needed, pending, complete, needs review, failed |
| Transcription Status | Not needed, pending, complete, needs review |
| Review Status | Draft, needs metadata review, approved, published, suppressed |
| Sensitivity | Standard, graphic content, personal information, donor restriction |

## 6. Taxonomy Governance

Taxonomy needs a light approval process, even in a small archive.

| Action | Who can do it | Rule |
| --- | --- | --- |
| Add routine local subject | Cataloger/admin | Add only if it improves search or grouping. |
| Add new top-level campaign/battle term | Metadata lead | Confirm spelling, scope, and hierarchy. |
| Rename term | Metadata lead + developer awareness | Preserve old value in redirect/alias later. |
| Merge duplicate terms | Metadata lead | Move records, then deprecate duplicate term. |
| Delete term | Avoid | Prefer deprecating so historical records remain understandable. |
| Add external vocabulary source | Metadata lead | Record source such as LCSH, LCGFT, TGN, AAT, local. |

Term quality rules:

| Rule | Example |
| --- | --- |
| Use singular/plural consistently by vocabulary. | `Photographic prints` as genre/form; `Photograph` as resource type. |
| Do not use acronyms without authority support. | Use `Fleet Radio Unit Pacific`; store `FRUPAC` as alias. |
| Do not duplicate object type as subject unless subject meaning is different. | A photo is Resource Type `Photograph`; subject might be `Naval battles`. |
| Prefer one canonical name for battles. | `Battle of Manila`, alias `Manila 1945`. |
| Keep period-sensitive place names available. | Modern Country `Philippines`; Wartime Jurisdiction `Commonwealth of the Philippines`. |

## 7. Collection And Topic Design

Thematic collections are user-facing routes into the archive. They are broader and more curated than raw subject tags.

Current seeded collection examples:

| Collection | Intended use |
| --- | --- |
| Pacific War Collection | General umbrella collection |
| National Museum of the Pacific War Digital Archive Reference | Benchmark/reference source modeled after NMPWA patterns |
| Pearl Harbor Collection | Pearl Harbor-specific objects, oral histories, documents |
| Women in War Collection | Women's military, labor, home front, and support roles |
| WWII Documents Collection | Orders, reports, official documents, pamphlets |
| Nimitz Family Collection | Chester W. Nimitz and related family/reference material |
| National Museum of the Pacific War Oral History Collection | Interviews, transcripts, and audio |
| Fleet Radio Unit Pacific Map Collection | Maps, radio intelligence, operational geography |
| Pacific War Reference Materials | Bibliographies, reference summaries, test imports, contextual resources |

Recommended future collection fields:

| Field | Why |
| --- | --- |
| Collection code | Stable import/export identifier, e.g. `NMPWA`, `PEARL`, `ORAL`. |
| Collection description | Public explanation of scope. |
| Accrual policy | Whether new items are expected. |
| Accrual periodicity | How often new material is added. |
| Sponsor/partner | Museum, donor, archive partner, university. |
| Public visibility | Whether the collection can be shown externally. |

## 8. Search And Retrieval Design

### Current User Search

The current Catalog search supports:

| Search/browse path | Current behavior |
| --- | --- |
| Keyword | Searches title, description, ID, collection, authority names, aliases, taxonomy terms, media filenames, Drive URLs, and extended metadata fields. |
| Collection | Facet filter by collection name. |
| Object Type | Facet filter by internal type. |
| Resource Type | Facet filter by public resource type. |
| Place | Facet filter by authority. |
| Event | Facet filter by authority. |
| Subject | Facet filter by taxonomy term. |
| Rights | Facet filter by rights term. |
| Campaign | Facet filter by campaign term. |
| Formal Test Data | Include only fixture records or non-fixture records. |
| Date range | Filters by normalized start/end year overlap. |

### Current Read Access Boundary

The V1 demo separates viewer-safe catalog fields from stewardship fields. Viewer catalog and object API payloads do not include physical storage paths, internal notes, preservation notes, raw metadata JSON, media local paths, original filenames, or checksums. Storage-location and audit-log APIs are admin-only.

The Catalog default intentionally remains `All records` while this is a system demo with no real holdings loaded. Before public launch or production export, public views should default to excluding `Formal Test Data = True`.

### Current API Search

Useful API examples:

```text
GET /api/objects
GET /api/objects?query=Manila
GET /api/objects?object_type=Photograph
GET /api/objects?resource_type=Letter
GET /api/objects?campaign=Philippines%20Campaign
GET /api/objects?formal_test_data=true
GET /api/objects?date_from=1941&date_to=1945
GET /api/objects?query=NMPWA&campaign=Philippines%20Campaign
```

Suggested developer behavior for future public search:

| Search behavior | Recommendation |
| --- | --- |
| Exact ID lookup | Highest priority result. |
| Title match | Higher weight than description. |
| Authority match | Show related records and authority landing pages. |
| Subject match | Support browse pages by term. |
| OCR/transcript match | Searchable, but label as full-text hit. |
| Restricted media | Show metadata when allowed; hide/download-block files according to access policy. |
| Formal test data | Exclude by default from public views. |

## 9. NMPWA / Portal To Texas History Benchmark

The National Museum of the Pacific War Digital Archive in The Portal to Texas History is a strong benchmark because it combines public browse, rich item pages, programmatic APIs, OAI-PMH harvesting, IIIF manifests, and a qualified Dublin Core-derived local metadata profile.

Use the NMPWA public collection page as a dynamic source. Counts for items, photographs, letters, sound recordings, maps, languages, places, and included series change as digitization continues, so do not hard-code them in production UI. If a report needs counts, record the date of retrieval.

Known public patterns to model:

| Pattern | Local implication |
| --- | --- |
| Resource-type browse | Keep Resource Type distinct from file MIME type. |
| Collection and included series pages | Support collection/subcollection/series metadata. |
| Public item pages | Preserve Item URL, Thumbnail URL, ARK, and IIIF Manifest URL. |
| OAI-PMH `oai_dc` | Export simple Dublin Core for broad compatibility. |
| OAI-PMH `untl` | Preserve richer local fields for higher-fidelity exchange. |
| IIIF Presentation | Add future manifests for images, maps, and multi-page documents. |
| Search and OpenSearch | Add public search endpoints later. |
| Dynamic updates | Add a harvester job instead of manually rechecking pages. |

## 10. Import And Update Pipeline Design

V1 supports manual ongoing updates. Automated source tracking should be added in a later version.

### Proposed NMPWA/Portal Harvest Flow

```text
Schedule harvest
  -> call OAI-PMH ListRecords or Portal API
  -> store raw source metadata
  -> map to local fields
  -> dedupe by ARK / item URL / external identifier
  -> stage new or changed records
  -> review metadata diff
  -> approve import
  -> create/update local object
  -> attach source URLs and metadata JSON
  -> log audit event
```

### Import Status Values

Add these when automated import begins:

| Status | Meaning |
| --- | --- |
| `new_source_record` | Source item not yet imported. |
| `mapped_pending_review` | Raw source metadata mapped, needs human review. |
| `approved_for_import` | Reviewer approved staged record. |
| `imported` | Local object created. |
| `updated_from_source` | Existing local object updated from source. |
| `source_unchanged` | Source checked, no local change needed. |
| `mapping_error` | Source record could not be mapped safely. |
| `suppressed` | Do not import or display. |

### Dedupe Keys

Use these in order:

1. ARK
2. Source item URL
3. External identifier / source call number
4. Title + date + source collection + creator, only as a weak candidate

Never dedupe solely by title. Archival collections often contain many letters or photos with similar supplied titles.

## 11. Export Design

### Simple Dublin Core Export

Use for OAI-PMH compatibility and broad interoperability.

```json
{
  "dc:title": ["Letter formal test record 002: Battle of Midway"],
  "dc:creator": ["Doris Miller"],
  "dc:subject": ["WWII", "Pacific Theater", "Correspondence"],
  "dc:description": ["Formal test data record for Pacific War metadata..."],
  "dc:publisher": ["National Museum of the Pacific War / local demo seed"],
  "dc:date": ["1942"],
  "dc:type": ["Letter"],
  "dc:format": ["text/plain"],
  "dc:identifier": ["TEST-PW-0002", "ark:/99999/testpw0002"],
  "dc:source": ["https://texashistory.unt.edu/explore/collections/NMPWA/"],
  "dc:language": ["English"],
  "dc:coverage": ["Guadalcanal", "1942/1942"],
  "dc:rights": ["Public Domain"]
}
```

### Rich Local JSON Export

Use for round-tripping into this application or a future custom portal.

```json
{
  "schema": "archive_collection_system.v1",
  "object": {
    "permanent_id": "TEST-PW-0002",
    "title": "Letter formal test record 002: Battle of Midway",
    "resource_type": "Letter",
    "genre_form": "Correspondence",
    "campaign": "Central Pacific Campaign",
    "battle": "Battle of Midway",
    "formal_test_data": true
  },
  "authorities": {
    "people": ["Doris Miller"],
    "organizations": ["U.S. Marine Corps"],
    "places": ["Guadalcanal"],
    "events": ["Battle of Midway"]
  },
  "interop": {
    "source": "https://texashistory.unt.edu/explore/collections/NMPWA/",
    "ark": "ark:/99999/testpw0002",
    "iiif_manifest_url": "http://127.0.0.1:8787/iiif/3/TEST-PW-0002/manifest"
  }
}
```

## 12. Data Quality Rules

### Minimum Viable Record

Every real record should have:

| Field | Requirement |
| --- | --- |
| Permanent ID | Unique and stable. |
| Title | Specific enough to identify the item. |
| Object Type | Controlled value. |
| Resource Type | Controlled value for public browsing. |
| Description | Factual content summary. |
| Collection | At least one collection or accession grouping. |
| Rights | Known enough to guide reuse or access. |
| Access Rights | Known enough to control viewing/download. |
| Date Label | Present when known. |
| Location | Present for physical items. |
| Digital Media | Present for digitized items. |

### Recommended Record

For higher-quality public discovery, add:

| Area | Recommended metadata |
| --- | --- |
| People | Creator, depicted/mentioned people, interview participants |
| Organizations | Military branch, unit, publisher, donor/partner when appropriate |
| Places | Place authority plus coverage spatial text |
| Events | Battle, campaign, ceremony, interview, or accession event |
| Subjects | At least two useful subject terms |
| Physical description | Extent, medium, dimensions, page count, duration |
| Interop | Source, item URL, external ID, ARK, thumbnail, IIIF manifest |
| Preservation | Checksum, derivative type, preservation note |

### Common Metadata Smells

| Smell | Why it is risky | Better approach |
| --- | --- | --- |
| Title is `Photo` or `Scan 01` | Not searchable or citable. | Use supplied title: `Soldiers outside barracks, Saipan`. |
| People are only in Subjects | Loses role and authority reuse. | Add Person authority links. |
| Rights field is blank | Causes access uncertainty. | Use `Unknown` if truly unknown and flag for review. |
| Object Type says `Image` for a text letter scan | Confuses users filtering for letters. | Resource Type `Letter`; MIME type can be image/PDF. |
| Source URL stored only in notes | Hard to dedupe/import/export. | Use Source and Item URL fields. |
| Physical location in description only | Hard to inventory. | Use Physical Location hierarchy. |
| Test data mixed with real data | Public trust issue. | Keep `Formal Test Data = True` and filter out in production. |

## 13. Developer Implementation Notes

### Current Files

| File | Role |
| --- | --- |
| `app.py` | Python stdlib HTTP server, SQLite schema, seed data, API handlers, metadata save logic. |
| `static/index.html` | UI forms, filters, tabs, metadata field layout. |
| `static/app.js` | Client state, API calls, filtering UI, detail rendering. |
| `static/styles.css` | Layout and detail/table styling. |
| `docs/metadata-user-manual.md` | Cataloging and user-facing metadata manual. |
| `docs/taxonomy-metadata-reference.md` | Shared taxonomy, metadata, and developer reference. |
| `docs/feature-test-cases.md` | Manual QA and smoke tests. |

### Storage Boundaries

| Data | Current place | Future production place |
| --- | --- | --- |
| Catalog DB | `data/archive.db` | Managed database with backups |
| Digital files | `storage/archive-master/{Permanent ID}/` | S3 preservation bucket + derivatives bucket |
| Metadata exports | backup folder JSON | Scheduled export store |
| Test fixtures | same SQLite DB, marked formal test | Separate test/staging DB or explicit fixture namespace |

### API Parameters To Keep Stable

| Parameter | Meaning |
| --- | --- |
| `query` | Keyword search across descriptive, authority, taxonomy, media, and extended metadata fields. |
| `collection` | Collection name filter. |
| `object_type` | Internal object type filter. |
| `resource_type` | Public resource type filter. |
| `place` | Place authority filter. |
| `event` | Event authority filter. |
| `subject` | Subject taxonomy filter. |
| `rights` | Rights filter. |
| `campaign` | Campaign taxonomy/domain filter. |
| `date_from`, `date_to` | Year range overlap filter. |
| `formal_test_data` | `true` or `false` fixture filter. |

### Indexing Recommendations

As the dataset grows, add indexes for:

```sql
CREATE INDEX idx_objects_permanent_id ON objects(permanent_id);
CREATE INDEX idx_objects_object_type ON objects(object_type);
CREATE INDEX idx_objects_resource_type ON objects(resource_type);
CREATE INDEX idx_objects_campaign ON objects(campaign);
CREATE INDEX idx_objects_formal_test_data ON objects(formal_test_data);
CREATE INDEX idx_objects_date_range ON objects(date_start, date_end);
CREATE INDEX idx_object_terms_object_id ON object_terms(object_id);
CREATE INDEX idx_object_authorities_object_id ON object_authorities(object_id);
```

For OCR/transcripts, add a dedicated full-text table later instead of overloading object descriptions.

## 14. Security, Rights, And Ethical Notes

Pacific War collections can include graphic, traumatic, personal, military, or culturally sensitive materials.

| Concern | Metadata response |
| --- | --- |
| Copyright uncertainty | Use `Rights = Unknown` and `Access Rights = Restricted` or `Reading Room Only` until reviewed. |
| Donor restrictions | Store public-facing note separately from internal note. |
| Graphic content | Add a sensitivity/review vocabulary before public launch. |
| Personal information | Avoid exposing addresses, service numbers, or private donor details in public metadata. |
| Cultural context | Preserve wartime terms when historically necessary, but add modern place/country fields for respectful discovery. |
| Test data | Clearly label generated records and exclude from public exports by default. |

## 15. Roadmap

### V1 Current

| Area | Status |
| --- | --- |
| Manual cataloging | Done |
| Metadata fields | Done |
| Taxonomy seed | Done |
| Authority seed | Done |
| Thematic collections | Done |
| Local media placeholders | Done |
| Formal test data | Done |
| Basic API search | Done |
| Backup export | Done |

### V1.1 Suggested

| Area | Work |
| --- | --- |
| Export | Add Dublin Core JSON and CSV export. |
| Import staging | Add source record table and review queue. |
| Relationship roles | Replace comma-separated role assumptions with role vocabulary. |
| Date model | Add date type and EDTF/ISO fields. |
| Subject source | Store source per subject term. |
| Public exclusion | Default-hide `Formal Test Data = True` in public views. |
| Data quality | Add validation report for missing rights, dates, subjects, source IDs. |

### V2 Suggested

| Area | Work |
| --- | --- |
| NMPWA/Portal tracking | OAI-PMH or API harvester with scheduled updates. |
| IIIF | Manifest endpoint and image viewer. |
| OAI-PMH | Provider endpoint for external harvesters. |
| Full-text search | OCR/transcript indexing and highlight snippets. |
| DAM integration | S3 masters, derivatives, checksums, media lifecycle. |
| Public portal | Browse pages, authority pages, exhibit/thematic landing pages. |
| Preservation | PREMIS events and fixity checks. |

## 16. Source Links

Use these sources when extending the profile:

- DCMI Metadata Terms: https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
- DCMI Collection Description Application Profile: https://www.dublincore.org/specifications/dublin-core/collection-description/collection-application-profile/
- UNT Libraries Metadata Documentation: https://www.library.unt.edu/metadata/index.html
- UNT Input Guidelines for Descriptive Metadata: https://library.unt.edu/metadata/input-guidelines-descriptive.html
- UNT Resource Type Guidelines: https://library.unt.edu/metadata/fields/resource-type.html
- UNT Subject Guidelines: https://library.unt.edu/metadata/fields/subject.html
- UNT Description Guidelines: https://library.unt.edu/metadata/fields/description.html
- Portal to Texas History API: https://texashistory.unt.edu/api/
- NMPWA collection page: https://texashistory.unt.edu/explore/collections/NMPWA/
- Library of Congress MODS: https://www.loc.gov/standards/mods/
- Library of Congress EAD: https://www.loc.gov/ead/
- Library of Congress METS: https://www.loc.gov/standards/mets/
- Library of Congress PREMIS: https://www.loc.gov/standards/premis/
- CIDOC CRM: https://cidoc-crm.org/
- Schema.org CreativeWork: https://schema.org/CreativeWork
