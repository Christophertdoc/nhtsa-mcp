"""MCP tool: decode_wmi — WMI decoding via vPIC."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from app.models.inputs import DecodeWMIInput
from app.models.outputs import ToolResponse, WMIResult


async def decode_wmi_tool(
    ctx: Context,
    wmi: str,
) -> dict[str, Any]:
    """Decode a World Manufacturer Identifier (WMI) — the first 3 or 6 characters of a VIN.

    Returns manufacturer name, make, vehicle type, and country info.

    Args:
        wmi: 3 or 6 character World Manufacturer Identifier
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)

    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = DecodeWMIInput(wmi=wmi)

    cache_key = f"wmi:{validated.wmi}"

    async def fetch() -> dict[str, Any]:
        return await app_ctx.vpic_client.decode_wmi(validated.wmi)

    raw, cache_hit = await app_ctx.caches["vpic_ref"].get_or_fetch(cache_key, fetch)

    app_ctx.rate_limiter.record(ip_hash)

    results_list = raw.get("Results", [])
    results = [
        WMIResult(
            common_name=r.get("CommonName", ""),
            make_name=r.get("MakeName", ""),
            manufacturer_name=r.get("ManufacturerName", ""),
            vehicle_type=r.get("VehicleType", ""),
            wmi=r.get("WMI", ""),
        )
        for r in results_list
    ]

    return ToolResponse[WMIResult](
        summary={"wmi": validated.wmi, "count": len(results), "cache_hit": cache_hit},
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()
