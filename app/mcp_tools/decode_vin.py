"""MCP tool: decode_vin — VIN decoding via vPIC."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from app.models.inputs import DecodeVinInput
from app.models.outputs import ToolResponse, VinResult


async def decode_vin_tool(
    ctx: Context,
    vin: str,
    model_year: int | None = None,
    extended: bool = False,
) -> dict[str, Any]:
    """Decode a 17-character Vehicle Identification Number (VIN) using the NHTSA vPIC API.

    Returns detailed vehicle specifications including make, model, year, body class,
    engine, transmission, and more.

    Args:
        vin: The 17-character VIN to decode (letters I, O, Q not allowed)
        model_year: Optional model year to improve decode accuracy (1980-current+1)
        extended: If True, return extended decode fields
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)

    # Rate limit check (before validation)
    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash, is_vin=True)

    # Validate
    validated = DecodeVinInput(vin=vin, model_year=model_year, extended=extended)

    # Cache key
    cache_key = f"vin:{validated.vin}:{validated.model_year}:{validated.extended}"

    async def fetch() -> dict[str, Any]:
        return await app_ctx.vpic_client.decode_vin(
            validated.vin, validated.model_year, validated.extended
        )

    raw, cache_hit = await app_ctx.caches["vin"].get_or_fetch(cache_key, fetch)

    # Record rate limit usage
    app_ctx.rate_limiter.record(ip_hash, is_vin=True)

    # Parse response
    results_list = raw.get("Results", [])
    if not results_list:
        return ToolResponse[VinResult](
            summary={"vin": validated.vin, "count": 0},
            results=[],
            raw_response=raw if app_ctx.settings.include_raw_response else None,
        ).model_dump()

    r = results_list[0]
    vin_result = VinResult(
        make=r.get("Make", ""),
        model=r.get("Model", ""),
        model_year=r.get("ModelYear", ""),
        body_class=r.get("BodyClass", ""),
        vehicle_type=r.get("VehicleType", ""),
        plant_city=r.get("PlantCity", ""),
        plant_country=r.get("PlantCountry", ""),
        fuel_type=r.get("FuelTypePrimary", ""),
        engine_cylinders=r.get("EngineCylinders", ""),
        displacement_l=r.get("DisplacementL", ""),
        drive_type=r.get("DriveType", ""),
        transmission=r.get("TransmissionStyle", ""),
        doors=r.get("Doors", ""),
        error_code=r.get("ErrorCode", ""),
        error_text=r.get("ErrorText", ""),
    )

    return ToolResponse[VinResult](
        summary={
            "vin": validated.vin,
            "make": vin_result.make,
            "model": vin_result.model,
            "year": vin_result.model_year,
            "cache_hit": cache_hit,
        },
        results=[vin_result],
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()
