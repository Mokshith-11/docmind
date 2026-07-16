"""Application settings, loaded from environment / .env (pydantic-settings)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Reads repo-root .env first, then backend/.env (latter wins). Extra vars ignored.
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_jwt_secret: str = ""

    # LLMs / retrieval
    gemini_api_key: str = ""
    groq_api_key: str = ""
    cohere_api_key: str = ""

    # Billing (Lemon Squeezy) — needed from Phase 5
    lemonsqueezy_api_key: str = ""
    lemonsqueezy_webhook_secret: str = ""
    lemonsqueezy_variant_id: str = ""

    # App
    frontend_url: str = "http://localhost:5173"


settings = Settings()
