# Quickstart: Calendar Settings UI

**Feature**: 063-calendar-settings-ui

This guide describes validation scenarios for implementation. Commands reference tests expected to be created during `$speckit-tasks` / `$speckit-implement`.

## Prerequisites

- Active feature directory: `specs/063-calendar-settings-ui/`
- Local dependencies installed for server and macOS workspaces.
- Safe calendar fixtures only. Do not use real tokens, app passwords, private event text, attendee email dumps, signed links, passcodes, or raw provider payloads in committed tests/evidence.

## Focused Validation Scenarios

### 1. Web Cabinet Navigation

Expected:

- User reaches `Настройки -> Интеграции -> Календари`.
- Page is actionable, not a placeholder.
- Empty state explains read-only access and offers provider choices.

### 2. Provider List And Connection Methods

Expected:

- All required providers appear with Russian labels.
- Connection method category is understandable.
- Read-only boundary appears before authorization or credential submission.
- No raw credentials are displayed after submission.

### 3. Connected Source With Zero Selected Calendars

Expected:

- After source connection, zero calendars are selected by default.
- Source shows "connected, selection needed" behavior.
- Source does not contribute upcoming events or prompts until calendars are selected.
- User can select calendars and can also deselect all calendars without disconnecting the source.

### 4. Calendar Selection Interface

Expected:

- Each readable calendar can be toggled independently.
- Selected count is visible and screen-reader understandable.
- Shared, private, hidden, unavailable, duplicate-label, and delegated states are safe and understandable.

### 5. Event Category Defaults And Preferences

Expected:

- Default settings include timed events with participants or meeting link/location.
- All-day events do not produce prompts by default.
- Private/free-busy prompt candidates do not produce prompts by default.
- User can opt into supported categories and preview changes.

### 6. Sync Health And Stale State

Expected:

- Source becomes stale when last successful sync is older than 24 hours or latest sync attempt failed.
- Stale state appears on the source row/card and in sync details.
- Upcoming preview repeats stale state only when affected by stale source data.
- Manual sync/reconnect/safe troubleshooting action is visible where appropriate.

### 7. Duplicate And Overlap Handling

Expected:

- Same stable provider event ID or same meeting link is shown as one meeting with multiple sources.
- Similar title/organizer/time alone does not deduplicate.
- Partial overlap such as 12:00-13:00 and 12:30-13:30 creates a conflict only from 12:30-13:00.
- UI asks the user to choose event context or continue without calendar context.
- Active recording context does not switch automatically.

### 8. Private And Free/Busy Safety

Expected:

- Private/free-busy events show only safe minimum information.
- No private title, agenda, attendee email dump, meeting link, passcode, attachment link, signed link, or raw payload appears in UI, errors, logs, screenshots, or evidence.

### 9. Disconnect

Expected:

- Confirmation explains future sync stops and credentials are removed/revoked where 2brain Rec controls them.
- Copy does not promise deletion outside 2brain Rec control.
- Source no longer contributes future meetings after disconnect.

### 10. Embedded macOS Cabinet

Expected:

- Calendar settings open inside the embedded cabinet.
- Active recording indicator and one-action Stop remain visible when recording is active.
- Manual recording remains available when policy permits, even if no calendar is connected.
- Network/auth unavailable state stays inside embedded content and does not hide native controls.

## Focused Test Commands

Run focused tests during implementation as they are added:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_calendar_settings_contract.py \
  tests/unit/test_calendar_settings_view_models.py \
  tests/integration/test_calendar_settings_flow.py

cd apps/server && PYTHONPATH=src uv run --extra dev ruff check .

swift test --package-path apps/macos --disable-swift-testing --filter 'Calendar|Cabinet|DesktopCalendarReminder'
```

## Closeout Gate

Before implementation closeout or PR:

```sh
infra/scripts/ci-local.sh
```

No production deploy is part of 063 planning or implementation unless the user separately approves a release/deploy gate.

## Validation Evidence - 2026-06-28

Focused server validation:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_calendar_settings_contract.py \
  tests/unit/test_calendar_settings_view_models.py \
  tests/integration/test_calendar_settings_flow.py \
  tests/integration/test_calendar_persistence.py
```

Result: `77 passed, 1 warning`.

Focused server lint:

```sh
cd apps/server && PYTHONPATH=src uv run --extra dev ruff check .
```

Result: `All checks passed!`.

Focused macOS validation:

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'Calendar|Cabinet|DesktopCalendarReminder'
```

Result: `96 tests, 0 failures`.

Full macOS validation:

```sh
swift test --package-path apps/macos
```

Result: `678 tests, 0 failures`.

Forbidden-content scan:

```sh
rg -n -i -e "authorization\s*[:=]\s*bearer\s+[a-z0-9._~+/-]{10,}" \
  -e "x-amz-signature=[a-z0-9]" \
  -e "-----BEGIN [A-Z ]*PRIVATE KEY-----" \
  -e "(refresh_token|access_token|id_token|app_password|api[_-]?key|passcode|signed_url|attendee_email_dump|raw_event_payload)\s*[:=]\s*[^,[:space:]}]{4,}" \
  specs/063-calendar-settings-ui \
  apps/server/src/twobrain_rec_server/cabinet \
  apps/server/src/twobrain_rec_server/calendar \
  apps/server/tests/contract/test_calendar_settings_contract.py \
  apps/server/tests/unit/test_calendar_settings_view_models.py \
  apps/server/tests/integration/test_calendar_settings_flow.py \
  apps/server/tests/fixtures/calendar_settings.py \
  apps/macos/Shared/Tests \
  apps/macos/RecApp/Sources/Cabinet \
  apps/macos/RecApp/Sources/Calendar \
  apps/macos/Shared/Sources/Models
```

Result: no credential, token, signed-link, raw-provider-payload, attendee dump,
or private event evidence found. Remaining matches were source-code detector
references only: `contains_passcode` fields and the passcode detector in
calendar conference-link parsing.

Removed-provider catalog scan: exact disallowed provider-name scan returned no
matches in the calendar feature surface. The command is not embedded here so
removed provider names do not re-enter the feature docs.

Full high-risk local gate:

```sh
infra/scripts/ci-local.sh
```

Result: `ci_local_result=pass`; server tests `862 passed, 4 skipped,
103 warnings`; server lint passed; Python compile passed; production compose
config rendered; deployment evidence scan passed. RLS validation remains a
local `postgres_test` boundary with `live_production_enforcement=not_inspected`.
