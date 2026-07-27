#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
run_suffix="$(id -u)_$$_${RANDOM}_${RANDOM}"
run_suffix="${run_suffix//[^a-z0-9_]/_}"
run_prefix="twobrain_rec_test_${run_suffix}"
rls_database="${run_prefix}_rls"
container_name="graf-postgres-test-${run_suffix}"
postgres_port=""
metadata_directory=""
container_started=false

if [[ ! "$run_prefix" =~ ^twobrain_rec_test_[a-z0-9_]+$ ]] \
  || [[ ! "$rls_database" =~ ^twobrain_rec_test_[a-z0-9_]+_rls$ ]] \
  || (( ${#run_prefix} > 40 )); then
  printf 'refusing unsafe generated PostgreSQL test name\n' >&2
  exit 2
fi

cleanup() {
  local exit_status=$?
  trap - EXIT INT TERM
  if [[ -n "$metadata_directory" ]]; then
    rm -rf "$metadata_directory"
  fi
  if [[ "$container_started" == true ]]; then
    docker rm --force "$container_name" >/dev/null 2>&1 || true
    printf 'postgres_test_cleanup=isolated_container_removed\n'
  else
    printf 'postgres_test_cleanup=container_not_started\n'
  fi
  exit "$exit_status"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if ! docker info >/dev/null 2>&1; then
  printf 'Docker Engine is unavailable; start Docker Desktop and retry.\n' >&2
  exit 1
fi

postgres_ready=false
database_ready=false

create_database_if_missing() {
  local database_name="$1"
  for _ in {1..40}; do
    if docker exec "$container_name" \
      psql --set=ON_ERROR_STOP=1 --username=twobrain_rec --dbname=postgres \
      --tuples-only --no-align \
      --command "select 1 from pg_database where datname = '${database_name}'" \
      2>/dev/null | grep -qx '1'; then
      return 0
    fi
    if docker exec "$container_name" \
      psql --set=ON_ERROR_STOP=1 --username=twobrain_rec --dbname=postgres \
      --command "create database \"${database_name}\"" \
      >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  return 1
}

for attempt in 1 2; do
  if docker run --detach --rm --name "$container_name" \
    --env POSTGRES_DB=postgres \
    --env POSTGRES_USER=twobrain_rec \
    --env POSTGRES_PASSWORD=twobrain_rec \
    --publish 127.0.0.1::5432 \
    postgres:17-alpine >/dev/null; then
    container_started=true
  else
    container_started=false
  fi

  if [[ "$container_started" == true ]]; then
    for _ in {1..120}; do
      if docker exec "$container_name" pg_isready --username=twobrain_rec --dbname=postgres \
        >/dev/null 2>&1; then
        postgres_ready=true
        break
      fi
      sleep 0.25
    done
  fi

  if [[ "$postgres_ready" == true ]] \
    && create_database_if_missing "$run_prefix" \
    && create_database_if_missing "$rls_database"; then
    database_ready=true
    break
  fi

  if [[ "$container_started" == true ]]; then
    docker rm --force "$container_name" >/dev/null 2>&1 || true
    container_started=false
  fi
  postgres_ready=false
  if (( attempt == 1 )); then
    printf 'postgres_test_container_start_retry=1\n' >&2
  fi
done

if [[ "$postgres_ready" != true || "$database_ready" != true ]]; then
  printf 'Disposable PostgreSQL test container did not become ready.\n' >&2
  exit 1
fi

postgres_port="$(docker port "$container_name" 5432/tcp | awk -F: 'NR == 1 { print $NF }')"
if [[ ! "$postgres_port" =~ ^[0-9]+$ ]]; then
  printf 'Disposable PostgreSQL test container did not expose a safe port.\n' >&2
  exit 1
fi

pytest_args=()
mode="full"
for argument in "$@"; do
  case "$argument" in
    --focused)
      mode="focused"
      ;;
    --full)
      mode="full"
      ;;
    *)
      pytest_args+=("$argument")
      ;;
  esac
done

workers="${GRAF_TEST_WORKERS:-8}"
if [[ ! "$workers" =~ ^[1-9][0-9]*$ ]] || (( workers > 8 )); then
  printf 'GRAF_TEST_WORKERS must be an integer from 1 through 8.\n' >&2
  exit 2
fi

metadata_directory="$(mktemp -d "${TMPDIR:-/tmp}/graf-postgres-test.XXXXXX")"
test_url="postgresql+asyncpg://twobrain_rec:twobrain_rec@127.0.0.1:${postgres_port}/${run_prefix}"
rls_url="postgresql+asyncpg://twobrain_rec:twobrain_rec@127.0.0.1:${postgres_port}/${rls_database}"
admin_url="postgresql+asyncpg://twobrain_rec:twobrain_rec@127.0.0.1:${postgres_port}/postgres"

cd "$repo_root/apps/server"
export PYTHONPATH=src
export GRAF_TEST_DATABASE_URL="$test_url"
export GRAF_TEST_DATABASE_PREFIX="$run_prefix"
export GRAF_TEST_POSTGRES_ADMIN_URL="$admin_url"
export RLS_TEST_DATABASE_URL="$rls_url"
export TWOBRAIN_DATABASE_URL="$test_url"

run_phase() {
  local phase="$1"
  shift
  local started_at completed_at duration_seconds phase_status
  started_at="$(date +%s)"
  if "$@"; then
    completed_at="$(date +%s)"
    duration_seconds=$((completed_at - started_at))
    printf 'postgres_test_phase=%s status=pass duration_seconds=%s\n' \
      "$phase" "$duration_seconds"
    return 0
  else
    phase_status=$?
    completed_at="$(date +%s)"
    duration_seconds=$((completed_at - started_at))
    printf 'postgres_test_phase=%s status=fail duration_seconds=%s\n' \
      "$phase" "$duration_seconds" >&2
    return "$phase_status"
  fi
}

if [[ "$mode" == "focused" ]]; then
  run_phase focused uv run --extra dev pytest --durations=20 "${pytest_args[@]}"
  printf 'postgres_test_result=pass mode=focused\n'
  exit 0
fi

collect_node_ids() {
  local destination="$1"
  shift
  uv run --extra dev pytest --collect-only -q "$@" \
    | awk '/^tests\// { print }' \
    | LC_ALL=C sort -u >"$destination"
}

baseline_node_ids="$metadata_directory/baseline-nodeids.txt"
ordinary_node_ids="$metadata_directory/ordinary-nodeids.txt"
governance_node_ids="$metadata_directory/governance-nodeids.txt"
strict_node_ids="$metadata_directory/strict-nodeids.txt"
union_node_ids="$metadata_directory/union-nodeids.txt"
collect_node_ids "$baseline_node_ids" -m "not spike" "${pytest_args[@]}"
collect_node_ids "$ordinary_node_ids" -m "not governance and not strict_rls and not spike" "${pytest_args[@]}"
collect_node_ids "$governance_node_ids" -m "governance and not strict_rls and not spike" "${pytest_args[@]}"
collect_node_ids "$strict_node_ids" -m "strict_rls and not spike" "${pytest_args[@]}"
cat "$ordinary_node_ids" "$governance_node_ids" "$strict_node_ids" | LC_ALL=C sort -u >"$union_node_ids"

if ! cmp -s "$baseline_node_ids" "$union_node_ids"; then
  printf 'full PostgreSQL phase union differs from baseline collection\n' >&2
  diff -u "$baseline_node_ids" "$union_node_ids" >&2 || true
  exit 1
fi

collection_count="$(wc -l <"$baseline_node_ids" | tr -d ' ')"
collection_digest="$(shasum -a 256 "$baseline_node_ids" | awk '{ print $1 }')"
printf 'postgres_test_mode=full worker_count=%s collection_count=%s collection_digest=%s\n' \
  "$workers" "$collection_count" "$collection_digest"

run_phase ordinary uv run --extra dev pytest -n "$workers" --dist=loadfile \
  -m "not governance and not strict_rls and not spike" --durations=20 "${pytest_args[@]}"
run_phase governance uv run --extra dev pytest -n "$workers" --dist=loadfile \
  -m "governance and not strict_rls and not spike" --durations=20 "${pytest_args[@]}"
run_phase strict uv run --extra dev pytest -m "strict_rls and not spike" --durations=20 "${pytest_args[@]}"
printf 'postgres_test_result=pass mode=full collection_digest=%s\n' "$collection_digest"
