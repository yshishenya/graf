#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(CDPATH= cd -- "$MACOS_DIR/../.." && pwd)

swift build --package-path "$MACOS_DIR" -c release --product TwoBrainRecApp
sh "$REPO_ROOT/tests/macos/static/audio-rt-safety-check.sh"
if [ "${TWO_BRAIN_RUN_COREAUDIO_PROBES:-0}" = "1" ]; then
  sh "$REPO_ROOT/tests/macos/installer-recovery/default-passthrough-disabled-check.sh"
fi
if ! swift test --package-path "$MACOS_DIR" --filter 'AppIOHealthTests|LivePassthroughPolicyTests|SharedAudioMemoryCompatibilityTests|LatencyGateTests|RouteVerificationTests|BrowserTargetEvidenceTests|RouteInvalidationTests|DiagnosticRedactionTests'; then
  TEST_BUNDLE_BINARY=$(find "$MACOS_DIR/.build" -path '*TwoBrainRecMacOSPackageTests.xctest/Contents/MacOS/TwoBrainRecMacOSPackageTests' -type f | head -n 1)
  if [ -n "$TEST_BUNDLE_BINARY" ]; then
    codesign --force --sign - "$TEST_BUNDLE_BINARY"
    swift test --package-path "$MACOS_DIR" --skip-build --filter 'AppIOHealthTests|LivePassthroughPolicyTests|SharedAudioMemoryCompatibilityTests|LatencyGateTests|RouteVerificationTests|BrowserTargetEvidenceTests|RouteInvalidationTests|DiagnosticRedactionTests'
  else
    exit 1
  fi
fi
make -C "$MACOS_DIR/AudioDriver" proof-plugin-build proof-runtime-probe-build

for check in \
  tests/macos/route-synthetic/live-mic-readiness-check.swift \
  tests/macos/route-synthetic/live-mic-passthrough-check.swift \
  tests/macos/route-synthetic/live-mic-silence-check.swift \
  tests/macos/route-synthetic/live-mic-self-routing-check.swift \
  tests/macos/route-synthetic/live-speaker-readiness-check.swift \
  tests/macos/route-synthetic/live-speaker-passthrough-check.swift \
  tests/macos/route-synthetic/live-speaker-failure-check.swift \
  tests/macos/route-synthetic/live-passthrough-no-loopback-check.swift \
  tests/macos/route-synthetic/live-self-routing-check.swift \
  tests/macos/route-synthetic/live-latency-check.swift \
  tests/macos/route-synthetic/live-leakage-check.swift \
  tests/macos/route-synthetic/live-route-outage-check.swift \
  tests/macos/route-synthetic/live-passthrough-outage-check.swift \
  tests/macos/route-synthetic/live-passthrough-fail-closed-check.swift
do
  if [ -f "$REPO_ROOT/$check" ]; then
    (cd "$REPO_ROOT" && swift "$check")
  fi
done

echo "validate-real-bidirectional-passthrough: completed available checks"
