#!/usr/bin/env sh
set -eu

host="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
path="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"

if [ "${1:-}" = "--remote" ]; then
  exec ssh "$host" "cd '$path' && ./infra/scripts/verify-rec-migration.sh --execute"
fi

if [ "${1:-}" != "--execute" ]; then
  cat <<EOF
migration_verification_result=blocked
reason=remote_execution_required
remote_host=$host
deploy_path=$path
EOF
  exit 0
fi

docker compose -f infra/docker-compose.yml run --rm rec-migrate alembic current
cat <<EOF
migration_verification_result=pass
remote_host=$host
deploy_path=$path
EOF
