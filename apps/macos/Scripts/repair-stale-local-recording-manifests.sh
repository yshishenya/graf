#!/bin/sh
set -eu

ROOT="${GRAF_RECORDINGS_DIR:-${TWO_BRAIN_REC_RECORDINGS_DIR:-$HOME/Library/Application Support/GRAF/Recordings}}"
MODE="dry-run"

usage() {
    cat <<'USAGE'
repair-stale-local-recording-manifests.sh

Repairs stale local recording manifest metadata where the recording or track
truth is degraded/failed, but nested captureHealth still says passed/none.

This tool is metadata-only. It does not inspect audio content and does not
rewrite WAV files.

Usage:
  repair-stale-local-recording-manifests.sh [--root <recordings-dir>] [--dry-run]
  repair-stale-local-recording-manifests.sh [--root <recordings-dir>] --apply

Safety:
  --dry-run is the default and only reports stale manifests.
  --apply creates manifest.json.capture-health-repair.<timestamp>.bak next to
  each changed manifest before writing repaired JSON.
USAGE
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --root)
            [ "$#" -ge 2 ] || { usage >&2; exit 3; }
            ROOT="$2"
            shift 2
            ;;
        --dry-run)
            MODE="dry-run"
            shift
            ;;
        --apply)
            MODE="apply"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage >&2
            exit 3
            ;;
    esac
done

[ -d "$ROOT" ] || {
    printf 'manifest_repair=blocked\n'
    printf 'reason=recordings directory does not exist: %s\n' "$ROOT"
    exit 2
}

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

/usr/bin/python3 - "$ROOT" "$MODE" "$STAMP" <<'PY'
import json
import os
import shutil
import sys
from pathlib import Path

root = Path(sys.argv[1])
mode = sys.argv[2]
stamp = sys.argv[3]

gate_for_reason = {
    "none": "passed",
    "permission_denied": "blocked",
    "scope_unavailable": "blocked",
    "protected_audio_blocked": "blocked",
    "directory_unavailable": "failed",
    "capture_failed": "failed",
    "write_failed": "failed",
    "finalization_failed": "failed",
    "timeline_misaligned": "failed",
    "cpu_gate_failed": "failed",
    "hal_probe_observed": "failed",
    "device_unavailable": "failed",
    "app_closed": "failed",
    "empty_required_track": "degraded",
    "format_not_ready": "degraded",
    "silent_input": "degraded",
    "no_frames": "degraded",
    "stopped_before_frames": "degraded",
    "legacy_not_ready": "degraded",
    "unknown": "degraded",
}

def resolved_reason(manifest):
    reason = manifest.get("failureReason") or "none"
    if reason != "none":
        return reason
    for track in manifest.get("tracks") or []:
        track_reason = track.get("failureReason") or "none"
        if track_reason != "none":
            return track_reason
    if any(track.get("timelineAligned") is False for track in manifest.get("tracks") or []):
        return "timeline_misaligned"
    return "none"

checked = 0
stale = 0
repaired = 0
skipped_no_health = 0
errors = 0

for manifest_path in sorted(root.glob("*/manifest.json")):
    checked += 1
    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except Exception as exc:
        errors += 1
        print(f"error path={manifest_path} reason=json_decode_failed detail={exc}", file=sys.stderr)
        continue

    health = manifest.get("captureHealth")
    if not isinstance(health, dict):
        skipped_no_health += 1
        continue

    reason = resolved_reason(manifest)
    gate = gate_for_reason.get(reason, "degraded")
    current_reason = health.get("failureReason") or "none"
    current_gate = health.get("gateStatus") or "passed"
    if current_reason == reason and current_gate == gate:
        continue

    stale += 1
    print(
        "stale_manifest "
        f"path={manifest_path} "
        f"captureHealth={current_gate}/{current_reason} "
        f"expected={gate}/{reason}"
    )

    if mode == "apply":
        backup_path = manifest_path.with_name(f"{manifest_path.name}.capture-health-repair.{stamp}.bak")
        shutil.copy2(manifest_path, backup_path)
        health["failureReason"] = reason
        health["gateStatus"] = gate
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        repaired += 1
        print(f"repaired_manifest path={manifest_path} backup={backup_path}")

print(f"manifest_repair={mode}")
print(f"checked={checked}")
print(f"stale={stale}")
print(f"repaired={repaired}")
print(f"skipped_no_capture_health={skipped_no_health}")
print(f"errors={errors}")

if errors:
    sys.exit(1)
if mode == "dry-run" and stale:
    sys.exit(2)
PY
