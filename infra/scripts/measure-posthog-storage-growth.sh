#!/usr/bin/env bash
set -euo pipefail

# Absolute analytics storage and expected growth (FR-039, SC-012, T076).
#
# The capacity baseline needs one repeatable measurement instead of eyeballed
# numbers, so this task reports the same rows the capacity document holds:
#
#   analytics_filesystem_total  the filesystem that carries the analytics stack
#   relational                  the PostHog relational database
#   events                      the ClickHouse event storage
#   object_storage              recording objects held next to the analytics node
#
# Each row reports the absolute size, the measurement window, the events seen in
# that window, the derived daily growth, the growth per thousand events and the
# twelve- and thirty-six-month projection. When a previous sample exists in the
# state file, growth comes from the measured difference between the two samples;
# otherwise it is derived from the observed event rate and the average stored
# event size, and the row says which basis was used.
#
# The measurement never reads event content: it asks storage systems for sizes
# and counts only. Nothing here is written into the repository, and the run does
# not change retention, configuration or the running stack.
#
# Usage:
#   measure-posthog-storage-growth.sh                 # measure and print
#   measure-posthog-storage-growth.sh --status        # print the last sample
#   measure-posthog-storage-growth.sh --window-hours 168

umask 077

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
app_dir="${GRAF_APP_DIR:-/opt/projects/2brain-rec}"
analytics_path="${GRAF_POSTHOG_ANALYTICS_PATH:-$app_dir}"
object_storage_path="${GRAF_POSTHOG_OBJECT_STORAGE_PATH:-}"
state_dir="${GRAF_POSTHOG_STORAGE_STATE_DIR:-/var/lib/graf-posthog-storage}"
state_file="${GRAF_POSTHOG_STORAGE_STATE_FILE:-$state_dir/storage-growth-state}"
posthog_project="${GRAF_POSTHOG_PROJECT:-graf-posthog}"
clickhouse_container_hint="${GRAF_POSTHOG_CLICKHOUSE_CONTAINER:-}"
compose_file="${GRAF_POSTHOG_COMPOSE_FILE:-$repo_root/infra/posthog/docker-compose.posthog.yml}"
database_service="${GRAF_POSTHOG_STORAGE_DATABASE_SERVICE:-posthog-db}"
database_name="${GRAF_POSTHOG_STORAGE_DATABASE_NAME:-posthog}"
database_user="${GRAF_POSTHOG_STORAGE_DATABASE_USER:-posthog}"
events_table="${GRAF_POSTHOG_GUARD_EVENTS_TABLE:-events}"
event_storage_table="${GRAF_POSTHOG_STORAGE_EVENTS_TABLE:-sharded_events}"
window_hours="${GRAF_POSTHOG_STORAGE_WINDOW_HOURS:-24}"
mode="measure"

usage() {
  cat >&2 <<EOF
usage: $0 [--status] [--window-hours <n>]
EOF
}

while (( $# > 0 )); do
  case "$1" in
    --status) mode="status" ;;
    --window-hours)
      (( $# > 1 )) || { usage; exit 2; }
      window_hours="$2"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
  shift
done

if [[ ! "$window_hours" =~ ^[0-9]+$ ]] || (( window_hours <= 0 )); then
  echo "storage_growth_result=failed"
  echo "reason=window_hours_invalid"
  exit 2
fi

now_epoch="$(date +%s 2>/dev/null || printf '')"
recorded_at="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf 'unknown')"
if [[ ! "$now_epoch" =~ ^[0-9]+$ ]]; then
  echo "storage_growth_result=failed"
  echo "reason=clock_unavailable"
  exit 1
fi

state_value() {
  local key="$1"
  [[ -r "$state_file" ]] || return 0
  awk -v key="$key" 'index($0, key "=") == 1 {print substr($0, length(key) + 2); exit}' "$state_file"
}

if [[ "$mode" == "status" ]]; then
  if [[ -r "$state_file" ]]; then
    cat "$state_file"
  else
    printf 'storage_growth_state=missing\n'
  fi
  exit 0
fi

clickhouse_container() {
  if [[ -n "$clickhouse_container_hint" ]]; then
    printf '%s' "$clickhouse_container_hint"
    return 0
  fi
  docker ps --filter "label=com.docker.compose.project=$posthog_project" \
    --filter "label=com.docker.compose.service=clickhouse" -q 2>/dev/null | awk 'NF {print; exit}'
}

clickhouse_scalar() {
  local container="$1"
  local query="$2"
  [[ -n "$container" ]] || { printf 'unknown'; return 0; }
  local value
  value="$(docker exec "$container" clickhouse-client --query "$query" 2>/dev/null | tr -d '[:space:]')"
  if [[ "$value" =~ ^[0-9]+$ ]]; then
    printf '%s' "$value"
  else
    printf 'unknown'
  fi
}

postgres_scalar() {
  local query="$1"
  local value
  value="$(docker compose -f "$compose_file" exec -T "$database_service" \
    psql -U "$database_user" -d "$database_name" -tAqc "$query" 2>/dev/null | tr -d '[:space:]')"
  if [[ "$value" =~ ^[0-9]+$ ]]; then
    printf '%s' "$value"
  else
    printf 'unknown'
  fi
}

filesystem_total_bytes() {
  local value
  value="$(df -Pk "$analytics_path" 2>/dev/null | awk 'NR == 2 {print $2 * 1024}')"
  if [[ "$value" =~ ^[0-9]+$ ]]; then
    printf '%s' "$value"
  else
    printf 'unknown'
  fi
}

filesystem_free_percent() {
  local value
  value="$(df -P "$analytics_path" 2>/dev/null | awk 'NR == 2 {gsub(/%/, "", $5); print 100 - $5}')"
  if [[ "$value" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    printf '%s' "$value"
  else
    printf 'unknown'
  fi
}

directory_bytes() {
  local path="$1"
  local value
  [[ -n "$path" && -d "$path" ]] || { printf 'unknown'; return 0; }
  value="$(du -sk "$path" 2>/dev/null | awk 'NR == 1 {print $1 * 1024}')"
  if [[ "$value" =~ ^[0-9]+$ ]]; then
    printf '%s' "$value"
  else
    printf 'unknown'
  fi
}

container="$(clickhouse_container)"
events_bytes="$(clickhouse_scalar "$container" "SELECT sum(bytes_on_disk) FROM system.parts WHERE active AND table = '$event_storage_table'")"
window_events="$(clickhouse_scalar "$container" "SELECT count() FROM $events_table WHERE timestamp >= now() - INTERVAL $window_hours HOUR")"
total_events="$(clickhouse_scalar "$container" "SELECT count() FROM $event_storage_table")"
relational_bytes="$(postgres_scalar "SELECT pg_database_size(current_database())")"
fs_total_bytes="$(filesystem_total_bytes)"
object_bytes="$(directory_bytes "$object_storage_path")"
disk_free_percent="$(filesystem_free_percent)"

previous_epoch="$(state_value "recorded_at_epoch")"
[[ "$previous_epoch" =~ ^[0-9]+$ ]] || previous_epoch=""

events_per_day="unknown"
if [[ "$window_events" =~ ^[0-9]+$ ]]; then
  events_per_day=$(( window_events * 24 / window_hours ))
fi

growth_for() {
  local class="$1"
  local absolute="$2"
  local previous
  previous="$(state_value "sample_class=$class absolute_bytes")"
  if [[ "$previous" =~ ^[0-9]+$ ]] && [[ -n "$previous_epoch" ]] \
    && [[ "$absolute" =~ ^[0-9]+$ ]] && (( now_epoch > previous_epoch )); then
    local elapsed_hours=$(( (now_epoch - previous_epoch) / 3600 ))
    if (( elapsed_hours > 0 )); then
      local delta=$(( absolute - previous ))
      (( delta < 0 )) && delta=0
      printf '%s %s' "$(( delta * 24 / elapsed_hours ))" "previous_sample"
      return 0
    fi
  fi
  if [[ "$absolute" =~ ^[0-9]+$ ]] && [[ "$events_bytes" =~ ^[0-9]+$ ]] && [[ "$total_events" =~ ^[0-9]+$ ]] \
    && (( total_events > 0 )) && [[ "$events_per_day" =~ ^[0-9]+$ ]]; then
    # Measured sizes with the observed event rate: the class grows with the same
    # event volume that the events table already carries.
    printf '%s' "$(( absolute * events_per_day / total_events ))"
    printf ' %s' "event_rate_and_average_event_size"
    return 0
  fi
  printf 'unknown unknown'
}

per_1000_events() {
  local per_day="$1"
  if [[ "$per_day" =~ ^[0-9]+$ ]] && [[ "$events_per_day" =~ ^[0-9]+$ ]] && (( events_per_day > 0 )); then
    printf '%s' "$(( per_day * 1000 / events_per_day ))"
  else
    printf 'unknown'
  fi
}

projection() {
  local absolute="$1"
  local per_day="$2"
  local days="$3"
  if [[ "$absolute" =~ ^[0-9]+$ ]] && [[ "$per_day" =~ ^[0-9]+$ ]]; then
    printf '%s' "$(( absolute + per_day * days ))"
  else
    printf 'unknown'
  fi
}

report_class() {
  local class="$1"
  local absolute="$2"
  local growth basis per_day
  growth="$(growth_for "$class" "$absolute")"
  per_day="${growth%% *}"
  basis="${growth##* }"
  printf 'storage_class=%s absolute_bytes=%s window_hours=%s events_in_window=%s bytes_per_day=%s bytes_per_1000_events=%s projected_bytes_12_months=%s projected_bytes_36_months=%s analytics_disk_free_percent=%s recorded_at=%s growth_basis=%s\n' \
    "$class" "${absolute:-unknown}" "$window_hours" "${window_events:-unknown}" "$per_day" \
    "$(per_1000_events "$per_day")" "$(projection "$absolute" "$per_day" 365)" \
    "$(projection "$absolute" "$per_day" 1095)" "$disk_free_percent" "$recorded_at" "$basis"
}

report_class "analytics_filesystem_total" "$fs_total_bytes"
report_class "relational" "$relational_bytes"
report_class "events" "$events_bytes"
report_class "object_storage" "$object_bytes"

printf 'analytics_retention_event_days=%s\n' "${POSTHOG_EVENT_RETENTION_DAYS:-365}"
printf 'events_table=%s\n' "$events_table"
printf 'event_storage_table=%s\n' "$event_storage_table"
printf 'content_policy=metadata_only_storage_sizes_and_counts\n'
printf 'next_step=copy_the_rows_above_into_docs/analytics/product-analytics-capacity-baseline.md_and_record_pending_operator_receipt_until_the_run_happens\n'

mkdir -p "$(dirname "$state_file")"
tmp_file="$(mktemp "$state_file.XXXXXX")"
{
  printf 'storage_sample_version=1\n'
  printf 'recorded_at=%s\n' "$recorded_at"
  printf 'recorded_at_epoch=%s\n' "$now_epoch"
  printf 'window_hours=%s\n' "$window_hours"
  printf 'events_in_window=%s\n' "${window_events:-unknown}"
  printf 'total_events=%s\n' "${total_events:-unknown}"
  printf 'analytics_disk_free_percent=%s\n' "$disk_free_percent"
  printf 'analytics_filesystem_total=%s\n' "${fs_total_bytes:-unknown}"
  printf 'relational=%s\n' "${relational_bytes:-unknown}"
  printf 'events=%s\n' "${events_bytes:-unknown}"
  printf 'object_storage=%s\n' "${object_bytes:-unknown}"
  for class in analytics_filesystem_total relational events object_storage; do
    case "$class" in
      analytics_filesystem_total) absolute="$fs_total_bytes" ;;
      relational) absolute="$relational_bytes" ;;
      events) absolute="$events_bytes" ;;
      *) absolute="$object_bytes" ;;
    esac
    printf 'sample_class=%s absolute_bytes=%s\n' "$class" "${absolute:-unknown}"
  done
} > "$tmp_file"
chmod 0640 "$tmp_file" 2>/dev/null || true
mv "$tmp_file" "$state_file"

printf 'storage_growth_result=pass\n'
printf 'storage_state_file=%s\n' "$(basename "$state_file")"
exit 0
