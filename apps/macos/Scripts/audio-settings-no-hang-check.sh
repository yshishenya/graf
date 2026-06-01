#!/usr/bin/env sh
set -eu

RUN_UI=${TWO_BRAIN_REC_RUN_UI_NO_HANG:-0}
TIMEOUT_SECONDS=${TIMEOUT_SECONDS:-5}

emit_metadata_only() {
  target=$1
  reason=$2
  echo "target_surface=$target"
  echo "opened_within_seconds=not_run"
  echo "route_state_before=unknown"
  echo "route_state_after=unknown"
  echo "result=not_accepted"
  echo "failure_reason=$reason"
}

open_target() {
  target=$1
  case "$target" in
    macos-sound)
      open "x-apple.systempreferences:com.apple.Sound-Settings.extension" >/dev/null 2>&1 || open -b com.apple.SystemSettings >/dev/null 2>&1
      ;;
    chrome)
      open -a "Google Chrome" "chrome://settings/content/microphone" >/dev/null 2>&1
      ;;
    opera)
      open -a "Opera" "opera://settings/content/microphone" >/dev/null 2>&1
      ;;
    zoom)
      open -a "zoom.us" >/dev/null 2>&1
      ;;
    telemost)
      open "https://telemost.yandex.ru/" >/dev/null 2>&1
      ;;
    *)
      echo "Unknown target: $target" >&2
      exit 64
      ;;
  esac
}

target=${1:-all}

if [ "$target" = "--list" ]; then
  printf '%s\n' macos-sound chrome opera zoom telemost
  exit 0
fi

if [ "$target" = "all" ]; then
  for item in macos-sound chrome opera zoom telemost; do
    "$0" "$item"
  done
  exit 0
fi

if [ "$RUN_UI" != "1" ]; then
  emit_metadata_only "$target" "ui_launch_disabled_set_TWO_BRAIN_REC_RUN_UI_NO_HANG_1"
  exit 0
fi

start=$(date +%s)
if ! open_target "$target"; then
  emit_metadata_only "$target" "target_unavailable_or_failed_to_open"
  exit 0
fi

elapsed=$(( $(date +%s) - start ))
echo "target_surface=$target"
echo "opened_within_seconds=$elapsed"
echo "timeout_seconds=$TIMEOUT_SECONDS"
echo "route_state_before=unknown"
echo "route_state_after=unknown"
if [ "$elapsed" -le "$TIMEOUT_SECONDS" ]; then
  echo "result=passed"
  echo "failure_reason=none"
else
  echo "result=blocked"
  echo "failure_reason=opened_after_threshold"
  exit 2
fi
