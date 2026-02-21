"""MCP tools: carseat_stations_by_zip, by_state, by_geo — CSSI stations."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context

from app.models.inputs import CarseatByGeoInput, CarseatByStateInput, CarseatByZipInput
from app.models.outputs import CarseatStationResult, ToolResponse


def _parse_station(r: dict[str, Any]) -> CarseatStationResult:
    return CarseatStationResult(
        name=r.get("Name", r.get("Organization", "")),
        address=r.get("StreetAddress", r.get("Address", "")),
        city=r.get("City", ""),
        state=r.get("State", ""),
        zip_code=r.get("Zip", r.get("ZipCode", "")),
        phone=r.get("Phone", r.get("PhoneNumber", "")),
        latitude=r.get("Latitude"),
        longitude=r.get("Longitude"),
        distance_miles=r.get("Distance"),
        url=r.get("URL", r.get("Url", "")),
    )


async def carseat_stations_by_zip_tool(
    ctx: Context,
    zip: str,
    lang: str | None = None,
    cpsweek: bool | None = None,
) -> dict[str, Any]:
    """Find child car seat inspection stations near a ZIP code.

    Args:
        zip: 5-digit US ZIP code (ZIP+4 also accepted, will be truncated)
        lang: Language for results — "en"/"english" or "es"/"spanish"
        cpsweek: If True, only show stations participating in CPS Week
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)
    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = CarseatByZipInput(zip=zip, lang=lang, cpsweek=cpsweek)
    cache_key = f"cssi_zip:{validated.zip}:{validated.lang}:{validated.cpsweek}"

    async def fetch() -> dict[str, Any]:
        return await app_ctx.nhtsa_client.carseat_stations_by_zip(
            validated.zip, validated.lang, validated.cpsweek
        )

    raw, cache_hit = await app_ctx.caches["cssi"].get_or_fetch(cache_key, fetch)
    app_ctx.rate_limiter.record(ip_hash)

    results = [_parse_station(r) for r in raw.get("Results", [])]
    return ToolResponse[CarseatStationResult](
        summary={"zip": validated.zip, "count": len(results), "cache_hit": cache_hit},
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()


async def carseat_stations_by_state_tool(
    ctx: Context,
    state: str,
    lang: str | None = None,
    cpsweek: bool | None = None,
) -> dict[str, Any]:
    """Find child car seat inspection stations in a US state or territory.

    Args:
        state: Two-letter US state/territory code (e.g. "CA", "TX", "DC")
        lang: Language for results — "en"/"english" or "es"/"spanish"
        cpsweek: If True, only show stations participating in CPS Week
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)
    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = CarseatByStateInput(state=state, lang=lang, cpsweek=cpsweek)
    cache_key = f"cssi_state:{validated.state}:{validated.lang}:{validated.cpsweek}"

    async def fetch() -> dict[str, Any]:
        return await app_ctx.nhtsa_client.carseat_stations_by_state(
            validated.state, validated.lang, validated.cpsweek
        )

    raw, cache_hit = await app_ctx.caches["cssi"].get_or_fetch(cache_key, fetch)
    app_ctx.rate_limiter.record(ip_hash)

    results = [_parse_station(r) for r in raw.get("Results", [])]
    return ToolResponse[CarseatStationResult](
        summary={"state": validated.state, "count": len(results), "cache_hit": cache_hit},
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()


async def carseat_stations_by_geo_tool(
    ctx: Context,
    lat: float,
    long: float,
    miles: int = 25,
    lang: str | None = None,
    cpsweek: bool | None = None,
) -> dict[str, Any]:
    """Find child car seat inspection stations near a geographic coordinate.

    Args:
        lat: Latitude (-90.0 to 90.0)
        long: Longitude (-180.0 to 180.0)
        miles: Search radius in miles (1-200, default 25)
        lang: Language for results — "en"/"english" or "es"/"spanish"
        cpsweek: If True, only show stations participating in CPS Week
    """
    from app.main import get_app_context

    app_ctx = get_app_context(ctx)
    ip_hash = app_ctx.rate_limiter.hash_ip("stdio")
    app_ctx.rate_limiter.check(ip_hash)

    validated = CarseatByGeoInput(lat=lat, long=long, miles=miles, lang=lang, cpsweek=cpsweek)
    cache_key = (
        f"cssi_geo:{validated.lat}:{validated.long}:"
        f"{validated.miles}:{validated.lang}:{validated.cpsweek}"
    )

    async def fetch() -> dict[str, Any]:
        return await app_ctx.nhtsa_client.carseat_stations_by_geo(
            validated.lat, validated.long, validated.miles, validated.lang, validated.cpsweek
        )

    raw, cache_hit = await app_ctx.caches["cssi"].get_or_fetch(cache_key, fetch)
    app_ctx.rate_limiter.record(ip_hash)

    results = [_parse_station(r) for r in raw.get("Results", [])]
    return ToolResponse[CarseatStationResult](
        summary={
            "lat": validated.lat,
            "long": validated.long,
            "miles": validated.miles,
            "count": len(results),
            "cache_hit": cache_hit,
        },
        results=results,
        raw_response=raw if app_ctx.settings.include_raw_response else None,
    ).model_dump()
