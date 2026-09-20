#!/usr/bin/env bash
set -euo pipefail

# Automatic PostHog analytics backup (FR-033, FR-051, FR-052).
#
# What it does, in order:
#   1. archives every volume class listed in the backup inventory into a new
#      dated backup directory with a SHA-256 manifest;
#   2. ships that directory off the measured server through the reviewed
#      offsite command and marks the copy offsite only after the upload
#      succeeded;
#   3. keeps at least two copies, deletes older copies beyond the retention
#      count, and logs every deletion;
#   4. writes a metadata-only state file that the readiness check and the
#      external alert script read.
#
# Nothing here reads event content, provider payloads, account identifiers or
# credentials. The manifest carries volume names, sizes, digests and the
# operator-supplied offsite target label only. Backup failure never stops the
# product: it blocks the analytics readiness claim and raises an alert.
#
# Usage:
#   backup-posthog.sh                 # dry run, prints the plan
#   backup-posthog.sh --execute       # performs the backup
#   backup-posthog.sh --status        # prints the recorded state

umask 077

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
backup_dir="${GRAF_POSTHOG_BACKUP_DIR:-/var/backups/graf-posthog}"
state_dir="${GRAF_POSTHOG_BACKUP_STATE_DIR:-/var/lib/graf-posthog-backup}"
keep_copies="${GRAF_POSTHOG_BACKUP_KEEP:-7}"
inventory_file="${GRAF_POSTHOG_BACKUP_INVENTORY:-$repo_root/infra/posthog/backup-volumes.txt}"
offsite_command="${GRAF_POSTHOG_OFFSITE_COMMAND:-}"
offsite_target_label="${GRAF_POSTHOG_OFFSITE_TARGET_LABEL:-operator_offsite_target}"
backup_image="${GRAF_POSTHOG_BACKUP_IMAGE:-alpine:3.20}"
alert_script="${GRAF_POSTHOG_ALERT_SCRIPT:-$repo_root/infra/scripts/alert-analytics-degradation.sh}"
minimum_copies="${GRAF_POSTHOG_BACKUP_MIN_COPIES:-2}"
state_file="$state_dir/backup-state"
mode="dry-run"

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
  logger -t graf-posthog-backup "level=$level $*" 2>/dev/null || true
}

sha256_of() {
  local path="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$path" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$path" | awk '{print $1}'
  else
    printf 'unavailable'
  fi
}

file_size() {
  local path="$1"
  wc -c < "$path" | awk '{print $1}'
}

count_copies() {
  local directory="$1"
  [[ -d "$directory" ]] || { printf '0'; return 0; }
  find "$directory" -mindepth 1 -maxdepth 1 -type d -name '20*T*Z' 2>/dev/null | wc -l | awk '{print $1}'
}

count_offsite_copies() {
  local directory="$1"
  [[ -d "$directory" ]] || { printf '0'; return 0; }
  find "$directory" -mindepth 2 -maxdepth 2 -name '.offsite' 2>/dev/null | wc -l | awk '{print $1}'
}

write_state() {
  local attempt_result="$1"
  local attempt_reason="$2"
  local last_success_epoch="$3"
  local last_success_at="$4"
  local last_success_reference="$5"
  local archived_volumes="$6"
  local archived_bytes="$7"
  local copies_local="$8"
  local copies_offsite="$9"
  local tmp_file
  mkdir -p "$(dirname "$state_file")"
  tmp_file="$(mktemp "$state_file.XXXXXX")" || return 1
  {
    printf 'backup_state_version=1\n'
    printf 'recorded_at=%s\n' "$recorded_at_iso"
    printf 'recorded_at_epoch=%s\n' "$now_epoch"
    printf 'last_attempt_at=%s\n' "$recorded_at_iso"
    printf 'last_attempt_epoch=%s\n' "$now_epoch"
    printf 'last_attempt_result=%s\n' "$attempt_result"
    printf 'last_attempt_reason=%s\n' "$attempt_reason"
    printf 'last_success_at=%s\n' "$last_success_at"
    printf 'last_success_epoch=%s\n' "$last_success_epoch"
    printf 'last_success_reference=%s\n' "$last_success_reference"
    printf 'copies_local=%s\n' "$copies_local"
    printf 'copies_offsite=%s\n' "$copies_offsite"
    printf 'offsite_target_label=%s\n' "$offsite_target_label"
    printf 'offsite_required=%s\n' "1"
    printf 'retention_keep=%s\n' "$keep_copies"
    printf 'volumes_archived=%s\n' "$archived_volumes"
    printf 'bytes_archived=%s\n' "$archived_bytes"
    if [[ "$attempt_result" == "failed" ]]; then
      printf 'last_failure_at=%s\n' "$recorded_at_iso"
      printf 'last_failure_epoch=%s\n' "$now_epoch"
      printf 'last_failure_reason=%s\n' "$attempt_reason"
    else
      printf 'last_failure_reason=%s\n' "$(previous_failure_reason)"
    fi
    printf 'product_impact=measurement_gap_only\n'
  } > "$tmp_file"
  chmod 0640 "$tmp_file" 2>/dev/null || true
  mv "$tmp_file" "$state_file"
}

previous_failure_reason() {
  [[ -r "$state_file" ]] || { printf 'none'; return 0; }
  awk 'index($0, "last_failure_reason=") == 1 {print substr($0, 21); exit}' "$state_file"
}

raise_alert() {
  [[ -x "$alert_script" ]] || { log_event warning "result=alert_script_missing"; return 0; }
  if "$alert_script" >/dev/null 2>&1; then
    printf 'backup_alert=delivered\n'
  else
    printf 'backup_alert=delivery_failed\n'
  fi
}

now_epoch="$(date +%s 2>/dev/null || printf '')"
recorded_at_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf 'unknown')"
if [[ ! "$now_epoch" =~ ^[0-9]+$ ]]; then
  echo "backup_result=failed"
  echo "reason=clock_unavailable"
  exit 1
fi

if [[ "$mode" == "status" ]]; then
  if [[ -r "$state_file" ]]; then
    cat "$state_file"
  else
    printf 'backup_state=missing\n'
  fi
  printf 'backup_dir=%s\n' "$( [[ -d "$backup_dir" ]] && printf present || printf missing )"
  printf 'backup_inventory=%s\n' "$( [[ -r "$inventory_file" ]] && printf present || printf missing )"
  exit 0
fi

if [[ ! "$keep_copies" =~ ^[0-9]+$ ]] || (( keep_copies < minimum_copies )); then
  echo "backup_result=blocked"
  echo "reason=retention_below_minimum_copies"
  echo "retention_keep=$keep_copies"
  echo "minimum_copies=$minimum_copies"
  exit 2
fi
if [[ ! -r "$inventory_file" ]]; then
  echo "backup_result=blocked"
  echo "reason=backup_inventory_missing"
  exit 2
fi

label="$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null || printf 'unknown')"
target_dir="$backup_dir/$label"

required_patterns=()
optional_patterns=()
while IFS= read -r line; do
  line="${line%%#*}"
  line="$(printf '%s' "$line" | tr -d '[:space:]')"
  [[ -n "$line" ]] || continue
  if [[ "$line" == *'?' ]]; then
    optional_patterns+=("${line%?}")
  else
    required_patterns+=("$line")
  fi
done < "$inventory_file"

volumes=()
if ! volume_list="$(docker volume ls --format '{{.Name}}' 2>/dev/null)"; then
  echo "backup_result=blocked"
  echo "reason=docker_volume_list_unavailable"
  exit 1
fi
while IFS= read -r name; do
  [[ -n "$name" ]] || continue
  for pattern in "${required_patterns[@]-}" "${optional_patterns[@]-}"; do
    [[ -n "$pattern" ]] || continue
    # shellcheck disable=SC2053
    if [[ "$name" == $pattern ]]; then
      volumes+=("$name")
      break
    fi
  done
done <<< "$volume_list"

unmatched_required=()
for pattern in "${required_patterns[@]-}"; do
  [[ -n "$pattern" ]] || continue
  matched=0
  for name in "${volumes[@]-}"; do
    # shellcheck disable=SC2053
    if [[ "$name" == $pattern ]]; then
      matched=1
      break
    fi
  done
  (( matched == 1 )) || unmatched_required+=("$pattern")
done

if [[ "$mode" != "execute" ]]; then
  echo "backup_result=dry_run"
  echo "backup_reference=$label"
  echo "backup_dir=$( [[ -d "$backup_dir" ]] && printf present || printf missing )"
  echo "volumes_matched=${#volumes[@]}"
  printf 'required_classes=%s\n' "${#required_patterns[@]}"
  printf 'optional_classes=%s\n' "${#optional_patterns[@]}"
  printf 'unmatched_required=%s\n' "$( [[ ${#unmatched_required[@]} -eq 0 ]] && printf none || printf '%s' "${unmatched_required[*]}" )"
  printf 'retention_keep=%s\n' "$keep_copies"
  printf 'minimum_copies=%s\n' "$minimum_copies"
  printf 'offsite_command=%s\n' "$( [[ -n "$offsite_command" ]] && printf configured || printf not_configured )"
  printf 'offsite_target_label=%s\n' "$offsite_target_label"
  printf 'next_step=run_with_--execute_from_the_analytics_host\n'
  exit 0
fi

previous_success_epoch=""
previous_success_at=""
previous_success_reference=""
if [[ -r "$state_file" ]]; then
  previous_success_epoch="$(awk 'index($0, "last_success_epoch=") == 1 {print substr($0, 20); exit}' "$state_file")"
  previous_success_at="$(awk 'index($0, "last_success_at=") == 1 {print substr($0, 17); exit}' "$state_file")"
  previous_success_reference="$(awk 'index($0, "last_success_reference=") == 1 {print substr($0, 24); exit}' "$state_file")"
fi
[[ "$previous_success_epoch" =~ ^[0-9]+$ ]] || previous_success_epoch=""
if [[ "$previous_success_at" == "unknown" ]]; then
  previous_success_at=""
fi

fail_backup() {
  local reason="$1"
  echo "backup_result=failed"
  echo "reason=$reason"
  echo "backup_reference=$label"
  write_state "failed" "$reason" "$previous_success_epoch" "$previous_success_at" "$previous_success_reference" \
    "${#volumes[@]}" "0" "$(count_copies "$backup_dir")" "$(count_offsite_copies "$backup_dir")"
  raise_alert
  log_event critical "result=backup_failed reason=$reason reference=$label"
  exit 1
}

if (( ${#volumes[@]} == 0 )); then
  fail_backup "no_volumes_matched"
fi
if (( ${#unmatched_required[@]} > 0 )); then
  fail_backup "required_volume_class_missing"
fi
if [[ -z "$offsite_command" ]]; then
  fail_backup "offsite_command_not_configured"
fi
if ! command -v docker >/dev/null 2>&1; then
  fail_backup "docker_unavailable"
fi

mkdir -p "$target_dir"
archive_bytes=0
manifest="$target_dir/manifest.txt"
{
  printf 'backup_reference=%s\n' "$label"
  printf 'created_at=%s\n' "$recorded_at_iso"
  printf 'offsite_target_label=%s\n' "$offsite_target_label"
} > "$manifest"

for volume in "${volumes[@]}"; do
  archive="$target_dir/$volume.tar.gz"
  if ! docker run --rm --pull never \
    -v "$volume:/data:ro" \
    -v "$target_dir:/backup" \
    "$backup_image" \
    tar -czf "/backup/$volume.tar.gz" -C /data . >/dev/null 2>&1; then
    fail_backup "volume_archive_failed"
  fi
  if [[ ! -s "$archive" ]]; then
    fail_backup "volume_archive_empty"
  fi
  size_bytes="$(file_size "$archive")"
  digest="$(sha256_of "$archive")"
  archive_bytes=$((archive_bytes + size_bytes))
  printf 'volume=%s bytes=%s sha256=%s\n' "$volume" "$size_bytes" "$digest" >> "$manifest"
  printf 'volume_archived=%s\n' "$volume"
done

offsite_resolved="${offsite_command//%ARCHIVE%/$target_dir}"
offsite_resolved="${offsite_resolved//%LABEL%/$label}"
if ! GRAF_POSTHOG_BACKUP_ARCHIVE_DIR="$target_dir" GRAF_POSTHOG_BACKUP_REFERENCE="$label" sh -c "$offsite_resolved"; then
  fail_backup "offsite_upload_failed"
fi
if ! : > "$target_dir/.offsite"; then
  fail_backup "offsite_marker_write_failed"
fi
printf 'offsite_copy=uploaded\n'

# Retention: keep the newest copies, delete the rest, never below the minimum.
existing=()
while IFS= read -r existing_dir; do
  [[ -n "$existing_dir" ]] && existing+=("$existing_dir")
done < <(find "$backup_dir" -mindepth 1 -maxdepth 1 -type d -name '20*T*Z' -print 2>/dev/null | LC_ALL=C sort)
if (( ${#existing[@]} > keep_copies )); then
  delete_count=$(( ${#existing[@]} - keep_copies ))
  for (( index = 0; index < delete_count; index++ )); do
    victim="${existing[index]}"
    remaining=$(( ${#existing[@]} - index ))
    if (( remaining <= minimum_copies )); then
      printf 'retention_kept=%s\n' "$(basename "$victim")"
      continue
    fi
    if rm -rf "$victim"; then
      printf 'retention_deleted=%s\n' "$(basename "$victim")"
      log_event pass "result=retention_deleted reference=$(basename "$victim")"
    fi
  done
fi

copies_local="$(count_copies "$backup_dir")"
copies_offsite="$(count_offsite_copies "$backup_dir")"
write_state "pass" "none" "$now_epoch" "$recorded_at_iso" "$label" "${#volumes[@]}" "$archive_bytes" "$copies_local" "$copies_offsite"
log_event pass "result=backup_pass reference=$label volumes=${#volumes[@]} copies_local=$copies_local copies_offsite=$copies_offsite"

echo "backup_result=pass"
echo "backup_reference=$label"
echo "volumes_archived=${#volumes[@]}"
echo "bytes_archived=$archive_bytes"
echo "copies_local=$copies_local"
echo "copies_offsite=$copies_offsite"
echo "offsite_target_label=$offsite_target_label"
echo "retention_keep=$keep_copies"
echo "product_impact=none"
exit 0
