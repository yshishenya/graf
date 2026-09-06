#!/usr/bin/env bash
set -euo pipefail

MODE="dry-run"
if [[ "${1:-}" == "--remote" ]]; then
  MODE="remote"
elif [[ "${1:-}" == "--execute" ]]; then
  MODE="execute"
elif [[ "${1:-}" == "--dry-run" || $# -eq 0 ]]; then
  MODE="dry-run"
else
  echo "usage: $0 [--dry-run|--remote|--execute]" >&2
  exit 2
fi

REMOTE_HOST="${TWOBRAIN_DEPLOY_HOST:-2brain.dev}"
REMOTE_PATH="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"
if [[ -n "${TWOBRAIN_SMOKE_RUN_ID+x}" ]]; then
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

if [[ -f .env ]]; then
  set -a
  . ./.env
  set +a
fi

SMOKE_ARTIFACT_BASE="${TWOBRAIN_SMOKE_ARTIFACT_DIR:-/tmp/twobrain-rec-smoke-artifact}"
if [[ ! "$SMOKE_ARTIFACT_BASE" =~ ^/tmp/[A-Za-z0-9._-]+$ ]]; then
  echo "TWOBRAIN_SMOKE_ARTIFACT_DIR must be a direct child name under /tmp" >&2
  exit 2
fi
SMOKE_ARTIFACT_DIR="${SMOKE_ARTIFACT_BASE%/}-${RUN_ID}"
SMOKE_TOKEN_FILE="${TWOBRAIN_SMOKE_TOKEN_FILE:-/tmp/twobrain-rec-smoke-auth-token-${RUN_ID}}"
if [[ ! "$SMOKE_TOKEN_FILE" =~ ^/tmp/[A-Za-z0-9._-]+$ ]]; then
  echo "TWOBRAIN_SMOKE_TOKEN_FILE must be a direct child under /tmp" >&2
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
  if [[ "$mode" == "best_effort" ]]; then
    docker compose -f infra/docker-compose.yml exec -T rec-api \
      sh -eu -c '
        for path in "$1" "$2"; do
          case "$path" in
            /tmp/*) ;;
            *) exit 2 ;;
          esac
          [ "${path%/*}" = /tmp ]
          if [ -e "$path" ] || [ -L "$path" ]; then
            rm -rf -- "$path"
          fi
          if [ -e "$path" ] || [ -L "$path" ]; then
            exit 1
          fi
        done
      ' _ "$SMOKE_ARTIFACT_DIR" "$SMOKE_TOKEN_FILE" \
      >/dev/null 2>&1 || true
    return 0
  fi
  docker compose -f infra/docker-compose.yml exec -T rec-api \
    sh -eu -c '
      for path in "$1" "$2"; do
        case "$path" in
          /tmp/*) ;;
          *) exit 2 ;;
        esac
        [ "${path%/*}" = /tmp ]
        if [ -e "$path" ] || [ -L "$path" ]; then
          rm -rf -- "$path"
        fi
        if [ -e "$path" ] || [ -L "$path" ]; then
          exit 1
        fi
      done
    ' _ "$SMOKE_ARTIFACT_DIR" "$SMOKE_TOKEN_FILE" \
    >/dev/null
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
    docker compose -f infra/docker-compose.yml run --rm --no-deps -T rec-maintenance \
      "${cleanup_args[@]}" \
      >"$SMOKE_AUTH_CLEANUP_JSON" 2>"$SMOKE_AUTH_CLEANUP_ERR" || true
    return 0
  fi

  docker compose -f infra/docker-compose.yml run --rm --no-deps -T rec-maintenance \
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
  if [[ -f "$SMOKE_UPLOAD_JSON" ]]; then
    local meeting_id
    local session_id
    meeting_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("meeting_id") or "")' "$SMOKE_UPLOAD_JSON" 2>/dev/null || true)"
    session_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("session_id") or "")' "$SMOKE_UPLOAD_JSON" 2>/dev/null || true)"
    if [[ -n "$meeting_id" && -n "$session_id" ]]; then
      cleanup_args+=(--meeting-id "$meeting_id" --session-id "$session_id")
    fi
  fi
  if [[ "$mode" == "best_effort" ]]; then
    docker compose -f infra/docker-compose.yml run --rm --no-deps -T rec-maintenance \
      "${cleanup_args[@]}" \
      >"$SMOKE_ARTIFACT_CLEANUP_JSON" 2>"$SMOKE_ARTIFACT_CLEANUP_ERR" || true
    return 0
  fi

  docker compose -f infra/docker-compose.yml run --rm --no-deps -T rec-maintenance \
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

infra/scripts/validate-production-config.sh
infra/scripts/verify-rec-migration.sh --execute

docker compose -f infra/docker-compose.yml exec -T rec-api \
  python scripts/create_test_artifact.py \
  --out "$SMOKE_ARTIFACT_DIR" \
  --duration-seconds "${TWOBRAIN_SMOKE_DURATION_SECONDS:-3}" >"$SMOKE_ARTIFACT_JSON"

docker compose -f infra/docker-compose.yml exec -T rec-api \
  sh -eu -c '
    path="$1"
    [ "${path%/*}" = /tmp ]
    [ ! -L "$path" ]
    [ -d "$path" ]
  ' _ "$SMOKE_ARTIFACT_DIR"

docker compose -f infra/docker-compose.yml run --rm --no-deps -T rec-maintenance \
  python scripts/seed_smoke_identity.py \
  --run-id "$RUN_ID" \
  --execute >"$SMOKE_SEED_JSON"
require_json_status "$SMOKE_SEED_JSON" seed_result pass

docker compose -f infra/docker-compose.yml exec -T rec-api \
  python scripts/issue_smoke_auth_session.py \
  --run-id "$RUN_ID" \
  --execute \
  --ttl-seconds 600 \
  --token-file "$SMOKE_TOKEN_FILE" >"$SMOKE_AUTH_JSON"

SMOKE_TOKEN_FILE="$(
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["token_file"])' "$SMOKE_AUTH_JSON"
)"
if [[ ! "$SMOKE_TOKEN_FILE" =~ ^/tmp/[A-Za-z0-9._-]+$ || "${SMOKE_TOKEN_FILE%/*}" != /tmp ]]; then
  echo "issued smoke token path must be a direct child under /tmp" >&2
  exit 2
fi
SMOKE_AUTH_SESSION_ID="$(
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("auth_session_id") or "")' "$SMOKE_AUTH_JSON"
)"

docker compose -f infra/docker-compose.yml exec -T rec-api \
  python scripts/upload_test_artifact.py \
  --api "${TWOBRAIN_PUBLIC_BASE_URL:-https://rec.2brain.pro}" \
  --organization "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["X-Organization-Id"])' "$SMOKE_AUTH_JSON")" \
  --workspace "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["X-Workspace-Id"])' "$SMOKE_AUTH_JSON")" \
  --user "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["X-User-Id"])' "$SMOKE_AUTH_JSON")" \
  --device "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["X-Device-Id"])' "$SMOKE_AUTH_JSON")" \
  --run-id "$RUN_ID" \
  --token-file "$SMOKE_TOKEN_FILE" \
  --artifact "$SMOKE_ARTIFACT_DIR" >"$SMOKE_UPLOAD_JSON"

outcome_seed_result='{"status":"skipped"}'
outcome_proof_result='{"status":"skipped"}'
if [[ "$OUTCOME_SMOKE_ENABLED" == "true" ]]; then
  SMOKE_MEETING_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["meeting_id"])' "$SMOKE_UPLOAD_JSON")"
  docker compose -f infra/docker-compose.yml run --rm --no-deps -T rec-maintenance \
    python scripts/seed_smoke_outcome.py \
    --run-id "$RUN_ID" \
    --meeting-id "$SMOKE_MEETING_ID" \
    --execute >"$SMOKE_OUTCOME_SEED_JSON"

  docker compose -f infra/docker-compose.yml exec -T rec-api \
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
