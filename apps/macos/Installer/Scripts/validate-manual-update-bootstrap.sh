#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
VALIDATOR="$SCRIPT_DIR/../../Scripts/validate-app-updates.sh"

fail() {
  echo "Sparkle trust-generation bootstrap validation failed: $*" >&2
  exit 1
}

if [ "$#" -lt 2 ] || [ "$#" -gt 2 ]; then
  echo "usage: $0 /path/to/new/GRAF.app /path/to/previous/GRAF.app" >&2
  echo "note: this wrapper changes Sparkle Ed25519 trust only; it is not an Apple Developer ID migration" >&2
  exit 64
fi

[ -x "$VALIDATOR" ] || fail "ordinary update validator is missing or not executable"
[ -z "${GRAF_UPDATE_ARCHIVE:-}" ] || fail "Sparkle trust-generation bootstrap must not receive an update archive"
[ -z "${GRAF_UPDATE_APPCAST:-}" ] || fail "Sparkle trust-generation bootstrap must not receive an appcast"
[ "${GRAF_REQUIRE_PUBLIC_UPDATE_TRUST:-0}" = "0" ] || fail "Sparkle trust-generation bootstrap cannot use public in-app update validation"
[ "${GRAF_REQUIRE_OWNER_ONLY_UPDATE_TRUST:-0}" = "0" ] || fail "Sparkle trust-generation bootstrap cannot use owner-only in-app update validation"

GRAF_MANUAL_TRUST_BOOTSTRAP=1 \
  GRAF_UPDATE_ARCHIVE='' \
  GRAF_UPDATE_APPCAST='' \
  "$VALIDATOR" "$1" "$2"
