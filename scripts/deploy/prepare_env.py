#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from src.infrastructure.database.url_utils import validate_runtime_database_url

REQUIRED_BOOLEAN_FIELDS = ("LOG_JSON",)
OPTIONAL_BOOLEAN_DEFAULTS = {
    "SMTP_USE_TLS": "false",
    "SMTP_USE_AUTH": "false",
}
REQUIRED_POSITIVE_INTEGER_FIELDS = (
    "HEALTHCHECK_TIMEOUT_SECONDS",
    "APPROVAL_TOKEN_TTL_MINUTES",
    "JWT_EXPIRATION_MINUTES",
)
OPTIONAL_POSITIVE_INTEGER_DEFAULTS = {
    "SMTP_PORT": "587",
    "SMTP_TIMEOUT_SECONDS": "10",
}
REQUIRED_TEXT_FIELDS = (
    "APP_NAME",
    "APP_VERSION",
    "ENVIRONMENT",
    "LOG_LEVEL",
    "LOG_JSON",
    "DATABASE_URL",
    "APP_BASE_URL",
    "CORS_ALLOWED_ORIGINS",
    "TRUSTED_HOSTS",
    "JWT_ALGORITHM",
)
VALID_ENVIRONMENTS = {"development", "test", "staging", "production"}
VALID_EMAIL_PROVIDERS = {"SMTP", "NOOP"}


class EnvValidationError(ValueError):
    pass


def load_env_file(env_path: Path) -> tuple[list[tuple[str, str]], dict[str, str]]:
    if not env_path.exists():
        raise EnvValidationError(f"Missing env file: {env_path}")

    entries: list[tuple[str, str]] = []
    values: dict[str, str] = {}

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw_line:
            entries.append(("raw", raw_line))
            continue

        key, value = raw_line.split("=", 1)
        normalized_key = key.strip()
        entries.append(("kv", normalized_key))
        values[normalized_key] = value.strip()

    return entries, values


def require_non_empty(values: dict[str, str], key: str) -> str:
    value = values.get(key, "").strip()
    if not value:
        raise EnvValidationError(f"{key} is required.")
    return value


def require_any(values: dict[str, str], keys: tuple[str, ...], label: str) -> None:
    if any(values.get(key, "").strip() for key in keys):
        return
    raise EnvValidationError(f"{label} is required ({' or '.join(keys)}).")


def normalize_boolean(values: dict[str, str], key: str) -> bool:
    raw_value = require_non_empty(values, key).lower()
    if raw_value not in {"true", "false"}:
        raise EnvValidationError(f"{key} must be true or false.")
    values[key] = raw_value
    return raw_value == "true"


def normalize_positive_integer(values: dict[str, str], key: str) -> None:
    raw_value = values.get(key, "").strip()
    if not raw_value:
        return

    try:
        number = int(raw_value)
    except ValueError as exc:
        raise EnvValidationError(f"{key} must be an integer.") from exc

    if number <= 0:
        raise EnvValidationError(f"{key} must be greater than zero.")

    values[key] = str(number)


def normalize_optional_boolean(values: dict[str, str], key: str, default: str) -> bool:
    raw_value = values.get(key, "").strip().lower()
    if not raw_value:
        if key in values:
            values[key] = default
        return default == "true"

    if raw_value not in {"true", "false"}:
        raise EnvValidationError(f"{key} must be true or false.")
    values[key] = raw_value
    return raw_value == "true"


def normalize_optional_positive_integer(
    values: dict[str, str], key: str, default: str
) -> None:
    raw_value = values.get(key, "").strip()
    if not raw_value:
        if key in values:
            values[key] = default
        return

    normalize_positive_integer(values, key)


def validate_database_url(values: dict[str, str]) -> None:
    database_url = require_non_empty(values, "DATABASE_URL")
    if not database_url.startswith(("postgresql://", "postgresql+asyncpg://")):
        raise EnvValidationError(
            "DATABASE_URL must start with postgresql:// or postgresql+asyncpg://."
        )
    try:
        validate_runtime_database_url(
            database_url,
            expected_database=values.get(
                "EXPECTED_DATABASE_NAME", "billing_service_db"
            ),
            expected_username=values.get(
                "EXPECTED_DATABASE_USERNAME", "billing_service_user"
            ),
        )
    except ValueError as exc:
        raise EnvValidationError(str(exc)) from exc


def validate_app_base_url(values: dict[str, str]) -> None:
    app_base_url = require_non_empty(values, "APP_BASE_URL")
    parsed_url = urlparse(app_base_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise EnvValidationError("APP_BASE_URL must be a valid absolute URL.")


def normalize_list_field(values: dict[str, str], key: str) -> None:
    raw_value = require_non_empty(values, key)

    if raw_value.startswith("["):
        try:
            parsed_value = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise EnvValidationError(f"{key} must be a valid JSON array.") from exc
        if not isinstance(parsed_value, list):
            raise EnvValidationError(f"{key} must be a JSON array.")
        items = [str(item).strip() for item in parsed_value if str(item).strip()]
    else:
        items = [item.strip() for item in raw_value.split(",") if item.strip()]

    if not items:
        raise EnvValidationError(f"{key} must contain at least one value.")

    values[key] = json.dumps(items, separators=(",", ":"))


def validate_environment(values: dict[str, str]) -> None:
    environment = require_non_empty(values, "ENVIRONMENT").lower()
    if environment not in VALID_ENVIRONMENTS:
        raise EnvValidationError(
            "ENVIRONMENT must be one of: development, test, staging, production."
        )
    values["ENVIRONMENT"] = environment


def normalize_email_provider(values: dict[str, str]) -> str:
    provider = values.get("EMAIL_PROVIDER", "SMTP").strip().upper() or "SMTP"
    if provider not in VALID_EMAIL_PROVIDERS:
        raise EnvValidationError("EMAIL_PROVIDER must be SMTP or NOOP.")
    values["EMAIL_PROVIDER"] = provider
    return provider


def validate_secret_contract(
    values: dict[str, str],
) -> None:
    require_any(
        values,
        ("APPROVAL_TOKEN_SECRET", "APPROVAL_TOKEN_SECRET_FILE"),
        "Approval token secret",
    )
    require_any(values, ("JWT_SECRET", "JWT_SECRET_FILE"), "JWT secret")
    require_any(
        values,
        ("CUSTOMER_JWT_SECRET", "CUSTOMER_JWT_SECRET_FILE"),
        "Customer JWT secret",
    )


def validate_required_text_fields(values: dict[str, str]) -> None:
    for key in REQUIRED_TEXT_FIELDS:
        require_non_empty(values, key)


def rewrite_env_file(
    env_path: Path, entries: list[tuple[str, str]], values: dict[str, str]
) -> None:
    normalized_lines: list[str] = []

    for entry_type, content in entries:
        if entry_type == "raw":
            normalized_lines.append(content)
            continue
        normalized_lines.append(f"{content}={values.get(content, '')}")

    env_path.write_text("\n".join(normalized_lines) + "\n", encoding="utf-8")


def prepare_env(env_path: Path) -> None:
    entries, values = load_env_file(env_path)

    validate_required_text_fields(values)
    validate_environment(values)
    normalize_email_provider(values)

    for key in REQUIRED_BOOLEAN_FIELDS:
        normalize_boolean(values, key)
    for key, default in OPTIONAL_BOOLEAN_DEFAULTS.items():
        normalize_optional_boolean(values, key, default)

    for key in REQUIRED_POSITIVE_INTEGER_FIELDS:
        normalize_positive_integer(values, key)
    for key, default in OPTIONAL_POSITIVE_INTEGER_DEFAULTS.items():
        normalize_optional_positive_integer(values, key, default)

    validate_database_url(values)
    validate_app_base_url(values)
    normalize_list_field(values, "CORS_ALLOWED_ORIGINS")
    normalize_list_field(values, "TRUSTED_HOSTS")
    validate_secret_contract(values)
    values["LOG_LEVEL"] = values["LOG_LEVEL"].upper()

    rewrite_env_file(env_path, entries, values)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and normalize a production .env file."
    )
    parser.add_argument("env_file", help="Path to the .env file to normalize")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env_path = Path(args.env_file)

    try:
        prepare_env(env_path)
    except EnvValidationError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    print(f"Prepared env file: {env_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
