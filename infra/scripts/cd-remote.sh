#!/usr/bin/env bash
set -euo pipefail

MODE="dry-run"
SKIP_LOCAL_CI=0
BRANCH="${TWOBRAIN_DEPLOY_BRANCH:-$(git branch --show-current)}"
REMOTE_HOST="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
REMOTE_PATH="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"
CANDIDATE_PATH="${GRAF_RELEASE_CANDIDATE:-}"

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
    --candidate)
      CANDIDATE_PATH="${2:-}"
      shift 2
      ;;
    *)
      echo "usage: $0 [--dry-run|--execute] [--skip-local-ci] [--branch <name>] [--candidate <decision.json>]" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$BRANCH" ]]; then
  echo "deploy_result=blocked"
  echo "reason=missing_branch"
  exit 2
fi

if [[ "$MODE" == "execute" && "$BRANCH" != "master" ]]; then
  echo "deploy_result=blocked"
  echo "reason=production_deploy_requires_master"
  echo "requested_branch=$BRANCH"
  exit 1
fi

if [[ "$MODE" == "execute" && -z "$CANDIDATE_PATH" ]]; then
  echo "deploy_result=blocked"
  echo "reason=release_candidate_required"
  exit 1
fi

if [[ "$MODE" == "dry-run" ]]; then
  cat <<EOF
deploy_result=dry_run
remote_host=$REMOTE_HOST
remote_path=$REMOTE_PATH
branch=$BRANCH
candidate=${CANDIDATE_PATH:-required_for_execute}
local_ci=$([[ "$SKIP_LOCAL_CI" == "1" ]] && echo skipped_incident_only || echo full_required)
posthog_stack_handoff=dry_run_metadata_only
posthog_stack_contract=infra/posthog/docker-compose.posthog.yml
posthog_stack_runtime_source=official_posthog_hobby_generated_compose_required
posthog_stack_execute=requires_explicit_release_approval
steps=clean_worktree,branch_sync,pinned_sha,local_ci,remote_fetch,backup,restore_rehearsal,runtime_secret_group,runtime_service_secret_permissions,runtime_db_secret_provision,media_storage_secret_provision,compose_config_secret_scan,migration_head,runtime_db_role_bootstrap,runtime_db_identity,initial_dispatch_closed,temporal_readiness,processing_worker_readiness,image_capability,profile_contract,media_worker_readiness_control,production_smoke,automatic_dispatch_open,guarded_rollback,runtime_secret_env_scan,public_health,automatic_retry_post_deploy,backfill_inventory_post_deploy,range_playback_post_deploy,normalization_cleanup_post_deploy
EOF
  exit 0
fi

cd "$(dirname "$0")/../.."

if ! WORKTREE_STATUS="$(git status --porcelain --untracked-files=all)"; then
  echo "deploy_result=blocked"
  echo "reason=worktree_status_failed"
  exit 1
fi
if [[ -n "$WORKTREE_STATUS" ]]; then
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

if [[ -n "$CANDIDATE_PATH" ]]; then
  [[ -f "$CANDIDATE_PATH" ]] || { echo "deploy_result=blocked"; echo "reason=release_candidate_missing"; exit 1; }
  infra/scripts/release-candidate.sh validate "$CANDIDATE_PATH" --current
  candidate_status="$(python3 - "$CANDIDATE_PATH" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
print(data.get("status", ""))
PY
)"
  if [[ "$candidate_status" != "go" ]]; then
    echo "deploy_result=blocked"
    echo "reason=release_candidate_not_go"
    echo "candidate_status=$candidate_status"
    exit 1
  fi
  echo "release_candidate=go"
fi

if [[ "$SKIP_LOCAL_CI" != "1" ]]; then
  infra/scripts/ci-local.sh --full
  if ! POST_CI_WORKTREE_STATUS="$(git status --porcelain --untracked-files=all)"; then
    echo "deploy_result=blocked"
    echo "reason=worktree_status_failed_after_full"
    exit 1
  fi
  if [[ -n "$POST_CI_WORKTREE_STATUS" ]]; then
    echo "deploy_result=blocked"
    echo "reason=candidate_changed_during_full"
    exit 1
  fi
  POST_CI_SHA="$(git rev-parse HEAD)"
  git fetch origin "$BRANCH"
  POST_CI_ORIGIN_SHA="$(git rev-parse "origin/$BRANCH")"
  if [[ "$POST_CI_SHA" != "$EXPECTED_SHA" || "$POST_CI_ORIGIN_SHA" != "$EXPECTED_SHA" ]]; then
    echo "deploy_result=blocked"
    echo "reason=candidate_changed_during_full"
    echo "expected_sha=$EXPECTED_SHA"
    echo "local_sha=$POST_CI_SHA"
    echo "origin_sha=$POST_CI_ORIGIN_SHA"
    exit 1
  fi
  echo "local_ci=full_passed"
else
  echo "local_ci=skipped_incident_only"
fi

remote_script=$(cat <<'SH'
set -eu
branch="$1"
expected_sha="$2"
deploy_lock="$(git rev-parse --git-path twobrain-rec-deploy.lock)"
exec 9>"$deploy_lock"
if ! /usr/bin/flock -n 9; then
  echo "deploy_result=blocked"
  echo "reason=deploy_already_running"
  exit 1
fi
previous_sha="$(git rev-parse HEAD)"

worktree_status="$(git status --porcelain --untracked-files=all)"
unexpected_worktree_status="$(printf '%s\n' "$worktree_status" | grep -v -F -x "?? twobrain-rec-deploy.lock" || true)"
if [ -n "$unexpected_worktree_status" ]; then
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
remote_branch="$(git branch --show-current)"
if [ "$remote_branch" != "$branch" ]; then
  echo "deploy_result=blocked"
  echo "reason=remote_branch_mismatch"
  echo "current_branch=$remote_branch"
  echo "deploy_branch=$branch"
  exit 1
fi
git cat-file -e "$expected_sha^{commit}"
git reset --hard "$expected_sha"
TWOBRAIN_PRODUCTION_RELEASE_GATE=1 \
TWOBRAIN_PRODUCTION_RELEASE_LOCK_HELD=1 \
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
