"""Tests for get_parts and get_equipment_plant_codes MCP tools."""

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

SAMPLE_PARTS = {
    "Results": [
        {
            "Manufacturer": "Bridgestone",
            "Name": "Turanza EL400",
            "URL": "https://example.com",
            "LetterDate": "1/15/2020",
            "Type": 565,
        }
    ]
}

SAMPLE_PLANT_CODES = {
    "Results": [
        {
            "DOTCode": "B9",
            "City": "Nashville",
            "StateProvince": "Tennessee",
            "Country": "United States",
            "Name": "Bridgestone",
            "StateCode": "TN",
            "EquipmentType": 1,
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


class TestGetParts:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self, app_ctx):
        respx.get(f"{VPIC_BASE}/vehicles/GetParts").mock(
            return_value=httpx.Response(200, json=SAMPLE_PARTS)
        )
        from app.mcp_tools.vpic_parts import get_parts_tool

        ctx = make_ctx(app_ctx)
        result = await get_parts_tool(ctx, type=565, from_date="1/1/2020", to_date="12/31/2020")
        assert result["summary"]["count"] == 1
        assert result["results"][0]["manufacturer"] == "Bridgestone"

    @pytest.mark.asyncio
    async def test_invalid_type_rejected(self, app_ctx):
        from pydantic import ValidationError

        from app.mcp_tools.vpic_parts import get_parts_tool

        ctx = make_ctx(app_ctx)
        with pytest.raises(ValidationError):
            await get_parts_tool(ctx, type=999, from_date="1/1/2020", to_date="12/31/2020")


class TestGetEquipmentPlantCodes:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self, app_ctx):
        respx.get(f"{VPIC_BASE}/vehicles/GetEquipmentPlantCodes/2020").mock(
            return_value=httpx.Response(200, json=SAMPLE_PLANT_CODES)
        )
        from app.mcp_tools.vpic_parts import get_equipment_plant_codes_tool

        ctx = make_ctx(app_ctx)
        result = await get_equipment_plant_codes_tool(ctx, year=2020, equipment_type=1)
        assert result["summary"]["count"] == 1
        assert result["results"][0]["dot_code"] == "B9"

    @pytest.mark.asyncio
    async def test_invalid_equipment_type_rejected(self, app_ctx):
        from pydantic import ValidationError

        from app.mcp_tools.vpic_parts import get_equipment_plant_codes_tool

        ctx = make_ctx(app_ctx)
        with pytest.raises(ValidationError):
            await get_equipment_plant_codes_tool(ctx, year=2020, equipment_type=99)
