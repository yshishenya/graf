# V7 Screen Task Backlog

This backlog replaces the v6 "screen inventory is enough" assumption. Every
screen group below requires design, five-critic review, Figma update, and
evidence before v7 can be accepted.

## Global Product Shell

### V7-T01 Header, Sync, Account, And Menu Bar

Problem:

- V5/V6 overexpose `Сервер в сети` and implementation state.
- Sync/account status takes too much visual space.
- Menu bar is functional but not elegant enough for a daily macOS recorder.

Required redesign:

- Use compact status in toolbar/menu bar: dot + `Синхронизировано`, `Офлайн`,
  `Очередь`, or `Нужно войти`.
- Status popover shows details: last sync, local queue count, account, open web,
  diagnostics.
- Do not copy Krisp's large trial/reactivation banner. Self-hosted/account
  issues should be compact, dismissible, and tied to user recovery.
- No visible `server`, `native`, `route`, `api`, `worker`, `web-view`.
- Menu bar popover has ready, detecting meeting, recording, saving, uploading,
  failed/offline states.

Acceptance:

- First viewport status occupies less than 160 px width in normal state.
- Details are one click away, not visible by default.
- Recording Stop is first action in menu bar while active.

### V7-T02 Auth And First Run

Problem:

- V5/V6 auth window is too large and copy-led.
- `Продолжить локально` is unclear and too prominent.
- Provider/social login is missing.

Required redesign:

- Compact centered auth panel, smaller than 520 x 520.
- Primary provider sign-in buttons include email, Google, Apple, Microsoft,
  Yandex, and SSO.
- Local/offline continuation is not a primary first-run action. If policy later
  requires it, it must be a clearly scoped recovery/help path, not a competing
  onboarding choice.
- Remove generic slogan copy; use one short value sentence tied to sync:
  `Записывайте встречи и открывайте транскрипты в приложении и вебе`.

Acceptance:

- No technical terms.
- Provider sign-in is visible without scrolling.
- No primary local/offline continuation competes with sign-in.

### V7-T03 Guided macOS Permissions

Problem:

- Current permissions screen is an unexplained route.
- User expects a first-open guided permission flow.

Required redesign:

- Native stepper: microphone, system audio, optional notifications.
- Each step shows a visual mini-guide: `System Settings -> Privacy & Security ->
  Microphone` or `Screen & System Audio Recording`.
- Actions: `Открыть настройки`, `Проверить`, `Позже`.
- Only show restart/quit copy if the OS requires it.

Acceptance:

- User can understand where to click without reading a long paragraph.
- Permission recovery does not look like an admin dashboard.

## Meeting Workspace

### V7-T04 Desktop Home / Meeting Workspace

Problem:

- V5/V6 first screen has too much empty space and not enough real daily value.
- Meeting rows lack date/time clarity.
- Upload/search/processing are split into separate screens.

Required redesign:

- Default desktop surface: compact native capture strip + embedded meeting
  workspace.
- Desktop may include a narrow native recording/status rail only when it
  increases trust. It must not become a copied Krisp noise/accent rail.
- Meeting rows include title, date/time, duration, source, status, next action,
  and lightweight owner/participants when available.
- Search, status filters, and upload are inline in the meeting workspace.
- Upload opens a sheet/drawer, then creates/updates a row immediately.
- Processing is a row state with expandable detail, not a generic page.

Acceptance:

- First screen answers: what can I do now, what is processing, what is ready.
- Empty area is purposeful; no hero/card marketing layout.

### V7-T05 Web Meeting List

Problem:

- Current web list composition is strange and search/filter as a separate
  screen breaks the IA.

Required redesign:

- Krisp-inspired clean-room cabinet: left nav, compact top bar, dense list,
  search field, filter chips, sort menu, upload action, optional upcoming block.
- Filters are inline chips/popovers: status, date, source, participant, owner,
  tag, access.
- Table/list can switch density but default is compact.

Acceptance:

- Search and filters are available on the list page.
- No empty filter chips.
- Status rows can represent desktop recordings, uploaded files, processing,
  failed items, and ready transcripts.

### V7-T06 Upload As Integrated Flow

Problem:

- Upload is a disconnected screen/menu item.
- Desktop and web upload should feel like the same server-owned surface.

Required redesign:

- Upload action opens sheet/drawer from desktop or web meeting workspace.
- Fields are minimal first: file, title, language, date/time, participants.
- Advanced fields are collapsed.
- Validation errors appear in the sheet and in the created row.

Acceptance:

- Upload does not remove the user from the meeting workspace.
- Validation explains exact recovery: format, no audio, size, quota, offline.

### V7-T07 Processing As Status Rows

Problem:

- Processing status is too large and isolated.

Required redesign:

- Main row states: `Сохранено на Mac`, `Загружается`, `Принято`,
  `Извлекаем звук`, `Транскрибация`, `Транскрипт готов`, `Заметки готовы`,
  `Нужна проверка`.
- Expanded row shows stage timeline and retry details.
- Dedicated processing detail exists only as deep link from row.

Acceptance:

- User sees current status from the list without opening a separate page.
- Web and desktop labels match.

## Recording And Detection

### V7-T08 Active Recording Shell State

Problem:

- V5/V6 active recording as a full screen feels wrong.

Required redesign:

- Active recording is a persistent native strip below toolbar and menu bar
  popover state.
- Strip includes meeting/app detected, timer, source chips, meters, local save
  truth, and Stop.
- If a right rail is used, it is a recording trust rail with current source,
  permission health, local save/sync status, and compact recovery actions. It
  never exposes backend/service labels.
- Under the strip, user stays in meeting list/review/upload.

Acceptance:

- No dedicated "recording dashboard" required for the happy path.
- Stop remains visible while any embedded route is open.

### V7-T09 Auto-Meeting Detection Prompt

Problem:

- Auto-detect meeting behavior is missing.

Required redesign:

- When a supported conferencing app/web meeting is detected, show a compact
  native prompt:
  `Похоже, началась встреча в Zoom. Записать?`
- Actions: `Записать`, `Не сейчас`, `Всегда спрашивать...` / policy menu.
- Settings policy:
  - `Спрашивать перед каждой встречей` (recommended default)
  - `Записывать автоматически для выбранных приложений`
  - `Не предлагать запись автоматически`
- App allowlist and exclusions live in settings.

Acceptance:

- No silent recording.
- User can choose default behavior and override per meeting.

## Review Workspace

### V7-T10 Meeting Review

Problem:

- Review needs stronger information hierarchy and less toolbar clutter.

Required redesign:

- Header: title, date/time, status, source, participants, share/export/more.
- Body: transcript and notes/actions as primary tabs or split mode.
- Bottom/player: playback and speaker lanes stay connected.
- Speaker assignment remains web-owned and embeddable, one lane per speaker.

Acceptance:

- Transcript, playback, notes, speaker correction, and export path are visible
  without feeling like unrelated tools.

## Settings Workspace

### V7-T11 Settings IA

Problem:

- Settings are not thought through.
- Theme switching is missing.
- Recording behavior and auto-detect policy are missing.

Required redesign:

- Settings sections:
  1. Account and sign-in
  2. Appearance: `Системная`, `Темная`, `Светлая`
  3. Recording: sources, save location summary, default behavior
  4. Meeting detection: supported apps, ask/auto/never policy
  5. Upload and storage: local queue, retries, cleanup
  6. Notifications
  7. Workspace policy: browser-owned admin settings
  8. Integrations: browser-owned
  9. Diagnostics and support bundle
- Risky account/workspace edits open in browser.

Acceptance:

- Every setting has a clear owner: desktop local, embedded web, or browser-only.
- Theme switch is present and affects token proof.
- Diagnostics are discoverable but not first-viewport content.

## Theme And Design System

### V7-T12 Light/Dark/System Theme

Problem:

- Dark theme exists, but theme switching and light proof are missing from v6.

Required redesign:

- Add appearance settings screen/state with system/dark/light segmented control.
- Add token proof for light and dark on core components.
- Provide at least three light-mode proof frames: meeting workspace, review,
  settings.

Acceptance:

- Component tokens are not one-off colors.
- Text contrast, focus, status colors, and disabled states pass visual QA in
  both themes.
