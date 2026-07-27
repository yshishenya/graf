# Контракт локального test pipeline

## Команды

```text
infra/scripts/ci-local.sh --fast
infra/scripts/ci-local.sh --full
infra/scripts/ci-local.sh --governance
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/...
```

## Fast

- не требует Docker/PostgreSQL;
- не собирает тесты, отмеченные `requires_postgres`, `governance`,
  `strict_rls` или `spike`;
- выполняет pure unit/static contracts, lint и compile.

## Full

- создаёт disposable PostgreSQL;
- собирает baseline node ids без optional spike tests;
- запускает ordinary phase bounded xdist, затем governance phase bounded xdist;
- запускает strict RLS phase serial;
- сравнивает union фаз с baseline;
- в любом исходе удаляет контейнер и worker databases.

## Failure contract

Runner обязан завершиться ненулевым кодом, если:

- Docker недоступен;
- URL не loopback/disposable;
- схема не мигрирует до head;
- фаза потеряла node id;
- test phase упала;
- cleanup не подтверждён.

## Owner audio default

- При отсутствии сохранённой policy owner готовой встречи получает доступное
  audio download state и server-mediated download.
- Shared/team viewer без явной policy получает отказ; saved policy сохраняет
  своё явное значение.

## Evidence contract

Разрешены только `mode`, `phase`, `duration_seconds`, `collection_count`,
`digest`, `passed/failed/skipped/xfail` и cleanup status. Запрещены URL, пароль,
полные env dumps, test payloads, audio и transcript.
