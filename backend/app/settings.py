from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Load from .env (optional) + still allow docker env vars
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # General
    BRAND_NAME: str = "Acme"
    DRY_RUN: int = 1
    LOG_LEVEL: str = "INFO"

    DATABASE_PATH: str = "/data/app.db"
    WORKSPACE_DIR: str = "/workspace"

    # Background / queue
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Schedules
    NIGHTLY_HOUR: int = 2
    NIGHTLY_MINUTE: int = 10
    REPORT_HOUR: int = 9
    REPORT_MINUTE: int = 0

    # Local actions
    LOCAL_ACTIONS_ENABLED: int = 0

    # Ollama (optional)
    OLLAMA_ENABLED: int = 0
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.1"

    # LLM (optional)
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Shopify
    SHOPIFY_SHOP: str = ""
    SHOPIFY_ACCESS_TOKEN: str = ""
    SHOPIFY_API_VERSION: str = "2026-01"

    # Research / Web signals (optional)
    GOOGLE_CSE_API_KEY: str = ""
    GOOGLE_CSE_CX: str = ""

    EBAY_CLIENT_ID: str = ""
    EBAY_CLIENT_SECRET: str = ""

    PEXELS_API_KEY: str = ""
    UNSPLASH_ACCESS_KEY: str = ""

    # Facebook
    FACEBOOK_GRAPH_VERSION: str = "v19.0"
    FACEBOOK_PAGE_ID: str = ""
    FACEBOOK_ACCESS_TOKEN: str = ""
    FACEBOOK_VERIFY_TOKEN: str = "dev-verify-token"

    # WhatsApp
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "dev-verify-token"


settings = Settings()
