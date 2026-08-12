#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

swift build --package-path "$MACOS_DIR"
if ! TEST_OUTPUT=$(swift test --package-path "$MACOS_DIR" 2>&1); then
  if echo "$TEST_OUTPUT" | rg -q "lib_TestingInterop|no such module 'XCTest'"; then
    echo "swift test is temporarily unavailable in this runtime (missing Xcode/Swift Testing runtime)." >&2
    echo "Skipping unit tests to keep headless regression flow executable." >&2
    echo "Set GRAF_STRICT_TESTS=1 to fail this step on missing runtime libraries." >&2
    echo "$TEST_OUTPUT" >&2
  else
    echo "$TEST_OUTPUT" >&2
    exit 1
  fi
else
  echo "$TEST_OUTPUT"
fi

swift run --package-path "$MACOS_DIR" ContractValidation
echo "Legacy virtual-driver runtime and route probes are retired from the US1 regression lane."
if [ -f "$MACOS_DIR/Installer/Packages/graf.pkgproj" ]; then
  xmllint --noout "$MACOS_DIR/Installer/Packages/graf.pkgproj"
else
  sh -n "$MACOS_DIR/Installer/Scripts/build-local-installer.sh"
fi
sh "$SCRIPT_DIR/validate-us1-gate.sh"

if [ "${GRAF_STRICT_TESTS:-${TWO_BRAIN_STRICT_TESTS:-0}}" = "1" ] && echo "$TEST_OUTPUT" | rg -q "lib_TestingInterop|no such module 'XCTest'"; then
  exit 1
fi
