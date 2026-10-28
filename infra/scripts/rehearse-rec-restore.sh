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
    child = subprocess.Popen(['sh', *sys.argv[1:]],
                             env=dict(os.environ, GRAF_RESTORE_LOCK_HELD='1'),
                             pass_fds=(lock.fileno(),))
    def forward(number, frame):
        try:
            child.send_signal(number)
        except ProcessLookupError:
            pass
    for number in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(number, forward)
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
restore_bucket="twobrain-rec-restore-rehearsal-$token"
staging="$(mktemp -d "${TMPDIR:-/tmp}/graf-rec-restore.XXXXXX")"
log="$staging/commands.log"
database_owned=0
bucket_owned=0
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
  if [ "$database_owned" = 1 ]; then
    if ! docker compose -f infra/docker-compose.yml exec -T rec-postgres dropdb --force -U twobrain_rec "$restore_db" >>"$log" 2>&1; then failed=1; fi
    remaining="$(docker compose -f infra/docker-compose.yml exec -T rec-postgres psql -X -U twobrain_rec -d twobrain_rec -Atqc "SELECT count(*) FROM pg_database WHERE datname='$restore_db'" 2>>"$log")" || failed=1
    [ "$remaining" = 0 ] || failed=1
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
# Flags follow successful create-only commands; an uncertain create never owns a target.
docker compose -f infra/docker-compose.yml exec -T rec-postgres createdb -U twobrain_rec "$restore_db" >>"$log" 2>&1
database_owned=1
docker compose -f infra/docker-compose.yml exec -T rec-postgres \
  pg_restore --exit-on-error -U twobrain_rec -d "$restore_db" --no-owner <"$reference/postgres.dump" >>"$log" 2>&1
docker compose -f infra/docker-compose.yml exec -T rec-postgres \
  psql -X -U twobrain_rec -d "$restore_db" -Atqc 'SELECT count(*) FROM information_schema.tables' >>"$log" 2>&1
mc_run "mc mb rec/$restore_bucket >/dev/null" >>"$log" 2>&1
bucket_owned=1
mc_run "mc mirror /backup/minio-objects rec/$restore_bucket >/dev/null" >>"$log" 2>&1
