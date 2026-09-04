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

## Decision 5: XCTest cases use one sequential process

- **Decision**: use one shared macOS test runner in GitHub Full CI and the
  retained local fallback. It requires nonempty `swift test list` discovery,
  clears SwiftPM's hidden test-skip override, then runs ordinary sequential
  `swift test --skip-build`.
- **Rationale**: [SwiftPM 6.0.3's parallel runner](https://github.com/swiftlang/swift-package-manager/blob/swift-6.0.3-RELEASE/Sources/Commands/SwiftTestCommand.swift#L1094-L1137)
  creates a new `TestRunner` and process for each XCTest case even with one
  worker. One XCTest process keeps test discovery and browser ownership simple
  without retry, quarantine or a suite allowlist. GitHub run `33838426331`
  later proved that process lifetime was not the cause of signal 5; Decision 9
  records the actual bridge failure.
- **Evidence boundary**: focused local runs prove the one-process harness and
  browser assertions; only a new post-merge GitHub Full CI run proves macOS 14
  with pinned Swift 6.0.3.
- **Alternatives considered**: per-case processes reproduce the failure;
  teardown, delay, retry and deprecated `WKProcessPool` either reintroduce the
  race or hide it.

## Decision 8: Keep WebKit alive to the shared process boundary

- **Decision**: retain synthetic `WKWebView` instances and their navigation
  delegates until the sequential XCTest process exits. Read plist values through
  the shared helper only when `plutil` returns success, and scan source with
  native `/usr/bin/grep` rather than an undeclared Homebrew dependency.
- **Rationale**: GitHub run `33836195145` disproved the per-case isolation
  assumption and also showed that `rg` is absent on the pinned macOS runner.
  The earlier run proved that macOS 14 may print a missing-key
  diagnostic to stdout before `plutil` exits nonzero; swallowing that status
  turns the diagnostic into a false legacy field.
- **Alternatives considered**: retry, sleep, quarantine and skipped tests hide
  failures; installing `rg` adds network and toolchain drift; special-casing
  individual plist fields duplicates the bug outside the common helper.

## Decision 9: Bridge WebKit's page-world completion handler into async tests

- **Decision**: every JavaScript evaluation in `CabinetSidebarRuntimeTests`
  uses the completion-handler `evaluateJavaScript(_:completionHandler:)`
  behind one async test helper.
- **Rationale**: side-effect JavaScript such as `HTMLElement.click()` correctly
  returns `undefined`. The macOS 14 SDK Swift async overlay treats the
  corresponding Objective-C `nil` as non-optional `Any` and traps at `:0`,
  including the explicit page-world async overload. The callback API is
  equivalent to main-frame page-world evaluation and preserves both `nil` and
  JavaScript errors; value-returning assertions keep their existing behavior.
  Separate-process run `33836195145` and sequential-process run `33838426331`
  disproved the lifetime hypothesis; diagnostic run `33841429909` disproved
  the optional-returning async-overload hypothesis.
- **Evidence boundary**: focused local tests check compilation and behavior;
  the manual macOS-only workflow checks pinned macOS 14 / Swift 6.0.3 without
  rerunning server-full. It is diagnostic only. One later complete
  `release-full` remains the sole authoritative release evidence.
- **Alternatives considered**: adding `return true` fixes only current scripts;
  deleting or moving tests to Node loses the system `WKWebView` boundary; retry,
  sleep, skip and quarantine hide the defect.

## Decision 10: Use SwiftPM's declared resource bundle for the fixture

- **Decision**: resolve the microphone manifest fixture through `Bundle.module`
  and remove the source-tree parent-directory walk.
- **Rationale**: exact-SHA probe run `33844470386` reached
  `before_fixture_lookup` and then stalled. Its `/usr/bin/sample` stack stayed
  inside `contractFixtureURL`, `UnfoldSequence.next` and Foundation URL path
  construction while XCTest grew to 8 GB. The test target already declares
  `.copy("Fixtures")`, so SwiftPM provides the native resource accessor.
- **Evidence boundary**: the probe proves the root cause, not the repair. The
  focused test, exact-SHA `governance-fast` and post-merge `macos-diagnostic`
  must pass before T024 closes; one later complete `release-full` remains the
  release evidence.
- **Alternatives considered**: a maximum parent depth would keep a duplicate
  source-layout dependency; retry, timeout growth and splitting XCTest would
  only hide the infinite lookup.

## Decision 11: Keep one behavioral owner for retry cleanup ordering

- **Decision**: remove the elapsed-time duplicate from standalone
  `ContractValidation`; make the focused XCTest release the first start and call
  retry directly, and retain a deterministic source-order invariant in the
  standalone validator.
- **Rationale**: GitHub run `33852464801` completed all 794 XCTest cases, then
  failed only because the contract checker slept for 0.1 seconds and assumed a
  0.2-second runtime start was still pending. Runner scheduling may exceed that
  interval, so the observation is not a valid ordering boundary. Both
  `release-full` and `macos-diagnostic` run the complete XCTest suite before
  standalone `ContractValidation`, while the scripts that call the standalone
  tool directly validate other named contracts. The source invariant still
  fails if a retry can create/start its runtime before pending cleanup, or if
  cleanup stops waiting for the first start before its final stop. The XCTest no
  longer uses `Task.yield` or an unbounded first-stop continuation: the held
  first start guarantees the timeout, then a direct retry proves cleanup and
  recovery complete. Removing the duplicate cannot skip the release test and
  avoids a second, weaker behavioral owner of the same behavior.
- **Evidence boundary**: repeat the standalone checker and focused XCTest during
  implementation; use `macos-diagnostic` on the exact merged SHA without
  server-full. One final complete `release-full` remains required for the
  release candidate because this release train includes server/infrastructure
  changes.
- **Alternatives considered**: retry, longer sleeps/timeouts and quarantine hide
  the race; a second continuation-based copy still needs either a product-code
  test hook or a timing assumption to prove that retry entered the actor.

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
