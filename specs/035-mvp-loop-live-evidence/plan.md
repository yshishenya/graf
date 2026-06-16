# Implementation Plan: MVP Loop Live Evidence

**Branch**: `035-mvp-loop-live-evidence` | **Date**: 2026-06-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/035-mvp-loop-live-evidence/spec.md`

## Summary

Produce a validation-only live MVP loop evidence pack after the accepted 022
mute-truth closeout. The slice must prove, or explicitly keep blocked, the owner
value loop across the permissioned `/Applications/2brain Rec.app` desktop
runtime, safe web owner review, backend readiness artifacts, launch gap truth,
forbidden-content scans, and clean-room reference comparison. The technical
approach is evidence orchestration and status/report synchronization only:
reuse the existing readiness package and validation scripts, collect fresh safe
runtime evidence, update generated readiness outputs and status docs, and refuse
stronger MVP/pilot claims when any P0/P1 evidence remains weak.

No new capture, notes/action generation, sharing, deletion, installer, or
deployment behavior is authorized by this plan.

## Technical Context

**Language/Version**: Python 3.13 for server/readiness utilities; Swift 6
toolchain for macOS validation; shell for local/production validation scripts.

**Primary Dependencies**: Existing `twobrain_rec_server.readiness` package,
pytest/ruff/uv, Swift Package Manager/XCTest, macOS accessibility/screenshot
inspection, GitHub CLI for issue sync, existing `infra/scripts/*` gates.

**Storage**: Repository evidence under
`docs/evidence/035-mvp-loop-live-evidence/`; existing local recording artifacts
under the user app support directory are inspected only through metadata-safe
manifest validators. No new product storage tables.

**Testing**: Existing server readiness tests, new/updated 035 evidence tests if
needed, relevant macOS focused tests, `infra/scripts/ci-local.sh`,
`apps/macos/Scripts/validate-meeting-mute-truth.sh --latest-artifact-directory`,
forbidden-content scans, and manual `/Applications` app walkthrough evidence.

**Target Platform**: macOS installed desktop app, browser/web owner cabinet, and
current Rec backend/deployment evidence.

**Project Type**: Hybrid desktop app + server/web cabinet + evidence/reporting
slice.

**Performance Goals**: Local evidence generation and report validation should
complete in under 10 minutes when production deploy is not changed. Manual
desktop/web capture should produce a bounded evidence pack in one reviewer
session.

**Constraints**:

- Evidence must be metadata-safe and commit-safe.
- `/Applications/2brain Rec.app` is the desktop runtime source for acceptance.
- Live private meeting content, raw audio, transcript text, credentials, signed
  URLs, private emails, and private reference captures must not be committed.
- `mvp_loop_ready`, `internal_pilot_candidate`, `user_rollout_ready`, and
  `production_ready` are forbidden while any P0/P1 launch gap remains.
- Clean-room reference comparison may use Krisp only for generic product lessons
  and must not copy protected expression.
- This slice cannot add missing product behavior; it can only prove, classify,
  or keep gaps open.

**Scale/Scope**: One owner MVP loop, one installed macOS app path, one current
web owner review surface, existing readiness stages, and the launch gap register
after 022.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| Capture-First MVP Integrity | PASS | 035 validates the accepted system-audio-first desktop path and does not change capture code. |
| Visible Consent And User Control | PASS | Evidence cannot pass without visible capture state and one-action stop from the installed app. |
| Data Boundary And Secret Discipline | PASS | Evidence is metadata-only and includes explicit forbidden-content scans. |
| Deletion Truth And Lifecycle Accounting | PASS | Readiness outputs must preserve deletion/retention truth and cannot overstate erasure. |
| Spec-Driven Delivery With Testable Gates | PASS | Full Spec Kit cycle is used with checklists, tasks, analyze, implementation, and validation. |
| Product And Platform Constraints | PASS | macOS remains the MVP platform; virtual-driver routing is not reintroduced. |
| UI Brand-Distance | PASS | Clean-room reference comparison is required and private Krisp captures are excluded. |

No constitution violations are introduced.

## Project Structure

### Documentation (this feature)

```text
specs/035-mvp-loop-live-evidence/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── live-evidence-pack-contract.md
│   ├── readiness-claim-contract.md
│   └── clean-room-reference-contract.md
├── checklists/
│   ├── requirements.md
│   ├── ux.md
│   ├── security.md
│   ├── infra.md
│   └── launch-readiness.md
└── tasks.md

docs/evidence/035-mvp-loop-live-evidence/
├── README.md
├── validation-log.md
├── readiness-report.json
├── readiness-report.md
├── launch-gap-register.md
├── clean-room-reference.md
└── screenshots/
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/readiness/
├── evidence.py
├── matrix.py
└── report.py

apps/server/scripts/
└── generate_mvp_loop_readiness.py

apps/server/tests/
├── integration/
│   └── test_mvp_loop_readiness_report.py
└── unit/
    └── test_mvp_loop_readiness_matrix.py

apps/macos/Scripts/
└── validate-meeting-mute-truth.sh

apps/macos/Shared/Tests/
└── existing capture, upload, permission, and meeting-mute-truth test suites

docs/
├── current-product-status.md
└── evidence/
    ├── 034-mvp-loop-readiness/
    └── 035-mvp-loop-live-evidence/
```

**Structure Decision**: Keep durable readiness logic in the existing server
`readiness` package and put feature-specific evidence under
`docs/evidence/035-mvp-loop-live-evidence/`. Use existing macOS validation
scripts and tests instead of creating a new desktop subsystem.

## Phase 0: Research

Research resolves claim thresholds, live-vs-fixture web evidence, installed app
proof requirements, forbidden-content scanning, and clean-room comparison
boundaries. Output: [research.md](./research.md).

## Phase 1: Design And Contracts

- [data-model.md](./data-model.md) defines the live evidence pack, loop stage,
  launch gap, readiness claim, validation run, and clean-room comparison note.
- [contracts/live-evidence-pack-contract.md](./contracts/live-evidence-pack-contract.md)
  defines required evidence sections and safe artifact boundaries.
- [contracts/readiness-claim-contract.md](./contracts/readiness-claim-contract.md)
  defines claim transitions and blockers.
- [contracts/clean-room-reference-contract.md](./contracts/clean-room-reference-contract.md)
  defines allowed reference lessons and forbidden similarity/capture content.
- [quickstart.md](./quickstart.md) defines local, desktop, web, server, scan,
  issue-sync, and final closeout validation scenarios.

## Post-Design Constitution Check

| Principle | Status | Evidence |
|-----------|--------|----------|
| Capture-First MVP Integrity | PASS | Contracts require installed desktop proof but do not alter capture behavior. |
| Visible Consent And User Control | PASS | Live evidence contract requires visible active/paused/stopped state and Stop availability. |
| Data Boundary And Secret Discipline | PASS | Evidence contract and quickstart include forbidden-content scans. |
| Deletion Truth And Lifecycle Accounting | PASS | Readiness claim contract preserves lifecycle truth and post-egress limits. |
| Spec-Driven Delivery With Testable Gates | PASS | Tasks and quickstart will make each user story independently verifiable. |
| UI Brand-Distance | PASS | Reference contract separates generic lessons from forbidden copied expression. |

No complexity waivers are required.

## Complexity Tracking

No constitution violations or extra architectural complexity are introduced.
