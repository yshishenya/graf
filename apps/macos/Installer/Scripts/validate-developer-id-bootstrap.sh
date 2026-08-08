#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
VALIDATOR="$SCRIPT_DIR/../../Scripts/validate-app-updates.sh"

fail() {
  echo "Developer ID migration bootstrap validation failed: $*" >&2
  exit 1
}

if [ "$#" -ne 3 ]; then
  echo "usage: $0 /path/to/new/GRAF.app /path/to/previous/GRAF.app /path/to/notarized/GRAF-version.pkg" >&2
  exit 64
fi

NEW_APP=$1
PREVIOUS_APP=$2
PACKAGE=$3

[ -x "$VALIDATOR" ] || fail "shared app-update validator is missing or not executable"
[ -d "$NEW_APP" ] || fail "new GRAF.app is missing"
[ -d "$PREVIOUS_APP" ] || fail "previous GRAF.app is missing"
[ -f "$PACKAGE" ] || fail "notarized Developer ID package is missing"
[ -z "${GRAF_UPDATE_ARCHIVE:-}" ] || fail "migration bootstrap must not receive an update archive"
[ -z "${GRAF_UPDATE_APPCAST:-}" ] || fail "migration bootstrap must not receive an appcast"
[ "${GRAF_REQUIRE_PUBLIC_UPDATE_TRUST:-0}" = "0" ] || fail "migration bootstrap has its own public trust gate"
[ "${GRAF_REQUIRE_OWNER_ONLY_UPDATE_TRUST:-0}" = "0" ] || fail "migration bootstrap cannot use owner-only update trust"
[ "${GRAF_MANUAL_TRUST_BOOTSTRAP:-0}" = "0" ] || fail "migration bootstrap cannot rotate Sparkle trust generation"

GRAF_MANUAL_DEVELOPER_ID_BOOTSTRAP=1 \
  GRAF_UPDATE_ARCHIVE='' \
  GRAF_UPDATE_APPCAST='' \
  "$VALIDATOR" "$NEW_APP" "$PREVIOUS_APP"

PACKAGE_SIGNATURE=$(pkgutil --check-signature "$PACKAGE" 2>&1) ||
  fail "package signature is invalid"
printf '%s\n' "$PACKAGE_SIGNATURE" | grep -Fq 'Developer ID Installer:' ||
  fail "package is not signed by a Developer ID Installer identity"
printf '%s\n' "$PACKAGE_SIGNATURE" | grep -Fq 'Notarization: trusted by the Apple notary service' ||
  fail "package notarization is not trusted by Apple"
xcrun stapler validate "$PACKAGE" >/dev/null 2>&1 ||
  fail "package notarization staple is invalid"
spctl --assess --type install --verbose=4 "$PACKAGE" >/dev/null 2>&1 ||
  fail "Gatekeeper rejected the Developer ID package"

echo "Developer ID migration bootstrap validation passed: publication=manual-pkg-only appcast_staged=no"
