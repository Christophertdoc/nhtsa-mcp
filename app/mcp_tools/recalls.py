"""MCP tools: recalls_by_vehicle, recalls_by_campaign_number."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from app.models.inputs import RecallsByCampaignInput, RecallsByVehicleInput
from app.models.outputs import RecallResult, ToolResponse


def _parse_recall(r: dict[str, Any]) -> RecallResult:
    return RecallResult(
        nhtsa_campaign_number=r.get("NHTSACampaignNumber", ""),
        report_received_date=r.get("ReportReceivedDate", ""),
        component=r.get("Component", ""),
        summary=r.get("Summary", ""),
        consequence=r.get("Consequence", ""),
        remedy=r.get("Remedy", ""),
        manufacturer=r.get("Manufacturer", ""),
        park_it=r.get("ParkIt"),
        park_outside=r.get("ParkOutside"),
    )


async def recalls_by_vehicle_tool(
    ctx: Context,
    model_year: int,
    make: str,
    model: str,
) -> dict[str, Any]:
    """Search NHTSA recall notices by vehicle year, make, and model.

    Returns all recalls including campaign numbers, affected components,
    safety consequences, and recommended remedies.

    Args:
        model_year: Vehicle model year (1980-current+1)
        make: Vehicle manufacturer (e.g. "Ford")
        model: Vehicle model name (e.g. "F-150")
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)
    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = RecallsByVehicleInput(model_year=model_year, make=make, model=model)
    cache_key = f"recalls:{validated.model_year}:{validated.make}:{validated.model}"

    async def fetch() -> dict[str, Any]:
        return await app_ctx.nhtsa_client.recalls_by_vehicle(
            validated.model_year, validated.make, validated.model
        )

    raw, cache_hit = await app_ctx.caches["recalls"].get_or_fetch(cache_key, fetch)
    app_ctx.rate_limiter.record(ip_hash)

    results = [_parse_recall(r) for r in raw.get("results", [])]
    return ToolResponse[RecallResult](
        summary={
            "query": f"{validated.model_year} {validated.make} {validated.model}",
            "count": len(results),
            "cache_hit": cache_hit,
        },
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()


async def recalls_by_campaign_number_tool(
    ctx: Context,
    campaign_number: str,
) -> dict[str, Any]:
    """Look up a specific NHTSA recall by campaign number.

    Args:
        campaign_number: NHTSA campaign number (e.g. "20V123000")
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)
    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = RecallsByCampaignInput(campaign_number=campaign_number)
    cache_key = f"recall_campaign:{validated.campaign_number}"

    async def fetch() -> dict[str, Any]:
        return await app_ctx.nhtsa_client.recalls_by_campaign_number(validated.campaign_number)

    raw, cache_hit = await app_ctx.caches["recalls"].get_or_fetch(cache_key, fetch)
    app_ctx.rate_limiter.record(ip_hash)

    results = [_parse_recall(r) for r in raw.get("results", [])]
    return ToolResponse[RecallResult](
        summary={
            "campaign_number": validated.campaign_number,
            "count": len(results),
            "cache_hit": cache_hit,
        },
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()
