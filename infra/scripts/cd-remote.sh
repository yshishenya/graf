#!/usr/bin/env bash
set -euo pipefail

MODE="dry-run"
SKIP_LOCAL_CI=0
SKIP_LOCAL_CI_EVIDENCE="${GRAF_SKIP_LOCAL_CI_EVIDENCE:-}"
BRANCH="${TWOBRAIN_DEPLOY_BRANCH:-$(git branch --show-current)}"
REMOTE_HOST="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
REMOTE_PATH="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"
CANDIDATE_PATH="${GRAF_RELEASE_CANDIDATE:-}"
EVIDENCE_PATH="${GRAF_RELEASE_EVIDENCE:-}"
REUSE_AUTHORITATIVE_FULL=0

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
    --skip-local-ci-evidence)
      SKIP_LOCAL_CI_EVIDENCE="${2:-}"
      shift 2
      ;;
    --branch)
      BRANCH="${2:-}"
      shift 2
      ;;
    --candidate)
      CANDIDATE_PATH="${2:-}"
      shift 2
      ;;
    --evidence)
      EVIDENCE_PATH="${2:-}"
      shift 2
      ;;
    *)
      echo "usage: $0 [--dry-run|--execute] [--skip-local-ci --skip-local-ci-evidence <json>] [--branch <name>] [--candidate <decision.json>] [--evidence <full-evidence.json>]" >&2
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

if [[ "$MODE" == "execute" && "$SKIP_LOCAL_CI" == "1" && -z "$SKIP_LOCAL_CI_EVIDENCE" ]]; then
  echo "deploy_result=blocked"
  echo "reason=skip_local_ci_approval_evidence_required"
  exit 1
fi

if [[ "$MODE" == "execute" && "$SKIP_LOCAL_CI" == "1" ]]; then
  if ! python3 - "$SKIP_LOCAL_CI_EVIDENCE" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
try:
    value = json.loads(path.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    raise SystemExit(f"invalid skip-local-ci approval evidence: {exc}")
if not isinstance(value, dict):
    raise SystemExit("skip-local-ci approval evidence must be a JSON object")
required = ("reason", "approved_by", "approved_at")
if any(not isinstance(value.get(key), str) or not value[key].strip() for key in required):
    raise SystemExit("skip-local-ci approval evidence requires reason, approved_by and approved_at")
PY
  then
    echo "deploy_result=blocked"
    echo "reason=skip_local_ci_approval_evidence_invalid"
    exit 1
  fi
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
  if ! CANDIDATE_VALIDATION_OUTPUT="$(infra/scripts/release-candidate.sh validate "$CANDIDATE_PATH" --current 2>&1)"; then
    printf '%s\n' "$CANDIDATE_VALIDATION_OUTPUT" >&2
    echo "deploy_result=blocked"
    echo "reason=release_candidate_invalid"
    exit 1
  fi
  printf '%s\n' "$CANDIDATE_VALIDATION_OUTPUT"
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
  if [[ -z "$EVIDENCE_PATH" ]]; then
    candidate_id="$(python3 - "$CANDIDATE_PATH" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle).get("candidate_id", ""))
PY
)"
    [[ -n "$candidate_id" ]] && EVIDENCE_PATH=".dev/ci-evidence/authoritative-${candidate_id}.json"
  fi
  [[ -n "$EVIDENCE_PATH" && -f "$EVIDENCE_PATH" ]] || {
    echo "deploy_result=blocked"
    echo "reason=authoritative_full_evidence_missing"
    exit 1
  }
  if ! python3 - "$CANDIDATE_PATH" "$EVIDENCE_PATH" <<'PY'
import hashlib
import importlib.util
import json
import pathlib
import sys

candidate_path, evidence_path = map(pathlib.Path, sys.argv[1:])
candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
expected = candidate.get("full_evidence_digest")
actual = "sha256:" + hashlib.sha256(evidence_path.read_bytes()).hexdigest()
if expected != actual:
    raise SystemExit("authoritative Full CI evidence digest differs from the decision record")
validator_path = pathlib.Path("scripts/validate-ci-evidence.py")
spec = importlib.util.spec_from_file_location("ci_evidence", validator_path)
if spec is None or spec.loader is None:
    raise SystemExit("CI evidence validator is unavailable")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
errors = module.validate(evidence)
if errors:
    raise SystemExit("authoritative Full CI evidence is invalid: " + "; ".join(errors))
if evidence.get("candidate_id") != candidate.get("candidate_id"):
    raise SystemExit("authoritative Full CI evidence candidate ID differs from the decision record")
if evidence.get("requested_sha") != candidate.get("source_sha"):
    raise SystemExit("authoritative Full CI evidence SHA differs from the decision record")
if evidence.get("lane") != "full" or evidence.get("authoritative_full") is not True:
    raise SystemExit("decision evidence is not an authoritative Full CI record")
PY
  then
    echo "deploy_result=blocked"
    echo "reason=authoritative_full_evidence_invalid"
    exit 1
  fi
  echo "authoritative_full_evidence=$EVIDENCE_PATH"
  [[ "$MODE" == "execute" ]] && REUSE_AUTHORITATIVE_FULL=1
  echo "release_candidate=go"
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
candidate_gates=$([[ -n "$CANDIDATE_PATH" ]] && echo passed || echo not_supplied)
steps=clean_worktree,branch_sync,pinned_sha,candidate_validation,authoritative_full_evidence_validation,local_ci,remote_fetch,backup,restore_rehearsal,runtime_secret_group,runtime_service_secret_permissions,runtime_db_secret_provision,media_storage_secret_provision,compose_config_secret_scan,migration_head,runtime_db_role_bootstrap,runtime_db_identity,initial_dispatch_closed,temporal_readiness,processing_worker_readiness,image_capability,profile_contract,media_worker_readiness_control,production_smoke,automatic_dispatch_open,guarded_rollback,runtime_secret_env_scan,public_health,automatic_retry_post_deploy,backfill_inventory_post_deploy,range_playback_post_deploy,normalization_cleanup_post_deploy
EOF
  exit 0
fi

if [[ "$REUSE_AUTHORITATIVE_FULL" == "1" ]]; then
  echo "local_ci=authoritative_full_reused"
elif [[ "$SKIP_LOCAL_CI" != "1" ]]; then
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
