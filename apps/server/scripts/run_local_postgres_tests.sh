#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
# Keep the generated name below PostgreSQL's 63-byte identifier limit after
# strict-RLS fixtures append their worker and collection digest suffix.
database_suffix="$(id -u)_$$_${RANDOM}"
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

pytest_args=()
requested_mode=""
partitioned=false
for argument in "$@"; do
  case "$argument" in
    --help|-h)
      printf 'usage: %s --fast|--full|--focused [--partitioned] [pytest arguments]\n' "$0"
      exit 0
      ;;
    --partitioned) partitioned=true ;;
    --fast|--full|--focused)
      if [[ -n "$requested_mode" && "$requested_mode" != "${argument#--}" ]]; then
        printf 'conflicting test runner modes\n' >&2
        exit 2
      fi
      requested_mode="${argument#--}"
      ;;
    *)
      pytest_args+=("$argument")
      ;;
  esac
done

if [[ "$partitioned" == true ]]; then
  [[ "$requested_mode" == focused ]] || { printf 'partitioned requires explicit --focused\n' >&2; exit 2; }
  for argument in "${pytest_args[@]}"; do
    case "$argument" in
      -n*|--numprocesses*|--dist*|--tx*|--px*|--graf-phase-file*|-f|--looponfail|-d)
        printf 'partitioned owns xdist settings; use GRAF_TEST_WORKERS\n' >&2
        exit 2
        ;;
    esac
  done
fi

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
if [[ "$requested_mode" == "fast" && "$mode" == "focused" ]]; then
  printf '%s\n' 'refusing --fast with a focused pytest selection; run the focused selection directly' >&2
  exit 2
fi
if [[ "$requested_mode" == "full" && "$mode" == "focused" ]]; then
  printf '%s\n' 'refusing --full with a focused pytest selection' >&2
  exit 2
fi
if [[ -n "$requested_mode" ]]; then
  mode="$requested_mode"
fi

collect_only=false
for argument in "${pytest_args[@]}"; do
  if [[ "$argument" == "--collect-only" || "$argument" == "--co" ]]; then
    collect_only=true
  fi
done

workers="${GRAF_TEST_WORKERS:-4}"
if [[ ! "$workers" =~ ^[1-9][0-9]*$ ]] || (( workers > 8 )); then
  printf 'GRAF_TEST_WORKERS must be an integer from 1 through 8.\n' >&2
  exit 2
fi

if [[ "$mode" == fast || "$partitioned" == true ]] && (( workers > 4 )); then workers=4; fi

performance_gate="${GRAF_PERFORMANCE_GATE:-report}"
if [[ "$performance_gate" != "report" && "$performance_gate" != "required" ]]; then
  printf 'GRAF_PERFORMANCE_GATE must be report or required.\n' >&2
  exit 2
fi
export GRAF_PERFORMANCE_GATE="$performance_gate"
if [[ "$mode" == "fast" && "$performance_gate" == "required" ]]; then
  printf 'refusing --fast with GRAF_PERFORMANCE_GATE=required; use --full\n' >&2
  exit 2
fi

timing_args=(--durations=20)
for argument in "${pytest_args[@]}"; do
  if [[ "$argument" == --durations || "$argument" == --durations=* ]]; then
    timing_args=()
    break
  fi
done

run_phase() {
  local phase="$1"
  shift
  local started_at
  local completed_at
  local duration_seconds
  started_at="$(date +%s)"
  local report_args=(-c "$repo_root/apps/server/pyproject.toml")
  if [[ -n "${GRAF_TEST_REPORT_DIR:-}" ]]; then
    mkdir -p "$GRAF_TEST_REPORT_DIR"
    report_args+=(-p tests.fixtures.test_resources --graf-report-file "$GRAF_TEST_REPORT_DIR/$phase.jsonl")
  fi
  if uv run --extra dev --extra evaluation pytest "${report_args[@]}" "$@"; then
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

start_postgres() {
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
        # `pg_isready` can succeed against the temporary post-init server before
        # the entrypoint starts the final postmaster. Wait for the stable marker
        # first so the database creation below cannot race that shutdown.
        if docker logs "$postgres_container" 2>&1 \
          | grep -q "PostgreSQL init process complete; ready for start up." \
          && docker exec "$postgres_container" \
            pg_isready --username=twobrain_rec --dbname=postgres >/dev/null 2>&1; then
          postgres_ready=true
          break
        fi
        sleep 0.25
      done
    fi
    if [[ "$postgres_ready" == true ]]; then
      # pg_isready can report the socket during the short initdb handoff while
      # PostgreSQL is still shutting down its bootstrap server. Retry the actual
      # DDL probe before discarding an otherwise healthy disposable container.
      for _db_attempt in {1..20}; do
        if docker exec "$postgres_container" \
          psql --set=ON_ERROR_STOP=1 --username=twobrain_rec --dbname=postgres \
          --command "create database \"${rls_database}\"" >/dev/null; then
          postgres_initialized=true
          break 2
        fi
        sleep 0.25
      done
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

  export TWOBRAIN_DATABASE_URL="$test_url"
  export RLS_TEST_DATABASE_URL="$rls_url"
  export GRAF_TEST_DATABASE_PREFIX="$test_database"
  export GRAF_TEST_POSTGRES_ADMIN_URL="$admin_url"
  export GRAF_TEST_POSTGRES_MEDIA_PASSWORD="$media_password"
  export RLS_TEST_MEDIA_DATABASE_URL="$rls_media_url"

}

cd "$repo_root/apps/server"
export PYTHONPATH="$repo_root/apps/server:$repo_root/apps/server/src" UV_FROZEN=1
# A nested runner is an independent pytest process. Do not inherit the parent
# xdist worker identity; its own parallel phase will receive fresh worker IDs.
unset PYTEST_XDIST_WORKER PYTEST_XDIST_TESTRUNUID PYTEST_XDIST_WORKER_COUNT
# Collection and pure tests must never inherit an operator database target.
unset TWOBRAIN_DATABASE_URL RLS_TEST_DATABASE_URL RLS_TEST_PROBE_DATABASE_URL \
  RLS_TEST_MEDIA_DATABASE_URL GRAF_TEST_DATABASE_PREFIX GRAF_TEST_POSTGRES_ADMIN_URL \
  GRAF_TEST_POSTGRES_MEDIA_PASSWORD
metadata_directory="$(mktemp -d "${TMPDIR:-/tmp}/graf-postgres-test.XXXXXX")"
selection=("${pytest_args[@]}")
if [[ "$mode" == fast ]]; then selection=(-q tests/unit); fi
collection_args=()
if [[ "$partitioned" == true ]]; then
  collection_args=(-p tests.fixtures.test_resources --graf-partition-preflight)
fi
if uv run --extra dev --extra evaluation pytest -c "$repo_root/apps/server/pyproject.toml" --collect-only \
  "${collection_args[@]}" --graf-collection-file "$metadata_directory/collection.json" "${selection[@]}" \
  > "$metadata_directory/collection.log" 2>&1; then
  :
else
  collection_status=$?
  cat "$metadata_directory/collection.log" >&2
  exit "$collection_status"
fi
python3 - "$metadata_directory" "$partitioned" <<'PY_INVENTORY'
import json
import pathlib
import sys
root = pathlib.Path(sys.argv[1])
groups = json.loads((root / "collection.json").read_text())
baseline = groups["baseline"]
if not baseline or len(set(baseline)) != len(baseline):
    raise SystemExit("empty or repeated baseline test collection")
for names in (("parallel", "performance", "strict"), ("pure", "resource")):
    combined = [node for name in names for node in groups[name]]
    if len(set(combined)) != len(combined) or set(combined) != set(baseline):
        raise SystemExit("test phase union is missing or repeats cases")
for name, nodes in groups.items():
    (root / f"{name}-count").write_text(str(len(nodes)))
if sys.argv[2] == "true":
    for name in ("parallel", "performance", "strict"):
        (root / f"{name}.json").write_text(json.dumps({"phase": name, "nodeids": groups[name]}))
(root / "baseline-nodeids.txt").write_text("\n".join(sorted(baseline)) + "\n")
PY_INVENTORY
collection_count="$(cat "$metadata_directory/baseline-count")"
collection_digest="$(shasum -a 256 "$metadata_directory/baseline-nodeids.txt" | awk '{ print $1 }')"
printf 'postgres_test_mode=%s worker_count=%s collection_count=%s collection_digest=%s\n' \
  "$mode" "$workers" "$collection_count" "$collection_digest"
if [[ "$collect_only" == true ]]; then
  cat "$metadata_directory/collection.log"
  printf 'postgres_test_result=inventory_only mode=%s collection_only=true\n' "$mode"
  exit 0
fi

if [[ "$mode" == fast ]]; then
  # Fail cheap pure tests before allocating PostgreSQL. The two sets partition unit.
  if (( $(cat "$metadata_directory/pure-count") > 0 )); then
    run_phase pure -q -n "$workers" --dist=loadfile \
      -m 'not postgres and not browser' tests/unit "${timing_args[@]}"
  fi
  if (( $(cat "$metadata_directory/resource-count") > 0 )); then
    start_postgres
    run_phase fast -q -n "$workers" --dist=loadfile \
      -m 'postgres or browser' tests/unit "${timing_args[@]}"
  fi
  printf 'postgres_test_result=pass mode=fast\n'
  exit 0
fi

if [[ "$mode" == focused ]]; then
  # Only the inspected unit resource contract can authorize a no-DB focused path.
  if (( $(cat "$metadata_directory/resource-count") > 0 )) \
    || ! python3 - "$metadata_directory/collection.json" <<'PY_PURE'
import json, sys
raise SystemExit(not all(node.startswith("tests/unit/") for node in json.load(open(sys.argv[1]))["baseline"]))
PY_PURE
  then
    start_postgres
  fi
  if [[ "$partitioned" == true ]]; then
    for phase in parallel performance strict; do
      (( $(cat "$metadata_directory/$phase-count") > 0 )) || continue
      phase_workers=0
      [[ "$phase" != parallel ]] || phase_workers="$workers"
      run_phase "focused-$phase" \
        --graf-phase-file "$metadata_directory/$phase.json" -n "$phase_workers" --dist=loadfile \
        "${timing_args[@]}" "${pytest_args[@]}"
    done
  else
    run_phase focused "${timing_args[@]}" "${pytest_args[@]}"
  fi
  printf 'postgres_test_result=pass mode=focused partitioned=%s\n' "$partitioned"
  exit 0
fi

start_postgres
if run_phase strict \
  -m strict_rls "${timing_args[@]}" "${pytest_args[@]}"; then
  :
else
  exit 1
fi
if run_phase performance \
  -m "serial_performance and not strict_rls" \
  "${timing_args[@]}" "${pytest_args[@]}"; then
  :
else
  printf 'postgres_test_performance_gate=%s result=fail\n' "$performance_gate" >&2
  exit 1
fi
if run_phase parallel \
  -n "$workers" --dist=loadfile \
  -m "not strict_rls and not serial_performance" \
  "${timing_args[@]}" "${pytest_args[@]}"; then
  :
else
  exit 1
fi
printf 'postgres_test_result=pass mode=full collection_digest=%s\n' "$collection_digest"
