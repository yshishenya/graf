#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
INSTALLER_DIR=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
MACOS_DIR=$(CDPATH='' cd -- "$INSTALLER_DIR/.." && pwd)
MANIFEST="$INSTALLER_DIR/UpdateSigningKey.json"
COMMON="$SCRIPT_DIR/release-signing-common.sh"
GENERATE_KEYS="$MACOS_DIR/.build/artifacts/sparkle/Sparkle/bin/generate_keys"

fail() {
  echo "release-signing custody provisioning failed: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
usage:
  provision-release-signing-custody.sh --initialize --keychain-account NAME
  provision-release-signing-custody.sh --resume --keychain-account NAME

--initialize creates one Keychain generation only while the public manifest is
unprovisioned, then atomically records its public trust metadata. The private
signer never leaves the named macOS Keychain account.

--resume is an explicit Keychain recovery after an interrupted initialization.
It reuses only the named existing generation and never creates, replaces,
exports, or prints private material.
EOF
  exit 64
}

MODE=
KEYCHAIN_ACCOUNT=
while [ "$#" -gt 0 ]; do
  case "$1" in
    --initialize|--resume)
      [ -z "$MODE" ] || usage
      MODE=${1#--}
      ;;
    --keychain-account)
      shift
      [ "$#" -gt 0 ] || usage
      KEYCHAIN_ACCOUNT=$1
      ;;
    -h|--help) usage ;;
    *) usage ;;
  esac
  shift
done

[ -n "$MODE" ] && [ -n "$KEYCHAIN_ACCOUNT" ] || usage
[ -r "$COMMON" ] || fail "release-signing trust helper is missing"
[ -x "$GENERATE_KEYS" ] || fail "official pinned Sparkle generate_keys tool was not found"
# shellcheck source=release-signing-common.sh
. "$COMMON"
release_signing_require_safe_identifier "$KEYCHAIN_ACCOUNT" "Keychain account" || exit 1

manifest_status=$(release_signing_plist_value status "$MANIFEST")
manifest_generation=$(release_signing_plist_value trustGeneration "$MANIFEST")
manifest_account=$(release_signing_plist_value channels.primary.account "$MANIFEST")
[ "$manifest_status" = "unprovisioned" ] || fail "initialization refuses to replace an existing public signing generation"
[ "$manifest_generation" = "0" ] || fail "unprovisioned manifest trust generation must be zero"
[ "$KEYCHAIN_ACCOUNT" = "$manifest_account" ] || fail "Keychain account must equal the unprovisioned manifest account"

if [ "$MODE" = "initialize" ]; then
  if KEY_LOOKUP_OUTPUT=$("$GENERATE_KEYS" --account "$KEYCHAIN_ACCOUNT" -p 2>&1); then
    fail "initialization refuses to overwrite an existing Keychain signing generation"
  fi
  case "$KEY_LOOKUP_OUTPUT" in
    *"No existing signing key found!"*) ;;
    *) fail "could not prove that the named Keychain signing generation is absent" ;;
  esac
  "$GENERATE_KEYS" --account "$KEYCHAIN_ACCOUNT" >/dev/null 2>&1 ||
    fail "could not initialize the named Keychain signing generation"
fi

if ! PUBLIC_KEY=$("$GENERATE_KEYS" --account "$KEYCHAIN_ACCOUNT" -p 2>/dev/null | tr -d '\r\n'); then
  [ "$MODE" != "resume" ] || fail "resume requires the named existing Keychain signing generation"
  fail "could not derive the public identity of the new Keychain generation"
fi
release_signing_require_public_key "$PUBLIC_KEY" || exit 1
KEY_ID=$(release_signing_key_id "$PUBLIC_KEY") || exit 1

umask 077
STAGED_MANIFEST="$INSTALLER_DIR/.UpdateSigningKey.json.$$"
cleanup() { rm -f "$STAGED_MANIFEST"; }
trap cleanup EXIT HUP INT TERM
cat > "$STAGED_MANIFEST" <<EOF
{
  "schemaVersion": 1,
  "status": "active",
  "trustGeneration": 1,
  "keyId": "$KEY_ID",
  "publicKey": "$PUBLIC_KEY",
  "channels": {
    "primary": {
      "kind": "macos-keychain",
      "account": "$KEYCHAIN_ACCOUNT"
    }
  }
}
EOF
release_signing_require_active_manifest "$STAGED_MANIFEST" ||
  fail "generated public signing manifest did not pass validation"
mv "$STAGED_MANIFEST" "$MANIFEST" || fail "could not activate the reviewed public signing manifest"
trap - EXIT HUP INT TERM
printf 'key_id=%s\ntrust_generation=1\nkeychain=ready\nnext_action=commit_public_manifest_for_review\n' "$KEY_ID"
