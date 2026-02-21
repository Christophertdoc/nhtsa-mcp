"""Tests for get_models MCP tool."""

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

SAMPLE_MODELS = {
    "Results": [
        {"Make_ID": 474, "Make_Name": "HONDA", "Model_ID": 1861, "Model_Name": "Civic"},
        {"Make_ID": 474, "Make_Name": "HONDA", "Model_ID": 1862, "Model_Name": "Accord"},
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


class TestGetModels:
    @respx.mock
    @pytest.mark.asyncio
    async def test_by_make_name(self, app_ctx):
        respx.get(f"{VPIC_BASE}/vehicles/GetModelsForMake/Honda").mock(
            return_value=httpx.Response(200, json=SAMPLE_MODELS)
        )
        from app.mcp_tools.vpic_models import get_models_tool

        ctx = make_ctx(app_ctx)
        result = await get_models_tool(ctx, make="Honda")
        assert result["summary"]["count"] == 2
        assert result["results"][0]["model_name"] == "Civic"

    @respx.mock
    @pytest.mark.asyncio
    async def test_by_make_id(self, app_ctx):
        respx.get(f"{VPIC_BASE}/vehicles/GetModelsForMakeId/474").mock(
            return_value=httpx.Response(200, json=SAMPLE_MODELS)
        )
        from app.mcp_tools.vpic_models import get_models_tool

        ctx = make_ctx(app_ctx)
        result = await get_models_tool(ctx, make_id=474)
        assert result["summary"]["count"] == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_by_make_and_year(self, app_ctx):
        respx.get(f"{VPIC_BASE}/vehicles/GetModelsForMakeYear/make/Honda/modelyear/2020").mock(
            return_value=httpx.Response(200, json=SAMPLE_MODELS)
        )
        from app.mcp_tools.vpic_models import get_models_tool

        ctx = make_ctx(app_ctx)
        result = await get_models_tool(ctx, make="Honda", year=2020)
        assert result["summary"]["count"] == 2

    @pytest.mark.asyncio
    async def test_neither_make_nor_id_rejected(self, app_ctx):
        from pydantic import ValidationError

        from app.mcp_tools.vpic_models import get_models_tool

        ctx = make_ctx(app_ctx)
        with pytest.raises(ValidationError):
            await get_models_tool(ctx)
