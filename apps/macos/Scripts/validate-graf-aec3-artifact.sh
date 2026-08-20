#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)
NATIVE_ROOT="$REPO_ROOT/apps/macos/Native/GrafAEC3"
XCFRAMEWORK="$REPO_ROOT/apps/macos/Vendor/GrafAEC3.xcframework"
ARCHIVE="$XCFRAMEWORK/macos-arm64_x86_64/libGrafAEC3.a"
HEADERS="$XCFRAMEWORK/macos-arm64_x86_64/Headers"
VALIDATION_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/graf-aec3-validate.XXXXXX")
trap 'rm -rf "$VALIDATION_ROOT"' EXIT HUP INT TERM

fail() {
  echo "graf-aec3 validation failed: $*" >&2
  exit 1
}

[ -f "$ARCHIVE" ] || fail "missing static archive"
[ -f "$HEADERS/GrafAEC3.h" ] || fail "missing public header"
[ -f "$HEADERS/module.modulemap" ] || fail "missing module map"

EXPECTED_HASH=$(sed -n 's/^artifact_sha256=//p' "$NATIVE_ROOT/upstream.lock")
ACTUAL_HASH=$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')
[ -n "$EXPECTED_HASH" ] || fail "artifact hash is absent from lock"
[ "$ACTUAL_HASH" = "$EXPECTED_HASH" ] || fail "artifact hash mismatch"

ARCHES=$(lipo -archs "$ARCHIVE" | tr ' ' '\n' | sort | tr '\n' ' ' | sed 's/ $//')
[ "$ARCHES" = "arm64 x86_64" ] || fail "unexpected architectures: $ARCHES"

plutil -extract AvailableLibraries.0.LibraryIdentifier raw "$XCFRAMEWORK/Info.plist" | \
  grep -qx 'macos-arm64_x86_64' || fail "unexpected XCFramework library identifier"
plutil -extract AvailableLibraries.0.SupportedPlatform raw "$XCFRAMEWORK/Info.plist" | \
  grep -qx 'macos' || fail "unexpected XCFramework platform"

for SYMBOL in create process get_statistics destroy library_version source_commit optional_processing_enabled; do
  nm -gU "$ARCHIVE" | grep -q "_graf_aec3_$SYMBOL$" || fail "missing C symbol graf_aec3_$SYMBOL"
done
grep -q 'config.echo_canceller.enabled = true' "$NATIVE_ROOT/Sources/GrafAEC3.cpp" || fail "AEC is not enabled"
grep -q 'config.echo_canceller.enforce_high_pass_filtering = false' "$NATIVE_ROOT/Sources/GrafAEC3.cpp" || fail "AEC high-pass is not disabled"
for DISABLED in high_pass_filter noise_suppression gain_controller1 gain_controller2 transient_suppression; do
  grep -q "config.$DISABLED.enabled = false" "$NATIVE_ROOT/Sources/GrafAEC3.cpp" || fail "$DISABLED is not explicitly disabled"
done

{
  echo '#include "GrafAEC3.h"'
  echo '#include <stdio.h>'
  echo 'int main(void) {'
  echo '  float render[GRAF_AEC3_FRAME_SAMPLES] = {0};'
  echo '  float capture[GRAF_AEC3_FRAME_SAMPLES] = {0};'
  echo '  float output[GRAF_AEC3_FRAME_SAMPLES] = {0};'
  echo '  GrafAEC3Processor *processor = graf_aec3_create();'
  echo '  if (!processor) return 10;'
  echo '  if (graf_aec3_optional_processing_enabled() != 0) return 11;'
  echo '  if (graf_aec3_process(processor, render, capture, GRAF_AEC3_FRAME_SAMPLES, 0, output) != GRAF_AEC3_OK) return 12;'
  echo '  graf_aec3_destroy(processor);'
  echo '  puts(graf_aec3_library_version());'
  echo '  return 0;'
  echo '}'
} > "$VALIDATION_ROOT/smoke.cpp"

build_smoke() {
  ARCH=$1
  OUTPUT="$VALIDATION_ROOT/smoke-$ARCH"
  clang++ -std=c++17 -arch "$ARCH" -mmacosx-version-min=14.0 \
    -I"$HEADERS" "$VALIDATION_ROOT/smoke.cpp" "$ARCHIVE" \
    -framework CoreFoundation -o "$OUTPUT"
  if otool -L "$OUTPUT" | grep -Eiq 'webrtc|absl'; then
    fail "$ARCH smoke has dynamic WebRTC/Abseil dependency"
  fi
}

build_smoke arm64
build_smoke x86_64

if [ "$(uname -m)" = "arm64" ]; then
  "$VALIDATION_ROOT/smoke-arm64" | grep -qx '2.1' || fail "arm64 smoke failed"
  if arch -x86_64 /usr/bin/true >/dev/null 2>&1; then
    arch -x86_64 "$VALIDATION_ROOT/smoke-x86_64" | grep -qx '2.1' || fail "x86_64 Rosetta smoke failed"
    echo "graf-aec3 x86_64 Rosetta smoke: PASS"
  else
    echo "graf-aec3 x86_64 Rosetta smoke: SKIP (Rosetta unavailable)"
  fi
fi

echo "graf-aec3 artifact validation: PASS"
echo "graf-aec3 artifact sha256: $ACTUAL_HASH"
echo "graf-aec3 architectures: $ARCHES"
