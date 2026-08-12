#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(CDPATH= cd -- "$MACOS_DIR/../.." && pwd)
RUN_LIFECYCLE=${GRAF_RUN_INSTALLER_LIFECYCLE:-${TWO_BRAIN_REC_RUN_INSTALLER_LIFECYCLE:-0}}
OPERATION=${1:-all}

emit_not_accepted() {
  operation=$1
  reason=$2
  echo "operation=$operation"
  echo "pre_state=unknown"
  echo "post_state=unknown"
  echo "core_audio_refresh_required=false"
  echo "runtime_probe_result=not_applicable"
  echo "result=not_accepted"
  echo "failure_reason=$reason"
}

run_operation() {
  operation=$1
  if [ "$RUN_LIFECYCLE" != "1" ]; then
    emit_not_accepted "$operation" "destructive_installer_lifecycle_disabled_set_GRAF_RUN_INSTALLER_LIFECYCLE_1"
    return 0
  fi

  case "$operation" in
    install|update|reinstall)
      GRAF_ALLOW_ADHOC_APP_SIGNING=1 \
        sh "$MACOS_DIR/Installer/Scripts/build-local-installer.sh"
      sudo installer -pkg "$MACOS_DIR/.build/installer/graf.pkg" -target /
      ;;
    repair)
      emit_not_accepted "$operation" "retired_virtual_driver_lifecycle"
      ;;
    rollback)
      emit_not_accepted "$operation" "retired_virtual_driver_lifecycle"
      ;;
    uninstall)
      emit_not_accepted "$operation" "retired_virtual_driver_lifecycle"
      ;;
    *)
      echo "Unknown lifecycle operation: $operation" >&2
      exit 64
      ;;
  esac
}

if [ "$OPERATION" = "--list" ]; then
  printf '%s\n' install update repair rollback uninstall reinstall
  exit 0
fi

if [ "$OPERATION" = "all" ]; then
  for operation in install update repair rollback uninstall reinstall; do
    run_operation "$operation"
  done
  exit 0
fi

run_operation "$OPERATION"
