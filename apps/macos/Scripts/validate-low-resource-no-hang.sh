#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)

echo "== 006 low-resource audio: no-hang and startup timeout gates =="

swift "$REPO_ROOT/tests/macos/route-synthetic/low-resource-startup-timeout-check.swift"
GRAF_LOW_RESOURCE_MODE=1 sh "$SCRIPT_DIR/audio-settings-no-hang-check.sh" all

echo "low-resource-no-hang: completed available no-hang gates"
