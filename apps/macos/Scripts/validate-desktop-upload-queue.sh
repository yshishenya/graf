#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
FEATURE_DIR="$ROOT_DIR/specs/014-desktop-upload-queue"

fail() {
  printf 'desktop-upload-queue validation: FAIL - %s\n' "$1" >&2
  exit 1
}

[[ -f "$FEATURE_DIR/spec.md" ]] || fail "missing feature spec"
[[ -f "$FEATURE_DIR/plan.md" ]] || fail "missing feature plan"
[[ -f "$FEATURE_DIR/tasks.md" ]] || fail "missing tasks"

clarity_targets=(
  "$ROOT_DIR/AGENTS.md"
  "$FEATURE_DIR/spec.md"
  "$FEATURE_DIR/plan.md"
  "$FEATURE_DIR/research.md"
  "$FEATURE_DIR/data-model.md"
  "$FEATURE_DIR/tasks.md"
  "$FEATURE_DIR/contracts"
)

rg -n "NEEDS CLARIFICATION|027-desktop-upload-resilience" "${clarity_targets[@]}" &&
  fail "unresolved clarification or stale feature reference found"

rg -n "DesktopUploadQueueService|DesktopUploadClient|DesktopUploadQueueItem" \
  "$ROOT_DIR/apps/macos/RecApp/Sources" "$ROOT_DIR/apps/macos/Shared/Sources" >/dev/null ||
  fail "desktop upload queue implementation symbols not found"

rg -n "mediascribe\\.2brain|MediaScribe.*upload|signedUrl|signed_url|temporaryUploadUrl|uploadToken" \
  "$ROOT_DIR/apps/macos/RecApp/Sources/Upload" "$ROOT_DIR/apps/macos/RecApp/App" \
  --glob '!*.md' && fail "forbidden desktop upload egress or token wording found in implementation"

printf 'desktop-upload-queue validation: PASS\n'
