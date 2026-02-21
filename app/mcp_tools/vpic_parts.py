"""MCP tools: get_parts, get_equipment_plant_codes — parts and plant code lookups via vPIC."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from app.models.inputs import GetEquipmentPlantCodesInput, GetPartsInput
from app.models.outputs import EquipmentPlantResult, PartsResult, ToolResponse


async def get_parts_tool(
    ctx: Context,
    type: int,
    from_date: str,
    to_date: str,
    page: int | None = None,
    manufacturer: str | None = None,
) -> dict[str, Any]:
    """Search NHTSA parts (565 = tire, 566 = rim) by date range.

    Args:
        type: Part type code (565 for tires, 566 for rims)
        from_date: Start date in M/D/YYYY format
        to_date: End date in M/D/YYYY format
        page: Page number for paginated results (1-1000)
        manufacturer: Filter by manufacturer name or ID
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)

    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = GetPartsInput(
        type=type, from_date=from_date, to_date=to_date, page=page, manufacturer=manufacturer
    )

    cache_key = (
        f"parts:{validated.type}:{validated.from_date}:{validated.to_date}"
        f":{validated.page}:{validated.manufacturer}"
    )

    async def fetch() -> dict[str, Any]:
        return await app_ctx.vpic_client.get_parts(
            validated.type,
            validated.from_date,
            validated.to_date,
            validated.page,
            validated.manufacturer,
        )

    raw, cache_hit = await app_ctx.caches["vpic_query"].get_or_fetch(cache_key, fetch)

    app_ctx.rate_limiter.record(ip_hash)

    results_list = raw.get("Results", [])
    results = [
        PartsResult(
            manufacturer=r.get("Manufacturer", ""),
            name=r.get("Name", ""),
            url=r.get("URL", ""),
            letter_date=r.get("LetterDate", ""),
            type_code=str(r.get("Type", "")),
        )
        for r in results_list
    ]

    return ToolResponse[PartsResult](
        summary={"count": len(results), "cache_hit": cache_hit, "type": validated.type},
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()


async def get_equipment_plant_codes_tool(
    ctx: Context,
    year: int,
    equipment_type: int,
) -> dict[str, Any]:
    """Get equipment plant codes for a given year and equipment type.

    Args:
        year: Model year (1980-current+1)
        equipment_type: Equipment type (1=Tires, 3=Brake Hoses, 13=Glazing, 16=Retread Tires)
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)

    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = GetEquipmentPlantCodesInput(year=year, equipment_type=equipment_type)

    cache_key = f"equip_plant:{validated.year}:{validated.equipment_type}"

    async def fetch() -> dict[str, Any]:
        return await app_ctx.vpic_client.get_equipment_plant_codes(
            validated.year, validated.equipment_type
        )

    raw, cache_hit = await app_ctx.caches["vpic_query"].get_or_fetch(cache_key, fetch)

    app_ctx.rate_limiter.record(ip_hash)

    results_list = raw.get("Results", [])
    results = [
        EquipmentPlantResult(
            dot_code=r.get("DOTCode", ""),
            plant_city=r.get("City", ""),
            plant_state=r.get("StateProvince", ""),
            plant_country=r.get("Country", ""),
            name=r.get("Name", ""),
            state_code=r.get("StateCode", ""),
            equipment_type=str(r.get("EquipmentType", "")),
        )
        for r in results_list
    ]

    return ToolResponse[EquipmentPlantResult](
        summary={
            "count": len(results),
            "cache_hit": cache_hit,
            "year": validated.year,
            "equipment_type": validated.equipment_type,
        },
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()
