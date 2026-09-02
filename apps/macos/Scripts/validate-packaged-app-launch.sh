#!/usr/bin/env sh
set -eu

fail() {
  echo "packaged app launch validation failed: $*" >&2
  exit 1
}

[ "$#" -ge 1 ] && [ "$#" -le 3 ] ||
  fail "usage: $0 /absolute/path/GRAF.app [minimum-seconds] [native|arm64|x86_64]"

APP_BUNDLE=$1
MINIMUM_SECONDS=${2:-5}
ARCHITECTURE=${3:-native}
case "$APP_BUNDLE" in
  /*/GRAF.app) ;;
  *) fail "candidate must be an absolute GRAF.app path" ;;
esac
case "$MINIMUM_SECONDS" in
  ''|*[!0-9]*) fail "minimum seconds must be an integer of at least 5" ;;
esac
[ "$MINIMUM_SECONDS" -ge 5 ] || fail "minimum seconds must be at least 5"
case "$ARCHITECTURE" in
  native|arm64|x86_64) ;;
  *) fail "architecture must be native, arm64 or x86_64" ;;
esac

INFO_PLIST="$APP_BUNDLE/Contents/Info.plist"
[ -f "$INFO_PLIST" ] || fail "candidate Info.plist is missing"
EXECUTABLE=$(/usr/bin/plutil -extract CFBundleExecutable raw -o - "$INFO_PLIST" 2>/dev/null) ||
  fail "candidate executable metadata is invalid"
[ "$EXECUTABLE" = "GRAF" ] || fail "candidate executable must be GRAF"
BINARY="$APP_BUNDLE/Contents/MacOS/$EXECUTABLE"
[ -x "$BINARY" ] || fail "candidate binary is missing or not executable"
BASELINE="$APP_BUNDLE/Contents/Resources/TwoBrainRecMacOS_TwoBrainRecAppCore.bundle/Resources/meeting-target-registry-baseline.json"
[ -f "$BASELINE" ] || fail "candidate target registry baseline is missing"

RUNTIME_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/graf-packaged-launch.XXXXXX")
CHILD_PID=
cleanup() {
  if [ -n "$CHILD_PID" ] && kill -0 "$CHILD_PID" 2>/dev/null; then
    kill "$CHILD_PID" 2>/dev/null || true
    attempts=0
    while kill -0 "$CHILD_PID" 2>/dev/null && [ "$attempts" -lt 50 ]; do
      sleep 0.1
      attempts=$((attempts + 1))
    done
    kill -9 "$CHILD_PID" 2>/dev/null || true
  fi
  [ -z "$CHILD_PID" ] || wait "$CHILD_PID" 2>/dev/null || true
  rm -rf "$RUNTIME_ROOT"
}
trap cleanup EXIT HUP INT TERM
LOG_DIRECTORY="$RUNTIME_ROOT/logs"
mkdir -p "$RUNTIME_ROOT/home" "$LOG_DIRECTORY"

if [ "$ARCHITECTURE" = native ]; then
  HOME="$RUNTIME_ROOT/home" \
  GRAF_LOG_DIRECTORY="$LOG_DIRECTORY" \
  GRAF_CABINET_BASE_URL=http://127.0.0.1:9 \
  GRAF_CABINET_REQUIRE_EXPLICIT_BASE_URL=1 \
  GRAF_UPLOAD_BASE_URL=http://127.0.0.1:9 \
  GRAF_UPLOAD_REQUIRE_EXPLICIT_BASE_URL=1 \
    "$BINARY" >/dev/null 2>&1 &
else
  HOME="$RUNTIME_ROOT/home" \
  GRAF_LOG_DIRECTORY="$LOG_DIRECTORY" \
  GRAF_CABINET_BASE_URL=http://127.0.0.1:9 \
  GRAF_CABINET_REQUIRE_EXPLICIT_BASE_URL=1 \
  GRAF_UPLOAD_BASE_URL=http://127.0.0.1:9 \
  GRAF_UPLOAD_REQUIRE_EXPLICIT_BASE_URL=1 \
    /usr/bin/arch "-$ARCHITECTURE" "$BINARY" >/dev/null 2>&1 &
fi
CHILD_PID=$!

sleep "$MINIMUM_SECONDS"
kill -0 "$CHILD_PID" 2>/dev/null || {
  wait "$CHILD_PID" 2>/dev/null || true
  fail "candidate process exited before ${MINIMUM_SECONDS}s"
}

printf 'packaged_app_launch=pass minimum_seconds=%s architecture=%s child_pid_owned=yes\n' "$MINIMUM_SECONDS" "$ARCHITECTURE"
