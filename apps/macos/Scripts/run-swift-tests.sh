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

# One worker keeps execution sequential while SwiftPM starts a fresh XCTest
# process for every discovered case, including the WebKit runtime tests.
swift test --package-path apps/macos --parallel --num-workers 1 --skip-build
