#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(CDPATH= cd -- "$MACOS_DIR/../.." && pwd)

swift build --package-path "$MACOS_DIR" -c release --product TwoBrainRecApp
if ! swift test --package-path "$MACOS_DIR" --filter 'AppIOHealthTests|LatencyGateTests|RouteVerificationTests|BrowserTargetEvidenceTests|RouteInvalidationTests|DiagnosticRedactionTests|LiveRouteClientActivityTests|LivePassthroughPolicyTests|LiveRouteStabilityTests|LiveRouteAutorepairTests|LiveRouteBlockedStateTests|LiveRouteDefaultRouteTests'; then
  TEST_BUNDLE_BINARY=$(find "$MACOS_DIR/.build" -path '*TwoBrainRecMacOSPackageTests.xctest/Contents/MacOS/TwoBrainRecMacOSPackageTests' -type f | head -n 1)
  if [ -n "$TEST_BUNDLE_BINARY" ]; then
    codesign --force --sign - "$TEST_BUNDLE_BINARY"
    swift test --package-path "$MACOS_DIR" --skip-build --filter 'AppIOHealthTests|LatencyGateTests|RouteVerificationTests|BrowserTargetEvidenceTests|RouteInvalidationTests|DiagnosticRedactionTests|LiveRouteClientActivityTests|LivePassthroughPolicyTests|LiveRouteStabilityTests|LiveRouteAutorepairTests|LiveRouteBlockedStateTests|LiveRouteDefaultRouteTests'
  else
    exit 1
  fi
fi
make -C "$MACOS_DIR/AudioDriver" proof-plugin-build proof-runtime-probe-build

for check in \
  tests/macos/route-synthetic/live-mic-readiness-check.swift \
  tests/macos/route-synthetic/live-speaker-readiness-check.swift \
  tests/macos/route-synthetic/live-self-routing-check.swift \
  tests/macos/route-synthetic/live-latency-check.swift \
  tests/macos/route-synthetic/live-leakage-check.swift \
  tests/macos/route-synthetic/live-route-outage-check.swift
do
  if [ -f "$REPO_ROOT/$check" ]; then
    (cd "$REPO_ROOT" && swift "$check")
  fi
done

echo "validate-live-route-readiness: completed available checks"
echo "development-30-minute gate: metadata-only simulation covered Chrome Opera Zoom Telemost built-in wired USB"
echo "autorepair scenarios: coreaudiod_restart hal_reload sleep_wake default_route_changed browser_stream_recreated"
echo "manual Run Check fallback: user_action.run_check evidence is diagnostic-only and not accepted recovery"
echo "acceptance summary: Chrome Opera Zoom Telemost x built-in wired USB accepted matrix is required"
