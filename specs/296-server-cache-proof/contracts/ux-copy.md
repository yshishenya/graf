# Contract: UX copy and accessibility

**Used by**: manual cleanup action, confirmation, ineligible reasons, automatic eviction status/toggle, VoiceOver.

## Manual cleanup

- Action title: «Освободить место»
- Confirmation title: «Удалить локальную копию транскрипции?»
- Confirmation body: «Будет удалён только файл транскрипции этой записи. Аудио для прослушивания и описание записи останутся на Mac. Встреча на сервере не удалится.»
- Space line: «Освободится: {size}.»
- Confirm button: «Освободить {size}»
- Cancel button: «Отмена»
- Success: «Локальная копия транскрипции удалена. Аудио для прослушивания осталось.»
- No-op: «Эта запись уже очищена.»
- Unexpected missing: «Файл уже отсутствует. Проверьте запись перед повторной очисткой.»

## Ineligible reasons (user copy)

| Code | Copy |
|---|---|
| `proof_missing` | «Серверная копия ещё не подтверждена. Запись оставлена на Mac.» |
| `proof_stale` | «Данные о серверной копии устарели. Повторите проверку позже.» |
| `revision_mismatch` | «Серверная копия относится к другой версии записи. Запись оставлена на Mac.» |
| `playback_not_available` | «Сервер пока не может воспроизвести запись. Запись оставлена на Mac.» |
| `playback_not_verified` | «Сервер не подтвердил сохранность аудио. Запись оставлена на Mac.» |
| `archive_audio_false` | «Сервер не сохранил аудио для этой записи. Запись оставлена на Mac.» |
| `retention_unsafe` | «Срок хранения на сервере скоро истечёт. Запись оставлена на Mac.» |
| `deletion_operation_open` | «Встреча удаляется. Дождитесь завершения удаления.» |
| `account_scope_mismatch` | «Запись относится к другому аккаунту. Переключитесь на нужный аккаунт.» |
| `local_artifacts_missing` | «Локальные файлы записи неполные. Очистка недоступна.» |
| `local_integrity_unverified` | «Локальные файлы не прошли проверку. Очистка недоступна.» |
| `dependency_unavailable` | «Не удалось проверить серверную копию. Попробуйте позже.» |
| default | «Очистка сейчас недоступна. Запись оставлена на Mac.» |

## Automatic eviction

- Section title: «Локальный кэш»
- Status: «Занято {used} из {budget}.»
- Explanation: «GRAF может автоматически удалять только локальные файлы транскрипции подтверждённых записей. Аудио для прослушивания и описание записи остаются.»
- Toggle: «Автоматически освобождать место»
- Toggle detail: «Удаляются только файлы транскрипции записей, которые уже доступны на сервере.»
- Disabled state: «Автоматическая очистка выключена. Новые файлы не удаляются.»
- Operator override: «Автоматическая очистка временно отключена администратором.»
- Eviction result: «Освобождено {size}. Аудио для прослушивания осталось.»
- Warning: «Локальный кэш заполняется. Старые подтверждённые файлы транскрипции будут очищены автоматически.»

## VoiceOver labels

- Cleanup action: «Освободить место. Будет удалён только локальный файл транскрипции. Аудио и описание записи останутся.»
- Confirmation: «Подтвердите удаление локальной копии транскрипции. Серверная встреча не удаляется.»
- Reason row: full user copy from the table.
- Status: «Локальный кэш: занято {used} из {budget}.»
- Toggle: «Автоматически освобождать место. Удаляются только файлы транскрипции подтверждённых записей.»
- Disabled/operator override: full copy above.

## Rules

- No internal reason codes, raw errors, paths, meeting titles, transcript text, tokens or credentials in user-visible copy.
- Normal automatic cleanup is informational, not an error.
- The confirmation must never imply server deletion.
