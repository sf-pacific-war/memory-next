"""Check the official NARA Catalog v2 API; separate from its public S3 data."""

import json
from urllib.parse import urlencode

from archive_access import Source, run_cli


SOURCE = Source(
    id="nara_catalog", name="NARA Catalog API v2", access_mode="api",
    endpoint="https://catalog.archives.gov/api/v2/records/search",
    portal_url="https://catalog.archives.gov/", credential_env="NARA_API_KEY",
    notes=("Request a read-only key from Catalog_API@nara.gov. API responses are not cached or saved; "
           "the public S3 dataset is a separate access route."),
    documentation_url="https://www.archives.gov/research/catalog/help/api",
)


def probe(query, rows, credential, request):
    if not credential or type(rows) is not int or not 1 <= rows <= 5:
        raise ValueError
    params = urlencode({"q": query, "limit": rows})
    payload = json.loads(request(SOURCE.endpoint + "?" + params, headers={
        "Accept": "application/json", "Content-Type": "application/json", "x-api-key": credential,
    }))
    if (not isinstance(payload, dict) or payload.get("error") or payload.get("errors")
            or ("statusCode" in payload and (type(payload["statusCode"]) is not int
                                             or payload["statusCode"] != 200))):
        raise ValueError
    body = payload.get("body")
    if not isinstance(body, dict) or body.get("error") or body.get("errors"):
        raise ValueError
    hits = body.get("hits")
    if not isinstance(hits, dict) or not isinstance(hits.get("total"), dict):
        raise ValueError
    records, total = hits.get("hits"), hits["total"].get("value")
    if (not isinstance(records, list) or type(total) is not int or total < len(records)
            or len(records) > rows or any(not isinstance(item, dict) for item in records)):
        raise ValueError
    relation = hits["total"].get("relation")
    if not isinstance(relation, str) or relation not in {"eq", "gte"}:
        raise ValueError
    # Elasticsearch can report a lower bound rather than the exact total.
    summary = {"sample_count": len(records)}
    if relation == "eq":
        summary["total_results"] = total
    return summary


def main(argv=None):
    return run_cli(SOURCE, probe, argv)


if __name__ == "__main__":
    raise SystemExit(main())
