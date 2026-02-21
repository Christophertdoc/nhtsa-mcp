"""Tests for app/security/cache.py."""

from __future__ import annotations

import asyncio

import pytest

from app.security.cache import AsyncTTLCache


class TestAsyncTTLCache:
    @pytest.mark.asyncio
    async def test_miss_calls_fetch(self):
        cache = AsyncTTLCache(maxsize=10, ttl=60)
        call_count = 0

        async def fetch():
            nonlocal call_count
            call_count += 1
            return {"data": "value"}

        result, hit = await cache.get_or_fetch("key1", fetch)
        assert result == {"data": "value"}
        assert hit is False
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_hit_skips_fetch(self):
        cache = AsyncTTLCache(maxsize=10, ttl=60)
        call_count = 0

        async def fetch():
            nonlocal call_count
            call_count += 1
            return {"data": "value"}

        await cache.get_or_fetch("key1", fetch)
        result, hit = await cache.get_or_fetch("key1", fetch)
        assert result == {"data": "value"}
        assert hit is True
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_different_keys(self):
        cache = AsyncTTLCache(maxsize=10, ttl=60)

        async def fetch_a():
            return "A"

        async def fetch_b():
            return "B"

        a, hit_a = await cache.get_or_fetch("a", fetch_a)
        b, hit_b = await cache.get_or_fetch("b", fetch_b)
        assert a == "A"
        assert b == "B"
        assert hit_a is False
        assert hit_b is False

    @pytest.mark.asyncio
    async def test_ttl_expiry(self):
        cache = AsyncTTLCache(maxsize=10, ttl=0.1)  # 100ms TTL
        call_count = 0

        async def fetch():
            nonlocal call_count
            call_count += 1
            return "value"

        await cache.get_or_fetch("key", fetch)
        assert call_count == 1

        await asyncio.sleep(0.15)

        _, hit = await cache.get_or_fetch("key", fetch)
        assert hit is False
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        cache = AsyncTTLCache(maxsize=2, ttl=60)

        async def f(v: str):
            return v

        await cache.get_or_fetch("a", lambda: f("A"))
        await cache.get_or_fetch("b", lambda: f("B"))
        await cache.get_or_fetch("c", lambda: f("C"))  # evicts "a"

        call_count = 0

        async def counting_fetch():
            nonlocal call_count
            call_count += 1
            return "A2"

        _result, hit = await cache.get_or_fetch("a", counting_fetch)
        assert hit is False  # "a" was evicted
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_clear(self):
        cache = AsyncTTLCache(maxsize=10, ttl=60)

        async def fetch():
            return "value"

        await cache.get_or_fetch("key", fetch)
        await cache.clear()

        call_count = 0

        async def counting_fetch():
            nonlocal call_count
            call_count += 1
            return "new_value"

        _result, hit = await cache.get_or_fetch("key", counting_fetch)
        assert hit is False
        assert call_count == 1
