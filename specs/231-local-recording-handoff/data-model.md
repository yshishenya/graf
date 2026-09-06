# Data Model: локальная запись и server handoff

## LocalRecordingRow

- `id`: opaque queue item ID, используется только native bridge.
- `meetingId`: server meeting ID, если уже подтверждён.
- `title`, `startedAt`: безопасные display metadata.
- `durationSeconds`: фактически сохранённая длительность.
- `sessionDurationSeconds`: полный wall-clock интервал, только для partial copy.
- `status`: русская безопасная подпись состояния.
- `canOpen`, `canSend`, `canDelete`: разрешённые действия, вычисленные native-side.
- `uploadComplete`: подтверждённое состояние очереди.

WebView не получает локальный путь. Native заново находит item по `id`, проверяет разрешение и существование файла.

## DesktopUploadQueueItem lifecycle

```text
saving → queued → uploading → uploaded
                    ↘ retrying
capture failure → blocked/local_resource → terminalDeleted
```

- `schema_incompatibility` допустима только для действительно неподдерживаемой схемы.
- Для валидного текущего v5 capture failure хранится `local_resource` + точный `captureFailureCode`.
- Existing non-terminal item при refresh получает исправленную локальную категорию.
- `uploaded` с meeting ID не скрывает локальную строку, пока server row фактически не появилась.

## Duration rules

- `savedDuration = max(media duration, playback duration)` для доступных текущих v5 artifacts.
- `sessionDuration = stoppedAt - startedAt`.
- Если `savedDuration < sessionDuration` и package не uploadable, UI показывает `Сохранено X из Y`.
- Для legacy или отсутствующего readable artifact используется bounded wall-clock fallback.

## Deletion invariants

- Target directory MUST be a descendant of configured recordings root after standardization and symlink resolution.
- Удаляется только item из точного allowlist пользователя.
- Успешный server meeting ID `876ca9ec-d065-43b8-a36a-e2020dc41151` не является target.
- После удаления item остаётся terminal tombstone и не восстанавливается scanner-ом.
