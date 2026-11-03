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
import fcntl, os, select, signal, subprocess, sys, time
path = subprocess.check_output(['git', 'rev-parse', '--git-path', 'twobrain-rec-deploy.lock'], text=True).strip()
with open(path, 'a') as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('restore_rehearsal_result=blocked\nreason=deployment_or_rehearsal_running')
        raise SystemExit(1)
    child = None
    pending = set()
    read_fd, write_fd = os.pipe()
    if 9 in (lock.fileno(), write_fd):
        raise SystemExit("restore_rehearsal_result=failed\nreason=reserved_log_fd_unavailable")
    cleanup_started = timed_out = False
    def cleanup_timeout(number, frame):
        global timed_out
        timed_out = True
        if child is not None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    def begin_cleanup(deadline):
        global cleanup_started
        if not cleanup_started:
            cleanup_started = True
            signal.setitimer(signal.ITIMER_REAL, max(0.001, deadline - time.monotonic()))
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
    signal.signal(signal.SIGALRM, cleanup_timeout)
    child = subprocess.Popen(['sh', *sys.argv[1:]],
                             env=dict(os.environ, GRAF_RESTORE_LOCK_HELD='1',
                                      GRAF_RESTORE_CLEANUP_FD=str(write_fd)),
                             start_new_session=True,
                             pass_fds=(lock.fileno(), write_fd))
    os.close(write_fd)
    for number in pending:
        forward(number, None)
    notification = b''
    while child.poll() is None:
        if select.select([read_fd], [], [], 0.05)[0]:
            notification += os.read(read_fd, 128)
            if b'\n' in notification:
                begin_cleanup(float(notification.split(b'\n', 1)[0]))
    status = child.wait()
    os.close(read_fd)
    signal.alarm(0)
    if timed_out:
        # Killing local CLI processes does not prove remote daemon cleanup.
        print('restore_rehearsal_result=failed\nreason=cleanup_timeout_resources_unverified')
        raise SystemExit(1)
    raise SystemExit(status if status >= 0 else 128 - status)
PY
fi
restore_cleanup_fd="${GRAF_RESTORE_CLEANUP_FD:?restore supervisor required}"
readonly restore_cleanup_fd
if [ -f .env ]; then set -a; . ./.env; set +a; fi
if [ -z "${GRAF_RELEASE_MC_IMAGE:-}" ]; then
  GRAF_RELEASE_MC_IMAGE="$(python3 infra/scripts/release-images.py current-override --service rec-minio-init)"
fi
token="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
restore_db="rec_restore_rehearsal_$token"
schema_db="rec_restore_schema_$token"
restore_bucket="twobrain-rec-restore-rehearsal-$token"
staging="$(mktemp -d "${TMPDIR:-/tmp}/graf-rec-restore.XXXXXX")"
staging_identity="$(python3 -c 'import os,sys; i=os.lstat(sys.argv[1]); print((i.st_dev,i.st_ino,i.st_uid))' "$staging")"
readonly staging_identity
log="$staging/commands.log"
# Keep the original log inode open; a replaced staging path must never be written.
exec 9>>"$log"
database_owned=0
schema_owned=0
bucket_owned=0
reader_attempted=0
reader_pid=""
postgres_staging=""
stop_requested=0
root_user_file="${TWOBRAIN_MINIO_ROOT_USER_FILE:-./secrets/twobrain_minio_root_user}"
root_password_file="${TWOBRAIN_MINIO_ROOT_PASSWORD_FILE:-./secrets/twobrain_minio_root_password}"
root_user_file="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).absolute())' "$root_user_file")"
root_password_file="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).absolute())' "$root_password_file")"
manifest="$staging/object-manifest.json"
staging_owned() {
  python3 -c 'import os,stat,sys; i=os.lstat(sys.argv[1]); sys.exit(not (stat.S_ISDIR(i.st_mode) and stat.S_IMODE(i.st_mode)==0o700 and i.st_uid==os.geteuid() and str((i.st_dev,i.st_ino,i.st_uid))==sys.argv[2]))' "$staging" "$staging_identity"
}
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
  trap - EXIT
  trap 'stop_requested=1' HUP INT TERM
  failed=0
  reader_safe=1
  if ! staging_owned 2>/dev/null; then reader_safe=0; failed=1; fi
  cleanup_watchdog=""
  cleanup_deadline=""
  if [ "$reader_safe" != 1 ] || ! cleanup_deadline="$(GRAF_RESTORE_CLEANUP_FD="$restore_cleanup_fd" python3 - "$script_dir/rec-object-verify.py" "$manifest" "$staging_identity" <<'PY'
import ast, importlib.util, os, sys
spec = importlib.util.spec_from_file_location('checker', sys.argv[1])
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
try:
    deadline, notified = checker.cleanup_budget(sys.argv[2], os.environ['GRAF_RESTORE_CLEANUP_FD'],
                                               expected_parent=ast.literal_eval(sys.argv[3]))
except Exception:
    raise SystemExit(1)
print(deadline)
raise SystemExit(0 if notified else 1)
PY
)"; then
    failed=1
    # SIGKILL cannot be forwarded; bound our cleanup even if its supervisor died.
    python3 - "$$" "$cleanup_deadline" <<'PY' &
import os, signal, sys, time
group = int(sys.argv[1])
if os.getpgrp() != group:
    raise SystemExit(1)
try:
    remaining = max(0, float(sys.argv[2]) - time.monotonic())
except ValueError:
    remaining = 0
time.sleep(remaining)
print('restore_rehearsal_result=failed\nreason=cleanup_timeout_resources_unverified', flush=True)
os.killpg(group, signal.SIGKILL)
PY
    cleanup_watchdog=$!
  fi
  if [ "$reader_attempted" = 1 ]; then
    if [ ! -f "$manifest.cleanup" ] || [ -L "$manifest.cleanup" ] || [ "$(cat "$manifest.cleanup")" != 'container_cleanup=pass' ]; then
      reader_safe=0
      failed=1
    fi
  fi
  if [ "$bucket_owned" = 1 ] && [ "$reader_safe" = 1 ]; then
    if ! mc_run "mc rb --force rec/$restore_bucket >/dev/null" >&9 2>&1; then failed=1; fi
    if listing="$(mc_run 'mc ls --json rec' 2>&9)"; then
      if ! printf '%s' "$listing" | python3 -c 'import json,sys; target=sys.argv[1]; rows=[json.loads(s) for s in sys.stdin]; sys.exit(any(r.get("key", "").rstrip("/")==target for r in rows))' "$restore_bucket" >&9 2>&1; then failed=1; fi
    else failed=1; fi
  fi
  for cleanup_db in "$restore_db" "$schema_db"; do
    if [ "$cleanup_db" = "$restore_db" ]; then owned="$database_owned"; else owned="$schema_owned"; fi
    [ "$owned" = 1 ] || continue
    if ! docker compose -f infra/docker-compose.yml exec -T rec-postgres dropdb --force -U twobrain_rec "$cleanup_db" >&9 2>&1; then failed=1; fi
    remaining="$(docker compose -f infra/docker-compose.yml exec -T rec-postgres psql -X -U twobrain_rec -d twobrain_rec -Atqc "SELECT count(*) FROM pg_database WHERE datname='$cleanup_db'" 2>&9)" || failed=1
    [ "$remaining" = 0 ] || failed=1
  done
  if [ -n "$postgres_staging" ]; then
    if ! docker compose -f infra/docker-compose.yml exec -T rec-postgres \
      sh -c 'rm -rf -- "$1"; test ! -e "$1"' sh "$postgres_staging" >&9 2>&1; then failed=1; fi
  fi
  if [ "$reader_safe" = 1 ]; then
    if ! staging_owned 2>/dev/null || ! rm -rf -- "$staging" 2>&9 || [ -e "$staging" ]; then failed=1; fi
  fi
  if [ -n "$cleanup_watchdog" ]; then
    kill -TERM "$cleanup_watchdog" 2>/dev/null || failed=1
    wait "$cleanup_watchdog" 2>/dev/null || :
  fi
  [ "$failed" = 0 ] && [ "$stop_requested" = 0 ] || result=1
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
python3 "$script_dir/rec-object-verify.py" snapshot "$reference/minio-objects" "$manifest" >&9 2>&1
# Defer stop until successful creation records ownership for cleanup.
trap 'stop_requested=1' HUP INT TERM
docker compose -f infra/docker-compose.yml exec -T rec-postgres createdb -U twobrain_rec "$restore_db" >&9 2>&1
database_owned=1
trap 'exit 1' HUP INT TERM
[ "$stop_requested" = 0 ] || exit 1
docker compose -f infra/docker-compose.yml exec -T rec-postgres \
  pg_restore --exit-on-error -U twobrain_rec -d "$restore_db" <"$reference/postgres.dump" >&9 2>&1
# Native parsing canonicalizes CHECK casts/AND trees without rewriting SQL text.
trap 'stop_requested=1' HUP INT TERM
docker compose -f infra/docker-compose.yml exec -T rec-postgres createdb -U twobrain_rec "$schema_db" >&9 2>&1
schema_owned=1
trap 'exit 1' HUP INT TERM
[ "$stop_requested" = 0 ] || exit 1
docker compose -f infra/docker-compose.yml exec -T rec-postgres \
  psql -Xq -v ON_ERROR_STOP=1 -U twobrain_rec -d "$schema_db" <"$reference/schema.sql" >&9 2>&1
# A new container staging is owned only after a validated successful create.
trap 'stop_requested=1' HUP INT TERM
candidate="$(docker compose -f infra/docker-compose.yml exec -T rec-postgres \
  sh -c 'umask 077; mktemp -d /tmp/twobrain-rec-backup.XXXXXX' 2>&9)"
case "$candidate" in /tmp/twobrain-rec-backup.*) suffix="${candidate#/tmp/twobrain-rec-backup.}" ;; *) exit 1 ;; esac
case "$suffix" in ''|*[!a-zA-Z0-9]*) exit 1 ;; esac
postgres_staging="$candidate"
trap 'exit 1' HUP INT TERM
[ "$stop_requested" = 0 ] || exit 1
postgres_id="$(docker compose -f infra/docker-compose.yml ps -q rec-postgres 2>&9)"
[ -n "$postgres_id" ] || exit 1
for capture_db in "$restore_db" "$schema_db"; do
  docker compose -f infra/docker-compose.yml exec -T rec-postgres \
    sh -c 'umask 077; exec psql -XqAt -v ON_ERROR_STOP=1 -U twobrain_rec -d "$1" -v expected_db="$1" -v capture_dump=false -v staging="$2"' \
    sh "$capture_db" "$postgres_staging" <"$script_dir/rec-db-backup-inventory.sql" >&9 2>&1
  mkdir -m 700 "$staging/$capture_db"
  for artifact in schema.sql inventory.jsonl; do
    docker cp "$postgres_id:$postgres_staging/$artifact" "$staging/$capture_db/$artifact" >&9 2>&1
  done
  python3 - "$staging/$capture_db" >&9 2>&1 <<'PY'
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
python3 "$script_dir/rec-db-verify.py" "$reference" "$staging/$restore_db" "$restore_db" "$staging/$schema_db" "$schema_db" >&9 2>&1
trap 'stop_requested=1' HUP INT TERM
mc_run "mc mb rec/$restore_bucket >/dev/null" >&9 2>&1
bucket_owned=1
trap 'exit 1' HUP INT TERM
[ "$stop_requested" = 0 ] || exit 1
mc_run "mc mirror /backup/minio-objects rec/$restore_bucket >/dev/null" >&9 2>&1
readback_image="$(python3 "$script_dir/release-images.py" current-override --service rec-api 2>&9)"
# Forward stop and await the reader's own bounded cleanup before the EXIT trap.
trap 'stop_requested=1; if [ -n "$reader_pid" ]; then kill -TERM "$reader_pid" 2>/dev/null || :; fi' HUP INT TERM
reader_attempted=1
GRAF_RESTORE_CLEANUP_FD="$restore_cleanup_fd" python3 "$script_dir/rec-object-verify.py" container "$reference/minio-objects" "$manifest" \
  "$restore_bucket" "$readback_image" "$root_user_file" "$root_password_file" >&9 2>&1 &
reader_pid=$!
if [ "$stop_requested" != 0 ]; then kill -TERM "$reader_pid" 2>/dev/null || :; fi
while :; do
  if wait "$reader_pid"; then reader_status=0; break; else reader_status=$?; fi
  if ! kill -0 "$reader_pid" 2>/dev/null; then break; fi
done
reader_pid=""
trap 'exit 1' HUP INT TERM
[ "$reader_status" = 0 ] && [ "$stop_requested" = 0 ]
