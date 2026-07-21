# Feature 108: canonical local CI receipt

Дата проверки: 2026-07-20
Проверенный master SHA: `da250976a67583c63267ee5d23b6239f35c02c00`

## Команда

```sh
GRAF_TEST_WORKERS=8 bash infra/scripts/ci-local.sh
```

## Результат

- macOS Swift build: pass.
- macOS Swift tests: `581 executed, 0 failures`.
- macOS contract validation: pass.
- PostgreSQL full runner: `1913 passed, 1 skipped`; strict RLS lane:
  `34 passed, 1 skipped`; collection `1949`, digest
  `5af1d6be0f3c121cf60ec198af58d51ba82d8e503ad4ac6541c8408cbcdf50f8`.
- Ruff, Python compile, production Compose config и deployment-evidence scan:
  pass.
- Итог: `ci_local_result=pass`.

Ограничение: встроенная `rls hardening validation boundary` вернула
`rls_validation_result=blocked`, потому что для этой локальной команды нет
live production probe и destructive probe database. Это ожидаемая отдельная
граница production-truth T101; она не переключает runner на SQLite и не
отменяет локальное PostgreSQL-прохождение.
