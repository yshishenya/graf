# UI Contract: Native Capture Surface

## Ownership

The native macOS surface is authoritative for recording readiness, permissions, Start, Pause/Resume, Stop, local artifact truth, and immediate recovery. Embedded server content cannot replace, hide, delay, or contradict it.

## Compact Rail

Width remains 52 pt. Controls use at least a 30×30 pt visual/hit region inside the rail and expose Russian accessibility names/help.

Top to bottom:

1. Concise capture readiness/attention state that is not color-only.
2. Direct capture action/state.
3. Local-custody attention badge only when owner awareness/action is required.
4. Flexible space.
5. Inspector expand/collapse control.

Capture action:

| State | Rail action | Visual semantics |
|---|---|---|
| Ready | `Начать запись` | Existing accent, record symbol, not red failure styling. |
| Starting/stopping | Disabled transition state | Progress/status label; no duplicate command. |
| Recording | `Стоп` | Destructive red with stop symbol. |
| Paused | `Стоп` | Stop remains direct; Resume remains in titlebar/expanded controls. |
| Permission/action blocker | Expand/open recovery | Warning symbol plus explicit accessible label. |

## Titlebar HUD

During every state for which the capture session can still be stopped, the native titlebar HUD remains visible with:

- `Запись аудио` or the existing truthful capture-mode title;
- elapsed time when available;
- Pause or Resume when applicable;
- one-action `Стоп`.

The HUD is independent of inspector disclosure and WebView health.

## Expanded Panel

Target width is 304–312 pt. Header is `Запись`; remove the duplicate `Локальное управление` subtitle. Settings remains a secondary icon action.

Order:

1. Current capture status and primary action.
2. Permission/blocker or detected-meeting prompt only when present.
3. Concise auto-detection mode with a settings affordance when relevant.
4. Recording parameters disclosure for microphone choice only when the user asks or recovery is required.
5. Local custody/recovery item only when it affects a user result.
6. Live input meters only during active capture.

The panel does not auto-expand merely because recording starts. It can open automatically only for a stable actionable problem; transient technical warnings remain logged/diagnostic unless the user must act.

## User-facing Copy

| Situation | Status | Primary action / detail |
|---|---|---|
| Idle and eligible | `Готово к записи` | `Начать запись` |
| Permission missing | `Нужно разрешение` | `Открыть настройки` and affected capability |
| Meeting detected | `Встреча обнаружена` | Existing ask/start choice without telemetry |
| Starting | `Начинаем запись…` | none |
| Active | `Идёт запись` | `Стоп` |
| Paused | `Запись на паузе` | `Продолжить`; Stop remains visible |
| Finalizing | `Сохраняем запись…` | none |
| Local-only safe copy | `Сохранено на Mac` | `Повторим отправку автоматически` when true |
| Recoverable failure | `Нужна помощь` | one specific recovery action |
| Support-eligible failure | same truthful failure | secondary `Связаться с поддержкой` |

Auto-detection examples: `Автоопределение: спрашивать`, `Автоопределение: включено`, or `Автоопределение выключено`. Do not include telemetry counts, registry version/source, candidate IDs, or internal policy keys.

## Hidden From Ordinary UI

- Diagnostic/telemetry counters and IDs.
- Registry source/version.
- Apple voice-processing and WebRTC implementation names.
- Local filesystem paths.
- Generic `Отправить отчет` and `Скопировать отчет` buttons.
- Report contents.
- Idle meters.
- Permanent `Доверие записи` and `Диагностика` cards.

The underlying metadata-only diagnostics, redaction, support request, and evidence services remain available to internal/support flows.

## Accessibility And Failure Rules

- Rail controls and inspector toggle have distinct names, roles, values/states, and help.
- The status is never conveyed by color alone.
- Starting, recording, paused, stopping, saved, and failed are distinguishable in text.
- A support failure cannot hide local custody truth or Stop.
- Focus does not jump merely because recording starts; if an actionable problem opens the panel, focus remains on the initiating control unless the user must immediately resolve a modal permission boundary.
