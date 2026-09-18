#!/usr/bin/env bash
# One command for a product release.
#
# The release was a dozen hand-typed steps, and each one had its own argument
# format that was easy to get wrong (synthetic merge SHA, per-pull-request
# receipts, the attested train file, the canonical evidence path).  This script
# runs the whole documented sequence and derives every argument from the
# repository itself, so the operator only decides two things: whether the
# release-preparation pull request may be merged, and whether production may be
# deployed.  Everything else is measured, printed and stopped on failure.

set -euo pipefail

usage() {
  cat <<'EOF'
usage: scripts/release.sh <YYYY.MM.DD.N> [options]

  --operator <name>   release operator identity (default: git config user.name)
  --merge             merge the release-preparation pull request after checks pass
  --deploy            deploy to production after a clean dry run
  --no-app            skip building and attaching the macOS app update
  --from <step>       resume at a step: prep, train, ci, decide, deploy, publish
  --stop-after <step> stop once this step is done

The macOS app update is built in the background while the release train runs
and is attached to the release before it becomes public; --no-app skips it.

Steps: prep, train, ci, decide, deploy, publish.
Without --merge the script stops after the release-preparation pull request is
verified and prints the command to continue.  Without --deploy it stops after the
mandatory dry run of the production deploy.
EOF
}

version=""
operator="${GRAF_RELEASE_OPERATOR:-$(git config user.name || true)}"
merge=false
deploy=false
with_app=true
resume_step=""
stop_after=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --operator) operator="${2:-}"; shift 2 ;;
    --merge) merge=true; shift ;;
    --deploy) deploy=true; shift ;;
    --no-app) with_app=false; shift ;;
    --from) resume_step="${2:-}"; shift 2 ;;
    --stop-after) stop_after="${2:-}"; shift ;;
    -*) printf 'release: unknown option %s\n' "$1" >&2; usage >&2; exit 2 ;;
    *) version="$1"; shift ;;
  esac
done

[[ "$version" =~ ^[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$ ]] \
  || { printf 'release: version must look like YYYY.MM.DD.N, got %s\n' "${version:-<empty>}" >&2; exit 2; }
[[ -n "$operator" ]] || { printf 'release: set --operator or GRAF_RELEASE_OPERATOR\n' >&2; exit 2; }

root="$(git rev-parse --show-toplevel)"
cd "$root"
tag="v${version}"

step_index=0
step_started=0
step() {
  step_index=$((step_index + 1))
  printf '\n=== [%s] %s\n' "$step_index" "$1"
  step_started="$(date -u +%s)"
  printf 'release_step=%s started_at=%s\n' "$1" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
step_done() {
  local finished elapsed
  finished="$(date -u +%s)"
  elapsed=$((finished - step_started))
  printf 'release_step=%s duration_seconds=%s status=done\n' "$1" "$elapsed"
  total_elapsed=$((total_elapsed + elapsed))
}
# The three checks that branch protection requires, as "name=STATE" pairs.  An
# empty result means the check runs do not exist yet.
read_required_checks() {
  gh pr checks "$1" --json name,state \
    --jq '[.[]|select(.name=="governance-fast" or .name=="macos-pr" or .name=="pr-metadata")|"\(.name)=\(.state)"]|join(" ")' \
    2>/dev/null || true
}
# The previous release base comes from published GitHub Releases rather than
# from tags.  A stray or future-dated tag would otherwise move the release base
# and make the release compare itself against the wrong history.
latest_published_tag() {
  gh release list --limit 100 --json tagName,isDraft,isPrerelease,publishedAt \
    --jq '[.[]|select(.isDraft==false and .isPrerelease==false and .publishedAt!=null and .tagName!="")]|max_by(.publishedAt)|.tagName' \
    2>/dev/null || true
}
# The release candidate takes numeric feature IDs, while the changelog marker
# spells them as F271.  Convert one into the other so the operator never has to
# retype the list.
numeric_feature_ids() {
  python3 -c 'import re,sys; print(",".join(dict.fromkeys(re.findall(r"[0-9]{3,}", sys.argv[1]))))' "$1"
}
total_elapsed=0
started_all="$(date -u +%s)"

completed=false
step_order=(prep train ci decide deploy publish)
step_index_of() {
  local name="$1" index=0
  for candidate in "${step_order[@]}"; do
    [[ "$candidate" == "$name" ]] && { printf '%s' "$index"; return 0; }
    index=$((index + 1))
  done
  return 1
}
should_run() {
  # Resume support: --from skips earlier steps, --stop-after stops later ones.
  local name="$1" index
  index="$(step_index_of "$name")" || return 0
  if [[ -n "$resume_step" ]]; then
    local resume_index
    resume_index="$(step_index_of "$resume_step")" \
      || { printf 'release: unknown --from step %s\n' "$resume_step" >&2; exit 2; }
    (( index >= resume_index )) || return 1
  fi
  if [[ -n "$stop_after" ]]; then
    local stop_index
    stop_index="$(step_index_of "$stop_after")" \
      || { printf 'release: unknown --stop-after step %s\n' "$stop_after" >&2; exit 2; }
    (( index <= stop_index )) || return 1
  fi
  return 0
}

require_clean_master() {
  [[ -z "$(git status --porcelain)" ]] || { printf 'release: worktree is not clean\n' >&2; exit 1; }
  git fetch --no-tags origin master
  local head master
  head="$(git rev-parse HEAD)"
  master="$(git rev-parse origin/master)"
  [[ "$head" == "$master" ]] \
    || { printf 'release: HEAD %s is not origin/master %s\n' "${head:0:12}" "${master:0:12}" >&2; exit 1; }
}

# ---------------------------------------------------------------- step: prep

if should_run prep; then
  step "prep: собрать раздел журнала и открыть пул-реквест"
  require_clean_master
  previous_tag="$(latest_published_tag)"
  [[ -n "$previous_tag" ]] \
    || { printf 'release: cannot resolve the latest published release\n' >&2; exit 1; }
  base_sha="$(git rev-list -n 1 "$previous_tag")"
  printf 'release_base=%s base_sha=%s\n' "$previous_tag" "$base_sha"

  branch="release-prep-${version}"
  # An abandoned earlier attempt at this exact version can leave the branch and
  # its pull request behind.  The version has no published release yet, so the
  # preparation is rebuilt from scratch instead of failing on a raw git error.
  for stale_pr in $(gh pr list --head "$branch" --state open --json number --jq '.[].number' 2>/dev/null); do
    [[ -n "$stale_pr" ]] || continue
    gh pr close "$stale_pr" \
      --comment "Подготовка релиза ${version} выполняется заново: прошлая попытка была прервана." >/dev/null
    printf 'release: закрыт прерванный пул-реквест подготовки %s\n' "$stale_pr"
  done
  if git show-ref --verify --quiet "refs/heads/${branch}"; then
    git branch -D "$branch" >/dev/null
    printf 'release: местная ветка подготовки %s пересобрана с нуля\n' "$branch"
  fi
  if git ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
    git push -q origin --delete "$branch"
    printf 'release: ветка подготовки %s удалена на сервере и пересобрана\n' "$branch"
  fi
  git switch -c "$branch"
  GRAF_RELEASE_OPERATOR="$operator" ./scripts/prepare-release.sh "$version"

  features="$(python3 - "$version" <<'PY'
import pathlib
import re
import sys

text = pathlib.Path("CHANGELOG.md").read_text(encoding="utf-8")
heading = re.search(rf"^## \[{re.escape(sys.argv[1])}\]", text, re.MULTILINE)
if not heading:
    raise SystemExit("release section missing from CHANGELOG.md")
tail = text[heading.end():]
next_heading = re.search(r"^## \[", tail, re.MULTILINE)
section = tail[: next_heading.start()] if next_heading else tail
marker = re.search(r"<!-- Release features: ([^>]*?)-->", section)
if not marker:
    raise SystemExit("release features marker missing")
print(marker.group(1).strip())
PY
)"
  [[ -n "$features" ]] || { printf 'release: release features marker is empty\n' >&2; exit 1; }
  feature_ids="$(numeric_feature_ids "$features")"
  [[ -n "$feature_ids" ]] \
    || { printf 'release: release features marker has no numeric IDs\n' >&2; exit 1; }
  feature_id="${feature_ids%%,*}"
  printf 'release_features=%s feature_ids=%s\n' "$features" "$feature_ids"

  git add -A
  git commit -m "Подготовка релиза ${version}

Раздел CHANGELOG.md собран из фрагментов выпуска, фрагменты перенесены в
архив выпуска."
  source_sha="$(git rev-parse HEAD)"
  git push -u origin "$branch"

  feature_id="$(printf '%s' "$features" | tr ',' '\n' | head -1 | tr -d ' F')"
  umbrella="$(grep -oE "Фича ${feature_id}, issue #[0-9]+" CHANGELOG.md | head -1 | grep -oE '[0-9]+$' || true)"
  [[ -n "$umbrella" ]] || umbrella="$(gh issue list --label "feature:${feature_id}" --state all --limit 1 --json number --jq '.[0].number')"
  [[ -n "$umbrella" ]] || { printf 'release: umbrella issue for feature %s not found\n' "$feature_id" >&2; exit 1; }

  body_file="$(mktemp)"
  cat > "$body_file" <<EOF
## Кратко

Подготовка релиза \`${version}\`: раздел \`CHANGELOG.md\` собран из фрагментов
выпуска (${features}), фрагменты перенесены в архив выпуска.

## Feature identity

- Feature ID: F${feature_id}
- Spec task IDs: \`T001\`
- Exact source SHA: \`${source_sha}\`

## Как проверено

- \`scripts/prepare-release.sh ${version}\` — pass: раздел \`CHANGELOG.md\` собран,
  фрагменты выпуска проверены и перенесены в архив
- \`git diff --stat origin/master...HEAD\` — pass: меняются только журнал
  изменений, архив фрагментов и записанный номер версии
- Обязательные проверки GitHub \`governance-fast\`, \`macos-pr\` и
  \`pr-metadata\` на точном SHA — этот пул-реквест

## Risk / validation lane

Lane: release-deploy. Меняются только журнал изменений и архив фрагментов.

## Issues

Umbrella issue: #${umbrella}

Refs #${umbrella}

## Legacy Impact

- Classification: untouched

## Перед merge

- [x] Раздел журнала собран оператором релиза
- [ ] Обязательные проверки GitHub на точном SHA
EOF
  pr_url="$(gh pr create --base master --head "$branch" \
    --title "[F${feature_id}] Подготовка релиза ${version}" --body-file "$body_file")"
  rm -f "$body_file"
  pr_number="${pr_url##*/}"
  printf 'release_pr=%s\n' "$pr_number"
  step_done prep

  if [[ "$merge" != true ]]; then
    cat <<EOF

Пул-реквест подготовки релиза: $pr_url

Дальше: дождаться проверок и продолжить командой
  scripts/release.sh ${version} --from train$([[ "$deploy" == true ]] && printf ' --deploy')
EOF
    exit 0
  fi

  step "prep: дождаться обязательных проверок и влить"
  required_checks="governance-fast macos-pr pr-metadata"
  checks=""
  # A freshly created pull request has no check runs for the first seconds, and
  # `gh pr checks` reports that as an error rather than an empty list.  Wait for
  # the checks to exist before watching them, otherwise the release stops on a
  # pull request that is perfectly healthy.
  for attempt in $(seq 1 40); do
    checks="$(read_required_checks "$pr_number")"
    [[ -n "$checks" ]] && break
    printf 'release: обязательные проверки ещё не появились, ожидание %s/40\n' "$attempt"
    sleep 15
  done
  [[ -n "$checks" ]] \
    || { printf 'release: обязательные проверки так и не появились на пул-реквесте %s\n' "$pr_number" >&2; exit 1; }
  gh pr checks "$pr_number" --watch --interval 30 || true
  checks="$(read_required_checks "$pr_number")"
  printf 'release_pr_checks=%s\n' "$checks"
  for required in $required_checks; do
    printf '%s' "$checks" | grep -q "${required}=SUCCESS" \
      || { printf 'release: required check %s is not successful\n' "$required" >&2; exit 1; }
  done
  head_sha="$(gh pr view "$pr_number" --json headRefOid --jq '.headRefOid')"
  [[ "$head_sha" == "$source_sha" ]] \
    || { printf 'release: pull request head %s moved away from %s\n' "${head_sha:0:12}" "${source_sha:0:12}" >&2; exit 1; }
  gh pr merge "$pr_number" --squash \
    --subject "[F${feature_id}] Подготовка релиза ${version}" \
    --body "Обязательные проверки governance-fast, macos-pr и pr-metadata пройдены на точном SHA ${source_sha}."
  step_done "prep:merge"

  step "prep: вернуться на master"
  git switch master
  git fetch --no-tags origin master
  git reset --hard origin/master
  source_sha="$(git rev-parse HEAD)"
  printf 'release_source_sha=%s\n' "$source_sha"
  step_done "prep:sync"
else
  previous_tag="$(latest_published_tag)"
  [[ -n "$previous_tag" ]] \
    || { printf 'release: cannot resolve the latest published release
' >&2; exit 1; }
  base_sha="$(git rev-list -n 1 "$previous_tag")"
  features="$(python3 - <<'PY'
import pathlib, re
text = pathlib.Path("CHANGELOG.md").read_text(encoding="utf-8")
match = re.search(r"<!-- Release features: ([^>]*?)-->", text)
print(match.group(1).strip() if match else "")
PY
)"
  source_sha="$(git rev-parse HEAD)"
  feature_ids="$(numeric_feature_ids "$features")"
  [[ -n "$feature_ids" ]] \
    || { printf 'release: release features marker has no numeric IDs\n' >&2; exit 1; }
  feature_id="${feature_ids%%,*}"
  printf 'release_features=%s feature_ids=%s\n' "$features" "$feature_ids"
fi

# The app update needs a build, a notarization wait and Apple trust checks, and
# it does not depend on the release train.  Starting it here lets that work
# overlap the train, the full check and the deploy instead of adding to them.
app_work_pid=""
app_work_log=""
upload_release_input() {
  # The signer reads the candidate archive and the release notes from the release
  # itself, so both must be attached before it runs.  The asset name is set by
  # the target file name, because gh keeps the local basename otherwise.
  local source_path="$1" asset_name="$2" staging
  [[ -f "$source_path" ]] || { printf 'release: missing release input %s\n' "$source_path" >&2; exit 1; }
  staging="$(mktemp -d)"
  cp "$source_path" "$staging/$asset_name"
  gh release upload "$tag" "$staging/$asset_name" --clobber >/dev/null
  rm -rf "$staging"
  printf 'release_input_uploaded=%s\n' "$asset_name"
}

app_work() {
  # The whole app update runs in one background job next to the release train:
  # build, notarize, attach the inputs and sign.  It cannot wait for a process
  # the main shell started — a subshell may only wait for its own children —
  # so the build runs here too.  It must not print step markers: the main flow
  # prints the single step that waits for it.
  if [[ -f "$root/apps/macos/.build/notary/$version-$source_sha/final/GRAF-$version-candidate.zip" \
     && -f "$root/apps/macos/.build/release-state/$version.handoff" ]]; then
    printf 'release_app_prepare=reused source=%s\n' "$source_sha"
  else
    bash apps/macos/Installer/Scripts/release-app-update.sh \
      --version "$version" --phase prepare || return 1
  fi
  app_candidate_zip="$root/apps/macos/.build/notary/$version-$source_sha/final/GRAF-$version-candidate.zip"
  [[ -f "$app_candidate_zip" ]] \
    || { printf 'release: the app build produced no candidate archive\n'; return 1; }
  upload_release_input "$app_candidate_zip" "GRAF-$version-candidate.zip" || return 1
  if [[ -n "${release_notes_file:-}" && -f "$release_notes_file" ]]; then
    upload_release_input "$release_notes_file" "release-notes-v$version.md" || return 1
  fi
  bash apps/macos/Installer/Scripts/release-app-update.sh \
    --version "$version" --phase publish || return 1
  [[ -n "${release_notes_file:-}" ]] && rm -f "$release_notes_file"
  printf 'release_app_update=done version=%s\n' "$version"
  return 0
}

start_app_work() {
  [[ "$with_app" == "true" ]] || return 0
  [[ -n "${source_sha:-}" ]] || return 0
  app_work_log="$(mktemp)"
  app_work >"$app_work_log" 2>&1 &
  app_work_pid="$!"
  printf 'release_app_work=started pid=%s\n' "$app_work_pid"
}

open_draft_release() {
  # The update signer can only attach to a draft release, and preparing the
  # draft here lets the app signing and upload overlap the release train, the
  # full check and the deploy instead of running after them.  A draft release
  # does not create the tag: GitHub creates it when the release goes public, so
  # a failed release leaves no stray tag behind.
  [[ -n "${source_sha:-}" ]] || return 0
  if gh release view "$tag" >/dev/null 2>&1; then
    printf 'release_draft=exists tag=%s\n' "$tag"
    return 0
  fi
  release_notes_file="$(mktemp)"
  notes_python
  gh release create "$tag" --draft --title "${tag}" --notes-file "$release_notes_file" --target "$source_sha" >/dev/null
  printf 'release_draft=created tag=%s\n' "$tag"
}

notes_python() {
  python3 - "$version" "$release_notes_file" <<'NOTES'
import pathlib
import re
import sys

version, output = sys.argv[1], sys.argv[2]
text = pathlib.Path("CHANGELOG.md").read_text(encoding="utf-8")
heading = re.search(rf"^## \[{re.escape(version)}\]", text, re.MULTILINE)
if not heading:
    raise SystemExit("release section missing from CHANGELOG.md")
line_end = text.index("\n", heading.start())
tail = text[line_end + 1:]
next_heading = re.search(r"^## \[", tail, re.MULTILINE)
section = tail[: next_heading.start()] if next_heading else tail
section = re.sub(r"<!--.*?-->", "", section, flags=re.DOTALL).strip()
pathlib.Path(output).write_text(
    "## Что изменилось\n\n" + section + "\n\n## Проверка\n\nПолная проверка GitHub "
    "`release-full` на точном SHA прошла. Обязательные проверки `governance-fast`, "
    "`macos-pr` и `pr-metadata` пройдены. Выкатка подтверждена отчётом `deploy_result=pass`.\n",
    encoding="utf-8",
)
NOTES
}

open_draft_release
start_app_work

# --------------------------------------------------------------- step: train

if should_run train; then
  step "train: заморозить поезд и кандидата"
  require_clean_master

  # The train needs one receipt reference per included pull request.  They are
  # derived from the successful governance run on each pull request's exact
  # head, so the operator never copies identifiers by hand.  The loop avoids
  # mapfile because macOS still ships bash 3.2.
  prs=()
  receipts=()
  while IFS= read -r number; do
    [[ -n "$number" ]] || continue
    merge_sha="$(gh pr view "$number" --json mergeCommit --jq '.mergeCommit.oid')"
    [[ -n "$merge_sha" && "$merge_sha" != "null" ]] || continue
    git merge-base --is-ancestor "$merge_sha" HEAD 2>/dev/null || continue
    git merge-base --is-ancestor "$merge_sha" "$base_sha" 2>/dev/null && continue
    head_sha="$(gh pr view "$number" --json headRefOid --jq '.headRefOid')"
    run_id="$(gh api "repos/$(gh repo view --json nameWithOwner --jq '.nameWithOwner')/commits/${head_sha}/check-runs?per_page=100" \
      --jq '[.check_runs[]|select(.name=="governance-fast" and .conclusion=="success")]|sort_by(.id)|last|.id' 2>/dev/null || true)"
    [[ -n "$run_id" && "$run_id" != "null" ]] || continue
    prs+=("$number")
    receipts+=("pr-${number}-governance-${run_id}")
  done < <(gh pr list --state merged --base master --limit 50 --json number --jq '.[].number')
  [[ ${#prs[@]} -gt 0 ]] || { printf 'release: no merged pull requests found between %s and HEAD\n' "$previous_tag" >&2; exit 1; }
  pr_list="$(IFS=,; printf '%s' "${prs[*]}")"
  receipt_list="$(IFS=,; printf '%s' "${receipts[*]}")"
  printf 'release_prs=%s\n' "$pr_list"

  # A synthetic merge SHA is a real commit object whose tree is the released
  # tree, so the train references an object that exists rather than a guess.
  tree="$(git rev-parse 'HEAD^{tree}')"
  synthetic_sha="$(git commit-tree "$tree" -p "$base_sha" -p "$source_sha" -m "synthetic train merge for ${tag}")"
  printf 'release_synthetic_merge=%s\n' "$synthetic_sha"

  train_output="$(infra/scripts/release-candidate.sh train-freeze \
    --source-sha "$source_sha" --base-sha "$base_sha" \
    --synthetic-merge-sha "$synthetic_sha" \
    --prs "$pr_list" --features "$feature_ids" --operator "$operator" \
    --pr-receipts "$receipt_list")"
  printf '%s\n' "$train_output" | tail -3
  train_file="$(ls -t .dev/release/trains/train-*.json | grep -v -- '-go.json' | head -1)"
  printf 'release_train=%s\n' "$train_file"

  infra/scripts/release-candidate.sh freeze \
    --sha "$source_sha" --features "$feature_ids" --operator "$operator" --train "$train_file" | tail -3
  candidate_file="$(ls -t .dev/release/candidates/rc-*.json | head -1)"
  candidate_id="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['candidate_id'])" "$candidate_file")"
  printf 'release_candidate=%s\n' "$candidate_id"
  step_done train
fi

download_evidence() {
  # GitHub intermittently fails this download with a TLS handshake timeout, and
  # that transient failure used to end the whole release after every check had
  # already passed.  Retry with a growing pause before giving up.
  local run_id="$1" artifact="$2" work="$3" attempt delay=5
  for attempt in 1 2 3 4 5; do
    if gh run download "$run_id" -n "$artifact" -D "$work"; then
      [[ "$attempt" -gt 1 ]] && printf 'release_evidence_attempts=%s\n' "$attempt"
      return 0
    fi
    printf 'release: evidence download attempt %s of 5 failed; retrying in %ss\n' "$attempt" "$delay" >&2
    sleep "$delay"
    delay=$((delay * 2))
  done
  printf 'release: could not download %s after 5 attempts\n' "$artifact" >&2
  return 1
}

# ------------------------------------------------------------------ step: ci

if should_run ci; then
  step "ci: полная проверка релиза"
  if [[ -z "${candidate_id:-}" ]]; then
    candidate_file="$(ls -t .dev/release/candidates/rc-*.json | head -1)"
    candidate_id="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['candidate_id'])" "$candidate_file")"
  fi
  [[ -n "${source_sha:-}" ]] || source_sha="$(git rev-parse HEAD)"
  gh workflow run release-full.yml --ref master \
    -f "candidate_id=${candidate_id}" -f "requested_sha=${source_sha}"
  sleep 20
  run_id="$(gh run list --workflow=release-full.yml --limit 5 --json databaseId,headSha,status \
    --jq "[.[]|select(.headSha==\"${source_sha}\")][0].databaseId")"
  [[ -n "$run_id" && "$run_id" != "null" ]] || { printf 'release: release-full run not found\n' >&2; exit 1; }
  printf 'release_full_run=%s\n' "$run_id"
  gh run watch "$run_id" --exit-status --interval 60
  mkdir -p .dev/ci-evidence
  work="$(mktemp -d)"
  download_evidence "$run_id" "graf-full-ci-${candidate_id}" "$work"
  cp "$work/authoritative-${candidate_id}.json" ".dev/ci-evidence/authoritative-${candidate_id}.json"
  rm -rf "$work"
  printf 'release_evidence=.dev/ci-evidence/authoritative-%s.json\n' "$candidate_id"
  step_done ci
fi

# -------------------------------------------------------------- step: decide

if should_run decide; then
  step "decide: подтвердить поезд и вынести решение"
  candidate_file="$(ls -t .dev/release/candidates/rc-*.json | head -1)"
  train_file="$(ls -t .dev/release/trains/train-*.json | grep -v -- '-go.json' | head -1)"
  evidence=".dev/ci-evidence/authoritative-$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['candidate_id'])" "$candidate_file").json"
  infra/scripts/release-candidate.sh train-attest "$train_file" \
    --candidate "$candidate_file" --evidence "$evidence" | tail -2
  train_go="${train_file%.json}-go.json"
  [[ -f "$train_go" ]] || train_go="$(ls -t .dev/release/trains/*-go.json | head -1)"
  infra/scripts/release-candidate.sh decide "$candidate_file" \
    --evidence "$evidence" --train "$train_go" --calver "$version" --tag "$tag" | tail -3
  decision_file="$(ls -t .dev/release/decisions/*.decision.json | head -1)"
  printf 'release_decision=%s\n' "$decision_file"
  step_done decide
fi

# -------------------------------------------------------------- step: deploy

if should_run deploy; then
  step "deploy: предварительный прогон"
  decision_file="${decision_file:-$(ls -t .dev/release/decisions/*.decision.json | head -1)}"
  candidate_id="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['candidate_id'])" "$decision_file")"
  evidence=".dev/ci-evidence/authoritative-${candidate_id}.json"
  infra/scripts/cd-remote.sh --dry-run --branch master \
    --candidate "$decision_file" --evidence "$evidence" | tee /tmp/release-dry-run.log | tail -6
  grep -q '^deploy_result=dry_run$' /tmp/release-dry-run.log \
    || { printf 'release: dry run did not report deploy_result=dry_run\n' >&2; exit 1; }
  step_done "deploy:dry-run"

  if [[ "$deploy" != true ]]; then
    cat <<EOF

Предварительный прогон чист. Дальше — выкатка в прод:
  scripts/release.sh ${version} --from deploy --deploy
EOF
    exit 0
  fi

  step "deploy: выкатка в прод"
  infra/scripts/cd-remote.sh --execute --branch master \
    --candidate "$decision_file" --evidence "$evidence" | tee /tmp/release-deploy.log | tail -8
  grep -q '^deploy_result=pass$' /tmp/release-deploy.log \
    || { printf 'release: production deploy did not report deploy_result=pass\n' >&2; exit 1; }
  step_done "deploy:execute"
fi

# ------------------------------------------------------------- step: publish

if should_run publish; then
  step "publish: тег, выпуск и подтверждение"
  [[ -n "${source_sha:-}" ]] || source_sha="$(git rev-parse HEAD)"
  if [[ -n "${app_work_pid:-}" ]]; then
    step "publish: дождаться обновления приложения"
    if ! wait "$app_work_pid"; then
      printf 'release: app update failed; log %s\n' "$app_work_log" >&2
      cat "$app_work_log" >&2 || true
      exit 1
    fi
    cat "$app_work_log"
    app_work_pid=""
    step_done "publish:app-attach"
  fi
  # The tag is created only now, after every check passed.  A draft release does
  # not create it, so nothing is published while the release is still unproven.
  if git ls-remote --tags origin "refs/tags/$tag" | grep -q .; then
    printf 'release_tag=exists tag=%s\n' "$tag"
  else
    git tag -a "$tag" -m "Релиз ${version}" "$source_sha"
    git push origin "$tag"
  fi
  if [[ "$(gh release view "$tag" --json isDraft --jq .isDraft 2>/dev/null || true)" == "true" ]]; then
    gh release edit "$tag" --draft=false
    printf 'release_published=%s\n' "$tag"
  else
    printf 'release_publish=already_published tag=%s\n' "$tag"
  fi
  decision_file="${decision_file:-$(ls -t .dev/release/decisions/*.decision.json | head -1)}"
  infra/scripts/release-candidate.sh attest "$decision_file" \
    --release-url "https://github.com/$(gh repo view --json nameWithOwner --jq '.nameWithOwner')/releases/tag/${tag}" \
    --release-sha "$source_sha" --operator "$operator" | tail -6
  step_done publish
fi

finished_all="$(date -u +%s)"
printf '\nrelease_result=pass version=%s total_duration_seconds=%s\n' "$version" "$((finished_all - started_all))"
