"""Async TTL cache wrapping cachetools.TTLCache with asyncio.Lock."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from cachetools import TTLCache


class AsyncTTLCache:
    """Thread-safe async TTL cache with get_or_fetch pattern."""

    def __init__(self, maxsize: int, ttl: float) -> None:
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = asyncio.Lock()

    async def get_or_fetch(
        self, key: str, fetch_fn: Callable[[], Awaitable[Any]]
    ) -> tuple[Any, bool]:
        """Return (value, cache_hit). Calls fetch_fn on miss."""
        async with self._lock:
            try:
                value = self._cache[key]
                return value, True
            except KeyError:
                pass

        # Fetch outside the lock to avoid blocking other keys,
        # but re-acquire to store.
        value = await fetch_fn()

        async with self._lock:
            self._cache[key] = value
        return value, False

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()
