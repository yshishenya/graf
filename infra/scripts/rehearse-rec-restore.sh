#!/usr/bin/env sh
set -eu
umask 077
host="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
path="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"
reference="${RESTORE_BACKUP_REFERENCE:-}"
if [ -z "$reference" ]; then
  printf 'restore_rehearsal_result=blocked\nreason=backup_reference_missing\n'
  exit 0
fi
case "$reference" in /*) ;; *) printf 'restore_rehearsal_result=blocked\nreason=backup_reference_invalid\n'; exit 1 ;; esac
case "$reference" in *[!A-Za-z0-9._/-]*) printf 'restore_rehearsal_result=blocked\nreason=backup_reference_invalid\n'; exit 1 ;; esac
if [ "${1:-}" = "--remote" ]; then
  exec ssh "$host" "cd '$path' && RESTORE_BACKUP_REFERENCE='$reference' ./infra/scripts/rehearse-rec-restore.sh --execute"
fi
if [ "${1:-}" != "--execute" ]; then
  printf 'restore_rehearsal_result=dry_run\nbackup_reference=%s\n' "$reference"
  exit 0
fi
if [ -L "$reference" ] || [ ! -d "$reference" ] || [ -L "$reference/postgres.dump" ] || [ ! -s "$reference/postgres.dump" ] || [ -L "$reference/minio-objects" ] || [ ! -d "$reference/minio-objects" ]; then
  printf 'restore_rehearsal_result=blocked\nreason=backup_set_incomplete\n'
  exit 1
fi
script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if ! python3 "$script_dir/rec-db-verify.py" "$reference" --inventory 2>/dev/null; then
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
                             env=dict(os.environ, GRAF_RESTORE_LOCK_HELD='1'),
                             pass_fds=(lock.fileno(),))
    for number in pending:
        forward(number, None)
    status = child.wait()
    raise SystemExit(status if status >= 0 else 128 - status)
PY
fi
if [ -f .env ]; then set -a; . ./.env; set +a; fi
if [ -z "${GRAF_RELEASE_MC_IMAGE:-}" ]; then
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
stop_requested=0
root_user_file="${TWOBRAIN_MINIO_ROOT_USER_FILE:-./secrets/twobrain_minio_root_user}"
root_password_file="${TWOBRAIN_MINIO_ROOT_PASSWORD_FILE:-./secrets/twobrain_minio_root_password}"
mc_run() {
  docker run --rm --pull never --network twobrain-rec-private --entrypoint /bin/sh \
    -e MC_CONFIG_DIR=/tmp/graf-restore-mc \
    -v "$reference/minio-objects":/backup/minio-objects:ro \
    -v "$root_user_file":/run/secrets/user:ro \
    -v "$root_password_file":/run/secrets/password:ro \
    "$GRAF_RELEASE_MC_IMAGE" -c 'set -eu; umask 077; mc alias set rec http://rec-minio:9000 "$(cat /run/secrets/user)" "$(cat /run/secrets/password)" >/dev/null; '"$1"
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
    if ! docker compose -f infra/docker-compose.yml exec -T rec-postgres dropdb --force -U twobrain_rec "$cleanup_db" >>"$log" 2>&1; then failed=1; fi
    remaining="$(docker compose -f infra/docker-compose.yml exec -T rec-postgres psql -X -U twobrain_rec -d twobrain_rec -Atqc "SELECT count(*) FROM pg_database WHERE datname='$cleanup_db'" 2>>"$log")" || failed=1
    [ "$remaining" = 0 ] || failed=1
  done
  if [ -n "$postgres_staging" ]; then
    if ! docker compose -f infra/docker-compose.yml exec -T rec-postgres \
      sh -c 'rm -rf -- "$1"; test ! -e "$1"' sh "$postgres_staging" >>"$log" 2>&1; then failed=1; fi
  fi
  if ! rm -rf -- "$staging" 2>>"$log" || [ -e "$staging" ]; then failed=1; fi
  [ "$failed" = 0 ] || result=1
  if [ "$result" = 0 ]; then
    printf 'restore_rehearsal_result=pass\nbackup_reference=%s\ncleanup_result=pass\n' "$reference"
  else
    printf 'restore_rehearsal_result=failed\nreason=restore_or_cleanup_failed\npostgres_restore_target=%s\nminio_restore_target=%s\n' "$restore_db" "$restore_bucket"
  fi
  exit "$result"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
chmod 0700 "$staging"
# Defer stop until successful creation records ownership for cleanup.
trap 'stop_requested=1' HUP INT TERM
docker compose -f infra/docker-compose.yml exec -T rec-postgres createdb -U twobrain_rec "$restore_db" >>"$log" 2>&1
database_owned=1
trap 'exit 1' HUP INT TERM
[ "$stop_requested" = 0 ] || exit 1
docker compose -f infra/docker-compose.yml exec -T rec-postgres \
  pg_restore --exit-on-error -U twobrain_rec -d "$restore_db" <"$reference/postgres.dump" >>"$log" 2>&1
# Native parsing canonicalizes CHECK casts/AND trees without rewriting SQL text.
trap 'stop_requested=1' HUP INT TERM
docker compose -f infra/docker-compose.yml exec -T rec-postgres createdb -U twobrain_rec "$schema_db" >>"$log" 2>&1
schema_owned=1
trap 'exit 1' HUP INT TERM
[ "$stop_requested" = 0 ] || exit 1
docker compose -f infra/docker-compose.yml exec -T rec-postgres \
  psql -Xq -v ON_ERROR_STOP=1 -U twobrain_rec -d "$schema_db" <"$reference/schema.sql" >>"$log" 2>&1
# A new container staging is owned only after a validated successful create.
trap 'stop_requested=1' HUP INT TERM
candidate="$(docker compose -f infra/docker-compose.yml exec -T rec-postgres \
  sh -c 'umask 077; mktemp -d /var/lib/postgresql/data/twobrain-rec-backup.XXXXXX' 2>>"$log")"
case "$candidate" in /var/lib/postgresql/data/twobrain-rec-backup.*) suffix="${candidate#/var/lib/postgresql/data/twobrain-rec-backup.}" ;; *) exit 1 ;; esac
case "$suffix" in ''|*[!a-zA-Z0-9]*) exit 1 ;; esac
postgres_staging="$candidate"
trap 'exit 1' HUP INT TERM
[ "$stop_requested" = 0 ] || exit 1
postgres_id="$(docker compose -f infra/docker-compose.yml ps -q rec-postgres 2>>"$log")"
[ -n "$postgres_id" ] || exit 1
for capture_db in "$restore_db" "$schema_db"; do
  docker compose -f infra/docker-compose.yml exec -T rec-postgres \
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
python3 "$script_dir/rec-db-verify.py" "$reference" "$staging/$restore_db" "$restore_db" "$staging/$schema_db" "$schema_db" >>"$log" 2>&1
trap 'stop_requested=1' HUP INT TERM
mc_run "mc mb rec/$restore_bucket >/dev/null" >>"$log" 2>&1
bucket_owned=1
trap 'exit 1' HUP INT TERM
[ "$stop_requested" = 0 ] || exit 1
mc_run "mc mirror /backup/minio-objects rec/$restore_bucket >/dev/null" >>"$log" 2>&1
