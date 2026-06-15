# Visual QA Evidence

Current status: v5 visual QA is failed/superseded after the 2026-06-13
Krisp/code/Figma re-audit. V6 passed narrow mechanical QA but failed
stakeholder product/design review. The first v7 page, v7.1, v7.2, v7.3, and
v7.4 are superseded. V8 is the active clean Russian review candidate after the
Krisp IA correction lineage plus the final screen-by-screen pass for settings,
button consistency, web cabinet list/detail, share/export/delete, light-theme
proof, and component QA rules.
It is not final implementation handoff until stakeholder review passes.

| Check | Result | Evidence |
|---|---|---|
| Active design candidate | V8 CLEAN RU PASS | Figma page `030 MVP Experience v8 - Clean RU`, page id `341:2`, is the current review candidate. V7.4 was renamed `030 MVP Experience v7.4 - Superseded by v8`. |
| V8 whole-page structure QA | PASS | Final Figma Plugin API audit across 17 V8 frames found frame-bound overflow `0`, bad button heights `0`, bad chip heights `0`, visible forbidden implementation copy `0`, placeholder nodes `0`, and the post-Krisp IA follow-up returned `reactionNodeCount=92` with `gateFailures=0`. |
| V8 clickable flow QA | PASS | Figma Plugin API reaction graph audit found 92 valid `ON_CLICK` reactions across 92 nodes, invalid destinations `0`, self-links `0`, superseded-page destinations `0`, and required owner-value-loop coverage passing. |
| V8 screen coverage | PASS | `00-16` now cover flow map, compact sign-in, guided permissions, desktop workspace, auto-detect prompt, active recording shell, inline upload/processing, transcript review, speaker lanes, settings, web list, web detail, share/export/delete, light theme proof, shared upload sheet, command search/filter overlay, and QA/component rules. |
| V8 web cabinet | PASS | `V8 10` integrates search, filters, sorting, upload, upcoming meeting context, processing status, source, date/time, and row actions on the list page. `V8 11` provides full meeting review with transcript, playback, outcomes, speaker action, and share/export actions. |
| V8 settings and theme | PASS | `V8 09` covers recording behavior, selected-app auto-detection, Zoom/Google Meet/Teams toggles, audio sources, system/dark/light theme, Russian language, upload/access/notification/diagnostics sections, and browser cabinet handoff. |
| V8 speaker lane model | PASS | `V8 08` uses one separate lane per speaker, visible talk-time percentages, assignment actions, participant names, low-confidence review, and save action. |
| Text overflow in compact desktop surfaces | PASS | Screen specs require wrapping and short button verbs |
| Active Stop visibility | V7.4.5 SHELL PASS | V7.4.5 keeps recording as a compact pinned native/menu-bar shell state with Stop visible over embedded cabinet content, removes the contradictory active-state `Записать` action, and avoids a wide red band obscuring the review route. |
| Dark MVP theme | V7.4 CORRECTION PASS | V7.4 Figma page uses dark theme as primary launch surface. |
| Light token compatibility | PASS | `system/tokens.md` keeps light roles for future compatibility |
| Non-color status cues | PASS | Accessibility and component docs require text plus icon/shape |
| Browser-only routes absent from embedded app | PASS | Route matrix plus v7.4 governance/settings frames keep broad risky actions browser-owned |
| Brand distance | PASS | `brand-distance-review.md` |
| Cabinet-first visual quality | V7.4 CORRECTION PASS | V7.4 makes the meeting cockpit the default surface and integrates upload, search/filter, lifecycle status, and recent meetings. |
| First-run/auth/permissions | V7.4.12 CORRECTION PASS | `V7.4 01` now uses a compact sign-in window with email, Google, Apple, Microsoft, Yandex, and SSO options; `V7.4 02` now uses a first-open guided permission flow with a visual System Settings mock, direct open/check/later controls, and no clipped privacy copy. |
| Detected meeting prompt | V7.4.12 CORRECTION PASS | `V7.4 04` now keeps auto-detected meeting capture as an inline decision in the meeting workspace, with compact sync status, explicit record/skip/rule actions, date/time in the table, and no separate active-recording destination. |
| Desktop workspace density | V7.4.9 DENSITY PASS | `V7.4 03` now shows 9 meeting rows, keeps date/time/source/participants/status/action visible, adds a compact `Очередь обработки` rail, and reduces the largest vertical gap to 60px without introducing overflow or technical copy. |
| Cockpit upload density | V7.4.10 DENSITY PASS | `V7.4 05` and `V7.4 08A` now keep upload as local cockpit context and show 8 meeting rows with max vertical gap 38px, action buttons 36/40px, and no label/technical-copy/frame-bound regressions. |
| Desktop speaker assignment | V7.4.11 DENSITY PASS | `V7.4 06` and `V7.4 08B` are now dense speaker-review workspaces with 9 transcript rows, contextual save/cancel/browser actions, selected-segment assignment, merge/split/new-speaker actions, no generic upload/record/open actions, and no technical route copy. |
| Speaker lane model | V7.4.11 DENSITY PASS | V7.4.11 dark review and light review each preserve 4 separate speaker lanes with 16 segment markers; active embedded review still preserves 4 lanes with 12 segment markers from the shell pass. |
| Button sizing consistency | V7.4.8 WHOLE-PAGE PASS | Final v7.4.8 audit found all 16 visible V7.4 frames free of button-height issue frames, button label-bound issue frames, technical-copy leaks, and frame-bound overflow; primary/header controls use 40px, table-row actions use 36px, and disabled tertiary `Сбросить` is documented as a non-primary filter reset. |
| Russian-first UI | V7.4.5 SHELL PASS | V7.4.5 focused audit found no visible `Переим.`, `локальная копия`, native/server/route/api labels in the active target frames; status copy uses `офлайн-файл` and `сохранено на Mac`. |
| Realistic neutral data | PASS | V7 frames use synthetic neutral Russian meeting examples |
| Screenshot/desktop QA | V7.4.12 CORRECTION PASS | V7.4 key frames were reviewed via Figma Plugin API structure/screenshot passes after the Krisp IA correction; `01`, `02`, and `04` received first-run/detected-flow correction, `03`, `05`, `06`, `08A`, and `08B` received density fixes, `04`, `05`, and `08A` received geometry fixes, `06`, `07`, `08B`, `08C`, and `11` received focused review/settings/active-recording polish, `10` and `11` received menu-bar/active-shell correction, `07`/`08C` received settings IA/depth correction, `12`/`13` received governance/light-critical correction, and v7.4.12 focused QA found no technical-copy/action-height/chip-height/clipping/frame-bound regressions in the corrected entry/detection frames. |
| Free UI kit grounding | PASS | SDS Upload live instance plus Button, Search, Input Field, Tag, Switch Field samples; Apple macOS 26 kept as native reference pending manual library attachment |
| Layout overflow | V7.4.1 GEOMETRY PASS | Final v7.4.1 audit found no button sizing, wrapped button text, technical-copy, Latin UI, or prototype destination issues; targeted row geometry found `statusActionIssues=0` for `04`, `05`, and `08A`, with compact desktop access hidden and wide cockpit access kept inside the table. |
| Clickable main path | V7.4 CORRECTION PASS | V7.4 has 13 valid cross-frame reactions; same-frame upload/filter states are documented without fake navigation. |
| Menu-bar invariant | V7.4.5 SHELL PASS | `V7.4 10` proves ready, recording, offline, and queued menu-bar states as compact popover states with `Стоп` first while active. |
| Settings console depth | V7.4.6 SETTINGS PASS | Dark and light settings now show a denser settings console with list-detail subnav, theme/language controls, recording policy, source controls, meeting detection apps, upload/storage, access/deletion, diagnostics, browser handoff, and visible owner signals for what lives on Mac, in the cabinet, or in the browser. |
| Active embedded route | V7.4.5 SHELL PASS | `V7.4 11` proves native Stop remains visible over an embedded review route while the recording status stays compact, readable, and free of a duplicate `Записать` action. |
| Share/export/delete governance | V7.4.7 GOVERNANCE PASS | `V7.4 12` now includes meeting context, date/time, access and file state, share/export/delete cards, truthful deletion scope, and audit trace without promising erasure outside 2brain control. |
| Light critical states | V7.4.7 LIGHT PASS | `V7.4 08A`, `08B`, `08C`, and rebuilt `13` prove light meeting, review, settings, sign-in, permissions, upload, detection, recording, deletion, and light-theme control rules. |

## Remaining Human Review

A stakeholder should not approve implementation from v5, v6, or the first v7
page. V7.4 has completed the correction pass and still needs stakeholder visual
approval before final handoff:

- [x] button cluster size/radius audit;
- [x] technical-copy leak audit;
- [x] speaker-lane contract audit;
- [x] desktop/web route ownership audit;
- [x] clickable prototype reaction audit for current draft;
- [x] screenshot review of current v7 contact sheet;
- [x] improve first-run/auth/permissions composition;
- [x] add more light-theme product proof frames;
- [x] rerun five-critic review on v7.1 and apply fixes;
- [x] add menu-bar, active embedded route, governance, and light critical-state
  proof frames;
- [x] run v7.4 Krisp IA correction for meeting cockpit, recording shell,
  settings, upload/status integration, speaker lanes, Russian UI, and
  prototype links;
- [x] run v7.4.1 geometry pass for detected-meeting prompt placement, cockpit
  table width, status/action separation, compact access visibility, and
  dark/light cockpit parity;
- [x] run v7.4.2 focused review/settings polish for clipped speaker actions,
  readable talk-time percentages, denser transcript review, settings console
  depth, old settings underlayers, active-recording compactness, and
  user-facing status copy;
- [x] run v7.4.5 shell/menu-bar correction for sparse menu-bar composition,
  active-state `Записать` contradiction, overlapping active header subtitle,
  stale local-copy layer names, and active review usability while recording;
- [x] run v7.4.6 settings IA/depth correction for dark/light settings density,
  clipped policy/source/detection controls, side-panel handoff button overflow,
  theme switching, owner signals, and browser-cabinet governance;
- [x] run v7.4.7 governance/light-critical correction for meeting-context
  share/export/delete, truthful deletion copy, audit trace, filled light
  critical-state board, and remaining technical-copy leak removal;
- [x] run v7.4.8 whole-page geometry pass for all 16 visible frames, fixing
  hidden row-action label overflow in `04`, `05`, and `08A` while preserving
  table composition;
- [x] run v7.4.9 desktop workspace density pass for `03`, extending the
  meeting table to 9 rows, adding an integrated processing rail, and verifying
  no button, label, technical-copy, or frame-bound regressions;
- [x] run v7.4.10 cockpit/upload density pass for `05` and `08A`, keeping
  upload as local context, extending both tables to 8 rows, and verifying dark
  and light parity with no button, label, technical-copy, or frame-bound
  regressions;
- [x] run v7.4.10 follow-up whole-page semantic audit for all 16 visible
  frames, confirming no mechanical regressions and narrowing remaining
  product-density work to `06` and `08B`;
- [x] run v7.4.11 review/speaker-assignment density pass for `06` and `08B`,
  rebuilding review as a dense speaker workspace and confirming 9 transcript
  rows, 4 speaker lanes, 16 segments, no generic global actions, and no
  mechanical regressions after fixing light secondary-button contrast;
- [x] run v7.4.12 first-run/detected-meeting correction pass for `01`, `02`,
  and `04`, confirming compact provider auth, guided macOS permissions with
  visual settings mock, inline auto-detect prompt, 36/40px action controls,
  28px chips, no clipped nodes, and no technical-copy leaks;
- [x] run v8 clean Russian redesign pass for 17 frames, replacing remaining
  weak placeholders with full web list/detail/governance, light-theme proof,
  settings IA, shared upload, command search/filter overlay, component QA rules,
  and final Figma Plugin API checks for overflow, button heights, chip heights,
  placeholder nodes, and forbidden visible implementation copy;
- [ ] stakeholder visual approval.
