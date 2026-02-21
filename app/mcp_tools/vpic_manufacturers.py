"""MCP tool: get_manufacturers — manufacturer lookups via vPIC."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from app.models.inputs import GetManufacturersInput
from app.models.outputs import (
    ManufacturerResult,
    ManufacturerWMIResult,
    ToolResponse,
)


async def get_manufacturers_tool(
    ctx: Context,
    manufacturer: str | None = None,
    page: int | None = None,
    manufacturer_type: str | None = None,
    include_wmis: bool = False,
    vehicle_type: str | None = None,
) -> dict[str, Any]:
    """Look up vehicle manufacturers from the NHTSA vPIC database.

    Without a specific manufacturer, returns a paginated list of all manufacturers.
    With a manufacturer name/ID, returns detailed info or associated WMIs.

    Args:
        manufacturer: Manufacturer name or numeric ID for detail/WMI lookup
        page: Page number for paginated results (1-1000)
        manufacturer_type: Filter by manufacturer type (e.g. "Completed Vehicle Manufacturer")
        include_wmis: If True and manufacturer is provided, return WMIs instead of details
        vehicle_type: Filter WMIs by vehicle type (only with include_wmis=True)
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)

    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = GetManufacturersInput(
        manufacturer=manufacturer,
        page=page,
        manufacturer_type=manufacturer_type,
        include_wmis=include_wmis,
        vehicle_type=vehicle_type,
    )

    if validated.manufacturer and validated.include_wmis:
        cache_key = f"mfr_wmis:{validated.manufacturer}:{validated.vehicle_type}"

        async def fetch() -> dict[str, Any]:
            return await app_ctx.vpic_client.get_wmis_for_manufacturer(
                validated.manufacturer,  # type: ignore[arg-type]
                validated.vehicle_type,
            )

        raw, cache_hit = await app_ctx.caches["vpic_query"].get_or_fetch(cache_key, fetch)

        app_ctx.rate_limiter.record(ip_hash)

        results_list = raw.get("Results", [])
        wmi_results = [
            ManufacturerWMIResult(
                wmi=r.get("WMI", ""),
                name=r.get("Name", ""),
                vehicle_type=r.get("VehicleType", ""),
                country=r.get("Country", ""),
            )
            for r in results_list
        ]

        return ToolResponse[ManufacturerWMIResult](
            summary={
                "manufacturer": validated.manufacturer,
                "count": len(wmi_results),
                "cache_hit": cache_hit,
            },
            results=wmi_results,
            raw_response=raw if app_ctx.settings.include_raw_response else None,
        ).model_dump()

    elif validated.manufacturer:
        cache_key = f"mfr_detail:{validated.manufacturer}"

        async def fetch() -> dict[str, Any]:
            return await app_ctx.vpic_client.get_manufacturer_details(
                validated.manufacturer  # type: ignore[arg-type]
            )

        raw, cache_hit = await app_ctx.caches["vpic_query"].get_or_fetch(cache_key, fetch)

    else:
        cache_key = f"mfr_all:{validated.manufacturer_type}:{validated.page}"

        async def fetch() -> dict[str, Any]:
            return await app_ctx.vpic_client.get_all_manufacturers(
                validated.manufacturer_type, validated.page
            )

        raw, cache_hit = await app_ctx.caches["vpic_query"].get_or_fetch(cache_key, fetch)

    app_ctx.rate_limiter.record(ip_hash)

    results_list = raw.get("Results", [])
    results = [
        ManufacturerResult(
            manufacturer_id=r.get("Mfr_ID"),
            name=r.get("Mfr_Name", ""),
            common_name=r.get("Mfr_CommonName") or "",
            country=r.get("Country", ""),
            vehicle_types=r.get("VehicleTypes", []),
        )
        for r in results_list
    ]

    return ToolResponse[ManufacturerResult](
        summary={
            "count": len(results),
            "cache_hit": cache_hit,
            "page": validated.page,
        },
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()
