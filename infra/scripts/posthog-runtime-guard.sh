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
umask 077
project_name="${GRAF_POSTHOG_PROJECT:-graf-posthog}"
app_dir="${GRAF_APP_DIR:-/opt/projects/2brain-rec}"
env_file="${GRAF_ENV_FILE:-$app_dir/.env}"
state_dir="${GRAF_POSTHOG_GUARD_STATE_DIR:-/var/lib/graf-posthog-runtime-guard}"
dry_run="${GRAF_POSTHOG_GUARD_DRY_RUN:-1}"
auto_rollback="${GRAF_POSTHOG_GUARD_AUTO_ROLLBACK:-0}"
stop_stack="${GRAF_POSTHOG_GUARD_STOP_STACK:-0}"
analytics_path="${GRAF_POSTHOG_ANALYTICS_PATH:-$app_dir}"
analytics_health_url="${GRAF_POSTHOG_HEALTH_URL:-https://analytics.2brain.pro/_health/}"
graf_ready_url="${GRAF_READY_URL:-https://rec.2brain.pro/api/v1/health/ready}"

# Analytics scope: fires first, disables measurement only.
analytics_health_failure_threshold="${GRAF_POSTHOG_GUARD_ANALYTICS_HEALTH_FAILURES:-1}"
analytics_disk_free_percent_threshold="${GRAF_POSTHOG_GUARD_ANALYTICS_DISK_FREE_PERCENT:-20}"
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
host_disk_free_percent_threshold="${GRAF_POSTHOG_GUARD_HOST_DISK_FREE_PERCENT:-10}"
host_health_failure_threshold="${GRAF_POSTHOG_GUARD_HOST_HEALTH_FAILURES:-2}"

mkdir -p "$state_dir"
chmod 0750 "$state_dir" 2>/dev/null || true
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
disk_free_percent="$(df -P "$analytics_path" 2>/dev/null | awk 'NR == 2 {gsub(/%/, "", $5); print 100 - $5}')"
[[ "$load_1m" =~ ^[0-9]+([.][0-9]+)?$ ]] || host_sensor_failure="host_load_unavailable"
[[ "$available_memory_mib" =~ ^[0-9]+$ ]] || host_sensor_failure="${host_sensor_failure:-host_memory_unavailable}"
[[ "$disk_free_percent" =~ ^[0-9]+([.][0-9]+)?$ ]] || host_sensor_failure="${host_sensor_failure:-host_disk_unavailable}"
container_ids=""
if ! container_ids="$(docker ps --filter "label=com.docker.compose.project=$project_name" -q 2>/dev/null)"; then
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
else
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
if [[ "$now_epoch" =~ ^[0-9]+$ ]]; then
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
if command -v docker >/dev/null 2>&1; then
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
curl -fsS --max-time 5 "$analytics_health_url" >/dev/null 2>&1 || analytics_probe_ok=0
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
printf '%s\n' "$analytics_health_failures" > "$analytics_state_file"

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

# Analytics scope is evaluated first: measurement degrades before the host does.
if [[ -n "$sensor_failure" ]]; then
  add_analytics_disable "$sensor_failure"
fi
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
if [[ "$disk_free_percent" =~ ^[0-9]+$ ]] && (( disk_free_percent < analytics_disk_free_percent_threshold )); then
  add_analytics_disable "analytics_storage"
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
if [[ "$disk_free_percent" =~ ^[0-9]+$ ]] && (( disk_free_percent < host_disk_free_percent_threshold )); then
  add_host_breach "host_disk"
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
  if [[ "$auto_rollback" == "1" ]]; then
    rollback_status="blocked_dry_run"
    measurement_action="blocked_dry_run"
    if [[ "$dry_run" == "0" ]]; then
      rollback_status="executed"
      measurement_action="disabled"
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
          log_event rollback "result=executed scope=analytics reason=$analytics_disable_reasons product_impact=measurement_gap_only"
        else
          rollback_status="failed"
          measurement_action="failed"
          rollback_failure=1
          log_event critical "result=rollback_failed reason=$analytics_disable_reasons product_impact=measurement_gap_only"
        fi
      else
        log_event rollback "result=executed scope=analytics reason=$analytics_disable_reasons product_impact=measurement_gap_only runtime_restart=unavailable"
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
    fi
  else
    log_event alert "result=alert scope=analytics reason=$analytics_disable_reasons rollback=not_enabled product_impact=measurement_gap_only"
  fi
fi

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

recorded_at="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown)"
if tmp_alert_state="$(mktemp "$state_dir/alert-state.XXXXXX")"; then
  {
    printf 'alert_state_version=1\n'
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
    log_event warning "result=alert_state_write_failed product_impact=measurement_gap_only"
  else
    tmp_alert_state=""
  fi
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
