# US3: честная деградация и повторная синхронизация

Сервер сначала сохраняет принятый metadata-only отчёт. Ошибка GitHub даёт
`202 pending_sync` и `CUST-*`; повторная попытка отправляет только номер
обращения. macOS различает `sent`, `pending_sync`, rejected и sign-in-required,
а clipboard fallback содержит только безопасную краткую сводку.

## Проверка

- Server intake/contract/redaction/readiness quickstart: **45 passed, 2
  warnings**.
- XCTest: `DesktopUploadQueueV5Tests` — **59**, `CaptureControlV5Tests` —
  **37**, `EmbeddedCabinetSupportIncidentBridgeTests` — **2**, все без ошибок.
- Интеграционные тесты покрывают pending-to-sync переход по одному
  correlation number, idempotency, rate limit и отсутствие повторного GitHub
  Issue.

В evidence нет payload, текста встреч, cookies, токенов или реальных ссылок.
