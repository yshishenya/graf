#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

sh "$SCRIPT_DIR/validate-foundation.sh"
echo "US1 gate accepted: native system-audio app-only universal installer validated"
