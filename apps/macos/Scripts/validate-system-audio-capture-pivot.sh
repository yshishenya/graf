#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
EVIDENCE_DIR="$ROOT_DIR/specs/025-system-audio-capture-pivot/evidence"

case "${1:-}" in
  -h|--help)
    cat <<'USAGE'
validate-system-audio-capture-pivot.sh

Validates the system-audio-first recording pivot without requiring virtual
2brain Rec devices or HAL runtime probes.

Expected later evidence:
- manifest.json contains mic.wav and incoming.wav
- incoming.wav remains mapped to remoteSpeaker with systemAudio source metadata
- no external egress or transcription starts in this feature
- degraded, blocked, failed, and not-tested are not counted as acceptance
USAGE
    exit 0
    ;;
esac

mkdir -p "$EVIDENCE_DIR"

cat <<'RESULT'
system_audio_capture_pivot_validation=not_implemented
reason=Phase 1 skeleton only; real validation is implemented by later tasks.
RESULT

exit 2
