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

SAMPLE_VARIANTS = {
    "Results": [
        {
            "VehicleId": 12345,
            "VehicleDescription": "2020 Toyota Camry 4 DR FWD",
        },
        {
            "VehicleId": 12346,
            "VehicleDescription": "2020 Toyota Camry 4 DR AWD",
        },
    ]
}

SAMPLE_DETAIL_12345 = {
    "Results": [
        {
            "VehicleId": 12345,
            "VehicleDescription": "2020 Toyota Camry 4 DR FWD",
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

SAMPLE_DETAIL_12346 = {
    "Results": [
        {
            "VehicleId": 12346,
            "VehicleDescription": "2020 Toyota Camry 4 DR AWD",
            "OverallRating": "4",
            "OverallFrontCrashRating": "4",
            "OverallSideCrashRating": "5",
            "RolloverRating": "3",
            "ComplaintsCount": 5,
            "RecallsCount": 1,
            "InvestigationCount": 0,
        }
    ]
}

# Used for ratings_by_vehicle_id_tool tests
SAMPLE_RATINGS = SAMPLE_DETAIL_12345


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
        # Step 1: variant listing
        respx.get(f"{NHTSA_BASE}/SafetyRatings/modelyear/2020/make/Toyota/model/Camry").mock(
            return_value=httpx.Response(200, json=SAMPLE_VARIANTS)
        )
        # Step 2: detailed ratings per variant
        respx.get(f"{NHTSA_BASE}/SafetyRatings/VehicleId/12345").mock(
            return_value=httpx.Response(200, json=SAMPLE_DETAIL_12345)
        )
        respx.get(f"{NHTSA_BASE}/SafetyRatings/VehicleId/12346").mock(
            return_value=httpx.Response(200, json=SAMPLE_DETAIL_12346)
        )
        from app.mcp_tools.ratings import ratings_search_tool

        ctx = make_ctx(app_ctx)
        result = await ratings_search_tool(ctx, model_year=2020, make="Toyota", model="Camry")
        assert result["summary"]["count"] == 2
        assert result["results"][0]["vehicle_id"] == 12345
        assert result["results"][0]["overall_rating"] == "5"
        assert result["results"][1]["vehicle_id"] == 12346
        assert result["results"][1]["overall_rating"] == "4"

    @respx.mock
    @pytest.mark.asyncio
    async def test_caches_vehicle_id_results(self, app_ctx):
        """Step 2 results are cached so ratings_by_vehicle_id_tool can reuse them."""
        respx.get(f"{NHTSA_BASE}/SafetyRatings/modelyear/2020/make/Toyota/model/Camry").mock(
            return_value=httpx.Response(200, json=SAMPLE_VARIANTS)
        )
        respx.get(f"{NHTSA_BASE}/SafetyRatings/VehicleId/12345").mock(
            return_value=httpx.Response(200, json=SAMPLE_DETAIL_12345)
        )
        respx.get(f"{NHTSA_BASE}/SafetyRatings/VehicleId/12346").mock(
            return_value=httpx.Response(200, json=SAMPLE_DETAIL_12346)
        )
        from app.mcp_tools.ratings import ratings_search_tool

        ctx = make_ctx(app_ctx)
        await ratings_search_tool(ctx, model_year=2020, make="Toyota", model="Camry")

        # Verify the cache now has the vehicle ID entries
        cached, _ = await app_ctx.caches["ratings"].get_or_fetch(
            "ratings_id:12345", lambda: None
        )
        assert cached["Results"][0]["OverallRating"] == "5"


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
