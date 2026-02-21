"""Integration tests — live calls to real NHTSA endpoints.

Skipped by default. Run with: uv run pytest tests/integration/ -m integration -v
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from app.config import Settings
from app.nhtsa_clients.api_nhtsa_client import APINHTSAClient
from app.nhtsa_clients.vpic_client import VPICClient

pytestmark = pytest.mark.integration


@pytest.fixture
def settings():
    return Settings(rate_limit_enabled=False)


@pytest.fixture
def semaphore():
    return asyncio.Semaphore(5)


class TestVPICLive:
    @pytest.mark.asyncio
    async def test_decode_vin(self, settings, semaphore):
        async with httpx.AsyncClient(base_url=settings.vpic_base_url) as client:
            vpic = VPICClient(client, semaphore, settings)
            result = await vpic.decode_vin("1FA6P8AM0G5227539")
            assert "Results" in result
            assert len(result["Results"]) > 0
            r = result["Results"][0]
            assert r["Make"] == "FORD"


class TestSafetyRatingsLive:
    @pytest.mark.asyncio
    async def test_ratings_search(self, settings, semaphore):
        async with httpx.AsyncClient(base_url=settings.api_nhtsa_base_url) as client:
            nhtsa = APINHTSAClient(client, semaphore, settings)
            result = await nhtsa.ratings_search(2020, "Toyota", "Camry")
            assert "Results" in result


class TestRecallsLive:
    @pytest.mark.asyncio
    async def test_recalls_by_vehicle(self, settings, semaphore):
        async with httpx.AsyncClient(base_url=settings.api_nhtsa_base_url) as client:
            nhtsa = APINHTSAClient(client, semaphore, settings)
            result = await nhtsa.recalls_by_vehicle(2020, "Toyota", "Camry")
            assert "results" in result or "Results" in result


class TestComplaintsLive:
    @pytest.mark.asyncio
    async def test_complaints_by_vehicle(self, settings, semaphore):
        async with httpx.AsyncClient(base_url=settings.api_nhtsa_base_url) as client:
            nhtsa = APINHTSAClient(client, semaphore, settings)
            result = await nhtsa.complaints_by_vehicle(2020, "Toyota", "Camry")
            assert "results" in result or "Results" in result


class TestCSSILive:
    @pytest.mark.asyncio
    async def test_stations_by_zip(self, settings, semaphore):
        async with httpx.AsyncClient(base_url=settings.api_nhtsa_base_url) as client:
            nhtsa = APINHTSAClient(client, semaphore, settings)
            result = await nhtsa.carseat_stations_by_zip("20001")
            assert "Results" in result or "results" in result
