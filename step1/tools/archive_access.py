"""Shared, standard-library-only access checks; no metadata or secrets persisted."""

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    access_mode: str
    endpoint: str
    portal_url: str
    default_query: str = "Burma"
    credential_env: str = None
    requires_permission: bool = False
    notes: str = ""
    documentation_url: str = ""


MESSAGES = {
    "ready": "Configuration is ready; use --live for one request. Connectivity and access are not yet verified.",
    "ok": "One bounded request succeeded and its response structure was validated.",
    "manual_only": "Use the official portal. No documented public API is configured; no request was sent.",
    "missing_credential": "Required credential is not configured; no request was sent.",
    "credential_error": "Credential format or local credential file is invalid; no request was sent.",
    "permission_required": "This source requires prior access approval; use --permission-confirmed only after approval.",
    "invalid_input": "Use 1–5 rows and a nonempty query of at most 200 characters. Dataset checks do not accept queries.",
    "access_denied": "The source rejected authentication or access. A configured key is not proof of permission.",
    "rate_limited": "The source rate-limited this request. No retry was attempted.",
    "redirect_blocked": "The source redirected the request. No redirect was followed.",
    "http_error": "The source returned an HTTP error. No retry was attempted.",
    "timeout": "The request timed out; this does not mean zero search results.",
    "network_error": "The source could not be reached; this does not mean zero search results.",
    "invalid_response": "The response was oversized, malformed or not the expected API structure.",
    "error": "The check failed; details were suppressed to protect credentials.",
}


class CredentialError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "Invalid arguments. Use --help.\n")


def load_credential(name, env_file=None, environ=None):
    """Read one named key literally, with no dotenv dependency or shell evaluation."""
    environment = os.environ if environ is None else environ
    value = environment.get(name, "")
    if not value and env_file:
        try:
            path = Path(env_file).resolve(strict=True)
            relative = path.relative_to(PROJECT_ROOT)
            ignored = subprocess.run(
                ["git", "check-ignore", "--quiet", "--", str(relative)],
                cwd=PROJECT_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=5, check=False,
            )
            if ignored.returncode != 0 or not path.is_file() or path.stat().st_size > 65536:
                raise CredentialError
            assignments = []
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith(name + "="):
                    item = line.partition("=")[2].strip()
                    if len(item) >= 2 and item[0] == item[-1] and item[0] in "\"'":
                        item = item[1:-1]
                    assignments.append(item)
            if len(assignments) > 1:
                raise CredentialError
            value = assignments[0] if assignments else ""
        except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
            raise CredentialError from None
    if not isinstance(value, str) or len(value) > 512 or any(c.isspace() or ord(c) < 32 for c in value):
        raise CredentialError
    return value or None


def request_bytes(url, headers=None):
    request = Request(url, headers={
        "User-Agent": "PacificWarDiscoveryAccessCheck/1.0 (single metadata request)",
        **(headers or {}),
    })
    with build_opener(NoRedirect()).open(request, timeout=TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise HTTPError(url, response.status, "Unexpected status", {}, None)
        data = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError
    return data


def check_source(source, probe, *, query=None, rows=3, live=False, env_file=None,
                 permission_confirmed=False, environ=None, request=None):
    result = {
        "source": source.id, "name": source.name, "access_mode": source.access_mode,
        "endpoint": source.endpoint, "portal_url": source.portal_url,
        "documentation_url": source.documentation_url, "notes": source.notes,
        "credential_env": source.credential_env,
        "credential_state": "missing" if source.credential_env else "not_required",
        "permission_required": source.requires_permission,
        "permission_confirmed": bool(permission_confirmed) if source.requires_permission else None,
        "request_sent": False,
        "checked_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    def finish(status):
        result.update(status=status, message=MESSAGES[status])
        return result

    if source.access_mode == "portal":
        result["credential_state"] = "not_applicable"
        return finish("manual_only")
    effective_query = source.default_query if query is None else query
    if type(rows) is not int or not 1 <= rows <= 5:
        return finish("invalid_input")
    if source.access_mode == "dataset":
        if query is not None:
            return finish("invalid_input")
    elif not isinstance(effective_query, str) or not effective_query.strip() or len(effective_query) > 200:
        return finish("invalid_input")
    credential = None
    if source.credential_env:
        try:
            credential = load_credential(source.credential_env, env_file, environ)
        except CredentialError:
            result["credential_state"] = "invalid"
            return finish("credential_error")
        if not credential:
            return finish("missing_credential")
        result["credential_state"] = "configured"
    if source.requires_permission and not permission_confirmed:
        return finish("permission_required")
    if not live:
        return finish("ready")

    # Bound every provider to its documented endpoint and one request. A key
    # must never be redirected or forwarded to a different host or path.
    expected = urlsplit(source.endpoint)
    transport = request if request is not None else request_bytes

    def bounded_request(url, headers=None):
        target = urlsplit(url)
        if (result["request_sent"] or target.scheme != "https" or target.netloc != expected.netloc
                or target.path != expected.path or target.fragment or target.username or target.password):
            raise ValueError
        result["request_sent"] = True
        data = transport(url, headers=headers)
        if not isinstance(data, bytes) or len(data) > MAX_RESPONSE_BYTES:
            raise ValueError
        return data

    try:
        summary = probe(effective_query, rows, credential, bounded_request)
        # Diagnostics retain counts only. Upstream text and URLs never cross
        # this output boundary, even when an API echoes a supplied key.
        if (not result["request_sent"] or not isinstance(summary, dict)
                or set(summary) - {"sample_count", "total_results"}
                or "sample_count" not in summary
                or any(type(v) is not int or v < 0 for v in summary.values())
                or summary["sample_count"] > rows
                or ("total_results" in summary and summary["total_results"] < summary["sample_count"])):
            raise ValueError
        result.update(summary)
        return finish("ok")
    except HTTPError as exc:
        code = exc.code
        try:
            if exc.fp is not None:
                exc.close()
        except Exception:
            pass
        result["http_status"] = code if type(code) is int else None
        if code in {401, 403}:
            return finish("access_denied")
        if code == 429:
            return finish("rate_limited")
        if type(code) is int and 300 <= code < 400:
            return finish("redirect_blocked")
        return finish("http_error")
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


def exit_code(result, live):
    if result["status"] == "ok" or (not live and result["status"] in {"ready", "manual_only"}):
        return 0
    if result["status"] in {"missing_credential", "permission_required", "manual_only", "invalid_input"}:
        return 2
    return 1


def argument_parser(description):
    parser = SafeArgumentParser(description=description)
    parser.add_argument("--live", action="store_true", help="Make one request; default only checks configuration")
    parser.add_argument("--query", help="Optional API query (not supported for fixed datasets)")
    parser.add_argument("--rows", type=int, default=3, help="1–5 records, default 3")
    parser.add_argument("--env-file", help="Explicit Git-ignored credential file inside this Step 1 directory")
    parser.add_argument("--permission-confirmed", action="store_true", help="For TNA: confirm prior IP access approval")
    return parser


def run_cli(source, probe=None, argv=None):
    args = argument_parser(source.name + ": " + source.notes).parse_args(argv)
    result = check_source(source, probe, **vars(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code(result, args.live)
