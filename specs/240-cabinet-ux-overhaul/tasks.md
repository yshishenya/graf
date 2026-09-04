# Tasks: Полная переработка интерфейса кабинета GRAF

**Input**: Design documents from `/specs/240-cabinet-ux-overhaul/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/,
quickstart.md

**Tests**: Required because this is high-risk UX/reference-fidelity work. Tests
must protect the no-change functional UI contract.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Подготовить безопасный audit boundary и evidence.

- [X] T001 Собрать исходную surface/state/viewport матрицу и metadata-only before evidence в specs/240-cabinet-ux-overhaul/design-qa.md
- [X] T002 [P] Сопоставить presentation-only CSS/HTML/JS selectors с functional hooks в specs/240-cabinet-ux-overhaul/contracts/ui-surface-contract.md
- [X] T003 [P] Составить безопасный реестр legacy-кандидатов с доказательствами поиска в specs/240-cabinet-ux-overhaul/legacy-register.md

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Общая визуальная система и контрактные проверки до изменений поверхностей.

- [X] T004 Добавить focused contract assertions для маршрутов, HTMX/data-hooks, landmarks и функциональных IDs в apps/server/tests/contract/test_graf_ux_ui_contract.py
- [X] T005 [P] Добавить проверку accessibility/overflow invariants для shared cabinet shell в apps/server/tests/contract/test_cabinet_frontend_foundation_contract.py
- [X] T006 [P] Зафиксировать shared visual tokens, typography, surfaces, focus, density и responsive rules в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css

## Phase 3: User Story 1 - Список встреч (Priority: P1) 🎯 MVP

**Goal**: Первый экран кабинета сразу объясняет контекст, поиск, фильтры,
сортировку, загрузку и список встреч.

**Independent Test**: Проверить ready/empty/filtered/upload states на 320/390/768/1024/1440
в standalone/embedded; открыть встречу и вернуться без потери functional hooks.

### Tests for User Story 1

- [X] T007 [P] [US1] Расширить contract checks toolbar, row semantics, primary upload, empty/error states и responsive selectors в apps/server/tests/contract/test_cabinet_frontend_foundation_contract.py
- [X] T008 [US1] Расширить list journey checks для сохранения query/filter/sort/HTMX поведения в apps/server/tests/integration/test_cabinet_meeting_list.py

### Implementation for User Story 1

- [X] T009 [US1] Переработать композицию и responsive layout шапки списка, поиска, фильтров, сортировки и загрузки в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html
- [X] T010 [US1] Улучшить иерархию строк встреч, selection toolbar, status labels и empty/error states в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_list.html
- [X] T011 [US1] Реализовать визуальную полировку списка встреч без изменения data-hooks в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css
- [X] T012 [US1] Проверить и при необходимости упростить только presentation-only list handlers в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js

## Phase 4: User Story 2 - Detail встречи (Priority: P1)

**Goal**: Header, status, tabs, playback, transcript, outcomes и recovery
образуют одну понятную и честную иерархию.

**Independent Test**: Пройти ready/processing/partial/failed/unavailable detail,
переключить tabs, playback и recovery keyboard-only, затем проверить mobile.

### Tests for User Story 2

- [X] T013 [P] [US2] Расширить detail accessibility and no-change assertions в apps/server/tests/contract/test_cabinet_playback_contract.py и apps/server/tests/contract/test_recording_workflow_accessibility.py
- [X] T014 [US2] Расширить synthetic ready/partial/failed/unavailable detail journey checks в apps/server/tests/integration/test_cabinet_meeting_detail.py

### Implementation for User Story 2

- [X] T015 [US2] Переработать визуальную иерархию заголовка, meta, actions, tabs и processing recovery в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html
- [X] T016 [US2] Согласовать presentation of playback, transcript, outcomes, share and dialogs in apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_detail.html
- [X] T017 [US2] Улучшить detail layout, tab states, recovery hierarchy, player density and long-content wrapping в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css
- [X] T018 [US2] Удалить только доказанно недостижимые presentation-only detail branches в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js и зафиксировать evidence

## Phase 5: User Story 3 - Настройки и профиль (Priority: P2)

**Goal**: Settings IA and profile menu are predictable, grouped and reversible.

**Independent Test**: Пройти all settings routes and profile menu keyboard-only in
standalone/embedded, light/dark, without changing saved values unexpectedly.

### Tests for User Story 3

- [X] T019 [P] [US3] Расширить settings IA/navigation and focus assertions в apps/server/tests/integration/test_settings_ia_flow.py и apps/server/tests/contract/test_settings_ui_contract.py
- [X] T020 [P] [US3] Добавить profile menu keyboard/focus/disabled-action contract checks в apps/server/tests/contract/test_cabinet_frontend_foundation_contract.py

### Implementation for User Story 3

- [X] T021 [US3] Переработать shared sidebar, settings navigation, account summary и profile menu grouping в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html
- [X] T022 [US3] Согласовать headings, section cards, forms, empty/loading/error and primary actions across settings pages в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/*.html
- [X] T023 [US3] Согласовать sidebar/profile/settings responsive, theme and focus styling в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css
- [X] T024 [US3] Проверить menu disclosure, focus return, rail and theme interactions in apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js without changing form semantics

## Phase 6: User Story 4 - Auth, billing, shared и состояния (Priority: P2)

**Goal**: Secondary surfaces use the same visual language and truthful states.

**Independent Test**: Review auth, billing, shared, unavailable and deletion-report
screens in the surface matrix; functional forms and truth copy remain intact.

### Tests for User Story 4

- [X] T025 [P] [US4] Расширить auth/billing/share accessibility and no-change contract assertions в apps/server/tests/contract/test_billing_accessibility.py, apps/server/tests/contract/test_billing_ui.py и apps/server/tests/contract/test_recording_share_ui_contract.py
- [X] T026 [P] [US4] Добавить/расширить state-panel route coverage для shared/unavailable/deletion в apps/server/tests/contract/test_cabinet_shell_response_contract.py

### Implementation for User Story 4

- [X] T027 [US4] Согласовать auth hierarchy, provider states, email-code and legal copy layout в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/auth/*.html
- [X] T028 [US4] Согласовать billing/shared/deletion state cards and action hierarchy в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/*.html и apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/*.html
- [X] T029 [US4] Применить shared visual rules to auth, billing, shared, notices and full-page states в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Re-audit, safely clean legacy, collect evidence and close PR gate.

- [X] T030 [P] Удалить только legacy-кандидаты, прошедшие search/runtime evidence, и обновить specs/240-cabinet-ux-overhaul/legacy-register.md
- [X] T031 [P] Провести after visual/a11y/keyboard/responsive matrix and add metadata-only screenshots to specs/240-cabinet-ux-overhaul/evidence/
- [X] T032 Повторить полный UX/UI/IA audit against specs/240-cabinet-ux-overhaul/contracts/ui-surface-contract.md и записать findings before/after/remaining в specs/240-cabinet-ux-overhaul/design-qa.md
- [X] T033 Выполнить quickstart focused tests, `node --check`, `git diff --check` и `infra/scripts/ci-local.sh --fast`; сохранить результаты в specs/240-cabinet-ux-overhaul/validation.md
- [X] T034 Провести Ponytail review changed diff и убрать необоснованную сложность без ослабления accessibility, truth и functional hooks в changed files
- [X] T035 Подготовить русский PR body с risk/validation lane, exact source SHA, test evidence, screenshots, legacy impact и `Refs`/`Fixes` только для действительно закрытых issues

## Dependencies & Execution Order

- Phase 1 → Phase 2 → User Stories; each story can be reviewed independently
  after foundational contract protection.
- US1 and US2 are both P1; do US1 first for MVP, then US2.
- US3 and US4 can run in parallel after shared tokens, but the same CSS file
  requires sequential integration.
- Polish depends on all desired surface changes and the second audit.

## Parallel Opportunities

- T002/T003; T005/T006; T007/T008; T013/T014; T019/T020; T025/T026; T030/T031.
- Different agents may audit/test different files, but only one agent edits
  `cabinet.css`, `cabinet.js` or shared template files at a time.

## Implementation Strategy

1. Protect the no-change boundary and capture before evidence.
2. Ship the list/detail MVP polish first, validating after each story.
3. Apply the same tokens and information hierarchy to settings and secondary
   surfaces.
4. Run a second independent audit, then close only proven legacy candidates.
5. Run fast PR validation and prepare exact-SHA metadata.
