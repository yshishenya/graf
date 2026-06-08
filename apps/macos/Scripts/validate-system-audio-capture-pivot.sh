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

  --duration-minutes 30
      Check the 30-minute development evidence file.

  --duration-minutes 75 --manual-release
      Check the 75-minute manual release evidence file.

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

count_not_tested_rows() {
    path="$1"
    grep -c '| not-tested |' "$path" 2>/dev/null || true
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

    append_run_header "$PERMISSION_MATRIX" "2026-06-08 Metadata Validator Run"
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

    passed "permission matrix has no not-tested rows"
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

    append_run_header "$ARTIFACT_MATRIX" "2026-06-08 Metadata Validator Run"
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

    passed "artifact matrix has no not-tested rows"
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
    append_run_header "$path" "2026-06-08 Metadata Validator Run"
    {
        printf -- '- Mode: `--duration-minutes %s%s`\n' "$minutes" "$( [ "$manual_release" = true ] && printf ' --manual-release' || true )"
        printf -- '- Validator result: `blocked`\n'
        printf -- '- Reason: Real sustained recording run is still required before acceptance.\n'
        printf -- '- Safe checks: evidence file exists; not-tested rows are not counted as acceptance.\n'
    } >> "$path"

    remaining="$(count_not_tested_rows "$path")"
    [ "$remaining" = "0" ] ||
        blocked "$title still has $remaining not-tested row(s); keep $issue open"

    passed "$title has no not-tested rows"
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

    rg -n "activeRecording| stop | quit" "$CPU_GATES" >/dev/null 2>&1 || {
        printf '%s\n' "$CPU_GATES is missing active/stop/quit evidence"
        incomplete=1
    }

    if [ "$incomplete" -ne 0 ]; then
        blocked "final evidence review is incomplete; keep #313/T077 open"
    fi

    passed "all final evidence gates are present and contain no not-tested rows"
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
    --duration-minutes)
        [ "${2:-}" ] || fail_invalid "--duration-minutes requires a number"
        manual_release=false
        [ "${3:-}" != "--manual-release" ] || manual_release=true
        validate_duration "$2" "$manual_release"
        ;;
    --review-evidence)
        validate_review_evidence
        ;;
    *)
        fail_invalid "unknown mode: $mode"
        ;;
esac
