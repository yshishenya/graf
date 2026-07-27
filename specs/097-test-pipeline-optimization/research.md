# Исследование

## Наблюдения

- До этой оптимизации server tests в `conftest.py` и нескольких ручных
  app/migration fixtures создавали отдельные локальные базы.
- Старый `client` создавал локальный engine и вызывал
  `Base.metadata.create_all` для каждого теста.
- Runtime уже использует `asyncpg`, а dev Compose уже содержит PostgreSQL 17.
- RLS proof suite уже принимает `RLS_TEST_DATABASE_URL`; в полном runner отсутствие
  boundary теперь является ошибкой, а не тихим skip.
- macOS unit suite проходит быстро относительно server suite; hardware/spike
  проверки требуют отдельного lane.
- Audit выявил расхождение между `can_download=True` у owner и transient
  default policy `audio_download=disabled`: green tests включали policy вручную
  и не покрывали реальный owner journey.
- `ingest/access_policy.py` имел только test caller и проверял уже неактуальные
  placeholders; historical evidence оставалось в integration directory, хотя
  относится к governance lane.

## Варианты

| Вариант | Решение | Причина |
|---|---|---|
| локальная база для всех тестов | отклонён | быстро, но недостоверно |
| одна постоянная dev database | отклонён | загрязнение данных и риск production target |
| PostgreSQL + `create_all` на каждый тест | отклонён | медленно и не покрывает migration-managed objects |
| disposable PostgreSQL + worker DB + reset | выбран | production-like dialect, isolation и повторяемая скорость |
| внешняя shared CI database | отклонён | collision, credential/data boundary и сложнее локальный запуск |

## Открытые риски

- Migration tests могут менять роли/политики и должны идти в clean/strict lane.
- xdist нельзя включать до подтверждения collection union и worker isolation.
- Cleanup должен работать при SIGINT; runner не должен оставлять container.
- Owner default не должен расширять доступ team/shared viewer: для transient
  audio policy выбран существующий `owner_only`, а не общий `allowed`.

## Измерение worker count

На текущем checkout полный PostgreSQL lane дал baseline и phase union: 1 246
тестов, digest `2ea0af62323a2fcd5017502e2dce7fe7d031ee68dc62d80e9afd652080d36e17`.
Обычная фаза на 8 workers заняла около 85 секунд; строгая RLS-фаза остаётся
последовательной и заняла около 3 секунд. Поэтому 8 workers выбран default, а
`GRAF_TEST_WORKERS` оставлен явным ограничителем для машин с меньшим числом
CPU/памяти.
