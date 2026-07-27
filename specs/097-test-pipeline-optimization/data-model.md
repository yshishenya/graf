# Модель test pipeline

| Объект | Жизненный цикл | Граница |
|---|---|---|
| `run_prefix` | один runner invocation | regex `twobrain_rec_test_[a-z0-9_]+` |
| admin URL | session | loopback, database `postgres`, synthetic credential |
| worker DB | session per xdist worker | `${run_prefix}_${worker_id}` |
| clean DB | one migration test | `${run_prefix}_clean_*`, без seeded schema |
| schema | once per worker | Alembic `head` |
| test data | function | bounded truncate + deterministic seed |
| phase manifest | one full run | node ids/count/digest only |

## Invariants

- Ни один test URL не может указывать live database name.
- Worker DB names не пересекаются между runner invocations.
- `alembic_version` не очищается обычным reset.
- Clean DB не используется как application seeded DB.
- Cleanup удаляет только созданные run-prefixed resources.
