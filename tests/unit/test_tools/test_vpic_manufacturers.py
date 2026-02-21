"""Tests for get_manufacturers MCP tool."""

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

SAMPLE_ALL_MFRS = {
    "Results": [
        {
            "Mfr_ID": 955,
            "Mfr_Name": "HONDA MOTOR CO., LTD",
            "Mfr_CommonName": "Honda",
            "Country": "JAPAN",
            "VehicleTypes": [{"IsPrimary": True, "Name": "Passenger Car"}],
        }
    ]
}

SAMPLE_MFR_DETAIL = {
    "Results": [
        {
            "Mfr_ID": 955,
            "Mfr_Name": "HONDA MOTOR CO., LTD",
            "Mfr_CommonName": "Honda",
            "Country": "JAPAN",
            "VehicleTypes": [],
        }
    ]
}

SAMPLE_MFR_WMIS = {
    "Results": [
        {
            "WMI": "1HG",
            "Name": "HONDA MOTOR CO., LTD",
            "VehicleType": "Passenger Car",
            "Country": "UNITED STATES (USA)",
        }
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


class TestGetManufacturers:
    @respx.mock
    @pytest.mark.asyncio
    async def test_all_manufacturers(self, app_ctx):
        respx.get(f"{VPIC_BASE}/vehicles/GetAllManufacturers").mock(
            return_value=httpx.Response(200, json=SAMPLE_ALL_MFRS)
        )
        from app.mcp_tools.vpic_manufacturers import get_manufacturers_tool

        ctx = make_ctx(app_ctx)
        result = await get_manufacturers_tool(ctx)
        assert result["summary"]["count"] == 1
        assert result["results"][0]["name"] == "HONDA MOTOR CO., LTD"

    @respx.mock
    @pytest.mark.asyncio
    async def test_manufacturer_details(self, app_ctx):
        respx.get(f"{VPIC_BASE}/vehicles/GetManufacturerDetails/Honda").mock(
            return_value=httpx.Response(200, json=SAMPLE_MFR_DETAIL)
        )
        from app.mcp_tools.vpic_manufacturers import get_manufacturers_tool

        ctx = make_ctx(app_ctx)
        result = await get_manufacturers_tool(ctx, manufacturer="Honda")
        assert result["summary"]["count"] == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_manufacturer_wmis(self, app_ctx):
        respx.get(f"{VPIC_BASE}/vehicles/GetWMIsForManufacturer/Honda").mock(
            return_value=httpx.Response(200, json=SAMPLE_MFR_WMIS)
        )
        from app.mcp_tools.vpic_manufacturers import get_manufacturers_tool

        ctx = make_ctx(app_ctx)
        result = await get_manufacturers_tool(ctx, manufacturer="Honda", include_wmis=True)
        assert result["summary"]["count"] == 1
        assert result["results"][0]["wmi"] == "1HG"
