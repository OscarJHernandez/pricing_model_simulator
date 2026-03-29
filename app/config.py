from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost:5432/pricing_simulator"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    static_dir: str | None = Field(
        default=None,
        description="Built frontend directory for production (e.g. frontend/dist)",
    )


def get_settings() -> Settings:
    return Settings()
