from __future__ import annotations

from sqlalchemy import create_engine, text

from .url_utils import normalize_postgresql_url_for_alembic


class DatabaseReadinessProbe:
    def __init__(
        self,
        database_url: str,
        *,
        expected_database: str,
        expected_username: str,
        timeout_seconds: int,
    ) -> None:
        self._expected_database = expected_database
        self._expected_username = expected_username
        self._engine = create_engine(
            normalize_postgresql_url_for_alembic(database_url),
            pool_pre_ping=True,
            connect_args={"connect_timeout": timeout_seconds},
        )

    def check(self) -> dict[str, str]:
        with self._engine.connect() as connection:
            current_database = str(
                connection.execute(text("SELECT current_database()")).scalar_one()
            )
            current_user = str(connection.execute(text("SELECT current_user")).scalar_one())

        if current_database != self._expected_database:
            raise RuntimeError(
                "Database readiness failed because the connected database does not "
                f"match the service boundary: expected '{self._expected_database}', "
                f"got '{current_database}'."
            )
        if current_user != self._expected_username:
            raise RuntimeError(
                "Database readiness failed because the connected database user does "
                f"not match the service boundary: expected '{self._expected_username}', "
                f"got '{current_user}'."
            )

        return {"application": "ok", "database": "ok"}

    def close(self) -> None:
        self._engine.dispose()
