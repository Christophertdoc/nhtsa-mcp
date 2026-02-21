"""NHTSA MCP Server — FastMCP instance, lifespan, health endpoint, tool registration."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import httpx
import structlog
from mcp.server.fastmcp import Context, FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import Settings
from app.logging_config import configure_logging
from app.nhtsa_clients.api_nhtsa_client import APINHTSAClient
from app.nhtsa_clients.vpic_client import VPICClient
from app.security.cache import AsyncTTLCache
from app.security.rate_limiter import RateLimiter

configure_logging()
logger = structlog.get_logger()


@dataclass
class AppContext:
    vpic_client: VPICClient
    nhtsa_client: APINHTSAClient
    caches: dict[str, AsyncTTLCache]
    rate_limiter: RateLimiter
    settings: Settings


def get_app_context(ctx: Context) -> AppContext:
    """Extract AppContext from the MCP Context's lifespan state."""
    return ctx.request_context.lifespan_context  # type: ignore[return-value]


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    settings = Settings()

    timeout = httpx.Timeout(
        connect=settings.http_connect_timeout,
        read=settings.http_read_timeout,
        write=settings.http_read_timeout,
        pool=settings.http_total_timeout,
    )
    semaphore = asyncio.Semaphore(settings.max_concurrent_upstream_requests)

    vpic_http = httpx.AsyncClient(base_url=settings.vpic_base_url, timeout=timeout)
    nhtsa_http = httpx.AsyncClient(base_url=settings.api_nhtsa_base_url, timeout=timeout)

    vpic_client = VPICClient(vpic_http, semaphore, settings)
    nhtsa_client = APINHTSAClient(nhtsa_http, semaphore, settings)

    caches: dict[str, AsyncTTLCache] = {
        "vin": AsyncTTLCache(maxsize=500, ttl=86400),
        "ratings": AsyncTTLCache(maxsize=200, ttl=3600),
        "recalls": AsyncTTLCache(maxsize=200, ttl=1800),
        "complaints": AsyncTTLCache(maxsize=200, ttl=900),
        "cssi": AsyncTTLCache(maxsize=100, ttl=3600),
        "vpic_ref": AsyncTTLCache(maxsize=500, ttl=86400),
        "vpic_query": AsyncTTLCache(maxsize=300, ttl=3600),
    }

    rate_limiter = RateLimiter(
        global_per_minute=settings.rate_limit_global_per_minute,
        vin_per_minute=settings.rate_limit_vin_per_minute,
        daily_quota=settings.rate_limit_daily_quota,
        enabled=settings.rate_limit_enabled,
    )
    await rate_limiter.start_pruning()

    app_ctx = AppContext(
        vpic_client=vpic_client,
        nhtsa_client=nhtsa_client,
        caches=caches,
        rate_limiter=rate_limiter,
        settings=settings,
    )

    logger.info("NHTSA MCP server starting", transport="lifespan")

    try:
        yield app_ctx
    finally:
        await rate_limiter.stop_pruning()
        await vpic_http.aclose()
        await nhtsa_http.aclose()
        logger.info("NHTSA MCP server shut down")


# --- FastMCP instance ---

mcp = FastMCP("NHTSA MCP", lifespan=app_lifespan)

# Import tool modules — their @mcp.tool() registrations happen at import time
from app.mcp_tools.carseat import (  # noqa: E402
    carseat_stations_by_geo_tool,
    carseat_stations_by_state_tool,
    carseat_stations_by_zip_tool,
)
from app.mcp_tools.complaints import (  # noqa: E402
    complaints_by_odi_number_tool,
    complaints_by_vehicle_tool,
)
from app.mcp_tools.decode_vin import decode_vin_tool  # noqa: E402
from app.mcp_tools.ratings import (  # noqa: E402
    ratings_by_vehicle_id_tool,
    ratings_search_tool,
)
from app.mcp_tools.recalls import (  # noqa: E402
    recalls_by_campaign_number_tool,
    recalls_by_vehicle_tool,
)
from app.mcp_tools.vpic_batch import decode_vin_batch_tool  # noqa: E402
from app.mcp_tools.vpic_makes import get_all_makes_tool, get_makes_tool  # noqa: E402
from app.mcp_tools.vpic_manufacturers import get_manufacturers_tool  # noqa: E402
from app.mcp_tools.vpic_models import get_models_tool  # noqa: E402
from app.mcp_tools.vpic_parts import (  # noqa: E402
    get_equipment_plant_codes_tool,
    get_parts_tool,
)
from app.mcp_tools.vpic_variables import get_vehicle_variables_tool  # noqa: E402
from app.mcp_tools.vpic_vehicle_types import get_vehicle_types_tool  # noqa: E402
from app.mcp_tools.vpic_wmi import decode_wmi_tool  # noqa: E402

# Register tools with FastMCP
mcp.tool()(decode_vin_tool)
mcp.tool()(ratings_search_tool)
mcp.tool()(ratings_by_vehicle_id_tool)
mcp.tool()(recalls_by_vehicle_tool)
mcp.tool()(recalls_by_campaign_number_tool)
mcp.tool()(complaints_by_vehicle_tool)
mcp.tool()(complaints_by_odi_number_tool)
mcp.tool()(carseat_stations_by_zip_tool)
mcp.tool()(carseat_stations_by_state_tool)
mcp.tool()(carseat_stations_by_geo_tool)
mcp.tool()(decode_wmi_tool)
mcp.tool()(decode_vin_batch_tool)
mcp.tool()(get_all_makes_tool)
mcp.tool()(get_makes_tool)
mcp.tool()(get_manufacturers_tool)
mcp.tool()(get_models_tool)
mcp.tool()(get_vehicle_types_tool)
mcp.tool()(get_vehicle_variables_tool)
mcp.tool()(get_parts_tool)
mcp.tool()(get_equipment_plant_codes_tool)


# --- Health endpoint via custom_route (no FastAPI wrapper needed) ---


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> Response:
    return JSONResponse({"status": "ok"})


# --- ASGI app (Starlette, served by uvicorn) ---

app = mcp.streamable_http_app()


def run() -> None:
    """Entry point for stdio transport (nhtsa-mcp CLI)."""
    mcp.run(transport="stdio")
