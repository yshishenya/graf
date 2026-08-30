# Release And Validation

## Local Validation

Use the feature `quickstart.md` first when working inside a Spec Kit slice. For
repository-wide local validation, use one explicit lane:

```sh
# Fast feedback before a code PR.
infra/scripts/ci-local.sh --fast

# Full baseline for a release candidate or early broad diagnosis.
infra/scripts/ci-local.sh --full
```

The lane is mandatory: a bare command exits before tests instead of silently
choosing evidence strength. `--fast` derives the changed paths from the merge
base with `origin/master`: server unit tests plus the reviewed calendar/domain
source surfaces, macOS and ordinary documentation run their component checks.
High-risk backend/API surfaces, deployment evidence, infrastructure,
dependencies, migrations, contract/integration tests, shared/unknown paths or
an unavailable diff expand to `--full`. It is for iteration and PR feedback,
never a release gate. Focused tests remain the first check during implementation.

GitHub Actions are intentionally disabled for this repository. Nothing runs
automatically on a pull request: the author must run the selected local lane and
record its result in the PR. Use `--full` only for a release candidate or early
broad diagnosis; do not run it after every small edit.

Use targeted tests during development, but do not replace the feature
quickstart or canonical local gate with a narrow command when the change touches
shared behavior, privacy, auth, storage, infrastructure, user-facing flows,
UX/QA expectations, operations, release readiness, or shared code paths.

## Validation Lanes

Every change must record one risk/validation lane in the final response or PR.

- **Read-only investigation**: no tests required; report inspected sources and
  limits.
- **Docs-only / mechanical**: review the rendered wording or template diff; run
  a focused markdown/template check when one exists.
- **Tiny low-risk code**: run the focused test or lint command for the touched
  path. Add one small runnable check when the change adds non-trivial logic.
- **Active Spec Kit slice**: use `quickstart.md` and focused tests during
  development, then the fast lane before the PR. Run the full lane only for an
  early broad baseline or when a release candidate is being prepared.
- **Significant or high-risk feature**: run the feature quickstart and fast
  lane before closeout/PR; add a full baseline before release when it helps
  resolve risk early.
- **Release / deploy**: run the CD dry-run and execute only after the release
  gate is met and approved. The pinned SHA must have one valid full-CI receipt;
  `--execute` reuses matching evidence or runs the full fallback itself.

Do not rerun full local CI after every small edit inside a slice. Accumulate
focused checks while developing, use the fast lane for PR feedback, and rely on
the full exact-SHA gate during the approved production deployment.

## Development-To-Release Workflow

Use this sequence for every batch of work. A release may happen rarely; the
validation boundary does not become weaker because several changes were
accumulated.

### 1. Local development

1. Start with the feature `quickstart.md` when one exists.
2. Run focused tests for the files and behavior being changed.
3. Before calling a feature slice ready, run:

   ```sh
   infra/scripts/ci-local.sh --fast
   ```

The fast lane is the normal feedback loop. It is not a release approval and it
does not replace the full lane for a release candidate.

### 2. PR and merge

The PR must record the selected risk/validation lane, commands, result, and
commit SHA. GitHub Actions are disabled, so this evidence is supplied by the
author. Do not run full CI after every local edit or every small commit.

Before merging a significant or high-risk slice, the fast lane and the feature
quickstart must pass. If the change affects capture, privacy, auth, storage,
infrastructure, deletion, diagnostics, deployment, UX/QA expectations, or a
shared code path, focused tests alone are insufficient.

### 3. Release candidate

When the batch is approved for release, prepare the CalVer release metadata
before the final validation:

```sh
./scripts/prepare-release.sh YYYY.MM.DD.N
```

Review the changelog and release metadata, commit that release-prep change, and
use the resulting commit as the candidate. The full lane must run after this
step, because release metadata is part of what will be shipped.

Run the full lane only when a release candidate is assembled or when a broad
diagnostic is needed:

```sh
infra/scripts/ci-local.sh --full
```

The candidate is the exact commit that passed. If any code, configuration,
release metadata, or dependency lockfile changes after that run, the full result
is invalid and must be repeated. Do not use `origin/<branch>` or a moving branch
as the evidence identity; record and deploy the exact SHA.

There are two supported release paths; both finish with exactly one valid full
receipt for the unchanged candidate:

- **Economical**: run the CD dry-run, obtain approval, then let
  `cd-remote.sh --execute` perform the mandatory full fallback immediately
  before deployment and create the receipt.
- **Preflighted**: run `ci-local.sh --full` first to find issues before asking
  for production approval; `--execute` reuses its fresh exact-input receipt and
  does not repeat the same full gate.

The receipt is local metadata under the Git worktree metadata directory. It is
valid for 24 hours only when the commit, tree, CI runner, dependency lockfiles,
test surface, server collection, toolchain and complete ordered full-stage
journal still match. A clean start snapshot must still match after the last
stage, so a commit or input change during the run cannot receive a receipt. The
helper rejects direct creation from collection metadata alone. Missing, stale,
malformed or mismatched evidence never bypasses CI: deploy runs full fallback.

### 4. Production gate

Run the dry-run first:

```sh
infra/scripts/cd-remote.sh --dry-run --branch <branch>
```

After explicit production approval, run:

```sh
infra/scripts/cd-remote.sh --execute --branch <branch>
```

`--execute` requires a clean tracked-and-untracked worktree, synchronizes and
pins the SHA, validates the full-CI receipt, and runs `ci-local.sh --full` only
when that receipt is unavailable or invalid. It then proceeds to the unchanged
backup, restore rehearsal, migration/RLS, secret, deployment, health, smoke and
guarded rollback gates. `--skip-local-ci` is an incident exception only: it
requires explicit approval and a written reason for the accepted risk.

### 5. Closeout

After a successful deployment, retain metadata-only evidence for the exact SHA,
full-CI result, deploy result, health/smoke checks, and rollback status. Update
the Russian changelog and create the matching CalVer tag and GitHub Release.
Do not claim a release is complete when full CI, smoke, notarization, or
rollback evidence is missing.

### Full CI decision rule

Use this rule when deciding whether to spend the longer run:

- local edit: focused check;
- ready slice or PR: `--fast`;
- release candidate: `--full`;
- approved production execution: a valid exact-input full receipt is mandatory;
  `cd-remote.sh --execute` reuses it or runs `--full` as fallback;
- new commit after full CI: full CI must be repeated.

An interrupted run is not a passing full-CI result and cannot create a receipt.
Focused tests and the fast lane must not be counted as full CI in release
evidence. Only the load-sensitive p95 threshold may become an expected
report-only result on unrelated shared-host runs; functional assertions,
collection/setup/database/import failures always remain hard. Calendar matching
changes, an explicit controlled run, or a synchronized-master full fallback set
the timing threshold to required.

## Public macOS Signing And Migration

The active public macOS path is Developer ID-only. A releasable app uses
`Developer ID Application`, a published package uses `Developer ID Installer`,
and both artifacts require Apple notarization, stapling and Gatekeeper
acceptance. Set `GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1` for the public candidate;
the builder and validator must fail closed before public files or the appcast
change when an identity is local, self-signed, ad-hoc, owner-only or missing.

The current published reference is `v2026.07.26.8`: it passed Apple
notarization, stapling, Gatekeeper assessment and a real Developer ID →
Developer ID Sparkle update from `2026.07.26.7`. Use the [release note](../releases/v2026.07.26.8.md)
and [production receipt](../deployments/2brain-rec/release-v2026.07.26.8.md)
as the evidence template for the next release.

The published `v2026.07.26.6` is a one-time migration bootstrap from the
historical local/self-signed predecessor. Validate that transition with
`apps/macos/Installer/Scripts/validate-developer-id-bootstrap.sh` and install
the notarized `.pkg` manually. The migration validator forbids an update ZIP
and appcast; keep the live appcast unchanged for this step. After that manual
installation, use the ordinary `validate-app-updates.sh` path only with a
Developer ID predecessor and candidate, preserving bundle ID, team identity,
designated requirement, feed URL and Sparkle trust generation.

`build-trust-bootstrap.sh` and `validate-manual-update-bootstrap.sh` concern
Sparkle Ed25519 trust-generation custody/rotation. They are not Apple
code-signing migration tools. Local/self-signed/ad-hoc commands may remain in
historical receipts or disposable fixtures for negative tests, but are never a
public release fallback.

Sparkle update signing is also local-only. The active signer remains in the
named macOS Keychain account and is never exported to GitHub or a temporary key
file. Follow `docs/agent-guidance/macos-notarization.md` and run
`apps/macos/Installer/Scripts/sign-graf-app-update-local.sh` only from the clean
exact release tag on current `origin/master`.

## Dependency Updates

Use the latest stable dependency versions by default. Before adding or updating
dependencies, refresh the package index with the project package manager instead
of relying on memory or old lockfile state.

For the server app:

- update `apps/server/pyproject.toml`, `apps/server/uv.lock`, and
  `apps/server/constraints.txt` together when runtime dependencies change;
- regenerate `apps/server/constraints.txt` from the lockfile so the production
  Docker image installs the same validated runtime package set without dev
  tools;
- run `uv lock --upgrade` and `uv tree --outdated` to prove whether direct
  dependencies are current;
- avoid prerelease versions unless the user explicitly accepts that risk;
- keep an older pin only with an adjacent reason, owner, and recheck trigger.

Runtime dependency upgrades are significant maintenance when they affect backend
frameworks, auth, storage, database, infra, or shared behavior. Use the relevant
Spec Kit lane and finish with `infra/scripts/ci-local.sh --fast` before
closeout; use `--full` for the assembled release candidate.

## Production Deployment And Smoke

Deployment is remote-first and gate-driven:

```sh
infra/scripts/cd-remote.sh --dry-run
infra/scripts/cd-remote.sh --execute
```

Only run `--execute` when the release gate is met. Production deploy/smoke work
must preserve:

- clean tracked-and-untracked working tree;
- branch/ref sync with the intended remote;
- pinned commit SHA;
- backup and restore rehearsal evidence where required;
- secret scans;
- health checks and smoke evidence;
- metadata-only evidence.

Use the exact production sequence:

1. Merge reviewed PRs, then start from a clean checkout of the intended branch
   synced with `origin/<branch>`.
2. Run `infra/scripts/cd-remote.sh --dry-run --branch <branch>`.
3. Obtain explicit user approval for production.
4. Run `infra/scripts/cd-remote.sh --execute --branch <branch>`. It validates a
   fresh full receipt for the pinned commit or runs
   `infra/scripts/ci-local.sh --full` as the safe fallback before remote backup,
   migration, deployment and smoke checks.

`--skip-local-ci` bypasses the full local CI only; it does not bypass production
gates. It is reserved for an explicitly approved incident response that names
the omitted check and accepted risk; it is never a normal speed optimization.

Batch small validated changes into an intentional release candidate when that
reduces repeated release overhead. Two planned release windows per day are a
useful operating rhythm, not a hard gate; an explicitly marked hotfix remains
available when production risk requires it.

## Changelog

Maintain `CHANGELOG.md` in the repository root.

Every implemented feature slice that changes behavior, architecture, UX, QA
expectations, operations, or release readiness must update `[Unreleased]` before
merge.

Keep entries grouped by:

- `Added`
- `Changed`
- `Fixed`
- `Security`
- `Docs`
- `Ops`

Include feature, issue, or task references when available.

## Versioning

Every release must have a version tag, a GitHub Release, and a human-written
Russian changelog entry. Do not ship a release from a floating branch name or
from a tag that has no release notes.

Use this versioning policy:

- Product apps, deployed services, and release-train bundles use Calendar
  Versioning: `vYYYY.MM.DD.N`, where `N` starts at `1` and increments for
  multiple releases on the same day. Example: `v2026.06.18.1`.
- Libraries, CLI tools, reusable Spec Kit extensions, bootstrap wrappers, and
  anything consumed as a dependency use Semantic Versioning:
  `vMAJOR.MINOR.PATCH`.
- Use SemVer `MAJOR` for breaking API/CLI/workflow compatibility changes,
  `MINOR` for backward-compatible features or new capabilities, and `PATCH` for
  fixes, docs, reliability, or operational quality improvements.
- Do not put a descriptive slug in the stable tag. A tag such as
  `v2026.06.18.1-release-rules` is harder to sort and may be interpreted like a
  prerelease by tooling. Put the readable postfix in the GitHub Release title
  instead, for example `v2026.06.18.1 - release-rules`.
- Use prerelease suffixes only for real prereleases: `-alpha.N`, `-beta.N`, or
  `-rc.N`.
- If a repository already has a published versioning scheme, do not switch it
  silently. Document the migration in `CHANGELOG.md`, explain why the old scheme
  no longer fits, and make the next release notes explicit.

Product release command:

```sh
./scripts/prepare-release.sh YYYY.MM.DD.N
```

For example:

```sh
./scripts/prepare-release.sh 2026.06.18.1
```

Use `patch`, `minor`, or `major` only in repositories that are intentionally
still using SemVer. In a CalVer product release train, pass the full version
explicitly so the date and same-day release counter are deliberate.

Then review `CHANGELOG.md`, commit release prep, create the matching tag, and
push the branch and tags only when the user approves the release action.

## Release Notes

Каждый GitHub Release должен быть написан простым русским языком:

- не смешивай русский текст с английским инженерным жаргоном, кроме буквальных
  названий продуктов, команд, тегов, файлов, протоколов и внешних сервисов;
- пиши для пользователя, а не для внутренней команды разработки;
- избегай внутренних терминов вроде payload, fixture, dependency,
  status/reason, review surface, metadata-safe или benchmark.

В каждом GitHub Release должны быть:

- что изменилось, простыми словами;
- влияние на совместимость или миграции;
- чем проверяли релиз;
- ссылки на запросы на слияние и задачи, если они есть;
- заметки про выкатку, откат или эксплуатацию, если это важно;
- явные ограничения и следующая работа.

## Git Safety

- Never reset or discard user changes.
- Do not auto-commit implementation code, generated build outputs, secrets, or
  unrelated changes.
- Implementation commits require explicit user approval after validation.
- Spec Kit documentation auto-commits may run only through user-approved Spec
  Kit hooks.

## Evidence Safety

Evidence must be metadata-only unless a spec explicitly allows more. Do not
commit raw audio, transcript text, credentials, tokens, signed URLs, passwords,
live local paths, private screenshots, private meeting content, or real account
identifiers.
