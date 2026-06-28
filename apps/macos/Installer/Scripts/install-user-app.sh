#!/usr/bin/env sh
set -eu
export COPYFILE_DISABLE=1

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
INSTALLER_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
MACOS_DIR=$(CDPATH= cd -- "$INSTALLER_DIR/.." && pwd)
SOURCE_APP="$MACOS_DIR/.build/installer/stage/app/Applications/GRAF.app"
DEST_APP="${GRAF_USER_APP_DEST:-${TWO_BRAIN_REC_USER_APP_DEST:-"$HOME/Applications/GRAF.app"}}"
LEGACY_DEST_APP="${GRAF_LEGACY_USER_APP_DEST:-"$HOME/Applications/2brain Rec.app"}"
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"

if [ ! -d "$SOURCE_APP" ]; then
  cat >&2 <<EOF
Missing staged app bundle:
  $SOURCE_APP

Build it first:
  GRAF_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh
EOF
  exit 1
fi

mkdir -p "$(dirname "$DEST_APP")"
if [ -d "$LEGACY_DEST_APP" ] && [ "$LEGACY_DEST_APP" != "$DEST_APP" ]; then
  rm -rf "$LEGACY_DEST_APP" || true
fi
rsync -a --delete "$SOURCE_APP/" "$DEST_APP/"
xattr -cr "$DEST_APP" 2>/dev/null || true
codesign --verify --deep --strict "$DEST_APP"
if [ -x "$LSREGISTER" ]; then
  "$LSREGISTER" -f "$DEST_APP" 2>/dev/null || true
fi
printf '%s\n' "$DEST_APP"
