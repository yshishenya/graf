# Tasks: Calendar Context Ingestion

**Input**: Design documents from `/specs/060-calendar-context-ingestion/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `provider-deep-dive.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required. This is a high-risk product lane because it touches provider credentials, sensitive calendar content, API contracts, retention/deletion behavior, and desktop recording prompts.

**Organization**: Tasks are grouped by user story so the P1 calendar layer can be implemented and validated independently before P2 recipient-candidate work.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it edits different files or independent test fixtures.
- **[Story]**: Maps to the user story in `spec.md`.
- Every task includes exact file paths.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare evidence, fixture structure, and requirement-quality gaps before implementation.

- [X] T001 Create the implementation evidence log at `specs/060-calendar-context-ingestion/validation/implementation-evidence.md` with sections for tests, provider fixtures, privacy scan, RLS proof, desktop proof, and known limitations.
- [X] T002 Resolve and check off requirement-quality gaps in `specs/060-calendar-context-ingestion/checklists/calendar-integration.md`, updating `specs/060-calendar-context-ingestion/spec.md` or `specs/060-calendar-context-ingestion/plan.md` first if any checklist item is still not objectively testable.
- [X] T003 [P] Create synthetic provider fixture guidance at `apps/server/tests/fixtures/calendar/README.md` describing no-private-calendar-content rules, attendee caps, passcode redaction, and provider limitation markers.
- [X] T004 [P] Create the synthetic calendar fixture module at `apps/server/tests/fixtures/calendar.py` for Yandex, Mail.ru, Google Calendar, Microsoft Graph, Exchange EWS, Bitrix24, Nextcloud/SOGo-like CalDAV, and custom CalDAV/on-prem samples.
- [X] T005 [P] Create forbidden-content evidence notes at `specs/060-calendar-context-ingestion/validation/forbidden-content-notes.md` listing the exact strings and patterns that must never appear in logs, API responses, screenshots, or evidence.
- [X] T006 Record the selected risk/validation lane and the no-deploy implementation boundary in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the provider-neutral calendar domain, persistence, API shell, privacy boundary, and test harness that all user stories depend on.

**CRITICAL**: No user story implementation starts until this phase is complete.

### Tests First

- [X] T007 [P] Add calendar persistence and migration tests in `apps/server/tests/integration/test_calendar_persistence.py` covering source, credential envelope metadata, external calendar, event snapshot, participant, conference-link, meeting-context link, reminder state, and audit rows.
- [X] T008 [P] Add calendar RLS inventory tests in `apps/server/tests/contract/test_calendar_rls_contract.py` requiring all new calendar tables to appear in `apps/server/src/twobrain_rec_server/db/rls_validation.py`.
- [X] T009 [P] Add API contract tests in `apps/server/tests/contract/test_calendar_context_contract.py` from `specs/060-calendar-context-ingestion/contracts/calendar-context.openapi.yaml`.
- [X] T010 [P] Add calendar no-secret/no-content-egress tests in `apps/server/tests/contract/test_calendar_no_secret_content_egress.py` covering credentials, attendee dumps, passcodes, full meeting URLs, agenda text, attachment links, and raw provider payloads.
- [X] T011 [P] Add calendar credential envelope tests in `apps/server/tests/unit/test_calendar_credentials.py` for sealed storage, fingerprint-only API responses, purge behavior, and redacted error messages.
- [X] T012 [P] Add calendar normalization tests in `apps/server/tests/unit/test_calendar_normalization.py` for unsupported, not-returned, private-redacted, free-busy-only, unknown, and admin-policy-dependent field states.
- [X] T013 [P] Add conference-link classifier tests in `apps/server/tests/unit/test_calendar_conference_links.py` for Telemost, MTS Link, Kontur.Talk, TrueConf, VK Calls, Zoom, Google Meet, Microsoft Teams, Webex, and generic links.
- [X] T014 [P] Add provider fixture tests in `apps/server/tests/unit/test_calendar_provider_fixtures.py` that prove fixture coverage for Yandex, Mail.ru, Google Calendar, Microsoft Graph, Exchange EWS, Bitrix24, VK WorkSpace/custom CalDAV, Mailion/MyOffice, R7-Office, CommuniGate Pro, RuPost, and Nextcloud/SOGo-like CalDAV.

### Implementation

- [X] T015 Add calendar status and reason enums to `apps/server/src/twobrain_rec_server/domain/statuses.py` and `apps/server/src/twobrain_rec_server/domain/reasons.py`.
- [X] T016 Add calendar SQLAlchemy models in `apps/server/src/twobrain_rec_server/db/models/calendar.py` for `CalendarSource`, `CalendarCredentialEnvelope`, `ExternalCalendar`, `CalendarEventSnapshot`, `CalendarParticipant`, `ConferenceLinkCandidate`, `RecordingCalendarContextLink`, `CalendarReminderState`, and `CalendarAuditEvent`.
- [X] T017 Export the new calendar models from `apps/server/src/twobrain_rec_server/db/models/__init__.py`.
- [X] T018 Add Alembic migration `apps/server/src/twobrain_rec_server/db/migrations/versions/0010_calendar_context_ingestion.py` with indexes, uniqueness constraints, retention/deletion fields, and PostgreSQL RLS policies for all calendar tables.
- [X] T019 Update RLS table inventory and production-state coverage in `apps/server/src/twobrain_rec_server/db/rls_validation.py` for every new calendar table.
- [X] T020 Add Pydantic request/response schemas to `apps/server/src/twobrain_rec_server/api/schemas.py` for provider presets, calendar sources, selected calendars, sync responses, upcoming events, desktop prompts, and meeting calendar context links.
- [X] T021 Create the calendar package entrypoint in `apps/server/src/twobrain_rec_server/calendar/__init__.py` with stable exports for services and adapters.
- [X] T022 Add `cryptography` to `apps/server/pyproject.toml` and `apps/server/uv.lock`, then implement sealed credential-envelope helpers in `apps/server/src/twobrain_rec_server/calendar/credentials.py`.
- [X] T023 Implement provider capability presets in `apps/server/src/twobrain_rec_server/calendar/capabilities.py` for Yandex, Mail.ru, Google Calendar, Microsoft Graph, Exchange EWS, Bitrix24, VK WorkSpace/custom CalDAV, Mailion/MyOffice, R7-Office, CommuniGate Pro, RuPost, and Nextcloud/SOGo-like CalDAV.
- [X] T024 Implement metadata-only calendar audit helpers in `apps/server/src/twobrain_rec_server/calendar/audit.py`.
- [X] T025 Implement normalized event mapping helpers in `apps/server/src/twobrain_rec_server/calendar/normalize.py`.
- [X] T026 Implement conference-link parsing and safe URL handling in `apps/server/src/twobrain_rec_server/calendar/conference_links.py`.
- [X] T027 Implement calendar source, event, participant, and context orchestration in `apps/server/src/twobrain_rec_server/calendar/service.py`.
- [X] T028 Implement bounded future sync orchestration in `apps/server/src/twobrain_rec_server/calendar/sync.py`.
- [X] T029 Implement disconnect, purge, and meeting-retention lifecycle helpers in `apps/server/src/twobrain_rec_server/calendar/lifecycle.py`.
- [X] T030 Create provider adapter protocol and registry in `apps/server/src/twobrain_rec_server/calendar/adapters.py`.
- [X] T031 Implement the generic CalDAV/iCalendar adapter in `apps/server/src/twobrain_rec_server/calendar/adapters.py` with explicit timeouts, pagination/report bounds, and no attachment-file fetching.
- [X] T032 Implement the Google Calendar read-only adapter in `apps/server/src/twobrain_rec_server/calendar/adapters.py` with event mapping and safe limitation states.
- [X] T033 Implement the Microsoft Graph read-only adapter in `apps/server/src/twobrain_rec_server/calendar/adapters.py` with event mapping and safe tenant-policy limitation states.
- [X] T034 Implement the Exchange EWS read-only adapter in `apps/server/src/twobrain_rec_server/calendar/adapters.py` with event mapping and safe enterprise limitation states.
- [X] T035 Implement the Bitrix24 read-only adapter in `apps/server/src/twobrain_rec_server/calendar/adapters.py` with event mapping and safe REST capability states.
- [X] T036 Add the calendar FastAPI router in `apps/server/src/twobrain_rec_server/api/calendar.py` using the existing auth/session patterns from `apps/server/src/twobrain_rec_server/api/ingest.py`.
- [X] T037 Register the calendar router in `apps/server/src/twobrain_rec_server/main.py`.
- [X] T038 Update OpenAPI drift ownership in `apps/server/tests/contract/test_openapi_contract_drift.py` and `specs/012-server-ingest-foundation/contracts/openapi.yaml` so calendar routes are covered.
- [X] T039 Update redaction coverage in `apps/server/src/twobrain_rec_server/observability/redaction.py` for calendar secrets, attendee lists, passcodes, conference URLs, signed URLs, and provider payload fragments.

**Checkpoint**: Calendar foundation compiles, new tests fail for missing behavior before story implementation, and no desktop/provider credentials are stored outside the server.

---

## Phase 3: User Story 1 - Connect Calendar Sources (Priority: P1) MVP

**Goal**: A workspace user can connect read-only calendar sources, select calendars, see capability states, trigger bounded future sync, and disconnect safely.

**Independent Test**: Contract and integration tests prove provider list, connect, list, selected calendars, sync request, safe errors, and disconnect lifecycle without returning raw credentials.

### Tests for User Story 1

- [X] T040 [P] [US1] Add provider preset contract tests in `apps/server/tests/contract/test_calendar_context_contract.py` for `GET /api/v1/calendar/providers`.
- [X] T041 [P] [US1] Add source connect/list/disconnect contract tests in `apps/server/tests/contract/test_calendar_context_contract.py` for `/api/v1/calendar/sources` and `/api/v1/calendar/sources/{source_id}/disconnect`.
- [X] T042 [P] [US1] Add selected-calendar and sync-request integration tests in `apps/server/tests/integration/test_calendar_persistence.py`.
- [X] T043 [P] [US1] Add safe credential failure tests in `apps/server/tests/unit/test_calendar_credentials.py` for invalid app password, OAuth unavailable, tenant denial, provider timeout, and rate limit.

### Implementation for User Story 1

- [X] T044 [US1] Implement provider preset response mapping in `apps/server/src/twobrain_rec_server/calendar/capabilities.py`.
- [X] T045 [US1] Implement source creation, source listing, calendar discovery results, and selected-calendar persistence in `apps/server/src/twobrain_rec_server/calendar/service.py`.
- [X] T046 [US1] Implement credential sealing, credential-state fingerprints, and no-secret response behavior in `apps/server/src/twobrain_rec_server/calendar/credentials.py`.
- [X] T047 [US1] Implement read-only connect/list/get/select/sync/disconnect endpoints in `apps/server/src/twobrain_rec_server/api/calendar.py`.
- [X] T048 [US1] Implement safe provider error mapping in `apps/server/src/twobrain_rec_server/calendar/service.py` and `apps/server/src/twobrain_rec_server/api/problems.py`.
- [X] T049 [US1] Implement disconnect credential purge and unmatched/future cache purge in `apps/server/src/twobrain_rec_server/calendar/lifecycle.py`.
- [X] T050 [US1] Record US1 validation results and limitations in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.

**Checkpoint**: US1 is independently usable for read-only source management and does not expose credential material.

---

## Phase 4: User Story 2 - Ingest Full Event Context Safely (Priority: P1) MVP

**Goal**: Selected calendars sync future events and normalize all available provider information or explicit unavailable states without fabricating data or leaking sensitive content.

**Independent Test**: Synthetic fixtures for each provider prove normalized identity, schedule, content, participants, conference links, recurrence, limitation states, and provider extras boundaries.

### Tests for User Story 2

- [X] T051 [P] [US2] Add Yandex CalDAV fixture cases in `apps/server/tests/fixtures/calendar.py` and assertions in `apps/server/tests/unit/test_calendar_provider_fixtures.py`.
- [X] T052 [P] [US2] Add Mail.ru CalDAV fixture cases in `apps/server/tests/fixtures/calendar.py` and assertions in `apps/server/tests/unit/test_calendar_provider_fixtures.py`.
- [X] T053 [P] [US2] Add Google Calendar event-resource fixture cases in `apps/server/tests/fixtures/calendar.py` and assertions in `apps/server/tests/unit/test_calendar_provider_fixtures.py`.
- [X] T054 [P] [US2] Add Microsoft Graph event fixture cases in `apps/server/tests/fixtures/calendar.py` and assertions in `apps/server/tests/unit/test_calendar_provider_fixtures.py`.
- [X] T055 [P] [US2] Add Exchange EWS fixture cases in `apps/server/tests/fixtures/calendar.py` and assertions in `apps/server/tests/unit/test_calendar_provider_fixtures.py`.
- [X] T056 [P] [US2] Add Bitrix24 REST calendar fixture cases in `apps/server/tests/fixtures/calendar.py` and assertions in `apps/server/tests/unit/test_calendar_provider_fixtures.py`.
- [X] T057 [P] [US2] Add custom CalDAV fixture cases for VK WorkSpace, Mailion/MyOffice, R7-Office, CommuniGate Pro, RuPost, and Nextcloud/SOGo-like CalDAV in `apps/server/tests/fixtures/calendar.py` and assertions in `apps/server/tests/unit/test_calendar_provider_fixtures.py`.
- [X] T058 [P] [US2] Add recurrence, all-day, floating-time, missing-DTEND, duplicate-UID, cancelled-instance, and moved-instance tests in `apps/server/tests/unit/test_calendar_normalization.py`.
- [X] T059 [P] [US2] Add sensitive description, passcode, attachment-metadata, multiple-link, and stale-link tests in `apps/server/tests/unit/test_calendar_conference_links.py`.
- [X] T060 [P] [US2] Add provider-extras bounding and raw-payload rejection tests in `apps/server/tests/contract/test_calendar_no_secret_content_egress.py`.

### Implementation for User Story 2

- [X] T061 [US2] Implement iCalendar field extraction and limitation-state mapping in `apps/server/src/twobrain_rec_server/calendar/normalize.py`.
- [X] T062 [US2] Implement Google Calendar event-resource normalization in `apps/server/src/twobrain_rec_server/calendar/adapters.py`.
- [X] T063 [US2] Implement Microsoft Graph event-resource normalization in `apps/server/src/twobrain_rec_server/calendar/adapters.py`.
- [X] T064 [US2] Implement Exchange EWS event normalization in `apps/server/src/twobrain_rec_server/calendar/adapters.py`.
- [X] T065 [US2] Implement Bitrix24 event normalization in `apps/server/src/twobrain_rec_server/calendar/adapters.py`.
- [X] T066 [US2] Implement custom CalDAV provider-label mapping for VK WorkSpace, Mailion/MyOffice, R7-Office, CommuniGate Pro, RuPost, and Nextcloud/SOGo-like CalDAV in `apps/server/src/twobrain_rec_server/calendar/adapters.py`.
- [X] T067 [US2] Implement conference-link candidate extraction with redacted diagnostic output in `apps/server/src/twobrain_rec_server/calendar/conference_links.py`.
- [X] T068 [US2] Implement event snapshot, participant, conference-link, version, deletion, and sync-token upserts in `apps/server/src/twobrain_rec_server/calendar/sync.py`.
- [X] T069 [US2] Implement upcoming event query response shaping in `apps/server/src/twobrain_rec_server/calendar/service.py`.
- [X] T070 [US2] Implement `GET /api/v1/calendar/events/upcoming` in `apps/server/src/twobrain_rec_server/api/calendar.py`.
- [X] T071 [US2] Record US2 fixture coverage, provider limitations, and no-private-content evidence in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.

**Checkpoint**: US2 can ingest and expose safe upcoming context from synthetic fixtures for all required provider families.

---

## Phase 5: User Story 3 - Match Recordings To Calendar Events (Priority: P1) MVP

**Goal**: At recording time, the system can link a new recording to the current or explicitly selected future event, use the calendar title when safe, and never retrospectively match old recordings.

**Independent Test**: Tests prove current-event selection, ambiguity fallback, manual selection, no-context fallback, user-title priority, and no past-recording matching.

### Tests for User Story 3

- [X] T072 [P] [US3] Add recording-time context selection tests in `apps/server/tests/unit/test_calendar_recording_context.py`.
- [X] T073 [P] [US3] Add meeting calendar-context endpoint contract tests in `apps/server/tests/contract/test_calendar_context_contract.py` for `PUT /api/v1/meetings/{meeting_id}/calendar-context` and `DELETE /api/v1/meetings/{meeting_id}/calendar-context`.
- [X] T074 [P] [US3] Add no-retrospective-matching tests in `apps/server/tests/integration/test_calendar_persistence.py`.
- [X] T075 [P] [US3] Add desktop upload client context-link tests in `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`.

### Implementation for User Story 3

- [X] T076 [US3] Implement current-event, selected-event, ambiguous, and no-context scoring in `apps/server/src/twobrain_rec_server/calendar/service.py`.
- [X] T077 [US3] Implement `RecordingCalendarContextLink` creation, update, and removal in `apps/server/src/twobrain_rec_server/calendar/service.py`.
- [X] T078 [US3] Implement meeting calendar-context endpoints in `apps/server/src/twobrain_rec_server/api/calendar.py`.
- [X] T079 [US3] Preserve user-provided meeting title priority and safe calendar-title fallback in `apps/server/src/twobrain_rec_server/ingest/meetings.py`.
- [X] T080 [US3] Add calendar title-source fields to meeting API responses in `apps/server/src/twobrain_rec_server/api/schemas.py` and `apps/server/src/twobrain_rec_server/api/ingest.py`.
- [X] T081 [US3] Add optional calendar context link request support to `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift` without storing provider credentials on desktop.
- [X] T082 [US3] Record US3 validation results and no-retrospective-matching evidence in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.

**Checkpoint**: US3 links recordings only forward/current at recording time and keeps manual recording/title behavior intact.

---

## Phase 6: User Story 4 - Build Calendar Participant Roster (Priority: P1) MVP

**Goal**: Calendar organizer, attendees, resources, rooms, groups, and response states become meeting roster context without granting access, sending messages, or renaming speakers.

**Independent Test**: Tests prove roster classification, attendee caps, hidden attendee behavior, duplicate handling, and separation from transcript speakers and access recipients.

### Tests for User Story 4

- [X] T083 [P] [US4] Add participant normalization tests in `apps/server/tests/unit/test_calendar_participants.py` for organizer, required, optional, declined, hidden, no-email, resource, room, group, internal, external, and duplicate participants.
- [X] T084 [P] [US4] Add roster API contract tests in `apps/server/tests/contract/test_calendar_context_contract.py` requiring participant counts and safe roster states without attendee dumps.
- [X] T085 [P] [US4] Add cabinet read-model tests in `apps/server/tests/unit/test_cabinet_view_models.py` proving calendar roster fields do not rename transcript speakers or grant meeting access.

### Implementation for User Story 4

- [X] T086 [US4] Implement participant normalization and candidate classification in `apps/server/src/twobrain_rec_server/calendar/normalize.py`.
- [X] T087 [US4] Implement participant persistence and deduplication in `apps/server/src/twobrain_rec_server/calendar/sync.py`.
- [X] T088 [US4] Add safe roster response fields to `apps/server/src/twobrain_rec_server/api/schemas.py`.
- [X] T089 [US4] Expose roster context for authorized meeting review through `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/queries.py`.
- [X] T090 [US4] Ensure roster context does not change access decisions in `apps/server/src/twobrain_rec_server/cabinet/access.py`.
- [X] T091 [US4] Record US4 roster/access/speaker-boundary evidence in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.

**Checkpoint**: US4 provides useful meeting roster context while keeping access, recipient, and speaker identity boundaries intact.

---

## Phase 7: User Story 5 - Keep Calendar Privacy, Retention, And Deletion Truth (Priority: P1) MVP

**Goal**: Calendar content is access-controlled, redacted in diagnostics, retained/deleted honestly, and disconnected sources purge credentials plus unmatched/future cache.

**Independent Test**: Tests prove authorized/denied access, disconnect behavior, meeting deletion behavior, redacted logs/evidence, and non-blocking upload/review when calendar providers fail.

### Tests for User Story 5

- [X] T092 [P] [US5] Add disconnect lifecycle tests in `apps/server/tests/integration/test_calendar_disconnect_lifecycle.py`.
- [X] T093 [P] [US5] Add calendar deletion lifecycle tests in `apps/server/tests/integration/test_calendar_deletion_lifecycle.py`.
- [X] T094 [P] [US5] Add calendar access-control tests in `apps/server/tests/integration/test_calendar_access_policy.py`.
- [X] T095 [P] [US5] Add provider downtime and stale-sync non-blocking tests in `apps/server/tests/integration/test_calendar_provider_failures.py`.
- [X] T096 [P] [US5] Add calendar redaction unit tests in `apps/server/tests/unit/test_redaction.py`.

### Implementation for User Story 5

- [X] T097 [US5] Implement disconnect lifecycle accounting in `apps/server/src/twobrain_rec_server/calendar/lifecycle.py`.
- [X] T098 [US5] Integrate calendar context deletion with existing meeting deletion behavior in `apps/server/src/twobrain_rec_server/calendar/lifecycle.py` and `apps/server/src/twobrain_rec_server/ingest/lifecycle.py`.
- [X] T099 [US5] Implement calendar access decisions for upcoming events, matched meeting context, and roster context in `apps/server/src/twobrain_rec_server/calendar/service.py`.
- [X] T100 [US5] Implement stale-sync, rate-limit, provider-timeout, and provider-unavailable safe states in `apps/server/src/twobrain_rec_server/calendar/sync.py`.
- [X] T101 [US5] Ensure calendar failures never block upload, processing, playback, or review paths in `apps/server/src/twobrain_rec_server/api/ingest.py`, `apps/server/src/twobrain_rec_server/api/processing.py`, and `apps/server/src/twobrain_rec_server/api/cabinet.py`.
- [X] T102 [US5] Record US5 privacy, disconnect, deletion, and provider-failure evidence in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.

**Checkpoint**: P1 MVP calendar layer is privacy-safe, deletion-aware, and non-blocking for the recording product.

---

## Phase 8: User Story 6 - Provide Upcoming Meeting Context Without Starting Capture (Priority: P1)

**Goal**: The macOS app can show a join/open prompt one minute before a meeting and a record prompt at meeting start, while never starting recording automatically in 060.

**Independent Test**: Desktop tests prove prompt timing, safe copy, accessibility labels, open-meeting action, record action, overlap fallback, and visible Stop behavior.

### Tests for User Story 6

- [X] T103 [P] [US6] Add desktop prompt model tests in `apps/macos/Shared/Tests/DesktopCalendarReminderTests.swift`.
- [X] T104 [P] [US6] Add capture-control prompt UI tests in `apps/macos/Shared/Tests/CaptureControlTests.swift`.
- [X] T105 [P] [US6] Add accessibility regression tests in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`.
- [X] T106 [P] [US6] Add desktop calendar API client tests in `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`.

### Implementation for User Story 6

- [X] T107 [US6] Implement `GET /api/v1/desktop/calendar/upcoming` response shaping in `apps/server/src/twobrain_rec_server/api/calendar.py`.
- [X] T108 [US6] Add desktop calendar prompt models to `apps/macos/Shared/Sources/Models/CalendarContextModels.swift`.
- [X] T109 [US6] Add desktop calendar client methods to `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`.
- [X] T110 [US6] Implement in-app prompt timing and state evaluation in `apps/macos/RecApp/Sources/Calendar/DesktopCalendarReminderService.swift`.
- [X] T111 [US6] Implement join/open and record prompt actions in `apps/macos/RecApp/Sources/Calendar/DesktopCalendarPromptActions.swift`.
- [X] T112 [US6] Add safe prompt UI to `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`.
- [X] T113 [US6] Wire in-app calendar reminder polling into `apps/macos/RecApp/App/TwoBrainRecApp.swift` without starting recording automatically.
- [X] T114 [US6] Add Russian user-facing prompt copy and accessibility labels in `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`.
- [X] T115 [US6] Record US6 prompt timing, no-auto-record, accessibility, localization, and brand-distance evidence in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.

**Checkpoint**: Desktop can help the user join and start recording, but recording still requires an explicit action in 060.

---

## Phase 9: User Story 7 - Prepare Future Recipient Candidates Without Sending (Priority: P2)

**Goal**: Calendar attendees can be classified as future recipient candidates, but no messages, shares, report delivery, or access grants are created in 060.

**Independent Test**: Tests prove candidate classification and no-egress/no-share behavior for all attendee types.

### Tests for User Story 7

- [X] T116 [P] [US7] Add recipient-candidate classification tests in `apps/server/tests/unit/test_calendar_recipient_candidates.py`.
- [X] T117 [P] [US7] Add no-send/no-share/no-access-grant tests in `apps/server/tests/contract/test_calendar_no_secret_content_egress.py`.
- [X] T118 [P] [US7] Add meeting share boundary regression tests in `apps/server/tests/integration/test_meeting_share_links.py`.

### Implementation for User Story 7

- [X] T119 [US7] Implement future-recipient candidate classes in `apps/server/src/twobrain_rec_server/calendar/normalize.py`.
- [X] T120 [US7] Expose candidate counts and safe states in `apps/server/src/twobrain_rec_server/api/schemas.py` without exposing raw attendee dumps.
- [X] T121 [US7] Ensure no calendar attendee creates share grants in `apps/server/src/twobrain_rec_server/cabinet/access.py` or `apps/server/src/twobrain_rec_server/db/models/meeting_access.py`.
- [X] T122 [US7] Record US7 no-send/no-share/no-access-grant evidence in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.

**Checkpoint**: Recipient candidates are ready for a later policy-gated delivery layer, but 060 sends nothing.

---

## Phase 10: Polish And Cross-Cutting Validation

**Purpose**: Complete documentation, evidence, changelog, and the full validation lane.

- [X] T123 [P] Update `docs/current-product-status.md` with the calendar context layer status, supported provider families, limits, and out-of-scope auto-record/send behavior.
- [X] T124 [P] Update `CHANGELOG.md` with feature 060 behavior, privacy impact, validation evidence summary, compatibility impact, and known limitations.
- [X] T125 [P] Update `specs/060-calendar-context-ingestion/quickstart.md` if implementation commands or exact test names changed.
- [X] T126 [P] Update `specs/060-calendar-context-ingestion/provider-deep-dive.md` with any provider capability corrections found during implementation.
- [X] T127 Run `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_calendar_credentials.py tests/unit/test_calendar_normalization.py tests/unit/test_calendar_conference_links.py tests/unit/test_calendar_provider_fixtures.py tests/unit/test_calendar_recording_context.py tests/unit/test_calendar_participants.py tests/unit/test_cabinet_view_models.py tests/unit/test_redaction.py tests/unit/test_calendar_recipient_candidates.py` and record results in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.
- [X] T128 Run `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_calendar_context_contract.py tests/contract/test_calendar_no_secret_content_egress.py tests/contract/test_calendar_rls_contract.py tests/contract/test_openapi_contract_drift.py` and record results in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.
- [X] T129 Run `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_calendar_persistence.py tests/integration/test_calendar_disconnect_lifecycle.py tests/integration/test_calendar_deletion_lifecycle.py tests/integration/test_calendar_access_policy.py tests/integration/test_calendar_provider_failures.py tests/integration/test_meeting_share_links.py tests/integration/test_persistent_ingest_storage.py` and record results in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.
- [X] T130 Run `swift test --package-path apps/macos --disable-swift-testing --filter DesktopCalendarReminder` and record results in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.
- [X] T131 Run `swift test --package-path apps/macos --disable-swift-testing --filter 'CaptureControl|AppControlAccessibility|DesktopUploadClient'` and record results in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.
- [X] T132 Run the forbidden-content scan from `specs/060-calendar-context-ingestion/quickstart.md` and record the sanitized result in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.
- [X] T133 Run `infra/scripts/ci-local.sh` and record final local CI evidence in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.
- [X] T134 Run a Ponytail complexity review for the feature diff and record accepted simplifications or intentional `ponytail:` notes in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.
- [X] T135 Re-run `specs/060-calendar-context-ingestion/checklists/calendar-integration.md` against the final implementation and mark each item complete or document a blocker in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.
- [ ] T136 Verify `tasks.md` completion, GitHub issue closure evidence, and final PR/release notes in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.

---

## Dependencies And Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1. Blocks all user stories.
- **US1 Connect Sources**: Depends on Phase 2.
- **US2 Ingest Event Context**: Depends on Phase 2 and benefits from US1 source state.
- **US3 Recording Context Link**: Depends on Phase 2 and needs US2 event snapshots for full validation.
- **US4 Participant Roster**: Depends on Phase 2 and US2 participant normalization.
- **US5 Privacy/Lifecycle**: Depends on Phase 2 and should run alongside US1-US4 before MVP closeout.
- **US6 Desktop Prompts**: Depends on US2 upcoming context and US3 context-link contract.
- **US7 Recipient Candidates**: Depends on US4 participant classification.
- **Phase 10 Polish**: Depends on all target user stories for the selected implementation slice.

### MVP Boundary

- MVP for feature 060 is Phase 1 through Phase 8: US1, US2, US3, US4, US5, and US6.
- P2 addition is Phase 9: future recipient candidates.
- Auto-record, auto-join, messaging, calendar mutation, share grants, and retrospective matching stay out of scope.

### Parallel Opportunities

- T003-T005 can run in parallel after T001.
- T007-T014 can run in parallel before foundational implementation.
- T015-T039 touch separate model, migration, API, calendar package, adapter, RLS, and redaction files and can be split across backend developers after test skeletons exist.
- T040-T043, T051-T060, T072-T075, T083-T085, T092-T096, T103-T106, and T116-T118 are test tasks that can run in parallel by story.
- Provider adapter tasks T061-T066 can run in parallel after shared normalization contracts are stable.
- Documentation tasks T123-T126 can run in parallel after the implemented behavior is known.

### Test-First Rule

- Write each story's test tasks first and verify they fail for the missing behavior before implementing that story.
- Mark a task `[X]` only after the relevant tests or evidence in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md` prove it.
- Do not close a GitHub issue unless the matching task is `[X]`, evidence is recorded, and the issue receives a clear Russian closure comment.

### Provider Evidence Rule

- Use synthetic fixtures by default. Do not commit real calendar payloads, private meeting titles, attendee dumps, provider credentials, screenshots with private content, transcript text, signed URLs, or raw provider responses.
- Live provider checks, if later approved, must record only metadata-safe evidence in `specs/060-calendar-context-ingestion/validation/implementation-evidence.md`.
