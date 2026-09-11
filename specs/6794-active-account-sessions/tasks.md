# Tasks: Актуальные входы
## Phase 1 — Setup and foundational gates
Spec/clarify/plan готовы; reviewer-owned checklist и analyze до кода. Issue sync обязателен.
## Phase 2 — US1: только актуальный список
Independent test: смешанный набор состояний, текущий первым, общий счётчик действующих входов, история отсутствует.
- [X] T001 [US1] Расширить регрессию только действующих входов, unknown, одинаковых имён, пустого и недоступного состояния в `apps/server/tests/contract/test_account_routes.py` (FR-001–004, FR-007–008).
- [X] T002 [US1] Убрать историю и уточнить основной список, область пространства и справку в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html` (FR-001–004, FR-007–009).
## Phase 3 — US2: понятное завершение
Independent test: действующие POST/CSRF confirmation/cancel/current-protection в обеих формах кабинета.
- [X] T003 [US2] Согласовать подписи одиночного/массового завершения в шаблоне и `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py`; проверить их в `apps/server/tests/contract/test_account_routes.py` и существующем `apps/server/tests/integration/test_account_lifecycle.py` (FR-005–006, FR-008).
## Phase 4 — Validation and closeout
- [ ] T004 Проверить `quickstart.md`, записать локальное evidence/converge в `specs/6794-active-account-sessions/validation.md` и фрагмент `changes/unreleased/F6794.yaml`; до закрытия issues получить review и governance-fast exact PR SHA (SC-001–004).
## Dependencies and implementation strategy
T001 → T002 → T003 → T004. US1 сначала, US2 использует тот же шаблон. Параллельная запись кода не нужна; рецензент независимо проверяет требования. Все вопросы clarify разрешены; необязательное обновление AGENTS пропущено ради стабильного корневого router. Коммит-хуки disabled.

## GitHub ownership
Umbrella: https://github.com/yshishenya/graf/issues/6925
- T001: https://github.com/yshishenya/graf/issues/6926
- T002: https://github.com/yshishenya/graf/issues/6927
- T003: https://github.com/yshishenya/graf/issues/6928
- T004: https://github.com/yshishenya/graf/issues/6929

## Локальный результат
T001–T003 выполнены и проверены; issues OPEN до PR/точного SHA и governance-fast. T004 локальные проверки, screenshots и фрагмент готовы, остаток — review/CI и блокер версии specify в validation.md.

## Утверждённая доработка плотности
- [X] T005 [US1] Проверить компактный контракт и реализовать единый список, native details и соседнее серверное подтверждение в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`; регрессия в `apps/server/tests/contract/test_account_routes.py` (FR-010–011).
Зависимость: T001–T003 → T005 → повторная T004. Старые визуальные проверки T004 не подтверждают компактную версию.

- T005: https://github.com/yshishenya/graf/issues/6940

T005 локально выполнена: 83 contract/view-model + 7 PostgreSQL integration PASS, browser compact/keyboard/no-JS/200% PASS, независимый code review PASS. #6940 остаётся OPEN до PR/SHA/CI в T004.
