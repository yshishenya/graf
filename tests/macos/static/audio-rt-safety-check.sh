#!/usr/bin/env sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
BRIDGE_FILE="$REPO_ROOT/apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift"
TMP_DIR="${TMPDIR:-/tmp}/2brain-rec-rt-safety"
mkdir -p "$TMP_DIR"

extract_callback() {
  callback_name="$1"
  awk -v callback="$callback_name" '
    $0 ~ "private let " callback ": AURenderCallback" { in_callback = 1 }
    in_callback { print }
    in_callback && /^}$/ { exit }
  ' "$BRIDGE_FILE"
}

MIC_CALLBACK="$TMP_DIR/mic-callback.swift"
SPEAKER_CALLBACK="$TMP_DIR/speaker-callback.swift"
extract_callback "micInputCallback" > "$MIC_CALLBACK"
extract_callback "speakerRenderCallback" > "$SPEAKER_CALLBACK"

failures=0

check_forbidden() {
  file="$1"
  pattern="$2"
  description="$3"
  if rg -n "$pattern" "$file" >/tmp/2brain-rec-rt-safety-match.txt 2>/dev/null; then
    echo "RT safety violation: $description" >&2
    cat /tmp/2brain-rec-rt-safety-match.txt >&2
    failures=$((failures + 1))
  fi
}

for callback_file in "$MIC_CALLBACK" "$SPEAKER_CALLBACK"; do
  check_forbidden "$callback_file" '\[Float\]\(repeating:' "heap allocation in AudioUnit callback"
  check_forbidden "$callback_file" 'bridgeLog\(' "file/string logging in AudioUnit callback"
  check_forbidden "$callback_file" 'Date\(' "wall-clock access in AudioUnit callback"
  check_forbidden "$callback_file" 'String\(format:' "string formatting in AudioUnit callback"
  check_forbidden "$callback_file" 'open\(|write\(|close\(' "file I/O in AudioUnit callback"
  check_forbidden "$callback_file" 'callbackErrorCount|micCallbackCount|speakerCallbackCount|micDropCount|speakerUnderrunCount' "non-atomic Swift counter mutation in AudioUnit callback"
done

if [ "$failures" -ne 0 ]; then
  echo "audio-rt-safety-check: BLOCKED ($failures violations)" >&2
  exit 1
fi

echo "audio-rt-safety-check: ACCEPTED"
