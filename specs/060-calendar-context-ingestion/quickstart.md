# Quickstart: Calendar Context Ingestion

**Feature**: 060-calendar-context-ingestion

## Purpose

Validate that calendar integration ingests future calendar context safely and uses it for upcoming prompts and recording-time context without sending messages, mutating calendars, auto-joining, or auto-recording.

## Prerequisites

- Local server dependencies available through `uv`.
- Docker available for Postgres-backed validation.
- macOS Swift package available under `apps/macos`.
- No real calendar credentials, real meeting links, attendee email dumps, passcodes, transcript text, or private event text in committed fixtures or evidence.

## 1. Server Contract And Unit Checks

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_calendar_credentials.py \
  tests/unit/test_calendar_normalization.py \
  tests/unit/test_calendar_conference_links.py \
  tests/unit/test_calendar_provider_fixtures.py \
  tests/unit/test_calendar_recording_context.py \
  tests/unit/test_calendar_participants.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_redaction.py \
  tests/unit/test_calendar_recipient_candidates.py
```

Expected outcome:

- Provider fixture payloads normalize into the common event contract.
- Private/free-busy events do not fabricate title, attendees, organizer, or links.
- Conference links are classified without logging full URLs/passcodes.
- Credential envelope tests prove raw secrets are not returned or logged.
- Recording-time context selection, roster separation, redaction, and recipient-candidate boundaries stay deterministic and metadata-safe.

## 2. API Contract Checks

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_calendar_context_contract.py \
  tests/contract/test_calendar_no_secret_content_egress.py \
  tests/contract/test_calendar_rls_contract.py \
  tests/contract/test_openapi_contract_drift.py
```

Expected outcome:

- Runtime OpenAPI includes the calendar context endpoints from `contracts/calendar-context.openapi.yaml`.
- API responses expose source/event state but no credential payloads.
- Calendar diagnostics and audit metadata redact secret/content-bearing fields.

## 3. Postgres Persistence And Lifecycle Checks

```sh
docker compose -f infra/docker-compose.dev.yml up -d rec-postgres rec-minio rec-minio-init rec-migrate
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_calendar_persistence.py \
  tests/integration/test_calendar_disconnect_lifecycle.py \
  tests/integration/test_calendar_deletion_lifecycle.py \
  tests/integration/test_calendar_access_policy.py \
  tests/integration/test_calendar_provider_failures.py \
  tests/integration/test_meeting_share_links.py \
  tests/integration/test_persistent_ingest_storage.py
```

Expected outcome:

- Calendar sources, selected calendars, event snapshots, participants, conference links, context links, reminder states, and audit events persist with workspace scoping.
- Rolling 12-month future horizon excludes past events.
- Disconnect purges credentials and unmatched/future cache while preserving matched meeting context under meeting retention/deletion policy.
- Deleting a meeting retention-accounts linked calendar context.
- Provider downtime leaves meeting review/upload available with `calendar_context_unavailable`.
- Calendar attendees do not create meeting access or share grants.
- Meeting create responses expose `title` and `title_source` so calendar-based
  names remain distinguishable from user and generic titles.

## 4. Desktop Reminder Checks

```sh
swift test --package-path apps/macos --disable-swift-testing --filter DesktopCalendarReminder
swift test --package-path apps/macos --disable-swift-testing --filter 'CaptureControl|AppControlAccessibility|DesktopUploadClient'
```

Expected outcome:

- One minute before event start, desktop state can show a join/open prompt when a meeting link is authorized.
- At event start, desktop state can show a record prompt with the event context.
- Neither prompt starts recording automatically in 060.
- Existing visible Record/Stop and accessibility checks still pass.

## 5. Fixture Matrix

Run the focused fixture suite once implementation provides the fixtures:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/unit/test_calendar_provider_fixtures.py \
  tests/unit/test_calendar_normalization.py
```

Fixture coverage must include:

- Yandex/Mail.ru-style CalDAV.
- Generic CalDAV with custom URL.
- Private/free-busy-only event.
- Recurring series with moved instance.
- Recurring series with cancelled instance.
- Attendee-heavy event.
- Duplicate organizer/attendee copies.
- Bitrix24 event with CRM links.
- Google event with Meet conference data.
- Microsoft Graph event with Teams onlineMeeting.
- Exchange EWS recurring exception.

## 6. Forbidden Content Scan

```sh
rg -n "\b(refresh_token|app_password|signed_url|attendee_email_dump|raw_event_payload)\s*[:=]|Authorization\s*:|Bearer [A-Za-z0-9._~+/-]+|\bpasscode\s*[:=]" \
  specs/060-calendar-context-ingestion apps/server/tests/fixtures apps/server/src/twobrain_rec_server apps/macos \
  --glob 'specs/060-calendar-context-ingestion/**' \
  --glob 'apps/server/tests/fixtures/calendar.py' \
  --glob 'apps/server/src/twobrain_rec_server/calendar/**' \
  --glob 'apps/server/src/twobrain_rec_server/api/calendar.py' \
  --glob 'apps/macos/RecApp/Sources/Calendar/**' \
  --glob 'apps/macos/Shared/Sources/Models/CalendarContextModels.swift' \
  --glob '!specs/060-calendar-context-ingestion/quickstart.md' \
  --glob '!specs/060-calendar-context-ingestion/validation/forbidden-content-notes.md'
```

Expected outcome:

- No real secrets, raw provider tokens, meeting passcodes, signed links, private event text, or attendee dumps are present.
- Placeholder schema field names are acceptable only when they do not contain real values.

## 7. Repository Gate Before Closeout

Run from the repository root:

```sh
infra/scripts/ci-local.sh
```

Expected outcome:

- Server tests pass.
- Ruff passes.
- Python compile passes.
- RLS validation boundary passes.
- Production compose config validates.
- Deployment evidence scan passes.

## Out Of Scope For This Quickstart

- Production deploy or remote smoke.
- Calendar invite mutation.
- Summary/transcript/report delivery.
- Bot auto-join.
- "Do not ask again" or always-record automation.
- Retrospective matching of past recordings.
