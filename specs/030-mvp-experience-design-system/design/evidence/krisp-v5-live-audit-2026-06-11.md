# Krisp Live Audit For V5 Redesign

Date: 2026-06-11
Scope: Krisp desktop app, Krisp web meeting-notes page, local installed bundle, and public help/docs where UI could not be safely clicked.

## Evidence Captured

- Desktop window: `design/reviews/v5-full-flow-critics-2026-06-11/screenshots/krisp-desktop-main.png`
- Web meeting notes window: `design/reviews/v5-full-flow-critics-2026-06-11/screenshots/krisp-web-meeting-notes-with-browser-ui.png`
- Installed app path: `/Users/yshishenya/Applications/krisp.app`
- Running app version observed in process annotations: `3.12.5`
- Runtime windows observed: `MAIN`, `WEB`, `WEB_OVERLAY`, `DESKTOP_REPORT_WINDOW`, `CONFIRMATION_WINDOW`, `NOTIFICATION_INDICATOR`, `NOTIFICATION_REMINDER`
- Bundle renderers found: `main_window`, `web_window`, `widget`, `notification_indicator`, `notification_reminder`, `companion`

## Safe Navigation Limits

Direct accessibility tree access is blocked by macOS permissions for `osascript`. Computer Use app-server also failed in this session. I therefore used:

- CoreGraphics window enumeration and screenshots.
- Safe screenshots of already-open Krisp desktop and web windows.
- Local Electron bundle inspection for window names, event names, and feature surfaces.
- Public Krisp help/source checks for meeting-note capabilities.

No destructive Krisp action was clicked. Delete, revoke, upgrade, and sharing actions were not executed.

## Desktop App Surface Observed

Krisp desktop does not behave like a tiny recorder-only utility. It shows a full cabinet-like workspace:

- Left navigation: workspace/account, invite teammates, search, My Meetings, Shared with me, Action Items, Activity, Contacts, Settings, Get Krisp, Developers, Reactivate, account switcher.
- Center content: trial status banner, Upcoming calendar block, Meeting notes table.
- Meeting rows: title, duration, source/status icons, locked states, date.
- Floating assistant/search bar: `Ask anything...`.
- Right panel: Meeting Controls with AI Note Taker mode buttons, Accent Conversion, Noise Cancellation, Krisp Devices, Test Run, Limited mode and Upgrade controls.

V5 implication: 2brain Rec desktop must show a real cabinet, not a blank native shell. But capture-critical controls remain native and visibly local.

## Web Meeting Notes Surface Observed

The web meeting-notes page mirrors the cabinet surface:

- Same central meeting notes list and upcoming block.
- Same dark operational density.
- Same product-account/sidebar framing.
- Browser chrome and side tabs can obscure content, so our web design must be resilient to narrower viewport widths.

V5 implication: desktop embedded cabinet and browser web cabinet should share the same information architecture and API-backed states.

## Bundle Feature Surfaces Found

Local bundle/event names confirm these surface categories:

- Auth and device authentication.
- Dashboard/webview navigation and dashboard initial path.
- Meeting assistant modes.
- Recording start, pause, resume, stop.
- In-person meeting start/stop.
- App call and screen recording permissions.
- Transcript ready and transcription state.
- Save transcription and after-call summary.
- Summary copy and retry.
- Speaker detection vote/hide banner.
- File attach/copy/remove user attached file.
- Note-taker storage type/location.
- Accessibility, microphone, screen/audio processing permission windows.
- Network checker and report/problem windows.
- Widget, notification indicator, reminder, companion overlay.

V5 implication: MVP must include not just one list screen, but also permissions, active capture, queue, status, transcript/review, speaker assignment, actions, sharing/export/delete, settings, and small live surfaces.

## Product Lessons To Apply

1. Desktop shows value immediately: current meetings, statuses, and local controls in one window.
2. Recording control must stay visible and one-action stoppable.
3. Web/cabinet needs dense rows, not marketing cards.
4. Processing states need stage history and clear retry/degraded paths.
5. Meeting review must include transcript, timeline, speakers, notes, decisions, and assigned actions.
6. Speaker assignment belongs to the server-owned review surface; desktop may embed the allowlisted route while native code only hosts it and keeps capture authority local.
7. Speaker separation should be readable as per-speaker lanes: each speaker gets
   a distinct horizontal track with that speaker's segments and a talk-time
   percentage, rather than one combined multicolor timeline strip.
8. Share/export/delete must be first-class MVP flows because they complete the value loop.
9. Empty, locked, limited, failed, and offline states need meaningful actions.
10. Trial/upsell patterns from Krisp should not dominate our MVP first viewport.
11. Design must keep brand distance: no Krisp copy, no Krisp colors as primary identity, no cloning of exact layout proportions.
