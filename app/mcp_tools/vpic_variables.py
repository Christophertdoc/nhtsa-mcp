"""MCP tool: get_vehicle_variables — variable list and value lookups via vPIC."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from app.models.inputs import GetVehicleVariablesInput
from app.models.outputs import ToolResponse, VehicleVariableResult


async def get_vehicle_variables_tool(
    ctx: Context,
    variable: str | None = None,
) -> dict[str, Any]:
    """Get the list of VIN decode variables, or the allowed values for a specific variable.

    Without a variable name/ID, returns the full variable list with descriptions.
    With a variable, returns its allowed values.

    Args:
        variable: Variable name or numeric ID to get values for (omit for full list)
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)

    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = GetVehicleVariablesInput(variable=variable)

    if validated.variable:
        cache_key = f"var_values:{validated.variable}"

        async def fetch() -> dict[str, Any]:
            return await app_ctx.vpic_client.get_vehicle_variable_values_list(
                validated.variable  # type: ignore[arg-type]
            )

        raw, cache_hit = await app_ctx.caches["vpic_ref"].get_or_fetch(cache_key, fetch)
    else:
        cache_key = "var_list"

        async def fetch() -> dict[str, Any]:
            return await app_ctx.vpic_client.get_vehicle_variable_list()

        raw, cache_hit = await app_ctx.caches["vpic_ref"].get_or_fetch(cache_key, fetch)

    app_ctx.rate_limiter.record(ip_hash)

    results_list = raw.get("Results", [])

    if validated.variable:
        results = [
            VehicleVariableResult(
                variable_id=r.get("Id"),
                variable_name=r.get("Name", ""),
            )
            for r in results_list
        ]
    else:
        results = [
            VehicleVariableResult(
                variable_id=r.get("ID"),
                variable_name=r.get("Name", ""),
                group_name=r.get("GroupName", ""),
                description=r.get("Description", ""),
            )
            for r in results_list
        ]

    return ToolResponse[VehicleVariableResult](
        summary={"count": len(results), "cache_hit": cache_hit},
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()
