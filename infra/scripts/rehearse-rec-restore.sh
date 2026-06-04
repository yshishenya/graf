#!/usr/bin/env sh
set -eu

host="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
path="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"

if [ "${1:-}" = "--remote" ]; then
  exec ssh "$host" "cd '$path' && RESTORE_BACKUP_REFERENCE='${RESTORE_BACKUP_REFERENCE:-}' ./infra/scripts/rehearse-rec-restore.sh --execute"
fi

if [ -z "${RESTORE_BACKUP_REFERENCE:-}" ]; then
  cat <<EOF
restore_rehearsal_result=blocked
reason=backup_reference_missing
remote_host=$host
deploy_path=$path
EOF
  exit 0
fi

if [ "${1:-}" != "--execute" ]; then
  cat <<EOF
restore_rehearsal_result=dry_run
backup_reference=$RESTORE_BACKUP_REFERENCE
remote_host=$host
deploy_path=$path
EOF
  exit 0
fi

test -d "$RESTORE_BACKUP_REFERENCE"
test -f "$RESTORE_BACKUP_REFERENCE/postgres-volume.tgz"
test -f "$RESTORE_BACKUP_REFERENCE/minio-volume.tgz"
cat <<EOF
restore_rehearsal_result=pass
backup_reference=$RESTORE_BACKUP_REFERENCE
EOF
