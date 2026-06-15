# Contract: Prototype And Handoff Evidence

## Purpose

Define the minimum evidence required for the visual prototype to be accepted as
implementation-ready input while keeping repository Spec Kit artifacts as the
product source of truth.

## Preferred Source

Figma is preferred for:

- static visual pack;
- design system components/tokens;
- clickable key flows;
- review comments and visual iteration.

The design should stay compatible with a free Figma account when possible.

## V8 Acceptance Evidence Required

- Figma file: [https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr](https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr)
- File key: `ylPz3AxOOfVoLJEG4dF9Yr`
- Active v8 page: `030 MVP Experience v8 - Clean RU`
- Active v8 page id: `341:2`
- Required active v8 flow model: compact provider sign-in, guided macOS
  permissions, desktop meeting workspace, detected-meeting prompt, active
  recording menu-bar/header state, inline upload and processing, transcript
  review, speaker assignment lanes, settings with recording/theme/source
  policy, full web meetings list, command search/filter overlay, shared media
  upload sheet, full web meeting detail, browser-owned share/export/delete,
  light-theme proof, and component/QA rules.
- Current v8 QA result: all 17 visible frames audited with frame-bound overflow
  `0`, bad button heights `0`, bad chip heights `0`, visible forbidden
  implementation copy `0`, placeholder artifact nodes `0`, English
  UI/review-copy leaks `0`, and text overlap `0`; buttons use `36/40px`,
  compact segmented/theme controls use `32px`, and chips use `28px`.
- Current v8 clickable result: 98 valid `ON_CLICK` reactions across 98 nodes,
  `invalidDestinationCount=0`, `selfLinkCount=0`, and
  `supersededDestinationCount=0`; every destination is a visible V8 frame and
  required owner-value-loop coverage passes.
- Current v8 five-critic result:
  `design/reviews/v8-clean-ru-2026-06-15/five-critic-screen-audit.md` passes
  all 17 frames through product-flow, IA, visual/UI, platform, and
  content/trust lenses.
- Current v8 stakeholder approval pack:
  `design/reviews/v8-clean-ru-2026-06-15/stakeholder-visual-approval-pack.md`
  defines the required human review script, direct frame links, reject
  criteria, and approval decision template.
- Superseded v5 page: `030 MVP Experience v5 - Full MVP Flow`
- Superseded v5 page id: `17:2`
- Superseded v6 page: `030 MVP Experience v6 - Krisp-grounded RU`
- Superseded v6 page id: `118:2`
- Superseded v7 page: `030 MVP Experience v7 - IA rebuilt RU`
- Superseded v7 page id: `137:2`
- Superseded v7.1 page: `030 MVP Experience v7.1 - Krisp IA polish RU`
- Superseded v7.1 page id: `143:2`
- Superseded v7.2 page: `030 MVP Experience v7.2 - Pixel polish RU`
- Superseded v7.2 page id: `158:2`
- Superseded v7.3 page: `030 MVP Experience v7.3 - Screen-by-screen polish RU`
- Superseded v7.3 page id: `177:2`
- Superseded v7.4 page: `030 MVP Experience v7.4 - Superseded by v8`
- Superseded v7.4 original page id: `210:2`
- Superseded pages: `030 MVP Experience`, `030 MVP Experience v2 - Cabinet First`,
  `030 MVP Experience v3 - Dark RU`, `030 MVP Experience v4 - SDS + macOS 26`.
- Historical v7 flow model: workspace connection, compact provider auth,
  workspace/policy selection, guided permissions, desktop meeting workspace,
  detected-meeting prompt, recording shell state, menu-bar controller, web
  meeting library cockpit, integrated upload drawer, lifecycle/status row,
  meeting review, speaker assignment, governance actions, settings, meeting
  detection policy, and light-theme proof.
- Historical v5 frame count: 36 top-level frames, including proof frames for
  desktop embedded speaker assignment and active recording over embedded web.
- Historical product prototype reactions: 82 button `ON_CLICK` reactions, 130 sidebar/nav
  `ON_CLICK` reactions, and 8 meeting-row/status-pill reactions.
- Historical layout QA: `appOverflowCount=0`; superseded by 2026-06-13
  re-audit blockers.
- Historical v6 QA requirement: no same-row adjacent button cluster with mixed
  height/radius; no product first viewport with implementation labels; one lane
  per speaker in browser and embedded desktop; active native stop visible above
  every embedded route; Russian dark screenshots reviewed after node-property
  audit.
- Historical v6 result: `frameCount=29`, `totalButtons=70`,
  `buttonClusterIssues=0`, `technicalCopyHits=0`, `overflowCount=0`,
  `reactionNodeCount=183`, `totalReactions=183`, and `reactionIssues=0`;
  speaker review frames each include 4 tracks, 10 segments, and 4 talk-time
  percentages.
- Superseded v7 draft result: `frameCount=19`, `totalButtons=95`, button heights
  `32/36/40`, button radius `6`, `overflowCount=0`,
  `technicalCopyLeaks=0`, `forbiddenTopLevelNav=0`, `reactionIssues=0`.
- Superseded v7 speaker review frames each include 4 tracks, 10 segments, and 4
  talk-time percentages.
- Superseded v7.1 fix-pass result: `visibleFrameCount=16`, `buttons=68`, button
  heights `32/36/40`, button radius `6`, `buttonIssueCount=0`,
  `overflowCount=0`, `technicalCopyLeaks=0`, `englishHitCount=0`,
  `reactionIssueCount=0`, 10 valid cross-frame prototype reactions, and
  separate light proof frames for meeting workspace, review, settings, and
  critical states.
- Superseded v7.1 status: five-critic fix-pass applied, then superseded by
  v7.2 for pixel polish, denser first-run composition, settings depth, and
  clickable-flow repair.
- Superseded v7.1 added proof: menu-bar controller states, active recording above
  an embedded review route, and share/export/delete governance actions.
- Superseded v7.1 speaker review frames each include 4 tracks, 12 segments, and 4
  talk-time percentages.
- Superseded v7.2 polish result: `visibleFrameCount=16`, `buttons=64`, button
  heights `32/36/40`, button radius `6`, `buttonIssueCount=0`,
  `technicalCopyLeaks=0`, `englishHitCount=0`, `forbiddenTopLevelNav=0`,
  `reactionIssueCount=0`, and 34 valid cross-frame prototype reactions.
- Superseded v7.2 status: pixel-polish evidence only after v7.3/v7.4.
- Superseded v7.2 added polish: rebuilt IA map without cramped text, compact
  provider auth, guided macOS permissions with visual system-settings guide,
  richer settings workspace, removed/deferred global `Действия` nav, and
  repaired v7.2 prototype links.
- Superseded v7.2 speaker review frames each include 4 tracks, 12 segments, and 4
  talk-time percentages.
- Superseded v7.3 status: failed five-critic handoff review because the
  product flow still overemphasized queue/upload, active recording behaved like
  a destination, settings were too thin, and speaker assignment/governance were
  not yet strong enough.
- Superseded v7.4 correction result: `visibleFrameCount=16`,
  `buttonCount=99`, button heights `36/40`, `buttonIssueCount=0`,
  `wrappedButtonTextCount=0`, `forbiddenNavCount=0`,
  `technicalHitCount=0`, `latinHitCount=0`, `reactionNodeCount=13`,
  `totalReactions=13`, and `reactionIssueCount=0`.
- Superseded v7.4.1 geometry result: `V7.4 04`, `V7.4 05`, and `V7.4 08A`
  have `statusActionIssues=0`; detected-meeting prompt is inline with the
  current recording state; compact desktop hides access details from the table;
  wide dark/light cockpit keeps access inside the widened table.
- Superseded v7.4.2 focused polish result: target frames `06`, `07`, `08B`,
  `08C`, `10`, `11`, `12`, and `13` have no visible `Переим.`,
  `локальная копия`, native/server/route/api labels; dark/light settings use
  the corrected settings-dashboard overlays; old settings underlayers are
  hidden from handoff; talk-time percentages are readable in dark, light, and
  active speaker-lane frames; active recording uses a compact native status
  strip over the embedded review route.
- Superseded v7.4.5 shell/menu-bar result: visible technical-copy leaks for
  native/server/route/api/worker/`локальная копия` are `0`; active-recording
  visible `Записать` actions are `0`; button heights remain `36/40`; the
  menu-bar controller is a compact `Готово`/`Идет запись`/`Офлайн` state model
  with `Стоп` first while active; active recording over the embedded cabinet
  uses one compact status pill plus persistent `Стоп`, with old overlapping
  strip/tab layers hidden.
- Superseded v7.4.6 settings IA/depth result: dark settings `V7.4 07` and light
  settings `V7.4 08C` are rebuilt as dense settings consoles with subnav, main
  work area, and governance rail; theme controls explicitly include
  `Системная`, `Темная`, and `Светлая`; recording policy uses `Спрашивать`,
  `Авто выбранные`, and `Вручную`; source controls and meeting detection apps
  are visible without clipped Russian labels; owner signals distinguish
  `на Mac`, `кабинет`, `В приложении`, `В кабинете`, and `В браузере`; final
  focused audit found visible stale settings layers `0`, technical-copy leaks
  `0`, action button heights `36/40`, segmented controls `32px`, toggles
  `24px`, control label overflow `0`, and frame-bound overflow `0`.
- Superseded v7.4.7 governance/light-critical result: `V7.4 12` is rebuilt around
  meeting context, date/time, duration, source, participants, share/export
  actions, truthful deletion scope, and audit trace; `V7.4 13` is rebuilt into a
  dense light-theme proof for sign-in, permissions, upload, meeting detection,
  active recording, deletion, and light-theme control rules; focused audit found
  visible technical-copy leaks `0`, action button heights `40px`, chip heights
  `28px`, control label overflow `0`, and frame-bound overflow `0`.
- Superseded v7.4.8 whole-page geometry result: all 16 visible V7.4 frames were
  audited; visible technical-copy leaks are `0`; button-height issue frames are
  `0`; button label-bound issue frames are `0`; frame-bound overflow frames are
  `0`; row-action text-frame overflow in `V7.4 04`, `V7.4 05`, and
  `V7.4 08A` was fixed without changing visible table composition; final
  screenshots are saved as `/tmp/2brain-figma-v74-qa/v748-04-detected-final.png`,
  `/tmp/2brain-figma-v74-qa/v748-05-cockpit-final.png`, and
  `/tmp/2brain-figma-v74-qa/v748-08a-light-cockpit-final.png`.
- Superseded v7.4.9 desktop workspace density result: `V7.4 03 - Desktop meeting
  workspace` now uses a denser 9-row meeting table with date/time, source,
  participants, status, and row action visible; upload, network, processing,
  and speaker-assignment statuses remain integrated into the meeting list
  rather than becoming separate top-level routes; a compact `Очередь обработки`
  rail summarizes processing state in the right column; focused audit found
  button heights `36/40`, button label overflow `0`, visible technical-copy
  leaks `0`, frame-bound overflow `0`, max vertical gap `60`, and table height
  `560`; final screenshot is saved as
  `/tmp/2brain-figma-v74-qa/v749-03-desktop-workspace-density-final.png`.
- Superseded v7.4.10 cockpit/upload density result: dark `V7.4 05 - Meeting
  cockpit with upload` and light `V7.4 08A - Light meeting cockpit` keep upload
  as local cockpit context instead of a standalone upload route; both frames
  now use 8-row meeting tables with date/time, source, participants, status,
  action, and access columns visible; table height is `504` in both frames;
  focused audit found 15 action buttons per frame, button heights `36/40`, bad
  action-button heights `0`, action label overflow `0`, visible technical-copy
  leaks `0`, frame-bound overflow `0`, max vertical gap `38`, and wrapped
  speaker-needed copy `0`; final screenshots are saved as
  `/tmp/2brain-figma-v74-qa/v7410-05-cockpit-density-final2.png` and
  `/tmp/2brain-figma-v74-qa/v7410-08a-light-cockpit-density-final2.png`.
- Superseded v7.4.10 whole-page semantic follow-up result: all 16 visible V7.4
  frames were re-audited after the cockpit/upload density pass; forbidden
  technical copy frames = `0`, bad action-button-height frames = `0`,
  action-label overflow frames = `0`, and frame-bound overflow frames = `0`;
  the corrected density frames hold at max gaps `60` for `V7.4 03` and `38`
  for both `V7.4 05` and `V7.4 08A`; remaining product-density review is
  narrowed to `V7.4 06` and `V7.4 08B`.
- Superseded v7.4.11 review/speaker-assignment density result: dark
  `V7.4 06 - Review speaker assignment` and light `V7.4 08B - Light review
  speakers` are rebuilt as dense speaker-review workspaces; both frames show 9
  transcript rows, 4 separate speaker lanes, 16 speaker segments, contextual
  save/cancel/browser actions, selected-segment assignment, and
  merge/split/new-speaker actions; old global upload/record/open actions are
  hidden from this route; focused audit found action button heights `36/40`,
  bad action-button heights `0`, action label overflow `0`, visible
  technical-copy leaks `0`, frame-bound overflow `0`, max vertical gap `172`,
  and selected-segment controls fully inside the side panel; screenshot review
  found and fixed wrapping warning chips and light secondary-button contrast;
  final screenshots are saved as
  `/tmp/2brain-figma-v74-qa/v7411-06-review-density-final2.png` and
  `/tmp/2brain-figma-v74-qa/v7411-08b-review-light-density-final3.png`.
- Superseded v7.4.11 whole-page semantic follow-up result: all 16 visible V7.4
  frames were re-audited after the speaker-review density pass; forbidden
  technical copy frames = `0`, bad action-button-height frames = `0`,
  action-label overflow frames = `0`, and frame-bound overflow frames = `0`;
  `V7.4 06` and `V7.4 08B` hold at max vertical gap `172`, and no product
  screen remains in the large-gap candidate list.
- Superseded v7.4.12 first-run/detected-meeting correction result: `V7.4 01`,
  `V7.4 02`, and `V7.4 04` were rebuilt for compact provider auth, visual
  guided macOS permissions, and inline auto-detected meeting decision flow;
  focused audit found button heights `36/40`, chip heights `28`, bad button
  heights `0`, bad chip heights `0`, visible technical-copy leaks `0`,
  clipped nodes `0`, and frame-bound overflow `0`; final screenshots are saved
  as `/tmp/2brain-figma-v74-qa/v7412-01-auth-final.png`,
  `/tmp/2brain-figma-v74-qa/v7412-02-permissions-final.png`, and
  `/tmp/2brain-figma-v74-qa/v7412-04-detected-final2.png`.
- Current v8 status: implementation baseline for the first real UI slice.
  Stakeholder visual acceptance remains the final polish gate, but it no
  longer blocks starting desktop/web interface development from this baseline.
- Superseded v7.4 added correction: meeting cockpit as default surface, compact
  provider auth, guided permissions, inline upload/status, real settings
  console, auto-detect policy, menu-bar controller, active recording over
  embedded cabinet, browser-owned share/export/delete, and dedicated light
  proof frames.
- Superseded v7.4 speaker review frames include 4 separate speaker lanes in dark
  review, light review, and active embedded review.
- Kit evidence: SDS Upload live instance in the product upload screen plus SDS
  Button, Search, Input Field, Tag, and Switch Field samples in the component
  map.
- Apple macOS 26 status: selected native kit reference; real Apple instances
  require manual Figma library attachment because MCP import was not permitted.
- Primary MVP theme: dark.
- Primary MVP language: Russian.
- Repository handoff: `design/prototype/figma-handoff.md`,
  `design/screen-inventory.md`, `design/validation-evidence.md`.

## Fallback Source

StitchFlow may be used when Figma access, plan limits, connector availability,
or workflow friction blocks delivery.

When StitchFlow is used, record:

- Stitch project id;
- screen ids and names;
- `DESIGN.md` upload/design-system status;
- exported screenshots;
- exported HTML/code checkpoint path;
- prototype/linking status;
- `download-project.json` or equivalent manifest path;
- warnings, missing screens, and external runtime dependencies.

## Repo Handoff Requirements

External design/prototype artifacts must be mirrored by repository references:

- screen inventory;
- owner value loop flow;
- route visibility matrix;
- cross-surface status model;
- component inventory;
- copy/status principles;
- accessibility and localization notes;
- clean-room brand-distance review;
- launch backlog map.

## Required Prototype Paths

The clickable prototype must cover:

1. First-run/sign-in or signed-out local policy state.
2. Desktop idle/ready state.
3. Active recording and one-action stop.
4. Recording stopped and local saved/queued status.
5. Upload queue/current status in app and web.
6. Embedded cabinet subset entry.
7. Manual upload for audio and common video/meeting file.
8. Audio extraction/transcription in progress.
9. Meeting review complete.
10. Speaker assignment in desktop as an embedded server-owned web surface.
11. Active recording with native stop pinned above an embedded route.
12. Partial/degraded or failed processing.
13. Browser-only handoff.
14. Deletion/access entry point.

The historical v3 Figma handoff also included supporting boards for:

- search command palette;
- filters/sort/upcoming menus;
- meeting row variants;
- share/access modal;
- export/download menu;
- deletion confirmation lifecycle;
- AI drawer scopes;
- tags/activity/action items;
- empty states;
- account/session/security modals;
- upload validation errors;
- processing failure recovery;
- localization;
- accessibility/focus behavior.

Those v3 boards remain useful requirement-coverage notes, but they are not the
accepted visual direction. V5, v6, the first v7 page, v7.1, v7.2, v7.3, and
v7.4 are also only coverage evidence. V8 is the active redesign direction, but
it is not final implementation input until stakeholder visual acceptance is
recorded.

## Forbidden Prototype Content

Prototype artifacts must not include:

- real private meeting content;
- raw audio;
- secrets, tokens, passwords, signed URLs, API keys, device credentials;
- live local filesystem paths;
- copied Krisp UI, copy, icons, screenshots, assets, or proprietary behavior;
- claims that implementation or production rollout is already complete.

## Visual QA Requirements

Before accepting the prototype:

- inspect desktop and compact layouts for text overflow;
- verify dark theme contrast and tokenized light-theme compatibility;
- verify non-color status cues;
- verify active recording and stop are not obscured;
- verify browser-only routes do not appear as embedded desktop screens;
- verify variable product routes such as speaker assignment are embedded from
  web/backend rather than reimplemented as native desktop logic;
- verify clickable paths match the owner value loop;
- record visual QA notes in the handoff artifact.

## Final Validation Artifacts

- `design/visual/visual-qa.md`
- `design/qa-checklist.md`
- `design/validation-evidence.md`
