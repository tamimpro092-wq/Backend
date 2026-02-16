from __future__ import annotations

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Core
    BRAND_NAME: str = os.getenv("BRAND_NAME", "MIRA")
    DRY_RUN: bool = os.getenv("DRY_RUN", "false").lower() == "true"

    # DB / Redis
    DB_PATH: str = os.getenv("DB_PATH", "/tmp/app.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # Local actions (disabled by default for safety)
    LOCAL_ACTIONS_ENABLED: bool = os.getenv("LOCAL_ACTIONS_ENABLED", "false").lower() == "true"

    # Shopify
    SHOPIFY_SHOP: str = os.getenv("SHOPIFY_SHOP", "")
    SHOPIFY_ACCESS_TOKEN: str = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
    SHOPIFY_API_VERSION: str = os.getenv("SHOPIFY_API_VERSION", "2024-10")

    # ✅ Missing in your project (caused crash)
    STORE_NICHE: str = os.getenv("STORE_NICHE", "general")
    DEFAULT_INVENTORY_QTY: int = int(os.getenv("DEFAULT_INVENTORY_QTY", "100"))

    # Google CSE (optional)
    GOOGLE_CSE_API_KEY: str = os.getenv("GOOGLE_CSE_API_KEY", "")
    GOOGLE_CSE_CX: str = os.getenv("GOOGLE_CSE_CX", "")

    # eBay (optional)
    EBAY_CLIENT_ID: str = os.getenv("EBAY_CLIENT_ID", "")
    EBAY_CLIENT_SECRET: str = os.getenv("EBAY_CLIENT_SECRET", "")
    EBAY_MARKETPLACE_ID: str = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US")

    # Pexels (optional)
    PEXELS_API_KEY: str = os.getenv("PEXELS_API_KEY", "")

    # Ollama (optional)
    OLLAMA_ENABLED: bool = os.getenv("OLLAMA_ENABLED", "false").lower() == "true"

    class Config:
        extra = "ignore"


settings = Settings()
