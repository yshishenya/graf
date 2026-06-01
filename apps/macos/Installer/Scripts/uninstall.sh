#!/usr/bin/env sh
set -eu

HAL_PATH=${2BRAIN_REC_HAL_PATH:-"/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver"}
APP_PATH=${2BRAIN_REC_APP_PATH:-"/Applications/2brain Rec.app"}
TRACE_FILE=${2BRAIN_REC_TRACE_FILE:-"/tmp/2brain-rec-driver.trace"}
REPORT_PATH=${2BRAIN_REC_UNINSTALL_REPORT:-"/var/tmp/2brain-rec-uninstall-report.json"}
RESTART_REQUIRED_FILE=${2BRAIN_REC_RESTART_REQUIRED_FILE:-"/var/tmp/2brain-rec-restart-required"}

manual_items=()
cleanup_ok=true

if [ -d "$HAL_PATH" ]; then
  if ! rm -rf "$HAL_PATH"; then
    cleanup_ok=false
    manual_items+=("- Remove driver folder manually: $HAL_PATH")
  fi
fi

if [ -d "$APP_PATH" ]; then
  if ! rm -rf "$APP_PATH"; then
    cleanup_ok=false
    manual_items+=("- Remove app bundle manually: $APP_PATH")
  fi
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
