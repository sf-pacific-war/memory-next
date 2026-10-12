"""Check nine access routes for eight platforms; optionally send one keyword to each API."""

from collections import Counter
import importlib
import json
from archive_access import argument_parser, check_source, exit_code


SOURCE_IDS = ("loc", "europeana", "nara", "nara_catalog", "dpla", "tna", "jacar", "iwm", "taiwan")


def print_table(report):
    print("Mode: " + report["mode"] + (" (live)" if report["live"] else " (offline)"))
    if report["query"] is not None:
        print("Query (unchanged; no translation): " + json.dumps(report["query"], ensure_ascii=False))
    print("{:<14} {:<22} {:<5} {:>6} {:>10}".format("SOURCE", "STATUS", "SENT", "SAMPLE", "TOTAL"))
    for result in report["results"]:
        print("{:<14} {:<22} {:<5} {:>6} {:>10}".format(
            result["source"], result["status"], "yes" if result["request_sent"] else "no",
            result.get("sample_count", "-"), result.get("total_results", "-")))
    print("Summary: " + json.dumps(report["summary"], ensure_ascii=False))
    print("- = not measured/reported; 0 = a successful query returned no matches.")
    print("Counts only; no records saved or added to the website. Use --format json for details.")


def main(argv=None):
    parser = argument_parser(__doc__)
    parser.add_argument("--source", choices=("all",) + SOURCE_IDS, default="all")
    parser.add_argument("--format", choices=("json", "table"), default="json", help="Report format; default json")
    args = parser.parse_args(argv)
    # Reject bad input before the first source can make a request.
    if not 1 <= args.rows <= 5 or (args.query is not None and (not args.query.strip() or len(args.query) > 200)):
        parser.error("Use 1–5 rows and a nonempty query of at most 200 characters.")
    options = vars(args).copy()
    selected = options.pop("source")
    output_format = options.pop("format")
    results = []
    for source_id in SOURCE_IDS if selected == "all" else (selected,):
        adapter = importlib.import_module("access_" + source_id)
        results.append(check_source(adapter.SOURCE, getattr(adapter, "probe", None), **options))
    report = {"live": args.live, "mode": "keyword" if args.query is not None else "access",
              "query": args.query, "summary": dict(Counter(r["status"] for r in results)), "results": results}
    if output_format == "table":
        print_table(report)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    codes = [exit_code(result, args.live) for result in results]
    return 1 if 1 in codes else (2 if 2 in codes else 0)


if __name__ == "__main__":
    raise SystemExit(main())
