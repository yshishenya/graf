#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
EVIDENCE_DIR="$ROOT_DIR/specs/025-system-audio-capture-pivot/evidence"

case "${1:-}" in
  -h|--help)
    cat <<'USAGE'
validate-system-audio-no-hal-probe.sh

Validates that the system-audio MVP recording acceptance path does not depend
on HAL virtual-device publication, driver repair, Core Audio restart, or
runtime route probes.

The scan is intentionally scoped to the new system-audio acceptance files.
Legacy driver/readiness UI can still exist while the pivot is being completed,
but it must not be required by this MVP recording path.
USAGE
    exit 0
    ;;
esac

mkdir -p "$EVIDENCE_DIR"

targets="
apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift
apps/macos/RecApp/Sources/Capture/MicrophoneCaptureService.swift
apps/macos/RecApp/Sources/Capture/CaptureScopeApprovalService.swift
apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift
apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift
apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift
apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift
"

patterns='startExperimentalRoute|PassthroughRouteEngine|CoreAudioSystemSnapshot|install_or_repair_driver|driverReloaded|needsRepair|CoreAudio.*restart|virtual.*selection.*required|HAL.*probe.*required|SharedMemoryRecordingSampleSource'

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

for target in $targets; do
  if [ -f "$ROOT_DIR/$target" ]; then
    if grep -nE "$patterns" "$ROOT_DIR/$target" | grep -vE 'NoHAL|no-HAL|halProbeObserved|halRuntimeProbeExecuted|passesMVPBoundary|SystemAudioNoHALEvidence' > "$tmp_file.match"; then
      sed "s#^#$target:#" "$tmp_file.match" >> "$tmp_file"
    fi
    rm -f "$tmp_file.match"
  fi
done

checked_count="$(printf '%s\n' "$targets" | awk 'NF { count += 1 } END { print count + 0 }')"
if [ -s "$tmp_file" ]; then
  status="failed"
  reason="halProbeObserved"
else
  status="passed"
  reason="none"
fi

{
  printf '\n## %s No-HAL MVP Boundary\n\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  printf '%s\n' "- Command: \`$0\`"
  printf '%s\n' "- Checked files: \`$checked_count\`"
  printf '%s\n' "- Status: \`$status\`"
  printf '%s\n\n' "- Failure reason: \`$reason\`"
  if [ -s "$tmp_file" ]; then
    printf 'Forbidden matches:\n\n```text\n'
    cat "$tmp_file"
    printf '```\n'
  else
    printf 'No forbidden runtime route/HAL dependencies found in the system-audio acceptance path.\n'
  fi
} >> "$EVIDENCE_DIR/no-hal-probe.md"

printf 'system_audio_no_hal_probe_validation=%s\n' "$status"
printf 'failureReason=%s\n' "$reason"
printf 'checkedFiles=%s\n' "$checked_count"
if [ -s "$tmp_file" ]; then
  cat "$tmp_file" >&2
  exit 1
fi
