#!/usr/bin/env sh
set -eu

if [ -d "/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver" ]; then
  xattr -cr "/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver" || true
  xattr -dr com.apple.provenance "/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver" || true
  xattr -dr com.apple.quarantine "/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver" || true
fi

if [ "${TWO_BRAIN_REC_ALLOW_COREAUDIOD_RESTART:-0}" = "1" ]; then
  killall coreaudiod >/dev/null 2>&1 || true
else
  echo "coreaudiod restart skipped; set TWO_BRAIN_REC_ALLOW_COREAUDIOD_RESTART=1 for driver diagnostics" >&2
fi
exit 0
