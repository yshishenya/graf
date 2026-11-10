# Interface Contract: Сквозное укрепление интерфейса GRAF

**Feature**: `293-interface-hardening` | **Date**: 2026-11-10

## 1. Capture status

1. Every native surface uses the same `CaptureStatusPresentation` for a given `CaptureSessionState`.
2. `starting`, `active`, `paused`, `degraded`, `stopping` expose Stop. `stopping` disables it.
3. `paused` exposes Resume and Stop.
4. `failed` never renders as success or “Готово к записи”.
5. `detail` and `title` contain no `_`, `/`, `\`, `file://`, `sessionId`, paths, raw failure codes, tokens, passwords or other credentials.
6. Status text changes do not change visibility or action logic.

## 2. Local recording custody

1. `degraded` is not rendered as full success.
2. `blocked` and `failed` require attention and offer a next action.
3. `saving` and `uploading` show progress and do not allow destructive actions.
4. `saved` does not steal focus or auto-expand the inspector.
5. `expired` explains that automatic sending is over and offers local open/delete/support where allowed.
6. Opening, sending and deleting remain separate actions; no destructive action is implied by opening.
7. Deletion copy stays within GRAF control and does not promise universal erasure.
8. Copying the safe support summary shows a visible confirmation and copies only metadata allowed by the existing support policy; no raw audio, transcript, tokens, paths or private meeting content.
9. Quitting during save either finalizes within the bounded termination window or preserves a recoverable local package; it never silently discards buffered audio.

## 3. Permissions

1. Both permissions are required for `isReady`.
2. `denied` offers system settings; `restricted` does not loop on a request that cannot succeed; `stale` offers retry.
3. Onboarding, capture panel and start gate use the same wording.
4. Onboarding never starts a recording.

## 3a. Settings and cabinet states

1. Settings sections: «Аккаунт» (cabinet required), «Запись» (local), «Уведомления» (local), «Календарь» (cabinet required), «Биллинг» (cabinet required).
2. Default route is the requested section; without a request, «Запись».
3. For a cabinet-required section while offline: show section name, reason, «Повторить» and «Локальные настройки».
4. For a local section while offline: show the local controls and a short note that cabinet sections are unavailable.
5. Cabinet empty state: no meetings, one clear action to start recording or upload; no old meeting data.
6. Cabinet loading state: progress/placeholder without old meeting content; Stop remains available if recording.
7. Cabinet error state: human reason, retry, return to meetings; old content cleared.
8. Settings error state: local controls remain usable where possible; save failure is visible and retryable.

## 4. Account switch

1. On authentication change, the UI resets to the meetings list before showing new data.
2. Old calendar prompt, meeting title, local player item and selected recording are cleared synchronously.
3. Web bridges are invalidated; in-flight responses from the old session are ignored. Cabinet-origin cookies, `localStorage`, `sessionStorage` and in-memory route state from the old account are cleared or isolated per account before new data is shown.
4. New data is requested only after the reset.
5. Reset does not delete local recordings or change their ownership silently.
6. Auth provider flow, attribution labels and workspace selection are not redesigned; the reset preserves the approved post-login attribution behavior and never opens another workspace implicitly.

## 5. Menus and keyboard

1. All user-facing menu titles are Russian.
2. No two visible menu items share the same key equivalent.
3. `⌘⇧R` starts recording; `⌘⇧S` stops recording when active; `⌘,` opens settings; `⌘0` resets cabinet zoom.
4. “Домой” uses a non-conflicting shortcut.
5. Stop is available from the application menu while recording, even if the main window is closed, minimized or full-screen.
6. Disabled items remain in the menu with correct state.

### Canonical visible labels

| Surface | Start | Stop | Pause mic | Resume mic |
|---|---|---|---|---|
| Capture panel | «Начать запись» | «Остановить запись» | «Выключить микрофон» | «Включить микрофон» |
| Titlebar HUD | — | «Остановить запись» | «Выключить микрофон» | «Включить микрофон» |
| Compact rail | tooltip «Начать запись» | tooltip «Остановить запись» | — | — |
| Application menu | — | «Остановить запись» | — | — |
| Menu bar | «Начать запись» | «Остановить запись» | «Выключить микрофон» | «Включить микрофон» |

Термин «Mute» в видимых подписях не используется.

## 6. Preferences

1. Window frame, inspector expansion and selected microphone survive a normal relaunch.
2. Invalid stored values fall back to defaults without blocking launch.
3. A disconnected microphone falls back to the system default with a visible explanation.
4. Preferences do not store meeting titles, transcript text or credentials.

## 7. Accessibility

1. Every critical icon-only control has an accessibility label and help.
2. Capture region has a logical VoiceOver order before the embedded cabinet.
3. Reduced motion disables decorative pulses and equalizer animation.
4. Increased contrast keeps critical borders and text distinguishable.
5. Key surfaces tolerate long Russian strings and enlarged system text without hiding the primary action.
6. Keyboard focus can reach Start, Stop, Pause, Resume and settings.
7. The notification card never covers the persistent recording indicator or Stop; if placement would conflict, it moves or closes, and keyboard focus can still reach Stop.

## 8. Performance

1. The render path contains no `FileManager` checks, `AVCaptureDevice.DiscoverySession`, JSON decoding or network waits.
2. Level updates at 5 Hz do not allocate a new `DateFormatter` per row per render.
3. Queue reads/writes do not block the main thread.
4. Logging is bounded and does not redact less than the diagnostic redactor.
5. Primary control response remains ≤100 ms in the 60-minute/100-recording scenario.
6. Performance is measured with `os_signpost` around the control action and Instruments Time Profiler over a 60-second active-recording sample with a 100-item synthetic queue; main-thread samples must show zero `FileManager`, `AVCaptureDevice.DiscoverySession`, JSON decode and network wait frames.

## 9. Design tokens

1. Core CSS variables and `DesktopDesignTokens` agree on background, panel, surface, text, muted, accent, green, amber, red and line.
2. A contract test fails on drift.
3. Native notification card uses the same palette or a documented floating-surface exception.

## 10. Dead code

1. Removing a type/constant does not change public behavior.
2. Test-only constants are either removed with their tests or moved to a test support file.
3. Dev-only local mode is explicitly marked and does not run in production paths.
4. Analytics scaffold and encrypted-buffer contracts are not removed without a separate product decision.
