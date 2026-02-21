"""Tests for decode_vin_batch MCP tool."""

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

SAMPLE_BATCH_RESPONSE = {
    "Results": [
        {
            "Make": "BMW",
            "Model": "X5",
            "ModelYear": "2011",
            "BodyClass": "Sport Utility Vehicle (SUV)",
            "VehicleType": "MULTIPURPOSE PASSENGER VEHICLE (MPV)",
            "PlantCity": "",
            "PlantCountry": "",
            "FuelTypePrimary": "Gasoline",
            "EngineCylinders": "6",
            "DisplacementL": "3.0",
            "DriveType": "",
            "TransmissionStyle": "",
            "Doors": "",
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
            "vpic_ref": AsyncTTLCache(maxsize=10, ttl=60),
            "vpic_query": AsyncTTLCache(maxsize=10, ttl=60),
        },
        rate_limiter=RateLimiter(enabled=False),
        settings=settings,
    )


class TestDecodeVinBatch:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self, app_ctx):
        respx.post(f"{VPIC_BASE}/vehicles/DecodeVINValuesBatch/").mock(
            return_value=httpx.Response(200, json=SAMPLE_BATCH_RESPONSE)
        )
        from app.mcp_tools.vpic_batch import decode_vin_batch_tool

        ctx = make_ctx(app_ctx)
        result = await decode_vin_batch_tool(ctx, vins="5UXWX7C5*BA,2011")
        assert result["summary"]["count"] == 1
        assert result["results"][0]["make"] == "BMW"

    @pytest.mark.asyncio
    async def test_empty_vins_rejected(self, app_ctx):
        from pydantic import ValidationError

        from app.mcp_tools.vpic_batch import decode_vin_batch_tool

        ctx = make_ctx(app_ctx)
        with pytest.raises(ValidationError):
            await decode_vin_batch_tool(ctx, vins="")
