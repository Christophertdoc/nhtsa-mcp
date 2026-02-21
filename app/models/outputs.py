"""Output types for all MCP tools."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ToolResponse(BaseModel, Generic[T]):
    """Standard response wrapper for all MCP tools."""

    summary: dict[str, Any]
    results: list[T]
    raw_response: Any | None = None


# --- Per-domain result types ---


class VinResult(BaseModel):
    make: str
    model: str
    model_year: str
    body_class: str
    vehicle_type: str
    plant_city: str
    plant_country: str
    fuel_type: str
    engine_cylinders: str
    displacement_l: str
    drive_type: str
    transmission: str
    doors: str
    error_code: str
    error_text: str
    additional_fields: dict[str, str] = {}


class SafetyRatingResult(BaseModel):
    vehicle_id: int | None = None
    vehicle_description: str = ""
    overall_rating: str = ""
    front_crash_rating: str = ""
    side_crash_rating: str = ""
    rollover_rating: str = ""
    complaints_count: int | None = None
    recalls_count: int | None = None
    investigation_count: int | None = None


class RecallResult(BaseModel):
    nhtsa_campaign_number: str = ""
    report_received_date: str = ""
    component: str = ""
    summary: str = ""
    consequence: str = ""
    remedy: str = ""
    manufacturer: str = ""
    park_it: bool | None = None
    park_outside: bool | None = None


class ComplaintResult(BaseModel):
    odi_number: str = ""
    date_of_incident: str = ""
    date_complaint_filed: str = ""
    component: str = ""
    summary: str = ""
    crash: bool | None = None
    fire: bool | None = None
    injuries: int | None = None
    deaths: int | None = None


class CarseatStationResult(BaseModel):
    name: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    phone: str = ""
    latitude: float | None = None
    longitude: float | None = None
    distance_miles: float | None = None
    url: str = ""
