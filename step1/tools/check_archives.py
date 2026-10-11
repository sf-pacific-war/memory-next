"""Inventory nine access routes for eight platforms; --live is explicit and serial."""

from collections import Counter
import importlib
import json
from archive_access import argument_parser, check_source, exit_code


SOURCE_IDS = ("loc", "ndl", "europeana", "nara", "nara_catalog", "dpla", "tna", "jacar", "iwm")


def main(argv=None):
    parser = argument_parser(__doc__)
    parser.add_argument("--source", choices=("all",) + SOURCE_IDS, default="all")
    args = parser.parse_args(argv)
    if args.source == "all" and args.query is not None:
        parser.error("Choose one source when using a custom query.")
    options = vars(args).copy()
    selected = options.pop("source")
    results = []
    for source_id in SOURCE_IDS if selected == "all" else (selected,):
        adapter = importlib.import_module("access_" + source_id)
        results.append(check_source(adapter.SOURCE, getattr(adapter, "probe", None), **options))
    print(json.dumps({"live": args.live, "summary": dict(Counter(r["status"] for r in results)),
                      "results": results}, ensure_ascii=False, indent=2))
    codes = [exit_code(result, args.live) for result in results]
    return 1 if 1 in codes else (2 if 2 in codes else 0)


if __name__ == "__main__":
    raise SystemExit(main())
