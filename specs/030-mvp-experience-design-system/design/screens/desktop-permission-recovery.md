# Desktop Permission Recovery

## Purpose

Recover capture without turning first launch into a driver diagnostics console.

## Layout

- Capture strip shows blocked status and exact missing permission.
- Main surface is a focused checklist, max width `720 px`.
- Diagnostics are behind a secondary disclosure.

Checklist rows:

1. Microphone permission.
2. Screen/system audio permission.
3. Local buffer/disk health.
4. Sync/session and workspace policy.

Each row includes:

- Icon and state.
- One-sentence reason.
- Primary action.
- Secondary `Зачем это нужно` disclosure.

## Required States

- Microphone permission missing.
- System audio/screen permission missing.
- Permission prompt denied.
- Sync unavailable with previously trusted policy.
- Workspace policy blocks recording.
- Local buffer unhealthy.
- Recovery complete.

## Actions

- `Открыть настройки macOS`.
- `Проверить снова`.
- `Записать позже` when the recovery path cannot safely continue now.
- `Диагностика`.
- `Связаться с поддержкой` handoff with redacted support bundle only.

## Forbidden

- No driver install/repair language in MVP first-run unless a future advanced
  routing feature explicitly enables it.
- No recording start while permissions are ambiguous.
- No raw local log paths in normal copy.

## Acceptance Evidence

Covered by Figma `V8 02 - Первый запуск и разрешения macOS`, `V8 09 - Settings
recording and theme`, and `design/validation-evidence.md`.
