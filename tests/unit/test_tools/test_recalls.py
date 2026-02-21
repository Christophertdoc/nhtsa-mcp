"""Tests for recalls MCP tools with mocked upstream."""

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

SAMPLE_RECALLS = {
    "results": [
        {
            "NHTSACampaignNumber": "20V123000",
            "ReportReceivedDate": "01/15/2020",
            "Component": "ENGINE",
            "Summary": "Engine may stall",
            "Consequence": "Loss of control",
            "Remedy": "Dealer will repair",
            "Manufacturer": "Ford Motor Company",
            "ParkIt": False,
            "ParkOutside": False,
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


class TestRecallsByVehicle:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self, app_ctx):
        respx.get(
            f"{NHTSA_BASE}/recalls/recallsByVehicle",
            params={"make": "Toyota", "model": "Camry", "modelYear": "2020"},
        ).mock(return_value=httpx.Response(200, json=SAMPLE_RECALLS))
        from app.mcp_tools.recalls import recalls_by_vehicle_tool

        ctx = make_ctx(app_ctx)
        result = await recalls_by_vehicle_tool(ctx, model_year=2020, make="Toyota", model="Camry")
        assert result["summary"]["count"] == 1
        assert result["results"][0]["nhtsa_campaign_number"] == "20V123000"


class TestRecallsByCampaign:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self, app_ctx):
        respx.get(f"{NHTSA_BASE}/recalls/campaignNumber/20V123000").mock(
            return_value=httpx.Response(200, json=SAMPLE_RECALLS)
        )
        from app.mcp_tools.recalls import recalls_by_campaign_number_tool

        ctx = make_ctx(app_ctx)
        result = await recalls_by_campaign_number_tool(ctx, campaign_number="20V123000")
        assert result["summary"]["count"] == 1
