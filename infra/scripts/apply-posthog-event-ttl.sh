#!/usr/bin/env bash
set -euo pipefail

# T109: remove the old event TTL; no data deletion is performed here.
umask 077
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
sql_template="${GRAF_POSTHOG_EVENT_TTL_SQL:-$repo_root/infra/posthog/clickhouse-retention.sql}"
posthog_project="${GRAF_POSTHOG_PROJECT:-graf-posthog}"
container_hint="${GRAF_POSTHOG_CLICKHOUSE_CONTAINER:-}"
retention_mode="${GRAF_PRODUCT_ANALYTICS_RETENTION_MODE:-}"
mode="dry-run"

while (( $# > 0 )); do
  case "$1" in
    --dry-run) mode="dry-run" ;;
    --execute) mode="execute" ;;
    --status) mode="status" ;;
    --help|-h) echo "usage: $0 [--dry-run|--execute|--status]"; exit 0 ;;
    *) echo "posthog_event_ttl_result=failed"; echo "reason=unsupported_argument"; exit 2 ;;
  esac
  shift
done

fail() {
  printf 'posthog_event_ttl_result=failed\nreason=%s\n' "$1"
  logger -t graf-posthog-event-ttl "level=critical result=event_ttl_failed reason=$1" 2>/dev/null || true
  exit 1
}

[[ "$retention_mode" == "until_decision" ]] || fail retention_mode_missing_or_unknown
[[ -z "${POSTHOG_EVENT_RETENTION_DAYS:-}" ]] || fail legacy_age_configuration
[[ -r "$sql_template" ]] || fail ttl_sql_missing
statement="$(sed '/^--/d' "$sql_template" | tr '\n' ' ' | tr -s ' ' | sed 's/^ //;s/ $//')"
[[ "$statement" == 'ALTER TABLE posthog.sharded_events REMOVE TTL;' ]] || fail ttl_statement_conflicts_with_policy

if [[ "$mode" == "dry-run" ]]; then
  printf 'posthog_event_ttl_result=dry_run\nretention_mode=until_decision\nstatement=%s\n' "$statement"
  exit 0
fi

command -v docker >/dev/null 2>&1 || fail docker_unavailable
container="$container_hint"
if [[ -z "$container" ]]; then
  container="$(docker ps --filter "label=com.docker.compose.project=$posthog_project" \
    --filter 'label=com.docker.compose.service=clickhouse' -q 2>/dev/null | awk 'NF {print; exit}' || true)"
fi
[[ -n "$container" ]] || fail clickhouse_container_not_found

ttl_present() {
  docker exec "$container" clickhouse-client --query \
    "SELECT if(count() = 1, toString(countIf(match(create_table_query, '(?i)\\\\bTTL\\\\b'))), 'unknown') FROM system.tables WHERE database = 'posthog' AND name = 'sharded_events'" \
    2>/dev/null | tr -d '[:space:]'
}
observed="$(ttl_present || true)"
[[ "$observed" == 0 || "$observed" == 1 ]] || fail ttl_observation_unknown
if [[ "$observed" == 1 && "$mode" == execute ]]; then
  printf '%s\n' "$statement" | docker exec -i "$container" clickhouse-client --multiquery >/dev/null 2>&1 \
    || fail ttl_statement_failed
  observed="$(ttl_present || true)"
fi
printf 'posthog_event_ttl_present=%s\n' "${observed:-unknown}"
[[ "$observed" == 0 ]] || fail age_ttl_still_present
printf 'posthog_event_ttl_result=pass\nretention_mode=until_decision\nposthog_event_ttl_enforcement=decision_required\n'
