#!/usr/bin/env bash
set -euo pipefail

run_migrations="${RUN_MIGRATIONS:-false}"

if [ "${run_migrations}" = "true" ]; then
    attempts=5
    delay=1
    for attempt in $(seq 1 "${attempts}"); do
        echo "running database migrations (attempt ${attempt}/${attempts})"
        if alembic upgrade head; then
            break
        fi
        if [ "${attempt}" = "${attempts}" ]; then
            echo "database migrations failed" >&2
            exit 1
        fi
        sleep "${delay}"
        delay=$((delay * 2))
    done
fi

exec "$@"
