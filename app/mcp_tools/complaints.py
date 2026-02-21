"""MCP tools: complaints_by_vehicle, complaints_by_odi_number."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from app.models.inputs import ComplaintsByOdiInput, ComplaintsByVehicleInput
from app.models.outputs import ComplaintResult, ToolResponse


def _parse_complaint(r: dict[str, Any]) -> ComplaintResult:
    return ComplaintResult(
        odi_number=str(r.get("odiNumber", "")),
        date_of_incident=r.get("dateOfIncident", ""),
        date_complaint_filed=r.get("dateComplaintFiled", ""),
        component=r.get("components", ""),
        summary=r.get("summary", ""),
        crash=r.get("crash"),
        fire=r.get("fire"),
        injuries=r.get("numberOfInjuries"),
        deaths=r.get("numberOfDeaths"),
    )


async def complaints_by_vehicle_tool(
    ctx: Context,
    model_year: int,
    make: str,
    model: str,
) -> dict[str, Any]:
    """Search NHTSA consumer complaints by vehicle year, make, and model.

    Returns complaint details including incident descriptions, injuries, and deaths.

    Args:
        model_year: Vehicle model year (1980-current+1)
        make: Vehicle manufacturer (e.g. "Honda")
        model: Vehicle model name (e.g. "Civic")
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)
    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = ComplaintsByVehicleInput(model_year=model_year, make=make, model=model)
    cache_key = f"complaints:{validated.model_year}:{validated.make}:{validated.model}"

    async def fetch() -> dict[str, Any]:
        return await app_ctx.nhtsa_client.complaints_by_vehicle(
            validated.model_year, validated.make, validated.model
        )

    raw, cache_hit = await app_ctx.caches["complaints"].get_or_fetch(cache_key, fetch)
    app_ctx.rate_limiter.record(ip_hash)

    results = [_parse_complaint(r) for r in raw.get("results", [])]
    return ToolResponse[ComplaintResult](
        summary={
            "query": f"{validated.model_year} {validated.make} {validated.model}",
            "count": len(results),
            "cache_hit": cache_hit,
        },
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()


async def complaints_by_odi_number_tool(
    ctx: Context,
    odi_number: str,
) -> dict[str, Any]:
    """Look up a specific NHTSA consumer complaint by ODI number.

    Args:
        odi_number: NHTSA ODI complaint number (5-12 digits)
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)
    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = ComplaintsByOdiInput(odi_number=odi_number)
    cache_key = f"complaint_odi:{validated.odi_number}"

    async def fetch() -> dict[str, Any]:
        return await app_ctx.nhtsa_client.complaints_by_odi_number(validated.odi_number)

    raw, cache_hit = await app_ctx.caches["complaints"].get_or_fetch(cache_key, fetch)
    app_ctx.rate_limiter.record(ip_hash)

    results = [_parse_complaint(r) for r in raw.get("results", [])]
    return ToolResponse[ComplaintResult](
        summary={
            "odi_number": validated.odi_number,
            "count": len(results),
            "cache_hit": cache_hit,
        },
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()
