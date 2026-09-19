#!/usr/bin/env sh
# One command for the public macOS app update release.
#
# The release is a single chain: Developer ID build -> Apple notarization ->
# stapling -> Sparkle signature -> draft GitHub Release assets. This script runs
# that chain without adding or removing any trust gate: every step delegates to
# the existing validators, and the step order is the order they already require.
#
# Two phases exist so the external Apple wait can overlap the rest of the
# release train instead of extending it:
#
#   prepare   identities, exact-source build, notarization, stapling, the
#             codesign/stapler/spctl trust gates. Needs only the clean frozen
#             commit. Start it while the server release train is still running.
#   publish   Sparkle update signature and draft asset upload. Needs the exact
#             tag published at origin/master, so it runs after the tag exists.
#
# Use --phase prepare and --phase publish from two terminals, or --phase all for
# one foreground chain. Both are resumable: the underlying helpers reuse a
# completed notarization and a completed staged update byte for byte.
#
# This local command never publishes to the public feed. The outer release
# driver replaces infra/runtime/public-downloads/graf-appcast.xml atomically
# through publish-appcast-remote.sh after the signed assets are ready.
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
SELF_REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)
DEFAULT_REPO_ROOT=$SELF_REPO_ROOT
[ -n "$DEFAULT_REPO_ROOT" ] ||
  DEFAULT_REPO_ROOT=$(CDPATH='' cd -- "$SCRIPT_DIR/../../.." && pwd)
REPO_ROOT=${GRAF_RELEASE_REPO_ROOT:-$DEFAULT_REPO_ROOT}

# Every path below is derived from the selected repository root, so --repo-root
# and GRAF_RELEASE_REPO_ROOT run the release of that checkout even when this
# script itself lives in a worktree.
BUILDER=
ARTIFACTS=
UPDATE_SIGNER=
VERIFY_CUSTODY=
FEED_VERIFIER=
MACOS_DIR=

derive_paths() {
  MACOS_DIR="$REPO_ROOT/apps/macos"
  BUILDER="$MACOS_DIR/Installer/Scripts/build-local-installer.sh"
  ARTIFACTS="$MACOS_DIR/Installer/Scripts/release-artifacts.py"
  UPDATE_SIGNER="$MACOS_DIR/Installer/Scripts/sign-graf-app-update-local.sh"
  VERIFY_CUSTODY="$MACOS_DIR/Installer/Scripts/verify-release-signing-custody.sh"
  FEED_VERIFIER="$MACOS_DIR/Scripts/validate-app-updates.sh"
}

FEED_URL_DEFAULT="https://rec.2brain.pro/static/public/downloads/graf-appcast.xml"

PHASE=all
VERSION=${GRAF_VERSION:-}
PREVIOUS_TAG=
PREVIOUS_APP_ASSET=
CANDIDATE_APP_ASSET=
NOTES_ASSET=
NOTES_FILE=
PKG_PATH=
NOTARY_PROFILE=${GRAF_NOTARY_PROFILE:-graf-notary}
FEED_URL=${GRAF_UPDATE_FEED_URL:-$FEED_URL_DEFAULT}
DRY_RUN=0
VERIFY_FEED_VERSION=
APP_SIGN_IDENTITY=${GRAF_APP_SIGN_IDENTITY:-}
INSTALLER_IDENTITY=${DEVELOPER_ID_INSTALLER_IDENTITY:-}

usage() {
  cat >&2 <<'EOF'
usage: release-app-update.sh --version YYYY.MM.DD.N [options]

One command for the local public macOS app update release. It produces and
uploads draft release assets only; the outer release driver publishes the signed
archive and appcast atomically after deployment.

  --version V            CalVer release version without the leading v. Required.
  --phase P              prepare | publish | all. Default all.
                           prepare  build + notarize + staple + trust gates
                           publish  Sparkle signature + draft asset upload
  --previous-tag T       Last tag that published an app update, vYYYY.MM.DD.N.
                         Default: derived from the newest release that carries
                         GRAF-<version>.zip. Only needed by publish.
  --previous-app-asset N Predecessor app ZIP asset name. Default: derived.
  --candidate-app-asset N
                         Candidate app ZIP asset name in the draft release.
                         Default: GRAF-<version>-candidate.zip
  --release-notes-asset N
                         Release notes asset name in the draft release.
                         Default: release-notes-v<version>.md
  --notes-file PATH      Russian release notes used to create the draft release
                         when --release-notes-asset does not exist yet.
  --pkg PATH             Output package path. Default: the canonical release
                         path apps/macos/.build/release/GRAF-<version>.pkg
  --notary-profile P     Keychain profile for notarytool. Default: graf-notary
  --feed-url URL         Sparkle feed URL. Default: the canonical public feed.
  --app-sign-identity S  Developer ID Application identity. Default: discovered.
  --installer-identity S Developer ID Installer identity. Default: discovered.
  --verify-feed V        Also assert that the live feed already offers V.
  --repo-root PATH       Repository root. Default: this checkout.
  --dry-run              Check prerequisites and print the plan. No build, no
                         Apple call, no upload, no draft release creation.
  -h, --help             Show this help.

Exit codes: 0 success, 1 release failure, 64 usage error.
EOF
}

log() {
  printf '%s\n' "$*" >&2
}

fail() {
  printf 'release-app-update: %s\n' "$*" >&2
  exit 1
}

usage_error() {
  printf 'release-app-update: %s\n' "$*" >&2
  usage
  exit 64
}

# --- measured phase timing ---------------------------------------------------
# Real measured durations per phase, printed as one summary at the end. Nothing
# here influences release decisions; it exists so a slow phase is visible
# instead of guessed. A phase entered twice accumulates instead of overwriting.
TIMING_NAMES=
TIMING_VALUES=
TIMING_ACTIVE=
TIMING_STARTED=0

timing_begin() {
  TIMING_ACTIVE=$1
  TIMING_STARTED=$(date +%s)
  log "== phase $1 =="
}

timing_end() {
  [ -n "$TIMING_ACTIVE" ] || return 0
  ended=$(date +%s)
  elapsed=$((ended - TIMING_STARTED))
  index=1
  count=$(printf '%s' "$TIMING_NAMES" | grep -c . || true)
  found=0
  while [ "$index" -le "$count" ]; do
    if [ "$(printf '%s' "$TIMING_NAMES" | sed -n "${index}p")" = "$TIMING_ACTIVE" ]; then
      previous=$(printf '%s' "$TIMING_VALUES" | sed -n "${index}p")
      TIMING_VALUES=$(printf '%s' "$TIMING_VALUES" | awk -v i="$index" -v v="$((previous + elapsed))" \
        'NR == i { print v; next } { print }')
      found=1
      break
    fi
    index=$((index + 1))
  done
  if [ "$found" = 0 ]; then
    TIMING_NAMES="$TIMING_NAMES$TIMING_ACTIVE
"
    TIMING_VALUES="$TIMING_VALUES$elapsed
"
  fi
  TIMING_ACTIVE=
}

timing_report() {
  timing_end
  printf '\n=== app release timings (seconds, measured on this machine) ===\n'
  total=0
  index=1
  count=$(printf '%s' "$TIMING_NAMES" | grep -c . || true)
  while [ "$index" -le "$count" ]; do
    name=$(printf '%s' "$TIMING_NAMES" | sed -n "${index}p")
    value=$(printf '%s' "$TIMING_VALUES" | sed -n "${index}p")
    total=$((total + value))
    printf '%-24s %6s\n' "$name" "$value"
    index=$((index + 1))
  done
  printf '%-24s %6s\n' "TOTAL" "$total"
  printf 'note: the Apple notarization row is external waiting, not local work.\n'
}

# --- argument parsing --------------------------------------------------------
while [ "$#" -gt 0 ]; do
  case "$1" in
    --version) shift; [ "$#" -gt 0 ] || usage_error "--version needs a value"; VERSION=$1 ;;
    --phase) shift; [ "$#" -gt 0 ] || usage_error "--phase needs a value"; PHASE=$1 ;;
    --previous-tag) shift; [ "$#" -gt 0 ] || usage_error "--previous-tag needs a value"; PREVIOUS_TAG=$1 ;;
    --previous-app-asset) shift; [ "$#" -gt 0 ] || usage_error "--previous-app-asset needs a value"; PREVIOUS_APP_ASSET=$1 ;;
    --candidate-app-asset) shift; [ "$#" -gt 0 ] || usage_error "--candidate-app-asset needs a value"; CANDIDATE_APP_ASSET=$1 ;;
    --release-notes-asset) shift; [ "$#" -gt 0 ] || usage_error "--release-notes-asset needs a value"; NOTES_ASSET=$1 ;;
    --notes-file) shift; [ "$#" -gt 0 ] || usage_error "--notes-file needs a value"; NOTES_FILE=$1 ;;
    --pkg) shift; [ "$#" -gt 0 ] || usage_error "--pkg needs a value"; PKG_PATH=$1 ;;
    --notary-profile) shift; [ "$#" -gt 0 ] || usage_error "--notary-profile needs a value"; NOTARY_PROFILE=$1 ;;
    --feed-url) shift; [ "$#" -gt 0 ] || usage_error "--feed-url needs a value"; FEED_URL=$1 ;;
    --app-sign-identity) shift; [ "$#" -gt 0 ] || usage_error "--app-sign-identity needs a value"; APP_SIGN_IDENTITY=$1 ;;
    --installer-identity) shift; [ "$#" -gt 0 ] || usage_error "--installer-identity needs a value"; INSTALLER_IDENTITY=$1 ;;
    --verify-feed) shift; [ "$#" -gt 0 ] || usage_error "--verify-feed needs a value"; VERIFY_FEED_VERSION=$1 ;;
    --repo-root) shift; [ "$#" -gt 0 ] || usage_error "--repo-root needs a value"; REPO_ROOT=$1 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) usage_error "unknown argument: $1" ;;
  esac
  shift
done

case "$PHASE" in
  prepare|publish|all) ;;
  *) usage_error "--phase must be prepare, publish or all" ;;
esac

# TMPDIR already ends with a separator on macOS; strip it so paths stay single-slashed.
DEFAULT_PKG_PATH="${TMPDIR:-/tmp}"
DEFAULT_PKG_PATH=${DEFAULT_PKG_PATH%/}/GRAF-$VERSION.pkg

if [ -z "$VERSION" ]; then
  [ "$DRY_RUN" = 1 ] || usage_error "--version YYYY.MM.DD.N is required"
  VERSION=YYYY.MM.DD.N
fi

# --- prerequisite checks -----------------------------------------------------
# Every check below already exists in the release path. They run first so a
# missing credential or identity stops the release in seconds instead of after
# a ten-minute build.
PREREQUISITE_FAILURES=

require_command() {
  command -v "$1" >/dev/null 2>&1 || PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
missing command: $1"
}

require_file() {
  [ -f "$1" ] || PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
missing file: $1"
}

require_executable() {
  [ -x "$1" ] || PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
missing or not executable: $1"
}

check_calver() {
  printf '%s\n' "$1" | grep -Eq '^[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[1-9][0-9]*$'
}

check_identities() {
  identities=$(security find-identity -v 2>/dev/null || true)
  if [ -z "$APP_SIGN_IDENTITY" ]; then
    APP_SIGN_IDENTITY=$(printf '%s\n' "$identities" |
      sed -n 's/.*"\(Developer ID Application: [^"]*\)".*/\1/p' | head -n 1)
  fi
  if [ -z "$INSTALLER_IDENTITY" ]; then
    INSTALLER_IDENTITY=$(printf '%s\n' "$identities" |
      sed -n 's/.*"\(Developer ID Installer: [^"]*\)".*/\1/p' | head -n 1)
  fi
  case "$APP_SIGN_IDENTITY" in
    "Developer ID Application:"*) ;;
    *) PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
no Developer ID Application identity in the login Keychain" ;;
  esac
  case "$INSTALLER_IDENTITY" in
    "Developer ID Installer:"*) ;;
    *) PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
no Developer ID Installer identity in the login Keychain" ;;
  esac
}

check_notary_profile() {
  # Missing Apple credentials are a publication stop, not a retry.
  xcrun notarytool history --keychain-profile "$NOTARY_PROFILE" >/dev/null 2>&1 ||
    PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
notarytool Keychain profile is unusable: $NOTARY_PROFILE"
}

check_clean_exact_source() {
  dirty=$(git -C "$REPO_ROOT" status --porcelain --untracked-files=all 2>/dev/null || true)
  [ -z "$dirty" ] ||
    PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
release requires a clean worktree; commit or stash first"
  SOURCE_SHA=$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || true)
  case "$SOURCE_SHA" in
    [0-9a-f][0-9a-f][0-9a-f][0-9a-f]*) ;;
    *) PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
cannot resolve HEAD in $REPO_ROOT" ;;
  esac
}

check_published_tag() {
  # The Sparkle signer fails closed unless HEAD equals the published tag and
  # origin/master. Check it here too so a forgotten push is reported in seconds.
  tag="v$VERSION"
  local_tag=$(git -C "$REPO_ROOT" rev-parse "refs/tags/$tag^{}" 2>/dev/null || true)
  if [ -z "$local_tag" ]; then
    PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
tag $tag does not exist locally"
    return 0
  fi
  [ "$local_tag" = "$SOURCE_SHA" ] ||
    PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
tag $tag does not point at HEAD"
  remote_tag=$(git -C "$REPO_ROOT" ls-remote origin "refs/tags/$tag^{}" "refs/tags/$tag" 2>/dev/null |
    awk '$2 ~ /\^\{\}$/ { peeled = $1 } NR == 1 { direct = $1 } END { if (peeled != "") print peeled; else print direct }')
  [ "$remote_tag" = "$SOURCE_SHA" ] ||
    PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
tag $tag is not published at HEAD on origin"
  remote_master=$(git -C "$REPO_ROOT" ls-remote origin refs/heads/master 2>/dev/null | awk 'NR == 1 { print $1 }')
  [ "$remote_master" = "$SOURCE_SHA" ] ||
    PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
HEAD is not the current origin/master"
}

check_draft_release() {
  draft=$(gh --repo "$TARGET_REPO" release view "v$VERSION" --json isDraft --jq .isDraft 2>/dev/null || true)
  if [ -z "$draft" ]; then
    # A missing draft is recoverable: ensure_draft_release creates it from
    # --notes-file. Report the requirement instead of blocking the phase.
    log "note: draft GitHub Release v$VERSION does not exist yet; it will be created"
  elif [ "$draft" != "true" ]; then
    PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
GitHub Release v$VERSION is already published; the update signer requires a draft"
  fi
}

check_sparkle_tools() {
  sparkle_bin="$MACOS_DIR/.build/artifacts/sparkle/Sparkle/bin"
  for tool in generate_appcast generate_keys sign_update; do
    [ -x "$sparkle_bin/$tool" ] ||
      PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
pinned Sparkle tool is missing: $sparkle_bin/$tool"
  done
}

check_tooling() {
  for tool in python3 shasum ditto lipo otool codesign pkgbuild productbuild \
              spctl xcrun xmllint unzip zipinfo curl awk sed; do
    require_command "$tool"
  done
  require_command swift
  require_command git
  [ "$PHASE" = prepare ] || require_command gh
  require_executable "$BUILDER"
  # release-artifacts.py is invoked explicitly through python3 and is tracked
  # without the executable bit, so only its presence is required here.
  require_file "$ARTIFACTS"
  require_executable "$UPDATE_SIGNER"
  require_executable "$VERIFY_CUSTODY"
  require_executable "$FEED_VERIFIER"
  # The check below must resolve against a known root, so establish that first.
  [ -n "$REPO_ROOT" ] || PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
cannot determine the repository root"
  require_file "$REPO_ROOT/apps/macos/Installer/UpdateSigningKey.json"
}

resolve_repo() {
  origin=$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)
  case "$origin" in
    git@github.com:*) TARGET_REPO=${origin#git@github.com:} ;;
    https://github.com/*) TARGET_REPO=${origin#https://github.com/} ;;
    ssh://git@github.com/*) TARGET_REPO=${origin#ssh://git@github.com/} ;;
    *) TARGET_REPO= ;;
  esac
  TARGET_REPO=${TARGET_REPO%.git}
}

run_prerequisites() {
  resolve_repo
  check_tooling
  # Resolve the signing identities even for a dry run so the printed plan names
  # the identities the release would actually use.
  check_identities
  if [ "$DRY_RUN" = 1 ]; then
    # A dry run reports what is missing through the plan instead of failing, so
    # an operator can see every gap at once before starting a real release.
    PREREQUISITE_FAILURES=
    return 0
  fi
  check_calver "$VERSION" || PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
--version must be CalVer YYYY.MM.DD.N with N >= 1"
  check_clean_exact_source
  check_sparkle_tools
  case "$PHASE" in
    prepare|all) check_notary_profile ;;
  esac
  case "$PHASE" in
    publish|all)
      [ -n "$TARGET_REPO" ] ||
        PREREQUISITE_FAILURES="$PREREQUISITE_FAILURES
origin must be a github.com repository"
      check_draft_release
      ;;
  esac
  # --phase all starts before the release tag exists, so its tag check runs
  # between prepare and publish instead of here. --phase publish is a resumed
  # run and must already have the published tag.
  case "$PHASE" in
    publish) check_published_tag ;;
  esac
}

report_prerequisites() {
  if [ -n "$PREREQUISITE_FAILURES" ]; then
    printf 'release-app-update: prerequisites failed:%s\n' "$PREREQUISITE_FAILURES" >&2
    exit 1
  fi
}

# --- prepare phase -----------------------------------------------------------
# Order is fixed by the trust model: build and sign, submit both notary inputs,
# wait once, then staple copies and prove Gatekeeper acceptance. Nothing here
# may be reordered or skipped.
run_prepare() {
  # The default output lives outside the checkout on purpose: an untracked
  # package inside the repository would make the exact-source guard fail on the
  # next notary or Sparkle step.
  [ -n "$PKG_PATH" ] || PKG_PATH="$DEFAULT_PKG_PATH"
  mkdir -p "$(dirname -- "$PKG_PATH")"
  timing_begin "build_and_sign"
  GRAF_VERSION="$VERSION" \
  GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1 \
  GRAF_UPDATE_FEED_URL="$FEED_URL" \
  GRAF_APP_SIGN_IDENTITY="$APP_SIGN_IDENTITY" \
  DEVELOPER_ID_INSTALLER_IDENTITY="$INSTALLER_IDENTITY" \
    sh "$BUILDER" "$PKG_PATH" >/dev/null
  timing_end

  timing_begin "notarize_wait_apple"
  # External Apple waiting. This is the row that must overlap the server train,
  # never extend it. The helper submits ZIP and PKG before waiting, keeps both
  # request IDs, and is resumable.
  python3 "$ARTIFACTS" notarize \
    --app "$MACOS_DIR/RecApp/.build/GRAF.app" \
    --pkg "$PKG_PATH" \
    --profile "$NOTARY_PROFILE"
  timing_end

  NOTARY_DIR="$MACOS_DIR/.build/notary/$VERSION-$SOURCE_SHA"
  FINAL_DIR="$NOTARY_DIR/final"
  FINAL_APP="$FINAL_DIR/GRAF.app"
  FINAL_PKG="$FINAL_DIR/GRAF-$VERSION.pkg"
  FINAL_CANDIDATE_ZIP="$FINAL_DIR/GRAF-$VERSION-candidate.zip"
  for artifact in "$FINAL_APP" "$FINAL_PKG" "$FINAL_CANDIDATE_ZIP"; do
    [ -e "$artifact" ] || fail "notarization did not produce $artifact"
  done

  timing_begin "trust_gates"
  # Mandatory before publication. The notary helper already ran these; repeating
  # them here is deliberate: this is the last point that can stop a release, and
  # a resumed run must re-prove the retained artifacts rather than trust a
  # receipt written by an earlier process.
  codesign --verify --deep --strict "$FINAL_APP" ||
    fail "stapled app failed codesign verification"
  xcrun stapler validate "$FINAL_APP" || fail "stapled app failed stapler validation"
  spctl --assess --type execute --verbose=4 "$FINAL_APP" ||
    fail "stapled app failed Gatekeeper assessment"
  xcrun stapler validate "$FINAL_PKG" || fail "stapled package failed stapler validation"
  spctl --assess --type install --verbose=4 "$FINAL_PKG" ||
    fail "stapled package failed Gatekeeper assessment"
  signature=$(codesign -dv --verbose=4 "$FINAL_APP" 2>&1)
  printf '%s\n' "$signature" | grep -q '^Authority=Developer ID Application:' ||
    fail "stapled app is not signed with a Developer ID Application identity"
  pkg_signature=$(pkgutil --check-signature "$FINAL_PKG") ||
    fail "stapled package signature is unreadable"
  printf '%s\n' "$pkg_signature" | grep -q 'Developer ID Installer:' ||
    fail "stapled package is not signed with a Developer ID Installer identity"
  timing_end

  # Record the handoff for --phase publish. The notary state is keyed by version
  # and built source, so a resumed publish must not have to guess either one;
  # the receipt written by the builder binds the package to the same commit.
  STATE_DIR="$MACOS_DIR/.build/release-state"
  mkdir -p "$STATE_DIR"
  printf 'version=%s\nsource=%s\npkg=%s\nnotary_dir=%s\n' \
    "$VERSION" "$SOURCE_SHA" "$PKG_PATH" "$NOTARY_DIR" > "$STATE_DIR/$VERSION.handoff"
  python3 "$ARTIFACTS" receipt-source "$PKG_PATH" >/dev/null 2>&1 ||
    fail "the build did not record a receipt binding this package to its source"

  printf '\nprepared_app=%s\nprepared_pkg=%s\nprepared_candidate_zip=%s\nsource=%s\npublished=no\n' \
    "$FINAL_APP" "$FINAL_PKG" "$FINAL_CANDIDATE_ZIP" "$SOURCE_SHA"
}

# --- publish phase -----------------------------------------------------------
# The Sparkle signer re-verifies the whole chain itself: named Keychain signer,
# metadata-only attestation, both app signatures, safe extraction, pinned
# Sparkle tools, and the public trust validator. This phase adds the pieces that
# are easy to forget by hand: deriving the predecessor release, creating the
# draft with the candidate asset, and checking the live feed afterwards.
resolve_previous_release() {
  if [ -n "$PREVIOUS_TAG" ] && [ -n "$PREVIOUS_APP_ASSET" ]; then
    return 0
  fi
  derived=$(python3 "$ARTIFACTS" latest-app-release --repo "$TARGET_REPO" --before "v$VERSION") ||
    fail "could not derive the predecessor app release; pass --previous-tag"
  [ -n "$derived" ] ||
    fail "no earlier release publishes an app update; pass --previous-tag"
  previous_tag=$(printf '%s' "$derived" | sed -n 's/^tag=//p')
  previous_asset=$(printf '%s' "$derived" | sed -n 's/^asset=//p')
  [ -n "$PREVIOUS_TAG" ] || PREVIOUS_TAG=$previous_tag
  [ -n "$PREVIOUS_APP_ASSET" ] || PREVIOUS_APP_ASSET=$previous_asset
  [ -n "$PREVIOUS_TAG" ] && [ -n "$PREVIOUS_APP_ASSET" ] ||
    fail "could not derive the predecessor app release; pass --previous-tag"
}

ensure_draft_release() {
  draft=$(gh --repo "$TARGET_REPO" release view "v$VERSION" --json isDraft --jq .isDraft 2>/dev/null || true)
  if [ -n "$draft" ]; then
    [ "$draft" = "true" ] ||
      fail "GitHub Release v$VERSION is already published; the update signer requires a draft"
    return 0
  fi
  [ -n "$NOTES_FILE" ] ||
    fail "draft GitHub Release v$VERSION is missing; create it or pass --notes-file"
  [ -f "$NOTES_FILE" ] || fail "--notes-file does not exist: $NOTES_FILE"
  [ -n "$CANDIDATE_APP_ASSET" ] ||
    fail "--candidate-app-asset is required to create the draft release"
  [ -n "$NOTES_ASSET" ] || fail "--release-notes-asset is required to create the draft release"
  log "creating draft GitHub Release v$VERSION"
  gh --repo "$TARGET_REPO" release create "v$VERSION" --draft \
    --title "v$VERSION" --notes-file "$NOTES_FILE" >/dev/null ||
    fail "could not create the draft GitHub Release"
  gh --repo "$TARGET_REPO" release upload "v$VERSION" "$NOTES_FILE#$NOTES_ASSET" >/dev/null ||
    fail "could not upload the release notes asset"
}

run_publish() {
  [ -n "$CANDIDATE_APP_ASSET" ] || CANDIDATE_APP_ASSET="GRAF-$VERSION-candidate.zip"
  [ -n "$NOTES_ASSET" ] || NOTES_ASSET="release-notes-v$VERSION.md"
  # Bind publication to the commit that was actually built. A resumed publish
  # must not follow a newer HEAD: the notary attempt is keyed by the built
  # source, and the signer independently requires that same commit to be the
  # published tag and origin/master.
  STATE_DIR="$MACOS_DIR/.build/release-state"
  HANDOFF="$STATE_DIR/$VERSION.handoff"
  if [ -f "$HANDOFF" ]; then
    SOURCE_SHA=$(sed -n 's/^source=//p' "$HANDOFF")
    HANDOFF_PKG=$(sed -n 's/^pkg=//p' "$HANDOFF")
    [ -n "$PKG_PATH" ] || PKG_PATH=$HANDOFF_PKG
  fi
  [ -n "$SOURCE_SHA" ] ||
    fail "no prepare handoff for $VERSION; run --phase prepare first"
  [ -n "$PKG_PATH" ] || PKG_PATH="$DEFAULT_PKG_PATH"
  # The receipt is the authoritative binding, so re-read the source from it and
  # never trust a stale handoff file over the package that is about to ship.
  RECEIPT_SOURCE=$(python3 "$ARTIFACTS" receipt-source "$PKG_PATH" 2>/dev/null || true)
  [ -n "$RECEIPT_SOURCE" ] ||
    fail "build receipt is missing at $PKG_PATH.build.json; run --phase prepare first"
  [ "$RECEIPT_SOURCE" = "$SOURCE_SHA" ] ||
    fail "the build receipt and the prepare handoff name different source commits"
  NOTARY_DIR="$MACOS_DIR/.build/notary/$VERSION-$SOURCE_SHA"
  FINAL_DIR="$NOTARY_DIR/final"
  FINAL_APP="$FINAL_DIR/GRAF.app"
  FINAL_PKG="$FINAL_DIR/GRAF-$VERSION.pkg"
  [ -d "$FINAL_APP" ] ||
    fail "stapled app is missing at $FINAL_APP; run --phase prepare for $VERSION first"
  [ -f "$FINAL_PKG" ] ||
    fail "stapled package is missing at $FINAL_PKG; run --phase prepare for $VERSION first"

  timing_begin "trust_gates"
  codesign --verify --deep --strict "$FINAL_APP" || fail "stapled app failed codesign verification"
  xcrun stapler validate "$FINAL_APP" || fail "stapled app failed stapler validation"
  spctl --assess --type execute --verbose=4 "$FINAL_APP" ||
    fail "stapled app failed Gatekeeper assessment"
  xcrun stapler validate "$FINAL_PKG" || fail "stapled package failed stapler validation"
  spctl --assess --type install --verbose=4 "$FINAL_PKG" ||
    fail "stapled package failed Gatekeeper assessment"
  timing_end

  timing_begin "predecessor_lookup"
  resolve_previous_release
  timing_end

  timing_begin "draft_release"
  ensure_draft_release
  # The predecessor app ZIP is a signing input and is already a published asset
  # of the predecessor release, so it is read from there, never re-uploaded.
  python3 "$ARTIFACTS" cache-inputs --repo "$TARGET_REPO" \
    --tag "v$VERSION" --source "$SOURCE_SHA" \
    --previous-tag "$PREVIOUS_TAG" --previous-source "$(git -C "$REPO_ROOT" rev-parse "refs/tags/$PREVIOUS_TAG^{}")" \
    --candidate "$CANDIDATE_APP_ASSET" --previous "$PREVIOUS_APP_ASSET" --notes "$NOTES_ASSET" \
    --output "$MACOS_DIR/.build/release-staging-inputs-$VERSION" >/dev/null ||
    fail "release inputs are not ready; check the candidate and predecessor assets"
  timing_end

  timing_begin "sparkle_sign_and_upload"
  # This is the single publication step. It signs the archive and appcast with
  # the named Keychain signer, re-verifies public trust and both architecture
  # startup checks, then uploads the four prepared assets to the draft release
  # only. It never touches the production feed.
  sh "$UPDATE_SIGNER" \
    --release-tag "v$VERSION" \
    --previous-tag "$PREVIOUS_TAG" \
    --candidate-app-asset "$CANDIDATE_APP_ASSET" \
    --previous-app-asset "$PREVIOUS_APP_ASSET" \
    --release-notes-asset "$NOTES_ASSET"
  timing_end

  timing_begin "feed_check"
  if [ -n "$VERIFY_FEED_VERSION" ]; then
    verify_live_feed "$VERIFY_FEED_VERSION"
  fi
  timing_end

  printf '\nrelease_tag=v%s\nprevious_tag=%s\nsource=%s\ndraft_assets_uploaded=yes\nproduction_feed=awaiting_outer_release_driver\n' \
    "$VERSION" "$PREVIOUS_TAG" "$SOURCE_SHA"
  printf 'next_step=release.sh publishes the archive first and replaces graf-appcast.xml last\n'
  printf 'check=release-app-update.sh --version %s --phase publish --verify-feed %s\n' \
    "$VERSION" "$VERSION"
}

# --- live feed check ---------------------------------------------------------
# The mandatory closeout check: the published feed must already serve the new
# version. Runs only when asked, so it never becomes an implicit publication.
verify_live_feed() {
  expected=$1
  [ "$expected" = "$VERSION" ] || [ -n "$expected" ] || fail "--verify-feed needs a version"
  feed=$(curl -fsS --connect-timeout 10 --max-time 60 --retry 2 --retry-delay 1 "$FEED_URL") ||
    fail "the live update feed is unreachable: $FEED_URL"
  printf '%s' "$feed" | xmllint --noout - 2>/dev/null ||
    fail "the live update feed is not well-formed XML"
  versions=$(printf '%s' "$feed" |
    xmllint --xpath "//*[local-name()='item']/*[local-name()='version']/text()" - 2>/dev/null || true)
  [ -n "$versions" ] || fail "the live update feed contains no version item"
  highest=
  for version in $versions; do
    if [ -z "$highest" ] || [ "$(printf '%s\n%s\n' "$highest" "$version" | sort -V | tail -n 1)" = "$version" ]; then
      highest=$version
    fi
  done
  [ "$highest" = "$expected" ] ||
    fail "the live feed offers $highest, not the requested $expected"
  archive_url=$(printf '%s' "$feed" | xmllint --xpath \
    "string((//*[local-name()='item' and *[local-name()='version' and normalize-space(text())='$expected']]/*[local-name()='enclosure'])/@url)" - 2>/dev/null || true)
  case "$archive_url" in
    https://*) ;;
    *) fail "the live feed item for $expected has no HTTPS archive URL" ;;
  esac
  status=$(curl -fsS -o /dev/null -w '%{http_code}' --connect-timeout 10 --max-time 60 -I "$archive_url" 2>/dev/null || true)
  [ "$status" = "200" ] ||
    fail "the feed archive for $expected is not reachable: HTTP $status"
  printf 'live_feed=pass version=%s archive_http=200 url=%s\n' "$expected" "$archive_url"
}

# --- dry run -----------------------------------------------------------------
print_plan() {
  cat <<EOF
release-app-update plan (dry run, nothing executed)
  repository root        $REPO_ROOT
  github repository      ${TARGET_REPO:-<unresolved>}
  version                $VERSION
  phase                  $PHASE
  app sign identity      ${APP_SIGN_IDENTITY:-<none found>}
  installer identity     ${INSTALLER_IDENTITY:-<none found>}
  notary profile         $NOTARY_PROFILE
  feed url               $FEED_URL
  package output         ${PKG_PATH:-$DEFAULT_PKG_PATH}

steps
  1. build_and_sign          Developer ID Application + Developer ID Installer, universal, exact source
  2. notarize_wait_apple     submit ZIP and PKG, then one bounded wait for both Apple requests
  3. staple_and_trust_gates  stapler + spctl for app and package, Developer ID assertions
  4. predecessor_lookup      last release that published GRAF-<version>.zip
  5. draft_release           create the draft release and cache the signing inputs
  6. sparkle_sign_and_upload Sparkle Keychain signature, public trust, both architecture startup checks
  7. feed_check              only with --verify-feed; asserts the live feed already serves the version
  never                      replace the public appcast; that stays a separate owner action

overlap
  --phase prepare needs only the clean frozen commit, so run it while the server
  release train is still running. --phase publish needs the published tag and
  runs afterwards. The Apple wait is inside prepare and does not extend the
  server train.
EOF
}

# --- main --------------------------------------------------------------------
derive_paths
if [ "$DRY_RUN" = 0 ] && [ -z "$REPO_ROOT" ]; then
  fail "cannot determine the repository root; pass --repo-root"
fi
[ -z "$REPO_ROOT" ] || cd "$REPO_ROOT"

run_prerequisites
report_prerequisites
SOURCE_SHA=$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || printf 'unknown')

if [ "$DRY_RUN" = 1 ]; then
  print_plan
  exit 0
fi

log "release-app-update: version=$VERSION phase=$PHASE source=$SOURCE_SHA"
case "$PHASE" in
  prepare) run_prepare ;;
  publish) run_publish ;;
  all)
    run_prepare
    # The build is done, so the commit and tag can be published now. The
    # Sparkle signer refuses to run without them, and this reports it here
    # instead of after the slow publish steps.
    PREREQUISITE_FAILURES=
    check_published_tag
    report_prerequisites
    run_publish
    ;;
esac
timing_report
