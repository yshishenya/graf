# Data Model: Надёжный RLS release gate

Изменений в production schema и пользовательских данных нет. Ниже описаны
только ephemeral сущности validation run, чтобы зафиксировать границы cleanup.

## Release gate run

- `exact_commit`: commit, для которого получено evidence.
- `mode`: `fast` или `full`.
- `stages`: упорядоченные проверки runner-а.
- `result`: `pass` или `blocked`/`failed`.

## Disposable RLS database

- `name`: bounded name с префиксом `twobrain_rec_rls_`.
- `host`: loopback-only адрес локального PostgreSQL.
- `owner_url`: runtime-only URL; пароль не является evidence и не сохраняется.
- `lifecycle`: create → migrate/probe → drop, включая failure cleanup.
- `production_exclusion`: `twobrain_rec` запрещена для destructive probe.

## Probe role

- `name`: временная роль RLS probe, если она создаётся скриптом.
- `privileges`: bounded non-superuser role с `row_security=on`.
- `lifecycle`: create or validate → direct probes → drop.

## Relationships

Один release gate run может владеть одной disposable базой и одной временной
probe role. Ни одна из этих сущностей не является частью production schema,
release receipt или committed evidence.
