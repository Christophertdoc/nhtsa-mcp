"""MCP tool: decode_vin_batch — batch VIN decoding via vPIC."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from app.models.inputs import DecodeVinBatchInput
from app.models.outputs import ToolResponse, VinResult


async def decode_vin_batch_tool(
    ctx: Context,
    vins: str,
) -> dict[str, Any]:
    """Decode multiple VINs in a single batch request (max 50).

    Each entry is a VIN optionally followed by a comma and model year.
    Entries are separated by semicolons.
    Example: "5UXWX7C5*BA,2011;5YJSA3DS*EF"

    Args:
        vins: Semicolon-separated VINs, optionally with model year after comma (max 50)
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)

    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash, is_vin=True)

    validated = DecodeVinBatchInput(vins=vins)

    cache_key = f"vin_batch:{validated.vins}"

    async def fetch() -> dict[str, Any]:
        return await app_ctx.vpic_client.decode_vin_batch(validated.vins)

    raw, cache_hit = await app_ctx.caches["vin"].get_or_fetch(cache_key, fetch)

    app_ctx.rate_limiter.record(ip_hash, is_vin=True)

    results_list = raw.get("Results", [])
    results = [
        VinResult(
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
        for r in results_list
    ]

    return ToolResponse[VinResult](
        summary={"count": len(results), "cache_hit": cache_hit},
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()
