"""Per-IP sliding window rate limiter — pure in-memory."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import time
from collections import deque
from typing import Any


class RateLimitExceededError(Exception):
    """Raised when a rate limit is exceeded."""

    def __init__(self, retry_after: float, limit_type: str = "global") -> None:
        self.retry_after = retry_after
        self.limit_type = limit_type
        super().__init__(f"Rate limit exceeded ({limit_type}). Retry after {retry_after:.1f}s")


class RateLimiter:
    """Sliding-window rate limiter keyed by hashed IP."""

    def __init__(
        self,
        global_per_minute: int = 60,
        vin_per_minute: int = 10,
        daily_quota: int = 1000,
        enabled: bool = True,
    ) -> None:
        self.global_per_minute = global_per_minute
        self.vin_per_minute = vin_per_minute
        self.daily_quota = daily_quota
        self.enabled = enabled

        # Keyed by ip_hash → deque of timestamps
        self._global_windows: dict[str, deque[float]] = {}
        self._vin_windows: dict[str, deque[float]] = {}
        self._daily_windows: dict[str, deque[float]] = {}

        self._prune_task: asyncio.Task[None] | None = None

    @staticmethod
    def hash_ip(ip: str) -> str:
        return f"sha256:{hashlib.sha256(ip.encode()).hexdigest()[:16]}"

    def check(self, ip_hash: str, is_vin: bool = False) -> None:
        """Raise RateLimitExceededError if any limit is exceeded."""
        if not self.enabled:
            return

        now = time.monotonic()
        day_seconds = 86400.0

        # Daily quota
        daily = self._daily_windows.setdefault(ip_hash, deque())
        self._prune_window(daily, now, day_seconds)
        if len(daily) >= self.daily_quota:
            raise RateLimitExceededError(
                retry_after=self._time_until_slot(daily, now, day_seconds),
                limit_type="daily",
            )

        # Global per-minute
        global_w = self._global_windows.setdefault(ip_hash, deque())
        self._prune_window(global_w, now, 60.0)
        if len(global_w) >= self.global_per_minute:
            raise RateLimitExceededError(
                retry_after=self._time_until_slot(global_w, now, 60.0),
                limit_type="global",
            )

        # VIN per-minute (only for VIN-related tools)
        if is_vin:
            vin_w = self._vin_windows.setdefault(ip_hash, deque())
            self._prune_window(vin_w, now, 60.0)
            if len(vin_w) >= self.vin_per_minute:
                raise RateLimitExceededError(
                    retry_after=self._time_until_slot(vin_w, now, 60.0),
                    limit_type="vin",
                )

    def record(self, ip_hash: str, is_vin: bool = False) -> None:
        """Record a successful request."""
        now = time.monotonic()
        self._global_windows.setdefault(ip_hash, deque()).append(now)
        self._daily_windows.setdefault(ip_hash, deque()).append(now)
        if is_vin:
            self._vin_windows.setdefault(ip_hash, deque()).append(now)

    @staticmethod
    def _prune_window(window: deque[float], now: float, window_size: float) -> None:
        cutoff = now - window_size
        while window and window[0] < cutoff:
            window.popleft()

    @staticmethod
    def _time_until_slot(window: deque[float], now: float, window_size: float) -> float:
        if window:
            return max(0.0, window[0] + window_size - now)
        return 0.0

    async def start_pruning(self) -> None:
        """Start background task to prune stale buckets every 5 minutes."""
        self._prune_task = asyncio.create_task(self._prune_loop())

    async def stop_pruning(self) -> None:
        if self._prune_task:
            self._prune_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._prune_task

    async def _prune_loop(self) -> None:
        while True:
            await asyncio.sleep(300)
            now = time.monotonic()
            self._prune_all(self._global_windows, now, 60.0)
            self._prune_all(self._vin_windows, now, 60.0)
            self._prune_all(self._daily_windows, now, 86400.0)

    def _prune_all(
        self,
        windows: dict[str, deque[float]],
        now: float,
        window_size: float,
    ) -> None:
        empty_keys: list[Any] = []
        for key, window in windows.items():
            self._prune_window(window, now, window_size)
            if not window:
                empty_keys.append(key)
        for key in empty_keys:
            del windows[key]
