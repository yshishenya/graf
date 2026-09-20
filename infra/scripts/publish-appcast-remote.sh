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
REMOTE_HOST="${TWOBRAIN_DEPLOY_HOST:-${GRAF_UPDATE_DEPLOY_HOST:-2brain.dev}}"
REMOTE_ROOT="${TWOBRAIN_DEPLOY_PATH:-/opt/projects/2brain-rec}"
REMOTE_PUBLIC_DIR="${REMOTE_ROOT%/}/infra/runtime/public-downloads"
REMOTE_PATH="${GRAF_UPDATE_DEPLOY_PATH:-$REMOTE_PUBLIC_DIR}"
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

  --host HOST             SSH host (default: TWOBRAIN_DEPLOY_HOST/2brain.dev)
  --remote-path PATH      Public directory on the host (default: TWOBRAIN_DEPLOY_PATH/infra/runtime/public-downloads)
  --feed-url URL          Expected public Sparkle feed URL
  --source-sha SHA        Required exact source SHA bound to the signed assets
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
[[ -n "$SOURCE_SHA" ]] || fail "source_sha_required"
if [[ ! "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  fail "invalid_source_sha"
fi
[[ "$REMOTE_PUBLIC_DIR" == /* ]] || fail "remote_path_not_absolute"
case "$REMOTE_PUBLIC_DIR" in
  *[!A-Za-z0-9_./-]*|*..*|*/./*|*/../*) fail "remote_path_not_canonical" ;;
esac
[[ "$REMOTE_PATH" == "$REMOTE_PUBLIC_DIR" ]] || fail "remote_path_not_allowed"
[[ "$REMOTE_HOST" =~ ^[A-Za-z0-9][A-Za-z0-9_.@:-]*$ ]] || fail "remote_host_invalid"

archive_size() {
  LC_ALL=C wc -c <"$1" | tr -d '[:space:]'
}

archive_bytes="$(archive_size "$ARCHIVE")"
[[ "$archive_bytes" -gt 0 ]] || fail "archive_empty"

# Validate the signed feed and its immutable prepared inputs before any network
# mutation. The macOS signer already ran the full Developer ID, Sparkle and
# trust validators before this handoff; these files bind that result to this
# exact archive, appcast, release and source commit.
ARTIFACT_DIR="$(dirname "$ARCHIVE")"
CHECKSUM_FILE="$ARTIFACT_DIR/GRAF-${VERSION}.sha256"
ATTESTATION_FILE="$ARTIFACT_DIR/GRAF-${VERSION}-signing-attestation.json"
[[ -f "$CHECKSUM_FILE" && ! -L "$CHECKSUM_FILE" ]] || fail "checksum_missing"
[[ -f "$ATTESTATION_FILE" && ! -L "$ATTESTATION_FILE" ]] || fail "signing_attestation_missing"

local_appcast_signature="$(python3 - "$APPCAST" "$VERSION" "$archive_bytes" "$FEED_URL" <<'PY'
from __future__ import annotations

import sys
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
signature = next((value for key, value in enclosure.attrib.items() if key.rsplit("}", 1)[-1] == "edSignature"), "")
if not signature:
    raise SystemExit("appcast item has no Sparkle signature")
url = enclosure.attrib.get("url", "")
parsed = urlparse(url)
feed = urlparse(feed_url)
expected_name = f"GRAF-{version}.zip"
expected_path = feed.path.rsplit("/", 1)[0] + f"/{expected_name}"
if parsed.scheme != "https" or parsed.netloc != feed.netloc or parsed.path != expected_path:
    raise SystemExit("appcast enclosure is not the expected HTTPS public archive")
if enclosure.attrib.get("length") != archive_bytes:
    raise SystemExit("appcast enclosure length differs from the archive")
print(signature)
PY
)"

python3 - "$ARCHIVE" "$APPCAST" "$CHECKSUM_FILE" "$ATTESTATION_FILE" "$VERSION" "$SOURCE_SHA" <<'PY'
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

archive_path, appcast_path, checksum_path, attestation_path = map(pathlib.Path, sys.argv[1:5])
version, source_sha = sys.argv[5:]

expected = {
    archive_path.name: hashlib.sha256(archive_path.read_bytes()).hexdigest(),
    appcast_path.name: hashlib.sha256(appcast_path.read_bytes()).hexdigest(),
}
observed = {}
for line in checksum_path.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    fields = line.split()
    if len(fields) != 2:
        raise SystemExit("release checksum file is malformed")
    digest, name = fields
    name = name[1:] if name.startswith("*") else name
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or name not in expected or name in observed:
        raise SystemExit("release checksum file is malformed")
    observed[name] = digest
if observed != expected:
    raise SystemExit("release checksum does not match prepared bytes")

try:
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as error:
    raise SystemExit(f"signing attestation is malformed: {error}") from None
if not isinstance(attestation, dict):
    raise SystemExit("signing attestation is malformed")
if attestation.get("releaseRef") != f"v{version}":
    raise SystemExit("signing attestation releaseRef does not match the requested version")
if attestation.get("commit") != source_sha:
    raise SystemExit("signing attestation commit does not match source SHA")
PY
printf 'appcast_local_validation=pass version=%s archive_bytes=%s signature=present\n' \
  "$VERSION" "$archive_bytes"

archive_sha="$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')"
appcast_sha="$(shasum -a 256 "$APPCAST" | awk '{print $1}')"
printf 'appcast_artifact_binding=pass version=%s source_sha=%s\n' "$VERSION" "$SOURCE_SHA"

if [[ "$DRY_RUN" == "1" ]]; then
  printf 'appcast_publish=dry_run version=%s archive_bytes=%s archive_sha256=%s appcast_sha256=%s host=%s path=%s\n' \
    "$VERSION" "$archive_bytes" "$archive_sha" "$appcast_sha" "$REMOTE_HOST" "$REMOTE_PATH"
  exit 0
fi

verify_public_feed() {
  local live_feed feed_info live_archive live_length live_signature archive_info archive_status
  local live_download_bytes live_archive_sha live_archive_file
  live_feed="$(curl -fsSL --connect-timeout 10 --max-time 90 --retry 3 --retry-delay 1 --retry-all-errors "$FEED_URL")" \
    || { printf 'appcast_publish=blocked reason=public_feed_unreachable\n' >&2; return 1; }
  feed_info="$(LIVE_APPCAST="$live_feed" python3 - "$VERSION" "$FEED_URL" <<'PY'
from __future__ import annotations

import os
import sys
from urllib.parse import urlparse
from xml.etree import ElementTree

version, feed_url = sys.argv[1:]
root = ElementTree.fromstring(os.environ["LIVE_APPCAST"])
items = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "item"]
matching = []
for item in items:
    children = {child.tag.rsplit("}", 1)[-1]: child for child in item}
    version_node = children.get("version")
    if version_node is not None and (version_node.text or "").strip() == version:
        matching.append(item)
if len(matching) != 1:
    raise SystemExit(f"public appcast must contain one item for {version}, found {len(matching)}")
item = matching[0]
enclosure = next((child for child in item if child.tag.rsplit("}", 1)[-1] == "enclosure"), None)
if enclosure is None:
    raise SystemExit("public appcast item has no enclosure")
signature = next((value for key, value in enclosure.attrib.items() if key.rsplit("}", 1)[-1] == "edSignature"), "")
if not signature:
    raise SystemExit("public appcast item has no Sparkle signature")
url = enclosure.attrib.get("url", "")
length = enclosure.attrib.get("length", "")
parsed = urlparse(url)
feed = urlparse(feed_url)
expected_path = feed.path.rsplit("/", 1)[0] + f"/GRAF-{version}.zip"
if parsed.scheme != "https" or parsed.netloc != feed.netloc or parsed.path != expected_path:
    raise SystemExit("public appcast enclosure is not the expected HTTPS archive")
if not length.isdigit():
    raise SystemExit("public appcast enclosure length is not numeric")
print(url, length, signature)
PY
  )" || { printf 'appcast_publish=blocked reason=public_feed_invalid\n' >&2; return 1; }
  read -r live_archive live_length live_signature <<<"$feed_info"
  [[ -n "$live_archive" && -n "$live_length" && -n "$live_signature" ]] \
    || { printf 'appcast_publish=blocked reason=public_feed_fields_missing\n' >&2; return 1; }
  [[ "$live_signature" == "$local_appcast_signature" ]] \
    || { printf 'appcast_publish=blocked reason=public_appcast_signature_mismatch\n' >&2; return 1; }
  [[ "$live_length" == "$archive_bytes" ]] \
    || { printf 'appcast_publish=blocked reason=public_archive_length_mismatch enclosure=%s local=%s\n' \
      "$live_length" "$archive_bytes" >&2; return 1; }
  live_archive_file="$(mktemp "${TMPDIR:-/tmp}/graf-live-archive.XXXXXX")" \
    || { printf 'appcast_publish=blocked reason=public_archive_tempfile_failed\n' >&2; return 1; }
  archive_info="$(curl -fsSL --connect-timeout 10 --max-time 180 --retry 3 --retry-delay 1 --retry-all-errors \
    -o "$live_archive_file" -w '%{http_code} %{size_download}' "$live_archive")" \
    || { rm -f "$live_archive_file"; printf 'appcast_publish=blocked reason=public_archive_unreachable\n' >&2; return 1; }
  read -r archive_status live_download_bytes <<<"$archive_info"
  live_archive_sha="$(shasum -a 256 "$live_archive_file" | awk '{print $1}')"
  rm -f "$live_archive_file"
  [[ "$archive_status" == "200" && "$live_download_bytes" == "$live_length" \
     && "$live_download_bytes" == "$archive_bytes" ]] \
    || { printf 'appcast_publish=blocked reason=public_archive_length_mismatch status=%s bytes=%s expected=%s\n' \
      "$archive_status" "$live_download_bytes" "$archive_bytes" >&2; return 1; }
  [[ "$live_archive_sha" == "$archive_sha" ]] \
    || { printf 'appcast_publish=blocked reason=public_archive_sha256_mismatch expected=%s observed=%s\n' \
      "$archive_sha" "$live_archive_sha" >&2; return 1; }
  printf 'public_feed=pass version=%s archive_http=%s archive_bytes=%s archive_sha256=%s signature=match\n' \
    "$VERSION" "$archive_status" "$live_download_bytes" "$live_archive_sha"
}

transaction_id="${VERSION//./-}-$$-${RANDOM:-0}"

staging=""
cleanup() {
  if [[ -n "$staging" ]]; then
    ssh -o BatchMode=yes -o ConnectTimeout=20 "$REMOTE_HOST" \
      "rm -rf -- $(printf '%q' "$staging")" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

rollback_remote_transaction() {
  ssh -o BatchMode=yes -o ConnectTimeout=20 "$REMOTE_HOST" bash -s -- \
    "$REMOTE_PATH" "$REMOTE_ROOT" "$VERSION" "$transaction_id" <<'REMOTE_ROLLBACK'
set -euo pipefail

target_dir="$1"
remote_root="$2"
version="$3"
transaction_id="$4"
expected_dir="${remote_root%/}/infra/runtime/public-downloads"
[[ "$target_dir" == "$expected_dir" ]] || { echo "rollback=blocked reason=remote_path_not_allowed" >&2; exit 1; }
case "$target_dir" in
  /*) ;;
  *) echo "rollback=blocked reason=remote_path_not_absolute" >&2; exit 1 ;;
esac
case "$target_dir" in
  *[!A-Za-z0-9_./-]*|*..*|*/./*|*/../*) echo "rollback=blocked reason=remote_path_not_canonical" >&2; exit 1 ;;
esac
[[ "$transaction_id" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "rollback=blocked reason=invalid_transaction_id" >&2; exit 1; }
transaction_file="$target_dir/.graf-appcast-transaction-$transaction_id"
[[ -f "$transaction_file" ]] || { echo "appcast_rollback=not_needed"; exit 0; }
archive_installed="$(sed -n 's/^archive_installed=//p' "$transaction_file")"
appcast_updated="$(sed -n 's/^appcast_updated=//p' "$transaction_file")"
appcast_backup="$(sed -n 's/^appcast_backup=//p' "$transaction_file")"
[[ "$archive_installed" == 0 || "$archive_installed" == 1 ]] || { echo "rollback=blocked reason=invalid_transaction" >&2; exit 1; }
[[ "$appcast_updated" == 0 || "$appcast_updated" == 1 ]] || { echo "rollback=blocked reason=invalid_transaction" >&2; exit 1; }
archive_target="$target_dir/GRAF-$version.zip"
appcast_target="$target_dir/graf-appcast.xml"
if [[ "$appcast_updated" == 1 ]]; then
  if [[ "$appcast_backup" != none ]]; then
    [[ "$appcast_backup" == "$target_dir/graf-appcast.xml.pre-v${version}-"* && -f "$appcast_backup" ]] || {
      echo "rollback=blocked reason=invalid_appcast_backup" >&2
      exit 1
    }
    rm -f -- "$appcast_target"
    mv -- "$appcast_backup" "$appcast_target"
  else
    rm -f -- "$appcast_target"
  fi
fi
if [[ "$archive_installed" == 1 ]]; then
  rm -f -- "$archive_target"
fi
rm -f -- "$transaction_file"
echo "appcast_rollback=pass version=$version"
REMOTE_ROLLBACK
}

finalize_remote_transaction() {
  ssh -o BatchMode=yes -o ConnectTimeout=20 "$REMOTE_HOST" bash -s -- \
    "$REMOTE_PATH" "$REMOTE_ROOT" "$transaction_id" <<'REMOTE_FINALIZE'
set -euo pipefail

target_dir="$1"
remote_root="$2"
transaction_id="$3"
expected_dir="${remote_root%/}/infra/runtime/public-downloads"
[[ "$target_dir" == "$expected_dir" ]] || { echo "finalize=blocked reason=remote_path_not_allowed" >&2; exit 1; }
case "$target_dir" in
  /*) ;;
  *) echo "finalize=blocked reason=remote_path_not_absolute" >&2; exit 1 ;;
esac
case "$target_dir" in
  *[!A-Za-z0-9_./-]*|*..*|*/./*|*/../*) echo "finalize=blocked reason=remote_path_not_canonical" >&2; exit 1 ;;
esac
[[ "$transaction_id" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "finalize=blocked reason=invalid_transaction_id" >&2; exit 1; }
rm -f -- "$target_dir/.graf-appcast-transaction-$transaction_id"
echo "appcast_transaction=finalized"
REMOTE_FINALIZE
}

staging="$(ssh -o BatchMode=yes -o ConnectTimeout=20 "$REMOTE_HOST" \
  'mktemp -d /tmp/graf-appcast-release.XXXXXX')"
[[ "$staging" == /tmp/graf-appcast-release.* ]] || fail "invalid_remote_staging_path"
scp -q -o BatchMode=yes -o ConnectTimeout=20 "$ARCHIVE" \
  "$REMOTE_HOST:$staging/GRAF-${VERSION}.zip"
scp -q -o BatchMode=yes -o ConnectTimeout=20 "$APPCAST" \
  "$REMOTE_HOST:$staging/graf-appcast.xml"

ssh -o BatchMode=yes -o ConnectTimeout=20 "$REMOTE_HOST" bash -s -- \
  "$REMOTE_PATH" "$REMOTE_ROOT" "$VERSION" "GRAF-${VERSION}.zip" "$staging" "$transaction_id" <<'REMOTE'
set -euo pipefail
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

target_dir="$1"
remote_root="$2"
version="$3"
archive_name="$4"
staging="$5"
transaction_id="$6"
expected_dir="${remote_root%/}/infra/runtime/public-downloads"
[[ "$target_dir" == "$expected_dir" ]] || {
  echo "appcast_publish=blocked reason=remote_path_not_allowed" >&2
  exit 1
}
case "$target_dir" in
  /*) ;;
  *) echo "appcast_publish=blocked reason=remote_path_not_absolute" >&2; exit 1 ;;
esac
case "$target_dir" in
  *[!A-Za-z0-9_./-]*|*..*|*/./*|*/../*)
    echo "appcast_publish=blocked reason=remote_path_not_canonical" >&2
    exit 1
    ;;
esac
[[ "$transaction_id" =~ ^[A-Za-z0-9_-]+$ ]] || {
  echo "appcast_publish=blocked reason=invalid_transaction_id" >&2
  exit 1
}
lock_dir="$target_dir/.graf-appcast-publish.lock"
lock_owner="$lock_dir/pid"
if ! mkdir "$lock_dir" 2>/dev/null; then
  lock_pid="$(cat "$lock_owner" 2>/dev/null || true)"
  if [[ "$lock_pid" =~ ^[0-9]+$ ]] && ! kill -0 "$lock_pid" 2>/dev/null; then
    rm -rf -- "$lock_dir"
    mkdir "$lock_dir" 2>/dev/null || {
      echo "appcast_publish=blocked reason=remote_publication_in_progress" >&2
      exit 1
    }
  else
    echo "appcast_publish=blocked reason=remote_publication_in_progress" >&2
    exit 1
  fi
fi
printf '%s\n' "$$" >"$lock_owner"
lock_released=0
release_lock() {
  if [[ "$lock_released" == 0 ]]; then
    rm -f -- "$lock_owner"
    rmdir -- "$lock_dir" 2>/dev/null || true
    lock_released=1
  fi
}
archive_source="$staging/$archive_name"
appcast_source="$staging/graf-appcast.xml"
archive_target="$target_dir/$archive_name"
appcast_target="$target_dir/graf-appcast.xml"
transaction_file="$target_dir/.graf-appcast-transaction-$transaction_id"
archive_installed=0
appcast_updated=0
appcast_backup="none"
transaction_ok=0

write_transaction() {
  transaction_temporary="$(mktemp "$target_dir/.graf-transaction-${transaction_id}.XXXXXX")"
  printf 'version=%s\narchive_name=%s\narchive_installed=%s\nappcast_updated=%s\nappcast_backup=%s\n' \
    "$version" "$archive_name" "$archive_installed" "$appcast_updated" "$appcast_backup" >"$transaction_temporary"
  mv -- "$transaction_temporary" "$transaction_file"
}

rollback_transaction_file() {
  stale_transaction="$1"
  [[ -f "$stale_transaction" && ! -L "$stale_transaction" ]] || {
    echo "rollback=blocked reason=invalid_transaction" >&2
    return 1
  }
  recorded_version="$(sed -n 's/^version=//p' "$stale_transaction")"
  recorded_archive_name="$(sed -n 's/^archive_name=//p' "$stale_transaction")"
  recorded_archive_installed="$(sed -n 's/^archive_installed=//p' "$stale_transaction")"
  recorded_appcast_updated="$(sed -n 's/^appcast_updated=//p' "$stale_transaction")"
  recorded_appcast_backup="$(sed -n 's/^appcast_backup=//p' "$stale_transaction")"
  [[ "$recorded_version" =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$ ]] || {
    echo "rollback=blocked reason=invalid_transaction" >&2
    return 1
  }
  [[ "$recorded_archive_name" == "GRAF-${recorded_version}.zip" ]] || {
    echo "rollback=blocked reason=invalid_transaction" >&2
    return 1
  }
  [[ "$recorded_archive_installed" == 0 || "$recorded_archive_installed" == 1 ]] || {
    echo "rollback=blocked reason=invalid_transaction" >&2
    return 1
  }
  [[ "$recorded_appcast_updated" == 0 || "$recorded_appcast_updated" == 1 ]] || {
    echo "rollback=blocked reason=invalid_transaction" >&2
    return 1
  }
  recorded_archive_target="$target_dir/$recorded_archive_name"
  recorded_appcast_target="$target_dir/graf-appcast.xml"
  if [[ "$recorded_appcast_updated" == 1 ]]; then
    if [[ "$recorded_appcast_backup" != none ]]; then
      [[ "$recorded_appcast_backup" == "$target_dir/graf-appcast.xml.pre-v${recorded_version}-"* \
         && -f "$recorded_appcast_backup" && ! -L "$recorded_appcast_backup" ]] || {
        echo "rollback=blocked reason=invalid_appcast_backup" >&2
        return 1
      }
      rm -f -- "$recorded_appcast_target"
      mv -- "$recorded_appcast_backup" "$recorded_appcast_target"
    else
      rm -f -- "$recorded_appcast_target"
    fi
  elif [[ "$recorded_appcast_backup" != none ]]; then
    [[ "$recorded_appcast_backup" == "$target_dir/graf-appcast.xml.pre-v${recorded_version}-"* \
       && -f "$recorded_appcast_backup" && ! -L "$recorded_appcast_backup" ]] || {
      echo "rollback=blocked reason=invalid_appcast_backup" >&2
      return 1
    }
    rm -f -- "$recorded_appcast_backup"
  fi
  if [[ "$recorded_archive_installed" == 1 ]]; then
    rm -f -- "$recorded_archive_target"
  fi
  rm -f -- "$stale_transaction"
}

recover_stale_transactions() {
  stale_transaction=""
  for stale_transaction in "$target_dir"/.graf-appcast-transaction-*; do
    [[ -f "$stale_transaction" ]] || continue
    rollback_transaction_file "$stale_transaction"
    echo "appcast_recovery=pass transaction=$(basename "$stale_transaction")"
  done
}

rollback() {
  status=$?
  set +e
  if [[ "$transaction_ok" == 0 ]]; then
    if [[ "$appcast_updated" == 1 ]]; then
      if [[ "$appcast_backup" != none && -f "$appcast_backup" ]]; then
        rm -f -- "$appcast_target"
        mv -- "$appcast_backup" "$appcast_target"
      else
        rm -f -- "$appcast_target"
      fi
    elif [[ "$appcast_backup" != none ]]; then
      rm -f -- "$appcast_backup"
    fi
    if [[ "$archive_installed" == 1 ]]; then
      rm -f -- "$archive_target"
    fi
    rm -f -- "$transaction_file"
    rm -rf -- "$staging"
  fi
  release_lock
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

recover_stale_transactions
write_transaction

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
  archive_installed=1
  write_transaction
  mv -- "$archive_temporary" "$archive_target"
  echo "appcast_archive=installed"
fi

if [[ -L "$archive_target" || -L "$appcast_target" ]]; then
  echo "appcast_publish=blocked reason=remote_symlink" >&2
  exit 1
fi
if [[ -f "$appcast_target" ]] && cmp -s "$appcast_source" "$appcast_target"; then
  write_transaction
  rm -rf -- "$staging"
  transaction_ok=1
  echo "appcast_feed=already_present"
  echo "appcast_transaction=$transaction_id"
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
  write_transaction
fi
appcast_temporary="$(mktemp "$target_dir/.graf-appcast-${version}.XXXXXX")"
install -m 0644 "$appcast_source" "$appcast_temporary"
cmp -s "$appcast_source" "$appcast_temporary"
appcast_updated=1
write_transaction
mv -- "$appcast_temporary" "$appcast_target"
cmp -s "$appcast_source" "$appcast_target"
rm -rf -- "$staging"
transaction_ok=1
echo "appcast_feed=installed"
echo "appcast_backup=$appcast_backup"
echo "appcast_transaction=$transaction_id"
REMOTE

if ! verify_public_feed; then
  if rollback_remote_transaction; then
    printf 'appcast_publish=rolled_back reason=public_feed_verification_failed version=%s\n' "$VERSION" >&2
  else
    printf 'appcast_publish=rollback_failed reason=public_feed_verification_failed version=%s host=%s path=%s\n' \
      "$VERSION" "$REMOTE_HOST" "$REMOTE_PATH" >&2
  fi
  exit 1
fi
if ! finalize_remote_transaction; then
  if rollback_remote_transaction; then
    printf 'appcast_publish=rolled_back reason=transaction_finalize_failed version=%s\n' "$VERSION" >&2
  else
    printf 'appcast_publish=rollback_failed reason=transaction_finalize_failed version=%s host=%s path=%s\n' \
      "$VERSION" "$REMOTE_HOST" "$REMOTE_PATH" >&2
  fi
  exit 1
fi
printf 'appcast_publish=pass version=%s archive_bytes=%s archive_sha256=%s appcast_sha256=%s host=%s path=%s\n' \
  "$VERSION" "$archive_bytes" "$archive_sha" "$appcast_sha" "$REMOTE_HOST" "$REMOTE_PATH"
