#!/usr/bin/env sh
set -eu

STATE_FILE=${2BRAIN_REC_CAPTURE_ACTIVE_FILE:-/var/tmp/2brain-rec-capture-active}
CAPTURE_ACTIVE=${2BRAIN_REC_CAPTURE_ACTIVE:-0}
MODE=${2BRAIN_REC_INSTALL_MODE:-update}

echo "2brain-rec-preflight: mode=$MODE"

if [ "$CAPTURE_ACTIVE" = "1" ] || [ -f "$STATE_FILE" ]; then
  echo "2brain-rec-preflight: detected active capture; update deferred"
  echo '{"result":"deferred_active_call","reason":"capture_is_active"}'
  exit 2
fi

if [ "${2BRAIN_REC_ALLOW_IMMEDIATE_UPDATE:-}" = "1" ]; then
  echo "2brain-rec-preflight: override grants immediate update"
fi

echo "2brain-rec-preflight: no active capture detected"
echo '{"result":"ok","reason":"ready"}'
exit 0
