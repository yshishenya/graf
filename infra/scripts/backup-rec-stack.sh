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

if [ -z "${GRAF_RELEASE_MC_IMAGE:-}" ]; then
  GRAF_RELEASE_MC_IMAGE="$(python3 infra/scripts/release-images.py current-override --service rec-minio-init)"
fi

umask 077
fail() {
  printf 'backup_result=failed\nreason=%s\n' "$1" >&2
  exit 1
}

# Never reuse a destination: even an empty directory may belong to another run.
mkdir -p "$(dirname "$backup_dir")"
mkdir -m 700 "$backup_dir" 2>/dev/null || fail backup_destination_exists_or_unavailable
# Five octal digits also clear directory setgid inherited from the parent.
chmod 00700 "$backup_dir" 2>/dev/null || fail backup_permissions_failed
staging=""
cleanup() {
  result=$?
  trap - EXIT HUP INT TERM
  if [ -n "$staging" ]; then
    if ! docker compose -f infra/docker-compose.yml exec -T rec-postgres \
      sh -c 'umask 077; rm -rf -- "$1"' sh "$staging" >/dev/null 2>&1; then
      printf 'backup_result=failed\nreason=postgres_staging_cleanup_failed\n' >&2
      result=1
    fi
  fi
  exit "$result"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

staging_candidate="$(docker compose -f infra/docker-compose.yml exec -T rec-postgres \
  sh -c 'umask 077; mktemp -d /tmp/twobrain-rec-backup.XXXXXX' 2>/dev/null)" \
  || fail postgres_staging_create_failed
case "$staging_candidate" in
  /tmp/twobrain-rec-backup.*) suffix="${staging_candidate#/tmp/twobrain-rec-backup.}" ;;
  *) fail postgres_staging_invalid ;;
esac
case "$suffix" in
  ''|*[!a-zA-Z0-9]*) fail postgres_staging_invalid ;;
esac
staging="$staging_candidate"
docker compose -f infra/docker-compose.yml exec -T rec-postgres \
  sh -c 'umask 077; pg_dump -U twobrain_rec -d twobrain_rec --format=custom --file="$1/postgres.dump"' \
  sh "$staging" 2>/dev/null || fail postgres_dump_failed
postgres_id="$(docker compose -f infra/docker-compose.yml ps -q rec-postgres 2>/dev/null)" \
  || fail postgres_container_lookup_failed
[ -n "$postgres_id" ] || fail postgres_container_missing
docker cp "$postgres_id:$staging/postgres.dump" "$backup_dir/postgres.dump" 2>/dev/null \
  || fail postgres_copy_failed

mkdir -p "$backup_dir/minio-objects"
root_user_file="${TWOBRAIN_MINIO_ROOT_USER_FILE:-./secrets/twobrain_minio_root_user}"
root_password_file="${TWOBRAIN_MINIO_ROOT_PASSWORD_FILE:-./secrets/twobrain_minio_root_password}"
docker run --rm --pull never \
  --user "$(id -u):$(id -g)" \
  --network twobrain-rec-private \
  --entrypoint /bin/sh \
  -e MC_CONFIG_DIR=/tmp/graf-backup-mc \
  -e "TWOBRAIN_MINIO_BUCKET=${TWOBRAIN_MINIO_BUCKET:-twobrain-rec-ingest}" \
  -v "$backup_dir/minio-objects":/backup/minio-objects \
  -v "$root_user_file":/run/secrets/twobrain_minio_root_user:ro \
  -v "$root_password_file":/run/secrets/twobrain_minio_root_password:ro \
  "${GRAF_RELEASE_MC_IMAGE:-minio/mc:RELEASE.2025-05-21T01-59-54Z}" \
  -c 'set -eu; umask 077; mc alias set rec http://rec-minio:9000 "$(cat /run/secrets/twobrain_minio_root_user)" "$(cat /run/secrets/twobrain_minio_root_password)" >/dev/null; mc mirror --overwrite "rec/${TWOBRAIN_MINIO_BUCKET:-twobrain-rec-ingest}" /backup/minio-objects >/dev/null' \
  2>/dev/null || fail minio_copy_failed

# Tools may explicitly override umask. Reject links/special files before chmod;
# never follow a link or change permissions of a hard-linked external file.
unusual="$(find "$backup_dir" ! -type d ! -type f -print 2>/dev/null)" \
  || fail backup_inventory_failed
[ -z "$unusual" ] || fail backup_unusual_object
linked="$(find "$backup_dir" -type f -links +1 -print 2>/dev/null)" \
  || fail backup_inventory_failed
[ -z "$linked" ] || fail backup_hardlinked_file
find "$backup_dir" -type d -exec chmod 00700 {} + 2>/dev/null \
  || fail backup_permissions_failed
find "$backup_dir" -type f -exec chmod 600 {} + 2>/dev/null \
  || fail backup_permissions_failed

# PASS is printed only after successful cleanup, including its exit status.
docker compose -f infra/docker-compose.yml exec -T rec-postgres \
  sh -c 'umask 077; rm -rf -- "$1"' sh "$staging" >/dev/null 2>&1 \
  || fail postgres_staging_cleanup_failed
staging=""
cat <<EOF
backup_result=pass
backup_reference=$backup_dir
postgres_artifact=$backup_dir/postgres.dump
minio_artifact=$backup_dir/minio-objects/
EOF
