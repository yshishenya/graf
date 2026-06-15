# Krisp Full Navigation And Interaction Audit

Date: 2026-06-11
Scope: clean-room category audit before redesigning `2brain Rec`.

This file records what was inspected and what product lessons are allowed. It
does not copy Krisp visuals, screenshots, icons, brand colors, proprietary copy,
private meeting content, payment details, or user account details.

## Audit Method

- Opened the Krisp web cabinet in the user's current Zen browser at the provided
  meeting-notes URL.
- Opened the locally installed Krisp desktop app.
- Clicked safe navigation, popovers, menus, filters, list controls, settings
  sections, share modal, meeting detail, AI drawer, language menu, tag menu, and
  desktop shell surfaces.
- Did not trigger account, billing, subscription, support, delete, share-send,
  invite-send, public-link-change, 2FA, email-change, calendar-disconnect, live
  audio toggles, playback, or recording actions.
- Inspected the installed `2brain Rec` app and clicked only safe readiness
  actions. Did not start recording.

## Krisp Web Cabinet Surfaces Covered

### Meeting List Home

Observed:

- Persistent left navigation with Search, My Meetings, Shared with me, Action
  Items, Activity, Contacts, Settings, app/developer links, plan/account area,
  and reactivation/trial actions.
- Trial-ended state blocks new meeting creation but keeps historical meetings
  accessible.
- Upcoming meetings and meeting notes coexist on the same home route.
- Meeting rows are dense and status-rich, with title, duration, date/status
  markers, source icons, and row actions.
- Bottom AI entry is scoped to meetings rather than a generic assistant.

Allowed lesson:

- The first useful surface is a library and status workspace, not a generic
  analytics dashboard.
- A product can show account/degraded state without blocking access to past
  value.
- 2brain desktop must show a real meeting library and current status in the
  first viewport. Diagnostics cannot be the home screen.

### Search

Observed:

- Search opens as a command/modal layer with an input, recent results, and a
  command-search affordance.
- It is secondary to the meeting list.

Allowed lesson:

- Search should be fast and contextual, but it should not replace the meeting
  library. For 2brain MVP, search is useful after there are recordings,
  transcripts, and statuses to search.

### List Filters And Sorting

Observed:

- "Later" is a one-click list filter that changes URL query state.
- Filter menu includes Star, Date, Contains, Company, Type, and Tags.
- Date filter becomes a chip with choices like today, yesterday, recent ranges,
  and custom.
- Contains filter supports transcript, audio recording, video recording, and
  notes.
- Sort menu supports date, duration, last modified, newest, and oldest.
- Empty filter chips can remain visible even without a selected value.

Allowed lesson:

- Web cabinet should support richer filters because it is the full review
  surface.
- Desktop should start with simpler saved views: All, Processing, Ready, Local
  only, Failed, plus search.
- 2brain should not show empty filter chips. Active filters appear only when
  they have a value.

### Upcoming Settings

Observed:

- Upcoming has a popover for what calendar events to show, including events
  without attendees, events without location/link, and all-day events.

Allowed lesson:

- Calendar relevance filters are settings/admin territory, not first-launch
  desktop controls.
- If 2brain later supports calendar, desktop should show only relevant upcoming
  items and move tuning to web/settings.

### Invite / Team Trial

Observed:

- The invite entry opens a team trial modal, not a simple invite email form.
- The modal combines teammate invite, admin controls, premium-feature trial,
  and trial-start CTA.

Allowed lesson:

- Team/admin/trial/billing flows are not part of the owner value loop for the
  first 2brain release.
- Desktop should not make team setup a first-viewport action. It can show
  workspace identity and open admin in browser.

### Account Menu

Observed:

- Account menu contains appearance, settings, resources, support, feedback,
  community, and sign out.
- Appearance and resources behave like submenu entries.

Allowed lesson:

- Desktop account menu should be shorter and safer: account, appearance,
  diagnostics/support bundle, open web cabinet, sign out.
- Avoid hover-only or fragile submenu behavior for critical account/settings
  paths. It should be keyboard reachable and predictable.

### Settings

Observed settings groups:

- Account: profile fields, email change, 2FA, support access, delete account.
- Workspace: admin settings, users, team integrations, billing.
- Meeting Assistant: AI note taker, privacy and consent, personalization,
  calendar, language, action items, vocabulary, integrations, tags.
- App behavior and system: app settings including links in desktop app and
  appearance.

Observed boundaries:

- Admin settings include workspace sharing defaults, feature toggles, recording
  and bot policy, participant notification, deletion duration, SSO, and session
  duration.
- Users page is a member table with invite and role/status filters.
- Billing includes plan, seats, subscription, payment, and coupon controls.
- Integrations page is a marketplace with many external systems.
- Calendar and language settings are useful but not part of recording start.

Allowed lesson:

- Web owns account, workspace, team, billing, integrations, admin policy,
  consent policy, retention, and deletion settings.
- Desktop can show a summarized policy and account/session state, but should
  hand off edits and risky actions to the browser.
- App appearance/basic behavior can exist in desktop, but admin/account
  mutation should not live inside the recording shell.

### Meeting Detail / Review

Observed:

- Meeting detail has a header with title/date, summarize action, integration
  actions, share, comments, and more menu.
- The active content is "Recording & Transcript".
- Transcript is timestamped, speaker-labeled, searchable/scannable, and tied
  to a bottom playback timeline.
- Language menu can correct transcript language and then regenerate.
- Transcript quality feedback is a compact rating popover.
- Tag menu is a small search/input popover with empty state.
- AI drawer opens on the right with prompt suggestions and context scope.
- AI scope can switch between this meeting and all meetings.
- Share modal has invite email, owner list, access level dropdown, and copy
  link.
- Share access levels include invite-only, workspace/team scopes, and anyone
  with link.
- More menu includes copy link, favorite, save later, find/replace, export
  transcript, download recording, delete meeting, and open in desktop app.

Allowed lesson:

- The core product value is the meeting review workspace: transcript, playback,
  summary/notes, actions, provenance, language, export/share/delete, and AI.
- 2brain MVP must not stop at "uploaded" or "transcribing". It must lead users
  to a complete review state when processing finishes.
- Share/download/delete are powerful actions and need browser-first policy,
  confirmations, and truth copy.
- AI must be scoped explicitly. "All meetings" is a broader privacy and
  retention boundary than "this meeting".
- Transcript language correction/regeneration is a real processing action and
  must not happen accidentally.

### Activity, Shared, Contacts, Action Items

Observed:

- Activity opens as a panel with unread filter and empty state.
- Shared with me and Contacts are separate library routes.
- Centralized Action Items can be plan-gated and is not required for basic
  meeting review.

Allowed lesson:

- First 2brain release should include action items inside the meeting review
  result, not a broad global action-items product.
- Activity and contacts can be later web surfaces. Desktop should focus on
  current recording, upload, processing, and review.

## Krisp Desktop Surfaces Covered

Observed:

- Desktop combines the web cabinet/list in the main window with a compact
  right-side native/audio rail.
- The right rail exposes live audio mode, accent/noise toggles, mic/speaker
  controls, limited mode, and collapse behavior.
- The main desktop content is not merely settings. It gives access to the same
  meeting library and account state as the web cabinet.

Allowed lesson:

- 2brain desktop should use the same category split: native capture controls
  are always local; meeting library and review can be server-rendered and
  embedded.
- The native area should be compact and always visible, but it should not take
  over the whole first viewport after onboarding.
- Live audio toggles are not the same product as meeting capture. 2brain should
  avoid copying Krisp's noise/accent rail and instead build a recording trust
  shell.

## Current 2brain Rec App Audit

Observed:

- Installed app: 2brain Rec macOS app, bundle `pro.2brain.rec`.
- First viewport is a SwiftUI diagnostics/readiness console.
- Visible sections: driver diagnostics, recording status, record system audio,
  recorder input meters, audio health, permissions, current devices, recording
  path, route diagnostics, browser targets, buffer, health checks, diagnostic
  log.
- Safe clicks performed:
  - Refresh audio device status.
  - Run audio readiness check.
- Both safe actions only update diagnostic last-event text.
- Recording was not started.
- No account, server session, upload queue list, manual media upload, meeting
  library, processing status, transcript, review surface, share/export/delete
  surface, or browser handoff appears in the app.

Allowed lesson:

- The current app is a good internal diagnostic surface but not launchable as
  the primary MVP product UI.
- Diagnostics must move to an advanced/recovery drawer or route.
- The first screen should show the owner value loop: Record, Upload media,
  current statuses, recent meetings, and open result.

## Current Repository Web Surface Audit

Observed:

- The repository has `apps/server` and `apps/macos`.
- No separate web frontend app exists in the current worktree.
- Server README states that the backend ingest foundation does not expose
  transcript download, summary download, audio download, public share links,
  login-required share pages, team browsing, privileged admin review, dashboard
  meeting detail, deletion execution, indexing, or assisted auto-recording.
- Current status says desktop upload queue, MediaScribe processing, dashboard
  review, access/sharing/downloads, and retention/deletion remain separate
  future product slices.
- Current worktree contains `014-desktop-upload-queue`, `028-provider-auth-session`,
  `029-email-auth-account-linking`, and `030-mvp-experience-design-system`.
  `015-mediascribe-processing-pipeline` is active in a separate worktree/branch,
  so this design must align with its status/transcript contracts without
  duplicating or editing that feature here.

Allowed lesson:

- The web cabinet is a design target and follow-up implementation slice, not
  a current UI to restyle.
- Feature 030 must create implementation-ready web cabinet specs and backlog
  candidates, not pretend the cabinet already exists.

## 2brain MVP Value Loop From Audit

The smallest complete value loop worth launching is:

1. User signs in or sees exact offline/local-only state.
2. User records in the macOS app or uploads owned media in desktop/browser.
3. User sees saved/uploading/processing/transcribing/ready status in both app
   and web.
4. User opens a meeting result and sees transcript plus playback/provenance.
5. User sees summary, decisions, action items, and failure/degraded truth when
   available.
6. User can retry, export/download when allowed, manage access in browser, and
   delete with truthful boundaries.

Any screen that does not support this loop is secondary or browser-only for MVP.

## Risky Actions Intentionally Not Clicked

- Upgrade, Reactivate, Start Team Trial, billing, payment, coupon, seat changes.
- Work email trial extension.
- Invite send, email entry, public-link permission changes.
- Change email, enable 2FA, support access, delete account.
- Calendar disconnect.
- Admin toggles, workspace sharing policy toggles, SSO/session policy changes.
- Live audio accent/noise/mic/speaker toggles in Krisp.
- Record System Audio in 2brain Rec.
- Playback of private meeting audio.
- Delete meeting, download recording, copy link, export transcript, open in
  desktop app, support/contact/feedback submissions.

These are product-relevant but require explicit confirmation because they can
change account state, transmit data, expose private content, or alter local
system/audio behavior.
