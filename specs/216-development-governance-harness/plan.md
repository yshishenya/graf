# Implementation Plan: Единый процесс разработки и переносимый harness

**Branch**: `codex/216-development-governance-harness` | **Date**: 2026-08-31 | **Spec**: [spec.md](spec.md)

**Umbrella issue**: [#6090](https://github.com/yshishenya/graf/issues/6090)

## Summary

Feature 216 вводит детерминированный контур разработки: GitHub-backed Feature
ID claim, изолированный agent context, fragment-based changelog, один
SHA-consistent Dev manifest, stale-SHA CI guard, редкий release train и
обязательный Legacy Impact. Сначала изменения живут в GRAF как project adapter;
после self-test переносимая часть выпускается отдельным публичным
`graf-development-harness` с SemVer.

## Technical Context

**Language/Version**: Python 3.9+ stdlib для validators и manifest tooling;
POSIX shell для orchestration; Swift Package Manager/macOS scripts для Dev app

**Primary Dependencies**: существующие `uv`/pytest, Docker Compose, GitHub API/
`gh`, Spec Kit extensions и Ponytail; новые runtime dependencies не нужны

**Storage**: ignored per-worktree `.specify/feature.json`; metadata-only JSON/YAML
claims/manifests/evidence; существующие локальные Postgres/MinIO volumes для Dev

**Testing**: validator self-tests, shell/contract checks, focused backend/frontend
smoke, existing macOS identity/permission scripts, `infra/scripts/ci-local.sh --fast`;
Full CI только для frozen candidate

**Risk / Validation Lane**: `significant-feature` с governance/infra/release
контрактами; capture/product runtime не меняется, но Dev app and CI are shared
boundaries, поэтому required clarify/checklists/analyze/converge

**Release Gate**: `no deploy` for this feature; no public product release.
Reusable harness publication uses its own SemVer release gate after clean sample
project validation

**Target Platform**: macOS developer workstation, GitHub public repository and
portable POSIX/Python consumer projects

**Project Type**: monorepo with Python backend, macOS desktop client, Docker
development stack and governance tooling

**Performance Goals**: local governance preflight <10 seconds without network;
status/smoke output <30 seconds once services are warm; no additional full CI
invocations for unchanged frozen candidates

**Constraints**: one `/Applications/GRAF Dev.app`; loopback-only Dev origins;
no production data/credentials; no dynamic root AGENTS pointer; no mtime feature
selection; no auto-commit implementation commits; no mass legacy deletion

**Scale/Scope**: one GRAF repository with 188+ historical spec directories, many
worktrees and concurrent agents; reusable package must support at least one clean
external sample project in v1

## Constitution Check

*GATE: Must pass before Phase 0 research and after Phase 1 design.*

- **Capture-First MVP Integrity — PASS**: no capture implementation or routing
  change; existing no-legacy-driver guard remains in place.
- **Visible Consent/User Control — PASS**: Dev app identity and permissions are
  preserved; no invisible capture or permission bypass is introduced.
- **Plaintext Observability — PASS**: harness stores metadata only and never
  adds credentials, raw audio or transcript content.
- **Deletion Truth/Lifecycle — PASS**: Dev reset is local-only and release
  manifests distinguish rollback; product deletion semantics are untouched.
- **Public macOS Distribution — PASS**: this feature does not publish a product
  app; public Developer ID/notarization gates remain mandatory for later releases.
- **Spec-Driven Delivery — PASS**: full significant-feature sequence, reviewer
  checklists, analyze, issue sync and convergence are required.
- **Repository hygiene — PASS**: generated local state is ignored and portable
  package scans secrets/private paths before publication.
- **Ponytail — PASS**: reuse existing scripts and bootstrap checks; add only
  small stdlib validators and a thin adapter layer.

## Validation Plan

1. Run feature preflight and confirm branch/spec/umbrella issue/Feature ID 216,
   clean worktree and no user-owned changes overwritten.
2. Run validator self-tests for feature claims, context pointer, changelog
   fragments, stale CI evidence, Dev manifest invariants and Legacy Impact.
3. Run existing Dev app identity/permission and no-legacy-driver checks; build
   only against a loopback origin when a real app smoke is needed.
4. Run synthetic build/promote/status/smoke/rollback/reset fixture with one
   active manifest and concurrent promotion lock test.
5. Run focused backend/frontend smoke, then `infra/scripts/ci-local.sh --fast`
   once on the PR-ready SHA; record exact SHA and skipped gates.
6. Prepare but do not publish product release; Full CI and CD execute are
   reserved for a later frozen candidate with explicit approval.
7. Extract generic harness into a separate repository, run self-test, secret/
   path/provenance scans and a clean sample installation before its SemVer tag.

## Implementation Phases

### Phase 0 — Governance contracts and adapters

- Make root guidance stable and move active context to explicit per-worktree
  state.
- Add Feature ID claim/preflight and PR/issue linkage validation.
- Add changelog fragment schema and validator.
- Add Legacy Impact template/validator and DoD/PR requirements.

### Phase 1 — Dev and CI harness

- Add a single-manifest Dev orchestration layer around existing compose and
  macOS scripts; use lock, atomic pointer and dry-run/status/rollback.
- Add source SHA and component digest reporting; keep reset local-only.
- Resolve the current Alembic graph head during a real GRAF `build` when no
  explicit head is supplied; keep fixture roots explicit and reject unknown
  heads at promotion.
- Add stale-SHA and frozen-candidate validators and integrate them into the
  fast lane without running Full CI for every commit.

### Phase 2 — Release train and agent ergonomics

- Add release-candidate metadata, one-full-run guard, CalVer/release-note
  checklist and PR template Feature ID/evidence fields.
- Document the short operator runbook and next action for each blocked state.
- Disable auto-commit hooks by default while preserving read-only issue-canon /
  context hooks.

### Phase 3 — Portable extraction and legacy follow-up

- Extract generic schemas, validators, templates, scripts and self-tests into
  `graf-development-harness` (SemVer, immutable tag, migration notes).
- Keep GRAF product gates as a project adapter; run a clean sample installation.
- Create the next collision-free legacy-retirement feature/issue with the
  inventory and prioritized safe slices; do not delete product legacy here.

## Project Structure

### Documentation (this feature)

```text
specs/216-development-governance-harness/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── feature-claim.md
│   ├── dev-manifest.md
│   ├── ci-release.md
│   ├── legacy-impact.md
│   └── harness-package.md
├── checklists/
│   ├── requirements.md
│   └── governance.md
└── tasks.md
```

### Source Code (GRAF adapter)

```text
AGENTS.md
docs/agent-guidance/
├── spec-kit-flow.md
├── codex-worktrees.md
├── release-and-validation.md
├── github-issue-canon.md
└── development-process.md             # new stable operator runbook
.github/
├── pull_request_template.md
└── ISSUE_TEMPLATE/spec-kit-work-item.yml
changes/unreleased/                     # new owned fragments
scripts/
├── claim-feature.py                    # or thin shell wrapper
├── validate-changelog-fragments.py
├── validate-legacy-impact.py
├── validate-ci-evidence.py
└── dev-harness.py                      # manifest/lock adapter
infra/scripts/
├── dev-harness.sh
└── ci-local.sh
apps/macos/Scripts/
├── build-dev-app.sh
└── install-dev-app.sh
```

**Structure Decision**: keep project-specific orchestration in existing GRAF
paths and introduce small stdlib validators; no second backend, frontend or
database. Portable code is later extracted into the separate harness repository
with a thin project adapter interface.

## Complexity Tracking

No constitution violations. A separate reusable repository and one manifest
layer are justified by the user's explicit portability and single-Dev-app
requirements; they do not create a second product runtime or source of truth.
