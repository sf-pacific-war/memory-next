"""Link to IWM's official Collections Search; not a claimed API integration."""

from archive_access import Source, run_cli


SOURCE = Source(
    id="iwm", name="Imperial War Museums", access_mode="portal",
    endpoint="", portal_url="https://www.iwm.org.uk/collections/search",
    notes=("Use Collections Search. A documented public collection-search API has not been "
           "confirmed for this demo; public viewing is not permission to copy all collection media."),
    documentation_url="https://www.iwm.org.uk/collections",
)
probe = None


def main(argv=None):
    return run_cli(SOURCE, probe, argv)


if __name__ == "__main__":
    raise SystemExit(main())
