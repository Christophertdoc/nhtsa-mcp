# NHTSA MCP Server — Task List

See [PLAN.md](./PLAN.md) for full implementation details, architecture decisions, and acceptance criteria.

Tasks are ordered by dependency. Complete them roughly in sequence; tasks within the same milestone can be parallelized.

---

## Milestone 1 — MVP: Core Tools

| # | Task | Status |
|---|---|---|
| 1 | Set up pyproject.toml and uv project | done |
| 2 | Implement `app/config.py` | done |
| 3 | Implement `app/models/inputs.py` and `outputs.py` | done |
| 4 | Implement `app/nhtsa_clients/` (base, vpic, api) | done |
| 5 | Implement all 10 MCP tools in `app/mcp_tools/` | done |
| 6 | Implement `app/main.py` (FastMCP + FastAPI lifespan) | done |

**Acceptance criteria:** `decode_vin("1FA6P8AM0G5227539")` returns correct make/model/year; all 10 tools respond; invalid VINs return 400; `pytest tests/unit/ -v` passes.

---

## Milestone 2 — Security Hardening

| # | Task | Status |
|---|---|---|
| 7 | Implement `app/security/` (rate_limiter, sanitizer, cache) | done |
| 8 | Implement structured logging and error handler middleware | done |
| 9 | Write unit tests (`tests/unit/`) | done |

**Acceptance criteria:** 11th VIN call → 429 with `Retry-After`; upstream 5xx → 502 (no stack trace); cache hit on second identical call (upstream called once).

---

## Milestone 3 — CLI + LLM Agent

| # | Task | Status |
|---|---|---|
| 10 | Implement CLI (`cli/main.py`, `mcp_client.py`, `llm_agent.py`) | done |
| 11 | Write CLI tests (`tests/cli/`) | done |

**Acceptance criteria:** All `nhtsa-cli tool` subcommands work against running server; `agent ask` produces coherent answer using tool data; circuit breaker fires at max_iterations; unknown tool names blocked.

---

## Milestone 4 — Production Polish

| # | Task | Status |
|---|---|---|
| 12 | Write integration tests (`tests/integration/`) | done |
| 13 | Production polish: mypy, ruff, coverage ≥85%, README, CLAUDE.md | done |

**Acceptance criteria:** mypy strict passing; ruff clean; coverage ≥ 85%; README and CLAUDE.md fully updated.

---

## Task Details

### Task 1 — Set up pyproject.toml and uv project
Create `pyproject.toml` with all runtime dependencies (`fastapi`, `mcp[cli]`, `httpx`, `pydantic`, `pydantic-settings`, `tenacity`, `cachetools`, `structlog`, `typer`, `anthropic`, `openai`, `uvicorn`) and dev extras (`pytest`, `pytest-asyncio`, `respx`, `pytest-cov`, `ruff`, `mypy`). Add `[project.scripts]` for `nhtsa-mcp` and `nhtsa-cli`. Create `.gitignore` and `.env.example`. Run `uv sync --extra dev`.

### Task 2 — Implement `app/config.py`
pydantic-settings `Settings` class as the single source of all env vars: HTTP timeouts, retry config, concurrency limits, rate limit thresholds, output flags, bulk VIN toggle, LLM provider config. All fields have safe defaults.

### Task 3 — Implement `app/models/inputs.py` and `outputs.py`
`inputs.py`: All Pydantic v2 validators with `ConfigDict(str_strip_whitespace=True, frozen=True)`. VIN (17 chars, no I/O/Q), `model_year` (1980–current+1), `make`/`model` (max 64, title-case), `vehicle_id`, `campaign_number` regex, `odi_number`, `zip` (ZIP+4→5), `state` allowlist (56 codes), `lat`/`long` bounds, `miles` (1–200), `lang` canonicalization. `outputs.py`: Generic `ToolResponse[T]` with `summary`/`results`/`raw_response` fields plus per-tool result types.

### Task 4 — Implement `app/nhtsa_clients/` (base, vpic, api)
`base_client.py`: path allowlist check, semaphore-gated `_get()` with tenacity retry (3 attempts, exponential backoff 1–10s), typed exceptions. `vpic_client.py`: `ALLOWED_PATH_PREFIXES` for `DecodeVinValues`/`Extended`, `decode_vin()` method. `api_nhtsa_client.py`: prefixes for SafetyRatings, recalls, complaints, CSSIStation; all domain fetch methods.

### Task 5 — Implement all 10 MCP tools in `app/mcp_tools/`
`decode_vin.py`, `ratings.py`, `recalls.py`, `complaints.py`, `carseat.py` — each with `@mcp.tool()`. All return `ToolResponse` with `summary`/`results`/`raw_response`. Rate limiter called before validation in each tool.

### Task 6 — Implement `app/main.py`
`AppContext` dataclass, `app_lifespan` context manager (creates shared `httpx.AsyncClient` instances and per-domain `AsyncTTLCache`). `FastMCP` instance with lifespan. `FastAPI` app mounting `mcp.sse_app()` at `/mcp`. `GET /health` endpoint. `run()` entrypoint for stdio transport.

### Task 7 — Implement `app/security/` (rate_limiter, sanitizer, cache)
`rate_limiter.py`: per-IP sliding window deques keyed by `sha256(ip)`, global (60/min), VIN (10/min), daily (1000) limits, background pruning task every 5 min. `sanitizer.py`: strip `REDACTED_FIELDS`, truncate strings >50k chars, `sanitize_error()` maps exceptions to safe messages. `cache.py`: `AsyncTTLCache` wrapping `cachetools.TTLCache` with `asyncio.Lock`, `get_or_fetch(key, fetch_fn)` pattern.

### Task 8 — Implement structured logging and error handler middleware
structlog configuration. Every request emits JSON with: `request_id`, `tool`, `upstream_latency_ms`, `upstream_status_code`, `cache_hit`, `rate_limited`, `client_ip_hash`. FastAPI exception handler maps typed exceptions to HTTP status codes and safe error codes. Never log API keys, raw IPs, full bodies, or stack traces.

### Task 9 — Write unit tests (`tests/unit/`)
`test_inputs.py`: VIN/year/state/zip/lang/miles boundary tests. `test_rate_limiter.py`: 60 pass/61st fail, VIN 10/11, daily quota, time-window expiry via mock clock. `test_cache.py`: miss/hit/TTL/LRU/concurrent race. `test_tools/`: respx mocking for success, 5xx→502, timeout→504, cache hit (upstream called once).

### Task 10 — Implement CLI (`cli/main.py`, `mcp_client.py`, `llm_agent.py`)
`cli/main.py`: Typer `server`/`tool`/`agent` command groups; all tool subcommands output pretty-printed JSON. `cli/mcp_client.py`: sync httpx with `call_tool()` and `list_tools()`. `cli/llm_agent.py`: abstract `LLMProvider`, `AnthropicProvider`, `OpenAIProvider`, `run_agent()` with tool allowlist, schema validation, max_iterations circuit breaker, 30s timeout.

### Task 11 — Write CLI tests (`tests/cli/`)
`test_cli_smoke.py`: `typer.testing.CliRunner`; all subcommands register; invalid VIN → non-zero exit. `test_llm_stub.py`: `StubLLMProvider` returns predictable sequence; circuit breaker fires at `max_iterations`; unknown tool names blocked.

### Task 12 — Write integration tests (`tests/integration/`)
Live calls to real NHTSA endpoints. All tests gated by `@pytest.mark.integration`, skipped by default. Cover each of the five NHTSA API surfaces.

### Task 13 — Production polish
Run `mypy app/ cli/` strict and fix all type errors. Run `ruff check` + `ruff format` and fix all issues. Achieve ≥85% test coverage. Update `README.md` with tool reference table and quickstart. Update `CLAUDE.md` with all dev commands.
