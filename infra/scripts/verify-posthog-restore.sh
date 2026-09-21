#!/usr/bin/env bash
set -euo pipefail

# Scheduled restore verification for the PostHog analytics backup set
# (FR-035, FR-051, SC-010).
#
# The check proves that a stored copy can actually be restored, and it records
# evidence. It never touches the live analytics stack: every archive is verified
# against its SHA-256 manifest, unpacked into isolated rehearsal volumes, read
# back, and the rehearsal volumes are removed afterwards.
#
# The recorded evidence is metadata only: volume class names, archive count,
# digest verification result, restored file counts, duration class, timestamps
# and blocker codes. No dump contents, no visitor or account data, no provider
# payloads, no credentials, no private host paths.
#
# A failed or stale verification blocks the analytics readiness claim (FR-051)
# and raises an external alert through `alert-analytics-degradation.sh`.
#
# Usage:
#   verify-posthog-restore.sh                 # dry run, prints the plan
#   verify-posthog-restore.sh --execute
#   verify-posthog-restore.sh --execute --reference 20260919T023000Z
#   verify-posthog-restore.sh --status

umask 077

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
backup_dir="${GRAF_POSTHOG_BACKUP_DIR:-/var/backups/graf-posthog}"
state_dir="${GRAF_POSTHOG_BACKUP_STATE_DIR:-/var/lib/graf-posthog-backup}"
evidence_dir="${GRAF_POSTHOG_RESTORE_EVIDENCE_DIR:-/var/lib/graf-posthog-restore-evidence}"
restore_state_file="${GRAF_POSTHOG_RESTORE_STATE_FILE:-$state_dir/restore-state}"
rehearsal_prefix="${GRAF_POSTHOG_RESTORE_VOLUME_PREFIX:-graf-posthog-rehearsal}"
backup_image="${GRAF_POSTHOG_BACKUP_IMAGE:-alpine:3.20}"
alert_script="${GRAF_POSTHOG_ALERT_SCRIPT:-$repo_root/infra/scripts/alert-analytics-degradation.sh}"
max_age_days="${GRAF_POSTHOG_RESTORE_MAX_AGE_DAYS:-30}"
mode="dry-run"
requested_reference=""

usage() {
  cat >&2 <<EOF
usage: $0 [--dry-run|--execute|--status] [--reference <backup label>]
EOF
}

while (( $# > 0 )); do
  case "$1" in
    --dry-run) mode="dry-run" ;;
    --execute) mode="execute" ;;
    --status) mode="status" ;;
    --reference)
      (( $# > 1 )) || { usage; exit 2; }
      requested_reference="$2"
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
  logger -t graf-posthog-restore-verify "level=$level $*" 2>/dev/null || true
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

now_epoch="$(date +%s 2>/dev/null || printf '')"
checked_at_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf 'unknown')"
if [[ ! "$now_epoch" =~ ^[0-9]+$ ]]; then
  echo "restore_verification_result=failed"
  echo "reason=clock_unavailable"
  exit 1
fi

if [[ "$mode" == "status" ]]; then
  if [[ -r "$restore_state_file" ]]; then
    cat "$restore_state_file"
    last_verify_epoch="$(awk 'index($0, "last_verify_epoch=") == 1 {print substr($0, 19); exit}' "$restore_state_file")"
    if [[ "$last_verify_epoch" =~ ^[0-9]+$ ]]; then
      printf 'verification_age_days=%s\n' "$(( (now_epoch - last_verify_epoch) / 86400 ))"
    fi
  else
    printf 'restore_state=missing\n'
  fi
  printf 'restore_verification_max_age_days=%s\n' "$max_age_days"
  exit 0
fi

write_state() {
  local result="$1"
  local reason="$2"
  local reference="$3"
  local volumes_restored="$4"
  local files_restored="$5"
  local evidence_reference="$6"
  local tmp_file
  mkdir -p "$(dirname "$restore_state_file")"
  tmp_file="$(mktemp "$restore_state_file.XXXXXX")" || return 1
  {
    printf 'restore_state_version=1\n'
    printf 'checked_at=%s\n' "$checked_at_iso"
    printf 'checked_at_epoch=%s\n' "$now_epoch"
    printf 'last_verify_at=%s\n' "$checked_at_iso"
    printf 'last_verify_epoch=%s\n' "$now_epoch"
    printf 'last_verify_result=%s\n' "$result"
    printf 'last_verify_reason=%s\n' "$reason"
    printf 'last_verify_reference=%s\n' "$reference"
    printf 'volumes_restored=%s\n' "$volumes_restored"
    printf 'files_restored=%s\n' "$files_restored"
    printf 'evidence_reference=%s\n' "$evidence_reference"
    printf 'verification_max_age_days=%s\n' "$max_age_days"
    printf 'rehearsal_scope=isolated_volumes_removed_after_check\n'
    printf 'live_stack_touched=0\n'
    printf 'product_impact=measurement_gap_only\n'
  } > "$tmp_file"
  chmod 0640 "$tmp_file" 2>/dev/null || true
  mv "$tmp_file" "$restore_state_file"
}

raise_alert() {
  [[ -x "$alert_script" ]] || { log_event warning "result=alert_script_missing"; return 0; }
  if "$alert_script" >/dev/null 2>&1; then
    printf 'restore_verification_alert=delivered\n'
  else
    printf 'restore_verification_alert=delivery_failed\n'
  fi
}

resolve_reference() {
  if [[ -n "$requested_reference" ]]; then
    printf '%s' "$requested_reference"
    return 0
  fi
  [[ -d "$backup_dir" ]] || return 0
  find "$backup_dir" -mindepth 1 -maxdepth 1 -type d -name '20*T*Z' -print 2>/dev/null | LC_ALL=C sort | tail -n 1 | xargs -r -n 1 basename
}

reference="$(resolve_reference)"
source_dir=""
[[ -n "$reference" ]] && source_dir="$backup_dir/$reference"

if [[ "$mode" != "execute" ]]; then
  echo "restore_verification_result=dry_run"
  echo "backup_reference=$( [[ -n "$reference" ]] && printf '%s' "$reference" || printf none )"
  echo "backup_dir=$( [[ -d "$backup_dir" ]] && printf present || printf missing )"
  echo "rehearsal_volume_prefix=$rehearsal_prefix"
  echo "live_stack_touched=0"
  echo "verification_max_age_days=$max_age_days"
  echo "next_step=run_with_--execute_on_the_analytics_host"
  exit 0
fi

fail_verification() {
  local reason="$1"
  echo "restore_verification_result=failed"
  echo "reason=$reason"
  echo "backup_reference=$( [[ -n "$reference" ]] && printf '%s' "$reference" || printf none )"
  write_state "fail" "$reason" "${reference:-none}" "0" "0" "none"
  raise_alert
  log_event critical "result=restore_verification_failed reason=$reason reference=${reference:-none}"
  exit 1
}

if ! command -v docker >/dev/null 2>&1; then
  fail_verification "docker_unavailable"
fi
if [[ -z "$reference" ]]; then
  fail_verification "backup_reference_missing"
fi
if [[ ! -d "$source_dir" ]]; then
  fail_verification "backup_reference_not_found"
fi
if [[ ! -r "$source_dir/manifest.txt" ]]; then
  fail_verification "backup_manifest_missing"
fi

archives=()
while IFS= read -r archive; do
  [[ -n "$archive" ]] && archives+=("$archive")
done < <(find "$source_dir" -mindepth 1 -maxdepth 1 -name '*.tar.gz' -print 2>/dev/null | LC_ALL=C sort)
if (( ${#archives[@]} == 0 )); then
  fail_verification "backup_archives_missing"
fi

integrity_failures=0
for archive in "${archives[@]}"; do
  file_name="$(basename "$archive")"
  volume_name="${file_name%.tar.gz}"
  expected_digest="$(awk -v volume="$volume_name" '$1 == "volume=" volume {for (field = 1; field <= NF; field++) if (index($field, "sha256=") == 1) print substr($field, 8)}' "$source_dir/manifest.txt")"
  actual_digest="$(sha256_of "$archive")"
  if [[ -z "$expected_digest" ]] || [[ "$expected_digest" != "$actual_digest" ]]; then
    printf 'integrity_failed_archive=%s\n' "$volume_name"
    integrity_failures=$((integrity_failures + 1))
    continue
  fi
  printf 'integrity_verified_archive=%s\n' "$volume_name"
done
if (( integrity_failures > 0 )); then
  fail_verification "archive_integrity_failed"
fi

rehearsal_volumes=()
files_restored=0
volumes_restored=0
for archive in "${archives[@]}"; do
  file_name="$(basename "$archive")"
  volume_name="${file_name%.tar.gz}"
  rehearsal_volume="$rehearsal_prefix-$volume_name"
  if ! docker volume create "$rehearsal_volume" >/dev/null 2>&1; then
    fail_verification "rehearsal_volume_create_failed"
  fi
  rehearsal_volumes+=("$rehearsal_volume")
  if ! docker run --rm --pull never \
    -v "$rehearsal_volume:/data" \
    -v "$source_dir:/backup:ro" \
    "$backup_image" \
    tar -xzf "/backup/$file_name" -C /data >/dev/null 2>&1; then
    fail_verification "archive_extract_failed"
  fi
  restored_files="$(docker run --rm --pull never -v "$rehearsal_volume:/data:ro" "$backup_image" sh -c 'find /data -type f | wc -l' 2>/dev/null | awk '{print $1}')"
  if [[ ! "$restored_files" =~ ^[0-9]+$ ]] || (( restored_files == 0 )); then
    fail_verification "restored_volume_empty"
  fi
  files_restored=$((files_restored + restored_files))
  volumes_restored=$((volumes_restored + 1))
  printf 'volume_restored=%s files=%s\n' "$volume_name" "$restored_files"
done

for rehearsal_volume in "${rehearsal_volumes[@]}"; do
  if docker volume rm "$rehearsal_volume" >/dev/null 2>&1; then
    printf 'rehearsal_volume_removed=%s\n' "$rehearsal_volume"
  else
    printf 'rehearsal_volume_retained=%s\n' "$rehearsal_volume"
    log_event warning "result=rehearsal_volume_retained volume=$rehearsal_volume"
  fi
done

evidence_reference="$reference-$checked_at_iso"
mkdir -p "$evidence_dir"
evidence_file="$evidence_dir/restore-evidence-$reference.txt"
{
  printf 'restore_evidence_version=1\n'
  printf 'backup_reference=%s\n' "$reference"
  printf 'checked_at=%s\n' "$checked_at_iso"
  printf 'result=pass\n'
  printf 'archives_verified=%s\n' "${#archives[@]}"
  printf 'volumes_restored=%s\n' "$volumes_restored"
  printf 'files_restored=%s\n' "$files_restored"
  printf 'integrity=sha256_manifest_verified\n'
  printf 'rehearsal_scope=isolated_volumes_removed_after_check\n'
  printf 'live_stack_touched=0\n'
  printf 'content_policy=metadata_only_no_visitor_or_user_data\n'
} > "$evidence_file"
chmod 0640 "$evidence_file" 2>/dev/null || true
printf 'restore_evidence_file=%s\n' "$(basename "$evidence_file")"

write_state "pass" "none" "$reference" "$volumes_restored" "$files_restored" "$evidence_reference"
log_event pass "result=restore_verification_pass reference=$reference volumes=$volumes_restored files=$files_restored"

echo "restore_verification_result=pass"
echo "backup_reference=$reference"
echo "archives_verified=${#archives[@]}"
echo "volumes_restored=$volumes_restored"
echo "files_restored=$files_restored"
echo "integrity=sha256_manifest_verified"
echo "evidence_reference=$evidence_reference"
echo "verification_max_age_days=$max_age_days"
echo "live_stack_touched=0"
exit 0
