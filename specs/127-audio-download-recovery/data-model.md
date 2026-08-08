# Data Model: Восстановление скачивания аудио

Новых постоянных сущностей и миграций нет.

## Существующие сущности и состояния

- `Audio playback artifact`: существующий stored M4A, доступный только через server-mediated route после policy/lifecycle checks.
- `Audio download availability`: существующее вычисленное состояние `available`/denied/unavailable; источник и значения не меняются.
- `Menu interaction`: transient DOM state `open` → стандартное действие ссылки → `closed`; отложенное закрытие влияет только на порядок событий.
- `Save panel`: transient macOS state, управляемый существующим `WKDownloadDelegate`; cancel не меняет server state и допускает повтор.

Нет новых полей, API, storage URL, retention/deletion behavior или диагностических payloads.
