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
result_marker=""
minio_container="graf-minio-test-${database_suffix//_/-}"
minio_attempted=false
minio_owner=""
postgres_resource_directory="${GRAF_TEST_POSTGRES_RESOURCE_DIR:-}"
resource_context=false
resource_run_token=""
resource_image_id=""
resource_container_id=""
resource_manifest=""
resource_cid_file=""
resource_state_file=""
resource_attempted=false
resource_bootstrap_started_ms=""

if [[ ! "$test_database" =~ ^twobrain_rec_test_[a-z0-9_]+$ ]] \
  || [[ ! "$rls_database" =~ ^twobrain_rec_test_[a-z0-9_]+$ ]]; then
  printf 'refusing unsafe generated PostgreSQL test database name\n' >&2
  exit 2
fi

resource_state_write() {
  local phase="$1"
  local container_id="${2:-}"
  local started_ms="${3:-}"
  local temporary="$resource_state_file.tmp.$$"
  python3 - "$resource_state_file" "$temporary" "$phase" "$container_id" "$resource_run_token" "$started_ms" <<'PY_STATE'
import json
import os
import sys
import time

path, temporary, phase, container_id, token, started_ms = sys.argv[1:7]
now_ms = int(time.monotonic() * 1000)
payload = {
    "schema_version": 1,
    "phase": phase,
    "run_token": token,
    "container_id": container_id or None,
    "started_ms": int(started_ms) if started_ms else now_ms,
    "monotonic_ms": now_ms,
}
descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, "w", encoding="utf-8") as output:
    json.dump(payload, output, sort_keys=True, separators=(",", ":"))
    output.write("\n")
os.replace(temporary, path)
PY_STATE
}

remove_resource_handoff_files() {
  if [[ -f "$resource_cid_file" && ! -L "$resource_cid_file" ]]; then
    rm -f "$resource_cid_file"
  fi
  if [[ -n "$resource_state_file" && -f "$resource_state_file" && ! -L "$resource_state_file" ]]; then
    resource_state_write removed "" "$resource_bootstrap_started_ms"
  fi
}

container_identity() {
  docker inspect --format '{{.Id}}|{{.Name}}|{{index .Config.Labels "pro.2brain.graf.f099.run"}}|{{.Image}}' "$1" 2>/dev/null
}

remove_verified_container() {
  # Removes only the caller-owned container. An empty result is not proof of
  # absence: only a successful exact-name lookup may establish that.
  local candidate_id="${1:-}"
  local identity=""
  local ids=""
  local actual_id=""
  local actual_name=""
  local actual_token=""
  local actual_image=""
  if [[ -n "$candidate_id" ]]; then
    identity="$(container_identity "$candidate_id")" || identity=""
  fi
  if [[ -z "$identity" ]]; then
    if ! ids="$(docker ps -aq --no-trunc --filter "name=^/${postgres_container}$")"; then
      printf 'postgres_test_resource_cleanup=lookup_failed\n' >&2
      return 1
    fi
    if [[ -z "$ids" ]]; then
      remove_resource_handoff_files
      printf 'postgres_test_resource_cleanup=confirmed_absent\n'
      return 0
    fi
    if [[ "$(printf '%s\n' "$ids" | wc -l | tr -d ' ')" != "1" ]]; then
      printf 'postgres_test_resource_cleanup=ambiguous_lookup\n' >&2
      return 1
    fi
    candidate_id="$ids"
    identity="$(container_identity "$candidate_id")" || identity=""
  fi
  if [[ -z "$identity" ]]; then
    printf 'postgres_test_resource_cleanup=identity_unreadable\n' >&2
    return 1
  fi
  IFS='|' read -r actual_id actual_name actual_token actual_image <<< "$identity"
  if [[ "$actual_name" != "/$postgres_container" \
    || "$actual_token" != "$resource_run_token" \
    || "$actual_image" != "$resource_image_id" ]]; then
    printf 'postgres_test_resource_cleanup=foreign_or_mismatched_container\n' >&2
    return 1
  fi
  if ! docker rm --force --volumes "$actual_id" >/dev/null 2>&1; then
    printf 'postgres_test_resource_cleanup=remove_failed\n' >&2
    return 1
  fi
  if container_identity "$actual_id" >/dev/null 2>&1; then
    printf 'postgres_test_resource_cleanup=still_present_after_remove\n' >&2
    return 1
  fi
  if ! ids="$(docker ps -aq --no-trunc --filter "name=^/${postgres_container}$")"; then
    printf 'postgres_test_resource_cleanup=absence_lookup_failed\n' >&2
    return 1
  fi
  if [[ -n "$ids" ]]; then
    printf 'postgres_test_resource_cleanup=name_still_present\n' >&2
    return 1
  fi
  remove_resource_handoff_files
  printf 'postgres_test_resource_cleanup=removed\n'
  return 0
}

cleanup() {
  local exit_status=$?
  local minio_cleanup_proven=true
  trap - EXIT INT TERM
  if [[ "$minio_attempted" == true ]]; then
    minio_cleanup_proven=false
    local minio_identity minio_id remaining
    if minio_identity="$(docker inspect --format '{{.Id}} {{index .Config.Labels "graf.test.minio-owner"}}' "$minio_container" 2>/dev/null)"; then
      minio_id="${minio_identity%% *}"
      if [[ "$minio_id" =~ ^[0-9a-f]{64}$ && "$minio_identity" == "$minio_id $minio_owner" ]] \
        && docker rm --force --volumes "$minio_id" >/dev/null 2>&1; then
        minio_cleanup_proven=true
        printf 'minio_test_cleanup=isolated_container_removed\n'
      else
        printf 'minio_test_cleanup=ownership_or_remove_failed\n' >&2
        if (( exit_status == 0 )); then exit_status=1; fi
      fi
    elif remaining="$(docker ps --all --quiet --no-trunc --filter "name=^/${minio_container}$" 2>/dev/null)" \
      && [[ -z "$remaining" ]]; then
      minio_cleanup_proven=true
      printf 'minio_test_cleanup=container_absent\n'
    else
      printf 'minio_test_cleanup=identity_unknown\n' >&2
      if (( exit_status == 0 )); then exit_status=1; fi
    fi
  fi
  if [[ "$resource_context" == true ]]; then
    if [[ "$resource_attempted" == true && "$collect_only" != true ]]; then
      if ! remove_verified_container "$resource_container_id"; then
        if (( exit_status == 0 )); then exit_status=1; fi
      fi
    else
      printf 'postgres_test_resource_cleanup=not_started\n'
    fi
  elif [[ "$container_started" == true ]]; then
    if docker rm --force --volumes "$postgres_container" >/dev/null 2>&1; then
      printf 'postgres_test_cleanup=isolated_container_removed\n'
    else
      printf 'postgres_test_cleanup=isolated_container_remove_failed\n' >&2
      if (( exit_status == 0 )); then exit_status=1; fi
    fi
  else
    printf 'postgres_test_cleanup=container_not_started\n'
  fi
  if [[ -n "$metadata_directory" ]]; then
    if [[ "$minio_cleanup_proven" == true ]]; then
      rm -rf "$metadata_directory"
    else
      printf 'minio_test_temp_retained=%s\n' "$metadata_directory" >&2
    fi
  fi
  if (( exit_status == 0 )) && [[ -n "$result_marker" ]]; then
    printf '%s\n' "$result_marker"
  fi
  exit "$exit_status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

pytest_args=()
requested_mode=""
partitioned=false
phases_given=false
phases_spec=""
shard_spec=""
while (( $# > 0 )); do
  argument="$1"
  shift
  case "$argument" in
    --help|-h)
      printf 'usage: %s --fast|--full|--focused [--partitioned] [--phases parallel,performance,strict] [--shard index/total] [pytest arguments]\n' "$0"
      exit 0
      ;;
    --partitioned) partitioned=true ;;
    --phases)
      (( $# > 0 )) || { printf '%s\n' '--phases requires a comma-separated phase list' >&2; exit 2; }
      phases_given=true
      phases_spec="$1"
      shift
      ;;
    --phases=*)
      phases_given=true
      phases_spec="${argument#--phases=}"
      ;;
    --shard)
      (( $# > 0 )) || { printf '%s\n' '--shard requires an index/total value such as 2/4' >&2; exit 2; }
      shard_spec="$1"
      shift
      ;;
    --shard=*) shard_spec="${argument#--shard=}" ;;
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
      -n*|--numprocesses*|--dist*|--tx*|--px*|--graf-phase-file*|--graf-phase-shard*|-f|--looponfail|-d)
        printf 'partitioned owns xdist settings; use GRAF_TEST_WORKERS\n' >&2
        exit 2
        ;;
    esac
  done
fi

# Selected phases default to the complete Full partition; the release pipeline
# splits them across jobs so the short serial phases do not queue behind parallel.
selected_phases=(parallel performance strict)
if [[ "$phases_given" == true ]]; then
  [[ "$partitioned" == true && "$requested_mode" == focused ]] \
    || { printf '%s\n' '--phases requires --focused --partitioned' >&2; exit 2; }
  [[ -n "$phases_spec" ]] \
    || { printf '%s\n' '--phases requires a non-empty comma-separated phase list' >&2; exit 2; }
  [[ "$phases_spec" =~ ^[a-z]+(,[a-z]+)*$ ]] \
    || { printf 'invalid --phases %q; expected a comma-separated phase list\n' "$phases_spec" >&2; exit 2; }
  selected_phases=()
  IFS=',' read -r -a requested_phases <<< "$phases_spec"
  for phase in "${requested_phases[@]}"; do
    case "$phase" in
      parallel|performance|strict) ;;
      *)
        printf 'unknown test phase %q; expected parallel, performance or strict\n' "$phase" >&2
        exit 2
        ;;
    esac
    for known_phase in ${selected_phases[@]+"${selected_phases[@]}"}; do
      [[ "$known_phase" != "$phase" ]] || { printf 'repeated test phase %s\n' "$phase" >&2; exit 2; }
    done
    selected_phases+=("$phase")
  done
fi

shard_index=""
shard_total=""
if [[ -n "$shard_spec" ]]; then
  [[ "$partitioned" == true && "$requested_mode" == focused ]] \
    || { printf '%s\n' '--shard requires --focused --partitioned' >&2; exit 2; }
  [[ "$shard_spec" =~ ^([0-9]+)/([0-9]+)$ ]] \
    || { printf 'invalid --shard %q; expected index/total such as 2/4\n' "$shard_spec" >&2; exit 2; }
  shard_index="$((10#${BASH_REMATCH[1]}))"
  shard_total="$((10#${BASH_REMATCH[2]}))"
  if (( shard_total < 2 )) || (( shard_index < 0 )) || (( shard_index >= shard_total )); then
    printf 'invalid --shard %s; index must be 0-based and below total with total >= 2\n' "$shard_spec" >&2
    exit 2
  fi
  # A part covers exactly one slice of the parallel phase, so this run must not
  # claim the serial phases as well: those stay in the dedicated phases job.
  if [[ "$phases_spec" != parallel ]]; then
    printf 'postgres_test_shard_forced_phases=parallel\n'
  fi
  selected_phases=(parallel)
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

validate_postgres_resource_context() {
  if [[ -z "$postgres_resource_directory" ]]; then
    return 0
  fi
  if [[ "$requested_mode" != "focused" ]]; then
    printf 'GRAF_TEST_POSTGRES_RESOURCE_DIR requires explicit --focused\n' >&2
    exit 2
  fi
  local output
  if ! output="$(python3 - "$postgres_resource_directory" <<'PY_RESOURCE'
import json
import os
import stat
import sys

root = sys.argv[1]
if not os.path.isabs(root):
    raise SystemExit("resource directory must be an absolute path")
metadata = os.lstat(root)
if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
    raise SystemExit("resource directory must be a real directory")
if metadata.st_mode & 0o077:
    raise SystemExit("resource directory mode must be 0700")
if metadata.st_uid != os.geteuid():
    raise SystemExit("resource directory owner is invalid")

manifest_path = os.path.join(root, "postgres-resource.json")
manifest_metadata = os.lstat(manifest_path)
if not stat.S_ISREG(manifest_metadata.st_mode) or stat.S_ISLNK(manifest_metadata.st_mode):
    raise SystemExit("resource manifest must be a regular non-symlink file")
if manifest_metadata.st_mode & 0o177:
    raise SystemExit("resource manifest mode must be 0600")
if manifest_metadata.st_uid != os.geteuid():
    raise SystemExit("resource manifest owner is invalid")
if manifest_metadata.st_size > 4096:
    raise SystemExit("resource manifest is too large")
with open(manifest_path, "r", encoding="utf-8") as source:
    document = json.load(source)
if not isinstance(document, dict) or set(document) != {
    "schema_version",
    "run_token",
    "container_name",
    "image_id",
}:
    raise SystemExit("resource manifest must contain exactly schema_version, run_token, container_name, image_id")
if type(document["schema_version"]) is not int or document["schema_version"] != 1:
    raise SystemExit("resource manifest schema_version must be 1")
token = document["run_token"]
if not isinstance(token, str) or len(token) != 32 or any(ch not in "0123456789abcdef" for ch in token):
    raise SystemExit("resource manifest run_token must be 32 lowercase hex characters")
expected_name = "graf-postgres-test-f099-" + token
if document["container_name"] != expected_name:
    raise SystemExit("resource manifest container_name does not match its run_token")
image_id = document["image_id"]
if (
    not isinstance(image_id, str)
    or not image_id.startswith("sha256:")
    or len(image_id) != 71
    or any(ch not in "0123456789abcdef" for ch in image_id[7:])
):
    raise SystemExit("resource manifest image_id must be a sha256 image ID")
print(token)
print(image_id)
print(expected_name)
PY_RESOURCE
  )"; then
    printf 'invalid GRAF_TEST_POSTGRES_RESOURCE_DIR context; refusing to start\n' >&2
    exit 2
  fi
  resource_run_token="$(sed -n '1p' <<< "$output")"
  resource_image_id="$(sed -n '2p' <<< "$output")"
  resource_container_name="$(sed -n '3p' <<< "$output")"
  postgres_container="$resource_container_name"
  resource_manifest="$postgres_resource_directory/postgres-resource.json"
  resource_cid_file="$postgres_resource_directory/postgres.cid"
  resource_state_file="$postgres_resource_directory/postgres-state.json"
  resource_context=true
}

validate_postgres_resource_context

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
  # The resource plugin owns --graf-phase-file/--graf-phase-shard and the
  # resource markers, so every phase must load it before argument parsing; it
  # is also what lets a phase run work without a timing report directory.
  local report_args=(-c "$repo_root/apps/server/pyproject.toml" -p tests.fixtures.test_resources)
  if [[ -n "${GRAF_TEST_REPORT_DIR:-}" ]]; then
    mkdir -p "$GRAF_TEST_REPORT_DIR"
    report_args+=(--graf-report-file "$GRAF_TEST_REPORT_DIR/$phase.jsonl")
  fi
  local uv_run=("run")
  if [[ "$resource_context" == true ]]; then
    uv_run+=(--no-sync)
  fi
  if uv "${uv_run[@]}" --extra dev --extra evaluation pytest "${report_args[@]}" "$@"; then
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

start_minio() {
  local release='RELEASE.2025-05-24T17-08-30Z'
  local image_id arch binary_sha binary_bytes binary endpoint access secret ready=false
  image_id="$(docker inspect --format '{{.Image}}' "$postgres_container")"
  [[ "$image_id" =~ ^sha256:[0-9a-f]{64}$ ]] || { printf 'Invalid disposable PostgreSQL image ID.\n' >&2; exit 1; }
  arch="$(docker image inspect --format '{{.Architecture}}' "$image_id")"
  case "$arch" in
    amd64)
      binary_sha='fe8b37f38487b6caf758a71d6669a8c42a9a3ec88e7381cc24a39f067b0fa4c9'
      binary_bytes=110756024 ;;
    arm64)
      binary_sha='1fdf97b30dbe10e13db00f1c405bf16935d7e1d530b537b4ebd2ed941457280c'
      binary_bytes=104988856 ;;
    *) printf 'Unsupported disposable PostgreSQL image architecture.\n' >&2; exit 1 ;;
  esac
  binary="$(cd "$metadata_directory" && pwd -P)/minio"
  curl --disable --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
    --connect-timeout 10 --max-time 120 --max-filesize "$binary_bytes" --output "$binary" \
    "https://github.com/minio/minio/releases/download/$release/minio.linux-$arch.$release"
  if [[ "$(wc -c < "$binary" | awk '{ print $1 }')" != "$binary_bytes" ]] \
    || [[ "$(shasum -a 256 "$binary" | awk '{ print $1 }')" != "$binary_sha" ]]; then
    printf 'Disposable MinIO binary size or SHA256 mismatch.\n' >&2
    exit 1
  fi
  chmod 0555 "$binary"
  minio_owner="$(openssl rand -hex 16)"
  access="$(openssl rand -hex 16)"
  secret="$(openssl rand -hex 24)"
  if [[ ! "$minio_owner" =~ ^[a-f0-9]{32}$ || ! "$access" =~ ^[a-f0-9]{32}$ || ! "$secret" =~ ^[a-f0-9]{48}$ ]]; then
    printf 'Unable to generate disposable MinIO credentials.\n' >&2
    exit 1
  fi
  # Set ownership before run: a failed client call can still have created a container.
  minio_attempted=true
  if ! MINIO_ROOT_USER="$access" MINIO_ROOT_PASSWORD="$secret" \
    docker run --detach --rm --name "$minio_container" --label "graf.test.minio-owner=$minio_owner" \
      --publish 127.0.0.1::9000 --tmpfs /data:rw,size=256m \
      --entrypoint /graf-test-minio --mount "type=bind,source=$binary,target=/graf-test-minio,readonly" \
      --env MINIO_ROOT_USER --env MINIO_ROOT_PASSWORD --pull=never "$image_id" server /data >/dev/null 2>&1; then
    printf 'Disposable MinIO container start failed.\n' >&2
    exit 1
  fi
  endpoint="$(docker port "$minio_container" 9000/tcp)"
  if [[ ! "$endpoint" =~ ^127\.0\.0\.1:([0-9]{1,5})$ ]] \
    || (( 10#${BASH_REMATCH[1]} < 1 || 10#${BASH_REMATCH[1]} > 65535 )); then
    printf 'Disposable MinIO did not expose a safe loopback port.\n' >&2
    exit 1
  fi
  for _attempt in {1..60}; do
    if curl --disable --fail --silent --noproxy '*' --connect-timeout 1 --max-time 1 \
      "http://$endpoint/minio/health/ready" >/dev/null 2>&1; then
      ready=true
      break
    fi
    sleep 0.25
  done
  [[ "$ready" == true ]] || { printf 'Disposable MinIO did not become ready.\n' >&2; exit 1; }
  export GRAF_TEST_STRICT_MINIO_ENDPOINT="$endpoint"
  export GRAF_TEST_STRICT_MINIO_ACCESS="$access"
  export GRAF_TEST_STRICT_MINIO_SECRET="$secret"
  printf 'minio_test_ready=true release=%s binary_sha256=%s image_id=%s\n' "$release" "$binary_sha" "$image_id"
}

start_postgres_resource() {
  if ! docker info >/dev/null 2>&1; then
    printf 'Docker Engine is unavailable. Start Docker Desktop, wait until it is ready, then retry.\n' >&2
    exit 1
  fi
  local image_actual
  if ! image_actual="$(docker image inspect --format '{{.Id}}' "$resource_image_id" 2>/dev/null)"; then
    printf 'Admitted PostgreSQL image ID is unavailable locally.\n' >&2
    exit 1
  fi
  if [[ "$image_actual" != "$resource_image_id" ]]; then
    printf 'Admitted PostgreSQL image ID does not match the local image.\n' >&2
    exit 1
  fi
  if [[ -e "$resource_cid_file" || -L "$resource_cid_file" || -e "$resource_state_file" || -L "$resource_state_file" ]]; then
    printf 'PostgreSQL resource handoff already exists; refusing to create.\n' >&2
    exit 1
  fi
  resource_attempted=true
  resource_bootstrap_started_ms="$(python3 -c 'import time; print(int(time.monotonic() * 1000))')"
  resource_state_write starting "" "$resource_bootstrap_started_ms"
  local bootstrap_deadline=$((SECONDS + 60))

  postgres_initialized=false
  for start_attempt in 1 2; do
    if (( SECONDS >= bootstrap_deadline )); then
      printf 'postgres_test_bootstrap_timeout=1\n' >&2
      break
    fi
    postgres_ready=false
    if docker run --detach --rm --pull=never --name "$resource_container_name" \
      --label "pro.2brain.graf.f099.run=$resource_run_token" \
      --cidfile "$resource_cid_file" \
      --env POSTGRES_DB=postgres \
      --env POSTGRES_USER=twobrain_rec \
      --env POSTGRES_PASSWORD=twobrain_rec \
      --tmpfs /var/lib/postgresql/data:rw \
      --publish 127.0.0.1::5432 \
      "$resource_image_id" >/dev/null; then
      :
    fi
    local identity=""
    identity="$(container_identity "$resource_container_name")" || identity=""
    if [[ -n "$identity" ]]; then
      local actual_id="" actual_name="" actual_token="" actual_image=""
      IFS='|' read -r actual_id actual_name actual_token actual_image <<< "$identity"
      if [[ "$actual_name" != "/$resource_container_name" \
        || "$actual_token" != "$resource_run_token" \
        || "$actual_image" != "$resource_image_id" ]]; then
        printf 'PostgreSQL container identity does not match the admitted resource.\n' >&2
        exit 1
      fi
      resource_container_id="$actual_id"
      container_started=true
    else
      container_started=false
      if ! remove_verified_container ""; then
        printf 'postgres_test_container_identity_unreadable=1\n' >&2
        exit 1
      fi
    fi
    if [[ "$container_started" == true ]]; then
      for _attempt in {1..240}; do
        if (( SECONDS >= bootstrap_deadline )); then
          printf 'postgres_test_bootstrap_timeout=1\n' >&2
          break
        fi
        if docker logs "$resource_container_name" 2>&1 \
          | grep -q "PostgreSQL init process complete; ready for start up." \
          && docker exec "$resource_container_name" \
            pg_isready --username=twobrain_rec --dbname=postgres >/dev/null 2>&1; then
          postgres_ready=true
          break
        fi
        sleep 0.25
      done
    fi
    if [[ "$postgres_ready" == true ]]; then
      # Re-prove ownership immediately before the first SQL statement.
      identity="$(container_identity "$resource_container_id")" || identity=""
      IFS='|' read -r actual_id actual_name actual_token actual_image <<< "$identity"
      if [[ -z "$identity" \
        || "$actual_id" != "$resource_container_id" \
        || "$actual_name" != "/$resource_container_name" \
        || "$actual_token" != "$resource_run_token" \
        || "$actual_image" != "$resource_image_id" ]]; then
        printf 'PostgreSQL container identity changed before the first SQL statement.\n' >&2
        exit 1
      fi
      for _db_attempt in {1..20}; do
        if docker exec "$resource_container_id" \
          psql --set=ON_ERROR_STOP=1 --username=twobrain_rec --dbname=postgres \
          --command "create database \"${rls_database}\"" >/dev/null; then
          postgres_initialized=true
          break 2
        fi
        sleep 0.25
      done
    fi
    if [[ "$container_started" == true ]]; then
      if ! remove_verified_container "$resource_container_id"; then
        printf 'postgres_test_container_start_cleanup=failed\n' >&2
        exit 1
      fi
      resource_container_id=""
      container_started=false
      resource_state_write starting "" "$resource_bootstrap_started_ms"
    fi
    if (( start_attempt < 2 )); then
      printf 'postgres_test_container_start_retry=1\n' >&2
    fi
  done
  if [[ "$postgres_initialized" != true ]]; then
    printf 'Disposable PostgreSQL test container did not become ready.\n' >&2
    exit 1
  fi

  postgres_port="$(docker port "$resource_container_id" 5432/tcp | awk -F: 'NR == 1 { print $NF }')"
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
  resource_state_write ready "$resource_container_id" "$resource_bootstrap_started_ms"
}

start_postgres() {
  if [[ "$resource_context" == true ]]; then
    start_postgres_resource
    return 0
  fi
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
      if ! docker rm --force --volumes "$postgres_container" >/dev/null 2>&1; then
        printf 'postgres_test_container_start_cleanup=failed\n' >&2
        exit 1
      fi
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
# Never collect or execute against an inherited operator object store.
unset GRAF_TEST_STRICT_MINIO_ENDPOINT GRAF_TEST_STRICT_MINIO_ACCESS GRAF_TEST_STRICT_MINIO_SECRET
metadata_directory="$(mktemp -d "${TMPDIR:-/tmp}/graf-postgres-test.XXXXXX")"
selection=("${pytest_args[@]}")
if [[ "$mode" == fast ]]; then selection=(-q tests/unit); fi
collection_args=()
if [[ "$partitioned" == true || "$resource_context" == true ]]; then
  collection_args=(-p tests.fixtures.test_resources)
fi
if [[ "$partitioned" == true ]]; then
  collection_args+=(--graf-partition-preflight)
fi
uv_collection=(run)
if [[ "$resource_context" == true ]]; then
  uv_collection+=(--no-sync)
fi
if uv "${uv_collection[@]}" --extra dev --extra evaluation pytest -c "$repo_root/apps/server/pyproject.toml" --collect-only \
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

if [[ -n "$shard_spec" ]]; then
  # Полный список фазы parallel сохраняем до нарезки: по нему агрегирующая
  # задача доказывает, что части покрывают весь набор без пропусков и повторов.
  python3 - "$metadata_directory" "$shard_spec" <<'PY_SHARD'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
index, total = (int(part) for part in sys.argv[2].split("/"))
path = root / "parallel.json"
nodeids = sorted(json.loads(path.read_text(encoding="utf-8"))["nodeids"])
(root / "parallel-full-nodeids.txt").write_text("\n".join(nodeids) + "\n", encoding="utf-8")
slice_nodes = nodeids[index::total]
if not slice_nodes:
    raise SystemExit(f"shard {index}/{total} selected no cases")
path.write_text(json.dumps({"phase": "parallel", "nodeids": slice_nodes}), encoding="utf-8")
(root / "parallel-count").write_text(str(len(slice_nodes)), encoding="utf-8")
(root / "shard-nodeids.txt").write_text("\n".join(slice_nodes) + "\n", encoding="utf-8")
print(f"postgres_test_shard={index}/{total} shard_count={len(slice_nodes)} parallel_count={len(nodeids)}")
PY_SHARD
  if [[ -n "${GRAF_TEST_REPORT_DIR:-}" ]]; then
    # Publish the coverage evidence outside the disposable metadata directory so
    # the release job can upload it next to its component result.
    mkdir -p "$GRAF_TEST_REPORT_DIR"
    cp "$metadata_directory/parallel-full-nodeids.txt" \
      "$GRAF_TEST_REPORT_DIR/parallel-full-nodeids-$shard_index.txt"
    cp "$metadata_directory/shard-nodeids.txt" \
      "$GRAF_TEST_REPORT_DIR/shard-nodeids-$shard_index.txt"
  fi
fi
collection_count="$(cat "$metadata_directory/baseline-count")"
collection_digest="$(shasum -a 256 "$metadata_directory/baseline-nodeids.txt" | awk '{ print $1 }')"
printf 'postgres_test_mode=%s worker_count=%s collection_count=%s collection_digest=%s\n' \
  "$mode" "$workers" "$collection_count" "$collection_digest"
if [[ "$collect_only" == true ]]; then
  cat "$metadata_directory/collection.log"
  printf 'postgres_test_result=inventory_only mode=%s collection_only=true\n' "$mode"
  exit 0
fi

minio_required="$(python3 - "$metadata_directory" "$partitioned" "${selected_phases[@]}" <<'PY_MINIO'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
if sys.argv[2] == "true":
    nodes = [node for phase in sys.argv[3:]
             for node in json.loads((root / f"{phase}.json").read_text())["nodeids"]]
else:
    nodes = json.loads((root / "collection.json").read_text())["baseline"]
calendar = "tests/integration/test_calendar_auto_context_match.py::test_strict_track_assembly_real_minio_and_calendar_owner"
cleanup = "tests/integration/test_smoke_cleanup_deadlock.py::test_interrupted_smoke_retains_unconfirmed_object_intent_and_preserves_neighbor[real-minio]"
print("true" if any(node.split("[", 1)[0] == calendar or node == cleanup for node in nodes) else "false")
PY_MINIO
)"
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
  result_marker="postgres_test_result=pass mode=fast"
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
  if [[ "$minio_required" == true ]]; then start_minio; fi
  if [[ "$partitioned" == true ]]; then
    for phase in "${selected_phases[@]}"; do
      (( $(cat "$metadata_directory/$phase-count") > 0 )) || continue
      phase_workers=0
      [[ "$phase" != parallel ]] || phase_workers="$workers"
      phase_shard_args=()
      if [[ "$phase" == parallel && -n "$shard_spec" ]]; then
        # The part declares itself so the phase selector can prove that the
        # executed slice is exactly nodeids[index::total] of this collection.
        phase_shard_args=(--graf-phase-shard "$shard_index/$shard_total")
      fi
      run_phase "focused-$phase" \
        --graf-phase-file "$metadata_directory/$phase.json" \
        ${phase_shard_args[@]+"${phase_shard_args[@]}"} \
        -n "$phase_workers" --dist=loadfile \
        "${timing_args[@]}" "${pytest_args[@]}"
    done
  else
    run_phase focused "${timing_args[@]}" "${pytest_args[@]}"
  fi
  printf -v result_marker 'postgres_test_result=pass mode=focused partitioned=%s shard=%s' \
    "$partitioned" "${shard_spec:-none}"
  exit 0
fi

start_postgres
if [[ "$minio_required" == true ]]; then start_minio; fi
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
printf -v result_marker 'postgres_test_result=pass mode=full collection_digest=%s' "$collection_digest"
