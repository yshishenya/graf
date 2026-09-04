#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$repo_root"

# A full run must not inherit SwiftPM's hidden test-skip override.
unset _SWIFTPM_SKIP_TESTS_LIST

test_list="$(swift test --package-path apps/macos list)"
if [[ -z "$test_list" ]]; then
  printf 'macOS Swift tests: no tests discovered\n' >&2
  exit 1
fi

# Temporary exact-SHA probe: isolate the stalled fixture test and capture its
# stack instead of waiting for the outer job timeout. This branch is not merged.
test_filter='TwoBrainRecSharedTests.MicrophoneSampleGraphContractTests/testManifestFixtureWithMicrophoneStreamMetadataDecodesWithoutRawAudio'
NSUnbufferedIO=YES swift test --package-path apps/macos --skip-build --filter "$test_filter" &
swift_pid=$!

deadline=$((SECONDS + 60))
while kill -0 "$swift_pid" 2>/dev/null; do
  if (( SECONDS >= deadline )); then
    printf 'fixture_probe=watchdog_timeout\n' >&2
    for test_pid in $(pgrep -f 'TwoBrainRecMacOSPackageTests.xctest' || true); do
      sample_file="${RUNNER_TEMP:-/tmp}/graf-xctest-${test_pid}.sample.txt"
      /usr/bin/sample "$test_pid" 3 1 -file "$sample_file" || true
      sed -n '1,260p' "$sample_file" || true
      kill -TERM "$test_pid" 2>/dev/null || true
    done
    kill -TERM "$swift_pid" 2>/dev/null || true
    wait "$swift_pid" || true
    exit 124
  fi
  sleep 1
done

wait "$swift_pid"
