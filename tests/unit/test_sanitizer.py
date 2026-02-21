"""Tests for app/security/sanitizer.py."""

from __future__ import annotations

from pydantic import ValidationError

from app.nhtsa_clients.base_client import (
    UpstreamClientError,
    UpstreamConnectError,
    UpstreamServerError,
    UpstreamTimeoutError,
)
from app.security.rate_limiter import RateLimitExceededError
from app.security.sanitizer import sanitize_error, sanitize_output


class TestSanitizeOutput:
    def test_strips_redacted_fields(self):
        data = {
            "make": "Toyota",
            "traceback": "secret stack trace",
            "authorization": "Bearer xyz",
        }
        result = sanitize_output(data)
        assert "make" in result
        assert "traceback" not in result
        assert "authorization" not in result

    def test_nested_dict(self):
        data = {"outer": {"traceback": "secret", "value": "ok"}}
        result = sanitize_output(data)
        assert "traceback" not in result["outer"]
        assert result["outer"]["value"] == "ok"

    def test_list_of_dicts(self):
        data = [{"x-api-key": "secret", "name": "ok"}]
        result = sanitize_output(data)
        assert "x-api-key" not in result[0]
        assert result[0]["name"] == "ok"

    def test_truncates_long_strings(self):
        data = {"field": "x" * 60000}
        result = sanitize_output(data)
        assert len(result["field"]) < 60000
        assert result["field"].endswith("... [truncated]")

    def test_short_strings_untouched(self):
        data = {"field": "short"}
        result = sanitize_output(data)
        assert result["field"] == "short"

    def test_case_insensitive_field_names(self):
        data = {"Traceback": "secret", "AUTHORIZATION": "secret2", "data": "ok"}
        result = sanitize_output(data)
        assert "Traceback" not in result
        assert "AUTHORIZATION" not in result
        assert result["data"] == "ok"


class TestSanitizeError:
    def test_validation_error(self):
        try:
            from app.models.inputs import DecodeVinInput

            DecodeVinInput(vin="short")
        except ValidationError as e:
            safe = sanitize_error(e)
            assert safe.code == "VALIDATION_ERROR"
            assert safe.status == 400

    def test_value_error(self):
        safe = sanitize_error(ValueError("bad input"))
        assert safe.code == "VALIDATION_ERROR"
        assert safe.status == 400

    def test_rate_limit_exceeded(self):
        safe = sanitize_error(RateLimitExceededError(retry_after=30.0))
        assert safe.code == "RATE_LIMIT_EXCEEDED"
        assert safe.status == 429
        assert safe.retry_after == 30.0

    def test_upstream_server_error(self):
        safe = sanitize_error(UpstreamServerError("500"))
        assert safe.code == "UPSTREAM_ERROR"
        assert safe.status == 502
        assert "stack" not in safe.message.lower()

    def test_upstream_timeout(self):
        safe = sanitize_error(UpstreamTimeoutError("timed out"))
        assert safe.code == "UPSTREAM_TIMEOUT"
        assert safe.status == 504

    def test_upstream_connect_error(self):
        safe = sanitize_error(UpstreamConnectError("refused"))
        assert safe.code == "UPSTREAM_UNREACHABLE"
        assert safe.status == 502

    def test_upstream_404(self):
        safe = sanitize_error(UpstreamClientError(404, "not found"))
        assert safe.code == "NOT_FOUND"
        assert safe.status == 404

    def test_unexpected_error(self):
        safe = sanitize_error(RuntimeError("something broke"))
        assert safe.code == "INTERNAL_ERROR"
        assert safe.status == 500
        assert "something broke" not in safe.message
