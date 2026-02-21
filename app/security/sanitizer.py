"""Output sanitization and safe error mapping."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.nhtsa_clients.base_client import (
    UpstreamClientError,
    UpstreamConnectError,
    UpstreamRateLimitError,
    UpstreamServerError,
    UpstreamTimeoutError,
)
from app.security.rate_limiter import RateLimitExceededError

REDACTED_FIELDS = frozenset(
    {
        "traceback",
        "stack_trace",
        "exception",
        "internal_url",
        "x-api-key",
        "authorization",
        "cookie",
        "set-cookie",
        "x-forwarded-for",
        "x-real-ip",
    }
)

MAX_STRING_LENGTH = 50_000


def sanitize_output(data: Any) -> Any:
    """Remove sensitive fields and truncate oversized strings."""
    if isinstance(data, dict):
        return {k: sanitize_output(v) for k, v in data.items() if k.lower() not in REDACTED_FIELDS}
    if isinstance(data, list):
        return [sanitize_output(item) for item in data]
    if isinstance(data, str) and len(data) > MAX_STRING_LENGTH:
        return data[:MAX_STRING_LENGTH] + "... [truncated]"
    return data


class SafeError:
    """Structured error for tool responses."""

    def __init__(
        self,
        code: str,
        message: str,
        status: int,
        retry_after: float | None = None,
    ):
        self.code = code
        self.message = message
        self.status = status
        self.retry_after = retry_after

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"error": self.code, "message": self.message}
        if self.retry_after is not None:
            d["retry_after"] = self.retry_after
        return d


def sanitize_error(exc: Exception) -> SafeError:
    """Map exception types to safe user-facing error info."""
    if isinstance(exc, ValidationError):
        messages = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        return SafeError("VALIDATION_ERROR", messages, 400)

    if isinstance(exc, ValueError):
        return SafeError("VALIDATION_ERROR", str(exc), 400)

    if isinstance(exc, RateLimitExceededError):
        return SafeError(
            "RATE_LIMIT_EXCEEDED",
            str(exc),
            429,
            retry_after=exc.retry_after,
        )

    if isinstance(exc, UpstreamRateLimitError):
        return SafeError(
            "UPSTREAM_RATE_LIMITED",
            "NHTSA API rate limit reached. Try again later.",
            429,
        )

    if isinstance(exc, UpstreamServerError):
        return SafeError(
            "UPSTREAM_ERROR",
            "NHTSA API returned a server error. Try again later.",
            502,
        )

    if isinstance(exc, UpstreamTimeoutError):
        return SafeError(
            "UPSTREAM_TIMEOUT",
            "NHTSA API request timed out. Try again later.",
            504,
        )

    if isinstance(exc, UpstreamConnectError):
        return SafeError(
            "UPSTREAM_UNREACHABLE",
            "Could not connect to NHTSA API.",
            502,
        )

    if isinstance(exc, UpstreamClientError):
        if exc.status_code == 404:
            return SafeError(
                "NOT_FOUND",
                "No results found for the given query.",
                404,
            )
        return SafeError(
            "UPSTREAM_ERROR",
            f"NHTSA API returned an error ({exc.status_code}).",
            exc.status_code,
        )

    return SafeError("INTERNAL_ERROR", "An unexpected error occurred.", 500)
