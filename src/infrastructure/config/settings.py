from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def parse_csv_or_json_list(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return value
    raw_value = value.strip()
    if not raw_value:
        return []
    if raw_value.startswith("["):
        parsed = json.loads(raw_value)
        if not isinstance(parsed, list):
            raise ValueError("Expected a JSON array for list-based settings")
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def resolve_secret(raw_value: str, file_path: str | None, field_name: str) -> str:
    if raw_value.strip():
        return raw_value.strip()
    if not file_path:
        return ""
    content = Path(file_path).read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"{field_name}_FILE is empty")
    return content


def uses_real_mercado_pago_api(api_base_url: str) -> bool:
    normalized_url = api_base_url.strip().lower().rstrip("/")
    return normalized_url == "https://api.mercadopago.com"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "service-order-billing-service"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "test", "staging", "production"] = "development"
    APP_RUNTIME_MODE: Literal["memory", "real"] = "memory"
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False
    APP_BASE_URL: str = "http://localhost:8002"
    CORS_ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["*"]
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    TRUSTED_HOSTS: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["*"])
    DATABASE_URL: str = (
        "postgresql+asyncpg://billing_service_user:billing_service_password@localhost:"
        "5432/billing_service_db"
    )
    EXPECTED_DATABASE_NAME: str = "billing_service_db"
    EXPECTED_DATABASE_USERNAME: str = "billing_service_user"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/%2F"
    RABBITMQ_EXCHANGE: str = "service-order.events"
    RABBITMQ_ROUTING_KEY: str = "service-order.billing"
    RABBITMQ_QUEUE: str = "service-order.billing.events"
    RABBITMQ_CONSUME_ROUTING_KEYS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["service-order.os"]
    )
    JWT_SECRET: str = "dev-jwt-secret-with-32-characters"
    JWT_SECRET_FILE: str | None = None
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = ""
    CUSTOMER_JWT_SECRET: str = ""
    CUSTOMER_JWT_SECRET_FILE: str | None = None
    CUSTOMER_JWT_ALGORITHM: str = "HS256"
    CUSTOMER_JWT_ISSUER: str = "service-order-auth-lambda/development"
    HEALTHCHECK_TIMEOUT_SECONDS: int = 5
    DD_SERVICE: str = "service-order-billing-service"
    DD_ENV: str = "development"
    DD_VERSION: str = "0.1.0"
    DD_API_KEY: str = ""
    DD_TRACE_ENABLED: bool = False
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "service-order-billing-service"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    PAYMENT_PROVIDER_MODE: Literal["mock", "mercado_pago"] | None = None
    MERCADO_PAGO_ACCESS_TOKEN: str = ""
    MERCADO_PAGO_ACCESS_TOKEN_FILE: str | None = None
    MERCADO_PAGO_API_BASE_URL: str = "https://api.mercadopago.com"
    MERCADO_PAGO_SUCCESS_URL: str = "http://localhost:8002/payments/success"
    MERCADO_PAGO_FAILURE_URL: str = "http://localhost:8002/payments/failure"
    MERCADO_PAGO_PENDING_URL: str = "http://localhost:8002/payments/pending"
    MERCADO_PAGO_REQUEST_TIMEOUT_SECONDS: int = 10
    ENABLE_INTERNAL_TEST_ENDPOINTS: bool = False
    DEFAULT_QUOTE_ITEMS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["Initial workshop diagnosis"]
    )
    DEFAULT_QUOTE_AMOUNT: Decimal = Decimal("120.00")

    @field_validator(
        "CORS_ALLOWED_ORIGINS",
        "TRUSTED_HOSTS",
        "RABBITMQ_CONSUME_ROUTING_KEYS",
        "DEFAULT_QUOTE_ITEMS",
        mode="before",
    )
    @classmethod
    def parse_list_settings(cls, value: str | list[str]) -> list[str]:
        return parse_csv_or_json_list(value)

    @field_validator("LOG_LEVEL")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    def model_post_init(self, __context: object) -> None:
        self.JWT_SECRET = resolve_secret(
            self.JWT_SECRET,
            self.JWT_SECRET_FILE,
            "JWT_SECRET",
        )
        self.CUSTOMER_JWT_SECRET = resolve_secret(
            self.CUSTOMER_JWT_SECRET,
            self.CUSTOMER_JWT_SECRET_FILE,
            "CUSTOMER_JWT_SECRET",
        )
        self.MERCADO_PAGO_ACCESS_TOKEN = resolve_secret(
            self.MERCADO_PAGO_ACCESS_TOKEN,
            self.MERCADO_PAGO_ACCESS_TOKEN_FILE,
            "MERCADO_PAGO_ACCESS_TOKEN",
        )
        if self.PAYMENT_PROVIDER_MODE is None:
            self.PAYMENT_PROVIDER_MODE = (
                "mercado_pago"
                if (
                    self.APP_RUNTIME_MODE == "real"
                    and uses_real_mercado_pago_api(self.MERCADO_PAGO_API_BASE_URL)
                    and self.MERCADO_PAGO_ACCESS_TOKEN not in {"", "local-demo-token"}
                )
                else "mock"
            )
        if (
            self.PAYMENT_PROVIDER_MODE == "mercado_pago"
            and uses_real_mercado_pago_api(self.MERCADO_PAGO_API_BASE_URL)
            and self.MERCADO_PAGO_ACCESS_TOKEN == "local-demo-token"
        ):
            raise ValueError(
                "MERCADO_PAGO_ACCESS_TOKEN must be set to a valid Mercado Pago "
                "sandbox or production token when MERCADO_PAGO_API_BASE_URL "
                "points to the real API."
            )
        if not self.JWT_ISSUER:
            self.JWT_ISSUER = f"service-order-os-service/{self.ENVIRONMENT}"
        self.DD_SERVICE = self.APP_NAME
        self.DD_ENV = self.ENVIRONMENT
        self.DD_VERSION = self.APP_VERSION
        self.OTEL_SERVICE_NAME = self.APP_NAME


def get_settings() -> Settings:
    env_file = os.environ.get("APP_ENV_FILE") or ".env"
    return Settings(_env_file=env_file)
