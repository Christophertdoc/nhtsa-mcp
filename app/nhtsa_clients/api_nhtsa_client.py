"""api.nhtsa.gov client — Safety Ratings, Recalls, Complaints, CSSI stations."""

from __future__ import annotations

from typing import Any, ClassVar

from app.nhtsa_clients.base_client import BaseNHTSAClient


class APINHTSAClient(BaseNHTSAClient):
    ALLOWED_PATH_PREFIXES: ClassVar[list[str]] = [
        "/SafetyRatings",
        "/recalls/recallsByVehicle",
        "/recalls/campaignNumber",
        "/complaints/complaintsByVehicle",
        "/complaints/odiNumber",
        "/CSSIStation",
    ]

    # --- Safety Ratings ---

    async def ratings_search(self, model_year: int, make: str, model: str) -> dict[str, Any]:
        path = f"/SafetyRatings/modelyear/{model_year}/make/{make}/model/{model}"
        params = {"format": "json"}
        return await self._get(path, params)

    async def ratings_by_vehicle_id(self, vehicle_id: int) -> dict[str, Any]:
        path = f"/SafetyRatings/VehicleId/{vehicle_id}"
        params = {"format": "json"}
        return await self._get(path, params)

    # --- Recalls ---

    async def recalls_by_vehicle(self, model_year: int, make: str, model: str) -> dict[str, Any]:
        path = f"/recalls/recallsByVehicle?make={make}&model={model}&modelYear={model_year}"
        return await self._get(path)

    async def recalls_by_campaign_number(self, campaign_number: str) -> dict[str, Any]:
        path = f"/recalls/campaignNumber/{campaign_number}"
        return await self._get(path)

    # --- Complaints ---

    async def complaints_by_vehicle(self, model_year: int, make: str, model: str) -> dict[str, Any]:
        path = f"/complaints/complaintsByVehicle?make={make}&model={model}&modelYear={model_year}"
        return await self._get(path)

    async def complaints_by_odi_number(self, odi_number: str) -> dict[str, Any]:
        path = f"/complaints/odiNumber/{odi_number}"
        return await self._get(path)

    # --- Car Seat Inspection Stations ---

    async def carseat_stations_by_zip(
        self,
        zip_code: str,
        lang: str | None = None,
        cpsweek: bool | None = None,
    ) -> dict[str, Any]:
        path = self._build_cssi_path(f"/CSSIStation/zip/{zip_code}", lang, cpsweek)
        return await self._get(path)

    async def carseat_stations_by_state(
        self,
        state: str,
        lang: str | None = None,
        cpsweek: bool | None = None,
    ) -> dict[str, Any]:
        path = self._build_cssi_path(f"/CSSIStation/state/{state}", lang, cpsweek)
        return await self._get(path)

    async def carseat_stations_by_geo(
        self,
        lat: float,
        long: float,
        miles: int = 25,
        lang: str | None = None,
        cpsweek: bool | None = None,
    ) -> dict[str, Any]:
        path = self._build_cssi_path(
            f"/CSSIStation/lat/{lat}/long/{long}/miles/{miles}", lang, cpsweek
        )
        return await self._get(path)

    @staticmethod
    def _build_cssi_path(base: str, lang: str | None, cpsweek: bool | None) -> str:
        path = base
        if lang and lang == "spanish":
            path += "/lang/spanish"
        if cpsweek:
            path += "/cpsweek"
        return path
