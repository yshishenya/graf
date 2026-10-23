#!/usr/bin/env bash
set -euo pipefail

# Local PostHog volume backup (T117). Only verified complete sets count or
# participate in rotation. Consistent runtime restore is a separate T118 gate.
# --dry-run (default), --execute, --status; metadata-only output.

umask 077

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
backup_dir="${GRAF_POSTHOG_BACKUP_DIR:-/var/backups/graf-posthog}"
state_dir="${GRAF_POSTHOG_BACKUP_STATE_DIR:-/var/lib/graf-posthog-backup}"
keep_copies="${GRAF_POSTHOG_BACKUP_KEEP:-7}"
inventory_file="${GRAF_POSTHOG_BACKUP_INVENTORY:-$repo_root/infra/posthog/backup-volumes.txt}"
backup_image="${GRAF_POSTHOG_BACKUP_IMAGE:-alpine:3.20}"
alert_script="${GRAF_POSTHOG_ALERT_SCRIPT:-$repo_root/infra/scripts/alert-analytics-degradation.sh}"
minimum_copies="${GRAF_POSTHOG_BACKUP_MIN_COPIES:-2}"
project="${GRAF_POSTHOG_PROJECT:-graf-posthog}"
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

# A directory name or a historical .offsite marker is never proof of a copy.
verified_sets() {
  python3 - "$backup_dir" "$inventory_file" "$project" "${volumes[@]-}" <<'VERIFY'
import fnmatch, hashlib, json, re, sys, time
from pathlib import Path

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

root = Path(sys.argv[1])
if not root.exists():
    raise SystemExit(0)
current_inventory = digest(Path(sys.argv[2]))
project = sys.argv[3]
current_volumes = set(filter(None, sys.argv[4:]))
for directory in sorted(root.iterdir()):
    if not re.fullmatch(r'20[0-9]{6}T[0-9]{6}Z', directory.name) or directory.is_symlink() or not directory.is_dir():
        continue
    try:
        marker = directory / '.complete'
        manifest = directory / 'manifest.txt'
        inventory = directory / 'inventory.txt'
        if any(p.is_symlink() for p in (marker, manifest, inventory)):
            continue
        completed = json.loads(marker.read_text())
        if (completed.get('version') != 2 or type(completed.get('finished_epoch')) is not int
                or not 0 < completed['finished_epoch'] <= time.time()
                or completed.get('project') != project
                or completed.get('manifest_sha256') != digest(manifest)
                or completed.get('inventory_sha256') != digest(inventory)
                or completed['inventory_sha256'] != current_inventory):
            continue
        patterns = [line.partition('#')[0].strip() for line in inventory.read_text().splitlines()]
        patterns = [p.replace("graf-posthog_", project + "_", 1) for p in patterns if p]
        if not patterns or any(not re.fullmatch(r'[A-Za-z0-9_.*-]+\??', p) for p in patterns):
            continue
        rows = [dict(token.split('=', 1) for token in line.split())
                for line in manifest.read_text().splitlines() if line.startswith('volume=')]
        if manifest.read_text().splitlines()[0] != "backup_reference=" + directory.name:
            continue
        volumes = [r['volume'] for r in rows]
        if (not volumes or set(volumes) != current_volumes or len(set(volumes)) != len(volumes)
                or any(not re.fullmatch(r'[A-Za-z0-9_-]+', v) for v in volumes)
                or any(not any(fnmatch.fnmatchcase(v, p.rstrip('?')) for p in patterns) for v in volumes)
                or any(not p.endswith('?') and not any(fnmatch.fnmatchcase(v, p) for v in volumes) for p in patterns)
                or {p.name for p in directory.glob('*.tar.gz')} != {v + '.tar.gz' for v in volumes}):
            continue
        for row in rows:
            archive = directory / (row['volume'] + '.tar.gz')
            if (archive.is_symlink() or archive.stat().st_size <= 0
                    or archive.stat().st_size != int(row['bytes']) or digest(archive) != row['sha256']):
                raise ValueError('invalid archive')
        print(directory.name)
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        continue
VERIFY
}

count_copies() {
  local verified
  verified="$(verified_sets)" || return 1
  printf '%s\n' "$verified" | awk 'NF {n++} END {print n+0}'
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
  local tmp_file
  mkdir -p "$(dirname "$state_file")" || return 1
  tmp_file="$(mktemp "$state_file.XXXXXX")" || return 1
  {
    printf 'backup_state_version=2\n'
    printf 'backup_set_complete=%s\n' "$([[ "$attempt_result" == pass ]] && printf true || printf false)"
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
  } > "$tmp_file" || return 1
  chmod 0640 "$tmp_file" || return 1
  python3 - "$tmp_file" "$state_file" <<'STATE'
import os, sys
with open(sys.argv[1], 'rb') as stream:
    os.fsync(stream.fileno())
os.replace(*sys.argv[1:])
fd = os.open(os.path.dirname(sys.argv[2]), os.O_RDONLY)
try:
    os.fsync(fd)
finally:
    os.close(fd)
STATE
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
previous_success_epoch=""
previous_success_at=""
previous_success_reference=""
volumes=()
label=unknown
staging_owned=0
fail_backup() {
  local reason="$1"
  local exit_code="${2:-1}"
  trap - EXIT ERR
  now_epoch="$(date +%s 2>/dev/null || printf 0)"
  recorded_at_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown)"
  echo "backup_result=failed"
  echo "reason=$reason"
  echo "backup_reference=$label"
  if (( staging_owned == 1 )); then
    if ! rm -rf -- "$target_dir"; then
      log_event critical "result=backup_staging_cleanup_failed"
    fi
  fi
  # Invalidate a previous pass even if the atomic replacement below fails.
  rm -f "$state_file" || log_event critical "result=state_invalidation_failed"
  if ! write_state "failed" "$reason" "$previous_success_epoch" "$previous_success_at" "$previous_success_reference" \
    "${#volumes[@]}" "0" "$(count_copies 2>/dev/null || printf 0)"; then
    log_event critical "result=backup_state_write_failed"
  fi
  raise_alert
  log_event critical "result=backup_failed reason=$reason reference=$label"
  exit "$exit_code"
}

if [[ "$mode" == execute ]]; then
  trap 'result=$?; if (( result != 0 )); then fail_backup unexpected_backup_failure "$result"; fi' EXIT
fi

# Existing guard pattern: keep the lock in a parent Python process.
if [[ "${GRAF_BACKUP_LOCK_HELD:-0}" != 1 && "$mode" == execute ]]; then
  mkdir -p "$state_dir"
  chmod 0750 "$state_dir"
  if (( EUID == 0 )); then
    chgrp "${TWOBRAIN_RUNTIME_SECRET_GID:-1001}" "$state_dir"
    chmod 2750 "$state_dir"
  fi
  if python3 - "$state_dir/backup.lock" "$BASH" "$0" --execute <<'LOCK'
import fcntl, os, subprocess, sys
try:
    lock = open(sys.argv[1], 'a')
    fcntl.flock(lock, fcntl.LOCK_EX)
except OSError:
    raise SystemExit(125)
with lock:
    env = dict(os.environ, GRAF_BACKUP_LOCK_HELD='1')
    raise SystemExit(subprocess.call(sys.argv[2:], env=env))
LOCK
  then result=0; else result=$?; fi
  if (( result == 125 || result == 126 || result == 127 )); then fail_backup lock_unavailable; fi
  trap - EXIT
  exit "$result"
fi

if [[ "$mode" == execute ]]; then
  if [[ -r "$state_file" ]]; then
    previous_success_epoch="$(awk 'index($0, "last_success_epoch=") == 1 {print substr($0, 20); exit}' "$state_file")"
    previous_success_at="$(awk 'index($0, "last_success_at=") == 1 {print substr($0, 17); exit}' "$state_file")"
    previous_success_reference="$(awk 'index($0, "last_success_reference=") == 1 {print substr($0, 24); exit}' "$state_file")"
  fi
  [[ "$previous_success_epoch" =~ ^[0-9]+$ ]] || previous_success_epoch=""
  if [[ "$previous_success_at" == "unknown" ]]; then
    previous_success_at=""
  fi

  # Remove and fsync the old readiness before any probe or fallible state write.
  rm -f "$state_file"
  python3 - "$state_dir" <<'INVALIDATE'
import os, sys
fd = os.open(sys.argv[1], os.O_RDONLY)
try:
    os.fsync(fd)
finally:
    os.close(fd)
INVALIDATE
  write_state running backup_in_progress "$previous_success_epoch" "$previous_success_at" "$previous_success_reference" 0 0 0
fi

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

if [[ ! "$keep_copies" =~ ^[0-9]+$ || ! "$minimum_copies" =~ ^[0-9]+$ ]] || (( minimum_copies != 2 || keep_copies != 7 )); then
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
target_dir="$backup_dir/.$label.incomplete"
final_dir="$backup_dir/$label"

required_patterns=()
optional_patterns=()
while IFS= read -r line; do
  line="${line%%#*}"
  line="$(printf '%s' "$line" | tr -d '[:space:]')"
  [[ -n "$line" ]] || continue
  [[ "$line" =~ ^[A-Za-z0-9_.*?-]+$ ]] || { echo "reason=backup_inventory_invalid"; exit 2; }
  line="${line/graf-posthog_/${project}_}"
  if [[ "$line" == *'?' ]]; then
    optional_patterns+=("${line%?}")
  else
    required_patterns+=("$line")
  fi
done < "$inventory_file"

volumes=()
unclassified_volumes=0
if ! volume_list="$(docker volume ls --format '{{.Name}}' 2>/dev/null)"; then
  echo "backup_result=blocked"
  echo "reason=docker_volume_list_unavailable"
  exit 1
fi
while IFS= read -r name; do
  [[ -n "$name" ]] || continue
  [[ "$name" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "reason=volume_name_invalid"; exit 1; }
  classified=0
  for pattern in "${required_patterns[@]-}" "${optional_patterns[@]-}"; do
    [[ -n "$pattern" ]] || continue
    # shellcheck disable=SC2053
    if [[ "$name" == $pattern ]]; then
      volumes+=("$name")
      classified=1
      break
    fi
  done
  if [[ "$name" == "$project"_* && "$classified" == 0 ]]; then unclassified_volumes=1; fi
done <<< "$volume_list"
# Docker project labels also cover explicitly named (non-prefixed) volumes.
if ! labelled_volumes="$(docker volume ls --format '{{.Name}}' --filter "label=com.docker.compose.project=$project" 2>/dev/null)"; then
  echo "reason=project_volume_list_unavailable"; exit 1
fi
while IFS= read -r name; do
  [[ -n "$name" ]] || continue
  classified=0
  for volume in "${volumes[@]-}"; do [[ "$name" == "$volume" ]] && classified=1; done
  (( classified == 1 )) || unclassified_volumes=1
done <<< "$labelled_volumes"

# Image-created anonymous volumes may have neither the project prefix nor label.
# Check actual mounts too; an unknown volume must never yield a complete set.
if ! project_containers="$(docker ps -aq --filter "label=com.docker.compose.project=$project" 2>/dev/null)"; then
  echo "reason=project_container_list_unavailable"; exit 1
fi
container_ids=()
while IFS= read -r container_id; do
  [[ -n "$container_id" ]] || continue
  [[ "$container_id" =~ ^[a-f0-9]{12,64}$ ]] || { echo "reason=container_id_invalid"; exit 1; }
  container_ids+=("$container_id")
done <<< "$project_containers"
if (( ${#container_ids[@]} > 0 )); then
  if ! mounted_volumes="$(docker inspect --format '{{range .Mounts}}{{if eq .Type "volume"}}{{println .Name}}{{end}}{{end}}' "${container_ids[@]}" 2>/dev/null)"; then
    echo "reason=project_mount_inventory_unavailable"; exit 1
  fi
  while IFS= read -r name; do
    [[ -n "$name" ]] || continue
    classified=0
    for volume in "${volumes[@]-}"; do [[ "$name" == "$volume" ]] && classified=1; done
    (( classified == 1 )) || unclassified_volumes=1
  done <<< "$mounted_volumes"
fi

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
  printf 'copy_policy=local_verified_sets\n'
  printf 'next_step=run_with_--execute_from_the_analytics_host\n'
  exit 0
fi

if (( ${#volumes[@]} == 0 )); then
  fail_backup "no_volumes_matched"
fi
if (( ${#unmatched_required[@]} > 0 )); then
  fail_backup "required_volume_class_missing"
fi
if (( unclassified_volumes == 1 )); then fail_backup "project_volume_unclassified"; fi
if ! command -v docker >/dev/null 2>&1; then
  fail_backup "docker_unavailable"
fi

[[ ! -L "$backup_dir" ]] || fail_backup backup_directory_linked
mkdir -p "$backup_dir" "$state_dir"
chmod 0700 "$backup_dir"
[[ ! -e "$target_dir" && ! -e "$final_dir" ]] || fail_backup backup_reference_exists
mkdir "$target_dir"
staging_owned=1
cp "$inventory_file" "$target_dir/inventory.txt"
archive_bytes=0
manifest="$target_dir/manifest.txt"
{
  printf 'backup_reference=%s\n' "$label"
  printf 'created_at=%s\n' "$recorded_at_iso"
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
  chmod 0600 "$archive"
  size_bytes="$(file_size "$archive")"
  digest="$(sha256_of "$archive")"
  archive_bytes=$((archive_bytes + size_bytes))
  printf 'volume=%s bytes=%s sha256=%s\n' "$volume" "$size_bytes" "$digest" >> "$manifest"
  printf 'volume_archived=%s\n' "$volume"
done

# Persist the complete set before making it visible to readers/rotation.
python3 - "$target_dir" "$final_dir" "$project" <<'COMPLETE'
import hashlib, json, os, sys, time
from pathlib import Path
stage, target = map(Path, sys.argv[1:3])
hashes = {}
for path in stage.iterdir():
    with path.open('rb') as stream:
        os.fsync(stream.fileno())
        if path.name in ('manifest.txt', 'inventory.txt'):
            hashes[path.name] = hashlib.file_digest(stream, 'sha256').hexdigest()
with (stage / '.complete').open('x') as stream:
    json.dump({'version': 2, 'finished_epoch': int(time.time()), 'project': sys.argv[3],
               'manifest_sha256': hashes['manifest.txt'], 'inventory_sha256': hashes['inventory.txt']}, stream)
    stream.flush()
    os.fsync(stream.fileno())
fd = os.open(stage, os.O_RDONLY)
try:
    os.fsync(fd)
finally:
    os.close(fd)
os.rename(stage, target)
fd = os.open(target.parent, os.O_RDONLY)
try:
    os.fsync(fd)
finally:
    os.close(fd)
COMPLETE
staging_owned=0
now_epoch="$(date +%s)"
recorded_at_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
verified="$(verified_sets)" || fail_backup complete_sets_unverified
printf '%s\n' "$verified" | awk -v label="$label" '$0==label {found=1} END {exit !found}' || fail_backup new_set_unverified

# Retention: keep the newest copies, delete the rest, never below the minimum.
existing=()
while IFS= read -r existing_dir; do
  [[ -n "$existing_dir" ]] && existing+=("$existing_dir")
done <<< "$verified"
if (( ${#existing[@]} > keep_copies )); then
  delete_count=$(( ${#existing[@]} - keep_copies ))
  for (( index = 0; index < delete_count; index++ )); do
    victim="$backup_dir/${existing[index]}"
    remaining=$(( ${#existing[@]} - index ))
    if (( remaining <= minimum_copies )); then
      printf 'retention_kept=%s\n' "$(basename "$victim")"
      continue
    fi
    if rm -rf "$victim"; then
      printf 'retention_deleted=%s\n' "$(basename "$victim")"
      log_event pass "result=retention_deleted reference=$(basename "$victim")"
    else
      fail_backup retention_delete_failed
    fi
  done
fi

copies_local="$(count_copies)"
now_epoch="$(date +%s)"
recorded_at_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
write_state "pass" "none" "$now_epoch" "$recorded_at_iso" "$label" "${#volumes[@]}" "$archive_bytes" "$copies_local"
log_event pass "result=backup_pass reference=$label volumes=${#volumes[@]} copies_local=$copies_local"

echo "backup_result=pass"
echo "backup_reference=$label"
echo "volumes_archived=${#volumes[@]}"
echo "bytes_archived=$archive_bytes"
echo "copies_local=$copies_local"
echo "retention_keep=$keep_copies"
echo "product_impact=none"
exit 0
