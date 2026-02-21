"""Tests for get_all_makes and get_makes MCP tools."""

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


def make_ctx(app_ctx: AppContext):
    class FakeRequestContext:
        lifespan_context = app_ctx

    class FakeContext:
        request_context = FakeRequestContext()

    return FakeContext()


VPIC_BASE = "https://vpic.nhtsa.dot.gov/api"
NHTSA_BASE = "https://api.nhtsa.gov"

SAMPLE_ALL_MAKES = {
    "Results": [
        {"Make_ID": 440, "Make_Name": "ASTON MARTIN"},
        {"Make_ID": 441, "Make_Name": "TOYOTA"},
    ]
}

SAMPLE_MAKES_FOR_MFR = {
    "Results": [
        {"MakeId": 474, "MakeName": "HONDA", "MfrName": "HONDA MOTOR CO., LTD"},
    ]
}


@pytest.fixture
def app_ctx():
    settings = Settings(rate_limit_enabled=False)
    semaphore = asyncio.Semaphore(20)
    vpic_http = httpx.AsyncClient(base_url=VPIC_BASE)
    nhtsa_http = httpx.AsyncClient(base_url=NHTSA_BASE)
    return AppContext(
        vpic_client=VPICClient(vpic_http, semaphore, settings),
        nhtsa_client=APINHTSAClient(nhtsa_http, semaphore, settings),
        caches={
            "vin": AsyncTTLCache(maxsize=10, ttl=60),
            "ratings": AsyncTTLCache(maxsize=10, ttl=60),
            "recalls": AsyncTTLCache(maxsize=10, ttl=60),
            "complaints": AsyncTTLCache(maxsize=10, ttl=60),
            "cssi": AsyncTTLCache(maxsize=10, ttl=60),
            "vpic_ref": AsyncTTLCache(maxsize=10, ttl=60),
            "vpic_query": AsyncTTLCache(maxsize=10, ttl=60),
        },
        rate_limiter=RateLimiter(enabled=False),
        settings=settings,
    )


class TestGetAllMakes:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self, app_ctx):
        respx.get(f"{VPIC_BASE}/vehicles/GetAllMakes").mock(
            return_value=httpx.Response(200, json=SAMPLE_ALL_MAKES)
        )
        from app.mcp_tools.vpic_makes import get_all_makes_tool

        ctx = make_ctx(app_ctx)
        result = await get_all_makes_tool(ctx)
        assert result["summary"]["count"] == 2
        assert result["results"][0]["make_name"] == "ASTON MARTIN"


class TestGetMakes:
    @respx.mock
    @pytest.mark.asyncio
    async def test_by_manufacturer(self, app_ctx):
        respx.get(f"{VPIC_BASE}/vehicles/GetMakeForManufacturer/Honda").mock(
            return_value=httpx.Response(200, json=SAMPLE_MAKES_FOR_MFR)
        )
        from app.mcp_tools.vpic_makes import get_makes_tool

        ctx = make_ctx(app_ctx)
        result = await get_makes_tool(ctx, manufacturer="Honda")
        assert result["summary"]["count"] == 1
        assert result["results"][0]["make_name"] == "HONDA"

    @respx.mock
    @pytest.mark.asyncio
    async def test_by_vehicle_type(self, app_ctx):
        respx.get(f"{VPIC_BASE}/vehicles/GetMakesForVehicleType/Passenger Car").mock(
            return_value=httpx.Response(200, json=SAMPLE_ALL_MAKES)
        )
        from app.mcp_tools.vpic_makes import get_makes_tool

        ctx = make_ctx(app_ctx)
        result = await get_makes_tool(ctx, vehicle_type="Passenger Car")
        assert result["summary"]["count"] == 2

    @pytest.mark.asyncio
    async def test_no_filters_returns_error(self, app_ctx):
        from app.mcp_tools.vpic_makes import get_makes_tool

        ctx = make_ctx(app_ctx)
        result = await get_makes_tool(ctx)
        assert result["summary"]["count"] == 0
        assert "error" in result["summary"]
