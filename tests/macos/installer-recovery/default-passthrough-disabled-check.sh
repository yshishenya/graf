#!/usr/bin/env sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
APP_LOG="$HOME/Library/Logs/2brain Rec/2brain-rec.log"

osascript -e 'quit app "2brain Rec"' >/dev/null 2>&1 || true
pkill -f '/Applications/2brain Rec.app' 2>/dev/null || true
sleep 1

BEFORE_SIZE=0
if [ -f "$APP_LOG" ]; then
  BEFORE_SIZE=$(wc -c < "$APP_LOG" | tr -d ' ')
fi

open -a "2brain Rec"
sleep "${TWO_BRAIN_REC_DEFAULT_OFF_WAIT_SECONDS:-6}"

TIMEOUT_BIN=$(command -v timeout || command -v gtimeout || true)
if [ -n "$TIMEOUT_BIN" ]; then
  PROBE_OUTPUT=$("$TIMEOUT_BIN" 20 make -C "$REPO_ROOT/apps/macos/AudioDriver" proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe 2>&1 || true)
else
  PROBE_OUTPUT=$(make -C "$REPO_ROOT/apps/macos/AudioDriver" proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe 2>&1 || true)
fi
printf '%s\n' "$PROBE_OUTPUT"

if printf '%s\n' "$PROBE_OUTPUT" | rg -q 'timed out|Terminated: 15'; then
  echo "default-passthrough-disabled-check: runtime publication proof timed out" >&2
  exit 1
fi

if ! printf '%s\n' "$PROBE_OUTPUT" | rg -q 'Runtime Core Audio publication proof: ACCEPTED'; then
  echo "default-passthrough-disabled-check: runtime publication proof failed" >&2
  exit 1
fi

if ! printf '%s\n' "$PROBE_OUTPUT" | rg -q 'running=0'; then
  echo "default-passthrough-disabled-check: expected default app launch to keep virtual devices non-running" >&2
  exit 1
fi

NEW_LOG=""
if [ -f "$APP_LOG" ]; then
  NEW_LOG=$(tail -c +"$((BEFORE_SIZE + 1))" "$APP_LOG" 2>/dev/null || true)
fi

LAUNCH_ROUTE_EVIDENCE=$(printf '%s\n' "$NEW_LOG" |
  rg 'passthrough_bridge_armed|passthrough_bridge_started|passthrough_bridge_already_active' |
  rg 'automatic non-recording route engine|waiting for virtual device client|route engine refreshed app IO heartbeat' || true)

if [ -z "$LAUNCH_ROUTE_EVIDENCE" ]; then
  echo "default-passthrough-disabled-check: expected automatic non-recording route evidence during default app launch" >&2
  exit 1
fi

if printf '%s\n' "$LAUNCH_ROUTE_EVIDENCE" | rg -q 'passthrough_bridge_started' &&
   ! printf '%s\n' "$LAUNCH_ROUTE_EVIDENCE" | rg -q 'automatic non-recording route engine active|passthrough_bridge_already_active'; then
  echo "default-passthrough-disabled-check: expected started route-engine evidence to remain non-recording" >&2
  exit 1
fi

if printf '%s\n' "$LAUNCH_ROUTE_EVIDENCE" | rg -q 'passthrough_bridge_armed' &&
   ! printf '%s\n' "$LAUNCH_ROUTE_EVIDENCE" | rg -q 'waiting for virtual device client'; then
  echo "default-passthrough-disabled-check: expected armed route-engine evidence to wait for a virtual device client" >&2
  exit 1
fi

echo "default-passthrough-disabled-check: ACCEPTED"
