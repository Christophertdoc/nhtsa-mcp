"""Shared test fixtures."""

from __future__ import annotations

import asyncio

import pytest

from app.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        rate_limit_enabled=False,
        include_raw_response=False,
    )


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
