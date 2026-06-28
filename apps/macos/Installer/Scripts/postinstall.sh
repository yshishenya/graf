#!/usr/bin/env sh
set -eu

HAL_PATH="/Library/Audio/Plug-Ins/HAL/GrafProof.driver"
LEGACY_HAL_PATH="/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver"

if [ -d "$HAL_PATH" ]; then
  xattr -cr "$HAL_PATH" || true
  xattr -dr com.apple.provenance "$HAL_PATH" || true
  xattr -dr com.apple.quarantine "$HAL_PATH" || true
fi

if [ -d "$LEGACY_HAL_PATH" ]; then
  rm -rf "$LEGACY_HAL_PATH" || true
fi

if [ "${GRAF_ALLOW_COREAUDIOD_RESTART:-${TWO_BRAIN_REC_ALLOW_COREAUDIOD_RESTART:-0}}" = "1" ]; then
  killall coreaudiod >/dev/null 2>&1 || true
else
  echo "coreaudiod restart skipped; set GRAF_ALLOW_COREAUDIOD_RESTART=1 for driver diagnostics" >&2
fi
exit 0
