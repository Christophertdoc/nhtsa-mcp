"""Pydantic v2 input validators — security boundary for all MCP tool inputs."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator


def _current_year() -> int:
    return datetime.now(tz=UTC).year


# --- Validators ---


def validate_vin(v: str) -> str:
    v = v.upper().strip()
    if len(v) != 17:
        raise ValueError("VIN must be exactly 17 characters")
    if not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", v):
        raise ValueError("VIN contains invalid characters (I, O, Q not allowed; alphanumeric only)")
    return v


def validate_model_year(v: int) -> int:
    if v < 1980:
        raise ValueError("model_year must be >= 1980")
    if v > _current_year() + 1:
        raise ValueError(f"model_year must be <= {_current_year() + 1}")
    return v


def validate_make_model(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("Value must not be empty")
    if len(v) > 64:
        raise ValueError("Value must be 64 characters or fewer")
    if not re.fullmatch(r"[A-Za-z0-9 \-]+", v):
        raise ValueError("Only letters, digits, spaces, and hyphens allowed")
    return v.title()


def validate_campaign_number(v: str) -> str:
    v = v.upper().strip()
    if not re.fullmatch(r"\d{2}[A-Z]\d{6}", v):
        raise ValueError(
            "campaign_number must match pattern: 2 digits, 1 letter, 6 digits (e.g. 20V123000)"
        )
    return v


def validate_odi_number(v: str) -> str:
    v = v.strip()
    if not re.fullmatch(r"\d{5,12}", v):
        raise ValueError("odi_number must be 5-12 digits")
    return v


def validate_zip_code(v: str) -> str:
    v = v.strip()
    # Normalize ZIP+4 to 5-digit
    if re.fullmatch(r"\d{5}-\d{4}", v):
        v = v[:5]
    if not re.fullmatch(r"\d{5}", v):
        raise ValueError("zip must be a 5-digit ZIP code (ZIP+4 accepted)")
    return v


US_STATE_CODES = frozenset(
    {
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "CT",
        "DE",
        "FL",
        "GA",
        "HI",
        "ID",
        "IL",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NH",
        "NJ",
        "NM",
        "NY",
        "NC",
        "ND",
        "OH",
        "OK",
        "OR",
        "PA",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
        "DC",
        "AS",
        "GU",
        "MP",
        "PR",
        "VI",  # DC + territories
    }
)


def validate_state(v: str) -> str:
    v = v.upper().strip()
    if v not in US_STATE_CODES:
        raise ValueError(f"state must be a valid US state/territory code, got '{v}'")
    return v


def validate_wmi(v: str) -> str:
    v = v.upper().strip()
    if len(v) not in (3, 6):
        raise ValueError("WMI must be 3 or 6 characters")
    if not re.fullmatch(r"[A-HJ-NPR-Z0-9]{3,6}", v):
        raise ValueError("WMI contains invalid characters")
    return v


def validate_manufacturer(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("manufacturer must not be empty")
    if len(v) > 128:
        raise ValueError("manufacturer must be 128 characters or fewer")
    if not re.fullmatch(r"[A-Za-z0-9 \-&.,]+", v):
        raise ValueError("manufacturer contains invalid characters")
    return v


def validate_page(v: int) -> int:
    if v < 1:
        raise ValueError("page must be >= 1")
    if v > 1000:
        raise ValueError("page must be <= 1000")
    return v


def validate_positive_id(v: int) -> int:
    if v <= 0:
        raise ValueError("ID must be a positive integer")
    return v


def validate_vehicle_type(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("vehicle_type must not be empty")
    if len(v) > 64:
        raise ValueError("vehicle_type must be 64 characters or fewer")
    if not re.fullmatch(r"[A-Za-z0-9 \-/]+", v):
        raise ValueError("vehicle_type contains invalid characters")
    return v


def validate_date_mmddyyyy(v: str) -> str:
    v = v.strip()
    if not re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", v):
        raise ValueError("Date must be in M/D/YYYY format")
    parts = v.split("/")
    month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
    if not (1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100):
        raise ValueError("Date values out of range")
    return v


def validate_variable_name_or_id(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("variable must not be empty")
    if len(v) > 128:
        raise ValueError("variable must be 128 characters or fewer")
    if not re.fullmatch(r"[A-Za-z0-9 \-_]+", v):
        raise ValueError("variable contains invalid characters")
    return v


def validate_vin_batch(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("vins must not be empty")
    entries = [e.strip() for e in v.split(";") if e.strip()]
    if len(entries) > 50:
        raise ValueError("Maximum 50 VINs per batch")
    if len(entries) == 0:
        raise ValueError("At least one VIN required")
    return v


def validate_equipment_type(v: int) -> int:
    if v not in (1, 3, 13, 16):
        raise ValueError("equipment_type must be 1, 3, 13, or 16")
    return v


def validate_parts_type(v: int) -> int:
    if v not in (565, 566):
        raise ValueError("parts_type must be 565 or 566")
    return v


def validate_lang(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.lower().strip()
    mapping = {"en": "english", "english": "english", "es": "spanish", "spanish": "spanish"}
    result = mapping.get(v)
    if result is None:
        raise ValueError("lang must be one of: en, english, es, spanish")
    return result


# --- Annotated types ---

Vin = Annotated[str, AfterValidator(validate_vin)]
ModelYear = Annotated[int, AfterValidator(validate_model_year)]
MakeModel = Annotated[str, AfterValidator(validate_make_model)]
CampaignNumber = Annotated[str, AfterValidator(validate_campaign_number)]
OdiNumber = Annotated[str, AfterValidator(validate_odi_number)]
ZipCode = Annotated[str, AfterValidator(validate_zip_code)]
StateCode = Annotated[str, AfterValidator(validate_state)]
Lang = Annotated[str | None, AfterValidator(validate_lang)]
WMI = Annotated[str, AfterValidator(validate_wmi)]
Manufacturer = Annotated[str, AfterValidator(validate_manufacturer)]
Page = Annotated[int, AfterValidator(validate_page)]
PositiveId = Annotated[int, AfterValidator(validate_positive_id)]
VehicleType = Annotated[str, AfterValidator(validate_vehicle_type)]
DateMMDDYYYY = Annotated[str, AfterValidator(validate_date_mmddyyyy)]
VariableNameOrId = Annotated[str, AfterValidator(validate_variable_name_or_id)]
VinBatch = Annotated[str, AfterValidator(validate_vin_batch)]
EquipmentType = Annotated[int, AfterValidator(validate_equipment_type)]
PartsType = Annotated[int, AfterValidator(validate_parts_type)]


# --- Input models ---


class DecodeVinInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    vin: Vin
    model_year: ModelYear | None = None
    extended: bool = False


class RatingsSearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    model_year: ModelYear
    make: MakeModel
    model: MakeModel


class RatingsByVehicleIdInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    vehicle_id: int = Field(gt=0)


class RecallsByVehicleInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    model_year: ModelYear
    make: MakeModel
    model: MakeModel


class RecallsByCampaignInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    campaign_number: CampaignNumber


class ComplaintsByVehicleInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    model_year: ModelYear
    make: MakeModel
    model: MakeModel


class ComplaintsByOdiInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    odi_number: OdiNumber


class CarseatByZipInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    zip: ZipCode
    lang: Lang = None
    cpsweek: bool | None = None


class CarseatByStateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    state: StateCode
    lang: Lang = None
    cpsweek: bool | None = None


class CarseatByGeoInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    lat: float = Field(ge=-90.0, le=90.0)
    long: float = Field(ge=-180.0, le=180.0)
    miles: int = Field(default=25, ge=1, le=200)
    lang: Lang = None
    cpsweek: bool | None = None


# --- vPIC input models ---


class DecodeWMIInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    wmi: WMI


class DecodeVinBatchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    vins: VinBatch


class GetManufacturersInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    manufacturer: Manufacturer | None = None
    page: Page | None = None
    manufacturer_type: str | None = None
    include_wmis: bool = False
    vehicle_type: VehicleType | None = None


class GetMakesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    manufacturer: Manufacturer | None = None
    vehicle_type: VehicleType | None = None
    year: ModelYear | None = None


class GetModelsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    make: MakeModel | None = None
    make_id: PositiveId | None = None
    year: ModelYear | None = None
    vehicle_type: VehicleType | None = None

    @model_validator(mode="after")
    def check_make_xor_make_id(self) -> GetModelsInput:
        if self.make and self.make_id:
            raise ValueError("Provide either make or make_id, not both")
        if not self.make and not self.make_id:
            raise ValueError("Provide either make or make_id")
        return self


class GetVehicleTypesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    make: MakeModel | None = None
    make_id: PositiveId | None = None

    @model_validator(mode="after")
    def check_make_xor_make_id(self) -> GetVehicleTypesInput:
        if self.make and self.make_id:
            raise ValueError("Provide either make or make_id, not both")
        if not self.make and not self.make_id:
            raise ValueError("Provide either make or make_id")
        return self


class GetVehicleVariablesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    variable: VariableNameOrId | None = None


class GetPartsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    type: PartsType
    from_date: DateMMDDYYYY
    to_date: DateMMDDYYYY
    page: Page | None = None
    manufacturer: Manufacturer | None = None


class GetEquipmentPlantCodesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    year: ModelYear
    equipment_type: EquipmentType
