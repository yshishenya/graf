# Krisp V10/V11 Web And Desktop IA Audit

Date: 2026-06-14
Updated: 2026-06-15
Scope: fresh Krisp desktop and web cabinet observation for the v7.4 design
correction pass. This is clean-room category learning only; do not copy Krisp
brand, private content, exact UI, icons, screenshots, or proprietary copy.

## Access And Capture Limits

- `System Events` can read the active process, but `click at` is still blocked
  for `osascript` with macOS Accessibility error `-25211`.
- Computer Use re-check: `<computer-use-app>` is installed, signed by OpenAI, notarized, and `SkyComputerUseService`
  starts successfully. However, no callable Computer Use tool is exposed in this
  session, `SkyComputerUseClient` does not stay running as a usable control
  process, and the user TCC database shows no Accessibility/Screen Capture/Post
  Event grants for `com.openai.sky.CUAService` or
  `com.openai.sky.CUAService.cli`.
- General `screencapture` returned only the desktop wallpaper in the v11 pass,
  but window-specific `screencapture -l <window-id>` works.
- Pointer automation through CoreGraphics executed without a system error but
  did not produce reliable navigation changes, so it is not counted as
  click-by-click proof.
- Temporary screenshots were saved under `/tmp/2brain-krisp-v10-audit/` and
  `/tmp/2brain-krisp-v11-a11y-audit/`. They are not committed because they can
  expose private meeting titles, contact names, emails, and account details.
- Safe URL navigation through Zen works for top-level Krisp web routes such as
  meeting notes and settings account in the v10 pass; the v11 direct-open
  attempt did not reliably switch the captured Zen tab and is not counted as
  fresh meeting-notes proof.
- A deeper `settings/ai-note-taker` route produced an unstable capture that
  returned only wallpaper, so it is not counted as verified in this pass.

2026-06-15 update:

- `computer-use` is now callable in this Codex session and can inspect the
  locally installed Krisp desktop app, including screenshots and accessibility
  trees.
- Live desktop coverage now verifies meeting list navigation, global search
  overlay, filter menu, meeting detail `Notes`, meeting detail
  `Recording & Transcript`, speaker assignment lanes, and settings sections:
  account, AI note taker, privacy/consent, app appearance/behavior, language,
  calendar, and notifications.
- `computer-use` is not allowed on `app.krisp.ai` in Zen. It ended the session
  when that browser URL was selected. Web evidence in this file remains a
  route/window-capture and earlier safe-navigation audit, while desktop
  embedded routes are now live-interaction evidence.

## Fresh Desktop Observation

Krisp desktop shows a full product workspace, not only a compact utility. V11
window-specific captures confirm the desktop surface can be inspected even when
general screen capture returns only wallpaper:

- Persistent left navigation: search, my meetings, shared with me, action
  items, activity, contacts, settings, app/developer links, account switcher,
  and plan/reactivation entry.
- Center workspace: dense table/list content with search, filtering, row
  selection, column headers, avatars/status, and action buttons.
- Right rail: meeting/audio controls, AI note taker controls, device selectors,
  test run, limited mode, and upgrade state.
- Secondary compact panel: upcoming meeting entry, meeting button, AI note
  taker state, live-record/bot actions, accent/noise controls, device
  selectors, limited-mode and upgrade controls.

Clean-room implications for `2brain Rec`:

- Desktop should open on the meeting cockpit, not diagnostics.
- Native desktop should add a compact recording trust layer: source, timer,
  meters, Stop, local queue/sync truth, and menu-bar state.
- The desktop center can host server-owned product UI, but capture-critical
  controls remain native.
- Technical labels such as native/server route/network details do not belong in
  the first viewport; they belong in diagnostics or recovery.

## Fresh Web Meeting Notes Observation

The Krisp web cabinet meeting notes route is a dense meeting workspace:

- Left nav is persistent and mirrors the desktop IA.
- Trial/account banner is prominent but does not replace the meeting workspace.
- Upcoming meetings appear above historical meeting notes.
- Meeting rows include title, duration, date, access/status icons, and source
  indicators.
- Search/filter/sort/new controls sit near the meeting list; they are not
  separate top-level products.
- A contextual ask/search prompt is available at the bottom of the workspace.

Clean-room implications for `2brain Rec`:

- `Встречи` should be the default web and embedded desktop surface.
- Search, filters, upload, and processing must be integrated into the meeting
  cockpit.
- Date/time, duration, source/provenance, participants/access, status, and next
  action should be visible in meeting rows.
- Upload should create or update a meeting row immediately, then progress
  through upload/extract/transcribe/transcript-ready/notes-ready states.

## Fresh Web Settings Observation

The Krisp settings route opens a list-detail settings console. V11 confirmed
the account settings capture through Zen window-specific capture:

- Left settings nav is grouped by account, workspace, meeting assistant, and
  app/system behavior.
- Account settings include profile, email/security, 2FA, support access, and
  account deletion.
- Workspace settings include admin settings, users, integrations, and billing.
- Meeting assistant settings are separated from app behavior/system settings.

Clean-room implications for `2brain Rec`:

- Settings must be a real console, not a small card.
- MVP settings groups should include account/workspace, appearance/theme,
  recording behavior, meeting detection policy, upload/storage/local queue,
  access/deletion truth, diagnostics, and browser-only admin handoff.
- Destructive actions such as delete/account removal need browser-owned
  governance and truthful scope copy.

## V7.4 Fit Check

V7.4 aligns with these observed patterns:

- Default surface is the meeting cockpit.
- Upload/search/filter/processing are inside the cockpit.
- Active recording is shell/menu-bar/header state, not a destination.
- Desktop keeps native capture trust controls while web owns variable product
  content.
- Settings are list-detail and cover the launch-critical policy areas.
- Review includes transcript, speaker assignment, governance, and light-theme
  proof.

## Open Follow-Up

Do not claim direct `computer-use` click-through coverage of `app.krisp.ai` in
Zen until a permitted browser/tool path is available. The locally installed
Krisp desktop app is now usable for live clean-room IA inspection, but the web
browser route remains bounded by the Computer Use URL policy.
