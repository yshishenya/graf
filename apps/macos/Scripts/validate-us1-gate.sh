#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPORT="$MACOS_DIR/AudioDriver/RuntimeProofReport.md"

sh "$SCRIPT_DIR/validate-foundation.sh"

STATUS_LINE=$(grep -m 1 -F '**Status**:' "$REPORT" || true)
case "$STATUS_LINE" in
  "**Status**: ACCEPTED"*) ;;
  *)
  echo "US1 gate blocked: RuntimeProofReport.md status is not ACCEPTED." >&2
  echo "Run the Apple Silicon Core Audio runtime proof and record evidence before US1 implementation." >&2
  exit 1
  ;;
esac

echo "US1 publication gate accepted: $STATUS_LINE"
