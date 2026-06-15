# 2brain Rec MVP Experience Blueprint

Feature: `030-mvp-experience-design-system`
Date: 2026-06-11
Status: V8 clean Russian redesign candidate after stakeholder rejection of v6/v7

This document is the product-design source for the MVP desktop and web
experience. It replaces the first rough visual pass, which was too diagnostic
and did not make the desktop app feel like a real personal cabinet. The v5
Figma page is now superseded as a final handoff target; use it only as coverage
evidence. The v6 page, first v7 page, v7.1, v7.2, and v7.3 are also
superseded for handoff. The v7.4 Figma page is the active correction candidate
after the Krisp IA review.

## Design Decision

2brain Rec ships as a hybrid product:

- The macOS app is a native trust shell. It owns recording, `Остановить`,
  permissions,
  local saved-file truth, local upload queue truth, offline recovery, and the
  menu bar/tray status.
- The web cabinet is the full product surface. It owns meeting library,
  uploaded media, processing, transcript review, notes, action items, account,
  workspace, admin, deletion, audit, billing, sharing, downloads, help, and
  legal surfaces.
- The macOS app embeds only a desktop-safe cabinet subset from the server. This
  subset gives the user a real library and meeting review inside the app, but
  it cannot own, hide, restyle, or delay capture-critical native controls.

The launch product must feel like: record or upload, watch the current status
everywhere, open the result, and act on the transcript/notes. Everything that
does not help that loop is either hidden, deferred, or a browser handoff.

## Current Product Reality

Accepted foundations already exist:

- Manual macOS `Начать запись`/`Остановить` and visible local recording state.
- Local dual-track recording artifacts with manifest truth.
- Server ingest/auth/deployment foundations.
- Desktop upload queue specs and code-level foundations are present, but the
  installed app does not expose a launchable upload queue or server-backed
  library UI yet.
- ADR boundary that keeps capture-critical control native/local.

Launch gaps still blocking a complete first version:

- The installed desktop app currently looks like audio diagnostics. It does not
  show the user's cabinet, meeting library, server account state, processing
  status, or transcript result.
- The web cabinet is a target surface, not an implemented product UI.
- Manual upload of user-owned media is not yet a complete user workflow.
- MediaScribe processing is handled by the separate `015` worktree/branch.
  This `030` design must align with its processing/transcript contracts, but it
  does not implement or duplicate `015`.
- Transcript review, notes display, deletion execution, sharing, downloads, and
  browser cabinet routes are not accepted in this worktree yet.
- Current worktree verification found `014-desktop-upload-queue`,
  `028-provider-auth-session`, `029-email-auth-account-linking`, and this `030`
  feature. `015-mediascribe-processing-pipeline` exists in a separate local
  worktree and remote branch.

## Krisp Clean-Room Observations

These observations were made for category learning only. Do not copy Krisp UI,
copy, icons, assets, colors, names, exact layout, proprietary behavior, or
meeting content.

Detailed evidence lives in
`design/evidence/krisp-full-navigation-audit.md`. This blueprint uses only the
allowed category lessons from that audit.

Observed category patterns from Krisp web cabinet:

- A persistent left cabinet menu groups Search, personal meeting list, shared
  items, action items, activity, contacts, and settings.
- Account identity, plan/trial state, teammate invitation, app download, and
  developer entry points live near the cabinet navigation.
- The meeting-notes URL is filterable by date, company, text search, tags,
  meeting id, participants, access, sort, starred, type, listen-later, and owner
  scope.
- The cabinet includes an AI query surface that is scoped to meetings rather
  than a generic global chat.
- Empty or blocked subscription states still keep past meetings reachable.
- List controls include later/starred state, filter chips, date/content/company
  filters, type/tags, sort by date/duration/modified, and upcoming calendar
  visibility settings.
- Meeting review includes transcript, playback timeline, speaker labels,
  language correction/regeneration, transcript quality feedback, tags,
  share/access, export/download/delete, and scoped AI.
- Account/settings expand far beyond the recorder loop: account security,
  admin policy, users, billing, team integrations, consent, personalization,
  calendar, language, action items, vocabulary, tags, and app behavior.

Observed category patterns from Krisp desktop:

- The desktop app embeds a server cabinet route inside the app.
- Local audio controls and server meeting notes coexist in one window.
- Meeting notes are dense rows, not oversized cards.
- Recording/audio toggles remain compact and close to native desktop behavior.
- Trial/account state is visible without replacing the local controls.

2brain Rec category lessons:

- Desktop must not be only diagnostics. It needs the user's real library.
- Web content can provide cabinet value inside the desktop app, but native
  recording truth must stay permanently visible.
- Meeting rows should be dense, scannable, and status-rich.
- Search/AI should retrieve meeting knowledge and status, not become the first
  screen or a decorative assistant.
- Subscription/team/admin concepts are not launch-critical for the owner value
  loop and should not crowd the app MVP.
- Rich web filters are useful in the browser, but desktop should start with
  simple saved views and status tabs. Do not show empty active-filter chips.
- The useful result is a review workspace, not just a file upload receipt.
  Transcript, playback, source provenance, summary, decisions, action items,
  and degraded truth must be designed together.
- Sharing, public links, billing, admin policy, calendar disconnect, deletion,
  and account security are browser-owned or require explicit confirmation.
- AI scope is a privacy boundary. "This meeting" and "all meetings" cannot be
  treated as a visual-only toggle.

## Audit-Driven MVP Value Loop

The first launch should be judged by one loop:

1. User opens the macOS app or web cabinet and sees exact account/server/local
   state.
2. User records in the app or uploads owned media in desktop/browser.
3. User sees the same meaningful status everywhere: saved locally, queued,
   uploading, uploaded, extracting, transcribing, transcript ready, notes ready,
   degraded, failed, deleted, or access denied.
4. User opens the meeting and gets transcript plus playback/provenance.
5. User gets notes, decisions, action items, questions, and follow-ups when
   processing succeeds.
6. User can correct speaker labels, retry, safely export/download when policy
   allows, manage access in browser, and delete with truthful boundaries.

Anything outside that loop is secondary for MVP:

- Team trials, billing, subscription, and seat management.
- Workspace admin policy editing and SSO.
- Integration marketplace and developer platform.
- Global contacts and activity center.
- Centralized action-item workspace.
- Detailed audit/deletion reports.
- Advanced transcript editing, find/replace, and language regeneration.

These can be represented as browser handoff, deferred markers, or future
backlog candidates, but not as first-viewport desktop UI.

## 2026 Product Design Direction

Research trend summary used for direction:

- Modern SaaS dashboards are moving toward workflow-first outcomes, lower
  cognitive load, and showing "what matters now" before broad dashboards.
- AI-native interfaces work when they are contextual controls for user intent,
  not floating novelty.
- macOS 26 direction favors familiar native structures with more expressive
  materials, but operational apps still need clear content boundaries and
  restraint.
- Minimalism in 2026 must keep cues, affordances, and accessibility. Empty
  slickness is worse than a dense but legible product surface.

Sources consulted:

- Apple Newsroom, "Apple introduces a delightful and elegant new software
  design", 2025-06-09.
- Apple Developer WWDC25, "Build a SwiftUI app with the new design".
- Figma resource library, "Top Web Design Trends for 2026".
- 925 Studios, "35 SaaS Dashboard Design Examples That Set the Standard in
  2026".
- SaaS UI Design, "7 SaaS UI Design Trends in 2026".

2brain Rec direction:

- Quiet operational premium, not marketing.
- Dense, readable, low-drama layouts.
- Dark Russian UI first for launch across desktop and web. Light/system theme
  remains a token-compatible follow-up proof, not the primary handoff target.
- Native macOS chrome uses system materials sparingly around the capture strip;
  meeting content stays on solid surfaces for readability.
- Semantic color is limited and meaningful: green for ready/saved/complete,
  cobalt for in progress, amber for waiting/degraded, red for destructive or
  failed, neutral for informational status.
- No decorative gradient orbs, mascot, fake illustrations, oversized hero,
  nested cards, or meaningless test data.

## Native Vs Web Boundary

The desktop product is multi-platform by design. macOS is the first native
shell, but Windows and Linux shells should reuse the same product web cabinet
wherever the UI is variable, server-backed, or likely to change between
releases.

Native shells own only platform-critical responsibilities:

- recording start/stop and visible capture indicator;
- system audio and microphone permission recovery;
- local recording buffer, local artifact truth, and upload queue truth;
- tray/menu-bar or platform status surface;
- local diagnostics and log bundle creation;
- embedded web host, route allowlist, auth/session holder, and fail-closed
  route guard.

Server/web owns variable product workflows:

- meetings list, meeting review, processing status, speaker assignment,
  notes/actions, upload metadata, account summaries, and most settings;
- copy, layout, feature flags, status wording, and screen evolution that should
  update consistently across macOS, Windows, and Linux without duplicating
  native UI code.

Rule: if a screen can change because the product, backend, status model, or
workspace policy changes, it should be web/backend-rendered and embedded in
desktop. If a screen needs OS APIs, capture safety, local files, or platform
permissions, it must stay native.

| Surface | Owner | Desktop embedded? | Browser web? | Rule |
|---|---|---:|---:|---|
| Recording start | Native macOS | Yes | No | Manual start is local. Web may explain, never start recording in MVP. |
| Active recording indicator | Native macOS | Yes | Status mirror only | Native indicator and `Остановить` must always remain visible. |
| `Остановить` recording | Native macOS | Yes | No | One-action `Остановить` cannot be server-rendered. |
| Microphone/system permission | Native macOS | Yes | No | Web may link help copy only. |
| Local recording saved | Native macOS + status API mirror | Yes | Yes | Desktop is authoritative until server confirms ingest. |
| Upload queue | Native macOS + server status | Yes | Yes | Desktop shows local truth; web shows server truth and may show "waiting for desktop". |
| Manual media upload | Web cabinet | Yes | Yes | Desktop embeds the same upload route with desktop-safe chrome. |
| Processing progress | Web cabinet + server API | Yes | Yes | Same stages and copy across app and browser. |
| Meeting list | Web cabinet | Yes | Yes | Desktop subset removes browser-only filters/actions. |
| Meeting detail/review | Web cabinet | Yes | Yes | Desktop can review; browser has the full review and admin/share/export depth. |
| Search current meetings | Web cabinet | Yes | Yes | Desktop search is scoped to accessible meetings/statuses only. |
| Rich filters and saved views | Web cabinet | Basic saved views | Yes | Browser owns full filter chips, sort, people/company/tags, and historical views. |
| Transcript playback | Web cabinet | Yes | Yes | Playback is safe only after audio is available and policy allows. |
| Speaker assignment | Web cabinet + server API | Yes | Yes | Desktop embeds the server-owned assignment panel; native code hosts it but does not own diarization/editing logic. |
| Transcript correction/regeneration | Web cabinet | Handoff/deferred | Yes | Processing-changing actions require confirmation and browser context. |
| AI "this meeting" scope | Web cabinet | Deferred/limited | Yes | Must use explicit scope and available source truth. |
| AI "all meetings" scope | Web cabinet | No | Browser/deferred | Broader privacy/retention boundary; not desktop MVP. |
| Tags/labels | Web cabinet | View/add basic only | Yes | Desktop can show labels; browser owns management. |
| Account status | Web cabinet + native session holder | Yes | Yes | Desktop can recover session and view workspace policy. |
| Workspace admin/team/billing | Web cabinet | Handoff only | Yes | Browser-only. Do not clutter desktop. |
| Invite/share/access levels | Web cabinet | Handoff marker | Yes | Browser-only for edits; default private in desktop. |
| Public sharing/download management | Web cabinet | Handoff marker | Yes | Deferred or browser-only for launch. |
| Export transcript / download audio | Web cabinet | Handoff/deferred | Yes | Available only after ready status and policy check. |
| Retention/deletion | Web cabinet + native local purge truth | Entry/details | Yes | Copy must account for local buffers, server objects, backups, external dependencies. |
| Diagnostics/log bundle | Native macOS | Yes | No | Browser may show audit summaries later, never raw local paths. |
| Help/legal | Web cabinet | Handoff only | Yes | Browser-only. |

## Product Information Architecture

### macOS Native Trust Shell

Native areas:

- Window toolbar: app identity, server connection, workspace/account chip,
  refresh/sync, open-in-browser.
- Capture strip: readiness, source, elapsed time, dual-track meters,
  `Начать запись` or `Остановить`, local save/upload status, policy state.
- Embedded cabinet host: server-rendered desktop-safe cabinet subset.
- Local recovery drawer: permissions, local artifacts, upload retry, diagnostic
  bundle, app logs redaction note.
- Tray/menu bar status: compact current state and one-action `Остановить`.

Default desktop route:

`/desktop/meetings`

This is not a diagnostic dashboard. The first visual payload is the meeting
library with current status and upload entry, wrapped by native capture truth.

### Embedded Desktop Cabinet Subset

Allowed routes:

- `/desktop/meetings`
- `/desktop/meetings/:id`
- `/desktop/meetings/:id/speakers`
- `/desktop/upload`
- `/desktop/processing/:id`
- `/desktop/account`
- `/desktop/workspace-policy`
- `/desktop/settings/basic`
- `/desktop/deletion/:id`

Hidden routes:

- Admin
- Billing
- Team management
- Public sharing
- Advanced downloads/exports
- Global action items
- Contacts management
- Activity center
- Integration marketplace
- Developer/API
- Transcript find/replace
- Transcript language regeneration
- Detailed audit
- Help/legal

Handoff behavior:

- A hidden route deep link opens a compact handoff banner: "This opens in the
  web cabinet." Primary action: `Open in browser`. Secondary: `Stay here`.
- During active recording, handoff links remain allowed, but the native
  `Остановить`
  strip stays above every view.

### Full Browser Web Cabinet

Primary nav:

- Meetings
- Upload
- Action items
- Shared
- Contacts
- Workspace
- Audit
- Settings

Secondary/browser-only nav:

- Team
- Billing
- Downloads
- Sharing
- Deletion reports
- Help
- Legal
- Developer/API

The browser can be broader because it is not capture-critical. It still uses
the same status names and meeting review model as desktop.

## Layout System

### Desktop App Window

Target canvas: `1080 x 760`.

Minimum usable size: `960 x 680`.

Structure:

- macOS titlebar/toolbar: `52 px` high.
- Native capture strip:
  - idle height `84 px`;
  - active height `96 px`;
  - degraded/offline height may expand to `124 px`;
  - pinned above all server content.
- Embedded cabinet viewport: fills remaining height.
- Cabinet sidebar inside embedded web: `216 px`.
- Main cabinet content: min `640 px`, fluid.
- Optional detail inspector inside web route: `320 px`, hidden below `1040 px`.

Spacing:

- Outer native padding: `16 px`.
- Toolbar gap: `10 px`.
- Capture strip inner gap: `12 px`.
- Cabinet content padding: `24 px` desktop, `32 px` browser.
- Row height: `60 px` compact desktop, `64 px` browser.

Radii:

- Small controls: `6 px`.
- Panels and rows: `8 px`.
- Modals/drawers: `10 px` max.
- No nested card-on-card sections.

### Browser Cabinet

Target canvas: `1440 x 900`.

Structure:

- App sidebar: `248 px`.
- Top header/search: `64 px`.
- Content max width: `1120 px` for list; review page uses `calc(100% - 360 px)`
  plus a `360 px` side panel.
- Filters row: `44 px`, horizontally scrollable below `1100 px`.
- Meeting list header: `44 px`.
- Meeting rows: `64 px`.

Responsive rules:

- `>=1280 px`: sidebar + content + optional inspector.
- `1024-1279 px`: sidebar narrows to `220 px`, inspector collapses.
- `<1024 px`: browser web uses top nav + drawer sidebar; desktop embedded
  should prefer a browser handoff rather than a cramped full review.

## Screen Specs

### 1. Desktop Ready Home / Cabinet

Purpose: show that the app is ready to capture and that the user has a real
cabinet.

Layout:

- Toolbar left: 2brain Rec mark, workspace name, `Синхронизировано` chip or exact
  degraded state.
- Toolbar right: account avatar, sync refresh, `Открыть веб-кабинет` icon button.
- Capture strip left:
  - status dot + `Готово к записи`;
  - selected source: `Звук системы + микрофон`;
  - policy: `Ручной старт`.
- Capture strip center:
  - two compact meters labeled `Микрофон` and `Система`;
  - permission summary with icon, not verbose diagnostics.
- Capture strip right:
  - primary `Начать запись` button `40 px` high;
  - secondary `Добавить запись` button if no recording active.
- Embedded cabinet:
  - left web sidebar with `Встречи`, account/workspace, settings, and
    browser handoff entries;
  - main header `Встречи`;
  - search field `Поиск по встречам, тексту, людям`;
  - status tabs: `Все`, `На проверку`, `В обработке`, `Только на этом Mac`,
    `Требуется действие`;
  - list rows with title, source, date, duration, status, primary action.

Primary actions:

- `Начать запись`
- `Добавить запись`
- `Открыть`
- `Повторить загрузку` for failed/local items

No-go:

- No driver diagnostics in the first viewport.
- No fake "sample/transcript" rows. Use seeded real/dev records or meaningful
  empty state.
- No web-rendered `Остановить` button.

### 2. Desktop Active Recording

Purpose: make active capture impossible to miss and one action away from stop.

Layout:

- Capture strip turns into active state and remains pinned.
- Left: red recording dot, title `Идёт запись`, elapsed timer, capture target.
- Center: live meters for `Микрофон` and `Система`, route/source provenance.
- Right: destructive `Остановить` button, `Отметить момент` secondary, optional `Свернуть`
  is not allowed if it hides the indicator.
- Embedded cabinet remains visible below. It may show library/review, but top
  of every server page has a read-only active recording banner aligned with the
  native state.

States:

- recording active;
- local save preparing;
- server offline while recording;
- policy stale while recording;
- low disk / buffer warning;
- permission revoked.

Primary action: `Остановить`.

No-go:

- Server content cannot push the active strip off-screen.
- Popovers cannot cover `Остановить`.
- Copy must not say "uploaded" before recording is stopped and upload truth is
  known.

### 3. Desktop Upload Queue / Local Truth

Purpose: let the user trust what happened after `Остановить`.

Layout:

- Native strip shows `Saved locally` then `Queued`, `Uploading`, `Uploaded`,
  `Retrying`, or `Blocked`.
- Embedded route `/desktop/processing/:id` shows a stage rail:
  `Saved locally -> Uploading -> Ingested -> Transcribing -> Notes -> Ready`.
- Right side details explain where the file is:
  - local package retained until server confirmation;
  - server accepted bytes/tracks;
  - next retry time;
  - deletion/retention implication.

Actions:

- `Retry now`
- `Pause retries`
- `Open local package` only in debug/internal builds
- `Open in web`

No-go:

- Do not collapse local-only and server-ready into the same status.
- Do not expose raw local paths in normal UI.

### 4. Desktop Permission Recovery

Purpose: recover capture safely without turning the app into diagnostics.

Layout:

- Top capture strip shows blocked status.
- Main body uses a focused recovery checklist:
  1. Microphone permission
  2. Screen/system audio permission
  3. Local buffer health
  4. Server session
- Each row has state, short reason, action, and "why this matters" disclosure.

Actions:

- `Открыть настройки macOS`
- `Проверить снова`
- `Продолжить без синхронизации` only when policy allows
- `Диагностика` secondary

No-go:

- No driver install/repair language in MVP first-run unless future advanced
  routing is explicitly enabled.

### 5. Tray / Menu Bar Mini Controller

Target size: `320 x 460`.

Purpose: answer "is it recording, can I stop, what happens next?" without
opening the full app.

Sections:

- Current state header.
- Active recording timer and `Остановить` when active.
- Latest meeting status: saved/uploading/transcribing/ready.
- Quick actions: `Открыть приложение`, `Добавить запись`, `Повторить загрузку`,
  `Открыть веб`.
- Footer: account/server connection.

No-go:

- Tray cannot start hidden recording.
- Tray cannot show broad cabinet/admin content.

### 6. Web Meetings List

Purpose: the home of post-meeting work.

Layout:

- Left sidebar `248 px`: workspace, `Встречи`, `Действия`, `Доступные мне`,
  `Контакты`, `Аудит`, and `Настройки`.
- Header:
  - title `Встречи`;
  - primary `Загрузить медиа`;
  - secondary `Открыть приложение для записи` with app handoff; the browser
    cabinet must not imply it can start native capture.
- Search row:
  - command/search field with `Поиск`;
  - `Дата` filter;
  - `Люди`/`Компания` filter;
  - `Статус` filter;
  - `Доступ` filter;
  - `Сортировка` menu.
- List:
  - columns: title, source, owner, duration, status, updated, actions.
  - row status is visible as icon + label + progress if processing.
- Empty state:
  - `Встреч пока нет`;
  - primary `Загрузить медиа`;
  - secondary `Открыть приложение для записи`;
  - short promise: `После загрузки появится расшифровка и заметки.`

Meaningful row examples:

- `Product sync - onboarding decisions`
- `Customer call - ACME renewal`
- `Research interview - capture workflow`

Do not use placeholder rows like "Test meeting 1" or user-private meeting data.

### 7. Web Manual Upload

Purpose: let users bring their own media.

Layout:

- Upload drawer or page with `720 px` max width.
- Drop zone with accepted categories:
  - audio files;
  - common video/meeting containers with usable audio;
  - exported meeting recordings.
- Copy explicitly says MVP extracts audio for transcript/notes; full video
  review is deferred.
- Metadata form:
  - title;
  - meeting date/time;
  - participants optional;
  - workspace;
  - source label: `Загруженное медиа`.
- Progress panel:
  `Проверка -> Загрузка -> Извлечение аудио -> Расшифровка -> Заметки -> Готово`.

Actions:

- `Выбрать файл`
- `Начать загрузку`
- `Отменить загрузку`
- `Подробнее`

Failure states:

- unsupported;
- oversized;
- encrypted/corrupt;
- no usable audio;
- duplicate;
- network failed;
- processing unavailable.

### 8. Web Processing Status

Purpose: be useful while waiting.

Layout:

- Meeting header with title, source, duration, owner, status.
- Stage rail with timestamps and current step.
- While transcription runs:
  - show audio metadata;
  - show what is already available;
  - show safe refresh behavior;
  - do not show empty transcript chrome that looks broken.
- If partial transcript exists, show read-only partial transcript with
  `Ещё обрабатываем` marker.

Actions:

- `Сообщить, когда будет готово`
- `Обновить`
- `Открыть статус в приложении`
- `Удалить` entry point, with truth copy.

### 9. Web Meeting Review Complete

Purpose: deliver the product value.

Layout:

- Header:
  - meeting title, date, duration, source provenance;
  - status `Ready`;
  - actions: `Copy summary`, `Open actions`, `Share`/`Export` browser-only or
    disabled if deferred, `Delete`.
- Playback bar:
  - audio play/pause;
  - timeline;
  - jump by transcript segment;
  - speed.
- Main split:
  - left `Transcript` column with timestamped segments, speaker labels,
    search-in-transcript, active playback highlight.
  - right `Review` panel with tabs/sections:
    `Summary`, `Decisions`, `Action items`, `Questions`, `Follow-ups`,
    `Source & status`.
- Source/provenance panel:
  - desktop dual-track, uploaded mixed audio, extracted audio, unknown source;
  - what generated notes came from;
  - degraded warnings.

Primary actions:

- `Play`
- `Search transcript`
- `Copy summary`
- `Create follow-up`

No-go:

- Transcript must not be hidden below AI notes.
- Notes must not claim certainty when transcript or diarization is partial.

### 10. Degraded / Deleted / Access Denied

Purpose: preserve trust when value is incomplete.

Variants:

- Transcript ready, notes failed.
- Upload ready, MediaScribe unavailable.
- Deleted in server, local desktop unreachable.
- Access denied due workspace policy.
- Meeting exists locally only.

Layout:

- Clear state title.
- What exists.
- What failed or is unavailable.
- What the user can do now.
- Deletion/retention truth if relevant.

Actions:

- `Retry processing`
- `Download available transcript` when allowed
- `Request access`
- `Open deletion report`
- `Contact admin` browser-only

### 11. Account And Workspace Settings

Purpose: give enough trust context without turning the desktop app into admin.

Embedded desktop includes:

- signed-in account;
- workspace name;
- server URL;
- recording policy summary;
- retention summary;
- session/device state;
- basic sign out / reconnect.

Browser includes:

- full workspace members;
- providers/account links;
- billing;
- audit;
- retention/deletion policies;
- API/developer entries if enabled.

## Component Rules

### Capture Strip

- Always native in desktop.
- Height `84/96/124 px` depending state.
- Uses semantic state icon + text + action.
- Visible `Остановить` action is right-aligned, `40 px` high, minimum `120 px`
  wide.
- Active state uses red as accent only, not full-screen alarm styling.
- Meters are compact, labeled, and never unlabeled visual decoration.

### Meeting Row

- Height `60 px` desktop, `64 px` web.
- Title max two lines only in narrow desktop; otherwise one line with middle
  truncation.
- Required cells: source icon, title, duration, status, updated/date, actions.
- Status uses icon + label; progress uses small linear progress, never spinner
  alone.

### Status Chip

- Height `24 px`.
- Radius `6 px`.
- Icon `14 px`, label `12-13 px`.
- Semantic variants: ready, local, queued, uploading, processing, degraded,
  failed, deleted, denied.

### Upload Drop Zone

- Minimum `560 x 180 px`.
- No dashed huge marketing blob; use a restrained bordered panel with file type
  truth and action.
- Shows accepted scope before file pick.

### Transcript Segment

- Timestamp column `64 px`.
- Speaker label `88 px` or inline on narrow widths.
- Segment text uses readable body size `14-15 px`, line height `22 px`.
- Current playback segment has left accent bar and subtle background.

### AI / Search Bar

- It is a meeting knowledge command bar, not the first product promise.
- Placeholder: `Спросить по встречам...`
- In desktop, it is secondary to `Начать запись`/`Остановить` and meeting list.
- It can answer status queries only from server/local state that is actually
  available.

## Visual Tokens

Typography:

- Native macOS: system `SF Pro`.
- Web/Figma: `Inter` or system fallback.
- Display is not used inside operational surfaces.
- H1 web: `28/36`, semibold.
- H2/panel title: `18/26`, semibold.
- Body: `14/22`.
- Dense row metadata: `12/16`.
- Buttons: `13-14`, medium.
- Letter spacing: `0`.

Light theme:

- App background: `#F6F7F9`.
- Surface: `#FFFFFF`.
- Surface subtle: `#F0F3F7`.
- Border: `#D9DEE7`.
- Text primary: `#101828`.
- Text secondary: `#667085`.
- Text muted: `#98A2B3`.
- Accent green: `#0E7C66`.
- Accent cobalt: `#2557D6`.
- Accent amber: `#B76E00`.
- Accent red: `#C9352B`.
- Accent violet, AI only: `#6F5DD6`.

Dark theme:

- App background: `#111318`.
- Surface: `#181B22`.
- Surface subtle: `#20242D`.
- Border: `#303642`.
- Text primary: `#F2F4F7`.
- Text secondary: `#AAB2C0`.
- Text muted: `#7D8796`.
- Semantic accents use lighter accessible variants.

## Copy Principles

- Say current truth, not optimistic future.
- Separate "saved locally", "uploaded", "transcribing", "transcript ready",
  and "notes ready".
- Deletion copy must say which systems are covered and which external or
  unreachable systems may age out later.
- Do not expose credentials, signed URLs, raw local paths, or private transcript
  content in diagnostics.
- Avoid vague test labels. Use realistic domain-neutral records.

## Current Prototype Draft

The active prototype draft is the Figma v8 page
`030 MVP Experience v8 - Clean RU` (`341:2`) in
[https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr](https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr).
It contains 17 visible top-level frames organized as workspaces and states, not
equal destinations. V8 keeps one default meeting cockpit and adds the final
clean Russian handoff coverage: compact provider sign-in, guided macOS
permissions, desktop meeting workspace, detected-meeting prompt, active
recording as a pinned menu-bar/header state, inline upload/status/search/filter
inside the cockpit, review with speaker assignment lanes, fuller settings,
full web list/detail screens, shared upload sheet, command search/filter
overlay, share/export/delete governance, dark mode, light proof, and component
QA rules. Current draft QA: frame-bound overflow
`0`, bad button heights `0`, bad chip heights `0`, visible forbidden
implementation copy `0`, placeholder artifact nodes `0`, button heights
`36/40`, chip height `28`.

The first v7 page `030 MVP Experience v7 - IA rebuilt RU` remains historical
IA evidence only. It introduced the meeting-workspace model but was superseded
by the v7.1 fix-pass for first-run composition, menu-bar invariants, active
embedded review, governance, and light critical states. V7.1 was superseded by
v7.2 for pixel polish, denser auth/permissions/settings composition, and
repaired prototype links. V7.3 preserved much of that polish but failed the
deep product-flow review; v7.4 superseded it by making recording a shell state,
moving upload/search/processing into the meeting cockpit, strengthening
settings, and removing technical/Latin UI leaks. V8 supersedes v7.4 as the
current clean Russian review candidate for web/detail/governance, settings,
light proof, and component QA.

The v6 page `030 MVP Experience v6 - Krisp-grounded RU` remains historical
mechanical evidence only. It fixed some v5 defects but was rejected by
stakeholder review because the IA, settings, auth, active-recording model,
upload/processing model, density, theme switching, and auto-detection policy
were still insufficient.

## Historical Prototype V2 Frame Plan

Replace the rough first Figma page with a v2 page named:

`030 MVP Experience v2 - Cabinet First`

The final handoff is not limited to 14 screens. The 14 primary frames are the
clickable executive walkthrough. A complete MVP design also requires supporting
state/detail boards for implementation.

Primary clickable flow frames:

1. `V2 Cover - Product Decision` (`1440 x 900`)
2. `V2 Desktop - Ready Cabinet` (`1080 x 760`)
3. `V2 Desktop - Active Recording` (`1080 x 760`)
4. `V2 Desktop - Upload And Processing` (`1080 x 760`)
5. `V2 Desktop - Permission Recovery` (`1080 x 760`)
6. `V2 Tray - Mini Controller` (`360 x 520`)
7. `V2 Web - Meetings List` (`1440 x 900`)
8. `V2 Web - Manual Upload` (`1440 x 900`)
9. `V2 Web - Processing Status` (`1440 x 900`)
10. `V2 Web - Meeting Review Complete` (`1440 x 900`)
11. `V2 Web - Degraded Deleted Access` (`1440 x 900`)
12. `V2 Settings - Account Workspace Policy` (`1440 x 900`)
13. `V2 Matrix - Native Web Route Boundary` (`1440 x 900`)
14. `V2 System - Components And States` (`1440 x 900`)

Supporting state/detail boards:

15. `V2 Detail - Desktop Signed Out Offline Policy`
16. `V2 Detail - Desktop Embedded Review Read Mode`
17. `V2 Detail - Desktop Upload Error Drawer`
18. `V2 Detail - Web Search Command Palette`
19. `V2 Detail - Web Filters Sort Upcoming`
20. `V2 Detail - Web Meeting Row Variants`
21. `V2 Detail - Web Share Access Modal`
22. `V2 Detail - Web Export Download Menu`
23. `V2 Detail - Web Delete Confirmation Lifecycle`
24. `V2 Detail - Web AI Drawer Scopes`
25. `V2 Detail - Web Tags Activity Actions`
26. `V2 Detail - Web Empty States`
27. `V2 Detail - Browser Only Handoff Catalog`
28. `V2 Detail - Account Security Session Modals`
29. `V2 Detail - Upload Validation Errors`
30. `V2 Detail - Processing Failure Recovery`
31. `V2 Detail - Localization Copy Board`
32. `V2 Detail - Accessibility Focus Board`

Prototype path:

`Cover -> Desktop Ready -> Active Recording -> Upload Processing -> Web
Processing -> Web Review -> Degraded/Deleted -> Settings -> Matrix`.

Critical visual changes from v1:

- Desktop first screen contains the cabinet list, not a diagnostics card.
- Active recording is a native pinned strip above embedded cabinet.
- Meeting list is row-based and dense.
- Upload and processing states are stage-based.
- Status copy and source provenance are visible.
- Browser-only surfaces are represented as handoff markers, not embedded app
  clutter.

## Launch Follow-Up Slices

Required implementation sequence after design approval:

1. Desktop shell redesign and embedded cabinet host.
2. Server cabinet MVP routes: meetings list, upload, processing, review.
3. Cross-surface status API contract for desktop/web consistency.
4. Manual media upload end to end.
5. MediaScribe processing result import and review rendering.
6. Deletion/retention truth and first deletion report.
7. Browser-only admin/share/download/deletion routes as later polish.

## Historical V2 Review Gate

The design is ready for implementation planning only when:

- Figma v2 matches this blueprint.
- Figma v2 includes 14 primary clickable frames plus supporting state/detail
  boards for implementation coverage.
- Screen docs reference this blueprint instead of v1 generic language.
- Route matrix classifies every desktop/browser route.
- Status matrix maps every lifecycle state to desktop and web copy.
- Brand-distance review confirms zero copied Krisp expression.
- The user approves the v2 cabinet-first direction.
