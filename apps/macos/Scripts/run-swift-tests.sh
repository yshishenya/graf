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

# WebKit owns helper processes outside XCTest. Keep all cases in one sequential
# XCTest process so retained browser objects cover the complete test run.
swift test --package-path apps/macos --skip-build
