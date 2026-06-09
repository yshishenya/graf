#!/bin/sh
set -eu
export LC_ALL=C

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
EVIDENCE_DIR="$ROOT_DIR/specs/025-system-audio-capture-pivot/evidence"
DEFAULT_APP_BINARY="$ROOT_DIR/apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec"
APP_BINARY="${SYSTEM_AUDIO_CPU_GATE_APP_BINARY:-$DEFAULT_APP_BINARY}"
PHASE="${1:-}"
SAMPLES="${SYSTEM_AUDIO_CPU_GATE_SAMPLES:-3}"
INTERVAL_SECONDS="${SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS:-2}"
SETTLE_SECONDS="${SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS:-}"

case "$PHASE" in
  -h|--help|"")
    cat <<'USAGE'
sample-system-audio-cpu-gate.sh <baseline|idle|activeRecording|stop|quit>

Samples metadata-only CPU evidence for the system-audio MVP.

Environment:
  SYSTEM_AUDIO_CPU_GATE_SAMPLES=3
  SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=2
  SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=10 for baseline/idle/stop/quit, 0 for activeRecording
  SYSTEM_AUDIO_CPU_GATE_APP_BINARY=<path>
      Expected app binary to sample. Defaults to the packaged repo app bundle.
  SYSTEM_AUDIO_CPU_GATE_APP_LOG=<path>
      App log used to bind activeRecording/stop CPU evidence to fresh app-local
      recording events. Defaults to ~/Library/Logs/2brain Rec/2brain-rec.log.
  SYSTEM_AUDIO_CPU_GATE_EVENT_SINCE_EPOCH=<epoch seconds>
      Minimum event timestamp for activeRecording/stop event binding.
  SYSTEM_AUDIO_CPU_GATE_EVENT_LOG_OFFSET=<bytes>
      Log byte offset; events before this offset are ignored.
  SYSTEM_AUDIO_CPU_GATE_NO_APPEND=1 for synthetic script checks that must not
      update specs/025-system-audio-capture-pivot/evidence/cpu-gates.md

Required gates:
- idle/stop/quit after settle: coreaudiod < 5% and app+helper < 5%
- quit after settle: app/helper process count must be 0
- activeRecording/stop: expected packaged app process must be observable
- active recording: no sustained coreaudiod > 10%
- active recording: no sustained app+helper > 25%
- baseline: diagnostic only; records coreaudiod/app/helper CPU without counting
  as acceptance.
- all phases record RSS memory samples for coreaudiod, app, helper, and
  app+helper totals as metadata-only diagnostics.

This script uses ps/pgrep metadata only and must not run HAL live-publication probes.
USAGE
    [ -z "$PHASE" ] && exit 2
    exit 0
    ;;
  baseline|idle|activeRecording|stop|quit)
    ;;
  *)
    echo "error=unknown_phase phase=$PHASE" >&2
    exit 2
    ;;
esac

mkdir -p "$EVIDENCE_DIR"

if [ -z "$SETTLE_SECONDS" ]; then
  case "$PHASE" in
    activeRecording) SETTLE_SECONDS=0 ;;
    *) SETTLE_SECONDS=10 ;;
  esac
fi

cpu_sum_for_pids() {
  pids="$1"
  if [ -z "$pids" ]; then
    printf '0.00'
    return
  fi
  total="0"
  for pid in $pids; do
    value="$(ps -o %cpu= -p "$pid" 2>/dev/null | awk '{print $1}' || true)"
    [ -n "$value" ] || value="0"
    total="$(awk -v a="$total" -v b="$value" 'BEGIN { printf "%.2f", a + b }')"
  done
  printf '%s' "$total"
}

rss_sum_mb_for_pids() {
  pids="$1"
  if [ -z "$pids" ]; then
    printf '0.00'
    return
  fi
  total_kb="0"
  for pid in $pids; do
    value="$(ps -o rss= -p "$pid" 2>/dev/null | awk '{print $1}' || true)"
    [ -n "$value" ] || value="0"
    total_kb="$(awk -v a="$total_kb" -v b="$value" 'BEGIN { printf "%.0f", a + b }')"
  done
  awk -v kb="$total_kb" 'BEGIN { printf "%.2f", kb / 1024 }'
}

coreaudiod_pids() {
  pgrep -x coreaudiod 2>/dev/null || true
}

app_pids() {
  ps -axo pid=,command= |
    awk -v self="$$" -v expected="$APP_BINARY" '
      {
        pid = $1
        line = $0
        sub(/^[[:space:]]*[0-9]+[[:space:]]+/, "", line)
      }
      pid != self && (line == expected || index(line, expected " ") == 1) {
        print pid
      }
    ' || true
}

helper_pids() {
  ps -axo pid=,command= |
    awk -v self="$$" '
      $1 != self &&
      $0 ~ /(\/2brain|\/TwoBrain|\/TwoBrainRec)/ &&
      index($0, "Helper") > 0 &&
      $0 ~ /Helper$/ {
        print $1
      }
    ' || true
}

unexpected_app_pids() {
  ps -axo pid=,command= |
    awk -v self="$$" -v expected="$APP_BINARY" '
      {
        pid = $1
        line = $0
        sub(/^[[:space:]]*[0-9]+[[:space:]]+/, "", line)
      }
      pid != self &&
      line ~ /^\/.*\/2brain Rec\.app\/Contents\/MacOS\/2brain Rec([[:space:]]|$)/ &&
      !(line == expected || index(line, expected " ") == 1) {
        print pid
      }
    ' || true
}

app_log_byte_count() {
  app_log="${SYSTEM_AUDIO_CPU_GATE_APP_LOG:-$HOME/Library/Logs/2brain Rec/2brain-rec.log}"
  [ -f "$app_log" ] || {
    printf '%s' 0
    return
  }
  wc -c < "$app_log" | tr -d ' '
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
  [ "$event_epoch" -ge "$since_epoch" ] || return 1

  printf '%s\n' "$line" | grep -E "$pattern" >/dev/null 2>&1
}

app_log_has_event_since_epoch() {
  pattern="$1"
  since_epoch="${SYSTEM_AUDIO_CPU_GATE_EVENT_SINCE_EPOCH:-0}"
  log_offset="${SYSTEM_AUDIO_CPU_GATE_EVENT_LOG_OFFSET:-0}"
  app_log="${SYSTEM_AUDIO_CPU_GATE_APP_LOG:-$HOME/Library/Logs/2brain Rec/2brain-rec.log}"

  case "$since_epoch" in
    *[!0-9]*|"") since_epoch=0 ;;
  esac
  case "$log_offset" in
    *[!0-9]*|"") log_offset=0 ;;
  esac

  [ -f "$app_log" ] || return 1
  current_size="$(app_log_byte_count)"
  case "$current_size" in
    *[!0-9]*|"") current_size=0 ;;
  esac
  if [ "$current_size" -lt "$log_offset" ]; then
    log_offset=0
  fi
  start_byte=$((log_offset + 1))
  log_slice="$(mktemp)"
  tail -c +"$start_byte" "$app_log" > "$log_slice" 2>/dev/null || {
    rm -f "$log_slice"
    return 1
  }

  while IFS= read -r line; do
    if line_has_event_since_epoch "$line" "$pattern" "$since_epoch"; then
      rm -f "$log_slice"
      return 0
    fi
  done < "$log_slice"

  rm -f "$log_slice"
  return 1
}

phase_event_observed() {
  case "$PHASE" in
    activeRecording)
      if app_log_has_event_since_epoch "event=recording\\.started"; then
        printf '%s' "true"
      else
        printf '%s' "false"
      fi
      ;;
    stop)
      if app_log_has_event_since_epoch "event=(recording\\.stopped|local_recording\\.(saved|degraded|failed))"; then
        printf '%s' "true"
      else
        printf '%s' "false"
      fi
      ;;
    *)
      printf '%s' "notRequired"
      ;;
  esac
}

word_count() {
  words="$1"
  if [ -z "$words" ]; then
    printf '0'
    return
  fi
  # shellcheck disable=SC2086
  set -- $words
  printf '%s' "$#"
}

if [ "$SETTLE_SECONDS" -gt 0 ]; then
  sleep "$SETTLE_SECONDS"
fi

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT
phase_event="$(phase_event_observed)"

i=1
while [ "$i" -le "$SAMPLES" ]; do
  core_pids="$(coreaudiod_pids)"
  app_pids_value="$(app_pids)"
  helper_pids_value="$(helper_pids)"
  unexpected_app_pids_value="$(unexpected_app_pids)"
  core_cpu="$(cpu_sum_for_pids "$core_pids")"
  app_cpu="$(cpu_sum_for_pids "$app_pids_value")"
  helper_cpu="$(cpu_sum_for_pids "$helper_pids_value")"
  core_rss_mb="$(rss_sum_mb_for_pids "$core_pids")"
  app_rss_mb="$(rss_sum_mb_for_pids "$app_pids_value")"
  helper_rss_mb="$(rss_sum_mb_for_pids "$helper_pids_value")"
  app_process_count="$(word_count "$app_pids_value")"
  helper_process_count="$(word_count "$helper_pids_value")"
  unexpected_app_process_count="$(word_count "$unexpected_app_pids_value")"
  app_helper_cpu="$(awk -v a="$app_cpu" -v b="$helper_cpu" 'BEGIN { printf "%.2f", a + b }')"
  app_helper_rss_mb="$(awk -v a="$app_rss_mb" -v b="$helper_rss_mb" 'BEGIN { printf "%.2f", a + b }')"
  sampled_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  printf '%s phase=%s sample=%s coreaudiodCpuPercent=%s appCpuPercent=%s helperCpuPercent=%s appHelperCpuPercent=%s coreaudiodRssMB=%s appRssMB=%s helperRssMB=%s appHelperRssMB=%s appProcessCount=%s helperProcessCount=%s unexpectedAppProcessCount=%s halProbeObserved=false phaseEventObserved=%s\n' \
    "$sampled_at" "$PHASE" "$i" "$core_cpu" "$app_cpu" "$helper_cpu" "$app_helper_cpu" "$core_rss_mb" "$app_rss_mb" "$helper_rss_mb" "$app_helper_rss_mb" "$app_process_count" "$helper_process_count" "$unexpected_app_process_count" "$phase_event" | tee -a "$tmp_file"
  if [ "$i" -lt "$SAMPLES" ]; then
    sleep "$INTERVAL_SECONDS"
  fi
  i=$((i + 1))
done

evaluation="$(awk -v phase="$PHASE" '
BEGIN {
  maxCore = 0; maxApp = 0; maxCoreRss = 0; maxAppRss = 0; coreSeq = 0; appSeq = 0; coreSustained = 0; appSustained = 0; count = 0; maxAppProcesses = 0; maxHelperProcesses = 0; maxUnexpectedAppProcesses = 0; phaseEventObserved = 0;
}
{
  count += 1;
  core = 0; app = 0; coreRss = 0; appRss = 0; appProcesses = 0; helperProcesses = 0; unexpectedAppProcesses = 0;
  for (i = 1; i <= NF; i += 1) {
    split($i, kv, "=");
    if (kv[1] == "coreaudiodCpuPercent") core = kv[2] + 0;
    if (kv[1] == "appHelperCpuPercent") app = kv[2] + 0;
    if (kv[1] == "coreaudiodRssMB") coreRss = kv[2] + 0;
    if (kv[1] == "appHelperRssMB") appRss = kv[2] + 0;
    if (kv[1] == "appProcessCount") appProcesses = kv[2] + 0;
    if (kv[1] == "helperProcessCount") helperProcesses = kv[2] + 0;
    if (kv[1] == "unexpectedAppProcessCount") unexpectedAppProcesses = kv[2] + 0;
    if (kv[1] == "phaseEventObserved" && kv[2] == "true") phaseEventObserved = 1;
  }
  if (core > maxCore) maxCore = core;
  if (app > maxApp) maxApp = app;
  if (coreRss > maxCoreRss) maxCoreRss = coreRss;
  if (appRss > maxAppRss) maxAppRss = appRss;
  if (appProcesses > maxAppProcesses) maxAppProcesses = appProcesses;
  if (helperProcesses > maxHelperProcesses) maxHelperProcesses = helperProcesses;
  if (unexpectedAppProcesses > maxUnexpectedAppProcesses) maxUnexpectedAppProcesses = unexpectedAppProcesses;
  if (phase == "baseline") {
    next;
  } else if (phase == "activeRecording") {
    if (core > 10) coreSeq += 1; else coreSeq = 0;
    if (app > 25) appSeq += 1; else appSeq = 0;
    if (coreSeq >= 3) coreSustained = 1;
    if (appSeq >= 3) appSustained = 1;
  } else {
    if (core >= 5) coreSustained = 1;
    if (app >= 5) appSustained = 1;
  }
}
END {
  if (phase == "baseline") {
    status = count > 0 ? "observed" : "failed";
  } else {
    status = (count >= 3 && coreSustained == 0 && appSustained == 0) ? "passed" : "failed";
    if ((phase == "idle" || phase == "activeRecording" || phase == "stop") && maxAppProcesses == 0) {
      status = "failed";
    }
    if (maxUnexpectedAppProcesses > 0) {
      status = "failed";
    }
    if (phase == "quit" && (maxAppProcesses > 0 || maxHelperProcesses > 0 || maxUnexpectedAppProcesses > 0)) {
      status = "failed";
    }
  }
  reason = status == "passed" ? "none" : "cpuGateFailed";
  if (phase != "baseline" && status == "failed" && count < 3) {
    reason = "insufficientSamples";
  }
  if ((phase == "idle" || phase == "activeRecording" || phase == "stop") && status == "failed" && maxAppProcesses == 0) {
    reason = "appNotRunning";
  }
  if (status == "failed" && maxUnexpectedAppProcesses > 0) {
    reason = "unexpectedAppProcessRunning";
  }
  if (phase == "quit" && status == "failed" && (maxAppProcesses > 0 || maxHelperProcesses > 0 || maxUnexpectedAppProcesses > 0)) {
    reason = "appStillRunning";
  }
  if (status == "observed") reason = "diagnosticOnly";
  phaseEventValue = (phase == "activeRecording" || phase == "stop") ? (phaseEventObserved ? "true" : "false") : "notRequired";
  printf "status=%s failureReason=%s sampleCount=%d maxCoreaudiodCpuPercent=%.2f maxAppHelperCpuPercent=%.2f maxCoreaudiodRssMB=%.2f maxAppHelperRssMB=%.2f maxAppProcessCount=%d maxHelperProcessCount=%d maxUnexpectedAppProcessCount=%d sustainedCoreaudiodExceeded=%s sustainedAppHelperExceeded=%s phaseEventObserved=%s", status, reason, count, maxCore, maxApp, maxCoreRss, maxAppRss, maxAppProcesses, maxHelperProcesses, maxUnexpectedAppProcesses, coreSustained ? "true" : "false", appSustained ? "true" : "false", phaseEventValue;
}' "$tmp_file")"

printf '%s\n' "$evaluation"

if [ "${SYSTEM_AUDIO_CPU_GATE_NO_APPEND:-0}" != "1" ]; then
  {
    printf '\n## %s %s\n\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$PHASE"
    printf '%s\n' "- Command: \`$0 $PHASE\`"
    printf '%s\n' "- App binary: \`$APP_BINARY\`"
    printf '%s\n' "- Samples: \`$SAMPLES\`, interval seconds: \`$INTERVAL_SECONDS\`, settle seconds: \`$SETTLE_SECONDS\`"
    printf '%s\n\n' "- Evaluation: \`$evaluation\`"
    printf '```text\n'
    cat "$tmp_file"
    printf '```\n'
  } >> "$EVIDENCE_DIR/cpu-gates.md"
fi

case "$evaluation" in
  status=passed*) exit 0 ;;
  status=observed*) exit 0 ;;
  *) exit 1 ;;
esac
