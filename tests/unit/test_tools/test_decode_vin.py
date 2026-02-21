"""Tests for decode_vin MCP tool with mocked upstream."""

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
    """Create a minimal mock MCP Context."""

    class FakeRequestContext:
        lifespan_context = app_ctx

    class FakeContext:
        request_context = FakeRequestContext()

    return FakeContext()


VPIC_BASE = "https://vpic.nhtsa.dot.gov/api"
NHTSA_BASE = "https://api.nhtsa.gov"

SAMPLE_VIN_RESPONSE = {
    "Results": [
        {
            "Make": "FORD",
            "Model": "Mustang",
            "ModelYear": "2016",
            "BodyClass": "Coupe",
            "VehicleType": "PASSENGER CAR",
            "PlantCity": "FLAT ROCK",
            "PlantCountry": "UNITED STATES (USA)",
            "FuelTypePrimary": "Gasoline",
            "EngineCylinders": "8",
            "DisplacementL": "5.0",
            "DriveType": "RWD",
            "TransmissionStyle": "Manual",
            "Doors": "2",
            "ErrorCode": "0",
            "ErrorText": "",
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
        },
        rate_limiter=RateLimiter(enabled=False),
        settings=settings,
    )


class TestDecodeVin:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self, app_ctx):
        respx.get(f"{VPIC_BASE}/vehicles/DecodeVinValues/1FA6P8AM0G5227539").mock(
            return_value=httpx.Response(200, json=SAMPLE_VIN_RESPONSE)
        )
        from app.mcp_tools.decode_vin import decode_vin_tool

        ctx = make_ctx(app_ctx)
        result = await decode_vin_tool(ctx, vin="1FA6P8AM0G5227539")
        assert result["summary"]["make"] == "FORD"
        assert result["summary"]["model"] == "Mustang"
        assert result["summary"]["year"] == "2016"
        assert len(result["results"]) == 1
        assert result["results"][0]["body_class"] == "Coupe"

    @respx.mock
    @pytest.mark.asyncio
    async def test_cache_hit(self, app_ctx):
        route = respx.get(f"{VPIC_BASE}/vehicles/DecodeVinValues/1FA6P8AM0G5227539").mock(
            return_value=httpx.Response(200, json=SAMPLE_VIN_RESPONSE)
        )
        from app.mcp_tools.decode_vin import decode_vin_tool

        ctx = make_ctx(app_ctx)
        await decode_vin_tool(ctx, vin="1FA6P8AM0G5227539")
        result = await decode_vin_tool(ctx, vin="1FA6P8AM0G5227539")
        assert result["summary"]["cache_hit"] is True
        assert route.call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_upstream_500(self, app_ctx):
        respx.get(f"{VPIC_BASE}/vehicles/DecodeVinValues/1FA6P8AM0G5227539").mock(
            return_value=httpx.Response(500, text="Server Error")
        )
        from app.mcp_tools.decode_vin import decode_vin_tool
        from app.nhtsa_clients.base_client import UpstreamServerError

        ctx = make_ctx(app_ctx)
        with pytest.raises(UpstreamServerError):
            await decode_vin_tool(ctx, vin="1FA6P8AM0G5227539")

    @pytest.mark.asyncio
    async def test_invalid_vin_rejected(self, app_ctx):
        from pydantic import ValidationError

        from app.mcp_tools.decode_vin import decode_vin_tool

        ctx = make_ctx(app_ctx)
        with pytest.raises(ValidationError):
            await decode_vin_tool(ctx, vin="INVALID")
