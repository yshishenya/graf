#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $(basename "$0") <YYYY.MM.DD.N>"
  exit 1
fi

bump_input="$1"
changelog="CHANGELOG.md"
today="$(date +%Y-%m-%d)"
release_operator="${GRAF_RELEASE_OPERATOR:-}"

if [[ -z "$release_operator" || ! "$release_operator" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ ]]; then
  echo "error: set GRAF_RELEASE_OPERATOR to an explicit release-operator identity"
  exit 1
fi

# Preparing a release mutates the root changelog and archives feature
# fragments. Never invalidate a candidate that has already been frozen for
# this exact source tree; create a new candidate only after the release-prep
# commit is complete.
current_sha="$(git rev-parse HEAD 2>/dev/null || true)"
if ! python3 - "$PWD/.dev/release/candidates" "$current_sha" <<'PY'
import json
import sys
from pathlib import Path

candidate_dir = Path(sys.argv[1])
current_sha = sys.argv[2]
if not candidate_dir.is_dir():
    raise SystemExit(0)
for path in sorted(candidate_dir.glob("rc-*.json")):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: release candidate is unreadable: {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"error: release candidate is malformed: {path}")
    if data.get("status") == "frozen" and data.get("source_sha") == current_sha:
        raise SystemExit(
            f"error: frozen release candidate targets current HEAD: {path}; "
            "validate or invalidate it before preparing a release"
        )
PY
then
  exit 1
fi

if [[ ! -f "$changelog" ]]; then
  echo "error: changelog file not found: $changelog"
  exit 1
fi

if [[ ! "$bump_input" =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$ ]]; then
  echo "error: product releases require explicit CalVer YYYY.MM.DD.N"
  exit 1
fi
next_version="$bump_input"

if ! python3 - "$next_version" <<'PY'
import datetime as dt
import sys

value = sys.argv[1]
year, month, day, _ = value.split(".")
try:
    dt.date(int(year), int(month), int(day))
except ValueError:
    raise SystemExit("invalid calendar date")
PY
then
  echo "error: CalVer date does not exist: $next_version"
  exit 1
fi

if git tag --list "v$next_version" | grep -q "v$next_version"; then
  echo "error: tag v$next_version already exists"
  exit 1
fi

published_tag=""
published_version=""
pending_versions=()
origin_url="$(git config --get remote.origin.url 2>/dev/null || true)"
if [[ "$origin_url" == *github.com* ]]; then
  if ! release_json="$(gh release list --limit 100 --json tagName,isDraft,isPrerelease,publishedAt)"; then
    echo "error: cannot resolve the latest published GitHub Release"
    exit 1
  fi
  if ! published_tag="$(python3 - "$release_json" <<'PY'
import json
import sys

try:
    releases = json.loads(sys.argv[1])
    published = [
        item for item in releases
        if isinstance(item, dict)
        and not item.get("isDraft")
        and not item.get("isPrerelease")
        and item.get("publishedAt")
        and item.get("tagName")
    ]
    print(max(published, key=lambda item: item["publishedAt"])["tagName"])
except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
    raise SystemExit(f"invalid GitHub Release inventory: {exc}")
PY
  )"; then
    echo "error: cannot select the latest published GitHub Release"
    exit 1
  fi
  if [[ ! "$published_tag" =~ ^v[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$ ]]; then
    echo "error: latest published GitHub Release has invalid product tag: $published_tag"
    exit 1
  fi
  if ! release_view_json="$(gh release view "$published_tag" --json tagName,targetCommitish,isDraft,isPrerelease,publishedAt)"; then
    echo "error: cannot verify published GitHub Release $published_tag"
    exit 1
  fi
  if ! python3 - "$release_view_json" "$published_tag" <<'PY'
import json
import sys

try:
    release = json.loads(sys.argv[1])
except json.JSONDecodeError as exc:
    raise SystemExit(f"invalid GitHub Release metadata: {exc}")
if (
    not isinstance(release, dict)
    or release.get("tagName") != sys.argv[2]
    or release.get("isDraft")
    or release.get("isPrerelease")
    or not release.get("publishedAt")
):
    raise SystemExit("selected GitHub Release is not published stable metadata")
PY
  then
    echo "error: cannot verify published GitHub Release metadata $published_tag"
    exit 1
  fi
  github_repo=""
  case "$origin_url" in
    git@github.com:*) github_repo="${origin_url#git@github.com:}" ;;
    ssh://git@github.com/*) github_repo="${origin_url#ssh://git@github.com/}" ;;
    https://github.com/*|http://github.com/*) github_repo="${origin_url#*github.com/}" ;;
  esac
  github_repo="${github_repo%.git}"
  if [[ ! "$github_repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
    echo "error: cannot resolve GitHub repository from origin URL"
    exit 1
  fi
  if ! remote_tag_json="$(gh api "repos/$github_repo/git/ref/tags/$published_tag")"; then
    echo "error: cannot resolve published GitHub tag $published_tag"
    exit 1
  fi
  if ! remote_tag_type="$(python3 - "$remote_tag_json" <<'PY'
import json
import sys

try:
    value = json.loads(sys.argv[1])
    object_value = value["object"]
    print(object_value["type"])
except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
    raise SystemExit(f"invalid GitHub tag reference: {exc}")
PY
  )" || [[ "$remote_tag_type" != "commit" && "$remote_tag_type" != "tag" ]]; then
    echo "error: published GitHub tag $published_tag has invalid object metadata"
    exit 1
  fi
  if ! remote_tag_object_sha="$(python3 - "$remote_tag_json" <<'PY'
import json
import re
import sys

try:
    value = json.loads(sys.argv[1])
    sha = str(value["object"]["sha"])
except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
    raise SystemExit(f"invalid GitHub tag reference: {exc}")
if not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
    raise SystemExit("GitHub tag object SHA must be an exact 40-character SHA")
print(sha.lower())
PY
  )"; then
    echo "error: published GitHub tag $published_tag has invalid object SHA"
    exit 1
  fi
  published_target="$remote_tag_object_sha"
  if [[ "$remote_tag_type" == "tag" ]]; then
    if ! remote_annotated_tag_json="$(gh api "repos/$github_repo/git/tags/$remote_tag_object_sha")"; then
      echo "error: cannot resolve annotated GitHub tag $published_tag"
      exit 1
    fi
    if ! published_target="$(python3 - "$remote_annotated_tag_json" <<'PY'
import json
import re
import sys

try:
    value = json.loads(sys.argv[1])
    target = str(value["object"]["sha"])
    target_type = value["object"]["type"]
except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
    raise SystemExit(f"invalid annotated GitHub tag: {exc}")
if target_type != "commit" or not re.fullmatch(r"[0-9a-fA-F]{40}", target):
    raise SystemExit("annotated GitHub tag must point to an exact commit SHA")
print(target.lower())
PY
    )"; then
      echo "error: annotated GitHub tag $published_tag does not point to a commit"
      exit 1
    fi
  fi
  if ! git rev-parse --verify --quiet "${published_tag}^{commit}" >/dev/null; then
    echo "error: published tag $published_tag is missing locally; fetch tags before release preparation"
    exit 1
  fi
  if ! git merge-base --is-ancestor "$published_tag" HEAD; then
    echo "error: published tag $published_tag is not an ancestor of current HEAD"
    exit 1
  fi
  local_published_target="$(git rev-parse "${published_tag}^{commit}")"
  if [[ "$local_published_target" != "$published_target" ]]; then
    echo "error: local tag $published_tag does not match its published GitHub Release target"
    exit 1
  fi
  published_version="${published_tag#v}"
  if ! pending_state_json="$(python3 - "$PWD" "$changelog" "$published_version" <<'PY'
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
text = Path(sys.argv[2]).read_text(encoding="utf-8")
published = sys.argv[3]
heading_re = re.compile(r"^## \[(?P<version>[^]]+)\][^\n]*$", re.MULTILINE)
headings = list(heading_re.finditer(text))
published_index = next(
    (index for index, match in enumerate(headings) if match.group("version") == published),
    None,
)
if published_index is None:
    raise SystemExit(f"published release {published} is missing from CHANGELOG.md")

pending = [
    match for match in headings[:published_index]
    if re.fullmatch(r"\d{4}\.\d{2}\.\d{2}\.\d+", match.group("version"))
]
pending_versions = [match.group("version") for match in pending]
published_key = tuple(map(int, published.split(".")))
for directory in (root / "changes" / "releases").glob("v*"):
    version = directory.name.removeprefix("v")
    if re.fullmatch(r"\d{4}\.\d{2}\.\d{2}\.\d+", version):
        if tuple(map(int, version.split("."))) > published_key and version not in pending_versions:
            raise SystemExit(f"orphan unpublished fragment directory without changelog heading: {directory}")

titles = ("Добавлено", "Изменено", "Исправлено", "Важно", "Безопасность", "Документы", "Операции")
groups = {title: [] for title in titles}
fragment_features = []
for version in pending_versions:
    fragment_dir = root / "changes" / "releases" / f"v{version}"
    for path in sorted(fragment_dir.glob("F*.yaml")):
        value = re.search(
            r"^feature_id[ \t]*:[ \t]*(\d+)[ \t]*$",
            path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if not value:
            raise SystemExit(f"invalid pending fragment: {path}")
        fragment_features.append(int(value.group(1)))
fragment_feature_set = set(fragment_features)

marked_entries = {}
seen_content = set()
for match in pending:
    version = match.group("version")
    start = match.end()
    next_heading = heading_re.search(text, start)
    block = text[start : next_heading.start() if next_heading else len(text)]
    lines = block.splitlines()
    category = None
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("### "):
            heading = line[4:].strip()
            category = heading if heading in groups else None
            index += 1
            continue
        if not category or not line.lstrip().startswith("-"):
            index += 1
            continue
        item = [line.strip()]
        index += 1
        while index < len(lines) and not lines[index].startswith("### ") and not lines[index].lstrip().startswith("-"):
            if lines[index].strip():
                item.append(lines[index].rstrip())
            index += 1
        value = "\n".join(item)
        if "Пока нет записей" in value or "No entries yet" in value:
            continue
        feature = re.search(r"Фича\s+(\d+)", value)
        if feature:
            feature_id = int(feature.group(1))
            if feature_id not in fragment_feature_set:
                raise SystemExit(
                    f"unpublished changelog entry references Feature {feature_id} without an archived fragment"
                )
            normalized = " ".join(value.split())
            previous = marked_entries.get(feature_id)
            if previous and previous != normalized:
                raise SystemExit(
                    f"conflicting unpublished changelog entries for Feature {feature_id}; consolidate them explicitly"
                )
            marked_entries[feature_id] = normalized
        normalized_content = " ".join(value.split())
        if normalized_content not in seen_content:
            seen_content.add(normalized_content)
            groups[category].append(value)

if not fragment_features and pending_versions:
    raise SystemExit(
        "unpublished changelog sections have no archived Feature fragments"
    )
content = "\n\n".join(
    f"### {title}\n" + "\n".join(groups[title])
    for title in titles
    if groups[title]
)
print(json.dumps({"versions": pending_versions, "content": content}, ensure_ascii=False))
PY
  )"; then
    echo "error: cannot reconcile unpublished changelog sections"
    exit 1
  fi
  pending_versions_text="$(python3 - "$pending_state_json" <<'PY'
import json
import sys
print("\n".join(json.loads(sys.argv[1])["versions"]))
PY
  )"
  pending_content="$(python3 - "$pending_state_json" <<'PY'
import json
import sys
print(json.loads(sys.argv[1])["content"])
PY
  )"
  while IFS= read -r version; do
    [[ -n "$version" ]] && pending_versions+=("$version")
  done <<< "$pending_versions_text"
  echo "Release base: $published_tag (${#pending_versions[@]} unpublished section(s) will be folded)"
fi

pending_content="${pending_content:-}"

shopt -s nullglob
fragment_paths=("$PWD"/changes/unreleased/F*.yaml)
for version in "${pending_versions[@]}"; do
  fragment_paths+=("$PWD"/changes/releases/"v$version"/F*.yaml)
done
shopt -u nullglob

if [[ -f "$PWD/scripts/validate-changelog-fragments.py" ]]; then
  python3 scripts/validate-changelog-fragments.py --root "$PWD"
fi

unreleased_content="$(python3 - "$changelog" <<'PY'
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
match = re.search(r"^## \[Unreleased\][ \t]*\n([\s\S]*?)(?=^## \[|\Z)", text, re.MULTILINE)
print(match.group(1).strip() if match else "")
PY
)"

# Feature agents own independent fragments. The release operator is the only
# writer that assembles them into the root changelog.
fragment_content="$(python3 - "$PWD" "${fragment_paths[@]}" <<'PY'
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
seen_features = {}
for path in sorted(Path(raw) for raw in sys.argv[2:]):
    is_current = path.parent.name == "unreleased"
    text = path.read_text(encoding="utf-8")

    def scalar(raw):
        raw = raw.strip()
        if raw.startswith('"') and raw.endswith('"'):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw[1:-1]
        if raw.startswith("'") and raw.endswith("'"):
            return raw[1:-1].replace("''", "'")
        return raw.split(" #", 1)[0].strip()

    def fields():
        result = {}
        lines = text.splitlines()
        index = 0
        while index < len(lines):
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)[ \t]*:[ \t]*(.*)$", lines[index])
            if not match:
                index += 1
                continue
            name, raw = match.groups()
            if name in result:
                raise SystemExit(f"duplicate fragment field {name}: {path}")
            index += 1
            if raw in {"|", ">", "|-", ">-", "|+", ">+"}:
                block = []
                while index < len(lines) and (not lines[index].strip() or lines[index].startswith((" ", "\t"))):
                    block.append(lines[index][2:] if lines[index].startswith("  ") else lines[index].lstrip())
                    index += 1
                result[name] = "\n".join(block) if raw.startswith("|") else " ".join(line.strip() for line in block)
                continue
            if not raw:
                values = []
                while index < len(lines):
                    item = re.match(r"^[ \t]{2,}-[ \t]*(.*)$", lines[index])
                    if not item:
                        break
                    values.append(scalar(item.group(1)))
                    index += 1
                result[name] = values if values else ""
                continue
            result[name] = scalar(raw)
        return result

    parsed = fields()

    def value(name):
        return parsed.get(name, "")

    category = value("category")
    feature = value("feature_id")
    summary = value("summary")
    issue = value("issue")
    tasks = value("tasks")
    compatibility = value("compatibility")
    release_notes = value("release_notes")
    limitations = value("known_limitations")
    if category not in groups or not feature or not summary:
        raise SystemExit(f"invalid fragment fields: {path}")
    if feature in seen_features:
        raise SystemExit(
            f"duplicate pending feature_id {feature}: {seen_features[feature]} and {path}; "
            "merge the fragments before preparing the release"
        )
    seen_features[feature] = path

    def display(raw):
        if isinstance(raw, list):
            return "; ".join(display(item) for item in raw if display(item))
        return " ".join(str(raw).split())

    summary = display(summary)
    compatibility = display(compatibility)
    release_notes = display(release_notes)
    limitations = display(limitations)
    refs = [f"Фича {feature}"]
    if issue and issue not in {"null", "[]"}:
        refs.append(f"issue #{issue.lstrip('#')}")
    if tasks and tasks not in {"null", "[]"}:
        refs.append(f"tasks {tasks}")
    entry = f"- {summary} ({', '.join(refs)})"
    if compatibility:
        entry += f"; совместимость: {compatibility}"
    if release_notes and release_notes not in {"[]", "null"}:
        entry += f"; release notes: {release_notes}"
    if limitations and limitations not in {"[]", "null"}:
        if limitations:
            entry += f"; ограничения: {limitations}"
    if is_current:
        groups[category].append(entry)
for category, title in titles.items():
    if groups[category]:
        print(f"### {title}")
        print("\n".join(groups[category]))
PY
)"
if [[ -n "$pending_content" ]]; then
  fragment_content="$pending_content"$'\n'"$fragment_content"
fi
if [[ -n "$fragment_content" ]]; then
  if [[ -n "$unreleased_content" ]]; then
    unreleased_content="$(python3 - "$unreleased_content" "$fragment_content" <<'PY'
import sys

existing, generated = sys.argv[1:]
titles = ("Добавлено", "Изменено", "Исправлено", "Важно", "Безопасность", "Документы", "Операции")
groups = {title: [] for title in titles}

def collect(text):
    current = None
    for line in text.splitlines():
        if line.startswith("### "):
            heading = line[4:].strip()
            current = heading if heading in groups else None
            continue
        if current and line.strip() and "Пока нет записей" not in line and "No entries yet" not in line:
            groups[current].append(line)

collect(existing)
collect(generated)
for title in titles:
    print(f"### {title}")
    print("\n".join(groups[title] or ["- _Пока нет записей._"]))
    print()
PY
)"
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
# Preserve every historical release heading.  The old implementation looked
# for an optional template heading that is not present in the real changelog,
# silently truncating release history on every preparation.
if [[ -n "$published_version" ]]; then
  history_part="$(python3 - "$changelog" "$published_version" <<'PY'
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
version = re.escape(sys.argv[2])
match = re.search(rf"^## \[{version}\][^\n]*$", text, re.MULTILINE)
if not match:
    raise SystemExit(f"published release {sys.argv[2]} is missing from CHANGELOG.md")
print(text[match.start():].rstrip())
PY
  )"
else
  history_part="$(awk '/^## \[20[0-9][0-9]\./{seen=1} seen{print}' "$changelog")"
fi

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
  printf '\n%s\n' "$history_part"
} > "$tmp_file"

mv "$tmp_file" "$changelog"
archive_dir="$PWD/changes/releases/v$next_version"
if [[ "${#fragment_paths[@]}" -gt 0 ]]; then
  mkdir -p "$archive_dir"
  for fragment in "${fragment_paths[@]}"; do
    mv "$fragment" "$archive_dir/"
  done
  for version in "${pending_versions[@]}"; do
    rmdir "$PWD/changes/releases/v$version" 2>/dev/null || true
  done
  echo "Archived release fragments in $archive_dir"
fi
echo "Prepared release section in $changelog for v$next_version"
echo "Next step: git add CHANGELOG.md && git commit -m \"chore: prepare release v$next_version\" && git tag -a v$next_version -m \"Release v$next_version\""
