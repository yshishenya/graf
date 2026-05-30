#!/usr/bin/env sh
set -eu

HAL_SRC=${2BRAIN_REC_HAL_SOURCE:-"/Library/Audio/Plug-Ins/HAL/.2brain-rec-driver-staged/2brainRecProof.driver"}
HAL_DEST=${2BRAIN_REC_HAL_PATH:-"/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver"}
STATE_PATH=${2BRAIN_REC_INSTALLER_STATE:-"/var/tmp/2brain-rec-installer-state"}
REPORT_PATH=${2BRAIN_REC_REPAIR_REPORT:-"/var/tmp/2brain-rec-repair-report.json"}

mkdir -p "/Library/Audio/Plug-Ins/HAL"
mkdir -p "$(dirname "$REPORT_PATH")"
mkdir -p "$(dirname "$STATE_PATH")"

if [ -e "$HAL_DEST" ]; then
  rm -rf "$HAL_DEST"
fi

if [ -d "$HAL_SRC" ]; then
  cp -R "$HAL_SRC" "$HAL_DEST"
else
  echo "repair-failed: staged component not found at $HAL_SRC" >&2
  cat > "$REPORT_PATH" <<EOF
{
  "operation": "repair",
  "result": "partial",
  "halSource": "$HAL_SRC",
  "halDestination": "$HAL_DEST",
  "state": "cannot_find_source"
}
EOF
  exit 1
fi

xattr -cr "$HAL_DEST" || true
killall coreaudiod >/dev/null 2>&1 || true
echo "repaired" > "$STATE_PATH"

cat > "$REPORT_PATH" <<EOF
{
  "operation": "repair",
  "result": "succeeded",
  "halSource": "$HAL_SRC",
  "halDestination": "$HAL_DEST",
  "state": "updated"
}
EOF

echo "repair-succeeded"
exit 0
