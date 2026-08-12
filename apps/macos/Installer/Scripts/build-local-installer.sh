#!/usr/bin/env sh
set -eu
export COPYFILE_DISABLE=1

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
INSTALLER_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
MACOS_DIR=$(CDPATH= cd -- "$INSTALLER_DIR/.." && pwd)
REPO_ROOT=$(git -C "$MACOS_DIR" rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$REPO_ROOT" ]; then
  REPO_ROOT=$(CDPATH= cd -- "$MACOS_DIR/../.." && pwd)
fi
BUILD_DIR="${GRAF_INSTALLER_BUILD_DIR:-${TWO_BRAIN_REC_INSTALLER_BUILD_DIR:-"$MACOS_DIR/.build/installer"}}"
STAGE_DIR="$BUILD_DIR/stage"
COMPONENT_DIR="$BUILD_DIR/components"
SCRIPTS_DIR="$BUILD_DIR/scripts"
APP_BUNDLE="$MACOS_DIR/RecApp/.build/GRAF.app"
APP_ICON="$MACOS_DIR/RecApp/Resources/AppIcon.icns"
WORDMARK_DARK="$MACOS_DIR/RecApp/Resources/GrafWordmarkDark.png"
WORDMARK_DARK_2X="$MACOS_DIR/RecApp/Resources/GrafWordmarkDark@2x.png"
WORDMARK_LIGHT="$MACOS_DIR/RecApp/Resources/GrafWordmarkLight.png"
WORDMARK_LIGHT_2X="$MACOS_DIR/RecApp/Resources/GrafWordmarkLight@2x.png"
OUTPUT_PKG="${1:-"$BUILD_DIR/graf.pkg"}"
APP_SIGN_IDENTITY="${GRAF_APP_SIGN_IDENTITY:-${TWO_BRAIN_REC_APP_SIGN_IDENTITY:-${DEVELOPER_ID_APPLICATION_IDENTITY:-}}}"
ALLOW_ADHOC_APP_SIGNING="${GRAF_ALLOW_ADHOC_APP_SIGNING:-${TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING:-0}}"
ARM64_TRIPLE="arm64-apple-macosx14.5"
X86_64_TRIPLE="x86_64-apple-macosx14.5"
ARM64_SCRATCH="$BUILD_DIR/swiftpm-arm64"
X86_64_SCRATCH="$BUILD_DIR/swiftpm-x86_64"
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

rm -rf "$BUILD_DIR"
mkdir -p "$STAGE_DIR/app/Applications"
mkdir -p "$COMPONENT_DIR"
mkdir -p "$SCRIPTS_DIR/desktop-app"

swift build \
  --package-path "$MACOS_DIR" \
  --product TwoBrainRecApp \
  --triple "$ARM64_TRIPLE" \
  --scratch-path "$ARM64_SCRATCH" \
  -c release
swift build \
  --package-path "$MACOS_DIR" \
  --product TwoBrainRecApp \
  --triple "$X86_64_TRIPLE" \
  --scratch-path "$X86_64_SCRATCH" \
  -c release

ARM64_BIN_DIR=$(swift build \
  --package-path "$MACOS_DIR" \
  --product TwoBrainRecApp \
  --triple "$ARM64_TRIPLE" \
  --scratch-path "$ARM64_SCRATCH" \
  -c release \
  --show-bin-path)
X86_64_BIN_DIR=$(swift build \
  --package-path "$MACOS_DIR" \
  --product TwoBrainRecApp \
  --triple "$X86_64_TRIPLE" \
  --scratch-path "$X86_64_SCRATCH" \
  -c release \
  --show-bin-path)
ARM64_EXECUTABLE="$ARM64_BIN_DIR/TwoBrainRecApp"
X86_64_EXECUTABLE="$X86_64_BIN_DIR/TwoBrainRecApp"

verify_architecture() {
  executable="$1"
  expected_architecture="$2"
  if [ ! -x "$executable" ]; then
    echo "Missing app executable at $executable" >&2
    exit 1
  fi
  actual_architectures=$(lipo -archs "$executable")
  if [ "$actual_architectures" != "$expected_architecture" ]; then
    echo "Expected $executable to contain only $expected_architecture, got: $actual_architectures" >&2
    exit 1
  fi
}

verify_architecture "$ARM64_EXECUTABLE" arm64
verify_architecture "$X86_64_EXECUTABLE" x86_64
if [ ! -f "$APP_ICON" ]; then
  echo "Missing app icon at $APP_ICON" >&2
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
lipo -create \
  "$ARM64_EXECUTABLE" \
  "$X86_64_EXECUTABLE" \
  -output "$APP_BUNDLE/Contents/MacOS/GRAF"
FINAL_ARCHITECTURES=$(lipo -archs "$APP_BUNDLE/Contents/MacOS/GRAF")
FINAL_ARCHITECTURE_SET=$(printf '%s\n' "$FINAL_ARCHITECTURES" | tr ' ' '\n' | sort | paste -sd ' ' -)
if [ "$FINAL_ARCHITECTURE_SET" != "arm64 x86_64" ]; then
  echo "Universal GRAF executable must contain arm64 and x86_64, got: $FINAL_ARCHITECTURES" >&2
  exit 1
fi
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
  <key>NSScreenCaptureUsageDescription</key>
  <string>GRAF использует доступ к записи экрана и системного звука, чтобы сохранить входящий звук встречи локально.</string>
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

  GRAF_APP_SIGN_IDENTITY="Apple Development: Your Name (TEAMID)" \
    sh apps/macos/Installer/Scripts/build-local-installer.sh

For packaging-only tests on locked-down hosts, set:

  GRAF_ALLOW_ADHOC_APP_SIGNING=1 \
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

xattr -cr "$APP_BUNDLE" 2>/dev/null || true

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
