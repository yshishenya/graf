# Tasks: Подключение Яндекс Календаря

**Input**: Design documents from `/specs/201-yandex-calendar-enable/`

**Validation lane**: high-risk-feature. Production rollout is a separate
release gate and is not part of the first implementation step.

## Phase 1: Setup

**Purpose**: Lock the existing provider contract and evidence boundary.

- [X] T001 [P] Add the metadata-only certification matrix in `specs/201-yandex-calendar-enable/contracts/yandex-certification.md`
- [X] T002 [P] Record the existing Yandex CalDAV endpoint, app-password mode and current `Скоро` state in `specs/201-yandex-calendar-enable/research.md`

## Phase 2: Foundational

**Purpose**: Preserve the shared calendar runtime and fail-closed rollout seam.

- [X] T003 Inspect `apps/server/src/twobrain_rec_server/calendar/capabilities.py`, `apps/server/src/twobrain_rec_server/calendar/service.py` and `apps/server/src/twobrain_rec_server/calendar/worker.py`; document the smallest certified-provider change before editing code
- [X] T004 [P] Run the focused synthetic CalDAV, credential, normalization, worker, no-secret and settings contract checks from `specs/201-yandex-calendar-enable/quickstart.md`
- [ ] T005 [P] Run the PostgreSQL calendar lifecycle and tenant-boundary checks from `specs/201-yandex-calendar-enable/quickstart.md` with disposable `TWOBRAIN_DATABASE_URL`

## Phase 3: User Story 1 — Подключить Яндекс Календарь (P1)

**Goal**: Prove account validation and catalog discovery before exposing a connect action.

**Independent test**: Complete Y201-01 through Y201-03 in browser and embedded macOS with a dedicated Yandex test account; no secret enters evidence.

- [ ] T006 [P] Execute browser scenarios Y201-01 through Y201-03 and record only metadata verdicts in `specs/201-yandex-calendar-enable/validation/yandex-certification.md`
- [ ] T007 [P] Execute embedded macOS scenarios Y201-01 through Y201-03 and record only metadata verdicts in `specs/201-yandex-calendar-enable/validation/yandex-certification.md`
- [ ] T008 Keep `caldav_yandex` fail-closed as `Скоро` until the complete Y201-01–Y201-09 matrix passes; record any connect blocker without changing the allowlist
- [ ] T009 If a connect root cause is found, add the smallest regression test in `apps/server/tests/unit/test_caldav_provider.py` or `apps/server/tests/integration/test_calendar_settings_flow.py`

## Phase 4: User Story 2 — Выбрать и синхронизировать календари (P1)

**Goal**: Prove explicit selection, real sync and safe upcoming projection.

**Independent test**: Complete Y201-04 through Y201-06 in both surfaces, including zero selection and reload.

- [ ] T010 [P] Execute browser selection/sync/reconnect scenarios Y201-04 through Y201-06 and update `specs/201-yandex-calendar-enable/validation/yandex-certification.md`
- [ ] T011 [P] Execute embedded macOS selection/sync/reconnect scenarios Y201-04 through Y201-06 and update `specs/201-yandex-calendar-enable/validation/yandex-certification.md`
- [ ] T012 [P] Verify sync, selection-limit and failure behavior in `apps/server/tests/integration/test_calendar_provider_runtime.py`, `apps/server/tests/integration/test_calendar_provider_failures.py` and `apps/server/tests/integration/test_calendar_settings_flow.py`
- [X] T022 Add Yandex immediate-connect, selection-triggered, five-minute due-source and blocking manual-sync coverage in `apps/server/tests/integration/test_calendar_settings_flow.py` and `apps/server/tests/integration/test_calendar_provider_runtime.py`
- [X] T023 Implement the shared immediate source runner and five-minute Yandex due-source enqueue in `apps/server/src/twobrain_rec_server/calendar/worker.py`, preserving maintenance tenant scope and fail-closed states
- [X] T024 Wire Yandex connect and calendar-selection flows to start the first/next sync immediately in `apps/server/src/twobrain_rec_server/cabinet/web_routes/calendar.py`
- [X] T025 Make the settings sync action execute the selected source synchronously and update its user-facing progress copy in `apps/server/src/twobrain_rec_server/cabinet/web_routes/calendar.py` and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`

## Phase 5: User Story 3 — Отключить Яндекс безопасно (P1)

**Goal**: Prove local-first disconnect, cleanup and continued recording availability.

**Independent test**: Complete Y201-07 through Y201-09 in browser and embedded macOS, then verify reload and fail-closed repeat sync.

- [ ] T013 [P] Execute browser disconnect/reload scenarios Y201-07 and Y201-09 and update `specs/201-yandex-calendar-enable/validation/yandex-certification.md`
- [ ] T014 [P] Execute embedded macOS disconnect/Record-Stop scenarios Y201-08 and Y201-09 and update `specs/201-yandex-calendar-enable/validation/yandex-certification.md`
- [ ] T015 Verify cleanup and retention behavior in `apps/server/tests/integration/test_calendar_disconnect_lifecycle.py` and `apps/server/tests/integration/test_calendar_deletion_lifecycle.py`

## Phase 6: Polish and closeout

- [ ] T016 After Y201-01–Y201-09 all pass, update the certified-provider allowlist in `apps/server/src/twobrain_rec_server/calendar/capabilities.py` for `caldav_yandex` only
- [ ] T017 If the allowlist changes, update availability expectations in `apps/server/tests/unit/test_calendar_settings_view_models.py` and provider contract coverage in `apps/server/tests/contract/test_calendar_context_contract.py`
- [ ] T018 [P] Update `specs/201-yandex-calendar-enable/data-model.md` and `specs/201-yandex-calendar-enable/quickstart.md` with final evidence boundaries and any non-secret deviations
- [ ] T019 [P] Update `CHANGELOG.md` with the Yandex read-only rollout state only after the provider gate is actually changed
- [ ] T020 Run `infra/scripts/ci-local.sh` and reconcile every failed or skipped gate in `specs/201-yandex-calendar-enable/validation/yandex-certification.md`
- [ ] T021 Keep production deploy unexecuted until explicit release approval; if approved, run `infra/scripts/cd-remote.sh --dry-run --branch master` before any execute

## Dependencies and execution order

1. T001–T005 establish the contract and automated baseline.
2. T006–T009 are the MVP connect/certification slice. If real E2E fails, stop
   here, leave Yandex as `Скоро`, and fix the reported root cause.
3. T010–T012 require a successful connection and prove sync/reconnect.
4. T013–T015 prove disconnect and deletion truth.
5. T022–T025 extend the runtime before the selection/sync E2E scenarios:
   T023 implements the shared runner, T024 wires connect and selection, T025
   wires the blocking manual action, and T022 covers their regression cases.
6. T010–T012 require T022–T025, the foundational checks and a successful
   connection; they prove selection, sync and reconnect before T013–T015 prove
   disconnect and deletion truth.
7. T016–T021 are closeout/release gates; T021 is never automatic.

Parallel opportunities: T001/T002, T004/T005, T006/T007, T010/T011 and
T013/T014 can run in parallel when their evidence files are coordinated.

**MVP**: T001–T009 plus T022–T025 and a passing Y201-01–Y201-03 matrix, but no
availability change. Public rollout is not complete until T010–T021 and
explicit release approval are complete.
