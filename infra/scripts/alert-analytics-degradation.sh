#!/usr/bin/env bash
set -euo pipefail

# External degradation alert for GRAF product analytics (FR-030, FR-054, FR-055,
# FR-056, SC-009).
#
# The measured server cannot report its own outage, so degradation is delivered
# through an external channel: a Telegram bot. The bot token and the chat
# identifier come only from the environment or from root-owned files outside
# git; they are never written to the repository, to state files, or to output.
#
# The message body carries metadata only: scope, rule codes, threshold values,
# timestamps and owner roles. It never carries visitor or user data, provider
# payloads, account identifiers or event content (FR-054).
#
# Delivery deadline is at most 15 minutes from the start of a degradation
# (SC-009). The systemd timer runs every 5 minutes and the guard writes its
# state file every minute, so the deadline is met with margin. Repeat messages
# for an unchanged condition are suppressed for GRAF_ANALYTICS_ALERT_REPEAT_MINUTES
# so the channel stays readable; a changed condition is always delivered.
#
# Channel availability is detected on an independent path (FR-056):
# `--check-channel` probes the channel provider API directly, records the
# result, verifies that the guard state and the last delivery are fresh, and
# escalates through GRAF_ANALYTICS_ALERT_FALLBACK_URL when that independent
# transport is configured. Failure is recorded locally in journald as well, so
# detection does not depend on the same channel delivering the notice.
#
# Usage:
#   alert-analytics-degradation.sh [--dry-run] [--print-message]
#   alert-analytics-degradation.sh --drill          # training alert (SC-009)
#   alert-analytics-degradation.sh --check-channel  # channel outage detection
#   alert-analytics-degradation.sh --status

umask 077

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
state_dir="${GRAF_ANALYTICS_ALERT_STATE_DIR:-/var/lib/graf-analytics-alert}"
guard_state_file="${GRAF_ANALYTICS_GUARD_STATE_FILE:-${GRAF_POSTHOG_GUARD_STATE_DIR:-/var/lib/graf-posthog-runtime-guard}/alert-state}"
backup_state_file="${GRAF_ANALYTICS_BACKUP_STATE_FILE:-${GRAF_POSTHOG_BACKUP_STATE_DIR:-/var/lib/graf-posthog-backup}/backup-state}"
restore_state_file="${GRAF_ANALYTICS_RESTORE_STATE_FILE:-${GRAF_POSTHOG_BACKUP_STATE_DIR:-/var/lib/graf-posthog-backup}/restore-state}"
retention_state_file="${GRAF_ANALYTICS_RETENTION_STATE_FILE:-${GRAF_PRODUCT_ANALYTICS_RETENTION_STATE_DIR:-/var/lib/graf-posthog-retention}/retention-state}"
rules_file="${GRAF_ANALYTICS_ALERT_RULES_FILE:-/etc/graf-analytics-alert-rules.txt}"
repeat_minutes="${GRAF_ANALYTICS_ALERT_REPEAT_MINUTES:-60}"
guard_state_max_age_minutes="${GRAF_ANALYTICS_ALERT_STATE_MAX_AGE_MINUTES:-15}"
# A newly installed channel has no delivery record until the first alert or
# drill. The existing state-age setting is the explicit, compatible first-run
# grace window; no new credential or configuration surface is required.
first_run_grace_minutes="$guard_state_max_age_minutes"
backup_max_age_hours="${GRAF_POSTHOG_BACKUP_MAX_AGE_HOURS:-26}"
restore_max_age_days="${GRAF_POSTHOG_RESTORE_MAX_AGE_DAYS:-30}"
minimum_copies="${GRAF_POSTHOG_BACKUP_MIN_COPIES:-2}"
minimum_offsite_copies="${GRAF_POSTHOG_BACKUP_MIN_OFFSITE_COPIES:-1}"
timeout_seconds="${GRAF_ANALYTICS_ALERT_TIMEOUT_SECONDS:-10}"
api_base="${GRAF_ANALYTICS_ALERT_API_BASE:-https://api.telegram.org}"
fallback_url="${GRAF_ANALYTICS_ALERT_FALLBACK_URL:-}"

last_delivery_file="$state_dir/last-delivery"
channel_state_file="$state_dir/channel-state"
drill_state_file="$state_dir/last-drill"
tmp_files=()
cleanup() {
  for tmp_file in "${tmp_files[@]-}"; do
    [[ -z "$tmp_file" ]] || rm -f "$tmp_file"
  done
}
trap cleanup EXIT

mode="once"
print_only=0
while (( $# > 0 )); do
  case "$1" in
    --dry-run) print_only=1 ;;
    --print-message) print_only=1 ;;
    --drill) mode="drill" ;;
    --check-channel) mode="channel" ;;
    --status) mode="status" ;;
    --rules)
      (( $# > 1 )) || { echo "alert_result=failed"; echo "reason=rules_argument_missing"; exit 2; }
      rules_file="$2"
      shift
      ;;
    --help|-h)
      sed -n '3,40p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *)
      echo "alert_result=failed" >&2
      echo "reason=unknown_argument" >&2
      echo "argument=$1" >&2
      exit 2
      ;;
  esac
  shift
done

mkdir -p "$state_dir"
chmod 0750 "$state_dir" 2>/dev/null || true

log_event() {
  local level="$1"
  shift
  logger -t graf-analytics-alert "level=$level $*" 2>/dev/null || true
}

read_value_file() {
  local path="$1"
  local value=""
  [[ -f "$path" && ! -L "$path" ]] || return 0
  read -r value < "$path" || true
  printf '%s' "$value"
}

bot_token="${GRAF_ANALYTICS_ALERT_BOT_TOKEN:-}"
if [[ -z "$bot_token" && -n "${GRAF_ANALYTICS_ALERT_BOT_TOKEN_FILE:-}" ]]; then
  bot_token="$(read_value_file "$GRAF_ANALYTICS_ALERT_BOT_TOKEN_FILE")"
fi
chat_id="${GRAF_ANALYTICS_ALERT_CHAT_ID:-}"
if [[ -z "$chat_id" && -n "${GRAF_ANALYTICS_ALERT_CHAT_ID_FILE:-}" ]]; then
  chat_id="$(read_value_file "$GRAF_ANALYTICS_ALERT_CHAT_ID_FILE")"
fi

redact() {
  local text="$1"
  if [[ -n "$bot_token" ]]; then
    printf '%s' "${text//$bot_token/<redacted>}"
  else
    printf '%s' "$text"
  fi
}

state_value() {
  local file="$1"
  local key="$2"
  [[ -r "$file" ]] || return 0
  awk -v key="$key" 'index($0, key "=") == 1 {print substr($0, length(key) + 2); exit}' "$file"
}

state_values() {
  local file="$1"
  local key="$2"
  [[ -r "$file" ]] || return 0
  awk -v key="$key" 'index($0, key "=") == 1 {print substr($0, length(key) + 2)}' "$file"
}

now_epoch="$(date +%s 2>/dev/null || printf '')"
recorded_at="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf 'unknown')"
if [[ ! "$now_epoch" =~ ^[0-9]+$ ]]; then
  echo "alert_result=failed"
  echo "reason=clock_unavailable"
  exit 1
fi

age_minutes() {
  local stamp="$1"
  local fallback="$2"
  if [[ "$stamp" =~ ^[0-9]+$ ]] && (( now_epoch >= stamp )); then
    printf '%s' "$(( (now_epoch - stamp) / 60 ))"
  else
    printf '%s' "$fallback"
  fi
}

owner_role_for_code() {
  local code="$1"
  [[ -r "$rules_file" ]] || { printf 'unassigned'; return 0; }
  awk -v code="$code" '
    /^rule[ \t]/ {
      matched = 0
      role = "unassigned"
      for (field = 1; field <= NF; field++) {
        if ($field == "code=" code) matched = 1
        if (index($field, "owner_role=") == 1) role = substr($field, 12)
      }
      if (matched) { print role; exit }
    }
  ' "$rules_file" | {
    read -r found || true
    [[ -n "$found" ]] && printf '%s' "$found" || printf 'unassigned'
  }
}

named_owner_for_role() {
  local role="$1"
  local variable="GRAF_ANALYTICS_ALERT_OWNER_$(printf '%s' "$role" | tr '[:lower:]' '[:upper:]')"
  printf '%s' "${!variable:-}"
}

owner_label_for_role() {
  local role="$1"
  local named
  named="$(named_owner_for_role "$role")"
  if [[ "$role" == "unassigned" ]]; then
    printf 'unassigned (rule owner missing)'
  elif [[ -n "$named" ]]; then
    printf '%s (%s)' "$named" "$role"
  else
    printf '%s (not named in environment)' "$role"
  fi
}

owner_label_for_code() {
  owner_label_for_role "$(owner_role_for_code "$1")"
}

# One label per involved role, in the order the rules appear. The alert carries
# the roles for every scope in the list, not only the first one, so a mixed
# analytics and host degradation reaches both owners (FR-055).
owner_summary() {
  local code_list="$1"
  local code role label seen existing summary=""
  local -a roles=()
  for code in $code_list; do
    role="$(owner_role_for_code "$code")"
    seen=0
    for existing in "${roles[@]-}"; do
      if [[ "$existing" == "$role" ]]; then
        seen=1
      fi
    done
    if (( seen == 1 )); then
      continue
    fi
    roles+=("$role")
    label="$(owner_label_for_role "$role")"
    summary="${summary:+$summary; }$label"
  done
  printf '%s' "$summary"
}

json_escape() {
  local text="$1"
  text="${text//\\/\\\\}"
  text="${text//\"/\\\"}"
  text="${text//$'\n'/\\n}"
  text="${text//$'\t'/\\t}"
  text="${text//$'\r'/}"
  printf '%s' "$text"
}

collect_reasons() {
  reasons=()
  owner_unnamed=0

  if [[ ! -r "$guard_state_file" ]]; then
    reasons+=("guard_state_missing")
  else
    local recorded
    recorded="$(state_value "$guard_state_file" recorded_at_epoch)"
    if [[ ! "$recorded" =~ ^[0-9]+$ ]] || (( (now_epoch - recorded) > guard_state_max_age_minutes * 60 )); then
      reasons+=("guard_state_stale")
    fi
    if [[ "$(state_value "$guard_state_file" result)" == "alert" ]]; then
      while IFS= read -r code; do
        [[ -n "$code" ]] && reasons+=("$code")
      done < <(state_values "$guard_state_file" analytics_breaches | tr ',' '\n')
      while IFS= read -r code; do
        [[ -n "$code" && "$code" != "none" ]] && reasons+=("$code")
      done < <(state_values "$guard_state_file" host_breaches | tr ',' '\n')
    fi
  fi

  if [[ -r "$backup_state_file" ]]; then
    local backup_age_hours last_success
    last_success="$(state_value "$backup_state_file" last_success_epoch)"
    if [[ ! "$last_success" =~ ^[0-9]+$ ]]; then
      reasons+=("backup_missing")
    else
      backup_age_hours=$(( (now_epoch - last_success) / 3600 ))
      if (( backup_age_hours > backup_max_age_hours )); then
        reasons+=("backup_stale")
      fi
    fi
    if [[ "$(state_value "$backup_state_file" last_attempt_result)" == "failed" ]]; then
      reasons+=("backup_failed")
    fi
  else
    reasons+=("backup_missing")
  fi

  if [[ -r "$restore_state_file" ]]; then
    local verify_epoch verify_result
    verify_result="$(state_value "$restore_state_file" last_verify_result)"
    verify_epoch="$(state_value "$restore_state_file" last_verify_epoch)"
    if [[ "$verify_result" != "pass" ]]; then
      reasons+=("restore_verification_failed")
    elif [[ ! "$verify_epoch" =~ ^[0-9]+$ ]]; then
      reasons+=("restore_verification_missing")
    elif (( (now_epoch - verify_epoch) > restore_max_age_days * 86400 )); then
      reasons+=("restore_verification_stale")
    fi
  else
    reasons+=("restore_verification_missing")
  fi

  if [[ -r "$retention_state_file" ]]; then
    [[ "$(state_value "$retention_state_file" result)" == "pass" ]] || reasons+=("retention_enforcement_failed")
    while IFS= read -r category; do
      [[ -n "$category" ]] && reasons+=("retention_category_missing")
    done < <(state_values "$retention_state_file" missing_category)
  fi

  if [[ -r "$backup_state_file" ]]; then
    local copies offsite
    copies="$(state_value "$backup_state_file" copies_local)"
    offsite="$(state_value "$backup_state_file" copies_offsite)"
    if [[ "$copies" =~ ^[0-9]+$ ]] && (( copies < minimum_copies )); then
      reasons+=("backup_copy_count_below_minimum")
    fi
    if [[ "$offsite" =~ ^[0-9]+$ ]] && (( offsite < minimum_offsite_copies )); then
      reasons+=("backup_offsite_missing")
    fi
  fi

  local code role
  for code in "${reasons[@]-}"; do
    [[ -n "$code" ]] || continue
    role="$(owner_role_for_code "$code")"
    if [[ "$role" == "unassigned" ]] || [[ -z "$(named_owner_for_role "$role")" ]]; then
      owner_unnamed=1
    fi
  done
}

unique_reasons() {
  local -a unique=()
  local code
  for code in "${reasons[@]-}"; do
    [[ -n "$code" ]] || continue
    local seen=0
    for existing in "${unique[@]-}"; do
      [[ "$existing" == "$code" ]] && seen=1
    done
    (( seen == 1 )) || unique+=("$code")
  done
  printf '%s' "${unique[*]-}"
}

metrics_summary() {
  local load memory disk lag queue growth
  load="$(state_value "$guard_state_file" load_1m)"
  memory="$(state_value "$guard_state_file" memory_mib)"
  disk="$(state_value "$guard_state_file" disk_free_percent)"
  lag="$(state_value "$guard_state_file" delivery_lag_seconds)"
  queue="$(state_value "$guard_state_file" queue_depth)"
  growth="$(state_value "$guard_state_file" queue_growth_per_min)"
  printf 'load_1m=%s memory_mib=%s disk_free_percent=%s delivery_lag_seconds=%s queue_depth=%s queue_growth_per_min=%s' \
    "${load:-unknown}" "${memory:-unknown}" "${disk:-unknown}" "${lag:-unknown}" "${queue:-unknown}" "${growth:-unknown}"
}

build_message() {
  local kind="$1"
  local scope="$2"
  local codes="$3"
  local extra="$4"
  local -a lines=()
  lines+=("GRAF product analytics: $kind")
  lines+=("result: alert")
  lines+=("scope: $scope")
  lines+=("rules: $codes")
  if [[ -n "$extra" ]]; then
    lines+=("detail: $extra")
  fi
  lines+=("metrics: $(metrics_summary)")
  lines+=("owner: $(owner_summary "$codes")")
  lines+=("product_impact: measurement gap only; product workflows stay online")
  lines+=("delivery_deadline_minutes: 15")
  lines+=("recorded_at: $recorded_at")
  lines+=("requirement: FR-030 FR-031 FR-032 FR-054 FR-055")
  printf '%s\n' "${lines[@]}"
}

signature_for() {
  printf '%s' "$1" | cksum | awk '{print $1 "-" $2}'
}

write_state() {
  local tmp_file
  tmp_file="$(mktemp "$state_dir/channel-state.XXXXXX")" || return 0
  tmp_files+=("$tmp_file")
  {
    printf 'channel_state_version=1\n'
    printf 'checked_at=%s\n' "$recorded_at"
    printf 'checked_at_epoch=%s\n' "$now_epoch"
    printf 'first_checked_at_epoch=%s\n' "${channel_first_checked_at_epoch:-$now_epoch}"
    printf 'channel=telegram\n'
    printf 'result=%s\n' "$1"
    printf 'reason=%s\n' "$2"
    printf 'first_run_grace_minutes=%s\n' "$first_run_grace_minutes"
    printf 'first_run_grace_status=%s\n' "${channel_first_run_grace:-inactive}"
    printf 'last_delivery_status=%s\n' "${channel_delivery_state:-not_checked}"
    printf 'guard_state_age_minutes=%s\n' "$(age_minutes "$(state_value "$guard_state_file" recorded_at_epoch)" unknown)"
    printf 'last_delivery_age_minutes=%s\n' "$(age_minutes "$(state_value "$last_delivery_file" sent_at_epoch)" unknown)"
    printf 'fallback_transport=%s\n' "$( [[ -n "$fallback_url" ]] && printf configured || printf not_configured )"
  } > "$tmp_file"
  chmod 0640 "$tmp_file" 2>/dev/null || true
  mv "$tmp_file" "$channel_state_file"
}

deliver_telegram() {
  local text="$1"
  local response="" http_code="" body=""
  [[ -n "$bot_token" && -n "$chat_id" ]] || return 2
  response="$(curl --silent --show-error --max-time "$timeout_seconds" --write-out '\n%{http_code}' \
    --request POST "${api_base}/bot${bot_token}/sendMessage" \
    --data-urlencode "chat_id=${chat_id}" \
    --data-urlencode "text=${text}" \
    --data "disable_web_page_preview=true" 2>&1)" || {
    log_event critical "result=alert_delivery_failed transport=telegram stage=transport"
    return 1
  }
  http_code="${response##*$'\n'}"
  body="${response%$'\n'*}"
  if [[ "$http_code" != "200" ]] || [[ "$body" != *'"ok":true'* ]]; then
    log_event critical "result=alert_delivery_failed transport=telegram stage=response status=$http_code detail=$(redact "$body" | tr -d '\n' | cut -c1-200)"
    return 1
  fi
  return 0
}

deliver_fallback() {
  local text="$1"
  local response="" http_code=""
  [[ -n "$fallback_url" ]] || return 2
  response="$(curl --silent --show-error --max-time "$timeout_seconds" --write-out '\n%{http_code}' \
    --request POST "$fallback_url" \
    --header 'Content-Type: application/json' \
    --data "$(printf '{"text":"%s"}' "$(json_escape "$text")")" 2>&1)" || {
    log_event critical "result=alert_delivery_failed transport=fallback stage=transport"
    return 1
  }
  http_code="${response##*$'\n'}"
  if [[ ! "$http_code" =~ ^2[0-9][0-9]$ ]]; then
    log_event critical "result=alert_delivery_failed transport=fallback stage=response status=$http_code"
    return 1
  fi
  return 0
}

# shellcheck disable=SC2317
deliver() {
  local text="$1"
  local transport="telegram"
  if deliver_telegram "$text"; then
    transport="telegram"
  elif deliver_fallback "$text"; then
    transport="fallback"
    log_event warning "result=alert_delivered transport=fallback primary=unavailable"
  else
    log_event critical "result=alert_delivery_failed transport=all"
    return 1
  fi
  local tmp_file
  tmp_file="$(mktemp "$state_dir/last-delivery.XXXXXX")" || return 0
  tmp_files+=("$tmp_file")
  {
    printf 'delivery_state_version=1\n'
    printf 'sent_at=%s\n' "$recorded_at"
    printf 'sent_at_epoch=%s\n' "$now_epoch"
    printf 'transport=%s\n' "$transport"
    printf 'signature=%s\n' "$2"
    printf 'result=%s\n' "$3"
  } > "$tmp_file"
  chmod 0640 "$tmp_file" 2>/dev/null || true
  mv "$tmp_file" "$last_delivery_file"
  printf 'alert_transport=%s\n' "$transport"
  return 0
}

if [[ "$mode" == "status" ]]; then
  collect_reasons
  printf 'alert_state_file=%s\n' "$( [[ -r "$guard_state_file" ]] && printf present || printf missing )"
  printf 'alert_reasons=%s\n' "$( [[ -n "$(unique_reasons)" ]] && unique_reasons || printf none )"
  printf 'alert_channel=%s\n' "$(state_value "$channel_state_file" result)"
  printf 'alert_last_delivery=%s\n' "$(state_value "$last_delivery_file" sent_at)"
  printf 'alert_secrets=not_read_from_repository\n'
  exit 0
fi

if [[ "$mode" == "channel" ]]; then
  channel_result="pass"
  channel_reason="none"
  channel_delivery_state="not_checked"
  channel_first_run_grace="inactive"
  channel_first_checked_at_epoch="$(state_value "$channel_state_file" first_checked_at_epoch)"
  if [[ ! "$channel_first_checked_at_epoch" =~ ^[0-9]+$ ]]; then
    # Preserve the age of a state file written by the previous schema. Only a
    # genuinely new channel check starts the explicit grace window; later
    # checks cannot silently reset it.
    channel_first_checked_at_epoch="$(state_value "$channel_state_file" checked_at_epoch)"
  fi
  if [[ ! "$channel_first_checked_at_epoch" =~ ^[0-9]+$ ]]; then
    channel_first_checked_at_epoch="$now_epoch"
  fi
  if (( now_epoch - channel_first_checked_at_epoch <= first_run_grace_minutes * 60 )); then
    channel_first_run_grace="active"
  else
    channel_first_run_grace="expired"
  fi

  if [[ -z "$bot_token" ]]; then
    channel_result="fail"
    channel_reason="bot_token_unset"
  elif [[ -z "$chat_id" ]]; then
    channel_result="fail"
    channel_reason="chat_id_unset"
  else
    probe="$(curl --silent --show-error --max-time "$timeout_seconds" --write-out '\n%{http_code}' \
      "${api_base}/bot${bot_token}/getMe" 2>&1)" || probe=""
    probe_code="${probe##*$'\n'}"
    probe_body="${probe%$'\n'*}"
    if [[ "$probe_code" != "200" ]] || [[ "$probe_body" != *'"ok":true'* ]]; then
      channel_result="fail"
      channel_reason="channel_api_unreachable"
    else
      chat_probe="$(curl --silent --show-error --max-time "$timeout_seconds" --write-out '\n%{http_code}' \
        --request POST "${api_base}/bot${bot_token}/getChat" \
        --data-urlencode "chat_id=${chat_id}" 2>&1)" || chat_probe=""
      chat_code="${chat_probe##*$'\n'}"
      chat_body="${chat_probe%$'\n'*}"
      if [[ "$chat_code" != "200" ]] || [[ "$chat_body" != *'"ok":true'* ]]; then
        channel_result="fail"
        channel_reason="channel_chat_unreachable"
      fi
    fi
  fi
  guard_age="$(age_minutes "$(state_value "$guard_state_file" recorded_at_epoch)" unknown)"
  if [[ "$channel_result" == "pass" ]] && [[ "$guard_age" != "unknown" ]] && (( guard_age > guard_state_max_age_minutes )); then
    channel_result="fail"
    channel_reason="guard_state_stale"
  fi
  if [[ "$channel_result" == "pass" ]] && [[ ! -r "$guard_state_file" ]]; then
    channel_result="fail"
    channel_reason="guard_state_missing"
  fi

  # A successful provider probe proves only that the provider answers now. The
  # last-delivery record proves that the configured transport has actually
  # delivered an alert recently. On a new installation that record does not
  # exist yet, so the first channel check gets the explicit grace window above;
  # after it expires, absence fails closed instead of looking healthy.
  if [[ "$channel_result" == "pass" ]]; then
    if [[ -r "$last_delivery_file" ]]; then
      last_delivery_epoch="$(state_value "$last_delivery_file" sent_at_epoch)"
      if [[ ! "$last_delivery_epoch" =~ ^[0-9]+$ ]] || (( last_delivery_epoch > now_epoch )) \
        || (( (now_epoch - last_delivery_epoch) > guard_state_max_age_minutes * 60 )); then
        channel_delivery_state="stale"
        channel_result="fail"
        channel_reason="last_delivery_stale"
      else
        channel_delivery_state="fresh"
      fi
    elif [[ "$channel_first_run_grace" == "active" ]]; then
      channel_delivery_state="first_run_grace"
    else
      channel_delivery_state="missing"
      channel_result="fail"
      channel_reason="last_delivery_missing"
    fi
  fi

  if [[ "$print_only" == "1" ]]; then
    printf 'alert_channel_result=%s\n' "$channel_result"
    printf 'alert_channel_reason=%s\n' "$channel_reason"
    printf 'alert_channel_first_run_grace=%s\n' "$channel_first_run_grace"
    printf 'alert_channel_last_delivery=%s\n' "$channel_delivery_state"
    printf 'alert_channel_transport_probe=telegram_getMe_getChat\n'
    exit 0
  fi

  write_state "$channel_result" "$channel_reason"
  if [[ "$channel_result" == "pass" ]]; then
    log_event pass "result=alert_channel_pass channel=telegram"
    printf 'alert_channel_result=pass\n'
    printf 'alert_channel_reason=none\n'
    printf 'alert_channel_first_run_grace=%s\n' "$channel_first_run_grace"
    printf 'alert_channel_last_delivery=%s\n' "$channel_delivery_state"
    exit 0
  fi

  log_event critical "result=alert_channel_unavailable reason=$channel_reason channel=telegram"
  notice="$(build_message "alert channel unavailable" "alerting" "alert_channel_unavailable" "channel_reason=$channel_reason")"
  if deliver_fallback "$notice"; then
    printf 'alert_channel_fallback=delivered\n'
  else
    printf 'alert_channel_fallback=not_delivered\n'
  fi
  printf 'alert_channel_result=fail\n'
  printf 'alert_channel_reason=%s\n' "$channel_reason"
  printf 'alert_channel_first_run_grace=%s\n' "$channel_first_run_grace"
  printf 'alert_channel_last_delivery=%s\n' "$channel_delivery_state"
  printf 'alert_channel_independent_detection=journald_and_channel_state_file\n'
  exit 1
fi

if [[ "$mode" == "drill" ]]; then
  text="$(build_message "TRAINING ALERT (учебная тревога), not a real degradation" "drill" "analytics_degradation_drill" "drill requested by operator; verifies the 15 minute delivery deadline (SC-009)")"
  if [[ "$print_only" == "1" ]]; then
    printf '%s\n' "$text"
    printf 'alert_result=dry_run\n'
    printf 'alert_transport=none\n'
    exit 0
  fi
  drill_signature="$(signature_for "$text")"
  if ! deliver "$text" "$drill_signature" "drill"; then
    printf 'alert_result=failed\n'
    printf 'reason=drill_delivery_failed\n'
    exit 1
  fi
  tmp_file="$(mktemp "$state_dir/last-drill.XXXXXX")"
  tmp_files+=("$tmp_file")
  printf 'drill_at=%s\ndrill_at_epoch=%s\n' "$recorded_at" "$now_epoch" > "$tmp_file"
  chmod 0640 "$tmp_file" 2>/dev/null || true
  mv "$tmp_file" "$drill_state_file"
  log_event pass "result=drill_delivered channel=telegram"
  printf 'alert_result=drill_delivered\n'
  printf 'alert_delivery_deadline_minutes=15\n'
  exit 0
fi

collect_reasons
codes="$(unique_reasons)"
if [[ -z "$codes" ]]; then
  log_event pass "result=pass reasons=none"
  printf 'alert_result=pass\n'
  printf 'alert_reasons=none\n'
  printf 'alert_delivery_deadline_minutes=15\n'
  exit 0
fi
if (( owner_unnamed == 1 )); then
  codes="$codes alert_owner_unnamed"
  log_event warning "result=alert_owner_unnamed rules_file=$rules_file"
fi

# Scope label mirrors the guard's `breach_scope` vocabulary, so a mixed list is
# visible as `analytics+host` instead of being collapsed into one scope. The
# analytics scope stays first: measurement degrades before the host does.
has_analytics=0
has_host=0
has_backup=0
has_retention=0
has_alerting=0
for code in $codes; do
  case "$code" in
    host_*)
      has_host=1
      ;;
    backup_*|restore_*)
      has_backup=1
      ;;
    retention_*)
      has_retention=1
      ;;
    alert_channel_*|guard_state_*|alert_owner_unnamed|alert_delivery_failed)
      has_alerting=1
      ;;
    *)
      has_analytics=1
      ;;
  esac
done
scope=""
if (( has_analytics == 1 )); then
  scope="analytics"
fi
if (( has_host == 1 )); then
  scope="${scope:+$scope+}host"
fi
if (( has_retention == 1 )); then
  scope="${scope:+$scope+}retention"
fi
if (( has_backup == 1 )); then
  scope="${scope:+$scope+}backup"
fi
if (( has_alerting == 1 )); then
  scope="${scope:+$scope+}alerting"
fi
if [[ -z "$scope" ]]; then
  scope="analytics"
fi

signature="$(signature_for "$codes")"
text="$(build_message "degradation" "$scope" "$codes" "guard_result=$(state_value "$guard_state_file" result) measurement_action=$(state_value "$guard_state_file" measurement_action)")"

if [[ "$print_only" == "1" ]]; then
  printf '%s\n' "$text"
  printf 'alert_result=dry_run\n'
  printf 'alert_reasons=%s\n' "$codes"
  printf 'alert_transport=none\n'
  printf 'alert_delivery_deadline_minutes=15\n'
  exit 0
fi

last_signature="$(state_value "$last_delivery_file" signature)"
last_sent_epoch="$(state_value "$last_delivery_file" sent_at_epoch)"
if [[ "$signature" == "$last_signature" ]] && [[ "$last_sent_epoch" =~ ^[0-9]+$ ]] \
  && (( (now_epoch - last_sent_epoch) < repeat_minutes * 60 )); then
  log_event pass "result=alert_suppressed reason=unchanged_within_repeat_window"
  printf 'alert_result=suppressed\n'
  printf 'alert_reasons=%s\n' "$codes"
  printf 'alert_transport=none\n'
  exit 0
fi

if ! deliver "$text" "$signature" "alert"; then
  printf 'alert_result=failed\n'
  printf 'alert_reasons=%s\n' "$codes"
  printf 'reason=delivery_failed\n'
  printf 'alert_delivery_deadline_minutes=15\n'
  exit 1
fi

log_event alert "result=alert_delivered scope=$scope rules=$codes"
printf 'alert_result=delivered\n'
printf 'alert_reasons=%s\n' "$codes"
printf 'alert_scope=%s\n' "$scope"
printf 'alert_delivery_deadline_minutes=15\n'
printf 'alert_secrets=not_printed\n'
exit 0
