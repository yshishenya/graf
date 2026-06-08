#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
INSTALLER_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
MACOS_DIR=$(CDPATH= cd -- "$INSTALLER_DIR/.." && pwd)
BUILD_DIR="${TWO_BRAIN_REC_INSTALLER_BUILD_DIR:-"$MACOS_DIR/.build/installer"}"
STAGE_DIR="$BUILD_DIR/stage"
COMPONENT_DIR="$BUILD_DIR/components"
SCRIPTS_DIR="$BUILD_DIR/scripts"
APP_BUNDLE="$MACOS_DIR/RecApp/.build/2brain Rec.app"
OUTPUT_PKG="${1:-"$BUILD_DIR/2brain-rec-local.pkg"}"
VERSION="${TWO_BRAIN_REC_VERSION:-0.1.0}"
APP_SIGN_IDENTITY="${TWO_BRAIN_REC_APP_SIGN_IDENTITY:-${DEVELOPER_ID_APPLICATION_IDENTITY:-}}"
ALLOW_ADHOC_APP_SIGNING="${TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING:-0}"
DEVELOPER_TOOLS_STATUS=$(DevToolsSecurity -status 2>&1 || true)
DEVELOPER_TOOLS_ENABLED=0
case "$DEVELOPER_TOOLS_STATUS" in
  *"currently enabled"*) DEVELOPER_TOOLS_ENABLED=1 ;;
esac

rm -rf "$BUILD_DIR"
mkdir -p "$STAGE_DIR/driver/Library/Audio/Plug-Ins/HAL"
mkdir -p "$STAGE_DIR/app/Applications"
mkdir -p "$COMPONENT_DIR"
mkdir -p "$SCRIPTS_DIR/audio-driver"

make -C "$MACOS_DIR/AudioDriver" proof-plugin-build
swift build --package-path "$MACOS_DIR" -c release --product TwoBrainRecApp

BIN_DIR=$(swift build --package-path "$MACOS_DIR" -c release --show-bin-path)
APP_EXECUTABLE="$BIN_DIR/TwoBrainRecApp"
DRIVER_BUNDLE="$MACOS_DIR/AudioDriver/.build/proof/2brainRecProof.driver"

if [ ! -x "$APP_EXECUTABLE" ]; then
  echo "Missing app executable at $APP_EXECUTABLE" >&2
  exit 1
fi

if [ ! -d "$DRIVER_BUNDLE" ]; then
  echo "Missing proof driver bundle at $DRIVER_BUNDLE" >&2
  exit 1
fi

rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"
cp "$APP_EXECUTABLE" "$APP_BUNDLE/Contents/MacOS/2brain Rec"
cat > "$APP_BUNDLE/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleExecutable</key>
  <string>2brain Rec</string>
  <key>CFBundleIdentifier</key>
  <string>pro.2brain.rec</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>2brain Rec</string>
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
  <key>NSMicrophoneUsageDescription</key>
  <string>2brain Rec needs microphone access to verify and capture meeting audio.</string>
  <key>NSScreenCaptureUsageDescription</key>
  <string>2brain Rec needs Screen/System Audio access to capture incoming meeting audio into a local recording.</string>
  <key>NSPrincipalClass</key>
  <string>NSApplication</string>
</dict>
</plist>
EOF

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

For a signed pre-release build, install an Apple Development or Developer ID
Application certificate, then run:

  TWO_BRAIN_REC_APP_SIGN_IDENTITY="Apple Development: Your Name (TEAMID)" \
    sh apps/macos/Installer/Scripts/build-local-installer.sh

For packaging-only tests on locked-down hosts, set:

  TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 \
    sh apps/macos/Installer/Scripts/build-local-installer.sh
EOF
  exit 1
fi

if [ -n "$APP_SIGN_IDENTITY" ]; then
  codesign --force --deep --timestamp=none --sign "$APP_SIGN_IDENTITY" "$APP_BUNDLE" >/dev/null
else
  if [ "$DEVELOPER_TOOLS_ENABLED" = "1" ]; then
    echo "Using ad-hoc app signing for local development because Developer Tools Security is enabled." >&2
  fi
  codesign --force --sign - "$APP_BUNDLE" >/dev/null
fi

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
  cat >&2 <<EOF
App bundle was signed, but not with an Apple application signing identity.

Observed signature:
$APP_SIGNATURE

Use an Apple Development or Developer ID Application identity for launchable local builds.
EOF
  exit 1
fi

cp -R "$DRIVER_BUNDLE" "$STAGE_DIR/driver/Library/Audio/Plug-Ins/HAL/"
cp -R "$APP_BUNDLE" "$STAGE_DIR/app/Applications/"
cp "$SCRIPT_DIR/postinstall.sh" "$SCRIPTS_DIR/audio-driver/postinstall"
chmod 755 "$SCRIPTS_DIR/audio-driver/postinstall"

pkgbuild \
  --root "$STAGE_DIR/driver" \
  --identifier "pro.2brain.rec.audio-driver" \
  --version "$VERSION" \
  --install-location "/" \
  --scripts "$SCRIPTS_DIR/audio-driver" \
  --ownership recommended \
  "$COMPONENT_DIR/2brain-rec-audio-driver.pkg"

pkgbuild \
  --root "$STAGE_DIR/app" \
  --identifier "pro.2brain.rec.desktop-app" \
  --version "$VERSION" \
  --install-location "/" \
  --ownership recommended \
  "$COMPONENT_DIR/2brain-rec-desktop-app.pkg"

cat > "$BUILD_DIR/distribution.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<installer-gui-script minSpecVersion="2">
  <title>2brain Rec</title>
  <options customize="never" require-scripts="true" rootVolumeOnly="true"/>
  <domains enable_anywhere="false" enable_currentUserHome="false" enable_localSystem="true"/>
  <installation-check script="InstallationCheck()"/>
  <script>
function InstallationCheck() {
  if(system.compareVersions(system.version.ProductVersion, "14.5") &lt; 0) {
    my.result.type = "Fatal";
    my.result.title = "Unsupported macOS";
    my.result.message = "2brain Rec requires macOS 14.5 or later.";
    return false;
  }
  return true;
}
  </script>
  <choices-outline>
    <line choice="default">
      <line choice="audio-driver"/>
      <line choice="desktop-app"/>
    </line>
  </choices-outline>
  <choice id="default" title="2brain Rec" start_selected="true" start_enabled="false" start_visible="false">
    <pkg-ref id="pro.2brain.rec.audio-driver"/>
    <pkg-ref id="pro.2brain.rec.desktop-app"/>
  </choice>
  <choice id="audio-driver" title="2brain Rec Audio Driver" start_selected="true" start_enabled="false">
    <pkg-ref id="pro.2brain.rec.audio-driver"/>
  </choice>
  <choice id="desktop-app" title="2brain Rec Desktop App" start_selected="true" start_enabled="false">
    <pkg-ref id="pro.2brain.rec.desktop-app"/>
  </choice>
  <pkg-ref id="pro.2brain.rec.audio-driver" version="$VERSION" auth="Root">2brain-rec-audio-driver.pkg</pkg-ref>
  <pkg-ref id="pro.2brain.rec.desktop-app" version="$VERSION" auth="Root">2brain-rec-desktop-app.pkg</pkg-ref>
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
