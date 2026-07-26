#!/usr/bin/env sh
set -eu

should_migrate="${MIGRATE_ON_STARTUP:-true}"

python - <<'PY'
import os
import socket
import sys

from src.infrastructure.database.url_utils import validate_runtime_database_url


database_url = os.environ.get("DATABASE_URL", "").strip()
expected_database = os.environ.get(
    "EXPECTED_DATABASE_NAME", "billing_service_db"
).strip()
expected_username = os.environ.get(
    "EXPECTED_DATABASE_USERNAME", "billing_service_user"
).strip()

try:
    host, port, database, username = validate_runtime_database_url(
        database_url,
        expected_database=expected_database,
        expected_username=expected_username,
    )
except ValueError as exc:
    print(f"[entrypoint] {exc}", flush=True)
    sys.exit(1)

print(
    f"[entrypoint] Database target host={host} port={port} db={database} user={username}",
    flush=True,
)

try:
    resolved = sorted(
        {
            result[4][0]
            for result in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        }
    )
except OSError as exc:
    print(
        f"[entrypoint] Database host resolution failed for host={host}: {exc}",
        flush=True,
    )
else:
    print(
        f"[entrypoint] Database host resolved to: {', '.join(resolved)}",
        flush=True,
    )
PY

if [ "$should_migrate" != "false" ]; then
  echo "[entrypoint] Running migrations (alembic upgrade head)..."
  attempts="${MIGRATE_MAX_ATTEMPTS:-30}"
  sleep_seconds="${MIGRATE_RETRY_SLEEP_SECONDS:-2}"

  i=1
  while [ "$i" -le "$attempts" ]; do
    if alembic -c alembic/alembic.ini upgrade head; then
      echo "[entrypoint] Migrations applied."
      break
    fi

    echo "[entrypoint] Migration attempt $i/$attempts failed; retrying in ${sleep_seconds}s..."
    i=$((i + 1))
    sleep "$sleep_seconds"
  done

  if [ "$i" -gt "$attempts" ]; then
    echo "[entrypoint] Migrations failed after ${attempts} attempts."
    exit 1
  fi
fi

echo "[entrypoint] Starting application: $*"
exec "$@"
