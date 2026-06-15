# Desktop Tray Status

## Purpose

Compact menu-bar controller for current truth and one safe primary action.

## Size

- Target: `360 x 520`.
- Minimum useful height: `420`.
- No broad cabinet/admin content.

## Sections

Header:

- Current state label.
- Compact sync/session chip: `Готово`, `Нет связи`, `Войдите снова`, or
  `Правила устарели`.
- Last sync as short relative time.

Active recording section:

- Visible only while recording.
- Timer.
- Source labels `Микрофон` and `Система`.
- Primary `Остановить` button.

Latest meeting section:

- Title or timestamp.
- Status: saved, uploading, transcribing, ready, failed, or needs speakers.
- Primary action: `Открыть`, `Подробнее`, `Повторить`, or `Исправить`.

Quick actions:

- `Открыть приложение`.
- `Загрузить медиа`.
- `Повторить загрузку` when relevant.
- `Открыть веб-кабинет`.

Footer:

- Account/workspace in one compact line.
- `Диагностика` secondary.

## Required States

- Idle ready.
- Active recording.
- Saving locally.
- Upload queued.
- Upload failed.
- Transcribing.
- Ready.
- Sync unavailable with trusted policy.
- User signed out or session expired.

## Forbidden

- Tray cannot start hidden recording.
- Tray cannot hide active recording.
- Tray cannot show browser-only admin surfaces.
- `Остановить` must be visible while active, not behind overflow.

## Acceptance Evidence

Covered by Figma `V8 05 - Активная запись в меню и окне`,
`V8 06 - Загрузка и обработка в списке`, `V8 14 - Правила интерфейса и QA`, and
`design/validation-evidence.md`.
