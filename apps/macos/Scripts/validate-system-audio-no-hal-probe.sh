#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
EVIDENCE_DIR="$ROOT_DIR/specs/025-system-audio-capture-pivot/evidence"

case "${1:-}" in
  -h|--help)
    cat <<'USAGE'
validate-system-audio-no-hal-probe.sh

Validates that MVP recording acceptance does not depend on HAL virtual-device
publication, driver repair, or runtime HAL probe scripts.

The final implementation must fail if a HAL probe is required for MVP
recording acceptance.
USAGE
    exit 0
    ;;
esac

mkdir -p "$EVIDENCE_DIR"

cat <<'RESULT'
system_audio_no_hal_probe_validation=not_implemented
reason=Phase 1 skeleton only; real no-HAL validation is implemented by later tasks.
RESULT

exit 2
