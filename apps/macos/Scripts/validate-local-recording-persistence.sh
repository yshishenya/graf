#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"

echo "local_recording_persistence_validation=started"

swift test --package-path "$ROOT_DIR/apps/macos" --disable-swift-testing
swift run --package-path "$ROOT_DIR/apps/macos" ContractValidation
sh "$ROOT_DIR/tests/macos/static/audio-rt-safety-check.sh"

test -f "$ROOT_DIR/tests/macos/contract/local-recording-manifest.json"

echo "local_recording_persistence_validation=passed"
