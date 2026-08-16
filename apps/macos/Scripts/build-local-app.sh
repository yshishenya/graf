#!/usr/bin/env sh
set -eu
export COPYFILE_DISABLE=1

ROOT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/../../.." && pwd)
MACOS_DIR="$ROOT_DIR/apps/macos"
BUILD_DIR="${GRAF_LOCAL_APP_BUILD_DIR:-$MACOS_DIR/.build/local}"
APP_BUNDLE="$BUILD_DIR/GRAF Local.app"
LOCAL_ORIGIN="http://127.0.0.1:8081"
OPEN_APP=0

case "${1:-}" in
  "") ;;
  --open) OPEN_APP=1 ;;
  *)
    echo "Usage: $0 [--open]" >&2
    exit 2
    ;;
esac

swift build \
  --package-path "$MACOS_DIR" \
  --configuration debug \
  --product TwoBrainRecApp
BIN_DIR=$(swift build --package-path "$MACOS_DIR" --configuration debug --show-bin-path)
APP_EXECUTABLE="$BIN_DIR/TwoBrainRecApp"
RESOURCE_BUNDLE="$BIN_DIR/TwoBrainRecMacOS_TwoBrainRecAppCore.bundle"
SPARKLE_FRAMEWORK="$BIN_DIR/Sparkle.framework"

for required_path in "$APP_EXECUTABLE" "$RESOURCE_BUNDLE" "$SPARKLE_FRAMEWORK"; do
  [ -e "$required_path" ] || {
    echo "Local app build input is missing: $required_path" >&2
    exit 1
  }
done

rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources" "$APP_BUNDLE/Contents/Frameworks"
cp "$APP_EXECUTABLE" "$APP_BUNDLE/Contents/MacOS/GRAF"
cp -R "$RESOURCE_BUNDLE" "$APP_BUNDLE/Contents/Resources/"
ditto "$SPARKLE_FRAMEWORK" "$APP_BUNDLE/Contents/Frameworks/Sparkle.framework"
cp "$MACOS_DIR/RecApp/Resources/AppIcon.icns" "$APP_BUNDLE/Contents/Resources/AppIcon.icns"

if ! otool -l "$APP_BUNDLE/Contents/MacOS/GRAF" | grep -Fq '@executable_path/../Frameworks'; then
  install_name_tool -add_rpath '@executable_path/../Frameworks' "$APP_BUNDLE/Contents/MacOS/GRAF"
fi

cat > "$APP_BUNDLE/Contents/MacOS/GRAF-local" <<'EOF'
#!/usr/bin/env sh
set -eu
APP_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
export GRAF_CABINET_BASE_URL=http://127.0.0.1:8081
export GRAF_UPLOAD_BASE_URL=http://127.0.0.1:8081
export GRAF_CABINET_REQUIRE_EXPLICIT_BASE_URL=1
export GRAF_UPLOAD_REQUIRE_EXPLICIT_BASE_URL=1
export GRAF_LOCAL_APP=1
unset GRAF_UPLOAD_BEARER_TOKEN TWO_BRAIN_REC_UPLOAD_BEARER_TOKEN
unset GRAF_USER_ID GRAF_WORKSPACE_ID TWO_BRAIN_REC_USER_ID TWO_BRAIN_REC_WORKSPACE_ID
exec "$APP_ROOT/MacOS/GRAF" "$@"
EOF
chmod 755 "$APP_BUNDLE/Contents/MacOS/GRAF-local"

cat > "$APP_BUNDLE/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleDisplayName</key>
  <string>GRAF Local</string>
  <key>CFBundleExecutable</key>
  <string>GRAF-local</string>
  <key>CFBundleIdentifier</key>
  <string>pro.2brain.graf.local</string>
  <key>CFBundleIconFile</key>
  <string>AppIcon</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>GRAF Local</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>0.0.0-local</string>
  <key>CFBundleVersion</key>
  <string>0.0.0-local</string>
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
</dict>
</plist>
EOF

codesign --force --deep --sign - "$APP_BUNDLE" >/dev/null

if [ "$OPEN_APP" = "1" ]; then
  open "$APP_BUNDLE"
fi

printf '%s\n' "$APP_BUNDLE"
