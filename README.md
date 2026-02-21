# NHTSA MCP Server

An MCP (Model Context Protocol) server providing structured access to NHTSA (National Highway Traffic Safety Administration) vehicle safety APIs.

## Features

- 10 MCP tools covering 5 NHTSA API surfaces
- Strict Pydantic v2 input validation
- In-memory TTL caching per domain
- Per-IP sliding window rate limiting
- HTTP/SSE and stdio MCP transports
- Typer CLI test harness
- LLM tool-calling agent (Anthropic/OpenAI)

## MCP Tools

| Tool | Description |
|---|---|
| `decode_vin_tool` | Decode a 17-character VIN via vPIC |
| `ratings_search_tool` | Search NCAP safety ratings by year/make/model |
| `ratings_by_vehicle_id_tool` | Get detailed ratings by NHTSA vehicle ID |
| `recalls_by_vehicle_tool` | Search recalls by year/make/model |
| `recalls_by_campaign_number_tool` | Look up a recall by campaign number |
| `complaints_by_vehicle_tool` | Search complaints by year/make/model |
| `complaints_by_odi_number_tool` | Look up a complaint by ODI number |
| `carseat_stations_by_zip_tool` | Find car seat inspection stations by ZIP |
| `carseat_stations_by_state_tool` | Find stations by state code |
| `carseat_stations_by_geo_tool` | Find stations by lat/long/radius |

## Quick Start

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --extra dev
cp .env.example .env  # edit to add API keys if using LLM agent

# Start the server
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Health check
curl http://127.0.0.1:8000/health

# MCP stdio transport (for Claude Desktop)
uv run nhtsa-mcp --transport stdio
```

## CLI Usage

```bash
# Server commands
uv run nhtsa-cli server health
uv run nhtsa-cli server list-tools
uv run nhtsa-cli server start --port 8000 --reload

# Tool commands (requires running server)
uv run nhtsa-cli tool decode-vin 1FA6P8AM0G5227539
uv run nhtsa-cli tool ratings-search 2020 Toyota Camry
uv run nhtsa-cli tool recalls 2020 Toyota Camry
uv run nhtsa-cli tool complaints 2020 Toyota Camry
uv run nhtsa-cli tool carseat --zip 20001

# LLM agent (requires api key in .env)
uv run nhtsa-cli agent ask "What are the safety ratings for a 2020 Toyota Camry?"
uv run nhtsa-cli agent demo
```

## Development

```bash
# Run unit tests
uv run pytest tests/unit/ tests/cli/ -v

# Run with coverage
uv run pytest tests/unit/ tests/cli/ --cov=app --cov=cli --cov-report=term-missing

# Integration tests (live NHTSA network)
uv run pytest tests/integration/ -m integration -v

# Lint and format
uv run ruff check app/ cli/ tests/
uv run ruff format app/ cli/ tests/

# Type check
uv run mypy app/ cli/
```

## Architecture

- `app/main.py` — FastMCP instance, FastAPI health endpoint, lifespan management
- `app/config.py` — pydantic-settings configuration
- `app/models/` — Pydantic v2 input validators and output types
- `app/nhtsa_clients/` — Typed HTTP clients with retry, semaphore, path allowlist
- `app/mcp_tools/` — 10 MCP tool implementations
- `app/security/` — Rate limiter, output sanitizer, async TTL cache
- `cli/` — Typer CLI, MCP client wrapper, LLM agent
