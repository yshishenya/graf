# Quickstart: Feature 216 governance checks

All commands below are local or read-only unless explicitly marked as a Dev
promotion. Evidence must contain metadata only: command, status, duration,
SHA, manifest IDs and counts. Never save audio, transcript text, credentials or
private meeting content.

## 1. Confirm feature and clean worktree

```sh
git status --short --branch
git rev-parse HEAD
cat .specify/feature.json
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

Expected: branch `codex/216-development-governance-harness`, feature directory
`specs/216-development-governance-harness`, and no user changes overwritten.

## 2. Validate specification and governance

```sh
rg -n 'NEEDS CLARIFICATION|TODO|\[FEATURE|\[###' \
  specs/216-development-governance-harness || true
python3 scripts/check_spec_kit_governance.py --self-test
python3 scripts/check_spec_kit_governance.py
```

Expected: no unresolved markers and positive/negative governance fixtures pass.

## 3. Verify Feature ID and issue linkage

```sh
git branch -a --list '*216*'
gh issue view 6090 --repo yshishenya/graf --json number,title,labels,url
gh issue list --repo yshishenya/graf --search '"[216]" in:title' --limit 100
```

Expected: one umbrella reservation, no duplicate active claim, and labels
`feature:216`, `priority:P0`, `area:docs/governance`, `type:hardening`.

## 4. Focused Dev harness fixture

```sh
./infra/scripts/dev-harness.sh build --sha "$(git rev-parse HEAD)" --dry-run
./infra/scripts/dev-harness.sh status --json
./infra/scripts/dev-harness.sh smoke --json --fixture
./infra/scripts/dev-harness.sh promote --manifest /path/to/fixture.json --dry-run
./infra/scripts/dev-harness.sh rollback --dry-run
```

Expected: commands fail closed when no valid manifest exists and never target a
production origin. Once implemented, a synthetic candidate must show one SHA
across backend/frontend/app and a rollback target.

## 5. Dev app identity

```sh
sh apps/macos/Scripts/validate-no-legacy-audio-driver.sh
sh apps/macos/Scripts/validate-macos-permission-retention.sh
```

When a local build is intentionally run, use only the existing Dev scripts with
a loopback origin. Verify `pro.2brain.graf.dev`, the same designated requirement
and atomic replacement; do not run public release/notarization commands here.

## 6. CI feedback gate

```sh
infra/scripts/ci-local.sh --fast
```

Record the exact SHA, effective lane, result and skipped gates in the PR. Each
run also emits metadata-only evidence under `.dev/ci-evidence/` and prints its
path as `ci_evidence_path=...`. Do not run `--full` for every edit. Full CI is
reserved for a frozen release candidate; set `GRAF_CI_CANDIDATE_FILE` for that
run and retain the printed evidence path. Evidence is invalid if the SHA
changes afterward.

## 7. Changelog and legacy checks

```sh
python3 scripts/validate-changelog-fragments.py
python3 scripts/validate-legacy-impact.py \
  --feature specs/216-development-governance-harness/spec.md
```

Expected: Feature 216 owns one fragment, the root changelog is untouched during
feature work, Legacy Impact is present, and no exception is expired or ownerless.

## 8. Reusable harness sample project

The generic core is published at
`https://github.com/yshishenya/graf-development-harness/releases/tag/v0.1.4`.
Clone that immutable tag into a clean temporary sample and run:

```sh
(cd harness/sample && ../bin/harness-check --spec specs/001-example/spec.md)
```

Record the release tag, commit SHA, tool versions and pass/fail counts. This
step must not include GRAF credentials, private paths or meeting content.

## Release-candidate boundary

Only after all feature tasks, reviewer checklists and convergence are complete:

1. prepare a CalVer candidate and review the assembled Russian changelog;
2. freeze the exact SHA and metadata digest;
3. run one authoritative Full CI;
4. run CD dry-run and obtain explicit approval before any production execute;
5. publish tag/GitHub Release and retain metadata-only evidence.
