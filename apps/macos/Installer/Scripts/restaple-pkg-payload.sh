#!/usr/bin/env sh
set -eu

# Repair the GRAF.app inside an already notarized PKG and re-notarize the PKG.
#
# The normal release order should build the PKG from the already stapled app.
# This script is the bounded workaround for the current builder order: expand
# the final PKG, staple the inner app, rebuild the PKG, sign it again, submit
# the new bytes to Apple, staple the PKG, and only then replace the original.
#
# Usage:
#   restaple-pkg-payload.sh --pkg <path> --identity <Developer ID Installer: ...> \
#     [--profile graf-notary]

fail() {
  echo "pkg_payload_restaple=failed reason=$1" >&2
  exit 1
}

PKG=""
IDENTITY=""
PROFILE="${GRAF_NOTARY_PROFILE:-graf-notary}"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --pkg) PKG=${2:-}; shift 2 ;;
    --identity) IDENTITY=${2:-}; shift 2 ;;
    --profile) PROFILE=${2:-}; shift 2 ;;
    *) fail usage ;;
  esac
done
[ -n "$PKG" ] && [ -n "$IDENTITY" ] || fail usage
[ -f "$PKG" ] || fail package_missing
case "$IDENTITY" in
  "Developer ID Installer:"*) ;;
  *) fail installer_identity_required ;;
esac

TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/graf-pkg-restaple.XXXXXX") || fail tempdir
trap 'rm -rf "$TMP_DIR"' EXIT HUP INT TERM

pkgutil --expand-full "$PKG" "$TMP_DIR/expanded" >/dev/null 2>&1 || fail expand_failed
APP=$(find "$TMP_DIR/expanded" -type d -path '*/Applications/GRAF.app' | head -1)
[ -n "$APP" ] || fail app_missing

xcrun stapler staple "$APP" >/dev/null 2>&1 || fail app_staple_failed
xcrun stapler validate "$APP" >/dev/null 2>&1 || fail app_staple_validate_failed
codesign --verify --deep --strict "$APP" >/dev/null 2>&1 || fail app_codesign_failed

pkgutil --flatten "$TMP_DIR/expanded" "$TMP_DIR/rebuilt-unsigned.pkg" >/dev/null 2>&1 \
  || fail flatten_failed
productsign --sign "$IDENTITY" "$TMP_DIR/rebuilt-unsigned.pkg" "$TMP_DIR/rebuilt.pkg" \
  >/dev/null 2>&1 || fail productsign_failed

xcrun notarytool submit "$TMP_DIR/rebuilt.pkg" \
  --keychain-profile "$PROFILE" --wait >/dev/null 2>&1 \
  || fail notarization_failed
xcrun stapler staple "$TMP_DIR/rebuilt.pkg" >/dev/null 2>&1 || fail pkg_staple_failed
xcrun stapler validate "$TMP_DIR/rebuilt.pkg" >/dev/null 2>&1 || fail pkg_staple_validate_failed

# Re-check both the outer package and the payload app before replacing the
# original file. A failed repair must leave the original PKG untouched.
sh "$(dirname -- "$0")/validate-pkg-payload.sh" "$TMP_DIR/rebuilt.pkg" >/dev/null \
  || fail payload_validation_failed

cp "$TMP_DIR/rebuilt.pkg" "$PKG"
sh "$(dirname -- "$0")/validate-pkg-payload.sh" "$PKG" >/dev/null \
  || fail final_payload_validation_failed
echo "pkg_payload_restaple=pass"
