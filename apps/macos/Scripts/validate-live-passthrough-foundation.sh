#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(CDPATH= cd -- "$MACOS_DIR/../.." && pwd)

swift test --package-path "$MACOS_DIR" --filter 'AppIOHealthTests|LatencyGateTests|RouteVerificationTests'
(cd "$REPO_ROOT" && swift tests/macos/route-synthetic/latency-check.swift)
