from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str | None
    openrouter_base_url: str
    openrouter_app_name: str
    openrouter_site_url: str | None
    factual_model: str
    logical_model: str
    completeness_model: str
    cors_allow_origins: list[str]
    database_url: str
    api_access_key: str | None
    rate_limit_requests: int
    rate_limit_window_seconds: int


def get_settings() -> Settings:
    raw_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
    cors_allow_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return Settings(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        openrouter_base_url=os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ),
        openrouter_app_name=os.getenv(
            "OPENROUTER_APP_NAME", "llm-output-arbitration-system"
        ),
        openrouter_site_url=os.getenv("OPENROUTER_SITE_URL"),
        factual_model=os.getenv("OPENROUTER_MODEL_FACTUAL", "openai/gpt-4o-mini"),
        logical_model=os.getenv("OPENROUTER_MODEL_LOGICAL", "openai/gpt-4o-mini"),
        completeness_model=os.getenv(
            "OPENROUTER_MODEL_COMPLETENESS", "openai/gpt-4o-mini"
        ),
        cors_allow_origins=cors_allow_origins or ["*"],
        database_url=os.getenv("DATABASE_URL", "sqlite:///./arbitration.db"),
        api_access_key=os.getenv("API_ACCESS_KEY"),
        rate_limit_requests=max(0, int(os.getenv("RATE_LIMIT_REQUESTS", "0"))),
        rate_limit_window_seconds=max(
            1, int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
        ),
    )
