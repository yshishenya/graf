#!/usr/bin/env sh
set -eu

HAL_PATH=${2BRAIN_REC_HAL_PATH:-"/Library/Audio/Plug-Ins/HAL/2brainRecProof.driver"}
BACKUP_DIR=${2BRAIN_REC_DRIVER_BACKUP_DIR:-"/var/tmp/2brain-rec-driver-backups"}
REPORT_PATH=${2BRAIN_REC_ROLLBACK_REPORT:-"/var/tmp/2brain-rec-rollback-report.json"}

echo "rollback-start"

mkdir -p "$BACKUP_DIR"
restore_path=""

if [ -d "$HAL_PATH" ]; then
  rm -rf "$HAL_PATH"
fi

if latest_backup="$(ls -1dt "$BACKUP_DIR"/2brainRecProof.driver.* 2>/dev/null | head -n 1)"; then
  restore_path="$latest_backup"
  cp -R "$latest_backup" "$HAL_PATH"
fi

if [ -d "$HAL_PATH" ]; then
  result="succeeded"
else
  result="partial"
fi

cat > "$REPORT_PATH" <<EOF
{
  "operation": "rollback",
  "result": "$result",
  "restoreSource": "${restore_path:-none}",
  "halPath": "$HAL_PATH"
}
EOF

if [ "$result" = "succeeded" ]; then
  echo "rollback-succeeded"
  exit 0
fi

echo "rollback-partial: no backup found or restore failed. Manual remediation may be required."
exit 1
