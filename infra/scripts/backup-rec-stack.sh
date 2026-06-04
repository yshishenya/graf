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
postgres_artifact=postgres.dump
minio_artifact=minio-objects/
next_step=run_with_--remote_after_preflight
EOF
  exit 0
fi

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

mkdir -p "$backup_dir"
docker compose -f infra/docker-compose.yml exec -T rec-postgres \
  pg_dump -U twobrain_rec -d twobrain_rec --format=custom --file=/tmp/twobrain-rec-postgres.dump
docker cp "$(docker compose -f infra/docker-compose.yml ps -q rec-postgres)":/tmp/twobrain-rec-postgres.dump "$backup_dir/postgres.dump"
docker compose -f infra/docker-compose.yml exec -T rec-postgres rm -f /tmp/twobrain-rec-postgres.dump

mkdir -p "$backup_dir/minio-objects"
root_user_file="${TWOBRAIN_MINIO_ROOT_USER_FILE:-./secrets/twobrain_minio_root_user}"
root_password_file="${TWOBRAIN_MINIO_ROOT_PASSWORD_FILE:-./secrets/twobrain_minio_root_password}"
docker run --rm \
  --network twobrain-rec-private \
  -e "TWOBRAIN_MINIO_BUCKET=${TWOBRAIN_MINIO_BUCKET:-twobrain-rec-ingest}" \
  -v "$backup_dir/minio-objects":/backup/minio-objects \
  -v "$root_user_file":/run/secrets/twobrain_minio_root_user:ro \
  -v "$root_password_file":/run/secrets/twobrain_minio_root_password:ro \
  minio/mc:RELEASE.2025-05-21T01-59-54Z \
  sh -c 'mc alias set rec http://rec-minio:9000 "$(cat /run/secrets/twobrain_minio_root_user)" "$(cat /run/secrets/twobrain_minio_root_password)" >/dev/null && mc mirror --overwrite "rec/${TWOBRAIN_MINIO_BUCKET:-twobrain-rec-ingest}" /backup/minio-objects >/dev/null'
cat <<EOF
backup_result=pass
backup_reference=$backup_dir
postgres_artifact=$backup_dir/postgres.dump
minio_artifact=$backup_dir/minio-objects/
EOF
