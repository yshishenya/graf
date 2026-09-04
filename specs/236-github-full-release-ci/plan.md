# Implementation Plan: Authoritative GitHub Full CI для релизного кандидата

**Branch**: `236-github-full-release-ci` | **Date**: 2026-09-02
**Spec**: [spec.md](spec.md)

## Summary

Добавить ручной GitHub workflow, который принимает только frozen candidate
identity, запускает полные backend/infrastructure и macOS проверки на подходящих
runner-ах, а затем создаёт одну SHA-bound authoritative evidence запись. PR
остаётся быстрым через `governance-fast`; локальный `ci-local.sh` сохраняется
только как диагностика/offline fallback. Release preparation берёт границу из
последнего опубликованного GitHub Release, а существующий closeout-validator
проверяет всю feature целиком.

## Technical Context

- **Language/Version**: Bash, Python 3.13, Swift 6 / macOS 14
- **Primary Dependencies**: GitHub Actions, existing `gh`, `uv`/pytest/ruff,
  `scripts/emit-ci-evidence.py`, `scripts/validate-ci-evidence.py`
- **Storage**: GitHub Actions artifacts; local ignored `.dev/ci-evidence/`
  and `.dev/release/` remain operator evidence stores
- **Testing**: pytest governance/contract tests, `swift build`, `swift test`,
  `swift run ContractValidation`, existing PostgreSQL test runner
- **Risk / Validation Lane**: significant-feature (governance and release gate)
- **Release Gate**: no automatic deploy; workflow must stop before signing,
  publication and production execution
- **Target Platform**: GitHub `ubuntu-latest` and `macos-14` with an explicit
  `uname -m` == `arm64` gate
- **Project Type**: self-hosted backend plus native macOS app and release tooling
- **Performance Goals**: component jobs run in parallel; no repeated Full CI for
  one candidate; `reserve=10`, `server=60`, `macos=45`, `aggregate=10`
  minute timeouts are explicit and release-blocking
- **Constraints**: read-only repository permissions, metadata-only artifacts,
  exact SHA equality, zero skipped gates in aggregate evidence
- **Scale/Scope**: one authoritative run per candidate ID; same-ID runs are
  serialized, while distinct candidate IDs are independent

## Constitution Check

- PASS: no capture, auth, privacy, data or product behavior changes.
- PASS: exact SHA, create-once evidence, fail-closed stale/cancelled behavior
  and linear release boundary are preserved.
- PASS: signing, notarization, appcast and deployment remain in their required
  owner-controlled custody boundary.
- PASS: local fallback is retained and explicitly non-authoritative.
- PASS: work follows Spec Kit and adds no new secret or dependency path.

### Required constitution checkpoints

- **Before Phase 0 research**: confirm the exact-SHA, metadata-only, read-only
  permissions and no-deploy boundaries against `.specify/memory/constitution.md`;
  record the result in this plan and `research.md`.
- **After Phase 1 design**: re-check workflow permissions, candidate reservation,
  failure states, Apple Silicon runner requirement and legacy classification;
  record the result in `contracts/release-full-workflow.md` and the reviewer
  checklist before implementation.

## Validation Plan

1. Run the feature quickstart and workflow contract self-tests.
2. Run focused governance tests plus `infra/scripts/ci-local.sh --fast` before
   opening the PR; do not run local `--full` as release evidence.
3. Dispatch `release-full.yml` once for a newly frozen candidate and verify the
   exact SHA, reservation, component jobs, aggregate evidence and artifact
   digest with `scripts/validate-ci-evidence.py`.
4. Download evidence locally, run `train-attest`/`decide`, then continue the
   existing CD dry-run and macOS signing/notarization gates.
5. Exercise release preparation with unpublished changelog sections and run
   feature-level closeout validation against GitHub issue metadata.
6. Keep T017 open through Full CI, publication and production validation. Then
   merge a closeout-only T017 task-state PR before closing Feature 236 child
   issues and the umbrella; the later closeout commit must not move the tag.
7. Run the focused WebKit runtime and signing-custody regressions before merge;
   evaluate page JavaScript through WebKit's optional-returning page-world async
   overload, keep tests in one sequential XCTest process, use only the native
   macOS scanner, and trust `plutil` output only after a successful exit status.
   Use the non-authoritative macOS-only workflow during diagnosis, then prove
   the complete pinned release lane with T017 after freeze.

## Project Structure

```text
specs/236-github-full-release-ci/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/release-full-workflow.md
├── checklists/requirements.md
├── checklists/infra.md
└── tasks.md

.github/workflows/release-full.yml
.github/workflows/macos-diagnostic.yml
apps/macos/Scripts/run-swift-tests.sh
apps/macos/Installer/Scripts/release-signing-common.sh
apps/macos/Shared/Tests/CabinetBillingRuntimeTests.swift
apps/macos/Shared/Tests/CabinetSidebarRuntimeTests.swift
scripts/validate-full-ci-workflow.py
scripts/validate-issue-closeout.py
scripts/prepare-release.sh
apps/server/tests/contract/test_ci_cd_contract.py
infra/scripts/ci-local.sh
docs/agent-guidance/release-and-validation.md
docs/agent-guidance/development-process.md
infra/scripts/README.md
AGENTS.md
changes/unreleased/F236.yaml
```

**Structure Decision**: keep the existing local harness and release scripts;
extend the current release-preparation and issue-closeout validators instead of
adding a second release or tracker implementation. Do not create a deployment
workflow.

## Complexity Tracking

No constitution violations or new runtime abstractions. The two runner jobs are
required by the existing platform split; the aggregator is required to produce
one release identity.
