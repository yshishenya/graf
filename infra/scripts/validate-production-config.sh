#!/usr/bin/env sh
set -eu

if [ "${1:-}" = "--remote" ]; then
  host="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
  path="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"
  exec ssh "$host" "cd '$path' && TWOBRAIN_ENV=production ./infra/scripts/validate-production-config.sh"
fi

cd "$(dirname "$0")/../.."

PYTHONPATH="${PYTHONPATH:-apps/server/src}"
export PYTHONPATH
export TWOBRAIN_ENV="${TWOBRAIN_ENV:-production}"

python3 - <<'PY'
from twobrain_rec_server.config import Settings

Settings()
print("production config validation: ok")
PY
