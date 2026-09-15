---

description: "Задачи реализации немедленного handoff записи в список встреч"
---

# Tasks: Immediate meeting-list handoff after native recording upload

**Input**: Design documents from `/specs/265-meeting-list-handoff/`

**Risk lane**: `high-risk-product` — видимый пользовательский путь записи,
доступность, фокус, выбор и восстановление после сбоя.

**Scope**: общий JavaScript кабинета и браузерные проверки. Серверная модель,
API, upload protocol, нативный мост, аудиозапись, обработка, удаление и
авторизация не меняются.

## Phase 1: Regression tests (before implementation)

**Purpose**: Зафиксировать пользовательский контракт до завершения изменения.

- [X] T001 [US1] Add the native-recording handoff browser scenario in `apps/server/tests/browser/local-recording-handoff.test.cjs`: detect the first missing-`meetingId` to confirmed-`meetingId` transition and the first linked projection in a newly loaded WebView, issue one current-form list refresh, keep the local alias until the response, and leave exactly one server row after the swap.
- [X] T002 [US2] Extend `apps/server/tests/browser/local-recording-handoff.test.cjs` with search, status/access filters, sorting, selection, keyboard focus, and excluded-result cases so the automatic refresh preserves context and does not resurrect an excluded alias.
- [X] T003 [US3] Extend `apps/server/tests/browser/local-recording-handoff.test.cjs` with repeated-progress, multiple-handoff, failed-request, retry, authorization-error, and no-page-error cases; keep the existing recovery/retry interaction as the only recovery surface, clear private DOM on `401/403`, preserve the native projection, and reconcile to one server row after reauthorization.

## Phase 2: Shared cabinet implementation

**Purpose**: Исправить общий стык локальной проекции и авторитетного списка одной
реализацией без дублирования логики в Swift или API.

- [X] T004 [US1] Implement the complete edge-triggered handoff in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`: track pending server identities per stable local ID, coalesce one publication into one `requestMeetingListRefresh` request, retain the temporary local row, and reconcile it on the authoritative `htmx:afterSwap` response without weakening existing HTMX fencing or manual-upload refresh behavior. (Issue #7008)
- [X] T005 [US2] Preserve list interaction semantics in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`: keep the current form query/filter/sort, transfer selection and focus only when appropriate, respect later user focus movement and modal interaction, and remove rather than resurrect a local alias when the authoritative result excludes it.
- [X] T006 [US3] Preserve failure and recovery semantics in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet.js`: keep pending local custody visible through the existing service/offline retry path, retain the pending state on request failure, and avoid new polling, notifications, API endpoints, local paths, or page errors.

## Phase 3: Validation and handoff

**Purpose**: Проверить фичу в выбранном полном контуре и оставить понятное
доказательство того, что релизные действия в эту задачу не входят.

- [X] T007 [US3] Run the focused browser and Python regression commands from `specs/265-meeting-list-handoff/quickstart.md`, including `node --check`, `git diff --check`, `local-recording-handoff.test.cjs`, `mixed-meeting-list.test.cjs`, `local-recording-focus.test.cjs`, and the three listed cabinet pytest modules.
- [X] T008 [US3] Add the Russian changelog fragment `changes/unreleased/F265.yaml` with the final GitHub issue reference and the `high-risk-product` validation lane; state that production release, deployment, public artifacts, and installed-app acceptance are out of scope.
- [X] T009 [US3] Run `infra/scripts/ci-local.sh --focused` and record the result for Feature 265; leave exact-PR-SHA GitHub checks (`governance-fast`, `macos-pr`, `pr-metadata`) as the pre-merge gate and do not claim release or deployment evidence.

## Dependencies and execution order

- T001–T003 are regression tests and precede T004–T006.
- T004 is the shared behavioral foundation; T005 and T006 refine the same path
  and run after T004 because they touch the same JavaScript file.
- T007 depends on T001–T006. T008 depends on GitHub issue sync so it can contain
  the real issue number. T009 depends on the implementation and focused local
  checks.
- No task changes Swift, the meeting API, upload protocol, database schema,
  retention, deletion, auth, or AI behavior.

## Traceability

| User story / requirement | Tasks |
| --- | --- |
| US1; FR-001–FR-006; SC-001–SC-002 | T001, T004 |
| US2; FR-007; SC-003–SC-004 | T002, T005 |
| US3; FR-003, FR-009–FR-011; SC-005–SC-006 | T003, T006–T009 |
| FR-008 and the out-of-scope boundaries | T004, T006, T009 |
