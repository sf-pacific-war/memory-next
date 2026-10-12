"""Check Discovery only after the request IP has received TNA access approval."""

import json
from urllib.parse import urlencode

from archive_access import Source, run_cli


SOURCE = Source(
    id="tna", name="The National Archives Discovery", access_mode="api",
    endpoint="https://discovery.nationalarchives.gov.uk/API/search/v1/records",
    portal_url="https://discovery.nationalarchives.gov.uk/", requires_permission=True,
    notes=("No API key parameter is documented. First email webmaster@nationalarchives.gov.uk "
           "with the request IP for access approval. --permission-confirmed only records your "
           "confirmation; it grants no access. Responses are not cached or saved."),
    documentation_url=("https://www.nationalarchives.gov.uk/terms-and-conditions/"
                       "discovery-for-developers-about-the-application-programming-interface-api/"),
)


def probe(query, rows, credential, request):
    if type(rows) is not int or not 1 <= rows <= 5:
        raise ValueError
    params = urlencode({"SearchQuery": query, "Page": 0, "ResultsPageSize": rows})
    payload = json.loads(request(SOURCE.endpoint + "?" + params, headers={"Accept": "application/json"}))
    if (not isinstance(payload, dict) or payload.get("error") or payload.get("errors")
            or payload.get("Error") or payload.get("Errors") or payload.get("ExceptionMessage")):
        raise ValueError
    records, total = payload.get("Records"), payload.get("Count")
    if (not isinstance(records, list) or type(total) is not int or total < len(records)
            or len(records) > rows or any(not isinstance(item, dict) for item in records)):
        raise ValueError
    return {"sample_count": len(records), "total_results": total}


def main(argv=None):
    return run_cli(SOURCE, probe, argv)


if __name__ == "__main__":
    raise SystemExit(main())
