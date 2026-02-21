"""Tests for app/security/rate_limiter.py."""

from __future__ import annotations

import pytest

from app.security.rate_limiter import RateLimiter, RateLimitExceededError


class TestRateLimiter:
    def test_global_limit_pass(self):
        rl = RateLimiter(global_per_minute=60)
        ip = rl.hash_ip("127.0.0.1")
        for _ in range(60):
            rl.check(ip)
            rl.record(ip)

    def test_global_limit_exceeded(self):
        rl = RateLimiter(global_per_minute=5)
        ip = rl.hash_ip("127.0.0.1")
        for _ in range(5):
            rl.check(ip)
            rl.record(ip)
        with pytest.raises(RateLimitExceededError, match="global"):
            rl.check(ip)

    def test_vin_limit_pass(self):
        rl = RateLimiter(vin_per_minute=10)
        ip = rl.hash_ip("127.0.0.1")
        for _ in range(10):
            rl.check(ip, is_vin=True)
            rl.record(ip, is_vin=True)

    def test_vin_limit_exceeded(self):
        rl = RateLimiter(vin_per_minute=3)
        ip = rl.hash_ip("127.0.0.1")
        for _ in range(3):
            rl.check(ip, is_vin=True)
            rl.record(ip, is_vin=True)
        with pytest.raises(RateLimitExceededError, match="vin"):
            rl.check(ip, is_vin=True)

    def test_daily_limit_exceeded(self):
        rl = RateLimiter(global_per_minute=10000, daily_quota=5)
        ip = rl.hash_ip("127.0.0.1")
        for _ in range(5):
            rl.check(ip)
            rl.record(ip)
        with pytest.raises(RateLimitExceededError, match="daily"):
            rl.check(ip)

    def test_independent_ip_buckets(self):
        rl = RateLimiter(global_per_minute=2)
        ip1 = rl.hash_ip("1.1.1.1")
        ip2 = rl.hash_ip("2.2.2.2")
        for _ in range(2):
            rl.check(ip1)
            rl.record(ip1)
        with pytest.raises(RateLimitExceededError):
            rl.check(ip1)
        # ip2 should still be fine
        rl.check(ip2)
        rl.record(ip2)

    def test_disabled(self):
        rl = RateLimiter(global_per_minute=1, enabled=False)
        ip = rl.hash_ip("127.0.0.1")
        # Should not raise even after exceeding limit
        for _ in range(100):
            rl.check(ip)
            rl.record(ip)

    def test_window_expiry(self):
        rl = RateLimiter(global_per_minute=2)
        ip = rl.hash_ip("127.0.0.1")
        # Fill the window
        rl.check(ip)
        rl.record(ip)
        rl.check(ip)
        rl.record(ip)
        with pytest.raises(RateLimitExceededError):
            rl.check(ip)

        # Simulate time passing by manipulating window timestamps
        window = rl._global_windows[ip]
        # Move all timestamps back by 61 seconds
        old_ts = list(window)
        window.clear()
        for ts in old_ts:
            window.append(ts - 61)

        # Should pass now
        rl.check(ip)

    def test_hash_ip_consistent(self):
        ip = "192.168.1.1"
        h1 = RateLimiter.hash_ip(ip)
        h2 = RateLimiter.hash_ip(ip)
        assert h1 == h2
        assert h1.startswith("sha256:")

    def test_hash_ip_different_ips(self):
        h1 = RateLimiter.hash_ip("1.1.1.1")
        h2 = RateLimiter.hash_ip("2.2.2.2")
        assert h1 != h2

    def test_retry_after_positive(self):
        rl = RateLimiter(global_per_minute=1)
        ip = rl.hash_ip("127.0.0.1")
        rl.check(ip)
        rl.record(ip)
        with pytest.raises(RateLimitExceededError) as exc_info:
            rl.check(ip)
        assert exc_info.value.retry_after > 0
