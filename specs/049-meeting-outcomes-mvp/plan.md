# Implementation Plan: Meeting Outcomes MVP

**Branch**: `049-meeting-outcomes-mvp` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/049-meeting-outcomes-mvp/spec.md`

## Summary

Create server-owned, stored meeting outcomes so the current `notes-action-output`
MVP blocker can close with evidence instead of placeholder truth states. The
implementation adds durable outcome set/item/attempt records scoped to a
meeting media revision and processing result, an idempotent outcome generation
service, category-level truth states, and web plus macOS embedded review
rendering from the same stored data. Transcript, diarization, and playback stay
visible as soon as their existing gates allow them; slower or failed outcome
generation shows a safe processing/blocked state and does not delay review.

The MVP path is intentionally conservative: store launch-safe extractive
outcomes with transcript evidence and explicit "not found/not inferable" states
when the transcript does not support a category. MediaScribe summary output may
be consumed as source material if available, but provider-reported summary
status alone never closes the blocker. Desktop clients never call outcome
providers and never receive provider credentials.

## Technical Context

**Language/Version**: Python 3.14 server; Swift/macOS app is verified for
embedded review parity but no native capture changes are expected.

**Primary Dependencies**: FastAPI, SQLAlchemy async ORM, Alembic, Pydantic,
Temporal worker boundary, MediaScribe client schemas, existing cabinet HTML
renderer, pytest, Playwright/Chrome runtime verifier, SwiftPM/XCTest for any
macOS shell regression if native files change.

**Storage**: Existing Postgres/Alembic production schema and SQLite-backed
local tests. New outcome tables must be tenant scoped and RLS covered:
`meeting_outcome_sets`, `meeting_outcome_items`, and
`meeting_outcome_generation_attempts`.

**Testing**: Server contract/integration/unit pytest, migration/RLS tests,
cabinet web shell tests, browser runtime checks for desktop web/mobile/desktop
embedded routes, forbidden-content scans, full `infra/scripts/ci-local.sh`,
deploy dry-run before release.

**Target Platform**: Server-owned web cabinet on Linux containers; macOS app
uses the existing embedded cabinet routes. No new desktop-to-provider egress.

**Project Type**: Self-hosted web service plus macOS trust shell.

**Performance Goals**:

- Outcome orchestration for a one-hour transcript with normal local/fake
  dependencies completes within 30 seconds or enters a safe non-blocking state.
- Transcript, diarization, and playback review must not wait for outcomes.
- Browser runtime validation reports no horizontal overflow or overlap across
  desktop web, mobile-width web, and desktop embedded review.

**Constraints**:

- Outcomes are meeting content, not harmless metadata.
- Default diagnostics, logs, Langfuse traces, release notes, screenshots, and
  committed evidence must not contain generated outcome text, transcript text,
  prompts with meeting content, raw audio, signed URLs, credentials, private
  paths, or private meeting identifiers.
- Desktop clients never send transcript/audio directly to MediaScribe, LLMs, or
  any outcome generation dependency.
- Stored outcome facts must cite transcript segment or timestamp evidence when
  evidence exists. Unsupported claims are omitted or stored as category-level
  "not found/not inferable" truth, never fabricated.
- Deletion, retention, access, export/download, audit, and lifecycle reporting
  must account for outcomes as derived meeting content.

**Scale/Scope**:

- MVP supports one latest accepted media revision and latest imported
  processing result per meeting.
- Outcome categories are summary, key discussion points, decisions, action
  items, follow-ups, risks/blockers, questions, and important evidence.
- Manual editing, manual regeneration UI, AI chat, public links, CRM sync,
  real-time coaching, transcript editing, speaker editing, and audio cleanup
  remain out of scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate Result | Reason |
| --- | --- | --- |
| I. Capture-First MVP Integrity | PASS | No capture, driver, ScreenCaptureKit, microphone, routing, or recording integrity behavior changes are planned. |
| II. Visible Consent And User Control | PASS | Outcome generation is post-processing only and does not change active capture visibility, Record/Stop, Pause/Resume, or assisted auto-start. |
| III. Data Boundary And Secret Discipline | PASS | Generation is server-owned, provider credentials remain server-side, diagnostics are metadata-only, and desktop clients never call providers directly. |
| IV. Deletion Truth And Lifecycle Accounting | PASS | Outcomes are modeled as meeting content with lifecycle artifacts, deletion accounting, retention behavior, and access/egress policy participation. |
| V. Spec-Driven Delivery With Testable Gates | PASS | Feature has spec and requirements checklist; plan produces research, data model, contracts, quickstart, then tasks/analyze before implementation. |

No constitution violations are accepted.

## Project Structure

### Documentation (this feature)

```text
specs/049-meeting-outcomes-mvp/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── meeting-outcomes-review-contract.md
│   └── meeting-outcomes-lifecycle-contract.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   └── ux.md
├── evidence/
│   └── validation-log.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── api/
│   ├── cabinet.py
│   └── schemas.py
├── cabinet/
│   ├── queries.py
│   ├── view_models.py
│   └── web.py
├── db/
│   ├── migrations/versions/0009_meeting_outcomes_mvp.py
│   ├── models/__init__.py
│   ├── models/outcomes.py
│   └── rls_validation.py
├── deletion/
│   ├── report.py
│   └── service.py
├── domain/
│   └── statuses.py
├── outcomes/
│   ├── __init__.py
│   ├── generator.py
│   ├── models.py
│   ├── service.py
│   └── store.py
├── processing/
│   ├── store.py
│   └── submit.py
└── readiness/
    ├── matrix.py
    └── report.py

apps/server/tests/
├── contract/
├── integration/
├── unit/
└── fakes/

specs/049-meeting-outcomes-mvp/evidence/
└── browser-runtime-check.cjs
```

**Structure Decision**: Implement outcomes inside the server application as a
new `twobrain_rec_server.outcomes` module and new database model file. The
cabinet and API layers consume stored outcome review state; the macOS app uses
the existing embedded route and only needs native tests if Swift files change.

## Phase 0 Research

See [research.md](./research.md).

Key decisions:

- Store outcomes in first-class tables with category-level item/state rows.
- Generate outcomes after transcript import through a server-owned,
  idempotent service. The first MVP generator is deterministic/extractive and
  safe-by-default; provider/LLM integration remains behind the same service
  boundary.
- Treat MediaScribe summary as optional source material, not as the readiness
  claim by itself.
- Keep transcript/playback review independent of outcome generation.
- Extend RLS/deletion/readiness gates as part of the feature, not later.

## Phase 1 Design

See:

- [data-model.md](./data-model.md)
- [meeting-outcomes-review-contract.md](./contracts/meeting-outcomes-review-contract.md)
- [meeting-outcomes-lifecycle-contract.md](./contracts/meeting-outcomes-lifecycle-contract.md)
- [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

| Principle | Gate Result | Design Evidence |
| --- | --- | --- |
| I. Capture-First MVP Integrity | PASS | No source paths under `apps/macos` or capture stack are required unless embedded shell verification reveals a native regression. |
| II. Visible Consent And User Control | PASS | Post-processing outcomes do not change local active-capture controls or meeting capture policy. |
| III. Data Boundary And Secret Discipline | PASS | Contracts require server-only generation, no desktop provider egress, metadata-only traces/evidence, and forbidden-content scans. |
| IV. Deletion Truth And Lifecycle Accounting | PASS | Data model defines controlled meeting content artifacts and lifecycle/deletion attempts for outcome rows. |
| V. Spec-Driven Delivery With Testable Gates | PASS | Quickstart defines focused, browser, RLS, forbidden-content, full CI, and deploy dry-run gates before closeout. |

No constitution violations are accepted.

## Complexity Tracking

No constitution violations or unusual complexity exceptions are introduced.
