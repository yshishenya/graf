#!/usr/bin/env bash
set -euo pipefail

MODE="dry-run"
if [[ "${1:-}" == "--remote" ]]; then
  MODE="remote"
elif [[ "${1:-}" == "--execute" ]]; then
  MODE="execute"
elif [[ "${1:-}" == "--forward" && $# -eq 8 ]]; then
  MODE="forward"
elif [[ "${1:-}" == "--dry-run" || $# -eq 0 ]]; then
  MODE="dry-run"
else
  echo "usage: $0 [--dry-run|--remote|--execute]" >&2
  exit 2
fi

REMOTE_HOST="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
REMOTE_PATH="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"
if [[ "$MODE" == "forward" ]]; then
  RUN_ID="$4"
elif [[ -n "${TWOBRAIN_SMOKE_RUN_ID+x}" ]]; then
  RUN_ID="$TWOBRAIN_SMOKE_RUN_ID"
else
  if ! run_nonce="$(od -An -N8 -tx1 /dev/urandom | tr -d '[:space:]')" || [[ -z "$run_nonce" ]]; then
    run_nonce="pid$$"
  fi
  RUN_ID="smoke-$(date -u +%Y%m%d-%H%M%S)-${run_nonce}-$$"
fi

if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]]; then
  echo "run_id must start with an ASCII letter or digit and contain only ASCII letters, digits, '.', '_' or '-' (maximum 128 characters)" >&2
  exit 2
fi

shell_quote() {
  local value="$1"
  value=${value//\'/\'\\\'\'}
  printf "'%s'" "$value"
}

if [[ "$MODE" == "remote" ]]; then
  if [[ "${TWOBRAIN_PRODUCTION_RELEASE_GATE:-}" != "1" ]]; then
    echo "smoke_result=blocked"
    echo "reason=production_smoke_requires_release_gate"
    exit 1
  fi
  remote_path_quoted="$(shell_quote "$REMOTE_PATH")"
  remote_run_id_quoted="$(shell_quote "$RUN_ID")"
  ssh "$REMOTE_HOST" "cd -- $remote_path_quoted && TWOBRAIN_PRODUCTION_RELEASE_GATE=1 TWOBRAIN_SMOKE_RUN_ID=$remote_run_id_quoted exec infra/scripts/run-production-smoke.sh --execute"
  exit $?
fi

if [[ "$MODE" == "dry-run" ]]; then
  cat <<EOF
smoke_result=blocked
reason=remote_execution_required_after_dns_tls_secrets_backup_and_restore_rehearsal
remote_host=$REMOTE_HOST
remote_path=$REMOTE_PATH
public_endpoint=https://rec.2brain.pro
allowed_verdicts=not_ready,blocked,infra_smoke_ready
run_id=$RUN_ID
EOF
  exit 0
fi

if [[ "$MODE" != "forward" && -f .env ]]; then
  set -a
  . ./.env
  set +a
fi

SMOKE_CONTAINER_DIR=/tmp
if [[ "$MODE" == "forward" ]]; then
  SMOKE_CONTAINER_DIR=/dev/shm
  unset TWOBRAIN_SMOKE_ARTIFACT_DIR TWOBRAIN_SMOKE_TOKEN_FILE TWOBRAIN_SMOKE_DURATION_SECONDS
  TWOBRAIN_PUBLIC_BASE_URL="$5"
  TWOBRAIN_OUTCOME_SMOKE_ENABLED=false
fi

SMOKE_ARTIFACT_BASE="${TWOBRAIN_SMOKE_ARTIFACT_DIR:-$SMOKE_CONTAINER_DIR/twobrain-rec-smoke-artifact}"
smoke_child_pattern="^${SMOKE_CONTAINER_DIR}/[A-Za-z0-9._-]+$"
if [[ ! "$SMOKE_ARTIFACT_BASE" =~ $smoke_child_pattern ]]; then
  echo "TWOBRAIN_SMOKE_ARTIFACT_DIR must be a direct child name under $SMOKE_CONTAINER_DIR" >&2
  exit 2
fi
SMOKE_ARTIFACT_DIR="${SMOKE_ARTIFACT_BASE%/}-${RUN_ID}"
SMOKE_TOKEN_FILE="${TWOBRAIN_SMOKE_TOKEN_FILE:-$SMOKE_CONTAINER_DIR/twobrain-rec-smoke-auth-token-${RUN_ID}}"
if [[ ! "$SMOKE_TOKEN_FILE" =~ $smoke_child_pattern ]]; then
  echo "TWOBRAIN_SMOKE_TOKEN_FILE must be a direct child under $SMOKE_CONTAINER_DIR" >&2
  exit 2
fi
token_basename="${SMOKE_TOKEN_FILE##*/}"
if [[ "$token_basename" != "$RUN_ID" && "$token_basename" != *-"$RUN_ID" ]]; then
  echo "TWOBRAIN_SMOKE_TOKEN_FILE must be bound to the exact run_id" >&2
  exit 2
fi
if [[ -L "$SMOKE_ARTIFACT_DIR" || -L "$SMOKE_TOKEN_FILE" ]]; then
  echo "smoke artifact and token paths must not be symlinks" >&2
  exit 2
fi
if [[ "${TWOBRAIN_PRODUCTION_RELEASE_GATE:-}" != "1" ]]; then
  echo "smoke_result=blocked"
  echo "reason=production_smoke_requires_release_gate"
  exit 1
fi

if [[ "$MODE" == "forward" ]]; then
  python3 infra/scripts/release-images.py check-forward-smoke "$2" "$3" "$4" "$5" "$6" "$7" "$8"
  api=(docker exec -i "$6")
  media=(docker exec -i "$7")
  maintenance=(docker exec -i "$8")
  "${api[@]}" python scripts/smoke_target.py --validate-forward-origin "$TWOBRAIN_PUBLIC_BASE_URL"
  "${api[@]}" sh -eu -c 'test -w /dev/shm; grep -q " /dev/shm .* - tmpfs " /proc/self/mountinfo'
  upload_mode=(--forward)
else
  if [[ "${TWOBRAIN_PRODUCTION_RELEASE_LOCK_HELD:-0}" != "1" ]]; then
    cd "$(dirname "$0")/../.."
    smoke_release_lock="$(git rev-parse --git-path twobrain-rec-deploy.lock)"
    exec 8>"$smoke_release_lock"
    if ! /usr/bin/flock -n 8; then
      echo "smoke_result=blocked"
      echo "reason=deploy_already_running"
      exit 1
    fi
  fi
  if [[ -z "${GRAF_RELEASE_IMAGE_OVERRIDE:-}" ]]; then
    GRAF_RELEASE_IMAGE_OVERRIDE="$(python3 infra/scripts/release-images.py current-override)"
    export GRAF_RELEASE_IMAGE_OVERRIDE
  fi
  compose=(docker compose -f infra/docker-compose.yml)
  if [[ -n "${GRAF_RELEASE_IMAGE_OVERRIDE:-}" ]]; then
    python3 infra/scripts/release-images.py validate-override "$GRAF_RELEASE_IMAGE_OVERRIDE"
    compose+=(-f "$GRAF_RELEASE_IMAGE_OVERRIDE")
  fi
  upload_mode=()
  api=("${compose[@]}" exec -T rec-api)
  media=("${compose[@]}" exec -T rec-media-worker)
  maintenance=("${compose[@]}" run --pull never --rm --no-deps -T rec-maintenance)
fi
SMOKE_RUN_DIR="$(mktemp -d "/tmp/twobrain-rec-smoke-${RUN_ID}.XXXXXX")"
chmod 700 "$SMOKE_RUN_DIR"
SMOKE_SEED_JSON="$SMOKE_RUN_DIR/seed.json"
SMOKE_AUTH_JSON="$SMOKE_RUN_DIR/auth.json"
SMOKE_AUTH_CLEANUP_JSON="$SMOKE_RUN_DIR/auth-cleanup.json"
SMOKE_ARTIFACT_CLEANUP_JSON="$SMOKE_RUN_DIR/artifact-cleanup.json"
SMOKE_ARTIFACT_JSON="$SMOKE_RUN_DIR/artifact.json"
SMOKE_UPLOAD_JSON="$SMOKE_RUN_DIR/upload.json"
SMOKE_OUTCOME_SEED_JSON="$SMOKE_RUN_DIR/outcome-seed.json"
SMOKE_OUTCOME_PROOF_JSON="$SMOKE_RUN_DIR/outcome-proof.json"
SMOKE_AUTH_CLEANUP_ERR="$SMOKE_RUN_DIR/auth-cleanup.err"
SMOKE_ARTIFACT_CLEANUP_ERR="$SMOKE_RUN_DIR/artifact-cleanup.err"
SMOKE_AUTH_SESSION_ID=""
SMOKE_AUTH_CLEANED="0"
SMOKE_ARTIFACTS_CLEANED="0"
OUTCOME_SMOKE_ENABLED="${TWOBRAIN_OUTCOME_SMOKE_ENABLED:-false}"

cleanup_smoke_container_files() {
  local mode="${1:-required}"
  local remove=("${api[@]}" sh -eu -c '
    directory="$1"
    shift
    for path; do
      [ "${path%/*}" = "$directory" ]
      if [ -e "$path" ] || [ -L "$path" ]; then
        rm -rf -- "$path"
      fi
      [ ! -e "$path" ] && [ ! -L "$path" ] || exit 1
    done
  ' _ "$SMOKE_CONTAINER_DIR" "$SMOKE_ARTIFACT_DIR" "$SMOKE_TOKEN_FILE")
  if [[ "$mode" == "best_effort" ]]; then
    "${remove[@]}" >/dev/null 2>&1 || true
  else
    "${remove[@]}" >/dev/null
  fi
}

cleanup_smoke_auth_session() {
  local mode="${1:-required}"
  if [[ "$mode" == "best_effort" && "$SMOKE_AUTH_CLEANED" == "1" ]]; then
    return 0
  fi
  local cleanup_args=(python scripts/cleanup_smoke_auth_session.py --run-id "$RUN_ID" --execute)
  if [[ -n "${SMOKE_AUTH_SESSION_ID:-}" ]]; then
    cleanup_args+=(--auth-session-id "$SMOKE_AUTH_SESSION_ID")
  fi
  if [[ "$mode" == "best_effort" ]]; then
    "${maintenance[@]}" \
      "${cleanup_args[@]}" \
      >"$SMOKE_AUTH_CLEANUP_JSON" 2>"$SMOKE_AUTH_CLEANUP_ERR" || true
    return 0
  fi

  "${maintenance[@]}" \
    "${cleanup_args[@]}" \
    >"$SMOKE_AUTH_CLEANUP_JSON"
  require_json_status "$SMOKE_AUTH_CLEANUP_JSON" auth_cleanup_result pass
  SMOKE_AUTH_CLEANED="1"
}

cleanup_smoke_artifacts() {
  local mode="${1:-required}"
  if [[ "$mode" == "best_effort" && "$SMOKE_ARTIFACTS_CLEANED" == "1" ]]; then
    return 0
  fi
  local cleanup_args=(
    python scripts/cleanup_smoke_artifacts.py
    --run-id "$RUN_ID"
    --execute
    --residue-owner deployment-operator
    --residue-follow-up-reason automatic-smoke-cleanup-incomplete
  )
  if [[ -f "$SMOKE_UPLOAD_JSON" && ( "$MODE" != "forward" || "$mode" != "best_effort" ) ]]; then
    local meeting_id
    local session_id
    meeting_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("meeting_id") or "")' "$SMOKE_UPLOAD_JSON" 2>/dev/null || true)"
    session_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("session_id") or "")' "$SMOKE_UPLOAD_JSON" 2>/dev/null || true)"
    if [[ -n "$meeting_id" && -n "$session_id" ]]; then
      cleanup_args+=(--meeting-id "$meeting_id" --session-id "$session_id")
    fi
  fi
  if [[ "$MODE" == "forward" && "$mode" != "best_effort" ]]; then
    cleanup_args+=(--media-revision-id "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["media_revision_id"])' "$SMOKE_UPLOAD_JSON")")
  fi
  if [[ "$mode" == "best_effort" ]]; then
    "${maintenance[@]}" \
      "${cleanup_args[@]}" \
      >"$SMOKE_ARTIFACT_CLEANUP_JSON" 2>"$SMOKE_ARTIFACT_CLEANUP_ERR" || true
    return 0
  fi

  "${maintenance[@]}" \
    "${cleanup_args[@]}" \
    >"$SMOKE_ARTIFACT_CLEANUP_JSON"
  require_json_status "$SMOKE_ARTIFACT_CLEANUP_JSON" cleanup_result pass
  SMOKE_ARTIFACTS_CLEANED="1"
}

cleanup_on_exit() {
  local status=$?
  set +e
  cleanup_smoke_auth_session best_effort
  cleanup_smoke_artifacts best_effort
  cleanup_smoke_container_files best_effort
  rm -rf -- "$SMOKE_RUN_DIR"
  return "$status"
}

require_json_status() {
  local json_path="$1"
  local field="$2"
  local expected="$3"
  python3 - "$json_path" "$field" "$expected" <<'PY'
import json
import sys

path, field, expected = sys.argv[1:]
with open(path, encoding="utf-8") as handle:
    payload = json.load(handle)
actual = payload.get(field)
if actual != expected:
    raise SystemExit(f"{path}: expected {field}={expected!r}, got {actual!r}")
PY
}

trap cleanup_on_exit EXIT

if [[ "$MODE" == "forward" ]]; then
  trap 'exit 143' TERM
else
  infra/scripts/validate-production-config.sh
  infra/scripts/verify-rec-migration.sh --execute
fi

# Only media-runtime contains ffmpeg. Its generator uses writable TMPDIR and
# removes its private temporary directory even when the pipe fails. The API
# accepts only a bounded tar of three allowlisted regular files. pipefail keeps
# either side's failure ahead of auth creation and upload.
"${media[@]}" \
  python scripts/create_test_artifact.py --stream \
  --duration-seconds "${TWOBRAIN_SMOKE_DURATION_SECONDS:-3}" | \
  "${api[@]}" \
    python scripts/create_test_artifact.py --receive \
    --out "$SMOKE_ARTIFACT_DIR" >"$SMOKE_ARTIFACT_JSON"

"${api[@]}" \
  sh -eu -c '
    path="$1"
    [ "${path%/*}" = "$2" ]
    [ ! -L "$path" ]
    [ -d "$path" ]
  ' _ "$SMOKE_ARTIFACT_DIR" "$SMOKE_CONTAINER_DIR"

"${maintenance[@]}" \
  python scripts/seed_smoke_identity.py \
  --run-id "$RUN_ID" \
  --execute >"$SMOKE_SEED_JSON"
require_json_status "$SMOKE_SEED_JSON" seed_result pass

"${api[@]}" \
  python scripts/issue_smoke_auth_session.py \
  --run-id "$RUN_ID" \
  --execute \
  --ttl-seconds 600 \
  --token-file "$SMOKE_TOKEN_FILE" >"$SMOKE_AUTH_JSON"

issued_token_file="$(
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["token_file"])' "$SMOKE_AUTH_JSON"
)"
if [[ "$issued_token_file" != "$SMOKE_TOKEN_FILE" ]]; then
  echo "issued smoke token path differs from the requested path" >&2
  exit 2
fi
SMOKE_AUTH_SESSION_ID="$(
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("auth_session_id") or "")' "$SMOKE_AUTH_JSON"
)"

"${api[@]}" \
  python scripts/upload_test_artifact.py \
  --api "${TWOBRAIN_PUBLIC_BASE_URL:-https://rec.2brain.pro}" \
  --organization "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["X-Organization-Id"])' "$SMOKE_AUTH_JSON")" \
  --workspace "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["X-Workspace-Id"])' "$SMOKE_AUTH_JSON")" \
  --user "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["X-User-Id"])' "$SMOKE_AUTH_JSON")" \
  --device "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["X-Device-Id"])' "$SMOKE_AUTH_JSON")" \
  --run-id "$RUN_ID" \
  --token-file "$SMOKE_TOKEN_FILE" \
  --artifact "$SMOKE_ARTIFACT_DIR" ${upload_mode[@]+"${upload_mode[@]}"} >"$SMOKE_UPLOAD_JSON"

outcome_seed_result='{"status":"skipped"}'
outcome_proof_result='{"status":"skipped"}'
if [[ "$OUTCOME_SMOKE_ENABLED" == "true" ]]; then
  SMOKE_MEETING_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["meeting_id"])' "$SMOKE_UPLOAD_JSON")"
  "${maintenance[@]}" \
    python scripts/seed_smoke_outcome.py \
    --run-id "$RUN_ID" \
    --meeting-id "$SMOKE_MEETING_ID" \
    --media-revision-id "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["media_revision_id"])' "$SMOKE_UPLOAD_JSON")" \
    --execute >"$SMOKE_OUTCOME_SEED_JSON"

  "${api[@]}" \
    python scripts/prove_meeting_outcome_live.py \
    --api "${TWOBRAIN_PUBLIC_BASE_URL:-https://rec.2brain.pro}" \
    --token-file "$SMOKE_TOKEN_FILE" \
    --run-id "$RUN_ID" \
    --meeting-id "$SMOKE_MEETING_ID" \
    --execute >"$SMOKE_OUTCOME_PROOF_JSON"
  require_json_status "$SMOKE_OUTCOME_PROOF_JSON" summary_state absent
  require_json_status "$SMOKE_OUTCOME_PROOF_JSON" slot_state unpublished
  outcome_seed_result="$(cat "$SMOKE_OUTCOME_SEED_JSON")"
  outcome_proof_result="$(cat "$SMOKE_OUTCOME_PROOF_JSON")"
fi

cleanup_smoke_auth_session
cleanup_smoke_artifacts
cleanup_smoke_container_files required
if [[ "$MODE" == "forward" ]]; then
  python3 - "$RUN_ID" "$SMOKE_UPLOAD_JSON" "$SMOKE_AUTH_CLEANUP_JSON" "$SMOKE_ARTIFACT_CLEANUP_JSON" <<'PYTHON'
import json
import sys

run_id, *paths = sys.argv[1:]
upload, auth_cleanup, cleanup = (json.load(open(path, encoding="utf-8")) for path in paths)
print(json.dumps(dict(run_id=run_id, upload=upload, auth_cleanup=auth_cleanup, cleanup=cleanup)))
PYTHON
  rm -rf -- "$SMOKE_RUN_DIR"
  trap - EXIT
  exit 0
fi
trap - EXIT

upload_result="$(cat "$SMOKE_UPLOAD_JSON")"
auth_cleanup_result="$(cat "$SMOKE_AUTH_CLEANUP_JSON")"
cleanup_result="$(cat "$SMOKE_ARTIFACT_CLEANUP_JSON")"
rm -rf -- "$SMOKE_RUN_DIR"

cat <<EOF
smoke_result=pass
readiness_verdict=infra_smoke_ready
run_id=$RUN_ID
upload_result=$upload_result
outcome_seed_result=$outcome_seed_result
outcome_proof_result=$outcome_proof_result
auth_cleanup_result=$auth_cleanup_result
cleanup_result=$cleanup_result
EOF
