#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)
NATIVE_ROOT="$REPO_ROOT/apps/macos/Native/GrafAEC3"
OUTPUT_PATH=${GRAF_AEC3_OUTPUT_PATH:-"$REPO_ROOT/apps/macos/Vendor/GrafAEC3.xcframework"}
EXPECTED_COMMIT=846fe90a289f58b7c9303a635142aa2c7caa93e5
BUILD_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/graf-aec3-build.XXXXXX")
trap 'rm -rf "$BUILD_ROOT"' EXIT HUP INT TERM

SOURCE_ROOT=${GRAF_AEC3_SOURCE_DIR:-"$BUILD_ROOT/webrtc-audio-processing-src"}
if [ -z "${GRAF_AEC3_SOURCE_DIR:-}" ]; then
  git clone --quiet --depth 1 --branch v2.1 \
    https://gitlab.freedesktop.org/pulseaudio/webrtc-audio-processing.git "$SOURCE_ROOT"
fi

ACTUAL_COMMIT=$(git -C "$SOURCE_ROOT" rev-parse HEAD)
if [ "$ACTUAL_COMMIT" != "$EXPECTED_COMMIT" ]; then
  echo "Unexpected webrtc-audio-processing commit: $ACTUAL_COMMIT" >&2
  exit 1
fi

"$SCRIPT_DIR/generate-graf-aec3-notices.sh" "$SOURCE_ROOT"

build_slice() {
  ARCH=$1
  CPU_FAMILY=$2
  BUILD_PATH="$BUILD_ROOT/build-$ARCH"
  CROSS_FILE="$BUILD_ROOT/$ARCH.ini"
  ARCHIVE_PATH="$BUILD_ROOT/libGrafAEC3-$ARCH.a"
  BRIDGE_OBJECT="$BUILD_ROOT/GrafAEC3-$ARCH.o"

  {
    echo '[binaries]'
    echo "c = ['clang', '-arch', '$ARCH', '-mmacosx-version-min=14.0']"
    echo "cpp = ['clang++', '-arch', '$ARCH', '-mmacosx-version-min=14.0']"
    echo "ar = 'ar'"
    echo "strip = 'strip'"
    echo '[host_machine]'
    echo "system = 'darwin'"
    echo "cpu_family = '$CPU_FAMILY'"
    echo "cpu = '$ARCH'"
    echo "endian = 'little'"
  } > "$CROSS_FILE"

  meson setup "$BUILD_PATH" "$SOURCE_ROOT" \
    --cross-file "$CROSS_FILE" \
    --default-library=static \
    --wrap-mode=forcefallback \
    -Db_lto=false \
    -Dbuildtype=release
  meson compile -C "$BUILD_PATH"

  clang++ -std=c++17 -O3 -fvisibility=hidden -fexceptions \
    -arch "$ARCH" -mmacosx-version-min=14.0 \
    -I"$NATIVE_ROOT/include" \
    -I"$SOURCE_ROOT/webrtc" \
    -I"$SOURCE_ROOT/subprojects/abseil-cpp-20240722.0" \
    -c "$NATIVE_ROOT/Sources/GrafAEC3.cpp" \
    -o "$BRIDGE_OBJECT"

  ZERO_AR_DATE=1 libtool -static -o "$ARCHIVE_PATH" \
    "$BRIDGE_OBJECT" \
    "$BUILD_PATH/webrtc/modules/audio_processing/libwebrtc-audio-processing-2.a"
}

build_slice arm64 aarch64
build_slice x86_64 x86_64

UNIVERSAL_ARCHIVE="$BUILD_ROOT/libGrafAEC3.a"
lipo -create \
  "$BUILD_ROOT/libGrafAEC3-arm64.a" \
  "$BUILD_ROOT/libGrafAEC3-x86_64.a" \
  -output "$UNIVERSAL_ARCHIVE"

STAGED_XCFRAMEWORK="$BUILD_ROOT/GrafAEC3.xcframework"
xcodebuild -create-xcframework \
  -library "$UNIVERSAL_ARCHIVE" \
  -headers "$NATIVE_ROOT/include" \
  -output "$STAGED_XCFRAMEWORK"

case "$OUTPUT_PATH" in
  "$REPO_ROOT"/apps/macos/Vendor/GrafAEC3.xcframework|/tmp/*) ;;
  *) echo "Refusing unexpected output path: $OUTPUT_PATH" >&2; exit 1 ;;
esac
mkdir -p "$(dirname "$OUTPUT_PATH")"
rm -rf "$OUTPUT_PATH"
mv "$STAGED_XCFRAMEWORK" "$OUTPUT_PATH"

echo "Built $OUTPUT_PATH"
lipo -archs "$OUTPUT_PATH/macos-arm64_x86_64/libGrafAEC3.a"
shasum -a 256 "$OUTPUT_PATH/macos-arm64_x86_64/libGrafAEC3.a"
