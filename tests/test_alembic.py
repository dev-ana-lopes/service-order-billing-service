from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_alembic_upgrade_head_runs_successfully(tmp_path: Path) -> None:
    database_path = tmp_path / "alembic-test.db"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite+pysqlite:///{database_path.as_posix()}"

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {
        "alembic_version",
        "payments",
        "processed_events",
        "quotes",
    }.issubset(table_names)


def test_alembic_upgrade_head_uses_app_env_file_when_database_url_is_not_exported(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "alembic-app-env-file.db"
    env_file = tmp_path / ".env.alembic"
    env_file.write_text(
        f"DATABASE_URL=sqlite+pysqlite:///{database_path.as_posix()}\n",
        encoding="utf-8",
    )

    environment = os.environ.copy()
    environment.pop("DATABASE_URL", None)
    environment["APP_ENV_FILE"] = str(env_file)

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
