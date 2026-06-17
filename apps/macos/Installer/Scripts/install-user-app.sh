#!/usr/bin/env sh
set -eu
export COPYFILE_DISABLE=1

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
INSTALLER_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
MACOS_DIR=$(CDPATH= cd -- "$INSTALLER_DIR/.." && pwd)
SOURCE_APP="$MACOS_DIR/.build/installer/stage/app/Applications/2brain Rec.app"
DEST_APP="${TWO_BRAIN_REC_USER_APP_DEST:-"$HOME/Applications/2brain Rec.app"}"

if [ ! -d "$SOURCE_APP" ]; then
  cat >&2 <<EOF
Missing staged app bundle:
  $SOURCE_APP

Build it first:
  TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh
EOF
  exit 1
fi

mkdir -p "$(dirname "$DEST_APP")"
rsync -a --delete "$SOURCE_APP/" "$DEST_APP/"
xattr -cr "$DEST_APP" 2>/dev/null || true
codesign --verify --deep --strict "$DEST_APP"
printf '%s\n' "$DEST_APP"
