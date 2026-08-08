#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"

echo "capture_session_indicator_validation=started"

swift test --package-path "$ROOT_DIR/apps/macos" --disable-swift-testing
swift run --package-path "$ROOT_DIR/apps/macos" ContractValidation
sh "$ROOT_DIR/apps/macos/Scripts/validate-no-legacy-audio-driver.sh"

echo "capture_session_indicator_validation=passed"
