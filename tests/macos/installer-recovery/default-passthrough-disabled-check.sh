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

PROBE_OUTPUT=$(make -C "$REPO_ROOT/apps/macos/AudioDriver" proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe 2>&1 || true)
printf '%s\n' "$PROBE_OUTPUT"

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

if printf '%s\n' "$NEW_LOG" | rg -q 'passthrough_bridge_started'; then
  echo "default-passthrough-disabled-check: bridge started during default app launch" >&2
  exit 1
fi

if ! printf '%s\n' "$NEW_LOG" | rg -q 'passthrough_bridge_experiment_available'; then
  echo "default-passthrough-disabled-check: expected explicit non-starting route-engine event during default app launch" >&2
  exit 1
fi

echo "default-passthrough-disabled-check: ACCEPTED"
