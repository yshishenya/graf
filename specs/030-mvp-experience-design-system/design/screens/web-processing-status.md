# Web Processing Status

## Purpose

Be useful while a meeting moves from upload/ingest to transcript and notes.

## Header

- Meeting title.
- Source provenance.
- Duration when known.
- Owner/workspace.
- Current status chip.
- Last updated.

## Stage Rail

Stages:

1. Saved locally or uploaded.
2. Uploading.
3. Accepted for processing.
4. Extracting audio.
5. Transcribing.
6. Transcript ready.
7. Notes ready.

Each stage includes:

- State icon.
- Label.
- Timestamp when known.
- Error/degraded marker if relevant.

## Body

While processing:

- Show what is already available.
- Show what is still running.
- Show expected next step without promising timing.
- If partial transcript exists, show read-only partial with `Ещё обрабатываем`.
- If no transcript exists, do not render an empty transcript panel that looks
  broken.

## Actions

- `Обновить`.
- `Сообщить, когда будет готово`.
- `Открыть статус в приложении`.
- `Повторить обработку` when retryable.
- `Удалить` entry with truth copy.

## Required States

- Uploading.
- Uploaded/pending processing.
- Extracting audio.
- Transcribing.
- Transcript ready, notes running.
- Notes ready.
- Degraded.
- Failed.

## Acceptance Evidence

Covered by Figma `V8 06 - Загрузка и обработка в списке`,
`V8 10 - Веб-кабинет: встречи и фильтры`, `V8 11 - Веб-детали встречи и транскрипт`, and
`design/validation-evidence.md`.
