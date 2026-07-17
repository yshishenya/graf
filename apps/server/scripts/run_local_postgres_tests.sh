#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
compose_file="$repo_root/infra/docker-compose.dev.yml"
compose=(docker compose -f "$compose_file")
database_suffix="$(id -u)_$$_${RANDOM}_${RANDOM}"
database_suffix="${database_suffix//[^a-z0-9_]/_}"
test_database="twobrain_rec_test_${database_suffix}"
rls_database="${test_database}_rls"
test_url="postgresql+asyncpg://twobrain_rec:twobrain_rec@127.0.0.1:54329/${test_database}"
rls_url="postgresql+asyncpg://twobrain_rec:twobrain_rec@127.0.0.1:54329/${rls_database}"
created_databases=()

if [[ ! "$test_database" =~ ^twobrain_rec_test_[a-z0-9_]+$ ]] \
  || [[ ! "$rls_database" =~ ^twobrain_rec_test_[a-z0-9_]+$ ]]; then
  printf 'refusing unsafe generated PostgreSQL test database name\n' >&2
  exit 2
fi

cleanup() {
  local database_name
  for database_name in "${created_databases[@]:-}"; do
    "${compose[@]}" exec -T rec-postgres \
      psql --set=ON_ERROR_STOP=1 --username=twobrain_rec --dbname=postgres \
      --command "drop database if exists \"${database_name}\" with (force)" >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT INT TERM

if ! docker info >/dev/null 2>&1; then
  printf 'Docker Engine is unavailable. Start Docker Desktop, wait until it is ready, then retry.\n' >&2
  exit 1
fi

if ! "${compose[@]}" up -d --wait rec-postgres; then
  printf 'Local PostgreSQL could not start. Check whether local port 54329 is occupied, then retry.\n' >&2
  exit 1
fi

for database_name in "$test_database" "$rls_database"; do
  "${compose[@]}" exec -T rec-postgres \
    psql --set=ON_ERROR_STOP=1 --username=twobrain_rec --dbname=postgres \
    --command "create database \"${database_name}\"" >/dev/null
  created_databases+=("$database_name")
done

cd "$repo_root/apps/server"
TWOBRAIN_DATABASE_URL="$test_url" \
RLS_TEST_DATABASE_URL="$rls_url" \
PYTHONPATH=src \
uv run --extra dev pytest "$@"
