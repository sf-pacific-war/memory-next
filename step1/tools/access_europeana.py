"""Check the Europeana Search API; explicit local credentials, counts only."""

import json
from urllib.parse import urlencode
from archive_access import Source, run_cli


SOURCE = Source(
    id="europeana", name="Europeana", access_mode="api",
    endpoint="https://api.europeana.eu/record/v2/search.json",
    portal_url="https://www.europeana.eu/en/search", default_query='"Burma Road"',
    credential_env="EUROPEANA_API_KEY",
    documentation_url="https://www.europeana.eu/en/how-to-register-for-and-manage-an-api-key",
    notes="Personal key for development testing; no raw response or metadata is saved by this check.",
)


def probe(query, rows, credential, request):
    if not credential:
        raise ValueError
    url = SOURCE.endpoint + "?" + urlencode({
        "query": query, "rows": rows, "profile": "rich", "wskey": credential,
    })
    payload = json.loads(request(url, headers={"Accept": "application/json"}))
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise ValueError
    total, items = payload.get("totalResults"), payload.get("items")
    if (type(total) is not int or total < 0 or not isinstance(items, list)
            or len(items) > rows or total < len(items)
            or any(not isinstance(item, dict) or not isinstance(item.get("id"), str)
                   or not item["id"].startswith("/") for item in items)):
        raise ValueError
    return {"sample_count": len(items), "total_results": total}


def main(argv=None):
    return run_cli(SOURCE, probe, argv)


if __name__ == "__main__":
    raise SystemExit(main())
