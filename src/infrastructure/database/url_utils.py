from __future__ import annotations

from urllib.parse import urlsplit

PLACEHOLDER_DATABASE_HOSTS = {
    "seu_host_postgres",
    "your-rds-endpoint",
    "endpoint-rds",
    "db-host",
}


def normalize_postgresql_url_for_alembic(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url


def describe_database_target(database_url: str) -> tuple[str, str, int, str]:
    parsed = urlsplit(database_url)
    username = parsed.username or ""
    host = parsed.hostname or ""
    port = parsed.port or 5432
    database = parsed.path.lstrip("/") or "<unknown>"
    return username, host, port, database


def validate_runtime_database_url(
    database_url: str,
    *,
    expected_database: str | None = None,
    expected_username: str | None = None,
) -> tuple[str, int, str, str]:
    if not database_url.strip():
        raise ValueError("DATABASE_URL environment variable is required.")

    username, host, port, database = describe_database_target(database_url)
    normalized_host = host.strip().lower()

    if not host:
        raise ValueError("DATABASE_URL must include a database host.")
    if not username:
        raise ValueError("DATABASE_URL must include a database username.")
    if database in {"", "<unknown>"}:
        raise ValueError("DATABASE_URL must include a database name.")

    if normalized_host in PLACEHOLDER_DATABASE_HOSTS:
        raise ValueError(
            "DATABASE_URL host still uses a placeholder value. "
            "Replace it with the real RDS endpoint."
        )

    if expected_database and database != expected_database:
        raise ValueError(
            "DATABASE_URL points to the wrong database. "
            f"Expected '{expected_database}', got '{database}'."
        )
    if expected_username and username != expected_username:
        raise ValueError(
            "DATABASE_URL uses the wrong database user. "
            f"Expected '{expected_username}', got '{username}'."
        )

    return host, port, database, username
