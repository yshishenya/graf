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

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

test -d "$RESTORE_BACKUP_REFERENCE"
test -f "$RESTORE_BACKUP_REFERENCE/postgres.dump"
test -d "$RESTORE_BACKUP_REFERENCE/minio-objects"

restore_db="rec_restore_rehearsal_$(date -u +%Y%m%d%H%M%S)"
restore_bucket="twobrain-rec-restore-rehearsal-$(date -u +%Y%m%d%H%M%S)"
cleanup() {
  docker compose -f infra/docker-compose.yml exec -T rec-postgres dropdb -U twobrain_rec --if-exists "$restore_db" >/dev/null 2>&1 || true
  if [ -n "${root_user_file:-}" ] && [ -n "${root_password_file:-}" ]; then
    docker run --rm \
      --network twobrain-rec-private \
      -e "TWOBRAIN_MINIO_BUCKET=${TWOBRAIN_MINIO_BUCKET:-twobrain-rec-ingest}" \
      -v "$root_user_file":/run/secrets/twobrain_minio_root_user:ro \
      -v "$root_password_file":/run/secrets/twobrain_minio_root_password:ro \
      minio/mc:RELEASE.2025-05-21T01-59-54Z \
      sh -c 'mc alias set rec http://rec-minio:9000 "$(cat /run/secrets/twobrain_minio_root_user)" "$(cat /run/secrets/twobrain_minio_root_password)" >/dev/null && mc rb --force "rec/'"$restore_bucket"'" >/dev/null 2>&1 || true' >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

docker compose -f infra/docker-compose.yml exec -T rec-postgres createdb -U twobrain_rec "$restore_db"
docker compose -f infra/docker-compose.yml exec -T rec-postgres mkdir -p /tmp/twobrain-rec-restore
docker cp "$RESTORE_BACKUP_REFERENCE/postgres.dump" "$(docker compose -f infra/docker-compose.yml ps -q rec-postgres)":/tmp/twobrain-rec-restore/postgres.dump
docker compose -f infra/docker-compose.yml exec -T rec-postgres \
  pg_restore -U twobrain_rec -d "$restore_db" --no-owner /tmp/twobrain-rec-restore/postgres.dump
docker compose -f infra/docker-compose.yml exec -T rec-postgres \
  psql -U twobrain_rec -d "$restore_db" -Atc "select count(*) >= 0 from information_schema.tables" >/dev/null

root_user_file="${TWOBRAIN_MINIO_ROOT_USER_FILE:-./secrets/twobrain_minio_root_user}"
root_password_file="${TWOBRAIN_MINIO_ROOT_PASSWORD_FILE:-./secrets/twobrain_minio_root_password}"
docker run --rm \
  --network twobrain-rec-private \
  -e "TWOBRAIN_MINIO_BUCKET=${TWOBRAIN_MINIO_BUCKET:-twobrain-rec-ingest}" \
  -v "$RESTORE_BACKUP_REFERENCE/minio-objects":/backup/minio-objects:ro \
  -v "$root_user_file":/run/secrets/twobrain_minio_root_user:ro \
  -v "$root_password_file":/run/secrets/twobrain_minio_root_password:ro \
  minio/mc:RELEASE.2025-05-21T01-59-54Z \
  sh -c 'mc alias set rec http://rec-minio:9000 "$(cat /run/secrets/twobrain_minio_root_user)" "$(cat /run/secrets/twobrain_minio_root_password)" >/dev/null && mc mb --ignore-existing "rec/'"$restore_bucket"'" >/dev/null && mc mirror --overwrite /backup/minio-objects "rec/'"$restore_bucket"'" >/dev/null && mc ls --recursive "rec/'"$restore_bucket"'" >/dev/null'
cat <<EOF
restore_rehearsal_result=pass
backup_reference=$RESTORE_BACKUP_REFERENCE
postgres_restore_target=$restore_db
minio_restore_target=$restore_bucket
EOF
