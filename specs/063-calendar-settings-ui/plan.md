# Implementation Plan: Calendar Settings UI

**Branch**: `codex/063-calendar-settings-ui` | **Date**: 2026-06-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/063-calendar-settings-ui/spec.md`

## Summary

Feature 063 adds the user-facing settings layer for read-only calendar integrations. Users can find `Настройки -> Интеграции -> Календари`, connect a supported provider, explicitly choose calendars, see sync health, manage prompt behavior, preview safe upcoming behavior, and disconnect sources without surprise recording or calendar mutation.

The implementation approach is to reuse feature 060's server-owned calendar layer and the existing cabinet/macos embedding surfaces. The server cabinet provides the settings UI, view models, safe copy, and recovery states. The macOS app only needs to route the embedded cabinet to the settings surface while preserving native active-recording visibility and one-action Stop. No new provider adapter layer, bot join, calendar mutation, summary sending, attendee sharing, or auto-record behavior is introduced.

## Technical Context

**Language/Version**: Python 3.13 backend; Jinja/HTMX/CSS server-rendered cabinet; Swift Package macOS app.

**Primary Dependencies**: Existing FastAPI, Pydantic v2, SQLAlchemy asyncio, Jinja2 templates, cabinet HTMX/static assets, pytest, ruff; SwiftUI/AppKit/WebKit-based embedded cabinet. No new dependency is planned for 063.

**Storage**: Existing Postgres/Alembic calendar tables from 060 for sources, credentials, external calendars, event snapshots, context links, reminder states, and audit events. 063 adds minimal `CalendarSettingsPreference` persistence for event-category preferences, prompt toggles, and local display preferences because those are user settings rather than provider credentials or event snapshots. MinIO is not used for calendar settings.

**Testing**: Focused server pytest contract/unit/integration tests, ruff for touched backend code, focused Swift tests for embedded cabinet routing and prompt safety, quickstart scenarios, and final `infra/scripts/ci-local.sh` before implementation closeout.

**Risk / Validation Lane**: High-risk product area. The feature touches privacy-sensitive calendar settings, provider credentials display boundaries, recording-adjacent prompts, embedded macOS UX, localization, accessibility, and degraded/unavailable states.

**Release Gate**: No deploy for planning. Implementation must not run production deploy without separate release approval. If a later release is approved, use `infra/scripts/cd-remote.sh --dry-run` before `--execute`.

**Target Platform**: 2brain Rec server web cabinet; embedded cabinet inside the macOS app on Apple Silicon macOS MVP.

**Project Type**: Web service plus server-rendered cabinet plus macOS desktop shell integration.

**Performance Goals**: Calendar settings initial state renders from stored provider/source/calendar summaries without provider network calls. Manual sync request returns an accepted/already-running/error state within 2 seconds under normal server conditions and does not wait for provider sync completion before giving feedback. Upcoming preview remains bounded to safe summaries and does not block manual recording controls.

**Constraints**: Calendar access remains read-only. Provider credentials are server-owned and never stored in the desktop app. UI, errors, screenshots, diagnostics, and evidence must not show raw tokens, app passwords, private event text, attendee email dumps, signed links, passcodes, full meeting URLs, or raw provider payloads. Manual Record/Stop remains available when policy permits. Active recording visibility and one-action Stop remain native. No retrospective matching. No real auto-record in 063.

**Scale/Scope**: MVP/internal-user scale with multiple connected sources, selected calendars per source, the supported provider preset list from 060, upcoming preview limited to safe future summaries, and explicit handling for duplicate events, overlapping events, stale sync, private/free-busy events, and policy-constrained settings.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first MVP integrity**: Pass. 063 does not change capture, audio routing, upload, MediaScribe, or driver behavior. Calendar prompts remain prompts only.
- **Visible consent and user control**: Pass with required guard. Calendar settings must not enable hidden recording or auto-record. Manual Record/Stop stays visible and available when policy permits.
- **Data boundary and secret discipline**: Pass with required design. Credentials stay server-owned; desktop stores no provider credentials; settings and evidence are metadata-safe.
- **Deletion truth and lifecycle accounting**: Pass with required copy. Disconnect stops future sync and removes/revokes credentials where 2brain Rec controls them; existing meeting context follows meeting retention/deletion policy.
- **Spec-driven delivery with testable gates**: Pass. Spec and clarify are complete; this plan creates research, data model, contracts, quickstart, and updates agent context. Checklist, tasks, analyze, issue sync, and implementation remain required before code closeout.

No constitution violations are justified or accepted in this plan.

### Post-Design Constitution Re-Check

- **Research**: Pass. Decisions preserve server-owned read-only calendar access, explicit calendar selection, safe sync health display, and no auto-record.
- **Data model**: Pass. Entities are UI/read-model and preference focused; credential and event content boundaries remain inherited from 060.
- **Contracts**: Pass. UI and embedded macOS contracts keep calendar settings in the server-owned cabinet and active recording truth in the native shell.
- **Quickstart**: Pass. Validation covers privacy, stale sync, empty/error/loading states, overlap conflict choice, duplicate handling, accessibility, localization, and embedded macOS recording visibility.

No post-design constitution violations were introduced.

## Validation Plan

Focused validation during implementation:

- Server unit tests for calendar settings view models: provider list labels, source state labels, stale sync threshold, no-default-calendar selection, event-category defaults, duplicate event grouping, overlap conflict grouping, and safe copy.
- Server contract tests for the calendar settings UI/read-model contract, including zero selected calendars after connection and empty selected-calendar state when a source is connected but not used.
- Server integration tests for source connect/select/sync/disconnect flows through existing 060 calendar APIs and minimal `CalendarSettingsPreference` persistence.
- Cabinet rendering/accessibility checks for keyboard navigation, focus states, screen-reader labels, loading/error/empty states, destructive disconnect confirmation, and no secret/private-content leakage.
- macOS focused tests for settings route availability inside the embedded cabinet, native active-recording strip visibility, one-action Stop preservation, provider credential non-storage/non-rendering, prompt settings not enabling auto-record, and network/auth unavailable states.
- Forbidden-content scans over rendered settings, errors, fixtures, committed docs/evidence, and test outputs.

Closeout validation:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q
cd apps/server && PYTHONPATH=src uv run --extra dev ruff check .
swift test --package-path apps/macos --disable-swift-testing --filter 'Calendar|Cabinet|DesktopCalendarReminder'
infra/scripts/ci-local.sh
```

Deploy validation is not required for this planning step and must not run without separate release/deploy approval.

## Project Structure

### Documentation (this feature)

```text
specs/063-calendar-settings-ui/
├── plan.md
├── research.md
├── ux-research.md
├── data-model.md
├── design-handoff.md
├── design-qa.md
├── measurement.md
├── quickstart.md
├── checklists/
│   └── requirements.md
└── contracts/
    ├── calendar-settings-ui-contract.md
    └── embedded-macos-cabinet-contract.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── api/
│   ├── calendar.py              # existing 060 API surface reused by settings
│   └── schemas.py               # calendar/settings response and selection contract adjustments
├── cabinet/
│   ├── view_models.py           # calendar settings read models and safe display copy
│   ├── web.py                   # settings/integrations/calendar cabinet routes/fragments
│   ├── static/cabinet/
│   │   ├── cabinet.css          # existing cabinet styles extended for settings states
│   │   └── cabinet.js           # only if existing cabinet interaction needs small state handling
│   └── templates/cabinet/
│       ├── components/          # existing primitives/sections reused
│       ├── fragments/           # calendar settings fragments as needed
│       └── pages/               # calendar settings page content
└── calendar/
    └── service.py               # existing source/sync/selection behavior reused; no new provider layer

apps/server/tests/
├── contract/
│   └── test_calendar_settings_contract.py
├── integration/
│   └── test_calendar_settings_flow.py
└── unit/
    └── test_calendar_settings_view_models.py

apps/macos/
├── RecApp/Sources/Cabinet/      # embedded settings route and native shell preservation
├── RecApp/Sources/Calendar/     # prompt safety remains non-auto-record
└── Shared/Tests/                # focused calendar/cabinet prompt tests
```

**Structure Decision**: Use the existing backend/cabinet/macOS split. Calendar provider connection, credentials, sync, source state, selected calendars, upcoming events, and desktop prompt data stay in the 060 calendar layer. 063 adds the missing user-facing settings surface, safe read models, minimal `CalendarSettingsPreference` support, and embedded navigation. Avoid a separate frontend app, new provider adapters, new background system, or new calendar mutation layer.

## Complexity Tracking

No constitution gate violations and no extra application/project are introduced.
