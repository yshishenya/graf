#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(git -C "$MACOS_DIR" rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$REPO_ROOT" ]; then
  REPO_ROOT=$(CDPATH= cd -- "$MACOS_DIR/../.." && pwd)
fi

IDENTITY="${GRAF_APP_SIGN_IDENTITY:-GRAF Local Code Signing}"
PKG_PATH="${GRAF_PERMISSION_RETENTION_PKG:-$MACOS_DIR/.build/installer/graf-local-permission-retention.pkg}"
STAGED_APP="$MACOS_DIR/RecApp/.build/GRAF.app"
INSTALLED_APP="${GRAF_PERMISSION_RETENTION_APP:-/Applications/GRAF.app}"
BUNDLE_ID="pro.2brain.graf"
LOG_PATH="$HOME/Library/Logs/GRAF/graf.log"

usage() {
  cat <<EOF
Usage: $0 <command>

Commands:
  preflight          Check local signing identity availability.
  build              Build a local package with explicit local self-signed signing.
  staged-identity    Inspect staged app bundle identity.
  installed-identity Inspect /Applications/GRAF.app identity.
  permissions        Print metadata-only permission state summaries.
  quit               Ask installed GRAF app to quit and wait for exit.

This helper never resets TCC, never grants permissions, and never records
private key material, raw audio, transcripts, or meeting content.
EOF
}

require_bundle_id() {
  app_path="$1"
  observed=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$app_path/Contents/Info.plist")
  if [ "$observed" != "$BUNDLE_ID" ]; then
    echo "bundle_id_mismatch expected=$BUNDLE_ID observed=$observed app=$app_path" >&2
    exit 1
  fi
  echo "bundle_id=$observed app=$app_path"
}

inspect_app_identity() {
  app_path="$1"
  if [ ! -d "$app_path" ]; then
    echo "missing_app app=$app_path" >&2
    exit 1
  fi
  require_bundle_id "$app_path"
  codesign --verify --deep --strict "$app_path"
  codesign -dv --verbose=4 "$app_path" 2>&1 | sed -n '/^Authority=/p;/^TeamIdentifier=/p;/^Signature=/p'
  codesign -dr - "$app_path" 2>&1 | sed -n 's/^designated => /designated_requirement=/p'
}

permission_summaries() {
  if [ -f "$LOG_PATH" ]; then
    tail -n 120 "$LOG_PATH" |
      sed -n '/desktop.permission_onboarding_checked/p' |
      tail -n 5
  else
    echo "missing_log path=$LOG_PATH"
  fi

  user_tcc="$HOME/Library/Application Support/com.apple.TCC/TCC.db"
  if [ -f "$user_tcc" ]; then
    sqlite3 "$user_tcc" \
      "select service,client,auth_value from access where client='$BUNDLE_ID' and service='kTCCServiceMicrophone';" || true
  else
    echo "missing_user_tcc"
  fi

  system_tcc="/Library/Application Support/com.apple.TCC/TCC.db"
  if sudo -n true 2>/dev/null; then
    sudo sqlite3 "$system_tcc" \
      "select service,client,auth_value from access where client='$BUNDLE_ID' and service='kTCCServiceScreenCapture';" || true
  else
    echo "system_tcc_requires_sudo_manual_check"
  fi
}

wait_for_exit() {
  bundle="$1"
  deadline=$(( $(date +%s) + 10 ))
  while pgrep -x "$bundle" >/dev/null 2>&1; do
    if [ "$(date +%s)" -ge "$deadline" ]; then
      echo "quit_timeout app=$bundle" >&2
      exit 1
    fi
    sleep 1
  done
  echo "quit_ok app=$bundle"
}

command="${1:-}"
case "$command" in
  preflight)
    security find-identity -v -p codesigning | grep -F "$IDENTITY" >/dev/null
    echo "signing_identity_present name=$IDENTITY"
    ;;
  build)
    GRAF_APP_SIGN_IDENTITY="$IDENTITY" \
    GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1 \
      sh "$MACOS_DIR/Installer/Scripts/build-local-installer.sh" "$PKG_PATH"
    echo "package=$PKG_PATH"
    ;;
  staged-identity)
    inspect_app_identity "$STAGED_APP"
    ;;
  installed-identity)
    inspect_app_identity "$INSTALLED_APP"
    ;;
  permissions)
    permission_summaries
    ;;
  quit)
    osascript -e 'tell application "GRAF" to quit'
    wait_for_exit "GRAF"
    ;;
  ""|help|--help|-h)
    usage
    ;;
  *)
    usage >&2
    exit 64
    ;;
esac
