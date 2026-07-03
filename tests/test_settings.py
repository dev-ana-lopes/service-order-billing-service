from pathlib import Path

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
