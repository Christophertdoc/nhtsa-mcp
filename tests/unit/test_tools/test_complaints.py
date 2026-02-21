"""Tests for complaints MCP tools with mocked upstream."""

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

SAMPLE_COMPLAINTS = {
    "results": [
        {
            "odiNumber": "11234567",
            "dateOfIncident": "01/01/2020",
            "dateComplaintFiled": "02/01/2020",
            "components": "STEERING",
            "summary": "Steering wheel vibrates at highway speeds",
            "crash": False,
            "fire": False,
            "numberOfInjuries": 0,
            "numberOfDeaths": 0,
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


class TestComplaintsByVehicle:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self, app_ctx):
        respx.get(
            f"{NHTSA_BASE}/complaints/complaintsByVehicle",
            params={"make": "Honda", "model": "Civic", "modelYear": "2020"},
        ).mock(return_value=httpx.Response(200, json=SAMPLE_COMPLAINTS))
        from app.mcp_tools.complaints import complaints_by_vehicle_tool

        ctx = make_ctx(app_ctx)
        result = await complaints_by_vehicle_tool(ctx, model_year=2020, make="Honda", model="Civic")
        assert result["summary"]["count"] == 1
        assert result["results"][0]["component"] == "STEERING"


class TestComplaintsByOdi:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self, app_ctx):
        respx.get(f"{NHTSA_BASE}/complaints/odiNumber/11234567").mock(
            return_value=httpx.Response(200, json=SAMPLE_COMPLAINTS)
        )
        from app.mcp_tools.complaints import complaints_by_odi_number_tool

        ctx = make_ctx(app_ctx)
        result = await complaints_by_odi_number_tool(ctx, odi_number="11234567")
        assert result["summary"]["count"] == 1
