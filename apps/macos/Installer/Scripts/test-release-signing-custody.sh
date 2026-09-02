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
LOCAL_SIGNER="$SCRIPT_DIR/sign-graf-app-update-local.sh"
STARTUP_VALIDATOR="$MACOS_DIR/Scripts/validate-packaged-app-launch.sh"

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
[ -x "$LOCAL_SIGNER" ] || fail "local draft-signing entrypoint is missing or not executable"
[ -x "$STARTUP_VALIDATOR" ] || fail "packaged app launch validator is missing or not executable"

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

SAFE_CHECKED_AT=$(LC_ALL=C /bin/date -u '+%Y-%m-%dT%H:%M:%SZ')

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

write_keychain_attestation "$TEMP_ROOT/stale-attestation.json" v2026.07.17.998
if (
  # shellcheck source=release-signing-common.sh
  . "$COMMON"
  release_signing_require_active_manifest "$VALID_MANIFEST"
  release_signing_require_keychain_attestation "$TEMP_ROOT/stale-attestation.json" v2026.07.17.999 0000000000000000000000000000000000000000
) >/dev/null 2>&1; then
  fail "stale safe attestation was accepted for another release"
fi

if (
  # shellcheck source=release-signing-common.sh
  . "$COMMON"
  release_signing_require_active_manifest "$VALID_MANIFEST"
  release_signing_require_keychain_attestation "$TEMP_ROOT/keychain-attestation.json" v2026.07.17.999 1111111111111111111111111111111111111111
) >/dev/null 2>&1; then
  fail "safe attestation with the wrong commit was accepted"
fi

write_keychain_attestation "$TEMP_ROOT/expired-attestation.json" v2026.07.17.999 '2000-01-01T00:00:00Z'
if (
  # shellcheck source=release-signing-common.sh
  . "$COMMON"
  release_signing_require_active_manifest "$VALID_MANIFEST"
  release_signing_require_keychain_attestation "$TEMP_ROOT/expired-attestation.json" v2026.07.17.999 0000000000000000000000000000000000000000
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
  write_keychain_attestation "$fixture/keychain-attestation.json" "$release_ref" "$SAFE_CHECKED_AT" "$commit"
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

run_local_signer_failures() {
  fixture="$TEMP_ROOT/local-signer"
  fake_bin="$fixture/bin"
  upload_log="$fixture/upload.log"
  mkdir -p "$fake_bin" "$fixture/archive/GRAF.app"
  ln -s ../../outside "$fixture/archive/GRAF.app/unsafe-link"
  (cd "$fixture/archive" && zip -qry -y "$fixture/candidate.zip" GRAF.app)
  printf '%s\n' 'not used' > "$fixture/previous.zip"
  printf '%s\n' 'Проверка безопасного выпуска.' > "$fixture/notes.md"

cat > "$fake_bin/git" <<'EOF'
#!/usr/bin/env sh
if [ "${1:-}" = "-C" ]; then shift 2; fi
case "${1:-}" in
  remote)
    [ "${2:-}" = "get-url" ] && printf '%s\n' 'git@github.com:yshishenya/crisp.git' ;;
  rev-parse)
    if [ "${2:-}" = "--show-toplevel" ]; then
      printf '%s\n' "$GRAF_TEST_REPO_ROOT"
    elif [ "${2:-}" = "refs/tags/v2026.07.20.6^{}" ]; then
      printf '%s\n' 6666666666666666666666666666666666666666
    elif [ "${2:-}" = "refs/tags/v2026.07.20.5^{}" ]; then
      printf '%s\n' 5555555555555555555555555555555555555555
    else
      printf '%s\n' 6666666666666666666666666666666666666666
    fi
    ;;
  merge-base) [ "${GRAF_TEST_ANCESTOR:-1}" = "1" ] ;;
  status)
    [ "${GRAF_TEST_GIT_DIRTY:-0}" = "0" ] || printf '%s\n' ' M tracked-file'
    ;;
  fetch) ;;
  ls-remote)
    printf '%s\t%s\n' 6666666666666666666666666666666666666666 "${3:-refs/heads/master}"
    ;;
  *) exit 1 ;;
esac
EOF
cat > "$fake_bin/gh" <<'EOF'
#!/usr/bin/env sh
repo=
if [ "${1:-}" = "--repo" ]; then repo=$2; shift 2; fi
case "${1:-} ${2:-}" in
  'auth status') exit 0 ;;
  'release view')
    [ "$repo" = yshishenya/crisp ] || exit 1
    printf '%s\n' "${GRAF_TEST_RELEASE_DRAFT:-false}"
    ;;
  'release download')
    case "$repo" in yshishenya/crisp|sparkle-project/Sparkle) ;; *) exit 1 ;; esac
    shift 2
    pattern=
    destination=
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --pattern) shift; pattern=$1 ;;
        --dir) shift; destination=$1 ;;
      esac
      shift
    done
    case "$pattern" in
      candidate.zip) source=$GRAF_TEST_CANDIDATE_SOURCE ;;
      previous.zip) source=$GRAF_TEST_PREVIOUS_SOURCE ;;
      notes.md) source=$GRAF_TEST_NOTES_SOURCE ;;
      *) exit 1 ;;
    esac
    cp "$source" "$destination/$pattern"
    ;;
  'release upload')
    [ "$repo" = yshishenya/crisp ] || exit 1
    printf '%s\n' upload >> "$GRAF_TEST_UPLOAD_LOG"
    ;;
  *) exit 1 ;;
esac
EOF
  chmod 755 "$fake_bin/git" "$fake_bin/gh"

  run_local_signer_failure() {
    label=$1
    dirty=$2
    draft=$3
    previous_tag=${4:-v2026.07.20.5}
    ancestor=${5:-1}
    gh_repo=${6:-}
    if GRAF_TEST_REPO_ROOT="$REPO_ROOT" \
      GRAF_TEST_GIT_DIRTY="$dirty" \
      GRAF_TEST_RELEASE_DRAFT="$draft" \
      GRAF_TEST_ANCESTOR="$ancestor" \
      GRAF_TEST_CANDIDATE_SOURCE="$fixture/candidate.zip" \
      GRAF_TEST_PREVIOUS_SOURCE="$fixture/previous.zip" \
      GRAF_TEST_NOTES_SOURCE="$fixture/notes.md" \
      GRAF_TEST_UPLOAD_LOG="$upload_log" \
      GH_REPO="$gh_repo" \
      PATH="$fake_bin:$PATH" \
      sh "$LOCAL_SIGNER" \
        --release-tag v2026.07.20.6 \
        --previous-tag "$previous_tag" \
        --candidate-app-asset candidate.zip \
        --previous-app-asset previous.zip \
        --release-notes-asset notes.md >/dev/null 2>&1; then
      fail "$label was accepted by the local signer"
    fi
    [ ! -s "$upload_log" ] || fail "$label reached draft upload"
    echo "failure_simulation=$label upload_count=0 result=pass"
  }

  run_local_signer_failure dirty_worktree 1 true
  run_local_signer_failure published_release 0 false
  run_local_signer_failure wrong_repository 0 true v2026.07.20.5 1 yshishenya/other
  run_local_signer_failure non_ancestor_predecessor 0 true v2026.07.20.5 0
  run_local_signer_failure newer_predecessor 0 true v2026.07.20.7 1
  lock_dir="$MACOS_DIR/.build/.graf-local-signing.lock"
  mkdir -p "$lock_dir"
  run_local_signer_failure concurrent_signer 0 true
  [ -d "$lock_dir" ] || fail "contending local signer removed the active serialization lock"
  rmdir "$lock_dir"
  run_local_signer_failure unsafe_symlink_archive 0 true
  [ ! -d "$MACOS_DIR/.build/.graf-local-signing.lock" ] ||
    fail "local signer failure left its serialization lock behind"
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

write_manifest "$TEMP_ROOT/legacy-fields.json" active 1 "$DUMMY_KEY_ID" "$DUMMY_PUBLIC_KEY"
sed -i '' 's/"account": "graf-release-signing-test"/"account": "graf-release-signing-test", "environment": "graf-release-signing"/' "$TEMP_ROOT/legacy-fields.json"
if (
  # shellcheck source=release-signing-common.sh
  . "$COMMON"
  release_signing_require_active_manifest "$TEMP_ROOT/legacy-fields.json"
) >/dev/null 2>&1; then
  fail "manifest with legacy remote signing fields was accepted"
fi

TEMP_KEY_FILE="$TEMP_ROOT/forbidden-key-file"
: > "$TEMP_KEY_FILE"

if GRAF_VERSION=2026.07.17.999 \
  GRAF_SPARKLE_PRIVATE_KEY_FILE="$TEMP_KEY_FILE" \
  sh "$PREPARE" >/dev/null 2>&1; then
  fail "legacy arbitrary private-file input was accepted"
fi

grep -Fq 'Sparkle public key changed without an approved rotation' "$ORDINARY_VALIDATOR" ||
  fail "ordinary Sparkle key rotation guard is missing"
grep -Fq 'Sparkle trust-generation bootstrap requires a new public signing generation' "$ORDINARY_VALIDATOR" ||
  fail "manual-only trust transition guard is missing"
grep -Fq 'GRAF_MANUAL_TRUST_BOOTSTRAP=1' "$BOOTSTRAP_VALIDATOR" ||
  fail "manual bootstrap wrapper does not activate its explicit validator mode"
grep -Fq 'Sparkle trust-generation bootstrap must not receive an appcast' "$BOOTSTRAP_VALIDATOR" ||
  fail "manual bootstrap wrapper can receive an appcast"
grep -Fq 'appcast_staged=no' "$BOOTSTRAP_BUILDER" ||
  fail "bootstrap builder does not explicitly forbid appcast staging"
grep -Fq 'release provenance requires a safe Keychain attestation' "$PREPARE" ||
  fail "production staging does not require local Keychain attestation binding"
grep -Fq 'another release staging attempt is already in progress' "$PREPARE" ||
  fail "local staging is not serialized"
grep -Fq '.graf-update-staging.lock' "$PREPARE" ||
  fail "local staging lock is missing"
grep -Fq 'safe signing attestation is older than 24 hours' "$COMMON" ||
  fail "shared helper does not reject expired attestation evidence"
grep -Fq 'safe Keychain attestation does not bind the requested commit' "$COMMON" ||
  fail "shared helper does not bind the Keychain attestation to the release commit"
if grep -Eq 'gh secret set|github-environment|GITHUB_ACTIONS|ephemeral-ci' "$PROVISIONER" "$COMMON" "$PREPARE" "$VERIFIER" "$LOCAL_SIGNER"; then
  fail "active release-signing source still contains a GitHub execution or signer channel"
fi
grep -Fq 'initialization refuses to overwrite an existing Keychain signing generation' "$PROVISIONER" ||
  fail "provisioner could overwrite a named Keychain generation"
grep -Fq 'could not prove that the named Keychain signing generation is absent' "$PROVISIONER" ||
  fail "provisioner treats a Keychain lookup error as an absent generation"
grep -Fq -- '--resume is an explicit Keychain recovery' "$PROVISIONER" ||
  fail "provisioner cannot safely resume an interrupted approved enrollment"
grep -Fq 'overall=ready' "$VERIFIER" ||
  fail "verifier does not emit a safe ready state"
grep -Fq 'origin/master commit' "$VERIFIER" ||
  fail "verifier does not bind the attestation to origin/master"

for source in "$COMMON" "$PREPARE" "$BOOTSTRAP_VALIDATOR" "$BOOTSTRAP_BUILDER" "$ORDINARY_VALIDATOR" "$PROVISIONER" "$VERIFIER" "$LOCAL_SIGNER" "$STARTUP_VALIDATOR"; do
  sh -n "$source"
done

grep -Fq 'release upload' "$LOCAL_SIGNER" ||
  fail "local draft-signing entrypoint does not upload bounded draft assets"
grep -Fq 'GRAF_RELEASE_SIGNING_MODE=keychain' "$LOCAL_SIGNER" ||
  fail "local draft-signing entrypoint does not use the named Keychain signer"
grep -Fq 'GRAF_RELEASE_SIGNING_KEYCHAIN_ATTESTATION="$ATTESTATION"' "$LOCAL_SIGNER" ||
  fail "local draft-signing entrypoint does not bind staging to local custody evidence"
grep -Fq 'codesign --verify --deep --strict "$app_bundle"' "$LOCAL_SIGNER" ||
  fail "local draft-signing entrypoint does not verify the downloaded candidate before launch"
grep -Fq 'codesign --verify --deep --strict "$previous_app_bundle"' "$LOCAL_SIGNER" ||
  fail "local draft-signing entrypoint does not verify the downloaded predecessor before launch"
grep -Fq 'Authority=Developer ID Application:' "$LOCAL_SIGNER" ||
  fail "local draft-signing entrypoint does not verify the downloaded candidate identity"
grep -Fq 'EXPECTED_GRAF_TEAM_IDENTIFIER=94N8HYG672' "$LOCAL_SIGNER" ||
  fail "local draft-signing entrypoint does not pin the trusted GRAF signing team"
grep -Fq 'downloaded predecessor app is not signed by the trusted GRAF team' "$LOCAL_SIGNER" ||
  fail "local draft-signing entrypoint does not verify predecessor team continuity before launch"
grep -Fq 'codesign -R="$previous_requirement" --verify "$app_bundle"' "$LOCAL_SIGNER" ||
  fail "local draft-signing entrypoint does not verify predecessor identity continuity before launch"
grep -Fq 'GRAF_LOG_DIRECTORY="$LOG_DIRECTORY"' "$STARTUP_VALIDATOR" ||
  fail "packaged-app launch validator does not isolate the application log directory"
grep -Fq 'GRAF_APPLICATION_SUPPORT_DIRECTORY="$APPLICATION_SUPPORT_DIRECTORY"' "$STARTUP_VALIDATOR" ||
  fail "packaged-app launch validator does not isolate application support storage"
grep -Fq 'event=app_launch_finished' "$STARTUP_VALIDATOR" ||
  fail "packaged-app launch validator does not require a startup readiness marker"
grep -Fq '"$STARTUP_VALIDATOR" "$APP_DIR/candidate/GRAF.app" 5 arm64' "$LOCAL_SIGNER" ||
  fail "local draft-signing entrypoint does not validate the arm64 packaged candidate launch"
grep -Fq '"$STARTUP_VALIDATOR" "$APP_DIR/candidate/GRAF.app" 5 x86_64' "$LOCAL_SIGNER" ||
  fail "local draft-signing entrypoint does not validate the x86_64 packaged candidate launch"
grep -Fq 'cb6fdbdc8884f15d62a616e79face92b08322410fd2d425edc6596ccbf4ba3b0' "$LOCAL_SIGNER" ||
  fail "local draft-signing entrypoint does not pin the Sparkle tool checksum"
workflow_files="$(find "$REPO_ROOT/.github/workflows" -type f -print 2>/dev/null || true)"
if [ -n "$workflow_files" ] &&
  printf '%s\n' "$workflow_files" | xargs grep -Eqi \
    'GRAF_RELEASE_SIGNING|SPARKLE_PRIVATE|PRIVATE_KEY|gh secret set|sign-graf-app-update'; then
  fail "remote workflow files remain in the active repository"
fi

if rg -n -I -e \
  '(BEGIN (EC|RSA|OPENSSH) PRIVATE KEY|private[_-]?key[[:space:]]*=[[:space:]]*[A-Za-z0-9+/]{40,}|ed25519:[[:space:]]*[A-Za-z0-9+/]{40,})' \
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
run_local_signer_failures
run_prepare_staging_guard_failures

echo "release-signing custody tests passed: fixture=disposable-public key_id=$DUMMY_KEY_ID"
