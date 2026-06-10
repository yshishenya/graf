#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $(basename "$0") <patch|minor|major|version>"
  exit 1
fi

bump_input="$1"
changelog="CHANGELOG.md"
today="$(date +%Y-%m-%d)"

if [[ ! -f "$changelog" ]]; then
  echo "error: changelog file not found: $changelog"
  exit 1
fi

latest_tag="$(git tag --list 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -n 1 || true)"
if [[ -z "$latest_tag" ]]; then
  latest_version="0.0.0"
else
  latest_version="${latest_tag#v}"
fi

if [[ "$bump_input" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  next_version="$bump_input"
else
  IFS='.' read -r major minor patch <<< "$latest_version"
  case "$bump_input" in
    patch)
      patch=$((patch + 1))
      ;;
    minor)
      minor=$((minor + 1))
      patch=0
      ;;
    major)
      major=$((major + 1))
      minor=0
      patch=0
      ;;
    *)
      echo "error: bump must be patch, minor, major, or explicit version"
      exit 1
      ;;
  esac
  next_version="$major.$minor.$patch"
fi

if git tag --list "v$next_version" | grep -q "v$next_version"; then
  echo "error: tag v$next_version already exists"
  exit 1
fi

unreleased_content="$(awk '/^## \[Unreleased\]/{record=1; next} /^## \[Unreleased Template\]/{if (record) exit} record{print}' "$changelog")"

if [[ -z "${unreleased_content}" ]]; then
  echo "error: unreleased block is empty. add entries before release"
  exit 1
fi

real_entries="$(printf '%s\n' "$unreleased_content" | awk '/^[[:space:]]*-[[:space:]]*/ {if ($0 !~ /No entries yet/) count++} END {if (count > 0) print count else print 0}')"
if [[ "$real_entries" -eq 0 ]]; then
  echo "error: unreleased block has no concrete entries"
  echo "add real bullets to CHANGELOG.md first"
  exit 1
fi

head_part="$(awk '/^## \[Unreleased\]/{exit} {print}' "$changelog")"
template_part="$(awk '/^## \[Unreleased Template\]/{print; flag=1; next} flag{print}' "$changelog")"

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

{
  printf '%s\n' "$head_part"
  cat <<'EOF'
## [Unreleased]

### Added
- _No entries yet._

### Changed
- _No entries yet._

### Fixed
- _No entries yet._

### Security
- _No entries yet._

### Docs
- _No entries yet._

### Ops
- _No entries yet._

EOF
  printf '## [%s] - %s\n\n' "$next_version" "$today"
  printf '%s\n' "$unreleased_content"
  printf '\n%s\n' "$template_part"
} > "$tmp_file"

mv "$tmp_file" "$changelog"
echo "Prepared release section in $changelog for v$next_version"
echo "Next step: git add CHANGELOG.md && git commit -m \"chore: prepare release v$next_version\" && git tag -a v$next_version -m \"Release v$next_version\""
