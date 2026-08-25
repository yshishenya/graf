#!/usr/bin/env sh
set -eu
ROOT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
COMPOSE_FILE="$ROOT_DIR/infra/docker-compose.local.yml"
SERVER_DIR="$ROOT_DIR/apps/server"
LOCAL_CREDENTIAL_KEY_FILE="$ROOT_DIR/infra/secrets/graf_credential_encryption_key"
export TWOBRAIN_ENV=development
export TWOBRAIN_CALENDAR_ALLOW_UNCERTIFIED_YANDEX="${TWOBRAIN_CALENDAR_ALLOW_UNCERTIFIED_YANDEX:-true}"
export TWOBRAIN_API_HOST=127.0.0.1
export TWOBRAIN_API_PORT="${TWOBRAIN_API_PORT:-8081}"
export TWOBRAIN_DATABASE_URL="${TWOBRAIN_DATABASE_URL:-postgresql+asyncpg://twobrain_rec:twobrain_rec@127.0.0.1:54330/twobrain_rec}"
export TWOBRAIN_MINIO_ENDPOINT="${TWOBRAIN_MINIO_ENDPOINT:-127.0.0.1:9010}"
export TWOBRAIN_MINIO_ACCESS_KEY="${TWOBRAIN_MINIO_ACCESS_KEY:-twobrain_rec}"
export TWOBRAIN_MINIO_SECRET_KEY="${TWOBRAIN_MINIO_SECRET_KEY:-twobrain_rec_dev_secret}"
export TWOBRAIN_MINIO_BUCKET="${TWOBRAIN_MINIO_BUCKET:-twobrain-rec-ingest}"
export TWOBRAIN_MINIO_SECURE=false
export TWOBRAIN_WEB_LOGIN_WORKSPACE_ID=20000000-0000-0000-0000-000000000001
export TWOBRAIN_EMAIL_LOGIN_DELIVERY_ENABLED=false
export TWOBRAIN_LOCAL_HTTP_AUTH_COOKIE_ENABLED=true
export TWOBRAIN_LOCAL_EMAIL_LOGIN_CODE=000000
export TWOBRAIN_PROCESSING_ENABLED=false
export TWOBRAIN_OUTCOME_GENERATION_ENABLED=false
export TWOBRAIN_BILLING_CHECKOUT_ENABLED=false
export TWOBRAIN_PRODUCT_ANALYTICS_ENABLED=false
export TWOBRAIN_PUBLIC_ANALYTICS_ENABLED=false
command -v docker >/dev/null || { echo "docker is required" >&2; exit 1; }
command -v uv >/dev/null || { echo "uv is required" >&2; exit 1; }
if [ ! -s "$LOCAL_CREDENTIAL_KEY_FILE" ]; then
  mkdir -p "$(dirname "$LOCAL_CREDENTIAL_KEY_FILE")"
  (
    umask 077
    cd "$SERVER_DIR"
    uv run python -c 'from cryptography.fernet import Fernet; from pathlib import Path; import sys; Path(sys.argv[1]).write_bytes(Fernet.generate_key() + b"\n")' "$LOCAL_CREDENTIAL_KEY_FILE"
  )
fi
export GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE="${GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE:-$LOCAL_CREDENTIAL_KEY_FILE}"
docker compose -f "$COMPOSE_FILE" up -d --wait rec-postgres rec-minio
(
  cd "$SERVER_DIR"
  uv run alembic upgrade head
  uv run python scripts/seed_dev_identity.py --print-login
  uv run python -c 'from twobrain_rec_server.config import Settings; from twobrain_rec_server.storage.minio_client import MinioStorage; MinioStorage(Settings()).ensure_bucket()'
)
echo "Local GRAF server: http://${TWOBRAIN_API_HOST}:${TWOBRAIN_API_PORT}"
echo "Local login: http://${TWOBRAIN_API_HOST}:${TWOBRAIN_API_PORT}/login"
cd "$SERVER_DIR"
exec uv run uvicorn twobrain_rec_server.main:create_app --factory --host "$TWOBRAIN_API_HOST" --port "$TWOBRAIN_API_PORT"
