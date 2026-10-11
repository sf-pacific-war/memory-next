"""Check one DPLA search response using a locally configured API key."""

import json
from urllib.parse import urlencode

from archive_access import Source, run_cli


SOURCE = Source(
    id="dpla", name="Digital Public Library of America", access_mode="api",
    endpoint="https://api.dp.la/v2/items", portal_url="https://dp.la/",
    credential_env="DPLA_API_KEY",
    notes="Request your own DPLA key; this check returns counts only and does not save records.",
    documentation_url="https://pro.dp.la/developers/requests",
)


def probe(query, rows, credential, request):
    if not credential or type(rows) is not int or not 1 <= rows <= 5:
        raise ValueError
    params = urlencode({"q": query, "page_size": rows, "page": 1, "api_key": credential})
    payload = json.loads(request(SOURCE.endpoint + "?" + params, headers={"Accept": "application/json"}))
    if not isinstance(payload, dict) or payload.get("error") or payload.get("errors"):
        raise ValueError
    records, total = payload.get("docs"), payload.get("count")
    if (not isinstance(records, list) or type(total) is not int or total < len(records)
            or len(records) > rows or any(not isinstance(item, dict) for item in records)):
        raise ValueError
    return {"sample_count": len(records), "total_results": total}


def main(argv=None):
    return run_cli(SOURCE, probe, argv)


if __name__ == "__main__":
    raise SystemExit(main())
