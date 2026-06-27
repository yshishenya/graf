# Implementation Plan: Calendar Context Ingestion

**Branch**: `060-calendar-context-ingestion` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/060-calendar-context-ingestion/spec.md`

## Summary

Feature 060 adds the first calendar layer for 2brain Rec: read-only calendar connection, provider-neutral future-event ingestion, recording-time context selection, meeting naming, calendar roster extraction, one-minute join prompts, event-start record prompts, provider capability reporting, and lifecycle accounting. It explicitly does not send messages, mutate calendars, auto-join meetings, auto-record, or match old recordings.

The implementation approach is server-owned and provider-neutral: add a calendar domain/service layer to the existing FastAPI backend, persist normalized calendar snapshots and metadata-only audit events in Postgres, expose a small `/api/v1/calendar` API plus desktop upcoming-context contract, and add minimal macOS reminder/context handling that preserves visible local Record/Stop authority.

## Technical Context

**Language/Version**: Python 3.13 backend; Swift Package macOS app.

**Primary Dependencies**: Existing FastAPI, Pydantic v2, SQLAlchemy asyncio, Alembic, httpx, structlog, pytest, ruff; Swift Foundation/AppKit for local in-app prompts; add `cryptography` for server-side calendar credential envelope encryption.

**Storage**: Existing Postgres/Alembic for calendar source, selected calendar, event snapshot, roster, context link, reminder state, and audit/lifecycle records. MinIO is not used for calendar content in 060.

**Testing**: `pytest` through `uv run --extra dev`, OpenAPI contract drift test, focused server unit/contract tests, macOS `swift test --package-path apps/macos --disable-swift-testing`, and final `infra/scripts/ci-local.sh`.

**Risk / Validation Lane**: High-risk product area. The feature touches external credentials, privacy-sensitive calendar content, retention/deletion accounting, provider egress, desktop reminders near recording start, and API contracts.

**Release Gate**: No deploy for planning and implementation closeout unless the user separately approves a release. Production deploy would require `infra/scripts/cd-remote.sh --dry-run` and then `--execute` only after release approval.

**Target Platform**: 2brain Rec server on Docker/Postgres; macOS desktop app for local reminders and visible recording control.

**Project Type**: Web service plus macOS desktop app.

**Performance Goals**: Calendar sync must not block upload, processing, playback, or review. A sync run is bounded to selected calendars, a rolling 12-month future horizon, provider pagination/rate limits, and safe timeout/failure states. Upcoming prompt lookup uses stored future-event snapshots, honors request limits, and must fail closed without starting recording.

**Constraints**: Read-only provider access; server owns credentials; desktop never stores provider app passwords/OAuth refresh tokens; logs/evidence never include provider secrets, private event text, attendee dumps, passcodes, signed links, or live credential paths; no retrospective matching of past recordings; no auto-record in 060; active capture visibility and one-action Stop remain mandatory for any later auto-record feature.

**Scale/Scope**: MVP/internal workspace scale with selected calendars per user/workspace, rolling 12-month future sync, recurrence bounded by provider time-range queries, and fixture coverage for attendee-heavy events, recurrence exceptions, private/free-busy events, duplicate calendars, Google/Microsoft/Bitrix rich payloads, and Yandex/Mail.ru-style CalDAV.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first MVP integrity**: Pass. 060 does not change capture pipeline, audio routing, microphone/system audio, driver, upload integrity, or MediaScribe behavior. Recording may only be started by existing visible local controls after prompt/manual action.
- **Visible consent and user control**: Pass with constraint. 060 can show join and record prompts but must not auto-record, hide capture, or remove one-action Stop. Later auto-record requires a separate high-risk feature.
- **Data boundary and secret discipline**: Pass with required design. Calendar credentials remain server-owned, sealed/encrypted at rest, never stored on desktop, never exposed in logs/diagnostics/API responses/evidence.
- **Deletion truth and lifecycle accounting**: Pass with required design. Calendar context is treated as meeting content under 2brain Rec control; provider events remain outside deletion control unless a later write adapter exists.
- **Spec-driven delivery with testable gates**: Pass. Spec and clarification are complete; plan creates research, data model, contracts, and quickstart; checklist/analyze/tasks remain required before implementation.

No constitution violations are justified or accepted in this plan.

### Post-Design Constitution Re-Check

- **Contracts**: Pass. Calendar API, desktop reminder, and provider adapter contracts preserve read-only provider access, no auto-record, no auto-send, and metadata-safe surfaces.
- **Data model**: Pass. Calendar credentials are sealed, calendar content is treated as meeting content, participant emails remain candidates only, and disconnect/deletion lifecycle is explicit.
- **Quickstart**: Pass. Validation covers credential secrecy, provider failure, disconnect/deletion, reminder prompts, no auto-record, and repository CI.

No post-design constitution violations were introduced.

## Validation Plan

Focused validation during implementation:

- Server unit tests for provider-neutral event normalization, iCalendar field extraction, conference-link detection, capability mapping, sensitive-field redaction, lifecycle/disconnect behavior, and credential-envelope boundaries.
- Server contract tests for `/api/v1/calendar` OpenAPI additions and desktop upcoming-context responses.
- Server integration tests for Postgres persistence, tenant scoping/RLS readiness where applicable, disconnect purge behavior, and deletion accounting.
- Fixture tests for Yandex/Mail.ru-style CalDAV, generic CalDAV, Nextcloud/SOGo-like CalDAV, private/free-busy-only events, recurrence exceptions, attendee-heavy events, duplicate event copies, Bitrix24 payloads, Google Meet conference data, Microsoft Teams onlineMeeting data, and Exchange EWS-style recurrence exceptions.
- macOS focused tests for one-minute join prompt state, event-start record prompt state, no auto-record, visible Record/Stop authority, metadata-safe reminder copy, accessibility, localization, and brand-distance evidence.
- Forbidden-content scans covering logs, diagnostics, committed docs/evidence, and API/cabinet surfaces.

Closeout validation:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q
cd apps/server && PYTHONPATH=src uv run --extra dev ruff check .
swift test --package-path apps/macos --disable-swift-testing --filter 'Calendar|DesktopUpload|CaptureControl|AppControlAccessibility'
infra/scripts/ci-local.sh
```

Deploy validation is not required for this planning step and must not run without a separate release/deploy approval.

## Project Structure

### Documentation (this feature)

```text
specs/060-calendar-context-ingestion/
├── plan.md
├── research.md
├── provider-deep-dive.md
├── data-model.md
├── quickstart.md
├── checklists/
│   ├── calendar-integration.md
│   └── requirements.md
└── contracts/
    ├── calendar-context.openapi.yaml
    ├── desktop-reminder-contract.md
    └── provider-adapter-contract.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── api/
│   ├── calendar.py              # new /api/v1/calendar routes
│   └── schemas.py               # calendar request/response schemas
├── calendar/                    # new provider-neutral calendar domain
│   ├── adapters.py              # provider adapter protocol and registry
│   ├── audit.py                 # metadata-only calendar audit events
│   ├── capabilities.py          # provider capability matrix
│   ├── conference_links.py      # meeting URL classification
│   ├── credentials.py           # sealed credential envelope boundary
│   ├── lifecycle.py             # disconnect, purge, deletion accounting
│   ├── normalize.py             # provider -> event snapshot normalization
│   ├── service.py               # source connect/sync/upcoming/context link
│   └── sync.py                  # rolling 12-month future sync orchestration
├── db/
│   ├── models/calendar.py       # new calendar tables
│   └── migrations/versions/     # new Alembic migration
└── domain/statuses.py           # calendar enums/status strings if needed

apps/server/tests/
├── contract/
│   ├── test_calendar_context_contract.py
│   └── test_calendar_no_secret_content_egress.py
├── fixtures/
│   └── calendar.py
├── integration/
│   ├── test_calendar_persistence.py
│   ├── test_calendar_disconnect_lifecycle.py
│   ├── test_calendar_deletion_lifecycle.py
│   ├── test_calendar_access_policy.py
│   └── test_calendar_provider_failures.py
└── unit/
    ├── test_calendar_normalization.py
    ├── test_calendar_conference_links.py
    ├── test_calendar_credentials.py
    ├── test_calendar_participants.py
    └── test_calendar_recipient_candidates.py

apps/macos/
├── RecApp/Sources/Calendar/      # new lightweight desktop context/reminder code
└── Shared/Tests/
    └── DesktopCalendarReminderTests.swift
```

The tree shows the new calendar-owned surface. Existing integration points touched by tasks stay authoritative in `tasks.md`: ingest, cabinet/access, meeting lifecycle, desktop upload, prompt UI, app wiring, shared models, lockfile, changelog, and current product status.

**Structure Decision**: Use the existing FastAPI/SQLAlchemy/Pydantic backend and Swift Package macOS app. Add one calendar domain package instead of scattering provider logic through ingest/cabinet. Keep desktop work to reminder/context display and existing Record/Stop handoff; provider credentials and sync stay server-side.

## Complexity Tracking

No constitution gate violations and no extra application/project are introduced.
