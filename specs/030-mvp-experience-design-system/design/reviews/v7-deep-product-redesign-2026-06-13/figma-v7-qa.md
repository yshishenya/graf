# Figma V7/V7.1/V7.2/V7.4/V7.4.12 QA Evidence

File: <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr>
Historical page for this V7 review: `030 MVP Experience v7.4 - Krisp IA corrected RU`
Historical page id: `210:2`
Status: superseded correction candidate after the v7.3 five-critic failure,
Krisp IA correction, v7.4.1 geometry pass, v7.4.2 focused
review/settings polish pass, v7.4.5 shell/menu-bar correction pass,
v7.4.6 settings IA/depth correction pass, v7.4.7 governance/light-critical
correction pass, v7.4.8 whole-page geometry pass, and v7.4.9 desktop
workspace density pass, v7.4.10 cockpit/upload density pass, the
follow-up v7.4.10 whole-page semantic audit, the v7.4.11
review/speaker-assignment density pass, and the v7.4.12 first-run/detected
meeting correction pass. It is no longer the active handoff source; use the V8
clean Russian page for current implementation review.

## Current V7.4 Screen Coverage

- Visible frames: 16.
- Primary language: Russian.
- Primary theme: dark, with separate light-theme proof frames.
- Core surfaces covered:
  - IA and owner value loop;
  - compact provider/email/SSO/Yandex sign-in;
  - guided macOS permissions with visual system-settings guide;
  - desktop meeting workspace;
  - detected-meeting prompt state;
  - menu-bar controller states;
  - meeting cockpit with integrated upload/status/search/filter;
  - review workspace with transcript and speaker assignment lanes;
  - active recording over embedded cabinet;
  - browser-owned share/export/delete governance;
  - real settings console with appearance, recording, detection, storage,
    access/deletion, diagnostics, and workspace boundaries;
  - light meeting, review, settings, and critical-state proof;
  - QA gates.

## Current V7.4 Programmatic QA

Final Figma Plugin API audit after the Krisp IA correction, auth overflow
fix, and v7.4.1 geometry pass:

| Check | Result |
|---|---:|
| Visible frame count | 16 |
| Button candidates | 99 |
| Button heights | 36, 40 |
| Button issue count | 0 |
| Wrapped button text count | 0 |
| Forbidden top-level queue/upload/search nav | 0 |
| Technical-copy leaks | 0 |
| Latin/English visible UI hits | 0 |
| Valid prototype reaction nodes | 13 |
| Total reactions | 13 |
| Prototype destination issues | 0 |

Targeted geometry pass:

| Frame | Status/action overlap | Access column behavior | Result |
|---|---:|---|---|
| `V7.4 04 - Detected meeting prompt state` | 0 | hidden in compact desktop table with right status rail | PASS |
| `V7.4 05 - Meeting cockpit with upload` | 0 | visible inside widened cockpit table | PASS |
| `V7.4 08A - Light meeting cockpit` | 0 | visible inside widened light cockpit table | PASS |

Filter/action note: `Сбросить` is intentionally a tertiary disabled action
when no date/source/status filter is active. Primary header actions use 40px
height; table-row actions use the denser 36px height. Buttons of the same role
must remain size-consistent in implementation.

Focused v7.4.2 review/settings polish pass:

| Check | Result |
|---|---:|
| Target frames audited | 8 |
| Visible bad labels: `Переим.`, `локальная копия`, native/server/route/api | 0 |
| Settings visible overlays | 2 each in dark/light settings frames |
| Speaker-track percentage x-position | 1080 in dark, light, and active review |
| Hidden superseded settings layers | 88 |

V7.4.2 fixed a second screenshot-review batch:

- review speaker buttons now use `Изменить` instead of clipped `Переим.`;
- transcript review gained two extra realistic turns to reduce empty review
  space and keep the text connected to speaker lanes;
- `Сервер принял файл...` was replaced with user-facing upload/status copy;
- `локальная копия` footer/status copy was replaced with `офлайн-файл`;
- dark and light settings were rebuilt as a visible settings dashboard covering
  appearance/theme, language, recording policy, upload, access/deletion,
  notifications, and diagnostics;
- superseded settings underlayers were hidden so handoff does not expose
  contradictory old settings copy;
- active recording over cabinet now uses a compact native recording strip plus
  one-action `Стоп`, instead of a wide red band over the embedded review.

Focused v7.4.5 shell/menu-bar correction pass:

| Check | Result |
|---|---:|
| Visible technical-copy leaks: native/server/route/api/worker/локальная копия | 0 |
| Active-recording visible `Записать` actions | 0 |
| Button heights after shell fixes | 36, 40 |
| Button issue count after shell fixes | 0 |
| New menu-bar rectangle buttons | 6, all 40px high |
| New menu-bar button label overflow | 0 |
| Dark/light/active speaker-lane frames | 4 lanes each |
| Speaker segments per audited lane frame | 12 |

V7.4.5 fixed the newest screen-by-screen review batch:

- `V7.4 10 - Menu bar controller` was rebuilt from a sparse right-side
  popover mock into a compact three-state menu-bar model: `Готово`, `Идет
  запись`, and `Офлайн`;
- menu-bar recording state now keeps `Стоп` as the first action and shows queue
  truth inside the popover instead of creating a separate queue destination;
- `V7.4 11 - Active recording over cabinet` no longer exposes a contradictory
  top-level `Записать` button while recording is active;
- superseded overlapping active-strip and tab layers were hidden, leaving one
  compact active status pill plus the persistent `Стоп`;
- visible and layer-name copy now uses `офлайн-файл`, `сохранено на Mac`, or
  `файл сохраняется на Mac` instead of `локальная копия`;
- active review remains usable while recording continues in the shell.

Focused v7.4.6 settings IA correction pass:

| Check | Result |
|---|---:|
| Settings frames rebuilt | dark `V7.4 07`, light `V7.4 08C` |
| Visible stale v7.4.2/v7.4.6 settings layers after final pass | 0 |
| Visible technical-copy leaks: native/server/route/api/worker/`локальная копия` | 0 |
| Required settings sections present in dark/light | 15/15 |
| Action button heights | 36, 40 |
| Action button height issues | 0 |
| Segmented-control heights | 32 |
| Segmented-control height issues | 0 |
| Toggle heights | 24 |
| Toggle height issues | 0 |
| Control label overflow | 0 |
| Frame-bound overflow | 0 |

V7.4.6 fixed the settings-specific review batch:

- dark and light settings were rebuilt from a sparse card grid into a denser
  product-grade console with a persistent settings subnav, main work area, and
  right governance rail;
- appearance now has explicit `Системная`, `Темная`, and `Светлая` theme
  controls plus Russian language and sync status proof;
- recording policy now uses concise Russian controls: `Спрашивать`, `Авто
  выбранные`, and `Вручную`, avoiding clipped long labels;
- sources and meeting detection are split into readable control groups with
  `Микрофон`, `Системный звук`, Zoom, Google Meet, Teams, and Телемост states;
- upload/storage, access/deletion, diagnostics, and browser cabinet handoff are
  visible without exposing implementation labels;
- every visible settings control has a clear owner signal: `на Mac`, `кабинет`,
  `В приложении`, `В кабинете`, or `В браузере`.

Focused v7.4.7 governance and light-critical correction pass:

| Check | `V7.4 12` governance | `V7.4 13` light critical |
|---|---:|---:|
| Visible technical-copy leaks | 0 | 0 |
| Action button heights | 40 | 40 |
| Action button height issues | 0 | 0 |
| Chip heights | 28 | 28 |
| Chip height issues | 0 | 0 |
| Control label overflow | 0 | 0 |
| Frame-bound overflow | 0 | 0 |

V7.4.7 fixed the governance/light-proof review batch:

- share/export/delete now starts from a meeting context row with date/time,
  duration, source, participants, access count, transcript-ready state, and
  file-retention state;
- share, export, delete, and audit history are denser and no longer leave a
  large empty first viewport;
- deletion copy is truthful: it requires meeting-name confirmation and does not
  promise erasure of copies outside 2brain control;
- light critical states now cover sign-in, permissions, upload progress,
  meeting detection, active recording, deletion, and light-theme control rules
  in a filled two-row board rather than sparse demo tiles;
- the final v7.4.7 QA pass removed the remaining `нативной` copy leak from
  light active-recording proof and replaced it with user-facing top-bar copy.

Focused v7.4.8 whole-page geometry pass:

| Check | Result |
|---|---:|
| Visible V7.4 frames audited | 16 |
| Visible technical-copy leaks | 0 |
| Button-height issue frames | 0 |
| Button label-bound issue frames | 0 |
| Frame-bound overflow frames | 0 |
| `V7.4 04` row-action label overflow after fix | 0 |
| `V7.4 05` row-action label overflow after fix | 0 |
| `V7.4 08A` row-action label overflow after fix | 0 |

V7.4.8 fixed the whole-page audit batch:

- the active page was re-audited across all 16 visible V7.4 frames instead of
  only the recently changed settings/governance frames;
- hidden text-frame overflow was found in row-action buttons on `V7.4 04`,
  `V7.4 05`, and `V7.4 08A`;
- the visual button sizes were intentionally preserved, while each overflowing
  text layer was resized to the button width and centered;
- the follow-up audit found no remaining visible technical-copy leaks,
  button-height issue frames, button label-bound issue frames, or frame-bound
  overflow frames.

Focused v7.4.9 desktop workspace density pass:

| Check | Result |
|---|---:|
| Audited frame | `V7.4 03 - Desktop meeting workspace` |
| Meeting rows after fix | 9 |
| Table height after fix | 560 |
| Button count after fix | 16 |
| Button heights after fix | 36, 40 |
| Button label overflow | 0 |
| Visible technical-copy leaks | 0 |
| Frame-bound overflow | 0 |
| Max vertical gap after fix | 60 |
| Queue/processing rail present | true |

V7.4.9 fixed the desktop workspace density batch:

- the ready desktop workspace no longer leaves the lower half of the main
  content area empty after only five meeting rows;
- the meeting table now shows nine realistic rows, preserving date/time,
  source, participant, status, and action columns;
- upload, network, processing, and speaker-assignment status remain integrated
  into the main meeting list instead of becoming a separate top-level route;
- a compact right-side `Очередь обработки` rail summarizes the same actionable
  processing states without taking focus away from the table;
- focused QA found only 36px row actions and 40px header controls, with no
  label overflow, technical-copy leaks, or frame-bound overflow.

Follow-up whole-page semantic audit after v7.4.9:

| Check | Result |
|---|---:|
| Visible V7.4 frames | 16 |
| Frames with forbidden technical copy | 0 |
| Frames with bad action-button heights | 0 |
| Frames with action-label overflow | 0 |
| Frames with frame-bound overflow | 0 |
| `V7.4 03` max vertical gap after density fix | 60 |

Next density candidates, not blockers for the v7.4.9 fix itself:

- `V7.4 05 - Meeting cockpit with upload` and `V7.4 08A - Light meeting
  cockpit` still report large vertical-gap heuristics around 199px;
- `V7.4 06 - Review speaker assignment` and `V7.4 08B - Light review
  speakers` still report large vertical-gap heuristics around 208px;
- these frames have no current action-height, label-overflow, technical-copy,
  or frame-bound issues, but they should be reviewed next for product density
  and content balance.

Focused v7.4.10 cockpit/upload density pass:

| Check | `V7.4 05` dark cockpit | `V7.4 08A` light cockpit |
|---|---:|---:|
| Meeting rows after fix | 8 | 8 |
| Table height after fix | 504 | 504 |
| Action buttons after fix | 15 | 15 |
| Action button heights | 36, 40 | 36, 40 |
| Bad action-button heights | 0 | 0 |
| Action label overflow | 0 | 0 |
| Visible technical-copy leaks | 0 | 0 |
| Frame-bound overflow | 0 | 0 |
| Max vertical gap after fix | 38 | 38 |
| Wrapped speaker-needed copy | 0 | 0 |

V7.4.10 fixed the cockpit/upload density batch:

- dark and light meeting cockpits keep the upload banner as local context, not
  a separate upload destination;
- both cockpits now show eight meeting rows below the upload banner, preserving
  date/time, source, participants, status, action, and access columns;
- upload, processing, network-error, and speaker-needed states remain visible
  in the table where the user expects current meeting status;
- the `Планирование` row subtitle was shortened to `нужны спикеры` after
  screenshot review found an unnecessary line wrap;
- final dark/light QA found no action-height, label-overflow, technical-copy,
  or frame-bound issues.

Follow-up whole-page semantic audit after v7.4.10:

| Check | Result |
|---|---:|
| Visible V7.4 frames | 16 |
| Frames with forbidden technical copy | 0 |
| Frames with bad action-button heights | 0 |
| Frames with action-label overflow | 0 |
| Frames with frame-bound overflow | 0 |
| `V7.4 03` max vertical gap | 60 |
| `V7.4 05` max vertical gap | 38 |
| `V7.4 08A` max vertical gap | 38 |
| Remaining product-screen large-gap candidates | `06`, `08B` |

Next density candidates after v7.4.10, now completed by v7.4.11:

- `V7.4 06 - Review speaker assignment` and `V7.4 08B - Light review
  speakers` needed the next product-density review pass;
- the IA/value-loop board also reports a 188px heuristic gap, but it is a
  map/evidence frame rather than a product screen and is not part of the next
  product-density batch.

Focused v7.4.11 review/speaker-assignment density pass:

| Check | `V7.4 06` dark review | `V7.4 08B` light review |
|---|---:|---:|
| Transcript rows after fix | 9 | 9 |
| Separate speaker lanes | 4 | 4 |
| Speaker segments | 16 | 16 |
| Action buttons | 14 | 14 |
| Action button heights | 36, 40 | 36, 40 |
| Bad action-button heights | 0 | 0 |
| Action label overflow | 0 | 0 |
| Visible technical-copy leaks | 0 | 0 |
| Old global actions visible: `Загрузить`/`Записать`/`Открыть` | 0 | 0 |
| Frame-bound overflow | 0 | 0 |
| Max vertical gap after fix | 172 | 172 |
| Selected-segment controls inside side panel | true | true |
| Wrapped warning chip copy | 0 | 0 |

V7.4.11 fixed the review/speaker workspace density batch:

- the review speaker route no longer uses generic global header actions for
  upload, recording, or open; it now has contextual `Сохранить`, `Отменить`,
  and `В браузере` actions for speaker-review work;
- the transcript area grew from a sparse sample into a 9-row workbench with
  confidence chips and inline `Назн.`/`Провер.` actions on uncertain segments;
- the speaker side panel now shows per-speaker counts, confidence context,
  selected-segment assignment, merge/split/new-speaker actions, and a save
  path in the same workspace;
- the lane panel now fills the lower workspace with one separate lane per
  speaker, 16 segment markers, and visible warning outlines for uncertain
  segments;
- screenshot review caught two defects after the first pass: wrapping warning
  chip copy and light-theme secondary buttons with insufficient visible label
  contrast; both were fixed before the final v7.4.11 QA pass;
- light secondary buttons now use outline treatment with dark labels, while
  the primary `Сохранить` action remains filled.

Follow-up whole-page semantic audit after v7.4.11:

| Check | Result |
|---|---:|
| Visible V7.4 frames | 16 |
| Frames with forbidden technical copy | 0 |
| Frames with bad action-button heights | 0 |
| Frames with action-label overflow | 0 |
| Frames with frame-bound overflow | 0 |
| `V7.4 06` max vertical gap | 172 |
| `V7.4 08B` max vertical gap | 172 |
| Remaining product-screen large-gap candidates | 0 |

The only remaining large-gap heuristic hit is `V7.4 00 - IA and value loop`
at 188px. It is an evidence/map frame, not a product screen.

Speaker-lane contract:

| Frame | Tracks | Segments | Talk-time percentages |
|---|---:|---:|---:|
| `V7.4 06 - Review speaker assignment` | 4 | present | present |
| `V7.4 08B - Light review speakers` | 4 | present | present |
| `V7.4 11 - Active recording over cabinet` | 4 | present | present |

Focused v7.4.12 first-run/auth/permissions/detected-meeting correction pass:

| Check | `V7.4 01` auth | `V7.4 02` permissions | `V7.4 04` detected meeting |
|---|---:|---:|---:|
| Action buttons | 6 | 3 | 18 |
| Action button heights | 36, 40 | 40 | 36, 40 |
| Bad action-button heights | 0 | 0 | 0 |
| Status chips | 3 | 1 | 8 |
| Chip heights | 28 | 28 | 28 |
| Visible technical-copy leaks | 0 | 0 | 0 |
| Clipped/hidden-by-parent nodes | 0 | 0 | 0 |
| Frame-bound overflow | 0 | 0 | 0 |
| Required proof | provider auth present | visual settings guide present | prompt/date-time proof present |

V7.4.12 fixed the first-run and detected-meeting batch:

- `V7.4 01 - First launch auth` was rebuilt as a compact macOS-style sign-in
  window with email, Google, Apple, Microsoft, Yandex, and SSO options; the
  old local/offline continuation path is no longer a primary action.
- `V7.4 02 - Guided permissions` now appears as a first-open guided native
  flow with a visual System Settings mock, direct `Открыть настройки`,
  `Проверить`, and `Позже` controls, and shorter privacy copy that does not
  collide with the buttons.
- `V7.4 04 - Detected meeting prompt state` now treats auto-detected meeting
  capture as an inline working decision in the meeting workspace, not a
  separate destination or modal. Header status is compact
  `синхронизировано`, the record decision is explicit, and meeting rows keep
  date/time visible.
- A visual QA pass caught and fixed two defects after the first rebuild:
  clipped permissions controls and an inconsistent 28px `Правило` control in
  the detected-meeting prompt. The final pass keeps primary/header controls at
  40px, compact row/secondary actions at 36px, and chips at 28px.

## Current V7.4 Visual Screenshot QA

Saved screenshots:

- V7.4 key frames were reviewed through inline Figma Plugin API screenshots.
- Auth overflow was found during screenshot review, then fixed with a compact
  auth preview/sign-in layout and stale old table layers removed.
- V7.4.1 screenshot review found and fixed real geometry defects in `04`,
  `05`, and `08A`: floating detected-meeting prompt overlap, filter/date/source
  overlap, table action/status overlap, and access text escaping the table.
- V7.4.2 screenshot review found and fixed `V7.4 06`, `07`, `08B`, `08C`, and
  `11` defects: clipped speaker rename labels, `10%` talk-time overlap,
  underfilled transcript review, sparse settings, old settings underlayers, and
  over-heavy active-recording band.
- V7.4.5 screenshot review found and fixed `V7.4 10` and `V7.4 11` defects:
  sparse menu-bar composition, active-state `Записать` contradiction,
  overlapping active header subtitle, stale `локальная копия` layer names, and
  old active-strip underlayers.
- V7.4.6 screenshot review found and fixed `V7.4 07` and `V7.4 08C` settings
  defects: sparse settings composition, over-short policy labels, cramped
  source rows, overflowing meeting-detection controls, and side-panel handoff
  button overflow.
- V7.4.7 screenshot review found and fixed `V7.4 12` and `V7.4 13` defects:
  sparse governance composition, clipped/overlapping file-retention chip,
  light critical-state empty space, lower-card button overflow, and one
  technical-copy leak in active-recording light proof.
- V7.4.8 screenshot review found and fixed hidden row-action text-frame
  overflow in `V7.4 04`, `V7.4 05`, and `V7.4 08A` without changing the visible
  table composition.
- V7.4.9 screenshot review found and fixed underused vertical space in
  `V7.4 03` by extending the meeting list and adding an integrated processing
  rail; final screenshot saved as
  `/tmp/2brain-figma-v74-qa/v749-03-desktop-workspace-density-final.png`.
- V7.4.10 screenshot review found and fixed underused vertical space in
  `V7.4 05` and `V7.4 08A`; final screenshots saved as
  `/tmp/2brain-figma-v74-qa/v7410-05-cockpit-density-final2.png` and
  `/tmp/2brain-figma-v74-qa/v7410-08a-light-cockpit-density-final2.png`.
- V7.4.10 follow-up whole-page semantic audit found no technical-copy,
  action-height, action-label, or frame-bound regressions across all 16 visible
  frames; before the v7.4.11 pass, `V7.4 06` and `V7.4 08B` were the only
  remaining product-density candidates.
- V7.4.11 screenshot review rebuilt `V7.4 06` and `V7.4 08B` as dense
  review/speaker-assignment workspaces; final screenshots saved as
  `/tmp/2brain-figma-v74-qa/v7411-06-review-density-final2.png` and
  `/tmp/2brain-figma-v74-qa/v7411-08b-review-light-density-final3.png`.
- V7.4.11 whole-page semantic audit found no technical-copy, action-height,
  action-label, or frame-bound regressions across all 16 visible frames; no
  product screen remains in the large-gap candidate list.
- V7.4.12 screenshot review rebuilt `V7.4 01`, `V7.4 02`, and `V7.4 04` for
  compact auth, guided permissions, and detected-meeting flow consistency;
  final screenshots saved as
  `/tmp/2brain-figma-v74-qa/v7412-01-auth-final.png`,
  `/tmp/2brain-figma-v74-qa/v7412-02-permissions-final.png`, and
  `/tmp/2brain-figma-v74-qa/v7412-04-detected-final2.png`.
- Current local QA PNGs are saved under `/tmp/2brain-figma-v74-qa/`:
  `v742-06-review-fixed2.png`, `v742-07-settings-fixed2.png`,
  `v742-08c-settings-light-fixed2.png`, `v742-11-active-fixed2.png`,
  `v745-10-menubar-fixed.png`, `v745-11-active-final.png`,
  `v746-07-settings-final.png`, `v746-08c-settings-light-final.png`,
  `v747-12-governance-final.png`, and
  `v747-13-light-critical-final.png`, `v748-04-detected-final.png`,
  `v748-05-cockpit-final.png`, `v748-08a-light-cockpit-final.png`,
  `v749-03-desktop-workspace-density-final.png`,
  `v7410-05-cockpit-density-final2.png`, and
  `v7410-08a-light-cockpit-density-final2.png`,
  `v7411-06-review-density-final2.png`, and
  `v7411-08b-review-light-density-final3.png`,
  `v7412-01-auth-final.png`, `v7412-02-permissions-final.png`, and
  `v7412-04-detected-final2.png`.
- Historical v7.1 contact sheet remains at
  `screenshots/v7-1-polish-fixpass-contact-sheet.png`.

Visual pass findings:

- V7.4 is materially stronger than v6-v7.3 on IA: meetings are the default
  cockpit; search/filter/upload/processing are integrated into that cockpit;
  active recording is a shell/menu-bar state; settings are a real workspace.
- First-run/auth/permissions now use compact, product-grade composition with a
  smaller auth panel, provider sign-in, no primary local/offline continuation,
  and a visual macOS settings guide.
- Settings now covers appearance, recording, detection, sources,
  upload/storage, access/deletion, diagnostics, and workspace boundaries
  without technical product-surface copy.
- Settings now presents the launch-critical controls in a dense list-detail
  console with explicit ownership tags rather than a sparse summary card grid.
- Menu-bar controller and active recording over embedded review are now explicit
  proof frames, not implied behavior. V7.4.5 makes the menu-bar proof a compact
  state board instead of a sparse decorative popover.
- Active recording is now a compact native status layer above the embedded
  review route, with Stop visible, no duplicate start-recording action, and the
  review content still usable.
- Share/export/delete governance is explicit, contextual, and truthful about
  deletion scope.
- Light theme proof now covers meeting workspace, review, settings, and dense
  critical states for sign-in, permissions, upload, detection, recording, and
  deletion.
- Detected-meeting state is now an inline current-recording decision surface,
  not a floating modal over the list; this matches the product rule that active
  recording is shell/status behavior rather than a separate destination.
- Upload/status/search/filter remain integrated in the main meeting cockpit.
  The wide web/embedded cockpit uses the full content width, while compact
  desktop hides access details from the table and keeps account state in the
  right rail/menu-bar surfaces.

## Remaining V7.4 Work

- Record stakeholder visual acceptance before calling this implementation-ready.

## Superseded V7.3 QA Evidence

Page: `030 MVP Experience v7.3 - Screen-by-screen polish RU`
Page id: `177:2`
Status: failed handoff review; superseded by v7.4.

Historical v7.3 finding:

- 16 visible frames existed, but five critics found P0/P1 blockers in active
  recording, top-level queue/upload, settings depth, upload/status integration,
  speaker assignment, governance, and auth/local policy.

## Superseded V7.2 QA Evidence

Page: `030 MVP Experience v7.2 - Pixel polish RU`
Page id: `158:2`
Status: pixel-polish evidence; superseded by v7.3/v7.4.

Historical v7.2 audit:

| Check | Result |
|---|---:|
| Visible frame count | 16 |
| Button candidates | 64 |
| Button heights | 32, 36, 40 |
| Button radius variants | 6 |
| Invalid button tokens | 0 |
| Technical-copy leaks | 0 |
| English visible UI hits | 0 |
| Valid prototype reaction nodes | 34 |
| Prototype destination issues | 0 |

## Superseded V7.1 QA Evidence

Page: `030 MVP Experience v7.1 - Krisp IA polish RU`
Page id: `143:2`
Status: five-critic fix-pass evidence; superseded by v7.2.

Historical v7.1 audit:

| Check | Result |
|---|---:|
| Visible frame count | 16 |
| Button candidates | 68 |
| Button heights | 32, 36, 40 |
| Button radius variants | 6 |
| Invalid button tokens | 0 |
| Technical-copy leaks | 0 |
| English visible UI hits | 0 |
| Valid prototype reaction nodes | 10 |
| Prototype destination issues | 0 |

## Superseded V7 QA Evidence

Page: `030 MVP Experience v7 - IA rebuilt RU`
Page id: `137:2`
Status: first v7 IA rebuild draft; superseded by v7.1.

Historical audit after the desktop-row overflow fix:

| Check | Result |
|---|---:|
| Frame count | 19 |
| Button candidates | 95 |
| Button heights | 32, 36, 40 |
| Button radius variants | 6 |
| Invalid button tokens | 0 |
| Adjacent button cluster issues | 0 |
| Technical-copy leaks outside allowed setup/settings/appendix frames | 0 |
| Top-level forbidden nav entries for search/upload/processing | 0 |
| Overflow count | 0 |
| Valid prototype reaction nodes | 16 |
| Prototype destination issues | 0 |

Historical screenshot:

- `screenshots/v7-full-contact-sheet.png`

Historical finding: v7 improved IA but still needed denser first-run
composition, broader light proof, menu-bar proof, active embedded review proof,
and governance proof.
