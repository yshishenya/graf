#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/../.."

host="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
path="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"

run_rls_validation() {
  if [ -n "${RLS_TEST_DATABASE_URL:-}" ]; then
    python3 apps/server/scripts/verify_rls_hardening.py
    return $?
  fi

  rls_db_name="twobrain_rec_rls_$(date -u +%Y%m%d%H%M%S)_$$"
  if ! docker compose -f infra/docker-compose.yml exec -T rec-postgres sh -c '
    set -eu
    db_name="$1"
    export PGPASSWORD="$(cat /run/secrets/twobrain_postgres_password)"
    createdb -U twobrain_rec "$db_name"
  ' sh "$rls_db_name"; then
    cat <<EOF
rls_validation_result=blocked
environment=postgres_test
live_production_probe=not_attempted
destructive_probe_database=not_provided
live_production_enforcement=not_inspected
ready_for_production_truth=false
reason=rls_disposable_database_create_failed
EOF
    return 1
  fi

  set +e
  rls_output="$(docker compose -f infra/docker-compose.yml run --rm --no-deps --entrypoint sh rec-migrate -c '
    set -eu
    db_name="$1"
    password="$(cat /run/secrets/twobrain_postgres_password)"
    encoded_password="$(python - "$password" <<'"'"'PY'"'"'
from urllib.parse import quote
import sys

print(quote(sys.argv[1], safe=""))
PY
)"
    export RLS_TEST_DATABASE_URL="postgresql+asyncpg://twobrain_rec:${encoded_password}@rec-postgres:5432/${db_name}"
    export RLS_DESTRUCTIVE_PROBE_DATABASE_CLASS=disposable
    python scripts/verify_rls_hardening.py
  ' sh "$rls_db_name" 2>&1)"
  rls_status=$?
  docker compose -f infra/docker-compose.yml exec -T rec-postgres sh -c '
    set -eu
    db_name="$1"
    export PGPASSWORD="$(cat /run/secrets/twobrain_postgres_password)"
    dropdb -U twobrain_rec --if-exists --force "$db_name"
  ' sh "$rls_db_name" >/dev/null 2>&1
  cleanup_status=$?
  set -e

  printf '%s\n' "$rls_output"
  if [ "$cleanup_status" -ne 0 ]; then
    cat <<EOF
rls_validation_result=blocked
environment=postgres_test
live_production_probe=not_attempted
destructive_probe_database=not_provided
live_production_enforcement=not_inspected
ready_for_production_truth=false
reason=rls_disposable_database_cleanup_failed
EOF
    return 1
  fi
  return "$rls_status"
}

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
set +e
rls_output="$(run_rls_validation)"
rls_status=$?
set -e
if [ -z "$rls_output" ]; then
  rls_output="$(cat <<EOF
rls_validation_result=blocked
environment=postgres_test
live_production_probe=not_attempted
destructive_probe_database=not_provided
live_production_enforcement=not_inspected
ready_for_production_truth=false
reason=rls_validation_output_missing
EOF
)"
fi
printf '%s\n' "$rls_output"
if [ "$rls_status" -ne 0 ]; then
  cat <<EOF
migration_verification_result=blocked
reason=rls_validation_command_failed
remote_host=$host
deploy_path=$path
EOF
  exit "$rls_status"
fi
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
