#!/usr/bin/env sh
set -eu

STATE_FILE=${GRAF_CAPTURE_ACTIVE_FILE:-/var/tmp/graf-capture-active}
CAPTURE_ACTIVE=${GRAF_CAPTURE_ACTIVE:-0}
MODE=${GRAF_INSTALL_MODE:-update}

echo "graf-preflight: mode=$MODE"

if [ "$CAPTURE_ACTIVE" = "1" ] || [ -f "$STATE_FILE" ]; then
  echo "graf-preflight: detected active capture; update deferred"
  echo '{"result":"deferred_active_call","reason":"capture_is_active"}'
  exit 2
fi

if [ "${GRAF_ALLOW_IMMEDIATE_UPDATE:-}" = "1" ]; then
  echo "graf-preflight: override grants immediate update"
fi

echo "graf-preflight: no active capture detected"
echo '{"result":"ok","reason":"ready"}'
exit 0
