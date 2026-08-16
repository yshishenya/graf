#!/usr/bin/env sh
set -eu
ROOT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/../../.." && pwd)
LOCAL_ORIGIN="${GRAF_LOCAL_ORIGIN:-http://127.0.0.1:8081}"
case "$LOCAL_ORIGIN" in http://127.0.0.1:*|http://localhost:*) ;; *) echo "GRAF_LOCAL_ORIGIN must be loopback HTTP" >&2; exit 1 ;; esac
export GRAF_CABINET_BASE_URL="$LOCAL_ORIGIN"
export GRAF_UPLOAD_BASE_URL="$LOCAL_ORIGIN"
export GRAF_CABINET_REQUIRE_EXPLICIT_BASE_URL=1
export GRAF_UPLOAD_REQUIRE_EXPLICIT_BASE_URL=1
export GRAF_LOCAL_APP=1
cd "$ROOT_DIR"
exec swift run --package-path apps/macos TwoBrainRecApp
