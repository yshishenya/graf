#!/usr/bin/env sh
set -eu

HAL_PATH=${GRAF_HAL_PATH:-"/Library/Audio/Plug-Ins/HAL/GrafProof.driver"}
APP_PATH=${GRAF_APP_PATH:-"/Applications/GRAF.app"}
TRACE_FILE=${GRAF_TRACE_FILE:-"/tmp/graf-driver.trace"}
REPORT_PATH=${GRAF_UNINSTALL_REPORT:-"/var/tmp/graf-uninstall-report.json"}
RESTART_REQUIRED_FILE=${GRAF_RESTART_REQUIRED_FILE:-"/var/tmp/graf-restart-required"}
LEGACY_HAL_PATH=${GRAF_LEGACY_HAL_PATH:-"/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver"}
LEGACY_APP_PATH=${GRAF_LEGACY_APP_PATH:-"/Applications/2brain Rec.app"}

manual_items=()
cleanup_ok=true

if [ -d "$HAL_PATH" ]; then
  if ! rm -rf "$HAL_PATH"; then
    cleanup_ok=false
    manual_items+=("- Remove driver folder manually: $HAL_PATH")
  fi
fi
if [ -d "$LEGACY_HAL_PATH" ]; then
  rm -rf "$LEGACY_HAL_PATH" || true
fi

if [ -d "$APP_PATH" ]; then
  if ! rm -rf "$APP_PATH"; then
    cleanup_ok=false
    manual_items+=("- Remove app bundle manually: $APP_PATH")
  fi
fi
if [ -d "$LEGACY_APP_PATH" ]; then
  rm -rf "$LEGACY_APP_PATH" || true
fi

if [ -f "$TRACE_FILE" ]; then
  rm -f "$TRACE_FILE" || true
fi

rm -f "$RESTART_REQUIRED_FILE" || true
xattr -cr "/Library/Audio/Plug-Ins/HAL" 2>/dev/null || true

if [ "$cleanup_ok" = false ]; then
  manual_json="$(printf '%s\n' "${manual_items[@]}" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk 'NF{print "\"" $0 "\""}' | paste -sd, -)"
  echo "uninstall-partial"
  cat > "$REPORT_PATH" <<EOF
{
  "result": "partial",
  "manualCleanupRequired": true,
  "manualCleanup": [${manual_json}]
}
EOF
  exit 1
fi

cat > "$REPORT_PATH" <<EOF
{
  "result": "succeeded",
  "manualCleanupRequired": false
}
EOF
echo "uninstall-succeeded"
exit 0
