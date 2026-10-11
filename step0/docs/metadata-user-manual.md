# Archive Collection System Metadata User Manual

This manual describes the legacy Step 0 app. Filesystem paths such as `data/`, `storage/`, and `backups/` are relative to `step0/`. See the [Step 0 README](../README.md) for startup and existing local-data migration.

Version: 0.1  
Audience: archivists, metadata curators, collection managers, and developers maintaining the V1 local demo.

This guide explains the metadata supported by the local Archive Collection System, how to enter records consistently, how the fields map to Dublin Core and related metadata standards, and how the model compares with the National Museum of the Pacific War Digital Archive in The Portal to Texas History.

For a deeper field dictionary, taxonomy governance model, developer notes, import/export design, and NMPWA tracking roadmap, see [Taxonomy And Metadata Reference](taxonomy-metadata-reference.md).

## 1. What The System Describes

The V1 system separates descriptive, authority, taxonomy, physical, and digital-file metadata. Do not treat everything as a tag. A record should describe one archival object and link it to reusable entities.

Core entities:

| Entity | Meaning | Where it appears |
| --- | --- | --- |
| Object | The archival thing being cataloged: photograph, letter, map, oral history, document, physical object, etc. | Catalog and Record tabs |
| Collection | The collection, subcollection, or accession group that contains the object. | Catalog, filters, record form |
| Authority | Reusable Person, Organization, Place, or Event record. | Authorities tab and record relationships |
| Taxonomy Term | Controlled vocabulary value such as Object Type, Subject, Language, Rights, Condition, Digitization Status. | Filters and taxonomy display |
| Storage Location | Hierarchical physical storage path. | Admin Storage tab and admin object detail |
| Digital Media | Local files or Google Drive demo links representing the object. | Object detail and Admin tab, with preservation fields hidden from viewers |
| Movement | Physical location history. | Backend/audit data |
| Audit Log | Administrative action history. | Admin tab |

Recommended mental model:

```text
Object
  belongs to Collection
  created by Person / Organization
  associated with Person / Organization / Place / Event
  classified by Subject / Object Type / Rights / Language / Status
  stored at Physical Location
  represented by Digital Media
```

## 2. Metadata Fields Supported In V1

The Record tab supports the following object-level fields.

### Core catalog fields

| Field | Required | Example | Use |
| --- | --- | --- | --- |
| Permanent ID | Yes | `MNA-000123` | Stable internal identifier for both physical and digital representations. Never reuse. |
| Title | Yes | `Soldier portrait, Manila` | Human-readable display title. |
| Object Type | Yes | `Photograph` | Controlled resource type used for browsing and filtering. |
| Collection | No | `Pacific War Collection` | Collection or subcollection name. |
| Date Label | No | `circa 1945` | Human-readable date as it should display. |
| Date Start | No | `1945` | Normalized start year for filtering. |
| Date End | No | `1945` | Normalized end year for filtering. |
| Language | No | `English` | Language of the resource, not the cataloging language. |
| Rights | No | `Public Domain` | Rights/access summary used for filtering and download policy. |
| Condition | No | `Good` | Physical condition summary. |
| Digitization Status | No | `Complete` | Digitization workflow state. |
| Physical Location | No | `Main Repository / Room 1 / Cabinet A / Shelf 2 / Box 12 / Folder 7` | Admin-only current storage hierarchy. Slash or arrow-separated paths are accepted. |
| Description | No | `Photograph of...` | Content summary, scope note, or abstract. |
| Provenance | No | `Donated by...` | Custodial history, donor, acquisition, accession, or source note. |
| Creators | No | `John Smith` | People primarily responsible for creating the object. |
| People | No | `Chester W. Nimitz` | People depicted, mentioned, interviewed, or otherwise associated. |
| Organizations | No | `U.S. Army` | Organizations, units, ships, agencies, or publishers associated with the object. |
| Places | No | `Manila` | Places depicted, described, created at, or otherwise associated. |
| Events | No | `Battle of Manila` | Battles, campaigns, ceremonies, interviews, accessions, or other historical events. |
| Subjects | No | `WWII, Pacific Theater` | Topical terms and themes. |

### Dublin Core / DCMI Terms fields

These fields make the local data easier to export into Dublin Core, DCMI Terms, OAI-PMH, JSON-LD, and portal-style discovery records.

| Field | Example | Use |
| --- | --- | --- |
| Alternative Title | `NMPWA-style photograph fixture` | Variant, translated, supplied, or former title. |
| Publisher | `National Museum of the Pacific War` | Entity making the resource available or publishing the item. |
| Contributors | `University of North Texas Libraries metadata reference` | Secondary contributors such as interviewer, transcriber, donor, editor, or host institution. |
| Source | `https://texashistory.unt.edu/explore/collections/NMPWA/` | Source collection, imported record, donor source, or derived-from resource. |
| Relation | `Is part of Pearl Harbor Collection` | Related item, series, exhibition, original/surrogate relationship, or cross-reference. |
| Coverage Spatial | `Philippines; Manila` | Spatial coverage as display text or export-friendly phrase. |
| Coverage Temporal | `World War II, 1941-1945` | Historical period, campaign period, or date span. |
| Physical Description | `1 photograph : black-and-white ; 8 x 10 in.` | Human-readable physical format, dimensions, page count, or duration. |
| Extent | `4 pages` | Count, duration, dimensions, or quantity. |
| Medium | `gelatin silver print` | Physical material or carrier. |
| Citation | `Archive Collection System, TEST-PW-0001` | Preferred citation for researchers. |

### Pacific War / UNTL-inspired fields

These fields are tuned for Pacific War letters, photographs, maps, oral histories, military documents, and reference materials. They follow patterns visible in The Portal to Texas History and the National Museum of the Pacific War Digital Archive without copying that platform's full UNTL schema.

| Field | Example | Use |
| --- | --- | --- |
| Resource Type | `Photograph`, `Letter`, `Sound`, `Map` | Portal-style browse type. This can mirror Object Type or use a broader public-facing value. |
| Genre/Form | `Correspondence`, `Oral histories`, `Military maps` | More specific form term, ideally from LCGFT or a local controlled list. |
| Series Title | `Women in War Collection` | Series, named collection, or intellectual grouping. |
| Subcollection | `Pearl Harbor Collection` | Lower-level grouping inside the main collection. |
| Theater | `Pacific Theater` | High-level military theater or region. |
| Campaign | `Philippines Campaign` | Campaign-level browse value. |
| Battle | `Battle of Manila` | Battle or operation. |
| Military Unit | `U.S. Marine Corps` | Unit, ship, squadron, agency, or command. |
| Vessel / Aircraft | `USS Enterprise` | Named ship, aircraft, or vehicle. |
| Modern Country | `Philippines` | Current country for geographic browsing. |
| Wartime Jurisdiction | `Commonwealth of the Philippines` | Period-accurate jurisdiction or colonial/occupation context. |
| Subject Source | `LCSH; LCGFT; local` | Source of subject, genre, or keyword terms. |

### Identifiers, rights, preservation, and interoperability

| Field | Example | Use |
| --- | --- | --- |
| External Identifier | `NMPWA-REF-0001` | Source call number, accession number, imported ID, or partner ID. |
| ARK | `ark:/67531/...` | Persistent public identifier when available. |
| Item URL | `https://texashistory.unt.edu/ark:/67531/.../` | Public source item page or future local item page. |
| Thumbnail URL | `https://.../thumbnail/` | External thumbnail reference. |
| IIIF Manifest URL | `https://.../manifest/` | IIIF Presentation manifest for interoperable viewers. |
| License URI | `https://creativecommons.org/licenses/...` | Machine-readable license. |
| Access Rights | `public`, `reading room only`, `restricted` | Access policy separate from copyright. |
| Primary Source | checked | Flags whether an item is a primary source. |
| Formal Test Data | checked | Marks generated fixture records that should not be treated as real archival holdings. |
| Metadata Profile | `Dublin Core + UNTL-inspired local profile` | Export/profile note for cross-platform mapping. |
| Display Note | `Formal test data: not a real archival item.` | Public note. |
| Internal Note | `Generated to exercise search facets.` | Staff-only administrative note; hidden from viewer catalog/API responses. |
| Preservation Note | `Checksum pending` | Staff-only fixity, preservation, migration, or packaging note; hidden from viewer catalog/API responses. |
| Metadata JSON | `{"schema":"untl-inspired"}` | Structured sidecar metadata for advanced testing and exports; hidden from viewer catalog/API responses. |

### Controlled vocabularies now seeded

The local taxonomy now includes starter vocabularies for Object Type, Resource Type, Genre/Form, Subject, Theater, Campaign, Battle, Language, Rights, Access Rights, Condition, Digitization Status, Metadata Standard, Data Source, Formal Test Data, and Historical Period.

Digital media fields are managed from the Admin tab.

| Field | Example | Use |
| --- | --- | --- |
| Object | `MNA-000123` | The object receiving media. |
| Derivative Type | `preservation_master`, `access_derivative`, `ocr`, `transcript`, `metadata_export`, `working_copy` | Distinguishes masters, access files, OCR, transcripts, and working files. |
| Local File | `master.tif` | Stored under `storage/archive-master/{Permanent ID}/`. |
| Google Drive URL | `https://drive.google.com/...` | Demo-only external collaboration link. It is not canonical storage in V1. |
| SHA-256 Checksum | generated automatically for local files | Admin-visible fixity value for future preservation checks. |
| Size / MIME Type | generated when possible | Technical metadata for local media. |

## 3. Cataloging Rules

### Permanent IDs

Use one permanent identifier per archival object. The same ID should appear on the physical container label, digital folder, metadata export, and any public citation.

Recommended pattern:

```text
MNA-000001
MNA-000002
MNA-000003
```

Do not encode changing facts in the ID. Avoid collection names, locations, dates, rights, or file formats in the permanent ID because those can change.

### Titles

Prefer a concise descriptive title. If an object has a title written on it, transcribe that title. If no title exists, create a supplied title that identifies the object.

Good:

```text
Soldier portrait, Manila
Leyte Gulf operations map
Letter from San Francisco embarkation
```

Avoid:

```text
Photo
Scan 0045
Unknown
```

### Object Type

Object Type is a controlled vocabulary, not a free-form description. Keep values broad enough for filtering.

Recommended starting values:

```text
Photograph
Map
Letter
Text
Sound
Video
Postcard
Newspaper
Book
Pamphlet
Report
Poster
Physical Object
Technical Drawing
Artwork
```

### Dates

Use `Date Label` for what users should see and normalized start/end years for filtering.

Examples:

| Historical date | Date Label | Date Start | Date End |
| --- | --- | --- | --- |
| Known year | `1945` | `1945` | `1945` |
| Approximate | `circa 1944` | `1944` | `1944` |
| Range | `1941-1945` | `1941` | `1945` |
| Unknown | `undated` | blank | blank |

Future export should prefer ISO 8601 or EDTF-style values when more precise dates are needed.

### Creators, People, Organizations, Places, and Events

Use authority fields for real-world entities. Do not flatten these into `Subjects` unless the term is truly topical.

Use:

```text
Creators: John Smith
Organizations: U.S. Army
Places: Manila
Events: Battle of Manila
Subjects: WWII, Pacific Theater
```

Avoid:

```text
Subjects: John Smith, U.S. Army, Manila, Battle of Manila, WWII
```

This distinction matters because authority records can later support aliases, external URIs, biographies, geocoding, relationship graphs, and cross-platform matching.

### Rights

Use consistent values. Suggested starter set:

```text
Public Domain
Research Use
Restricted
Attribution Non-commercial No Derivatives
Unknown
```

If a record is `Restricted`, viewers can still see the catalog metadata, but local file downloads are blocked for non-admin users.

### Physical Location

Enter storage as a hierarchy:

```text
Main Repository / Room 1 / Cabinet A / Shelf 2 / Box 12 / Folder 7
```

The system will create missing location nodes. Keep naming consistent so the hierarchy stays clean.

Physical location data is a stewardship field. Admin users can view and search it; viewer users do not receive storage paths in catalog detail or object API payloads.

### Digital Media

Use local storage for canonical demo files:

```text
storage/archive-master/MNA-000123/master.tif
storage/archive-master/MNA-000123/access.jpg
storage/archive-master/MNA-000123/ocr.txt
storage/archive-master/MNA-000123/metadata.json
```

Use Google Drive links for temporary collaboration and working copies only. In this V1 demo, Google Drive is a URL reference field, not an integrated cloud storage backend.

### AI Intake Review

Use AI Intake Review when files should be staged, described, and approved before they become formal archive records.

Current V1 behavior:

1. Admin users batch upload local images or PDFs from the Admin tab.
2. Files are staged under `storage/intake/{Intake ID}/`.
3. A mock AI analyzer creates draft metadata suggestions from the filename, media type, checksum, and size.
4. A curator reviews and edits the draft before submitting.
5. Submit can either create a new object or attach the staged file to an existing object.
6. Reject keeps the intake item out of the formal catalog.

Do not treat mock AI suggestions as authoritative metadata. Review title, object type, date, rights, subjects, provenance, and notes before submit. In V1, the analyzer is a local placeholder for the future OCR or vision-model integration.

After submit, the system copies the file into canonical local storage at:

```text
storage/archive-master/{Permanent ID}/
```

The intake draft records the review status and submitted object ID, while the official catalog record continues to live in the normal object and digital media tables.

## 4. Search And Browse In V1

The Catalog tab supports:

| Search mode | Supported now |
| --- | --- |
| Keyword search | Yes, across title, description, ID, collection, authority names, aliases, taxonomy, media filenames, and Google Drive demo URLs. Admin search also includes internal stewardship fields. |
| Collection filter | Yes |
| Object Type filter | Yes |
| Place filter | Yes |
| Event filter | Yes |
| Subject filter | Yes |
| Rights filter | Yes |
| Date range filter | Yes, by normalized start/end year |
| Physical location browse | Admin only, via Storage tab display |
| Authority browse | Yes, via Authorities tab |
| Resource Type filter | Yes |
| Campaign filter | Yes |
| Formal Test Data filter | Yes |

Example local API query:

```text
http://127.0.0.1:8787/api/objects?query=Manila&object_type=Photograph&date_from=1941&date_to=1945
```

### Formal test data

The seeded database includes 100 generated Pacific War fixture records with permanent IDs `TEST-PW-0001` through `TEST-PW-0100`. Each one has `Formal Test Data = True`, NMPWA-inspired source/citation fields, populated Dublin Core / DCMI Terms fields, Pacific War taxonomy values, authority links, placeholder digital media, and a metadata JSON sidecar.

Use this dataset for search, browse, metadata export, UI QA, and workflow testing. Do not cite these fixture records as real archival holdings.

For the local system demo, the Catalog default intentionally remains `All records` so the seeded fixtures are visible. Before any real public portal or production export, default public views should exclude `Formal Test Data = True`.

Useful checks:

```text
GET /api/objects?formal_test_data=true
GET /api/objects?formal_test_data=true&resource_type=Letter
GET /api/objects?query=NMPWA&campaign=Philippines%20Campaign
```

## 5. Dublin Core Baseline

Dublin Core is the lowest-friction interchange vocabulary for discovery. The original Dublin Core Element Set contains 15 broad elements. The broader DCMI Metadata Terms specification includes the original elements plus additional properties, classes, encoding schemes, and RDF-oriented semantics.

For new exports, prefer DCMI Terms (`dcterms`) where possible, while still supporting simple `oai_dc` for OAI-PMH compatibility.

| Dublin Core element | Meaning | Local field mapping |
| --- | --- | --- |
| `dc:title` | Name of the resource | Title |
| `dc:creator` | Primary creator | Creators |
| `dc:subject` | Topic | Subjects, plus optionally authority labels for compatibility |
| `dc:description` | Account of the resource | Description |
| `dc:publisher` | Entity making resource available | Publisher |
| `dc:contributor` | Secondary contributor | Contributors, plus related People/Organizations |
| `dc:date` | Date associated with lifecycle | Date Label / normalized date range |
| `dc:type` | Nature or genre | Object Type, Resource Type, Genre/Form |
| `dc:format` | File format, physical medium, dimensions | Digital media MIME type, Physical Description, Extent, Medium |
| `dc:identifier` | Unambiguous reference | Permanent ID, External Identifier, ARK, Item URL, IIIF Manifest URL |
| `dc:source` | Source from which derived | Source, Provenance |
| `dc:language` | Language | Language |
| `dc:relation` | Related resource | Relation, Collection, Series Title, Subcollection |
| `dc:coverage` | Spatial or temporal topic | Coverage Spatial, Coverage Temporal, Places, Events, Date Label/date range |
| `dc:rights` | Rights information | Rights, License URI, Access Rights |

Recommended DCMI Terms additions:

| DCMI Terms field | Local use |
| --- | --- |
| `dcterms:abstract` | Short display summary if different from full Description |
| `dcterms:created` | Creation date |
| `dcterms:issued` | Publication/release date |
| `dcterms:temporal` | Period or date range |
| `dcterms:spatial` | Place authority |
| `dcterms:isPartOf` | Collection membership |
| `dcterms:provenance` | Provenance |
| `dcterms:accessRights` | Public, restricted, reading-room only, etc. |
| `dcterms:license` | Rights URI, such as Creative Commons |
| `dcterms:extent` | Physical extent, dimensions, page count, duration |
| `dcterms:medium` | Physical medium |

## 6. Alternatives And Complements To Dublin Core

Dublin Core is excellent for cross-system discovery, but it is intentionally broad. Use other standards when the project needs more structure.

| Standard | Best for | Why it matters here |
| --- | --- | --- |
| DCMI Terms | General web/linked-data metadata | Better modern DC export than unqualified DC alone. |
| MODS | Library-style item metadata | Richer bibliographic fields, names, titles, identifiers, notes, related items. |
| DACS | Archival content rules | Helps decide what archival descriptions should contain at collection, series, file, and item levels. |
| EAD | Encoded archival finding aids | Good for exporting hierarchical collection/finding aid descriptions. |
| EAC-CPF | Authority records for people, families, corporate bodies | Future upgrade path for Person and Organization authority exports. |
| VRA Core | Images and visual/cultural works | Useful when separating an original work/object from its digital image surrogate. |
| CCO | Cataloging rules for cultural objects | Helps standardize titles, creators, dates, physical description, and subjects. |
| CIDOC CRM | Semantic cultural heritage graph | Good future model for complex relationships among objects, events, actors, places, and provenance. |
| METS | Digital object packaging | Packages descriptive, administrative, structural, rights, and file metadata together. |
| PREMIS | Preservation metadata | Tracks fixity, preservation events, agents, rights, and file provenance. |
| IIIF Presentation | Image/document viewing interoperability | Exposes manifests for viewers like Mirador and OpenSeadragon. |
| Schema.org | Public web discoverability | Enables search engines and web crawlers to understand item pages. |

Practical V1 recommendation:

1. Keep the internal model entity-based.
2. Export simple Dublin Core for broad compatibility.
3. Export a richer local JSON/UNTL-like profile for full fidelity.
4. Add PREMIS-style fixity and preservation events around digital media.
5. Add IIIF manifests for images, maps, and multi-page documents when public viewing becomes a V2 priority.

## 7. Comparison With UNT NMPWA / Portal To Texas History

The National Museum of the Pacific War Digital Archive in The Portal to Texas History is a useful benchmark because it covers the same subject domain at much larger scale.

### Collection-level comparison

The NMPWA collection page reports tens of thousands of items and exposes browse dimensions including resource types, languages, states, counties, titles, partner, usage, creation/update timing, and included archival series. It lists resource types such as Photograph, Text, Letter, Sound, Map, Video, Pamphlet, Postcard, Newspaper, Book, Artwork, Clipping, Physical Object, Technical Drawing, Poster, Article, Legal Document, and Script.

Local V1 comparison:

| Area | Local V1 | NMPWA / Portal model |
| --- | --- | --- |
| Scale | Demo seed records plus local additions | Large public collection with many thousands of items |
| Object type | Local controlled Object Type terms | Public browse by Resource Type |
| Language | Free text plus taxonomy term | Language facet and normalized language codes in UNTL |
| Geography | Place authorities | Coverage fields and browse by state/county/country |
| Collection structure | Collection table and names | Collection set codes, titles, subcollections, archival series |
| Authority control | Local Person/Organization/Place/Event authority rows | Local authority files for names, events, software, buildings, locations, and vocabularies |
| Public website | Local admin/search UI only | Public portal with item pages, collection pages, feeds, search, IIIF, OAI-PMH |

### Item-level metadata comparison

Sample NMPWA OAI-PMH `oai_dc` records include:

```text
dc:title
dc:creator
dc:subject
dc:description
dc:publisher
dc:contributor
dc:date
dc:type
dc:format
dc:identifier
dc:language
dc:coverage
dc:rights
```

Sample NMPWA native `untl` records are richer. They expose fields and qualifiers such as:

```text
untl:title qualifier="officialtitle"
untl:creator qualifier="ivr" / "ive"
untl:contributor qualifier="trc"
untl:publisher/name and publisher/location
untl:date qualifier="creation"
untl:language
untl:description qualifier="content" / "physical"
untl:subject qualifier="UNTL-BS" / "LCSH" / "LCGFT" / "KWD" / "named_person"
untl:primarySource
untl:coverage qualifier="placeName" / "timePeriod" / "date"
untl:collection
untl:institution
untl:rights qualifier="license" / "note"
untl:resourceType
untl:format
untl:identifier qualifier="itemURL" / "LOCAL-CONT-NO" / "thumbnailURL" / "ARK" / "iiif-manifest"
untl:note qualifier="display" / "nonDisplay" / "digitalPreservation"
untl:meta qualifier="meta-id" / "system" / "ark" / "metadataCreationDate" / "metadataCreator" / "metadataModifier" / "metadataModificationDate" / "hidden"
```

Local V1 crosswalk to UNTL-style fields:

| Local V1 | UNTL-style equivalent | Gap / recommendation |
| --- | --- | --- |
| Permanent ID | `identifier LOCAL-CONT-NO`; ARK in `identifier ARK` | Use Permanent ID internally and ARK/External Identifier for partner IDs. |
| Title | `title officialtitle` | Alternative Title is supported for variant/supplied titles. |
| Creators | `creator` with qualifier and type | Add creator role/type fields instead of comma-separated names. |
| People | `subject named_person` or contributor depending role | Add role-specific person associations. |
| Organizations | `creator`, `contributor`, `publisher`, `subject`, or `institution` depending role | Add relationship role vocabulary. |
| Description | `description content` | Physical Description is supported separately. |
| Date Label/Start/End | `date creation`; `coverage date` | Add date type qualifier and EDTF/ISO support. |
| Object Type | `resourceType` | Keep broad, controlled values. |
| Digital media MIME/type | `format` | Use MIME type for digital files; use Physical Description, Extent, and Medium for object format. |
| Language | `language` | Normalize to ISO codes for export. |
| Places | `coverage placeName` | Add geocoding and place hierarchy. |
| Events | subject or local event authority | Good local extension; export as subject/relation if no target format supports events. |
| Subjects | `subject` with qualifier | Subject Source and Genre/Form are supported; add per-term sources later. |
| Collection | `collection` | Collection names are supported; add collection codes later. |
| Rights | `rights license` / `rights note` | Rights, License URI, and Access Rights are supported. |
| Provenance | `source`, `note`, or `dcterms:provenance` | Source and Citation fields are supported. |
| Storage Location | Usually internal admin metadata | Do not expose public shelf locations unless policy allows. |
| Digital media checksum | `note digitalPreservation` or PREMIS | Move toward PREMIS event/object metadata. |

### Remaining gaps before exchanging with NMPWA-like platforms

These are now the most important remaining improvements:

| Field | Why |
| --- | --- |
| Contributor with role | Interviews, transcriptions, donors, editors, photographers, and collectors need role precision. |
| Relationship role vocabulary | People and organizations need explicit roles such as creator, donor, interviewer, interviewee, transcriber, publisher, and subject. |
| Date type and EDTF/ISO support | Creation, publication, coverage, accession, digitization, and modification dates should be distinguishable. |
| Per-term subject qualifiers | Distinguish LCSH, local browse subjects, keywords, named persons, and genre/form terms at the individual term level. |
| Collection codes | Add stable public collection codes in addition to display names. |
| Export services | Add OAI-PMH, IIIF, JSON-LD, CSV, and UNTL-like JSON export endpoints. |
| PREMIS events | Store preservation checks, checksum verification, migrations, and file provenance as structured events. |

## 8. Cross-platform Retrieval And Search Options

### Current local retrieval

Local API:

```text
GET /api/objects
GET /api/objects/{id}
GET /api/collections
GET /api/authorities
GET /api/taxonomy
GET /api/storage-locations
GET /local-media/{media_id}
```

Local structured query example:

```text
GET /api/objects?query=Manila&object_type=Photograph&place=Manila&date_from=1941&date_to=1945
GET /api/objects?formal_test_data=true&resource_type=Letter
GET /api/objects?query=NMPWA&campaign=Philippines%20Campaign
```

### Portal to Texas History retrieval patterns

The Portal to Texas History exposes several public retrieval options:

| Option | Use | Example pattern |
| --- | --- | --- |
| Human search | Basic, guided, advanced, and proximity search | `https://texashistory.unt.edu/search/` |
| Collection page | Browse collection facets and holdings | `https://texashistory.unt.edu/explore/collections/NMPWA/` |
| OAI-PMH | Harvest metadata records | `https://texashistory.unt.edu/oai/?verb=ListRecords&metadataPrefix=oai_dc&set=collection:NMPWA` |
| OAI-PMH native | Harvest richer UNTL metadata | `https://texashistory.unt.edu/oai/?verb=ListRecords&metadataPrefix=untl&set=collection:NMPWA` |
| OAI-PMH formats | Discover available metadata formats | `https://texashistory.unt.edu/oai/?verb=ListMetadataFormats` |
| IIIF manifest | Retrieve structured viewer manifest per item | `https://texashistory.unt.edu/ark:/67531/metapth193885/manifest/` |
| Thumbnail | Retrieve item thumbnail | append `/thumbnail/` to an item ARK URL |
| Feed | Follow new additions | collection `feed/` endpoint |
| OpenSearch | Simple full-text search protocol | `https://texashistory.unt.edu/search/opensearch/` |

### Recommended V2 interoperability roadmap

To make the local system cross-platform friendly, add these export endpoints in order:

1. Dublin Core JSON export:

```text
GET /api/objects/{id}/export?format=dc-json
```

2. OAI-PMH provider:

```text
GET /oai/?verb=Identify
GET /oai/?verb=ListMetadataFormats
GET /oai/?verb=ListSets
GET /oai/?verb=ListRecords&metadataPrefix=oai_dc
GET /oai/?verb=ListRecords&metadataPrefix=archive_json
```

3. IIIF Presentation manifests:

```text
GET /iiif/3/{permanent_id}/manifest
```

4. OpenSearch description and query:

```text
GET /search/opensearch.xml
GET /search/opensearch/?q=Manila
```

5. CSV/JSON-LD export for researcher workflows:

```text
GET /api/objects/export.csv
GET /api/objects/export.jsonld
```

## 9. Recommended Metadata Quality Checks

Run these checks before considering a batch complete:

| Check | Rule |
| --- | --- |
| Identifier | Every object has a unique Permanent ID. |
| Title | Every object has a specific, readable title. |
| Object Type | Every object has one controlled object type. |
| Collection | Every object belongs to a collection or accession group. |
| Date | Date label is present when known; normalized start/end years are populated for browse/search. |
| Authority separation | People, organizations, places, and events are in authority fields, not only subjects. |
| Rights | Rights and access state are not blank for public-facing records. |
| Location | Physical objects have a current storage path. |
| Digital media | Preservation masters and derivatives are clearly distinguished. |
| Checksum | Local digital files have SHA-256 checksums. |
| External links | Google Drive demo links are working copies, not canonical preservation files. |

## 10. Source Notes

Research consulted:

- DCMI Metadata Terms: https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
- Dublin Core Collection Description Application Profile: https://www.dublincore.org/specifications/dublin-core/collection-description/collection-application-profile/
- MODS, Library of Congress: https://www.loc.gov/standards/mods/
- EAD, Library of Congress: https://loc.gov/ead/
- VRA Core FAQ: https://core.vraweb.org/vracore_faq.html
- Cataloging Cultural Objects: https://www.vraweb.org/cco
- CIDOC CRM: https://cidoc-crm.org/
- METS, Library of Congress: https://www.loc.gov/standards/mets/
- PREMIS, Library of Congress: https://www.loc.gov/standards/premis/
- DACS: https://saa-ts-dacs.github.io/dacs/dacs.html
- Schema.org CreativeWork: https://schema.org/CreativeWork
- Portal to Texas History API: https://texashistory.unt.edu/api/
- Portal programmatic access FAQ: https://texashistory.unt.edu/help/faq/programmatic-access/
- NMPWA collection page: https://texashistory.unt.edu/explore/collections/NMPWA/
- UNT Technical Guidelines: https://library.unt.edu/metadata/technical-guidelines.html
- UNT Input Guidelines for Descriptive Metadata: https://library.unt.edu/metadata/input-guidelines-descriptive.html
- UNTL Metadata Application Profile repository: https://github.com/unt-libraries/untl_map
