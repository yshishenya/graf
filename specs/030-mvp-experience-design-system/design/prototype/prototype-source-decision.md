# Prototype Source Decision

## Decision

Use Figma as the prototype source for feature `030`. The first Figma page
remains historical evidence only. The light/English v2 page is also
superseded. The Russian dark v3 page is also superseded after stakeholder
review because it remained too rough and not sufficiently kit-grounded. The
v4.1 free-kit redesign is also superseded because 14 frames were not enough for
full MVP design coverage. The v5 full-flow redesign is now superseded after the
2026-06-13 Krisp/code/Figma re-audit. V6 is also superseded for implementation
handoff after stakeholder product/design review. The first v7 IA rebuild is
superseded by v7.1, v7.1 is superseded by v7.2, v7.2 is superseded by v7.3,
v7.3 is superseded by v7.4, and v7.4 is superseded by V8. V8 is the active
clean Russian visual and clickable redesign draft.

## Why

- Figma connector authenticated successfully.
- A second Figma account/team with usable limits became available, avoiding the
  earlier starter-plan friction.
- New design file was created successfully.
- Editable v1 frames and click reactions were created through the Figma API.
- Full pre-redesign audit required replacing the v1 page with a v2 page, then
  replacing v2 with a Russian dark v3 page.
- Stakeholder review rejected v3; v4.1 used the free Figma Simple Design
  System for the web/cabinet surface and Apple macOS 26 as the native reference
  kit for macOS.
- Follow-up critique found that v4.1 was useful as an executive walkthrough but
  not enough for a full launch design; v5 expands the prototype to auth,
  permissions, desktop, web list, upload, processing, review, speakers, actions,
  scoped AI, share, export, deletion, settings, browser-only handoff, empty
  states, light-theme proof, tokens, route matrix, and click map.
- 2026-06-13 re-audit found that v5 is broad but not handoff-ready: same-row
  toolbar radius mismatch, stale duplicate controls, visible technical labels,
  and insufficient speaker-assignment emphasis remain.
- 2026-06-13 stakeholder review found that v6 is still not handoff-ready:
  fragmented IA, standalone search/upload/processing screens, underdesigned
  settings, ambiguous auth/local mode, active recording as a page, missing
  auto-detect policy, too much empty space, and insufficient theme proof.
- V7 rebuilt the prototype around meeting workspace, recording shell state,
  integrated upload/processing, meeting review, settings, auto-detection, and
  theme proof.
- V7.1 applies the five-critic fix-pass: compact first-run composition,
  menu-bar invariants, active recording over embedded review,
  share/export/delete governance, and expanded light critical-state proof.
- V7.2 applies the pixel-polish pass: rebuilt IA map, smaller auth, guided
  permissions, fuller settings, removed/deferred global `Действия` nav, and
  repaired cross-frame prototype links.
- V7.3 exposed remaining handoff blockers during the screen-by-screen
  five-critic review: active recording still behaved like a destination, queue
  and upload were too prominent, settings were not deep enough, and speaker
  assignment/governance needed stronger product treatment.
- V7.4 applies the Krisp IA correction: meeting cockpit as default surface,
  inline upload/status, active recording as native shell/menu-bar state,
  compact provider auth, guided permissions, real settings console, speaker
  lanes, browser-owned governance, and light proof.
- V8 applies the clean Russian pass after the remaining stakeholder critique:
  it keeps the same product IA, removes the last visible technical/English copy
  leaks, fills out web list/detail/governance and light-theme proof, and rebuilds
  the clickable MVP owner value loop.

## Evidence

- Current file URL:
  [https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr](https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr)
- Current file key: `ylPz3AxOOfVoLJEG4dF9Yr`
- Active V8 page: `030 MVP Experience v8 - Clean RU`
- Active V8 page id: `341:2`
- Actual V8 frames: 17 visible top-level frames.
- Actual V8 click reactions: 92 valid `ON_CLICK` reactions across 92 nodes,
  with 0 invalid destinations, 0 self-links, and required owner-value-loop
  coverage passing.
- Historical v1 frames: 11
- Historical v1 click reactions: 10
- Superseded v2 page: `030 MVP Experience v2 - Cabinet First`
- Superseded v3 page: `030 MVP Experience v3 - Dark RU`
- Superseded v4.1 page: `030 MVP Experience v4 - SDS + macOS 26`
- Actual v4.1 page id: `3:2`
- Actual v4.1 frames: 14 primary MVP frames.
- Actual v4.1 product click reactions: 5 main-path reactions.
- Superseded v5 page: `030 MVP Experience v5 - Full MVP Flow`
- Actual v5 page id: `17:2`
- Actual v5.1 frames: 36 top-level frames.
- Actual v5.1 product click reactions: 82 button reactions, 130 sidebar/nav
  reactions, and 8 meeting-row/status-pill reactions.
- Actual v5 product UI language: Russian.
- Actual v5 primary theme: dark, with light-theme proof frames.
- Actual v5.1 layout audit: `appOverflowCount=0`.
- Superseded v6 page: `030 MVP Experience v6 - Krisp-grounded RU`
- Superseded v6 page id: `118:2`
- Actual v6 frames: 29 top-level frames.
- Actual v6 click reactions: 183 valid `ON_CLICK` reactions with 0 invalid
  prototype destinations.
- Actual v6 mechanical QA: `totalButtons=70`, `buttonClusterIssues=0`,
  `technicalCopyHits=0`, `overflowCount=0`.
- Superseded v7 page: `030 MVP Experience v7 - IA rebuilt RU`
- Superseded v7 page id: `137:2`
- Actual v7 draft frames: 19 top-level frames.
- Actual v7 draft QA: `totalButtons=95`, button heights `32/36/40`, button
  radius `6`, `overflowCount=0`, `technicalCopyLeaks=0`,
  `forbiddenTopLevelNav=0`.
- Superseded v7.1 page: `030 MVP Experience v7.1 - Krisp IA polish RU`
- Superseded v7.1 page id: `143:2`
- Actual v7.1 visible frames: 16 top-level frames.
- Actual v7.1 QA: `buttons=68`, button heights `32/36/40`, button radius `6`,
  `buttonIssueCount=0`, `overflowCount=0`, `technicalCopyLeaks=0`,
  `englishHitCount=0`, `reactionIssueCount=0`, and 10 valid cross-frame
  prototype reactions.
- Superseded v7.2 page: `030 MVP Experience v7.2 - Pixel polish RU`
- Superseded v7.2 page id: `158:2`
- Actual v7.2 visible frames: 16 top-level frames.
- Actual v7.2 QA: `buttons=64`, button heights `32/36/40`, button radius `6`,
  `buttonIssueCount=0`, `technicalCopyLeaks=0`, `englishHitCount=0`,
  `forbiddenTopLevelNav=0`, `reactionIssueCount=0`, and 34 valid cross-frame
  prototype reactions.
- Superseded v7.3 page: `030 MVP Experience v7.3 - Screen-by-screen polish RU`
- Superseded v7.3 page id: `177:2`
- Actual v7.3 status: failed five-critic handoff review.
- Active v8 page: `030 MVP Experience v8 - Clean RU`
- Active v8 page id: `341:2`
- Actual v8 visible frames: 17 top-level frames.
- Actual v8 QA: frame-bound overflow `0`, bad button heights `0`, bad chip
  heights `0`, visible forbidden implementation copy `0`, placeholder artifact
  nodes `0`, English UI/review-copy leaks `0`, text overlap `0`; buttons use
  `36/40px`, compact segmented/theme controls use `32px`, and chips use
  `28px`.
- Superseded v7.4 page: `030 MVP Experience v7.4 - Superseded by v8`
- Superseded v7.4 original page id: `210:2`
- Actual v4.1 live kit evidence: SDS Upload plus SDS Button, Search, Input
  Field, Tag, and Switch Field samples.
- Apple macOS 26 status: selected as native kit reference; real Apple instances
  require manual Figma library attachment because MCP import was not permitted.
- Repo mirror: `design/` artifacts in this feature directory.

## Fallback

StitchFlow remains documented in `design/prototype/stitchflow-fallback.md` and
is used only if Figma v8 handoff becomes blocked.
