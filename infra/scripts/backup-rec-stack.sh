#!/usr/bin/env sh
set -eu

host="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
path="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="${TWOBRAIN_BACKUP_DIR:-/opt/projects/2brain-rec/backups/$timestamp}"

if [ "${1:-}" = "--remote" ]; then
  exec ssh "$host" "cd '$path' && TWOBRAIN_BACKUP_DIR='$backup_dir' ./infra/scripts/backup-rec-stack.sh --execute"
fi

if [ "${1:-}" != "--execute" ]; then
  cat <<EOF
backup_result=dry_run
remote_host=$host
deploy_path=$path
backup_reference=$backup_dir
postgres_volume=twobrain-rec-postgres-data
minio_volume=twobrain-rec-minio-data
next_step=run_with_--remote_after_preflight
EOF
  exit 0
fi

mkdir -p "$backup_dir"
docker run --rm -v twobrain-rec-postgres-data:/source:ro -v "$backup_dir":/backup alpine \
  sh -c 'cd /source && tar czf /backup/postgres-volume.tgz .'
docker run --rm -v twobrain-rec-minio-data:/source:ro -v "$backup_dir":/backup alpine \
  sh -c 'cd /source && tar czf /backup/minio-volume.tgz .'
cat <<EOF
backup_result=pass
backup_reference=$backup_dir
postgres_volume=twobrain-rec-postgres-data
minio_volume=twobrain-rec-minio-data
EOF
