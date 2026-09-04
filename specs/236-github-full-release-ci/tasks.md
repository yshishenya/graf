# Tasks: Authoritative GitHub Full CI для релизного кандидата

## Phase 1: Foundation

- [X] T001 [P] [US1] Add the release-full workflow contract validator in `scripts/validate-full-ci-workflow.py` (Issue #6417).
- [X] T002 [P] [US1] Add the metadata-only component-result contract test in `apps/server/tests/contract/test_ci_cd_contract.py` (Issue #6416).
- [X] T003 [US3] Add `changes/unreleased/F236.yaml` with release-process impact and no runtime behavior change (Issue #6419).

## Phase 2: User Story 1 - One frozen candidate

- [X] T004 [US1] Add manual exact-SHA GitHub workflow inputs, read-only permissions and candidate concurrency in `.github/workflows/release-full.yml` (Issue #6423).
- [X] T005 [US1] Implement create-once candidate reservation and existing-artifact refusal in `.github/workflows/release-full.yml` (Issue #6422).
- [X] T006 [US1] Implement Ubuntu server/governance/infrastructure full component checks and metadata-only result in `.github/workflows/release-full.yml` (Issue #6420).
- [X] T007 [US1] Implement macOS Swift build/test/contract checks, arm64 assertion and metadata-only result in `.github/workflows/release-full.yml` (Issue #6424).
- [X] T008 [US1] Implement aggregate exact-SHA evidence generation, validation and artifact publication in `.github/workflows/release-full.yml` (Issue #6418).

## Phase 3: User Story 2 - Fast versus full lanes

- [X] T009 [US2] Update `AGENTS.md`, `docs/agent-guidance/development-process.md`, `docs/agent-guidance/release-and-validation.md` and `infra/scripts/README.md` to make GitHub Full CI authoritative and local `--full` diagnostic-only (Issue #6421).
- [X] T010 [US2] Add workflow and lane invariants to `apps/server/tests/contract/test_ci_cd_contract.py`, including the executable deterministic same-candidate reservation/collision test `test_github_full_workflow_is_manual_exact_sha_and_metadata_only` (`candidate_already_reserved`, `cancel-in-progress: false`, immutable artifact names), and preserve `governance-fast` PR-only behavior (Issue #6425).

## Phase 4: User Story 3 - Fallback and closeout

- [X] T011 [US3] Document freeze → GitHub Full CI → evidence download → decision → signing/deploy sequence in `specs/236-github-full-release-ci/quickstart.md` and release guidance (Issue #6426).
- [X] T012 [US3] Run `specs/236-github-full-release-ci/quickstart.md`, `python3 scripts/check_spec_kit_governance.py`, `python3 scripts/check-development-process.py`, `python3 -m pytest -q apps/server/tests/contract/test_ci_cd_contract.py`, `infra/scripts/ci-local.sh --fast` (diagnostic on dirty worktree is explicitly ambiguous), and `python3 scripts/validate-full-ci-workflow.py .github/workflows/release-full.yml` on the PR SHA. Static workflow checks run on PR SHA; authoritative Full CI runs only after merge and freeze (Issue #6427).
- [X] T013 [US3] After analyze, sync `specs/236-github-full-release-ci/tasks.md` to child GitHub issues #6416–#6429 and track umbrella #6415 separately. Reconcile task mappings and reviewer evidence before merge; after authoritative Full CI, validate and close child issues with Russian GitHub comments and an ignored metadata-only closeout manifest so tracked source does not invalidate the candidate (Issue #6428).
- [X] T014 [US3] Run `speckit-converge` before release preparation and record the repeatable closeout procedure plus reviewer-owned checklist evidence in `specs/236-github-full-release-ci/quickstart.md`. Record the final PR SHA in the PR description and the post-merge candidate SHA only in immutable/ignored evidence and GitHub comments; never change tracked source after freeze (Issue #6429).

## Dependencies

T001-T003 → T004-T008 → T009-T011 → T012 → T013-T014.

## Implementation Strategy

Use the existing test commands and evidence validators. Add no new runtime
service, dependency, signing secret or deployment path. Keep component results
small and metadata-only; the aggregation job is the sole authoritative writer.

## Phase 5: Convergence

- [X] T015 [US3] Make `scripts/prepare-release.sh`, focused tests and release guidance derive the release-train base from the latest published non-draft, non-prerelease GitHub Release and fold every later unpublished changelog section into one candidate per FR-011 (Issue #6466; partial).
- [X] T016 [US3] Extend `scripts/validate-issue-closeout.py`, focused tests and closeout guidance to require canonical authoritative evidence, both `governance-fast` and `release-full` run URLs, complete task↔issue inventory and umbrella-last closeout per FR-012 (Issue #6467; partial).

## Phase 6: macOS release-gate stabilization

- [X] T018 [US1] Keep synthetic WebKit objects alive to the isolated XCTest
  process boundary, make the shared plist reader accept output only after a
  successful `plutil` exit, and run the focused macOS regressions before merge
  per FR-013 (Issue #6471).

## Phase 7: Release-preparation convergence

- [X] T019 [US3] Make `scripts/prepare-release.sh` safely rerunnable for the
  same unpublished CalVer when fragments are already stored in that release's
  archive, and cover the same-source archive path in
  `tests/governance/test_prepare_release.py` per FR-011 (Issue #6473).
- [X] T020 [US3] Reject filename-to-feature mismatches and multiple fragment
  sources that map to the same target archive path before changing
  `CHANGELOG.md` or moving files, with a fail-closed regression in
  `tests/governance/test_prepare_release.py` per FR-011 (Issue #6475).

## Phase 8: Post-release closeout

- [ ] T017 [US3] After the new exact-SHA candidate proves SC-008 in authoritative GitHub `release-full` and the release/deploy gates complete, land a post-release closeout-only PR that marks T017 complete without changing the published candidate; this makes #6468 eligible for the child/umbrella closure procedure in `quickstart.md` per FR-012 (Issue #6468; missing).

Dependency: T018 → T019 → T020 → T017.

Closeout correction: the `[X]` state of T013-T014 records their implemented
procedure and pre-merge reconciliation only. T017 stays unchecked in the
published candidate and becomes `[X]` only in the later closeout-only PR; issue
closure then uses that merged task state without changing the release tag.
