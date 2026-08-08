#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"

echo "recording_artifact_format_validation=started"

swift test --package-path "$ROOT_DIR/apps/macos" --disable-swift-testing
swift test --package-path "$ROOT_DIR/apps/macos" --disable-swift-testing --filter 'LocalRecordingManifestTests|DesktopUploadQueueTests|DesktopUploadClientTests'
swift run --package-path "$ROOT_DIR/apps/macos" ContractValidation
sh "$ROOT_DIR/apps/macos/Scripts/validate-no-legacy-audio-driver.sh"

test -f "$ROOT_DIR/tests/macos/contract/recording-artifact-format.json"

echo "recording_artifact_format_validation=passed"
echo "canonical_v5_recording_package=checked"
