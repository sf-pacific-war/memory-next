"""Check credential-free local keyword search in Taiwan NAA's official CSV."""

import json
import socket
from urllib.error import HTTPError, URLError

from archive_access import Source, MESSAGES, argument_parser, check_source, exit_code
import fetch_taiwan_metadata as taiwan_csv


SOURCE = Source(
    id="taiwan", name=taiwan_csv.INSTITUTION,
    access_mode="csv", endpoint=taiwan_csv.CSV_URL, portal_url=taiwan_csv.CATALOGUE_URL,
    default_query=taiwan_csv.DEFAULT_QUERY,
    notes=("One credential-free CSV request, searched locally over case title, fonds and archival number. "
           "Explicit simplified/traditional Chinese and English aliases are reported in effective_queries. "
           "Default bounds are 4 MiB and 200000 rows. Partial scans have no whole-dataset total. "
           "Case metadata does not establish access to images or full text; A+ links open catalogue search."),
    documentation_url="https://data.gov.tw/dataset/95315",
)


def check(*, query=None, rows=3, live=False, env_file=None, permission_confirmed=False,
          environ=None, request=None):
    # Reuse common input/configuration validation. CSV transport and scan counts
    # need their own boundary because API checks are limited to 2 MiB responses.
    result = check_source(SOURCE, None, query=query, rows=rows, live=False,
                          env_file=env_file, permission_confirmed=permission_confirmed, environ=environ)

    def finish(status):
        result.update(status=status, message=MESSAGES[status])
        return result

    if result["status"] != "ready":
        return result
    effective_query = SOURCE.default_query if query is None else query
    try:
        result["effective_query"] = effective_query
        result["effective_queries"] = taiwan_csv.expand_queries(effective_query)
    except ValueError:
        return finish("invalid_input")
    if not live:
        return result
    try:
        result["request_sent"] = True
        download = (request or taiwan_csv.fetch_csv)(taiwan_csv.DEFAULT_MAX_BYTES)
        payload = taiwan_csv.snapshot_from_download(download, effective_query, rows)
        for key in ("total_results", "matched_count", "scanned_rows", "bytes_read", "scan_complete",
                    "source_exhausted", "row_limit_reached", "duplicate_rows"):
            if key in payload:
                result[key] = payload[key]
        result["sample_count"] = payload["returned_count"]
        finish("ok")
        result["message"] = ("Official CSV validated and searched locally. "
                             + ("Whole dataset scanned." if payload["scan_complete"] else
                                "Partial scan only; observed matches are not a whole-dataset total."))
        return result
    except HTTPError as exc:
        code = exc.code
        if exc.fp is not None:
            exc.close()
        result["http_status"] = code if type(code) is int else None
        return finish("access_denied" if code in {401, 403} else "rate_limited" if code == 429 else
                      "redirect_blocked" if type(code) is int and 300 <= code < 400 else "http_error")
    except (TimeoutError, socket.timeout):
        return finish("timeout")
    except URLError as exc:
        return finish("timeout" if isinstance(exc.reason, (TimeoutError, socket.timeout)) else "network_error")
    except (ValueError, UnicodeError, TypeError, KeyError):
        return finish("invalid_response")
    except OSError:
        return finish("network_error")
    except Exception:
        return finish("error")


def main(argv=None):
    args = argument_parser(SOURCE.name + ": " + SOURCE.notes).parse_args(argv)
    result = check(**vars(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code(result, args.live)


if __name__ == "__main__":
    raise SystemExit(main())
