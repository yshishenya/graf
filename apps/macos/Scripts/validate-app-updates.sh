#!/usr/bin/env sh
set -eu

APP_BUNDLE=${1:-}
PREVIOUS_APP_BUNDLE=${2:-${GRAF_PREVIOUS_APP_BUNDLE:-}}
UPDATE_ARCHIVE=${3:-${GRAF_UPDATE_ARCHIVE:-}}
UPDATE_APPCAST=${4:-${GRAF_UPDATE_APPCAST:-}}
REQUIRE_PUBLIC_TRUST=${GRAF_REQUIRE_PUBLIC_UPDATE_TRUST:-0}
REQUIRE_OWNER_ONLY_TRUST=${GRAF_REQUIRE_OWNER_ONLY_UPDATE_TRUST:-0}
MANUAL_TRUST_BOOTSTRAP=${GRAF_MANUAL_TRUST_BOOTSTRAP:-0}
MANUAL_DEVELOPER_ID_BOOTSTRAP=${GRAF_MANUAL_DEVELOPER_ID_BOOTSTRAP:-0}
ALLOW_HISTORICAL_OWNER_ONLY_FIXTURE=${GRAF_ALLOW_HISTORICAL_OWNER_ONLY_FIXTURE:-0}

fail() {
  echo "app-update validation failed: $*" >&2
  exit 1
}

if [ -z "$APP_BUNDLE" ]; then
  echo "usage: $0 /path/to/GRAF.app [/path/to/previous/GRAF.app] [/path/to/GRAF-version.zip] [/path/to/appcast.xml]" >&2
  exit 64
fi

case "$MANUAL_TRUST_BOOTSTRAP" in
  0) ;;
  1)
    [ -n "$PREVIOUS_APP_BUNDLE" ] || fail "Sparkle trust-generation bootstrap requires the previous GRAF.app"
    [ -z "$UPDATE_ARCHIVE" ] || fail "Sparkle trust-generation bootstrap must not validate or stage an appcast archive"
    [ -z "$UPDATE_APPCAST" ] || fail "Sparkle trust-generation bootstrap must not validate or stage an appcast"
    [ "$REQUIRE_PUBLIC_TRUST" = "0" ] || fail "Sparkle trust-generation bootstrap cannot claim public in-app update trust"
    [ "$REQUIRE_OWNER_ONLY_TRUST" = "0" ] || fail "Sparkle trust-generation bootstrap cannot claim owner-only in-app update trust"
    [ "$MANUAL_DEVELOPER_ID_BOOTSTRAP" = "0" ] || fail "choose either Sparkle trust bootstrap or Developer ID migration bootstrap"
    ;;
  *)
    fail "GRAF_MANUAL_TRUST_BOOTSTRAP must be 0 or 1"
    ;;
esac

case "$MANUAL_DEVELOPER_ID_BOOTSTRAP" in
  0) ;;
  1)
    [ -n "$PREVIOUS_APP_BUNDLE" ] || fail "Developer ID migration bootstrap requires the previous GRAF.app"
    [ -z "$UPDATE_ARCHIVE" ] || fail "Developer ID migration bootstrap must not validate or stage an update archive"
    [ -z "$UPDATE_APPCAST" ] || fail "Developer ID migration bootstrap must not validate or stage an appcast"
    [ "$REQUIRE_PUBLIC_TRUST" = "0" ] || fail "Developer ID migration bootstrap has its own public trust gate"
    [ "$REQUIRE_OWNER_ONLY_TRUST" = "0" ] || fail "Developer ID migration bootstrap cannot claim owner-only update trust"
    [ "$MANUAL_TRUST_BOOTSTRAP" = "0" ] || fail "choose either Sparkle trust bootstrap or Developer ID migration bootstrap"
    ;;
  *)
    fail "GRAF_MANUAL_DEVELOPER_ID_BOOTSTRAP must be 0 or 1"
    ;;
esac

if [ "$REQUIRE_OWNER_ONLY_TRUST" = "1" ] && [ "$ALLOW_HISTORICAL_OWNER_ONLY_FIXTURE" != "1" ]; then
  fail "owner-only validation is historical fixture-only; set GRAF_ALLOW_HISTORICAL_OWNER_ONLY_FIXTURE=1 for an isolated negative-test receipt"
fi

INFO_PLIST="$APP_BUNDLE/Contents/Info.plist"
EXECUTABLE="$APP_BUNDLE/Contents/MacOS/GRAF"
SPARKLE_FRAMEWORK="$APP_BUNDLE/Contents/Frameworks/Sparkle.framework"
SPARKLE_LICENSE="$APP_BUNDLE/Contents/Resources/Sparkle-LICENSE.txt"
SPARKLE_LICENSE_SHA256="389a4e4e9a32f059775b13a06e25a591445ba229d2838d26dd3e7c0c45127cfe"

[ -d "$APP_BUNDLE" ] || fail "app bundle is missing"
[ -f "$INFO_PLIST" ] || fail "Info.plist is missing"
[ -x "$EXECUTABLE" ] || fail "GRAF executable is missing"
[ -d "$SPARKLE_FRAMEWORK" ] || fail "Contents/Frameworks/Sparkle.framework is missing"
[ -f "$SPARKLE_LICENSE" ] || fail "Sparkle license notice is missing"
[ "$(shasum -a 256 "$SPARKLE_LICENSE" | awk '{print $1}')" = "$SPARKLE_LICENSE_SHA256" ] || fail "Sparkle license notice differs from release 2.9.4"

plist_read() {
  /usr/bin/plutil -extract "$1" raw -o - "$2" 2>/dev/null || true
}

assert_plist_value() {
  observed=$(plist_read "$1" "$INFO_PLIST")
  [ "$observed" = "$2" ] || fail "$1 must be $2"
}

assert_calver() {
  version=$1
  printf '%s\n' "$version" | awk -F. '
    NF != 4 { exit 1 }
    $1 !~ /^[0-9][0-9][0-9][0-9]$/ || $1 + 0 < 2020 { exit 1 }
    $2 !~ /^[0-9][0-9]$/ || $2 + 0 < 1 || $2 + 0 > 12 { exit 1 }
    $3 !~ /^[0-9][0-9]$/ || $3 + 0 < 1 || $3 + 0 > 31 { exit 1 }
    $4 !~ /^[0-9]+$/ || $4 + 0 < 1 { exit 1 }
  ' || fail "CFBundleVersion is not numeric CalVer"
  calendar_date=${version%.*}
  parsed_date=$(LC_ALL=C /bin/date -j -f '%Y.%m.%d' "$calendar_date" '+%Y.%m.%d' 2>/dev/null || true)
  [ "$parsed_date" = "$calendar_date" ] || fail "CFBundleVersion contains an invalid calendar date"
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

assert_plist_value CFBundleIdentifier pro.2brain.graf
assert_plist_value CFBundleName GRAF
assert_plist_value CFBundleDisplayName GRAF
assert_plist_value CFBundleExecutable GRAF
assert_plist_value LSMinimumSystemVersion 14.5

VERSION=$(plist_read CFBundleVersion "$INFO_PLIST")
SHORT_VERSION=$(plist_read CFBundleShortVersionString "$INFO_PLIST")
assert_calver "$VERSION"
[ "$SHORT_VERSION" = "$VERSION" ] || fail "short and machine versions differ"

MICROPHONE_COPY=$(plist_read NSMicrophoneUsageDescription "$INFO_PLIST")
SYSTEM_AUDIO_CAPTURE_COPY=$(plist_read NSAudioCaptureUsageDescription "$INFO_PLIST")
SYSTEM_AUDIO_COPY=$(plist_read NSScreenCaptureUsageDescription "$INFO_PLIST")
[ -n "$MICROPHONE_COPY" ] || fail "microphone usage description is missing"
[ -n "$SYSTEM_AUDIO_CAPTURE_COPY" ] || fail "system-audio capture usage description is missing"
[ -n "$SYSTEM_AUDIO_COPY" ] || fail "screen/system-audio usage description is missing"

lipo -archs "$EXECUTABLE" | tr ' ' '\n' | grep -qx arm64 || fail "GRAF executable is not arm64-capable"
otool -L "$EXECUTABLE" | grep -Fq '@rpath/Sparkle.framework/' || fail "GRAF executable is not linked to embedded Sparkle"

for nested in \
  "$SPARKLE_FRAMEWORK/Versions/B/XPCServices/Downloader.xpc" \
  "$SPARKLE_FRAMEWORK/Versions/B/XPCServices/Installer.xpc" \
  "$SPARKLE_FRAMEWORK/Versions/B/Updater.app" \
  "$SPARKLE_FRAMEWORK/Versions/B/Autoupdate"; do
  [ -e "$nested" ] || fail "nested Sparkle code is missing"
  codesign --verify --strict "$nested" 2>/dev/null || fail "nested Sparkle signature is invalid"
done
codesign --verify --strict "$SPARKLE_FRAMEWORK" 2>/dev/null || fail "Sparkle framework signature is invalid"
codesign --verify --deep --strict "$APP_BUNDLE" 2>/dev/null || fail "GRAF bundle signature is invalid"

SPARKLE_VERSION=$(plist_read CFBundleShortVersionString "$SPARKLE_FRAMEWORK/Versions/B/Resources/Info.plist")
[ "$SPARKLE_VERSION" = "2.9.4" ] || fail "embedded Sparkle version must be 2.9.4"

FEED_URL=$(plist_read SUFeedURL "$INFO_PLIST")
PUBLIC_KEY=$(plist_read SUPublicEDKey "$INFO_PLIST")
if [ -z "$FEED_URL" ] && [ -z "$PUBLIC_KEY" ]; then
  UPDATE_CONFIGURATION=disabled
elif [ -n "$FEED_URL" ] && [ -n "$PUBLIC_KEY" ]; then
  case "$FEED_URL" in
    https://*) ;;
    *) fail "SUFeedURL must use HTTPS" ;;
  esac
  case "$FEED_URL" in
    *"@"*|*"?"*|*"#"*) fail "SUFeedURL must be public and credential-free" ;;
  esac
  FEED_LOCATION=${FEED_URL#https://}
  FEED_AUTHORITY=${FEED_LOCATION%%/*}
  [ -n "$FEED_AUTHORITY" ] || fail "SUFeedURL must contain a host"
  case "$FEED_LOCATION" in
    */graf-appcast.xml) ;;
    *) fail "SUFeedURL must end with /graf-appcast.xml" ;;
  esac
  PUBLIC_KEY_BYTES=$(printf '%s' "$PUBLIC_KEY" | /usr/bin/base64 -D 2>/dev/null | wc -c | tr -d ' ')
  [ "$PUBLIC_KEY_BYTES" = "32" ] || fail "SUPublicEDKey must be a base64-encoded 32-byte Ed25519 public key"
  assert_plist_value SURequireSignedFeed true
  assert_plist_value SUVerifyUpdateBeforeExtraction true
  assert_plist_value SUSignedFeedFailureExpirationInterval 0
  assert_plist_value SUEnableAutomaticChecks true
  assert_plist_value SUScheduledCheckInterval 86400
  assert_plist_value SUAutomaticallyUpdate false
  assert_plist_value SUAllowsAutomaticUpdates false
  assert_plist_value SUEnableSystemProfiling false
  UPDATE_CONFIGURATION=configured
else
  fail "feed URL and public key must be both present or both absent"
fi

for forbidden_bundle_path in \
  "$APP_BUNDLE/Contents/Library" \
  "$APP_BUNDLE/Contents/PlugIns" \
  "$APP_BUNDLE/Contents/LaunchServices" \
  "$APP_BUNDLE/Contents/XPCServices"; do
  [ ! -e "$forbidden_bundle_path" ] || fail "app update contains an unexpected privileged component directory"
done
if find "$APP_BUNDLE" -type d \( -name '*.kext' -o -name '*.dext' -o -name '*.systemextension' \) -print | grep -q .; then
  fail "app update contains an unexpected privileged extension"
fi

SIGNATURE_INFO=$(codesign -dv --verbose=4 "$APP_BUNDLE" 2>&1)
TEAM_IDENTIFIER=$(printf '%s\n' "$SIGNATURE_INFO" | sed -n 's/^TeamIdentifier=//p' | head -n 1)
[ "$TEAM_IDENTIFIER" != "not set" ] || TEAM_IDENTIFIER=
AUTHORITY=$(printf '%s\n' "$SIGNATURE_INFO" | sed -n 's/^Authority=//p' | head -n 1)
SIGNING_KIND=unknown
IDENTITY_CHECK=not-requested
UPDATE_CONTINUITY=not-evaluated
if printf '%s\n' "$SIGNATURE_INFO" | grep -q '^Signature=adhoc'; then
  SIGNING_KIND=adhoc
elif printf '%s\n' "$SIGNATURE_INFO" | grep -q '^Authority=Developer ID Application'; then
  SIGNING_KIND=developer-id
elif [ -n "$AUTHORITY" ]; then
  SIGNING_KIND=local
else
  fail "application signing kind is unavailable"
fi

APP_ENTITLEMENTS=$(codesign -d --entitlements :- "$APP_BUNDLE" 2>&1 || true)
APP_ENTITLEMENTS_COMPACT=$(printf '%s\n' "$APP_ENTITLEMENTS" | tr -d '[:space:]')
AUDIO_INPUT_ENABLED=0
case "$APP_ENTITLEMENTS_COMPACT" in
  *"<key>com.apple.security.device.audio-input</key><true/>"*)
    AUDIO_INPUT_ENABLED=1
    ;;
esac
[ "$AUDIO_INPUT_ENABLED" = "1" ] || fail "app signing must declare hardened-runtime audio input entitlement"
LIBRARY_VALIDATION_DISABLED=0
case "$APP_ENTITLEMENTS_COMPACT" in
  *"<key>com.apple.security.cs.disable-library-validation</key><true/>"*)
    LIBRARY_VALIDATION_DISABLED=1
    ;;
esac
if [ -z "$TEAM_IDENTIFIER" ]; then
  [ "$LIBRARY_VALIDATION_DISABLED" = "1" ] || fail "teamless signing requires disabled library validation for embedded Sparkle"
else
  [ "$LIBRARY_VALIDATION_DISABLED" = "0" ] || fail "team-identified signing must keep library validation enabled"
fi

if { [ "$REQUIRE_PUBLIC_TRUST" = "1" ] || [ "$REQUIRE_OWNER_ONLY_TRUST" = "1" ] || [ "$MANUAL_DEVELOPER_ID_BOOTSTRAP" = "1" ]; } &&
   [ -z "$PREVIOUS_APP_BUNDLE" ]; then
  fail "release update validation requires the previous GRAF.app"
fi

if [ -n "$PREVIOUS_APP_BUNDLE" ]; then
  PREVIOUS_INFO_PLIST="$PREVIOUS_APP_BUNDLE/Contents/Info.plist"
  [ -f "$PREVIOUS_INFO_PLIST" ] || fail "previous app Info.plist is missing"
  PREVIOUS_ID=$(plist_read CFBundleIdentifier "$PREVIOUS_INFO_PLIST")
  PREVIOUS_NAME=$(plist_read CFBundleName "$PREVIOUS_INFO_PLIST")
  PREVIOUS_VERSION=$(plist_read CFBundleVersion "$PREVIOUS_INFO_PLIST")
  PREVIOUS_MICROPHONE_COPY=$(plist_read NSMicrophoneUsageDescription "$PREVIOUS_INFO_PLIST")
  PREVIOUS_SYSTEM_AUDIO_COPY=$(plist_read NSScreenCaptureUsageDescription "$PREVIOUS_INFO_PLIST")
  PREVIOUS_FEED_URL=$(plist_read SUFeedURL "$PREVIOUS_INFO_PLIST")
  PREVIOUS_PUBLIC_KEY=$(plist_read SUPublicEDKey "$PREVIOUS_INFO_PLIST")
  [ "$PREVIOUS_ID" = "pro.2brain.graf" ] || fail "previous bundle identifier differs"
  [ "$PREVIOUS_NAME" = "GRAF" ] || fail "previous app name differs"
  assert_calver "$PREVIOUS_VERSION"
  version_is_greater "$VERSION" "$PREVIOUS_VERSION" || fail "update version is not strictly greater"
  [ "$MICROPHONE_COPY" = "$PREVIOUS_MICROPHONE_COPY" ] || fail "microphone usage description changed"
  [ "$SYSTEM_AUDIO_COPY" = "$PREVIOUS_SYSTEM_AUDIO_COPY" ] || fail "screen/system-audio usage description changed"

  if [ "$MANUAL_DEVELOPER_ID_BOOTSTRAP" = "1" ]; then
    [ -n "$PREVIOUS_FEED_URL" ] && [ -n "$PREVIOUS_PUBLIC_KEY" ] || fail "Developer ID migration bootstrap requires a configured previous app"
    [ "$UPDATE_CONFIGURATION" = "configured" ] || fail "Developer ID migration bootstrap requires a configured candidate app"
    [ "$FEED_URL" = "$PREVIOUS_FEED_URL" ] || fail "Developer ID migration bootstrap cannot change the update feed URL"
    [ "$PUBLIC_KEY" = "$PREVIOUS_PUBLIC_KEY" ] || fail "Developer ID migration bootstrap cannot rotate the Sparkle public key"
    UPDATE_CONTINUITY=manual-developer-id-bootstrap
  elif [ "$MANUAL_TRUST_BOOTSTRAP" = "1" ]; then
    [ -n "$PREVIOUS_FEED_URL" ] && [ -n "$PREVIOUS_PUBLIC_KEY" ] || fail "Sparkle trust-generation bootstrap requires a configured previous app"
    [ "$UPDATE_CONFIGURATION" = "configured" ] || fail "Sparkle trust-generation bootstrap requires a configured candidate app"
    [ "$FEED_URL" = "$PREVIOUS_FEED_URL" ] || fail "Sparkle trust-generation bootstrap cannot change the update feed URL"
    [ "$PUBLIC_KEY" != "$PREVIOUS_PUBLIC_KEY" ] || fail "Sparkle trust-generation bootstrap requires a new public signing generation"
    UPDATE_CONTINUITY=manual-trust-bootstrap
  elif [ -z "$PREVIOUS_FEED_URL" ] && [ -z "$PREVIOUS_PUBLIC_KEY" ]; then
    UPDATE_CONTINUITY=manual-bootstrap
  elif [ -n "$PREVIOUS_FEED_URL" ] && [ -n "$PREVIOUS_PUBLIC_KEY" ]; then
    [ "$UPDATE_CONFIGURATION" = "configured" ] || fail "a configured previous app cannot update to an updater-disabled app"
    [ "$FEED_URL" = "$PREVIOUS_FEED_URL" ] || fail "update feed URL changed from the previous app"
    [ "$PUBLIC_KEY" = "$PREVIOUS_PUBLIC_KEY" ] || fail "Sparkle public key changed without an approved rotation"
    UPDATE_CONTINUITY=in-app
  else
    fail "previous app has incomplete trusted update configuration"
  fi

  PREVIOUS_SIGNATURE_INFO=$(codesign -dv --verbose=4 "$PREVIOUS_APP_BUNDLE" 2>&1)
  PREVIOUS_TEAM_IDENTIFIER=$(printf '%s\n' "$PREVIOUS_SIGNATURE_INFO" | sed -n 's/^TeamIdentifier=//p' | head -n 1)
  [ "$PREVIOUS_TEAM_IDENTIFIER" != "not set" ] || PREVIOUS_TEAM_IDENTIFIER=
  PREVIOUS_AUTHORITY=$(printf '%s\n' "$PREVIOUS_SIGNATURE_INFO" | sed -n 's/^Authority=//p' | head -n 1)
  PREVIOUS_SIGNING_KIND=unknown
  if printf '%s\n' "$PREVIOUS_SIGNATURE_INFO" | grep -q '^Signature=adhoc'; then
    PREVIOUS_SIGNING_KIND=adhoc
  elif printf '%s\n' "$PREVIOUS_SIGNATURE_INFO" | grep -q '^Authority=Developer ID Application'; then
    PREVIOUS_SIGNING_KIND=developer-id
  elif [ -n "$PREVIOUS_AUTHORITY" ]; then
    PREVIOUS_SIGNING_KIND=local
  fi
  if [ "$MANUAL_DEVELOPER_ID_BOOTSTRAP" = "1" ]; then
    case "$PREVIOUS_SIGNING_KIND" in
      local|adhoc) ;;
      *) fail "Developer ID migration bootstrap requires a historical local or ad-hoc predecessor" ;;
    esac
    [ -z "$PREVIOUS_TEAM_IDENTIFIER" ] || fail "historical predecessor unexpectedly has a signing team"
    [ "$SIGNING_KIND" = "developer-id" ] || fail "Developer ID migration bootstrap requires Developer ID Application signing"
    [ -n "$TEAM_IDENTIFIER" ] || fail "Developer ID migration bootstrap requires a signing team identifier"
    IDENTITY_CHECK=manual-developer-id-bootstrap
  else
    [ "$PREVIOUS_SIGNING_KIND" = "$SIGNING_KIND" ] || fail "signing kind changed"

    if [ "$SIGNING_KIND" = "developer-id" ] || [ "$SIGNING_KIND" = "local" ]; then
      if [ "$SIGNING_KIND" = "developer-id" ]; then
        [ -n "$PREVIOUS_TEAM_IDENTIFIER" ] || fail "previous signing team is unavailable"
        [ -n "$TEAM_IDENTIFIER" ] || fail "new signing team is unavailable"
        [ "$PREVIOUS_TEAM_IDENTIFIER" = "$TEAM_IDENTIFIER" ] || fail "signing team changed"
      else
        [ -z "$PREVIOUS_TEAM_IDENTIFIER" ] || fail "unexpected previous local signing team"
        [ -z "$TEAM_IDENTIFIER" ] || fail "unexpected new local signing team"
        [ "$PREVIOUS_AUTHORITY" = "$AUTHORITY" ] || fail "local signing authority changed"
      fi
      PREVIOUS_REQUIREMENT=$(codesign -dr - "$PREVIOUS_APP_BUNDLE" 2>&1 | sed -n 's/^designated => //p' | head -n 1)
      [ -n "$PREVIOUS_REQUIREMENT" ] || fail "previous designated requirement is unavailable"
      codesign -R="$PREVIOUS_REQUIREMENT" --verify "$APP_BUNDLE" 2>/dev/null || fail "new app does not satisfy the previous designated requirement"
      IDENTITY_CHECK=designated-requirement
    else
      # Ad-hoc signatures bind their designated requirement to a content hash,
      # which changes on every build. Local validation can prove only the stable
      # bundle shape; public readiness always requires the Developer ID path.
      [ -z "$PREVIOUS_TEAM_IDENTIFIER" ] || fail "unexpected previous ad-hoc signing team"
      [ -z "$TEAM_IDENTIFIER" ] || fail "unexpected new ad-hoc signing team"
      IDENTITY_CHECK=structural-adhoc
    fi
  fi
fi

if [ -n "$UPDATE_ARCHIVE" ]; then
  [ -f "$UPDATE_ARCHIVE" ] || fail "update archive is missing"
  unzip -tq "$UPDATE_ARCHIVE" >/dev/null || fail "update archive is corrupt"
  ARCHIVE_LIST=$(unzip -Z1 "$UPDATE_ARCHIVE")
  [ -z "$(printf '%s\n' "$ARCHIVE_LIST" | sort | uniq -d)" ] || fail "archive contains duplicate paths"
  printf '%s\n' "$ARCHIVE_LIST" | grep -q '^GRAF.app/' || fail "archive does not contain GRAF.app at its root"
  if printf '%s\n' "$ARCHIVE_LIST" |
    grep -Ev '^(GRAF\.app(/|$)|__MACOSX(/?$|/GRAF\.app(/|$)))' |
    grep -q .; then
    fail "archive contains an unexpected top-level entry"
  fi
  if printf '%s\n' "$ARCHIVE_LIST" | grep -Eq '(^|/)\.\.(/|$)'; then
    fail "archive contains an unsafe parent path"
  fi
  # The ERE needs two backslashes to match one literal backslash.
  # shellcheck disable=SC1003
  if printf '%s\n' "$ARCHIVE_LIST" | grep -Eq '^/|\\'; then
    fail "archive contains an unsafe absolute or backslash path"
  fi
  ARCHIVE_INFO_SHA=$(unzip -p "$UPDATE_ARCHIVE" GRAF.app/Contents/Info.plist | shasum -a 256 | awk '{print $1}')
  ARCHIVE_EXECUTABLE_SHA=$(unzip -p "$UPDATE_ARCHIVE" GRAF.app/Contents/MacOS/GRAF | shasum -a 256 | awk '{print $1}')
  ARCHIVE_CODE_RESOURCES_SHA=$(unzip -p "$UPDATE_ARCHIVE" GRAF.app/Contents/_CodeSignature/CodeResources | shasum -a 256 | awk '{print $1}')
  [ "$ARCHIVE_INFO_SHA" = "$(shasum -a 256 "$INFO_PLIST" | awk '{print $1}')" ] || fail "archive Info.plist differs from the validated app"
  [ "$ARCHIVE_EXECUTABLE_SHA" = "$(shasum -a 256 "$EXECUTABLE" | awk '{print $1}')" ] || fail "archive executable differs from the validated app"
  [ "$ARCHIVE_CODE_RESOURCES_SHA" = "$(shasum -a 256 "$APP_BUNDLE/Contents/_CodeSignature/CodeResources" | awk '{print $1}')" ] || fail "archive code resources differ from the validated app"
fi

if [ -n "$UPDATE_APPCAST" ]; then
  [ -n "$UPDATE_ARCHIVE" ] || fail "appcast validation requires the matching archive"
  [ -f "$UPDATE_APPCAST" ] || fail "appcast is missing"
  xmllint --noout "$UPDATE_APPCAST" 2>/dev/null || fail "appcast XML is malformed"
  grep -Fq '<!-- sparkle-signatures:' "$UPDATE_APPCAST" || fail "appcast feed signature is missing"
  grep -Fq 'edSignature:' "$UPDATE_APPCAST" || fail "appcast feed EdDSA signature is missing"
  ITEM_XPATH="//*[local-name()='item' and *[local-name()='version' and normalize-space(text())='$VERSION']]"
  ITEM_COUNT=$(xmllint --xpath "count($ITEM_XPATH)" "$UPDATE_APPCAST")
  [ "$ITEM_COUNT" = "1" ] || fail "appcast must contain exactly one item for the update version"
  ENCLOSURE_XPATH="$ITEM_XPATH/*[local-name()='enclosure']"
  ENCLOSURE_COUNT=$(xmllint --xpath "count($ENCLOSURE_XPATH)" "$UPDATE_APPCAST")
  [ "$ENCLOSURE_COUNT" = "1" ] || fail "appcast update item must contain exactly one enclosure"
  APPCAST_URL=$(xmllint --xpath "string(($ENCLOSURE_XPATH)/@url)" "$UPDATE_APPCAST")
  APPCAST_LENGTH=$(xmllint --xpath "string(($ENCLOSURE_XPATH)/@length)" "$UPDATE_APPCAST")
  APPCAST_SIGNATURE=$(xmllint --xpath "string(($ENCLOSURE_XPATH)/@*[local-name()='edSignature'])" "$UPDATE_APPCAST")
  APPCAST_SHORT_VERSION=$(xmllint --xpath "string(($ITEM_XPATH)/*[local-name()='shortVersionString'])" "$UPDATE_APPCAST")
  APPCAST_MINIMUM_SYSTEM=$(xmllint --xpath "string(($ITEM_XPATH)/*[local-name()='minimumSystemVersion'])" "$UPDATE_APPCAST")
  APPCAST_HARDWARE=$(xmllint --xpath "string(($ITEM_XPATH)/*[local-name()='hardwareRequirements'])" "$UPDATE_APPCAST")
  APPCAST_PUB_DATE=$(xmllint --xpath "normalize-space(string(($ITEM_XPATH)/*[local-name()='pubDate']))" "$UPDATE_APPCAST")
  APPCAST_RELEASE_NOTES=$(xmllint --xpath "normalize-space(string(($ITEM_XPATH)/*[local-name()='description']))" "$UPDATE_APPCAST")
  case "$APPCAST_URL" in
    https://*) ;;
    *) fail "appcast enclosure URL must use HTTPS" ;;
  esac
  case "$APPCAST_URL" in
    *"@"*|*"?"*|*"#"*) fail "appcast enclosure URL must be credential-free" ;;
  esac
  [ "$APPCAST_SHORT_VERSION" = "$VERSION" ] || fail "appcast short version differs"
  [ "$APPCAST_MINIMUM_SYSTEM" = "14.5" ] || [ "$APPCAST_MINIMUM_SYSTEM" = "14.5.0" ] || fail "appcast minimum system differs"
  [ "$APPCAST_HARDWARE" = "arm64" ] || fail "appcast hardware requirement differs"
  [ -n "$APPCAST_PUB_DATE" ] || fail "appcast publication date is missing"
  [ -n "$APPCAST_RELEASE_NOTES" ] || fail "appcast release notes are missing"
  printf '%s\n' "$APPCAST_RELEASE_NOTES" | grep -Eq '[А-Яа-яЁё]' || fail "appcast release notes must contain Russian user-facing text"
  [ -n "$APPCAST_SIGNATURE" ] || fail "archive EdDSA signature is missing"
  EXPECTED_APPCAST_URL="${FEED_URL%/graf-appcast.xml}/$(basename -- "$UPDATE_ARCHIVE")"
  [ "$APPCAST_URL" = "$EXPECTED_APPCAST_URL" ] || fail "appcast enclosure URL differs from the configured feed directory"
  ARCHIVE_LENGTH=$(stat -f '%z' "$UPDATE_ARCHIVE")
  [ "$APPCAST_LENGTH" = "$ARCHIVE_LENGTH" ] || fail "appcast archive length differs"
fi

if [ "$MANUAL_DEVELOPER_ID_BOOTSTRAP" = "1" ]; then
  [ "$SIGNING_KIND" = "developer-id" ] || fail "Developer ID migration bootstrap requires Developer ID Application signing"
  [ -n "$TEAM_IDENTIFIER" ] || fail "Developer ID migration bootstrap requires a signing team identifier"
  printf '%s\n' "$SIGNATURE_INFO" | grep -Eq 'flags=.*\(runtime\)' || fail "Developer ID migration bootstrap requires hardened runtime"
  xcrun stapler validate "$APP_BUNDLE" >/dev/null 2>&1 || fail "notarization staple is invalid for Developer ID migration bootstrap"
  spctl --assess --type execute --verbose=4 "$APP_BUNDLE" >/dev/null 2>&1 || fail "Gatekeeper rejected GRAF.app for Developer ID migration bootstrap"
elif [ "$REQUIRE_PUBLIC_TRUST" = "1" ]; then
  [ "$SIGNING_KIND" = "developer-id" ] || fail "public update requires Developer ID Application signing"
  [ -n "$TEAM_IDENTIFIER" ] || fail "public update requires a signing team identifier"
  printf '%s\n' "$SIGNATURE_INFO" | grep -Eq 'flags=.*\(runtime\)' || fail "public update requires hardened runtime"
  xcrun stapler validate "$APP_BUNDLE" >/dev/null 2>&1 || fail "notarization staple is invalid"
  spctl --assess --type execute --verbose=4 "$APP_BUNDLE" >/dev/null 2>&1 || fail "Gatekeeper rejected GRAF.app"
fi

if [ "$REQUIRE_OWNER_ONLY_TRUST" = "1" ]; then
  [ "$REQUIRE_PUBLIC_TRUST" != "1" ] || fail "choose either public or owner-only update trust"
  [ "$SIGNING_KIND" = "local" ] || fail "owner-only update requires local certificate signing"
  [ "$AUTHORITY" = "GRAF Local Code Signing" ] || fail "owner-only update requires GRAF Local Code Signing"
  [ "$IDENTITY_CHECK" = "designated-requirement" ] || fail "owner-only update requires designated-requirement continuity"
  [ "$UPDATE_CONFIGURATION" = "configured" ] || fail "owner-only update requires a complete signed feed configuration"
  printf '%s\n' "$SIGNATURE_INFO" | grep -Eq 'flags=.*\(runtime\)' || fail "owner-only update requires hardened runtime"
fi

echo "app-update validation passed: version=$VERSION updater=$UPDATE_CONFIGURATION signing=$SIGNING_KIND identity=$IDENTITY_CHECK continuity=$UPDATE_CONTINUITY previous=$([ -n "$PREVIOUS_APP_BUNDLE" ] && printf yes || printf no) archive=$([ -n "$UPDATE_ARCHIVE" ] && printf yes || printf no) appcast=$([ -n "$UPDATE_APPCAST" ] && printf yes || printf no)"
