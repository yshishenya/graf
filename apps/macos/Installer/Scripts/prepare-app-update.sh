#!/usr/bin/env sh
set -eu
export COPYFILE_DISABLE=1

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH='' cd -- "$SCRIPT_DIR/../.." && pwd)
REPO_ROOT=$(git -C "$MACOS_DIR" rev-parse --show-toplevel)

VERSION=${GRAF_VERSION:-}
APP_BUNDLE=${GRAF_UPDATE_APP_BUNDLE:-$MACOS_DIR/RecApp/.build/GRAF.app}
PREVIOUS_APP_BUNDLE=${GRAF_PREVIOUS_APP_BUNDLE:-}
RELEASE_NOTES=${GRAF_UPDATE_RELEASE_NOTES:-}
DOWNLOAD_BASE_URL=${GRAF_UPDATE_DOWNLOAD_BASE_URL:-}
PRIVATE_KEY_FILE=${GRAF_SPARKLE_PRIVATE_KEY_FILE:-}
KEYCHAIN_ACCOUNT=${GRAF_SPARKLE_KEYCHAIN_ACCOUNT:-}
REQUIRE_RELEASE_PROVENANCE=${GRAF_REQUIRE_RELEASE_PROVENANCE:-0}
RELEASE_BRANCH=master
OUTPUT_DIR=$REPO_ROOT/apps/macos/.build/updates
VALIDATOR="$MACOS_DIR/Scripts/validate-app-updates.sh"
DERIVE_PUBLIC_KEY="$SCRIPT_DIR/derive-sparkle-public-key.swift"

fail() {
  echo "app-update preparation failed: $*" >&2
  exit 1
}

version_is_greater() {
  awk -v new="$1" -v old="$2" 'BEGIN {
    split(new, n, "."); split(old, o, ".");
    for (i = 1; i <= 4; i++) {
      if ((n[i] + 0) > (o[i] + 0)) exit 0;
      if ((n[i] + 0) < (o[i] + 0)) exit 1;
    }
    exit 1;
  }'
}

assert_calver() {
  version=$1
  label=$2
  printf '%s\n' "$version" | awk -F. '
    NF != 4 { exit 1 }
    $1 !~ /^[0-9][0-9][0-9][0-9]$/ || $1 + 0 < 2020 { exit 1 }
    $2 !~ /^[0-9][0-9]$/ || $2 + 0 < 1 || $2 + 0 > 12 { exit 1 }
    $3 !~ /^[0-9][0-9]$/ || $3 + 0 < 1 || $3 + 0 > 31 { exit 1 }
    $4 !~ /^[0-9]+$/ || $4 + 0 < 1 { exit 1 }
  ' || fail "$label is not numeric CalVer"
  calendar_date=${version%.*}
  parsed_date=$(LC_ALL=C /bin/date -j -f '%Y.%m.%d' "$calendar_date" '+%Y.%m.%d' 2>/dev/null || true)
  [ "$parsed_date" = "$calendar_date" ] || fail "$label contains an invalid calendar date"
}

[ -n "$VERSION" ] || fail "GRAF_VERSION=YYYY.MM.DD.N is required"
assert_calver "$VERSION" "GRAF_VERSION"

case "$REQUIRE_RELEASE_PROVENANCE" in
  0|1) ;;
  *) fail "GRAF_REQUIRE_RELEASE_PROVENANCE must be 0 or 1" ;;
esac
if [ "$REQUIRE_RELEASE_PROVENANCE" = "1" ]; then
  [ -z "$(git -C "$REPO_ROOT" status --porcelain --untracked-files=all)" ] ||
    fail "release provenance requires a clean worktree"

  HEAD_SHA=$(git -C "$REPO_ROOT" rev-parse HEAD)
  REMOTE_BRANCH_SHA=$(git -C "$REPO_ROOT" ls-remote --heads origin "refs/heads/$RELEASE_BRANCH" |
    awk 'NR == 1 { print $1 }')
  [ -n "$REMOTE_BRANCH_SHA" ] ||
    fail "release provenance could not resolve origin/$RELEASE_BRANCH"
  [ "$HEAD_SHA" = "$REMOTE_BRANCH_SHA" ] ||
    fail "release provenance requires HEAD to match origin/$RELEASE_BRANCH"

  RELEASE_TAG="v$VERSION"
  LOCAL_TAG_SHA=$(git -C "$REPO_ROOT" rev-parse "refs/tags/$RELEASE_TAG^{}" 2>/dev/null || true)
  [ "$LOCAL_TAG_SHA" = "$HEAD_SHA" ] ||
    fail "release provenance requires exact tag $RELEASE_TAG at HEAD"
  REMOTE_TAG_REFS=$(git -C "$REPO_ROOT" ls-remote origin \
    "refs/tags/$RELEASE_TAG" "refs/tags/$RELEASE_TAG^{}")
  REMOTE_TAG_SHA=$(printf '%s\n' "$REMOTE_TAG_REFS" | awk '
    $2 ~ /\^\{\}$/ { peeled = $1 }
    NR == 1 { direct = $1 }
    END { if (peeled != "") print peeled; else print direct }
  ')
  [ "$REMOTE_TAG_SHA" = "$HEAD_SHA" ] ||
    fail "release provenance requires published tag $RELEASE_TAG at HEAD"
fi

[ -d "$APP_BUNDLE" ] || fail "GRAF_UPDATE_APP_BUNDLE is missing"
[ "$(basename -- "$APP_BUNDLE")" = "GRAF.app" ] || fail "update bundle must be named GRAF.app"
[ -d "$PREVIOUS_APP_BUNDLE" ] || fail "GRAF_PREVIOUS_APP_BUNDLE is required for same-identity and monotonic-version validation"
[ -f "$RELEASE_NOTES" ] || fail "GRAF_UPDATE_RELEASE_NOTES must name an existing Russian release-notes file"
[ -n "$DOWNLOAD_BASE_URL" ] || fail "GRAF_UPDATE_DOWNLOAD_BASE_URL is required"
case "$DOWNLOAD_BASE_URL" in
  https://*) ;;
  *) fail "GRAF_UPDATE_DOWNLOAD_BASE_URL must use HTTPS" ;;
esac
case "$DOWNLOAD_BASE_URL" in
  *"@"*|*"?"*|*"#"*) fail "download base URL must be public and credential-free" ;;
esac
DOWNLOAD_LOCATION=${DOWNLOAD_BASE_URL#https://}
DOWNLOAD_AUTHORITY=${DOWNLOAD_LOCATION%%/*}
[ -n "$DOWNLOAD_AUTHORITY" ] || fail "download base URL must contain a host"
DOWNLOAD_BASE_URL=${DOWNLOAD_BASE_URL%/}

if [ -n "$PRIVATE_KEY_FILE" ] && [ -n "$KEYCHAIN_ACCOUNT" ]; then
  fail "choose either GRAF_SPARKLE_PRIVATE_KEY_FILE or GRAF_SPARKLE_KEYCHAIN_ACCOUNT"
fi
if [ -n "$PRIVATE_KEY_FILE" ]; then
  [ -f "$PRIVATE_KEY_FILE" ] || fail "GRAF_SPARKLE_PRIVATE_KEY_FILE does not exist"
  PRIVATE_KEY_FILE=$(/bin/realpath "$PRIVATE_KEY_FILE")
  case "$PRIVATE_KEY_FILE" in
    "$REPO_ROOT"/*) fail "the Sparkle private key file must stay outside the repository" ;;
  esac
elif [ -z "$KEYCHAIN_ACCOUNT" ]; then
  fail "set GRAF_SPARKLE_PRIVATE_KEY_FILE outside git or GRAF_SPARKLE_KEYCHAIN_ACCOUNT"
fi

grep -Eq '[А-Яа-яЁё]' "$RELEASE_NOTES" || fail "release notes must contain Russian user-facing text"

APP_INFO_PLIST="$APP_BUNDLE/Contents/Info.plist"
APP_VERSION=$(/usr/bin/plutil -extract CFBundleVersion raw -o - "$APP_INFO_PLIST")
APP_FEED_URL=$(/usr/bin/plutil -extract SUFeedURL raw -o - "$APP_INFO_PLIST" 2>/dev/null || true)
APP_PUBLIC_KEY=$(/usr/bin/plutil -extract SUPublicEDKey raw -o - "$APP_INFO_PLIST" 2>/dev/null || true)
[ "$APP_VERSION" = "$VERSION" ] || fail "GRAF_VERSION differs from the app bundle version"
[ -n "$APP_FEED_URL" ] || fail "GRAF.app is updater-disabled; build it with complete trusted update configuration"
[ "$APP_FEED_URL" = "$DOWNLOAD_BASE_URL/graf-appcast.xml" ] || fail "app feed URL and staged download base URL disagree"
[ -n "$APP_PUBLIC_KEY" ] || fail "GRAF.app does not contain SUPublicEDKey"

SPARKLE_BIN_DIR="$MACOS_DIR/.build/artifacts/sparkle/Sparkle/bin"
GENERATE_APPCAST="$SPARKLE_BIN_DIR/generate_appcast"
GENERATE_KEYS="$SPARKLE_BIN_DIR/generate_keys"
SIGN_UPDATE="$SPARKLE_BIN_DIR/sign_update"
[ -x "$GENERATE_APPCAST" ] || fail "official pinned Sparkle generate_appcast tool was not found"
[ -x "$GENERATE_KEYS" ] || fail "official pinned Sparkle generate_keys tool was not found"
[ -x "$SIGN_UPDATE" ] || fail "official pinned Sparkle sign_update tool was not found"
[ -f "$DERIVE_PUBLIC_KEY" ] || fail "Sparkle public-key derivation helper is missing"
[ -x "$VALIDATOR" ] || fail "validate-app-updates.sh is missing or not executable"

if [ -n "$PRIVATE_KEY_FILE" ]; then
  SIGNING_PUBLIC_KEY=$(/usr/bin/xcrun swift "$DERIVE_PUBLIC_KEY" "$PRIVATE_KEY_FILE")
else
  SIGNING_PUBLIC_KEY=$("$GENERATE_KEYS" --account "$KEYCHAIN_ACCOUNT" -p | tr -d '\r\n')
fi
SIGNING_PUBLIC_KEY_BYTES=$(printf '%s' "$SIGNING_PUBLIC_KEY" | /usr/bin/base64 -D 2>/dev/null | wc -c | tr -d ' ')
[ "$SIGNING_PUBLIC_KEY_BYTES" = "32" ] || fail "the selected Sparkle signing key did not produce a valid public key"
[ "$SIGNING_PUBLIC_KEY" = "$APP_PUBLIC_KEY" ] || fail "the Sparkle signing key does not match GRAF.app SUPublicEDKey"

"$VALIDATOR" "$APP_BUNDLE" "$PREVIOUS_APP_BUNDLE"

if [ -d "$OUTPUT_DIR" ]; then
  EXISTING_APPCAST="$OUTPUT_DIR/graf-appcast.xml"
  [ -f "$EXISTING_APPCAST" ] || fail "existing staging directory is missing graf-appcast.xml"
  xmllint --noout "$EXISTING_APPCAST" 2>/dev/null || fail "existing staged appcast XML is malformed"
  EXISTING_VERSION_COUNT=$(xmllint --xpath "count(//*[local-name()='item']/*[local-name()='version'])" "$EXISTING_APPCAST")
  index=1
  while [ "$index" -le "$EXISTING_VERSION_COUNT" ]; do
    EXISTING_VERSION=$(xmllint --xpath "string((//*[local-name()='item']/*[local-name()='version'])[$index])" "$EXISTING_APPCAST")
    assert_calver "$EXISTING_VERSION" "existing staged appcast version"
    version_is_greater "$VERSION" "$EXISTING_VERSION" || fail "GRAF_VERSION must exceed every existing staged appcast version"
    index=$((index + 1))
  done
fi

OUTPUT_PARENT=$(dirname -- "$OUTPUT_DIR")
mkdir -p "$OUTPUT_PARENT"
WORK_DIR="$OUTPUT_PARENT/.graf-update-$VERSION-$$"
BACKUP_DIR="$OUTPUT_PARENT/.graf-update-backup-$$"
cleanup_staging() {
  status=$?
  trap - EXIT HUP INT TERM
  if [ ! -e "$OUTPUT_DIR" ] && [ -d "$BACKUP_DIR" ]; then
    mv "$BACKUP_DIR" "$OUTPUT_DIR" 2>/dev/null || true
  fi
  rm -rf "$WORK_DIR"
  exit "$status"
}
trap cleanup_staging EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
mkdir -p "$WORK_DIR"
if [ -d "$OUTPUT_DIR" ]; then
  ditto "$OUTPUT_DIR" "$WORK_DIR"
fi

ARCHIVE_NAME="GRAF-$VERSION.zip"
ARCHIVE_PATH="$WORK_DIR/$ARCHIVE_NAME"
NOTES_PATH="$WORK_DIR/GRAF-$VERSION.md"
APPCAST_PATH="$WORK_DIR/graf-appcast.xml"
[ ! -e "$ARCHIVE_PATH" ] || fail "staged archive for version $VERSION already exists"

ditto -c -k --sequesterRsrc --keepParent "$APP_BUNDLE" "$ARCHIVE_PATH"
cp "$RELEASE_NOTES" "$NOTES_PATH"

if [ -n "$PRIVATE_KEY_FILE" ]; then
  "$GENERATE_APPCAST" \
    --ed-key-file "$PRIVATE_KEY_FILE" \
    --download-url-prefix "$DOWNLOAD_BASE_URL/" \
    --embed-release-notes \
    --versions "$VERSION" \
    --maximum-deltas 0 \
    --maximum-versions 3 \
    -o "$APPCAST_PATH" \
    "$WORK_DIR"
else
  "$GENERATE_APPCAST" \
    --account "$KEYCHAIN_ACCOUNT" \
    --download-url-prefix "$DOWNLOAD_BASE_URL/" \
    --embed-release-notes \
    --versions "$VERSION" \
    --maximum-deltas 0 \
    --maximum-versions 3 \
    -o "$APPCAST_PATH" \
    "$WORK_DIR"
fi

"$VALIDATOR" "$APP_BUNDLE" "$PREVIOUS_APP_BUNDLE" "$ARCHIVE_PATH" "$APPCAST_PATH"

APPCAST_SIGNATURE=$(xmllint --xpath \
  "string((//*[local-name()='item' and *[local-name()='version' and normalize-space(text())='$VERSION']]/*[local-name()='enclosure'])/@*[local-name()='edSignature'])" \
  "$APPCAST_PATH")
if [ -n "$PRIVATE_KEY_FILE" ]; then
  "$SIGN_UPDATE" --verify --ed-key-file "$PRIVATE_KEY_FILE" "$APPCAST_PATH"
  "$SIGN_UPDATE" --verify --ed-key-file "$PRIVATE_KEY_FILE" "$ARCHIVE_PATH" "$APPCAST_SIGNATURE"
else
  "$SIGN_UPDATE" --verify --account "$KEYCHAIN_ACCOUNT" "$APPCAST_PATH"
  "$SIGN_UPDATE" --verify --account "$KEYCHAIN_ACCOUNT" "$ARCHIVE_PATH" "$APPCAST_SIGNATURE"
fi

if [ -d "$OUTPUT_DIR" ]; then
  mv "$OUTPUT_DIR" "$BACKUP_DIR"
fi
if ! mv "$WORK_DIR" "$OUTPUT_DIR"; then
  if [ -d "$BACKUP_DIR" ]; then
    mv "$BACKUP_DIR" "$OUTPUT_DIR" || true
  fi
  fail "could not replace staged output; the prior staging directory was retained when possible"
fi
rm -rf "$BACKUP_DIR"
trap - EXIT HUP INT TERM

ARCHIVE_LENGTH=$(stat -f '%z' "$OUTPUT_DIR/$ARCHIVE_NAME")
echo "app-update artifacts staged: version=$VERSION archive=$ARCHIVE_NAME bytes=$ARCHIVE_LENGTH appcast=graf-appcast.xml output=$OUTPUT_DIR published=no"
