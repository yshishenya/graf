# V6 Krisp-Grounded Code And Design Audit

Date: 2026-06-13
Feature: `030-mvp-experience-design-system`
Status: v5 rejected for handoff; v6 mechanically passed narrow QA but was
rejected by stakeholder product/design review. Continue with v7.

## Why This Audit Exists

The previous v5 handoff claimed button consistency, speaker-lane coverage, and
final visual QA. A fresh inspection found that the real Figma page and the
current macOS code still contain design blockers:

- same-row controls with mismatched radii and stale duplicate buttons;
- visible technical labels in product UI such as `Сервер в сети`, `нативный`,
  route names, and internal backend component names;
- a desktop app implementation that is currently diagnostics-first rather than
  a finished recorder/library product;
- speaker assignment shown in some places, but not yet treated as a first-class
  review workspace anchored by one lane per speaker.

This means v5 is useful as a coverage inventory, but it is not acceptable as
the final MVP design target.

## Evidence Used

- Live Krisp web account in Zen, inspected through route navigation and
  screenshots.
- Live Krisp desktop app, inspected visually and via local bundle metadata/logs.
- Current Figma file `ylPz3AxOOfVoLJEG4dF9Yr`, page
  `030 MVP Experience v5 - Full MVP Flow`, inspected through the Figma Plugin
  API.
- Current repo code for macOS SwiftUI surfaces and FastAPI backend contracts.
- Official UX/accessibility references:
  - Apple Human Interface Guidelines, Buttons:
    <https://developer.apple.com/design/human-interface-guidelines/buttons>
  - W3C WCAG 2.2 Target Size and Status Messages:
    <https://www.w3.org/TR/WCAG22/#target-size-minimum>,
    <https://www.w3.org/TR/WCAG22/#status-messages>
  - Material Design 3 Buttons:
    <https://m3.material.io/components/buttons/guidelines>
  - Microsoft Fluent 2 component model:
    <https://fluent2.microsoft.design/>

## Evidence Safety

Do not commit private Krisp meeting transcript text, account email, screenshots
with user content, raw logs with personal data, or downloaded proprietary
bundles. This audit records product structure only.

Local screenshots used for visual review were saved under
`/tmp/2brain-krisp-live-audit/` and are intentionally not added to the repo.

## Current Verdict

V5 should be treated as a rejected coverage map. V6 is now rebuilt as a
stricter, Russian-first, dark MVP design with these non-negotiables:

- first screen must show user value: meetings, upload/record entry, and status;
- desktop native surface owns capture, Stop, permissions, local queue, tray,
  and diagnostics only;
- web/server surface owns variable product UI: meetings, processing,
  transcript, notes, speaker assignment, account, policy, and safe handoffs;
- speaker assignment must use one horizontal lane per speaker everywhere it is
  editable or reviewable;
- button sizes/radii must be tokenized and pass programmatic audit;
- technical implementation copy must be removed from primary product screens;
- every status must be meaningful in both app and web.

## V6 Result

- Figma page: `030 MVP Experience v6 - Krisp-grounded RU`, page id `118:2`.
- Screen coverage: 29 dark Russian frames across auth, desktop, menu bar, web
  cabinet, upload, processing, review, speaker assignment, share/export/delete,
  settings, browser handoff, empty states, tokens, and route matrix.
- Clickable prototype: 183 valid `ON_CLICK` reactions; no self-destination or
  non-frame destination issues.
- Mechanical QA: `totalButtons=70`, `buttonClusterIssues=0`,
  `technicalCopyHits=0`, `overflowCount=0`.
- Speaker-lane QA: `V6 16`, `V6 18`, and `V6 19` each have 4 speaker tracks,
  10 lane segments, and 4 talk-time percentages.
