"""Tests for ratings MCP tools with mocked upstream."""

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

SAMPLE_RATINGS = {
    "Results": [
        {
            "VehicleId": 12345,
            "VehicleDescription": "2020 Toyota Camry",
            "OverallRating": "5",
            "OverallFrontCrashRating": "5",
            "OverallSideCrashRating": "5",
            "RolloverRating": "4",
            "ComplaintsCount": 10,
            "RecallsCount": 2,
            "InvestigationCount": 0,
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


class TestRatingsSearch:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self, app_ctx):
        respx.get(f"{NHTSA_BASE}/SafetyRatings/modelyear/2020/make/Toyota/model/Camry").mock(
            return_value=httpx.Response(200, json=SAMPLE_RATINGS)
        )
        from app.mcp_tools.ratings import ratings_search_tool

        ctx = make_ctx(app_ctx)
        result = await ratings_search_tool(ctx, model_year=2020, make="Toyota", model="Camry")
        assert result["summary"]["count"] == 1
        assert result["results"][0]["overall_rating"] == "5"
        assert result["results"][0]["vehicle_id"] == 12345


class TestRatingsByVehicleId:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self, app_ctx):
        respx.get(f"{NHTSA_BASE}/SafetyRatings/VehicleId/12345").mock(
            return_value=httpx.Response(200, json=SAMPLE_RATINGS)
        )
        from app.mcp_tools.ratings import ratings_by_vehicle_id_tool

        ctx = make_ctx(app_ctx)
        result = await ratings_by_vehicle_id_tool(ctx, vehicle_id=12345)
        assert result["summary"]["count"] == 1
        assert result["results"][0]["overall_rating"] == "5"
