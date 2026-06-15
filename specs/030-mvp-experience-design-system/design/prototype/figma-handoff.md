# Figma Handoff

## Current Status

V8 is now the active redesign direction. It is the clean Russian pass after the
Krisp-IA-corrected v7.4 lineage and the follow-up stakeholder critique found
remaining settings, button consistency, web-cabinet, light-theme, and
technical-copy issues. It is not final implementation handoff until stakeholder
acceptance is recorded.

- Current file:
  [https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr](https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr)
- Active v8 page: `030 MVP Experience v8 - Clean RU`
- Active v8 page id: `341:2`
- V8 visible frame count: 17.
- V8 QA: frame-bound overflow `0`, bad button heights `0`, bad chip heights
  `0`, visible forbidden implementation copy `0`, placeholder artifact nodes
  `0`, English UI/review-copy leaks `0`, text overlap `0`; buttons use
  `36/40px`, compact segmented/theme controls use `32px`, and chips use
  `28px`.
- V8 clickable QA: 92 valid `ON_CLICK` reactions across 92 nodes,
  `issueCount=0`, all destinations are visible V8 frames, no self-links, and
  required owner-value-loop coverage passes.
- V8 speaker-lane proof: `V8 08` uses one separate lane per speaker with
  visible percentages, assignment actions, participant names, low-confidence
  review, and save action.
- V8 product correction: keeps the meeting cockpit as the default surface,
  keeps active recording in the menu-bar/header shell, integrates upload and
  processing into meeting lists, adds full web list/detail/governance screens,
  makes settings a real list-detail console, adds shared upload, contextual
  command search/filter overlay, compact provider auth, guided permissions,
  dark/light proof, and component QA rules.
- V8 QA detail:
  `design/reviews/v8-clean-ru-2026-06-15/figma-v8-qa.md`.
- V8 five-critic screen audit:
  `design/reviews/v8-clean-ru-2026-06-15/five-critic-screen-audit.md`.
- V8 stakeholder visual approval pack:
  `design/reviews/v8-clean-ru-2026-06-15/stakeholder-visual-approval-pack.md`.
- Superseded v7.4 page: `030 MVP Experience v7.4 - Superseded by v8`
- Superseded v7.4 original page id: `210:2`
- Superseded v7.3 page: `030 MVP Experience v7.3 - Screen-by-screen polish RU`
- Superseded v7.3 page id: `177:2`
- V7.3 failure summary: 16 frames and clickable coverage existed, but critic
  review still found active recording as a destination, over-prominent queue,
  weak settings controls, too much test-like status copy, upload/status
  fragmentation, and insufficiently strong speaker-assignment workflow.
- Superseded v7.2 page: `030 MVP Experience v7.2 - Pixel polish RU`
- Superseded v7.2 page id: `158:2`
- V7.2 QA: `buttons=64`, button heights `32/36/40`, button radius `6`,
  `buttonIssueCount=0`, `technicalCopyLeaks=0`, `englishHitCount=0`,
  `forbiddenTopLevelNav=0`, `reactionIssueCount=0`, and 34 valid cross-frame
  prototype reactions.
- Superseded v7.1 page: `030 MVP Experience v7.1 - Krisp IA polish RU`
- Superseded v7.1 page id: `143:2`
- V7.1 visible frame count: 16.
- V7.1 QA: `buttons=68`, 10 valid cross-frame prototype reactions.
- V7.1 screenshot evidence:
  `design/reviews/v7-deep-product-redesign-2026-06-13/screenshots/v7-1-polish-fixpass-contact-sheet.png`.
- V7.1 product proof added after critic review: menu-bar controller, active
  recording over embedded review, share/export/delete governance, and light
  critical states.
- Superseded v7 page: `030 MVP Experience v7 - IA rebuilt RU`
- Superseded v7 page id: `137:2`
- V7 draft frame count: 19.
- Superseded v6 page: `030 MVP Experience v6 - Krisp-grounded RU`
- Superseded v6 page id: `118:2`
- V6 frame count: 29.
- V6 clickable prototype: 183 valid `ON_CLICK` reactions; no self-destination
  or non-frame destination issues.
- V6 final programmatic QA: `totalButtons=70`, `buttonClusterIssues=0`,
  `technicalCopyHits=0`, `overflowCount=0`.
- V6 speaker-lane contract: `V6 16`, `V6 18`, and `V6 19` each have 4 speaker
  tracks, 10 segments, and 4 talk-time percentages.
- V6 screenshot evidence:
  `design/reviews/v6-krisp-code-audit-2026-06-13/screenshots/`.

V6 rejection reasons are captured in
`design/reviews/v7-deep-product-redesign-2026-06-13/`. The main blockers are
fragmented IA, standalone search/upload/processing screens, underdesigned
settings, auth/local-mode ambiguity, active recording as a page instead of a
native shell state, missing auto-meeting detection policy, no real theme switch,
and weak density/empty-space handling.

V5 is also no longer accepted for implementation handoff. The 2026-06-13 live
Krisp/code/Figma re-audit found real blockers in the live canvas:

- inconsistent same-row button radii in `V5 15`;
- stale duplicate toolbar controls in meeting review;
- visible technical labels such as `Сервер в сети`, `нативный`, and route/debug
  copy in product frames;
- speaker assignment needs to be rebuilt as a primary review mode with one
  lane per speaker across browser and embedded desktop;
- current macOS code is diagnostics-first, so the design must more explicitly
  specify the app/product split before implementation.

V5, v6, the first v7 pass, v7.1, v7.2, v7.3, and v7.4 remain useful
coverage/evidence inventories. The active design target is v8.

- Historical v1-v3 file:
  [https://www.figma.com/design/XZKEfkdYsVuq2dhRRp8dD1](https://www.figma.com/design/XZKEfkdYsVuq2dhRRp8dD1)
- Historical v1-v3 file key: `XZKEfkdYsVuq2dhRRp8dD1`
- Current plan/account status: Figma team account with usable limits.
- Historical v1 page: `030 MVP Experience`
- Historical v1 frames: 11
- Historical v1 prototype reactions: 10 sequential `ON_CLICK` reactions.
- V1 status: rejected for final design handoff after full pre-redesign audit.
- Superseded v2 page: `030 MVP Experience v2 - Cabinet First`
- V2 status: rejected for final handoff because the direction was still
  light/English and not aligned with the requested Russian dark MVP interface.
- Superseded v3 page: `030 MVP Experience v3 - Dark RU`
- V3 status: rejected for final handoff after stakeholder review; it was
  Russian/dark but still too rough and not sufficiently kit-grounded.
- Superseded v4.1 file:
  [https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr](https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr)
- Superseded v4.1 file key: `ylPz3AxOOfVoLJEG4dF9Yr`
- Superseded v4.1 page: `030 MVP Experience v4 - SDS + macOS 26`
- Superseded v4.1 page id: `3:2`
- Actual v4.1 frames: 14 primary MVP frames.
- Actual v4.1 product click reactions: 5 main-path `ON_CLICK` reactions:
  desktop start, quick record, quick upload, open cabinet, and open ready
  meeting review.
- Superseded v5 file:
  [https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr](https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr)
- Superseded v5 file key: `ylPz3AxOOfVoLJEG4dF9Yr`
- Superseded v5 page: `030 MVP Experience v5 - Full MVP Flow`
- Superseded v5 page id: `17:2`
- Actual v5.1 frames: 36 top-level frames covering auth, server connection,
  permissions, native desktop, menu bar, upload, processing, meeting review,
  speaker assignment, actions, AI drawer, share, export, deletion, settings,
  browser-only handoff, empty states, light-theme coverage, tokens, route
  matrix, critics board, click map, desktop embedded speaker assignment, and
  active recording over embedded web.
- Actual v5.1 product click reactions: 82 button `ON_CLICK` reactions, 130
  sidebar/nav `ON_CLICK` reactions, and 8 meeting-row/status-pill reactions.
- Historical v5.2 QA audit: `frameCount=36`, `buttons=106`, `buttonReactions=82`,
  `navReactions=130`, `rowAndPillReactions=8`, `totalClickReactions=220`,
  `appOverflowCount=0`.
- The historical live Figma polish audit is superseded by the 2026-06-13
  re-audit. It previously claimed final button and speaker-lane readiness, but
  the live canvas still contains mismatched toolbar radii, stale duplicate
  controls, and user-visible technical labels.
- Non-navigating local-state controls are intentionally left without fake
  transitions where the current frame already shows the relevant state, such as
  `Скачать`, `Изменить`, `Назначить`, and `Отозвать ссылку`.
- Live kit evidence: SDS `Upload` instance in the upload screen plus live SDS
  Button, Search, Input Field, Tag, and Switch Field samples in the component
  map frame.
- Apple macOS 26 caveat: the library is visible to the account, but MCP import
  returned a permission error; the desktop frames therefore use Apple macOS 26
  geometry and hierarchy as reference until the library is manually attached in
  Figma.
- Primary UI language: Russian.
- Primary theme: dark, with dedicated light proof frames and a settings theme
  control.

## Superseded V5 Frame Inventory

These frames remain useful as coverage inventory, but they are not accepted as
the final visual direction.

- `V5 00 - Full flow cover and acceptance map`: MVP value and route coverage.
- `V5 01 - Auth sign-in and local policy`: sign-in and local-only policy.
- `V5 02 - Workspace/server connection`: API/storage/worker connection.
- `V5 03 - macOS permissions onboarding`: required native permissions.
- `V5 04 - Desktop ready cabinet`: native capture shell plus embedded cabinet.
- `V5 05 - Desktop active recording`: active capture and persistent Stop.
- `V5 06 - Menu bar controller`: compact local status controller.
- `V5 07 - Desktop saved/upload queue`: saved, queued, upload, retry states.
- `V5 08 - Desktop embedded upload`: desktop-safe upload entry.
- `V5 09 - Web meetings list`: dense status list, upcoming meetings, ask bar.
- `V5 10 - Search and filters`: browser-rich filtering.
- `V5 11 - Web upload and metadata`: owned media upload form.
- `V5 12 - Upload validation errors`: file/type/size validation.
- `V5 13 - Processing status`: stage history and transcript readiness.
- `V5 14 - Degraded processing`: partial/failure states.
- `V5 15 - Meeting review with transcript and timeline`: review hub.
- `V5 16 - Speaker assignment and talk time`: speaker correction workflow.
- `V5 17 - Notes decisions and assigned actions`: task/value extraction.
- `V5 18 - Action item edit drawer`: assignee/status/source edits.
- `V5 19 - Scoped AI drawer`: meeting-scoped assistant.
- `V5 20 - Share and access`: scoped access, link, revoke model.
- `V5 21 - Export and download`: export formats with audit log.
- `V5 22 - Delete and retention truth`: deletion truth by storage area.
- `V5 23 - Account security and settings`: account and server settings.
- `V5 24 - Browser-only handoff`: web-only routes absent from desktop.
- `V5 25 - Empty states`: first-run, no data, offline states.
- `V5 26 - Light desktop ready`: light-theme desktop proof.
- `V5 27 - Light web meetings`: light-theme web list proof.
- `V5 28 - Light upload`: light-theme upload proof.
- `V5 29 - Light review`: light-theme review proof.
- `V5 30 - Tokens and components`: token/component board.
- `V5 31 - Native/web route matrix`: route ownership map.
- `V5 32 - Critics fixes board`: review fix evidence.
- `V5 33 - Prototype click map`: click-path overview.
- `V5 34 - Desktop embedded speaker assignment`: server-owned speaker
  assignment route hosted inside the platform desktop shell.
- `V5 35 - Active recording with embedded review`: active native Stop pinned
  above embedded web content.

## Access Constraints

The file is in the authenticated user's Figma drafts/team context. Repo artifacts remain source of truth if external access changes.

## QA Evidence

- Historical Figma v5.1 programmatic audit: `frameCount=36`, `buttons=106`,
  `buttonReactions=82`, `navReactions=130`, `rowAndPillReactions=8`,
  `totalClickReactions=220`, `appOverflowCount=0`.
- 2026-06-13 re-audit blocker: `V5 15` contains same-row toolbar buttons with
  mixed radii (`0` and `7`) plus stale duplicate controls.
- 2026-06-13 re-audit blocker: product frames expose technical implementation
  labels such as `Сервер в сети`, `нативный`, route names, and backend service
  names.
- 2026-06-13 re-audit blocker: speaker lanes exist in some frames, but v6 must
  treat one-lane-per-speaker as the primary speaker assignment contract, not as
  supporting decoration.
- Historical v6 click validation: 183 valid `ON_CLICK` reactions across auth,
  desktop record/stop, upload, processing, meeting review, speaker assignment,
  notes/actions, share, export, delete, settings, browser handoff, empty states,
  web nav, and meeting rows.
- Historical v5 click validation: 82 button reactions, 130 sidebar/nav
  reactions, and 8 meeting-row/status-pill reactions.
- Visual screenshot QA saved under
  `design/reviews/v5-full-flow-critics-2026-06-11/screenshots/`.
- Non-blocking caveat: Apple macOS 26 library import still requires manual
  library attachment or permission change before real Apple instances can
  replace the desktop reference geometry.
