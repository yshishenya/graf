#!/usr/bin/env bash
set -euo pipefail

# T109: scheduled policy verification, never an age-based purge.
# Explicit deletion decisions use the separate legal-basis lifecycle path.
umask 077
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
state_dir="${GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR:-/var/lib/graf-posthog-retention}"
state_file="$state_dir/retention-state"
compose_file="${GRAF_APP_COMPOSE_FILE:-$repo_root/infra/docker-compose.yml}"
database_service="${GRAF_PRODUCT_ANALYTICS_DATABASE_SERVICE:-rec-postgres}"
database_name="${GRAF_PRODUCT_ANALYTICS_DATABASE_NAME:-twobrain_rec}"
database_user="${GRAF_PRODUCT_ANALYTICS_DATABASE_USER:-twobrain_rec}"
alert_script="${GRAF_POSTHOG_ALERT_SCRIPT:-$repo_root/infra/scripts/alert-analytics-degradation.sh}"
clickhouse_container_hint="${GRAF_PRODUCT_ANALYTICS_CLICKHOUSE_CONTAINER:-}"
posthog_project="${GRAF_POSTHOG_PROJECT:-graf-posthog}"
retention_mode="${GRAF_PRODUCT_ANALYTICS_RETENTION_MODE:-}"
mode="dry-run"
categories=(measurement_events anonymous_aggregate visit_attribution acquisition_attribute)

retention_category_for() {
  case "$1" in
    measurement_events) printf posthog_product_events ;;
    anonymous_aggregate) printf anonymous_page_aggregate ;;
    visit_attribution) printf visit_attribution ;;
    acquisition_attribute) printf client_acquisition_attribute ;;
    *) return 1 ;;
  esac
}
table_for() {
  case "$1" in
    anonymous_aggregate) printf anonymous_page_aggregate_buckets ;;
    visit_attribution) printf public_visit_attributions ;;
    acquisition_attribute) printf client_acquisition_attributes ;;
    *) return 1 ;;
  esac
}
while (( $# > 0 )); do
  case "$1" in
    --dry-run) mode=dry-run ;;
    --execute) mode=execute ;;
    --status) mode=status ;;
    --help|-h) echo "usage: $0 [--dry-run|--execute|--status]"; exit 0 ;;
    *) echo 'retention_result=failed'; echo 'reason=unsupported_argument'; exit 2 ;;
  esac
  shift
done
if [[ "$mode" == status ]]; then
  if [[ -r "$state_file" ]]; then cat "$state_file"; else echo 'retention_state=missing'; fi
  exit 0
fi

failure_reason=""
if [[ "$retention_mode" != until_decision ]]; then
  failure_reason=retention_mode_missing_or_unknown
elif [[ -n "${POSTHOG_EVENT_RETENTION_DAYS:-}" ]]; then
  failure_reason=legacy_age_configuration
fi
if [[ "$mode" == dry-run ]]; then
  [[ -z "$failure_reason" ]] || { printf 'retention_result=failed\nreason=%s\n' "$failure_reason"; exit 2; }
  printf 'retention_result=dry_run\nretention_mode=until_decision\nrows_deleted_total=0\n'
  exit 0
fi

now_epoch="$(date +%s)"
recorded_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
[[ "$now_epoch" =~ ^[0-9]+$ ]] || failure_reason=clock_unavailable
if ! command -v docker >/dev/null 2>&1; then failure_reason=docker_unavailable; fi

psql_scalar() {
  docker compose -f "$compose_file" exec -T "$database_service" \
    psql -U "$database_user" -d "$database_name" -tAqc "$1" 2>/dev/null | tr -d '[:space:]'
}
category_lines=""
missing_categories=""
for category in "${categories[@]}"; do
  storage=postgres
  verified=false
  if [[ "$category" == measurement_events ]]; then storage=clickhouse; fi
  if [[ -z "$failure_reason" ]]; then
    if [[ "$category" == measurement_events ]]; then
      container="$clickhouse_container_hint"
      if [[ -z "$container" ]]; then
        container="$(docker ps --filter "label=com.docker.compose.project=$posthog_project" \
          --filter 'label=com.docker.compose.service=clickhouse' -q 2>/dev/null | awk 'NF {print; exit}' || true)"
      fi
      observed=""
      if [[ -n "$container" ]]; then
        observed="$(docker exec "$container" clickhouse-client --query \
          "SELECT if(count() = 1, toString(countIf(match(create_table_query, '(?i)\\\\bTTL\\\\b'))), 'unknown') FROM system.tables WHERE database = 'posthog' AND name = 'sharded_events'" \
          2>/dev/null | tr -d '[:space:]' || true)"
      fi
      if [[ "$observed" == 0 ]]; then verified=true; else failure_reason=age_ttl_present_or_unknown; fi
    else
      table="$(table_for "$category")"
      exists="$(psql_scalar "SELECT to_regclass('public.$table') IS NOT NULL" || true)"
      if [[ "$exists" == t ]]; then
        verified=true
      else
        failure_reason=retention_category_missing
        missing_categories="$missing_categories $category"
      fi
    fi
  fi
  category_lines="$category_lines
category=$category retention_mode=until_decision retention_days=none storage=$storage enforcement=decision_required retention_rule=$(retention_category_for "$category") last_enforced_at=$recorded_at rows_deleted=0 enforcement_verified=$verified"
done

result=pass
[[ -z "$failure_reason" ]] || result=failed
mkdir -p "$state_dir"
tmp_file="$(mktemp "$state_file.XXXXXX")"
trap 'rm -f "$tmp_file"' EXIT
{
  printf 'retention_state_version=2\nrecorded_at=%s\nrecorded_at_epoch=%s\n' "$recorded_at" "$now_epoch"
  printf 'result=%s\nreason=%s\nretention_mode=until_decision\n' "$result" "${failure_reason:-none}"
  printf 'required_categories=%s\nrows_deleted_total=0\n' "${#categories[@]}"
  printf '%s\n' "$category_lines" | sed '/^$/d'
  for category in $missing_categories; do printf 'missing_category=%s\n' "$category"; done
  printf 'content_policy=metadata_only_no_visitor_or_user_data\nproduct_impact=measurement_gap_only\n'
} > "$tmp_file"
chmod 0640 "$tmp_file"
mv "$tmp_file" "$state_file"
if [[ "$result" != pass ]]; then
  printf 'retention_result=failed\nreason=%s\n' "$failure_reason"
  logger -t graf-posthog-retention "level=critical result=retention_enforcement_failed reason=$failure_reason" 2>/dev/null || true
  if [[ -x "$alert_script" ]]; then
    if "$alert_script" >/dev/null 2>&1; then echo 'retention_alert=delivered'; else echo 'retention_alert=delivery_failed'; fi
  else
    echo 'retention_alert=script_missing'
  fi
  exit 1
fi
printf 'retention_result=pass\nretention_mode=until_decision\nrows_deleted_total=0\n'
