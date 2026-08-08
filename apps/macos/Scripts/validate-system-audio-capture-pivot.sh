#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")/../../.." && pwd)

usage() {
    echo "validate-system-audio-capture-pivot.sh"
    echo
    echo "Metadata-only validator for the active v5 local recording package."
    echo "It never starts capture, decodes audio, changes TCC or writes evidence."
    echo
    echo "Modes:"
    echo "  --artifact-directory <path>       validate one completed v5 package"
    echo "  --latest-artifact-directory       print the newest completed v5 package"
    echo "  --validate-latest-artifact        validate that newest package"
    echo "  --installer-app-only              build and inspect the app-only package"
    echo "  --self-test-artifact-metadata     run temporary v5 metadata parser checks"
    echo "  --self-test-latest-artifact-selection"
    echo "                                    run temporary v5 selection checks"
    echo
    echo "The required final members are manifest.json, meeting-transcription.wav"
    echo "and meeting-review.m4a. Historic v3/v4 packages are intentionally not"
    echo "accepted by this new-recording validator."
}

fail_invalid() {
    echo "v5_recording_package_validation=invalid"
    echo "reason=$1"
    exit 3
}

blocked() {
    echo "v5_recording_package_validation=blocked"
    echo "reason=$1"
    exit 2
}

passed() {
    echo "v5_recording_package_validation=passed"
    echo "detail=$1"
}

require_file() {
    [ -f "$1" ] || fail_invalid "missing required file: $1"
}

recordings_root() {
    if [ -n "${GRAF_RECORDINGS_DIR-}" ]; then
        echo "$GRAF_RECORDINGS_DIR"
    else
        echo "$HOME/Library/Application Support/GRAF/Recordings"
    fi
}

file_mtime() {
    stat -f "%m" "$1" 2>/dev/null || echo 0
}

latest_completed_artifact_directory() {
    root=$(recordings_root)
    [ -d "$root" ] || blocked "recordings directory does not exist"
    min_mtime=${GRAF_RECORDING_MIN_ARTIFACT_MTIME:-0}
    case "$min_mtime" in
        *[!0-9]*|"") fail_invalid "GRAF_RECORDING_MIN_ARTIFACT_MTIME must be epoch seconds" ;;
    esac

    latest_directory=""
    latest_mtime=0
    for directory in "$root"/*; do
        [ -d "$directory" ] || continue
        [ -f "$directory/manifest.json" ] || continue
        [ -f "$directory/meeting-transcription.wav" ] || continue
        [ -f "$directory/meeting-review.m4a" ] || continue
        manifest_mtime=$(file_mtime "$directory/manifest.json")
        wav_mtime=$(file_mtime "$directory/meeting-transcription.wav")
        m4a_mtime=$(file_mtime "$directory/meeting-review.m4a")
        [ "$manifest_mtime" -ge "$min_mtime" ] || continue
        [ "$wav_mtime" -ge "$min_mtime" ] || continue
        [ "$m4a_mtime" -ge "$min_mtime" ] || continue
        if [ "$manifest_mtime" -gt "$latest_mtime" ]; then
            latest_directory=$directory
            latest_mtime=$manifest_mtime
        fi
    done

    [ -n "$latest_directory" ] ||
        blocked "no completed v5 package exists after the requested minimum mtime"
    echo "$latest_directory"
}

u16_le_at() {
    od -An -j "$2" -N 2 -t u2 "$1" 2>/dev/null | tr -d " "
}

u32_le_at() {
    od -An -j "$2" -N 4 -t u4 "$1" 2>/dev/null | tr -d " "
}

ascii_at() {
    dd if="$1" bs=1 skip="$2" count=4 2>/dev/null
}

validate_wav_header() {
    wav=$1
    require_file "$wav"
    [ "$(ascii_at "$wav" 0)" = "RIFF" ] || fail_invalid "canonical WAV is missing RIFF header"
    [ "$(ascii_at "$wav" 8)" = "WAVE" ] || fail_invalid "canonical WAV is missing WAVE header"
    [ "$(ascii_at "$wav" 12)" = "fmt " ] || fail_invalid "canonical WAV is missing fmt chunk"
    [ "$(u16_le_at "$wav" 20)" = "1" ] || fail_invalid "canonical WAV must be PCM"
    [ "$(u16_le_at "$wav" 22)" = "1" ] || fail_invalid "canonical WAV must be mono"
    [ "$(u32_le_at "$wav" 24)" = "16000" ] || fail_invalid "canonical WAV must be 16 kHz"
    [ "$(u16_le_at "$wav" 34)" = "16" ] || fail_invalid "canonical WAV must be s16le"
    [ "$(ascii_at "$wav" 36)" = "data" ] || fail_invalid "canonical WAV is missing data chunk"
    [ "$(u32_le_at "$wav" 40)" -gt 0 ] || fail_invalid "canonical WAV has no frames"
}

validate_review_m4a_metadata() {
    review=$1
    require_file "$review"
    command -v afinfo >/dev/null 2>&1 ||
        blocked "afinfo is required to inspect review M4A metadata on macOS"
    metadata=$(afinfo "$review" 2>&1) ||
        fail_invalid "review M4A cannot be read by the macOS metadata inspector"
    echo "$metadata" | grep -E "Data format: 1 ch, (48000|48,000) Hz, 'aac '" >/dev/null ||
        fail_invalid "review M4A must be AAC mono 48 kHz"
}

validate_manifest_contract() {
    manifest=$1
    command -v jq >/dev/null 2>&1 || fail_invalid "jq is required for manifest metadata validation"
    jq empty "$manifest" >/dev/null 2>&1 || fail_invalid "manifest.json is not valid JSON"

    if ! jq -e '
        .schemaVersion == "local-recording-manifest.v5" and
        .manifestFileName == "manifest.json" and
        .status == "saved" and
        .transcriptionReadiness == "ready" and
        .mediaScribeSourceMode == "single_wav_v1" and
        .canonicalMixProfile == "canonical-mix.v1" and
        .externalEgressStarted == false and
        .transcriptionStarted == false and
        .diagnosticSafe == true and
        .failureReason == "none" and
        .scopeApproval != null and
        .permissions.microphone == "granted" and
        .permissions.systemAudio == "granted" and
        ([.tracks[].role] | sort) == ["mixed_meeting_audio", "review_playback"] and
        ([.tracks[] | select(
            .role == "mixed_meeting_audio" and
            .sourceKind == "canonical_mix" and
            .mediaScribeField == "media_file" and
            .fileName == "meeting-transcription.wav" and
            .format == "wav-pcm-s16le" and
            .sampleRate == 16000 and
            .channelCount == 1 and
            .bitsPerSample == 16 and
            .timelineStartMs == 0 and
            .timelineAligned == true and
            .status == "saved"
        )] | length) == 1 and
        ([.tracks[] | select(
            .role == "review_playback" and
            .sourceKind == "canonical_mix" and
            .mediaScribeField == "playback_file" and
            .fileName == "meeting-review.m4a" and
            .format == "m4a-aac-lc" and
            .sampleRate == 48000 and
            .channelCount == 1 and
            .timelineStartMs == 0 and
            .timelineAligned == true and
            .status == "saved"
        )] | length) == 1
    ' "$manifest" >/dev/null; then
        fail_invalid "manifest does not describe one complete v5 WAV and review M4A package"
    fi

    for forbidden_key in rawAudio audioSnippet transcriptText meetingContent credentials apiKey tokens signedUrls password absolutePath liveSecretPath; do
        if ! jq -e --arg forbidden_key "$forbidden_key" '[paths | select(.[-1] == $forbidden_key)] | length == 0' "$manifest" >/dev/null; then
            fail_invalid "manifest contains forbidden content-bearing field"
        fi
    done
}

validate_artifact_directory() {
    directory=$1
    [ -n "$directory" ] || fail_invalid "--artifact-directory requires a path"
    [ -d "$directory" ] || fail_invalid "artifact directory does not exist"

    manifest=$directory/manifest.json
    wav=$directory/meeting-transcription.wav
    review=$directory/meeting-review.m4a
    require_file "$manifest"
    require_file "$wav"
    require_file "$review"

    unexpected_count=$(find "$directory" -mindepth 1 -maxdepth 1 \
        ! -name manifest.json \
        ! -name meeting-transcription.wav \
        ! -name meeting-review.m4a | wc -l | tr -d " ")
    [ "$unexpected_count" = "0" ] ||
        fail_invalid "v5 package contains an unexpected or partial artifact"

    validate_manifest_contract "$manifest"
    if [ "${GRAF_V5_SKIP_MEDIA_PROBE-0}" != "1" ]; then
        validate_wav_header "$wav"
        validate_review_m4a_metadata "$review"
    fi
    passed "v5 manifest, final member set and media metadata are valid"
}

write_self_test_manifest() {
    target=$1
    echo '{"schemaVersion":"local-recording-manifest.v5","manifestFileName":"manifest.json","status":"saved","transcriptionReadiness":"ready","mediaScribeSourceMode":"single_wav_v1","canonicalMixProfile":"canonical-mix.v1","externalEgressStarted":false,"transcriptionStarted":false,"diagnosticSafe":true,"failureReason":"none","scopeApproval":{"scopeApprovalId":"safe-test"},"permissions":{"microphone":"granted","systemAudio":"granted"},"tracks":[{"role":"mixed_meeting_audio","sourceKind":"canonical_mix","mediaScribeField":"media_file","fileName":"meeting-transcription.wav","format":"wav-pcm-s16le","sampleRate":16000,"channelCount":1,"bitsPerSample":16,"timelineStartMs":0,"timelineAligned":true,"status":"saved"},{"role":"review_playback","sourceKind":"canonical_mix","mediaScribeField":"playback_file","fileName":"meeting-review.m4a","format":"m4a-aac-lc","sampleRate":48000,"channelCount":1,"bitsPerSample":0,"timelineStartMs":0,"timelineAligned":true,"status":"saved"}]}' > "$target"
}

make_self_test_package() {
    directory=$1
    mkdir -p "$directory"
    write_self_test_manifest "$directory/manifest.json"
    : > "$directory/meeting-transcription.wav"
    : > "$directory/meeting-review.m4a"
}

self_test_artifact_metadata() {
    temporary_root=$(mktemp -d)
    trap 'rm -rf "$temporary_root"' EXIT HUP INT TERM
    package=$temporary_root/package
    make_self_test_package "$package"

    if ! (GRAF_V5_SKIP_MEDIA_PROBE=1 validate_artifact_directory "$package") >/dev/null; then
        fail_invalid "temporary v5 package metadata did not validate"
    fi
    : > "$package/unexpected.wav"
    if (GRAF_V5_SKIP_MEDIA_PROBE=1 validate_artifact_directory "$package") >/dev/null 2>&1; then
        fail_invalid "unexpected artifact was accepted by v5 validator"
    fi
    passed "temporary v5 metadata rejects non-v5 members"
}

self_test_latest_artifact_selection() {
    temporary_root=$(mktemp -d)
    trap 'rm -rf "$temporary_root"' EXIT HUP INT TERM
    make_self_test_package "$temporary_root/older"
    make_self_test_package "$temporary_root/newer"
    touch -t 202607160101 "$temporary_root/older/manifest.json" "$temporary_root/older/meeting-transcription.wav" "$temporary_root/older/meeting-review.m4a"
    touch -t 202607160102 "$temporary_root/newer/manifest.json" "$temporary_root/newer/meeting-transcription.wav" "$temporary_root/newer/meeting-review.m4a"
    selected=$(GRAF_RECORDINGS_DIR="$temporary_root" latest_completed_artifact_directory)
    [ "$selected" = "$temporary_root/newer" ] ||
        fail_invalid "newest completed v5 package was not selected"
    passed "temporary v5 latest-package selection passed"
}

validate_installer_app_only() {
    build_output=$(mktemp)
    trap 'rm -f "$build_output"' EXIT HUP INT TERM
    if ! GRAF_ALLOW_ADHOC_APP_SIGNING=1 \
        sh "$ROOT_DIR/apps/macos/Installer/Scripts/build-local-installer.sh" > "$build_output" 2>&1; then
        tail -n 40 "$build_output"
        blocked "local app-only package build failed"
    fi

    component_dir=$ROOT_DIR/apps/macos/.build/installer/components
    stage_app_dir=$ROOT_DIR/apps/macos/.build/installer/stage/app
    product_package=$ROOT_DIR/apps/macos/.build/installer/graf-local.pkg
    [ -f "$product_package" ] || blocked "local product package is missing"
    [ -f "$component_dir/graf-desktop-app.pkg" ] || blocked "desktop app component package is missing"
    component_count=$(find "$component_dir" -maxdepth 1 -type f -name "*.pkg" | wc -l | tr -d " ")
    [ "$component_count" = "1" ] || blocked "installer contains more than one component package"
    [ -d "$stage_app_dir/GRAF.app" ] || blocked "staged application bundle is missing"
    if find "$stage_app_dir" -type d -name "*.driver" -o -type d -name "*.plugin" | grep -q .; then
        blocked "app-only package contains an audio component"
    fi
    passed "local installer contains one desktop app component and was not installed"
}

mode=""
if [ "$#" -gt 0 ]; then
    mode=$1
fi

case "$mode" in
    -h|--help|"")
        usage
        ;;
    --artifact-directory)
        [ "$#" -eq 2 ] || fail_invalid "--artifact-directory requires a path"
        validate_artifact_directory "$2"
        ;;
    --latest-artifact-directory)
        latest_completed_artifact_directory
        ;;
    --validate-latest-artifact)
        validate_artifact_directory "$(latest_completed_artifact_directory)"
        ;;
    --installer-app-only)
        validate_installer_app_only
        ;;
    --self-test-artifact-metadata)
        self_test_artifact_metadata
        ;;
    --self-test-latest-artifact-selection)
        self_test_latest_artifact_selection
        ;;
    *)
        fail_invalid "unknown mode: $mode"
        ;;
esac
