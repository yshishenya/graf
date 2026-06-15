# Krisp V8 Window Capture Audit

Date: 2026-06-13
Updated: 2026-06-15
Scope: current live Krisp web cabinet evidence and locally installed Krisp
desktop app. This addendum supplements the earlier full navigation audit.

## Capture Method

- 2026-06-13 historical pass: full-screen macOS capture returned only wallpaper
  because screen capture privacy was restricted in that environment.
- 2026-06-13 historical pass: `System Events` UI automation for clicking
  windows was blocked by macOS Accessibility permissions for `osascript`.
- 2026-06-13 historical pass: `CGWindowList` via Swift successfully identified
  and captured the visible Krisp/Zen windows by window id.
- 2026-06-15 live pass: Codex `computer-use` became available after the user
  granted Accessibility to Codex and restarted the app. It returned both window
  screenshots and accessibility trees for the running Krisp desktop app.
- 2026-06-15 live pass: `computer-use` can inspect and safely navigate the
  locally installed Krisp desktop app. It cannot use Zen on `app.krisp.ai`
  because Computer Use policy blocks that browser URL.
- Temporary screenshots and accessibility trees may contain private meeting
  names, transcript fragments, contact names, and account data. They are used
  only as local evidence and are not copied into the repository.

Captured windows:

- Zen web window: owner `Zen`, title `Meeting notes`, 1800 x 1038 logical px.
- Krisp desktop window: owner `krisp`, title `Krisp`, 1800 x 1038 logical px.
- Krisp notification overlay: owner `krisp`, title `Krisp Notification`.

## Observed Web Cabinet IA

- The main product workspace is the meeting list, not settings or diagnostics.
- A persistent left navigation contains workspace/account, invite/team entry,
  search, meetings, shared meetings, action items, activity, contacts, settings,
  app/developer links, plan/reactivation, and the account switcher.
- The center workspace combines upcoming meetings, meeting-note rows, list
  controls, status icons, dates, and a bottom contextual AI/search prompt.
- Search/filter/sort/list actions are adjacent to the meeting list. They are not
  separate first-level destinations.
- Account/plan state can appear as a banner, but it should not block access to
  past meetings. For 2brain self-hosted MVP, the equivalent should be a compact
  workspace/sync/account state, not a large marketing/trial banner.

## Observed Desktop IA

- Krisp desktop mirrors the web cabinet meeting workspace in the center.
- It adds a right-side live controls rail for meeting/audio behavior. That rail
  contains AI note-taker mode, accent conversion, noise cancellation, device
  pickers, test run, limited mode, and upgrade.
- The desktop app is not only a tiny recorder widget; it is a product workspace
  with native shell affordances.
- The right rail is specific to Krisp's noise/accent product and must not be
  copied. For 2brain Rec, the analogous desktop-native value is a compact
  recording trust rail/strip: current source, timer, meters, local save truth,
  one-action Stop, and sync/local-queue status.

## Clean-Room IA Lessons For 2brain

- Default surface: meeting workspace with dense rows and real statuses.
- Desktop-specific layer: native recording trust strip/menu-bar state, not a
  full recording page.
- Web-owned product routes: meeting list, upload sheet, processing/status row,
  review, speaker assignment, share/export/delete, settings/admin.
- Native-owned routes: capture start/stop, permissions, local buffer/queue
  truth, menu bar, OS recovery, diagnostics.
- Upload and processing belong inside the meeting workspace as row/sheet states.
- Speaker assignment belongs inside the review workspace, with one lane per
  speaker and backend-owned save/conflict truth.
- Settings should be a real workspace, but not the default first screen.

## 2026-06-15 Computer-Use Desktop Live Pass

Safe Krisp desktop interactions verified through `computer-use`:

- Meeting list navigation opened the same `desktop.krisp.ai/meeting-notes`
  workspace inside the desktop shell.
- The meeting list uses dense rows with title, duration, date, source/status
  icons, and compact list actions. Upload/status/search/filter actions are near
  the list, not standalone first-level screens.
- Global search opens a command/search overlay above the current workspace with
  a search field, recent results, and keyboard affordance. It does not replace
  the meeting list route.
- The filter button opens a compact menu with categories such as starred, date,
  contains, company, type, and tags. Filters are list-level controls rather than
  separate navigation destinations.
- Meeting detail keeps the meeting as the central object: title, exact date and
  time, contextual actions, `Notes`, and `Recording & Transcript`.
- `Notes` contains action items and key points with timestamp links. This
  confirms that MVP value after transcription is not only a raw transcript; the
  review surface must make decisions/actions/outcomes easy to scan.
- `Recording & Transcript` includes timestamped turns, speaker labels, a sticky
  playback area, and a speaker assignment entry.
- Speaker evidence renders as separate horizontal lanes per speaker with
  colored segments and talk-time percentages. For 2brain, speaker assignment in
  desktop must be an embedded server-owned review route with one lane per
  speaker, not a native macOS-only control.
- Settings open as a list-detail console. The left settings IA groups account,
  workspace, meeting assistant, audio, and app behavior/system.
- `AI Note Taker` settings group automatic start, automatic meeting-page open,
  title/summary generation, excluded apps, templates, and sharing policy.
- `Privacy & Consent` separates participant notification, visible consent
  badge, bot/participant recording mode, and storage location. For 2brain, the
  equivalent must be owner-server storage truth, visible recording indicator,
  local buffer truth, consent/notification wording, and bounded deletion copy.
- `App` settings include links opening behavior, widget visibility, appearance
  (`Light`, `Dark`, `System`), launch at startup, opening the desktop app, and
  updates. For 2brain, theme selection must be a compact segmented control:
  `Системная`, `Тёмная`, `Светлая`.
- `Calendar` settings control connected calendar, which events count as
  upcoming, tray visibility, and menu-bar event detail. For 2brain, this maps to
  meeting detection policy and menu-bar status, not to a separate first-run
  screen.
- `Notifications` include upcoming meeting reminders, meeting recap, on/off
  state indicator, and device setup reminders. For 2brain, notification settings
  should cover detected-meeting prompt, finished transcript, failed upload, and
  active recording reminder.

Clean-room implications confirmed by live desktop interaction:

- Keep `Встречи` as the first useful surface in both desktop and web.
- Treat `Запись`, `Загрузка`, `Транскрибация`, `Готов транскрипт`, and
  `Нужны говорящие` as states of one meeting object.
- Keep search/filter/upload/status inside the meeting workspace.
- Keep active recording in native chrome/menu-bar with one visible stop action.
- Keep broad settings as a list-detail workspace with clear groups instead of
  one large mixed settings card.
- Keep risky governance actions in the browser cabinet.

## Remaining Constraint

`computer-use` is allowed for the locally installed Krisp desktop app, but it
ended the session when pointed at `app.krisp.ai` in Zen because that browser URL
is not allowed for Computer Use. Current web-cabinet evidence therefore comes
from:

- earlier safe web navigation and window-capture audits;
- Krisp desktop embedded web routes;
- direct Figma/code property QA;
- public standards and product docs;
- clean-room synthesis without copying Krisp assets, copy, icons, private data,
  or exact layout.
