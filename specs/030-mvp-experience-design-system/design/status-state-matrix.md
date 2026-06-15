# Cross-Surface Status State Matrix

| Status | Meaning | RU label | EN label | Primary action | Forbidden claim |
|---|---|---|---|---|---|
| local_recording_saved | Local package saved after stop | Сохранено на этом Mac | Saved on this Mac | Подробнее | Must not imply upload |
| local_only | Meeting exists only on this Mac | Только на этом Mac | On this Mac only | Загрузить | Must not imply backup |
| queued | Waiting for upload | В очереди | Queued | Ждать или повторить | Must not imply upload complete |
| uploading | Transfer in progress | Загружается | Uploading | Показать прогресс | Must not imply transcription |
| uploaded | 2brain Rec accepted artifacts | Принято для обработки | Accepted for processing | Подробнее | Must not imply transcript ready |
| audio_extraction | Extracting audio | Извлекаем аудио | Extracting audio | Ждать | Must not imply transcript |
| transcription | Transcription running | Идёт расшифровка | Transcribing | Подробнее | Must not show blank transcript as failure |
| transcript_ready | Transcript available | Транскрипт готов | Transcript ready | Открыть | Must not imply notes ready |
| notes_ready | Summary/actions available | Итоги готовы | Outcomes ready | Открыть обзор | Must show provenance |
| partial_degraded | Some outputs failed | Частично готово | Partially ready | Открыть доступное | Must not hide missing outputs |
| failed | Cannot continue automatically | Требуется действие | Needs attention | Исправить | Must not delete local artifacts silently |
| deleted | Deleted where controlled | Удалено в 2brain Rec | Deleted in 2brain Rec | Отчёт об удалении | Must not promise universal erasure |
| access_denied | Viewer cannot access | Нет доступа | Access denied | Войти или запросить | Must not leak meeting content |
| signed_out | No active server session | Войдите для синхронизации | Sign in to sync | Войти | Must not block local recording if policy allows |
| server_offline | Sync endpoint unavailable | Нет связи | Sync unavailable | Повторить синхронизацию | Must not imply upload or backup |
| policy_stale | Local app needs fresh policy | Правила устарели | Policy needs refresh | Обновить правила | Must not start recording if policy blocks it |
| permission_blocked | macOS permission missing | Нужно разрешение macOS | Permission needed | Открыть настройки macOS | Must not suggest sync can fix local permission |
| no_usable_audio | Uploaded file has no usable audio | Нет пригодного аудио | No usable audio | Загрузить другой файл | Must not start transcription |
| unsupported_media | File cannot be processed | Формат не поддерживается | Unsupported file | Загрузить другой файл | Must not silently discard file |
| speaker_assignment_loading | Speaker data is loading | Загружаем спикеров | Loading speakers | Ждать | Must not show stale local speaker truth as current |
| speaker_assignment_saving | Speaker edits are being saved | Сохраняем спикеров | Saving speakers | Ждать | Must not imply save is complete |
| speaker_assignment_saved | Speaker edits accepted | Спикеры сохранены | Speakers saved | Вернуться к обзору | Must not imply app-local diarization changed independently |
| speaker_assignment_conflict | Changed segments or conflict detected | Конфликт в спикерах | Speaker conflict | Проверить изменения | Must not silently overwrite segments |
| speaker_assignment_failed | Speaker edits failed | Не удалось сохранить | Speaker save failed | Повторить | Must not lose unsaved edits |

## Surface Rules

- Desktop and web may render differently but must use the same meaning.
- Upload success, transcript readiness, and notes readiness are separate.
- Deletion and access states must avoid leaking private content.
- Source/track provenance is shown whenever meeting quality or review context could be misunderstood.
- AI scopes are status/security scopes too: `this_meeting` can use the open
  meeting, while `all_meetings` requires a separate browser/search privacy
  decision.
- Regeneration, delete, access widening, export/download, and support bundle
  creation require explicit confirmation or browser handoff according to route
  visibility rules.
- Speaker assignment statuses are server-owned and shared by browser and
  embedded desktop. Native shells may host and display these states but must not
  create a separate local speaker state machine.
