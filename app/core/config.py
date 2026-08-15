from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@db:5432/silentsepsis"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    secret_key: str = "replace_this_with_a_secure_secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    bootstrap_secret: str = "change-me-in-production"
    redis_url: str = "redis://redis:6379/0"
    risk_evaluation_interval_minutes: int = 5

    cors_allowed_origins: list[str] = ["http://localhost:5173"]
    login_rate_limit: str = "5/minute"
    bootstrap_rate_limit: str = "3/minute"
    default_rate_limit: str = "100/minute"
    environment: str = "development"

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
