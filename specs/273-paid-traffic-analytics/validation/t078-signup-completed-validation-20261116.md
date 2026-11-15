# T078 — охват завершённого шага регистрации, 16.11.2026

## Результат и границы

Продолжение FR-020/T078 реализовано и локально проверено на основе
`e44aae0a3c174249b72db77894ff761e67e2d962`. Полоса — `high-risk-product`
в существующей F273. Issue — [#8054](https://github.com/yshishenya/graf/issues/8054).
Новый аккаунт через обычный email-вход и общий OAuth callback теперь добавляет
прежний обезличенный шаг после успешного окончательного commit. Явная форма
регистрации сохраняет один шаг. Повторный вход и привязка не добавляют его.

Это счётчик шагов с возможным пропуском при отказе, а не авторитетный реестр
новых внешних клиентов. Схема, авторизация, cookies, согласие, контент, вёрстка,
почта и рабочие настройки не менялись. Рабочий сбор не включался.
T098/T099/T112/T113, полное измерение, T0, трафик и продажи остаются открытыми.
Postal — почтовая интеграция ГРАФ; соседний Stalwart не зависимость этого среза.

## Требования и независимый контроль

Формальное clarify16.11, уточнённые plan/quickstart и повторно открытый T078
предшествовали коду. Reviewer-owned checklist — 12/12, открытых0.
Scoped analyze: CRITICAL0/HIGH0/MEDIUM0, блокирующих вопросов0.
Отдельный проверяющий принял реализацию: P1=0/P2=0. Контрольные суммы кода
и журнала повторно совпали с его отчётом перед подготовкой commit.

- [Ревью требований](t078-signup-completed-requirements-review-20261116.md)
- [Ревью реализации и SHA-256](t078-signup-completed-implementation-review-20261116.md)
- [Контрольный список](../checklists/signup-completed-coverage.md)

## Проверки

На неизменённом коде три новых причинных проверки завершились RED: аккаунты
созданы, completed отсутствует. После правки исходный профиль —15PASS.
Расширенный окончательный профиль — **139passed, 1warning**, без skip/error.
Warning: прежний `PytestAssertRewriteWarning` заранее импортированного fixture.

```sh
UV_PROJECT_ENVIRONMENT=/Users/yshishenya/Documents/crisp/apps/server/.venv \
UV_NO_SYNC=1 GRAF_TEST_WORKERS=1 \
/opt/homebrew/bin/bash apps/server/scripts/run_local_postgres_tests.sh \
  --focused \
  tests/contract/test_product_analytics_registration_handoff_contract.py \
  tests/unit/test_registration_measurement.py \
  tests/contract/test_auth_contracts.py \
  tests/contract/test_product_analytics_anonymous_aggregate_contract.py \
  tests/unit/test_public_analytics.py -q
```

PostgreSQL17 — изолированный временный контейнер; runner подтвердил удаление
после проверки. Свободное место перед стендом —163GiB. Существующее окружение
Python использовано без синхронизации зависимостей. Реальных писем, внешнего
OAuth и рабочего сервера проверки не касались.

Итоговый журнал: `/private/tmp/graf-t078-final-profile-20261116.log`.
Collection count139, digest
`67820651cb372008da916c5488ced260e83c664b1887e6308dff3eb4a6ed1e65`.
Pytest69.65с; фаза runner77с. Журнал SHA-256
`2fcd2c7c6332941221a686c2c9fee2a79efcd8c7f5d85577570ebc0caff4a750`.
Ruff четырёх затронутых Python-файлов и `git diff --check` — PASS.

Матрица: три пути; browser-bound/unbound OAuth; новый/existing/replay/link;
кампания/unknown; auth commit failure; L1 off; setup/upsert/commit/ambiguous
measurement commit. Другая DB-сессия видит сохранённый аккаунт до измерения.
Отказ счётчика сохраняет успешный вход, неоднозначная запись не повторяется,
внешняя отмена распространяется. Это причинная матрица, не полный перебор
всех сочетаний next/маршрут/кампания/отказ; пределы указаны в ревью.

## Общая проверка правил

Первый запуск остановился: глобальный Specify1.2.6 не совпал с проектным
lock1.0.7. Во временную отдельную среду установлен настоящий Specify1.0.7
из закреплённого `fe1d00e3ccaf495880aaf90fb0e17679e82f065b`.
Только для вызова `scripts/check_spec_kit_governance.py` его bin добавлен в PATH.
Повторный результат: `spec-kit-governance: OK (bootstrap integrity + GRAF invariants)`.
Lock, проверки и глобальный инструмент не менялись.

`ci-local.sh --plan` — только диагностическая опись частичного покрытия;
следующие ворота governance-fast и release-full. Full/native/CD не запускались:
это не замороженный выпуск. Корневого npm preflight в репозитории нет;
использован предписанный проектом профиль и обязательные проверки GitHub.

## Scoped converge

Сверены9 требований FR-007/010/011/013/018/020/024/057/058, применимые части
SC-002/005,6 решений plan и принципы конституции II/III/IV/VI.
Пропусков missing/partial/contradicts/unrequested в продолжении T078 —0,
CRITICAL/HIGH/MEDIUM/LOW —0. Результат `converged`; новых задач не добавлено,
при convergence tasks.md не менялся. Остальные открытые задачи F273 не
переоценивались. Отдельная последующая запись реализации сохраняет T078 `[ ]`
до обязательных checks точного PR SHA/base и merge.

## Оставшиеся ворота

Локальное доказательство не заменяет GitHub `governance-fast`, `macos-pr`,
`pr-metadata`, общий валидатор, принятую основу и merge. Issue8054 остаётся
открытым до этих доказательств и сверки tracker. Выпуск/рабочая приёмка
измерения — отдельно. Legacy Impact — `untouched`.
