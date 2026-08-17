#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/../../.." && pwd)
BUILDER="$ROOT_DIR/apps/macos/Scripts/build-dev-app.sh"
DESTINATION="${GRAF_DEV_INSTALL_PATH:-/Applications/GRAF Dev.app}"
INSTALL_PARENT=$(dirname -- "$DESTINATION")
DESTINATION_NAME=$(basename -- "$DESTINATION")
TEMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/graf-dev-install.XXXXXX")
trap 'rm -rf "$TEMP_ROOT"' EXIT INT TERM

fail() {
  echo "GRAF Dev install: $1" >&2
  exit 1
}

[ "$DESTINATION_NAME" = "GRAF Dev.app" ] || fail "destination must end in GRAF Dev.app"
[ "$DESTINATION_NAME" != "GRAF.app" ] || fail "production GRAF.app is not a Dev destination"
[ -x "$BUILDER" ] || fail "Dev builder is missing or not executable"

CANDIDATE="$TEMP_ROOT/GRAF Dev.app"
GRAF_DEV_BUILD_DIR="$TEMP_ROOT/build" \
GRAF_DEV_APP_BUNDLE="$CANDIDATE" \
  sh "$BUILDER"

INFO_PLIST="$CANDIDATE/Contents/Info.plist"
plutil -extract CFBundleDisplayName raw "$INFO_PLIST" | grep -Fxq "GRAF Dev" || fail "candidate display name is invalid"
plutil -extract CFBundleIdentifier raw "$INFO_PLIST" | grep -Fxq "pro.2brain.graf.dev" || fail "candidate bundle ID is invalid"
plutil -extract CFBundleExecutable raw "$INFO_PLIST" | grep -Fxq "GRAF" || fail "candidate executable must be native GRAF"
[ ! -e "$CANDIDATE/Contents/MacOS/GRAF-dev" ] || fail "shell launcher cannot own the Dev bundle identity"
plutil -extract LSEnvironment.GRAF_APP_CHANNEL raw "$INFO_PLIST" | grep -Fxq "dev" ||
  fail "candidate channel is not Dev"
plutil -extract LSEnvironment.GRAF_CABINET_BASE_URL raw "$INFO_PLIST" | grep -Eq '^http://(127\.0\.0\.1|localhost):' ||
  fail "candidate origin is not loopback"
if plutil -extract SUFeedURL raw "$INFO_PLIST" >/dev/null 2>&1 ||
   plutil -extract SUPublicEDKey raw "$INFO_PLIST" >/dev/null 2>&1; then
  fail "candidate production updater metadata must be absent"
fi
codesign --verify --deep --strict "$CANDIDATE" >/dev/null || fail "candidate signature is invalid"

CANDIDATE_REQUIREMENT=$(codesign -dr - "$CANDIDATE" 2>&1 | sed -n 's/^designated => //p' | head -n 1)
[ -n "$CANDIDATE_REQUIREMENT" ] || fail "candidate designated requirement is unavailable"
if [ -d "$DESTINATION" ]; then
  EXISTING_REQUIREMENT=$(codesign -dr - "$DESTINATION" 2>&1 | sed -n 's/^designated => //p' | head -n 1)
  [ -n "$EXISTING_REQUIREMENT" ] || fail "existing Dev designated requirement is unavailable"
  [ "$EXISTING_REQUIREMENT" = "$CANDIDATE_REQUIREMENT" ] || fail "designated_requirement drift; refusing replacement"
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

printf '%s\n' "$DESTINATION"
