"""vPIC client — VIN decoding via vpic.nhtsa.dot.gov."""

from __future__ import annotations

from typing import Any, ClassVar

from app.nhtsa_clients.base_client import BaseNHTSAClient


class VPICClient(BaseNHTSAClient):
    ALLOWED_PATH_PREFIXES: ClassVar[list[str]] = [
        "/vehicles/DecodeVinValues/",
        "/vehicles/DecodeVinValuesExtended/",
    ]

    async def decode_vin(
        self,
        vin: str,
        model_year: int | None = None,
        extended: bool = False,
    ) -> dict[str, Any]:
        endpoint = "DecodeVinValuesExtended" if extended else "DecodeVinValues"
        path = f"/vehicles/{endpoint}/{vin}"
        params: dict[str, Any] = {"format": "json"}
        if model_year is not None:
            params["modelyear"] = model_year
        return await self._get(path, params)
