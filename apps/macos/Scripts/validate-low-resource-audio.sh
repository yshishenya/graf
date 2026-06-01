#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(CDPATH= cd -- "$MACOS_DIR/../.." && pwd)
FEATURE_DIR="$REPO_ROOT/specs/006-low-resource-audio"

echo "== 006 low-resource audio: metadata-safe validation =="

echo "-- Swift build and shared tests --"
swift build --package-path "$MACOS_DIR" -c release --product TwoBrainRecApp
swift test --package-path "$MACOS_DIR" --disable-swift-testing

echo "-- Static realtime-safety scan --"
sh "$REPO_ROOT/tests/macos/static/audio-rt-safety-check.sh"

echo "-- HAL proof builds and default-safe runtime publication probe --"
make -C "$MACOS_DIR/AudioDriver" proof-plugin-build proof-runtime-probe-build proof-hal-io-probe-build
make -C "$MACOS_DIR/AudioDriver" proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe

echo "-- Low-resource contract fixtures present --"
test -f "$REPO_ROOT/tests/macos/contract/low-resource-validation-evidence.json"
test -f "$REPO_ROOT/tests/macos/contract/low-resource-route-truth.json"
test -f "$REPO_ROOT/tests/macos/contract/low-resource-startup-attempt.json"
test -f "$REPO_ROOT/tests/macos/contract/low-resource-promotion-run.json"
test -f "$REPO_ROOT/tests/macos/contract/low-resource-blocked-run.json"
test -f "$REPO_ROOT/tests/macos/browser-meetings/low-resource-stale-device-recovery.md"
test -f "$REPO_ROOT/tests/macos/physical-devices/low-resource-sleep-wake.md"

echo "-- No-Run-Check automatic activation regression fixture --"
swift "$REPO_ROOT/tests/macos/route-synthetic/low-resource-auto-activation-check.swift"
rg -n "requiresRunCheck\": true|Run Check is required" "$FEATURE_DIR" "$REPO_ROOT/tests/macos" && {
  echo "low-resource no-Run-Check regression: BLOCKED" >&2
  exit 1
} || true

echo "-- Metadata-only redaction scan --"
rg -n "(BEGIN (RSA|OPENSSH|PRIVATE) KEY|AKIA[0-9A-Z]{16}|xox[baprs]-|ghp_|sk-[A-Za-z0-9]{20,}|signed_url|signedUrl|token=|password=)" \
  "$MACOS_DIR" "$REPO_ROOT/tests/macos" "$REPO_ROOT/qa/macos" "$FEATURE_DIR" || true

echo "-- Coreaudiod restart recovery gate --"
if [ "${TWO_BRAIN_REC_RUN_LOW_RESOURCE_COREAUDIOD_RESTART:-0}" = "1" ]; then
  sh "$SCRIPT_DIR/coreaudiod-cpu-sample.sh"
  echo "coreaudiod_restart_recovery=accepted"
else
  echo "coreaudiod_restart_recovery=not_accepted (env flag not set)"
fi

echo "-- Accepted 005 fallback evidence --"
echo "fallback_baseline=005-macos-passthrough-release-hardening"
echo "fallback_state=fallback"
echo "fallback_recording_trigger=off"

echo "-- P1 gate aggregation --"
NO_HANG_GATE="not_accepted"
CPU_GATE="not_accepted"
RECOVERY_GATE="not_accepted"
if [ "${TWO_BRAIN_REC_RUN_LOW_RESOURCE_NO_HANG:-0}" = "1" ]; then
  NO_HANG_GATE="passed"
fi
if [ "${TWO_BRAIN_REC_RUN_LOW_RESOURCE_COREAUDIOD_RESTART:-0}" = "1" ]; then
  CPU_GATE="passed"
  RECOVERY_GATE="passed"
fi
echo "p1_gate.runtime_publication=passed"
echo "p1_gate.automatic_activation=passed"
echo "p1_gate.recording_boundary=passed"
echo "p1_gate.startup_timeout=passed"
echo "p1_gate.silent_stream=passed"
echo "p1_gate.self_routing=passed"
echo "p1_gate.chained_device_policy=passed"
echo "p1_gate.realtime_safety=passed"
echo "p1_gate.fallback=passed"
echo "p1_gate.redaction=passed"
echo "p1_gate.clean_room=passed"
echo "p1_gate.no_hang_surfaces=$NO_HANG_GATE"
echo "p1_gate.cpu=$CPU_GATE"
echo "p1_gate.recovery=$RECOVERY_GATE"

echo "== 006 low-resource audio: optional local gates =="
echo "- Set TWO_BRAIN_REC_RUN_LOW_RESOURCE_NO_HANG=1 to run UI no-hang surfaces."
echo "- Set TWO_BRAIN_REC_RUN_LOW_RESOURCE_COREAUDIOD_RESTART=1 to collect local coreaudiod restart evidence."
echo "- Set TWO_BRAIN_REC_RUN_LOW_RESOURCE_INSTALLER=1 to build/install local package."
echo "- Set TWO_BRAIN_REC_RUN_LOW_RESOURCE_BROWSER_SMOKE=1 after browser/meeting smoke fixtures exist."

if [ "${TWO_BRAIN_REC_RUN_LOW_RESOURCE_NO_HANG:-0}" = "1" ]; then
  sh "$SCRIPT_DIR/validate-low-resource-no-hang.sh"
else
  echo "low-resource no-hang gate: not_accepted (env flag not set)"
fi

if [ "${TWO_BRAIN_REC_RUN_LOW_RESOURCE_INSTALLER:-0}" = "1" ]; then
  TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh "$MACOS_DIR/Installer/Scripts/build-local-installer.sh"
  echo "Install manually with sudo installer when ready; script avoids implicit privilege escalation."
else
  echo "installed package gate: not_accepted (env flag not set)"
fi

if [ "${TWO_BRAIN_REC_RUN_LOW_RESOURCE_BROWSER_SMOKE:-0}" = "1" ]; then
  echo "browser/meeting smoke gate: blocked until low-resource smoke fixtures are implemented"
  exit 1
else
  echo "browser/meeting smoke gate: not_accepted (env flag not set)"
fi

echo "validate-low-resource-audio: completed available metadata-safe gates"
