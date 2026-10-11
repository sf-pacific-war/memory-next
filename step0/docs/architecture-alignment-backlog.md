# Architecture Alignment Backlog

This backlog records follow-up work from the architecture principle review against the archival infrastructure proposal for the legacy Step 0 app. Step 0 remains a local system demo, so some public-portal rules are intentionally staged for later rather than enforced now. The separate [Step 1 discovery app](../../step1/README.md) has its own scope and roadmap.

## Implemented Now

- Viewer-facing catalog/API payloads now hide internal stewardship fields: physical storage location, internal note, preservation note, raw metadata JSON, media local paths, original filenames, and checksums.
- Storage location and audit log APIs now require admin access.

## Demo Note

- Keep the Catalog default as `All records` for now. The seed data is intentionally dominated by generated `Formal Test Data = True` records because no real holdings have entered this system demo yet.
- Before any real public reading-room or production portal launch, default public views and public exports should exclude `Formal Test Data = True`.

## Backlog Items

1. Access policy enforcement
   - Drive media download and future publication gating from `access_rights` plus review/publication state, not only from the descriptive `rights` value.
   - Treat `Rights = Unknown` with restrictive `Access Rights` as blocked for public file delivery until reviewed.

2. Review and publication state
   - Add explicit object-level state such as `review_status`, `publication_status`, and later `sensitivity`.
   - Use those states in search, detail display, exports, and any future public portal.

3. AI review provenance after submit
   - Preserve which metadata came from AI intake, which fields were curator-reviewed, and the confidence/evidence package after the draft becomes a formal object.
   - Consider a structured AI/enrichment table instead of relying only on `metadata_json`.

4. Preservation events
   - Add PREMIS-style preservation events for ingest, checksum creation, fixity checks, derivative generation, migration, and file provenance.
   - Keep backups as a demo safeguard, but do not treat backup export alone as the preservation workflow.
