#!/usr/bin/env sh
set -eu
export COPYFILE_DISABLE=1

ROOT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/../../.." && pwd)
MACOS_DIR="$ROOT_DIR/apps/macos"
BUILD_DIR="${GRAF_DEV_BUILD_DIR:-$MACOS_DIR/.build/dev}"
APP_BUNDLE="${GRAF_DEV_APP_BUNDLE:-$BUILD_DIR/GRAF Dev.app}"
LOCAL_ORIGIN="${GRAF_DEV_ORIGIN:-}"
SIGNING_IDENTITY="${GRAF_DEV_SIGN_IDENTITY:-GRAF Local Code Signing}"
DEV_BUNDLE_ID="pro.2brain.graf.dev"
SOURCE_SHA="${GRAF_DEV_SOURCE_SHA:-$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || true)}"
SOURCE_SHA_SHORT=$(printf '%s' "$SOURCE_SHA" | cut -c1-12)
MANIFEST_ID="${GRAF_DEV_MANIFEST_ID:-dev-$SOURCE_SHA_SHORT}"

fail() {
  echo "GRAF Dev build: $1" >&2
  exit 1
}

[ -n "$LOCAL_ORIGIN" ] || fail "GRAF_DEV_ORIGIN must be explicitly supplied"
[ "$SOURCE_SHA" ] && printf '%s' "$SOURCE_SHA" | grep -Eq '^[0-9a-fA-F]{40}$' || fail "GRAF_DEV_SOURCE_SHA must be a 40-character git SHA"
[ "$MANIFEST_ID" ] && printf '%s' "$MANIFEST_ID" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$' || fail "GRAF_DEV_MANIFEST_ID contains unsupported characters"
[ "$(basename -- "$APP_BUNDLE")" = "GRAF Dev.app" ] || fail "Dev bundle path must end in GRAF Dev.app"
case "$LOCAL_ORIGIN" in
  http://127.0.0.1:*|http://localhost:*) ;;
  *) fail "GRAF_DEV_ORIGIN must be loopback HTTP" ;;
esac
case "$LOCAL_ORIGIN" in
  *[!A-Za-z0-9:/._-]*) fail "GRAF_DEV_ORIGIN contains unsupported characters" ;;
esac
case "$LOCAL_ORIGIN" in
  *rec.2brain.pro*|*rec.2brain.dev*) fail "Refusing production origin" ;;
esac

security find-identity -v -p codesigning 2>/dev/null | grep -Fq "\"$SIGNING_IDENTITY\"" ||
  fail "signing identity is unavailable: $SIGNING_IDENTITY"

swift build \
  --package-path "$MACOS_DIR" \
  --build-path "$BUILD_DIR" \
  --configuration debug \
  --product TwoBrainRecApp
BIN_DIR=$(swift build \
  --package-path "$MACOS_DIR" \
  --build-path "$BUILD_DIR" \
  --configuration debug \
  --show-bin-path)
APP_EXECUTABLE="$BIN_DIR/TwoBrainRecApp"
RESOURCE_BUNDLE="$BIN_DIR/TwoBrainRecMacOS_TwoBrainRecAppCore.bundle"
SPARKLE_FRAMEWORK="$BIN_DIR/Sparkle.framework"

for required_path in "$APP_EXECUTABLE" "$RESOURCE_BUNDLE" "$SPARKLE_FRAMEWORK"; do
  [ -e "$required_path" ] || fail "build input is missing: $required_path"
done

rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources" "$APP_BUNDLE/Contents/Frameworks"
cp "$APP_EXECUTABLE" "$APP_BUNDLE/Contents/MacOS/GRAF"
cp -R "$RESOURCE_BUNDLE" "$APP_BUNDLE/Contents/Resources/"
ditto "$SPARKLE_FRAMEWORK" "$APP_BUNDLE/Contents/Frameworks/Sparkle.framework"
ICONSET_DIR="$BUILD_DIR/GRAF Dev.iconset"
DEV_ICON_PNG="$BUILD_DIR/graf-dev-icon.png"
rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"
swift "$MACOS_DIR/Scripts/render-dev-icon.swift" \
  "$MACOS_DIR/RecApp/Resources/AppIcon.icns" \
  "$DEV_ICON_PNG"
for icon_size in 16 32 128 256 512; do
  sips -z "$icon_size" "$icon_size" "$DEV_ICON_PNG" --out "$ICONSET_DIR/icon_${icon_size}x${icon_size}.png" >/dev/null
  retina_size=$((icon_size * 2))
  sips -z "$retina_size" "$retina_size" "$DEV_ICON_PNG" --out "$ICONSET_DIR/icon_${icon_size}x${icon_size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET_DIR" -o "$APP_BUNDLE/Contents/Resources/AppIcon.icns"

if ! otool -l "$APP_BUNDLE/Contents/MacOS/GRAF" | grep -Fq '@executable_path/../Frameworks'; then
  install_name_tool -add_rpath '@executable_path/../Frameworks' "$APP_BUNDLE/Contents/MacOS/GRAF"
fi

cat > "$APP_BUNDLE/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleDisplayName</key>
  <string>GRAF Dev</string>
  <key>CFBundleExecutable</key>
  <string>GRAF</string>
  <key>CFBundleIdentifier</key>
  <string>pro.2brain.graf.dev</string>
  <key>CFBundleIconFile</key>
  <string>AppIcon</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>GRAF Dev</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>0.0.0-dev</string>
  <key>CFBundleVersion</key>
  <string>0.0.0-dev</string>
  <key>GRAFSourceSHA</key>
  <string>$SOURCE_SHA</string>
  <key>GRAFManifestID</key>
  <string>$MANIFEST_ID</string>
  <key>LSMinimumSystemVersion</key>
  <string>14.5</string>
  <key>NSHighResolutionCapable</key>
  <true/>
  <key>ApplePersistenceIgnoreState</key>
  <true/>
  <key>NSQuitAlwaysKeepsWindows</key>
  <false/>
  <key>LSEnvironment</key>
  <dict>
    <key>GRAF_CABINET_BASE_URL</key>
    <string>$LOCAL_ORIGIN</string>
    <key>GRAF_UPLOAD_BASE_URL</key>
    <string>$LOCAL_ORIGIN</string>
    <key>GRAF_CABINET_REQUIRE_EXPLICIT_BASE_URL</key>
    <string>1</string>
    <key>GRAF_UPLOAD_REQUIRE_EXPLICIT_BASE_URL</key>
    <string>1</string>
    <key>GRAF_LOCAL_APP</key>
    <string>1</string>
    <key>GRAF_APP_CHANNEL</key>
    <string>dev</string>
    <key>GRAF_UPLOAD_BEARER_TOKEN</key>
    <string></string>
    <key>TWO_BRAIN_REC_UPLOAD_BEARER_TOKEN</key>
    <string></string>
    <key>GRAF_USER_ID</key>
    <string></string>
    <key>GRAF_WORKSPACE_ID</key>
    <string></string>
    <key>TWO_BRAIN_REC_USER_ID</key>
    <string></string>
    <key>TWO_BRAIN_REC_WORKSPACE_ID</key>
    <string></string>
  </dict>
  <key>NSMicrophoneUsageDescription</key>
  <string>GRAF Dev использует доступ к микрофону, чтобы проверить и записать звук встречи.</string>
  <key>NSAudioCaptureUsageDescription</key>
  <string>GRAF Dev использует доступ к системному звуку, чтобы сохранить входящий звук встречи локально.</string>
  <key>NSScreenCaptureUsageDescription</key>
  <string>GRAF Dev использует доступ к записи экрана и системного звука, чтобы сохранить входящий звук встречи локально.</string>
</dict>
</plist>
EOF

APP_ENTITLEMENTS="$BUILD_DIR/dev-app-signing.entitlements"
cat > "$APP_ENTITLEMENTS" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>com.apple.security.device.audio-input</key>
  <true/>
  <!-- Local Sparkle artifacts have no Apple Team ID; this is Dev-only. -->
  <key>com.apple.security.cs.disable-library-validation</key>
  <true/>
</dict>
</plist>
EOF

sign_nested_code() {
  target=$1
  [ -e "$target" ] || return 0
  codesign --force --options runtime --timestamp=none \
    --preserve-metadata=identifier,entitlements,flags \
    --sign "$SIGNING_IDENTITY" "$target" >/dev/null
}

# install_name_tool above invalidates the copied SwiftPM executable. Re-sign
# that nested code explicitly before signing the outer app bundle.
codesign --force --options runtime --timestamp=none \
  --identifier "$DEV_BUNDLE_ID" \
  --entitlements "$APP_ENTITLEMENTS" \
  --sign "$SIGNING_IDENTITY" "$APP_BUNDLE/Contents/MacOS/GRAF" >/dev/null

SPARKLE_VERSION_DIR="$APP_BUNDLE/Contents/Frameworks/Sparkle.framework/Versions/B"
sign_nested_code "$SPARKLE_VERSION_DIR/XPCServices/Downloader.xpc"
sign_nested_code "$SPARKLE_VERSION_DIR/XPCServices/Installer.xpc"
sign_nested_code "$SPARKLE_VERSION_DIR/Updater.app"
sign_nested_code "$SPARKLE_VERSION_DIR/Autoupdate"
sign_nested_code "$APP_BUNDLE/Contents/Frameworks/Sparkle.framework"
codesign --force --options runtime --timestamp=none \
  --entitlements "$APP_ENTITLEMENTS" \
  --sign "$SIGNING_IDENTITY" "$APP_BUNDLE" >/dev/null

codesign --verify --deep --strict "$APP_BUNDLE" >/dev/null
SIGNATURE_INFO=$(codesign -dv --verbose=4 "$APP_BUNDLE" 2>&1)
printf '%s\n' "$SIGNATURE_INFO" | grep -Fq "Authority=$SIGNING_IDENTITY" ||
  fail "final bundle signer differs from requested identity"
DESIGNATED_REQUIREMENT=$(codesign -dr - "$APP_BUNDLE" 2>&1 | sed -n 's/^designated => //p' | head -n 1)
[ -n "$DESIGNATED_REQUIREMENT" ] || fail "designated requirement is unavailable"

INFO_PLIST="$APP_BUNDLE/Contents/Info.plist"
plutil -extract CFBundleDisplayName raw "$INFO_PLIST" | grep -Fxq "GRAF Dev" || fail "Dev display name is invalid"
plutil -extract CFBundleIdentifier raw "$INFO_PLIST" | grep -Fxq "pro.2brain.graf.dev" || fail "Dev bundle ID is invalid"
if plutil -extract SUFeedURL raw "$INFO_PLIST" >/dev/null 2>&1 ||
   plutil -extract SUPublicEDKey raw "$INFO_PLIST" >/dev/null 2>&1; then
  fail "Dev updater metadata must be absent"
fi

printf '%s\n' "$APP_BUNDLE"
