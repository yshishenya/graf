#!/usr/bin/env sh
set -eu

fail() {
  echo "packaged app launch validation failed: $*" >&2
  exit 1
}

check_readiness_log() {
  [ -f "$LOG_DIRECTORY/graf.log" ] || fail "candidate did not create its startup log"
  grep -Eq '(^|[[:space:]])event=app_launch_finished([[:space:]]|$)' "$LOG_DIRECTORY/graf.log" ||
    fail "candidate did not emit the startup launch marker"
  grep -Eq '(^|[[:space:]])event=app_main_window_presented([[:space:]]|$)' "$LOG_DIRECTORY/graf.log" ||
    fail "candidate did not emit the startup readiness marker: main window was never presented"
}

# Internal read-only observer. Only dev-harness owns launch/quit and fresh logs.
# This branch cannot launch a Dev binary or terminate an installed process.
if [ "${1:-}" = --observe-installed-dev ]; then
  [ "$#" -eq 3 ] || fail "installed Dev observation requires identity and fresh log directory"
  EXPECTED_IDENTITY=$2
  LOG_DIRECTORY=$3
  case "$EXPECTED_IDENTITY" in
    ''|*[!0-9.:]*) fail "invalid Dev process identity" ;;
  esac
  DEV_PID=${EXPECTED_IDENTITY%%:*}
  case "$DEV_PID" in ''|*[!0-9]*) fail "invalid Dev pid" ;; esac
  [ "$DEV_PID" -gt 1 ] || fail "invalid Dev pid"
  LIFECYCLE=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)/dev-app-lifecycle.swift
  observed=$(swift "$LIFECYCLE" identity "/Applications/GRAF Dev.app") ||
    fail "installed Dev process is unavailable or ambiguous"
  [ "$observed" = "$EXPECTED_IDENTITY" ] || fail "installed Dev process identity changed"
  attempts=0
  while [ "$attempts" -lt 50 ]; do
    kill -0 "$DEV_PID" 2>/dev/null || fail "installed Dev exited before 5s"
    state=$(ps -p "$DEV_PID" -o stat=) || fail "installed Dev exited before 5s"
    case "$state" in ''|*Z*) fail "installed Dev is not live" ;; esac
    sleep 0.1
    attempts=$((attempts + 1))
  done
  observed=$(swift "$LIFECYCLE" identity "/Applications/GRAF Dev.app") ||
    fail "installed Dev process is unavailable or ambiguous"
  [ "$observed" = "$EXPECTED_IDENTITY" ] || fail "installed Dev process identity changed"
  check_readiness_log
  printf 'packaged_app_launch=pass minimum_seconds=5 architecture=native lifecycle=dev-harness\n'
  exit 0
fi

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
APPLICATION_SUPPORT_DIRECTORY="$RUNTIME_ROOT/application-support"
mkdir -p "$RUNTIME_ROOT/home" "$LOG_DIRECTORY" "$APPLICATION_SUPPORT_DIRECTORY"

if [ "$ARCHITECTURE" = native ]; then
  HOME="$RUNTIME_ROOT/home" \
  GRAF_LOG_DIRECTORY="$LOG_DIRECTORY" \
  GRAF_APPLICATION_SUPPORT_DIRECTORY="$APPLICATION_SUPPORT_DIRECTORY" \
  GRAF_CABINET_BASE_URL=http://127.0.0.1:9 \
  GRAF_CABINET_REQUIRE_EXPLICIT_BASE_URL=1 \
  GRAF_UPLOAD_BASE_URL=http://127.0.0.1:9 \
  GRAF_UPLOAD_REQUIRE_EXPLICIT_BASE_URL=1 \
    "$BINARY" >/dev/null 2>&1 &
else
  HOME="$RUNTIME_ROOT/home" \
  GRAF_LOG_DIRECTORY="$LOG_DIRECTORY" \
  GRAF_APPLICATION_SUPPORT_DIRECTORY="$APPLICATION_SUPPORT_DIRECTORY" \
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
check_readiness_log

printf 'packaged_app_launch=pass minimum_seconds=%s architecture=%s child_pid_owned=yes\n' "$MINIMUM_SECONDS" "$ARCHITECTURE"
