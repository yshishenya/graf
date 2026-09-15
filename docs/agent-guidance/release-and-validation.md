# Release And Validation

## Local Validation (manual fallback)

Use the feature `quickstart.md` first when working inside a Spec Kit slice.
For cabinet/settings changes, the shared selection can be inspected and run
locally before creating a PR:

```sh
infra/scripts/ci-local.sh --plan
infra/scripts/ci-local.sh --focused
```

The plan reads the existing Git diff and lists related groups, environment and
partial coverage without starting tests, Docker, an app, dependency installation
or network access. Focused uses an already prepared `apps/server/.venv` and
Node.js; prepare that checkout once with `uv sync --frozen --extra dev` from
`apps/server` if needed. It accepts dirty changes as local diagnostics, emits no
CI receipt and does not replace the exact-SHA GitHub check. Empty/unmatched
focused selection fails with guidance to the feature quickstart. Missing,
empty or skipped mandatory proof fails. The same map adds these checks to fast
while retaining its unit/changed/performance safety sets without repeating
mapped files. Mapping scope and validation: `specs/211-optimize-ci-cd/quickstart.md`.

The workstation does not run repository-wide CI automatically. For explicit
diagnosis or offline fallback, use one local lane:

```sh
# Optional bounded diagnosis or offline fallback.
infra/scripts/ci-local.sh --fast

# Optional broad local diagnosis, never authoritative release evidence.
infra/scripts/ci-local.sh --full
```

The lane is mandatory: a bare command exits before tests instead of silently
choosing evidence strength. `--fast` derives the changed paths from the merge
base with `GRAF_CI_BASE_REF` (default `origin/master` locally) and always remains bounded:
server, macOS,
infrastructure/tooling and documentation run their component checks; changed
server contract/integration files run focused. Calendar performance paths run a
focused required proof without changing the lane; a missing/renamed proof is
reported as partial instead of being passed to pytest. Deployment evidence runs
its dedicated secret/verdict scanner in fast. Shared/high-risk/unknown
paths or an unavailable diff report `coverage=partial` and
`next_gate=full_before_release` instead of silently starting the full suite.
Shared governance documents use the same partial marker, and the whitespace
stage covers both committed/working-tree changes and selected untracked files.
Canonical `changes/unreleased/F<digits>.yaml` and
`changes/releases/vYYYY.MM.DD.N/F<digits>.yaml` are metadata paths: adding the
required fragment or archiving it does not select infrastructure tests by
itself. Product and infrastructure changes still select their applicable tests.
The existing process preflight always runs, including clean PR/release
checkouts without `.specify/feature.json`; it validates unreleased fragments
and changed specifications. Archive validation remains in `prepare-release.sh`.
Fast is for iteration and PR feedback, never a release gate. Focused tests
remain the first check during implementation.

GitHub requires `governance-fast`, `macos-pr` and `pr-metadata` for every PR.
Code and native results bind the exact head and checked base; metadata binds the
current description to the same identity. Local focused tests remain the normal
development loop. Local `ci-local.sh --fast` / `--full` are optional diagnostics,
not additional pre-PR gates. One complete GitHub `release-full` remains required
for the frozen release candidate.

For PR and `merge_group` runs, the workflow pins `GRAF_CI_BASE_REF` to the
event `base_sha` recorded in the receipt. Missing, invalid or unavailable bases
and a missing merge base fail before tests; moving `origin/master` cannot change
the selected diff. Manual dispatch retains a null event base and diagnostic
default selection, not PR/merge-group provenance. Server lint and compile run
once before selected server tests with the same commands and scope; a static
failure stops before those tests. Proven title/body-only edits run a cheap scope
step, trusted metadata and source-proof verification in the existing fixed-name
`governance-fast` and `macos-pr` checks. They do not enter code-job concurrency,
install test resources, repeat product tests or create new source receipts.
Scope and text-reuse tools come from the exact running workflow SHA in a
separate sparse checkout; Git still reads the exact primary PR head, including
older heads that do not contain the newer helpers. For a merged PR, text scope and reuse recover the checked base from the actual
linear squash/rebase history and retain the real merge SHA; advancing master
does not invalidate that immutable history. The fixed-name check passes only after verifying the latest actual source
execution for the exact PR/head/base, workflow and run attempt. A running source
may be waited on within the job's timeout; failure, cancellation, timeout,
missing/expired proof or an API error fails the text check without an older-success fallback.
Retarget, empty/unknown changes and code edits retain the complete applicable checks.

This reuse requires the workflow version selected by GitHub to contain the F211
cutover. Editing a historical merged PR can execute its older workflow, even
after master has advanced. Record closeout for such PRs in issue comments and
release evidence without editing their title/body. Do not weaken current-check
validation or claim that the newer workflow ran for a historical event.

The required metadata check uses `pull_request_target` from the trusted `github.workflow_sha`. The validator
runs in isolated Python; it only reads PR Git objects and never checks out or
executes PR code. Two API snapshots must agree on repository, PR, head/base/ref,
state/merge identity and title/body digest. Its separate concurrency cancels only
older metadata runs. A snapshot PASS is not atomic merge-time approval. API,
identity, history and policy errors fail; no stale event-text fallback exists.
Evidence contains identity/digests only and is retained for 90 days. A merged
PR's checked base comes from its exact linear squash/rebase history, rather
than today's master; closed/unmerged PRs are rejected.

The required `macos-pr` checks the exact diff conservatively. Swift build,
tests and ContractValidation run for native/API/cabinet/shared/unknown changes;
only proven independent paths can omit native execution. If the exact scope
requires native execution, a skipped execution fails the required check. Proven
title/body-only events retain the `macos-pr` required name and verify the actual
native source proof on Ubuntu. They never enter native execution concurrency,
including when a retarget check is already running. Verified text scopes are
excluded from source selection even while their result jobs are running, so
text checks neither become new source proofs nor wait on each other.

The three required contexts were activated on 2026-09-13 at 13:18:40 UTC,
after foundation PR #6987 merged as `a3f5f72e994e7872ee175ebafd9f7699a2d4ffca`.
Strict base freshness, app IDs and linear history remain enabled. The canonical
activation record is `.github/pr-check-policy.json`. Code receipts, native scope
and metadata artifacts are retained for 90 days. Before merging or accepting
closeout evidence, use the common current-check validator:

```sh
python3 scripts/validate-pr-checks.py --repository yshishenya/graf --pr <number>
```

It validates both the actual source proofs and the latest corresponding required
gate runs, including title/body runs. Each gate needs exactly one successful job
with its fixed required name. Source selection uses actual execution time/run ID
and attempt, never the latest success. Before PASS, it rechecks every selected
source and gate attempt as well as the current PR identity. It rejects missing,
expired, unsuccessful, stale or mixed-attempt proof, including a later failed
rerun of an older run ID. New governance artifacts include run ID and attempt.
The former artifact name is read only if the exact name is absent, the legacy
artifact is unique/unexpired and its internal run/attempt matches. A merged PR must match its actual squash
or linear-rebase history and final tree. Only PRs merged before the recorded
activation use historical combined evidence; old open PRs receive no exemption.
Release freeze/decision verifies the PR range after the latest published stable
GitHub Release; train input must cover that actual range. These operations read
existing results and do not execute product tests. The personal repository keeps
serial merges because native merge queue is unavailable.

For an iterative macOS-only failure, manually dispatch `macos-diagnostic` on
the exact SHA instead of rerunning `release-full`. It runs no server-full job,
publishes no authoritative evidence and cannot approve a release. After the
macOS problem is resolved, the frozen candidate still needs exactly one complete
`release-full` with both server and macOS components.

After Feature 227 is merged and the operator has enabled the required checks,
the remote workflow must validate PR and `merge_group` target identity before
merge-queue enforcement. A synthetic merge SHA is provenance only; the release
candidate is frozen on the resulting exact `master` SHA.

For a batched release window, first resolve the latest published non-draft,
non-prerelease GitHub Release by `publishedAt`; its tag is the only valid base
for the included commit/PR range. A newer local tag or prepared changelog
heading is not a release. Create a metadata-only train manifest with
`infra/scripts/release-candidate.sh train-freeze`, then run
`train-validate <manifest> --current`. A train must include the synthetic
merge SHA, post-merge `source_sha`, included PRs, Feature IDs, receipt
references and the changelog digest. Freeze the linked candidate with
`freeze ... --train <manifest>`, run the one authoritative Full CI, and bind
that receipt with `train-attest <manifest> --candidate <candidate> --evidence
.dev/ci-evidence/authoritative-<candidate-id>.json`. Only the resulting
`*-go.json` train may be passed to
`decide ... --train <train-go>`. Every record is create-once; if `master` or
the changelog changes, validation fails and a new train must be frozen.

Use targeted tests during development, but do not replace the feature
quickstart or canonical GitHub gate with a narrow command when the change touches
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
  development, then require GitHub `governance-fast`, `macos-pr` and `pr-metadata` on exact PR SHA. Local
  wide lanes are diagnostic/fallback only; release uses GitHub `release-full`.
- **Significant or high-risk feature**: run focused quickstart/domain checks
  and require GitHub `governance-fast`, `macos-pr` and `pr-metadata` on exact PR SHA before merge. A local
  broad diagnostic is optional when needed to investigate risk, not a second
  routine gate and not authoritative release evidence.
- **Release / deploy**: run the CD dry-run and execute only after the release
  gate is met and approved. The release operator runs exactly one authoritative
  Full CI for the frozen candidate before `decide`; `--execute` synchronizes the
  approved SHA and verifies/reuses that immutable evidence before remote
  production actions. It must not launch a second Full CI for the same candidate.
  Dry-run reports `local_ci=authoritative_full_required` until a validated candidate
  is supplied, then `local_ci=authoritative_full_reused`; this is the existing
  GitHub evidence gate, not another local test run.

Do not rerun full local CI after every small edit inside a slice. Accumulate
focused checks while developing, use required GitHub fast for PR feedback, and
rely on the full exact-SHA gate during the approved production deployment.

## Development-To-Release Workflow

Use this sequence for every batch of work. A release may happen rarely; the
validation boundary does not become weaker because several changes were
accumulated.

### 1. Local development

1. Start with the feature `quickstart.md` when one exists.
2. Run focused tests for the files and behavior being changed.
3. Push the branch and wait for all three required GitHub checks;
   local CI is a manual fallback only.

Focused local checks and required GitHub fast form the normal feedback loop.
Fast is not a release approval and does not replace the full lane for a release
candidate.

### 2. PR and merge

Перед отправкой PR проверь его описание локально на финальном SHA:

```sh
python3 scripts/validate-pr-metadata.py /path/to/pr-body.md \
  --feature-id scoped --scoped \
  --expected-sha <полный-40-символьный-SHA> \
  --title "<точный заголовок PR>"
```

Строка `Exact source SHA` должна быть отдельной строкой вида
`- Exact source SHA: \`<40 hex>\`` без точки, запятой или другого текста после
закрывающего обратного апострофа. После каждого нового коммита SHA в описании
нужно обновить и дождаться всех обязательных GitHub checks; старая проверка не
доказывает корректность нового SHA.

The PR must record the selected risk/validation lane, commands, result, and
commit SHA. The required `governance-fast`, `macos-pr` and `pr-metadata` GitHub checks must agree
on that exact SHA and checked base; local evidence may supplement it but cannot replace it. Do not
run full CI after every local edit or every small commit.

Before merging a significant or high-risk slice, required GitHub fast and the feature
quickstart must pass. If the change affects capture, privacy, auth, storage,
infrastructure, deletion, diagnostics, deployment, UX/QA expectations, or a
shared code path, focused tests alone are insufficient.

### 3. Release candidate

When the batch is approved for release, confirm the latest published GitHub
Release and prepare the CalVer release metadata before the final validation:

```sh
GRAF_RELEASE_OPERATOR=<release-operator> ./scripts/prepare-release.sh YYYY.MM.DD.N
```

`prepare-release.sh` queries GitHub and folds every later prepared-but-
unpublished changelog section and its archived fragments into this one release.
It fails closed when an entry has no matching fragment or one Feature ID has
multiple pending fragments; merge the duplicate fragments explicitly and rerun.

Review the changelog and release metadata, commit that release-prep change, and
use the resulting commit as the candidate. The full lane must run after this
step, because release metadata is part of what will be shipped.

The release operator may make one follow-up metadata-only commit after that
preparation when a release note must be corrected before freezing the candidate.
The source validator accepts this exception only when the commit has one parent,
its subject identifies release notes, and its complete diff contains only
`CHANGELOG.md` plus modified archived fragments under one
`changes/releases/vYYYY.MM.DD.N/` directory. The fragment version must equal
the newest release section in `CHANGELOG.md`; its `feature_id` must match the
`F<id>.yaml` name and the release feature marker; structural fields (`schema`,
feature, issue, tasks and category) must be unchanged. Only prose fields may
change, and added lines are checked for private paths, credentials and other
forbidden content. A changed heading, feature marker, old release fragment,
code path, added/deleted/renamed file or failed content check is a no-go and
requires a normal PR. The exception does not add a PR to the train: the train
still lists every merged PR, and the metadata commit remains part of the exact
source SHA and changelog digest.

Freeze the exact release boundary before starting Full CI:

    infra/scripts/release-candidate.sh freeze \
      --sha <exact-HEAD-40-hex> \
      --features <feature[,feature,...]> \
      --operator <release-operator> \
      --output .dev/release/candidates/rc-<sha12>.json
    infra/scripts/release-candidate.sh validate \
      .dev/release/candidates/rc-<sha12>.json --current

\`freeze\` requires a clean checkout, records the exact HEAD and changelog
digest, and refuses to overwrite an existing candidate. It never creates a tag
or GitHub Release. Full evidence must include \`candidate_id\`,
\`authoritative_full=true\`, component SHA checks and artifact digests. Attach
that evidence to a separate immutable decision record:

    infra/scripts/release-candidate.sh decide .dev/release/candidates/rc-<sha12>.json \
      --evidence .dev/ci-evidence/authoritative-<candidate-id>.json \
      --calver YYYY.MM.DD.N \
      --output .dev/release/decisions/<candidate-id>.decision.json

`decide` validates the Full CI evidence, checks its candidate ID and exact SHA,
and writes a separate create-once decision record; it never overwrites the
frozen candidate. Only `go` from this decision record may proceed to tag/release
preparation. A failed, stale, interrupted or mismatched run produces `no-go`.
Changed HEAD or changelog, a failed/interrupted run, a component mismatch, or
skipped gates produces \`no-go\`; create a new candidate after correction.

After the GitHub Release is published, record the immutable link without
editing either the candidate or decision:

```sh
infra/scripts/release-candidate.sh attest \
  .dev/release/decisions/<candidate-id>.decision.json \
  --release-url https://github.com/<owner>/<repo>/releases/tag/vYYYY.MM.DD.N \
  --release-sha <exact-tag-commit-40-hex> \
  --operator <release-operator> \
  --output .dev/release/attestations/<candidate-id>.publication.json
```

The command resolves the repository from `origin`, queries GitHub to confirm
that the non-draft Release and tag exist, and verifies that the tag resolves
to the approved commit before creating a write-once attestation. The schema is
`infra/release/publication-attestation.schema.json`.

Download the successful GitHub artifact `graf-full-ci-<candidate-id>` and keep
its authoritative record only at
`.dev/ci-evidence/authoritative-<candidate-id>.json`. This is the sole path
accepted by `train-attest`, `decide` and production execution. The artifact is
create-once; never rename a local diagnostic receipt into this path.

The producer records the requested/start/end SHA, run identity, timestamps,
lane, commands, scope, skipped gates, component SHAs and artifact digests.
The record is written atomically and remains invalid for release if the target
SHA changes, a stage fails, or the run is interrupted. It contains metadata
only: never add logs, credentials, raw audio, transcripts or private paths.

Run the local full lane directly only for broad diagnosis:

```sh
infra/scripts/ci-local.sh --full
```

The local full lane is always diagnostic, even when `GRAF_CI_CANDIDATE_FILE` is
set. It never creates authoritative candidate evidence or a `release_ready`
result. The normal release path does not run a separate local preflight full;
GitHub `release-full` is the only authoritative Full CI source. After review
and merge, run the CD dry-run and pass the immutable decision record explicitly
to the execute step:

For a train-linked decision, `train-attest` and `decide` resolve the cited
GitHub run, require the successful `workflow_dispatch` execution of
`.github/workflows/release-full.yml` on the exact candidate SHA, and verify its
live `graf-full-ci-<candidate-id>` artifact.

```sh
infra/scripts/cd-remote.sh --dry-run --branch master
infra/scripts/cd-remote.sh --execute --branch master \
  --candidate .dev/release/decisions/<candidate-id>.decision.json \
  --evidence .dev/ci-evidence/authoritative-<candidate-id>.json
```

The execute step synchronizes and pins the exact SHA, then re-checks the
unchanged worktree/local/remote SHA immediately before remote production
actions. Release candidates and decisions are operator evidence and should
remain under the ignored `.dev/release/` path (or an explicit external evidence
directory). A direct full run prints `next_gate=full_diagnostic_only` when no
candidate is supplied; it remains available for diagnosis, but it is not the
authoritative release run.

### 4. Production gate

Run the dry-run first:

```sh
infra/scripts/cd-remote.sh --dry-run --branch <branch>
```

After explicit production approval, run:

```sh
infra/scripts/cd-remote.sh --execute --branch master \
  --candidate .dev/release/decisions/<candidate-id>.decision.json \
  --evidence .dev/ci-evidence/authoritative-<candidate-id>.json
```

For a production execution, pass the immutable decision record:

```sh
infra/scripts/cd-remote.sh --execute --branch master \
  --candidate .dev/release/decisions/<candidate-id>.decision.json \
  --evidence .dev/ci-evidence/authoritative-<candidate-id>.json
```

Для production `--execute` обязательно передаётся `--candidate
<candidate.decision.json>` (или задаётся `GRAF_RELEASE_CANDIDATE`). Скрипт
проверяет текущий SHA и changelog digest, затем допускает только decision
`status=go`; frozen/no-go/stale candidate блокируется до удалённых действий.

`--execute` requires a clean tracked-and-untracked worktree, synchronizes and
pins the SHA, verifies the candidate's immutable Full CI evidence digest, and
only then proceeds to the unchanged backup, restore rehearsal, migration/RLS,
secret, deployment, health, smoke and guarded rollback gates. It does not run a
second Full CI for a candidate that already has authoritative evidence.
`--skip-local-ci` is an incident exception only: it requires
`--skip-local-ci-evidence <json>` containing non-empty `reason`, `approved_by`
and `approved_at` fields. The evidence is machine-readable and must identify
the accepted risk; it never bypasses candidate, SHA or production gates.

### 5. Closeout

After a successful deployment, retain metadata-only evidence for the exact SHA,
full-CI result, deploy result, health/smoke checks, and rollback status. Update
the Russian changelog and create the matching CalVer tag and GitHub Release.
Do not claim a release is complete when full CI, smoke, notarization, or
rollback evidence is missing.

Before closing a feature umbrella, run the live feature inventory mode of
`scripts/validate-issue-closeout.py` with the feature label, umbrella number,
`tasks.md`, exact candidate SHA and `--require-release-full`. Close task-backed issues first with both
GitHub run URLs, close the umbrella last, then rerun without
`--allow-open-umbrella`.

### Full CI decision rule

Use this rule when deciding whether to spend the longer run:

- local edit: focused check;
- ready slice or PR: required GitHub `governance-fast`, `macos-pr` and `pr-metadata` on exact PR SHA;
- release candidate: reviewed and merged exact SHA;
- approved production execution: `cd-remote.sh --execute` verifies the one
  authoritative Full CI evidence record after synchronization and before remote
  actions;
- direct `--full` before execute: diagnostic only and not a release attestation.

An interrupted run is not a passing full-CI result.
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

Server CD preserves an existing regular, nonempty runtime `graf.pkg`; its
public-download smoke verifies those preserved bytes. Only an absent runtime
file uses the tracked package for initial installation and rollback. Publish
new macOS packages through the runtime directory as specified in
`macos-notarization.md`, keeping the tracked source tree clean. Public static
version URLs use file identity to invalidate the bounded hash cache when the
canonical package is atomically replaced.

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
Spec Kit lane, run focused checks locally and require GitHub `governance-fast`
on exact PR SHA before merge. Local wide fast is diagnostic/fallback only.
The fast result remains bounded and requires the separate exact-SHA
full gate before release.

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
4. Run `infra/scripts/cd-remote.sh --execute --branch <branch> \
   --candidate .dev/release/decisions/<candidate-id>.decision.json \
   --evidence .dev/ci-evidence/authoritative-<candidate-id>.json`. It verifies the immutable
   Full CI record on the pinned commit before remote backup, migration,
   deployment and smoke checks.

`--skip-local-ci` bypasses the local Full CI invocation only; it does not bypass
production gates. It is reserved for an explicitly approved incident response
with machine-readable `--skip-local-ci-evidence <json>`; it is never a normal
speed optimization.

Batch small validated changes into an intentional release candidate when that
reduces repeated release overhead. Two planned release windows per day are a
useful operating rhythm, not a hard gate; an explicitly marked hotfix remains
available when production risk requires it.

### Release-train checklist

- [ ] Release window, owner and included Feature IDs are recorded.
- [ ] Each included PR has fast evidence on its own exact SHA.
- [ ] \`prepare-release.sh YYYY.MM.DD.N\` assembled fragments and passed CalVer,
      Russian notes, compatibility, limitations and rollback review.
- [ ] \`release-candidate.sh freeze\` produced one immutable candidate manifest.
- [ ] Exactly one authoritative Full CI identity passed for that candidate;
      stale, cancelled, ambiguous and skipped-gate results do not qualify.
- [ ] Candidate SHA and changelog digest are unchanged after Full CI.
- [ ] CD dry-run passed; production execute and tag/GitHub Release wait for
      explicit approval.

## Changelog

Maintain `CHANGELOG.md` in the repository root, but do not make it a parallel
agent write target. During feature work each agent owns one
`changes/unreleased/F<feature-id>.yaml` fragment. The release operator alone
assembles fragments into `[Unreleased]` while freezing a release candidate.

Every implemented feature slice that changes behavior, architecture, UX, QA
expectations, operations, or release readiness must update its fragment before
merge. The fragment must contain a category, Russian summary, Feature ID,
issue/task links, compatibility impact and known limitations. The root file is
updated only by the release operator, preserving one writer and conflict-free
parallel work.

The release operator bases the batch on the latest actually published GitHub
Release. Prepared sections without a published non-draft, non-prerelease
Release are still unreleased and are folded into the next CalVer section.

Keep entries grouped by:

- `Added`
- `Changed`
- `Fixed`
- `Security`
- `Docs`
- `Ops`

Include feature, issue, or task references when available.

## Legacy Definition of Done

Every feature and PR must include a `Legacy Impact` classification (`remove`,
`retain-with-exception` or `untouched`). New aliases, fallback names, flags,
dependencies, fixtures, tests or documentation that preserve an old path are
not accepted. A compatibility exception must name an owner, expiry date,
removal trigger, risk, validation and retirement task. The release gate checks:

```text
legacy_new=0
unowned_legacy=0
expired_exceptions=0
```

Existing migrations, Temporal history, Sparkle/client compatibility and other
production boundaries are retired in separate features with cutover and
rollback evidence; this rule does not authorize mass deletion.

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
GRAF_RELEASE_OPERATOR=<release-operator> ./scripts/prepare-release.sh YYYY.MM.DD.N
```

For example:

```sh
GRAF_RELEASE_OPERATOR=<release-operator> ./scripts/prepare-release.sh 2026.06.18.1
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
