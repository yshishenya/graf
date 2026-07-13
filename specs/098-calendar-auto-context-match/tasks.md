# Tasks: Calendar Auto Context Match

**Input**: Design documents from `specs/098-calendar-auto-context-match/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `checklists/calendar-context-readiness.md`

**Tests**: Required. Feature 098 is a high-risk active Spec Kit slice touching calendar privacy, authorization, recording metadata, persistence, lifecycle, web/macOS UX and production rollout. Test tasks precede implementation in each story.

**Organization**: Tasks are dependency ordered and grouped by the six user stories in `spec.md`. A task is checked `[X]` only after its exact acceptance evidence is recorded.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it uses different files and has no dependency on unfinished tasks in the same phase.
- **[Story]**: Maps to `US1`–`US6` in `spec.md`.
- Every task names exact repository paths.

## Phase 1: Setup And Baseline

**Purpose**: Anchor feature 098 without touching the four unrelated user-modified files and create reusable synthetic evidence surfaces.

- [X] T001 Create/switch to `codex/098-calendar-auto-context-match`, anchor `SPECIFY_FEATURE_DIRECTORY`, and record the active feature in `.specify/feature.json` without modifying unrelated user changes
- [X] T002 [P] Add bounded synthetic clear/overlap/private/stale/recurring fixtures in `apps/server/tests/fixtures/calendar_auto_match.py` and document their no-live-data rule in `apps/server/tests/fixtures/calendar/README.md`
- [X] T003 [P] Add synthetic resolve/selection/recovery fixture builders in `apps/macos/Shared/Tests/CalendarSettingsFixtures.swift`
- [X] T004 [P] Record pre-implementation HEAD, dirty-tree accounting, focused baseline commands and expected feature boundaries in `specs/098-calendar-auto-context-match/validation/baseline.md`

---

## Phase 2: Foundational Persistence, Contracts And Tenant Boundaries

**Purpose**: Introduce portable persistence/title provenance and shared contract types that block every user story.

**⚠️ CRITICAL**: No user-story implementation begins until migration, RLS and contract foundations pass.

- [X] T005 Add failing upgrade/reconciliation/downgrade coverage for meeting title provenance, match attempts and one context row per meeting in `apps/server/tests/integration/test_calendar_auto_context_migrations.py`
- [X] T006 [P] Add failing RLS inventory/policy requirements for `recording_calendar_match_attempts` and the extended context table in `apps/server/tests/contract/test_calendar_rls_contract.py`, `apps/server/tests/contract/test_rls_table_inventory_contract.py`, `apps/server/tests/contract/test_rls_policy_matrix_contract.py`, `apps/server/tests/fixtures/rls.py`, and `apps/server/tests/integration/test_rls_postgres_migrations.py`
- [X] T007 [P] Add `Meeting.title_source` and `Meeting.title_updated_at` to `apps/server/src/twobrain_rec_server/db/models/meeting.py` with conservative legacy defaults
- [X] T008 Add `RecordingCalendarMatchAttempt` and authoritative one-row `RecordingCalendarContextLink` state/snapshot fields to `apps/server/src/twobrain_rec_server/db/models/calendar.py`
- [X] T009 Implement portable migration/reconciliation/RLS policy changes in `apps/server/src/twobrain_rec_server/db/migrations/versions/0021_calendar_auto_context_match.py` using `batch_alter_table` and deterministic legacy collapse, and preserve authoritative unlink -> relink compatibility in `apps/server/src/twobrain_rec_server/calendar/service.py` and `apps/server/tests/contract/test_calendar_context_contract.py`
- [X] T010 Update workspace-table/RLS validation inventories and the 031 policy matrix for the new attempt entity in `apps/server/src/twobrain_rec_server/db/rls_validation.py`, `apps/server/tests/fixtures/rls.py`, and `specs/031-rls-hardening/contracts/rls-policy-matrix.md`
- [X] T011 Persist, reload and project meeting title provenance through `apps/server/src/twobrain_rec_server/ingest/store.py`, `apps/server/src/twobrain_rec_server/ingest/meetings.py`, `apps/server/src/twobrain_rec_server/ingest/manual_media_upload.py`, and `apps/server/src/twobrain_rec_server/api/ingest.py`
- [X] T012 [P] Add shared resolve/context/title enums and schemas in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T013 [P] Extend metadata-only calendar audit reason/outcome helpers in `apps/server/src/twobrain_rec_server/calendar/audit.py` and redaction assertions in `apps/server/tests/contract/test_calendar_no_secret_content_egress.py`
- [X] T014 Update the canonical API document for foundation-owned create/context schemas, keep exact runtime drift, and add direct resolve-schema ownership until T024 registers the route in `specs/012-server-ingest-foundation/contracts/openapi.yaml` and `apps/server/tests/contract/test_openapi_contract_drift.py`
- [X] T015 Run focused SQLite and disposable PostgreSQL migration/RLS suites and record exact reconciliation/rollback output in `specs/098-calendar-auto-context-match/validation/migration-foundation.md`
- [X] T016 Reconcile foundational implementation against `specs/098-calendar-auto-context-match/data-model.md` and record no unresolved schema/tenant blocker in `specs/098-calendar-auto-context-match/validation/migration-foundation.md`

**Checkpoint**: Portable schema, title provenance, RLS inventory and shared schemas are ready.

---

## Phase 3: User Story 1 - Automatic Title And Roster For One Clear Event (Priority: P1) 🎯 MVP

**Goal**: A normal online first-party recording resolves exactly one safe, fresh calendar event by actual recording time and receives immutable calendar title/roster context without manual event selection.

**Independent Test**: Start synthetic capture with one current or valid pre-start event, persist the opaque attempt, create the meeting, and prove `matched_auto`, calendar title precedence, safe roster, no provider call and one context row.

### Tests For User Story 1

- [X] T017 [P] [US1] Add failing matcher tests for clear current/pre-start events, later-overlap confirmation, strong dedupe and at least 100 warmed resolves at `<= 200 ms` p95 with four selected sources and 50 candidates in `apps/server/tests/unit/test_calendar_auto_context_match.py`
- [X] T018 [P] [US1] Add failing resolve/create/OpenAPI contract tests, including exact `expires_at = evaluated_at + 24 hours`, in `apps/server/tests/contract/test_calendar_auto_context_contract.py`
- [X] T019 [P] [US1] Add failing clear-match transaction, title, roster, idempotency, expiry-boundary, no-provider-I/O and at least 100 warmed atomic consumptions at `<= 50 ms` p95 in `apps/server/tests/integration/test_calendar_auto_context_match.py`
- [X] T020 [P] [US1] Add failing macOS automatic-resolve, attempt persistence and create-payload tests in `apps/macos/Shared/Tests/CalendarAutoContextMatchTests.swift`, `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`, and `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`

### Implementation For User Story 1

- [X] T021 [US1] Implement bounded deterministic eligibility/window/confidence/dedupe logic in `apps/server/src/twobrain_rec_server/calendar/matching.py`
- [X] T022 [US1] Load strong conference-link/source recurrence identities for matcher grouping in `apps/server/src/twobrain_rec_server/calendar/matching.py` and preserve bounded hashes in `apps/server/src/twobrain_rec_server/calendar/sync.py`
- [X] T023 [US1] Implement idempotent recording-start attempt creation with exact `evaluated_at + 24 hours` expiry and immutable safe title/roster/time/series capture in `apps/server/src/twobrain_rec_server/calendar/matching.py`
- [X] T024 [US1] Add `POST /desktop/recordings/{local_recording_id}/calendar-context/resolve` orchestration in `apps/server/src/twobrain_rec_server/api/calendar.py`, then register its `Idempotency-Key` operation and shared resolve schemas in `specs/012-server-ingest-foundation/contracts/openapi.yaml` with exact drift assertions in `apps/server/tests/contract/test_openapi_contract_drift.py`
- [X] T025 [US1] Implement atomic same-owner/workspace/device attempt consumption, reject consumption at the exact 24-hour expiry boundary, and finalize provisional-prestart state in `apps/server/src/twobrain_rec_server/calendar/matching.py`
- [X] T026 [US1] Consume the attempt in first-party meeting creation without blocking ingest in `apps/server/src/twobrain_rec_server/api/ingest.py` and `apps/server/src/twobrain_rec_server/ingest/meetings.py`
- [X] T027 [P] [US1] Send persisted desktop title provenance and opaque attempt ID in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- [X] T028 [P] [US1] Add durable attempt/resolve/selection models with backward-safe decoding in `apps/macos/Shared/Sources/Models/CalendarContextModels.swift` and `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [X] T029 [US1] Implement the non-blocking resolve client call and idempotency key in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- [X] T030 [US1] Start resolve only after capture begins and preserve its opaque result in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T031 [US1] Persist attempt ID through live enqueue/retry/create payloads in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [X] T032 [US1] Project immutable matched context/roster into meeting list and review schemas in `apps/server/src/twobrain_rec_server/cabinet/queries.py`, `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, and `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T033 [US1] Render `Из календаря` and matched roster context with existing cabinet primitives in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`
- [X] T034 [US1] Run the US1 unit/contract/integration/Swift filters and record exact SC-017 resolve/consumption p95, sample counts, 24-hour expiry and FR receipts in `specs/098-calendar-auto-context-match/validation/us1-clear-match.md`

**Checkpoint**: One clear live event produces independently testable automatic context.

---

## Phase 4: User Story 2 - Safe No-Match And Degraded Outcomes (Priority: P1)

**Goal**: Weak, private, all-day, stale, manual-upload, offline/recovery, cross-space and unavailable cases never receive automatic context and never block the recording pipeline.

**Independent Test**: Exercise every negative scenario with synthetic inputs and prove generic list state, owner-safe reason where allowed, unchanged upload/processing and zero private content/side effects.

### Tests For User Story 2

- [X] T035 [P] [US2] Add failing eligibility tests for weak/private/free-busy/all-day/cancelled/deleted/zero-duration/stale/latest-failed events and stale-source veto in `apps/server/tests/unit/test_calendar_auto_context_match.py`
- [X] T036 [P] [US2] Add failing manual-upload, missing-attempt, recovery, provider-failure and cross-space scenarios in `apps/server/tests/integration/test_calendar_auto_context_match.py`, `apps/server/tests/integration/test_manual_media_upload.py`, and `apps/server/tests/integration/test_calendar_provider_failures.py`
- [X] T037 [P] [US2] Add failing private-count/no-detail/audit-response assertions in `apps/server/tests/contract/test_calendar_auto_context_contract.py` and `apps/server/tests/contract/test_calendar_no_secret_content_egress.py`
- [X] T038 [P] [US2] Add failing recovered-queue/no-fabricated-attempt tests in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift` and `apps/macos/Shared/Tests/CalendarAutoContextMatchTests.swift`

### Implementation For User Story 2

- [X] T039 [US2] Implement strict auto-match filters and protected skip states independent of 063 preview preferences in `apps/server/src/twobrain_rec_server/calendar/matching.py`
- [X] T040 [US2] Persist `skipped_offline_or_unknown` for missing/invalid attempts without fallback matching in `apps/server/src/twobrain_rec_server/ingest/meetings.py`
- [X] T041 [US2] Persist `skipped_manual_upload` and upload/file title provenance in `apps/server/src/twobrain_rec_server/ingest/manual_media_upload.py`
- [X] T042 [US2] Implement current-source/horizon/latest-failure veto and fail-soft outcome shaping in `apps/server/src/twobrain_rec_server/calendar/matching.py`
- [X] T043 [US2] Expose generic list state plus owner-only safe no-context reasons in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T044 [P] [US2] Add 098 boundary helper copy to `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html` and `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T045 [US2] Ensure recovery scans and failed resolves never fabricate attempt IDs in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift` and `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T046 [US2] Record metadata-only matched/skipped/ambiguous/manual/offline/stale outcomes in `apps/server/src/twobrain_rec_server/calendar/audit.py` and keep meeting/upload/processing success independent in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [X] T047 [US2] Run the US2 negative/fail-soft/privacy filters and record exact FR receipts in `specs/098-calendar-auto-context-match/validation/us2-safe-no-match.md`

**Checkpoint**: Every unsafe/unavailable path degrades to truthful no context.

---

## Phase 5: User Story 3 - Ambiguity Choice, Correction And Durable Clear (Priority: P1)

**Goal**: Overlap/back-to-back recordings remain unlinked until the owner chooses an event or explicitly continues without context; corrections and clear survive retries.

**Independent Test**: Produce two safe candidates, prove no automatic title/roster, select/correct/clear through owner UI/API, retry meeting/sync, and prove one authoritative row with terminal user intent.

### Tests For User Story 3

- [X] T048 [P] [US3] Add failing GET/PUT/DELETE owner/non-owner/CSRF contract tests in `apps/server/tests/contract/test_calendar_auto_context_contract.py` and `apps/server/tests/integration/test_cabinet_csrf.py`
- [X] T049 [P] [US3] Add failing overlap/back-to-back/selection/retry/concurrent-owner scenarios and prove start-time `declined_by_user` remains distinct from later `cleared_by_user` in `apps/server/tests/integration/test_calendar_auto_context_match.py` and `apps/server/tests/integration/test_calendar_access_policy.py`
- [X] T050 [P] [US3] Add failing chooser/list/detail accessibility and localized-copy tests in `apps/server/tests/unit/test_cabinet_web_shell.py`, `apps/server/tests/integration/test_cabinet_meeting_list.py`, and `apps/server/tests/integration/test_cabinet_meeting_detail.py`
- [X] T051 [P] [US3] Add failing single-prompt automatic, overlap selection and explicit no-context intent tests in `apps/macos/Shared/Tests/DesktopCalendarReminderTests.swift`, `apps/macos/Shared/Tests/CalendarAutoContextMatchTests.swift`, and `apps/macos/Shared/Tests/CaptureControlTests.swift`

### Implementation For User Story 3

- [X] T052 [US3] Implement safe owner/non-owner context response projection and candidate resolution in `apps/server/src/twobrain_rec_server/calendar/service.py`
- [X] T053 [US3] Serialize explicit selection/correction/clear against the one context row, preserve automatic-vs-user precedence, and keep start-time `declined_by_user` distinct from later `cleared_by_user` in `apps/server/src/twobrain_rec_server/calendar/service.py`
- [X] T054 [US3] Add GET and extend PUT/DELETE meeting context endpoints in `apps/server/src/twobrain_rec_server/api/calendar.py`
- [X] T055 [US3] Load owner-safe candidates and context actions in `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [X] T056 [US3] Build list/detail/chooser/decline/clear view models and distinct RU/EN state copy in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T057 [US3] Add owner-only HTMX choose/continue-without/clear routes in `apps/server/src/twobrain_rec_server/cabinet/web_routes/calendar.py` and route registration in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T058 [US3] Render the main-column ambiguity fieldset, context inspector and stable-title clear confirmation in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`
- [X] T059 [P] [US3] Add design-system-consistent row/context/chooser/focus/responsive styles in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T060 [US3] Make single-event prompts automatic and overlap/without-context choices explicit in `apps/macos/RecApp/Sources/Calendar/DesktopCalendarPromptActions.swift` and `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T061 [US3] Persist only the opaque attempt ID and selected event ID in the macOS queue, while keeping selected/declined intent durable on the server attempt without changing capture truth, in `apps/macos/Shared/Sources/Models/AudioModels.swift` and `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [X] T062 [US3] Preserve embedded meeting-action routing in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift` and add coverage in `apps/macos/Shared/Tests/DesktopCabinetUploadLinkTests.swift`
- [X] T063 [US3] Run the US3 API/cabinet/Swift filters and record ambiguity, accessibility, concurrency, distinct decline/clear and durable-choice FR receipts in `specs/098-calendar-auto-context-match/validation/us3-ambiguity-correction.md`

**Checkpoint**: Ambiguity never produces wrong magic; explicit owner intent is durable.

---

## Phase 6: User Story 4 - Stable Title And Context History (Priority: P2)

**Goal**: Later provider edits, sync, deletion/cancellation and user clear never silently rewrite matched title/roster history or overwrite authoritative titles.

**Independent Test**: Match a recording, mutate/delete/cancel the source event and roster, exercise title sources and clear, then prove immutable meeting-owned context and truthful lifecycle accounting.

### Tests For User Story 4

- [X] T064 [P] [US4] Add failing title-source precedence and correction/clear tests in `apps/server/tests/integration/test_calendar_auto_context_match.py` and `apps/server/tests/integration/test_ingest_happy_path.py`
- [X] T065 [P] [US4] Add failing post-match rename/move/delete/cancel/roster-sync stability tests in `apps/server/tests/integration/test_calendar_persistence.py`
- [X] T066 [P] [US4] Add failing context/attempt deletion and disconnect accounting tests in `apps/server/tests/integration/test_calendar_deletion_lifecycle.py`, `apps/server/tests/integration/test_calendar_disconnect_lifecycle.py`, and `apps/server/tests/integration/test_meeting_deletion_workflow.py`

### Implementation For User Story 4

- [X] T067 [US4] Enforce title-source precedence and calendar-title correction rules in `apps/server/src/twobrain_rec_server/calendar/service.py` and `apps/server/src/twobrain_rec_server/ingest/meetings.py`
- [X] T068 [US4] Read review/list roster/title exclusively from immutable context snapshots after match in `apps/server/src/twobrain_rec_server/cabinet/queries.py` and `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T069 [US4] Expire/purge unconsumed attempts and scrub unresolved candidates on source disconnect in `apps/server/src/twobrain_rec_server/calendar/lifecycle.py`
- [X] T070 [US4] Add calendar-context artifact accounting and snapshot scrub on meeting deletion in `apps/server/src/twobrain_rec_server/calendar/lifecycle.py`, `apps/server/src/twobrain_rec_server/deletion/service.py`, and `apps/server/src/twobrain_rec_server/deletion/report.py`
- [X] T071 [US4] Reconcile legacy multi-link rows and safe snapshot backfill rules in `apps/server/src/twobrain_rec_server/db/migrations/versions/0021_calendar_auto_context_match.py`
- [X] T072 [US4] Render stable-title clear explanation and activity state in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`
- [X] T073 [US4] Extend metadata-only activity/audit projections for correction, clear and lifecycle outcomes in `apps/server/src/twobrain_rec_server/calendar/audit.py` and `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [X] T074 [US4] Run the US4 stability/lifecycle filters and record title-source, provider-mutation, deletion and rollback FR receipts in `specs/098-calendar-auto-context-match/validation/us4-stable-history.md`

**Checkpoint**: Recording history is stable and lifecycle-accounted independently of live provider state.

---

## Phase 7: User Story 5 - Recurring Meeting Continuity (Priority: P3)

**Goal**: Authorized users can see a safe pointer to the latest earlier matched occurrence in the same series/workspace, with no existence leak for deleted/inaccessible/cross-space meetings.

**Independent Test**: Match two occurrences, authorize/deny/delete/move the predecessor across scenarios, and prove only an authorized safe pointer/readiness state appears.

### Tests For User Story 5

- [X] T075 [P] [US5] Add failing series-key/UID-fallback/ordering tests in `apps/server/tests/unit/test_calendar_auto_context_match.py`
- [X] T076 [P] [US5] Add failing authorized/deleted/inaccessible/cross-space recurring scenarios in `apps/server/tests/integration/test_calendar_auto_context_match.py` and `apps/server/tests/integration/test_calendar_access_policy.py`
- [X] T077 [P] [US5] Add failing recurring pointer contract/render tests in `apps/server/tests/contract/test_calendar_auto_context_contract.py` and `apps/server/tests/integration/test_cabinet_meeting_detail.py`

### Implementation For User Story 5

- [X] T078 [US5] Derive and persist hashed provider-series/ical-UID fallback keys in `apps/server/src/twobrain_rec_server/calendar/matching.py`
- [X] T079 [US5] Query the latest earlier same-series meeting and apply its independent access decision in `apps/server/src/twobrain_rec_server/cabinet/queries.py`
- [X] T080 [US5] Add safe previous-meeting/readiness projections in `apps/server/src/twobrain_rec_server/api/schemas.py` and `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T081 [US5] Render the `В серии` review pointer and reuse it in the server-owned `Ближайшие` section in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`, and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html`
- [X] T082 [US5] Prove browser/embedded route parity for recurring context in `apps/macos/Shared/Tests/DesktopCabinetUploadLinkTests.swift` and `apps/server/tests/integration/test_cabinet_meeting_list.py`
- [X] T083 [US5] Run the US5 recurring/access filters and record same-series authorization FR receipts in `specs/098-calendar-auto-context-match/validation/us5-recurring-context.md`

**Checkpoint**: Recurring continuity provides a pointer without copying content or weakening access control.

---

## Phase 8: User Story 6 - Speaker Identity Remains Explicitly Deferred (Priority: P3)

**Goal**: Calendar invitees remain roster metadata and never become transcript speakers, permissions, recipients or delivery targets; future speaker naming stays a separate feature note.

**Independent Test**: Match a roster-heavy event and prove transcript labels remain `SPEAKER_XX`, access/share/delivery state is unchanged, and UI copy distinguishes invitees from speakers.

### Tests For User Story 6

- [X] T084 [P] [US6] Extend roster-versus-speaker regression coverage in `apps/server/tests/unit/test_cabinet_view_models.py` and `apps/server/tests/unit/test_calendar_participants.py`
- [X] T085 [P] [US6] Add zero-grant/share/delivery side-effect scenarios in `apps/server/tests/integration/test_calendar_access_policy.py` and `apps/server/tests/integration/test_meeting_share_links.py`
- [X] T086 [P] [US6] Add transcript-label and roster contract assertions in `apps/server/tests/contract/test_cabinet_contract.py` and `apps/server/tests/integration/test_cabinet_meeting_detail.py`

### Implementation For User Story 6

- [X] T087 [US6] Render roster copy that says invitees are not confirmed speakers in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`
- [X] T088 [P] [US6] Record calendar/contact speaker-name suggestions as a separate future capability and 098 exclusion in `docs/current-product-status.md` and `specs/098-calendar-auto-context-match/validation/future-speaker-naming.md`
- [X] T089 [US6] Run the US6 roster/speaker/access/share filters and record zero-side-effect counts in `specs/098-calendar-auto-context-match/validation/us6-speaker-deferral.md`
- [X] T090 [US6] Reconcile FR-020–FR-026 and FR-040/FR-044 against the final schemas/UI and record no identity/permission conflict in `specs/098-calendar-auto-context-match/validation/us6-speaker-deferral.md`

**Checkpoint**: Calendar context is useful without claiming speaker truth or creating delivery/access side effects.

---

## Phase 9: Polish, Cross-Cutting Validation And PR Readiness

**Purpose**: Prove the full 098 slice, keep the deferred security audit explicit, and prepare an evidence-backed PR without committing unrelated user changes.

- [X] T091 Run the complete focused server unit/contract/integration commands from `specs/098-calendar-auto-context-match/quickstart.md` and record exact counts in `specs/098-calendar-auto-context-match/validation/implementation-evidence.md`
- [X] T092 [P] Run focused Ruff from `specs/098-calendar-auto-context-match/quickstart.md` and record output in `specs/098-calendar-auto-context-match/validation/implementation-evidence.md`
- [X] T093 [P] Run the focused macOS `CalendarAutoContextMatch|DesktopUploadClient|DesktopUploadQueue|DesktopCalendarReminder|CaptureControl|DesktopCabinetWorkspace|DesktopCabinetUploadLink` filter and record counts in `specs/098-calendar-auto-context-match/validation/implementation-evidence.md`
- [X] T094 Run SQLite upgrade/downgrade plus `infra/scripts/verify-rec-migration.sh --execute` and record PostgreSQL/RLS/cleanup truth in `specs/098-calendar-auto-context-match/validation/migration-evidence.md`
- [X] T095 Execute every row in the quickstart scenario/FR map with synthetic data and record immutable receipts in `specs/098-calendar-auto-context-match/validation/scenario-matrix.md`
- [X] T096 Re-run and reconcile `specs/098-calendar-auto-context-match/checklists/requirements.md` and `specs/098-calendar-auto-context-match/checklists/calendar-context-readiness.md` against final artifacts
- [X] T097 [P] Add user-visible/architecture/QA/release-readiness changes under `[Unreleased]` in `CHANGELOG.md`
- [X] T098 [P] Update truthful implemented/not-released limitations and deferred standalone audit state in `docs/current-product-status.md`
- [X] T099 Review the final diff against `docs/agent-guidance/ponytail-upstream.md` and record simplification/debt decisions in `specs/098-calendar-auto-context-match/validation/ponytail-review.md`
- [X] T100 Run ordinary authorization/privacy/forbidden-content acceptance tests, record zero leaked-content receipts, and state explicitly that they do not complete the deferred Codex Security scan in `specs/098-calendar-auto-context-match/validation/implementation-evidence.md`
- [X] T101 Run `infra/scripts/ci-local.sh` once at closeout and record exact SHA/result/counts/known limits in `specs/098-calendar-auto-context-match/validation/implementation-evidence.md`
- [X] T102 Reconcile every `[X]` task with its GitHub issue/PR/evidence link in `specs/098-calendar-auto-context-match/tasks.md` and `specs/098-calendar-auto-context-match/validation/implementation-evidence.md`
- [X] T103 Prepare the Russian PR description with risk lane, FR/SC coverage, migration/rollback, validation evidence, 097 skip and deferred standalone audit in `.github/pull_request_template.md`-compatible form referenced from `specs/098-calendar-auto-context-match/validation/pr-closeout.md`
- [X] T104 Obtain explicit user approval for the implementation commit, stage only 098-owned files, and record commit/branch/status evidence in `specs/098-calendar-auto-context-match/validation/pr-closeout.md`

### Completed Task / GitHub Issue / Evidence Map

The mapping is one-to-one and deterministic: issue number = `3081 + task number`.
Baseline canon validation found `109/109` task-backed issues with no
missing, extra or duplicate task IDs. Completed task ranges reconcile as
follows; no issue is closed by local evidence alone.

| Completed tasks | GitHub issues | Primary receipt |
|---|---|---|
| T001–T004 | #3082–#3085 | `validation/baseline.md` |
| T005–T016 | #3086–#3097 | `validation/migration-foundation.md` |
| T017–T034 | #3098–#3115 | `validation/us1-clear-match.md` |
| T035–T047 | #3116–#3128 | `validation/us2-safe-no-match.md` |
| T048–T063 | #3129–#3144 | `validation/us3-ambiguity-correction.md` |
| T064–T074 | #3145–#3155 | `validation/us4-stable-history.md` |
| T075–T083 | #3156–#3164 | `validation/us5-recurring-context.md` |
| T084–T090 | #3165–#3171 | `validation/us6-speaker-deferral.md` |
| T091–T102 | #3172–#3183 | `validation/implementation-evidence.md` |
| T103–T104 | #3184–#3185 | `validation/pr-closeout.md` |

T105–T109 / #3186–#3190 remain open for merge, release, deploy, production
proof and final cleanup. Completed task issues remain open until post-merge
evidence and closure comments are available.

---

## Phase 10: Release, Deploy And Production Closeout

**Purpose**: Complete the active goal's release obligation after PR merge; do not substitute local CI for production proof.

- [X] T105 After PR merge, choose the next CalVer and run `./scripts/prepare-release.sh YYYY.MM.DD.N`, recording the version and generated diff in `specs/098-calendar-auto-context-match/validation/release-closeout.md`
- [ ] T106 Publish the matching tag and Russian GitHub Release notes with changes, validation, migration/compatibility, known limitations, PR/issues and deferred audit in `specs/098-calendar-auto-context-match/validation/release-closeout.md`
- [ ] T107 Run `infra/scripts/cd-remote.sh --dry-run`, resolve every gate, then run `infra/scripts/cd-remote.sh --execute` only when met and record backup/rollback/deployed SHA in `specs/098-calendar-auto-context-match/validation/release-closeout.md`
- [ ] T108 Prove production health, migration state, clear/no-context/ambiguous behavior, browser/embedded parity and installed macOS app impact without private content in `specs/098-calendar-auto-context-match/validation/release-closeout.md`
- [ ] T109 Close task-backed GitHub issues only after evidence comments, update `docs/current-product-status.md`, verify branch/worktree cleanup, and record that feature 097 plus the standalone security audit remain separately deferred in `specs/098-calendar-auto-context-match/validation/release-closeout.md`

---

## Dependencies And Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Starts from the validated `origin/master` snapshot and preserves unrelated dirty files.
- **Foundational (Phase 2)**: Depends on Setup and blocks every user story.
- **US1 (Phase 3)**: Depends on Foundational and creates the MVP live auto-match path.
- **US2 (Phase 4)**: Depends on the US1 matcher/state foundation; independently proves every no-match/degraded path.
- **US3 (Phase 5)**: Depends on US1 state plus US2 safe filtering; adds owner ambiguity/correction/clear.
- **US4 (Phase 6)**: Depends on US1/US3 context mutation and proves stable history/lifecycle.
- **US5 (Phase 7)**: Depends on US1 immutable series snapshot; can proceed in parallel with US4 after US3 schemas stabilize.
- **US6 (Phase 8)**: Depends on US1 roster projection; can proceed in parallel with US4/US5.
- **PR Readiness (Phase 9)**: Depends on all six user stories.
- **Release/Deploy (Phase 10)**: Depends on validated PR merge and release gate.

### User Story Dependency Graph

```text
Setup -> Foundation -> US1
                       ├── US2 -> US3 -> US4
                       ├──────────────> US5
                       └──────────────> US6
US1 + US2 + US3 + US4 + US5 + US6 -> PR Readiness -> Release/Deploy
```

### Parallel Opportunities

- T002, T003 and T004 can run in parallel.
- T005 and T006 are independent failing-test tasks; T007/T012/T013 touch separate files.
- Within each story, `[P]` test tasks can be authored in parallel before implementation.
- After US3 schemas stabilize, US4 lifecycle, US5 recurring queries and US6 regression/doc work can run in parallel on different files, with integration deferred until each story checkpoint.
- T092, T093, T097 and T098 can run in parallel only after the implementation diff is stable.

## Parallel Examples

### User Story 1

```text
T017 server matcher tests
T018 API contract tests
T019 server integration tests
T020 macOS tests
```

### User Story 3

```text
T048 API/CSRF contracts
T049 ambiguity/concurrency integration tests
T050 cabinet accessibility tests
T051 macOS prompt-intent tests
```

### User Stories 4–6 After US3

```text
US4: T064–T066 stability/lifecycle tests
US5: T075–T077 recurring tests
US6: T084–T086 speaker/access regression tests
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundation.
2. Complete US1 and its independent evidence.
3. Complete US2 before any product rollout so unsafe/no-match cases are covered.
4. Complete US3 before calling the primary calendar loop usable.

The MVP checkpoint is therefore US1+US2+US3, not a clear-match-only demo.

### Incremental Completion

1. US1: automatic clear match.
2. US2: safe silence/degradation.
3. US3: ambiguity/correction/clear.
4. US4: stable history/lifecycle.
5. US5: recurring pointer.
6. US6: explicit speaker/access deferral.
7. Full quickstart/CI, PR, merge, release and production closeout.

## Notes

- Run `$speckit-analyze` and resolve every critical blocker before `$speckit-taskstoissues` and implementation.
- Use `$speckit-taskstoissues` after analyze; do not create duplicate issues and use the repository's exact Russian title canon.
- Tests must fail for the intended reason before their implementation task begins.
- `[P]` means different files/no unfinished dependency, not permission to merge unreviewed parallel changes.
- Do not mark `[X]` from intent or partial output; attach exact evidence first.
- Do not commit implementation files until validation is complete and the user explicitly approves the commit.
- Do not touch `.specify/templates/checklist-template.md`, `.specify/templates/plan-template.md`, `AGENTS.md`, or `docs/agent-guidance/ponytail-upstream.md` except for an explicitly authorized managed update.
- Feature 097 and the standalone Codex Security audit remain separately deferred and are not prerequisites for 098 implementation.
