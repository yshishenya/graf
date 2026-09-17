#!/usr/bin/env sh
# Weekly restore rehearsal for the production stack.
#
# The rehearsal used to run inside every release (step `restore_rehearsal` of
# `infra/scripts/cd-remote.sh`). It restores the whole Postgres dump and the
# whole object store into disposable targets, so it dominated release time; it
# now runs on a schedule instead. The release keeps its own fresh backup
# (`infra/scripts/backup-rec-stack.sh`) and reports `backup_reference=`, and
# this script proves that a backup can actually be restored.
#
# How to run it
# -------------
# Run it from a workstation that can already reach the production host the same
# way `infra/scripts/cd-remote.sh` does:
#
#   infra/scripts/rehearse-restore-scheduled.sh --dry-run
#   infra/scripts/rehearse-restore-scheduled.sh --execute
#   infra/scripts/rehearse-restore-scheduled.sh --execute \
#     --backup-reference /opt/projects/2brain-rec/backups/20260917T101500Z
#
# Without `--backup-reference` the script asks the production host for the
# newest directory under `<deploy path>/backups/` and rehearses that one.
#
# Why the GitHub schedule cannot do this by itself yet
# --------------------------------------------------
# No workflow in this repository has production host access: every job runs on
# GitHub-hosted runners, no workflow uses SSH, and Actions has no deploy key.
# `.github/workflows/backup-restore-rehearsal.yml` therefore fails closed with
# `reason=production_host_ssh_secret_missing` until the operator provisions
# `PROD_SSH_HOST`, `PROD_SSH_USER`, `PROD_SSH_KEY` and `PROD_SSH_KNOWN_HOSTS`.
# Until then the weekly run is the reminder and this script is the real check.
#
# The rehearsal itself is non-destructive: it restores into a temporary
# database and a temporary bucket and drops both afterwards.

set -eu

host="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
path="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"
mode="dry-run"
backup_reference="${TWOBRAIN_RESTORE_BACKUP_REFERENCE:-}"

usage() {
  cat >&2 <<EOF
usage: $0 [--dry-run|--execute] [--backup-reference <absolute path on the production host>]
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)
      mode="dry-run"
      shift
      ;;
    --execute)
      mode="execute"
      shift
      ;;
    --backup-reference)
      backup_reference="${2:-}"
      shift 2
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

# The reference travels into a remote shell command, so accept only absolute
# paths made of characters that cannot break out of the quoting below.
valid_backup_reference() {
  case "$1" in
    /*) ;;
    *) return 1 ;;
  esac
  case "$1" in
    *[!A-Za-z0-9._/-]*) return 1 ;;
  esac
  return 0
}

if [ -n "$backup_reference" ] && ! valid_backup_reference "$backup_reference"; then
  echo "restore_rehearsal_schedule_result=blocked"
  echo "reason=backup_reference_invalid"
  echo "backup_reference=$backup_reference"
  exit 1
fi

if [ "$mode" != "execute" ]; then
  cat <<EOF
restore_rehearsal_schedule_result=dry_run
remote_host=$host
deploy_path=$path
backup_reference=${backup_reference:-newest_under_${path}/backups_resolved_on_execute}
next_step=run_with_--execute_from_a_workstation_that_can_ssh_$host
EOF
  exit 0
fi

if [ -z "$backup_reference" ]; then
  if ! newest="$(ssh "$host" "cd '$path' && ls -1d backups/*/ 2>/dev/null | sort | tail -n 1")"; then
    echo "restore_rehearsal_schedule_result=blocked"
    echo "reason=backup_reference_discovery_failed"
    echo "remote_host=$host"
    echo "deploy_path=$path"
    exit 1
  fi
  newest="${newest%/}"
  if [ -z "$newest" ]; then
    echo "restore_rehearsal_schedule_result=blocked"
    echo "reason=backup_reference_missing"
    echo "remote_host=$host"
    echo "deploy_path=$path"
    echo "searched=$path/backups/"
    exit 1
  fi
  backup_reference="$path/$newest"
  if ! valid_backup_reference "$backup_reference"; then
    echo "restore_rehearsal_schedule_result=blocked"
    echo "reason=backup_reference_invalid"
    echo "backup_reference=$backup_reference"
    exit 1
  fi
fi

checked_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if ! rehearsal_output="$(
  ssh "$host" "cd '$path' && RESTORE_BACKUP_REFERENCE='$backup_reference' ./infra/scripts/rehearse-rec-restore.sh --execute" 2>&1
)"; then
  printf '%s\n' "$rehearsal_output"
  echo "restore_rehearsal_schedule_result=blocked"
  echo "reason=restore_rehearsal_failed"
  echo "backup_reference=$backup_reference"
  echo "checked_at=$checked_at"
  exit 1
fi
printf '%s\n' "$rehearsal_output"

if ! printf '%s\n' "$rehearsal_output" | grep -qx 'restore_rehearsal_result=pass'; then
  echo "restore_rehearsal_schedule_result=blocked"
  echo "reason=restore_rehearsal_result_missing"
  echo "backup_reference=$backup_reference"
  echo "checked_at=$checked_at"
  exit 1
fi

cat <<EOF
restore_rehearsal_schedule_result=pass
remote_host=$host
deploy_path=$path
backup_reference=$backup_reference
checked_at=$checked_at
EOF
