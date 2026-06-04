#!/usr/bin/env bash
set -euo pipefail

MODE="dry-run"
SKIP_LOCAL_CI=0
BRANCH="${TWOBRAIN_DEPLOY_BRANCH:-$(git branch --show-current)}"
REMOTE_HOST="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
REMOTE_PATH="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --dry-run)
      MODE="dry-run"
      shift
      ;;
    --execute)
      MODE="execute"
      shift
      ;;
    --skip-local-ci)
      SKIP_LOCAL_CI=1
      shift
      ;;
    --branch)
      BRANCH="${2:-}"
      shift 2
      ;;
    *)
      echo "usage: $0 [--dry-run|--execute] [--skip-local-ci] [--branch <name>]" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$BRANCH" ]]; then
  echo "deploy_result=blocked"
  echo "reason=missing_branch"
  exit 2
fi

if [[ "$MODE" == "dry-run" ]]; then
  cat <<EOF
deploy_result=dry_run
remote_host=$REMOTE_HOST
remote_path=$REMOTE_PATH
branch=$BRANCH
local_ci=$([[ "$SKIP_LOCAL_CI" == "1" ]] && echo skipped || echo required)
steps=local_ci,remote_fetch,backup,restore_rehearsal,compose_config_secret_scan,deploy_build_up,production_smoke,public_health
EOF
  exit 0
fi

cd "$(dirname "$0")/../.."

if [[ "$SKIP_LOCAL_CI" != "1" ]]; then
  infra/scripts/ci-local.sh
fi

remote_script=$(cat <<'SH'
set -eu
branch="$1"

git fetch origin "$branch"
git reset --hard "origin/$branch"

backup_output="$(infra/scripts/backup-rec-stack.sh --execute)"
printf '%s\n' "$backup_output"
backup_reference="$(printf '%s\n' "$backup_output" | sed -n 's/^backup_reference=//p' | tail -n 1)"
if [ -z "$backup_reference" ]; then
  echo "deploy_result=blocked"
  echo "reason=backup_reference_missing"
  exit 1
fi

RESTORE_BACKUP_REFERENCE="$backup_reference" infra/scripts/rehearse-rec-restore.sh --execute

set -a
. ./.env
set +a
docker compose -f infra/docker-compose.yml config >/tmp/twobrain-rec-compose-deploy.yml
if grep -E 'TWOBRAIN_(POSTGRES_PASSWORD|MINIO_ROOT_USER|MINIO_ROOT_PASSWORD|MINIO_API_ACCESS_KEY|MINIO_API_SECRET_KEY):|MINIO_ROOT_PASSWORD:|MINIO_ROOT_USER:' /tmp/twobrain-rec-compose-deploy.yml; then
  echo "deploy_result=blocked"
  echo "reason=secret_env_exposure"
  exit 1
fi

docker compose -f infra/docker-compose.yml up -d --build rec-api rec-migrate rec-minio rec-minio-init
infra/scripts/run-production-smoke.sh --execute
curl -fsS https://rec.2brain.pro/api/v1/health/live >/dev/null
curl -fsS https://rec.2brain.pro/api/v1/health/ready >/dev/null

cat <<EOF
deploy_result=pass
branch=$branch
backup_reference=$backup_reference
readiness_verdict=infra_smoke_ready
EOF
SH
)

ssh "$REMOTE_HOST" "cd '$REMOTE_PATH' && $(printf '%q' bash) -s -- $(printf '%q' "$BRANCH")" <<<"$remote_script"
