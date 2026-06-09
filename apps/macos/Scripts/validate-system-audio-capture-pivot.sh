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

        mtime="$(stat -f "%m" "$directory" 2>/dev/null || printf '0')"
        case "$mtime" in
            *[!0-9]*|"") mtime=0 ;;
        esac
        [ "$mtime" -ge "$min_mtime" ] || continue
        if [ -z "$latest_mtime" ] || [ "$mtime" -gt "$latest_mtime" ]; then
            latest_mtime="$mtime"
            latest_directory="$directory"
        fi
    done

    [ -n "$latest_directory" ] ||
        blocked "no completed local recording directories with manifest.json, mic.wav, and incoming.wav found under: $root after epoch: $min_mtime"

    printf '%s\n' "$latest_directory"
}

count_not_tested_rows() {
    path="$1"
    grep -c '| not-tested |' "$path" 2>/dev/null || true
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
            if (duration == minutes " minutes" &&
                scope == "passed" &&
                mic == "passed" &&
                incoming == "passed" &&
                alignment == "passed" &&
                cpu == "passed" &&
                responsiveness == "passed" &&
                release == "passed" &&
                result == "passed") {
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

validate_cpu_phase_passed() {
    phase="$1"
    evaluation="$(last_cpu_evaluation_for_phase "$phase")"
    if [ -z "$evaluation" ]; then
        printf '%s\n' "$CPU_GATES is missing $phase CPU evaluation"
        return 1
    fi
    case "$evaluation" in
        status=passed\ *)
            return 0
            ;;
        *)
            printf '%s\n' "$CPU_GATES latest $phase CPU evaluation is not passed: $evaluation"
            return 1
            ;;
    esac
}

ensure_no_forbidden_hal_requirement() {
    if rg -n "HAL runtime probe|required virtual device|driver reinstall required|coreaudiod restart" \
        "$PERMISSION_MATRIX" "$ARTIFACT_MATRIX" "$DEV_DURATION" "$RELEASE_DURATION" "$SCOPE_REVIEW" \
        >/dev/null 2>&1; then
        blocked "evidence contains forbidden HAL/virtual-device recovery wording"
    fi
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
        printf -- '- Safe checks: required rows present; `incoming.wav` remains `remoteSpeaker` with `systemAudio` metadata; blocked/degraded/not-tested rows are not counted as acceptance.\n'
    } >> "$ARTIFACT_MATRIX"

    ensure_no_forbidden_hal_requirement
    remaining="$(count_not_tested_rows "$ARTIFACT_MATRIX")"
    [ "$remaining" = "0" ] ||
        blocked "artifact matrix still has $remaining not-tested row(s); keep #308/T072 open"

    accepted_rows="$(count_accepted_artifact_rows "$ARTIFACT_MATRIX")"
    [ "$accepted_rows" = "5" ] ||
        blocked "artifact matrix has $accepted_rows accepted row(s), expected 5 required artifact scenarios with Result passed; keep #308/T072 open"

    passed "artifact matrix has accepted evidence for all required scenarios"
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
    check_jq '([.tracks[] | select(.role == "localMic") | .durationMs] | length) == 1 and ([.tracks[] | select(.role == "remoteSpeaker") | .durationMs] | length) == 1 and ([.tracks[] | select(.role == "localMic") | .durationMs][0] | type) == "number" and ([.tracks[] | select(.role == "remoteSpeaker") | .durationMs][0] | type) == "number"' "manifest must contain exactly one numeric durationMs for localMic and remoteSpeaker"
    check_jq '([.tracks[] | select(.role == "localMic") | .durationMs][0]) as $mic | ([.tracks[] | select(.role == "remoteSpeaker") | .durationMs][0]) as $incoming | (($mic - $incoming) as $diff | (if $diff < 0 then -$diff else $diff end) as $abs | ($abs <= 3000 and .durationDifferenceSeconds == ($abs / 1000)))' "durationDifferenceSeconds must equal the absolute mic/incoming duration difference and be <= 3"
    check_jq '.scopeApproval != null' "scopeApproval must be present"
    check_jq '.scopeApproval.approvedBy == "user" and .scopeApproval.notTriggerForBackgroundAudio == true' "scopeApproval must be user-approved and not a background-audio trigger"
    check_jq '.permissions.microphone == "granted"' "microphone permission must be granted"
    check_jq '.permissions.systemAudio == "granted"' "system audio permission must be granted"
    check_jq '([.tracks[].role] | sort) == ["localMic","remoteSpeaker"]' "tracks must contain localMic and remoteSpeaker"
    check_jq 'any(.tracks[]; .role == "localMic" and (.trackId | type) == "string" and (.trackId | length) > 0 and .sourceKind == "microphone" and .mediaScribeField == "mic_file" and .status == "saved" and .fileName == "mic.wav" and .format == "wav-pcm-s16le" and .sampleRate == 16000 and .channelCount == 1 and .bitsPerSample == 16 and .timelineStartMs == 0 and .timelineAligned == true and .failureReason == "none" and .byteCount > 0 and .frameCount > 0 and .durationMs > 0)' "localMic track must be saved microphone wav-pcm-s16le metadata"
    check_jq 'any(.tracks[]; .role == "remoteSpeaker" and (.trackId | type) == "string" and (.trackId | length) > 0 and .sourceKind == "systemAudio" and .mediaScribeField == "incoming_file" and .status == "saved" and .fileName == "incoming.wav" and .format == "wav-pcm-s16le" and .sampleRate == 16000 and .channelCount == 1 and .bitsPerSample == 16 and .timelineStartMs == 0 and .timelineAligned == true and .failureReason == "none" and .byteCount > 0 and .frameCount > 0 and .durationMs > 0)' "remoteSpeaker track must be saved systemAudio wav-pcm-s16le metadata"

    validate_wav_metadata "$mic" "localMic" "mic.wav"
    validate_wav_metadata "$incoming" "remoteSpeaker" "incoming.wav"

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
    fmt="$(wav_ascii "$file" 12)"
    data_marker="$(wav_ascii "$file" 36)"
    riff_byte_count="$(wav_u32_le "$file" 4)"
    fmt_byte_count="$(wav_u32_le "$file" 16)"
    audio_format="$(wav_u16_le "$file" 20)"
    wav_channel_count="$(wav_u16_le "$file" 22)"
    wav_sample_rate="$(wav_u32_le "$file" 24)"
    byte_rate="$(wav_u32_le "$file" 28)"
    block_align="$(wav_u16_le "$file" 32)"
    wav_bits_per_sample="$(wav_u16_le "$file" 34)"
    data_bytes="$(wav_u32_le "$file" 40)"

    [ "$riff" = "RIFF" ] || printf '%s\n' "$file_name WAV header must start with RIFF" >> "$failure_file"
    [ "$wave" = "WAVE" ] || printf '%s\n' "$file_name WAV header must contain WAVE" >> "$failure_file"
    [ "$fmt" = "fmt " ] || printf '%s\n' "$file_name WAV header must contain fmt chunk" >> "$failure_file"
    [ "$data_marker" = "data" ] || printf '%s\n' "$file_name WAV header must contain data chunk at byte 36" >> "$failure_file"
    [ "$audio_format" = "1" ] || printf '%s\n' "$file_name WAV audio format must be PCM" >> "$failure_file"
    [ "$wav_sample_rate" = "$manifest_sample_rate" ] || printf '%s\n' "$file_name WAV sampleRate must equal manifest sampleRate" >> "$failure_file"
    [ "$wav_channel_count" = "$manifest_channel_count" ] || printf '%s\n' "$file_name WAV channelCount must equal manifest channelCount" >> "$failure_file"
    [ "$wav_bits_per_sample" = "$manifest_bits_per_sample" ] || printf '%s\n' "$file_name WAV bitsPerSample must equal manifest bitsPerSample" >> "$failure_file"

    expected_block_align=$((manifest_channel_count * manifest_bits_per_sample / 8))
    expected_byte_rate=$((manifest_sample_rate * expected_block_align))
    expected_data_bytes=$((manifest_frame_count * expected_block_align))
    expected_file_bytes=$((44 + expected_data_bytes))
    expected_riff_byte_count=$((expected_file_bytes - 8))
    expected_duration_ms=$((manifest_frame_count * 1000 / manifest_sample_rate))

    [ "$block_align" = "$expected_block_align" ] || printf '%s\n' "$file_name WAV blockAlign must match manifest format" >> "$failure_file"
    [ "$byte_rate" = "$expected_byte_rate" ] || printf '%s\n' "$file_name WAV byteRate must match manifest format" >> "$failure_file"
    [ "$riff_byte_count" = "$expected_riff_byte_count" ] || printf '%s\n' "$file_name WAV RIFF byte count must match file size" >> "$failure_file"
    [ "$fmt_byte_count" = "16" ] || printf '%s\n' "$file_name WAV fmt chunk size must be 16 for PCM" >> "$failure_file"
    [ "$data_bytes" = "$expected_data_bytes" ] || printf '%s\n' "$file_name WAV data byte count must match manifest frameCount" >> "$failure_file"
    [ "$file_bytes" = "$expected_file_bytes" ] || printf '%s\n' "$file_name file size must equal 44-byte header plus manifest data bytes" >> "$failure_file"
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
    trap 'rm -f "$build_output" "$failure_file"' EXIT

    if ! TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 \
        TWO_BRAIN_REC_INCLUDE_DRIVER_COMPONENT=0 \
        sh "$ROOT_DIR/apps/macos/Installer/Scripts/build-local-installer.sh" >"$build_output" 2>&1; then
        printf '%s\n' "default app-only package build failed" >> "$failure_file"
    fi

    component_dir="$ROOT_DIR/apps/macos/.build/installer/components"
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
        printf -- '- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.\n'
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
    for path in "$PERMISSION_MATRIX" "$ARTIFACT_MATRIX" "$DEV_DURATION" "$RELEASE_DURATION"; do
        rows="$(count_not_tested_rows "$path")"
        if [ "$rows" != "0" ]; then
            printf '%s\n' "$path has $rows not-tested row(s)"
            incomplete=1
        fi
    done

    permission_rows="$(count_accepted_permission_rows "$PERMISSION_MATRIX")"
    if [ "$permission_rows" != "5" ]; then
        printf '%s\n' "$PERMISSION_MATRIX has $permission_rows accepted permission row(s), expected 5"
        incomplete=1
    fi

    artifact_rows="$(count_accepted_artifact_rows "$ARTIFACT_MATRIX")"
    if [ "$artifact_rows" != "5" ]; then
        printf '%s\n' "$ARTIFACT_MATRIX has $artifact_rows accepted artifact row(s), expected 5"
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

    for phase in idle activeRecording stop quit; do
        validate_cpu_phase_passed "$phase" || incomplete=1
    done

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
    *)
        fail_invalid "unknown mode: $mode"
        ;;
esac
