from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/payments"


class Settings(DatabaseSettings):
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    api_key: SecretStr = Field(default=SecretStr(""), min_length=1)
    api_host: str = Field(default="0.0.0.0", min_length=1)
    api_port: int = Field(default=8000, ge=1, le=65535)
    webhook_timeout: float = Field(default=10.0, gt=0)
    max_retries: int = Field(default=3, ge=0)
    retry_base_delay: float = Field(default=2.0, gt=0)
    outbox_batch_size: int = Field(default=100, gt=0)
    outbox_poll_interval: float = Field(default=1.0, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
