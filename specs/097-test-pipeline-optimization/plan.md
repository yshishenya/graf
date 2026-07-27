# План: быстрый и достоверный test pipeline

## Risk / validation lane

High-risk test-infrastructure and artifact-egress change: затрагивает
PostgreSQL, Alembic, RLS, Docker, canonical local CI и owner-only audio
download. Deployment не выполняется, но полный Spec Kit flow обязателен.

## Решения

1. **Источник истины** — текущая ветка `096-product-analytics-provider-rollout`;
   старый срез 110 используется только как reference, потому что его состав
   тестов содержит уже удалённые legacy-файлы.
2. **Database boundary** — runner поднимает новый `postgres:17-alpine` в
   disposable контейнере, публикует случайный loopback-порт и создаёт базы с
   префиксом `twobrain_rec_test_`.
3. **Обычная изоляция** — отдельная база на xdist worker, Alembic `head` один
   раз на worker, затем bounded truncate + seed на каждый DB-dependent test.
4. **Чистая схема** — отдельная временная база на тест; migration tests сами
   прогоняют Alembic и затем удаляют базу.
5. **Декомпозиция CI** — fast без БД; full через runner; strict RLS serial;
   governance/spike — explicit lane.
6. **Owner default** — отсутствие сохранённой artifact policy означает
   `audio_download=owner_only`; остальные artifact defaults остаются
   `disabled`, а сохранённая policy имеет приоритет.
7. **Фазы full lane** — ordinary runtime/static checks, governance/evidence и
   strict RLS идут разными непересекающимися фазами; baseline не включает
   optional spike tests.

## Фазы

### Фаза 1 — тесты контракта и инструменты

- добавить markers и contract tests для safe URL/database names, lane flags и
  collection accounting;
- добавить `pytest-xdist` как dev-only dependency;
- описать команды и evidence.

### Фаза 2 — PostgreSQL fixture

- реализовать безопасное создание/удаление баз;
- применить миграции к worker database;
- заменить per-test `create_all` и повторную инициализацию данных на truncate/seed;
- перевести clean-schema/migration callers на чистую PostgreSQL database.

### Фаза 3 — lanes и runner

- добавить disposable runner с retry, cleanup и metadata-only output;
- включить bounded xdist для ordinary tests;
- запускать strict RLS serial после baseline union;
- изменить `infra/scripts/ci-local.sh` на `--fast`, `--full`, `--governance`.

### Фаза 4 — очистка и оптимизация

- завершить перевод оставшихся database fixtures на общий test boundary;
- отметить governance/readiness tests и отделить их от fast lane;
- оставить hardware/spike suites opt-in;
- не удалять актуальные audio/export, RLS и deletion assertions.

### Фаза 5 — validation

- targeted audio/download;
- fast lane;
- PostgreSQL focused и full lane;
- lint, compile, lock, compose, RLS boundary и canonical CI;
- сравнить collection/outcome counts и сохранить только безопасные aggregate
  evidence.

### Фаза 6 — audit remediation

- добавить owner/default и shared/denied audio regressions через реальный API;
- удалить test-only access placeholders без production callers;
- перенести очевидные HTTP tests из `unit` в `integration` и pure worker
  payload checks в `unit`;
- отделить historical evidence governance marker и заменить stale current-app
  assertion;
- подтвердить deterministic phase order и collection union.

## Constitution / product gates

- PostgreSQL target только loopback/disposable; production database запрещена.
- RLS assertions остаются обязательными.
- Evidence не содержит meeting content, audio, transcript, credentials или
  signed URLs.
- No deploy: это изменение release/CI confidence surface.
- Default owner audio download сохраняет server-mediated egress, audit и
  явные запреты для остальных viewers.
