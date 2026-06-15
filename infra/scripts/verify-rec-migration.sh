#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/../.."

host="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
path="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"

if [ "${1:-}" = "--remote" ]; then
  exec ssh "$host" "cd '$path' && ./infra/scripts/verify-rec-migration.sh --execute"
fi

if [ "${1:-}" != "--execute" ]; then
  rls_output="$(python3 apps/server/scripts/verify_rls_hardening.py)"
  cat <<EOF
migration_verification_result=blocked
reason=remote_execution_required
remote_host=$host
deploy_path=$path
$rls_output
EOF
  exit 0
fi

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

docker compose -f infra/docker-compose.yml run --rm rec-migrate alembic current
rls_output="$(python3 apps/server/scripts/verify_rls_hardening.py)"
printf '%s\n' "$rls_output"
case "$rls_output" in
  *"rls_validation_result=pass"*) ;;
  *)
    cat <<EOF
migration_verification_result=blocked
reason=rls_validation_blocked
remote_host=$host
deploy_path=$path
EOF
    exit 1
    ;;
esac
cat <<EOF
migration_verification_result=pass
remote_host=$host
deploy_path=$path
EOF
