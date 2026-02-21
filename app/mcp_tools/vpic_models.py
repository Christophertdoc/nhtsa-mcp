"""MCP tool: get_models — model lookups via vPIC."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from app.models.inputs import GetModelsInput
from app.models.outputs import ModelResult, ToolResponse


async def get_models_tool(
    ctx: Context,
    make: str | None = None,
    make_id: int | None = None,
    year: int | None = None,
    vehicle_type: str | None = None,
) -> dict[str, Any]:
    """Get vehicle models for a given make, optionally filtered by year and vehicle type.

    Provide either make (name) or make_id (numeric), not both.

    Args:
        make: Make name (e.g. "Honda", "Ford")
        make_id: Numeric make ID from NHTSA
        year: Model year to filter by
        vehicle_type: Vehicle type to filter by (e.g. "Passenger Car")
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)

    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = GetModelsInput(make=make, make_id=make_id, year=year, vehicle_type=vehicle_type)

    if validated.make and (validated.year or validated.vehicle_type):
        cache_key = f"models:make:{validated.make}:yr:{validated.year}:vt:{validated.vehicle_type}"

        async def fetch() -> dict[str, Any]:
            return await app_ctx.vpic_client.get_models_for_make_year(
                validated.make,  # type: ignore[arg-type]
                validated.year,
                validated.vehicle_type,
            )

        raw, cache_hit = await app_ctx.caches["vpic_query"].get_or_fetch(cache_key, fetch)

    elif validated.make_id and (validated.year or validated.vehicle_type):
        cache_key = f"models:id:{validated.make_id}:yr:{validated.year}:vt:{validated.vehicle_type}"

        async def fetch() -> dict[str, Any]:
            return await app_ctx.vpic_client.get_models_for_make_id_year(
                validated.make_id,  # type: ignore[arg-type]
                validated.year,
                validated.vehicle_type,
            )

        raw, cache_hit = await app_ctx.caches["vpic_query"].get_or_fetch(cache_key, fetch)

    elif validated.make:
        cache_key = f"models:make:{validated.make}"

        async def fetch() -> dict[str, Any]:
            return await app_ctx.vpic_client.get_models_for_make(validated.make)  # type: ignore[arg-type]

        raw, cache_hit = await app_ctx.caches["vpic_query"].get_or_fetch(cache_key, fetch)

    else:
        cache_key = f"models:id:{validated.make_id}"

        async def fetch() -> dict[str, Any]:
            return await app_ctx.vpic_client.get_models_for_make_id(validated.make_id)  # type: ignore[arg-type]

        raw, cache_hit = await app_ctx.caches["vpic_query"].get_or_fetch(cache_key, fetch)

    app_ctx.rate_limiter.record(ip_hash)

    results_list = raw.get("Results", [])
    results = [
        ModelResult(
            make_id=r.get("Make_ID"),
            make_name=r.get("Make_Name", ""),
            model_id=r.get("Model_ID"),
            model_name=r.get("Model_Name", ""),
        )
        for r in results_list
    ]

    return ToolResponse[ModelResult](
        summary={"count": len(results), "cache_hit": cache_hit},
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()
