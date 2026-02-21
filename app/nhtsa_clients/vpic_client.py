"""vPIC client — VIN decoding and vehicle data via vpic.nhtsa.dot.gov."""

from __future__ import annotations

from typing import Any, ClassVar

from app.nhtsa_clients.base_client import BaseNHTSAClient


class VPICClient(BaseNHTSAClient):
    ALLOWED_PATH_PREFIXES: ClassVar[list[str]] = [
        "/vehicles/DecodeVinValues/",
        "/vehicles/DecodeVinValuesExtended/",
        "/vehicles/DecodeWMI/",
        "/vehicles/DecodeVINValuesBatch/",
        "/vehicles/GetAllMakes",
        "/vehicles/GetAllManufacturers",
        "/vehicles/GetManufacturerDetails/",
        "/vehicles/GetWMIsForManufacturer/",
        "/vehicles/GetMakeForManufacturer/",
        "/vehicles/GetMakesForManufacturerAndYear/",
        "/vehicles/GetMakesForVehicleType/",
        "/vehicles/GetModelsForMake/",
        "/vehicles/GetModelsForMakeId/",
        "/vehicles/GetModelsForMakeYear/",
        "/vehicles/GetModelsForMakeIdYear/",
        "/vehicles/GetVehicleTypesForMake/",
        "/vehicles/GetVehicleTypesForMakeId/",
        "/vehicles/GetVehicleVariableList",
        "/vehicles/GetVehicleVariableValuesList/",
        "/vehicles/GetParts",
        "/vehicles/GetEquipmentPlantCodes/",
    ]

    # --- Existing ---

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

    # --- WMI ---

    async def decode_wmi(self, wmi: str) -> dict[str, Any]:
        return await self._get(f"/vehicles/DecodeWMI/{wmi}", {"format": "json"})

    # --- Batch VIN ---

    async def decode_vin_batch(self, vins: str) -> dict[str, Any]:
        return await self._post(
            "/vehicles/DecodeVINValuesBatch/",
            data={"DATA": vins, "format": "json"},
        )

    # --- Makes ---

    async def get_all_makes(self) -> dict[str, Any]:
        return await self._get("/vehicles/GetAllMakes", {"format": "json"})

    async def get_makes_for_manufacturer(self, manufacturer: str) -> dict[str, Any]:
        return await self._get(
            f"/vehicles/GetMakeForManufacturer/{manufacturer}",
            {"format": "json"},
        )

    async def get_makes_for_manufacturer_and_year(
        self, manufacturer: str, year: int
    ) -> dict[str, Any]:
        return await self._get(
            f"/vehicles/GetMakesForManufacturerAndYear/{manufacturer}",
            {"format": "json", "year": year},
        )

    async def get_makes_for_vehicle_type(self, vehicle_type: str) -> dict[str, Any]:
        return await self._get(
            f"/vehicles/GetMakesForVehicleType/{vehicle_type}",
            {"format": "json"},
        )

    # --- Manufacturers ---

    async def get_all_manufacturers(
        self,
        manufacturer_type: str | None = None,
        page: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"format": "json"}
        if manufacturer_type:
            params["ManufacturerType"] = manufacturer_type
        if page:
            params["page"] = page
        return await self._get("/vehicles/GetAllManufacturers", params)

    async def get_manufacturer_details(self, manufacturer: str) -> dict[str, Any]:
        return await self._get(
            f"/vehicles/GetManufacturerDetails/{manufacturer}",
            {"format": "json"},
        )

    async def get_wmis_for_manufacturer(
        self, manufacturer: str, vehicle_type: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"format": "json"}
        if vehicle_type:
            params["vehicleType"] = vehicle_type
        return await self._get(f"/vehicles/GetWMIsForManufacturer/{manufacturer}", params)

    # --- Models ---

    async def get_models_for_make(self, make: str) -> dict[str, Any]:
        return await self._get(f"/vehicles/GetModelsForMake/{make}", {"format": "json"})

    async def get_models_for_make_id(self, make_id: int) -> dict[str, Any]:
        return await self._get(f"/vehicles/GetModelsForMakeId/{make_id}", {"format": "json"})

    async def get_models_for_make_year(
        self,
        make: str,
        year: int | None = None,
        vehicle_type: str | None = None,
    ) -> dict[str, Any]:
        path = f"/vehicles/GetModelsForMakeYear/make/{make}"
        if year:
            path += f"/modelyear/{year}"
        if vehicle_type:
            path += f"/vehicletype/{vehicle_type}"
        return await self._get(path, {"format": "json"})

    async def get_models_for_make_id_year(
        self,
        make_id: int,
        year: int | None = None,
        vehicle_type: str | None = None,
    ) -> dict[str, Any]:
        path = f"/vehicles/GetModelsForMakeIdYear/makeId/{make_id}"
        if year:
            path += f"/modelyear/{year}"
        if vehicle_type:
            path += f"/vehicletype/{vehicle_type}"
        return await self._get(path, {"format": "json"})

    # --- Vehicle Types ---

    async def get_vehicle_types_for_make(self, make: str) -> dict[str, Any]:
        return await self._get(f"/vehicles/GetVehicleTypesForMake/{make}", {"format": "json"})

    async def get_vehicle_types_for_make_id(self, make_id: int) -> dict[str, Any]:
        return await self._get(f"/vehicles/GetVehicleTypesForMakeId/{make_id}", {"format": "json"})

    # --- Variables ---

    async def get_vehicle_variable_list(self) -> dict[str, Any]:
        return await self._get("/vehicles/GetVehicleVariableList", {"format": "json"})

    async def get_vehicle_variable_values_list(self, variable: str) -> dict[str, Any]:
        return await self._get(
            f"/vehicles/GetVehicleVariableValuesList/{variable}",
            {"format": "json"},
        )

    # --- Parts ---

    async def get_parts(
        self,
        type_: int,
        from_date: str,
        to_date: str,
        page: int | None = None,
        manufacturer: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "format": "json",
            "type": type_,
            "fromDate": from_date,
            "toDate": to_date,
        }
        if page:
            params["page"] = page
        if manufacturer:
            params["manufacturer"] = manufacturer
        return await self._get("/vehicles/GetParts", params)

    # --- Equipment Plant Codes ---

    async def get_equipment_plant_codes(self, year: int, equipment_type: int) -> dict[str, Any]:
        return await self._get(
            f"/vehicles/GetEquipmentPlantCodes/{year}",
            {"format": "json", "equipmentType": equipment_type},
        )
