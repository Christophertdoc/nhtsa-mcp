# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server for the NHTSA (National Highway Traffic Safety Administration) API. It provides 10 MCP tools covering VIN decoding, safety ratings, recalls, complaints, and car seat inspection stations.

## IDE Configuration

The `.vscode/settings.json` is configured with `claudeCode.useTerminal: true`, meaning Claude Code uses the integrated terminal rather than the editor for commands.

## Build & Run

```bash
# Install dependencies
uv sync --extra dev

# Start dev server (auto-reload)
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# MCP stdio transport
uv run nhtsa-mcp --transport stdio
```

## Testing

```bash
# Unit + CLI tests (default, skips integration)
uv run pytest tests/unit/ tests/cli/ -v

# With coverage
uv run pytest tests/unit/ tests/cli/ --cov=app --cov=cli --cov-report=term-missing

# Integration tests only (requires network)
uv run pytest tests/integration/ -m integration -v
```

## Linting & Type Checking

```bash
uv run ruff check app/ cli/ tests/
uv run ruff format app/ cli/ tests/
uv run mypy app/ cli/
```

## Architecture

- `app/main.py` — FastMCP + FastAPI, lifespan, tool registration
- `app/config.py` — pydantic-settings (all env vars with defaults)
- `app/models/inputs.py` — Pydantic v2 validators (security boundary)
- `app/models/outputs.py` — ToolResponse[T] and result types
- `app/nhtsa_clients/` — HTTP clients with retry, semaphore, path allowlist
- `app/mcp_tools/` — 10 @mcp.tool() implementations
- `app/security/` — rate_limiter, sanitizer, cache
- `cli/` — Typer CLI, MCP client, LLM agent

## Key Design Decisions

- Two httpx.AsyncClient instances (vpic + api.nhtsa), shared via lifespan
- All upstream paths validated against ALLOWED_PATH_PREFIXES (SSRF prevention)
- Rate limiter checked before Pydantic validation (prevents validation-based DoS)
- Cache keys derived from normalized inputs (case-insensitive dedup)
- Errors sanitized — no stack traces, internal URLs, or API keys in responses
