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
steps=clean_worktree,branch_sync,pinned_sha,local_ci,remote_fetch,backup,restore_rehearsal,compose_config_secret_scan,deploy_build_up,runtime_secret_env_scan,production_smoke,public_health
EOF
  exit 0
fi

cd "$(dirname "$0")/../.."

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "deploy_result=blocked"
  echo "reason=dirty_worktree"
  exit 1
fi

CURRENT_BRANCH="$(git branch --show-current)"
if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
  echo "deploy_result=blocked"
  echo "reason=branch_mismatch"
  echo "current_branch=$CURRENT_BRANCH"
  echo "deploy_branch=$BRANCH"
  exit 1
fi

git fetch origin "$BRANCH"
EXPECTED_SHA="$(git rev-parse HEAD)"
ORIGIN_SHA="$(git rev-parse "origin/$BRANCH")"
if [[ "$EXPECTED_SHA" != "$ORIGIN_SHA" ]]; then
  echo "deploy_result=blocked"
  echo "reason=origin_sha_mismatch"
  echo "local_sha=$EXPECTED_SHA"
  echo "origin_sha=$ORIGIN_SHA"
  exit 1
fi

if [[ "$SKIP_LOCAL_CI" != "1" ]]; then
  infra/scripts/ci-local.sh
fi

remote_script=$(cat <<'SH'
set -eu
branch="$1"
expected_sha="$2"

git fetch origin "$branch"
origin_sha="$(git rev-parse "origin/$branch")"
if [ "$origin_sha" != "$expected_sha" ]; then
  echo "deploy_result=blocked"
  echo "reason=remote_origin_sha_mismatch"
  echo "expected_sha=$expected_sha"
  echo "origin_sha=$origin_sha"
  exit 1
fi
git cat-file -e "$expected_sha^{commit}"
git reset --hard "$expected_sha"

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
if grep -Eq 'TWOBRAIN_(POSTGRES_PASSWORD|MINIO_ROOT_USER|MINIO_ROOT_PASSWORD|MINIO_API_ACCESS_KEY|MINIO_API_SECRET_KEY|POSTAL_API_KEY):|MINIO_ROOT_PASSWORD:|MINIO_ROOT_USER:|POSTGRES_PWD:' /tmp/twobrain-rec-compose-deploy.yml; then
  echo "deploy_result=blocked"
  echo "reason=secret_env_exposure"
  exit 1
fi

docker compose -f infra/docker-compose.yml up -d --build \
  rec-api \
  rec-migrate \
  rec-minio \
  rec-minio-init \
  rec-temporal \
  rec-processing-worker
rec_api_container="$(docker compose -f infra/docker-compose.yml ps -q rec-api)"
if [ -z "$rec_api_container" ]; then
  echo "deploy_result=blocked"
  echo "reason=rec_api_container_missing"
  exit 1
fi
docker inspect "$rec_api_container" --format '{{range .Config.Env}}{{println .}}{{end}}' >/tmp/twobrain-rec-api-env.txt
if grep -Eq '^(TWOBRAIN_(POSTGRES_PASSWORD|MINIO_ROOT_USER|MINIO_ROOT_PASSWORD|MINIO_API_ACCESS_KEY|MINIO_API_SECRET_KEY|POSTAL_API_KEY)|MINIO_ROOT_PASSWORD|MINIO_ROOT_USER)=' /tmp/twobrain-rec-api-env.txt; then
  echo "deploy_result=blocked"
  echo "reason=runtime_secret_env_exposure"
  exit 1
fi
infra/scripts/run-production-smoke.sh --execute
curl -fsS https://rec.2brain.pro/api/v1/health/live >/dev/null
curl -fsS https://rec.2brain.pro/api/v1/health/ready >/dev/null

cat <<EOF
deploy_result=pass
branch=$branch
deployed_sha=$expected_sha
backup_reference=$backup_reference
readiness_verdict=infra_smoke_ready
EOF
SH
)

remote_payload="$(printf '%s' "$remote_script" | base64 | tr -d '\n')"
remote_command="cd $(printf '%q' "$REMOTE_PATH") && tmp=\$(mktemp /tmp/twobrain-rec-deploy.XXXXXX) && trap 'rm -f \"\$tmp\"' EXIT && printf '%s' $(printf '%q' "$remote_payload") | base64 -d > \"\$tmp\" && $(printf '%q' bash) \"\$tmp\" $(printf '%q' "$BRANCH") $(printf '%q' "$EXPECTED_SHA")"

set +e
remote_output="$(ssh "$REMOTE_HOST" "$remote_command" 2>&1)"
remote_status=$?
set -e
printf '%s\n' "$remote_output"

if [[ "$remote_status" -ne 0 ]]; then
  exit "$remote_status"
fi

if ! printf '%s\n' "$remote_output" | grep -Eq '^deploy_result=(pass|blocked)$'; then
  echo "deploy_result=blocked"
  echo "reason=remote_deploy_result_missing"
  exit 1
fi
