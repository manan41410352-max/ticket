#!/bin/sh
set -eu

DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"
MAX_RETRIES="${DB_MAX_RETRIES:-30}"
SLEEP_SECONDS="${DB_RETRY_INTERVAL:-2}"

echo "Starting backend entrypoint..."
echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}"

attempt=1
while [ "$attempt" -le "$MAX_RETRIES" ]; do
  if python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('${DB_HOST}', int('${DB_PORT}'))); s.close()"; then
    echo "PostgreSQL is reachable."
    break
  fi

  echo "Attempt ${attempt}/${MAX_RETRIES}: PostgreSQL is not ready yet. Retrying in ${SLEEP_SECONDS}s..."
  attempt=$((attempt + 1))
  sleep "$SLEEP_SECONDS"
done

if [ "$attempt" -gt "$MAX_RETRIES" ]; then
  echo "Failed to connect to PostgreSQL at ${DB_HOST}:${DB_PORT} after ${MAX_RETRIES} attempts."
  exit 1
fi

echo "Running database migrations..."
python manage.py migrate

echo "Starting gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000
