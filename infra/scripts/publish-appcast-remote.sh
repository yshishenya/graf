#!/usr/bin/env bash
# Publish one already signed Sparkle archive and appcast atomically.
#
# The versioned archive is installed first. The signed appcast is replaced last,
# and the old appcast is retained as a rollback copy. Any failure restores the
# previous appcast and removes an archive this attempt installed.
set -euo pipefail

VERSION=""
ARCHIVE=""
APPCAST=""
REMOTE_HOST="${GRAF_UPDATE_DEPLOY_HOST:-2brain.dev}"
REMOTE_PATH="${GRAF_UPDATE_DEPLOY_PATH:-/opt/projects/2brain-rec/infra/runtime/public-downloads}"
FEED_URL="${GRAF_UPDATE_FEED_URL:-https://rec.2brain.pro/static/public/downloads/graf-appcast.xml}"
SOURCE_SHA=""
DRY_RUN=0

usage() {
  cat >&2 <<'EOF'
usage: infra/scripts/publish-appcast-remote.sh --version YYYY.MM.DD.N \
  --archive GRAF-YYYY.MM.DD.N.zip --appcast graf-appcast.xml [options]

Publishes versioned Sparkle assets to the public download host. The archive is
installed before graf-appcast.xml; the previous appcast is retained and every
failed transaction is rolled back.

  --host HOST             SSH host (default: 2brain.dev)
  --remote-path PATH      Public directory on the host
  --feed-url URL          Expected public Sparkle feed URL
  --source-sha SHA        Source SHA printed in the receipt
  --dry-run               Validate local inputs and print the plan only
EOF
}

fail() {
  printf 'appcast_publish=blocked reason=%s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version) VERSION="${2:-}"; shift 2 ;;
    --archive) ARCHIVE="${2:-}"; shift 2 ;;
    --appcast) APPCAST="${2:-}"; shift 2 ;;
    --host) REMOTE_HOST="${2:-}"; shift 2 ;;
    --remote-path) REMOTE_PATH="${2:-}"; shift 2 ;;
    --feed-url) FEED_URL="${2:-}"; shift 2 ;;
    --source-sha) SOURCE_SHA="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage; exit 64 ;;
  esac
done

[[ "$VERSION" =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[1-9][0-9]*$ ]] || fail "invalid_version"
[[ -n "$ARCHIVE" && -f "$ARCHIVE" && ! -L "$ARCHIVE" ]] || fail "archive_missing"
[[ -n "$APPCAST" && -f "$APPCAST" && ! -L "$APPCAST" ]] || fail "appcast_missing"
[[ "$(basename "$ARCHIVE")" == "GRAF-${VERSION}.zip" ]] || fail "archive_name_mismatch"
[[ "$(basename "$APPCAST")" == "graf-appcast.xml" ]] || fail "appcast_name_mismatch"
if [[ -n "$SOURCE_SHA" && ! "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  fail "invalid_source_sha"
fi

archive_size() {
  if stat -f '%z' "$1" >/dev/null 2>&1; then
    stat -f '%z' "$1"
  else
    stat -c '%s' "$1"
  fi
}

archive_bytes="$(archive_size "$ARCHIVE")"
[[ "$archive_bytes" -gt 0 ]] || fail "archive_empty"

# Validate the signed feed before any network mutation. This deliberately checks
# only the release identity and enclosure binding; the macOS signer already ran
# the full Developer ID, Sparkle and trust validators before this handoff.
python3 - "$APPCAST" "$VERSION" "$archive_bytes" "$FEED_URL" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree

path, version, archive_bytes, feed_url = sys.argv[1:]
root = ElementTree.parse(path).getroot()
items = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "item"]
matching = []
for item in items:
    values = {
        child.tag.rsplit("}", 1)[-1]: (child.text or "").strip()
        for child in item
    }
    if values.get("version") == version:
        matching.append((item, values))
if len(matching) != 1:
    raise SystemExit(f"appcast must contain one item for {version}, found {len(matching)}")
item, values = matching[0]
enclosure = next((child for child in item if child.tag.rsplit("}", 1)[-1] == "enclosure"), None)
if enclosure is None:
    raise SystemExit("appcast item has no enclosure")
url = enclosure.attrib.get("url", "")
parsed = urlparse(url)
feed = urlparse(feed_url)
expected_name = f"GRAF-{version}.zip"
if parsed.scheme != "https" or parsed.netloc != feed.netloc or Path(parsed.path).name != expected_name:
    raise SystemExit("appcast enclosure is not the expected HTTPS public archive")
if enclosure.attrib.get("length") != archive_bytes:
    raise SystemExit("appcast enclosure length differs from the archive")
print(f"appcast_local_validation=pass version={version} archive_bytes={archive_bytes}")
PY

archive_sha="$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')"
appcast_sha="$(shasum -a 256 "$APPCAST" | awk '{print $1}')"

if [[ "$DRY_RUN" == "1" ]]; then
  printf 'appcast_publish=dry_run version=%s archive_bytes=%s archive_sha256=%s appcast_sha256=%s host=%s path=%s\n' \
    "$VERSION" "$archive_bytes" "$archive_sha" "$appcast_sha" "$REMOTE_HOST" "$REMOTE_PATH"
  exit 0
fi

staging=""
cleanup() {
  if [[ -n "$staging" ]]; then
    ssh -o BatchMode=yes -o ConnectTimeout=20 "$REMOTE_HOST" \
      "rm -rf -- $(printf '%q' "$staging")" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

staging="$(ssh -o BatchMode=yes -o ConnectTimeout=20 "$REMOTE_HOST" \
  'mktemp -d /tmp/graf-appcast-release.XXXXXX')"
[[ "$staging" == /tmp/graf-appcast-release.* ]] || fail "invalid_remote_staging_path"
scp -q -o BatchMode=yes -o ConnectTimeout=20 "$ARCHIVE" \
  "$REMOTE_HOST:$staging/GRAF-${VERSION}.zip"
scp -q -o BatchMode=yes -o ConnectTimeout=20 "$APPCAST" \
  "$REMOTE_HOST:$staging/graf-appcast.xml"

ssh -o BatchMode=yes -o ConnectTimeout=20 "$REMOTE_HOST" bash -s -- \
  "$REMOTE_PATH" "$VERSION" "GRAF-${VERSION}.zip" "$staging" <<'REMOTE'
set -euo pipefail

target_dir="$1"
version="$2"
archive_name="$3"
staging="$4"
archive_source="$staging/$archive_name"
appcast_source="$staging/graf-appcast.xml"
archive_target="$target_dir/$archive_name"
appcast_target="$target_dir/graf-appcast.xml"
archive_installed=0
appcast_updated=0
appcast_backup=""
transaction_ok=0

rollback() {
  status=$?
  if [[ "$transaction_ok" == "1" ]]; then
    exit "$status"
  fi
  set +e
  if [[ "$appcast_updated" == "1" ]]; then
    if [[ -n "$appcast_backup" && -f "$appcast_backup" ]]; then
      mv -- "$appcast_backup" "$appcast_target"
    else
      rm -f -- "$appcast_target"
    fi
  elif [[ -n "$appcast_backup" && -f "$appcast_backup" ]]; then
    rm -f -- "$appcast_backup"
  fi
  if [[ "$archive_installed" == "1" ]]; then
    rm -f -- "$archive_target"
  fi
  rm -rf -- "$staging"
  exit "$status"
}
trap rollback EXIT

[[ -d "$target_dir" && ! -L "$target_dir" ]] || {
  echo "appcast_publish=blocked reason=remote_directory_invalid" >&2
  exit 1
}
[[ -f "$archive_source" && -s "$archive_source" ]] || {
  echo "appcast_publish=blocked reason=staged_archive_missing" >&2
  exit 1
}
[[ -f "$appcast_source" && -s "$appcast_source" ]] || {
  echo "appcast_publish=blocked reason=staged_appcast_missing" >&2
  exit 1
}

if [[ -e "$archive_target" ]]; then
  [[ -f "$archive_target" && ! -L "$archive_target" ]] || {
    echo "appcast_publish=blocked reason=remote_archive_invalid" >&2
    exit 1
  }
  cmp -s "$archive_source" "$archive_target" || {
    echo "appcast_publish=blocked reason=remote_archive_conflict" >&2
    exit 1
  }
  echo "appcast_archive=already_present"
else
  archive_temporary="$(mktemp "$target_dir/.graf-archive-${version}.XXXXXX")"
  install -m 0644 "$archive_source" "$archive_temporary"
  cmp -s "$archive_source" "$archive_temporary"
  mv -- "$archive_temporary" "$archive_target"
  archive_installed=1
  echo "appcast_archive=installed"
fi

if [[ -f "$appcast_target" ]] && cmp -s "$appcast_source" "$appcast_target"; then
  echo "appcast_feed=already_present"
  transaction_ok=1
  rm -rf -- "$staging"
  exit 0
fi

if [[ -e "$appcast_target" ]]; then
  [[ -f "$appcast_target" && ! -L "$appcast_target" ]] || {
    echo "appcast_publish=blocked reason=remote_appcast_invalid" >&2
    exit 1
  }
  appcast_backup="$(mktemp "$target_dir/graf-appcast.xml.pre-v${version}-XXXXXX")"
  cp -p "$appcast_target" "$appcast_backup"
  cmp -s "$appcast_target" "$appcast_backup"
fi
appcast_temporary="$(mktemp "$target_dir/.graf-appcast-${version}.XXXXXX")"
install -m 0644 "$appcast_source" "$appcast_temporary"
cmp -s "$appcast_source" "$appcast_temporary"
mv -- "$appcast_temporary" "$appcast_target"
appcast_updated=1
cmp -s "$appcast_source" "$appcast_target"
transaction_ok=1
rm -rf -- "$staging"
echo "appcast_feed=installed"
echo "appcast_backup=${appcast_backup:-none}"
REMOTE

printf 'appcast_publish=pass version=%s archive_bytes=%s archive_sha256=%s appcast_sha256=%s host=%s path=%s\n' \
  "$VERSION" "$archive_bytes" "$archive_sha" "$appcast_sha" "$REMOTE_HOST" "$REMOTE_PATH"
