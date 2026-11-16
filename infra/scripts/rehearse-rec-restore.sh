#!/usr/bin/env sh
set -eu
umask 077
host="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
path="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"
reference="${RESTORE_BACKUP_REFERENCE:-}"
forward_attempt=""
if [ "$#" -gt 1 ]; then
  [ "$#" = 3 ] && [ "$2" = "--forward-attempt" ] || exit 1
  forward_attempt="$3"
  case "$forward_attempt" in *[!a-f0-9]*) exit 1 ;; esac
  [ "${#forward_attempt}" = 32 ] || exit 1
fi
if [ -z "$reference" ]; then
  printf 'restore_rehearsal_result=blocked\nreason=backup_reference_missing\n'
  exit 0
fi
case "$reference" in /*) ;; *) printf 'restore_rehearsal_result=blocked\nreason=backup_reference_invalid\n'; exit 1 ;; esac
case "$reference" in *[!A-Za-z0-9._/-]*) printf 'restore_rehearsal_result=blocked\nreason=backup_reference_invalid\n'; exit 1 ;; esac
if [ "${1:-}" = "--remote" ]; then
  forward_argument=""
  if [ -n "$forward_attempt" ]; then forward_argument=" --forward-attempt $forward_attempt"; fi
  exec ssh "$host" "cd '$path' && RESTORE_BACKUP_REFERENCE='$reference' ./infra/scripts/rehearse-rec-restore.sh --execute$forward_argument"
fi
if [ "${1:-}" != "--execute" ]; then
  printf 'restore_rehearsal_result=dry_run\nbackup_reference=%s\n' "$reference"
  exit 0
fi
if [ -L "$reference" ] || [ ! -d "$reference" ] || [ -L "$reference/postgres.dump" ] || [ ! -s "$reference/postgres.dump" ] || [ -L "$reference/minio-objects" ] || [ ! -d "$reference/minio-objects" ]; then
  printf 'restore_rehearsal_result=blocked\nreason=backup_set_incomplete\n'
  exit 1
fi
if [ -n "$forward_attempt" ]; then
  if [ ! -f "$reference/minio-inventory.jsonl" ] || [ -L "$reference/minio-inventory.jsonl" ]; then
    printf 'restore_rehearsal_result=blocked\nreason=protected_object_manifest_missing_or_invalid\n'
    exit 1
  fi
elif [ -e "$reference/minio-inventory.jsonl" ] || [ -L "$reference/minio-inventory.jsonl" ]; then
  printf 'restore_rehearsal_result=blocked\nreason=forward_attempt_required\n'
  exit 1
fi
script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ -z "$forward_attempt" ] && ! python3 "$script_dir/rec-db-verify.py" "$reference" --inventory 2>/dev/null; then
  printf 'restore_rehearsal_result=blocked\nreason=postgres_backup_unverified\n'
  exit 1
fi
# Reuse the deployment lock: a rehearsal may not overlap production replacement.
if [ "${GRAF_RESTORE_LOCK_HELD:-0}" != "1" ]; then
  exec python3 - "$0" "$@" <<'PY'
import fcntl, os, signal, subprocess, sys
path = subprocess.check_output(['git', 'rev-parse', '--git-path', 'twobrain-rec-deploy.lock'], text=True).strip()
with open(path, 'a') as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('restore_rehearsal_result=blocked\nreason=deployment_or_rehearsal_running')
        raise SystemExit(1)
    child = None
    pending = set()
    def forward(number, frame):
        if child is None:
            pending.add(number)
            return
        try:
            child.send_signal(number)
        except ProcessLookupError:
            pass
    for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(number, forward)
    child = subprocess.Popen(['sh', *sys.argv[1:]],
                             env=dict(os.environ, GRAF_RESTORE_LOCK_HELD='1', GRAF_RESTORE_LOCK_FD=str(lock.fileno())),
                             pass_fds=(lock.fileno(),))
    for number in pending:
        forward(number, None)
    status = child.wait()
    raise SystemExit(status if status >= 0 else 128 - status)
PY
fi
if [ -f .env ]; then set -a; . ./.env; set +a; fi
if [ -z "$forward_attempt" ] && [ -z "${GRAF_RELEASE_MC_IMAGE:-}" ]; then
  GRAF_RELEASE_MC_IMAGE="$(python3 infra/scripts/release-images.py current-override --service rec-minio-init)"
fi
token="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
restore_db="rec_restore_rehearsal_$token"
schema_db="rec_restore_schema_$token"
restore_bucket="twobrain-rec-restore-rehearsal-$token"
staging="$(mktemp -d "${TMPDIR:-/tmp}/graf-rec-restore.XXXXXX")"
log="$staging/commands.log"
database_owned=0
schema_owned=0
bucket_owned=0
postgres_staging=""
postgres_id=""
minio_network=twobrain-rec-private
minio_endpoint=http://rec-minio:9000
stop_requested=0
root_user_file="${TWOBRAIN_MINIO_ROOT_USER_FILE:-./secrets/twobrain_minio_root_user}"
root_password_file="${TWOBRAIN_MINIO_ROOT_PASSWORD_FILE:-./secrets/twobrain_minio_root_password}"
postgres_exec() {
  if [ -n "$forward_attempt" ] && [ -n "$postgres_id" ]; then
    docker exec -i "$postgres_id" "$@"
  else
    docker compose -f infra/docker-compose.yml exec -T rec-postgres "$@"
  fi
}
mc_run() {
  docker run --rm -i --pull never --network "$minio_network" --entrypoint /bin/sh \
    -e MC_CONFIG_DIR=/tmp/graf-restore-mc -e "GRAF_REHEARSAL_MINIO_ENDPOINT=$minio_endpoint" \
    -v "$reference/minio-objects":/backup/minio-objects:ro \
    -v "$root_user_file":/run/secrets/user:ro \
    -v "$root_password_file":/run/secrets/password:ro \
    "$GRAF_RELEASE_MC_IMAGE" -c 'set -eu; umask 077; mc alias set rec "$GRAF_REHEARSAL_MINIO_ENDPOINT" "$(cat /run/secrets/user)" "$(cat /run/secrets/password)" >/dev/null; '"$1"
}
cleanup() {
  result=$?
  trap - EXIT HUP INT TERM
  failed=0
  if [ "$bucket_owned" = 1 ]; then
    if ! mc_run "mc rb --force rec/$restore_bucket >/dev/null" >>"$log" 2>&1; then failed=1; fi
    if listing="$(mc_run 'mc ls --json rec' 2>>"$log")"; then
      if ! printf '%s' "$listing" | python3 -c 'import json,sys; target=sys.argv[1]; rows=[json.loads(s) for s in sys.stdin]; sys.exit(any(r.get("key", "").rstrip("/")==target for r in rows))' "$restore_bucket" >>"$log" 2>&1; then failed=1; fi
    else failed=1; fi
  fi
  for cleanup_db in "$restore_db" "$schema_db"; do
    if [ "$cleanup_db" = "$restore_db" ]; then owned="$database_owned"; else owned="$schema_owned"; fi
    [ "$owned" = 1 ] || continue
    if ! postgres_exec dropdb --force -U twobrain_rec "$cleanup_db" >>"$log" 2>&1; then failed=1; fi
    remaining="$(postgres_exec psql -X -U twobrain_rec -d twobrain_rec -Atqc "SELECT count(*) FROM pg_database WHERE datname='$cleanup_db'" 2>>"$log")" || failed=1
    [ "$remaining" = 0 ] || failed=1
  done
  if [ -n "$postgres_staging" ]; then
    if ! postgres_exec \
      sh -c 'rm -rf -- "$1"; test ! -e "$1"' sh "$postgres_staging" >>"$log" 2>&1; then failed=1; fi
  fi
  if ! rm -rf -- "$staging" 2>>"$log" || [ -e "$staging" ]; then failed=1; fi
  [ "$failed" = 0 ] || result=1
  if [ "$result" = 0 ]; then
    object_mode=legacy-file-mirror
    if [ -n "$forward_attempt" ]; then object_mode=verified-forward-manifest; fi
    printf 'restore_rehearsal_result=pass\nbackup_reference=%s\nobject_restore_mode=%s\ncleanup_result=pass\n' "$reference" "$object_mode"
  else
    printf 'restore_rehearsal_result=failed\nreason=restore_or_cleanup_failed\npostgres_restore_target=%s\nminio_restore_target=%s\n' "$restore_db" "$restore_bucket"
  fi
  exit "$result"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
chmod 0700 "$staging"
db_reference="$reference"
if [ -n "$forward_attempt" ]; then
  db_reference="$staging/attested"
  mkdir -m 700 "$db_reference"
  for artifact in postgres.dump schema.sql inventory.jsonl checksums.sha256 minio-inventory.jsonl; do
    [ ! -L "$reference/$artifact" ] && [ -f "$reference/$artifact" ] || exit 1
    cp "$reference/$artifact" "$db_reference/$artifact"
  done
  GRAF_RELEASE_MC_IMAGE="$(python3 "$script_dir/release-images.py" check-forward-backup \
    --deployment-lock-fd "${GRAF_RESTORE_LOCK_FD:-0}" --attempt-id "$forward_attempt" \
    --backup-directory "$reference" --rehearsal-copy "$db_reference" 2>>"$log")"
  python3 "$script_dir/rec-db-verify.py" "$db_reference" --inventory >>"$log" 2>&1
  python3 "$script_dir/verify-rec-object-backup.py" --prepare-rehearsal \
    "$reference" "$db_reference/minio-inventory.jsonl" "$restore_bucket" >"$staging/restore-objects.sh" 2>>"$log"
  postgres_id="$(docker compose --project-name twobrain-rec -f infra/docker-compose.yml ps -q rec-postgres 2>>"$log")"
  minio_id="$(docker compose --project-name twobrain-rec -f infra/docker-compose.yml ps -q rec-minio 2>>"$log")"
  for store_id in "$postgres_id" "$minio_id"; do
    printf '%s\n' "$store_id" | grep -Eq '^[0-9a-f]{64}$' || exit 1
    [ "${#store_id}" = 64 ] || exit 1
  done
  [ "$postgres_id" != "$minio_id" ] || exit 1
  minio_network="container:$minio_id"
  minio_endpoint=http://127.0.0.1:9000
fi
# Defer stop until successful creation records ownership for cleanup.
trap 'stop_requested=1' HUP INT TERM
postgres_exec createdb -U twobrain_rec "$restore_db" >>"$log" 2>&1
database_owned=1
trap 'exit 1' HUP INT TERM
[ "$stop_requested" = 0 ] || exit 1
postgres_exec \
  pg_restore --exit-on-error -U twobrain_rec -d "$restore_db" <"$db_reference/postgres.dump" >>"$log" 2>&1
# Native parsing canonicalizes CHECK casts/AND trees without rewriting SQL text.
trap 'stop_requested=1' HUP INT TERM
postgres_exec createdb -U twobrain_rec "$schema_db" >>"$log" 2>&1
schema_owned=1
trap 'exit 1' HUP INT TERM
[ "$stop_requested" = 0 ] || exit 1
postgres_exec \
  psql -Xq -v ON_ERROR_STOP=1 -U twobrain_rec -d "$schema_db" <"$db_reference/schema.sql" >>"$log" 2>&1
# A new container staging is owned only after a validated successful create.
trap 'stop_requested=1' HUP INT TERM
candidate="$(postgres_exec \
  sh -c 'umask 077; mktemp -d /tmp/twobrain-rec-backup.XXXXXX' 2>>"$log")"
case "$candidate" in /tmp/twobrain-rec-backup.*) suffix="${candidate#/tmp/twobrain-rec-backup.}" ;; *) exit 1 ;; esac
case "$suffix" in ''|*[!a-zA-Z0-9]*) exit 1 ;; esac
postgres_staging="$candidate"
trap 'exit 1' HUP INT TERM
[ "$stop_requested" = 0 ] || exit 1
if [ -z "$postgres_id" ]; then
  postgres_id="$(docker compose -f infra/docker-compose.yml ps -q rec-postgres 2>>"$log")"
  [ -n "$postgres_id" ] || exit 1
fi
for capture_db in "$restore_db" "$schema_db"; do
  postgres_exec \
    sh -c 'umask 077; exec psql -XqAt -v ON_ERROR_STOP=1 -U twobrain_rec -d "$1" -v expected_db="$1" -v capture_dump=false -v staging="$2"' \
    sh "$capture_db" "$postgres_staging" <"$script_dir/rec-db-backup-inventory.sql" >>"$log" 2>&1
  mkdir -m 700 "$staging/$capture_db"
  for artifact in schema.sql inventory.jsonl; do
    docker cp "$postgres_id:$postgres_staging/$artifact" "$staging/$capture_db/$artifact" >>"$log" 2>&1
  done
  python3 - "$staging/$capture_db" >>"$log" 2>&1 <<'PY'
import os, stat, sys
from pathlib import Path
for name in ('schema.sql', 'inventory.jsonl'):
    fd = os.open(Path(sys.argv[1]) / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size == 0:
            raise ValueError('invalid_restore_metadata')
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)
PY
done
python3 "$script_dir/rec-db-verify.py" "$db_reference" "$staging/$restore_db" "$restore_db" "$staging/$schema_db" "$schema_db" >>"$log" 2>&1
trap 'stop_requested=1' HUP INT TERM
mc_run "mc mb rec/$restore_bucket >/dev/null" >>"$log" 2>&1
bucket_owned=1
trap 'exit 1' HUP INT TERM
[ "$stop_requested" = 0 ] || exit 1
if [ -n "$forward_attempt" ]; then
  mc_run 'exec /bin/sh -s' <"$staging/restore-objects.sh" >"$staging/restored-objects.jsonl" 2>>"$log"
  python3 "$script_dir/verify-rec-object-backup.py" --verify-rehearsal \
    "$db_reference/minio-inventory.jsonl" "$staging/restored-objects.jsonl" "$restore_bucket" >>"$log" 2>&1
else
  mc_run "mc mirror /backup/minio-objects rec/$restore_bucket >/dev/null" >>"$log" 2>&1
fi
