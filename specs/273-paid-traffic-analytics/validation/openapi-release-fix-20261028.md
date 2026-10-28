# F273/T113: исправление OpenAPI после остановки выпуска

Дата: 28.10.2026. Lane: active Spec Kit slice / high-risk API contract.
Основа: `5fe5bc711a5bc934c066e6fdf2ab3a56188c5120`.

## Причина и границы

Full40606039505 остановил выпуск до dry-run/CD на строгом сравнении runtime
OpenAPI с canonical YAML. В двух POST `/api/v1/product-analytics/events` и
`/api/v1/product-analytics/posthog-desktop-capture` принятая зависимость
`get_optional_principal` добавила три необязательных header-параметра:
`X-User-Id`, `X-Organization-Id`, `X-Workspace-Id`. YAML не был синхронизирован.
Полный структурный diff содержит только эти два массива.

В canonical YAML добавлены ровно эти массивы, 50 строк. Порядок остальных
узлов сохранён. Код авторизации, маршруты, модели, миграции, флаги и equality
тест не менялись. Заголовки описывают существующий ввод; рабочее разрешение
legacy-header auth, сбор IP или аналитики этим не включаются.

## Допуск и согласованность

Независимое before-code ревью: `.dev/growth/openapi-before-code-review-20261028.md`.
117 checked / 0 unchecked; девять обязательных входов совпали. Применено
разрешённое владельцем повторное чтение затронутых требований F273.

Узкий анализ: FR021/025 → T113 → принятая trusted-principal boundary двух
HTTP ingress → canonical schema → существующий strict drift test.
Новых требований, целей, прав, получателей и состояний данных нет.
Critical=0, high=0, medium=0, blocking clarifications=0; новая фича не нужна.
Существующая связь T113 с открытой #7698 проверена; общая задача не закрывается.

## Проверки

До исправления один существующий equality test: 1 failed, 2 warnings, 6.84с;
runner11с. Одноразовая PostgreSQL удалена штатным runner.

После исправления:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/contract/test_openapi_contract_drift.py \
  tests/contract/test_activation_milestone_ingress.py \
  tests/integration/test_product_activation_analytics_rollout.py
```

**30 passed, 2 warnings, 10.98с; runner14с.** Контейнер удалён. Набор
покрывает полное равенство схем, оба HTTP ingress, отсутствие/подмену principal,
конкуренцию, отзыв при ожидании lock и безопасное выключенное состояние.

`git diff --check`, changelog-fragments, development-process и
spec-kit-governance: PASS. Локальный указатель первоначально имел неканоническое
значение lane; исправлен на `active-spec-kit` и охват сохранённых отчётов.
Продуктовые документы/правила из-за этого не менялись.

Converge узкой коррекции: canonical schema равна runtime, runtime и строгий
тест не менялись, новых обязательных работ именно по двум узлам не найдено.
T112/T113/T106/T118 и общая воронка остаются открытыми.

## Оставшиеся ворота

Текущие exact-SHA/base PR checks, merge, обновлённая подготовка неопубликованного
v2026.10.28.1, новый frozen candidate с собственным Full, dry-run/CD и рабочая
приёмка. Проваленный кандидат не переписывается и не переиспользуется.
Успех тестов не доказывает трафик, оплату или включённое измерение.

## Контрольные суммы

- `specs/012-server-ingest-foundation/contracts/openapi.yaml`: `8c1a7eacc932b570c1da495618a6deb5698579ea3d99b91b12b82a9e9f767318`
- `.dev/growth/openapi-before-20261028.log`: `22af496a1a6a58b5972a792365cb17c9dee085547185cf45242231fada8c737f`
- `.dev/growth/openapi-after-20261028.log`: `af4b4ca9562c13c0f63a36f1d0edc23a7e57d256e815637fcd3f7b76cd517758`
- `.dev/growth/openapi-diff-20261028.json`: `4547ee18f68446077feae1da669e69efbfab8483e36398d89f9254cf9b5eb60a`
- `.dev/growth/openapi-before-code-review-20261028.md`: `a239ed2f8ce043f1bed0b5b4a1d00feec3eb45d04db4b572c6007859c1a44ab3`
