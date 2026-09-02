#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/../../.." && pwd)
BUILDER="$ROOT_DIR/apps/macos/Scripts/build-dev-app.sh"
APP_LIFECYCLE="$ROOT_DIR/apps/macos/Scripts/dev-app-lifecycle.swift"
DESTINATION="${GRAF_DEV_INSTALL_PATH:-/Applications/GRAF Dev.app}"
INSTALL_PARENT=$(dirname -- "$DESTINATION")
DESTINATION_NAME=$(basename -- "$DESTINATION")
TEMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/graf-dev-install.XXXXXX")
trap 'rm -rf "$TEMP_ROOT"' EXIT INT TERM

# Resolve lexical aliases before any filesystem mutation. A custom Dev path is
# allowed, but it must never be the production bundle or anything below it.
DESTINATION_CANONICAL=$(python3 - "$DESTINATION" <<'PY'
import os
import sys

print(os.path.realpath(sys.argv[1]))
PY
)
PRODUCTION_APP_CANONICAL=$(python3 - "/Applications/GRAF.app" <<'PY'
import os
import sys

print(os.path.realpath(sys.argv[1]))
PY
)

fail() {
  echo "GRAF Dev install: $1" >&2
  exit 1
}

# ``codesign -d`` writes human-readable diagnostics to stderr. Hash only the
# canonical entitlements plist so paths in those diagnostics cannot make an
# otherwise identical candidate and installed app appear different.
entitlements_digest() {
  codesign -d --entitlements :- "$1" > "$TEMP_ROOT/entitlements.plist" 2>/dev/null || return 1
  plutil -convert xml1 -o - -- "$TEMP_ROOT/entitlements.plist" 2>/dev/null |
    shasum -a 256 | awk '{print $1}'
}

[ "$DESTINATION_NAME" = "GRAF Dev.app" ] || fail "destination must end in GRAF Dev.app"
[ "$DESTINATION" = "/Applications/GRAF Dev.app" ] || fail "Dev install destination is fixed at /Applications/GRAF Dev.app"
[ "$DESTINATION_NAME" != "GRAF.app" ] || fail "production GRAF.app is not a Dev destination"
[ "$DESTINATION_CANONICAL" != "$PRODUCTION_APP_CANONICAL" ] || fail "production GRAF.app is not a Dev destination"
case "$DESTINATION_CANONICAL" in
  "$PRODUCTION_APP_CANONICAL"/*) fail "Dev destination cannot be inside production GRAF.app" ;;
esac
[ -x "$BUILDER" ] || fail "Dev builder is missing or not executable"
[ -f "$APP_LIFECYCLE" ] || fail "Dev app lifecycle helper is missing"
APP_STATE=$(swift "$APP_LIFECYCLE" status "$DESTINATION") || fail "could not inspect the Dev app process"
[ "$APP_STATE" = "stopped" ] || fail "Dev app is running; use dev-harness promote or rollback"

CANDIDATE="$TEMP_ROOT/GRAF Dev.app"
LOCAL_ORIGIN="${GRAF_DEV_ORIGIN:-}"
SOURCE_SHA="${GRAF_DEV_SOURCE_SHA:-$(git -C "$ROOT_DIR" rev-parse HEAD)}"
MANIFEST_ID="${GRAF_DEV_MANIFEST_ID:-dev-$(printf '%s' "$SOURCE_SHA" | cut -c1-12)}"
SOURCE_BUNDLE="${GRAF_DEV_APP_SOURCE_BUNDLE:-}"
[ -n "$LOCAL_ORIGIN" ] || fail "GRAF_DEV_ORIGIN must be explicitly supplied"
[ "$SOURCE_SHA" ] && printf '%s' "$SOURCE_SHA" | grep -Eq '^[0-9a-fA-F]{40}$' || fail "GRAF_DEV_SOURCE_SHA must be a 40-character git SHA"
if [ -n "$SOURCE_BUNDLE" ]; then
  [ "$(basename -- "$SOURCE_BUNDLE")" = "GRAF Dev.app" ] || fail "prebuilt Dev bundle must end in GRAF Dev.app"
  [ -d "$SOURCE_BUNDLE" ] || fail "prebuilt Dev bundle is missing: $SOURCE_BUNDLE"
  ditto --norsrc --noextattr --noqtn "$SOURCE_BUNDLE" "$CANDIDATE"
else
  GRAF_DEV_BUILD_DIR="$TEMP_ROOT/build" \
  GRAF_DEV_APP_BUNDLE="$CANDIDATE" \
  GRAF_DEV_SOURCE_SHA="$SOURCE_SHA" \
  GRAF_DEV_MANIFEST_ID="$MANIFEST_ID" \
  GRAF_DEV_ORIGIN="$LOCAL_ORIGIN" \
    sh "$BUILDER"
fi

INFO_PLIST="$CANDIDATE/Contents/Info.plist"
plutil -extract CFBundleDisplayName raw "$INFO_PLIST" | grep -Fxq "GRAF Dev" || fail "candidate display name is invalid"
plutil -extract CFBundleName raw "$INFO_PLIST" | grep -Fxq "GRAF Dev" || fail "candidate bundle name is invalid"
plutil -extract CFBundleIdentifier raw "$INFO_PLIST" | grep -Fxq "pro.2brain.graf.dev" || fail "candidate bundle ID is invalid"
plutil -extract CFBundleIconFile raw "$INFO_PLIST" | grep -Fxq "AppIcon" || fail "candidate icon metadata is invalid"
plutil -extract CFBundleExecutable raw "$INFO_PLIST" | grep -Fxq "GRAF" || fail "candidate executable must be native GRAF"
[ ! -e "$CANDIDATE/Contents/MacOS/GRAF-dev" ] || fail "shell launcher cannot own the Dev bundle identity"
plutil -extract LSEnvironment.GRAF_APP_CHANNEL raw "$INFO_PLIST" | grep -Fxq "dev" ||
  fail "candidate channel is not Dev"
DEV_ICON="$CANDIDATE/Contents/Resources/AppIcon.icns"
[ -s "$DEV_ICON" ] || fail "candidate Dev icon is missing"
if cmp -s "$ROOT_DIR/apps/macos/RecApp/Resources/AppIcon.icns" "$DEV_ICON"; then
  fail "candidate Dev icon is not distinct from production"
fi
plutil -extract GRAFSourceSHA raw "$INFO_PLIST" | grep -Fxq "$SOURCE_SHA" ||
  fail "candidate source SHA metadata is invalid"
plutil -extract GRAFManifestID raw "$INFO_PLIST" | grep -Fxq "$MANIFEST_ID" ||
  fail "candidate manifest ID metadata is invalid"
validate_loopback_url() {
  python3 - "$1" "$2" <<'PY'
from urllib.parse import urlsplit
import sys

label, raw = sys.argv[1:]
try:
    parsed = urlsplit(raw)
    port = parsed.port
except ValueError:
    raise SystemExit(f"{label} has an invalid port")
if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
    raise SystemExit(f"{label} must use an HTTP loopback hostname")
if parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
    raise SystemExit(f"{label} contains forbidden URL userinfo or path components")
if port is None or not 1 <= port <= 65535:
    raise SystemExit(f"{label} must include a valid port")
PY
}

CABINET_URL=$(plutil -extract LSEnvironment.GRAF_CABINET_BASE_URL raw "$INFO_PLIST") || fail "candidate cabinet URL is missing"
UPLOAD_URL=$(plutil -extract LSEnvironment.GRAF_UPLOAD_BASE_URL raw "$INFO_PLIST") || fail "candidate upload URL is missing"
validate_loopback_url cabinet "$CABINET_URL" || fail "candidate cabinet URL is not loopback-safe"
validate_loopback_url upload "$UPLOAD_URL" || fail "candidate upload URL is not loopback-safe"
[ "$CABINET_URL" = "$LOCAL_ORIGIN" ] || fail "candidate cabinet URL does not match requested Dev origin"
[ "$UPLOAD_URL" = "$LOCAL_ORIGIN" ] || fail "candidate upload URL does not match requested Dev origin"
if plutil -extract SUFeedURL raw "$INFO_PLIST" >/dev/null 2>&1 ||
   plutil -extract SUPublicEDKey raw "$INFO_PLIST" >/dev/null 2>&1; then
  fail "candidate production updater metadata must be absent"
fi
codesign --verify --deep --strict "$CANDIDATE" >/dev/null || fail "candidate signature is invalid"

CANDIDATE_REQUIREMENT=$(codesign -dr - "$CANDIDATE" 2>&1 | sed -n 's/^designated => //p' | head -n 1)
[ -n "$CANDIDATE_REQUIREMENT" ] || fail "candidate designated requirement is unavailable"
CANDIDATE_SIGNER=$(codesign -dv --verbose=4 "$CANDIDATE" 2>&1 | sed -n 's/^Authority=//p' | head -n 1)
[ -n "$CANDIDATE_SIGNER" ] || fail "candidate signing identity is unavailable"
CANDIDATE_ENTITLEMENTS_DIGEST=$(entitlements_digest "$CANDIDATE")
[ -n "$CANDIDATE_ENTITLEMENTS_DIGEST" ] || fail "candidate entitlements are unavailable"
if [ -d "$DESTINATION" ]; then
  EXISTING_REQUIREMENT=$(codesign -dr - "$DESTINATION" 2>&1 | sed -n 's/^designated => //p' | head -n 1)
  [ -n "$EXISTING_REQUIREMENT" ] || fail "existing Dev designated requirement is unavailable"
  [ "$EXISTING_REQUIREMENT" = "$CANDIDATE_REQUIREMENT" ] || fail "designated_requirement drift; refusing replacement"
  EXISTING_SIGNER=$(codesign -dv --verbose=4 "$DESTINATION" 2>&1 | sed -n 's/^Authority=//p' | head -n 1)
  [ "$EXISTING_SIGNER" = "$CANDIDATE_SIGNER" ] || fail "signing identity drift; refusing replacement"
  EXISTING_ENTITLEMENTS_DIGEST=$(entitlements_digest "$DESTINATION")
  [ "$EXISTING_ENTITLEMENTS_DIGEST" = "$CANDIDATE_ENTITLEMENTS_DIGEST" ] || fail "entitlements drift; refusing replacement"
fi

mkdir -p "$INSTALL_PARENT"
STAGED_DESTINATION="$INSTALL_PARENT/.GRAF Dev.app.new.$$"
BACKUP_DESTINATION="$INSTALL_PARENT/.GRAF Dev.app.previous.$$"
rm -rf "$STAGED_DESTINATION" "$BACKUP_DESTINATION"
ditto --norsrc --noextattr --noqtn "$CANDIDATE" "$STAGED_DESTINATION"

if [ -e "$DESTINATION" ]; then
  mv "$DESTINATION" "$BACKUP_DESTINATION"
fi
if ! mv "$STAGED_DESTINATION" "$DESTINATION"; then
  if [ -e "$BACKUP_DESTINATION" ]; then
    mv "$BACKUP_DESTINATION" "$DESTINATION"
  fi
  fail "atomic replacement failed; previous Dev app was restored when possible"
fi
rm -rf "$BACKUP_DESTINATION"
touch "$DESTINATION"
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
if [ -x "$LSREGISTER" ]; then
  "$LSREGISTER" -f "$DESTINATION" >/dev/null 2>&1 || true
fi

printf '%s\n' "$DESTINATION"
