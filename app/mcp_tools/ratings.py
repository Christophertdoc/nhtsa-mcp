"""MCP tools: ratings_search, ratings_by_vehicle_id — NCAP Safety Ratings."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from app.models.inputs import RatingsByVehicleIdInput, RatingsSearchInput
from app.models.outputs import SafetyRatingResult, ToolResponse


def _parse_rating_result(r: dict[str, Any]) -> SafetyRatingResult:
    return SafetyRatingResult(
        vehicle_id=r.get("VehicleId"),
        vehicle_description=r.get("VehicleDescription", ""),
        overall_rating=r.get("OverallRating", ""),
        front_crash_rating=r.get("OverallFrontCrashRating", ""),
        side_crash_rating=r.get("OverallSideCrashRating", ""),
        rollover_rating=r.get("RolloverRating", r.get("RolloverRating2", "")),
        complaints_count=r.get("ComplaintsCount"),
        recalls_count=r.get("RecallsCount"),
        investigation_count=r.get("InvestigationCount"),
    )


async def ratings_search_tool(
    ctx: Context,
    model_year: int,
    make: str,
    model: str,
) -> dict[str, Any]:
    """Search NHTSA NCAP safety ratings by vehicle year, make, and model.

    Returns overall star ratings, front/side crash ratings, and rollover ratings.

    Args:
        model_year: Vehicle model year (1980-current+1)
        make: Vehicle manufacturer (e.g. "Toyota")
        model: Vehicle model name (e.g. "Camry")
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)
    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = RatingsSearchInput(model_year=model_year, make=make, model=model)
    cache_key = f"ratings:{validated.model_year}:{validated.make}:{validated.model}"

    async def fetch() -> dict[str, Any]:
        return await app_ctx.nhtsa_client.ratings_search(
            validated.model_year, validated.make, validated.model
        )

    raw, cache_hit = await app_ctx.caches["ratings"].get_or_fetch(cache_key, fetch)
    app_ctx.rate_limiter.record(ip_hash)

    results = [_parse_rating_result(r) for r in raw.get("Results", [])]
    return ToolResponse[SafetyRatingResult](
        summary={
            "query": f"{validated.model_year} {validated.make} {validated.model}",
            "count": len(results),
            "cache_hit": cache_hit,
        },
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()


async def ratings_by_vehicle_id_tool(
    ctx: Context,
    vehicle_id: int,
) -> dict[str, Any]:
    """Get detailed NHTSA NCAP safety ratings for a specific vehicle ID.

    Use ratings_search first to find vehicle IDs, then this tool for detailed ratings.

    Args:
        vehicle_id: NHTSA vehicle ID (positive integer)
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)
    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = RatingsByVehicleIdInput(vehicle_id=vehicle_id)
    cache_key = f"ratings_id:{validated.vehicle_id}"

    async def fetch() -> dict[str, Any]:
        return await app_ctx.nhtsa_client.ratings_by_vehicle_id(validated.vehicle_id)

    raw, cache_hit = await app_ctx.caches["ratings"].get_or_fetch(cache_key, fetch)
    app_ctx.rate_limiter.record(ip_hash)

    results = [_parse_rating_result(r) for r in raw.get("Results", [])]
    return ToolResponse[SafetyRatingResult](
        summary={
            "vehicle_id": validated.vehicle_id,
            "count": len(results),
            "cache_hit": cache_hit,
        },
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()
