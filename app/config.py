"""Application configuration via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # HTTP timeouts (seconds)
    http_connect_timeout: float = 5.0
    http_read_timeout: float = 15.0
    http_total_timeout: float = 20.0

    # Retry
    retry_max_attempts: int = 3
    retry_wait_min_seconds: float = 1.0
    retry_wait_max_seconds: float = 10.0

    # Concurrency
    max_concurrent_upstream_requests: int = 20

    # Rate limits
    rate_limit_global_per_minute: int = 60
    rate_limit_vin_per_minute: int = 10
    rate_limit_daily_quota: int = 1000
    rate_limit_enabled: bool = True

    # Output
    include_raw_response: bool = False

    # Bulk VIN
    bulk_vin_enabled: bool = False
    bulk_vin_max: int = 5

    # LLM (for CLI agent)
    llm_provider: str = "openai"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_model_anthropic: str = "claude-opus-4-6"
    llm_model_openai: str = "gpt-4o"
    llm_max_tool_iterations: int = 10

    # Upstream base URLs
    vpic_base_url: str = "https://vpic.nhtsa.dot.gov/api"
    api_nhtsa_base_url: str = "https://api.nhtsa.gov"
