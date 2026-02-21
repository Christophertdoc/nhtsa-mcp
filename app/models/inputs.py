"""Pydantic v2 input validators — security boundary for all MCP tool inputs."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


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
