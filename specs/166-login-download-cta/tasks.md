# Tasks: Контекстная ссылка на приложение на экране входа

**Input**: Design documents from `specs/166-login-download-cta/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`

**Tests**: Required because this is a high-risk auth and user-facing UX lane.

**Organization**: Tasks are grouped by independently testable user story.

## Phase 1: Foundational regression coverage

**Purpose**: Capture web/embedded login surface expectations before the shared
rendering change.

- [X] T001 [P] Add web-login CTA render assertions in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T002 [P] Add `/desktop/...` login absence and auth-error route assertions in `apps/server/tests/integration/test_web_owner_session_context.py`

**Checkpoint**: Focused tests describe both target surfaces and fail only for
the missing context-aware CTA behavior.

## Phase 2: User Story 1 - Веб-пользователь видит приложение (Priority: P1)

**Goal**: Show one prominent secondary download CTA on browser login without
competing with the primary auth form.

**Independent Test**: Render `/login?next=/meetings` and its auth-error response;
the web CTA appears once, is keyboard-accessible and points to `/download`.

- [X] T003 [US1] Pass the normalized login surface context and render one web-only CTA outside the auth card in `apps/server/src/twobrain_rec_server/cabinet/auth_rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/auth/login.html`
- [X] T004 [US1] Style the web-only CTA in the lower-left auth viewport with responsive non-overlap and visible focus treatment in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T005 [US1] Run the focused browser-login render and integration checks from `specs/166-login-download-cta/quickstart.md`

**Checkpoint**: Browser login is independently usable and the existing
`/download` destination remains unchanged.

## Phase 3: User Story 2 - Встроенное приложение не предлагает скачать себя (Priority: P1)

**Goal**: Suppress the download CTA for every normalized `/desktop/...` login
target while preserving auth controls and error copy.

**Independent Test**: Render `/login?next=/desktop/meetings` and an embedded
auth-error response at wide and narrow widths; no download CTA or placeholder is
present.

- [X] T006 [US2] Run the embedded route and template contract checks from `specs/166-login-download-cta/quickstart.md`, including the no-placeholder and auth-controls checks
- [X] T007 [US2] Complete the wide/narrow embedded visual review and record the absence of the CTA in `specs/166-login-download-cta/quickstart.md`

**Checkpoint**: The shared login renderer has web/embedded parity without
adding a client header, cookie, route or auth-state change.

## Phase 4: Polish and closeout

- [X] T008 [P] Add a user-facing Russian entry for the context-aware login CTA in `[Unreleased]` of `CHANGELOG.md`
- [X] T009 Record focused test, visual matrix and metadata-only evidence in `specs/166-login-download-cta/quickstart.md`
- [X] T010 Run `infra/scripts/ci-local.sh --fast` once for the completed shared auth UX slice and record the result in `specs/166-login-download-cta/quickstart.md`

## Dependencies & Execution Order

- T001 and T002 are independent test setup tasks and can run in parallel.
- T003 is the shared rendering prerequisite for both user stories; T004 follows
  it because the new class must be positioned outside the panel.
- T005 follows T003–T004 and validates the web story.
- T006 follows T003 and validates the embedded branch; T007 follows T006.
- T008 may run in parallel with T006 after behavior is fixed; T009–T010 follow
  all implementation and visual checks.

## Parallel Execution Examples

- T001 and T002 can run in parallel because they touch separate test files.
- T008 can run in parallel with the focused validation tasks because it is a
  user-facing documentation-only change in `CHANGELOG.md`.
- T003 and T004 must remain sequential because both define the final rendered
  CTA contract and T004 depends on the template class.

## Implementation Strategy

Ship the smallest complete slice: regression assertions first, then one shared
rendering guard and scoped CSS, then browser/embedded visual checks. Do not add
client-side detection, analytics, persistence, new auth routes or a second
download surface.
