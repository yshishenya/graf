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
  echo "usage: $0 --app /path/to/GRAF.app --release-tag vYYYY.MM.DD.N (--attestation /path/to/cloud-attestation.json | --emit-keychain-attestation /path/to/safe-keychain-attestation.json) [--allow-approved-degraded]" >&2
  exit 64
}

APP_BUNDLE=
ATTESTATION=
RELEASE_TAG=
ALLOW_DEGRADED=0
KEYCHAIN_ATTESTATION_OUTPUT=
while [ "$#" -gt 0 ]; do
  case "$1" in
    --app)
      shift
      [ "$#" -gt 0 ] || usage
      APP_BUNDLE=$1
      ;;
    --attestation)
      shift
      [ "$#" -gt 0 ] || usage
      ATTESTATION=$1
      ;;
    --release-tag)
      shift
      [ "$#" -gt 0 ] || usage
      RELEASE_TAG=$1
      ;;
    --emit-keychain-attestation)
      shift
      [ "$#" -gt 0 ] || usage
      KEYCHAIN_ATTESTATION_OUTPUT=$1
      ;;
    --allow-approved-degraded)
      ALLOW_DEGRADED=1
      ;;
    -h|--help)
      usage
      ;;
    *)
      usage
      ;;
  esac
  shift
done

[ -d "$APP_BUNDLE" ] || fail "candidate GRAF.app is required"
[ -f "$APP_BUNDLE/Contents/Info.plist" ] || fail "candidate GRAF.app Info.plist is missing"
[ -n "$ATTESTATION" ] || [ -n "$KEYCHAIN_ATTESTATION_OUTPUT" ] || usage
[ -n "$RELEASE_TAG" ] || usage
[ -r "$COMMON" ] || fail "release-signing trust helper is missing"
[ -x "$GENERATE_KEYS" ] || fail "official pinned Sparkle generate_keys tool was not found"
# shellcheck source=release-signing-common.sh
. "$COMMON"
release_signing_require_active_manifest "$MANIFEST" || exit 1
CHECKED_AT=$(LC_ALL=C /bin/date -u '+%Y-%m-%dT%H:%M:%SZ')

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

APP_PUBLIC_KEY=$(release_signing_plist_value SUPublicEDKey "$APP_BUNDLE/Contents/Info.plist")
release_signing_require_matching_public_key "$APP_PUBLIC_KEY" "$RELEASE_SIGNING_PUBLIC_KEY" "candidate GRAF.app SUPublicEDKey" || exit 1

KEYCHAIN_STATE=unavailable
GITHUB_STATE=unavailable
if KEYCHAIN_PUBLIC_KEY=$("$GENERATE_KEYS" --account "$RELEASE_SIGNING_RECOVERY_ACCOUNT" -p 2>/dev/null | tr -d '\r\n'); then
  if release_signing_require_matching_public_key "$KEYCHAIN_PUBLIC_KEY" "$RELEASE_SIGNING_PUBLIC_KEY" "named Keychain recovery generation"; then
    KEYCHAIN_STATE=ready
  fi
fi

write_keychain_attestation() {
  destination=$1
  [ "$KEYCHAIN_STATE" = ready ] || fail "named Keychain recovery generation is unavailable"
  [ ! -e "$destination" ] || fail "safe Keychain attestation destination already exists"
  destination_directory=$(CDPATH='' cd -- "$(dirname -- "$destination")" && pwd) ||
    fail "safe Keychain attestation destination is unavailable"
  temporary_attestation=$(mktemp "$destination_directory/.graf-keychain-attestation.XXXXXX") ||
    fail "could not create a safe Keychain attestation"
  # shellcheck disable=SC2329 # Invoked by the EXIT/HUP/INT/TERM trap below.
  cleanup_attestation() {
    rm -f "$temporary_attestation"
  }
  trap cleanup_attestation EXIT HUP INT TERM
  umask 077
  evidence_id=$(uuidgen | tr '[:upper:]' '[:lower:]')
  cat > "$temporary_attestation" <<EOF
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
  "evidenceId": "$evidence_id"
}
EOF
  /usr/bin/plutil -convert xml1 -o /dev/null "$temporary_attestation" >/dev/null ||
    fail "could not validate a safe Keychain attestation"
  chmod 600 "$temporary_attestation"
  mv "$temporary_attestation" "$destination" ||
    fail "could not finalize a safe Keychain attestation"
  trap - EXIT HUP INT TERM
}

if [ -n "$KEYCHAIN_ATTESTATION_OUTPUT" ]; then
  write_keychain_attestation "$KEYCHAIN_ATTESTATION_OUTPUT"
  if [ -z "$ATTESTATION" ]; then
    printf 'checked_at=%s\nkey_id=%s\ntrust_generation=%s\nkeychain=ready\ngithub_environment=not-checked\noverall=keychain-attestation-created\n' "$CHECKED_AT" "$RELEASE_SIGNING_KEY_ID" "$RELEASE_SIGNING_TRUST_GENERATION"
    exit 0
  fi
fi

if release_signing_require_attestation "$ATTESTATION" "$RELEASE_TAG" "$REMOTE_TAG_COMMIT"; then
  GITHUB_STATE=ready
fi

if [ "$KEYCHAIN_STATE" = ready ] && [ "$GITHUB_STATE" = ready ]; then
  printf 'checked_at=%s\nkey_id=%s\ntrust_generation=%s\nkeychain=ready\ngithub_environment=ready\noverall=ready\n' "$CHECKED_AT" "$RELEASE_SIGNING_KEY_ID" "$RELEASE_SIGNING_TRUST_GENERATION"
  exit 0
fi

if [ "$ALLOW_DEGRADED" = "1" ] &&
   [ "${GRAF_RELEASE_SIGNING_APPROVED_DEGRADED_FALLBACK:-0}" = "1" ] &&
   { [ "$KEYCHAIN_STATE" = ready ] || [ "$GITHUB_STATE" = ready ]; }; then
  printf 'checked_at=%s\nkey_id=%s\ntrust_generation=%s\nkeychain=%s\ngithub_environment=%s\noverall=degraded\n' "$CHECKED_AT" "$RELEASE_SIGNING_KEY_ID" "$RELEASE_SIGNING_TRUST_GENERATION" "$KEYCHAIN_STATE" "$GITHUB_STATE"
  exit 0
fi

printf 'checked_at=%s\nkey_id=%s\ntrust_generation=%s\nkeychain=%s\ngithub_environment=%s\noverall=unavailable\n' "$CHECKED_AT" "$RELEASE_SIGNING_KEY_ID" "$RELEASE_SIGNING_TRUST_GENERATION" "$KEYCHAIN_STATE" "$GITHUB_STATE" >&2
exit 1
