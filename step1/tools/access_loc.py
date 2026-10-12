#!/usr/bin/env python3
"""Probe the Library of Congress photos JSON API without credentials."""

import json
from urllib.parse import urlencode

from archive_access import Source, run_cli
from fetch_public_metadata import source_url


SOURCE = Source(
    id="loc",
    name="Library of Congress",
    access_mode="api",
    endpoint="https://www.loc.gov/photos/",
    portal_url="https://www.loc.gov/",
    default_query="Burma Road",
    notes="One photos API request; no key is required. Results are metadata, not a guarantee of digitized or reusable content.",
    documentation_url="https://www.loc.gov/apis/json-and-yaml/requests/",
)


def probe(query, rows, credential, request):
    url = SOURCE.endpoint + "?" + urlencode({"q": query, "fo": "json", "c": rows})
    payload = json.loads(request(url))
    if not isinstance(payload, dict):
        raise ValueError("Unexpected LoC response structure.")
    items = payload.get("results")
    pagination = payload.get("pagination")
    total = pagination.get("of") if isinstance(pagination, dict) else None
    if not isinstance(items, list) or type(total) is not int or total < 0 or total < len(items):
        raise ValueError("Unexpected LoC response structure.")
    for item in items:
        # Some valid records use a protocol-relative catalog URL but retain a
        # canonical LoC item ID. Validate either identity without following it.
        if not isinstance(item, dict) or not any(
            source_url(item.get(field), {"www.loc.gov", "loc.gov"}) for field in ("url", "id")
        ):
            raise ValueError("Unexpected LoC record structure.")
    return {"sample_count": min(len(items), rows), "total_results": total}


def main(argv=None):
    return run_cli(SOURCE, probe, argv)


if __name__ == "__main__":
    raise SystemExit(main())
