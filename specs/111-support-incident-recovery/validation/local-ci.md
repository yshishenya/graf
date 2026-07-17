# Локальный gate и ускоренный runner

Риск/валидационный lane: **significant/high-risk feature** — auth/session и
CSRF, private GitHub egress, PostgreSQL-backed diagnostics, durable local state
и пользовательская деградация.

## Проверки

- `git diff --check`: **PASS**.
- Focused quickstart через disposable PostgreSQL runner: **45 passed, 2
  warnings**.
- Ускоренный `bash apps/server/scripts/run_local_postgres_tests.sh --full`:
  коллекция **1872** тестов, digest
  `455d3cbedf0d052ccf68c069aae432fc1d896dd11d3efe03c065f26293e6a083`;
  parallel-фаза на **4 bounded workers** — **1836 passed, 1 skipped, 10
  warnings**; строгая RLS-фаза — **34 passed, 1 skipped, 2 warnings**.
- `infra/scripts/ci-local.sh`: **PASS**. Внутри gate: legacy-audio guard,
  macOS build/tests (**573 tests, 0 failures**), `ContractValidation`, обе
  PostgreSQL-фазы, Ruff и deployment evidence scan.
- Результат canonical CI: `ci_local_result=pass`; disposable PostgreSQL
  контейнеры удалены после прогонов.
- После финального двухстрочного shrink из ponytail review повторён focused
  support-поднабор: **31 passed, 2 warnings**. Он подтверждает, что удалённый
  дублирующий flush не меняет поведение; актуальный rebased quickstart также
  зелёный: **45 passed, 2 warnings**.

В evidence нет секретов, live session material, аудио, расшифровок и private
production identifiers. Deploy выполнен после явной approval; отдельный
CalVer release/tag остаётся границей release train.
