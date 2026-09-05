# Implementation Plan: Непрерывность способов входа при ошибках

**Branch**: `241-fix-auth-provider-errors` | **Date**: 2026-09-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/241-fix-auth-provider-errors/spec.md`

## Summary

Исправить общий разрыв серверных экранов авторизации: восстановимые ошибки
email-входа, регистрации и запуска внешнего провайдера должны повторно читать
тот же workspace-scoped provider snapshot, который используется исходной
страницей, вместо локальной подмены `providers=[]`. Один существующий загрузчик
политики остаётся источником правды и fail-closed возвращает пустое состояние,
если безопасно прочитать политику нельзя. Дополнительно экран сохраняет только
нормализованный корректный email, а сообщение pre-delivery отказа становится
правдивым и не раскрывает существование аккаунта. Новые модели, миграции,
провайдеры, зависимости и production-настройки не нужны.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: FastAPI, SQLAlchemy 2 async, PostgreSQL, Jinja 3

**Storage**: Существующие workspace provider policies и auth-состояния в PostgreSQL; схема не меняется

**Testing**: pytest 9, FastAPI TestClient, существующий PostgreSQL/RLS harness

**Risk / Validation Lane**: `high-risk-feature` — меняются auth recovery UX, provider policy projection и маршруты входа

**Release Gate**: focused checks, feature quickstart и `infra/scripts/ci-local.sh --fast` до PR; deploy отсутствует

**Target Platform**: Linux server; общие browser и embedded macOS WebView auth surfaces

**Project Type**: FastAPI web service с серверной HTML-авторизацией

**Performance Goals**: не добавлять чтение provider policy в успешный email-start path; на ошибку — не более одного дополнительного локального DB snapshot read

**Constraints**: сохранить forced RLS, CSRF, OAuth state/nonce, одноразовые коды, rate limits, verified-email, безопасный `next` и транзакционные границы; не раскрывать наличие аккаунта

**Scale/Scope**: все error-rendering ветки `GET/POST login`, `sign-up` и `provider/start` в одном серверном модуле и их существующие шаблоны/интеграционные тесты

## Constitution Check

*GATE: Passed before Phase 0 research; re-checked after Phase 1 design.*

- **Spec-driven delivery**: PASS — Feature 241 использует mandatory clarify,
  security/UX checklists, tasks, analyze, issue sync и convergence.
- **Tenant/privacy boundary**: PASS — используется существующий
  `WorkspaceAuthContext`; область RLS и роли не расширяются.
- **Auth integrity**: PASS — обычный вход не создаёт и не связывает аккаунт;
  CSRF, state/nonce, rate limit, verified-email и single-use правила не меняются.
- **Truthful recovery**: PASS — pre-delivery отказ не маскируется под сбой
  доставки и не подтверждает наличие либо отсутствие пользователя.
- **Surface parity/accessibility**: PASS — browser и embedded используют один
  серверный contract; активные провайдеры остаются обычными доступными ссылками.
- **Secret/evidence discipline**: PASS — только синтетические email; коды,
  токены, реальные идентификаторы и данные встреч не попадают в артефакты.
- **Release integrity**: PASS — изменения серверные, сборку macOS и production
  не затрагивают; PR привязывается к точному SHA.
- **Post-design re-check**: PASS — после Phase 1 нет новой схемы, зависимости,
  внешнего вызова или исключения из конституции.

## Validation Plan

1. Тестами сначала зафиксировать текущий сброс провайдеров для invalid email,
   invitation mismatch, rate limit, unknown/unselectable identity, delivery
   failure, sign-up и provider-start ошибок.
2. В той же матрице проверить включённые, частично выключенные и недоступные
   provider policies, browser/embedded safe-next и отсутствие новых кодов или
   сессий на отказах.
3. Проверить сохранение нормализованного корректного email и экранирование
   HTML-подобного значения шаблонизатором; неверный email не отражать.
4. Выполнить статический аудит всех `render_login_page` /
   `render_signup_page` call sites: `providers=[]` допустим только без
   безопасного workspace/DB/policy context или в намеренном recovery state.
5. Запустить focused pytest selectors, Ruff для затронутых Python-файлов,
   compile/template assertions, `git diff --check` и quickstart.
6. Запустить `infra/scripts/ci-local.sh --fast`, затем проверить обязательный
   GitHub Actions `governance-fast` на точном SHA PR. Полный CI относится к
   frozen release candidate и в этой PR-задаче не требуется.

## Project Structure

### Documentation (this feature)

```text
specs/241-fix-auth-provider-errors/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── auth-error-continuity.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/cabinet/
├── auth_rendering.py
├── templates/cabinet/auth/login.html
├── templates/cabinet/auth/signup.html
└── web_routes/auth.py

apps/server/tests/integration/
└── test_web_owner_session_context.py

apps/server/tests/contract/
├── test_account_routes.py
└── test_auth_contracts.py

changes/unreleased/
└── F241.yaml
```

**Structure Decision**: Исправить существующий общий auth route/rendering path
и расширить его текущий интеграционный модуль. Не создавать второй provider
registry, сервис, middleware, клиентский сценарий или новую таблицу.

## Complexity Tracking

Нет нарушений конституции и исключений, требующих оправдания.
