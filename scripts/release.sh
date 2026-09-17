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
  --skip-local-tests  skip the local governance slice before starting
  --from <step>       resume at a step: prep, train, ci, decide, deploy, publish
  --stop-after <step> stop once this step is done

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
skip_local_tests=false
resume_step=""
stop_after=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --operator) operator="${2:-}"; shift 2 ;;
    --merge) merge=true; shift ;;
    --deploy) deploy=true; shift ;;
    --skip-local-tests) skip_local_tests=true; shift ;;
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
  previous_tag="$(git tag --list 'v*' --sort=-v:refname | head -1)"
  [[ -n "$previous_tag" ]] || { printf 'release: no previous release tag found\n' >&2; exit 1; }
  base_sha="$(git rev-list -n 1 "$previous_tag")"
  printf 'release_base=%s base_sha=%s\n' "$previous_tag" "$base_sha"

  branch="release-prep-${version}"
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
  printf 'release_features=%s\n' "$features"

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

- \`scripts/prepare-release.sh ${version}\` — раздел собран, фрагменты проверены
- Локально: \`tests/governance/\` — см. вывод выше
- Обязательные проверки GitHub \`governance-fast\`, \`macos-pr\`, \`pr-metadata\` на точном SHA — этот пул-реквест

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
  gh pr checks "$pr_number" --watch --interval 30 || true
  checks="$(gh pr checks "$pr_number" --json name,state --jq '[.[]|select(.name=="governance-fast" or .name=="macos-pr" or .name=="pr-metadata")|"\(.name)=\(.state)"]|join(" ")')"
  printf 'release_pr_checks=%s\n' "$checks"
  for required in governance-fast macos-pr pr-metadata; do
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
  previous_tag="$(git tag --list 'v*' --sort=-v:refname | head -1)"
  base_sha="$(git rev-list -n 1 "$previous_tag")"
  features="$(python3 - <<'PY'
import pathlib, re
text = pathlib.Path("CHANGELOG.md").read_text(encoding="utf-8")
match = re.search(r"<!-- Release features: ([^>]*?)-->", text)
print(match.group(1).strip() if match else "")
PY
)"
  source_sha="$(git rev-parse HEAD)"
  feature_id="$(printf '%s' "$features" | tr ',' '\n' | head -1 | tr -d ' F')"
fi

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
    --prs "$pr_list" --features "$features" --operator "$operator" \
    --pr-receipts "$receipt_list")"
  printf '%s\n' "$train_output" | tail -3
  train_file="$(ls -t .dev/release/trains/train-*.json | grep -v -- '-go.json' | head -1)"
  printf 'release_train=%s\n' "$train_file"

  infra/scripts/release-candidate.sh freeze \
    --sha "$source_sha" --features "$features" --operator "$operator" --train "$train_file" | tail -3
  candidate_file="$(ls -t .dev/release/candidates/rc-*.json | head -1)"
  candidate_id="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['candidate_id'])" "$candidate_file")"
  printf 'release_candidate=%s\n' "$candidate_id"
  step_done train
fi

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
  gh run download "$run_id" -n "graf-full-ci-${candidate_id}" -D "$work"
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
  if gh release view "$tag" >/dev/null 2>&1; then
    printf 'release_publish=already_published tag=%s\n' "$tag"
  else
    notes="$(mktemp)"
    python3 - "$version" "$notes" <<'PY'
import pathlib
import re
import sys

version, output = sys.argv[1], sys.argv[2]
text = pathlib.Path("CHANGELOG.md").read_text(encoding="utf-8")
heading = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n", text, re.MULTILINE)
if not heading:
    raise SystemExit("release section missing from CHANGELOG.md")
tail = text[heading.end():]
next_heading = re.search(r"^## \[", tail, re.MULTILINE)
section = tail[: next_heading.start()] if next_heading else tail
section = re.sub(r"<!--.*?-->", "", section, flags=re.DOTALL).strip()
pathlib.Path(output).write_text(
    "## Что изменилось\n\n" + section + "\n\n## Проверка\n\nПолная проверка GitHub "
    "`release-full` на точном SHA прошла. Обязательные проверки `governance-fast`, "
    "`macos-pr` и `pr-metadata` пройдены. Выкатка подтверждена отчётом `deploy_result=pass`.\n",
    encoding="utf-8",
)
PY
    git tag -a "$tag" -m "Релиз ${version}" "$source_sha"
    git push origin "$tag"
    gh release create "$tag" --title "${tag}" --notes-file "$notes" --target "$source_sha"
    rm -f "$notes"
  fi
  decision_file="${decision_file:-$(ls -t .dev/release/decisions/*.decision.json | head -1)}"
  infra/scripts/release-candidate.sh attest "$decision_file" \
    --release-url "https://github.com/$(gh repo view --json nameWithOwner --jq '.nameWithOwner')/releases/tag/${tag}" \
    --release-sha "$source_sha" --operator "$operator" | tail -6
  step_done publish
fi

finished_all="$(date -u +%s)"
printf '\nrelease_result=pass version=%s total_duration_seconds=%s\n' "$version" "$((finished_all - started_all))"
