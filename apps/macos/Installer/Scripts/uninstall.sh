#!/usr/bin/env sh
set -eu

APP_PATH="/Applications/GRAF.app"
LEGACY_APP_PATH="/Applications/2brain Rec.app"

if [ -d "$APP_PATH" ]; then
  rm -rf "$APP_PATH"
fi
if [ -d "$LEGACY_APP_PATH" ]; then
  rm -rf "$LEGACY_APP_PATH"
fi

echo "uninstall-succeeded"
