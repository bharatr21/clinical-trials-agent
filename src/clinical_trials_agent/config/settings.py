"""Application settings using pydantic-settings."""

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database settings (AACT PostgreSQL)
    db_host: str = "aact-db.ctti-clinicaltrials.org"
    db_port: int = 5432
    db_name: str = "aact"
    db_user: str = ""
    db_password: str = ""

    # OpenAI settings
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # LangSmith settings
    langsmith_tracing: bool = True
    langsmith_api_key: str = ""
    langsmith_project: str = "clinical-trials-agent"

    # API settings
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = "https://clinical-trials-agent.vercel.app"

    # Application database (local PostgreSQL for state persistence)
    app_db_host: str = "localhost"
    app_db_port: int = 5432
    app_db_name: str = "clinical_trials_app"
    app_db_user: str = ""
    app_db_password: str = ""

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL with URL-encoded credentials."""
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        return f"postgresql://{user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # SSL mode for app database (set to "disable" for Railway internal networking)
    app_db_sslmode: str = "prefer"

    @property
    def app_database_url(self) -> str:
        """Construct PostgreSQL URL for application database (async with psycopg)."""
        user = quote_plus(self.app_db_user)
        password = quote_plus(self.app_db_password)
        return f"postgresql://{user}:{password}@{self.app_db_host}:{self.app_db_port}/{self.app_db_name}?sslmode={self.app_db_sslmode}"

    @property
    def app_database_url_async(self) -> str:
        """Construct PostgreSQL URL for application database (async with asyncpg)."""
        user = quote_plus(self.app_db_user)
        password = quote_plus(self.app_db_password)
        return f"postgresql+asyncpg://{user}:{password}@{self.app_db_host}:{self.app_db_port}/{self.app_db_name}?sslmode={self.app_db_sslmode}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
