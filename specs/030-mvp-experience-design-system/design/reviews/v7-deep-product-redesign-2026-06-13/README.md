# V7 Deep Product Redesign Audit

Date: 2026-06-13
Feature: `030-mvp-experience-design-system`
Status: in progress; v6 rejected by stakeholder taste/product review; first
v7 IA rebuild, v7.1 fix-pass, v7.2 polish, and v7.3 screen-by-screen pass are
superseded; v7.4 Krisp IA correction candidate created in Figma with machine QA
passing.

## Why V7 Exists

The v6 page passed narrow mechanical checks, but the stakeholder review found
that those checks were not sufficient for product readiness. The design still
felt too screen-by-screen, too empty, and not enough like a real daily meeting
workspace.

Observed blocker classes:

- inconsistent perceived button sizing and toolbar hierarchy;
- orphaned flows such as standalone workspace/server connection, standalone
  search/filter, standalone processing, and standalone desktop upload;
- settings IA underdesigned, especially theme, auth/session, meeting detection,
  recording policy, diagnostics, and workspace policy boundaries;
- technical copy still driving too much of the design model even when literal
  implementation labels were removed;
- desktop recording state designed as a separate window instead of a compact
  always-visible native trust layer plus menu-bar controller;
- too much empty space and not enough meeting-list density;
- auth/onboarding missing provider sign-in and overemphasizing local mode;
- permission flow needs a guided first-open path, not an unexplained route;
- upload and processing should appear as integrated meeting-list states;
- web cabinet should use Krisp-like IA lessons: dense list, inline filters,
  upload action, status rows, and settings separated from the daily workspace.

## V7 Design Decision

V7 must be rebuilt around three persistent product spaces:

1. **Meeting workspace**: the default desktop and web surface. It includes
   search, filters, upload entry, meeting rows, recording rows, processing rows,
   failures, and ready transcripts.
2. **Review workspace**: transcript, playback, notes/actions, speaker lanes,
   provenance, share/export/delete handoffs.
3. **Settings workspace**: account, appearance, recording behavior,
   auto-meeting detection, notifications, storage/local queue, workspace policy,
   integrations, and diagnostics.

Standalone setup/status screens are allowed only when they are true lifecycle
states: first-run auth, first-run permissions, signed-out/offline, blocked
permission, or destructive confirmation.

## Required V7 Changes

- Replace `Workspace/server connection` with a small account/sync chip, account
  menu, and diagnostics-only status detail.
- Replace large "server online" badges with compact status in app header/menu
  bar: `Синхронизировано`, `Офлайн`, `Очередь`, `Нужно войти`.
- Remove visible `native`, `server route`, `web-view`, and similar language
  from user-facing product screens.
- Make auth compact: provider sign-in first, email secondary, local mode only as
  a policy-aware advanced path.
- Add guided permissions on first open with visual steps and clear recovery.
- Add auto-meeting detection prompt and settings policy:
  `Спрашивать перед каждой встречей`, `Записывать автоматически`, `Не
  предлагать`.
- Keep active recording in the header/menu-bar controller; do not make it a
  separate full product window.
- Put upload in the meeting workspace as a drawer/sheet or inline panel; create
  a row immediately after file selection.
- Put processing in the meeting list row and expandable detail, not a generic
  standalone dashboard.
- Put search and filters on the meeting list page; advanced filters open as a
  popover/sheet.
- Add date/time to meeting rows and make status meaningful at a glance.
- Add light/dark/system theme switching in settings and token proof.

## Standards And References

Use these as rules, not decoration:

- Apple HIG menu bar, toolbar, sidebar, menus, toggles, and search-field
  guidance for the macOS shell.
- WCAG 2.2 target size, focus visibility, status messages, language, and
  keyboard access.
- NN/g guidance for faceted filters, data tables, complex applications, empty
  states, tabs, and low-cognitive-load forms.
- Material 3 guidance for search, chips, menus, top app bars, and navigation
  components as cross-platform web patterns.
- Krisp clean-room IA lessons from `design/evidence/krisp-full-navigation-audit.md`
  and saved route screenshots. Do not copy Krisp assets, copy, exact layout, or
  private content.

## Completion Rule

V7 is not done when a page "looks clean". It is done only when each screen group
has:

- a written task and acceptance rule;
- a five-critic review pass;
- fixes applied after the review;
- a Figma node/property audit;
- a screenshot/contact-sheet review;
- no known stakeholder blocker left unresolved.

## Historical Figma V7.4 Correction Candidate

V7.4 is preserved as review evidence only. It has been superseded by the active
V8 clean Russian design page and should not be used as the implementation
handoff source.

- File: <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr>
- Page: `030 MVP Experience v7.4 - Krisp IA corrected RU`
- Page id: `210:2`
- Visible frames: 16.
- Current QA: `buttonCount=99`, `buttonIssueCount=0`,
  `wrappedButtonTextCount=0`, `forbiddenNavCount=0`, `technicalHitCount=0`,
  `latinHitCount=0`, `reactionNodeCount=13`, `totalReactions=13`,
  `reactionIssueCount=0`, and speaker lanes preserved in review, active
  embedded review, and light review modes.
- Visual evidence: key v7.4 frames were reviewed through inline Figma Plugin API
  screenshots; auth overflow was found and fixed before this status was
  recorded.

This is not final handoff until stakeholder acceptance is recorded. The
five-critic review was rerun on v7.3 and its blockers were addressed in v7.4:
active recording no longer behaves as a destination, queue/upload/search/
processing stay inside the meeting cockpit, settings are a real console,
speaker assignment is a review mode with separate lanes, governance is
browser-owned, and light-theme proof is preserved.

## Superseded Figma V7.3 Draft

- Page: `030 MVP Experience v7.3 - Screen-by-screen polish RU`
- Page id: `177:2`
- Historical status: failed five-critic handoff review. V7.3 still had too much
  standalone-state thinking around active recording, queue/upload, upload
  drawer, settings, speaker assignment, and governance.

## Superseded Figma V7.2 Polish Candidate

- Page: `030 MVP Experience v7.2 - Pixel polish RU`
- Page id: `158:2`
- Historical QA: 64 buttons, tokenized button heights `32/36/40`, radius `6`,
  `buttonIssueCount=0`, no forbidden top-level search/upload/processing nav,
  no product technical-copy leaks, no English UI leaks, and 34 valid prototype
  reactions.

## Superseded Figma V7.1 Draft

- Page: `030 MVP Experience v7.1 - Krisp IA polish RU`
- Page id: `143:2`
- Visible frames: 16.
- Historical QA: 68 buttons, tokenized button heights `32/36/40`, radius `6`,
  `buttonIssueCount=0`, no technical-copy leaks, no English UI leaks, 10 valid
  prototype reactions, and speaker lanes preserved.
- Screenshot evidence:
  `screenshots/v7-1-polish-fixpass-contact-sheet.png`.

## Superseded Figma V7 Draft

- Page: `030 MVP Experience v7 - IA rebuilt RU`
- Page id: `137:2`
- Frames: 19.
- Historical QA: 95 buttons, tokenized button heights `32/36/40`, radius `6`,
  `overflowCount=0`, no forbidden top-level search/upload/processing nav, no
  product technical-copy leaks outside allowed setup/settings/appendix frames,
  16 valid prototype reactions, and speaker lanes preserved in review and
  speaker-assignment modes.
- Screenshot evidence:
  `screenshots/v7-full-contact-sheet.png`.

The first visual pass improved IA, but first-run/auth/permissions needed
denser, more product-grade composition, light theme proof needed more product
frames, and critic review found missing menu-bar, active embedded, and
governance proof.
