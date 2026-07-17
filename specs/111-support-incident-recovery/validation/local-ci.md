# Локальный gate и ускоренный runner

Риск/валидационный lane: **significant/high-risk feature** — auth/session и
CSRF, private GitHub egress, PostgreSQL-backed diagnostics, durable local state
и пользовательская деградация.

## Проверки

- `git diff --check`: **PASS**.
- Focused quickstart через disposable PostgreSQL runner: **45 passed, 2
  warnings**.
- Ускоренный `bash apps/server/scripts/run_local_postgres_tests.sh --full`:
  коллекция **1833** тестов, digest
  `34e7b7193f4b32012aa0bf4729df258c7fc33e2410fd3cc1ec848251cb56df40`;
  parallel-фаза на **8 workers** — **1802 passed, 1 skipped, 18 warnings**;
  строгая RLS-фаза — **29 passed, 1 skipped, 2 warnings**.
- `infra/scripts/ci-local.sh`: **PASS**. Внутри gate: legacy-audio guard,
  macOS build/tests (**572 tests, 0 failures**), `ContractValidation`, обе
  PostgreSQL-фазы, Ruff и deployment evidence scan.
- Результат canonical CI: `ci_local_result=pass`; disposable PostgreSQL
  контейнеры удалены после прогонов.
- После финального двухстрочного shrink из ponytail review повторён focused
  support-поднабор: **31 passed, 2 warnings**. Он подтверждает, что удалённый
  дублирующий flush не меняет поведение; полный CI выше был зелёным на том же
  кодовом пути непосредственно до этого механического упрощения.

В evidence нет секретов, live session material, аудио, расшифровок и private
production identifiers. Release/deploy не выполнялся: для него нужна отдельная
явная approval.
