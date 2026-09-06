#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
VALIDATOR="$SCRIPT_DIR/../../Scripts/validate-packaged-app-launch.sh"
TEMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/graf-packaged-launch-test.XXXXXX")
CHILD_PID=

cleanup() {
  if [ -n "$CHILD_PID" ]; then
    kill "$CHILD_PID" 2>/dev/null || true
    wait "$CHILD_PID" 2>/dev/null || true
  fi
  rm -rf "$TEMP_ROOT"
}
trap cleanup EXIT HUP INT TERM

fail() {
  echo "packaged app launch test failed: $*" >&2
  exit 1
}

make_app() {
  name=$1
  command=$2
  app="$TEMP_ROOT/$name/GRAF.app"
  resource_dir="$app/Contents/Resources/TwoBrainRecMacOS_TwoBrainRecAppCore.bundle/Resources"
  mkdir -p "$app/Contents/MacOS" "$resource_dir"
  printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?>' \
    '<plist version="1.0"><dict><key>CFBundleExecutable</key><string>GRAF</string></dict></plist>' \
    > "$app/Contents/Info.plist"
  printf '%s\n' '#!/usr/bin/env sh' "$command" > "$app/Contents/MacOS/GRAF"
  printf '%s\n' '{}' > "$resource_dir/meeting-target-registry-baseline.json"
  chmod 755 "$app/Contents/MacOS/GRAF"
  printf '%s\n' "$app"
}

[ -x "$VALIDATOR" ] || fail "validator is missing or not executable"

living_app=$(make_app living 'printf "%s\\n" "timestamp event=app_launch_finished detail=fixture" >> "$GRAF_LOG_DIRECTORY/graf.log"; sleep 30')
"$VALIDATOR" "$living_app" 5 >/dev/null || fail "living direct child was rejected"

exiting_app=$(make_app exiting 'exit 17')
if "$VALIDATOR" "$exiting_app" 5 >/dev/null 2>&1; then
  fail "immediate exit was accepted"
fi

sleep 30 &
CHILD_PID=$!
if "$VALIDATOR" "$exiting_app" 5 >/dev/null 2>&1; then
  fail "immediate exit was accepted while another process was alive"
fi
kill -0 "$CHILD_PID" 2>/dev/null || fail "validator terminated an unrelated process"

not_ready_app=$(make_app not-ready 'sleep 30')
if "$VALIDATOR" "$not_ready_app" 5 >/dev/null 2>&1; then
  fail "candidate without startup readiness was accepted"
fi

malformed_app="$TEMP_ROOT/malformed/GRAF.app"
mkdir -p "$malformed_app/Contents"
if "$VALIDATOR" "$malformed_app" 5 >/dev/null 2>&1; then
  fail "malformed app was accepted"
fi
if "$VALIDATOR" "$living_app" 5 sparc >/dev/null 2>&1; then
  fail "unsupported architecture was accepted"
fi

echo "packaged app launch tests passed"
