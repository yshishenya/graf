# Tasks: Простое подтверждение удаления

**Input**: [spec.md](spec.md), [plan.md](plan.md), [quickstart.md](quickstart.md)
**Lane**: high-risk-feature / deletion UX. Локальная реализация отдельно от приёмки выпуска.

## Phase 1: Setup and foundational review

Spec/clarify/plan готовы. До реализации обязательны независимые ux/security checklists, analyze и синхронизация GitHub issue. Новых компонентов и зависимостей нет.

## Phase 2: US1 — Понятное подтверждение

Цель: точный короткий текст; прежнее поведение удаления и доступность. Независимая проверка: HTML web/embedded и существующие контракты.

- [X] T001 [US1] Обновить контракт в apps/server/tests/contract/test_recording_governance_ui_contract.py и добавить проверку реального HTML обоих кабинетов в apps/server/tests/unit/test_cabinet_web_shell.py (FR-001–006, SC-001–003). (Issue #6853)
- [X] T002 [US1] Сократить _render_delete_confirmation в apps/server/src/twobrain_rec_server/cabinet/review_policy_rendering.py до заданного текста и кнопок; убрать ссылку, сохранить защиту и доступность, использовать CSRF_FORM_FIELD_NAME для hidden-токена с проверкой реальной отправки обоих кабинетов в test_cabinet_csrf.py; включить cycleAll существующего trapModalFocus в cabinet.js и проверить Tab/Shift-Tab через tests/browser/meeting-delete-focus.test.cjs; разрешить существующий адрес формы в DesktopCabinetRoutePolicy.swift с регрессионной проверкой DesktopCabinetNavigationRequestPolicyTests (FR-001–006). (Issue #6853)

## Phase 3: Validation and closeout

- [X] T003 [US1] Выполнить локальные проверки по specs/6791-simplify-delete-dialog/quickstart.md, записать результаты/ограничения в specs/6791-simplify-delete-dialog/validation.md и changes/unreleased/F6791.yaml; выполнить converge (SC-001–003). (Issue #6853)
- [ ] T004 [US1] После разрешённого коммита выполнить приёмку GRAF Dev и точного SHA по specs/6791-simplify-delete-dialog/quickstart.md; получить governance-fast для PR и release-full перед выпуском, записать PR/CI/ручное evidence в specs/6791-simplify-delete-dialog/validation.md (FR-004/005, SC-003). (Issue #6853)

## Dependencies

T001 → T002 → T003 → T004. Параллельная реализация не нужна; независимое review требований идёт до T001. T004 требует отдельной авторизации коммита/выпуска и не является доказанным локальными тестами.

## Strategy

Одно изменение общего renderer; использовать существующие стили, helper фокуса и серверное удаление. Не менять общий BOUNDED_DELETE_COPY. Область и новые изменения сверить через speckit-converge.

## GitHub

T001, T002, T003, T004: https://github.com/yshishenya/graf/issues/6853 (единая небольшая правка; исходная reservation обновлена, дублей нет).
