#!/usr/bin/env sh
set -eu

# Validate the GRAF.app inside the final installer PKG, not just the outer PKG.
# A notarized PKG can still contain an app without a stapled ticket; that breaks
# offline first launch and must fail the release.

fail() {
  echo "pkg_payload_validation=failed reason=$1" >&2
  exit 1
}

[ "$#" -eq 1 ] || fail usage
PKG=$1
[ -f "$PKG" ] || fail package_missing

TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/graf-pkg-payload.XXXXXX") || fail tempdir
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

pkgutil --expand-full "$PKG" "$TMP_DIR/expanded" >/dev/null 2>&1 || fail expand_failed
APP=$(find "$TMP_DIR/expanded" -type d -path '*/Applications/GRAF.app' | head -1)
[ -n "$APP" ] || fail app_missing

codesign --verify --deep --strict "$APP" >/dev/null 2>&1 || fail codesign
xcrun stapler validate "$APP" >/dev/null 2>&1 || fail stapler
spctl --assess --type execute --verbose=4 "$APP" >/dev/null 2>&1 || fail gatekeeper
if [ -x /usr/bin/syspolicy_check ]; then
  /usr/bin/syspolicy_check distribution "$APP" >/dev/null 2>&1 || fail syspolicy
fi

echo "pkg_payload_validation=pass"
