# Design QA Checklist

Current status: v5 QA is superseded by the 2026-06-13 re-audit. V6 passed
mechanical Figma QA but failed stakeholder product/design review. The first v7
IA rebuild is superseded by v7.1, v7.1 by v7.2, v7.2 by v7.3, v7.3 by v7.4,
and v7.4 by v8. V8 has the clean Russian redesign and machine QA pass applied.
It is now the baseline for the first real UI implementation slice; final
stakeholder visual approval remains the polish gate before the handoff is
called final.

- [x] Route matrix classifies every launch-critical route.
- [x] Status matrix separates upload, transcription, transcript, notes, deletion, and access truth.
- [x] Desktop active recording keeps Stop visible and native.
- [x] Embedded cabinet excludes capture-critical controls.
- [x] Manual upload is audio-first and does not promise full video UX.
- [x] Meeting review includes transcript, playback context, summary, decisions, actions, provenance, and deletion/access entry.
- [x] Speaker assignment is available in desktop as an embedded server-owned web route, while native macOS keeps capture authority only.
- [x] V6 makes speaker separation a primary review contract: one horizontal lane per speaker in browser and embedded desktop, with label, segments, talk-time percentage, and edit/review state.
- [x] V6 passes a programmatic button-cluster audit for equal height/radius inside each adjacent toolbar or action cluster.
- [x] V6 removes stale duplicate controls from meeting review, especially the mixed toolbar/pill controls found in `V5 15`.
- [x] V6 removes visible technical implementation labels from product first viewports, including `Сервер в сети`, `нативный`, route names, and backend service names unless they are inside diagnostics/audit details.
- [x] Variable product UI is server/web-owned and embeddable across macOS, Windows, and Linux shells; native shells keep only platform-critical capture, permissions, local buffer/queue, tray/menu, diagnostics, and route guard.
- [x] V5 includes coverage proof frames for desktop embedded speaker assignment and active Stop pinned above embedded web.
- [x] V5.2 full-flow Figma page exists with 36 top-level MVP frames.
- [x] V5.2 primary path has 82 button reactions, 130 sidebar/nav reactions, and 8 meeting-row/status-pill reactions for auth, permissions, record, upload, status, review, speakers, actions, share, export, delete, and route navigation.
- [x] V6 primary clickable prototype has 183 valid `ON_CLICK` reactions with 0 self-destination or non-frame destination issues.
- [x] V7 first draft removes top-level Search/Upload/Processing nav and integrates those as meeting workspace actions/states.
- [x] V7 first draft adds compact provider sign-in, workspace policy, guided macOS permissions, auto-detect prompt/settings, and theme proof.
- [x] V7 first draft passes programmatic button/overflow/technical-copy QA: `totalButtons=95`, button heights `32/36/40`, radius `6`, `overflowCount=0`.
- [x] V7.1 improves first-run/auth/permissions composition, adds separate
  light-theme product proof frames, and applies the five-critic fix-pass.
- [x] V7.1 adds menu-bar controller proof, active recording over embedded
  review, and share/export/delete governance proof.
- [x] V7.1 final fix-pass audit passes: `buttons=68`, heights `32/36/40`,
  radius `6`, `overflowCount=0`, `technicalCopyLeaks=0`,
  `englishHitCount=0`, `reactionIssueCount=0`, and 10 valid cross-frame
  reactions.
- [x] V7.2 rebuilds cramped IA map, compact auth, guided permissions, and
  settings workspace after pixel review.
- [x] V7.2 removes/defer-hides global `Действия` nav and keeps upload/search/
  processing inside the meeting workspace.
- [x] V7.2 final Figma API audit passes: `buttons=64`, heights `32/36/40`,
  radius `6`, `buttonIssueCount=0`, `technicalCopyLeaks=0`,
  `englishHitCount=0`, `forbiddenTopLevelNav=0`, `reactionIssueCount=0`, and
  34 valid cross-frame reactions.
- [x] V7.3 failed the deeper five-critic handoff review, so it is not accepted
  as implementation input.
- [x] V7.4 corrects the Krisp IA model: meeting cockpit default, inline
  upload/search/status, active recording as shell/menu-bar state, compact auth,
  guided permissions, settings console, speaker lanes, governance, and light
  proof.
- [x] V7.4 final Figma API audit passes: `buttonCount=99`,
  `buttonIssueCount=0`, `wrappedButtonTextCount=0`, `forbiddenNavCount=0`,
  `technicalHitCount=0`, `latinHitCount=0`, `reactionIssueCount=0`, and
  13 valid cross-frame reactions.
- [x] V8 clean Russian Figma API audit passes: frame-bound overflow `0`, bad
  button heights `0`, bad chip heights `0`, visible forbidden implementation
  copy `0`, placeholder artifact nodes `0`, button heights `36/40`, compact
  segmented/theme control height `32`, and chip height `28`; post-copy live
  recheck after `Stop`/local wording fixes also returns forbidden text `0`.
- [x] V8 strict post-critique Figma re-audit passes: `controls=112`,
  `badControls=0`, `badChips=0`, `englishText=0`, `textOverlap=0`,
  `overflow=0`, and web table/playback metadata alignment fixes applied.
- [x] V8 post-`computer-use` Figma correction removes stale top-level desktop
  sidebar `Загрузка` navigation; targeted audit returns
  `sidebarUploadLeakCount=0`, `badControls=0`, `badChips=0`,
  `settingsStorageCount=1`, `inlineUploadStatusCount=2`, `overflowCount=0`,
  and `targetTextOverlapCount=0`.
- [x] V8 implementation-facing route/status/screen contracts are aligned with
  the final IA: desktop sidebar is `Встречи` / `Обзор` / `Настройки` /
  `Помощь`; upload and processing are meeting actions/states, not top-level
  desktop navigation; user-visible sync wording uses `Нет связи` /
  `Синхронизировано` instead of oversized server status blocks; active/tray/
  exception actions use Russian labels.
- [x] V8 desktop dark/light density polish adds a fourth realistic meeting row
  to `V8 03` and `V8 13`, removes stale sidebar layer names, fixes the clipped
  new status chip, and re-audits both frames with `badNavUploadCount=0`,
  `staleLayerNamesCount=0`, `badControlsCount=0`, and `overflowCount=0`.
- [x] V8 settings and web polish pass fixes `V8 09` theme/right-rail wording
  and chip spacing, `V8 10` clipped/overlapping table action columns, and
  `V8 11` clipped playback source chip; targeted re-audit returns
  `forbiddenCount=0`, `badControlsCount=0`, `overflowCount=0`, and
  `clippedByParentCount=0` for `V8 09`, `V8 10`, and `V8 11`.
- [x] V8 clickable prototype audit passes: 98 valid `ON_CLICK` reactions,
  invalid destinations `0`, self-links `0`, superseded-page destinations `0`,
  and required owner-value-loop coverage passing.
- [x] V8 post-accessibility Krisp live pass completed through `computer-use`
  for the locally installed desktop app: meeting list, search overlay, filter
  menu, meeting detail tabs, notes/actions, transcript/playback, speaker lanes,
  and settings IA. Direct Zen `app.krisp.ai` click-through remains unavailable
  because Computer Use blocks that browser URL.
- [x] V8 Krisp reference matrix correction queue is complete for first-path
  screens: `V8 01`, `V8 02`, `V8 03`, `V8 04`, `V8 05`, and `V8 06` now pass
  `design/reviews/v8-clean-ru-2026-06-15/krisp-reference-matrix.md`, not only
  mechanical button/overflow QA; targeted Figma API re-audit returned
  `missingFrames=0`, `forbiddenHits=0`, and `badControls=[]`.
- [x] V8 remaining value-surface deep pass is complete for `V8 07` through
  `V8 14`: transcript review, speaker lanes, settings, web list, web detail,
  share/export/delete, light proof, and component QA rules now pass
  `design/reviews/v8-clean-ru-2026-06-15/v8-remaining-screens-deep-pass.md`;
  targeted post-fix Figma API audit returned `missingFrames=0`,
  `badControls=[]`, `textOverlap=[]`, and `forbiddenHits=[]`.
- [x] V8 whole-page Krisp IA consistency audit covers all 17 frames after
  handoff-copy cleanup: `design/reviews/v8-clean-ru-2026-06-15/v8-whole-page-consistency-audit.md`
  records `frameCount=17`, `missingFrames=0`, `forbiddenHits=0`,
  `badControls=0`, `textOverlapHits=0`, `reactionIssues=0`, and
  `gateFailures=0`.
- [x] V8 strict Figma metadata pass checks implementation-relevant layer names
  as well as visible text: stale `client-call.mp4`, `Транскрибация`,
  `Button / Статус`, and `Загрузить файл` layer/text leaks were corrected, and
  the final audit returned `visibleStaleHits=0`, `textOverflow=0`,
  `textOverlaps=0`, and `gateFailures=0`.
- [x] V8 post-Krisp IA follow-up adds `V8 15` shared upload sheet and `V8 16`
  command search/filter overlay; the initial Figma audit returns
  `frameCount=17` and `reactionNodeCount=92`, and the stricter
  post-stakeholder polish below supersedes the intermediate button/copy metric
  set.
- [x] V8 post-stakeholder Krisp IA polish verifies the same screens by Figma
  metadata and screenshots: all V8 frame layer names use Russian handoff terms,
  V8 05 stop is inside the active-recording popover at `220x40`, V8 10 web
  shell is restored to `x=140`, `y=96`, web row chips are centered at `28px`,
  V8 15/V8 16 no longer expose implementation explanatory copy, V8 15
  validation chip is shortened to `Готово`, and the final focused audit returns
  `frameCount=17`, `expectedFrameCount=17`, `totalButtonLike=240`,
  `totalReactionNodes=92`, `staleNames=[]`, `forbiddenVisibleText=[]`,
  `suspectButtons=[]`, and `gateFailures=0`.
- [x] V8 final Krisp/action-row standards pass checks the pixel-level issues
  that made the UI feel rough: remaining `36x36` icon buttons are `40x40`,
  playback controls are at least `56x40`, web action rows use at least `8px`
  spacing, `V8 09` uses `Спрашивать` / `Всегда писать` / `Вручную`, QA number
  markers are not interactive chips, and the same-parent Figma API audit returns
  `targetSizeIssues=[]`, `buttonRowIssues=[]`, `technicalCopyHits=[]`,
  `staleNames=[]`, `missingSettingsConcepts=[]`, `missingFlowWords=[]`, and
  `gateFailures=0`.
- [x] V8 deep current-state polish pass fixes newly found roughness after
  visual review: `V8 16` no longer has `38px` buttons, `V8 05` uses
  `Остановить` consistently with an `8px`/`16px` top-cluster gap, `V8 06`
  uses `Выбрать медиа`, cloned density rows have no stale labels, `V8 05` has
  three recent meeting rows, `V8 06` has four lifecycle rows, and the final
  all-frame audit returns `targetSizeIssueCount=0`, `rowIssueCount=0`,
  `technicalCopyHitCount=0`, and `requiredGateFailures=0`.
- [x] V8 2026-06-16 button-rhythm follow-up removes the remaining visual
  mixed-size controls: sidebar/browser nav rows, transcript search, cabinet
  action, and close action now use `40px`; `V8 03` no longer has readiness or
  first-row text pressure; `V8 11` uses a non-clipped `Синхронизировано` chip;
  final Figma API validation returns `lowControlCount=0`,
  `forbiddenCount=0`, `visibleEverywhereCount=0`, `overflowCount=0`, and
  `textOverlapCount=0`.
- [x] V8 concrete Krisp extraction pass uses the actual desktop/web reference
  states, not only broad principles: 11 Krisp screenshots are captured under
  `design/reviews/v8-clean-ru-2026-06-15/krisp-reference-pass/`, the pass adds
  a persistent `V8 03` live-control rail, named `V8 07` transcript player
  speaker lanes, `V8 08` server-owned separate speaker tracks, and `V8 10`
  filter/date popovers; final targeted Figma QA returns missing frames `0`,
  required gate text present, key overlap areas `0`, `V8 07`
  `stillGeneric=[]`, `gapRailDuration=10`, and `gapDurationAction=30`.
- [x] V8 focused Krisp IA follow-up fixes the exact weak spots from
  stakeholder review: `V8 03` removes visible server wording, `V8 07` keeps the
  lower `Спикеры` action at `140x40` with label inside bounds, `V8 08` hides
  technical sync/banner copy and obsolete panels while preserving named
  separate speaker lanes, and `V8 09` removes queue jargon; focused Figma API
  validation returns `badCopy=[]`, `genericSpeakers=[]`,
  `v07Action40px=true`, `v07LabelInsideAction=true`, and
  `v08NamedLanes=true`.
- [x] V8 2026-06-16 explicit Krisp UX/IA reference recheck treats Krisp as a
  product-structure source, not a visual theme: desktop gates cover meeting
  workspace first, separated live controls, contextual search/filter, review
  value surface, speaker correction, and policy-grouped settings; web gates
  cover dense list/table, filter/date popovers, upload as meeting action,
  cross-surface status continuity, full transcript review, and browser-owned
  governance. Figma validation returns `missingSettingsConcepts=[]`,
  `technicalSettingsText=[]`, all Krisp IA coverage booleans `true`, and
  `invalidDestinations=[]`; the current clickable graph is `98` reactions
  across `98` nodes after adding missing prototype reactions for the V8 03
  live rail and V8 09 sound-check action.
- [x] V8 2026-06-16 settings IA polish makes `V8 09` ready as the first
  implementation settings baseline: selected section is `Основное`, top
  actions are equal `124x40`, right-rail actions are grouped at `138x40`,
  `Проверить звук` no longer floats at the bottom of an empty rail, `биллинг`
  is replaced with `оплата`, stale source layer name is `Chip / Система`, and
  focused Figma validation returns `technicalHits=[]`,
  `missingRequired=[]`, `badButtonSizes=[]`, `labelOverflowCount=0`, and
  `textOverlapCount=0`.
- [x] V8 five-critic screen audit covers all 17 frames through product-flow,
  IA, visual/UI, platform, and content/trust lenses.
- [x] V8 stakeholder visual approval pack exists with direct Figma links,
  click-through script, per-screen acceptance criteria, and decision template.
- [x] Active plan and route/status/prototype handoff contracts point to V8 as
  the current review candidate; V5-V7.4 are labeled as historical coverage or
  superseded evidence.
- [ ] Stakeholder visual approval of v8 is recorded.
- [x] V6 visible product UI copy is Russian-first, dark-theme first, and free from debug/implementation wording in user-facing surfaces.
- [x] V5 uses free UI kit evidence: Figma Simple Design System live samples and Apple macOS 26 native reference.
- [x] StitchFlow fallback is documented.
- [x] Brand-distance review has zero copied Krisp elements.
- [x] Accessibility rules cover keyboard, focus, screen readers, contrast, non-color cues, and overflow.
- [x] No secrets, real meeting content, signed URLs, emails, payment details, or account-private values appear in design artifacts.
- [x] V6 visual QA inspected rebuilt screenshots, visible-copy audit, overflow, button/sidebar/row geometry, and speaker lanes after the new page was created.
