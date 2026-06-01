#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(CDPATH= cd -- "$MACOS_DIR/../.." && pwd)

echo "== 005 passthrough release hardening: setup/foundation baseline =="

swift build --package-path "$MACOS_DIR" -c release --product TwoBrainRecApp
sh "$REPO_ROOT/tests/macos/static/audio-rt-safety-check.sh"
make -C "$MACOS_DIR/AudioDriver" proof-plugin-build proof-runtime-probe-build proof-hal-io-probe-build
make -C "$MACOS_DIR/AudioDriver" proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe
sh "$SCRIPT_DIR/coreaudiod-cpu-sample.sh"
sh "$SCRIPT_DIR/audio-settings-no-hang-check.sh" all
sh "$SCRIPT_DIR/installer-lifecycle-release-hardening.sh" all
sh "$SCRIPT_DIR/validate-real-bidirectional-passthrough.sh"
rg -n "(BEGIN (RSA|OPENSSH|PRIVATE) KEY|AKIA[0-9A-Z]{16}|xox[baprs]-|ghp_|sk-[A-Za-z0-9]{20,}|signed_url|signedUrl|token=|password=)" \
  "$MACOS_DIR" "$REPO_ROOT/tests/macos" "$REPO_ROOT/qa/macos" "$REPO_ROOT/specs/005-macos-passthrough-release-hardening" || true

echo "== 005 passthrough release hardening: pending gates =="
echo "- Installed runtime package build/install probe: pending final packaging run"
echo "- Audio settings no-hang helper defaults to metadata-only; set TWO_BRAIN_REC_RUN_UI_NO_HANG=1 for actual UI launch evidence"
echo "- Route recovery checklists are available; physical/coreaudiod/sleep-wake evidence still requires environment execution"
echo "- Installer lifecycle helper defaults to metadata-only; set TWO_BRAIN_REC_RUN_INSTALLER_LIFECYCLE=1 for destructive lifecycle evidence"
echo "- Diagnostics scan is metadata-only; matches must be policy text or deliberate fixtures"
echo "- Deferred recording-assisted acceptance: pending T072-T075"
echo "validate-passthrough-release-hardening: completed available baseline checks"
