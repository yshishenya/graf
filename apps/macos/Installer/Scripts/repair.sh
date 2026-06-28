#!/usr/bin/env sh
set -eu

HAL_SRC=${GRAF_HAL_SOURCE:-"/Library/Audio/Plug-Ins/HAL/.graf-driver-staged/GrafProof.driver"}
HAL_DEST=${GRAF_HAL_PATH:-"/Library/Audio/Plug-Ins/HAL/GrafProof.driver"}
STATE_PATH=${GRAF_INSTALLER_STATE:-"/var/tmp/graf-installer-state"}
REPORT_PATH=${GRAF_REPAIR_REPORT:-"/var/tmp/graf-repair-report.json"}

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
xattr -dr com.apple.provenance "$HAL_DEST" || true
xattr -dr com.apple.quarantine "$HAL_DEST" || true
if [ "${GRAF_ALLOW_COREAUDIOD_RESTART:-${TWO_BRAIN_REC_ALLOW_COREAUDIOD_RESTART:-0}}" = "1" ]; then
  killall coreaudiod >/dev/null 2>&1 || true
else
  echo "coreaudiod restart skipped; set GRAF_ALLOW_COREAUDIOD_RESTART=1 for driver diagnostics" >&2
fi
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
