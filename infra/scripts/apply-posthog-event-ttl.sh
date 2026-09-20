#!/usr/bin/env bash
set -euo pipefail

# Apply the forced row lifetime for measurement events in the PostHog ClickHouse
# store (FR-036, SC-011).
#
# The committed Compose file is a metadata-only handoff for the generated
# PostHog runtime, so the TTL cannot be declared there as a running service
# setting. This task applies the reviewed statement from
# `infra/posthog/clickhouse-retention.sql` to the running analytics stack and
# verifies the enforced interval afterwards. The scheduled retention task
# (`enforce-product-analytics-retention.sh`) fails closed when the verified TTL
# is missing or shorter than the approved term.
#
# Usage:
#   apply-posthog-event-ttl.sh              # dry run, prints the statement
#   apply-posthog-event-ttl.sh --execute
#   apply-posthog-event-ttl.sh --status

umask 077

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
sql_template="${GRAF_POSTHOG_EVENT_TTL_SQL:-$repo_root/infra/posthog/clickhouse-retention.sql}"
posthog_project="${GRAF_POSTHOG_PROJECT:-graf-posthog}"
clickhouse_container_hint="${GRAF_POSTHOG_CLICKHOUSE_CONTAINER:-}"
retention_days="${POSTHOG_EVENT_RETENTION_DAYS:-365}"
mode="dry-run"

usage() {
  cat >&2 <<EOF
usage: $0 [--dry-run|--execute|--status] [--days <n>]
EOF
}

while (( $# > 0 )); do
  case "$1" in
    --dry-run) mode="dry-run" ;;
    --execute) mode="execute" ;;
    --status) mode="status" ;;
    --days)
      (( $# > 1 )) || { usage; exit 2; }
      retention_days="$2"
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

log_event() {
  local level="$1"
  shift
  logger -t graf-posthog-event-ttl "level=$level $*" 2>/dev/null || true
}

if [[ ! "$retention_days" =~ ^[0-9]+$ ]] || (( retention_days <= 0 )); then
  echo "posthog_event_ttl_result=failed"
  echo "reason=retention_days_invalid"
  exit 2
fi
if [[ ! -r "$sql_template" ]]; then
  echo "posthog_event_ttl_result=failed"
  echo "reason=ttl_sql_missing"
  exit 2
fi

clickhouse_container() {
  if [[ -n "$clickhouse_container_hint" ]]; then
    printf '%s' "$clickhouse_container_hint"
    return 0
  fi
  docker ps --filter "label=com.docker.compose.project=$posthog_project" \
    --filter "label=com.docker.compose.service=clickhouse" -q 2>/dev/null | awk 'NF {print; exit}'
}

clickhouse_query() {
  local container="$1"
  local query="$2"
  [[ -n "$container" ]] || return 1
  docker exec "$container" clickhouse-client --query "$query" 2>/dev/null
}

enforced_ttl_days() {
  local container="$1"
  clickhouse_query "$container" \
    "SELECT extract(create_table_query, 'TTL[^0-9]*([0-9]+)') FROM system.tables WHERE database = currentDatabase() AND name = 'sharded_events' LIMIT 1" \
    | tr -d '[:space:]'
}

statement="$(sed "s/{{RETENTION_DAYS}}/$retention_days/g" "$sql_template" | sed '/^--/d' | sed '/^$/d')"

if [[ "$mode" == "status" ]]; then
  container="$(clickhouse_container)"
  ttl_days="$(enforced_ttl_days "$container" || true)"
  printf 'posthog_event_ttl_days=%s\n' "${ttl_days:-unknown}"
  printf 'posthog_event_ttl_expected_days=%s\n' "$retention_days"
  printf 'posthog_event_ttl_required_table=sharded_events\n'
  exit 0
fi

if [[ "$mode" != "execute" ]]; then
  echo "posthog_event_ttl_result=dry_run"
  echo "posthog_event_ttl_expected_days=$retention_days"
  echo "posthog_event_ttl_required_table=sharded_events"
  printf 'statement=%s\n' "$(printf '%s' "$statement" | tr '\n' ' ' | tr -s ' ')"
  echo "next_step=run_with_--execute_on_the_analytics_host"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "posthog_event_ttl_result=failed"
  echo "reason=docker_unavailable"
  exit 1
fi
container="$(clickhouse_container)"
if [[ -z "$container" ]]; then
  echo "posthog_event_ttl_result=failed"
  echo "reason=clickhouse_container_not_found"
  exit 1
fi

if ! printf '%s\n' "$statement" | docker exec -i "$container" clickhouse-client --multiquery >/dev/null 2>&1; then
  echo "posthog_event_ttl_result=failed"
  echo "reason=ttl_statement_failed"
  log_event critical "result=event_ttl_failed reason=ttl_statement_failed"
  exit 1
fi

ttl_days="$(enforced_ttl_days "$container" || true)"
if [[ ! "$ttl_days" =~ ^[0-9]+$ ]] || (( ttl_days < retention_days )); then
  echo "posthog_event_ttl_result=failed"
  echo "reason=ttl_not_verified"
  echo "posthog_event_ttl_days=${ttl_days:-unknown}"
  log_event critical "result=event_ttl_failed reason=ttl_not_verified observed=${ttl_days:-unknown}"
  exit 1
fi

printf 'posthog_event_ttl_result=pass\n'
printf 'posthog_event_ttl_days=%s\n' "$ttl_days"
printf 'posthog_event_ttl_table=sharded_events\n'
printf 'posthog_event_ttl_enforcement=row_ttl\n'
log_event pass "result=event_ttl_enforced days=$ttl_days table=sharded_events"
exit 0
