# Design Artifact Index: MVP Product Experience And Design System

Feature `030-mvp-experience-design-system` produces the reviewable MVP product experience blueprint for `2brain Rec`.

## Current Design Source

- Primary product design source: [`mvp-experience-blueprint.md`](mvp-experience-blueprint.md).
- Direction: cabinet-first desktop app with native capture trust shell and
  embedded desktop-safe web cabinet subset.
- Status: v6 passed narrow mechanical QA but was rejected by stakeholder
  product/design review. The first v7 IA rebuild draft, v7.1 fix-pass, v7.2
  pixel polish, v7.3 critique pass, and v7.4 correction pass are superseded.
  V8 is now the active clean Russian review candidate: meeting cockpit as the
  default surface, active recording as menu-bar/header state,
  upload/search/processing integrated into the meeting workspace, full web
  list/detail/governance screens, fuller settings, compact auth, guided
  permissions, speaker lanes, dark/light proof, and component QA rules. Final
  stakeholder visual acceptance is still required before implementation
  handoff.

## Prototype Source

- Preferred source used: Figma.
- Current Figma file: [https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr](https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr)
- Current Figma file key: `ylPz3AxOOfVoLJEG4dF9Yr`
- Active v8 page: `030 MVP Experience v8 - Clean RU`.
- Active v8 page id: `341:2`.
- V8 visible frame count: 17 top-level visible frames.
- V8 QA: frame-bound overflow `0`, bad button heights `0`, bad chip heights
  `0`, visible forbidden implementation copy `0`, placeholder artifact nodes
  `0`, English UI/review-copy leaks `0`, text overlap `0`; buttons use
  `36/40px`, compact segmented/theme controls use `32px`, and chips use
  `28px`.
- V8 clickable QA: 92 valid `ON_CLICK` reactions across 92 nodes,
  invalid destinations `0`, self-links `0`, superseded-page destinations `0`,
  and required owner-value-loop coverage PASS.
- V8 five-critic screen audit:
  `reviews/v8-clean-ru-2026-06-15/five-critic-screen-audit.md`.
- V8 stakeholder visual approval pack:
  `reviews/v8-clean-ru-2026-06-15/stakeholder-visual-approval-pack.md`.
- V8 proof coverage: flow map, compact provider auth, guided macOS
  permissions, desktop meeting workspace, detected-meeting prompt, active
  recording shell, inline upload/processing, transcript review, speaker lanes,
  settings, web meeting list, web meeting detail, share/export/delete, shared
  upload sheet, command search/filter overlay, light product proof, and
  QA/component rules.
- Superseded v7.4 page: `030 MVP Experience v7.4 - Superseded by v8`.
- Superseded v7.4 original page id: `210:2`.
- Superseded v7.3 page: `030 MVP Experience v7.3 - Screen-by-screen polish RU`.
- Superseded v7.3 page id: `177:2`.
- V7.3 status: failed five-critic review because active recording still behaved
  like a destination, settings were under-realized, top-level queue/upload
  surfaces remained too prominent, upload/search/status were fragmented, and
  speaker assignment was not strong enough as a daily review mode.
- Superseded v7.2 page: `030 MVP Experience v7.2 - Pixel polish RU`.
- Superseded v7.2 page id: `158:2`.
- V7.2 QA: `buttons=64`, button heights `32/36/40`, button radius `6`,
  `buttonIssueCount=0`, `technicalCopyLeaks=0`, `englishHitCount=0`,
  `forbiddenTopLevelNav=0`, `reactionIssueCount=0`, and 34 valid cross-frame
  prototype reactions.
- Superseded v7.1 page: `030 MVP Experience v7.1 - Krisp IA polish RU`.
- Superseded v7.1 page id: `143:2`.
- V7.1 QA: `buttons=68`, 10 valid cross-frame prototype reactions.
- Superseded v7 page: `030 MVP Experience v7 - IA rebuilt RU`.
- Superseded v7 page id: `137:2`.
- V7 draft frame count: 19 top-level frames.
- V7 draft QA: `totalButtons=95`, button heights `32/36/40`, button radius
  `6`, `overflowCount=0`, `technicalCopyLeaks=0`, `forbiddenTopLevelNav=0`.
- Historical v1 Figma frames: 11 editable frames on page `030 MVP Experience`.
- Superseded v2 page: `030 MVP Experience v2 - Cabinet First`.
- Superseded v3 page: `030 MVP Experience v3 - Dark RU`.
- Superseded v4.1 page: `030 MVP Experience v4 - SDS + macOS 26`.
- Superseded v4.1 page id: `3:2`.
- V4.1 frame count: 14 primary MVP frames.
- V4.1 product reaction count: 5 main-path reactions.
- Superseded v5 page: `030 MVP Experience v5 - Full MVP Flow`.
- Superseded v5 page id: `17:2`.
- Superseded v6 page: `030 MVP Experience v6 - Krisp-grounded RU`.
- Superseded v6 page id: `118:2`.
- V6 frame count: 29 top-level frames.
- V6 QA: `totalButtons=70`, `reactionNodeCount=183`,
  `totalReactions=183`, `reactionIssues=0`, `buttonClusterIssues=0`,
  `technicalCopyHits=0`, `overflowCount=0`.
- V5.1 frame count: 36 top-level frames.
- V5.1 product reaction count: 82 button reactions, 130 sidebar/nav reactions,
  and 8 meeting-row/status-pill reactions.
- Historical V5.1 layout QA: `appOverflowCount=0`; superseded by the
  2026-06-13 re-audit because button/radius and technical-copy blockers
  remained in v5.
- Free kit basis: Figma Simple Design System for web/cabinet; Apple macOS 26 as
  native macOS reference until manual library attachment enables real Apple
  instances.
- StitchFlow fallback: documented but not used because Figma creation and editing succeeded.

## Artifact Groups

- `evidence/`: current product, full Krisp clean-room navigation audit,
  v10/v11 Krisp web/desktop route observation, desktop app, and web cabinet
  observations.
- `screens/`: desktop, embedded cabinet, and web screen specifications.
- `system/`: terminology, design tokens, components, localization, and accessibility.
- `visual/`: visual direction, iconography, asset inventory, static pack, brand distance, and QA.
- `prototype/`: Figma handoff, StitchFlow fallback readiness, clickable paths, and source decision.
- `backlog/`: follow-up feature candidates and implementation handoff.

## Acceptance Boundary

This feature does not implement production UI, capture, auth, MediaScribe, sharing, deletion jobs, or rollout code. It creates implementation-ready design and product artifacts.

## Active V8 Product Rules

- The desktop first screen must show a real meeting/cabinet experience, not
  only driver or readiness diagnostics.
- Native macOS controls own Record, Stop, active recording indicator,
  permissions, local artifact truth, upload queue truth, and local recovery.
- Server web/backend product UI owns meetings, manual upload metadata,
  processing, transcript review, notes, action items, speaker assignment,
  account/workspace, deletion/access, and browser-only admin surfaces.
- The embedded desktop cabinet is an allowlisted subset of the web cabinet.
- Variable product UI is server-owned and embeddable across macOS, Windows,
  and Linux desktop shells; native shells keep only platform-critical capture,
  permissions, local buffer/queue, tray/menu, diagnostics, and route guard.
- Browser-only routes are hidden, disabled, or opened in browser from desktop.
- Meaningless test data is forbidden in visual prototypes; use realistic
  neutral Russian meeting examples or approved seeded records.
- Dark theme is the primary MVP visual mode; light mode is represented by
  dedicated proof frames and must remain available through settings.
- Russian is the primary MVP UI language. English remains a localization
  matrix/future translation concern, not the launch prototype language.
- The full pre-redesign audit is captured in
  [`evidence/krisp-full-navigation-audit.md`](evidence/krisp-full-navigation-audit.md);
- The fresh v7.4 Krisp route/window observation is captured in
  [`evidence/krisp-v10-web-desktop-audit.md`](evidence/krisp-v10-web-desktop-audit.md);
- v6 visual work resolved some mechanical issues but was not enough. v7 rebuilt
  the IA, v7.1 applied the critic fix-pass, v7.2 added pixel polish, v7.3
  exposed remaining product-flow blockers, v7.4 corrected the IA, and v8 is
  the current clean Russian review candidate for web/detail/governance,
  settings, shared upload, command search/filter overlay, component QA, and
  dark/light handoff. Final visual approval is still required.
