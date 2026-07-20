# US1: авторизованный приём отчёта

Результат: отчёт остаётся metadata-only, получает серверный номер `CUST-*` до
обращения к GitHub, а embedded cabinet выполняет same-origin запрос с
собственной cookie-сессией и CSRF-контекстом. Нативный upload-клиент больше не
передаёт support-report через ручные заголовки или скопированную web-сессию.

## Проверка

- `PYTHONPATH=src bash scripts/run_local_postgres_tests.sh -q ...` по командам
  из `quickstart.md`: **45 passed, 2 warnings**.
- После финального упрощения сервиса повторен server-поднабор intake/contract/
  Issue body: **31 passed, 2 warnings**.
- Канонический macOS XCTest: **577 tests, 0 failures**; затронутые наборы
  `DesktopUploadClientTests` — 38, `DesktopUploadQueueV5Tests` — 59,
  `EmbeddedCabinetSupportIncidentBridgeTests` — 6, все без ошибок. Bridge
  проверен на объектный результат WebKit `callAsyncJavaScript` и на прежний
  строковый JSON-результат.

Проверки используют синтетические metadata-only данные и fake GitHub client;
живые cookie, CSRF-токены, аудио, расшифровки и private URL в evidence не
попадают.
