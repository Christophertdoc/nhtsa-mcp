"""Base HTTP client with retry, semaphore, path allowlist, and typed exceptions."""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import Settings

logger = structlog.get_logger()


# --- Typed exceptions ---


class UpstreamError(Exception):
    """Base for all upstream errors."""


class UpstreamServerError(UpstreamError):
    """5xx from upstream."""


class UpstreamClientError(UpstreamError):
    """4xx from upstream (not rate-limit)."""

    def __init__(self, status_code: int, detail: str = "") -> None:
        self.status_code = status_code
        super().__init__(f"Upstream returned {status_code}: {detail}")


class UpstreamRateLimitError(UpstreamError):
    """429 from upstream."""


class UpstreamTimeoutError(UpstreamError):
    """Timeout reaching upstream."""


class UpstreamConnectError(UpstreamError):
    """Connection failed to upstream."""


class PathNotAllowedError(Exception):
    """Path is not in the allowlist."""


class BaseNHTSAClient:
    """Shared HTTP client logic for all NHTSA API surfaces."""

    ALLOWED_PATH_PREFIXES: ClassVar[list[str]] = []

    def __init__(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        settings: Settings,
    ) -> None:
        self._client = client
        self._semaphore = semaphore
        self._settings = settings

    def _assert_allowlisted_path(self, path: str) -> None:
        for prefix in self.ALLOWED_PATH_PREFIXES:
            if path.startswith(prefix):
                return
        raise PathNotAllowedError(f"Path not in allowlist: {path}")

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self._assert_allowlisted_path(path)

        @retry(
            stop=stop_after_attempt(self._settings.retry_max_attempts),
            wait=wait_exponential(
                min=self._settings.retry_wait_min_seconds,
                max=self._settings.retry_wait_max_seconds,
                multiplier=2,
            ),
            retry=retry_if_exception_type(
                (UpstreamServerError, UpstreamTimeoutError, UpstreamConnectError)
            ),
            reraise=True,
        )
        async def _do_get() -> Any:
            async with self._semaphore:
                try:
                    response = await self._client.get(path, params=params)
                except httpx.TimeoutException as exc:
                    raise UpstreamTimeoutError(str(exc)) from exc
                except httpx.ConnectError as exc:
                    raise UpstreamConnectError(str(exc)) from exc

                if response.status_code == 429:
                    raise UpstreamRateLimitError("Upstream rate limited")
                if response.status_code >= 500:
                    raise UpstreamServerError(f"Upstream returned {response.status_code}")
                if response.status_code >= 400:
                    raise UpstreamClientError(response.status_code, response.text[:200])

                return response.json()

        return await _do_get()

    async def _post(self, path: str, data: dict[str, Any] | None = None) -> Any:
        self._assert_allowlisted_path(path)

        @retry(
            stop=stop_after_attempt(self._settings.retry_max_attempts),
            wait=wait_exponential(
                min=self._settings.retry_wait_min_seconds,
                max=self._settings.retry_wait_max_seconds,
                multiplier=2,
            ),
            retry=retry_if_exception_type(
                (UpstreamServerError, UpstreamTimeoutError, UpstreamConnectError)
            ),
            reraise=True,
        )
        async def _do_post() -> Any:
            async with self._semaphore:
                try:
                    response = await self._client.post(path, data=data)
                except httpx.TimeoutException as exc:
                    raise UpstreamTimeoutError(str(exc)) from exc
                except httpx.ConnectError as exc:
                    raise UpstreamConnectError(str(exc)) from exc

                if response.status_code == 429:
                    raise UpstreamRateLimitError("Upstream rate limited")
                if response.status_code >= 500:
                    raise UpstreamServerError(f"Upstream returned {response.status_code}")
                if response.status_code >= 400:
                    raise UpstreamClientError(response.status_code, response.text[:200])

                return response.json()

        return await _do_post()
