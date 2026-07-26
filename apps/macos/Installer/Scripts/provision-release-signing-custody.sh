#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
INSTALLER_DIR=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
MACOS_DIR=$(CDPATH='' cd -- "$INSTALLER_DIR/.." && pwd)
MANIFEST="$INSTALLER_DIR/UpdateSigningKey.json"
COMMON="$SCRIPT_DIR/release-signing-common.sh"
VERIFIER="$SCRIPT_DIR/verify-release-signing-custody.sh"
GENERATE_KEYS="$MACOS_DIR/.build/artifacts/sparkle/Sparkle/bin/generate_keys"

fail() {
  echo "release-signing custody provisioning failed: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<'EOF'
usage:
  provision-release-signing-custody.sh --initialize --keychain-account NAME --github-environment NAME
  provision-release-signing-custody.sh --resume --keychain-account NAME --github-environment NAME
  provision-release-signing-custody.sh --verify --candidate-app /path/to/GRAF.app --attestation /path/to/attestation.json --release-tag vYYYY.MM.DD.N

--initialize creates one new Keychain generation only while the public manifest
is unprovisioned, transfers it directly to the named protected GitHub
environment secret, and atomically writes public trust metadata. It never
prints or stores the private material in this repository.

--resume is an explicit Keychain recovery for an interrupted initialization:
it reuses only the named existing Keychain generation while the public manifest
is still unprovisioned, repeats the protected secret transfer, and writes the
same public metadata. It never creates or replaces a Keychain generation.
EOF
  exit 64
}

MODE=
KEYCHAIN_ACCOUNT=
GITHUB_ENVIRONMENT=
CANDIDATE_APP=
ATTESTATION=
RELEASE_TAG=
while [ "$#" -gt 0 ]; do
  case "$1" in
    --initialize)
      [ -z "$MODE" ] || usage
      MODE=initialize
      ;;
    --resume)
      [ -z "$MODE" ] || usage
      MODE=resume
      ;;
    --verify)
      [ -z "$MODE" ] || usage
      MODE=verify
      ;;
    --keychain-account)
      shift
      [ "$#" -gt 0 ] || usage
      KEYCHAIN_ACCOUNT=$1
      ;;
    --github-environment)
      shift
      [ "$#" -gt 0 ] || usage
      GITHUB_ENVIRONMENT=$1
      ;;
    --candidate-app)
      shift
      [ "$#" -gt 0 ] || usage
      CANDIDATE_APP=$1
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
    -h|--help)
      usage
      ;;
    *)
      usage
      ;;
  esac
  shift
done

[ -n "$MODE" ] || usage
[ -r "$COMMON" ] || fail "release-signing trust helper is missing"
[ -x "$VERIFIER" ] || fail "release-signing custody verifier is missing or not executable"
[ -x "$GENERATE_KEYS" ] || fail "official pinned Sparkle generate_keys tool was not found"
# shellcheck source=release-signing-common.sh
. "$COMMON"

if [ "$MODE" = "initialize" ] || [ "$MODE" = "resume" ]; then
  [ -n "$KEYCHAIN_ACCOUNT" ] || usage
  [ -n "$GITHUB_ENVIRONMENT" ] || usage
  release_signing_require_safe_identifier "$KEYCHAIN_ACCOUNT" "Keychain account" || exit 1
  release_signing_require_safe_identifier "$GITHUB_ENVIRONMENT" "GitHub environment" || exit 1

  manifest_status=$(release_signing_plist_value status "$MANIFEST")
  manifest_generation=$(release_signing_plist_value trustGeneration "$MANIFEST")
  manifest_primary_environment=$(release_signing_plist_value channels.primary.environment "$MANIFEST")
  manifest_secret_name=$(release_signing_plist_value channels.primary.secretName "$MANIFEST")
  manifest_recovery_account=$(release_signing_plist_value channels.recovery.account "$MANIFEST")
  [ "$manifest_status" = "unprovisioned" ] || fail "initialization refuses to replace an existing public signing generation"
  [ "$manifest_generation" = "0" ] || fail "unprovisioned manifest trust generation must be zero"
  [ "$KEYCHAIN_ACCOUNT" = "$manifest_recovery_account" ] || fail "Keychain account must equal the unprovisioned manifest recovery account"
  [ "$GITHUB_ENVIRONMENT" = "$manifest_primary_environment" ] || fail "GitHub environment must equal the unprovisioned manifest primary environment"
  release_signing_require_safe_identifier "$manifest_secret_name" "public signing manifest secret name" || exit 1

  command -v gh >/dev/null 2>&1 || fail "GitHub CLI is required for the protected secret transfer"
  gh auth status >/dev/null 2>&1 || fail "GitHub CLI is not authenticated for the protected secret transfer"
  if [ "$MODE" = "initialize" ]; then
    if KEY_LOOKUP_OUTPUT=$("$GENERATE_KEYS" --account "$KEYCHAIN_ACCOUNT" -p 2>&1); then
      fail "initialization refuses to overwrite an existing Keychain signing generation"
    fi
    case "$KEY_LOOKUP_OUTPUT" in
      *"No existing signing key found!"*)
        ;;
      *)
        fail "could not prove that the named Keychain signing generation is absent"
        ;;
    esac
    "$GENERATE_KEYS" --account "$KEYCHAIN_ACCOUNT" >/dev/null 2>&1 ||
      fail "could not initialize the named Keychain signing generation"
  fi
  if ! PUBLIC_KEY=$("$GENERATE_KEYS" --account "$KEYCHAIN_ACCOUNT" -p 2>/dev/null | tr -d '\r\n'); then
    if [ "$MODE" = "resume" ]; then
      fail "resume requires the named existing Keychain signing generation"
    fi
    fail "could not derive the public identity of the new Keychain generation"
  fi
  release_signing_require_public_key "$PUBLIC_KEY" || exit 1
  KEY_ID=$(release_signing_key_id "$PUBLIC_KEY") || exit 1

  umask 077
  TRANSFER_DIRECTORY=
  STAGED_MANIFEST="$INSTALLER_DIR/.UpdateSigningKey.json.$$"
  cleanup() {
    if [ -n "${TRANSFER_DIRECTORY:-}" ]; then
      rm -rf "$TRANSFER_DIRECTORY"
    fi
    if [ -n "${STAGED_MANIFEST:-}" ]; then
      rm -f "$STAGED_MANIFEST"
    fi
  }
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
      "kind": "github-environment",
      "environment": "$GITHUB_ENVIRONMENT",
      "secretName": "$manifest_secret_name"
    },
    "recovery": {
      "kind": "macos-keychain",
      "account": "$KEYCHAIN_ACCOUNT"
    }
  }
}
EOF
  release_signing_require_active_manifest "$STAGED_MANIFEST" ||
    fail "generated public signing manifest did not pass validation"
  TRANSFER_DIRECTORY=$(mktemp -d "${TMPDIR:-/tmp}/graf-sparkle-transfer.XXXXXX")
  TRANSFER_FILE="$TRANSFER_DIRECTORY/signing-key"
  "$GENERATE_KEYS" --account "$KEYCHAIN_ACCOUNT" -x "$TRANSFER_FILE" >/dev/null 2>&1 ||
    fail "could not create a transient protected transfer"
  chmod 600 "$TRANSFER_FILE"
  [ "$(stat -f '%Lp' "$TRANSFER_FILE" 2>/dev/null || true)" = "600" ] ||
    fail "transient protected transfer does not have 0600 permissions"
  gh secret set "$manifest_secret_name" --env "$GITHUB_ENVIRONMENT" < "$TRANSFER_FILE" >/dev/null ||
    fail "protected GitHub environment secret transfer failed"
  mv "$STAGED_MANIFEST" "$MANIFEST" ||
    fail "could not activate the reviewed public signing manifest"
  STAGED_MANIFEST=
  trap - EXIT HUP INT TERM
  cleanup
  printf 'key_id=%s\ntrust_generation=1\nkeychain=ready\ngithub_environment=transferred\nnext_action=commit_public_manifest_for_review\n' "$KEY_ID"
  exit 0
fi

[ -n "$CANDIDATE_APP" ] || usage
[ -n "$ATTESTATION" ] || usage
[ -n "$RELEASE_TAG" ] || usage
release_signing_require_active_manifest "$MANIFEST" || exit 1
if [ -n "$KEYCHAIN_ACCOUNT" ] && [ "$KEYCHAIN_ACCOUNT" != "$RELEASE_SIGNING_RECOVERY_ACCOUNT" ]; then
  fail "Keychain account does not match the active public signing generation"
fi
if [ -n "$GITHUB_ENVIRONMENT" ] && [ "$GITHUB_ENVIRONMENT" != "$RELEASE_SIGNING_PRIMARY_ENVIRONMENT" ]; then
  fail "GitHub environment does not match the active public signing generation"
fi
if ! KEYCHAIN_PUBLIC_KEY=$("$GENERATE_KEYS" --account "$RELEASE_SIGNING_RECOVERY_ACCOUNT" -p 2>/dev/null | tr -d '\r\n'); then
  fail "named Keychain recovery generation is unavailable"
fi
release_signing_require_matching_public_key "$KEYCHAIN_PUBLIC_KEY" "$RELEASE_SIGNING_PUBLIC_KEY" "named Keychain recovery generation" || exit 1

set -- --app "$CANDIDATE_APP" --attestation "$ATTESTATION" --release-tag "$RELEASE_TAG"
"$VERIFIER" "$@"
