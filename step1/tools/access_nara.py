#!/usr/bin/env python3
"""Probe one official public NARA dataset shard without Catalog API credentials."""

from archive_access import Source, run_cli
from fetch_nara_metadata import DATASET_DOCUMENTATION, DATASET_URL, FetchError, normalize_jsonl


SOURCE = Source(
    id="nara",
    name="NARA public catalog dataset",
    access_mode="dataset",
    endpoint=DATASET_URL,
    portal_url="https://catalog.archives.gov/",
    default_query="",
    notes="Downloads one fixed RG 493 JSONL metadata shard anonymously. The returned sample count is not keyword search results, a full Catalog search, or the record-group total; query input is not supported. Authenticated Catalog API access is separate.",
    documentation_url=DATASET_DOCUMENTATION,
)


def probe(query, rows, credential, request):
    data = request(SOURCE.endpoint)
    try:
        payload = normalize_jsonl(data, fetched_at=None, dataset_updated_at=None, limit=rows)
    except FetchError:
        raise ValueError("Unexpected NARA public dataset structure.") from None
    return {"sample_count": payload["returned_count"]}


def main(argv=None):
    return run_cli(SOURCE, probe, argv)


if __name__ == "__main__":
    raise SystemExit(main())
