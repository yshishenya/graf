#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
MACOS_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(CDPATH= cd -- "$MACOS_DIR/../.." && pwd)"
APP_BUNDLE="$MACOS_DIR/RecApp/.build/2brain Rec.app"
APP_BINARY="$APP_BUNDLE/Contents/MacOS/2brain Rec"
APP_LOG="$HOME/Library/Logs/2brain Rec/2brain-rec.log"

usage() {
  cat <<'USAGE'
run-system-audio-controlled-manual-gate.sh [--preflight]

Guided metadata-only harness for the manual system-audio MVP gates.

It builds and launches the app-only local package, then prompts the tester to
press Record/Stop manually. It does not click UI, does not start recording by
itself, does not inspect audio content, does not reset TCC, does not install the
pkg, and does not run HAL probes.

Options:
  --preflight
      Run only the non-recording safety preflight: app-only package boundary,
      packaged app launch, idle CPU, quit CPU, and thermal-state printout. This
      mode never prompts for Record/Stop and never satisfies the active
      recording, artifact, permission, 30-minute, or 75-minute acceptance gates.

Steps performed:
  1. verify default local package is app-only;
  2. record baseline CPU;
  3. launch the packaged app bundle from the repo and verify the app process;
  4. wait for the tester to press Record with controlled non-sensitive audio
     and for a fresh app-local recording.started log event;
  5. record activeRecording CPU;
  6. wait for the tester to press Stop and for a fresh app-local stop/local
     recording log event;
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

line_has_event_since_epoch() {
  line="$1"
  pattern="$2"
  since_epoch="$3"

  case "$line" in
    *" event="*) ;;
    *) return 1 ;;
  esac

  timestamp="${line%% event=*}"
  event_epoch="$(date -j -u -f "%Y-%m-%dT%H:%M:%SZ" "$timestamp" "+%s" 2>/dev/null || printf '%s' 0)"
  if [ "$event_epoch" -lt "$since_epoch" ]; then
    return 1
  fi

  printf '%s\n' "$line" | grep -E "$pattern" >/dev/null 2>&1
}

app_log_has_event_since_epoch() {
  pattern="$1"
  since_epoch="$2"

  [ -f "$APP_LOG" ] || return 1

  while IFS= read -r line; do
    if line_has_event_since_epoch "$line" "$pattern" "$since_epoch"; then
      printf '%s\n' "$line"
      return 0
    fi
  done < "$APP_LOG"

  return 1
}

wait_for_app_log_event_since_epoch() {
  pattern="$1"
  since_epoch="$2"
  label="$3"
  timeout_seconds="${4:-20}"

  printf '%s\n' "waiting_for_$label=started log=$APP_LOG sinceEpoch=$since_epoch timeoutSeconds=$timeout_seconds"

  remaining="$timeout_seconds"
  while [ "$remaining" -gt 0 ]; do
    if matched_line="$(app_log_has_event_since_epoch "$pattern" "$since_epoch")"; then
      printf '%s\n' "waiting_for_$label=observed line=$matched_line"
      return 0
    fi
    sleep 1
    remaining=$((remaining - 1))
  done

  printf '%s\n' "waiting_for_$label=blocked reason=app_log_event_not_observed log=$APP_LOG pattern=$pattern sinceEpoch=$since_epoch timeoutSeconds=$timeout_seconds" >&2
  exit 2
}

quit_app() {
  if [ "$(app_process_count)" -eq 0 ]; then
    return 0
  fi
  osascript -e 'tell application "2brain Rec" to quit' >/dev/null 2>&1 || true
  remaining=10
  while [ "$remaining" -gt 0 ]; do
    if [ "$(app_process_count)" -eq 0 ]; then
      return 0
    fi
    sleep 1
    remaining=$((remaining - 1))
  done
  pkill -x "2brain Rec" 2>/dev/null || true
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

run_app_only_package_boundary() {
  printf '\n%s\n' "-- app-only package boundary --"
  apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only
}

run_baseline_cpu() {
  printf '\n%s\n' "-- baseline CPU before launch --"
  apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline
}

launch_packaged_app() {
  printf '\n%s\n' "-- launch packaged app bundle --"
  [ -d "$APP_BUNDLE" ] || {
    printf '%s\n' "app_launch=blocked reason=missing_app_bundle bundle=$APP_BUNDLE" >&2
    exit 2
  }
  quit_app
  open -n "$APP_BUNDLE"
  wait_for_app_launch
}

run_preflight() {
  printf '\n%s\n' "-- idle CPU with packaged app running, no recording --"
  SYSTEM_AUDIO_CPU_GATE_NO_APPEND=1 \
  SYSTEM_AUDIO_CPU_GATE_SAMPLES="${SYSTEM_AUDIO_PREFLIGHT_CPU_SAMPLES:-3}" \
  SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS="${SYSTEM_AUDIO_PREFLIGHT_CPU_INTERVAL_SECONDS:-2}" \
  SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS="${SYSTEM_AUDIO_PREFLIGHT_CPU_SETTLE_SECONDS:-5}" \
    apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle

  printf '\n%s\n' "-- quit packaged app --"
  quit_app

  printf '\n%s\n' "-- quit CPU after packaged app exit --"
  SYSTEM_AUDIO_CPU_GATE_NO_APPEND=1 \
  SYSTEM_AUDIO_CPU_GATE_SAMPLES="${SYSTEM_AUDIO_PREFLIGHT_CPU_SAMPLES:-3}" \
  SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS="${SYSTEM_AUDIO_PREFLIGHT_CPU_INTERVAL_SECONDS:-2}" \
  SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS="${SYSTEM_AUDIO_PREFLIGHT_QUIT_SETTLE_SECONDS:-5}" \
    apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit

  printf '\n%s\n' "-- thermal state --"
  pmset -g therm || true

  printf '\n%s\n' "manual_gate_preflight=passed"
  printf '%s\n' "preflight_scope=non_recording_only"
  printf '%s\n' "remaining_manual_gates=permission_matrix,controlled_artifact,activeRecording_cpu,stop_cpu,30_minute,75_minute,final_review"
}

MODE="${1:-}"
case "${1:-}" in
  -h|--help)
    usage
    exit 0
    ;;
  --preflight)
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

run_app_only_package_boundary
run_baseline_cpu
launch_packaged_app

if [ "$MODE" = "--preflight" ]; then
  run_preflight
  exit 0
fi

record_prompt_epoch="$(date +%s)"
prompt_continue "Start a controlled non-sensitive audio source, press Record System Audio in 2brain Rec, and wait until the app shows recording is active."
wait_for_app_log_event_since_epoch "event=recording\\.started" "$record_prompt_epoch" "recording_started"

printf '\n%s\n' "-- activeRecording CPU while recording is active --"
apps/macos/Scripts/sample-system-audio-cpu-gate.sh activeRecording

stop_prompt_epoch="$(date +%s)"
prompt_continue "Press Stop in 2brain Rec and wait until the recording status settles and the local recording status is visible."
wait_for_app_log_event_since_epoch "event=(recording\\.stopped|local_recording\\.(saved|degraded|failed))" "$stop_prompt_epoch" "recording_stopped_or_saved"

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
