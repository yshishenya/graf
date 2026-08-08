# Implementation Plan: Calendar Auto Context Match

**Branch**: `098-calendar-auto-context-match` | **Date**: 2026-07-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/098-calendar-auto-context-match/spec.md`

## Summary

Feature 098 makes calendar context automatic for normal first-party recordings. Immediately after local capture starts, the macOS app makes a non-blocking server resolve call with the actual recording start and no event ID. The server evaluates selected event snapshots owned by the same user in the same workspace and persists a match-time attempt that expires exactly 24 hours after server evaluation. Meeting creation later consumes that attempt atomically. One safe, fresh, meeting-like candidate is matched; overlapping, back-to-back, stale, private, all-day, manual-upload and offline-recovery cases remain unlinked or require an explicit owner choice. A start-time decline is persisted separately from clearing context on an existing meeting.

The implementation reuses the 060/063 calendar ingestion, settings, prompt, context-link, cabinet and embedded macOS surfaces. It adds a deterministic matcher, a short-lived recording-start attempt, one authoritative context row per meeting, immutable match-time title/roster/recurrence fields, persisted meeting title provenance, and an attempt ID consumed atomically by meeting creation. No provider adapter, calendar write, auto-record, sharing, delivery, speaker naming or new frontend application is introduced.

## Technical Context

**Language/Version**: Python >=3.13 server; SQLAlchemy 2/Alembic; Pydantic 2/FastAPI; Jinja/HTMX/CSS cabinet; Swift 6 package targeting macOS 14+.

**Primary Dependencies**: Existing calendar services and models from 060/063, ingest meeting creation, cabinet list/review read models, embedded macOS cabinet, desktop calendar prompt and upload queue/client. No new runtime dependency.

**Storage**: PostgreSQL production schema with SQLite test compatibility. Add migration `0021_calendar_auto_context_match.py` for meeting title provenance, bounded `recording_calendar_match_attempts`, and a one-row-per-meeting authoritative state plus immutable match-time fields on `recording_calendar_context_links`. Existing event, participant, audit and lifecycle tables remain authoritative inputs.

**Testing**: pytest unit/contract/integration tests, Alembic upgrade/downgrade and RLS inventory checks, Ruff, Swift/XCTest filters for calendar prompts/upload queue/client plus `DesktopCabinetWorkspace` and `DesktopCabinetUploadLink`, feature quickstart, then `infra/scripts/ci-local.sh` at closeout.

**Risk / Validation Lane**: High-risk feature / active Spec Kit slice. Calendar context touches recording metadata, privacy-sensitive event data, authorization and workspace boundaries, persistent title provenance, lifecycle/deletion accounting, web/macOS UX and a cross-platform ingest contract.

**Release Gate**: Planning performs no deploy. After implementation, quickstart, full local CI, PR review and merge, the release flow may run `./scripts/prepare-release.sh YYYY.MM.DD.N`, `infra/scripts/cd-remote.sh --dry-run`, then `--execute` only when the production gate is met. The user has deferred the standalone Codex Security scan; normal product/privacy assertions remain required and do not claim to replace that later audit.

**Target Platform**: GRAF server/cabinet plus the native macOS upload and embedded-cabinet shell on Apple Silicon macOS 14+.

**Project Type**: Web service with server-rendered cabinet and a native macOS capture/upload client.

**Performance Goals**: Matching uses bounded indexed database reads only, performs no provider network request, and evaluates at most 50 deduplicated candidates. Across at least 100 warmed synthetic resolves with four selected sources and 50 candidate rows, resolve completes within 200 ms p95; attempt consumption completes within 50 ms p95. The recording-start call is asynchronous and never gates capture. Failure never delays or blocks capture, meeting creation, upload, processing, playback or review.

**Constraints**: Actual recording time is the only time anchor. Automatic matching requires a successful authenticated recording-start attempt; absence of that attempt is treated as offline/recovery/unknown and never triggers retrospective matching. Every attempt expires exactly at `evaluated_at + 24 hours`; an expired attempt cannot be consumed. `declined_by_user` represents start-time continue-without-context and remains distinct from later `cleared_by_user`. A selected source must be current under the existing 24-hour freshness rule and have no later failed sync. Private/free-busy/all-day/cancelled/deleted/cross-owner/cross-workspace events are ineligible. Meeting attendees remain roster context only. Diagnostics and evidence contain reason codes/counts, not raw emails, descriptions, meeting links, passcodes, provider payloads, transcript text or audio.

**Scale/Scope**: MVP/internal workspace scale; multiple owner calendars and spaces; at most 50 bounded candidates per attempt; one unconsumed attempt per owner/local recording and one authoritative context row per meeting. Includes clear/no-match/ambiguous/correction/clear/recurring continuity and web/macOS parity. Excludes retrospective matching, auto-share, delivery, calendar mutation, speaker identity and multi-event timelines for one recording.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first MVP integrity**: Pass. Matching runs after local capture metadata exists and does not change ScreenCaptureKit, microphone capture, routing, start/stop, track alignment or local recording truth.
- **Visible consent and user control**: Pass with guard. 098 does not auto-start capture. Manual Record/Stop, visible capture state and one-action Stop remain unchanged. Ambiguity and explicit no-context choices are persisted and respected.
- **Data boundary and secret discipline**: Pass with required design. Provider credentials remain server-owned. Match state stores IDs, enums, counts and safe snapshots only; roster snapshots exclude raw email values and event descriptions/URLs.
- **Deletion truth and lifecycle accounting**: Pass with required design. Match state and immutable context snapshot fields join the meeting lifecycle, deletion accounting and source-disconnect cleanup paths.
- **Spec-driven delivery with testable gates**: Pass. Specify and clarify are complete. This plan produces research, data model, contracts and quickstart; checklist, tasks, analyze, GitHub issue sync and implementation remain mandatory.
- **Brand-distance and UX**: Pass. Existing GRAF cabinet primitives and calendar copy are reused. Public reference products do not supply UI, copy, assets or proprietary behavior.

No constitution violation is accepted or justified.

### Post-Design Constitution Re-Check

- **Research**: Pass. The selected algorithm is deterministic, bounded, no-provider-network and fail-soft; a successful recording-start attempt proves that matching happened live and prevents offline recovery from becoming retrospective matching.
- **Data model**: Pass. One bounded pre-meeting attempt plus one authoritative per-meeting context row are the minimum persistence needed for live/offline proof, idempotency, correction, stable history and recurring continuity.
- **Contracts**: Pass. A recording-start resolve endpoint creates the attempt and meeting creation consumes its ID atomically; existing PUT/DELETE paths remain explicit correction/clear operations; list/review projections disclose only authorized safe context.
- **Quickstart**: Pass. Validation covers clear, no-match, ambiguous, boundary, stale, private, all-day, manual/offline, title stability, cross-space, recurring, deletion and no-side-effect cases.

No post-design constitution violation is introduced.

## Validation Plan

Implementation validation is staged:

1. Unit tests for candidate eligibility, five-minute pre-start grace, five-minute back-to-back guard, duplicate collapse, stale-source veto, state transitions, title precedence and safe roster snapshot construction.
2. Contract tests for recording-start resolve idempotency, atomic attempt consumption, GET/PUT/DELETE calendar-context responses, owner-only candidate choice, list/review projections, CSRF on mutations and backward-safe defaults for older clients.
3. Integration tests for clear match, no calendar, ambiguity, private/free-busy, all-day, weak-signal, manual upload, live vs offline recovery, retry idempotency, user selection/clear, source rename/delete/cancel, multi-space ownership, recurring previous-recording authorization, deletion and disconnect.
4. Swift tests for server-owned match intent, persisted opaque attempt/event IDs, explicit no-context choice, recovered-queue default, create-meeting payload, prompt choice and embedded-cabinet parity, including `DesktopCabinetWorkspaceTests` and `DesktopCabinetUploadLinkTests`. No new native review UI is required.
5. Migration upgrade/downgrade, SQLite/Postgres-portable constraint checks, RLS inventory and focused Ruff.
6. Run [quickstart.md](./quickstart.md), then `infra/scripts/ci-local.sh` once at implementation closeout.

The standalone Codex Security scan is explicitly deferred by the user. Metadata-forbidden-content and authorization assertions remain ordinary acceptance tests because they are part of the feature requirements; their success must not be reported as completion of the deferred security audit.

## Project Structure

### Documentation (this feature)

```text
specs/098-calendar-auto-context-match/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   ├── requirements.md
│   └── calendar-context-readiness.md
├── contracts/
    ├── calendar-auto-context-api.md
    └── calendar-auto-context-ui.md
├── tasks.md
└── validation/
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── api/
│   ├── schemas.py                         # resolve/create and safe context projections
│   ├── ingest.py                          # atomic first-party attempt consumption
│   └── calendar.py                        # resolve plus GET/PUT/DELETE context contract
├── calendar/
│   ├── matching.py                        # new deterministic bounded matcher
│   ├── service.py                         # explicit correction/link reuse
│   ├── lifecycle.py                       # match-state/context deletion and disconnect accounting
│   └── audit.py                           # metadata-only match outcomes
├── cabinet/
│   ├── queries.py                         # list/review context and recurring predecessor reads
│   ├── view_models.py                     # safe list/detail/candidate projections
│   ├── rendering.py                       # existing server-rendered UI composition
│   ├── web_routes/                        # owner correction/clear actions
│   └── templates/cabinet/                 # list/review context fragments using existing primitives
├── db/models/
│   ├── meeting.py                         # persisted title provenance
│   └── calendar.py                        # recording-start attempt and authoritative context row
└── db/migrations/versions/
    └── 0021_calendar_auto_context_match.py

apps/server/tests/
├── unit/test_calendar_auto_context_match.py
├── contract/test_calendar_context_contract.py
├── contract/test_calendar_rls_contract.py
├── integration/test_calendar_auto_context_match.py
├── integration/test_calendar_access_policy.py
└── integration/test_calendar_deletion_lifecycle.py

apps/macos/
├── Shared/Sources/Models/
│   ├── AudioModels.swift                  # durable attempt ID and selected event ID
│   └── CalendarContextModels.swift        # resolve response and explicit no-context state
├── RecApp/App/TwoBrainRecApp.swift        # non-blocking recording-start resolve
├── RecApp/Sources/Upload/
│   ├── DesktopUploadQueueService.swift    # attempt ID persistence; recovered queues have none
│   └── DesktopUploadClient.swift          # resolve call and atomic create payload
└── Shared/Tests/
    ├── DesktopCalendarReminderTests.swift
    ├── DesktopUploadQueueTests.swift
    └── DesktopUploadClientTests.swift
```

**Structure Decision**: Keep the existing backend/cabinet/macOS split. The server owns candidate evaluation and durable decision intent; the macOS client starts a best-effort resolve request after capture begins and persists only the opaque attempt ID plus a selected event ID where the existing capture path needs it. Recovered queues without an attempt cannot auto-match. The embedded cabinet remains the desktop review surface, so web and desktop use one read model. A small `calendar/matching.py` module isolates deterministic product logic without adding a framework, worker or provider call.

## Phase 0: Research

See [research.md](./research.md).

## Phase 1: Design And Contracts

See [data-model.md](./data-model.md), [contracts/calendar-auto-context-api.md](./contracts/calendar-auto-context-api.md), [contracts/calendar-auto-context-ui.md](./contracts/calendar-auto-context-ui.md), and [quickstart.md](./quickstart.md).

## Complexity Tracking

No constitution violations or additional application layers are introduced.
