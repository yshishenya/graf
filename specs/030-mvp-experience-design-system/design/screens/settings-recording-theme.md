# Settings Recording And Theme

## Purpose

Settings must be a real list-detail workspace, not a small mixed card. The
screen lets the owner control recording behavior, meeting detection, theme,
language, sources, notifications, storage/queue truth, privacy/deletion copy,
and browser-owned account/workspace handoff.

## Layout

- Surface: desktop embedded settings plus full browser settings.
- Target desktop frame: `1080 x 760`.
- Target browser frame: `1440 x 900`.
- Left settings rail: `220-248 px`.
- Detail content width: `640-780 px`, left aligned.
- Section gap: `28-32 px`.
- Row height: `52-64 px` for rows with toggles; `72-88 px` when helper copy is
  needed.
- Buttons: `36 px` standard, `40 px` destructive/primary, `32 px` compact
  segmented controls, `28 px` chips.

## Settings IA

Launch MVP sections:

- `Аккаунт`
- `Запись`
- `Определение встреч`
- `Источники`
- `Внешний вид`
- `Язык`
- `Уведомления`
- `Приватность`
- `Хранилище и очередь`
- `Диагностика`

Browser-only or admin handoff sections:

- `Команда`
- `Доступы`
- `Интеграции`
- `Безопасность аккаунта`
- `Удаление аккаунта`
- `Биллинг` if a hosted/commercial edition later introduces it.

## Recording Behavior

Primary policy visible labels:

- `Спрашивать` default.
- `Всегда писать`.
- `Вручную`.

Helper copy explains the labels outside the chips. Do not put long policy text
inside the segmented control.

Rules:

- Auto-record policy never hides the active capture indicator.
- Manual start/stop remains available.
- If a workspace policy blocks recording, the row shows `Запись недоступна`
  with a browser handoff to policy details.
- Do not use implementation words such as native, driver, backend, webhook,
  route, or server online.

## Meeting Detection

Supported app/web meeting rows show:

- App/service name.
- Detection state: `Включено`, `Спрашивать`, `Вручную`.
- Last detected signal if useful: `Zoom`, `Google Meet`, `Microsoft Teams`,
  `Яндекс Телемост`, browser tab meeting, calendar event.
- Exclusions list: apps/services where prompts are muted.

Wording:

- Default: `Когда начинается встреча, спросить: записывать?`
- Always option: `Всегда писать выбранные встречи`.
- Manual option: `Запускать запись только вручную`.

## Sources

Controls:

- `Звук системы`.
- `Микрофон`.
- Input/source status.
- Permission recovery link: `Открыть настройки macOS`.

Rules:

- Source state is user-facing and compact.
- Detailed device diagnostics live in `Диагностика`.
- The UI must never imply a source is recorded before permissions and capture
  are active.

## Appearance And Language

Theme segmented control:

- `Системная`
- `Тёмная`
- `Светлая`

Rules:

- Switching theme must not change layout, density, status order, or available
  actions.
- The active theme choice is visible in both desktop and browser settings.
- A light-theme proof frame must exist for the main meeting cockpit.

Language:

- Interface language: `Русский` for MVP.
- Summary/transcript language is a meeting-processing preference and may be
  surfaced in meeting review when regeneration is safe.

## Notifications

Required controls:

- `Встреча обнаружена`.
- `Запись идёт`.
- `Транскрипт готов`.
- `Нужны говорящие`.
- `Загрузка не удалась`.

Rules:

- Notifications use human outcomes, not pipeline names.
- Active recording reminder cannot be disabled if that would remove the only
  visible capture signal.

## Privacy And Storage

Rows:

- `Где хранятся записи`: owner-controlled server plus local queue truth.
- `Локальная очередь`: count, last sync, retry/retry-all action.
- `Согласие и уведомления`: participant-facing reminder policy.
- `Удаление`: browser handoff with bounded deletion truth.

Copy constraints:

- Do not promise universal erasure outside 2brain Rec control.
- Do not hide MediaScribe, Langfuse, backups, local buffers, Temporal payloads,
  or diagnostics in deletion truth documents.
- Do not expose provider names in the first viewport unless the user opens
  details or diagnostics.

## Native Vs Web Ownership

Desktop native owns:

- Opening macOS permission settings.
- Capture source status.
- `Начать запись`/`Остановить` availability summary.
- Menu-bar and notification behavior.
- Local queue count/retry summary.
- Diagnostics bundle.

Server-owned embedded/web owns:

- Recording policy.
- Meeting detection app/service rules.
- Language/theme preference sync.
- Upload/storage policy.
- Speaker assignment settings if later added.
- Access/deletion governance entry.

Browser-only owns:

- Account security.
- Public link/access policy.
- Delete account.
- Team/admin/workspace policy.
- Integration credentials.

## Forbidden

- No standalone sync/server status block in normal settings.
- No `native` label in the user interface.
- No primary local/offline continuation button in sign-in or settings.
- No technical service names in normal settings rows.
- No nested cards inside settings cards.
- No oversized hero copy in settings.

## Acceptance Evidence

Covered by Figma `V8 09 - Настройки записи и темы`,
`V8 13 - Светлая тема: проверка экрана`, `V8 14 - Правила интерфейса и QA`,
`design/evidence/krisp-v8-window-capture-audit.md`, and
`design/validation-evidence.md`.
