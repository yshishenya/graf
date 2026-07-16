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
steps=clean_worktree,branch_sync,pinned_sha,local_ci,remote_fetch,backup,restore_rehearsal,runtime_secret_group,runtime_service_secret_permissions,runtime_db_secret_provision,media_storage_secret_provision,compose_config_secret_scan,migration_head,runtime_db_role_bootstrap,runtime_db_identity,initial_dispatch_closed,temporal_readiness,processing_worker_readiness,image_capability,profile_contract,media_worker_readiness_control,production_smoke,automatic_dispatch_open,guarded_rollback,runtime_secret_env_scan,public_health,automatic_retry_post_deploy,backfill_inventory_post_deploy,range_playback_post_deploy,normalization_cleanup_post_deploy
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
previous_sha="$(git rev-parse HEAD)"

if [ -n "$(git status --porcelain --untracked-files=all)" ]; then
  echo "deploy_result=blocked"
  echo "reason=remote_worktree_dirty"
  exit 1
fi

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
bash infra/scripts/cd-remote-runtime.sh "$branch" "$expected_sha" "$previous_sha"
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
