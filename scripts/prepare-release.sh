#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $(basename "$0") <YYYY.MM.DD.N>"
  exit 1
fi

bump_input="$1"
changelog="CHANGELOG.md"
today="$(date +%Y-%m-%d)"

if [[ ! -f "$changelog" ]]; then
  echo "error: changelog file not found: $changelog"
  exit 1
fi

if [[ ! "$bump_input" =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$ ]]; then
  echo "error: product releases require explicit CalVer YYYY.MM.DD.N"
  exit 1
fi
next_version="$bump_input"

if git tag --list "v$next_version" | grep -q "v$next_version"; then
  echo "error: tag v$next_version already exists"
  exit 1
fi

if [[ -f "$PWD/scripts/validate-changelog-fragments.py" ]]; then
  python3 scripts/validate-changelog-fragments.py --root "$PWD"
fi

unreleased_content="$(awk '/^## \[Unreleased\]/{record=1; next} /^## \[Unreleased Template\]/{if (record) exit} record{print}' "$changelog")"

# Feature agents own independent fragments. The release operator is the only
# writer that assembles them into the root changelog.
fragment_content="$(python3 - "$PWD" <<'PY'
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
titles = {
    "Added": "Добавлено",
    "Changed": "Изменено",
    "Fixed": "Исправлено",
    "Security": "Безопасность",
    "Docs": "Документы",
    "Ops": "Операции",
}
groups = {key: [] for key in titles}
for path in sorted((root / "changes" / "unreleased").glob("F*.yaml")):
    text = path.read_text(encoding="utf-8")

    def value(name):
        match = re.search(r"^" + re.escape(name) + r":\s*(.*)$", text, re.MULTILINE)
        if not match:
            return ""
        raw = match.group(1).strip()
        if raw.startswith('"') and raw.endswith('"'):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw[1:-1]
        return raw.strip("'")

    category = value("category")
    feature = value("feature_id")
    summary = value("summary")
    issue = value("issue")
    tasks = value("tasks")
    compatibility = value("compatibility")
    limitations = value("known_limitations")
    if category not in groups or not feature or not summary:
        raise SystemExit(f"invalid fragment fields: {path}")
    refs = [f"Фича {feature}"]
    if issue and issue not in {"null", "[]"}:
        refs.append(f"issue #{issue.lstrip('#')}")
    if tasks and tasks not in {"null", "[]"}:
        refs.append(f"tasks {tasks}")
    entry = f"- {summary} ({', '.join(refs)})"
    if compatibility:
        entry += f"; совместимость: {compatibility}"
    if limitations and limitations not in {"[]", "null"}:
        entry += f"; ограничения: {limitations}"
    groups[category].append(entry)
for category, title in titles.items():
    if groups[category]:
        print(f"### {title}")
        print("\n".join(groups[category]))
PY
)"
if [[ -n "$fragment_content" ]]; then
  if [[ -n "$unreleased_content" ]]; then
    unreleased_content="$fragment_content"$'\n\n'"$unreleased_content"
  else
    unreleased_content="$fragment_content"
  fi
fi
if [[ -z "${unreleased_content}" ]]; then
  echo "error: unreleased block is empty. add entries before release"
  exit 1
fi

real_entries="$(printf '%s\n' "$unreleased_content" | awk '/^[[:space:]]*-[[:space:]]*/ {if ($0 !~ /No entries yet/ && $0 !~ /Пока нет записей/) count++} END {if (count > 0) {print count} else {print 0}}')"
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
  printf '%s\n\n' "$head_part"
  cat <<'EOF'
## [Unreleased]

### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

EOF
  printf '## [%s] - %s\n\n' "$next_version" "$today"
  printf '%s\n' "$unreleased_content"
  printf '\n%s\n' "$template_part"
} > "$tmp_file"

mv "$tmp_file" "$changelog"
fragment_dir="$PWD/changes/unreleased"
archive_dir="$PWD/changes/releases/v$next_version"
if [[ -d "$fragment_dir" ]] && compgen -G "$fragment_dir/F*.yaml" > /dev/null; then
  mkdir -p "$archive_dir"
  for fragment in "$fragment_dir"/F*.yaml; do
    mv "$fragment" "$archive_dir/"
  done
  echo "Archived release fragments in $archive_dir"
fi
echo "Prepared release section in $changelog for v$next_version"
echo "Next step: git add CHANGELOG.md && git commit -m \"chore: prepare release v$next_version\" && git tag -a v$next_version -m \"Release v$next_version\""
