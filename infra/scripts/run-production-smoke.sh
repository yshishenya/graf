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

docker compose -f infra/docker-compose.yml exec -T rec-api \
  python scripts/create_test_artifact.py \
  --out "${TWOBRAIN_SMOKE_ARTIFACT_DIR:-/tmp/twobrain-rec-smoke-artifact}" \
  --duration-seconds "${TWOBRAIN_SMOKE_DURATION_SECONDS:-3}" >/tmp/twobrain-rec-smoke-artifact.json
docker compose -f infra/docker-compose.yml exec -T rec-api \
  python scripts/seed_smoke_identity.py --run-id "$RUN_ID" --execute >/tmp/twobrain-rec-smoke-identity.json
infra/scripts/validate-production-config.sh
infra/scripts/verify-rec-migration.sh --execute
docker compose -f infra/docker-compose.yml exec -T rec-api \
  python scripts/upload_test_artifact.py \
  --api "${TWOBRAIN_PUBLIC_BASE_URL:-https://rec.2brain.pro}" \
  --organization "$(python3 -c 'import json; print(json.load(open("/tmp/twobrain-rec-smoke-identity.json"))["X-Organization-Id"])')" \
  --workspace "$(python3 -c 'import json; print(json.load(open("/tmp/twobrain-rec-smoke-identity.json"))["X-Workspace-Id"])')" \
  --user "$(python3 -c 'import json; print(json.load(open("/tmp/twobrain-rec-smoke-identity.json"))["X-User-Id"])')" \
  --device "$(python3 -c 'import json; print(json.load(open("/tmp/twobrain-rec-smoke-identity.json"))["X-Device-Id"])')" \
  --artifact "${TWOBRAIN_SMOKE_ARTIFACT_DIR:-/tmp/twobrain-rec-smoke-artifact}" >/tmp/twobrain-rec-smoke-upload.json
docker compose -f infra/docker-compose.yml exec -T rec-api \
  python scripts/cleanup_smoke_artifacts.py \
  --run-id "$RUN_ID" \
  --execute \
  --meeting-id "$(python3 -c 'import json; print(json.load(open("/tmp/twobrain-rec-smoke-upload.json"))["meeting_id"])')" \
  --session-id "$(python3 -c 'import json; print(json.load(open("/tmp/twobrain-rec-smoke-upload.json"))["session_id"])')" >/tmp/twobrain-rec-smoke-cleanup.json
cat <<EOF
smoke_result=pass
readiness_verdict=infra_smoke_ready
run_id=$RUN_ID
upload_result=$(cat /tmp/twobrain-rec-smoke-upload.json)
cleanup_result=$(cat /tmp/twobrain-rec-smoke-cleanup.json)
EOF
