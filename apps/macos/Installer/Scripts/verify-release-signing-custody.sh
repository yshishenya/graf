#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
INSTALLER_DIR=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
MACOS_DIR=$(CDPATH='' cd -- "$INSTALLER_DIR/.." && pwd)
REPO_ROOT=$(git -C "$MACOS_DIR" rev-parse --show-toplevel)
MANIFEST="$INSTALLER_DIR/UpdateSigningKey.json"
COMMON="$SCRIPT_DIR/release-signing-common.sh"
GENERATE_KEYS="$MACOS_DIR/.build/artifacts/sparkle/Sparkle/bin/generate_keys"

fail() {
  echo "release-signing custody verification failed: $*" >&2
  exit 1
}

usage() {
  echo "usage: $0 --app /path/to/GRAF.app --release-tag vYYYY.MM.DD.N --emit-keychain-attestation /private/path/attestation.json" >&2
  exit 64
}

APP_BUNDLE=
RELEASE_TAG=
ATTESTATION_OUTPUT=
while [ "$#" -gt 0 ]; do
  case "$1" in
    --app) shift; [ "$#" -gt 0 ] || usage; APP_BUNDLE=$1 ;;
    --release-tag) shift; [ "$#" -gt 0 ] || usage; RELEASE_TAG=$1 ;;
    --emit-keychain-attestation) shift; [ "$#" -gt 0 ] || usage; ATTESTATION_OUTPUT=$1 ;;
    -h|--help) usage ;;
    *) usage ;;
  esac
  shift
done

[ -d "$APP_BUNDLE" ] || fail "candidate GRAF.app is required"
[ -f "$APP_BUNDLE/Contents/Info.plist" ] || fail "candidate GRAF.app Info.plist is missing"
[ -n "$RELEASE_TAG" ] && [ -n "$ATTESTATION_OUTPUT" ] || usage
[ -r "$COMMON" ] || fail "release-signing trust helper is missing"
[ -x "$GENERATE_KEYS" ] || fail "official pinned Sparkle generate_keys tool was not found"
# shellcheck source=release-signing-common.sh
. "$COMMON"
release_signing_require_active_manifest "$MANIFEST" || exit 1

printf '%s' "$RELEASE_TAG" | grep -Eq '^v[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$' ||
  fail "release tag must be CalVer with a leading v"
REMOTE_TAG_REFS=$(git -C "$REPO_ROOT" ls-remote origin \
  "refs/tags/$RELEASE_TAG" "refs/tags/$RELEASE_TAG^{}" 2>/dev/null || true)
REMOTE_TAG_COMMIT=$(printf '%s\n' "$REMOTE_TAG_REFS" | awk '
  $2 ~ /\^\{\}$/ { peeled = $1 }
  NR == 1 { direct = $1 }
  END { if (peeled != "") print peeled; else print direct }
')
[ -n "$REMOTE_TAG_COMMIT" ] || fail "requested release tag is not published on origin"
HEAD_COMMIT=$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || true)
MASTER_COMMIT=$(git -C "$REPO_ROOT" ls-remote origin refs/heads/master 2>/dev/null | awk 'NR == 1 { print $1 }')
[ "$HEAD_COMMIT" = "$REMOTE_TAG_COMMIT" ] || fail "checked-out source does not match the requested release tag"
[ -n "$MASTER_COMMIT" ] && [ "$REMOTE_TAG_COMMIT" = "$MASTER_COMMIT" ] ||
  fail "release tag is not the current origin/master commit"

APP_PUBLIC_KEY=$(release_signing_plist_value SUPublicEDKey "$APP_BUNDLE/Contents/Info.plist")
release_signing_require_matching_public_key "$APP_PUBLIC_KEY" "$RELEASE_SIGNING_PUBLIC_KEY" "candidate GRAF.app SUPublicEDKey" || exit 1
KEYCHAIN_PUBLIC_KEY=$("$GENERATE_KEYS" --account "$RELEASE_SIGNING_KEYCHAIN_ACCOUNT" -p 2>/dev/null | tr -d '\r\n') ||
  fail "named Keychain signing generation is unavailable"
release_signing_require_matching_public_key "$KEYCHAIN_PUBLIC_KEY" "$RELEASE_SIGNING_PUBLIC_KEY" "named Keychain signing generation" || exit 1

[ ! -e "$ATTESTATION_OUTPUT" ] || fail "safe Keychain attestation destination already exists"
ATTESTATION_DIR=$(CDPATH='' cd -- "$(dirname -- "$ATTESTATION_OUTPUT")" && pwd) ||
  fail "safe Keychain attestation destination is unavailable"
TEMP_ATTESTATION=$(mktemp "$ATTESTATION_DIR/.graf-keychain-attestation.XXXXXX") ||
  fail "could not create a safe Keychain attestation"
cleanup() { rm -f "$TEMP_ATTESTATION"; }
trap cleanup EXIT HUP INT TERM
umask 077
CHECKED_AT=$(LC_ALL=C /bin/date -u '+%Y-%m-%dT%H:%M:%SZ')
EVIDENCE_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
cat > "$TEMP_ATTESTATION" <<EOF
{
  "schemaVersion": 1,
  "keyId": "$RELEASE_SIGNING_KEY_ID",
  "trustGeneration": $RELEASE_SIGNING_TRUST_GENERATION,
  "channel": "macos-keychain",
  "state": "ready",
  "checkedAt": "$CHECKED_AT",
  "releaseRef": "$RELEASE_TAG",
  "commit": "$REMOTE_TAG_COMMIT",
  "workflow": "verify-release-signing-custody-local",
  "evidenceId": "$EVIDENCE_ID"
}
EOF
/usr/bin/plutil -convert xml1 -o /dev/null "$TEMP_ATTESTATION" >/dev/null ||
  fail "could not validate a safe Keychain attestation"
chmod 600 "$TEMP_ATTESTATION"
mv "$TEMP_ATTESTATION" "$ATTESTATION_OUTPUT" || fail "could not finalize a safe Keychain attestation"
trap - EXIT HUP INT TERM
printf 'checked_at=%s\nkey_id=%s\ntrust_generation=%s\nkeychain=ready\noverall=ready\n' \
  "$CHECKED_AT" "$RELEASE_SIGNING_KEY_ID" "$RELEASE_SIGNING_TRUST_GENERATION"
