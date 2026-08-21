# Feature 168 implementation tasks and closeout status

Implementation source of truth for feature 168. Issue sync is intentionally
omitted. Checked tasks are implemented and validated at the evidence level
shown below; unchecked tasks remain blocked, partial, or require product/OAuth
approval.

## Phase 1 — Setup and decisions

- [X] T001 Record product-owner decisions for Google scope, provider catalog policy, disconnect retention and rollout flag in `specs/168-calendar-integration-completion/research.md`
- [X] T002 [P] Add provider/runtime readiness matrix and launch blockers to `specs/168-calendar-integration-completion/contracts/google-calendar.md`
- [X] T003 [P] Add synthetic fixture inventory and forbidden-content rules to `apps/server/tests/fixtures/calendar/README.md`

## Phase 2 — Foundational contracts

- [X] T004 [P] Define provider-neutral validation/catalog/event adapter contract in `apps/server/src/twobrain_rec_server/calendar/providers.py`
- [X] T005 [P] Define operation/job state and safe reason allow-list using existing audit/state helpers in `apps/server/src/twobrain_rec_server/calendar/service.py`
- [X] T006 Add contract tests for tenant, CSRF, ownership, idempotency and no-secret egress in `apps/server/tests/contract/test_calendar_integration_completion_contract.py`
- [X] T007 Add disposable Postgres/RLS and migration evidence commands to `specs/168-calendar-integration-completion/validation/implementation-evidence.md`

## Phase 3 — US1: Trustworthy connection state (P0)

- [X] T008 [P] Add provider connect state/result fixtures for empty, cancel, validation, denied and timeout in `apps/server/tests/fixtures/calendar_settings.py`
- [X] T009 Add integration tests proving no source before validated provider/catalog success in `apps/server/tests/integration/test_calendar_settings_flow.py`
- [X] T010 Add shared mutation busy/disabled/live-region behavior for connect, sync and disconnect in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T011 Add provider form state attributes, error target and focus return hooks in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`
- [X] T012 Extend safe PRG/fragment result projection with authoritative operation/source state in `apps/server/src/twobrain_rec_server/cabinet/web_routes/calendar_helpers.py` and `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T013 Run browser and embedded C168-01..05 with synthetic provider double and record evidence in `specs/168-calendar-integration-completion/validation/implementation-evidence.md`

## Phase 4 — US2: Real provider sync (P0)

- [X] T014 [P] Implement the smallest tested CalDAV adapter against the provider contract in `apps/server/src/twobrain_rec_server/calendar/caldav.py`
- [X] T015 Add adapter timeout, malformed payload, auth failure, rate-limit and retry tests in `apps/server/tests/unit/test_calendar_provider_runtime.py`
- [X] T016 Add idempotent sync job claim/worker execution using the existing maintenance runtime in `apps/server/src/twobrain_rec_server/calendar/worker.py`
- [X] T017 Route worker pages/cursors/normalized events/deletes through `apps/server/src/twobrain_rec_server/calendar/sync.py`
- [X] T018 Add persistence tests for queued/syncing/synced/stale/failure and cursor invalidation in `apps/server/tests/integration/test_calendar_persistence.py`
- [X] T019 Run C168-06..08 and update evidence with provider-call count, cursor and snapshot read-back

## Phase 5 — US3: Disconnect/deletion truth (P0)

- [X] T020 Add idempotent cleanup outcome and tombstone semantics in `apps/server/src/twobrain_rec_server/calendar/lifecycle.py`
- [X] T021 Ensure disconnect prevents queued/running job claims and runtime credential reads in `apps/server/src/twobrain_rec_server/calendar/service.py`
- [X] T022 Add integration tests for future cache purge, credential non-readability, matched-context retention and meeting deletion in `apps/server/tests/integration/test_calendar_disconnect_lifecycle.py` and `apps/server/tests/integration/test_calendar_deletion_lifecycle.py`
- [X] T023 Update confirmation/result copy and active-source projection in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`
- [X] T024 Run C168-09..11 across browser/embedded, reload, logout/login and tenant boundary

## Phase 6 — US4/US5: Selection, settings and context parity (P1)

- [X] T025 Add selection/save/error/read-back tests for zero/one/many calendars in `apps/server/tests/integration/test_calendar_settings_flow.py`
- [X] T026 Add browser/embedded accessibility tests for settings mutation/status/focus in `apps/server/tests/contract/test_calendar_settings_contract.py`
- [X] T027 Reuse and extend 098 matcher fixtures for provider freshness, recurrence, cancelled/private/all-day/overlap/offline in `apps/server/tests/integration/test_calendar_auto_context_match.py`
- [X] T028 [P] Extend native prompt/queue regression coverage only where the new server state requires it in `apps/macos/Shared/Tests/DesktopCalendarReminderTests.swift` and `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`
- [X] T029 Run C168-12..14 and verify native Record/Stop remains available

## Phase 7 — US6: Google Calendar beta (P1, gated)

- [X] T030 Add Google provider preset/read-only capability and feature flag in `apps/server/src/twobrain_rec_server/calendar/capabilities.py` and `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T031 Implement server OAuth start/callback/state/CSRF/redirect validation in `apps/server/src/twobrain_rec_server/cabinet/web_routes/calendar.py` and existing auth/config surfaces
- [X] T032 Implement Google token exchange/refresh with server-owned secret access in `apps/server/src/twobrain_rec_server/calendar/google.py` and `apps/server/src/twobrain_rec_server/calendar/credentials.py`; provider-side revoke is explicitly excluded
- [X] T033 Implement paginated `calendarList.list`, selected catalog reconciliation and safe account identity in `apps/server/src/twobrain_rec_server/calendar/google.py`
- [X] T034 Implement paginated full/incremental `events.list`, 410 full-resync, cancellation, recurrence, timezone, all-day and conference metadata normalization in `apps/server/src/twobrain_rec_server/calendar/google.py`
- [X] T035 Add Google stub/unit/contract tests without real tokens in `apps/server/tests/unit/test_google_calendar_provider.py` and `apps/server/tests/contract/test_google_calendar_contract.py`
- [ ] T036 Run dedicated test-account C168-15..17 only after OAuth client/consent/redirect/policy dependencies are approved; record no private event content

## Phase 8 — Cross-cutting validation and release readiness

- [X] T037 [P] Run forbidden-content and secret-egress scans and record output in `specs/168-calendar-integration-completion/validation/implementation-evidence.md`
- [X] T038 [P] Run focused server, macOS and browser accessibility suites from `specs/168-calendar-integration-completion/quickstart.md`
- [X] T039 Run server CI/lint/compile and record exact result plus unresolved RLS boundary in `specs/168-calendar-integration-completion/validation/implementation-evidence.md`
- [X] T040 Prepare Russian release/rollback notes and only then request separate release/production approval in `CHANGELOG.md` and release artifacts

## Phase 9 — US7: macOS upcoming tray

- [X] T041 [P] Add a native menu-bar controller and bounded SwiftUI upcoming
  popover in `apps/macos/RecApp/Sources/Calendar/CalendarTray.swift`, reusing
  the existing desktop calendar endpoint and safe event projection.
- [X] T042 Wire tray navigation to the existing embedded cabinet routes in
  `apps/macos/RecApp/App/TwoBrainRecApp.swift`; do not add an auth or calendar
  persistence path.
- [X] T043 Add synthetic tray ordering, safe-projection and auth-state tests
  in `apps/macos/Shared/Tests/DesktopCalendarReminderTests.swift`.
- [X] T044 Run the real installed macOS app and capture redacted visual
  evidence for icon, popover, loading/empty/error states, route navigation,
  narrow sizing and native Record/Stop parity.
- [X] T045 Run full macOS/browser/embedded regression after tray validation and
  update `validation/scenario-matrix.md` and `implementation-evidence.md`.

## Phase 10 — US8: home upcoming, provider truth and cohesive IA

- [X] T046 Audit the current GRAF home/settings screens and installed Krisp
  behavior with current-run UI inspection; retain only redacted/synthetic
  evidence and document clean-room patterns in `analysis.md`.
- [X] T047 Make provider runtime truth authoritative in
  `calendar/capabilities.py`; route every CalDAV alias through the existing
  adapter and mark EWS/Bitrix24 unavailable until real adapters exist.
- [X] T048 Add an authoritative upcoming section to browser and embedded
  meeting home using the existing settings/event projection and user timezone.
- [X] T049 Reorder and group calendar settings by user goal, make unavailable
  providers non-interactive and show connected counts without changing GRAF
  tokens or copying Krisp expression.
- [X] T050 Close action-state gaps: queued/syncing disabled state, reconnect
  entry, required CalDAV identity, adjacent native validation and form cleanup.
- [X] T051 Run provider/home/settings focused Postgres, contract, unit, JS and
  macOS tests and correct regressions.
- [X] T052 Visually walk browser and embedded desktop/narrow states, compare
  current-run screenshots, and update scenario/evidence without private data.
- [X] T053 Run full fast CI and final macOS regression, then close T045 if green.

## Phase 11 — Post-runtime remediation

- [X] T054 Bound provider pagination and retry/backoff, reject repeated page
  tokens and cover retryable reads in `calendar/google.py`, `calendar/caldav.py`
  and `tests/integration/test_calendar_provider_runtime.py`.
- [X] T055 Remove provider I/O from the source row-lock window and re-check the
  source before persistence so disconnect wins safely in `calendar/sync.py`.
- [X] T056 Collapse the hidden legacy settings grid column and add the shared
  responsive rail breakpoint listener in `cabinet.css`, `cabinet.js` and
  `tests/unit/test_cabinet_web_shell.py`.
- [X] T057 Expose the existing safe open-meeting endpoint as the explicit
  `Подключиться` CTA on home and prove it with a sealed synthetic fixture in
  `cabinet/rendering.py` and `tests/contract/test_calendar_settings_contract.py`.
- [X] T058 Re-run desktop/narrow/embedded/native visual checks, the full
  calendar PostgreSQL selection, fast CI and focused macOS reminder/tray tests;
  record only sanitized evidence.

## Phase 12 — Approved owner-decision implementation

- [X] T059 Remove provider-side revoke calls from every disconnect path while
  preserving immediate local credential purge, sync stop, 30-day content-free
  lifecycle metadata and idempotent cleanup; update lifecycle/provider tests.
- [X] T060 Replace disconnect confirmation/result copy with the approved short
  Russian text, remove external-revoke guidance and prove cancel/success/reload
  parity in browser and embedded macOS.
- [X] T061 Change full sync to seven days back and 365 days forward, enforce
  zero-to-20 selected calendars, reject volume overflow without silent
  truncation and add provider/selection/PostgreSQL boundary tests.
- [ ] T062 Run the complete real connect/catalog/select/sync/reconnect/local-
  disconnect matrix for every advertised provider in browser and embedded
  macOS; expose `Подключить` only for providers that pass and label
  every other provider `Скоро` without an active form.
- [X] T063 Re-run sanitized visual, accessibility, calendar PostgreSQL, macOS
  and fast-CI evidence after the T059–T061 policy implementation; keep the
  global all-users launch flag disabled while T036, T040, T062 and external
  OAuth/release gates remain open.
- [X] T064 Add and run a warmed disposable-PostgreSQL p95 regression for
  post-callback/cached-catalog projection and manual-sync acknowledgement in
  `apps/server/tests/integration/test_calendar_settings_flow.py`; record the
  NFR-006 receipt in `validation/implementation-evidence.md`.

## Phase 13 — Live sync-state remediation

- [X] T065 Bound browser/embedded refresh while a manual sync remains queued
  or syncing, show a safe long-running fallback after one minute, and prove the
  real UI changes state without a manual reload in `cabinet.js` and
  `tests/unit/test_cabinet_web_shell.py`.

## Dependencies and parallelism

`T001–T007 → T008–T013 → T014–T019 → T020–T024 → T025–T029`.
Google tasks `T030–T036` depend on runtime contract and owner launch gates;
they can run after foundational tasks but before parity closeout. `T002,
T003,T004,T005,T008,T014,T015,T028,T037,T038` are parallel only when their
listed files are not concurrently edited.
Tray tasks `T041–T043` depend on the existing desktop upcoming contract;
`T044–T045` are required for visual/runtime closeout and do not unblock Google
production launch gates.
Post-runtime tasks `T054–T058` close implementation regressions found during
the required visual and race-condition walkthrough; they do not close T036 or
the external Google launch gates.
Owner-decision tasks `T059–T064` depend on T001 and supersede any earlier
provider-revoke, future-only horizon or unverified-connectable behavior; they
must pass before T040 release preparation.

## Independent story tests

- US1: C168-01..05; no source before validated success; durable result/reload.
- US2: C168-06..08; provider call, cursor, snapshots and failure state.
- US3: C168-09..11; cleanup read-back, second-sync fail-closed and retention.
- US4/US5: C168-12..14; browser/embedded parity and native controls.
- US6: C168-15..17; dedicated Google test account plus stub failure matrix.

## MVP recommendation

Implement US1 + US2 + US3 for one provider runtime first. Google remains
feature-flagged until T030–T036 and policy/verification gates pass.
