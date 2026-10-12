"""Link to JACAR's official portal; no verified public API is configured."""

from archive_access import Source, run_cli


SOURCE = Source(
    id="jacar", name="Japan Center for Asian Historical Records", access_mode="portal",
    endpoint="", portal_url="https://www.jacar.go.jp/english/",
    notes=("Public database browsing is available. A documented public search API has not been "
           "confirmed for this demo; this entry does not scrape or fetch search results."),
    documentation_url="https://www.jacar.go.jp/english/",
)
probe = None


def main(argv=None):
    return run_cli(SOURCE, probe, argv)


if __name__ == "__main__":
    raise SystemExit(main())
