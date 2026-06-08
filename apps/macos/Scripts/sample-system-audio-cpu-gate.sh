#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
EVIDENCE_DIR="$ROOT_DIR/specs/025-system-audio-capture-pivot/evidence"

case "${1:-}" in
  -h|--help)
    cat <<'USAGE'
sample-system-audio-cpu-gate.sh

Samples metadata-only CPU evidence for the system-audio MVP.

Required gates:
- idle after 10 seconds: coreaudiod < 5% and app < 5%
- active recording: no sustained coreaudiod > 10%
- active recording: no sustained combined app/helper > 25%
- stop/quit returns below idle gate within 10 seconds

This script must not run HAL live-publication probes.
USAGE
    exit 0
    ;;
esac

mkdir -p "$EVIDENCE_DIR"

cat <<'RESULT'
system_audio_cpu_gate_sampling=not_implemented
reason=Phase 1 skeleton only; real process sampling is implemented by later tasks.
RESULT

exit 2
