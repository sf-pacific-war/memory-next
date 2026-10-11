"""Inventory Taiwan's official archive portal; live keyword access is not implemented."""

from archive_access import Source, run_cli


SOURCE = Source(
    id="taiwan", name="National Archives Administration, National Development Council (Taiwan)",
    access_mode="portal", endpoint="", portal_url="https://aa.archives.gov.tw/",
    notes=("Official archive search is available through the A+ portal. An anonymous case-title CSV "
           "is listed at data.gov.tw/dataset/95315, but CSV ingestion and a keyword API are not "
           "implemented in this demo. This entry makes no request and does not search the CSV."),
    documentation_url="https://data.gov.tw/dataset/95315",
)
probe = None


def main(argv=None):
    return run_cli(SOURCE, probe, argv)


if __name__ == "__main__":
    raise SystemExit(main())
