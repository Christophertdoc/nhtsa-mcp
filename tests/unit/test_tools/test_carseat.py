"""Tests for carseat MCP tools with mocked upstream."""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from app.config import Settings
from app.main import AppContext
from app.nhtsa_clients.api_nhtsa_client import APINHTSAClient
from app.nhtsa_clients.vpic_client import VPICClient
from app.security.cache import AsyncTTLCache
from app.security.rate_limiter import RateLimiter

VPIC_BASE = "https://vpic.nhtsa.dot.gov/api"
NHTSA_BASE = "https://api.nhtsa.gov"

SAMPLE_STATIONS = {
    "Results": [
        {
            "Name": "Local Fire Station",
            "StreetAddress": "123 Main St",
            "City": "Washington",
            "State": "DC",
            "Zip": "20001",
            "Phone": "202-555-0100",
            "Latitude": 38.9,
            "Longitude": -77.0,
            "URL": "https://example.com",
        }
    ]
}


def make_ctx(app_ctx):
    class FakeRequestContext:
        lifespan_context = app_ctx

    class FakeContext:
        request_context = FakeRequestContext()

    return FakeContext()


@pytest.fixture
def app_ctx():
    settings = Settings(rate_limit_enabled=False)
    semaphore = asyncio.Semaphore(20)
    return AppContext(
        vpic_client=VPICClient(httpx.AsyncClient(base_url=VPIC_BASE), semaphore, settings),
        nhtsa_client=APINHTSAClient(httpx.AsyncClient(base_url=NHTSA_BASE), semaphore, settings),
        caches={
            "vin": AsyncTTLCache(maxsize=10, ttl=60),
            "ratings": AsyncTTLCache(maxsize=10, ttl=60),
            "recalls": AsyncTTLCache(maxsize=10, ttl=60),
            "complaints": AsyncTTLCache(maxsize=10, ttl=60),
            "cssi": AsyncTTLCache(maxsize=10, ttl=60),
        },
        rate_limiter=RateLimiter(enabled=False),
        settings=settings,
    )


class TestCarseatByZip:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self, app_ctx):
        respx.get(f"{NHTSA_BASE}/CSSIStation/zip/20001").mock(
            return_value=httpx.Response(200, json=SAMPLE_STATIONS)
        )
        from app.mcp_tools.carseat import carseat_stations_by_zip_tool

        ctx = make_ctx(app_ctx)
        result = await carseat_stations_by_zip_tool(ctx, zip="20001")
        assert result["summary"]["count"] == 1
        assert result["results"][0]["city"] == "Washington"


class TestCarseatByState:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self, app_ctx):
        respx.get(f"{NHTSA_BASE}/CSSIStation/state/DC").mock(
            return_value=httpx.Response(200, json=SAMPLE_STATIONS)
        )
        from app.mcp_tools.carseat import carseat_stations_by_state_tool

        ctx = make_ctx(app_ctx)
        result = await carseat_stations_by_state_tool(ctx, state="DC")
        assert result["summary"]["count"] == 1


class TestCarseatByGeo:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self, app_ctx):
        respx.get(f"{NHTSA_BASE}/CSSIStation/lat/38.9/long/-77.0/miles/25").mock(
            return_value=httpx.Response(200, json=SAMPLE_STATIONS)
        )
        from app.mcp_tools.carseat import carseat_stations_by_geo_tool

        ctx = make_ctx(app_ctx)
        result = await carseat_stations_by_geo_tool(ctx, lat=38.9, long=-77.0, miles=25)
        assert result["summary"]["count"] == 1
