# Checklist проверки реализации

- [x] Все DB-зависимые тесты используют disposable PostgreSQL boundary.
- [x] Fast lane проходит без Docker.
- [x] Focused audio/export tests проходят PostgreSQL.
- [x] Clean migration tests проходят в отдельной пустой БД.
- [x] Worker databases различаются и удаляются.
- [x] Full phase union равен baseline collection.
- [x] RLS lane не skip-ается при полном runner.
- [x] Runner cleanup подтверждён на pass/failure/SIGINT.
- [x] Ruff, compile, compose и RLS boundary проходят.
- [x] В evidence нет URL, секретов, аудио или transcript.
- [x] Owner без saved policy скачивает готовое аудио, shared viewer без policy получает отказ.
- [x] Full lane запускает непересекающиеся ordinary, governance и strict RLS phases без spike tests.
- [x] Удалены test-only legacy placeholders, а HTTP/API и pure worker tests размещены в верных слоях.
