# Five-Critic Synthesis

Date: 2026-06-13 / updated 2026-06-14
Scope: stakeholder-rejected v6 review, first v7 direction, v7.1 fix-pass, and
v7.2 pixel-polish pass, v7.3 failure review, and v7.4 Krisp IA correction.

## V7.3 Failure And V7.4 Correction Pass

V7.3 was useful because it made the remaining weaknesses visible, but it is not
accepted for handoff. Five critics converged on these blockers:

- active recording still read like a separate destination instead of a native
  header/menu-bar state;
- queue/upload/search/status were still too close to top-level products instead
  of compact meeting-list actions and row states;
- settings were not deep enough for a self-hosted multiplatform recorder;
- auth/local mode still needed clearer provider-first and policy-gated framing;
- speaker assignment was present but did not feel like a primary review mode;
- share/export/delete needed clearer browser-owned governance and deletion
  truth;
- button and tab sizing needed another property-level pass.

V7.4 corrections:

- Default surface is the meeting cockpit in desktop and web.
- Active capture appears through header/menu-bar/pinned strip states, not a
  full page.
- Upload creates or updates a meeting row from the cockpit instead of opening a
  separate product area.
- Processing is represented by status chips, row progress, and review readiness
  inside the meeting workspace.
- Settings use a list-detail console covering appearance, recording, detection,
  storage, access/deletion, diagnostics, workspace policy, and theme.
- Speaker assignment is a review tab/mode with one separate lane per speaker in
  dark, light, and active embedded-review frames.
- Share/export/delete are grouped as browser-owned governance actions.
- Auth is compact, provider-first, and local mode is policy-gated rather than
  a peer primary path.

Historical v7.4 QA result before V8:

- visible frames: 16;
- button candidates: 99;
- button issues: 0;
- wrapped button text: 0;
- forbidden top-level nav entries: 0;
- technical-copy leaks: 0;
- Latin/English visible UI hits: 0;
- invalid prototype destinations: 0;
- valid cross-frame reactions: 13;
- speaker lanes: 4 separate lanes in dark review, light review, and active
  embedded review.

Remaining gate:

- final stakeholder visual approval.

## V7.2 Pixel-Polish Pass

After visual inspection of the v7.1 contact sheet, v7.2 was created as a
separate Figma page so v7.1 remains review evidence. V7.2 keeps the same
product architecture but improves visible composition, wording, and prototype
links.

Applied fixes:

- IA map: rebuilt cramped cards and dense arrow chain into a clearer platform
  boundary plus 3-by-3 owner value loop.
- Auth: reduced the sign-in panel, removed the oversized explanatory headline,
  made work email/SSO/Yandex the primary choices, and kept local mode as a
  policy escape hatch instead of a primary product path.
- Permissions: replaced a sparse status screen with guided Mac permission steps,
  a visual system-settings guide, and a compact UX checklist.
- Settings: replaced the thin single-panel settings view with a fuller
  workspace covering appearance, recording, detection, upload/storage,
  access/deletion, diagnostics, and workspace boundaries.
- Navigation: removed/deferred global `Действия`; upload/search/processing stay
  inside the meeting workspace.
- Prototype: repaired cloned v7.2 cross-frame links and removed fake same-frame
  navigation for inline upload states.
- Copy: removed remaining visible technical/English UI labels from product
  frames.

Current v7.2 QA result:

- visible frames: 16;
- buttons: 64;
- button token issues: 0;
- technical-copy leaks: 0;
- English UI hits: 0;
- forbidden top-level nav entries: 0;
- invalid prototype destinations: 0;
- valid cross-frame reactions: 34;
- speaker lanes: 4 tracks, 12 segments, 4 talk-time percentages in review,
  light review, and active embedded review.

Remaining gate:

- final stakeholder visual approval.

## V7.1 Five-Critic Fix-Pass

The five-critic review was rerun against the v7.1 contact sheet and Figma node
properties. The result is a polish candidate, not final stakeholder approval.

Applied fixes:

- IA/product flow: top-level `Загрузки` became `Очередь`, global `Действия`
  is hidden/deferred, and search/upload/processing remain inside the meeting
  cockpit instead of becoming separate products.
- Visual density/layout: the old mini light-proof board was removed from the
  active visible frame set; separate full-size light proof frames now cover
  meeting workspace, review, settings, and critical states. Programmatic audit
  finds 68 buttons with allowed heights `32/36/40`, radius `6`, and no overflow.
- macOS/native UX: added `V7.1 10 - Menu bar controller proof`, changed
  misleading sync copy to local/queue truth, and added `V7.1 11 - Active
  recording over embedded review` so native Stop is visible above embedded web.
- Web cabinet/governance: added `V7.1 12 - Share export delete governance`
  with scoped access, export formats, audit implication, and truthful deletion
  copy across local copy, transcript/notes/uploaded file, backups/diagnostics,
  and external transcription policy.
- Auth/settings/onboarding/policy: provider order now starts with work email and
  SSO, local mode is framed as `Продолжить локально` with user-facing
  consequence, and light critical states cover auth, permissions, upload, and
  meeting detection.

Current v7.1 QA result:

- visible frames: 16;
- buttons: 68;
- overflow: 0;
- technical-copy leaks: 0;
- English UI hits: 0;
- invalid prototype destinations: 0;
- valid cross-frame reactions: 10;
- speaker lanes: 4 tracks, 12 segments, 4 talk-time percentages in review,
  light review, and active embedded review.

Remaining gate:

- final stakeholder visual approval.

## Overall Verdict

All five critics originally converged on the same issue: v6 passed narrow
mechanical QA but still behaved like a coverage board. It had too many peer
screens, too many centered state cards, too much empty space, and not enough
stable product IA. V7 rebuilt the prototype around persistent workspaces and
state variants; v7.1 applies the subsequent critic fixes.

## Critic Findings

### Critic 1: IA And Product Flow

Key finding:

- Search, filters, upload, processing, notes, speakers, share, export, delete,
  and browser handoff should not all become equal product destinations.

Accepted v7 decisions:

- Use 12 screen families, not 29 equal product screens.
- Search/filter live inside the meetings page.
- Processing is a meeting row state plus expandable detail.
- Active recording is a shell state, not a destination.
- Meeting review owns transcript, notes, speakers, AI, governance actions, and
  source/status context.

### Critic 2: Visual Density And Layout

Key finding:

- V6 feels sparse and small even where the node audit is "clean".

Accepted v7 decisions:

- Buttons:
  - primary: 40 px high, radius 6, min 120 px;
  - secondary: 36 px high, radius 6, min 96 px;
  - toolbar/filter/tab: 32 px high, radius 6;
  - chips/status: 24-28 px high;
  - icon buttons: 32 x 32.
- Dense rows:
  - browser rows: 64 px;
  - desktop embedded rows: 60 px.
- Data screens must fill at least about two-thirds of the vertical content area
  at 1440 x 900. If there are few rows, show processing-now, recent uploads, or
  compact recovery content.
- Settings need a two-column layout, not a narrow card floating in dark space.
- Auth should be a compact 420-480 px sheet/panel.

### Critic 3: macOS Native UX

Key finding:

- V6 still feels like a dark web admin shell with a recording page bolted on.

Accepted v7 decisions:

- Active recording appears in three places:
  1. menu bar item;
  2. toolbar/header native strip;
  3. tray/menu-bar popover.
- No dedicated full "active recording page" in the happy path.
- Red is limited to recording dot, timer, and Stop action.
- Permission onboarding is native SwiftUI and guided through macOS Privacy &
  Security paths.
- Native owns Record, Stop, active indicator, elapsed timer, meters, permission
  recovery, local buffer/queue truth, menu bar, diagnostics, and route guard.
- Embedded web owns meetings, transcript review, notes, speaker assignment,
  processing after server acceptance, and upload UI after native framing.

### Critic 4: Web Cabinet And Krisp IA

Key finding:

- The web cabinet should be a meeting library cockpit, not a menu of separate
  tools.

Accepted v7 decisions:

- Left nav:
  - keep `Встречи`;
  - keep `Настройки`;
  - defer/hide `Действия` until global action items exist;
  - remove top-level `Загрузка`, `Поиск`, and `Processing`.
- Top bar:
  - page title, count, last sync;
  - search field;
  - compact status chip;
  - `Открыть приложение`;
  - primary `Загрузить`;
  - account menu.
- Meeting table columns:
  - title;
  - source/provenance;
  - people/owner;
  - duration;
  - status;
  - updated/date;
  - next action;
  - overflow.
- Upload opens modal/drawer and immediately creates a meeting row.
- Status chips include local, queue, upload, extracting audio, transcription,
  transcript ready, notes ready, partial, failed, no access, and bounded deleted.

### Critic 5: Auth, Settings, Onboarding, Auto-Detection

Key finding:

- V6 lacks a trustworthy first-run and settings model for a self-hosted,
  multiplatform recorder.

Accepted v7 decisions:

- First-run begins with `Подключите рабочую область`, not a large generic sign
  in/local choice.
- Provider-first auth:
  - `Войти через Yandex ID`;
  - `Войти через VK ID`;
  - `Войти через Telegram`;
  - secondary `Войти по email`.
- Local recording is not a peer primary action. It appears in a disclosure only
  if cached/workspace policy allows it.
- Workspace selection shows recording policy summary.
- Guided permissions steps:
  - microphone;
  - system audio;
  - meeting notifications;
  - local storage;
  - readiness check.
- Auto-detect default is `Спрашивать перед записью`.
- Auto-recording is disabled/internal until false-positive, participant notice,
  policy, and safety evidence exist.

## Required V7 Screen Families

1. Entry and workspace policy.
2. Compact provider/email sign-in.
3. Workspace selection and policy summary.
4. Guided macOS permissions.
5. Desktop meeting workspace ready.
6. Desktop recording shell state.
7. Menu bar controller states.
8. Browser meeting library cockpit.
9. Upload drawer and validation states.
10. Meeting lifecycle/status row and expanded detail.
11. Meeting review workspace.
12. Speaker assignment mode.
13. Governance actions: share/export/delete.
14. Settings workspace.
15. Theme proof: dark/light/system.
16. Implementation appendix: route matrix, tokens, QA gates.

## V7 Acceptance Gates

- V6 is not an implementation handoff target.
- No top-level search/upload/processing nav in the primary cabinet.
- No dedicated active-recording full page in happy path.
- No visible implementation ownership labels in product screens.
- Every meeting row has date/time, status, and next action.
- Upload and processing appear as meeting lifecycle states.
- Settings include account, workspace/server summary, appearance, recording,
  detection, notifications, storage/queue, privacy/deletion, and diagnostics.
- Theme switch exists and at least three light-mode product screens exist.
- Five-critic review must be rerun after Figma v7 is created.
