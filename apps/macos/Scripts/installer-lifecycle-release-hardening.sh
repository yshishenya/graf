#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(CDPATH= cd -- "$MACOS_DIR/../.." && pwd)
RUN_LIFECYCLE=${GRAF_RUN_INSTALLER_LIFECYCLE:-${TWO_BRAIN_REC_RUN_INSTALLER_LIFECYCLE:-0}}
ALLOW_COREAUDIOD_RESTART=${GRAF_ALLOW_COREAUDIOD_RESTART:-${TWO_BRAIN_REC_ALLOW_COREAUDIOD_RESTART:-0}}
OPERATION=${1:-all}

emit_not_accepted() {
  operation=$1
  reason=$2
  echo "operation=$operation"
  echo "pre_state=unknown"
  echo "post_state=unknown"
  echo "core_audio_refresh_required=true"
  echo "runtime_probe_result=not_run"
  echo "result=not_accepted"
  echo "failure_reason=$reason"
}

run_probe() {
  make -C "$MACOS_DIR/AudioDriver" proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe
}

restart_coreaudiod_for_driver_diagnostics() {
  if [ "$ALLOW_COREAUDIOD_RESTART" = "1" ]; then
    sudo killall coreaudiod || true
  else
    echo "coreaudiod_restart=skipped set_GRAF_ALLOW_COREAUDIOD_RESTART_1_for_driver_diagnostics"
  fi
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
        GRAF_INCLUDE_DRIVER_COMPONENT=1 \
        sh "$MACOS_DIR/Installer/Scripts/build-local-installer.sh"
      sudo installer -pkg "$MACOS_DIR/.build/installer/graf-local.pkg" -target /
      restart_coreaudiod_for_driver_diagnostics
      run_probe
      ;;
    repair)
      sudo sh "$MACOS_DIR/Installer/Scripts/repair.sh"
      run_probe
      ;;
    rollback)
      sudo sh "$MACOS_DIR/Installer/Scripts/rollback.sh" || true
      run_probe || true
      ;;
    uninstall)
      sudo sh "$MACOS_DIR/Installer/Scripts/uninstall.sh"
      restart_coreaudiod_for_driver_diagnostics
      make -C "$MACOS_DIR/AudioDriver" proof-runtime-probe-run && {
        echo "result=blocked"
        echo "failure_reason=virtual_devices_still_visible_after_uninstall"
        return 2
      }
      echo "result=passed"
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
