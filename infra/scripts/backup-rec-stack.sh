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

backup_postgres_id=""
backup_minio_id=""
backup_bucket=""
release_mc_image="${GRAF_RELEASE_MC_IMAGE:-}"
if [ "$#" -ne 1 ]; then
  [ "$#" -eq 5 ] && [ "$2" = "--pinned-stores" ] || exit 2
  backup_postgres_id="$3"
  backup_minio_id="$4"
  backup_bucket="$5"
  for container in "$backup_postgres_id" "$backup_minio_id"; do
    printf '%s\n' "$container" | grep -Eq '^[0-9a-f]{64}$' || exit 2
  done
  printf '%s\n' "$release_mc_image" | grep -Eq '^sha256:[0-9a-f]{64}$' || exit 2
  printf '%s\n' "$backup_bucket" | grep -Eq '^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$' || exit 2
fi

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

if [ -n "$release_mc_image" ]; then
  GRAF_RELEASE_MC_IMAGE="$release_mc_image"
elif [ -z "${GRAF_RELEASE_MC_IMAGE:-}" ]; then
  GRAF_RELEASE_MC_IMAGE="$(python3 infra/scripts/release-images.py current-override --service rec-minio-init)"
fi

umask 077
fail() {
  printf 'backup_result=failed\nreason=%s\n' "$1" >&2
  exit 1
}

postgres_exec() {
  if [ -n "$backup_postgres_id" ]; then
    docker exec -i "$backup_postgres_id" "$@"
  else
    docker compose -f infra/docker-compose.yml exec -T rec-postgres "$@"
  fi
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
  if [ "$result" -ne 0 ] && [ -n "$backup_bucket" ]; then
    if ! rm -f -- "$backup_dir/.minio-version" "$backup_dir/.minio-version-after" \
      "$backup_dir/.minio-incomplete-before" "$backup_dir/.minio-incomplete-after" \
      "$backup_dir/.minio-before" "$backup_dir/.minio-after" "$backup_dir/.minio-hashes"; then
      printf 'backup_result=failed\nreason=minio_inventory_cleanup_failed\n' >&2
      result=1
    fi
  fi
  if [ -n "$staging" ]; then
    if ! postgres_exec \
      sh -c 'umask 077; rm -rf -- "$1"' sh "$staging" >/dev/null 2>&1; then
      printf 'backup_result=failed\nreason=postgres_staging_cleanup_failed\n' >&2
      result=1
    fi
  fi
  exit "$result"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

staging_candidate="$(postgres_exec \
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
script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
# PostgreSQL owns the exported snapshot until both dump and metadata finish.
postgres_exec \
  sh -c 'umask 077; psql -XqAt -v ON_ERROR_STOP=1 -U twobrain_rec -d twobrain_rec -v expected_db=twobrain_rec -v capture_dump=true -v staging="$1"' \
  sh "$staging" <"$script_dir/rec-db-backup-inventory.sql" 2>/dev/null \
  || fail postgres_snapshot_failed
postgres_id="$backup_postgres_id"
if [ -z "$postgres_id" ]; then
  postgres_id="$(docker compose -f infra/docker-compose.yml ps -q rec-postgres 2>/dev/null)" \
    || fail postgres_container_lookup_failed
fi
[ -n "$postgres_id" ] || fail postgres_container_missing
for artifact in postgres.dump schema.sql inventory.jsonl checksums.sha256; do
  docker cp "$postgres_id:$staging/$artifact" "$backup_dir/$artifact" 2>/dev/null \
    || fail postgres_copy_failed
  [ -s "$backup_dir/$artifact" ] || fail postgres_artifact_empty
done
python3 "$script_dir/rec-db-verify.py" "$backup_dir" 2>/dev/null \
  || fail postgres_checksum_failed

mkdir -p "$backup_dir/minio-objects"
root_user_file="${TWOBRAIN_MINIO_ROOT_USER_FILE:-./secrets/twobrain_minio_root_user}"
root_password_file="${TWOBRAIN_MINIO_ROOT_PASSWORD_FILE:-./secrets/twobrain_minio_root_password}"
minio_network="twobrain-rec-private"
minio_endpoint="http://rec-minio:9000"
minio_mount="$backup_dir/minio-objects:/backup/minio-objects"
if [ -n "$backup_minio_id" ]; then
  minio_network="container:$backup_minio_id"
  minio_endpoint="http://127.0.0.1:9000"
  minio_mount="$backup_dir:/backup"
fi
docker run --rm --pull never \
  --user "$(id -u):$(id -g)" \
  --network "$minio_network" \
  --entrypoint /bin/bash \
  -e MC_CONFIG_DIR=/tmp/graf-backup-mc \
  -e "GRAF_BACKUP_MINIO_ENDPOINT=$minio_endpoint" \
  -e "GRAF_BACKUP_PINNED_BUCKET=$backup_bucket" \
  -e "TWOBRAIN_MINIO_BUCKET=${TWOBRAIN_MINIO_BUCKET:-twobrain-rec-ingest}" \
  -v "$minio_mount" \
  -v "$root_user_file":/run/secrets/twobrain_minio_root_user:ro \
  -v "$root_password_file":/run/secrets/twobrain_minio_root_password:ro \
  "${GRAF_RELEASE_MC_IMAGE:-minio/mc:RELEASE.2025-05-21T01-59-54Z}" \
  -c '
    set -euo pipefail
    umask 077
    mc alias set rec "$GRAF_BACKUP_MINIO_ENDPOINT" "$(cat /run/secrets/twobrain_minio_root_user)" "$(cat /run/secrets/twobrain_minio_root_password)" >/dev/null
    source="rec/${GRAF_BACKUP_PINNED_BUCKET:-${TWOBRAIN_MINIO_BUCKET:-twobrain-rec-ingest}}"
    record_object_stats() {
      # Recursive stat fails for an empty bucket; only an independently empty listing can substitute.
      if ! mc --json stat --recursive "$source" >"$1"; then
        mc --json ls --recursive "$source" >"$1"
        test ! -s "$1"
      fi
    }
    if [ -n "$GRAF_BACKUP_PINNED_BUCKET" ]; then
      mc --json version info "$source" >/backup/.minio-version
      mc --json ls --recursive --incomplete "$source" >/backup/.minio-incomplete-before
      test ! -s /backup/.minio-incomplete-before
      record_object_stats /backup/.minio-before
    fi
    mc mirror --overwrite "$source" /backup/minio-objects >/dev/null
    if [ -n "$GRAF_BACKUP_PINNED_BUCKET" ]; then
      source_hashes() {
        local entry key sum
        for entry in "$1"/* "$1"/.[!.]* "$1"/..?*; do
          [ -e "$entry" ] || continue
          test ! -L "$entry"
          if [ -d "$entry" ]; then
            source_hashes "$entry"
          else
            test -f "$entry"
            key="${entry#/backup/minio-objects/}"
            sum="$(mc cat "$source/$key" | sha256sum)"
            printf "%s\t%s\n" "${sum%% *}" "$key"
          fi
        done
      }
      source_hashes /backup/minio-objects >/backup/.minio-hashes
      record_object_stats /backup/.minio-after
      mc --json version info "$source" >/backup/.minio-version-after
      mc --json ls --recursive --incomplete "$source" >/backup/.minio-incomplete-after
      test ! -s /backup/.minio-incomplete-after
    fi
  ' \
  2>/dev/null || fail minio_copy_failed

if [ -n "$backup_bucket" ]; then
  python3 "$script_dir/verify-rec-object-backup.py" "$backup_dir" "$backup_bucket" \
    || fail minio_inventory_verification_failed
fi

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
postgres_exec \
  sh -c 'umask 077; rm -rf -- "$1"' sh "$staging" >/dev/null 2>&1 \
  || fail postgres_staging_cleanup_failed
staging=""
cat <<EOF
backup_result=pass
backup_reference=$backup_dir
postgres_artifact=$backup_dir/postgres.dump
minio_artifact=$backup_dir/minio-objects/
EOF
