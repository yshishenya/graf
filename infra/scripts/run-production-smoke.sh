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
RUN_ID="${TWOBRAIN_SMOKE_RUN_ID:-smoke-$(date -u +%Y%m%d-%H%M%S)}"

if [[ "$MODE" == "remote" ]]; then
  ssh "$REMOTE_HOST" "cd '$REMOTE_PATH' && TWOBRAIN_SMOKE_RUN_ID='$RUN_ID' infra/scripts/run-production-smoke.sh --execute"
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

docker compose -f infra/docker-compose.yml exec -T rec-api \
  python scripts/create_test_artifact.py \
  --out "${TWOBRAIN_SMOKE_ARTIFACT_DIR:-/tmp/twobrain-rec-smoke-artifact}" \
  --duration-seconds "${TWOBRAIN_SMOKE_DURATION_SECONDS:-3}" >/tmp/twobrain-rec-smoke-artifact.json

SMOKE_AUTH_JSON="/tmp/twobrain-rec-smoke-auth.json"
SMOKE_AUTH_CLEANUP_JSON="/tmp/twobrain-rec-smoke-auth-cleanup.json"
SMOKE_ARTIFACT_CLEANUP_JSON="/tmp/twobrain-rec-smoke-cleanup.json"
SMOKE_TOKEN_FILE="${TWOBRAIN_SMOKE_TOKEN_FILE:-/tmp/twobrain-rec-smoke-auth-token-${RUN_ID}}"
SMOKE_AUTH_SESSION_ID=""
SMOKE_AUTH_CLEANED="0"
SMOKE_ARTIFACTS_CLEANED="0"

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
    docker compose -f infra/docker-compose.yml exec -T rec-api "${cleanup_args[@]}" \
      >"$SMOKE_AUTH_CLEANUP_JSON" 2>/tmp/twobrain-rec-smoke-auth-cleanup.err || true
    docker compose -f infra/docker-compose.yml exec -T rec-api sh -c 'rm -f "$1"' _ "$SMOKE_TOKEN_FILE" \
      >/dev/null 2>&1 || true
    return 0
  fi

  docker compose -f infra/docker-compose.yml exec -T rec-api "${cleanup_args[@]}" \
    >"$SMOKE_AUTH_CLEANUP_JSON"
  require_json_status "$SMOKE_AUTH_CLEANUP_JSON" auth_cleanup_result pass
  SMOKE_AUTH_CLEANED="1"
  docker compose -f infra/docker-compose.yml exec -T rec-api sh -c 'rm -f "$1"' _ "$SMOKE_TOKEN_FILE" \
    >/dev/null 2>&1 || true
}

cleanup_smoke_artifacts() {
  local mode="${1:-required}"
  if [[ "$mode" == "best_effort" && "$SMOKE_ARTIFACTS_CLEANED" == "1" ]]; then
    return 0
  fi
  local cleanup_args=(python scripts/cleanup_smoke_artifacts.py --run-id "$RUN_ID" --execute)
  if [[ -f /tmp/twobrain-rec-smoke-upload.json ]]; then
    local meeting_id
    local session_id
    meeting_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("meeting_id") or "")' /tmp/twobrain-rec-smoke-upload.json 2>/dev/null || true)"
    session_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("session_id") or "")' /tmp/twobrain-rec-smoke-upload.json 2>/dev/null || true)"
    if [[ -n "$meeting_id" && -n "$session_id" ]]; then
      cleanup_args+=(--meeting-id "$meeting_id" --session-id "$session_id")
    fi
  fi
  if [[ "$mode" == "best_effort" ]]; then
    docker compose -f infra/docker-compose.yml exec -T rec-api "${cleanup_args[@]}" \
      >"$SMOKE_ARTIFACT_CLEANUP_JSON" 2>/tmp/twobrain-rec-smoke-cleanup.err || true
    return 0
  fi

  docker compose -f infra/docker-compose.yml exec -T rec-api "${cleanup_args[@]}" \
    >"$SMOKE_ARTIFACT_CLEANUP_JSON"
  require_json_status "$SMOKE_ARTIFACT_CLEANUP_JSON" cleanup_result pass
  SMOKE_ARTIFACTS_CLEANED="1"
}

cleanup_on_exit() {
  cleanup_smoke_auth_session best_effort
  cleanup_smoke_artifacts best_effort
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

docker compose -f infra/docker-compose.yml exec -T rec-api \
  python scripts/issue_smoke_auth_session.py \
  --run-id "$RUN_ID" \
  --execute \
  --token-file "$SMOKE_TOKEN_FILE" >"$SMOKE_AUTH_JSON"

SMOKE_TOKEN_FILE="$(
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["token_file"])' "$SMOKE_AUTH_JSON"
)"
SMOKE_AUTH_SESSION_ID="$(
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("auth_session_id") or "")' "$SMOKE_AUTH_JSON"
)"

infra/scripts/validate-production-config.sh
infra/scripts/verify-rec-migration.sh --execute
docker compose -f infra/docker-compose.yml exec -T rec-api \
  python scripts/upload_test_artifact.py \
  --api "${TWOBRAIN_PUBLIC_BASE_URL:-https://rec.2brain.pro}" \
  --organization "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["X-Organization-Id"])' "$SMOKE_AUTH_JSON")" \
  --workspace "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["X-Workspace-Id"])' "$SMOKE_AUTH_JSON")" \
  --user "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["X-User-Id"])' "$SMOKE_AUTH_JSON")" \
  --device "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["X-Device-Id"])' "$SMOKE_AUTH_JSON")" \
  --token-file "$SMOKE_TOKEN_FILE" \
  --artifact "${TWOBRAIN_SMOKE_ARTIFACT_DIR:-/tmp/twobrain-rec-smoke-artifact}" >/tmp/twobrain-rec-smoke-upload.json

cleanup_smoke_auth_session
cleanup_smoke_artifacts
trap - EXIT

cat <<EOF
smoke_result=pass
readiness_verdict=infra_smoke_ready
run_id=$RUN_ID
upload_result=$(cat /tmp/twobrain-rec-smoke-upload.json)
auth_cleanup_result=$(cat "$SMOKE_AUTH_CLEANUP_JSON")
cleanup_result=$(cat "$SMOKE_ARTIFACT_CLEANUP_JSON")
EOF
