# Tasks: Непрерывность способов входа при ошибках

**Input**: Design documents from `specs/241-fix-auth-provider-errors/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/auth-error-continuity.md`, reviewer-approved custom checklists

**Tests**: Auth относится к high-risk lane, поэтому проверки пишутся и запускаются до реализации.

## Phase 1: Regression coverage

**Purpose**: Зафиксировать общий дефект до изменения production-кода.

- [x] T001 [US1] Добавить failing матрицу login, sign-up и provider-start ошибок с enabled/disabled/unavailable policy, browser/embedded safe-next, сохранением и экранированием email в `apps/server/tests/integration/test_web_owner_session_context.py`, `apps/server/tests/contract/test_auth_contracts.py` и `apps/server/tests/contract/test_account_routes.py`

**Checkpoint**: Проверки воспроизводят исчезновение Яндекс ID/VK и очищение корректного email на текущем master.

---

## Phase 2: User Story 1 — сохранить доступные способы входа (Priority: P0)

**Goal**: Все восстановимые auth errors используют фактический workspace provider snapshot.

**Independent Test**: Для каждой error class сравнить provider href/state с исходной страницей при enabled, partially disabled и unavailable policy.

- [x] T002 [US1] Свести восстановимые login/sign-up/provider-start error responses к существующему provider loader, сохранив fail-closed исключения и удалив связанное дублирование в `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth.py`

**Checkpoint**: Ошибка одного способа не удаляет другие разрешённые способы и не активирует выключенные.

---

## Phase 3: User Story 2 — правдивое восстановление email (Priority: P1)

**Goal**: Исправить сообщение и сохранить только безопасно нормализованный редактируемый email.

**Independent Test**: Unknown/unselectable identity и delivery failure показывают разные сообщения; корректный email сохраняется, неверный/HTML-подобный ввод не становится разметкой.

- [x] T003 [US2] Добавить `email_value` в существующий rendering/template contract, передавать только нормализованное значение и заменить non-enumerating pre-delivery copy с сохранением accessibility semantics в `apps/server/src/twobrain_rec_server/cabinet/auth_rendering.py`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/auth/login.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/auth/signup.html` и `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth.py`

**Checkpoint**: Пользователь понимает дальнейшие действия и не повторяет корректный ввод; account enumeration не появляется.

---

## Phase 4: User Story 3 — аудит и evidence (Priority: P1)

**Goal**: Устранить sibling-разрывы и только доказанно связанный legacy/duplicate code.

**Independent Test**: Репозиторный поиск не находит error render с `providers=[]`, когда workspace и DB доступны; успешные auth flows остаются зелёными.

- [x] T004 [US3] Провести scoped аудит всех auth error-render call sites, добавить changelog в `changes/unreleased/F241.yaml` и записать вывод/проверки в `specs/241-fix-auth-provider-errors/evidence.md`

**Checkpoint**: Общий root cause исправлен один раз, несвязанный auth-код не реорганизован.

---

## Phase 5: Validation and PR closeout

**Purpose**: Закрыть high-risk-feature gates на точном PR SHA.

- [ ] T005 Выполнить focused pytest, Ruff, compile, template assertions, `git diff --check`, `$speckit-converge` и `infra/scripts/ci-local.sh --fast`, сохранив результаты в `specs/241-fix-auth-provider-errors/evidence.md`
- [ ] T006 Создать commit/push/русский PR с high-risk lane и Exact source SHA, синхронизировать task-backed issues и дождаться `governance-fast` на том же SHA

---

## Dependencies & Execution Order

- T001 выполняется до production-кода и должна сначала воспроизвести дефект.
- T002 зависит от T001; T003 использует тот же общий error path.
- T004 выполняется после T002–T003.
- T005–T006 выполняются последовательно после всех пользовательских историй.
- До T001 все custom checklists должны иметь 0 unchecked items, а `$speckit-analyze` — 0 critical/high findings.

## Implementation Strategy

Использовать существующий provider loader, Jinja autoescape и текущий
интеграционный модуль. Не добавлять зависимости, таблицы, клиентский JavaScript,
новый provider registry или общий framework для одного auth-модуля.
