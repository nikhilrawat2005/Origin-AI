"""
Centralized application configuration.

All environment variables are read exactly once here and exposed via
`get_settings()`. No other module should call os.environ directly —
this keeps env access auditable and makes Railway deployment predictable.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Core ---
    app_env: str = "development"
    port: int = 8000

    # --- Database ---
    database_url: str = "sqlite:///./aether.db"

    # --- LLM Provider(s) ---
    gemini_api_key: str = ""
    llm_provider: str = "gemini"  # provider abstraction switch (Stage 6/7)

    # --- Memory (Breeth) ---
    breeth_api_key: str = ""

    # --- Scheduler (wired in Stage 18) ---
    publish_interval_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — env is read once per process."""
    return Settings()
