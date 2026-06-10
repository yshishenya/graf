#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
EVIDENCE_DIR="$ROOT_DIR/specs/025-system-audio-capture-pivot/evidence"
PERMISSION_MATRIX="$EVIDENCE_DIR/permission-matrix.md"
ARTIFACT_MATRIX="$EVIDENCE_DIR/artifact-matrix.md"
DEV_DURATION="$EVIDENCE_DIR/development-30-minute.md"
RELEASE_DURATION="$EVIDENCE_DIR/release-75-minute.md"
CPU_GATES="$EVIDENCE_DIR/cpu-gates.md"
NO_HAL="$EVIDENCE_DIR/no-hal-probe.md"
SCOPE_REVIEW="$EVIDENCE_DIR/scope-review.md"
DRIVER_PARKED="$EVIDENCE_DIR/driver-parked.md"

usage() {
    cat <<'USAGE'
validate-system-audio-capture-pivot.sh

Metadata-only validation helper for feature 025. It does not start recording,
does not inspect audio content, does not run HAL probes, and does not reset TCC.

Modes:
  --permission-matrix
      Check permission evidence structure and record a metadata-only validator
      run. Returns blocked while required matrix rows remain not-tested.

  --artifact-matrix
      Check controlled artifact evidence structure. Returns blocked while
      required artifact rows remain not-tested.

  --artifact-directory <path>
      Validate a completed local recording directory metadata-only. Requires
      manifest.json, mic.wav, incoming.wav, saved dual-track manifest,
      systemAudio incoming metadata, granted permissions, scope approval, no
      external egress, no transcription, and durationDifferenceSeconds <= 3.

  --latest-artifact-directory
      Print the newest completed local recording directory containing
      manifest.json, mic.wav, and incoming.wav. Uses
      TWO_BRAIN_REC_RECORDINGS_DIR when set; otherwise uses the app's default
      ~/Library/Application Support/2brain Rec/Recordings directory.
      When SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME is set to an epoch
      second, older completed directories are ignored.

  --validate-latest-artifact
      Find the newest completed local recording directory and validate it with
      the same metadata-only contract as --artifact-directory.

  --duration-minutes 30
      Check the 30-minute development evidence file.

  --duration-minutes 75 --manual-release
      Check the 75-minute manual release evidence file.

  --installer-app-only
      Build the default local package and verify it contains only the desktop
      app component, with no audio-driver package references. This is
      metadata-only and does not install the package.

  --review-evidence
      Check final evidence readiness across permission, artifact, CPU,
      no-HAL, duration, and scope review files.

  --self-test-cpu-evidence
      Run synthetic CPU evidence parser regression checks. Does not read or
      update real evidence files.

  --self-test-artifact-metadata
      Run synthetic metadata-only artifact validator checks against temporary
      manifest/WAV files. Does not read real recordings, inspect audio content,
      update evidence files, start recording, or touch TCC.

  --self-test-latest-artifact-selection
      Run synthetic latest-artifact selection checks against temporary
      recording directories. Does not read real recordings or update evidence
      files.

  --self-test-duration-evidence
      Run synthetic duration evidence parser checks against a temporary
      markdown table. Does not read or update real evidence files.

  --self-test-permission-evidence
      Run synthetic permission matrix parser checks against a temporary
      markdown table. Does not read or update real evidence files.

  --self-test-review-evidence
      Run synthetic final review marker parser checks against temporary
      markdown files. Does not read or update real evidence files.

Exit codes:
  0 passed
  2 blocked / not accepted yet
  3 invalid invocation or missing required evidence file
USAGE
}

now_utc() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

commit_sha() {
    git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || printf "unknown"
}

macos_version() {
    sw_vers -productVersion 2>/dev/null || printf "unknown"
}

hardware_model() {
    sysctl -n hw.model 2>/dev/null || printf "unknown"
}

fail_invalid() {
    printf '%s\n' "system_audio_capture_pivot_validation=invalid"
    printf '%s\n' "reason=$1"
    exit 3
}

blocked() {
    printf '%s\n' "system_audio_capture_pivot_validation=blocked"
    printf '%s\n' "reason=$1"
    exit 2
}

passed() {
    printf '%s\n' "system_audio_capture_pivot_validation=passed"
    printf '%s\n' "detail=$1"
    exit 0
}

require_file() {
    path="$1"
    [ -f "$path" ] || fail_invalid "missing required evidence file: $path"
}

append_run_header() {
    path="$1"
    header_title="$2"
    {
        printf '\n## %s\n\n' "$header_title"
        printf -- '- Run ID: `%s`\n' "$(date -u +%Y%m%dT%H%M%SZ)"
        printf -- '- Timestamp: `%s`\n' "$(now_utc)"
        printf -- '- Commit: `%s`\n' "$(commit_sha)"
        printf -- '- macOS: `%s`\n' "$(macos_version)"
        printf -- '- Hardware: `%s`\n' "$(hardware_model)"
    } >> "$path"
}

recordings_root() {
    printf '%s\n' "${TWO_BRAIN_REC_RECORDINGS_DIR:-$HOME/Library/Application Support/2brain Rec/Recordings}"
}

file_mtime() {
    path="$1"
    mtime="$(stat -f "%m" "$path" 2>/dev/null || printf '0')"
    case "$mtime" in
        *[!0-9]*|"") mtime=0 ;;
    esac
    printf '%s\n' "$mtime"
}

latest_completed_artifact_directory() {
    root="$(recordings_root)"
    [ -d "$root" ] || blocked "recordings directory does not exist: $root"
    min_mtime="${SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME:-0}"
    case "$min_mtime" in
        *[!0-9]*|"") fail_invalid "SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME must be epoch seconds" ;;
    esac

    latest_directory=""
    latest_mtime=""
    for directory in "$root"/*; do
        [ -d "$directory" ] || continue
        [ -f "$directory/manifest.json" ] || continue
        [ -f "$directory/mic.wav" ] || continue
        [ -f "$directory/incoming.wav" ] || continue

        manifest_mtime="$(file_mtime "$directory/manifest.json")"
        mic_mtime="$(file_mtime "$directory/mic.wav")"
        incoming_mtime="$(file_mtime "$directory/incoming.wav")"
        [ "$manifest_mtime" -ge "$min_mtime" ] || continue
        [ "$mic_mtime" -ge "$min_mtime" ] || continue
        [ "$incoming_mtime" -ge "$min_mtime" ] || continue
        mtime="$manifest_mtime"
        if [ -z "$latest_mtime" ] || [ "$mtime" -gt "$latest_mtime" ]; then
            latest_mtime="$mtime"
            latest_directory="$directory"
        fi
    done

    [ -n "$latest_directory" ] ||
        blocked "no completed local recording directories with manifest.json, mic.wav, and incoming.wav all modified after epoch: $min_mtime under: $root"

    printf '%s\n' "$latest_directory"
}

count_not_tested_rows() {
    path="$1"
    grep -c '| not-tested |' "$path" 2>/dev/null || true
}

has_exact_line() {
    path="$1"
    expected="$2"
    grep -Fx -- "$expected" "$path" >/dev/null 2>&1
}

has_exact_line_after_header() {
    path="$1"
    header="$2"
    expected="$3"
    awk -v header="$header" -v expected="$expected" '
        $0 == header {
            in_section = 1
            next
        }
        in_section && /^## / {
            in_section = 0
        }
        in_section && $0 == expected {
            found = 1
        }
        END {
            exit(found ? 0 : 1)
        }
    ' "$path"
}

count_accepted_permission_rows() {
    path="$1"
    awk -F '|' '
        BEGIN { count = 0 }
        /^\|/ && $2 !~ /Microphone/ && $2 !~ /---/ {
            for (i = 1; i <= NF; i += 1) {
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", $i)
            }
            key = $2 "||" $3
            result = $7
            if (result != "passed") {
                next
            }
            if (key == "granted||granted" ||
                key == "denied||granted" ||
                key == "granted||denied/restricted/unknown" ||
                key == "denied||denied/restricted/unknown" ||
                key == "permission revoked while recording||any required permission missing") {
                accepted[key] = 1
            }
        }
        END {
            for (key in accepted) {
                count += 1
            }
            print count + 0
        }
    ' "$path"
}

count_accepted_artifact_rows() {
    path="$1"
    awk -F '|' '
        BEGIN { count = 0 }
        /^\|/ && $2 !~ /Case/ && $2 !~ /---/ {
            for (i = 1; i <= NF; i += 1) {
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", $i)
            }
            case_name = $2
            result = $6
            if (result != "passed") {
                next
            }
            if (case_name == "Both microphone and system audio present" ||
                case_name == "Microphone present, incoming/system audio silent" ||
                case_name == "Incoming/system audio present, microphone missing" ||
                case_name == "Protected or blocked incoming/system audio" ||
                case_name == "Misaligned tracks") {
                accepted[case_name] = 1
            }
        }
        END {
            for (case_name in accepted) {
                count += 1
            }
            print count + 0
        }
    ' "$path"
}

has_controlled_artifact_acceptance() {
    path="$1"
    has_exact_line_after_header "$path" "## 2026-06-10 Controlled Artifact Acceptance" "- Decision: accepted for T072 / issue #308." &&
        has_exact_line_after_header "$path" "## 2026-06-10 Controlled Artifact Acceptance" '- Result: `passed`' &&
        has_exact_line_after_header "$path" "## 2026-06-10 Controlled Artifact Acceptance" '- Manifest status: `saved`'
}

has_manual_cpu_acceptance_caveat() {
    path="$1"
    has_exact_line_after_header "$path" "## 2026-06-10 Manual CPU Gate Acceptance With Caveat" "- Decision: accepted-with-caveat for T073 / issue #309 by product owner." &&
        rg -F "Telemost was left open during the manual stop gate" "$path" >/dev/null &&
        rg -F "no persistent CoreAudio hang" "$path" >/dev/null
}

count_accepted_duration_rows() {
    path="$1"
    minutes="$2"
    awk -F '|' -v minutes="$minutes" '
        BEGIN { count = 0 }
        /^\|/ && $2 !~ /Run/ && $2 !~ /---/ {
            for (i = 1; i <= NF; i += 1) {
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", $i)
            }
            duration = $3
            scope = $4
            mic = $5
            incoming = $6
            alignment = $7
            cpu = $8
            responsiveness = $9
            release = $10
            result = $11
            notes = $12
            if (duration == minutes " minutes" &&
                scope == "passed" &&
                mic == "passed" &&
                incoming == "passed" &&
                alignment == "passed" &&
                cpu == "passed" &&
                responsiveness == "passed" &&
                release == "passed" &&
                result == "passed" &&
                index(notes, "scope=") > 0 &&
                index(notes, "device=") > 0 &&
                index(notes, "artifact=") > 0 &&
                index(notes, "cpu=") > 0 &&
                index(notes, "micDuration=") > 0 &&
                index(notes, "incomingDuration=") > 0 &&
                index(notes, "durationDifferenceSeconds=") > 0 &&
                index(notes, "responsiveness=") > 0 &&
                index(notes, "release=") > 0) {
                count += 1
            }
        }
        END { print count + 0 }
    ' "$path"
}

last_cpu_evaluation_for_phase() {
    phase="$1"
    awk -v wanted="$phase" '
        /^## / {
            current = ""
            for (i = 1; i <= NF; i += 1) {
                if ($i == wanted) {
                    current = wanted
                }
            }
        }
        current == wanted && /^- Evaluation: `/ {
            line = $0
            sub(/^- Evaluation: `/, "", line)
            sub(/`$/, "", line)
            last = line
        }
        END {
            if (last != "") {
                print last
            }
        }
    ' "$CPU_GATES"
}

last_cpu_timestamp_for_phase() {
    phase="$1"
    awk -v wanted="$phase" '
        /^## / {
            current = ""
            timestamp = $2
            for (i = 1; i <= NF; i += 1) {
                if ($i == wanted) {
                    current = wanted
                }
            }
        }
        current == wanted && /^- Evaluation: `/ {
            last = timestamp
        }
        END {
            if (last != "") {
                print last
            }
        }
    ' "$CPU_GATES"
}

latest_hot_baseline_after_phase() {
    phase="$1"
    phase_timestamp="$(last_cpu_timestamp_for_phase "$phase")"
    baseline_timestamp="$(last_cpu_timestamp_for_phase baseline)"
    baseline_evaluation="$(last_cpu_evaluation_for_phase baseline)"

    [ -n "$baseline_timestamp" ] || return 1
    [ -n "$baseline_evaluation" ] || return 1
    if ! awk -v baseline="$baseline_timestamp" -v phase="$phase_timestamp" \
        'BEGIN { exit(phase == "" || baseline > phase ? 0 : 1) }'; then
        return 1
    fi

    baseline_max_core="$(evaluation_field maxCoreaudiodCpuPercent "$baseline_evaluation")"
    is_nonnegative_decimal "$baseline_max_core" || return 1
    if ! decimal_less_than "$baseline_max_core" 5; then
        printf '%s\n' "timestamp=$baseline_timestamp evaluation=$baseline_evaluation"
        return 0
    fi

    return 1
}

evaluation_field() {
    field="$1"
    evaluation="$2"
    printf '%s\n' "$evaluation" |
        awk -v field="$field" '{
            for (i = 1; i <= NF; i += 1) {
                split($i, kv, "=")
                if (kv[1] == field) {
                    print kv[2]
                    exit
                }
            }
        }'
}

is_nonnegative_decimal() {
    awk -v value="${1:-}" 'BEGIN { exit(value ~ /^[0-9]+([.][0-9]+)?$/ ? 0 : 1) }'
}

decimal_less_than() {
    awk -v left="${1:-}" -v right="${2:-}" 'BEGIN { exit((left + 0) < (right + 0) ? 0 : 1) }'
}

validate_cpu_evaluation_passed() {
    phase="$1"
    evaluation="$2"
    source_label="$3"

    case "$evaluation" in
        status=passed\ *)
            ;;
        *)
            printf '%s\n' "$source_label is not passed: $evaluation"
            return 1
            ;;
    esac

    sample_count="$(evaluation_field sampleCount "$evaluation")"
    max_core_cpu_percent="$(evaluation_field maxCoreaudiodCpuPercent "$evaluation")"
    max_app_cpu_percent="$(evaluation_field maxAppHelperCpuPercent "$evaluation")"
    max_app_process_count="$(evaluation_field maxAppProcessCount "$evaluation")"
    max_helper_process_count="$(evaluation_field maxHelperProcessCount "$evaluation")"
    max_unexpected_app_process_count="$(evaluation_field maxUnexpectedAppProcessCount "$evaluation")"
    max_core_rss_mb="$(evaluation_field maxCoreaudiodRssMB "$evaluation")"
    max_app_rss_mb="$(evaluation_field maxAppHelperRssMB "$evaluation")"
    sustained_core_exceeded="$(evaluation_field sustainedCoreaudiodExceeded "$evaluation")"
    sustained_app_exceeded="$(evaluation_field sustainedAppHelperExceeded "$evaluation")"
    phase_event_observed="$(evaluation_field phaseEventObserved "$evaluation")"

    case "$sample_count" in
        ""|*[!0-9]*)
            printf '%s\n' "$source_label is missing numeric sampleCount: $evaluation"
            return 1
            ;;
        *)
            if [ "$sample_count" -lt 3 ]; then
                printf '%s\n' "$source_label has insufficient samples: $evaluation"
                return 1
            fi
            ;;
    esac

    for field_value in \
        "maxCoreaudiodCpuPercent=$max_core_cpu_percent" \
        "maxAppHelperCpuPercent=$max_app_cpu_percent" \
        "maxCoreaudiodRssMB=$max_core_rss_mb" \
        "maxAppHelperRssMB=$max_app_rss_mb"; do
        field_name="${field_value%%=*}"
        value="${field_value#*=}"
        if ! is_nonnegative_decimal "$value"; then
            printf '%s\n' "$source_label is missing numeric $field_name: $evaluation"
            return 1
        fi
    done

    case "$sustained_core_exceeded:$sustained_app_exceeded" in
        false:false)
            ;;
        *)
            printf '%s\n' "$source_label has sustained CPU threshold exceedance or missing sustained flags: $evaluation"
            return 1
            ;;
    esac

    case "$max_app_process_count:$max_helper_process_count:$max_unexpected_app_process_count" in
        *[!0-9:]*|:*|*:)
            printf '%s\n' "$source_label is missing numeric process counts: $evaluation"
            return 1
            ;;
    esac

    if [ "$max_unexpected_app_process_count" != "0" ]; then
        printf '%s\n' "$source_label observed an unexpected extra 2brain Rec process: $evaluation"
        return 1
    fi

    case "$phase" in
        idle|stop|quit)
            if ! decimal_less_than "$max_core_cpu_percent" 5 ||
                ! decimal_less_than "$max_app_cpu_percent" 5; then
                printf '%s\n' "$source_label exceeds idle/stop/quit CPU ceiling: $evaluation"
                return 1
            fi
            ;;
    esac

    case "$phase" in
        idle|activeRecording|stop)
            case "$max_app_process_count" in
                ""|*[!0-9]*|0)
                    printf '%s\n' "$source_label did not observe the app process: $evaluation"
                    return 1
                    ;;
            esac
            ;;
        quit)
            case "$max_app_process_count:$max_helper_process_count" in
                0:0)
                    ;;
                *)
                    printf '%s\n' "$source_label did not prove app/helper process release: $evaluation"
                    return 1
                    ;;
            esac
            ;;
    esac

    case "$phase" in
        activeRecording|stop)
            if [ "$phase_event_observed" != "true" ]; then
                printf '%s\n' "$source_label is missing fresh app-log event binding for $phase: $evaluation"
                return 1
            fi
            ;;
    esac

    return 0
}

validate_cpu_phase_passed() {
    phase="$1"
    if [ "$phase" = "stop" ] && has_manual_cpu_acceptance_caveat "$CPU_GATES"; then
        return 0
    fi

    if [ "$phase" = "idle" ] &&
        hot_baseline="$(latest_hot_baseline_after_phase "$phase")"; then
        printf '%s\n' "$CPU_GATES has newer hot baseline before idle acceptance: $hot_baseline"
        return 1
    fi

    evaluation="$(last_cpu_evaluation_for_phase "$phase")"
    if [ -z "$evaluation" ]; then
        printf '%s\n' "$CPU_GATES is missing $phase CPU evaluation"
        return 1
    fi
    validate_cpu_evaluation_passed "$phase" "$evaluation" "$CPU_GATES latest $phase CPU evaluation"
}

expect_cpu_evaluation_accepts() {
    label="$1"
    phase="$2"
    evaluation="$3"
    if ! validate_cpu_evaluation_passed "$phase" "$evaluation" "self-test $label" >/dev/null 2>&1; then
        printf '%s\n' "cpu_evidence_self_test_failed=$label"
        return 1
    fi
}

expect_cpu_evaluation_rejects() {
    label="$1"
    phase="$2"
    evaluation="$3"
    if validate_cpu_evaluation_passed "$phase" "$evaluation" "self-test $label" >/dev/null 2>&1; then
        printf '%s\n' "cpu_evidence_self_test_failed=$label"
        return 1
    fi
}

self_test_cpu_evidence() {
    valid_idle="status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=4.99 maxAppHelperCpuPercent=0.10 maxCoreaudiodRssMB=58.10 maxAppHelperRssMB=93.20 maxAppProcessCount=1 maxHelperProcessCount=0 maxUnexpectedAppProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired"
    valid_active="status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=12.00 maxAppHelperCpuPercent=26.00 maxCoreaudiodRssMB=58.10 maxAppHelperRssMB=93.20 maxAppProcessCount=1 maxHelperProcessCount=0 maxUnexpectedAppProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=true"
    valid_stop="status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.10 maxAppHelperCpuPercent=0.10 maxCoreaudiodRssMB=58.10 maxAppHelperRssMB=93.20 maxAppProcessCount=1 maxHelperProcessCount=0 maxUnexpectedAppProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=true"
    valid_quit="status=passed failureReason=none sampleCount=3 maxCoreaudiodCpuPercent=0.00 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=58.10 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 maxUnexpectedAppProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired"

    expect_cpu_evaluation_accepts "valid-idle" idle "$valid_idle"
    expect_cpu_evaluation_accepts "valid-active-burst-without-sustained-exceedance" activeRecording "$valid_active"
    expect_cpu_evaluation_accepts "valid-stop-with-event" stop "$valid_stop"
    expect_cpu_evaluation_accepts "valid-quit" quit "$valid_quit"

    expect_cpu_evaluation_rejects "failed-status" idle "${valid_idle#status=passed }"
    expect_cpu_evaluation_rejects "insufficient-samples" idle "$(printf '%s\n' "$valid_idle" | sed 's/sampleCount=3/sampleCount=2/')"
    expect_cpu_evaluation_rejects "nonnumeric-cpu" idle "$(printf '%s\n' "$valid_idle" | sed 's/maxCoreaudiodCpuPercent=4.99/maxCoreaudiodCpuPercent=busy/')"
    expect_cpu_evaluation_rejects "nonnumeric-rss" idle "$(printf '%s\n' "$valid_idle" | sed 's/maxAppHelperRssMB=93.20/maxAppHelperRssMB=unknown/')"
    expect_cpu_evaluation_rejects "idle-ceiling" idle "$(printf '%s\n' "$valid_idle" | sed 's/maxCoreaudiodCpuPercent=4.99/maxCoreaudiodCpuPercent=5.00/')"
    expect_cpu_evaluation_rejects "sustained-core" activeRecording "$(printf '%s\n' "$valid_active" | sed 's/sustainedCoreaudiodExceeded=false/sustainedCoreaudiodExceeded=true/')"
    expect_cpu_evaluation_rejects "missing-app-process" activeRecording "$(printf '%s\n' "$valid_active" | sed 's/maxAppProcessCount=1/maxAppProcessCount=0/')"
    expect_cpu_evaluation_rejects "unexpected-app-process" activeRecording "$(printf '%s\n' "$valid_active" | sed 's/maxUnexpectedAppProcessCount=0/maxUnexpectedAppProcessCount=1/')"
    expect_cpu_evaluation_rejects "missing-unexpected-app-process-field" activeRecording "$(printf '%s\n' "$valid_active" | sed 's/maxUnexpectedAppProcessCount=0 //')"
    expect_cpu_evaluation_rejects "active-missing-event-binding" activeRecording "$(printf '%s\n' "$valid_active" | sed 's/phaseEventObserved=true/phaseEventObserved=false/')"
    expect_cpu_evaluation_rejects "stop-missing-event-binding" stop "$(printf '%s\n' "$valid_stop" | sed 's/phaseEventObserved=true/phaseEventObserved=false/')"
    expect_cpu_evaluation_rejects "quit-process-left" quit "$(printf '%s\n' "$valid_quit" | sed 's/maxAppProcessCount=0/maxAppProcessCount=1/')"

    original_cpu_gates="$CPU_GATES"
    temp_cpu_gates="$(mktemp)"
    CPU_GATES="$temp_cpu_gates"
    cat > "$CPU_GATES" <<EOF
## 2026-06-09T10:00:00Z idle

- Evaluation: \`$valid_idle\`

## 2026-06-09T10:01:00Z baseline

- Evaluation: \`status=observed failureReason=diagnosticOnly sampleCount=3 maxCoreaudiodCpuPercent=7.40 maxAppHelperCpuPercent=0.00 maxCoreaudiodRssMB=58.10 maxAppHelperRssMB=0.00 maxAppProcessCount=0 maxHelperProcessCount=0 sustainedCoreaudiodExceeded=false sustainedAppHelperExceeded=false phaseEventObserved=notRequired\`
EOF
    if ! latest_hot_baseline_after_phase idle >/dev/null 2>&1; then
        CPU_GATES="$original_cpu_gates"
        rm -f "$temp_cpu_gates"
        printf '%s\n' "cpu_evidence_self_test_failed=hot-baseline-after-idle"
        return 1
    fi
    cat >> "$CPU_GATES" <<EOF

## 2026-06-09T10:02:00Z idle

- Evaluation: \`$valid_idle\`
EOF
    if latest_hot_baseline_after_phase idle >/dev/null 2>&1; then
        CPU_GATES="$original_cpu_gates"
        rm -f "$temp_cpu_gates"
        printf '%s\n' "cpu_evidence_self_test_failed=fresh-idle-after-hot-baseline"
        return 1
    fi
    CPU_GATES="$original_cpu_gates"
    rm -f "$temp_cpu_gates"

    passed "synthetic CPU evidence parser checks passed"
}

write_synthetic_wav() {
    path="$1"
    {
        printf 'RIFF'
        printf '\044\175\000\000'
        printf 'WAVE'
        printf 'fmt '
        printf '\020\000\000\000'
        printf '\001\000'
        printf '\001\000'
        printf '\200\076\000\000'
        printf '\000\175\000\000'
        printf '\002\000'
        printf '\020\000'
        printf 'data'
        printf '\000\175\000\000'
        dd if=/dev/zero bs=32000 count=1 2>/dev/null
    } > "$path"
}

write_synthetic_manifest() {
    directory="$1"
    failure_reason="$2"
    status="$3"
    directory_id="$(basename "$directory")"
    cat > "$directory/manifest.json" <<EOF
{
  "schemaVersion": "local-recording-manifest.v2",
  "sessionId": "synthetic-artifact-self-test",
  "createdAt": "2026-06-09T00:00:00Z",
  "startedAt": "2026-06-09T00:00:00Z",
  "stoppedAt": "2026-06-09T00:00:01Z",
  "status": "$status",
  "directoryId": "$directory_id",
  "manifestFileName": "manifest.json",
  "transcriptionReadiness": "ready",
  "mediaScribeSourceMode": "dual",
  "externalEgressStarted": false,
  "transcriptionStarted": false,
  "diagnosticSafe": true,
  "failureReason": "$failure_reason",
  "durationDifferenceSeconds": 0,
  "scopeApproval": {
    "approvedBy": "user",
    "notTriggerForBackgroundAudio": true
  },
  "permissions": {
    "microphone": "granted",
    "systemAudio": "granted"
  },
  "captureHealth": {
    "recordingSessionId": "synthetic-artifact-self-test",
    "sampledAt": "2026-06-09T00:00:01Z",
    "phase": "stop",
    "halProbeObserved": false,
    "gateStatus": "passed",
    "failureReason": "none"
  },
  "tracks": [
    {
      "trackId": "local_mic-track",
      "role": "local_mic",
      "sourceKind": "microphone",
      "mediaScribeField": "mic_file",
      "status": "saved",
      "fileName": "mic.wav",
      "format": "wav-pcm-s16le",
      "sampleRate": 16000,
      "channelCount": 1,
      "bitsPerSample": 16,
      "durationMs": 1000,
      "byteCount": 32044,
      "frameCount": 16000,
      "timelineStartMs": 0,
      "timelineAligned": true,
      "failureReason": "none"
    },
    {
      "trackId": "remote_speaker-track",
      "role": "remote_speaker",
      "sourceKind": "systemAudio",
      "mediaScribeField": "incoming_file",
      "status": "saved",
      "fileName": "incoming.wav",
      "format": "wav-pcm-s16le",
      "sampleRate": 16000,
      "channelCount": 1,
      "bitsPerSample": 16,
      "durationMs": 1000,
      "byteCount": 32044,
      "frameCount": 16000,
      "timelineStartMs": 0,
      "timelineAligned": true,
      "failureReason": "none"
    }
  ]
}
EOF
}

self_test_artifact_metadata() {
    temp_root="$(mktemp -d)"
    trap 'rm -rf "$temp_root"' EXIT

    accepted_dir="$temp_root/synthetic-accepted"
    failed_dir="$temp_root/synthetic-failed"
    degraded_dir="$temp_root/synthetic-degraded"
    mkdir -p "$accepted_dir" "$failed_dir" "$degraded_dir"
    write_synthetic_wav "$accepted_dir/mic.wav"
    write_synthetic_wav "$accepted_dir/incoming.wav"
    write_synthetic_manifest "$accepted_dir" "none" "saved"

    cp "$accepted_dir/mic.wav" "$failed_dir/mic.wav"
    cp "$accepted_dir/incoming.wav" "$failed_dir/incoming.wav"
    write_synthetic_manifest "$failed_dir" "capture_failed" "saved"

    cp "$accepted_dir/mic.wav" "$degraded_dir/mic.wav"
    cp "$accepted_dir/incoming.wav" "$degraded_dir/incoming.wav"
    write_synthetic_manifest "$degraded_dir" "none" "degraded"

    SYSTEM_AUDIO_CAPTURE_PIVOT_NO_APPEND=1 "$0" --artifact-directory "$accepted_dir" >/dev/null ||
        fail_invalid "synthetic accepted artifact metadata did not pass"

    if SYSTEM_AUDIO_CAPTURE_PIVOT_NO_APPEND=1 "$0" --artifact-directory "$failed_dir" >/dev/null 2>&1; then
        fail_invalid "synthetic capture_failed artifact metadata was incorrectly accepted"
    fi
    if SYSTEM_AUDIO_CAPTURE_PIVOT_NO_APPEND=1 "$0" --artifact-directory "$degraded_dir" >/dev/null 2>&1; then
        fail_invalid "synthetic degraded artifact metadata was incorrectly accepted"
    fi

    passed "synthetic artifact metadata checks passed"
}

self_test_latest_artifact_selection() {
    temp_root="$(mktemp -d)"
    trap 'rm -rf "$temp_root"' EXIT

    stale_dir="$temp_root/stale-complete"
    fresh_dir="$temp_root/fresh-complete"
    partial_dir="$temp_root/newer-partial"
    mkdir -p "$stale_dir" "$fresh_dir" "$partial_dir"

    write_synthetic_wav "$stale_dir/mic.wav"
    write_synthetic_wav "$stale_dir/incoming.wav"
    write_synthetic_manifest "$stale_dir" "none" "saved"

    write_synthetic_wav "$fresh_dir/mic.wav"
    write_synthetic_wav "$fresh_dir/incoming.wav"
    write_synthetic_manifest "$fresh_dir" "none" "saved"

    write_synthetic_wav "$partial_dir/mic.wav"
    write_synthetic_manifest "$partial_dir" "none" "saved"

    stale_touch="202001010000"
    touch -t "$stale_touch" "$stale_dir/manifest.json" "$stale_dir/mic.wav" "$stale_dir/incoming.wav"
    touch "$stale_dir"

    min_epoch="$(date +%s)"
    touch "$fresh_dir/manifest.json" "$fresh_dir/mic.wav" "$fresh_dir/incoming.wav"
    touch "$partial_dir/manifest.json" "$partial_dir/mic.wav" "$partial_dir"

    selected="$(
        TWO_BRAIN_REC_RECORDINGS_DIR="$temp_root" \
        SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME="$min_epoch" \
        "$0" --latest-artifact-directory
    )" || fail_invalid "synthetic latest artifact selection did not find fresh complete artifact"

    [ "$selected" = "$fresh_dir" ] ||
        fail_invalid "synthetic latest artifact selection chose unexpected directory: $selected"

    TWO_BRAIN_REC_RECORDINGS_DIR="$temp_root" \
    SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME="$min_epoch" \
    SYSTEM_AUDIO_CAPTURE_PIVOT_NO_APPEND=1 \
        "$0" --validate-latest-artifact >/dev/null ||
        fail_invalid "synthetic latest artifact validation did not validate fresh complete artifact"

    future_epoch=$((min_epoch + 3600))
    if TWO_BRAIN_REC_RECORDINGS_DIR="$temp_root" \
        SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME="$future_epoch" \
        "$0" --latest-artifact-directory >/dev/null 2>&1; then
        fail_invalid "synthetic latest artifact selection accepted stale artifacts after future gate epoch"
    fi

    passed "synthetic latest artifact selection checks passed"
}

self_test_duration_evidence() {
    temp_file="$(mktemp)"
    trap 'rm -f "$temp_file"' EXIT
    cat > "$temp_file" <<'EOF'
| Run | Duration | Scope | mic.wav | incoming.wav | Alignment | CPU Gate | Responsiveness | Stop/Quit Release | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| accepted-30 | 30 minutes | passed | passed | passed | passed | passed | passed | passed | passed | scope=Display-1 device=Mac15,10 artifact=synthetic-accepted cpu=synthetic-cpu micDuration=1800s incomingDuration=1800s durationDifferenceSeconds=0 responsiveness=passed release=passed |
| wrong-duration | 29 minutes | passed | passed | passed | passed | passed | passed | passed | passed | wrong duration |
| failed-cpu | 30 minutes | passed | passed | passed | passed | failed | passed | passed | passed | failed CPU |
| not-tested-release | 30 minutes | passed | passed | passed | passed | passed | passed | not-tested | passed | incomplete release |
| failed-result | 30 minutes | passed | passed | passed | passed | passed | passed | passed | failed | failed result |
| passed-without-traceability | 30 minutes | passed | passed | passed | passed | passed | passed | passed | passed | missing traceability tokens |
| accepted-75 | 75 minutes | passed | passed | passed | passed | passed | passed | passed | passed | scope=Display-1 device=Mac15,10 artifact=synthetic-release cpu=synthetic-cpu micDuration=4500s incomingDuration=4500s durationDifferenceSeconds=0 responsiveness=passed release=passed |
EOF

    accepted_30="$(count_accepted_duration_rows "$temp_file" 30)"
    accepted_75="$(count_accepted_duration_rows "$temp_file" 75)"

    [ "$accepted_30" = "1" ] ||
        fail_invalid "synthetic duration parser expected exactly one accepted 30-minute row, got $accepted_30"
    [ "$accepted_75" = "1" ] ||
        fail_invalid "synthetic duration parser expected exactly one accepted 75-minute row, got $accepted_75"

    passed "synthetic duration evidence parser checks passed"
}

self_test_permission_evidence() {
    temp_file="$(mktemp)"
    trap 'rm -f "$temp_file"' EXIT
    cat > "$temp_file" <<'EOF'
| Microphone | Screen/System Audio | Normal Recording Outcome | Visible Copy | Manifest Outcome | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| granted | granted | accepted start allowed | no permission blocker | eligible saved | passed | accepted synthetic row |
| denied | granted | blocked before accepted start | microphone access required | permission_denied | passed | accepted synthetic row |
| granted | denied/restricted/unknown | blocked before accepted start | system audio access required | permission_denied | passed | accepted synthetic row |
| denied | denied/restricted/unknown | blocked before accepted start | both permissions required | permission_denied | passed | accepted synthetic row |
| permission revoked while recording | any required permission missing | stop/finalize degraded or failed | retry copy | permission_denied | passed | accepted synthetic row |
| granted | granted | accepted start allowed | no permission blocker | eligible saved | not-tested | duplicate not-tested must not matter |
| denied | granted | blocked before accepted start | microphone access required | permission_denied | failed | duplicate failed must not matter |
| granted | unknown future state | blocked | unknown | permission_denied | passed | unknown state must not count |
EOF

    accepted="$(count_accepted_permission_rows "$temp_file")"
    [ "$accepted" = "5" ] ||
        fail_invalid "synthetic permission parser expected exactly five accepted rows, got $accepted"

    passed "synthetic permission evidence parser checks passed"
}

self_test_review_evidence() {
    embedded_file="$(mktemp)"
    accepted_file="$(mktemp)"
    trap 'rm -f "$embedded_file" "$accepted_file"' EXIT

    cat > "$embedded_file" <<'EOF'
# Scope Review

This example mentions - Final scope review: accepted inside prose and should
not pass. It also mentions - Reviewed against quickstart and contracts: yes
inside prose and should not pass.

## Final Review Template

- Final scope review: accepted
- Reviewed against quickstart and contracts: yes
- Evidence traceability: #307/T071 #308/T072 #309/T073 #310/T074 #311/T075 #312/T076 #313/T077
EOF

    cat > "$accepted_file" <<'EOF'
# Scope Review

## Final Accepted Scope Review

- Final scope review: accepted
- Reviewed against quickstart and contracts: yes
- Evidence traceability: #307/T071 #308/T072 #309/T073 #310/T074 #311/T075 #312/T076 #313/T077
EOF

    if has_exact_line_after_header "$embedded_file" "## Final Accepted Scope Review" "- Final scope review: accepted" ||
        has_exact_line_after_header "$embedded_file" "## Final Accepted Scope Review" "- Reviewed against quickstart and contracts: yes" ||
        has_exact_line_after_header "$embedded_file" "## Final Accepted Scope Review" "- Evidence traceability: #307/T071 #308/T072 #309/T073 #310/T074 #311/T075 #312/T076 #313/T077"; then
        fail_invalid "synthetic review parser accepted marker text outside final accepted section"
    fi
    has_exact_line_after_header "$accepted_file" "## Final Accepted Scope Review" "- Final scope review: accepted" ||
        fail_invalid "synthetic review parser rejected exact final scope marker"
    has_exact_line_after_header "$accepted_file" "## Final Accepted Scope Review" "- Reviewed against quickstart and contracts: yes" ||
        fail_invalid "synthetic review parser rejected exact quickstart/contracts marker"
    has_exact_line_after_header "$accepted_file" "## Final Accepted Scope Review" "- Evidence traceability: #307/T071 #308/T072 #309/T073 #310/T074 #311/T075 #312/T076 #313/T077" ||
        fail_invalid "synthetic review parser rejected exact evidence traceability marker"

    passed "synthetic final review marker parser checks passed"
}

ensure_no_forbidden_hal_requirement() {
    if rg -n "HAL runtime probe|required virtual device|driver reinstall required|coreaudiod restart" \
        "$PERMISSION_MATRIX" "$ARTIFACT_MATRIX" "$DEV_DURATION" "$RELEASE_DURATION" "$SCOPE_REVIEW" \
        >/dev/null 2>&1; then
        blocked "evidence contains forbidden HAL/virtual-device recovery wording"
    fi
}

latest_no_hal_status() {
    awk '
        /^## .* No-HAL MVP Boundary$/ {
            in_section = 1
            status = ""
            next
        }
        in_section && /^- Status: `/ {
            line = $0
            sub(/^- Status: `/, "", line)
            sub(/`.*$/, "", line)
            status = line
        }
        END {
            print status
        }
    ' "$NO_HAL"
}

validate_permission_matrix() {
    mkdir -p "$EVIDENCE_DIR"
    require_file "$PERMISSION_MATRIX"

    for phrase in \
        "granted | granted" \
        "denied | granted" \
        "granted | denied/restricted/unknown" \
        "denied | denied/restricted/unknown" \
        "permission revoked while recording"
    do
        rg -F "$phrase" "$PERMISSION_MATRIX" >/dev/null ||
            fail_invalid "permission matrix is missing required row: $phrase"
    done

    append_run_header "$PERMISSION_MATRIX" "Metadata Validator Run"
    {
        printf -- '- Mode: `--permission-matrix`\n'
        printf -- '- Validator result: `blocked`\n'
        printf -- '- Reason: Manual TCC grant/deny/revoke rows are still required before acceptance.\n'
        printf -- '- Safe checks: required rows present; blocked/degraded/not-tested rows are not counted as acceptance; this helper avoids HAL probes and driver reinstall steps.\n'
    } >> "$PERMISSION_MATRIX"

    ensure_no_forbidden_hal_requirement
    remaining="$(count_not_tested_rows "$PERMISSION_MATRIX")"
    [ "$remaining" = "0" ] ||
        blocked "permission matrix still has $remaining not-tested row(s); keep #307/T071 open"

    accepted_rows="$(count_accepted_permission_rows "$PERMISSION_MATRIX")"
    [ "$accepted_rows" = "5" ] ||
        blocked "permission matrix has $accepted_rows accepted row(s), expected 5 required permission scenarios with Result passed; keep #307/T071 open"

    passed "permission matrix has accepted evidence for all required scenarios"
}

validate_artifact_matrix() {
    mkdir -p "$EVIDENCE_DIR"
    require_file "$ARTIFACT_MATRIX"

    for phrase in \
        "Both microphone and system audio present" \
        "Microphone present, incoming/system audio silent" \
        "Incoming/system audio present, microphone missing" \
        "Protected or blocked incoming/system audio" \
        "Misaligned tracks"
    do
        rg -F "$phrase" "$ARTIFACT_MATRIX" >/dev/null ||
            fail_invalid "artifact matrix is missing required row: $phrase"
    done

    append_run_header "$ARTIFACT_MATRIX" "Metadata Validator Run"
    {
        printf -- '- Mode: `--artifact-matrix`\n'
        printf -- '- Validator result: `blocked`\n'
        printf -- '- Reason: Controlled meeting/audio artifact rows are still required before acceptance.\n'
        printf -- '- Safe checks: required rows present; `incoming.wav` remains `remote_speaker` with `systemAudio` metadata; blocked/degraded/not-tested rows are not counted as acceptance.\n'
    } >> "$ARTIFACT_MATRIX"

    ensure_no_forbidden_hal_requirement

    accepted_rows="$(count_accepted_artifact_rows "$ARTIFACT_MATRIX")"
    if [ "$accepted_rows" != "5" ] && ! has_controlled_artifact_acceptance "$ARTIFACT_MATRIX"; then
        remaining="$(count_not_tested_rows "$ARTIFACT_MATRIX")"
        [ "$remaining" = "0" ] ||
            blocked "artifact matrix still has $remaining not-tested row(s); keep #308/T072 open"
        blocked "artifact matrix has $accepted_rows accepted row(s), expected 5 required artifact scenarios with Result passed or explicit controlled-artifact acceptance; keep #308/T072 open"
    fi

    passed "artifact matrix has accepted controlled artifact evidence"
}

validate_artifact_directory() {
    directory="${1:-}"
    [ -n "$directory" ] || fail_invalid "--artifact-directory requires a path"
    [ -d "$directory" ] || fail_invalid "artifact directory does not exist: $directory"

    manifest="$directory/manifest.json"
    mic="$directory/mic.wav"
    incoming="$directory/incoming.wav"
    require_file "$manifest"
    require_file "$mic"
    require_file "$incoming"
    unexpected_entry_count="$(find "$directory" -mindepth 1 -maxdepth 1 ! -name 'manifest.json' ! -name 'mic.wav' ! -name 'incoming.wav' | wc -l | tr -d ' ')"
    [ "$unexpected_entry_count" = "0" ] ||
        fail_invalid "artifact directory contains unexpected entry or entries; accepted packages must contain only manifest.json, mic.wav, and incoming.wav"
    command -v jq >/dev/null 2>&1 || fail_invalid "jq is required for artifact manifest validation"
    jq empty "$manifest" >/dev/null 2>&1 || fail_invalid "manifest.json is not valid JSON"

    failure_file="$(mktemp)"
    trap 'rm -f "$failure_file"' EXIT

    check_jq() {
        expression="$1"
        message="$2"
        if ! jq -e "$expression" "$manifest" >/dev/null 2>/dev/null; then
            printf '%s\n' "$message" >> "$failure_file"
        fi
    }

    check_jq '.schemaVersion == "local-recording-manifest.v2"' "schemaVersion must be local-recording-manifest.v2"
    check_jq '(.sessionId | type) == "string" and (.sessionId | length) > 0' "sessionId must be a non-empty string"
    check_jq '(.directoryId | type) == "string" and (.directoryId | length) > 0' "directoryId must be a non-empty string"
    expected_directory_id="$(basename "$directory")"
    if ! jq -e --arg expectedDirectoryId "$expected_directory_id" '.directoryId == $expectedDirectoryId' "$manifest" >/dev/null 2>/dev/null; then
        printf '%s\n' "directoryId must match artifact directory name" >> "$failure_file"
    fi
    check_jq '.manifestFileName == "manifest.json"' "manifestFileName must be manifest.json"
    check_jq '(.startedAt | type) == "string" and (.startedAt | length) > 0' "startedAt must be present"
    check_jq '(.stoppedAt | type) == "string" and (.stoppedAt | length) > 0' "stoppedAt must be present"
    check_jq '.status == "saved"' "manifest status must be saved"
    check_jq '.transcriptionReadiness == "ready"' "transcriptionReadiness must be ready"
    check_jq '.mediaScribeSourceMode == "dual"' "mediaScribeSourceMode must be dual"
    check_jq '.externalEgressStarted == false' "externalEgressStarted must be false"
    check_jq '.transcriptionStarted == false' "transcriptionStarted must be false"
    check_jq '.diagnosticSafe == true' "diagnosticSafe must be true"
    check_jq '.failureReason == "none"' "manifest failureReason must be none for accepted artifact"
    check_jq '(.durationDifferenceSeconds | type) == "number" and .durationDifferenceSeconds >= 0 and .durationDifferenceSeconds <= 3' "durationDifferenceSeconds must be a number between 0 and 3"
    check_jq '(.captureHealth | type) == "object" and .captureHealth.recordingSessionId == .sessionId and (.captureHealth.sampledAt | type) == "string" and .captureHealth.phase == "stop" and .captureHealth.halProbeObserved == false and .captureHealth.gateStatus == "passed" and .captureHealth.failureReason == "none"' "captureHealth must be present, match session, be stop-phase, no-HAL, passed, and failureReason none"
    check_jq '([.tracks[] | select(.role == "local_mic") | .durationMs] | length) == 1 and ([.tracks[] | select(.role == "remote_speaker") | .durationMs] | length) == 1 and ([.tracks[] | select(.role == "local_mic") | .durationMs][0] | type) == "number" and ([.tracks[] | select(.role == "remote_speaker") | .durationMs][0] | type) == "number"' "manifest must contain exactly one numeric durationMs for local_mic and remote_speaker"
    check_jq '([.tracks[] | select(.role == "local_mic") | .durationMs][0]) as $mic | ([.tracks[] | select(.role == "remote_speaker") | .durationMs][0]) as $incoming | (($mic - $incoming) as $diff | (if $diff < 0 then -$diff else $diff end) as $abs | ($abs <= 3000 and .durationDifferenceSeconds == ($abs / 1000)))' "durationDifferenceSeconds must equal the absolute mic/incoming duration difference and be <= 3"
    check_jq '.scopeApproval != null' "scopeApproval must be present"
    check_jq '.scopeApproval.approvedBy == "user" and .scopeApproval.notTriggerForBackgroundAudio == true' "scopeApproval must be user-approved and not a background-audio trigger"
    check_jq '.permissions.microphone == "granted"' "microphone permission must be granted"
    check_jq '.permissions.systemAudio == "granted"' "system audio permission must be granted"
    check_jq '([.tracks[].role] | sort) == ["local_mic","remote_speaker"]' "tracks must contain local_mic and remote_speaker"
    check_jq 'any(.tracks[]; .role == "local_mic" and (.trackId | type) == "string" and (.trackId | length) > 0 and .sourceKind == "microphone" and .mediaScribeField == "mic_file" and .status == "saved" and .fileName == "mic.wav" and .format == "wav-pcm-s16le" and .sampleRate == 16000 and .channelCount == 1 and .bitsPerSample == 16 and .timelineStartMs == 0 and .timelineAligned == true and .failureReason == "none" and .byteCount > 0 and .frameCount > 0 and .durationMs > 0)' "local_mic track must be saved microphone wav-pcm-s16le metadata"
    check_jq 'any(.tracks[]; .role == "remote_speaker" and (.trackId | type) == "string" and (.trackId | length) > 0 and .sourceKind == "systemAudio" and .mediaScribeField == "incoming_file" and .status == "saved" and .fileName == "incoming.wav" and .format == "wav-pcm-s16le" and .sampleRate == 16000 and .channelCount == 1 and .bitsPerSample == 16 and .timelineStartMs == 0 and .timelineAligned == true and .failureReason == "none" and .byteCount > 0 and .frameCount > 0 and .durationMs > 0)' "remote_speaker track must be saved systemAudio wav-pcm-s16le metadata"

    validate_wav_metadata "$mic" "local_mic" "mic.wav"
    validate_wav_metadata "$incoming" "remote_speaker" "incoming.wav"

    directory_id="$(jq -r '.directoryId // "unknown"' "$manifest")"
    manifest_status="$(jq -r '.status // "unknown"' "$manifest")"
    duration_difference="$(jq -r '.durationDifferenceSeconds // "unknown"' "$manifest")"
    append_evidence="${SYSTEM_AUDIO_CAPTURE_PIVOT_NO_APPEND:-0}"
    artifact_mode="${SYSTEM_AUDIO_CAPTURE_PIVOT_ARTIFACT_MODE:---artifact-directory}"

    if [ "$append_evidence" != "1" ]; then
        append_run_header "$ARTIFACT_MATRIX" "Artifact Directory Validator Run"
        {
            printf -- '- Mode: `%s`\n' "$artifact_mode"
            printf -- '- Directory ID: `%s`\n' "$directory_id"
            printf -- '- Manifest status: `%s`\n' "$manifest_status"
            printf -- '- Duration difference seconds: `%s`\n' "$duration_difference"
            if [ -n "${SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME:-}" ]; then
                printf -- '- Artifact minimum mtime epoch: `%s`\n' "$SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME"
            fi
        } >> "$ARTIFACT_MATRIX"
    fi

    if [ -s "$failure_file" ]; then
        if [ "$append_evidence" != "1" ]; then
            {
                printf -- '- Validator result: `blocked`\n'
                printf -- '- Reason: artifact directory did not satisfy accepted controlled-recording metadata.\n'
                printf -- '- Findings:\n'
                sed 's/^/  - /' "$failure_file"
            } >> "$ARTIFACT_MATRIX"
        fi
        printf '%s\n' "system_audio_capture_pivot_validation=blocked"
        printf '%s\n' "reason=artifact directory did not satisfy accepted controlled-recording metadata"
        cat "$failure_file"
        exit 2
    fi

    if [ "$append_evidence" != "1" ]; then
        {
            printf -- '- Validator result: `passed`\n'
            printf -- '- Safe checks: manifest/files/source metadata/permissions/scope/no-egress/duration contract passed without reading audio content.\n'
        } >> "$ARTIFACT_MATRIX"
    fi

    passed "artifact directory metadata passed for directoryId=$directory_id"
}

wav_ascii() {
    file="$1"
    offset="$2"
    dd if="$file" bs=1 skip="$offset" count=4 2>/dev/null
}

wav_u16_le() {
    file="$1"
    offset="$2"
    od -An -j "$offset" -N 2 -t u2 "$file" 2>/dev/null | tr -d ' '
}

wav_u32_le() {
    file="$1"
    offset="$2"
    od -An -j "$offset" -N 4 -t u4 "$file" 2>/dev/null | tr -d ' '
}

wav_chunk_offset() {
    file="$1"
    chunk_id="$2"
    file_bytes="$3"
    offset=12

    while [ "$((offset + 8))" -le "$file_bytes" ]; do
        current_id="$(wav_ascii "$file" "$offset")"
        current_size="$(wav_u32_le "$file" "$((offset + 4))")"
        if ! is_unsigned_integer "$current_size"; then
            return 1
        fi
        if [ "$current_id" = "$chunk_id" ]; then
            printf '%s\n' "$offset"
            return 0
        fi
        offset=$((offset + 8 + current_size))
        if [ "$((current_size % 2))" -eq 1 ]; then
            offset=$((offset + 1))
        fi
    done

    return 1
}

is_unsigned_integer() {
    case "${1:-}" in
        ""|*[!0-9]*)
            return 1
            ;;
        *)
            return 0
            ;;
    esac
}

validate_wav_metadata() {
    file="$1"
    role="$2"
    file_name="$3"

    manifest_byte_count="$(jq -r --arg role "$role" '.tracks[] | select(.role == $role) | .byteCount' "$manifest" | head -1)"
    manifest_frame_count="$(jq -r --arg role "$role" '.tracks[] | select(.role == $role) | .frameCount' "$manifest" | head -1)"
    manifest_duration_ms="$(jq -r --arg role "$role" '.tracks[] | select(.role == $role) | .durationMs' "$manifest" | head -1)"
    manifest_sample_rate="$(jq -r --arg role "$role" '.tracks[] | select(.role == $role) | .sampleRate' "$manifest" | head -1)"
    manifest_channel_count="$(jq -r --arg role "$role" '.tracks[] | select(.role == $role) | .channelCount' "$manifest" | head -1)"
    manifest_bits_per_sample="$(jq -r --arg role "$role" '.tracks[] | select(.role == $role) | .bitsPerSample' "$manifest" | head -1)"

    for value_name in byteCount frameCount durationMs sampleRate channelCount bitsPerSample; do
        case "$value_name" in
            byteCount) value="$manifest_byte_count" ;;
            frameCount) value="$manifest_frame_count" ;;
            durationMs) value="$manifest_duration_ms" ;;
            sampleRate) value="$manifest_sample_rate" ;;
            channelCount) value="$manifest_channel_count" ;;
            bitsPerSample) value="$manifest_bits_per_sample" ;;
        esac
        if ! is_unsigned_integer "$value"; then
            printf '%s\n' "$file_name manifest $value_name must be an unsigned integer" >> "$failure_file"
            return
        fi
    done

    file_bytes="$(wc -c < "$file" | tr -d ' ')"
    if [ "${file_bytes:-0}" != "${manifest_byte_count:-missing}" ]; then
        printf '%s\n' "$file_name file size must equal manifest byteCount (file=$file_bytes manifest=$manifest_byte_count)" >> "$failure_file"
    fi
    if [ "${file_bytes:-0}" -lt 44 ]; then
        printf '%s\n' "$file_name must be at least a 44-byte PCM WAV file" >> "$failure_file"
        return
    fi

    riff="$(wav_ascii "$file" 0)"
    wave="$(wav_ascii "$file" 8)"
    riff_byte_count="$(wav_u32_le "$file" 4)"
    fmt_offset="$(wav_chunk_offset "$file" "fmt " "$file_bytes" || true)"
    data_offset="$(wav_chunk_offset "$file" "data" "$file_bytes" || true)"

    [ "$riff" = "RIFF" ] || printf '%s\n' "$file_name WAV header must start with RIFF" >> "$failure_file"
    [ "$wave" = "WAVE" ] || printf '%s\n' "$file_name WAV header must contain WAVE" >> "$failure_file"
    [ -n "$fmt_offset" ] || printf '%s\n' "$file_name WAV header must contain fmt chunk" >> "$failure_file"
    [ -n "$data_offset" ] || printf '%s\n' "$file_name WAV header must contain data chunk" >> "$failure_file"

    if [ -z "$fmt_offset" ] || [ -z "$data_offset" ]; then
        return
    fi

    fmt_byte_count="$(wav_u32_le "$file" "$((fmt_offset + 4))")"
    audio_format="$(wav_u16_le "$file" "$((fmt_offset + 8))")"
    wav_channel_count="$(wav_u16_le "$file" "$((fmt_offset + 10))")"
    wav_sample_rate="$(wav_u32_le "$file" "$((fmt_offset + 12))")"
    byte_rate="$(wav_u32_le "$file" "$((fmt_offset + 16))")"
    block_align="$(wav_u16_le "$file" "$((fmt_offset + 20))")"
    wav_bits_per_sample="$(wav_u16_le "$file" "$((fmt_offset + 22))")"
    data_bytes="$(wav_u32_le "$file" "$((data_offset + 4))")"

    [ "$audio_format" = "1" ] || printf '%s\n' "$file_name WAV audio format must be PCM" >> "$failure_file"
    [ "$wav_sample_rate" = "$manifest_sample_rate" ] || printf '%s\n' "$file_name WAV sampleRate must equal manifest sampleRate" >> "$failure_file"
    [ "$wav_channel_count" = "$manifest_channel_count" ] || printf '%s\n' "$file_name WAV channelCount must equal manifest channelCount" >> "$failure_file"
    [ "$wav_bits_per_sample" = "$manifest_bits_per_sample" ] || printf '%s\n' "$file_name WAV bitsPerSample must equal manifest bitsPerSample" >> "$failure_file"

    expected_block_align=$((manifest_channel_count * manifest_bits_per_sample / 8))
    expected_byte_rate=$((manifest_sample_rate * expected_block_align))
    expected_data_bytes=$((manifest_frame_count * expected_block_align))
    expected_file_bytes=$((data_offset + 8 + expected_data_bytes))
    expected_riff_byte_count=$((expected_file_bytes - 8))
    expected_duration_ms=$((manifest_frame_count * 1000 / manifest_sample_rate))

    [ "$block_align" = "$expected_block_align" ] || printf '%s\n' "$file_name WAV blockAlign must match manifest format" >> "$failure_file"
    [ "$byte_rate" = "$expected_byte_rate" ] || printf '%s\n' "$file_name WAV byteRate must match manifest format" >> "$failure_file"
    [ "$riff_byte_count" = "$expected_riff_byte_count" ] || printf '%s\n' "$file_name WAV RIFF byte count must match file size" >> "$failure_file"
    [ "$fmt_byte_count" = "16" ] || printf '%s\n' "$file_name WAV fmt chunk size must be 16 for PCM" >> "$failure_file"
    [ "$data_bytes" = "$expected_data_bytes" ] || printf '%s\n' "$file_name WAV data byte count must match manifest frameCount" >> "$failure_file"
    [ "$file_bytes" = "$expected_file_bytes" ] || printf '%s\n' "$file_name file size must equal WAV data chunk end" >> "$failure_file"
    [ "$manifest_duration_ms" = "$expected_duration_ms" ] || printf '%s\n' "$file_name manifest durationMs must match manifest frameCount/sampleRate" >> "$failure_file"
}

validate_latest_artifact_directory() {
    directory="$(latest_completed_artifact_directory)"
    SYSTEM_AUDIO_CAPTURE_PIVOT_ARTIFACT_MODE="--validate-latest-artifact"
    export SYSTEM_AUDIO_CAPTURE_PIVOT_ARTIFACT_MODE
    validate_artifact_directory "$directory"
}

ensure_duration_file() {
    path="$1"
    minutes="$2"
    title="$3"
    if [ ! -f "$path" ]; then
        cat > "$path" <<EOF
# $title

Feature: \`025-system-audio-capture-pivot\`

This evidence file is metadata-only. Do not paste raw audio, transcripts,
meeting content, credentials, tokens, signed URLs, or personal contact details.

| Run | Duration | Scope | mic.wav | incoming.wav | Alignment | CPU Gate | Responsiveness | Stop/Quit Release | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pending | ${minutes} minutes | not-tested | not-tested | not-tested | not-tested | not-tested | not-tested | not-tested | not-tested | Manual validation pending |

Blocked, failed, degraded, and not-tested rows are not acceptance.

Accepted rows must include metadata-only traceability tokens in Notes:
\`scope=\`, \`device=\`, \`artifact=\`, \`cpu=\`, \`micDuration=\`,
\`incomingDuration=\`, \`durationDifferenceSeconds=\`, \`responsiveness=\`,
and \`release=\`.
EOF
    fi
}

validate_duration() {
    minutes="$1"
    manual_release="$2"
    case "$minutes:$manual_release" in
        30:false)
            path="$DEV_DURATION"
            title="Development 30-Minute Validation"
            issue="#310/T074"
            ;;
        75:true)
            path="$RELEASE_DURATION"
            title="Release 75-Minute Validation"
            issue="#311/T075"
            ;;
        75:false)
            fail_invalid "75-minute validation requires --manual-release"
            ;;
        *)
            fail_invalid "unsupported duration: $minutes"
            ;;
    esac

    mkdir -p "$EVIDENCE_DIR"
    ensure_duration_file "$path" "$minutes" "$title"
    append_run_header "$path" "Metadata Validator Run"
    {
        printf -- '- Mode: `--duration-minutes %s%s`\n' "$minutes" "$( [ "$manual_release" = true ] && printf ' --manual-release' || true )"
        printf -- '- Validator result: `blocked`\n'
        printf -- '- Reason: Real sustained recording run is still required before acceptance.\n'
        printf -- '- Safe checks: evidence file exists; not-tested rows are not counted as acceptance.\n'
    } >> "$path"

    remaining="$(count_not_tested_rows "$path")"
    [ "$remaining" = "0" ] ||
        blocked "$title still has $remaining not-tested row(s); keep $issue open"

    accepted_rows="$(count_accepted_duration_rows "$path" "$minutes")"
    [ "$accepted_rows" != "0" ] ||
        blocked "$title has no accepted row with duration/scope/mic/incoming/alignment/CPU/responsiveness/stop-quit all passed; keep $issue open"

    passed "$title has accepted duration evidence"
}

validate_installer_app_only() {
    mkdir -p "$EVIDENCE_DIR"
    require_file "$DRIVER_PARKED"

    build_output="$(mktemp)"
    failure_file="$(mktemp)"
    stage_sidecars="$build_output.stage-sidecars"
    trap 'rm -f "$build_output" "$failure_file" "$stage_sidecars"' EXIT

    if ! TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 \
        TWO_BRAIN_REC_INCLUDE_DRIVER_COMPONENT=0 \
        sh "$ROOT_DIR/apps/macos/Installer/Scripts/build-local-installer.sh" >"$build_output" 2>&1; then
        printf '%s\n' "default app-only package build failed" >> "$failure_file"
    fi

    component_dir="$ROOT_DIR/apps/macos/.build/installer/components"
    stage_app_dir="$ROOT_DIR/apps/macos/.build/installer/stage/app"
    distribution="$ROOT_DIR/apps/macos/.build/installer/distribution.xml"
    package="$ROOT_DIR/apps/macos/.build/installer/2brain-rec-local.pkg"

    [ -f "$package" ] || printf '%s\n' "missing local product package" >> "$failure_file"
    [ -f "$component_dir/2brain-rec-desktop-app.pkg" ] ||
        printf '%s\n' "missing desktop app component package" >> "$failure_file"
    if find "$component_dir" -maxdepth 1 -type f -name '*audio-driver*.pkg' | grep . >/dev/null 2>&1; then
        printf '%s\n' "audio-driver component package is present in default build" >> "$failure_file"
    fi
    if [ -f "$distribution" ] && rg -n "audio-driver|2brain-rec-audio-driver" "$distribution" >/dev/null 2>&1; then
        printf '%s\n' "distribution.xml contains audio-driver package references" >> "$failure_file"
    fi
    if find "$stage_app_dir" \( -name '._*' -o -name '.DS_Store' \) -print > "$stage_sidecars" &&
        [ -s "$stage_sidecars" ]; then
        printf '%s\n' "desktop app staging root contains AppleDouble or Finder sidecar files" >> "$failure_file"
        sed 's/^/stage sidecar: /' "$stage_sidecars" >> "$failure_file"
    fi

    append_run_header "$DRIVER_PARKED" "App-Only Installer Validator Run"
    {
        printf -- '- Mode: `--installer-app-only`\n'
        printf -- '- Package: `%s`\n' "$package"
        printf -- '- Component directory: `%s`\n' "$component_dir"
    } >> "$DRIVER_PARKED"

    if [ -s "$failure_file" ]; then
        {
            printf -- '- Validator result: `blocked`\n'
            printf -- '- Reason: default local package is not app-only.\n'
            printf -- '- Findings:\n'
            sed 's/^/  - /' "$failure_file"
            printf -- '- Build output tail:\n\n```text\n'
            tail -n 40 "$build_output"
            printf '```\n'
        } >> "$DRIVER_PARKED"
        printf '%s\n' "system_audio_capture_pivot_validation=blocked"
        printf '%s\n' "reason=default local package is not app-only"
        cat "$failure_file"
        exit 2
    fi

    {
        printf -- '- Validator result: `passed`\n'
        printf -- '- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.\n'
    } >> "$DRIVER_PARKED"

    passed "default local package is app-only"
}

validate_review_evidence() {
    require_file "$PERMISSION_MATRIX"
    require_file "$ARTIFACT_MATRIX"
    require_file "$CPU_GATES"
    require_file "$NO_HAL"
    require_file "$DEV_DURATION"
    require_file "$RELEASE_DURATION"

    ensure_no_forbidden_hal_requirement

    if [ ! -f "$SCOPE_REVIEW" ]; then
        cat > "$SCOPE_REVIEW" <<'EOF'
# Scope Review

Feature: `025-system-audio-capture-pivot`

Final review is pending until permission, artifact, CPU, 30-minute, and
75-minute evidence gates pass. Blocked, failed, degraded, and not-tested rows
are not acceptance.
EOF
    fi

    incomplete=0
    for path in "$PERMISSION_MATRIX" "$DEV_DURATION" "$RELEASE_DURATION"; do
        rows="$(count_not_tested_rows "$path")"
        if [ "$rows" != "0" ]; then
            printf '%s\n' "$path has $rows not-tested row(s)"
            incomplete=1
        fi
    done
    if ! has_controlled_artifact_acceptance "$ARTIFACT_MATRIX"; then
        rows="$(count_not_tested_rows "$ARTIFACT_MATRIX")"
        if [ "$rows" != "0" ]; then
            printf '%s\n' "$ARTIFACT_MATRIX has $rows not-tested row(s)"
            incomplete=1
        fi
    fi

    permission_rows="$(count_accepted_permission_rows "$PERMISSION_MATRIX")"
    if [ "$permission_rows" != "5" ]; then
        printf '%s\n' "$PERMISSION_MATRIX has $permission_rows accepted permission row(s), expected 5"
        incomplete=1
    fi

    artifact_rows="$(count_accepted_artifact_rows "$ARTIFACT_MATRIX")"
    if [ "$artifact_rows" != "5" ] && ! has_controlled_artifact_acceptance "$ARTIFACT_MATRIX"; then
        printf '%s\n' "$ARTIFACT_MATRIX has $artifact_rows accepted artifact row(s), expected 5 or explicit controlled-artifact acceptance"
        incomplete=1
    fi

    dev_duration_rows="$(count_accepted_duration_rows "$DEV_DURATION" 30)"
    if [ "$dev_duration_rows" = "0" ]; then
        printf '%s\n' "$DEV_DURATION has no accepted 30-minute row with all required gates passed"
        incomplete=1
    fi

    release_duration_rows="$(count_accepted_duration_rows "$RELEASE_DURATION" 75)"
    if [ "$release_duration_rows" = "0" ]; then
        printf '%s\n' "$RELEASE_DURATION has no accepted 75-minute row with all required gates passed"
        incomplete=1
    fi

    no_hal_status="$(latest_no_hal_status)"
    if [ "$no_hal_status" != "passed" ]; then
        printf '%s\n' "$NO_HAL latest No-HAL MVP Boundary status is not passed: ${no_hal_status:-missing}"
        incomplete=1
    fi

    for phase in idle activeRecording stop quit; do
        validate_cpu_phase_passed "$phase" || incomplete=1
    done

    if ! has_exact_line_after_header "$SCOPE_REVIEW" "## Final Accepted Scope Review" "- Final scope review: accepted"; then
        printf '%s\n' "$SCOPE_REVIEW is missing final accepted scope review marker"
        incomplete=1
    fi
    if ! has_exact_line_after_header "$SCOPE_REVIEW" "## Final Accepted Scope Review" "- Reviewed against quickstart and contracts: yes"; then
        printf '%s\n' "$SCOPE_REVIEW is missing quickstart/contracts review marker"
        incomplete=1
    fi
    if ! has_exact_line_after_header "$SCOPE_REVIEW" "## Final Accepted Scope Review" "- Evidence traceability: #307/T071 #308/T072 #309/T073 #310/T074 #311/T075 #312/T076 #313/T077"; then
        printf '%s\n' "$SCOPE_REVIEW is missing final evidence traceability marker"
        incomplete=1
    fi

    if [ "$incomplete" -ne 0 ]; then
        blocked "final evidence review is incomplete; keep #313/T077 open"
    fi

    passed "all final evidence gates are present and accepted"
}

mode="${1:-}"
case "$mode" in
    -h|--help|"")
        usage
        exit 0
        ;;
    --permission-matrix)
        validate_permission_matrix
        ;;
    --artifact-matrix)
        validate_artifact_matrix
        ;;
    --artifact-directory)
        validate_artifact_directory "${2:-}"
        ;;
    --latest-artifact-directory)
        latest_completed_artifact_directory
        ;;
    --validate-latest-artifact)
        validate_latest_artifact_directory
        ;;
    --duration-minutes)
        [ "${2:-}" ] || fail_invalid "--duration-minutes requires a number"
        manual_release=false
        [ "${3:-}" != "--manual-release" ] || manual_release=true
        validate_duration "$2" "$manual_release"
        ;;
    --installer-app-only)
        validate_installer_app_only
        ;;
    --review-evidence)
        validate_review_evidence
        ;;
    --self-test-cpu-evidence)
        self_test_cpu_evidence
        ;;
    --self-test-artifact-metadata)
        self_test_artifact_metadata
        ;;
    --self-test-latest-artifact-selection)
        self_test_latest_artifact_selection
        ;;
    --self-test-duration-evidence)
        self_test_duration_evidence
        ;;
    --self-test-permission-evidence)
        self_test_permission_evidence
        ;;
    --self-test-review-evidence)
        self_test_review_evidence
        ;;
    *)
        fail_invalid "unknown mode: $mode"
        ;;
esac
