#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(CDPATH= cd -- "$MACOS_DIR/../.." && pwd)

fail() {
  echo "no-legacy-audio-driver: FAIL: $*" >&2
  exit 1
}

for path in \
  "$MACOS_DIR/AudioDriver" \
  "$MACOS_DIR/Shared/CShmHelpers" \
  "$MACOS_DIR/Shared/Sources/SharedAudioMemory.swift" \
  "$MACOS_DIR/Installer/Scripts/postinstall.sh" \
  "$MACOS_DIR/Installer/Scripts/repair.sh" \
  "$MACOS_DIR/Installer/Scripts/rollback.sh"
do
  [ ! -e "$path" ] || fail "retired path still exists: ${path#"$REPO_ROOT/"}"
done

legacy_pattern='AudioDriver|CShmHelpers|SharedAudioMemory|SharedMemoryRecordingSampleSource|/graf-audio-bridge|GrafProof\.driver|2brainRecProof\.driver|pro\.2brain\.graf\.audio-driver|GRAF_INCLUDE_DRIVER_COMPONENT|TWO_BRAIN_REC_INCLUDE_DRIVER_COMPONENT|PassthroughBridge|PassthroughRouteEngine|ExperimentalPassthroughCoordinator|LivePassthrough|DriverSetupView|--enable-auto-passthrough|--start-passthrough|--enforce-low-resource-promotion-gate'

set -- \
  "$MACOS_DIR/Package.swift" \
  "$MACOS_DIR/RecApp" \
  "$MACOS_DIR/Shared/Sources" \
  "$MACOS_DIR/Shared/Tools" \
  "$MACOS_DIR/Shared/Tests" \
  "$MACOS_DIR/Installer" \
  "$REPO_ROOT/tests/macos" \
  "$REPO_ROOT/qa/macos"

# These two tests are the reviewed negative-reference allowlist: they assert
# that current app-only scripts do not regain retired package tokens. Historical
# specs and docs/evidence are outside the active roots above by design.
if matches=$(rg -n --hidden \
  --glob '!**/.build/**' \
  --glob '!validate-no-legacy-audio-driver.sh' \
  --glob '!InstallerPackagingTests.swift' \
  --glob '!InstallerLifecycleEvidenceTests.swift' \
  "$legacy_pattern" "$@" 2>/dev/null); then
  printf '%s\n' "$matches" >&2
  fail "retired implementation reference found in active source, package, test, or QA surface"
fi

if matches=$(rg -n \
  --glob '!validate-no-legacy-audio-driver.sh' \
  "$legacy_pattern" "$MACOS_DIR/Scripts" 2>/dev/null); then
  printf '%s\n' "$matches" >&2
  fail "retired implementation reference found in active validator"
fi

installer_mutation_pattern='Library/Audio/Plug-Ins/HAL|killall[[:space:]]+coreaudiod|rm[[:space:]]+-rf[^\n]*HAL|xattr[^\n]*HAL'
if matches=$(rg -n "$installer_mutation_pattern" "$MACOS_DIR/Installer" 2>/dev/null); then
  printf '%s\n' "$matches" >&2
  fail "normal installer path still mutates legacy HAL or Core Audio service state"
fi

active_docs_pattern='apps/macos/AudioDriver|make -C apps/macos/AudioDriver|GRAF_INCLUDE_DRIVER_COMPONENT|TWO_BRAIN_REC_INCLUDE_DRIVER_COMPONENT|GrafProof\.driver|2brainRecProof\.driver|PassthroughRouteEngine|Driver controls are parked|Driver diagnostics may still be displayed|virtual audio driver|virtual-driver routing'
if matches=$(rg -n "$active_docs_pattern" \
  "$REPO_ROOT/AGENTS.md" \
  "$REPO_ROOT/.specify/memory/constitution.md" \
  "$MACOS_DIR/README.md" \
  "$REPO_ROOT/docs/current-product-status.md" \
  "$REPO_ROOT/docs/prd-voice-layer-final.md" \
  "$REPO_ROOT/docs/agent-guidance/spec-kit-flow.md" \
  "$REPO_ROOT/docs/agent-guidance/product-gates.md" \
  "$REPO_ROOT/docs/adr/001-local-trust-shell-and-server-dashboard.md" \
  "$REPO_ROOT/qa/macos" 2>/dev/null); then
  printf '%s\n' "$matches" >&2
  fail "active product documentation still presents retired implementation as available"
fi

echo "no-legacy-audio-driver: PASS"
