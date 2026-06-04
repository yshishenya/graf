#!/usr/bin/env sh
set -eu

if [ "${1:-}" = "--remote" ]; then
  host="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
  path="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"
  exec ssh "$host" "cd '$path' && TWOBRAIN_ENV=production ./infra/scripts/validate-production-config.sh"
fi

cd "$(dirname "$0")/../.."

container_id=""
if command -v docker >/dev/null 2>&1; then
  container_id="$(docker compose -f infra/docker-compose.yml ps -q rec-api 2>/dev/null || true)"
fi

if [ -n "$container_id" ]; then
  docker compose -f infra/docker-compose.yml exec -T rec-api python - <<'PY'
from twobrain_rec_server.config import Settings

Settings()
print("production config validation: ok")
PY
  exit 0
fi

PYTHONPATH="${PYTHONPATH:-apps/server/src}"
export PYTHONPATH
export TWOBRAIN_ENV="${TWOBRAIN_ENV:-production}"

python3 - <<'PY'
from twobrain_rec_server.config import Settings

Settings()
print("production config validation: ok")
PY
