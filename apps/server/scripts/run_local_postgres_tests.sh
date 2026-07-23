#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
database_suffix="$(id -u)_$$_${RANDOM}_${RANDOM}"
database_suffix="${database_suffix//[^a-z0-9_]/_}"
test_database="twobrain_rec_test_${database_suffix}"
rls_database="${test_database}_rls"
postgres_container="graf-postgres-test-${database_suffix//_/-}"
postgres_port=""
container_started=false
metadata_directory=""
media_password=""

if [[ ! "$test_database" =~ ^twobrain_rec_test_[a-z0-9_]+$ ]] \
  || [[ ! "$rls_database" =~ ^twobrain_rec_test_[a-z0-9_]+$ ]]; then
  printf 'refusing unsafe generated PostgreSQL test database name\n' >&2
  exit 2
fi

cleanup() {
  local exit_status=$?
  trap - EXIT INT TERM
  if [[ -n "$metadata_directory" ]]; then
    rm -rf "$metadata_directory"
  fi
  if [[ "$container_started" == true ]]; then
    docker rm --force --volumes "$postgres_container" >/dev/null 2>&1 || true
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
  printf 'Docker Engine is unavailable. Start Docker Desktop, wait until it is ready, then retry.\n' >&2
  exit 1
fi

postgres_initialized=false
for start_attempt in 1 2; do
  postgres_ready=false
  if docker run --detach --rm --name "$postgres_container" \
    --env POSTGRES_DB=postgres \
    --env POSTGRES_USER=twobrain_rec \
    --env POSTGRES_PASSWORD=twobrain_rec \
    --tmpfs /var/lib/postgresql/data:rw \
    --publish 127.0.0.1::5432 \
    postgres:17-alpine >/dev/null; then
    container_started=true
  else
    container_started=false
  fi
  if [[ "$container_started" == true ]]; then
    for _attempt in {1..120}; do
      if docker exec "$postgres_container" \
        pg_isready --username=twobrain_rec --dbname=postgres >/dev/null 2>&1; then
        postgres_ready=true
        break
      fi
      sleep 0.25
    done
  fi
  if [[ "$postgres_ready" == true ]]; then
    for _database_attempt in {1..20}; do
      if docker exec "$postgres_container" \
        psql --set=ON_ERROR_STOP=1 --username=twobrain_rec --dbname=postgres \
        --command "create database \"${rls_database}\"" >/dev/null; then
        postgres_initialized=true
        break
      fi
      sleep 0.25
    done
  fi
  if [[ "$postgres_initialized" == true ]]; then
    break
  fi
  if [[ "$container_started" == true ]]; then
    docker rm --force --volumes "$postgres_container" >/dev/null 2>&1 || true
    container_started=false
  fi
  if (( start_attempt < 2 )); then
    printf 'postgres_test_container_start_retry=1\n' >&2
  fi
done
if [[ "$postgres_initialized" != true ]]; then
  printf 'Disposable PostgreSQL test container did not become ready.\n' >&2
  exit 1
fi

postgres_port="$(docker port "$postgres_container" 5432/tcp | awk -F: 'NR == 1 { print $NF }')"
if [[ ! "$postgres_port" =~ ^[0-9]+$ ]]; then
  printf 'Disposable PostgreSQL test container did not expose a safe loopback port.\n' >&2
  exit 1
fi

test_url="postgresql+asyncpg://twobrain_rec:twobrain_rec@127.0.0.1:${postgres_port}/${test_database}"
rls_url="postgresql+asyncpg://twobrain_rec:twobrain_rec@127.0.0.1:${postgres_port}/${rls_database}"
admin_url="postgresql+asyncpg://twobrain_rec:twobrain_rec@127.0.0.1:${postgres_port}/postgres"
media_password="$(openssl rand -hex 24)"
if [[ ! "$media_password" =~ ^[a-f0-9]{48}$ ]]; then
  printf 'Unable to generate an ephemeral PostgreSQL media-role credential.\n' >&2
  exit 1
fi
rls_media_url="postgresql+asyncpg://twobrain_rec_media:${media_password}@127.0.0.1:${postgres_port}/${rls_database}"

pytest_args=()
requested_mode=""
for argument in "$@"; do
  case "$argument" in
    --full)
      requested_mode="full"
      ;;
    --focused)
      requested_mode="focused"
      ;;
    *)
      pytest_args+=("$argument")
      ;;
  esac
done

mode="full"
for argument in "${pytest_args[@]}"; do
  case "$argument" in
    -k|--keyword|-m|--markers|--ignore|--deselect|--pyargs)
      mode="focused"
      ;;
    --keyword=*|--markers=*|--ignore=*|--deselect=*|--pyargs=*)
      mode="focused"
      ;;
    -*)
      ;;
    *)
      mode="focused"
      ;;
  esac
done
if [[ "$requested_mode" == "full" && "$mode" == "focused" ]]; then
  printf '%s\n' 'refusing --full with a focused pytest selection' >&2
  exit 2
fi
if [[ -n "$requested_mode" ]]; then
  mode="$requested_mode"
fi

collect_only=false
for argument in "${pytest_args[@]}"; do
  if [[ "$argument" == "--collect-only" ]]; then
    collect_only=true
  fi
done

collection_args=()
collection_quiet=false
for argument in "${pytest_args[@]}"; do
  case "$argument" in
    --collect-only)
      ;;
    -q|--quiet)
      if [[ "$collection_quiet" == false ]]; then
        collection_args+=("$argument")
        collection_quiet=true
      fi
      ;;
    *)
      collection_args+=("$argument")
      ;;
  esac
done
if [[ "$collection_quiet" == false ]]; then
  collection_args+=(-q)
fi

workers="${GRAF_TEST_WORKERS:-8}"
if [[ ! "$workers" =~ ^[1-9][0-9]*$ ]] || (( workers > 8 )); then
  printf 'GRAF_TEST_WORKERS must be an integer from 1 through 8.\n' >&2
  exit 2
fi

timing_args=(--durations=20)
for argument in "${pytest_args[@]}"; do
  if [[ "$argument" == --durations || "$argument" == --durations=* ]]; then
    timing_args=()
    break
  fi
done

metadata_directory="$(mktemp -d "${TMPDIR:-/tmp}/graf-postgres-test.XXXXXX")"

collect_node_ids() {
  local destination="$1"
  shift
  PYTHONPATH=src uv run --extra dev --extra evaluation pytest --collect-only "$@" \
    | awk '/^tests\// { print }' \
    | LC_ALL=C sort -u > "$destination"
}

run_phase() {
  local phase="$1"
  shift
  local started_at
  local completed_at
  local duration_seconds
  started_at="$(date +%s)"
  if "$@"; then
    completed_at="$(date +%s)"
    duration_seconds=$((completed_at - started_at))
    printf 'postgres_test_phase=%s status=pass duration_seconds=%s\n' "$phase" "$duration_seconds"
    return 0
  else
    local phase_status=$?
    completed_at="$(date +%s)"
    duration_seconds=$((completed_at - started_at))
    printf 'postgres_test_phase=%s status=fail duration_seconds=%s\n' "$phase" "$duration_seconds" >&2
    return "$phase_status"
  fi
}

cd "$repo_root/apps/server"
export TWOBRAIN_DATABASE_URL="$test_url"
export RLS_TEST_DATABASE_URL="$rls_url"
export GRAF_TEST_DATABASE_PREFIX="$test_database"
export GRAF_TEST_POSTGRES_ADMIN_URL="$admin_url"
export GRAF_TEST_POSTGRES_MEDIA_PASSWORD="$media_password"
export RLS_TEST_MEDIA_DATABASE_URL="$rls_media_url"
export PYTHONPATH=src

if [[ "$mode" == "focused" ]]; then
  printf 'postgres_test_mode=focused worker_count=1\n'
  if run_phase focused uv run --extra dev --extra evaluation pytest "${timing_args[@]}" "${pytest_args[@]}"; then
    :
  else
    exit 1
  fi
  printf 'postgres_test_result=pass mode=focused\n'
  exit 0
fi

baseline_node_ids="$metadata_directory/baseline-nodeids.txt"
parallel_node_ids="$metadata_directory/parallel-nodeids.txt"
strict_node_ids="$metadata_directory/strict-nodeids.txt"
union_node_ids="$metadata_directory/union-nodeids.txt"
collect_node_ids "$baseline_node_ids" "${collection_args[@]}"
collect_node_ids "$parallel_node_ids" -m "not strict_rls" "${collection_args[@]}"
collect_node_ids "$strict_node_ids" -m strict_rls "${collection_args[@]}"
cat "$parallel_node_ids" "$strict_node_ids" | LC_ALL=C sort -u > "$union_node_ids"
if ! cmp -s "$baseline_node_ids" "$union_node_ids"; then
  printf 'full PostgreSQL test runner phase union does not match the same-commit collection\n' >&2
  diff -u "$baseline_node_ids" "$union_node_ids" >&2 || true
  exit 1
fi

collection_count="$(wc -l < "$baseline_node_ids" | tr -d ' ')"
collection_digest="$(shasum -a 256 "$baseline_node_ids" | awk '{ print $1 }')"
printf 'postgres_test_mode=full worker_count=%s collection_count=%s collection_digest=%s\n' \
  "$workers" "$collection_count" "$collection_digest"

if [[ "$collect_only" == true ]]; then
  printf 'postgres_test_result=pass mode=full collection_only=true\n'
  exit 0
fi

if run_phase parallel \
  uv run --extra dev --extra evaluation pytest -n "$workers" --dist=loadfile -m "not strict_rls" \
  "${timing_args[@]}" "${pytest_args[@]}"; then
  :
else
  exit 1
fi
if run_phase strict \
  uv run --extra dev --extra evaluation pytest -m strict_rls "${timing_args[@]}" "${pytest_args[@]}"; then
  :
else
  exit 1
fi
printf 'postgres_test_result=pass mode=full collection_digest=%s\n' "$collection_digest"
