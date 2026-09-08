# Tasks: Страница итогов по интерфейсу Krisp

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [contracts/ui.md](contracts/ui.md), [design-handoff.md](design-handoff.md), [quickstart.md](quickstart.md).

**Подготовка 2026-09-08**: R01–R52 и подробная передача согласованы, задачи синхронизированы с GitHub. T001 принята независимым reviewer; T002 завершена: UX8/8, security5/5, analyze CRITICAL0/HIGH0/MEDIUM0, issue-canon validate PASS. Подробности — [readiness.md](readiness.md). Это не завершение всех конечных операций Krisp или проверки соответствия GRAF. Реализация T003–T008 выполнена локально; T009/T010 остаются открытыми. Доказательства — [validation/focused.md](validation/focused.md).

## Phase 1 — Исследование и подготовка

- [X] T001 Завершить и связать наблюдения установленного Krisp и веба, включая редактор блоков/текста, сохранение/отмену/восстановление, различия переименования/переназначения/удаления голоса и секции, AI Chat полного тарифа с принятым объёмом в `specs/257-krisp-meeting-detail/reference-audit.md` (FR-001/015/016/017, SC-001). (Issue #6797)
- [X] T002 Провести reviewer-owned UX/security review, analyze и синхронизировать задачи в `specs/257-krisp-meeting-detail/checklists/`, `analysis.md` и `issue-map.md` до реализации (FR-018). (Issue #6798)

T001/T002 выполнены локально как подготовка. Issues #6797/#6798 остаются открыты до опубликованных PR/SHA/governance-fast и validator закрытия по tracker-policy; это не незавершённые условия старта кода. Карта — [issue-map.md](issue-map.md).

## Phase 2 — US1: композиция страницы

**Goal**: единая центрированная колонка и компактная верхняя область в вебе/embedded.
**Independent test**: структурный контракт и synthetic reflow; все данные F239 доступны.

- [X] T003 [US1] Добавить проверки структуры, доступных действий и границ состояния в `apps/server/tests/contract/test_meeting_detail_reference_contract.py` (FR-002/003/005/012/013/014/019). (Issue #6800)
- [X] T004 [US1] Перестроить шапку/колонку/документ в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`, `cabinet/static/cabinet/cabinet.css` и при необходимости `cabinet/rendering.py`, сохранив все разделы и данные (FR-002/003/005/012/013/014/019). (Issue #6801)

## Phase 3 — US2: формат, вкладки и источники

**Goal**: picker рядом с итогами без потери генерации, клавиатуры и возврата.
**Independent test**: формат/каталог/Escape, источник/возврат и replacement-active.

- [X] T005 [US2] Перенести существующий format controls одной группой в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`, связать видимость с `activateDetailTab` в `cabinet/static/cabinet/cabinet.js`, сохранить доступное объяснение последствий и existing summary tests (FR-006/007/008/009/013). (Issue #6803)

## Phase 4 — US3: действия и копирование

**Goal**: прямое копирование выбранной вкладки через текущий доверенный экспорт; все действия встречи доступны.
**Independent test**: scopes, auth/revision error, detached form, rename, меню и отмена диалогов.

- [X] T006 [P] [US3] Добавить исполняемую Node-проверку async copy в `apps/server/tests/unit/test_meeting_detail_copy_runtime.py`, повторно используя способ запуска из `tests/contract/test_cabinet_static_assets_contract.py` (FR-010/018): outcomes→summary, recording→transcript, отсутствующий/disabled option, отсоединение формы/trigger, replacement-active с подключённой формой, запрет option во время await, повторный клик и смена вкладки. (Issue #6804)
- [X] T007 [US3] Добавить прямое копирование выбранного разрешённого состава через `initContentExport` в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, сохранив CSRF, редакции, recovery, доступный статус и все существующие действия (FR-004/010/011/018). (Issue #6806)

## Phase 5 — Проверка и закрытие

- [X] T008 Выполнить focused suites, lint, synthetic browser/reflow/keyboard, существующую смену подписи голоса → reload → восстановление и актуализировать связанные assertions в `apps/server/tests/`; результаты записать в `specs/257-krisp-meeting-detail/validation/focused.md` (SC-004/005). (Issue #6808)
- [ ] T009 После одобренного коммита проверить точный SHA через единственный GRAF Dev/dev-harness и Computer Use в вебе, включая смену подписи голоса → reload → восстановление на синтетических данных в обеих оболочках; сопоставить референс и FR/SC в `specs/257-krisp-meeting-detail/validation/ui-matrix.md` (SC-001/002/003/004/005). (Issue #6809)
- [ ] T010 Выполнить ponytail review, converge, canonical fast, связать состояние tasks/issues и написать `changes/unreleased/F257.yaml` и `specs/257-krisp-meeting-detail/validation/closeout.md`; открытые гейты не объявлять завершёнными (FR-018, SC-001/002). (Issue #6810)

## Dependencies & Execution Order

T001/T002 → T003 → T004 → T005 → T007 → T008 → T009 → T010. T006 после T002 может идти параллельно T004/T005, поскольку принадлежит отдельному файлу. T007 зависит от T006. Canonical fast также останавливается на dirty_worktree и выполняется после коммита. Пользовательское одобрение коммита после доступных проверок и продолжения T009 получено 2026-09-08; итоговый независимый review принят. Незавершённая ручная проверка не равна PASS.

## Implementation Strategy

Сначала существующий документ и шапка, затем безопасный перенос управления, затем один copy pipeline. Релиз, production и новая функциональность исключены. Не менять F256 и чужие правки.
