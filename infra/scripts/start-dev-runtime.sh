#!/usr/bin/env sh
set -eu

# One bounded entrypoint for the full local stack. It is the only active Dev
# runtime entrypoint; historical local startup remains outside this path.
ROOT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
COMPOSE_FILE="$ROOT_DIR/infra/docker-compose.dev.yml"
PROJECT="${GRAF_DEV_COMPOSE_PROJECT:-graf-dev}"
SOURCE_SHA="${GRAF_DEV_SOURCE_SHA:-}"
STATE_ROOT="${GRAF_DEV_STATE_ROOT:-${GRAF_DEV_STATE_DIR:-$HOME/Library/Application Support/GRAF Dev/$PROJECT}}"
SERVER_ROOT="$ROOT_DIR/apps/server"

fail() { echo "GRAF Dev runtime: $1" >&2; exit 1; }
require_image_id() {
  printf '%s' "$2" | grep -Eq '^sha256:[0-9a-fA-F]{64}$' || fail "$1 must be an immutable Docker image ID"
}

[ -f "$COMPOSE_FILE" ] || fail "full-stack Compose file is missing"
[ -n "$SOURCE_SHA" ] && printf '%s' "$SOURCE_SHA" | grep -Eq '^[0-9a-fA-F]{40}$' || fail "GRAF_DEV_SOURCE_SHA must be a full 40-character SHA"
case "$PROJECT" in graf-dev) ;; *) fail "Compose project must be the isolated graf-dev namespace" ;; esac
case "$STATE_ROOT" in *production*|*prod-data*|*prod_data*) fail "production-looking state root is forbidden" ;; esac

require_image_id GRAF_DEV_API_IMAGE "${GRAF_DEV_API_IMAGE:-}"
require_image_id GRAF_DEV_PROCESSING_WORKER_IMAGE "${GRAF_DEV_PROCESSING_WORKER_IMAGE:-}"
require_image_id GRAF_DEV_MAINTENANCE_IMAGE "${GRAF_DEV_MAINTENANCE_IMAGE:-}"
require_image_id GRAF_DEV_MEDIA_WORKER_IMAGE "${GRAF_DEV_MEDIA_WORKER_IMAGE:-}"
require_image_id GRAF_DEV_MIGRATION_IMAGE "${GRAF_DEV_MIGRATION_IMAGE:-}"
require_image_id GRAF_DEV_TEMPORAL_IMAGE "${GRAF_DEV_TEMPORAL_IMAGE:-}"
require_image_id GRAF_DEV_DATABASE_IMAGE "${GRAF_DEV_DATABASE_IMAGE:-}"
require_image_id GRAF_DEV_STORAGE_IMAGE "${GRAF_DEV_STORAGE_IMAGE:-}"
require_image_id GRAF_DEV_STORAGE_INIT_IMAGE "${GRAF_DEV_STORAGE_INIT_IMAGE:-}"

command -v docker >/dev/null 2>&1 || fail "docker is required"
command -v uv >/dev/null 2>&1 || fail "uv is required"
mkdir -p "$STATE_ROOT"

export GRAF_DEV_SOURCE_SHA="$SOURCE_SHA"
export GRAF_DEV_EXPECTED_MIGRATION_HEAD="${GRAF_DEV_EXPECTED_MIGRATION_HEAD:-${GRAF_DEV_MIGRATION_HEAD:-}}"
export GRAF_DEV_DATABASE_URL="${GRAF_DEV_DATABASE_URL:-postgresql+asyncpg://twobrain_rec:twobrain_rec@127.0.0.1:54329/twobrain_rec}"
export TWOBRAIN_DATABASE_URL="$GRAF_DEV_DATABASE_URL"
export TWOBRAIN_ENV=development
export TWOBRAIN_PUBLIC_BASE_URL="${TWOBRAIN_PUBLIC_BASE_URL:-http://127.0.0.1:8081}"
export TWOBRAIN_PROCESSING_ENABLED=true
export TWOBRAIN_WEB_LOGIN_WORKSPACE_ID=20000000-0000-0000-0000-000000000001
export TWOBRAIN_EMAIL_LOGIN_DELIVERY_ENABLED=false
export TWOBRAIN_LOCAL_HTTP_AUTH_COOKIE_ENABLED=true
export TWOBRAIN_LOCAL_EMAIL_LOGIN_CODE=000000
export TWOBRAIN_API_HOST=127.0.0.1
export TWOBRAIN_API_PORT=8081
export TWOBRAIN_MINIO_ENDPOINT=127.0.0.1:9002
export TWOBRAIN_MINIO_ACCESS_KEY=twobrain_rec_api
export TWOBRAIN_MINIO_SECRET_KEY=twobrain_rec_api_dev_secret
export TWOBRAIN_MINIO_BUCKET=twobrain-rec-ingest
export TWOBRAIN_MINIO_SECURE=false
export GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE="${GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE:-$STATE_ROOT/graf_credential_encryption_key}"

if [ ! -s "$GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE" ]; then
  mkdir -p "$(dirname -- "$GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE")"
  (umask 077; uv run --directory "$SERVER_ROOT" python -c 'from cryptography.fernet import Fernet; import pathlib,sys; pathlib.Path(sys.argv[1]).write_bytes(Fernet.generate_key()+b"\n")' "$GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE")
fi

compose() { docker compose -p "$PROJECT" -f "$COMPOSE_FILE" "$@"; }

# Install cleanup before the first infrastructure start.  Preflight, migration
# and seed failures must not leave a partially started stack holding the fixed
# Dev ports.  Clear the traps before exiting so the cleanup path is run once.
cleanup() {
  status=$?
  trap - 0 2 15
  compose stop >/dev/null 2>&1 || true
  exit "$status"
}
trap cleanup 0 2 15

# Config is the first safety gate: it resolves the explicit namespace and
# ensures no inherited production endpoint or secret is accepted.
compose config --quiet
# Recreate every service on promotion so a new exact-SHA image cannot be
# masked by Compose's config-hash reuse of a previous container.
compose up -d --wait --force-recreate rec-postgres rec-minio rec-temporal
compose run --rm rec-minio-init

PREFLIGHT="$ROOT_DIR/infra/scripts/dev-migration-preflight.py"
set +e
PREFLIGHT_JSON=$(uv run --directory "$SERVER_ROOT" python "$PREFLIGHT" --json)
PREFLIGHT_STATUS=$?
set -e
printf '%s\n' "$PREFLIGHT_JSON" > "$STATE_ROOT/migration-preflight.json"
[ "$PREFLIGHT_STATUS" -eq 0 ] || fail "migration preflight blocked; see metadata-only $STATE_ROOT/migration-preflight.json"

compose run --rm rec-migrate
(cd "$SERVER_ROOT" && uv run python scripts/seed_dev_identity.py --print-login)
compose up -d --wait --force-recreate api rec-processing-worker rec-maintenance rec-media-worker
compose ps --format json > "$STATE_ROOT/compose-services.json"
printf '%s\n' "GRAF Dev runtime ready: project=$PROJECT sha=$SOURCE_SHA"

# Keep a parent process with a verifiable command/start token.  The cleanup
# trap above stops the exact Compose project and never touches another
# worktree or production.
while compose ps --services --filter status=running 2>/dev/null | grep -q .; do
  sleep 2
done
