#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(CDPATH= cd -- "$MACOS_DIR/../.." && pwd)

echo "== 005 passthrough release hardening: setup/foundation baseline =="

swift build --package-path "$MACOS_DIR" -c release --product TwoBrainRecApp
sh "$REPO_ROOT/tests/macos/static/audio-rt-safety-check.sh"
make -C "$MACOS_DIR/AudioDriver" proof-plugin-build proof-runtime-probe-build proof-hal-io-probe-build
sh "$SCRIPT_DIR/validate-real-bidirectional-passthrough.sh"

echo "== 005 passthrough release hardening: pending gates =="
echo "- Installed runtime package probe: pending T025"
echo "- No-hang and CPU gate: pending T032-T034"
echo "- Route recovery gate: pending T043-T049"
echo "- Installer lifecycle gate: pending T054-T059"
echo "- Diagnostics and UX gate: pending T064-T069"
echo "- Deferred recording-assisted acceptance: pending T072-T075"
echo "validate-passthrough-release-hardening: completed available baseline checks"
