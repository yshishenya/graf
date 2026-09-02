#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
MACOS_DIR=$(CDPATH='' cd -- "$SCRIPT_DIR/../.." && pwd)
REPO_ROOT=$(git -C "$MACOS_DIR" rev-parse --show-toplevel)
cd "$REPO_ROOT"
PREPARE="$SCRIPT_DIR/prepare-app-update.sh"
VERIFIER="$SCRIPT_DIR/verify-release-signing-custody.sh"
STARTUP_VALIDATOR="$MACOS_DIR/Scripts/validate-packaged-app-launch.sh"
SPARKLE_DIR="$MACOS_DIR/.build/artifacts/sparkle/Sparkle"
SPARKLE_ARCHIVE_SHA256=cb6fdbdc8884f15d62a616e79face92b08322410fd2d425edc6596ccbf4ba3b0

fail() {
  echo "local app-update signing failed: $*" >&2
  exit 1
}

usage() {
  cat >&2 <<EOF
usage: $0 --release-tag vYYYY.MM.DD.N --previous-tag vYYYY.MM.DD.N \\
  --candidate-app-asset NAME.zip --previous-app-asset NAME.zip \\
  --release-notes-asset NAME.md
EOF
  exit 64
}

RELEASE_TAG=
PREVIOUS_TAG=
CANDIDATE_ASSET=
PREVIOUS_ASSET=
NOTES_ASSET=
while [ "$#" -gt 0 ]; do
  case "$1" in
    --release-tag) shift; [ "$#" -gt 0 ] || usage; RELEASE_TAG=$1 ;;
    --previous-tag) shift; [ "$#" -gt 0 ] || usage; PREVIOUS_TAG=$1 ;;
    --candidate-app-asset) shift; [ "$#" -gt 0 ] || usage; CANDIDATE_ASSET=$1 ;;
    --previous-app-asset) shift; [ "$#" -gt 0 ] || usage; PREVIOUS_ASSET=$1 ;;
    --release-notes-asset) shift; [ "$#" -gt 0 ] || usage; NOTES_ASSET=$1 ;;
    -h|--help) usage ;;
    *) usage ;;
  esac
  shift
done

printf '%s' "$RELEASE_TAG" | grep -Eq '^v[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$' || fail "invalid release tag"
printf '%s' "$PREVIOUS_TAG" | grep -Eq '^v[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$' || fail "invalid predecessor tag"
[ "$RELEASE_TAG" != "$PREVIOUS_TAG" ] || fail "release and predecessor tags must differ"
VERSION=${RELEASE_TAG#v}
for ASSET in "$CANDIDATE_ASSET" "$PREVIOUS_ASSET" "$NOTES_ASSET"; do
  case "$ASSET" in
    ''|.|..|*[!A-Za-z0-9._-]*) fail "invalid draft asset name" ;;
  esac
done
[ "$CANDIDATE_ASSET" != "$PREVIOUS_ASSET" ] || fail "candidate and predecessor assets must differ"
[ "$CANDIDATE_ASSET" != "$NOTES_ASSET" ] || fail "candidate and notes assets must differ"
[ "$PREVIOUS_ASSET" != "$NOTES_ASSET" ] || fail "predecessor and notes assets must differ"

command -v gh >/dev/null 2>&1 || fail "GitHub CLI is required for draft release assets"
ORIGIN_URL=$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)
case "$ORIGIN_URL" in
  git@github.com:*) TARGET_REPO=${ORIGIN_URL#git@github.com:} ;;
  https://github.com/*) TARGET_REPO=${ORIGIN_URL#https://github.com/} ;;
  ssh://git@github.com/*) TARGET_REPO=${ORIGIN_URL#ssh://git@github.com/} ;;
  *) fail "origin must be the configured github.com repository" ;;
esac
TARGET_REPO=${TARGET_REPO%.git}
printf '%s' "$TARGET_REPO" | grep -Eq '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$' ||
  fail "could not derive a safe GitHub repository from origin"
[ -z "${GH_REPO:-}" ] || [ "$GH_REPO" = "$TARGET_REPO" ] ||
  fail "GH_REPO does not match the repository origin"
[ -z "${GH_HOST:-}" ] || [ "$GH_HOST" = github.com ] ||
  fail "GH_HOST must remain github.com for the configured origin"
gh auth status --hostname github.com >/dev/null 2>&1 || fail "GitHub CLI is not authenticated"
[ -z "$(git -C "$REPO_ROOT" status --porcelain --untracked-files=all)" ] || fail "release signing requires a clean worktree"
git -C "$REPO_ROOT" fetch --force origin \
  "refs/tags/$RELEASE_TAG:refs/tags/$RELEASE_TAG" \
  "refs/tags/$PREVIOUS_TAG:refs/tags/$PREVIOUS_TAG"
HEAD_COMMIT=$(git -C "$REPO_ROOT" rev-parse HEAD)
TAG_COMMIT=$(git -C "$REPO_ROOT" rev-parse "refs/tags/$RELEASE_TAG^{}")
PREVIOUS_COMMIT=$(git -C "$REPO_ROOT" rev-parse "refs/tags/$PREVIOUS_TAG^{}")
MASTER_COMMIT=$(git -C "$REPO_ROOT" ls-remote origin refs/heads/master | awk 'NR == 1 { print $1 }')
[ -n "$MASTER_COMMIT" ] && [ "$HEAD_COMMIT" = "$TAG_COMMIT" ] && [ "$TAG_COMMIT" = "$MASTER_COMMIT" ] ||
  fail "HEAD, release tag and origin/master must match exactly"
git -C "$REPO_ROOT" merge-base --is-ancestor "$PREVIOUS_COMMIT" "$TAG_COMMIT" ||
  fail "predecessor tag must be an ancestor of the release tag"
PREVIOUS_VERSION=${PREVIOUS_TAG#v}
awk -v older="$PREVIOUS_VERSION" -v newer="$VERSION" '
  BEGIN {
    split(older, a, "."); split(newer, b, ".");
    for (i = 1; i <= 4; i++) {
      if ((a[i] + 0) < (b[i] + 0)) exit 0;
      if ((a[i] + 0) > (b[i] + 0)) exit 1;
    }
    exit 1
  }
' || fail "predecessor CalVer must be strictly older than the release tag"
[ "$(gh --repo "$TARGET_REPO" release view "$RELEASE_TAG" --json isDraft --jq .isDraft)" = "true" ] ||
  fail "target GitHub release must remain a draft"
LOCK_PARENT="$MACOS_DIR/.build"
mkdir -p "$LOCK_PARENT"
LOCK_DIR="$LOCK_PARENT/.graf-local-signing.lock"
LOCK_OWNED=0
WORK_ROOT=
INPUT_DIR=
APP_DIR=
ATTESTATION=
SPARKLE_BACKUP=
cleanup() {
  if [ -n "$SPARKLE_BACKUP" ] && { [ -e "$SPARKLE_BACKUP" ] || [ -L "$SPARKLE_BACKUP" ]; }; then
    rm -rf "$SPARKLE_DIR"
    mv "$SPARKLE_BACKUP" "$SPARKLE_DIR"
  elif [ -d "$SPARKLE_DIR" ] && [ -n "${SPARKLE_TOOLS_CREATED:-}" ]; then
    rm -rf "$SPARKLE_DIR"
  fi
  [ -z "$WORK_ROOT" ] || rm -rf "$WORK_ROOT"
  [ "$LOCK_OWNED" = 0 ] || rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap 'status=$?; trap - EXIT HUP INT TERM; cleanup; exit "$status"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  fail "another local draft-signing attempt is already in progress"
fi
LOCK_OWNED=1
WORK_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/graf-local-signing.XXXXXX")
INPUT_DIR="$WORK_ROOT/inputs"
APP_DIR="$WORK_ROOT/apps"
ATTESTATION="$WORK_ROOT/signing-attestation.json"
mkdir -p "$INPUT_DIR" "$APP_DIR/candidate" "$APP_DIR/previous"

gh --repo "$TARGET_REPO" release download "$RELEASE_TAG" --pattern "$CANDIDATE_ASSET" --dir "$INPUT_DIR"
gh --repo "$TARGET_REPO" release download "$PREVIOUS_TAG" --pattern "$PREVIOUS_ASSET" --dir "$INPUT_DIR"
gh --repo "$TARGET_REPO" release download "$RELEASE_TAG" --pattern "$NOTES_ASSET" --dir "$INPUT_DIR"
[ -f "$INPUT_DIR/$CANDIDATE_ASSET" ] && [ -f "$INPUT_DIR/$PREVIOUS_ASSET" ] && [ -f "$INPUT_DIR/$NOTES_ASSET" ] ||
  fail "required draft asset is missing"

extract_graf_app() {
  archive=$1
  destination=$2
  unzip -tq "$archive" >/dev/null || return 1
  archive_list=$(unzip -Z1 "$archive") || return 1
  printf '%s\n' "$archive_list" | grep -q '^GRAF.app/' || return 1
  if printf '%s\n' "$archive_list" | grep -Eq '(^/|(^|/)\.\.(/|$)|\\)'; then
    return 1
  fi
  if printf '%s\n' "$archive_list" | awk '
    $0 != "GRAF.app" && $0 !~ /^GRAF\.app\// && $0 != "__MACOSX" && $0 !~ /^__MACOSX\// { bad = 1 }
    END { exit bad }
  '; then :; else return 1; fi
  duplicate_paths=$(printf '%s\n' "$archive_list" | sort | uniq -d)
  [ -z "$duplicate_paths" ] || return 1
  if zipinfo -l "$archive" 2>/dev/null | awk 'NR > 3 && $1 ~ /^[sbcp]/ { bad = 1 } END { exit bad }'; then :; else return 1; fi
  validate_graf_archive_symlinks "$archive" || return 1
  ditto -x -k "$archive" "$destination"
  [ -d "$destination/GRAF.app" ] || return 1
  validate_graf_app_symlinks "$destination/GRAF.app"
}
expected_graf_app_symlinks() {
  cat <<'EOF'
Contents/Frameworks/Sparkle.framework/PrivateHeaders|Versions/Current/PrivateHeaders
Contents/Frameworks/Sparkle.framework/Resources|Versions/Current/Resources
Contents/Frameworks/Sparkle.framework/Versions/Current|B
Contents/Frameworks/Sparkle.framework/Autoupdate|Versions/Current/Autoupdate
Contents/Frameworks/Sparkle.framework/Updater.app|Versions/Current/Updater.app
Contents/Frameworks/Sparkle.framework/Headers|Versions/Current/Headers
Contents/Frameworks/Sparkle.framework/XPCServices|Versions/Current/XPCServices
Contents/Frameworks/Sparkle.framework/Modules|Versions/Current/Modules
Contents/Frameworks/Sparkle.framework/Sparkle|Versions/Current/Sparkle
EOF
}
validate_graf_archive_symlinks() {
  archive=$1
  actual=$(zipinfo -l "$archive" 2>/dev/null | awk 'NR > 3 && $1 ~ /^l/ { print $NF }') || return 1
  expected_count=0
  while IFS='|' read -r relative target; do
    expected_count=$((expected_count + 1))
    path="GRAF.app/$relative"
    printf '%s\n' "$actual" | grep -Fxq "$path" || return 1
    [ "$(unzip -p "$archive" "$path")" = "$target" ] || return 1
  done <<EOF
$(expected_graf_app_symlinks)
EOF
  actual_count=$(printf '%s\n' "$actual" | grep -c . || true)
  [ "$actual_count" = "$expected_count" ]
}
validate_graf_app_symlinks() {
  app_root=$1
  expected_count=0
  while IFS='|' read -r relative target; do
    expected_count=$((expected_count + 1))
    link="$app_root/$relative"
    [ -L "$link" ] || return 1
    [ "$(readlink "$link")" = "$target" ] || return 1
  done <<EOF
$(expected_graf_app_symlinks)
EOF
  actual_count=$(find "$app_root" -type l -print | wc -l | tr -d ' ')
  [ "$actual_count" = "$expected_count" ]
}
validate_downloaded_app_signature() {
  app_bundle=$1
  previous_app_bundle=$2
  [ -d "$app_bundle" ] || fail "downloaded candidate app is missing"
  codesign --verify --deep --strict "$app_bundle" >/dev/null 2>&1 ||
    fail "downloaded candidate app signature is invalid"

  signature_info=$(codesign -dv --verbose=4 "$app_bundle" 2>&1) ||
    fail "downloaded candidate app signing identity is unavailable"
  printf '%s\n' "$signature_info" | grep -Eq '^Authority=Developer ID Application:' ||
    fail "downloaded candidate app must be signed with a Developer ID Application identity"
  team_identifier=$(printf '%s\n' "$signature_info" | sed -n 's/^TeamIdentifier=//p' | head -n 1)
  [ -n "$team_identifier" ] && [ "$team_identifier" != "not set" ] ||
    fail "downloaded candidate app signing team is unavailable"

  previous_requirement=$(codesign -dr - "$previous_app_bundle" 2>&1 |
    sed -n 's/^designated => //p' | head -n 1)
  [ -n "$previous_requirement" ] ||
    fail "predecessor app designated requirement is unavailable"
  codesign -R="$previous_requirement" --verify "$app_bundle" >/dev/null 2>&1 ||
    fail "downloaded candidate app does not satisfy the predecessor designated requirement"
}
extract_graf_app "$INPUT_DIR/$CANDIDATE_ASSET" "$APP_DIR/candidate" || fail "candidate asset is not a safe GRAF.app ZIP"
extract_graf_app "$INPUT_DIR/$PREVIOUS_ASSET" "$APP_DIR/previous" || fail "predecessor asset is not a safe GRAF.app ZIP"
[ -x "$STARTUP_VALIDATOR" ] || fail "packaged app launch validator is missing or not executable"
validate_downloaded_app_signature "$APP_DIR/candidate/GRAF.app" "$APP_DIR/previous/GRAF.app"
"$STARTUP_VALIDATOR" "$APP_DIR/candidate/GRAF.app" 5 arm64 || fail "candidate arm64 packaged app launch failed"
"$STARTUP_VALIDATOR" "$APP_DIR/candidate/GRAF.app" 5 x86_64 || fail "candidate x86_64 packaged app launch failed"

DOWNLOAD_DIR="$WORK_ROOT/sparkle"
ARCHIVE="$DOWNLOAD_DIR/Sparkle-for-Swift-Package-Manager.zip"
mkdir -p "$DOWNLOAD_DIR"
gh --repo sparkle-project/Sparkle release download 2.9.4 \
  --pattern Sparkle-for-Swift-Package-Manager.zip --dir "$DOWNLOAD_DIR"
printf '%s  %s\n' "$SPARKLE_ARCHIVE_SHA256" "$ARCHIVE" | shasum -a 256 -c -
SPARKLE_BACKUP="$WORK_ROOT/sparkle-existing"
if [ -e "$SPARKLE_DIR" ]; then mv "$SPARKLE_DIR" "$SPARKLE_BACKUP"; fi
mkdir -p "$SPARKLE_DIR"
SPARKLE_TOOLS_CREATED=1
ditto -x -k "$ARCHIVE" "$SPARKLE_DIR"
for tool in generate_keys generate_appcast sign_update; do
  [ -x "$SPARKLE_DIR/bin/$tool" ] || fail "verified Sparkle 2.9.4 artifact lacks $tool"
done

"$VERIFIER" \
  --app "$APP_DIR/candidate/GRAF.app" \
  --release-tag "$RELEASE_TAG" \
  --emit-keychain-attestation "$ATTESTATION"
FEED_URL=$(/usr/bin/plutil -extract SUFeedURL raw -o - "$APP_DIR/candidate/GRAF.app/Contents/Info.plist" 2>/dev/null || true)
case "$FEED_URL" in
  https://*/graf-appcast.xml) ;;
  *) fail "candidate app does not contain a valid trusted update feed" ;;
esac

GRAF_VERSION="$VERSION" \
GRAF_UPDATE_APP_BUNDLE="$APP_DIR/candidate/GRAF.app" \
GRAF_PREVIOUS_APP_BUNDLE="$APP_DIR/previous/GRAF.app" \
GRAF_UPDATE_RELEASE_NOTES="$INPUT_DIR/$NOTES_ASSET" \
GRAF_UPDATE_DOWNLOAD_BASE_URL="${FEED_URL%/graf-appcast.xml}" \
GRAF_RELEASE_SIGNING_MODE=keychain \
GRAF_RELEASE_SIGNING_KEYCHAIN_ATTESTATION="$ATTESTATION" \
GRAF_REQUIRE_RELEASE_PROVENANCE=1 \
  "$PREPARE"

OUTPUT_DIR="$MACOS_DIR/.build/updates"
ARCHIVE_NAME="GRAF-$VERSION.zip"
CHECKSUM="$OUTPUT_DIR/GRAF-$VERSION.sha256"
RELEASE_ATTESTATION="$OUTPUT_DIR/GRAF-$VERSION-signing-attestation.json"
[ -f "$OUTPUT_DIR/$ARCHIVE_NAME" ] && [ -f "$OUTPUT_DIR/graf-appcast.xml" ] ||
  fail "signing did not produce the required staged artifacts"
(
  cd "$OUTPUT_DIR"
  shasum -a 256 "$ARCHIVE_NAME" graf-appcast.xml > "$(basename -- "$CHECKSUM")"
)
/usr/bin/plutil -replace workflow -string sign-graf-app-update-local "$ATTESTATION"
cp "$ATTESTATION" "$RELEASE_ATTESTATION"
[ "$(gh --repo "$TARGET_REPO" release view "$RELEASE_TAG" --json isDraft --jq .isDraft)" = "true" ] ||
  fail "target GitHub release must remain a draft before upload"
gh --repo "$TARGET_REPO" release upload "$RELEASE_TAG" \
  "$OUTPUT_DIR/$ARCHIVE_NAME" \
  "$OUTPUT_DIR/graf-appcast.xml" \
  "$CHECKSUM" \
  "$RELEASE_ATTESTATION" \
  --clobber

trap - EXIT HUP INT TERM
cleanup
printf 'release=%s\ncommit=%s\nsigner=macos-keychain\nupload=draft-only\nproduction_feed=unchanged\n' "$RELEASE_TAG" "$HEAD_COMMIT"
