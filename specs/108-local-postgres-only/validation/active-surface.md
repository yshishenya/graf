# Feature 108: active surface receipt

Дата проверки: 2026-07-20
Проверенный master SHA: `da250976a67583c63267ee5d23b6239f35c02c00`

## Regression guard

Команда:

```sh
rg -n -i 'sqlite|aiosqlite|sqlite3|sqlite\\+' \
  apps/server infra/scripts infra/docker-compose.dev.yml
```

Результат: `sqlite_match_count=0` в активных server source, dependencies,
tests, local scripts и development Compose. Контрактный тест
`test_active_server_paths_do_not_restore_retired_embedded_database_support`
также прошёл.

Исторические specs, changelog, migration/evidence notes и macOS TCC probe
намеренно не входят в guard: они описывают прошлое состояние и не являются
рабочим способом запуска server или тестов.
