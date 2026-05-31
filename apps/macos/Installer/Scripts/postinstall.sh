#!/usr/bin/env sh
set -eu

if [ -d "/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver" ]; then
  xattr -cr "/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver" || true
  xattr -dr com.apple.provenance "/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver" || true
  xattr -dr com.apple.quarantine "/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver" || true
fi

killall coreaudiod >/dev/null 2>&1 || true
exit 0
