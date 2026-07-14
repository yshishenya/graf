#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

work_root="$(mktemp -d "${TMPDIR:-/tmp}/graf-playback-normalization-integration.XXXXXX")"
cleanup() {
  rm -rf "$work_root"
}
trap cleanup EXIT INT TERM

infra/scripts/test-playback-normalization-container.sh

mkdir -m 0700 "$work_root/tmp"
(
  cd apps/server
  TMPDIR="$work_root/tmp" PYTHONPATH=src uv run --extra dev pytest \
    -p no:cacheprovider \
    -q \
    tests/integration/test_manual_media_upload.py \
    tests/integration/test_no_processing_side_effects.py \
    tests/integration/test_playback_normalization_finalize.py \
    tests/integration/test_playback_normalization_workflow.py \
    tests/integration/test_playback_normalization_media_matrix.py \
    tests/integration/test_playback_normalization_reuse.py
)

cleanup
trap - EXIT INT TERM
if [[ -e "$work_root" ]]; then
  printf 'playback_normalization_integration_result=fail\n' >&2
  printf 'synthetic_residue_count=unknown\n' >&2
  exit 1
fi

printf 'playback_normalization_integration_result=pass\n'
printf 'full_decode_gate=pass\n'
printf 'synthetic_residue_count=0\n'
