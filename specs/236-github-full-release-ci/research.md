# Research: GitHub Full CI

## Constitution checkpoints

- **Before Phase 0 research — PASS (2026-09-02)**: `.specify/memory/constitution.md`
  requires exact-SHA provenance, metadata-only evidence, read-only CI custody and
  no automatic production mutation. Those constraints are applied to every
  decision below.
- **After Phase 1 design — PASS (2026-09-02)**: the designed workflow has
  create-once reservation, fail-closed cancellation/stale handling, explicit
  `reserve=10`, `server=60`, `macos=45`, `aggregate=10` minute limits, an
  arm64 assertion on macOS, and `untouched` legacy classification. Reviewer
  checklist `infra.md` records the corresponding gate review.

## Decision 1: Manual workflow with two component jobs and one aggregator

- **Decision**: use a `workflow_dispatch` workflow with Ubuntu server/infrastructure
  and macOS Swift jobs, followed by one Ubuntu aggregation job.
- **Rationale**: the existing full harness contains both Docker/PostgreSQL and
  Swift gates; GitHub-hosted runners do not provide one portable environment for
  both. Parallel component jobs reduce wall-clock time while aggregation keeps
  one release decision identity.
- **Alternatives considered**: one Ubuntu job would skip macOS gates; one macOS
  job cannot reliably provide the Docker/PostgreSQL baseline; per-PR Full CI
  would recreate the current long-CI race.

## Decision 2: Candidate identity is passed as inputs and verified against master

- **Decision**: dispatch requires `candidate_id` and `requested_sha`; the workflow
  validates format, resolves the commit, and requires it to equal the current
  post-merge `origin/master` SHA.
- **Rationale**: ignored local candidate manifests must not be committed just to
  make GitHub aware of them. The local release operator retains the immutable
  manifest and later binds downloaded evidence with `train-attest`/`decide`.
- **Alternatives considered**: committing `.dev/release` would expose mutable
  operator state; accepting only `github.sha` would allow an accidental branch
  dispatch instead of the frozen post-merge SHA.

## Decision 3: GitHub artifact reservation is create-once

- **Decision**: a reservation artifact is created before component jobs and a
  per-candidate concurrency group uses `cancel-in-progress: false`; existing
  reservation or evidence blocks the dispatch.
- **Rationale**: `emit-ci-evidence.py` is create-once within a checkout, but a
  fresh GitHub runner has no prior ignored files. Artifact lookup supplies the
  cross-run identity boundary without granting write access to source.
- **Alternatives considered**: a mutable branch/file would violate frozen
  candidate semantics; `cancel-in-progress: true` could silently discard the
  only authoritative run.

## Decision 4: Signing and deployment remain separate operator gates

- **Decision**: Full CI validates source/build/test readiness only. Developer ID
  signing, notarization, appcast publication and production deploy remain on the
  named operator Mac and use the existing guarded scripts.
- **Rationale**: private Apple keychain and production credentials must not enter
  GitHub; the constitution requires those gates and final bytes to be checked in
  their real custody boundary.
- **Alternatives considered**: exporting signing or deploy credentials to Actions
  would breach secret custody and cannot prove the real installed-app path.

## Decision 5: XCTest cases use separate sequential processes

- **Decision**: use one shared macOS test runner in GitHub Full CI and the
  retained local fallback. It requires nonempty `swift test list` discovery,
  clears SwiftPM's hidden test-skip override, then runs
  `swift test --parallel --num-workers 1`.
- **Rationale**: [SwiftPM 6.0.3's parallel runner](https://github.com/swiftlang/swift-package-manager/blob/swift-6.0.3-RELEASE/Sources/Commands/SwiftTestCommand.swift#L1094-L1137)
  creates a new `TestRunner` and process for each XCTest case; one worker keeps
  execution sequential. This prevents WebKit content-process state from
  accumulating between tests without retries, quarantines, deprecated
  `WKProcessPool`, or a hand-maintained suite allowlist.
- **Evidence boundary**: the failed GitHub run proves a fatal nil unwrap in
  `CabinetSidebarRuntimeTests.testRailKeepsManualChoiceAcrossSameSessionNavigation`
  with exit code 1 after several WebKit cases. It does not prove signal 5 or a
  supported internal WebKit root cause. Per-case process isolation removes the
  observed cross-test boundary; one post-merge GitHub Full CI run remains the
  required proof on the pinned Swift 6.0.3/macOS runner.
- **Alternatives considered**: lifecycle changes and a shared process pool did
  not provide a process boundary; filtered suite invocations can return success
  with zero matching tests and still share one process within a suite.

## Decision 8: Keep WebKit alive to the isolated process boundary

- **Decision**: retain synthetic `WKWebView` instances and their navigation
  delegates until each isolated XCTest process exits. Read plist values through
  the shared helper only when `plutil` returns success.
- **Rationale**: GitHub run `33830401847` proved that per-case process isolation
  removed cross-test accumulation but per-test WebKit teardown still crashes on
  macOS 14.8.9. The same run proved that macOS 14 may print a missing-key
  diagnostic to stdout before `plutil` exits nonzero; swallowing that status
  turns the diagnostic into a false legacy field.
- **Alternatives considered**: retry, sleep, quarantine and skipped tests hide
  the failures; a shared `WKProcessPool` restores the earlier cross-test state;
  special-casing individual plist fields duplicates the bug outside the common
  trust-boundary helper.

## Decision 6: Published GitHub Release is the only release-train base

- **Decision**: select the latest non-draft, non-prerelease GitHub Release by
  `publishedAt`, then include every commit and prepared changelog fragment after
  its tag in the next candidate.
- **Rationale**: a local tag or dated changelog heading can exist without a
  published artifact. Treating either as released silently drops user-visible
  work from the next release.
- **Alternatives considered**: trusting the newest tag or changelog heading is
  faster but cannot prove that users could actually obtain that release.

## Decision 7: Reuse the issue closeout validator for whole-feature inventory

- **Decision**: extend `scripts/validate-issue-closeout.py` with a feature mode
  that reads all issues under one feature label and validates task ownership,
  closed state, both GitHub checks and umbrella ordering. Live mode queries
  GitHub to bind the PR number and PR SHA to a merged PR, `governance-fast` to
  that PR SHA, and release-gated `release-full` to the separate candidate SHA.
- **Rationale**: the existing per-issue validator already owns the closure
  contract. A second closeout script would duplicate parsing and drift again.
  T017 stays unchecked in the published candidate, then a post-release
  closeout-only PR records it complete before issue closure. Earlier T013-T014
  checkboxes prove only that the procedure was implemented.
- **Alternatives considered**: a documentation-only `gh issue list` command
  displays open issues but cannot fail closed on missing mappings or evidence.
