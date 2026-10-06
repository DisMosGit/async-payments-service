from functools import lru_cache
from typing import Self

from pydantic import Field, SecretStr, model_validator
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
    gateway_min_delay: float = Field(default=2.0, ge=0)
    gateway_max_delay: float = Field(default=5.0, ge=0)
    gateway_success_rate: float = Field(default=0.9, ge=0, le=1)
    outbox_batch_size: int = Field(default=100, gt=0)
    outbox_poll_interval: float = Field(default=1.0, gt=0)
    worker_heartbeat_file: str = Field(default="/tmp/async-payments-worker.heartbeat", min_length=1)
    worker_heartbeat_interval: float = Field(default=5.0, gt=0)

    @model_validator(mode="after")
    def validate_gateway_delay_window(self) -> Self:
        if self.gateway_min_delay > self.gateway_max_delay:
            raise ValueError("gateway_min_delay must not exceed gateway_max_delay")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
