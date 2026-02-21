"""MCP tools: get_all_makes, get_makes — make lookups via vPIC."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from app.models.inputs import GetMakesInput
from app.models.outputs import MakeResult, ToolResponse


async def get_all_makes_tool(
    ctx: Context,
) -> dict[str, Any]:
    """Get a list of all vehicle makes registered with NHTSA.

    Returns make IDs and names. This is a large dataset — consider using
    get_makes_tool with filters for more targeted results.
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)

    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    cache_key = "all_makes"

    async def fetch() -> dict[str, Any]:
        return await app_ctx.vpic_client.get_all_makes()

    raw, cache_hit = await app_ctx.caches["vpic_ref"].get_or_fetch(cache_key, fetch)

    app_ctx.rate_limiter.record(ip_hash)

    results_list = raw.get("Results", [])
    results = [
        MakeResult(
            make_id=r.get("Make_ID"),
            make_name=r.get("Make_Name", ""),
        )
        for r in results_list
    ]

    return ToolResponse[MakeResult](
        summary={"count": len(results), "cache_hit": cache_hit},
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()


async def get_makes_tool(
    ctx: Context,
    manufacturer: str | None = None,
    vehicle_type: str | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    """Get vehicle makes filtered by manufacturer, vehicle type, and/or year.

    At least one filter must be provided. Combines GetMakeForManufacturer,
    GetMakesForManufacturerAndYear, and GetMakesForVehicleType endpoints.

    Args:
        manufacturer: Manufacturer name or ID to filter by
        vehicle_type: Vehicle type to filter by (e.g. "Passenger Car", "Truck")
        year: Model year to filter by (requires manufacturer)
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)

    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = GetMakesInput(manufacturer=manufacturer, vehicle_type=vehicle_type, year=year)

    if validated.vehicle_type and not validated.manufacturer:
        cache_key = f"makes:vtype:{validated.vehicle_type}"

        async def fetch() -> dict[str, Any]:
            return await app_ctx.vpic_client.get_makes_for_vehicle_type(validated.vehicle_type)  # type: ignore[arg-type]

        raw, cache_hit = await app_ctx.caches["vpic_query"].get_or_fetch(cache_key, fetch)
    elif validated.manufacturer and validated.year:
        cache_key = f"makes:mfr:{validated.manufacturer}:yr:{validated.year}"

        async def fetch() -> dict[str, Any]:
            return await app_ctx.vpic_client.get_makes_for_manufacturer_and_year(
                validated.manufacturer,  # type: ignore[arg-type]
                validated.year,  # type: ignore[arg-type]
            )

        raw, cache_hit = await app_ctx.caches["vpic_query"].get_or_fetch(cache_key, fetch)
    elif validated.manufacturer:
        cache_key = f"makes:mfr:{validated.manufacturer}"

        async def fetch() -> dict[str, Any]:
            return await app_ctx.vpic_client.get_makes_for_manufacturer(validated.manufacturer)  # type: ignore[arg-type]

        raw, cache_hit = await app_ctx.caches["vpic_query"].get_or_fetch(cache_key, fetch)
    else:
        return ToolResponse[MakeResult](
            summary={"error": "Provide manufacturer and/or vehicle_type", "count": 0},
            results=[],
        ).model_dump()

    app_ctx.rate_limiter.record(ip_hash)

    results_list = raw.get("Results", [])
    results = [
        MakeResult(
            make_id=r.get("MakeId") or r.get("Make_ID"),
            make_name=r.get("MakeName") or r.get("Make_Name", ""),
            manufacturer_name=r.get("MfrName", ""),
        )
        for r in results_list
    ]

    return ToolResponse[MakeResult](
        summary={"count": len(results), "cache_hit": cache_hit},
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()
