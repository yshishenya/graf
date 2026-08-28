# Tasks: Аккуратная нижняя панель воспроизведения

**Input**: Design documents from `specs/205-playback-panel-layout/`

**Risk lane**: `significant-feature`; shared web/desktop layout without backend or audio semantics.

## Phase 1: User Story 1 — Панель и scrollbar не пересекаются (P1)

**Independent Test**: Static/render contracts require sibling grid placement and reject fixed overlay/clearance compensation.

- [X] T001 [US1] Обновить failing layout contracts для sibling grid-row и отсутствия fixed/clearance anti-pattern в `apps/server/tests/contract/test_cabinet_static_assets_contract.py` и `apps/server/tests/unit/test_cabinet_web_shell.py`.
- [X] T002 [US1] Перенести playback в отдельную строку общего shell и удалить CSS/JS compensation в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` и `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.

## Phase 2: User Story 2 — Геометрия следует за боковой панелью (P1)

**Independent Test**: Collapsed/expanded rail states use the same content-column for main and playback without horizontal coordinate variables.

- [X] T003 [US2] Проверить и закрепить responsive rail/playback geometry во всех поздних CSS selectors и существующем Node harness в `apps/server/tests/contract/test_cabinet_static_assets_contract.py`.

## Phase 3: User Story 3 — Ограниченный экран и closeout (P2)

**Independent Test**: Wide/narrow/short web и desktop-embedded runtime matrix соответствует `contracts/playback-layout.md`.

- [X] T004 [US3] Выполнить focused/runtime/repository validation, обновить `CHANGELOG.md` и записать evidence в `specs/205-playback-panel-layout/quickstart.md`.

## Phase 4: Review remediation

- [X] T005 Исправить найденные до merge регрессии: остановить и удалить playback при потере доступа, закрепить именованный region и no-JS grid order, убрать stale bottom reserve со страниц без playback, расширить runtime matrix на preparing/unavailable, увеличенный timeline и реальную meeting-list страницу.

## Phase 5: Production regression remediation

- [X] T006 Поднять profile menu в нативный browser top layer с compatibility fallback и проверить отсутствие clipping/перекрытия в Chromium и WebKit через `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` и `specs/205-playback-panel-layout/evidence/playback-layout-runtime-check.cjs`.

## Dependencies & Execution Order

T001 precedes T002. T003 validates the completed layout. T004 closes the original slice. T006 is a bounded production-regression remediation after T005.

## Implementation Strategy

Один shell grid является источником геометрии. Не добавлять wrapper, dependency, JavaScript coordinate sync или platform-specific scrollbar offset.
