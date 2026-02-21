"""MCP tool: get_vehicle_types — vehicle type lookups via vPIC."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from app.models.inputs import GetVehicleTypesInput
from app.models.outputs import ToolResponse, VehicleTypeResult


async def get_vehicle_types_tool(
    ctx: Context,
    make: str | None = None,
    make_id: int | None = None,
) -> dict[str, Any]:
    """Get vehicle types associated with a make name or make ID.

    Provide either make (name) or make_id (numeric), not both.

    Args:
        make: Make name (e.g. "Honda", "Ford")
        make_id: Numeric make ID from NHTSA
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)

    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = GetVehicleTypesInput(make=make, make_id=make_id)

    if validated.make:
        cache_key = f"vtypes:make:{validated.make}"

        async def fetch() -> dict[str, Any]:
            return await app_ctx.vpic_client.get_vehicle_types_for_make(validated.make)  # type: ignore[arg-type]

        raw, cache_hit = await app_ctx.caches["vpic_ref"].get_or_fetch(cache_key, fetch)
    else:
        cache_key = f"vtypes:id:{validated.make_id}"

        async def fetch() -> dict[str, Any]:
            return await app_ctx.vpic_client.get_vehicle_types_for_make_id(validated.make_id)  # type: ignore[arg-type]

        raw, cache_hit = await app_ctx.caches["vpic_ref"].get_or_fetch(cache_key, fetch)

    app_ctx.rate_limiter.record(ip_hash)

    results_list = raw.get("Results", [])
    results = [
        VehicleTypeResult(
            vehicle_type_id=r.get("VehicleTypeId"),
            vehicle_type_name=r.get("VehicleTypeName", ""),
        )
        for r in results_list
    ]

    return ToolResponse[VehicleTypeResult](
        summary={"count": len(results), "cache_hit": cache_hit},
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()
