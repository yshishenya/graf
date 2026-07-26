#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
INSTALLER_DIR=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
MACOS_DIR=$(CDPATH='' cd -- "$INSTALLER_DIR/.." && pwd)
BUILDER="$SCRIPT_DIR/build-local-installer.sh"
VALIDATOR="$SCRIPT_DIR/validate-manual-update-bootstrap.sh"
MANIFEST="$INSTALLER_DIR/UpdateSigningKey.json"
COMMON="$SCRIPT_DIR/release-signing-common.sh"

fail() {
  echo "Sparkle trust-generation bootstrap build failed: $*" >&2
  exit 1
}

VERSION=${GRAF_VERSION:-}
PREVIOUS_APP_BUNDLE=${GRAF_PREVIOUS_APP_BUNDLE:-}
OUTPUT_PKG=${GRAF_BOOTSTRAP_OUTPUT_PKG:-$MACOS_DIR/.build/bootstrap/GRAF-trust-bootstrap-${VERSION:-unversioned}.pkg}

[ -n "$VERSION" ] || fail "GRAF_VERSION=YYYY.MM.DD.N is required"
[ -d "$PREVIOUS_APP_BUNDLE" ] || fail "GRAF_PREVIOUS_APP_BUNDLE is required"
[ -n "${GRAF_UPDATE_FEED_URL:-}" ] || fail "GRAF_UPDATE_FEED_URL is required for the configured bootstrap app"
[ -x "$BUILDER" ] || fail "installer builder is missing or not executable"
[ -x "$VALIDATOR" ] || fail "manual bootstrap validator is missing or not executable"
[ -r "$COMMON" ] || fail "release-signing trust helper is missing"
# shellcheck source=release-signing-common.sh
. "$COMMON"
release_signing_require_active_manifest "$MANIFEST" || exit 1

mkdir -p "$(dirname -- "$OUTPUT_PKG")"
"$BUILDER" "$OUTPUT_PKG"

APP_BUNDLE="$MACOS_DIR/RecApp/.build/GRAF.app"
[ -d "$APP_BUNDLE" ] || fail "built GRAF.app is missing"
"$VALIDATOR" "$APP_BUNDLE" "$PREVIOUS_APP_BUNDLE"
[ -f "$OUTPUT_PKG" ] || fail "bootstrap package was not created"

PACKAGE_SHA256=$(shasum -a 256 "$OUTPUT_PKG" | awk '{print $1}')
SAFE_METADATA="$MACOS_DIR/.build/bootstrap/GRAF-trust-bootstrap-${VERSION}.metadata"
umask 077
{
  printf 'kind=sparkle-trust-generation-bootstrap\n'
  printf 'version=%s\n' "$VERSION"
  printf 'key_id=%s\n' "$RELEASE_SIGNING_KEY_ID"
  printf 'package_sha256=%s\n' "$PACKAGE_SHA256"
  printf 'appcast_staged=no\n'
} > "$SAFE_METADATA"
chmod 600 "$SAFE_METADATA"

echo "Sparkle trust-generation bootstrap built: version=$VERSION key_id=$RELEASE_SIGNING_KEY_ID package_sha256=$PACKAGE_SHA256 appcast_staged=no apple_code_signing_migration=no"
