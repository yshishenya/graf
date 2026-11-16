# T112 — принятый пробник, отказ до сбора тестов

17.11.2026. Автор `/root`; существующая F273/T112/#7698, T113/#7804,
полоса `high-risk-product`. Исходник
`ef9f5047ac5ac6c3ba2381e05b985b5071f3875c`. Этот checkpoint содержит
только отчёты; runtime, исходные тесты, probe и selfcheck не менялись.

## Независимое ревью

Получен FINAL и целиком прочитан
[отчёт реализации](t112-early-proof-implementation-review-20261117.md),
SHA-256 `55cda55ea23f3266365aed7d12541b356be096425d13909c58ac09c74064c4c5`:
**SCOPED IMPLEMENTATION PASS, P1=0/P2=0**. Он разрешает один диагностический
GET/PostgreSQL с прежними source pins, после сверки временной копии.
Reviewer независимо сверил18 входов и124/0 вопросов; отметки не менялись.
Это реальное полученное ревью, в отличие от прежнего только файла поручения.

Принятый probe SHA-256:
`e3c5f0d5dcec7c2f66d86ad9ec189b6689a233f12bdf27884b214316fa5030d8`.
Selfcheck SHA-256:
`c73fa8b646f0d028e9f64d3b027018e4d8e0dee2203ac5c146b0211e4ddf8608`.
Прежние15 synthetic не повторялись и не объявлены реальным GET.

## Реальная попытка и точный предел

Перед стендом доступно100592680960байт на Mac, выше80ГБ. Проверены HEAD,
SHA ревью/probe и все шесть PINS; временная копия в `apps/server` создана
эксклюзивно и сверена побайтово. Исполнена команда:

```sh
UV_PROJECT_ENVIRONMENT=/Users/yshishenya/Documents/crisp/apps/server/.venv \
UV_NO_SYNC=1 GRAF_TEST_WORKERS=1 \
/opt/homebrew/bin/bash apps/server/scripts/run_local_postgres_tests.sh \
  --focused test_t112_early_proof_probe_20261117.py::test_early_proof_single_get \
  -q -s --tb=short
```

**EXIT4, 0.423881s всего wrapper.** Pytest отказал до collection:
`unrecognized arguments: --graf-collection-file`.
Runner сообщил `postgres_test_cleanup=container_not_started`.
База не запущена, GET/POST/M1 не выполнялись, наблюдений0 означает отсутствие
исполнения пробника, а не пустую проекцию или результат приложения.
Временная копия снята в `finally` после повторной сверки её SHA.
Здесь нет `isolated_container_removed`: контейнер не создавался.

Raw log вне Git:
`/private/tmp/graf-t112-early-proof-native-20261117.log`, SHA-256
`3918cccb3072b4394a9387c33450b394e8ca8c0076f471c16245c5ee619d1d4c`.
Receipt с тем же basename.json содержит exact command, hashes, exit,
elapsed, observations=[] и temporary_copy_removed=true.
Лог прочитан: это ошибка CLI и предупреждение про унаследованный VIRTUAL_ENV,
не failure HTML/proof. В Git raw log и содержимое окружения не добавлены.

## Причина загрузки и следующий допуск

Статически установлено: временный файл в `apps/server` не имеет
`tests/conftest.py` среди родителей; `apps/server/conftest.py` отсутствует.
Штатный `tests/conftest.py` подключает `tests.fixtures.test_resources`,
который регистрирует `--graf-collection-file`, и определяет
`postgres_seeded_database_url`. Runner перед первой collection явно не
загружает этот plugin; явная загрузка в run_phase наступила бы позднее.
Это ошибка выбранного способа запуска, не отказ приложения/БД/Docker.

Минимальное предложение — сохранить исходный probe и его root, явно добавить
`-p tests.conftest` к focused invocation. До нового статического PASS именно
этого изменения загрузки повтор не назначен. Поручение подготовлено в
`/private/tmp/graf-t112-early-proof-invocation-review-request-20261117.txt`;
**оно пока только файл, не доставка и не проверенное ожидание**.
Нового FINAL по invocation ещё нет. Не переносить прежний допуск на другой
способ загрузки молча. V4/87/POST/M1 не запускать.

## Сохраняющиеся границы

Настоящий period остаётся `yield None`; почта ГРАФ — Postal. Неизвестная
причина прежних0proofs/repeated HOLD не объяснена этой ошибкой collection.
T112/T113/T098/restore/readiness/T0 и коммерческий результат открыты.
Новый недельный отчёт Метрики здесь не прочитан. Контент/вёрстка, production,
службы, настройки аналитики/IP, публикации и внешние события не менялись.
Свежий `get_goal` вернул active; цель не завершена.
