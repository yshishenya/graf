# US2: подробный private Issue

Результат: private Issue строится на сервере из уже отредактированного отчёта и
содержит номер `CUST-*`, проблему, категорию сбоя, состояние, версию, timeline,
fingerprint, безопасные identity-факты и статус синхронизации. Секреты,
meeting content, raw audio и локальные пути в тело Issue не попадают.

## Проверка

- Focused server quickstart: **45 passed, 2 warnings**.
- Contract drift check `test_runtime_openapi_matches_committed_contract`:
  **1 passed**; committed OpenAPI теперь совпадает с runtime-маршрутами,
  включая `POST .../sync` без request body и `202 pending_sync`.
- Канонический `ContractValidation`: **PASS**.
- Internal readiness сообщает только bounded state интеграции (`configured`,
  `not_configured` или `configuration_invalid`) и не делает публичный GitHub
  вызов.

Все значения в проверках синтетические; реальные issue IDs, URL и секреты не
сохранялись.
