# Web Manual Upload

## Purpose

Let a user upload owned audio or meeting media and immediately see truthful
processing status.

## Layout

- Page or drawer max content width: `760 px`.
- Drop zone minimum: `560 x 180 px`.
- Right-side status panel on large screens.
- On desktop-embedded route, use the same upload content but hide broad web
  admin/navigation.

## Drop Zone

Copy:

- Accepted: audio files and common video/meeting containers with usable audio.
- MVP promise: audio is extracted for transcript and notes.
- Non-promise: full video review is not part of first launch.

Actions:

- `Выбрать медиа`.
- Drag/drop.
- `Отменить`.

## Metadata Form

- Title.
- Meeting date/time.
- Participants optional.
- Workspace.
- Source label: `Uploaded media`.
- Language hint optional.

## Progress Stages

- Validating file.
- Uploading.
- Extracting audio.
- Transcribing.
- Preparing notes.
- Ready.

## Failure States

- Unsupported file.
- File too large.
- Encrypted or corrupt.
- No usable audio.
- Duplicate upload.
- Network failed.
- Processing unavailable.
- Permission/access blocked.

Each failure must say what exists, what failed, and what action is available.

## Actions After Upload Starts

- `Подробнее`.
- `Сообщить, когда будет готово`.
- `Отменить загрузку` before server acceptance.
- `Удалить` entry after acceptance, with truth copy.

## Forbidden

- No direct object-storage credentials or signed URLs in UI.
- No transcript promise before processing produces a transcript.
- No "video review" promise for MVP.

## Acceptance Evidence

Covered by Figma `V8 06 - Загрузка и обработка в списке`,
`V8 10 - Веб-кабинет: встречи и фильтры`, `V8 11 - Веб-детали встречи и транскрипт`, and
`design/validation-evidence.md`.
