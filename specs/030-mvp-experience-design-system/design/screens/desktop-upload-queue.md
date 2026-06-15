# Desktop Upload Queue

## Purpose

Tell the owner exactly where a stopped recording is: local, queued, uploading,
accepted by server, processing, failed, or blocked.

## Layout

- Native capture strip remains at top.
- Queue/status is not a top-level sidebar destination. It appears as a row
  state, detail state, or compact queue panel inside `/desktop/meetings`.
- Header: meeting title, source, saved time, current status.
- Stage rail:
  `Сохранено на этом Mac -> В очереди -> Загружается -> Принято для обработки -> Расшифровка -> Готово`.
- Details column:
  - Local package retained until server confirmation.
  - Upload attempts and next retry.
  - Accepted bytes/tracks when known.
  - Processing stage once 2brain Rec accepted the artifact.

## Row-Level Queue List

Each queued item shows:

- Title or generated timestamp title.
- Source: `Запись на этом Mac`.
- Duration.
- Local saved status.
- Upload progress or retry countdown.
- Primary action: `Подробнее`, `Повторить`, or `Исправить`.
- Secondary: `Пауза`, `Диагностика`, `Открыть в вебе`.

## Required States

- `local_recording_saved`
- `local_only`
- `queued`
- `uploading`
- `uploaded`
- `transcription`
- `transcript_ready`
- `failed`
- `blocked`

## Actions

- `Повторить`: allowed for retryable upload failures.
- `Пауза`: keeps local package and marks user-paused.
- `Открыть в вебе`: opens browser meeting/status when server id exists.
- `Диагностика`: platform support surface.

Debug/internal only:

- `Открыть локальный пакет`.

## Forbidden

- Do not collapse "only on this Mac" and uploaded into one state.
- Do not purge local artifacts while truth is non-terminal.
- Do not expose raw local paths in normal UI.
- Do not show transcript chrome while transcription has not produced output.

## Acceptance Evidence

Covered by Figma `V8 03 - Рабочее пространство встреч`,
`V8 06 - Загрузка и обработка в списке`, `V8 10 - Web meetings list and
filters`, and `design/validation-evidence.md`.
