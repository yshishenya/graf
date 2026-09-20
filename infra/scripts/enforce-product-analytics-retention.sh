#!/usr/bin/env bash
set -euo pipefail

# Forced analytics retention enforcement (FR-036, FR-050, SC-011).
#
# Two storage systems need two mechanisms, so this task covers both in one
# scheduled run and records one state file:
#
#   ClickHouse (inside PostHog): events of measurement levels 2 and 3 carry a
#     row TTL of POSTHOG_EVENT_RETENTION_DAYS (default 365). The task verifies
#     that the TTL exists; the TTL itself is applied by
#     `infra/scripts/apply-posthog-event-ttl.sh`, because ClickHouse deletes
#     expired rows during merges and does not need a per-row delete loop.
#
#   PostgreSQL (product database): only the anonymous aggregate, the visit
#     attribution row and the client acquisition attribute are deleted by age,
#     with an explicit statement per category. Every deletion is logged with the
#     row count it removed. The table names and age columns are an exact allowlist
#     from the SQLAlchemy models and Alembic migrations.
#
# Missing retention term, category mapping, table or age column is a
# configuration/schema error, never "keep forever" (FR-050). The run validates
# every target before issuing any local DELETE; on a failed preflight it records
# the failure and deletes nothing.
#
# The provider path is metadata-only: it reads ClickHouse system metadata to
# verify the configured TTL and never deletes provider-held rows. Local billing
# provider-event metadata is not an analytics retention category and is
# deliberately outside this script's scope.
#
# Logged metadata is limited to category names, configured terms, table names,
# row counts and timestamps. No visitor, user or provider payload is selected,
# copied or printed.
#
# Usage:
#   enforce-product-analytics-retention.sh                # dry run
#   enforce-product-analytics-retention.sh --execute
#   enforce-product-analytics-retention.sh --status

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
event_retention_days="${POSTHOG_EVENT_RETENTION_DAYS:-365}"
mode="dry-run"

# Required categories and their terms. A category without a term, or with a term
# below the required minimum, fails the run (FR-050).
categories=(
  "measurement_events:365:clickhouse:row_ttl"
  "anonymous_aggregate:1095:postgres:scheduled_task"
  "visit_attribution:90:postgres:scheduled_task"
  "acquisition_attribute:1095:postgres:scheduled_task"
)

# Operational retention-state keys are deliberately mapped to the canonical
# rules in product_analytics/retention.py. Keep this mapping explicit: silently
# treating an unknown key as a table or a timestamp would make deletion unsafe.
retention_category_for() {
  case "$1" in
    measurement_events) printf 'posthog_product_events' ;;
    anonymous_aggregate) printf 'anonymous_page_aggregate' ;;
    visit_attribution) printf 'visit_attribution' ;;
    acquisition_attribute) printf 'client_acquisition_attribute' ;;
    *) return 1 ;;
  esac
}

timestamp_column_for() {
  case "$1" in
    anonymous_aggregate) printf 'bucket_date' ;;
    visit_attribution) printf 'expires_at' ;;
    acquisition_attribute) printf 'captured_at' ;;
    *) return 1 ;;
  esac
}

table_candidates_for() {
  # These are exact, allow-listed table names from the SQLAlchemy models and
  # migrations. There is intentionally no fallback to the category name: a
  # missing mapping must fail closed instead of deleting an unrelated table.
  case "$1" in
    anonymous_aggregate) printf 'anonymous_page_aggregate_buckets' ;;
    visit_attribution) printf 'public_visit_attributions' ;;
    acquisition_attribute) printf 'client_acquisition_attributes' ;;
    *) return 1 ;;
  esac
}

usage() {
  cat >&2 <<EOF
usage: $0 [--dry-run|--execute|--status]
EOF
}

while (( $# > 0 )); do
  case "$1" in
    --dry-run) mode="dry-run" ;;
    --execute) mode="execute" ;;
    --status) mode="status" ;;
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
  logger -t graf-posthog-retention "level=$level $*" 2>/dev/null || true
}

now_epoch="$(date +%s 2>/dev/null || printf '')"
recorded_at_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf 'unknown')"
if [[ ! "$now_epoch" =~ ^[0-9]+$ ]]; then
  echo "retention_result=failed"
  echo "reason=clock_unavailable"
  exit 1
fi

if [[ "$mode" == "status" ]]; then
  if [[ -r "$state_file" ]]; then
    cat "$state_file"
  else
    printf 'retention_state=missing\n'
  fi
  exit 0
fi

if [[ ! "$event_retention_days" =~ ^[0-9]+$ ]] || (( event_retention_days <= 0 )); then
  echo "retention_result=failed"
  echo "reason=event_retention_days_invalid"
  exit 2
fi
# The script's local contract requires 365 days for measurement events. A
# shorter environment value must fail before any PostgreSQL probe or DELETE;
# comparing the live TTL only with its own shorter value would be fail-open.
required_measurement_event_days=365
if (( event_retention_days < required_measurement_event_days )); then
  echo "retention_result=failed"
  echo "reason=retention_term_below_required:measurement_events"
  exit 2
fi

psql_scalar() {
  local query="$1"
  docker compose -f "$compose_file" exec -T "$database_service" \
    psql -U "$database_user" -d "$database_name" -tAqc "$query" 2>/dev/null
}

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
  [[ -n "$container" ]] || return 1
  docker exec "$container" clickhouse-client --query "$query" 2>/dev/null | tr -d '[:space:]'
}

raise_alert() {
  [[ -x "$alert_script" ]] || { log_event warning "result=alert_script_missing"; return 0; }
  if "$alert_script" >/dev/null 2>&1; then
    printf 'retention_alert=delivered\n'
  else
    printf 'retention_alert=delivery_failed\n'
  fi
}

category_state_lines=""
missing_categories=""
failure_reason=""
preflight_failed="false"
declare -a planned_tables planned_columns clickhouse_ttl_days

if [[ "$mode" != "execute" ]]; then
  echo "retention_result=dry_run"
  echo "event_retention_days=$event_retention_days"
  for entry in "${categories[@]}"; do
    category="${entry%%:*}"
    remainder="${entry#*:}"
    term="${remainder%%:*}"
    remainder="${remainder#*:}"
    storage="${remainder%%:*}"
    enforcement="${remainder#*:}"
    table_name="$(table_candidates_for "$category" || true)"
    timestamp_column="$(timestamp_column_for "$category" || true)"
    printf 'category=%s retention_days=%s storage=%s enforcement=%s table_candidates="%s" timestamp_column=%s\n' \
      "$category" "$term" "$storage" "$enforcement" "$table_name" "${timestamp_column:-missing}"
  done
  echo "database_service=$database_service"
  echo "next_step=run_with_--execute_on_the_product_host"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  failure_reason="docker_unavailable"
  preflight_failed="true"
fi

# Preflight every target before issuing any DELETE. This is intentionally a
# separate pass: a missing table/column later in the list must not leave earlier
# categories partially purged.
if [[ "$preflight_failed" == "false" ]]; then
  category_index=0
  for entry in "${categories[@]}"; do
    category="${entry%%:*}"
    remainder="${entry#*:}"
    term="${remainder%%:*}"
    remainder="${remainder#*:}"
    storage="${remainder%%:*}"
    enforcement="${remainder#*:}"
    planned_tables[$category_index]=""
    planned_columns[$category_index]=""
    clickhouse_ttl_days[$category_index]=""

    canonical_category="$(retention_category_for "$category" || true)"
    if [[ -z "$canonical_category" ]]; then
      failure_reason="retention_category_mapping_invalid"
      missing_categories="$missing_categories $category"
      preflight_failed="true"
      category_index=$((category_index + 1))
      continue
    fi
    if [[ ! "$term" =~ ^[0-9]+$ ]] || (( term <= 0 )); then
      # Absence of a term is a configuration error, not indefinite retention.
      missing_categories="$missing_categories $category"
      failure_reason="${failure_reason:-retention_term_missing}"
      preflight_failed="true"
      category_index=$((category_index + 1))
      continue
    fi

    if [[ "$storage" == "clickhouse" ]]; then
      container="$(clickhouse_container)"
      ttl_days="$(clickhouse_scalar "$container" "SELECT extract(create_table_query, 'TTL[^0-9]*([0-9]+)') FROM system.tables WHERE name = 'sharded_events' LIMIT 1" || true)"
      if [[ "$ttl_days" =~ ^[0-9]+$ ]] && (( ttl_days >= event_retention_days )); then
        clickhouse_ttl_days[$category_index]="$ttl_days"
        printf 'clickhouse_ttl_days=%s\n' "$ttl_days"
      else
        enforcement_verified="false"
        failure_reason="${failure_reason:-clickhouse_ttl_not_enforced}"
        preflight_failed="true"
      fi
      category_index=$((category_index + 1))
      continue
    fi

    if [[ "$storage" != "postgres" || "$enforcement" != "scheduled_task" ]]; then
      failure_reason="${failure_reason:-retention_enforcement_mapping_invalid}"
      preflight_failed="true"
      category_index=$((category_index + 1))
      continue
    fi

    table_name="$(table_candidates_for "$category" || true)"
    timestamp_column="$(timestamp_column_for "$category" || true)"
    if [[ -z "$table_name" || -z "$timestamp_column" ]]; then
      failure_reason="${failure_reason:-retention_schema_mapping_invalid}"
      preflight_failed="true"
      missing_categories="$missing_categories $category"
      category_index=$((category_index + 1))
      continue
    fi

    exists="$(psql_scalar "SELECT to_regclass('public.$table_name') IS NOT NULL" || true)"
    if [[ "$exists" != "t" ]]; then
      # Keep the historical blocker code for an absent category/table.
      missing_categories="$missing_categories $category"
      preflight_failed="true"
      category_index=$((category_index + 1))
      continue
    fi
    column_exists="$(psql_scalar "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = '$table_name' AND column_name = '$timestamp_column')" || true)"
    if [[ "$column_exists" != "t" ]]; then
      failure_reason="${failure_reason:-retention_schema_mismatch}"
      preflight_failed="true"
      missing_categories="$missing_categories $category"
      category_index=$((category_index + 1))
      continue
    fi

    planned_tables[$category_index]="$table_name"
    planned_columns[$category_index]="$timestamp_column"
    category_index=$((category_index + 1))
  done
fi

if [[ "$preflight_failed" == "false" && -z "$missing_categories" ]]; then
  category_index=0
  for entry in "${categories[@]}"; do
    category="${entry%%:*}"
    remainder="${entry#*:}"
    term="${remainder%%:*}"
    remainder="${remainder#*:}"
    storage="${remainder%%:*}"
    enforcement="${remainder#*:}"

    if [[ "$storage" == "clickhouse" ]]; then
      clickhouse_verified="${clickhouse_ttl_days[$category_index]:-}"
      if [[ -n "$clickhouse_verified" ]]; then
        enforcement_verified="true"
      else
        enforcement_verified="false"
      fi
      category_state_lines="$category_state_lines
category=$category retention_days=$event_retention_days storage=clickhouse enforcement=$enforcement retention_rule=$(retention_category_for "$category") last_enforced_at=$recorded_at_iso rows_deleted=0 enforcement_verified=$enforcement_verified"
      category_index=$((category_index + 1))
      continue
    fi

    table_name="${planned_tables[$category_index]}"
    timestamp_column="${planned_columns[$category_index]}"
    interval_days="$term"
    if [[ "$category" == "visit_attribution" ]]; then
      # The visit attribution row carries its own expiry moment.
      predicate="$timestamp_column < now()"
    else
      predicate="$timestamp_column < (now() - interval '$interval_days days')"
    fi
    deleted="$(psql_scalar "WITH deleted AS (DELETE FROM public.$table_name WHERE $predicate RETURNING 1) SELECT count(*) FROM deleted" || true)"
    if [[ ! "$deleted" =~ ^[0-9]+$ ]]; then
      failure_reason="retention_delete_failed"
      deleted=0
      enforcement_verified="false"
    else
      enforcement_verified="true"
      log_event pass "result=retention_deleted category=$category table=$table_name rows=$deleted retention_days=$interval_days"
      printf 'category=%s table=%s rows_deleted=%s\n' "$category" "$table_name" "$deleted"
    fi
    category_state_lines="$category_state_lines
category=$category retention_days=$term storage=$storage enforcement=$enforcement retention_rule=$(retention_category_for "$category") table=$table_name age_column=$timestamp_column last_enforced_at=$recorded_at_iso rows_deleted=$deleted enforcement_verified=$enforcement_verified"
    category_index=$((category_index + 1))
  done
else
  # A failed preflight is recorded for every required category, and no DELETE
  # has been issued. Do not claim a category was enforced merely because its
  # table happened to resolve before another category failed.
  for entry in "${categories[@]}"; do
    category="${entry%%:*}"
    remainder="${entry#*:}"
    term="${remainder%%:*}"
    remainder="${remainder#*:}"
    storage="${remainder%%:*}"
    enforcement="${remainder#*:}"
    category_state_lines="$category_state_lines
category=$category retention_days=$term storage=$storage enforcement=$enforcement retention_rule=$(retention_category_for "$category" || printf unknown) last_enforced_at=$recorded_at_iso rows_deleted=0 enforcement_verified=false"
  done
fi

missing_category_lines=""
for category in $missing_categories; do
  missing_category_lines="$missing_category_lines
missing_category=$category"
done

result="pass"
[[ -n "$failure_reason" ]] && result="failed"
if [[ -n "$missing_categories" ]]; then
  result="failed"
  failure_reason="${failure_reason:-retention_category_missing}"
fi

mkdir -p "$(dirname "$state_file")"
tmp_file="$(mktemp "$state_file.XXXXXX")"
{
  printf 'retention_state_version=1\n'
  printf 'recorded_at=%s\n' "$recorded_at_iso"
  printf 'recorded_at_epoch=%s\n' "$now_epoch"
  printf 'result=%s\n' "$result"
  printf 'reason=%s\n' "${failure_reason:-none}"
  printf 'event_retention_days=%s\n' "$event_retention_days"
  printf 'required_categories=%s\n' "${#categories[@]}"
  printf 'missing_categories=%s\n' "$( [[ -z "$missing_categories" ]] && printf none || printf '%s' "$missing_categories" )"
  printf 'rows_deleted_total=%s\n' "$(printf '%s\n' "$category_state_lines" | awk -F 'rows_deleted=' 'NF > 1 {split($2, parts, " "); total += parts[1]} END {print total + 0}')"
  printf '%s\n' "$category_state_lines" | sed '/^$/d'
  printf '%s\n' "$missing_category_lines" | sed '/^$/d'
  printf 'content_policy=metadata_only_no_visitor_or_user_data\n'
  printf 'product_impact=measurement_gap_only\n'
} > "$tmp_file"
chmod 0640 "$tmp_file" 2>/dev/null || true
mv "$tmp_file" "$state_file"

if [[ "$result" != "pass" ]]; then
  echo "retention_result=failed"
  echo "reason=${failure_reason:-retention_category_missing}"
  echo "missing_categories=$( [[ -z "$missing_categories" ]] && printf none || printf '%s' "$missing_categories" )"
  raise_alert
  log_event critical "result=retention_enforcement_failed reason=${failure_reason:-retention_category_missing}"
  exit 1
fi

log_event pass "result=retention_enforcement_pass categories=${#categories[@]}"
echo "retention_result=pass"
echo "categories_enforced=${#categories[@]}"
echo "event_retention_days=$event_retention_days"
echo "product_impact=measurement_gap_only"
exit 0
