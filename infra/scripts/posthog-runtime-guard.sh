#!/usr/bin/env bash
set -euo pipefail

# Metadata-only guard: provider measurement may fail closed, product workflows may not.
#
# Two threshold scopes (FR-031, FR-032, SC-012):
#
#   analytics  node availability, delivery lag, ingest queue growth, analytics
#              storage fill, analytics container health. These fire first and may
#              disable measurement only.
#   host       processor load, available memory, server disk. These alert only;
#              they never disable measurement automatically, so a traffic spike
#              on the public site cannot stop measurement on its own.
#
# Every existing environment variable keeps its meaning. New variables are
# additive and default to the previous hard-coded thresholds.
measurement_scope="${GRAF_ANALYTICS_GUARD_SCOPE:-posthog}"
case "$measurement_scope" in
  posthog|graf-local) ;;
  *) printf 'reason=measurement_scope_invalid\n' >&2; exit 1 ;;
esac
umask 077
project_name="${GRAF_POSTHOG_PROJECT:-graf-posthog}"
app_dir="${GRAF_APP_DIR:-/opt/projects/2brain-rec}"
env_file="${GRAF_ENV_FILE:-$app_dir/.env}"
state_dir="${GRAF_POSTHOG_GUARD_STATE_DIR:-/var/lib/graf-posthog-runtime-guard}"
dry_run="${GRAF_POSTHOG_GUARD_DRY_RUN:-1}"
auto_rollback="${GRAF_POSTHOG_GUARD_AUTO_ROLLBACK:-0}"
stop_stack="${GRAF_POSTHOG_GUARD_STOP_STACK:-0}"
analytics_health_url="${GRAF_POSTHOG_HEALTH_URL:-https://analytics.2brain.pro/_health/}"
graf_ready_url="${GRAF_READY_URL:-https://rec.2brain.pro/api/v1/health/ready}"

# Analytics scope: fires first, disables measurement only.
analytics_health_failure_threshold="${GRAF_POSTHOG_GUARD_ANALYTICS_HEALTH_FAILURES:-1}"
analytics_lag_seconds_threshold="${GRAF_POSTHOG_GUARD_ANALYTICS_LAG_SECONDS:-900}"
analytics_queue_depth_threshold="${GRAF_POSTHOG_GUARD_ANALYTICS_QUEUE_DEPTH:-100000}"
analytics_queue_growth_threshold="${GRAF_POSTHOG_GUARD_ANALYTICS_QUEUE_GROWTH_PER_MIN:-5000}"
# When no analytics probe is configured or readable, unknown metrics are reported
# as an analytics alert. They disable measurement only after the operator turns
# strict metrics on, so an unreadable probe cannot silently stop production.
analytics_strict_metrics="${GRAF_POSTHOG_GUARD_ANALYTICS_STRICT_METRICS:-0}"
events_table="${GRAF_POSTHOG_GUARD_EVENTS_TABLE:-events}"
ingest_lag_query="${GRAF_POSTHOG_GUARD_LAG_QUERY:-SELECT toUnixTimestamp(now()) - toUnixTimestamp(max(timestamp)) FROM $events_table}"
ingest_queue_query="${GRAF_POSTHOG_GUARD_QUEUE_QUERY:-}"

# Host scope: alert only, measurement is never disabled from here.
host_load_threshold="${GRAF_POSTHOG_GUARD_HOST_LOAD:-11}"
host_memory_mib_threshold="${GRAF_POSTHOG_GUARD_HOST_MEMORY_MIB:-16384}"
host_health_failure_threshold="${GRAF_POSTHOG_GUARD_HOST_HEALTH_FAILURES:-2}"

mkdir -p "$state_dir"
chmod 0750 "$state_dir" 2>/dev/null || true
if (( EUID == 0 )); then
  # Reuse the API's runtime-reader group; only root may write this directory.
  chgrp "${TWOBRAIN_RUNTIME_SECRET_GID:-1001}" "$state_dir"
  chmod 2750 "$state_dir"
fi
# Keep one durable incident even when timer and operator runs overlap.
if [[ "${GRAF_POSTHOG_GUARD_LOCK_HELD:-0}" != "1" ]]; then
  exec python3 - "$state_dir/guard.lock" "$BASH" "$0" "$@" <<'PY'
import fcntl, os, subprocess, sys
with open(sys.argv[1], 'a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    environment = dict(os.environ, GRAF_POSTHOG_GUARD_LOCK_HELD='1')
    raise SystemExit(subprocess.run(sys.argv[2:], env=environment).returncode)
PY
fi
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
capacity_helper="$script_dir/posthog-capacity.py"
protection_file="$state_dir/protection-state.json"
protection_status="observed"
protection_state_ok=1
if ! protection_status="$(python3 "$capacity_helper" --scope "$measurement_scope" --protection-state "$protection_file")"; then
  protection_state_ok=0
fi
state_file="$state_dir/health-failures"
analytics_state_file="$state_dir/analytics-health-failures"
queue_snapshot_file="$state_dir/queue-depth"
alert_state_file="$state_dir/alert-state"
restart_snapshot_file="$state_dir/restart-snapshot"
restart_history_file="$state_dir/restart-history"
tmp_snapshot=""
tmp_history=""
tmp_alert_state=""
tmp_env_files=()
cleanup() {
  [[ -z "$tmp_snapshot" ]] || rm -f "$tmp_snapshot"
  [[ -z "$tmp_history" ]] || rm -f "$tmp_history"
  [[ -z "$tmp_alert_state" ]] || rm -f "$tmp_alert_state"
  for tmp_file in "${tmp_env_files[@]-}"; do
    [[ -z "$tmp_file" ]] || rm -f "$tmp_file"
  done
}
trap cleanup EXIT

read_counter() {
  local path="$1"
  local fallback="$2"
  local value=""
  if [[ -r "$path" ]]; then
    read -r value < "$path" || true
  fi
  if [[ ! "$value" =~ ^[0-9]+$ ]]; then
    value="$fallback"
  fi
  printf '%s' "$value"
}

json_or_none() {
  local value="$1"
  [[ -n "$value" ]] && printf '%s' "$value" || printf 'none'
}

health_failures="$(read_counter "$state_file" 0)"
analytics_health_failures="$(read_counter "$analytics_state_file" 0)"

log_event() {
  local level="$1"
  shift
  logger -t graf-posthog-runtime-guard "level=$level $*" 2>/dev/null || true
}

metric_or_unknown() {
  local value="$1"
  [[ -n "$value" ]] && printf '%s' "$value" || printf 'unknown'
}

sensor_failure=""
host_sensor_failure=""
load_1m="$(awk '{print $1}' /proc/loadavg 2>/dev/null || true)"
available_memory_mib="$(awk '/MemAvailable:/ {print int($2 / 1024); exit}' /proc/meminfo 2>/dev/null || true)"
# One collector supplies both scopes. Never infer usage from rounded df output.
storage_state="${GRAF_POSTHOG_STORAGE_STATE_FILE:-${GRAF_POSTHOG_STORAGE_STATE_DIR:-/var/lib/graf-posthog-storage}/storage-growth-state}"
collector="${GRAF_POSTHOG_STORAGE_COLLECTOR:-$script_dir/measure-posthog-storage-growth.sh}"
collector_completed=1
python3 - "$collector" "$measurement_scope" <<'PY' >/dev/null 2>&1 || collector_completed=0
import subprocess, sys
try:
    raise SystemExit(subprocess.run([sys.argv[1], "--scope", sys.argv[2]], timeout=45, check=False).returncode)
except (OSError, subprocess.TimeoutExpired):
    raise SystemExit(1)
PY
capacity_ready=false
input_verified=false
budget_accepted=false
sample_epoch=unknown
inventory_version=unknown
budget_version=unknown
budget_deadline_epoch=unknown
analytics_storage_bytes=unknown
analytics_budget_bytes=unknown
capacity_analytics_reasons=capacity_input_unverified
capacity_host_reasons=""
capacity_disable_reasons=""
capacity_filesystems='[]'
disk_free_percent=unknown
analytics_free_percent=unknown
storage_json="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).with_suffix(".json"))' "$storage_state")"
capacity_fields="$(python3 "$capacity_helper" --scope "$measurement_scope" --shell --sample "$storage_json" \
  --budget "${GRAF_POSTHOG_CAPACITY_BUDGET_FILE:-$state_dir/capacity-budget.json}")" || true
while IFS='=' read -r key value; do
  case "$key" in
    capacity_ready) capacity_ready="$value" ;;
    input_verified) input_verified="$value" ;;
    budget_accepted) budget_accepted="$value" ;;
    sample_epoch) sample_epoch="$value" ;;
    inventory_version) inventory_version="$value" ;;
    budget_version) budget_version="$value" ;;
    budget_deadline_epoch) budget_deadline_epoch="$value" ;;
    analytics_storage_bytes) analytics_storage_bytes="$value" ;;
    analytics_budget_bytes) analytics_budget_bytes="$value" ;;
    analytics_reasons) capacity_analytics_reasons="$value" ;;
    host_reasons) capacity_host_reasons="$value" ;;
    disable_reasons) capacity_disable_reasons="$value" ;;
    filesystems) capacity_filesystems="$value" ;;
    host_free_percent) disk_free_percent="$value" ;;
    analytics_free_percent) analytics_free_percent="$value" ;;
  esac
done <<< "$capacity_fields"
if (( collector_completed == 0 )); then
  capacity_ready=false
  input_verified=false
  capacity_analytics_reasons="${capacity_analytics_reasons:+$capacity_analytics_reasons,}capacity_input_unverified"
fi
[[ "$load_1m" =~ ^[0-9]+([.][0-9]+)?$ ]] || host_sensor_failure="host_load_unavailable"
[[ "$available_memory_mib" =~ ^[0-9]+$ ]] || host_sensor_failure="${host_sensor_failure:-host_memory_unavailable}"
[[ "$disk_free_percent" =~ ^[0-9]+([.][0-9]+)?$ ]] || host_sensor_failure="${host_sensor_failure:-host_disk_unavailable}"
container_ids=""
if [[ "$measurement_scope" == "posthog" ]] && ! container_ids="$(docker ps --filter "label=com.docker.compose.project=$project_name" -q 2>/dev/null)"; then
  sensor_failure="${sensor_failure:-docker_unavailable}"
fi
container_count="$(printf '%s\n' "$container_ids" | awk 'NF {count++} END {print count + 0}')"
oom_count=0
restart_delta=0
limit_failure=0
now_epoch="$(date +%s 2>/dev/null || true)"
[[ "$now_epoch" =~ ^[0-9]+$ ]] || host_sensor_failure="${host_sensor_failure:-host_clock_unavailable}"
if [[ -n "$container_ids" ]]; then
  tmp_snapshot="$(mktemp "$state_dir/restart-snapshot.XXXXXX")"
elif [[ "$measurement_scope" == "posthog" ]]; then
  sensor_failure="${sensor_failure:-posthog_containers_missing}"
fi
if [[ -n "$container_ids" ]]; then
  while read -r container_id; do
    [[ -z "$container_id" ]] && continue
    inspect=""
    if ! inspect="$(docker inspect --format '{{.State.OOMKilled}} {{.RestartCount}} {{.HostConfig.NanoCpus}} {{.HostConfig.Memory}}' "$container_id" 2>/dev/null)"; then
      sensor_failure="${sensor_failure:-docker_inspect_unavailable}"
      continue
    fi
    oom=""
    restarts=""
    nano_cpus=""
    memory_bytes=""
    read -r oom restarts nano_cpus memory_bytes <<< "$inspect"
    if [[ "$oom" == "true" ]]; then
      oom_count=$((oom_count + 1))
    fi
    if [[ ! "$restarts" =~ ^[0-9]+$ ]]; then
      sensor_failure="${sensor_failure:-restart_metric_unavailable}"
      continue
    fi
    if [[ ! "$nano_cpus" =~ ^[0-9]+$ ]] || (( nano_cpus <= 0 )) || [[ ! "$memory_bytes" =~ ^[0-9]+$ ]] || (( memory_bytes <= 0 )); then
      limit_failure=1
    fi
    previous_restarts=0
    if [[ -r "$restart_snapshot_file" ]]; then
      previous_restarts="$(awk -v id="$container_id" '$1 == id {print $2; exit}' "$restart_snapshot_file" 2>/dev/null || true)"
    fi
    if [[ "$previous_restarts" =~ ^[0-9]+$ ]] && (( restarts > previous_restarts )); then
      restart_delta=$((restart_delta + restarts - previous_restarts))
    fi
    printf '%s %s\n' "$container_id" "$restarts" >> "$tmp_snapshot"
  done <<< "$container_ids"
  if ! mv "$tmp_snapshot" "$restart_snapshot_file"; then
    sensor_failure="${sensor_failure:-restart_state_unavailable}"
  else
    tmp_snapshot=""
  fi
fi

restart_count=0
if [[ "$measurement_scope" == "posthog" && "$now_epoch" =~ ^[0-9]+$ ]]; then
  tmp_history="$(mktemp "$state_dir/restart-history.XXXXXX")"
  if [[ -r "$restart_history_file" ]]; then
    awk -v cutoff="$((now_epoch - 600))" '$1 >= cutoff {print}' "$restart_history_file" >> "$tmp_history"
  fi
  printf '%s %s\n' "$now_epoch" "$restart_delta" >> "$tmp_history"
  restart_count="$(awk '{sum += $2} END {print sum + 0}' "$tmp_history")"
  if ! mv "$tmp_history" "$restart_history_file"; then
    sensor_failure="${sensor_failure:-restart_history_unavailable}"
  else
    tmp_history=""
  fi
fi

clickhouse_container=""
if [[ "$measurement_scope" == "posthog" ]] && command -v docker >/dev/null 2>&1; then
  clickhouse_container="$(docker ps --filter "label=com.docker.compose.project=$project_name" \
    --filter "label=com.docker.compose.service=clickhouse" -q 2>/dev/null | awk 'NF {print; exit}')" || true
  if [[ -z "$clickhouse_container" ]]; then
    clickhouse_container="$(docker ps --filter "name=clickhouse" -q 2>/dev/null | awk 'NF {print; exit}')" || true
  fi
fi

clickhouse_scalar() {
  local query="$1"
  local output=""
  [[ -n "$clickhouse_container" ]] || return 1
  output="$(docker exec "$clickhouse_container" clickhouse-client --query "$query" 2>/dev/null)" || return 1
  output="${output//[[:space:]]/}"
  [[ "$output" =~ ^[0-9]+$ ]] || return 1
  printf '%s' "$output"
}

delivery_lag_seconds=""
queue_depth=""
if [[ -n "$clickhouse_container" ]]; then
  delivery_lag_seconds="$(clickhouse_scalar "$ingest_lag_query")" || delivery_lag_seconds=""
  if [[ -n "$ingest_queue_query" ]]; then
    queue_depth="$(clickhouse_scalar "$ingest_queue_query")" || queue_depth=""
  else
    for queue_query in \
      "SELECT sum(arraySum(assignments.intent_size)) FROM system.kafka_consumers" \
      "SELECT sum(assignments.intent_size) FROM system.kafka_consumers" \
      "SELECT sum(num_messages_behind) FROM system.kafka_consumers"; do
      queue_depth="$(clickhouse_scalar "$queue_query")" || queue_depth=""
      [[ -n "$queue_depth" ]] && break
    done
  fi
fi

queue_growth_per_min=""
previous_queue_depth=""
previous_queue_epoch=""
if [[ -r "$queue_snapshot_file" ]]; then
  read -r previous_queue_depth previous_queue_epoch < "$queue_snapshot_file" || true
fi
if [[ "$queue_depth" =~ ^[0-9]+$ ]] && [[ "$previous_queue_depth" =~ ^[0-9]+$ ]] && [[ "$previous_queue_epoch" =~ ^[0-9]+$ ]] \
  && [[ "$now_epoch" =~ ^[0-9]+$ ]] && (( now_epoch > previous_queue_epoch )) && (( queue_depth >= previous_queue_depth )); then
  elapsed_minutes=$(( (now_epoch - previous_queue_epoch) / 60 ))
  (( elapsed_minutes >= 1 )) || elapsed_minutes=1
  queue_growth_per_min=$(( (queue_depth - previous_queue_depth) / elapsed_minutes ))
fi
if [[ "$queue_depth" =~ ^[0-9]+$ ]] && [[ "$now_epoch" =~ ^[0-9]+$ ]]; then
  printf '%s %s\n' "$queue_depth" "$now_epoch" > "$queue_snapshot_file"
fi

analytics_probe_ok=1
product_probe_ok=1
if [[ "$measurement_scope" == "posthog" ]]; then
  curl -fsS --max-time 5 "$analytics_health_url" >/dev/null 2>&1 || analytics_probe_ok=0
fi
curl -fsS --max-time 5 "$graf_ready_url" >/dev/null 2>&1 || product_probe_ok=0
health_ok=1
if (( analytics_probe_ok == 0 || product_probe_ok == 0 )); then
  health_ok=0
fi
if (( health_ok == 1 )); then
  health_failures=0
else
  health_failures=$((health_failures + 1))
fi
printf '%s\n' "$health_failures" > "$state_file"
if (( analytics_probe_ok == 1 )); then
  analytics_health_failures=0
else
  analytics_health_failures=$((analytics_health_failures + 1))
fi
if [[ "$measurement_scope" == "posthog" ]]; then
  printf '%s\n' "$analytics_health_failures" > "$analytics_state_file"
fi

analytics_breaches=""
analytics_disable_reasons=""
host_breaches=""
append_breach() {
  local current="$1"
  local value="$2"
  [[ -z "$current" ]] && printf '%s' "$value" || printf '%s,%s' "$current" "$value"
}
add_analytics_breach() {
  analytics_breaches="$(append_breach "$analytics_breaches" "$1")"
}
add_analytics_disable() {
  analytics_breaches="$(append_breach "$analytics_breaches" "$1")"
  analytics_disable_reasons="$(append_breach "$analytics_disable_reasons" "$1")"
}
add_host_breach() {
  host_breaches="$(append_breach "$host_breaches" "$1")"
}

IFS=',' read -r -a capacity_codes <<< "$capacity_analytics_reasons"
for code in "${capacity_codes[@]-}"; do
  [[ -z "$code" ]] || add_analytics_breach "$code"
done
IFS=',' read -r -a capacity_codes <<< "$capacity_disable_reasons"
for code in "${capacity_codes[@]-}"; do
  [[ -z "$code" ]] || analytics_disable_reasons="$(append_breach "$analytics_disable_reasons" "$code")"
done
IFS=',' read -r -a capacity_codes <<< "$capacity_host_reasons"
for code in "${capacity_codes[@]-}"; do
  [[ -z "$code" ]] || add_host_breach "$code"
done
if (( protection_state_ok == 0 )); then
  add_analytics_breach "protection_state_unverified"
fi
if [[ "$protection_status" != "observed" ]]; then
  add_analytics_breach "analytics_protection_latched"
  capacity_ready=false
  if [[ "$protection_status" != "protected" ]]; then
    analytics_disable_reasons="$(append_breach "$analytics_disable_reasons" "analytics_protection_latched")"
  fi
fi

# Analytics scope is evaluated first: measurement degrades before the host does.
if [[ -n "$sensor_failure" ]]; then
  add_analytics_disable "$sensor_failure"
fi
if [[ "$measurement_scope" == "posthog" ]]; then
if [[ -z "$delivery_lag_seconds" ]]; then
  add_analytics_breach "analytics_delivery_lag_unavailable"
elif (( delivery_lag_seconds >= analytics_lag_seconds_threshold )); then
  add_analytics_disable "analytics_delivery_lag"
fi
if [[ -z "$queue_depth" ]]; then
  add_analytics_breach "analytics_queue_metric_unavailable"
elif (( queue_depth >= analytics_queue_depth_threshold )); then
  add_analytics_disable "analytics_queue_depth"
fi
if [[ -n "$queue_growth_per_min" ]] && (( queue_growth_per_min >= analytics_queue_growth_threshold )); then
  add_analytics_disable "analytics_queue_growth"
fi
if (( limit_failure == 1 )); then
  add_analytics_disable "container_limits_missing"
fi
if (( oom_count > 0 )); then
  add_analytics_disable "container_oom"
fi
if (( restart_count > 2 )); then
  add_analytics_disable "container_restarts"
fi
if (( analytics_health_failures >= analytics_health_failure_threshold )); then
  add_analytics_disable "analytics_node_unavailable"
fi
if [[ "$analytics_strict_metrics" == "1" ]]; then
  if [[ -z "$delivery_lag_seconds" ]]; then
    analytics_disable_reasons="$(append_breach "$analytics_disable_reasons" "analytics_delivery_lag_unavailable")"
  fi
  if [[ -z "$queue_depth" ]]; then
    analytics_disable_reasons="$(append_breach "$analytics_disable_reasons" "analytics_queue_metric_unavailable")"
  fi
fi
fi

# Host scope is alert-only: it must never disable measurement on its own.
if [[ -n "$host_sensor_failure" ]]; then
  add_host_breach "$host_sensor_failure"
fi
if [[ "$load_1m" =~ ^[0-9]+([.][0-9]+)?$ ]] && awk -v threshold="$host_load_threshold" "BEGIN {exit !($load_1m >= threshold)}"; then
  add_host_breach "host_load"
fi
if [[ "$available_memory_mib" =~ ^[0-9]+$ ]] && (( available_memory_mib < host_memory_mib_threshold )); then
  add_host_breach "host_memory"
fi
if (( health_failures >= host_health_failure_threshold )); then
  add_host_breach "host_product_probe_unavailable"
fi

breach=""
[[ -n "$analytics_breaches" ]] && breach="analytics"
[[ -n "$host_breaches" ]] && breach="${breach:+$breach+}host"
if [[ -z "$breach" ]]; then
  analytics_scope="pass"
  host_scope="pass"
else
  analytics_scope="$( [[ -n "$analytics_breaches" ]] && printf alert || printf pass )"
  host_scope="$( [[ -n "$host_breaches" ]] && printf alert || printf pass )"
fi

measurement_action="not_requested"
rollback_status="not_requested"
rollback_failure=0
if [[ -n "$analytics_disable_reasons" ]]; then
  capacity_ready=false
  if (( protection_state_ok == 0 )); then
    rollback_failure=1
    measurement_action=failed
  elif ! protection_status="$(python3 "$capacity_helper" --scope "$measurement_scope" --protection-state "$protection_file" \
    --protection-action protection_requested --reasons "$analytics_disable_reasons")"; then
    rollback_failure=1
    measurement_action=failed
  elif [[ "$protection_status" == "protected" ]]; then
    measurement_action=protected
    rollback_status=already_protected
  elif [[ "$auto_rollback" == "1" ]]; then
    rollback_status="blocked_dry_run"
    measurement_action="blocked_dry_run"
    if [[ "$dry_run" == "0" ]]; then
      rollback_status="failed"
      measurement_action="failed"
      keys=(
        TWOBRAIN_PRODUCT_ANALYTICS_ENABLED
        TWOBRAIN_PRODUCT_ANALYTICS_PROVIDER_MODE
        TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_ENABLED
        TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_WEB_DIRECT_ENABLED
        TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_DESKTOP_DIRECT_ENABLED
        TWOBRAIN_PRODUCT_ANALYTICS_POSTHOG_AUTOCAPTURE_ENABLED
        TWOBRAIN_PRODUCT_ANALYTICS_REPLAY_ENABLED
        TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_ALL_PAGES_ENABLED
        TWOBRAIN_PRODUCT_ANALYTICS_YANDEX_OFFLINE_ENABLED
        TWOBRAIN_PRODUCT_ANALYTICS_VALIDATION_MODE
      )
      apply_rollback() {
        [[ -f "$env_file" && ! -L "$env_file" ]] || return 1
        current_env="$env_file"
        for key in "${keys[@]}"; do
          value="disabled"
          [[ "$key" == *ENABLED ]] && value="false"
          next_env="$(mktemp "$env_file.guard.XXXXXX")" || return 1
          tmp_env_files+=("$next_env")
          if ! awk -v key="$key" -v value="$value" '
            BEGIN { found = 0 }
            index($0, key "=") == 1 { print key "=" value; found = 1; next }
            { print }
            END { if (!found) print key "=" value }
          ' "$current_env" > "$next_env"; then
            return 1
          fi
          chmod 0600 "$next_env" || return 1
          if [[ "$current_env" != "$env_file" ]]; then
            rm -f "$current_env"
          fi
          current_env="$next_env"
        done
        if [[ "$current_env" == "$env_file" ]]; then
          return 1
        fi
        if ! mv "$current_env" "$env_file"; then
          return 1
        fi
        tmp_env_files=()
      }
      rollback_failure=0
      if command -v flock >/dev/null 2>&1; then
        exec 9>"$env_file.lock"
        if ! flock -x 9; then
          rollback_failure=1
        elif ! apply_rollback; then
          rollback_failure=1
        fi
        flock -u 9 2>/dev/null || true
        exec 9>&-
      else
        if ! apply_rollback; then
          rollback_failure=1
        fi
      fi
      if (( rollback_failure == 1 )); then
        rollback_status="failed"
        measurement_action="failed"
        log_event critical "result=rollback_failed reason=$analytics_disable_reasons product_impact=measurement_gap_only"
      elif [[ -x "$app_dir/infra/docker-compose.yml" || -f "$app_dir/infra/docker-compose.yml" ]] && command -v docker >/dev/null 2>&1; then
        if docker compose --env-file "$env_file" -f "$app_dir/infra/docker-compose.yml" up -d --no-deps rec-api >/dev/null 2>&1; then
          log_event rollback "result=restart_completed scope=analytics reason=$analytics_disable_reasons product_impact=measurement_gap_only"
        else
          rollback_status="failed"
          measurement_action="failed"
          rollback_failure=1
          log_event critical "result=rollback_failed reason=$analytics_disable_reasons product_impact=measurement_gap_only"
        fi
      else
        rollback_failure=1
        log_event critical "result=rollback_failed reason=runtime_restart_unavailable product_impact=measurement_gap_only"
      fi
      if [[ "$stop_stack" == "1" && -n "$container_ids" ]] && command -v docker >/dev/null 2>&1; then
        if docker stop $container_ids >/dev/null 2>&1; then
          printf 'posthog_guard_stack_stop=executed\n'
        else
          rollback_status="failed"
          measurement_action="failed"
          rollback_failure=1
          printf 'posthog_guard_stack_stop=failed\n'
          log_event critical "result=stack_stop_failed reason=$analytics_disable_reasons product_impact=measurement_gap_only"
        fi
      else
        printf 'posthog_guard_stack_stop=not_requested\n'
      fi
      if (( rollback_failure == 0 )); then
        runtime_id="$(docker compose --env-file "$env_file" -f "$app_dir/infra/docker-compose.yml" ps -q rec-api 2>/dev/null)" || runtime_id=""
        runtime_env=""
        if [[ -n "$runtime_id" && "$runtime_id" != *$'\n'* ]]; then
          runtime_env="$(docker inspect --format '{{if .State.Running}}{{json .Config.Env}}{{else}}null{{end}}' "$runtime_id" 2>/dev/null)" || true
        fi
        if ! protection_status="$(printf '%s' "$runtime_env" | python3 "$capacity_helper" --scope "$measurement_scope" \
          --protection-state "$protection_file" --protection-action protected)"; then
          rollback_failure=1
        else
          rollback_status=executed
          measurement_action=protected
        fi
      fi
      if (( rollback_failure != 0 )); then
        protection_status="$(python3 "$capacity_helper" --scope "$measurement_scope" --protection-state "$protection_file" \
          --protection-action apply_failed)" || true
        measurement_action=failed
        rollback_status=failed
      fi
    else
      protection_status="$(python3 "$capacity_helper" --scope "$measurement_scope" --protection-state "$protection_file" \
        --protection-action blocked_dry_run)" || rollback_failure=1
    fi
  else
    protection_status="$(python3 "$capacity_helper" --scope "$measurement_scope" --protection-state "$protection_file" \
      --protection-action not_enabled)" || rollback_failure=1
    measurement_action=not_enabled
    log_event alert "result=alert scope=analytics reason=$analytics_disable_reasons rollback=not_enabled product_impact=measurement_gap_only"
  fi
fi

if [[ "$protection_status" != "observed" ]]; then
  capacity_ready=false
  [[ "$measurement_action" != "not_requested" ]] || measurement_action="$protection_status"
fi

if [[ "$measurement_scope" == "graf-local" ]]; then
  delivery_lag_seconds=not_applicable
  queue_depth=not_applicable
  queue_growth_per_min=not_applicable
  container_count=not_applicable
  oom_count=not_applicable
  restart_count=not_applicable
  analytics_health_failures=not_applicable
fi
printf 'posthog_guard_measurement_scope=%s\n' "$measurement_scope"
printf 'posthog_guard_result=%s\n' "$( [[ -n "$breach" ]] && printf alert || printf pass )"
printf 'posthog_guard_breach_scope=%s\n' "$(json_or_none "$breach")"
printf 'posthog_guard_analytics_scope=%s\n' "$analytics_scope"
printf 'posthog_guard_host_scope=%s\n' "$host_scope"
printf 'posthog_guard_analytics_breaches=%s\n' "$(json_or_none "$analytics_breaches")"
printf 'posthog_guard_host_breaches=%s\n' "$(json_or_none "$host_breaches")"
printf 'posthog_guard_analytics_disable_reasons=%s\n' "$(json_or_none "$analytics_disable_reasons")"
printf 'posthog_guard_analytics_strict_metrics=%s\n' "$analytics_strict_metrics"
printf 'posthog_guard_load_1m=%s\n' "$(metric_or_unknown "$load_1m")"
printf 'posthog_guard_memory_mib=%s\n' "$(metric_or_unknown "$available_memory_mib")"
printf 'posthog_guard_disk_free_percent=%s\n' "$(metric_or_unknown "$disk_free_percent")"
printf 'posthog_guard_delivery_lag_seconds=%s\n' "$(metric_or_unknown "$delivery_lag_seconds")"
printf 'posthog_guard_queue_depth=%s\n' "$(metric_or_unknown "$queue_depth")"
printf 'posthog_guard_queue_growth_per_min=%s\n' "$(metric_or_unknown "$queue_growth_per_min")"
printf 'posthog_guard_container_count=%s\n' "$container_count"
printf 'posthog_guard_oom_count=%s\n' "$oom_count"
printf 'posthog_guard_restart_count=%s\n' "$restart_count"
printf 'posthog_guard_health_failures=%s\n' "$health_failures"
printf 'posthog_guard_analytics_health_failures=%s\n' "$analytics_health_failures"
printf 'posthog_guard_product_impact=measurement_gap_only\n'
printf 'posthog_guard_capacity_ready=%s\n' "$capacity_ready"
printf 'posthog_guard_protection_status=%s\n' "$protection_status"

recorded_at="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown)"
if tmp_alert_state="$(mktemp "$state_dir/alert-state.XXXXXX")"; then
  {
    printf 'alert_state_version=3\n'
    printf 'measurement_scope=%s\n' "$measurement_scope"
    printf 'capacity_ready=%s\n' "$capacity_ready"
    printf 'capacity_input_verified=%s\n' "$input_verified"
    printf 'capacity_budget_accepted=%s\n' "$budget_accepted"
    printf 'capacity_sample_epoch=%s\n' "$sample_epoch"
    printf 'capacity_inventory_version=%s\n' "$inventory_version"
    printf 'capacity_budget_version=%s\n' "$budget_version"
    printf 'capacity_budget_deadline_epoch=%s\n' "$budget_deadline_epoch"
    printf 'analytics_storage_bytes=%s\n' "$analytics_storage_bytes"
    printf 'analytics_budget_bytes=%s\n' "$analytics_budget_bytes"
    printf 'capacity_filesystems=%s\n' "$capacity_filesystems"
    printf 'protection_status=%s\n' "$protection_status"
    printf 'recorded_at=%s\n' "$recorded_at"
    printf 'recorded_at_epoch=%s\n' "$(metric_or_unknown "$now_epoch")"
    printf 'result=%s\n' "$( [[ -n "$breach" ]] && printf alert || printf pass )"
    printf 'breach_scope=%s\n' "$(json_or_none "$breach")"
    printf 'analytics_scope=%s\n' "$analytics_scope"
    printf 'host_scope=%s\n' "$host_scope"
    printf 'analytics_breaches=%s\n' "$(json_or_none "$analytics_breaches")"
    printf 'host_breaches=%s\n' "$(json_or_none "$host_breaches")"
    printf 'analytics_disable_reasons=%s\n' "$(json_or_none "$analytics_disable_reasons")"
    printf 'measurement_action=%s\n' "$measurement_action"
    printf 'load_1m=%s\n' "$(metric_or_unknown "$load_1m")"
    printf 'memory_mib=%s\n' "$(metric_or_unknown "$available_memory_mib")"
    printf 'disk_free_percent=%s\n' "$(metric_or_unknown "$disk_free_percent")"
    printf 'delivery_lag_seconds=%s\n' "$(metric_or_unknown "$delivery_lag_seconds")"
    printf 'queue_depth=%s\n' "$(metric_or_unknown "$queue_depth")"
    printf 'queue_growth_per_min=%s\n' "$(metric_or_unknown "$queue_growth_per_min")"
    printf 'container_count=%s\n' "$container_count"
    printf 'oom_count=%s\n' "$oom_count"
    printf 'restart_count=%s\n' "$restart_count"
    printf 'health_failures=%s\n' "$health_failures"
    printf 'analytics_health_failures=%s\n' "$analytics_health_failures"
    printf 'product_impact=measurement_gap_only\n'
  } > "$tmp_alert_state"
  chmod 0640 "$tmp_alert_state" 2>/dev/null || true
  if ! mv "$tmp_alert_state" "$alert_state_file"; then
    rollback_failure=1
    log_event warning "result=alert_state_write_failed product_impact=measurement_gap_only"
  else
    tmp_alert_state=""
  fi
else
  rollback_failure=1
  log_event warning "result=alert_state_write_failed product_impact=measurement_gap_only"
fi

if (( rollback_failure != 0 )); then
  exit 1
fi
if [[ -z "$breach" ]]; then
  log_event pass "result=pass containers=$container_count oom=$oom_count restarts=$restart_count"
  exit 0
fi

log_event alert "result=alert scope=$(json_or_none "$breach") reason=$(json_or_none "$analytics_breaches")/($(json_or_none "$host_breaches")) containers=$container_count oom=$oom_count restarts=$restart_count"
printf 'posthog_guard_rollback=%s\n' "$rollback_status"
printf 'posthog_guard_measurement_action=%s\n' "$measurement_action"
if [[ "$rollback_failure" == "1" ]]; then
  exit 1
fi
exit 0
