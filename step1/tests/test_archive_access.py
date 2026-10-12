"""Offline access-contract tests; all requests and credentials are synthetic."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError


TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import archive_access as api


FAKE_KEY = "synthetic-contract-test-key-never-a-real-credential"
KEY_NAME = "CONTRACT_TEST_API_KEY"
ENDPOINT = "https://archive.example.invalid/search"


def source(**overrides):
    settings = {
        "id": "contract_test",
        "name": "Synthetic archive",
        "access_mode": "api",
        "endpoint": ENDPOINT,
        "portal_url": "https://archive.example.invalid/",
        "default_query": "Burma",
    }
    settings.update(overrides)
    return api.Source(**settings)


def json_probe(query, rows, credential, request):
    """A tiny fake adapter exercising the shared transport/error boundary."""
    headers = {"Authorization": "Bearer " + credential} if credential else None
    return json.loads(request(ENDPOINT, headers=headers))


class PreflightTests(unittest.TestCase):
    def check_without_request(self, definition, **kwargs):
        request = MagicMock(side_effect=AssertionError("Network must remain unused"))
        probe = MagicMock(side_effect=AssertionError("Probe must remain unused"))
        result = api.check_source(
            definition, probe, environ=kwargs.pop("environ", {}), request=request, **kwargs
        )
        probe.assert_not_called()
        request.assert_not_called()
        self.assertFalse(result["request_sent"])
        self.assertEqual(result["source"], definition.id)
        return result

    def test_public_api_is_ready_by_default_without_credentials(self):
        result = self.check_without_request(source())
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["credential_state"], "not_required")

    def test_public_dataset_is_ready_without_credentials(self):
        result = self.check_without_request(source(access_mode="dataset"))
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["credential_state"], "not_required")

    def test_public_source_does_not_need_an_unrelated_api_key(self):
        result = self.check_without_request(source(), environ={"UNRELATED_API_KEY": ""})
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["credential_state"], "not_required")

    def test_required_key_missing_blocks_even_live_requests(self):
        for live in (False, True):
            with self.subTest(live=live):
                result = self.check_without_request(source(credential_env=KEY_NAME), live=live)
                self.assertEqual(result["status"], "missing_credential")
                self.assertEqual(result["credential_state"], "missing")

    def test_other_platform_key_does_not_unlock_key_required_source(self):
        result = self.check_without_request(
            source(credential_env=KEY_NAME), live=True,
            environ={"SOME_OTHER_API_KEY": FAKE_KEY},
        )
        self.assertEqual(result["status"], "missing_credential")
        self.assertEqual(result["credential_state"], "missing")

    def test_configured_key_is_not_validated_by_default(self):
        result = self.check_without_request(
            source(credential_env=KEY_NAME), environ={KEY_NAME: FAKE_KEY}
        )
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["credential_state"], "configured")
        self.assertNotIn(FAKE_KEY, json.dumps(result))

    def test_environment_mapping_is_used_instead_of_ambient_credentials(self):
        with patch.dict(os.environ, {KEY_NAME: FAKE_KEY}):
            result = self.check_without_request(source(credential_env=KEY_NAME), environ={})
        self.assertEqual(result["status"], "missing_credential")

    def test_permission_required_cannot_be_bypassed_by_live_flag(self):
        for live in (False, True):
            with self.subTest(live=live):
                result = self.check_without_request(source(requires_permission=True), live=live)
                self.assertEqual(result["status"], "permission_required")

    def test_permission_confirmation_still_does_not_enable_network_by_default(self):
        result = self.check_without_request(
            source(requires_permission=True), permission_confirmed=True
        )
        self.assertEqual(result["status"], "ready")

    def test_portal_is_manual_only_even_when_live_and_permission_confirmed(self):
        result = self.check_without_request(
            source(access_mode="portal", endpoint=""),
            live=True, permission_confirmed=True,
        )
        self.assertEqual(result["status"], "manual_only")
        self.assertEqual(result["credential_state"], "not_applicable")

    def test_invalid_rows_do_not_start_a_request(self):
        for rows in (0, -1, True, "3"):
            with self.subTest(rows=rows):
                result = self.check_without_request(source(), rows=rows, live=True)
                self.assertEqual(result["status"], "invalid_input")

    def test_dataset_does_not_silently_ignore_a_search_query(self):
        result = self.check_without_request(
            source(access_mode="dataset"), query="Burma", live=True
        )
        self.assertEqual(result["status"], "query_not_supported")
        self.assertEqual(api.exit_code(result, True), 2)

    def test_empty_key_cannot_start_a_live_request(self):
        result = self.check_without_request(
            source(credential_env=KEY_NAME), environ={KEY_NAME: ""}, live=True
        )
        self.assertEqual(result["status"], "missing_credential")

    def test_newline_in_key_is_rejected_without_request(self):
        result = self.check_without_request(
            source(credential_env=KEY_NAME), environ={KEY_NAME: FAKE_KEY + "\nInjected: header"},
            live=True,
        )
        self.assertEqual(result["status"], "credential_error")
        self.assertEqual(result["credential_state"], "invalid")
        self.assertNotIn(FAKE_KEY, json.dumps(result))


class LiveRequestTests(unittest.TestCase):
    def test_public_live_request_reports_counts_without_requiring_key(self):
        request = MagicMock(return_value=b'{"sample_count": 2, "total_results": 17}')
        result = api.check_source(source(), json_probe, live=True, environ={}, request=request)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["request_sent"])
        self.assertEqual(result["credential_state"], "not_required")
        self.assertEqual(result["sample_count"], 2)
        self.assertEqual(result["total_results"], 17)
        request.assert_called_once_with(ENDPOINT, headers=None)

    def test_configured_key_is_passed_to_probe_but_never_returned(self):
        request = MagicMock(return_value=b'{"sample_count": 1}')
        result = api.check_source(
            source(credential_env=KEY_NAME), json_probe, live=True,
            environ={KEY_NAME: FAKE_KEY}, request=request,
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["credential_state"], "configured")
        request.assert_called_once_with(ENDPOINT, headers={"Authorization": "Bearer " + FAKE_KEY})
        self.assertNotIn(FAKE_KEY, json.dumps(result))

    def test_empty_success_is_distinct_from_failed_access(self):
        request = MagicMock(return_value=b'{"sample_count": 0, "total_results": 0}')
        result = api.check_source(source(), json_probe, live=True, environ={}, request=request)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["sample_count"], 0)
        self.assertEqual(result["total_results"], 0)

    def test_default_query_rows_and_transport_are_forwarded(self):
        request = MagicMock()
        probe = MagicMock(return_value={"sample_count": 0})
        api.check_source(source(), probe, live=True, environ={}, request=request)
        probe.assert_called_once()
        args = probe.call_args.args
        self.assertEqual(args[:3], ("Burma", 3, None))
        self.assertTrue(callable(args[3]))

    def test_explicit_query_rows_and_confirmed_permission_reach_probe(self):
        request = MagicMock(return_value=b'{"sample_count": 0}')
        seen = []

        def probe(query, rows, credential, transport):
            seen.append((query, rows))
            return json_probe(query, rows, credential, transport)

        result = api.check_source(
            source(requires_permission=True), probe, query="China Burma India", rows=2,
            live=True, permission_confirmed=True, environ={}, request=request,
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(seen, [("China Burma India", 2)])
        request.assert_called_once()


class ErrorAndRedactionTests(unittest.TestCase):
    def check_failure(self, failure, expected_status):
        request = MagicMock(side_effect=failure)
        captured = io.StringIO()
        with redirect_stdout(captured), redirect_stderr(captured):
            result = api.check_source(
                source(credential_env=KEY_NAME), json_probe, live=True,
                environ={KEY_NAME: FAKE_KEY}, request=request,
            )
        self.assertEqual(result["status"], expected_status)
        self.assertTrue(result["request_sent"])
        self.assertNotIn(FAKE_KEY, json.dumps(result) + captured.getvalue())
        self.assertNotIn("wskey=", json.dumps(result) + captured.getvalue())
        request.assert_called_once()
        return result

    def test_invalid_key_and_forbidden_access_are_redacted(self):
        for status in (401, 403):
            with self.subTest(status=status):
                self.check_failure(
                    HTTPError(
                        ENDPOINT + "?wskey=" + FAKE_KEY, status, FAKE_KEY, {},
                        io.BytesIO(FAKE_KEY.encode()),
                    ), "access_denied",
                )

    def test_rate_limit_is_reported_without_retries(self):
        self.check_failure(
            HTTPError(ENDPOINT + "?wskey=" + FAKE_KEY, 429, FAKE_KEY, {}, None),
            "rate_limited",
        )

    def test_timeout_is_reported(self):
        self.check_failure(TimeoutError(FAKE_KEY), "timeout")

    def test_wrapped_socket_timeout_is_reported_as_timeout(self):
        self.check_failure(URLError(socket.timeout(FAKE_KEY)), "timeout")

    def test_connection_failure_is_reported_without_raw_reason(self):
        self.check_failure(URLError(FAKE_KEY), "network_error")

    def test_invalid_json_is_reported_without_response_body(self):
        request = MagicMock(return_value=FAKE_KEY.encode())
        result = api.check_source(
            source(credential_env=KEY_NAME), json_probe, live=True,
            environ={KEY_NAME: FAKE_KEY}, request=request,
        )
        self.assertEqual(result["status"], "invalid_response")
        self.assertNotIn(FAKE_KEY, json.dumps(result))

    def test_probe_value_error_is_sanitized(self):
        self.check_failure(ValueError(FAKE_KEY), "invalid_response")

    def test_unexpected_exception_does_not_leak_secret_or_url(self):
        self.check_failure(RuntimeError(ENDPOINT + "?wskey=" + FAKE_KEY), "error")

    def test_probe_cannot_add_raw_response_or_credentials_to_output(self):
        for extra in ({"api_key": FAKE_KEY}, {"records": [{"title": FAKE_KEY}]}, {"url": ENDPOINT + "?wskey=" + FAKE_KEY}):
            with self.subTest(field=next(iter(extra))):
                request = MagicMock(return_value=json.dumps({"sample_count": 1, **extra}).encode())
                result = api.check_source(
                    source(credential_env=KEY_NAME), json_probe, live=True,
                    environ={KEY_NAME: FAKE_KEY}, request=request,
                )
                self.assertEqual(result["status"], "invalid_response")
                self.assertNotIn(FAKE_KEY, json.dumps(result))

    def test_summary_requires_nonnegative_integer_counts(self):
        payloads = [
            {}, [], {"sample_count": -1}, {"sample_count": True},
            {"sample_count": "1"}, {"sample_count": 1, "total_results": -1},
            {"sample_count": 1, "total_results": True},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                request = MagicMock(return_value=json.dumps(payload).encode())
                result = api.check_source(source(), json_probe, live=True, environ={}, request=request)
                self.assertEqual(result["status"], "invalid_response")


class EnvironmentFileTests(unittest.TestCase):
    def test_environment_takes_priority_over_nonexistent_env_file(self):
        result = api.check_source(
            source(credential_env=KEY_NAME), MagicMock(),
            environ={KEY_NAME: FAKE_KEY}, env_file=TOOLS / ".env.does-not-exist",
        )
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["credential_state"], "configured")

    def test_nonexistent_env_file_is_a_credential_error(self):
        request = MagicMock()
        result = api.check_source(
            source(credential_env=KEY_NAME), json_probe, live=True,
            environ={}, env_file=TOOLS / ".env.does-not-exist", request=request,
        )
        self.assertEqual(result["status"], "credential_error")
        self.assertEqual(result["credential_state"], "invalid")
        request.assert_not_called()

    def check_file(self, contents, *, ignored=True, live=False, probe=None):
        with tempfile.TemporaryDirectory() as directory:
            project_root = Path(directory).resolve()
            env_file = project_root / ".env.access-test"
            env_file.write_text(contents, encoding="utf-8")
            request = MagicMock(return_value=b'{"sample_count": 0}')
            with patch.object(api, "PROJECT_ROOT", project_root), patch.object(
                api.subprocess, "run", return_value=MagicMock(returncode=0 if ignored else 1)
            ) as run:
                result = api.check_source(
                    source(credential_env=KEY_NAME), probe or json_probe,
                    env_file=env_file, environ={}, live=live, request=request,
                )
            return result, request, run

    def test_ignored_env_file_can_supply_key(self):
        result, request, run = self.check_file(KEY_NAME + "=" + FAKE_KEY + "\n")
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["credential_state"], "configured")
        self.assertNotIn(FAKE_KEY, json.dumps(result))
        request.assert_not_called()
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][:3], ["git", "check-ignore", "--quiet"])

    def test_env_file_values_are_literal_and_never_shell_evaluated(self):
        literal = "$(do-not-execute)"
        observed = []

        def probe(query, rows, credential, request):
            observed.append(credential)
            return json_probe(query, rows, credential, request)

        result, request, run = self.check_file(KEY_NAME + "=" + literal + "\n", live=True, probe=probe)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(observed, [literal])
        self.assertNotIn(literal, json.dumps(result))
        run.assert_called_once()
        self.assertFalse(run.call_args.kwargs.get("shell", False))
        self.assertEqual(run.call_args.args[0][:3], ["git", "check-ignore", "--quiet"])
        request.assert_called_once()

    def test_env_file_with_only_other_platform_key_means_missing_credential(self):
        result, request, _ = self.check_file("UNRELATED_API_KEY=" + FAKE_KEY + "\n", live=True)
        self.assertEqual(result["status"], "missing_credential")
        self.assertEqual(result["credential_state"], "missing")
        request.assert_not_called()

    def test_unignored_env_file_is_rejected_without_request(self):
        result, request, _ = self.check_file(KEY_NAME + "=" + FAKE_KEY + "\n", ignored=False, live=True)
        self.assertEqual(result["status"], "credential_error")
        self.assertEqual(result["credential_state"], "invalid")
        self.assertNotIn(FAKE_KEY, json.dumps(result))
        request.assert_not_called()

    def test_duplicate_key_is_rejected_without_request(self):
        result, request, _ = self.check_file(
            KEY_NAME + "=" + FAKE_KEY + "\n" + KEY_NAME + "=second-value\n", live=True
        )
        self.assertEqual(result["status"], "credential_error")
        self.assertEqual(result["credential_state"], "invalid")
        self.assertNotIn(FAKE_KEY, json.dumps(result))
        request.assert_not_called()

    def test_env_file_outside_project_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            project_root = base / "project"
            project_root.mkdir()
            env_file = base / ".env.outside-project"
            env_file.write_text(KEY_NAME + "=" + FAKE_KEY + "\n", encoding="utf-8")
            request = MagicMock()
            with patch.object(api, "PROJECT_ROOT", project_root):
                result = api.check_source(
                    source(credential_env=KEY_NAME), json_probe,
                    env_file=env_file, environ={}, live=True, request=request,
                )
            self.assertEqual(result["status"], "credential_error")
            self.assertEqual(result["credential_state"], "invalid")
            request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
