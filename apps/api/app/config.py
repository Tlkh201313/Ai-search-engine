"""Application settings, loaded from environment / .env with safe defaults.

The LLM is a SINGLE server-hosted model reached through one Anthropic-Messages-
compatible base URL. End users never supply keys; the operator configures
`LLM_BASE_URL` + `LLM_API_KEY` once. With no key set, the app still runs and
returns deterministic extractive answers.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # --- Server ---
    app_name: str = "AI Research Engine"
    version: str = "1.0.0"
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    rate_limit_per_minute: int = 30

    # --- Cache ---
    cache_backend: str = "sqlite"  # sqlite | memory
    cache_db_path: str = "./data/cache.db"
    cache_ttl_search: int = 3600
    cache_ttl_fetch: int = 86400
    cache_ttl_research: int = 1800

    # --- Search ---
    search_providers: Annotated[list[str], NoDecode] = Field(
        default=["duckduckgo", "wikipedia"]
    )
    searxng_url: str = ""

    # --- Fetch ---
    fetch_timeout: float = 12.0
    fetch_max_chars: int = 12000
    fetch_concurrency: int = 6
    allow_private_ips: bool = False

    # --- LLM (single server-hosted, Anthropic Messages API compatible) ---
    llm_base_url: str = "https://api.anthropic.com"
    llm_api_key: str = ""  # operator sets this; empty/"dummy" => extractive fallback
    llm_model: str = "claude-sonnet-5"
    llm_max_tokens: int = 2048
    llm_timeout: float = 60.0
    llm_anthropic_version: str = "2023-06-01"

    @field_validator("cors_origins", "search_providers", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Accept comma-separated strings from env for list fields."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def llm_configured(self) -> bool:
        key = self.llm_api_key.strip().lower()
        return bool(self.llm_base_url.strip()) and key not in {"", "dummy", "changeme"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
