# Tasks: Calendar Settings UI

**Input**: Design documents from `specs/063-calendar-settings-ui/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `ux-research.md`, `data-model.md`, `design-handoff.md`, `measurement.md`, `contracts/`, `quickstart.md`
**Tests**: Included because Feature 063 is a high-risk product/UX/privacy slice and the plan requires focused validation.
**Risk / Validation Lane**: High-risk product area: privacy-sensitive calendar settings, provider credentials boundary, recording-adjacent prompts, embedded macOS UX, localization, accessibility, and degraded states.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other `[P]` tasks in the same phase because it touches different files or only adds independent tests.
- **[Story]**: User story label from `spec.md`.
- Every task includes an exact file path.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare safe fixtures and confirm the existing 060 calendar/cabinet surfaces that 063 reuses.

- [X] T001 [P] Create safe calendar settings fixture builders with synthetic providers, sources, calendars, sync states, overlap events, and private/free-busy events in `apps/server/tests/fixtures/calendar_settings.py`
- [X] T002 [P] Create macOS calendar settings fixture helpers for embedded route, active recording, and prompt overlap tests in `apps/macos/Shared/Tests/CalendarSettingsFixtures.swift`
- [X] T003 Review feature 060 calendar API and service behavior that 063 reuses in `apps/server/src/twobrain_rec_server/api/calendar.py` and `apps/server/src/twobrain_rec_server/calendar/service.py`
- [X] T004 Review existing cabinet primitives, layout tokens, and page rendering conventions before adding settings UI in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/primitives.html` and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared contracts, read models, persistence, and rendering hooks that all user stories depend on.

**CRITICAL**: No user story implementation should start until this phase is complete.

### Tests for Foundational Behavior

- [X] T005 [P] Add contract tests for empty selected calendar lists, supported provider labels, safe account/calendar/event label redaction, and forbidden secret/private fields in `apps/server/tests/contract/test_calendar_settings_contract.py`
- [X] T006 [P] Add unit tests for calendar settings source states, stale threshold, event-category defaults, duplicate grouping, and overlap grouping in `apps/server/tests/unit/test_calendar_settings_view_models.py`
- [X] T007 [P] Add integration tests for calendar settings preference defaults and migration coverage in `apps/server/tests/integration/test_calendar_settings_flow.py`

### Implementation for Foundational Behavior

- [X] T008 Allow `SelectCalendarsRequest.selected_provider_calendar_ids` to be empty while preserving forbidden extra fields in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T009 Add calendar settings read-model dataclasses and shared safe-label/redaction helpers for provider presets, source summaries, selectable calendars, preferences, preview items, safe errors, metadata-only event fields, duplicate groups, and overlap groups in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T010 Add `CalendarSettingsPreference` persistence for prompt and event-category settings in `apps/server/src/twobrain_rec_server/db/models/calendar.py`
- [X] T011 Add Alembic migration for calendar settings preferences with safe defaults in `apps/server/src/twobrain_rec_server/db/migrations/versions/0014_calendar_settings_preferences.py`
- [X] T012 Add calendar settings preference load/save helpers that use existing tenant scope and do not touch provider credentials in `apps/server/src/twobrain_rec_server/calendar/service.py`
- [X] T013 Add calendar settings query helpers that assemble provider presets, sources, calendars, preferences, sync state, and preview inputs from existing 060 tables in `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [X] T014 Add calendar settings rendering entrypoints and fragment helper names in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T015 Add base calendar settings CSS classes for source cards, provider rows, calendar rows, safe banners, preview rows, conflict blocks, and responsive stacking in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`

**Checkpoint**: Foundation ready. Calendar settings data can be represented safely, empty calendar selection is valid, and each user story can attach UI/routes/tests to the shared model.

---

## Phase 3: User Story 1 - Find Calendar Settings (Priority: P1) MVP

**Goal**: User reaches `Настройки -> Интеграции -> Календари` in web cabinet and embedded macOS cabinet, and sees an actionable settings screen.

**Independent Test**: Starting from the cabinet, open Calendar settings in web and embedded macOS surfaces; verify active navigation, Russian labels, location cue, no placeholder, and native recording controls preserved.

### Tests for User Story 1

- [X] T016 [P] [US1] Add cabinet route contract tests for `/settings/integrations/calendar` and `/desktop/settings/integrations/calendar` in `apps/server/tests/contract/test_calendar_settings_contract.py`
- [X] T017 [P] [US1] Add navigation model tests for enabled `Настройки`, `Интеграции`, and `Календари` states in `apps/server/tests/unit/test_cabinet_navigation_model.py`
- [X] T018 [P] [US1] Add macOS route policy tests that allow `/desktop/settings/integrations/calendar` without opening an external browser in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`

### Implementation for User Story 1

- [X] T019 [US1] Enable settings calendar navigation items and active state mapping in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T020 [US1] Implement web and embedded calendar settings routes in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T021 [US1] Render the Calendar settings page shell with breadcrumb, title, subtitle, and actionable empty state in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/calendar_settings.html`
- [X] T022 [US1] Render the Calendar settings fragment for HTMX refreshes and embedded cabinet reuse in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`
- [X] T023 [US1] Allow the embedded macOS route kind and same-origin decision for calendar settings in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`
- [X] T024 [US1] Route the macOS sidebar Settings item to the embedded calendar settings destination while preserving meeting workspace fallback in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`

**Checkpoint**: US1 works independently: the settings screen is reachable and not a placeholder.

---

## Phase 4: User Story 2 - Understand The Calendar Data Boundary (Priority: P1)

**Goal**: User understands read-only access, server-owned credentials, no auto-record, no calendar mutation, no summary sending, and no attendee access grants.

**Independent Test**: Before connection, inspect the settings screen and verify the safe Russian copy teaches the boundary without exposing secrets or private event content.

### Tests for User Story 2

- [X] T025 [P] [US2] Add unit tests for read-only boundary copy, no-auto-record copy, attendee non-recipient copy, and server-owned credential copy in `apps/server/tests/unit/test_calendar_settings_view_models.py`
- [X] T026 [P] [US2] Add no-secret/no-private-content rendering tests for the boundary and provider return states in `apps/server/tests/contract/test_calendar_settings_contract.py`

### Implementation for User Story 2

- [X] T027 [US2] Add reusable safe Russian boundary copy and forbidden-action labels to the calendar settings read model in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T028 [US2] Render the read-only boundary block at the top of Calendar settings in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`
- [X] T029 [US2] Add provider-return and policy-limited boundary messages to calendar settings rendering in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T030 [US2] Ensure embedded unavailable/auth copy says desktop stores no provider credentials and manual recording remains available in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetState.swift`

**Checkpoint**: US2 works independently: a privacy-conscious user can explain what 2brain Rec reads and what it will not do.

---

## Phase 5: User Story 3 - Connect A Calendar Source (Priority: P1)

**Goal**: User sees all supported providers and starts the correct connection method with safe progress, success, cancel, denied, failed, and admin-limited states.

**Independent Test**: From Calendar settings, choose each supported provider family with safe fixtures and verify method category, read-only explanation, progress, success, no-readable-calendars, and safe failure states.

### Tests for User Story 3

- [X] T031 [P] [US3] Add provider list contract tests for all required provider labels and method categories in `apps/server/tests/contract/test_calendar_settings_contract.py`
- [X] T032 [P] [US3] Add integration tests for connect success, cancelled, denied, failed, admin-required, and no-readable-calendars states in `apps/server/tests/integration/test_calendar_settings_flow.py`

### Implementation for User Story 3

- [X] T033 [US3] Map existing provider presets into required Russian labels, method categories, support state, and limitation copy in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T034 [US3] Add provider list and provider action rendering to the Calendar settings fragment in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`
- [X] T035 [US3] Add connection start and provider-result route handling for app-password, manual-url, and provider-limited methods in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T036 [US3] Render app-password and manual CalDAV forms with labels, inline errors, no credential echo, and read-only explanation in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`
- [X] T037 [US3] Map connection ProblemDetail categories into safe Russian user messages without raw provider payloads in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T038 [US3] Emit metadata-only calendar connect audit events for start/result categories using existing audit helpers in `apps/server/src/twobrain_rec_server/calendar/audit.py`

**Checkpoint**: US3 works independently: provider connection can be started and safely resolved without selecting calendars yet.

---

## Phase 6: User Story 4 - Choose Calendars Inside A Source (Priority: P1)

**Goal**: User chooses exactly which calendars inside each connected source are used for future meeting context and prompts.

**Independent Test**: Connect a source with multiple calendars, verify zero calendars selected by default, select/deselect calendars, save empty selection, and confirm upcoming/prompts use only selected calendars.

### Tests for User Story 4

- [X] T039 [P] [US4] Add contract tests for zero selected calendars after connect and saving an empty selected list in `apps/server/tests/contract/test_calendar_settings_contract.py`
- [X] T040 [P] [US4] Add unit tests for selectable calendar labels, duplicate display names, shared/delegated/private/unavailable states, selected counts, duplicate events, and partial overlap conflict windows in `apps/server/tests/unit/test_calendar_settings_view_models.py`
- [X] T041 [P] [US4] Add integration tests for select, deselect all, save empty selection, and no retrospective matching in `apps/server/tests/integration/test_calendar_settings_flow.py`

### Implementation for User Story 4

- [X] T042 [US4] Ensure `connect_source` never auto-selects calendars after successful connection in `apps/server/src/twobrain_rec_server/calendar/service.py`
- [X] T043 [US4] Ensure `replace_selected_calendars` supports an empty selection and updates selected count without disconnecting the source in `apps/server/src/twobrain_rec_server/calendar/service.py`
- [X] T044 [US4] Add calendar selection form handling and save/cancel feedback to calendar settings routes in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T045 [US4] Render per-source calendar selection rows, selected count, zero-selection warning, and safe visibility states in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`
- [X] T046 [US4] Add duplicate-event and overlap-conflict grouping helpers for selected upcoming events in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T047 [US4] Render overlap conflict choices and "continue without calendar context" state for ambiguous current intervals in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`

**Checkpoint**: US4 works independently: connected sources stay connected while calendar participation is explicitly chosen.

---

## Phase 7: User Story 5 - Control Which Event Types Appear (Priority: P1)

**Goal**: User controls event categories for upcoming meetings and prompts: events without participants, events without link/location, all-day events, and private/free-busy prompt candidates.

**Independent Test**: Toggle event-category preferences and verify preview/prompt eligibility changes while manual recording remains available.

### Tests for User Story 5

- [X] T048 [P] [US5] Add unit tests for default event-category preferences and eligibility filtering in `apps/server/tests/unit/test_calendar_settings_view_models.py`
- [X] T049 [P] [US5] Add integration tests for saving event-category preferences and preserving manual recording availability copy in `apps/server/tests/integration/test_calendar_settings_flow.py`

### Implementation for User Story 5

- [X] T050 [US5] Implement event-category preference defaults and safe eligibility rules in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T051 [US5] Add event-category preference save handling to calendar settings routes in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T052 [US5] Render event-category controls with Russian labels, helper text, and policy-constrained states in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`
- [X] T053 [US5] Persist event-category preference changes through the calendar settings preference helpers in `apps/server/src/twobrain_rec_server/calendar/service.py`
- [X] T054 [US5] Ensure private/free-busy opted-in preview state still redacts title, attendees, links, agenda, passcodes, and attachments in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`

**Checkpoint**: US5 works independently: event category choices change eligibility without blocking manual recording.

---

## Phase 8: User Story 6 - Understand Sync Health And Recover Safely (Priority: P1)

**Goal**: User sees current, stale, broken, needs-action, disabled, syncing, and disconnected sync states with last successful sync and recovery actions.

**Independent Test**: Simulate every sync state and verify clear Russian copy, no raw provider payloads, last successful sync, and correct manual sync/reconnect behavior.

### Tests for User Story 6

- [X] T055 [P] [US6] Add unit tests for sync health state mapping, 24-hour stale threshold, latest-failed stale state, and safe error copy in `apps/server/tests/unit/test_calendar_settings_view_models.py`
- [X] T056 [P] [US6] Add integration tests for manual sync accepted within 2 seconds, already-running, stale, failed, needs-action, disabled, and disconnected states in `apps/server/tests/integration/test_calendar_settings_flow.py`

### Implementation for User Story 6

- [X] T057 [US6] Implement sync health summary and safe recovery-action mapping in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T058 [US6] Add manual sync form handling that reports accepted, already-running, failed, and reconnect-required states without waiting for provider sync completion in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T059 [US6] Render sync health on source cards, sync details, stale warnings, and manual sync controls in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`
- [X] T060 [US6] Ensure `request_source_sync` returns or preserves a safe already-running state without duplicate sync work in `apps/server/src/twobrain_rec_server/calendar/service.py`
- [X] T061 [US6] Add safe sync status labels and stale/failed CSS states in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T062 [US6] Emit metadata-only manual sync request/result audit events using existing audit helpers in `apps/server/src/twobrain_rec_server/calendar/audit.py`

**Checkpoint**: US6 works independently: stale and failed sync are understandable and recoverable without logs.

---

## Phase 9: User Story 7 - Control Calendar-Driven Prompts (Priority: P1)

**Goal**: User controls one-minute join/open prompts, at-start record prompts, and local upcoming display without enabling real auto-record.

**Independent Test**: Toggle prompt settings and verify prompts stop/start as configured, manual recording remains available, active recording stays visible, overlap prompts require explicit choice, and auto-record remains disabled/out of scope.

### Tests for User Story 7

- [X] T063 [P] [US7] Add server unit tests for prompt preference defaults, disabled/future auto-record copy, policy-constrained prompt controls, and overlap prompt state in `apps/server/tests/unit/test_calendar_settings_view_models.py`
- [X] T064 [P] [US7] Add macOS reminder tests for overlap event choice, no active-context auto-switch, and no auto-record setting effect in `apps/macos/Shared/Tests/DesktopCalendarReminderTests.swift`
- [X] T065 [P] [US7] Add macOS shell invariant tests proving active recording strip and one-action Stop remain reachable while settings is open in `apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift`

### Implementation for User Story 7

- [X] T066 [US7] Implement prompt preference read/write mapping and disabled auto-record state in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T067 [US7] Add prompt preference save handling to calendar settings routes in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T068 [US7] Render one-minute join prompt, at-start record prompt, local upcoming display, safe title display, and disabled auto-record option in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`
- [X] T069 [US7] Update desktop prompt models to carry explicit overlap-choice and continue-without-context state without auto-record fields in `apps/macos/Shared/Sources/Models/CalendarContextModels.swift`
- [X] T070 [US7] Update desktop prompt service to require explicit event choice on overlap and never switch active recording context automatically in `apps/macos/RecApp/Sources/Calendar/DesktopCalendarReminderService.swift`
- [X] T071 [US7] Update desktop prompt actions to keep primary action manual and visible for record prompts in `apps/macos/RecApp/Sources/Calendar/DesktopCalendarPromptActions.swift`

**Checkpoint**: US7 works independently: calendar prompts are configurable and never become hidden or automatic recording.

---

## Phase 10: User Story 8 - Preview Upcoming Calendar Behavior Safely (Priority: P2)

**Goal**: User sees a safe preview of what selected calendars and settings will do before a real meeting starts.

**Independent Test**: With synthetic upcoming events, verify preview reflects selected calendars, event-category preferences, private/free-busy policy, stale confidence, duplicates, overlaps, and provider limitations.

### Tests for User Story 8

- [X] T072 [P] [US8] Add unit tests for preview item redaction, empty reasons, provider limitation copy, stale confidence, duplicate grouping, and overlap grouping in `apps/server/tests/unit/test_calendar_settings_view_models.py`
- [X] T073 [P] [US8] Add integration tests for preview with selected calendars, no selected calendars, no matching events, stale source, and private/free-busy events in `apps/server/tests/integration/test_calendar_settings_flow.py`

### Implementation for User Story 8

- [X] T074 [US8] Build safe upcoming preview read models from selected calendars, preferences, sync confidence, and event safety fields in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T075 [US8] Query bounded upcoming preview data without provider network calls during settings render in `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [X] T076 [US8] Render preview rows, empty reasons, stale confidence, duplicate source labels, overlap conflict groups, and provider limitation copy in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`
- [X] T077 [US8] Add preview styling for compact rows, safe title states, stale warning, and conflict grouping in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`

**Checkpoint**: US8 works independently: preview explains what will happen without leaking private calendar content.

---

## Phase 11: User Story 9 - Disconnect A Calendar Source (Priority: P2)

**Goal**: User disconnects a source intentionally and understands future sync, credential removal/revocation, and retention boundary.

**Independent Test**: Disconnect a connected source, confirm the Russian dialog, verify future events stop contributing, and ensure copy does not promise deletion outside 2brain Rec control.

### Tests for User Story 9

- [X] T078 [P] [US9] Add contract tests for disconnect confirmation copy, no universal deletion promise, and credentials removed/revoked wording in `apps/server/tests/contract/test_calendar_settings_contract.py`
- [X] T079 [P] [US9] Add integration tests for disconnect success, partial failure, sync-running priority, and source no longer contributing future events in `apps/server/tests/integration/test_calendar_settings_flow.py`

### Implementation for User Story 9

- [X] T080 [US9] Add disconnect confirmation view model with future-sync, credential-removal, and retention-boundary copy in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T081 [US9] Add disconnect confirmation and submit handling to calendar settings routes in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T082 [US9] Render destructive disconnect confirmation, cancel action, success feedback, and partial-failure feedback in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`
- [X] T083 [US9] Ensure disconnect service output stops future contribution and keeps matched-context retention truth in `apps/server/src/twobrain_rec_server/calendar/service.py`
- [X] T084 [US9] Emit metadata-only disconnect confirmed/result audit events using existing audit helpers in `apps/server/src/twobrain_rec_server/calendar/audit.py`

**Checkpoint**: US9 works independently: source removal is explicit, safe, and truthful.

---

## Phase 12: User Story 10 - Safe Empty, Loading, Error, And Accessibility States (Priority: P2)

**Goal**: Calendar settings are readable and operable with keyboard and screen reader across empty, loading, connected, needs-action, stale, error, disconnected, and policy-constrained states.

**Independent Test**: Navigate provider selection, calendar selection, manual sync, prompt settings, preview, and disconnect with keyboard/screen reader semantics; verify useful Russian states and visible focus.

### Tests for User Story 10

- [X] T085 [P] [US10] Add cabinet accessibility contract tests for labels, roles, live regions, focusable controls, and no mouse-only controls in `apps/server/tests/contract/test_calendar_settings_contract.py`
- [X] T086 [P] [US10] Add unit tests for empty/loading/error/policy state copy and private/free-busy limitation copy in `apps/server/tests/unit/test_calendar_settings_view_models.py`
- [X] T087 [P] [US10] Add macOS unavailable/auth state and provider credential-boundary tests proving embedded failures do not hide native recording controls and desktop code does not store or render provider credentials in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`

### Implementation for User Story 10

- [X] T088 [US10] Add safe empty, loading, unavailable, policy-constrained, no-readable-calendars, no-selected-calendars, and no-matching-events read models in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T089 [US10] Render semantic headings, labels, `role=status`, selected-count announcements, and disabled/policy explanations in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`
- [X] T090 [US10] Add keyboard/focus-safe behavior only where existing server-rendered controls need small interaction support in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T091 [US10] Add focus, long-text, mobile stacking, reduced-motion, and dialog overflow styling in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T092 [US10] Update embedded unavailable-state copy and recovery target behavior for calendar settings routes in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetState.swift`

**Checkpoint**: US10 works independently: all required states are operable and understandable without leaking private data.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Validate the full feature, update release docs/evidence, and keep the next Spec Kit gates ready.

- [X] T093 [P] Add metadata-only measurement event assertions for the events listed in `specs/063-calendar-settings-ui/measurement.md`, including no unsafe source/calendar/event labels in analytics, audit, diagnostic, or log-style fields, using `apps/server/tests/contract/test_calendar_settings_contract.py`
- [X] T094 [P] Update `CHANGELOG.md` with the Calendar settings UI behavior, validation scope, and explicit out-of-scope boundaries
- [X] T095 [P] Update `docs/current-product-status.md` to reflect Calendar settings route, read-only connection UI, selection behavior, sync health, prompt settings, and known limitations
- [X] T096 Run focused server tests from quickstart and record results in `specs/063-calendar-settings-ui/quickstart.md`
- [X] T097 Run focused macOS tests from quickstart and record results in `specs/063-calendar-settings-ui/quickstart.md`
- [X] T098 Run forbidden-content scans for tokens, app passwords, private event text, attendee emails, signed links, passcodes, raw provider payloads, full emails in labels, raw account IDs, raw calendar URLs, token-looking strings, private customer/project names, diagnostic output, test logs, screenshots, and committed evidence in `specs/063-calendar-settings-ui/quickstart.md`
- [X] T099 Run `infra/scripts/ci-local.sh` and record the high-risk validation lane result in `specs/063-calendar-settings-ui/quickstart.md`
- [X] T100 Update `specs/063-calendar-settings-ui/design-qa.md` with real source visual target and rendered screenshots if a visual target exists; otherwise keep `final result: blocked` and name the blocker
- [X] T101 Run guided usability/comprehension checks for SC-002, SC-003, and SC-014, then record setup time, boundary understanding, prompt/manual-recording understanding, blockers, and sample size in `specs/063-calendar-settings-ui/measurement.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: no dependencies.
- **Phase 2 Foundational**: depends on Phase 1; blocks every user story.
- **US1-US7 (P1)**: can start after Phase 2. Recommended order is US1 -> US2 -> US3 -> US4 -> US5 -> US6 -> US7 because the screen, boundary, provider/source state, selection, filters, sync, and prompts build naturally.
- **US8-US10 (P2)**: can start after Phase 2, but US8 benefits from US4-US6; US9 benefits from US3-US6; US10 can run alongside story work after shared components exist.
- **Final Phase**: depends on whichever stories are included in the implementation slice.

### User Story Dependencies

- **US1 Find Calendar Settings**: no dependency beyond foundation.
- **US2 Calendar Data Boundary**: can run after US1 route shell exists; copy/read model can be tested independently.
- **US3 Connect Calendar Source**: can run after US1/US2 for visible provider entry and boundary copy.
- **US4 Choose Calendars**: depends on source state from US3 and empty-selection contract from foundation.
- **US5 Event Types**: depends on preference persistence from foundation; preview integration can be deferred to US8.
- **US6 Sync Health**: depends on source cards from US3 and selected count from US4.
- **US7 Calendar-Driven Prompts**: depends on preferences from foundation and overlap rules from US4.
- **US8 Upcoming Preview**: depends on selected calendars and sync/event-category state for complete behavior.
- **US9 Disconnect**: depends on connected source cards and safe source state handling.
- **US10 Safe States & Accessibility**: cross-cuts all stories and should harden states as they land.

### Parallel Opportunities

- T001 and T002 can run in parallel.
- T005, T006, and T007 can run in parallel.
- Within each user story, test tasks marked `[P]` can be written before implementation work.
- Server-only stories and macOS-only tasks can run in parallel after Phase 2, especially T018/T023/T024 and T064/T065/T069/T070/T071.
- US8 preview and US9 disconnect can run in parallel after source/selection/sync read models are stable.

---

## Parallel Examples

### User Story 1

```text
Task: "T016 [US1] Add cabinet route contract tests in apps/server/tests/contract/test_calendar_settings_contract.py"
Task: "T018 [US1] Add macOS route policy tests in apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift"
```

### User Story 4

```text
Task: "T040 [US4] Add view-model tests in apps/server/tests/unit/test_calendar_settings_view_models.py"
Task: "T041 [US4] Add integration tests in apps/server/tests/integration/test_calendar_settings_flow.py"
```

### User Story 7

```text
Task: "T063 [US7] Add prompt preference server tests in apps/server/tests/unit/test_calendar_settings_view_models.py"
Task: "T064 [US7] Add desktop reminder tests in apps/macos/Shared/Tests/DesktopCalendarReminderTests.swift"
Task: "T065 [US7] Add native shell invariant tests in apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 only.
3. Stop and validate that Calendar settings is reachable in web and embedded macOS cabinet and is no longer a placeholder.

### Releaseable P1 Slice

1. Complete Phase 1 and Phase 2.
2. Complete US1 through US7 in order.
3. Validate with focused server tests, focused macOS tests, forbidden-content scan, and `infra/scripts/ci-local.sh`.
4. Do not deploy without separate release/deploy approval.

### Full 063 Slice

1. Complete all user stories US1-US10.
2. Run quickstart scenarios end to end.
3. Run `$speckit-analyze` before `$speckit-implement` if this file is changed after analysis.
4. Sync tasks to GitHub issues via `$speckit-taskstoissues` after analysis is clean.

---

## Notes

- Write tests first for each story phase and verify they fail before implementation.
- Keep calendar credentials server-owned; desktop code must not store or render provider credentials.
- Do not add new provider adapters, calendar mutation, bot auto-join, summary sending, attendee access grants, retrospective matching, or real auto-record behavior.
- Manual Record/Stop remains available and visible when workspace policy permits recording.
- Use existing cabinet primitives, CSS tokens, and macOS shell patterns before adding new abstractions.
