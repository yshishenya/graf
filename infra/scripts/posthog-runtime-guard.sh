#!/usr/bin/env bash
set -euo pipefail

# Metadata-only guard: provider measurement may fail closed, product workflows may not.
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

mkdir -p "$state_dir"
chmod 0750 "$state_dir" 2>/dev/null || true
state_file="$state_dir/health-failures"
restart_snapshot_file="$state_dir/restart-snapshot"
restart_history_file="$state_dir/restart-history"
tmp_snapshot=""
tmp_history=""
tmp_env_files=()
cleanup() {
  [[ -z "$tmp_snapshot" ]] || rm -f "$tmp_snapshot"
  [[ -z "$tmp_history" ]] || rm -f "$tmp_history"
  for tmp_file in "${tmp_env_files[@]-}"; do
    [[ -z "$tmp_file" ]] || rm -f "$tmp_file"
  done
}
trap cleanup EXIT
health_failures=0
if [[ -r "$state_file" ]]; then
  candidate_health_failures=""
  read -r candidate_health_failures < "$state_file" || true
  if [[ "$candidate_health_failures" =~ ^[0-9]+$ ]]; then
    health_failures="$candidate_health_failures"
  fi
fi

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
load_1m="$(awk '{print $1}' /proc/loadavg 2>/dev/null || true)"
available_memory_mib="$(awk '/MemAvailable:/ {print int($2 / 1024); exit}' /proc/meminfo 2>/dev/null || true)"
disk_free_percent="$(df -P "$analytics_path" 2>/dev/null | awk 'NR == 2 {gsub(/%/, "", $5); print 100 - $5}')"
[[ "$load_1m" =~ ^[0-9]+([.][0-9]+)?$ ]] || sensor_failure="load_unavailable"
[[ "$available_memory_mib" =~ ^[0-9]+$ ]] || sensor_failure="${sensor_failure:-memory_unavailable}"
[[ "$disk_free_percent" =~ ^[0-9]+([.][0-9]+)?$ ]] || sensor_failure="${sensor_failure:-analytics_disk_unavailable}"
container_ids=""
if ! container_ids="$(docker ps --filter "label=com.docker.compose.project=$project_name" -q 2>/dev/null)"; then
  sensor_failure="${sensor_failure:-docker_unavailable}"
fi
container_count="$(printf '%s\n' "$container_ids" | awk 'NF {count++} END {print count + 0}')"
oom_count=0
restart_delta=0
limit_failure=0
now_epoch="$(date +%s 2>/dev/null || true)"
[[ "$now_epoch" =~ ^[0-9]+$ ]] || sensor_failure="${sensor_failure:-clock_unavailable}"
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

health_ok=1
curl -fsS --max-time 5 "$analytics_health_url" >/dev/null 2>&1 || health_ok=0
curl -fsS --max-time 5 "$graf_ready_url" >/dev/null 2>&1 || health_ok=0
if (( health_ok == 1 )); then
  health_failures=0
else
  health_failures=$((health_failures + 1))
fi
printf '%s\n' "$health_failures" > "$state_file"

breach=""
if [[ -n "$sensor_failure" ]]; then
  breach="$sensor_failure"
elif (( limit_failure == 1 )); then
  breach="container_limits_missing"
elif awk "BEGIN {exit !($load_1m >= 11)}"; then
  breach="host_load"
elif [[ "$available_memory_mib" =~ ^[0-9]+$ ]] && (( available_memory_mib < 16384 )); then
  breach="available_memory"
elif [[ "$disk_free_percent" =~ ^[0-9]+$ ]] && (( disk_free_percent < 10 )); then
  breach="analytics_disk"
elif (( oom_count > 0 )); then
  breach="container_oom"
elif (( restart_count > 2 )); then
  breach="container_restarts"
elif (( health_failures >= 2 )); then
  breach="health_failures"
fi

printf 'posthog_guard_result=%s\n' "$( [[ -n "$breach" ]] && printf alert || printf pass )"
printf 'posthog_guard_load_1m=%s\n' "$(metric_or_unknown "$load_1m")"
printf 'posthog_guard_memory_mib=%s\n' "$(metric_or_unknown "$available_memory_mib")"
printf 'posthog_guard_disk_free_percent=%s\n' "$(metric_or_unknown "$disk_free_percent")"
printf 'posthog_guard_container_count=%s\n' "$container_count"
printf 'posthog_guard_oom_count=%s\n' "$oom_count"
printf 'posthog_guard_restart_count=%s\n' "$restart_count"
printf 'posthog_guard_health_failures=%s\n' "$health_failures"
printf 'posthog_guard_product_impact=measurement_gap_only\n'

if [[ -z "$breach" ]]; then
  log_event pass "result=pass containers=$container_count oom=$oom_count restarts=$restart_count"
  exit 0
fi

log_event alert "result=alert reason=$breach containers=$container_count oom=$oom_count restarts=$restart_count"
rollback_status="not_requested"
if [[ "$auto_rollback" == "1" ]]; then
  rollback_status="blocked_dry_run"
  if [[ "$dry_run" == "0" ]]; then
    rollback_status="executed"
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
      log_event critical "result=rollback_failed reason=$breach product_impact=measurement_gap_only"
    elif [[ -x "$app_dir/infra/docker-compose.yml" || -f "$app_dir/infra/docker-compose.yml" ]] && command -v docker >/dev/null 2>&1; then
      if docker compose --env-file "$env_file" -f "$app_dir/infra/docker-compose.yml" up -d --no-deps rec-api >/dev/null 2>&1; then
        log_event rollback "result=executed reason=$breach product_impact=measurement_gap_only"
      else
        rollback_status="failed"
        rollback_failure=1
        log_event critical "result=rollback_failed reason=$breach product_impact=measurement_gap_only"
      fi
    else
      log_event rollback "result=executed reason=$breach product_impact=measurement_gap_only runtime_restart=unavailable"
    fi
    if [[ "$stop_stack" == "1" && -n "$container_ids" ]] && command -v docker >/dev/null 2>&1; then
      if docker stop $container_ids >/dev/null 2>&1; then
        printf 'posthog_guard_stack_stop=executed\n'
      else
        rollback_status="failed"
        rollback_failure=1
        printf 'posthog_guard_stack_stop=failed\n'
        log_event critical "result=stack_stop_failed reason=$breach product_impact=measurement_gap_only"
      fi
    else
      printf 'posthog_guard_stack_stop=not_requested\n'
    fi
  fi
fi
printf 'posthog_guard_rollback=%s\n' "$rollback_status"
if [[ "${rollback_failure:-0}" == "1" ]]; then
  exit 1
fi
exit 0
