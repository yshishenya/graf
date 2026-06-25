#!/usr/bin/env bash
set -euo pipefail

PUBLIC_URL="${PUBLIC_URL:-https://rec.2brain.pro}"
REMOTE_HOST="${REC_DEPLOY_REMOTE:-2brain.dev}"
REMOTE_DIR="${REC_DEPLOY_DIR:-/opt/projects/2brain-rec}"

live_payload="$(curl -fsS "${PUBLIC_URL}/api/v1/health/live")"
ready_payload="$(curl -fsS "${PUBLIC_URL}/api/v1/health/ready")"
local_sha="$(git rev-parse HEAD)"
origin_master_sha="$(git rev-parse origin/master)"

remote_branch="unavailable"
remote_sha="unavailable"
if remote_output="$(
  ssh -o BatchMode=yes -o ConnectTimeout=10 "${REMOTE_HOST}" \
    "cd '${REMOTE_DIR}' && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD" 2>/dev/null
)"; then
  remote_branch="$(printf '%s\n' "${remote_output}" | sed -n '1p')"
  remote_sha="$(printf '%s\n' "${remote_output}" | sed -n '2p')"
fi

status="pass"
if ! printf '%s' "${live_payload}" | grep -q '"status":"ok"'; then
  status="fail"
fi
if ! printf '%s' "${ready_payload}" | grep -q '"status":"ready"'; then
  status="fail"
fi
if [[ "${remote_sha}" == "unavailable" ]]; then
  status="fail"
fi

python3 - "$status" "$PUBLIC_URL" "$live_payload" "$ready_payload" "$local_sha" "$origin_master_sha" "$remote_branch" "$remote_sha" <<'PY'
import json
import sys

status, public_url, live_payload, ready_payload, local_sha, origin_master_sha, remote_branch, remote_sha = sys.argv[1:]
print(json.dumps({
    "status": status,
    "public_url": public_url,
    "live_payload": live_payload,
    "ready_payload": ready_payload,
    "local_sha": local_sha,
    "origin_master_sha": origin_master_sha,
    "remote_branch": remote_branch,
    "remote_sha": remote_sha,
}, ensure_ascii=False, sort_keys=True))
PY

[[ "${status}" == "pass" ]]
