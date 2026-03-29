"""Application settings loaded from environment variables and optional ``.env``."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration: database URL, CORS, optional static SPA directory."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Default matches docker-compose.yml (host port 5433, user pricing).
    database_url: str = "postgresql+psycopg://pricing:pricing@localhost:5433/pricing_simulator"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    static_dir: str | None = Field(
        default=None,
        description="Built frontend directory for production (e.g. frontend/dist)",
    )


def get_settings() -> Settings:
    """Return a ``Settings`` instance from the current environment."""
    return Settings()
