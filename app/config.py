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


def get_settings() -> Settings:
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
    )
