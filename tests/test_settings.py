from pathlib import Path

import pytest

from src.infrastructure.config.settings import Settings


def test_settings_parse_csv_and_json_lists():
    csv_settings = Settings(CORS_ALLOWED_ORIGINS="https://a.example,https://b.example")
    json_settings = Settings(TRUSTED_HOSTS='["api.example.com", "admin.example.com"]')

    assert csv_settings.CORS_ALLOWED_ORIGINS == [
        "https://a.example",
        "https://b.example",
    ]
    assert json_settings.TRUSTED_HOSTS == ["api.example.com", "admin.example.com"]


def test_settings_resolve_secret_files(tmp_path: Path):
    secret_file = tmp_path / "jwt.secret"
    secret_file.write_text("jwt-secret-from-file", encoding="utf-8")

    settings = Settings(JWT_SECRET="", JWT_SECRET_FILE=str(secret_file))

    assert settings.JWT_SECRET == "jwt-secret-from-file"


def test_settings_default_to_billing_database_boundary():
    settings = Settings()

    assert settings.EXPECTED_DATABASE_NAME == "billing_service_db"
    assert settings.EXPECTED_DATABASE_USERNAME == "billing_service_user"
    assert "billing_service_db" in settings.DATABASE_URL


def test_real_mercado_pago_api_requires_non_demo_token():
    with pytest.raises(
        ValueError, match="valid Mercado Pago sandbox or production token"
    ):
        Settings(
            APP_RUNTIME_MODE="real",
            PAYMENT_PROVIDER_MODE="mercado_pago",
            MERCADO_PAGO_API_BASE_URL="https://api.mercadopago.com",
            MERCADO_PAGO_ACCESS_TOKEN="local-demo-token",
        )
