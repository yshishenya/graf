#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
INSTALLER_DIR=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
MACOS_DIR=$(CDPATH='' cd -- "$INSTALLER_DIR/.." && pwd)
REPO_ROOT=$(git -C "$MACOS_DIR" rev-parse --show-toplevel)
COMMON="$SCRIPT_DIR/release-signing-common.sh"
PREPARE="$SCRIPT_DIR/prepare-app-update.sh"
BOOTSTRAP_VALIDATOR="$SCRIPT_DIR/validate-manual-update-bootstrap.sh"
BOOTSTRAP_BUILDER="$SCRIPT_DIR/build-trust-bootstrap.sh"
ORDINARY_VALIDATOR="$MACOS_DIR/Scripts/validate-app-updates.sh"
PROVISIONER="$SCRIPT_DIR/provision-release-signing-custody.sh"
VERIFIER="$SCRIPT_DIR/verify-release-signing-custody.sh"
VERIFY_WORKFLOW="$REPO_ROOT/.github/workflows/verify-release-signing-custody.yml"
SIGN_WORKFLOW="$REPO_ROOT/.github/workflows/sign-graf-app-update.yml"

fail() {
  echo "release-signing custody test failed: $*" >&2
  exit 1
}

if [ "${1:-}" = "--assert-fixture-class" ]; then
  [ "${GRAF_RELEASE_SIGNING_FIXTURE_CLASS:-disposable-public}" = "disposable-public" ] ||
    fail "only disposable public signing fixtures are permitted"
  exit 0
fi

[ -x "$COMMON" ] || fail "shared release-signing helper is missing or not executable"
[ -x "$PREPARE" ] || fail "appcast preparation helper is missing or not executable"
[ -x "$BOOTSTRAP_VALIDATOR" ] || fail "manual bootstrap validator is missing or not executable"
[ -x "$BOOTSTRAP_BUILDER" ] || fail "manual bootstrap builder is missing or not executable"
[ -x "$ORDINARY_VALIDATOR" ] || fail "ordinary update validator is missing or not executable"
[ -x "$PROVISIONER" ] || fail "release-signing provisioner is missing or not executable"
[ -x "$VERIFIER" ] || fail "release-signing verifier is missing or not executable"
[ -f "$VERIFY_WORKFLOW" ] || fail "protected custody workflow is missing"
[ -f "$SIGN_WORKFLOW" ] || fail "draft-signing workflow is missing"

if GRAF_RELEASE_SIGNING_FIXTURE_CLASS=production "$0" --assert-fixture-class >/dev/null 2>&1; then
  fail "production-key fixture was accepted"
fi

TEMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/graf-release-signing.XXXXXX")
cleanup() {
  rm -rf "$TEMP_ROOT"
}
trap cleanup EXIT HUP INT TERM

DUMMY_PUBLIC_KEY=$(dd if=/dev/zero bs=32 count=1 2>/dev/null | /usr/bin/base64)
DUMMY_KEY_ID=$(
  # shellcheck source=release-signing-common.sh
  . "$COMMON"
  release_signing_key_id "$DUMMY_PUBLIC_KEY"
)

write_manifest() {
  destination=$1
  status=$2
  generation=$3
  key_id=$4
  public_key=$5
  cat > "$destination" <<EOF
{
  "schemaVersion": 1,
  "status": "$status",
  "trustGeneration": $generation,
  "keyId": "$key_id",
  "publicKey": "$public_key",
  "channels": {
    "primary": {
      "kind": "github-environment",
      "environment": "graf-release-signing-test",
      "secretName": "GRAF_SPARKLE_ED25519_PRIVATE_KEY"
    },
    "recovery": {
      "kind": "macos-keychain",
      "account": "graf-release-signing-test"
    }
  }
}
EOF
}

VALID_MANIFEST="$TEMP_ROOT/valid.json"
write_manifest "$VALID_MANIFEST" active 1 "$DUMMY_KEY_ID" "$DUMMY_PUBLIC_KEY"
(
  # shellcheck source=release-signing-common.sh
  . "$COMMON"
  release_signing_require_active_manifest "$VALID_MANIFEST"
  [ "$RELEASE_SIGNING_KEY_ID" = "$DUMMY_KEY_ID" ]
  [ "$RELEASE_SIGNING_PUBLIC_KEY" = "$DUMMY_PUBLIC_KEY" ]
) || fail "valid disposable public manifest was rejected"

write_attestation() {
  destination=$1
  release_ref=$2
  checked_at=${3:-$SAFE_CHECKED_AT}
  commit=${4:-0000000000000000000000000000000000000000}
  cat > "$destination" <<EOF
{
  "schemaVersion": 1,
  "keyId": "$DUMMY_KEY_ID",
  "trustGeneration": 1,
  "channel": "github-environment",
  "state": "ready",
  "checkedAt": "$checked_at",
  "releaseRef": "$release_ref",
  "commit": "$commit",
  "workflow": "verify-release-signing-custody",
  "runId": "1"
}
EOF
}

SAFE_CHECKED_AT=$(LC_ALL=C /bin/date -u '+%Y-%m-%dT%H:%M:%SZ')
write_attestation "$TEMP_ROOT/attestation.json" v2026.07.17.999
(
  # shellcheck source=release-signing-common.sh
  . "$COMMON"
  release_signing_require_active_manifest "$VALID_MANIFEST"
  release_signing_require_attestation "$TEMP_ROOT/attestation.json" v2026.07.17.999 0000000000000000000000000000000000000000
) || fail "matching safe attestation was rejected"

write_keychain_attestation() {
  destination=$1
  release_ref=$2
  checked_at=${3:-$SAFE_CHECKED_AT}
  commit=${4:-0000000000000000000000000000000000000000}
  cat > "$destination" <<EOF
{
  "schemaVersion": 1,
  "keyId": "$DUMMY_KEY_ID",
  "trustGeneration": 1,
  "channel": "macos-keychain",
  "state": "ready",
  "checkedAt": "$checked_at",
  "releaseRef": "$release_ref",
  "commit": "$commit",
  "workflow": "verify-release-signing-custody-local",
  "evidenceId": "00000000-0000-4000-8000-000000000000"
}
EOF
}

write_keychain_attestation "$TEMP_ROOT/keychain-attestation.json" v2026.07.17.999
(
  # shellcheck source=release-signing-common.sh
  . "$COMMON"
  release_signing_require_active_manifest "$VALID_MANIFEST"
  release_signing_require_keychain_attestation "$TEMP_ROOT/keychain-attestation.json" v2026.07.17.999 0000000000000000000000000000000000000000
) || fail "matching safe Keychain attestation was rejected"

write_attestation "$TEMP_ROOT/stale-attestation.json" v2026.07.17.998
if (
  # shellcheck source=release-signing-common.sh
  . "$COMMON"
  release_signing_require_active_manifest "$VALID_MANIFEST"
  release_signing_require_attestation "$TEMP_ROOT/stale-attestation.json" v2026.07.17.999 0000000000000000000000000000000000000000
) >/dev/null 2>&1; then
  fail "stale safe attestation was accepted for another release"
fi

if (
  # shellcheck source=release-signing-common.sh
  . "$COMMON"
  release_signing_require_active_manifest "$VALID_MANIFEST"
  release_signing_require_attestation "$TEMP_ROOT/attestation.json" v2026.07.17.999 1111111111111111111111111111111111111111
) >/dev/null 2>&1; then
  fail "safe attestation with the wrong commit was accepted"
fi

write_attestation "$TEMP_ROOT/expired-attestation.json" v2026.07.17.999 '2000-01-01T00:00:00Z'
if (
  # shellcheck source=release-signing-common.sh
  . "$COMMON"
  release_signing_require_active_manifest "$VALID_MANIFEST"
  release_signing_require_attestation "$TEMP_ROOT/expired-attestation.json" v2026.07.17.999 0000000000000000000000000000000000000000
) >/dev/null 2>&1; then
  fail "expired safe attestation was accepted"
fi

sha256_file() {
  shasum -a 256 "$1" | awk '{print $1}'
}

write_staged_appcast() {
  destination=$1
  version=$2
  cat > "$destination" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<rss><channel><item><version>$version</version></item></channel></rss>
EOF
}

assert_staged_appcast_unchanged() {
  label=$1
  destination=$2
  expected_digest=$3
  [ "$(sha256_file "$destination")" = "$expected_digest" ] ||
    fail "$label changed the staged appcast"
}

run_prepare_attestation_failure() {
  label=$1
  release_ref=$2
  commit=$3
  fixture="$TEMP_ROOT/prepare-$label"
  staged_appcast="$REPO_ROOT/apps/macos/.build/updates/graf-appcast.xml"
  fake_git="$fixture/git"
  mkdir -p "$fixture/candidate/GRAF.app" "$fixture/previous/GRAF.app"
  printf '%s\n' 'Проверка безопасного выпуска.' > "$fixture/release-notes.md"
  write_keychain_attestation "$fixture/keychain-attestation.json" v2026.07.20.6 "$SAFE_CHECKED_AT"
  write_attestation "$fixture/attestation.json" "$release_ref" "$SAFE_CHECKED_AT" "$commit"
  mkdir -p "$(dirname -- "$staged_appcast")"
  write_staged_appcast "$staged_appcast" 2026.07.20.1
  before_digest=$(sha256_file "$staged_appcast")
  cat > "$fake_git" <<'EOF'
#!/usr/bin/env sh
if [ "$1" = "-C" ] && [ "$3" = "rev-parse" ] && [ "$4" = "--show-toplevel" ]; then
  exec "$(command -p git)" "$@"
fi
if [ "$1" = "-C" ] && [ "$3" = "status" ]; then
  exit 0
fi
if [ "$1" = "-C" ] && [ "$3" = "rev-parse" ]; then
  case "$4" in
    HEAD|refs/tags/*)
      printf '%s\n' 0000000000000000000000000000000000000000
      exit 0
      ;;
  esac
fi
if [ "$1" = "-C" ] && [ "$3" = "ls-remote" ]; then
  case "$5" in
    refs/heads/master)
      printf '%s\trefs/heads/master\n' 0000000000000000000000000000000000000000
      ;;
    refs/tags/*)
      printf '%s\t%s\n' 0000000000000000000000000000000000000000 "$5"
      printf '%s\t%s^{}\n' 0000000000000000000000000000000000000000 "$5"
      ;;
    *)
      exec "$(command -p git)" "$@"
      ;;
  esac
  exit 0
fi
exec "$(command -p git)" "$@"
EOF
  chmod 755 "$fake_git"
  if PATH="$fixture:$PATH" \
    GRAF_VERSION=2026.07.20.6 \
    GRAF_UPDATE_APP_BUNDLE="$fixture/candidate/GRAF.app" \
    GRAF_PREVIOUS_APP_BUNDLE="$fixture/previous/GRAF.app" \
    GRAF_UPDATE_RELEASE_NOTES="$fixture/release-notes.md" \
    GRAF_UPDATE_DOWNLOAD_BASE_URL=https://rec.2brain.pro/static/public/downloads \
    GRAF_REQUIRE_RELEASE_PROVENANCE=1 \
    GRAF_RELEASE_SIGNING_MODE=keychain \
    GRAF_RELEASE_SIGNING_KEYCHAIN_ATTESTATION="$fixture/keychain-attestation.json" \
    GRAF_RELEASE_SIGNING_ATTESTATION="$fixture/attestation.json" \
    sh "$PREPARE" >/dev/null 2>&1; then
    fail "$label attestation failure was accepted"
  fi
  assert_staged_appcast_unchanged "$label attestation failure" "$staged_appcast" "$before_digest"
  rm -rf "$REPO_ROOT/apps/macos/.build/updates"
  echo "failure_simulation=$label result=pass"
}

run_prepare_missing_draft_failure() {
  fixture="$TEMP_ROOT/prepare-missing-draft"
  staged_appcast="$REPO_ROOT/apps/macos/.build/updates/graf-appcast.xml"
  mkdir -p "$fixture"
  mkdir -p "$(dirname -- "$staged_appcast")"
  write_staged_appcast "$staged_appcast" 2026.07.20.1
  before_digest=$(sha256_file "$staged_appcast")
  if GRAF_VERSION=2026.07.20.6 \
    GRAF_UPDATE_APP_BUNDLE="$fixture/missing/GRAF.app" \
    sh "$PREPARE" >/dev/null 2>&1; then
    fail "missing draft app bundle was accepted"
  fi
  assert_staged_appcast_unchanged "missing draft app bundle" "$staged_appcast" "$before_digest"
  rm -rf "$REPO_ROOT/apps/macos/.build/updates"
  echo "failure_simulation=draft_asset_failure result=pass"
}

run_prepare_staging_guard_failures() {
  candidate_app=$(printenv GRAF_RELEASE_SIGNING_CANDIDATE_APP_BUNDLE || true)
  previous_app=$(printenv GRAF_RELEASE_SIGNING_PREVIOUS_APP_BUNDLE || true)
  if [ ! -d "$candidate_app" ] || [ ! -d "$previous_app" ]; then
    echo "staging_failure_simulations=skipped reason=disposable_app_fixture_not_provided"
    return 0
  fi

  if [ -e "$MACOS_DIR/.build/artifacts/sparkle" ]; then
    echo "staging_failure_simulations=skipped reason=existing_sparkle_tools_preserved"
    return 0
  fi

  sparkle_bin_dir="$MACOS_DIR/.build/artifacts/sparkle/Sparkle/bin"
  staged_appcast="$REPO_ROOT/apps/macos/.build/updates/graf-appcast.xml"
  manifest_public_key=$(/usr/bin/plutil -extract publicKey raw -o - "$MACOS_DIR/Installer/UpdateSigningKey.json")
  mkdir -p "$sparkle_bin_dir"
  cat > "$sparkle_bin_dir/generate_keys" <<EOF
#!/usr/bin/env sh
case " \$* " in
  *" -p "*) printf '%s\n' "$manifest_public_key" ;;
esac
EOF
  cat > "$sparkle_bin_dir/generate_appcast" <<'EOF'
#!/usr/bin/env sh
exit 0
EOF
  cat > "$sparkle_bin_dir/sign_update" <<'EOF'
#!/usr/bin/env sh
exit 0
EOF
  chmod 755 "$sparkle_bin_dir/generate_keys" "$sparkle_bin_dir/generate_appcast" "$sparkle_bin_dir/sign_update"
  release_notes="$TEMP_ROOT/staging-release-notes.md"
  printf '%s\n' 'Проверка безопасного выпуска.' > "$release_notes"

  mkdir -p "$(dirname -- "$staged_appcast")"
  write_staged_appcast "$staged_appcast" 2026.07.20.1
  before_digest=$(sha256_file "$staged_appcast")
  mkdir "$REPO_ROOT/apps/macos/.build/.graf-update-staging.lock"
  if GRAF_VERSION=2026.07.20.2 \
    GRAF_UPDATE_APP_BUNDLE="$candidate_app" \
    GRAF_PREVIOUS_APP_BUNDLE="$previous_app" \
    GRAF_UPDATE_RELEASE_NOTES="$release_notes" \
    GRAF_UPDATE_DOWNLOAD_BASE_URL=https://rec.2brain.pro/static/public/downloads \
    GRAF_RELEASE_SIGNING_MODE=keychain \
    sh "$PREPARE" >/dev/null 2>&1; then
    fail "concurrent staging attempt was accepted"
  fi
  assert_staged_appcast_unchanged "concurrent staging attempt" "$staged_appcast" "$before_digest"
  rmdir "$REPO_ROOT/apps/macos/.build/.graf-update-staging.lock"
  rm -rf "$REPO_ROOT/apps/macos/.build/updates"
  echo "failure_simulation=concurrent_staging result=pass"

  mkdir -p "$(dirname -- "$staged_appcast")"
  write_staged_appcast "$staged_appcast" 2099.12.31.1
  before_digest=$(sha256_file "$staged_appcast")
  if GRAF_VERSION=2026.07.20.2 \
    GRAF_UPDATE_APP_BUNDLE="$candidate_app" \
    GRAF_PREVIOUS_APP_BUNDLE="$previous_app" \
    GRAF_UPDATE_RELEASE_NOTES="$release_notes" \
    GRAF_UPDATE_DOWNLOAD_BASE_URL=https://rec.2brain.pro/static/public/downloads \
    GRAF_RELEASE_SIGNING_MODE=keychain \
    sh "$PREPARE" >/dev/null 2>&1; then
    fail "forward-rollback attempt was accepted"
  fi
  assert_staged_appcast_unchanged "forward rollback" "$staged_appcast" "$before_digest"
  rm -rf "$REPO_ROOT/apps/macos/.build/updates"
  rm -f "$sparkle_bin_dir/generate_keys" "$sparkle_bin_dir/generate_appcast" "$sparkle_bin_dir/sign_update"
  rmdir "$sparkle_bin_dir" "$MACOS_DIR/.build/artifacts/sparkle/Sparkle" \
    "$MACOS_DIR/.build/artifacts/sparkle" 2>/dev/null || true
  echo "failure_simulation=forward_rollback result=pass"
  echo "staging_failure_simulations=pass"
}

printf '%s' '{not-json}' > "$TEMP_ROOT/malformed.json"
if (
  # shellcheck source=release-signing-common.sh
  . "$COMMON"
  release_signing_require_active_manifest "$TEMP_ROOT/malformed.json"
) >/dev/null 2>&1; then
  fail "malformed manifest was accepted"
fi

write_manifest "$TEMP_ROOT/mismatched-id.json" active 1 'sha256:0000000000000000000000000000000000000000000000000000000000000000' "$DUMMY_PUBLIC_KEY"
if (
  # shellcheck source=release-signing-common.sh
  . "$COMMON"
  release_signing_require_active_manifest "$TEMP_ROOT/mismatched-id.json"
) >/dev/null 2>&1; then
  fail "manifest with mismatched key identifier was accepted"
fi

RUNNER_TEMP_FIXTURE="$TEMP_ROOT/runner-temp"
mkdir -p "$RUNNER_TEMP_FIXTURE"
TEMP_KEY_FILE="$RUNNER_TEMP_FIXTURE/key"
: > "$TEMP_KEY_FILE"
chmod 644 "$TEMP_KEY_FILE"
if GITHUB_ACTIONS=true \
  RUNNER_TEMP="$RUNNER_TEMP_FIXTURE" \
  GRAF_RELEASE_SIGNING_MODE=ephemeral-ci \
  GRAF_RELEASE_SIGNING_CI_KEY_FILE="$TEMP_KEY_FILE" \
  sh -c '. "$1"; release_signing_select_signer' sh "$COMMON" >/dev/null 2>&1; then
  fail "ephemeral CI key file with unsafe permissions was accepted"
fi
chmod 600 "$TEMP_KEY_FILE"
SYMLINKED_TEMP_KEY="$RUNNER_TEMP_FIXTURE/symlinked-key"
ln -s "$TEMP_KEY_FILE" "$SYMLINKED_TEMP_KEY"
if GITHUB_ACTIONS=true \
  RUNNER_TEMP="$RUNNER_TEMP_FIXTURE" \
  GRAF_RELEASE_SIGNING_MODE=ephemeral-ci \
  GRAF_RELEASE_SIGNING_CI_KEY_FILE="$SYMLINKED_TEMP_KEY" \
  sh -c '. "$1"; release_signing_select_signer' sh "$COMMON" >/dev/null 2>&1; then
  fail "symlinked ephemeral CI key file was accepted"
fi

if GRAF_VERSION=2026.07.17.999 \
  GRAF_SPARKLE_PRIVATE_KEY_FILE="$TEMP_KEY_FILE" \
  sh "$PREPARE" >/dev/null 2>&1; then
  fail "legacy arbitrary private-file input was accepted"
fi

grep -Fq 'Sparkle public key changed without an approved rotation' "$ORDINARY_VALIDATOR" ||
  fail "ordinary Sparkle key rotation guard is missing"
grep -Fq 'manual trust bootstrap requires a new public signing generation' "$ORDINARY_VALIDATOR" ||
  fail "manual-only trust transition guard is missing"
grep -Fq 'GRAF_MANUAL_TRUST_BOOTSTRAP=1' "$BOOTSTRAP_VALIDATOR" ||
  fail "manual bootstrap wrapper does not activate its explicit validator mode"
grep -Fq 'manual trust bootstrap must not receive an appcast' "$BOOTSTRAP_VALIDATOR" ||
  fail "manual bootstrap wrapper can receive an appcast"
grep -Fq 'appcast_staged=no' "$BOOTSTRAP_BUILDER" ||
  fail "bootstrap builder does not explicitly forbid appcast staging"
grep -Fq 'release provenance requires a safe signing attestation' "$PREPARE" ||
  fail "production staging does not require safe attestation binding"
grep -Fq 'explicitly approved Keychain fallback' "$PREPARE" ||
  fail "production staging cannot use the explicit Keychain degraded fallback"
grep -Fq 'GRAF_RELEASE_SIGNING_DEGRADED_APPROVAL_ID' "$PREPARE" ||
  fail "production staging does not record a safe degraded-fallback approval identifier"
grep -Fq 'another release staging attempt is already in progress' "$PREPARE" ||
  fail "local staging is not serialized"
grep -Fq '.graf-update-staging.lock' "$PREPARE" ||
  fail "local staging lock is missing"
grep -Fq 'safe signing attestation does not bind the requested release' "$COMMON" ||
  fail "shared helper does not reject stale attestation binding"
grep -Fq 'safe signing attestation does not bind the requested commit' "$COMMON" ||
  fail "shared helper does not reject wrong attestation commit binding"
grep -Fq 'safe signing attestation is older than 24 hours' "$COMMON" ||
  fail "shared helper does not reject expired attestation evidence"
grep -Fq 'safe Keychain attestation does not bind the requested commit' "$COMMON" ||
  fail "shared helper does not bind the Keychain attestation to the release commit"
grep -Fq 'gh secret set' "$PROVISIONER" ||
  fail "provisioner does not transfer through a protected GitHub environment secret"
grep -Fq 'initialization refuses to overwrite an existing Keychain signing generation' "$PROVISIONER" ||
  fail "provisioner could overwrite a named Keychain generation"
grep -Fq 'could not prove that the named Keychain signing generation is absent' "$PROVISIONER" ||
  fail "provisioner treats a Keychain lookup error as an absent generation"
grep -Fq -- '--resume is an explicit owner-only recovery' "$PROVISIONER" ||
  fail "provisioner cannot safely resume an interrupted approved enrollment"
grep -Fq 'mktemp -d' "$PROVISIONER" ||
  fail "provisioner does not create a private temporary transfer directory"
grep -Fq 'rm -rf "$TRANSFER_DIRECTORY"' "$PROVISIONER" ||
  fail "provisioner does not clean its transient transfer"
grep -Fq 'overall=ready' "$VERIFIER" ||
  fail "verifier does not emit a safe ready state"
grep -Fq 'GRAF_RELEASE_SIGNING_APPROVED_DEGRADED_FALLBACK' "$VERIFIER" ||
  fail "verifier does not require explicit degraded-fallback approval"

for source in "$COMMON" "$PREPARE" "$BOOTSTRAP_VALIDATOR" "$BOOTSTRAP_BUILDER" "$ORDINARY_VALIDATOR" "$PROVISIONER" "$VERIFIER"; do
  sh -n "$source"
done

for workflow in "$VERIFY_WORKFLOW" "$SIGN_WORKFLOW"; do
  grep -Fq 'workflow_dispatch:' "$workflow" || fail "workflow is not manually dispatched"
  if grep -Eq '^[[:space:]]*pull_request' "$workflow"; then
    fail "workflow accepts pull-request execution"
  fi
  grep -Fq "if: github.ref == 'refs/heads/master'" "$workflow" ||
    fail "workflow does not require the protected default branch"
  if grep -Eq 'set -x|curl |scp |rsync ' "$workflow"; then
    fail "workflow contains an unsafe logging or public-host command"
  fi
  if grep -E '^ *uses:' "$workflow" | grep -Ev '@[0-9a-f]{40}( |$)' >/dev/null; then
    fail "workflow contains an external action without an immutable full SHA"
  fi
done
grep -Fq 'graf-release-signing-test' "$VERIFY_WORKFLOW" ||
  fail "custody workflow lacks a dedicated non-production environment"
grep -Fq 'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02' "$VERIFY_WORKFLOW" ||
  fail "safe attestation artifact action is not immutably pinned"
grep -Fq 'concurrency:' "$SIGN_WORKFLOW" ||
  fail "draft-signing workflow is not serialized"
grep -Fq 'GRAF_RELEASE_SIGNING_MODE=ephemeral-ci' "$SIGN_WORKFLOW" ||
  fail "draft-signing workflow does not use the restrictive CI signer mode"
grep -Fq 'GRAF_RELEASE_SIGNING_ATTESTATION="$ATTESTATION"' "$SIGN_WORKFLOW" ||
  fail "draft-signing workflow does not bind staging to its safe attestation"
grep -Fq 'GRAF_RELEASE_SIGNING_KEYCHAIN_ATTESTATION="$KEYCHAIN_ATTESTATION"' "$SIGN_WORKFLOW" ||
  fail "draft-signing workflow does not require the safe Keychain attestation"
grep -Fq 'keychain_attestation_asset:' "$SIGN_WORKFLOW" ||
  fail "draft-signing workflow has no safe Keychain-attestation draft input"
grep -Fq '"checkedAt": "$CHECKED_AT"' "$VERIFY_WORKFLOW" ||
  fail "custody workflow does not timestamp its safe attestation"
grep -Fq '"channel": "github-environment"' "$SIGN_WORKFLOW" ||
  fail "draft-signing workflow does not label the cloud channel"
grep -Fq 'gh release upload' "$SIGN_WORKFLOW" ||
  fail "draft-signing workflow does not upload signed draft assets"
if grep -Fq 'GRAF_SPARKLE_PRIVATE_KEY_FILE' "$SIGN_WORKFLOW"; then
  fail "draft-signing workflow still accepts the legacy arbitrary private-file input"
fi
command -v ruby >/dev/null 2>&1 || fail "Ruby is required for workflow syntax validation"
ruby -e 'require "yaml"; ARGV.each { |path| YAML.load_file(path) }' "$VERIFY_WORKFLOW" "$SIGN_WORKFLOW"
ruby -ryaml -e 'd=YAML.load_file(ARGV[0]); print d["jobs"]["verify"]["steps"][1]["run"]' "$VERIFY_WORKFLOW" | sh -n
ruby -ryaml -e 'd=YAML.load_file(ARGV[0]); print d["jobs"]["sign-draft"]["steps"][1]["run"]' "$SIGN_WORKFLOW" | sh -n

if rg -n -I -e \
  '(BEGIN (EC|RSA|OPENSSH) PRIVATE KEY|private[_-]?key[[:space:]]*=[[:space:]]*[A-Za-z0-9+/]{40,}|ed25519:[[:space:]]*[A-Za-z0-9+/]{40,})' \
  "$REPO_ROOT/.github" \
  "$REPO_ROOT/apps/macos/Installer" \
  "$REPO_ROOT/apps/macos/Scripts" \
  "$REPO_ROOT/apps/macos/Shared" \
  "$REPO_ROOT/qa" >/dev/null; then
  fail "current source contains a probable secret literal"
else
  secret_scan_status=$?
  [ "$secret_scan_status" = "1" ] ||
    fail "current-source secret-pattern guard could not complete"
fi

run_prepare_attestation_failure stale_attestation v2026.07.20.5 0000000000000000000000000000000000000000
run_prepare_attestation_failure wrong_release_attestation v2026.07.20.6 1111111111111111111111111111111111111111
run_prepare_missing_draft_failure
run_prepare_staging_guard_failures

echo "release-signing custody tests passed: fixture=disposable-public key_id=$DUMMY_KEY_ID"
