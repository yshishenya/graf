#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  apps/macos/Scripts/validate-meeting-mute-truth.sh --fixtures
  apps/macos/Scripts/validate-meeting-mute-truth.sh --latest-artifact-directory [PATH]
  apps/macos/Scripts/validate-meeting-mute-truth.sh --runtime-proof [--output-root PATH]

Validates meeting mute-truth metadata. The validator must not accept raw audio,
transcripts, meeting notes, credentials, signed URLs, or participant speech.
USAGE
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
fixture_dir="$repo_root/apps/macos/Shared/Tests/Fixtures/MeetingMuteTruth"

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

mode="$1"
shift || true

if [[ "$mode" == "--runtime-proof" ]]; then
  proof_args=("--default-store")
  if [[ $# -gt 0 ]]; then
    if [[ "$1" == "--output-root" && $# -ge 2 ]]; then
      proof_args=("--output-root" "$2")
    else
      usage
      exit 2
    fi
  fi
  proof_output="$(swift run --package-path "$repo_root/apps/macos" MeetingMuteTruthRuntimeProof "${proof_args[@]}")"
  printf '%s\n' "$proof_output"
  proof_dir="$(printf '%s\n' "$proof_output" | sed -n 's/^directory=//p' | tail -1)"
  if [[ -z "$proof_dir" ]]; then
    echo "meeting-mute-truth runtime proof: missing output directory" >&2
    exit 1
  fi
  mode="--latest-artifact-directory"
  set -- "$proof_dir"
fi

python3 - "$mode" "$fixture_dir" "${1:-}" <<'PY'
import json
import os
import pathlib
import sys

mode = sys.argv[1]
fixture_dir = pathlib.Path(sys.argv[2])
explicit_artifact = pathlib.Path(sys.argv[3]).expanduser() if len(sys.argv) > 3 and sys.argv[3] else None

FORBIDDEN_KEYS = {
    "rawAudio",
    "audioSnippet",
    "transcriptText",
    "meetingContent",
    "meetingNotes",
    "participantSpeech",
    "rawTranscript",
    "mediaScribeApiKey",
    "apiKey",
    "signedUrl",
    "signed_url",
    "token",
    "authorization",
}

REQUIRED_FIXTURES = [
    "pause-validated.json",
    "unsupported.json",
    "deferred.json",
    "unsafe.json",
]


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def forbidden_paths(value, prefix=""):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if key in FORBIDDEN_KEYS:
                found.append(path)
            found.extend(forbidden_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(forbidden_paths(child, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        lowered = value.lower()
        if "-----begin private key-----" in lowered or "authorization: bearer" in lowered:
            found.append(prefix)
    return found


def validate_payload(payload, source):
    errors = []
    schema = payload.get("schemaVersion") or payload.get("schema_version")
    if not schema:
        errors.append(f"{source}: missing schemaVersion")

    decision = payload.get("meetingMuteTruth")
    if not isinstance(decision, dict):
        errors.append(f"{source}: missing meetingMuteTruth object")
    else:
        value = decision.get("decision")
        if value == "mute_respecting":
            errors.append(f"{source}: illegal mute_respecting claim")
        if value not in {"meeting_mute_unproven", "unsupported", "degraded", "failed"}:
            errors.append(f"{source}: unexpected decision {value!r}")
        if decision.get("safeForDiagnostics") is False and value != "failed":
            errors.append(f"{source}: unsafe decision must be failed")

    capability = payload.get("targetMuteCapability")
    if capability is not None:
        status = capability.get("firstMatrixStatus")
        if status not in {"pause_validated", "unsupported", "deferred"}:
            errors.append(f"{source}: unexpected firstMatrixStatus {status!r}")
        if capability.get("meetingAppMuteAdapterSupported") is True:
            errors.append(f"{source}: adapter support is out of scope for MVP fixtures")

    forbidden = forbidden_paths(payload)
    expected = payload.get("expectedValidation", "accepted_metadata_only")
    if expected == "accepted_metadata_only" and forbidden:
        errors.append(f"{source}: forbidden content present: {', '.join(forbidden)}")
    if expected == "blocked_sensitive_content" and not forbidden:
        errors.append(f"{source}: unsafe fixture did not contain forbidden content")
    return errors


def latest_default_artifact_dir():
    roots = [
        pathlib.Path.home() / "Library" / "Application Support" / "2brain Rec" / "Recordings",
        pathlib.Path.home() / "Library" / "Application Support" / "2brainRec" / "Recordings",
    ]
    candidates = []
    for root in roots:
        if root.exists():
            candidates.extend(path.parent for path in root.rglob("manifest.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


if mode == "--fixtures":
    errors = []
    for name in REQUIRED_FIXTURES:
        path = fixture_dir / name
        if not path.exists():
            errors.append(f"missing fixture {name}")
            continue
        errors.extend(validate_payload(load_json(path), name))
    if errors:
        print("meeting-mute-truth fixtures: FAILED")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)
    print("meeting-mute-truth fixtures: OK")
    sys.exit(0)

if mode == "--latest-artifact-directory":
    artifact_dir = explicit_artifact or latest_default_artifact_dir()
    if artifact_dir is None:
        print("meeting-mute-truth latest artifact: no local artifact directory found")
        sys.exit(2)
    manifest_path = artifact_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"meeting-mute-truth latest artifact: manifest missing at {manifest_path}")
        sys.exit(1)
    errors = validate_payload(load_json(manifest_path), str(manifest_path))
    if errors:
        print("meeting-mute-truth latest artifact: FAILED")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)
    print(f"meeting-mute-truth latest artifact: OK {artifact_dir}")
    sys.exit(0)

print(f"unknown mode: {mode}")
sys.exit(2)
PY
