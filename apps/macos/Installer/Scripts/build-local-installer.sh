#!/usr/bin/env sh
set -eu
export COPYFILE_DISABLE=1

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
INSTALLER_DIR=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
MACOS_DIR=$(CDPATH='' cd -- "$INSTALLER_DIR/.." && pwd)
REPO_ROOT=$(git -C "$MACOS_DIR" rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$REPO_ROOT" ]; then
  REPO_ROOT=$(CDPATH='' cd -- "$MACOS_DIR/../.." && pwd)
fi
BUILD_DIR="${GRAF_INSTALLER_BUILD_DIR:-${TWO_BRAIN_REC_INSTALLER_BUILD_DIR:-"$MACOS_DIR/.build/installer"}}"
STAGE_DIR="$BUILD_DIR/stage"
COMPONENT_DIR="$BUILD_DIR/components"
SCRIPTS_DIR="$BUILD_DIR/scripts"
APP_BUNDLE="$MACOS_DIR/RecApp/.build/GRAF.app"
APP_ICON="$MACOS_DIR/RecApp/Resources/AppIcon.icns"
APP_CORE_RESOURCE_BUNDLE_NAME="TwoBrainRecMacOS_TwoBrainRecAppCore.bundle"
SPARKLE_LICENSE_SOURCE="$MACOS_DIR/.build/checkouts/Sparkle/LICENSE"
SPARKLE_LICENSE_SHA256="389a4e4e9a32f059775b13a06e25a591445ba229d2838d26dd3e7c0c45127cfe"
WORDMARK_DARK="$MACOS_DIR/RecApp/Resources/GrafWordmarkDark.png"
WORDMARK_DARK_2X="$MACOS_DIR/RecApp/Resources/GrafWordmarkDark@2x.png"
WORDMARK_LIGHT="$MACOS_DIR/RecApp/Resources/GrafWordmarkLight.png"
WORDMARK_LIGHT_2X="$MACOS_DIR/RecApp/Resources/GrafWordmarkLight@2x.png"
OUTPUT_PKG="${1:-"$BUILD_DIR/graf-local.pkg"}"
APP_SIGN_IDENTITY="${GRAF_APP_SIGN_IDENTITY:-${TWO_BRAIN_REC_APP_SIGN_IDENTITY:-${DEVELOPER_ID_APPLICATION_IDENTITY:-}}}"
UPDATE_FEED_URL="${GRAF_UPDATE_FEED_URL:-}"
SPARKLE_PUBLIC_ED_KEY="${GRAF_SPARKLE_PUBLIC_ED_KEY:-}"
UPDATE_SIGNING_MANIFEST="$INSTALLER_DIR/UpdateSigningKey.json"
RELEASE_SIGNING_COMMON="$SCRIPT_DIR/release-signing-common.sh"
ALLOW_ADHOC_APP_SIGNING="${GRAF_ALLOW_ADHOC_APP_SIGNING:-${TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING:-0}}"
ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING="${GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING:-${TWO_BRAIN_REC_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING:-0}}"
REQUIRE_PUBLIC_TRUST="${GRAF_REQUIRE_PUBLIC_UPDATE_TRUST:-0}"
DEVELOPER_ID_INSTALLER_IDENTITY="${DEVELOPER_ID_INSTALLER_IDENTITY:-}"

case "$REQUIRE_PUBLIC_TRUST" in
  0) ;;
  1)
    case "$APP_SIGN_IDENTITY" in
      "Developer ID Application:"*) ;;
      *)
        echo "Public release requires a Developer ID Application identity; local, ad-hoc and development identities are rejected." >&2
        exit 1
        ;;
    esac
    case "$DEVELOPER_ID_INSTALLER_IDENTITY" in
      "Developer ID Installer:"*) ;;
      *)
        echo "Public package release requires a Developer ID Installer identity." >&2
        exit 1
        ;;
    esac
    [ "$ALLOW_ADHOC_APP_SIGNING" = "0" ] || {
      echo "Public release cannot enable ad-hoc app signing." >&2
      exit 1
    }
    [ "$ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING" = "0" ] || {
      echo "Public release cannot enable local self-signed app signing." >&2
      exit 1
    }
    ;;
  *)
    echo "GRAF_REQUIRE_PUBLIC_UPDATE_TRUST must be 0 or 1." >&2
    exit 1
    ;;
esac

DEVELOPER_TOOLS_STATUS=$(DevToolsSecurity -status 2>&1 || true)
DEVELOPER_TOOLS_ENABLED=0
case "$DEVELOPER_TOOLS_STATUS" in
  *"currently enabled"*) DEVELOPER_TOOLS_ENABLED=1 ;;
esac

default_product_version() {
  today=$(date +%Y.%m.%d)
  today_pattern=$(printf '%s\n' "$today" | sed 's/\./\\./g')
  changelog="$REPO_ROOT/CHANGELOG.md"
  changelog_counters=""
  tag_counters=""
  if [ -f "$changelog" ]; then
    changelog_counters=$(sed -n "s/^## \[$today_pattern\.\([0-9][0-9]*\)\].*/\1/p" "$changelog")
  fi
  tag_counters=$(git -C "$REPO_ROOT" tag --list "v$today.*" 2>/dev/null |
    sed -n "s/^v$today_pattern\.\([0-9][0-9]*\)$/\1/p")
  latest_counter=$(
    {
      printf '%s\n' "$changelog_counters"
      printf '%s\n' "$tag_counters"
    } | awk 'NF { if ($1 + 0 > max) max = $1 + 0 } END { if (max > 0) print max }'
  )
  if [ -n "$latest_counter" ]; then
    printf '%s.%s\n' "$today" "$((latest_counter + 1))"
  else
    printf '%s.1\n' "$today"
  fi
}

VERSION="${GRAF_VERSION:-${TWO_BRAIN_REC_VERSION:-$(default_product_version)}}"
case "$VERSION" in
  [0-9][0-9][0-9][0-9].[0-9][0-9].[0-9][0-9].[0-9]*)
    ;;
  *)
    cat >&2 <<EOF
Invalid GRAF product version: $VERSION

macOS bundle and package fields use the numeric CalVer release train without
the git tag prefix. Use:

  GRAF_VERSION=YYYY.MM.DD.N sh apps/macos/Installer/Scripts/build-local-installer.sh

The matching git tag/GitHub Release adds the leading v: vYYYY.MM.DD.N.
EOF
    exit 1
    ;;
esac
echo "Building GRAF version $VERSION" >&2

[ -r "$RELEASE_SIGNING_COMMON" ] || {
  echo "Release-signing trust helper is missing." >&2
  exit 1
}
# shellcheck source=release-signing-common.sh
. "$RELEASE_SIGNING_COMMON"

if [ -n "$UPDATE_FEED_URL" ]; then
  case "$UPDATE_FEED_URL" in
    https://*) ;;
    *)
      echo "GRAF_UPDATE_FEED_URL must use HTTPS." >&2
      exit 1
      ;;
  esac
  case "$UPDATE_FEED_URL" in
    *"@"*|*"?"*|*"#"*)
      echo "GRAF_UPDATE_FEED_URL must be public and credential-free, without query or fragment data." >&2
      exit 1
      ;;
  esac
  UPDATE_FEED_LOCATION=${UPDATE_FEED_URL#https://}
  UPDATE_FEED_AUTHORITY=${UPDATE_FEED_LOCATION%%/*}
  if [ -z "$UPDATE_FEED_AUTHORITY" ]; then
    echo "GRAF_UPDATE_FEED_URL must contain a host." >&2
    exit 1
  fi
  case "$UPDATE_FEED_LOCATION" in
    */graf-appcast.xml) ;;
    *)
      echo "GRAF_UPDATE_FEED_URL must end with /graf-appcast.xml." >&2
      exit 1
      ;;
  esac
  if ! release_signing_require_active_manifest "$UPDATE_SIGNING_MANIFEST"; then
    exit 1
  fi
  if [ -n "$SPARKLE_PUBLIC_ED_KEY" ] && [ "$SPARKLE_PUBLIC_ED_KEY" != "$RELEASE_SIGNING_PUBLIC_KEY" ]; then
    echo "GRAF_SPARKLE_PUBLIC_ED_KEY must equal the active public signing manifest; it cannot override trust." >&2
    exit 1
  fi
  SPARKLE_PUBLIC_ED_KEY=$RELEASE_SIGNING_PUBLIC_KEY
elif [ -n "$SPARKLE_PUBLIC_ED_KEY" ]; then
  echo "Incomplete trusted update configuration: set GRAF_UPDATE_FEED_URL with the active public signing manifest, or neither." >&2
  exit 1
fi

rm -rf "$BUILD_DIR"
mkdir -p "$STAGE_DIR/app/Applications"
mkdir -p "$COMPONENT_DIR"
mkdir -p "$SCRIPTS_DIR/desktop-app"
swift build --package-path "$MACOS_DIR" -c release --product TwoBrainRecApp

BIN_DIR=$(swift build --package-path "$MACOS_DIR" -c release --show-bin-path)
APP_EXECUTABLE="$BIN_DIR/TwoBrainRecApp"
APP_CORE_RESOURCE_BUNDLE="$BIN_DIR/$APP_CORE_RESOURCE_BUNDLE_NAME"
SPARKLE_FRAMEWORK_SOURCE="$MACOS_DIR/.build/artifacts/sparkle/Sparkle/Sparkle.xcframework/macos-arm64_x86_64/Sparkle.framework"

if [ ! -x "$APP_EXECUTABLE" ]; then
  echo "Missing app executable at $APP_EXECUTABLE" >&2
  exit 1
fi
if [ ! -f "$APP_ICON" ]; then
  echo "Missing app icon at $APP_ICON" >&2
  exit 1
fi
if [ ! -d "$APP_CORE_RESOURCE_BUNDLE" ]; then
  echo "Missing app resource bundle at $APP_CORE_RESOURCE_BUNDLE" >&2
  exit 1
fi
if [ -z "$SPARKLE_FRAMEWORK_SOURCE" ] || [ ! -d "$SPARKLE_FRAMEWORK_SOURCE" ]; then
  echo "Missing pinned Sparkle framework under $MACOS_DIR/.build/artifacts" >&2
  exit 1
fi
if [ ! -f "$SPARKLE_LICENSE_SOURCE" ]; then
  echo "Missing pinned Sparkle license at $SPARKLE_LICENSE_SOURCE" >&2
  exit 1
fi
if [ "$(shasum -a 256 "$SPARKLE_LICENSE_SOURCE" | awk '{print $1}')" != "$SPARKLE_LICENSE_SHA256" ]; then
  echo "Pinned Sparkle license checksum differs from release 2.9.4." >&2
  exit 1
fi
for resource in "$WORDMARK_DARK" "$WORDMARK_DARK_2X" "$WORDMARK_LIGHT" "$WORDMARK_LIGHT_2X"; do
  if [ ! -f "$resource" ]; then
    echo "Missing app wordmark resource at $resource" >&2
    exit 1
  fi
done

rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"
mkdir -p "$APP_BUNDLE/Contents/Frameworks"
cp "$APP_EXECUTABLE" "$APP_BUNDLE/Contents/MacOS/GRAF"
ditto "$SPARKLE_FRAMEWORK_SOURCE" "$APP_BUNDLE/Contents/Frameworks/Sparkle.framework"
cp -R "$APP_CORE_RESOURCE_BUNDLE" "$APP_BUNDLE/Contents/Resources/"
cp "$SPARKLE_LICENSE_SOURCE" "$APP_BUNDLE/Contents/Resources/Sparkle-LICENSE.txt"
cp "$APP_ICON" "$APP_BUNDLE/Contents/Resources/AppIcon.icns"
cp "$WORDMARK_DARK" "$APP_BUNDLE/Contents/Resources/GrafWordmarkDark.png"
cp "$WORDMARK_DARK_2X" "$APP_BUNDLE/Contents/Resources/GrafWordmarkDark@2x.png"
cp "$WORDMARK_LIGHT" "$APP_BUNDLE/Contents/Resources/GrafWordmarkLight.png"
cp "$WORDMARK_LIGHT_2X" "$APP_BUNDLE/Contents/Resources/GrafWordmarkLight@2x.png"
cat > "$APP_BUNDLE/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleExecutable</key>
  <string>GRAF</string>
  <key>CFBundleDisplayName</key>
  <string>GRAF</string>
  <key>CFBundleIdentifier</key>
  <string>pro.2brain.graf</string>
  <key>CFBundleIconFile</key>
  <string>AppIcon</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>GRAF</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>$VERSION</string>
  <key>CFBundleVersion</key>
  <string>$VERSION</string>
  <key>LSMinimumSystemVersion</key>
  <string>14.5</string>
  <key>NSHighResolutionCapable</key>
  <true/>
  <key>ApplePersistenceIgnoreState</key>
  <true/>
  <key>NSQuitAlwaysKeepsWindows</key>
  <false/>
  <key>NSMicrophoneUsageDescription</key>
  <string>GRAF использует доступ к микрофону, чтобы проверить и записать звук встречи.</string>
  <key>NSAudioCaptureUsageDescription</key>
  <string>GRAF использует доступ к системному звуку, чтобы сохранить входящий звук встречи локально.</string>
  <key>NSScreenCaptureUsageDescription</key>
  <string>GRAF использует доступ к записи экрана и системного звука, чтобы сохранить входящий звук встречи локально.</string>
  <key>NSPrincipalClass</key>
  <string>NSApplication</string>
</dict>
</plist>
EOF

if [ -n "$UPDATE_FEED_URL" ]; then
  /usr/bin/plutil -insert SUFeedURL -string "$UPDATE_FEED_URL" "$APP_BUNDLE/Contents/Info.plist"
  /usr/bin/plutil -insert SUPublicEDKey -string "$SPARKLE_PUBLIC_ED_KEY" "$APP_BUNDLE/Contents/Info.plist"
  /usr/bin/plutil -insert SUEnableAutomaticChecks -bool YES "$APP_BUNDLE/Contents/Info.plist"
  /usr/bin/plutil -insert SUScheduledCheckInterval -integer 86400 "$APP_BUNDLE/Contents/Info.plist"
  /usr/bin/plutil -insert SUAutomaticallyUpdate -bool NO "$APP_BUNDLE/Contents/Info.plist"
  /usr/bin/plutil -insert SUAllowsAutomaticUpdates -bool NO "$APP_BUNDLE/Contents/Info.plist"
  /usr/bin/plutil -insert SUEnableSystemProfiling -bool NO "$APP_BUNDLE/Contents/Info.plist"
  /usr/bin/plutil -insert SUVerifyUpdateBeforeExtraction -bool YES "$APP_BUNDLE/Contents/Info.plist"
  /usr/bin/plutil -insert SURequireSignedFeed -bool YES "$APP_BUNDLE/Contents/Info.plist"
  /usr/bin/plutil -insert SUSignedFeedFailureExpirationInterval -integer 0 "$APP_BUNDLE/Contents/Info.plist"
fi

if ! otool -l "$APP_BUNDLE/Contents/MacOS/GRAF" | grep -Fq '@executable_path/../Frameworks'; then
  install_name_tool -add_rpath '@executable_path/../Frameworks' "$APP_BUNDLE/Contents/MacOS/GRAF"
fi

if [ -z "$APP_SIGN_IDENTITY" ] &&
   [ "$ALLOW_ADHOC_APP_SIGNING" != "1" ] &&
   [ "$DEVELOPER_TOOLS_ENABLED" != "1" ]; then
  cat >&2 <<'EOF'
Missing app signing identity and Developer Tools Security is disabled.

For a local development build, enable Developer Tools Security once:

  sudo DevToolsSecurity -enable
  spctl developer-mode enable-terminal

Then rerun:

  sh apps/macos/Installer/Scripts/build-local-installer.sh

For an isolated signed fixture, install an Apple Development identity, then run
the local command below. This is never a public release command; public release
must use the Developer ID guard in the Installer README:

  GRAF_APP_SIGN_IDENTITY="Apple Development: Your Name (TEAMID)" \
    sh apps/macos/Installer/Scripts/build-local-installer.sh

For an isolated permission-retention test fixture with a locally trusted
self-signed identity, run. Never use this with a public host, GitHub Release,
package release or appcast:

  GRAF_APP_SIGN_IDENTITY="GRAF Local Code Signing" \
  GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1 \
    sh apps/macos/Installer/Scripts/build-local-installer.sh

For packaging-only tests on locked-down hosts, set:

  GRAF_ALLOW_ADHOC_APP_SIGNING=1 \
    sh apps/macos/Installer/Scripts/build-local-installer.sh
EOF
  exit 1
fi

xattr -cr "$APP_BUNDLE" 2>/dev/null || true

sign_nested_code() {
  target=$1
  if [ -n "$APP_SIGN_IDENTITY" ]; then
    case "$APP_SIGN_IDENTITY" in
      "Developer ID Application:"*)
        codesign --force --options runtime --timestamp \
          --preserve-metadata=identifier,entitlements,flags \
          --sign "$APP_SIGN_IDENTITY" "$target" >/dev/null
        ;;
      *)
        codesign --force --options runtime --timestamp=none \
          --preserve-metadata=identifier,entitlements,flags \
          --sign "$APP_SIGN_IDENTITY" "$target" >/dev/null
        ;;
    esac
  else
    codesign --force --options runtime --timestamp=none \
      --preserve-metadata=identifier,entitlements,flags \
      --sign - "$target" >/dev/null
  fi
}

sign_app_bundle() {
  target=$1
  set -- --force --options runtime
  case "$APP_SIGN_IDENTITY" in
    "Developer ID Application:"*) set -- "$@" --timestamp ;;
    *) set -- "$@" --timestamp=none ;;
  esac
  if [ -n "$APP_ENTITLEMENTS" ]; then
    set -- "$@" --entitlements "$APP_ENTITLEMENTS"
  fi
  if [ -n "$APP_SIGN_IDENTITY" ]; then
    set -- "$@" --sign "$APP_SIGN_IDENTITY"
  else
    set -- "$@" --sign -
  fi
  codesign "$@" "$target" >/dev/null
}

SPARKLE_FRAMEWORK="$APP_BUNDLE/Contents/Frameworks/Sparkle.framework"
SPARKLE_FRAMEWORK_VERSION="$SPARKLE_FRAMEWORK/Versions/B"
sign_nested_code "$SPARKLE_FRAMEWORK_VERSION/XPCServices/Downloader.xpc"
sign_nested_code "$SPARKLE_FRAMEWORK_VERSION/XPCServices/Installer.xpc"
sign_nested_code "$SPARKLE_FRAMEWORK_VERSION/Updater.app"
sign_nested_code "$SPARKLE_FRAMEWORK_VERSION/Autoupdate"
sign_nested_code "$SPARKLE_FRAMEWORK"

SPARKLE_SIGNATURE=$(codesign -dv --verbose=4 "$SPARKLE_FRAMEWORK" 2>&1)
SPARKLE_TEAM_IDENTIFIER=$(printf '%s\n' "$SPARKLE_SIGNATURE" | sed -n 's/^TeamIdentifier=//p' | head -n 1)
[ "$SPARKLE_TEAM_IDENTIFIER" != "not set" ] || SPARKLE_TEAM_IDENTIFIER=
APP_ENTITLEMENTS="$BUILD_DIR/app-signing.entitlements"
LIBRARY_VALIDATION_ENTITLEMENT=
if [ -z "$SPARKLE_TEAM_IDENTIFIER" ]; then
  LIBRARY_VALIDATION_ENTITLEMENT='  <key>com.apple.security.cs.disable-library-validation</key>
  <true/>'
fi
cat > "$APP_ENTITLEMENTS" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "https://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>com.apple.security.device.audio-input</key>
  <true/>
$LIBRARY_VALIDATION_ENTITLEMENT
</dict>
</plist>
EOF

if [ -z "$APP_SIGN_IDENTITY" ] && [ "$DEVELOPER_TOOLS_ENABLED" = "1" ]; then
  echo "Using ad-hoc app signing for local development because Developer Tools Security is enabled." >&2
fi
sign_app_bundle "$APP_BUNDLE"

APP_SIGNATURE=$(codesign -dv --verbose=4 "$APP_BUNDLE" 2>&1)
if printf '%s\n' "$APP_SIGNATURE" | grep -q '^Signature=adhoc' &&
   [ "$ALLOW_ADHOC_APP_SIGNING" != "1" ] &&
   [ "$DEVELOPER_TOOLS_ENABLED" != "1" ]; then
  echo "Refusing to package ad-hoc signed app bundle while Developer Tools Security is disabled." >&2
  exit 1
fi

if [ -n "$APP_SIGN_IDENTITY" ] &&
   ! printf '%s\n' "$APP_SIGNATURE" |
     grep -Eq '^Authority=(Apple Development|Developer ID Application|Apple Distribution|Mac Developer)'; then
  if [ "$ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING" = "1" ] &&
     ! printf '%s\n' "$APP_SIGNATURE" | grep -q '^Signature=adhoc' &&
     printf '%s\n' "$APP_SIGNATURE" | grep -q '^Authority='; then
    echo "Using local self-signed app signing identity for local validation only: $APP_SIGN_IDENTITY" >&2
    echo "This package is not Developer ID signed or notarized for public distribution." >&2
  else
    cat >&2 <<EOF
App bundle was signed, but not with an Apple application signing identity.

Observed signature:
$APP_SIGNATURE

Use a Developer ID Application identity for a public release-like build. The
local command below is an isolated permission-retention fixture only:

  GRAF_APP_SIGN_IDENTITY="GRAF Local Code Signing" \\
  GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1 \\
    sh apps/macos/Installer/Scripts/build-local-installer.sh
EOF
    exit 1
  fi
fi

cp -R "$APP_BUNDLE" "$STAGE_DIR/app/Applications/"
xattr -cr "$STAGE_DIR/app" 2>/dev/null || true
cat > "$SCRIPTS_DIR/desktop-app/preinstall" <<'EOF'
#!/usr/bin/env sh
set -eu

LEGACY_APP="/Applications/2brain Rec.app"
if [ -d "$LEGACY_APP" ]; then
  rm -rf "$LEGACY_APP" || true
fi
exit 0
EOF
chmod 755 "$SCRIPTS_DIR/desktop-app/preinstall"

pkgbuild \
  --root "$STAGE_DIR/app" \
  --identifier "pro.2brain.graf.desktop-app" \
  --version "$VERSION" \
  --install-location "/" \
  --scripts "$SCRIPTS_DIR/desktop-app" \
  --ownership recommended \
  "$COMPONENT_DIR/graf-desktop-app.pkg"

cat > "$BUILD_DIR/distribution.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<installer-gui-script minSpecVersion="2">
  <title>GRAF</title>
  <options customize="never" require-scripts="true" rootVolumeOnly="true"/>
  <domains enable_anywhere="false" enable_currentUserHome="false" enable_localSystem="true"/>
  <installation-check script="InstallationCheck()"/>
  <script>
function InstallationCheck() {
  if(system.compareVersions(system.version.ProductVersion, "14.5") &lt; 0) {
    my.result.type = "Fatal";
    my.result.title = "Unsupported macOS";
    my.result.message = "GRAF requires macOS 14.5 or later.";
    return false;
  }
  return true;
}
  </script>
  <choices-outline>
    <line choice="default">
      <line choice="desktop-app"/>
    </line>
  </choices-outline>
  <choice id="default" title="GRAF" start_selected="true" start_enabled="false" start_visible="false">
    <pkg-ref id="pro.2brain.graf.desktop-app"/>
  </choice>
  <choice id="desktop-app" title="GRAF Desktop App" start_selected="true" start_enabled="false">
    <pkg-ref id="pro.2brain.graf.desktop-app"/>
  </choice>
  <pkg-ref id="pro.2brain.graf.desktop-app" version="$VERSION" auth="Root">graf-desktop-app.pkg</pkg-ref>
</installer-gui-script>
EOF

if [ -n "${DEVELOPER_ID_INSTALLER_IDENTITY:-}" ]; then
  productbuild \
    --distribution "$BUILD_DIR/distribution.xml" \
    --package-path "$COMPONENT_DIR" \
    --sign "$DEVELOPER_ID_INSTALLER_IDENTITY" \
    "$OUTPUT_PKG"
else
  productbuild \
    --distribution "$BUILD_DIR/distribution.xml" \
    --package-path "$COMPONENT_DIR" \
    "$OUTPUT_PKG"
fi

echo "$OUTPUT_PKG"
