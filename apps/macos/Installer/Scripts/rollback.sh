#!/usr/bin/env sh
set -eu

HAL_PATH=${GRAF_HAL_PATH:-"/Library/Audio/Plug-Ins/HAL/GrafProof.driver"}
BACKUP_DIR=${GRAF_DRIVER_BACKUP_DIR:-"/var/tmp/graf-driver-backups"}
REPORT_PATH=${GRAF_ROLLBACK_REPORT:-"/var/tmp/graf-rollback-report.json"}

echo "rollback-start"

mkdir -p "$BACKUP_DIR"
restore_path=""

if [ -d "$HAL_PATH" ]; then
  rm -rf "$HAL_PATH"
fi

if latest_backup="$(ls -1dt "$BACKUP_DIR"/GrafProof.driver.* 2>/dev/null | head -n 1)"; then
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
