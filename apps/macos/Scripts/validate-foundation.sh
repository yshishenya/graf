#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(CDPATH= cd -- "$MACOS_DIR/../.." && pwd)

swift build --package-path "$MACOS_DIR"
(cd "$REPO_ROOT" && swift run --package-path apps/macos ContractValidation)
"$SCRIPT_DIR/validate-no-legacy-audio-driver.sh"
