#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <webrtc-audio-processing-source>" >&2
  exit 2
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)
SOURCE_ROOT=$1
NOTICE_PATH="$REPO_ROOT/apps/macos/RecApp/Resources/AEC3-THIRD-PARTY-NOTICES.txt"

append_notice() {
  TITLE=$1
  RELATIVE_PATH=$2
  LICENSE_PATH="$SOURCE_ROOT/$RELATIVE_PATH"
  [ -f "$LICENSE_PATH" ] || {
    echo "missing AEC3 license input: $RELATIVE_PATH" >&2
    exit 1
  }
  {
    printf '\n======================================================================\n%s\nSource: %s\n======================================================================\n\n' "$TITLE" "$RELATIVE_PATH"
    sed -n 'p' "$LICENSE_PATH"
  } >> "$NOTICE_PATH"
}

printf '%s\n' \
  'GRAF AEC3 Third-Party Notices' \
  'Pinned source: webrtc-audio-processing v2.1 / WebRTC M131' \
  'Commit: 846fe90a289f58b7c9303a635142aa2c7caa93e5' \
  'This file is generated from the exact locked upstream license inputs.' \
  > "$NOTICE_PATH"

append_notice 'webrtc-audio-processing' 'COPYING'
append_notice 'WebRTC' 'webrtc/LICENSE'
append_notice 'WebRTC patent grant' 'webrtc/PATENTS'
append_notice 'Abseil' 'subprojects/abseil-cpp-20240722.0/LICENSE'
append_notice 'Ooura FFT' 'webrtc/common_audio/third_party/ooura/LICENSE'
append_notice 'spl_sqrt_floor' 'webrtc/common_audio/third_party/spl_sqrt_floor/LICENSE'
append_notice 'WebRTC FFT' 'webrtc/modules/third_party/fft/LICENSE'
append_notice 'PFFFT' 'webrtc/third_party/pffft/LICENSE'
append_notice 'RNNoise' 'webrtc/third_party/rnnoise/COPYING'

echo "Generated $NOTICE_PATH"
