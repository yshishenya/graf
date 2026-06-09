#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
MACOS_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(CDPATH= cd -- "$MACOS_DIR/../.." && pwd)"
APP_BUNDLE="$MACOS_DIR/RecApp/.build/2brain Rec.app"
APP_BINARY="$APP_BUNDLE/Contents/MacOS/2brain Rec"

usage() {
  cat <<'USAGE'
run-system-audio-controlled-manual-gate.sh

Guided metadata-only harness for the manual system-audio MVP gates.

It builds and launches the app-only local package, then prompts the tester to
press Record/Stop manually. It does not click UI, does not start recording by
itself, does not inspect audio content, does not reset TCC, does not install the
pkg, and does not run HAL probes.

Steps performed:
  1. verify default local package is app-only;
  2. record baseline CPU;
  3. launch the packaged app bundle from the repo and verify the app process;
  4. wait for the tester to press Record with controlled non-sensitive audio
     after the app shows recording is active;
  5. record activeRecording CPU;
  6. wait for the tester to press Stop and for local recording status to settle;
  7. record stop CPU;
  8. validate the newest local recording artifact metadata-only, limited to
     artifacts modified after this harness started;
  9. print the exact remaining evidence files to update.

Environment:
  SYSTEM_AUDIO_MANUAL_GATE_SKIP_ARTIFACT=1
      Skip latest artifact validation. Use only for permission/blocker rows
      where no accepted artifact is expected.
USAGE
}

prompt_continue() {
  message="$1"
  printf '\n%s\n' "$message"
  printf '%s' "Press Enter to continue, or Ctrl-C to stop: "
  # shellcheck disable=SC2034
  read answer
}

app_process_count() {
  ps -axo command= |
    awk -v expected="$APP_BINARY" '
      $0 == expected || index($0, expected " ") == 1 { count += 1 }
      END { print count + 0 }
    '
}

wait_for_app_launch() {
  remaining=15
  while [ "$remaining" -gt 0 ]; do
    if [ "$(app_process_count)" -gt 0 ]; then
      printf '%s\n' "app_launch=observed processCount=$(app_process_count)"
      return 0
    fi
    sleep 1
    remaining=$((remaining - 1))
  done
  printf '%s\n' "app_launch=blocked reason=app_process_not_observed bundle=$APP_BUNDLE" >&2
  exit 2
}

case "${1:-}" in
  -h|--help)
    usage
    exit 0
    ;;
  "")
    ;;
  *)
    printf '%s\n' "unknown argument: $1" >&2
    usage >&2
    exit 64
    ;;
esac

cd "$ROOT_DIR"

printf '%s\n' "== system-audio controlled manual gate =="
printf '%s\n' "repo=$ROOT_DIR"
manual_gate_started_epoch="$(date +%s)"
export SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME="$manual_gate_started_epoch"
printf '%s\n' "artifact_min_mtime_epoch=$manual_gate_started_epoch"

printf '\n%s\n' "-- app-only package boundary --"
apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only

printf '\n%s\n' "-- baseline CPU before launch --"
apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline

printf '\n%s\n' "-- launch packaged app bundle --"
[ -d "$APP_BUNDLE" ] || {
  printf '%s\n' "app_launch=blocked reason=missing_app_bundle bundle=$APP_BUNDLE" >&2
  exit 2
}
pkill -x "2brain Rec" 2>/dev/null || true
open -n "$APP_BUNDLE"
wait_for_app_launch

prompt_continue "Start a controlled non-sensitive audio source, press Record System Audio in 2brain Rec, and wait until the app shows recording is active."

printf '\n%s\n' "-- activeRecording CPU while recording is active --"
apps/macos/Scripts/sample-system-audio-cpu-gate.sh activeRecording

prompt_continue "Press Stop in 2brain Rec and wait until the recording status settles and the local recording status is visible."

printf '\n%s\n' "-- stop CPU immediately after Stop --"
apps/macos/Scripts/sample-system-audio-cpu-gate.sh stop

if [ "${SYSTEM_AUDIO_MANUAL_GATE_SKIP_ARTIFACT:-0}" != "1" ]; then
  printf '\n%s\n' "-- latest artifact directory --"
  apps/macos/Scripts/validate-system-audio-capture-pivot.sh --latest-artifact-directory

  printf '\n%s\n' "-- latest artifact metadata validation --"
  apps/macos/Scripts/validate-system-audio-capture-pivot.sh --validate-latest-artifact
else
  printf '\n%s\n' "-- latest artifact validation skipped by SYSTEM_AUDIO_MANUAL_GATE_SKIP_ARTIFACT=1 --"
fi

printf '\n%s\n' "-- next evidence updates --"
printf '%s\n' "Update only metadata in:"
printf '%s\n' "- specs/025-system-audio-capture-pivot/evidence/permission-matrix.md"
printf '%s\n' "- specs/025-system-audio-capture-pivot/evidence/artifact-matrix.md"
printf '%s\n' "- specs/025-system-audio-capture-pivot/evidence/cpu-gates.md"
printf '%s\n' "Do not paste raw audio, transcripts, meeting content, credentials, tokens, signed URLs, or personal details."

printf '\n%s\n' "manual_gate=completed_available_steps"
