#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
MACOS_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(CDPATH= cd -- "$MACOS_DIR/../.." && pwd)"
APP_BUNDLE="$MACOS_DIR/RecApp/.build/2brain Rec.app"
APP_BINARY="$APP_BUNDLE/Contents/MacOS/2brain Rec"
APP_LOG="${SYSTEM_AUDIO_MANUAL_GATE_APP_LOG:-$HOME/Library/Logs/2brain Rec/2brain-rec.log}"

usage() {
  cat <<'USAGE'
run-system-audio-controlled-manual-gate.sh [--preflight]

Guided metadata-only harness for the manual system-audio MVP gates.

It builds and launches the app-only local package, then prompts the tester to
press Record/Stop manually. It does not click UI, does not start recording by
itself, does not inspect audio content, does not reset TCC, does not install the
pkg, and does not run HAL probes. It holds a local caffeinate assertion during
the run so sleep/wake gaps cannot masquerade as app responsiveness or CPU
evidence.

Options:
  --preflight
      Run only the non-recording safety preflight: app-only package boundary,
      packaged app launch, idle CPU, quit CPU, and thermal-state printout. This
      mode never prompts for Record/Stop and never satisfies the active
      recording, artifact, permission, 30-minute, or 75-minute acceptance gates.
  --self-test
      Run metadata-only harness parser checks against a temporary log file. This
      does not build, launch, record, install, inspect audio, or touch TCC.

Steps performed:
  1. verify default local package is app-only;
  2. record baseline CPU;
  3. launch the packaged app bundle from the repo and verify the app process;
  4. wait for the tester to press Record with controlled non-sensitive audio
     and for a fresh app-local recording.started log event appended after the
     prompt begins;
  5. record activeRecording CPU;
  6. wait for the tester to press Stop and for a fresh app-local stop/local
     recording log event appended after the prompt begins;
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

app_log_byte_count() {
  [ -f "$APP_LOG" ] || {
    printf '%s' 0
    return
  }
  wc -c < "$APP_LOG" | tr -d ' '
}

app_log_has_event_since_epoch() {
  pattern="$1"
  since_epoch="$2"
  log_offset="${3:-0}"

  [ -f "$APP_LOG" ] || return 1
  current_size="$(app_log_byte_count)"
  case "$log_offset" in
    *[!0-9]*|"") log_offset=0 ;;
  esac
  case "$current_size" in
    *[!0-9]*|"") current_size=0 ;;
  esac
  if [ "$current_size" -lt "$log_offset" ]; then
    log_offset=0
  fi
  start_byte=$((log_offset + 1))
  log_slice="$(mktemp)"
  tail -c +"$start_byte" "$APP_LOG" > "$log_slice" 2>/dev/null || {
    rm -f "$log_slice"
    return 1
  }

  while IFS= read -r line; do
    if line_has_event_since_epoch "$line" "$pattern" "$since_epoch"; then
      printf '%s\n' "$line"
      rm -f "$log_slice"
      return 0
    fi
  done < "$log_slice"

  rm -f "$log_slice"
  return 1
}

wait_for_app_log_event_since_epoch() {
  pattern="$1"
  since_epoch="$2"
  label="$3"
  timeout_seconds="${4:-20}"
  log_offset="${5:-0}"

  printf '%s\n' "waiting_for_$label=started log=$APP_LOG sinceEpoch=$since_epoch logOffsetBytes=$log_offset timeoutSeconds=$timeout_seconds"

  remaining="$timeout_seconds"
  while [ "$remaining" -gt 0 ]; do
    if matched_line="$(app_log_has_event_since_epoch "$pattern" "$since_epoch" "$log_offset")"; then
      printf '%s\n' "waiting_for_$label=observed line=$matched_line"
      return 0
    fi
    sleep 1
    remaining=$((remaining - 1))
  done

  printf '%s\n' "waiting_for_$label=blocked reason=app_log_event_not_observed log=$APP_LOG pattern=$pattern sinceEpoch=$since_epoch logOffsetBytes=$log_offset timeoutSeconds=$timeout_seconds" >&2
  exit 2
}

block_if_app_log_event_since_epoch() {
  pattern="$1"
  since_epoch="$2"
  label="$3"
  log_offset="${4:-0}"

  if matched_line="$(app_log_has_event_since_epoch "$pattern" "$since_epoch" "$log_offset")"; then
    printf '%s\n' "waiting_for_$label=blocked reason=unexpected_app_log_event_observed line=$matched_line" >&2
    exit 2
  fi
}

run_self_test() {
  original_app_log="$APP_LOG"
  temp_log="$(mktemp)"
  trap 'rm -f "$temp_log"' EXIT
  APP_LOG="$temp_log"

  printf '2026-06-09T04:00:00Z event=recording.started detail=old\n' >> "$APP_LOG"
  old_offset="$(app_log_byte_count)"
  printf '2026-06-09T04:10:00Z event=recording.started detail=fresh\n' >> "$APP_LOG"
  printf '2026-06-09T04:10:01Z event=recording.stopped detail=fresh\n' >> "$APP_LOG"

  app_log_has_event_since_epoch "event=recording\\.started" 1780978200 "$old_offset" >/dev/null ||
    fail_self_test "fresh recording.started event was not found after offset"

  if app_log_has_event_since_epoch "event=recording\\.started" 0 "$old_offset" | grep -F "detail=old" >/dev/null 2>&1; then
    fail_self_test "stale recording.started event was accepted before offset"
  fi

  if ( block_if_app_log_event_since_epoch "event=recording\\.stopped" 1780978200 "self_test_stop_block" "$old_offset" ) >/dev/null 2>&1; then
    fail_self_test "unexpected recording.stopped event did not block"
  fi

  apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-artifact-metadata >/dev/null ||
    fail_self_test "artifact metadata validator self-test failed"
  apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-duration-evidence >/dev/null ||
    fail_self_test "duration evidence validator self-test failed"
  apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-permission-evidence >/dev/null ||
    fail_self_test "permission evidence validator self-test failed"

  APP_LOG="$original_app_log"
  printf '%s\n' "manual_gate_self_test=passed"
}

fail_self_test() {
  printf '%s\n' "manual_gate_self_test=failed reason=$1" >&2
  exit 1
}

caffeinate_pid=""

stop_caffeinate() {
  if [ -n "$caffeinate_pid" ]; then
    kill "$caffeinate_pid" >/dev/null 2>&1 || true
    wait "$caffeinate_pid" >/dev/null 2>&1 || true
    caffeinate_pid=""
  fi
}

start_caffeinate() {
  if ! command -v caffeinate >/dev/null 2>&1; then
    printf '%s\n' "wake_assertion=blocked reason=missing_caffeinate command=caffeinate" >&2
    exit 2
  fi
  caffeinate -dimsu -w "$$" >/dev/null 2>&1 &
  caffeinate_pid="$!"
  trap 'stop_caffeinate' EXIT
  printf '%s\n' "wake_assertion=held command=caffeinate flags=-dimsu pid=$caffeinate_pid"
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
  SYSTEM_AUDIO_CPU_GATE_SAMPLES="${SYSTEM_AUDIO_PREFLIGHT_CPU_SAMPLES:-3}" \
  SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS="${SYSTEM_AUDIO_PREFLIGHT_CPU_INTERVAL_SECONDS:-2}" \
  SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS="${SYSTEM_AUDIO_PREFLIGHT_CPU_SETTLE_SECONDS:-5}" \
    apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle

  printf '\n%s\n' "-- quit packaged app --"
  quit_app

  printf '\n%s\n' "-- quit CPU after packaged app exit --"
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
  --self-test)
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

if [ "$MODE" = "--self-test" ]; then
  run_self_test
  exit 0
fi

printf '%s\n' "== system-audio controlled manual gate =="
printf '%s\n' "repo=$ROOT_DIR"
manual_gate_started_epoch="$(date +%s)"
export SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME="$manual_gate_started_epoch"
printf '%s\n' "artifact_min_mtime_epoch=$manual_gate_started_epoch"
start_caffeinate

run_app_only_package_boundary
run_baseline_cpu
launch_packaged_app

if [ "$MODE" = "--preflight" ]; then
  run_preflight
  exit 0
fi

record_prompt_epoch="$(date +%s)"
record_prompt_log_offset="$(app_log_byte_count)"
prompt_continue "Start a controlled non-sensitive audio source, press Record System Audio in 2brain Rec, and wait until the app shows recording is active."
wait_for_app_log_event_since_epoch "event=recording\\.started" "$record_prompt_epoch" "recording_started" 20 "$record_prompt_log_offset"
block_if_app_log_event_since_epoch "event=(recording\\.stopped|local_recording\\.(saved|degraded|failed))" "$record_prompt_epoch" "recording_still_active_before_cpu" "$record_prompt_log_offset"

printf '\n%s\n' "-- activeRecording CPU while recording is active --"
active_cpu_epoch="$(date +%s)"
active_cpu_log_offset="$(app_log_byte_count)"
apps/macos/Scripts/sample-system-audio-cpu-gate.sh activeRecording
block_if_app_log_event_since_epoch "event=(recording\\.stopped|local_recording\\.(saved|degraded|failed))" "$active_cpu_epoch" "recording_still_active_after_cpu" "$active_cpu_log_offset"

stop_prompt_epoch="$(date +%s)"
stop_prompt_log_offset="$(app_log_byte_count)"
prompt_continue "Press Stop in 2brain Rec and wait until the recording status settles and the local recording status is visible."
wait_for_app_log_event_since_epoch "event=(recording\\.stopped|local_recording\\.(saved|degraded|failed))" "$stop_prompt_epoch" "recording_stopped_or_saved" 20 "$stop_prompt_log_offset"

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
