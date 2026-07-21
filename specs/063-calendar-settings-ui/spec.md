# Feature Specification: Calendar Settings UI

**Feature Branch**: `codex/063-calendar-settings-ui`

**Created**: 2026-06-27

**Status**: Implemented locally; moderated usability and rollout evidence remain open

**Input**: User description: "Feature 063: Настройки календарных интеграций и UI подключения. Feature 060 already added the backend calendar layer: read-only source connection, provider presets, selected calendars, sync, upcoming events, and recording-to-calendar-event context. Feature 063 must specify the user-facing layer: where settings live, how a user connects a calendar, chooses calendars, sees sync state, and controls reminder/recording prompt behavior. Study the project code, better settings practices, and external references; make the specification maximally detailed."

## Scope Summary

Feature 063 adds the complete user-facing calendar settings surface for 2brain Rec. The user must be able to find calendar settings, understand supported providers in plain Russian, connect a calendar through the provider's available method, choose which calendars are used for future meetings, see connection and sync health, run manual sync, disconnect a source, and understand exactly what 2brain Rec does with calendar data.

The primary navigation is:

```text
Настройки -> Интеграции -> Календари
```

The first screen is a working settings screen, not a landing or marketing page. It appears in the web cabinet and in the embedded cabinet inside the macOS app. The settings experience must preserve the existing product split: calendar integration management belongs to the server-owned cabinet, while active recording truth and one-action Stop remain visible in the native macOS shell.

Feature 063 is a settings and control layer over the calendar foundation from feature 060. It does not add calendar write behavior, bot join behavior, summary delivery, attendee-based sharing, or retrospective matching. Actual automatic recording is not part of 063. The UI may explain or reserve a future "do not ask again and record automatically" preference only as a disabled, policy-blocked, or separate-feature state. Enabling real auto-record behavior requires a separate high-risk feature because it changes recording start behavior, consent, visibility, audit, and one-action Stop guarantees.

## Clarifications

### Session 2026-06-27

- Q: When selected calendars contain overlapping events, which event should 2brain Rec use for join/recording context? → A: Show overlapping events as a conflict group during the time interval where events overlap; the user chooses the event for calendar context, and an active recording must not switch context automatically.
- Q: Which calendars should be selected by default after a source is connected? → A: No calendars are selected by default; the user must explicitly choose calendars in the calendar selection interface before the source contributes events to upcoming meetings or prompts.
- Q: What should count as the same meeting when selected calendars contain overlapping events? → A: Events are treated as duplicates only when they share a stable provider event ID or the same meeting link; otherwise overlapping events are shown as a conflict group.
- Q: Which event categories should be included by default after calendars are selected? → A: By default, include timed events with participants or a meeting link/location; exclude all-day events and private/free-busy prompts until the user opts in.
- Q: When should calendar sync be shown as stale and where should the user see it? → A: Show a source as stale when the last successful sync is older than 24 hours or the latest sync attempt failed; show the stale state on the connected source row/card, in sync details, and in the upcoming preview when stale data affects preview confidence.

## Current Product Findings

- The current cabinet already has a Russian, server-owned web shell with a disabled `Настройки` navigation item. Feature 063 should turn the calendar settings path into a real settings flow instead of inventing a separate product surface.
- The cabinet already has reusable product primitives for buttons, icon buttons, links, inputs, selects, checkboxes, chips, status labels, banners, empty states, unavailable states, dialogs, and sidebar navigation. The spec should require familiar settings controls and state vocabulary, not a bespoke marketing-style page.
- The macOS app already separates embedded cabinet content from native recording state. When an active recording exists, a native recording strip is visible above the embedded cabinet. Calendar settings must not obscure or replace that strip.
- The macOS shell currently routes only `Мои встречи` as a real embedded destination; other sidebar items show a "later" placeholder. Feature 063 should make `Настройки` actionable enough to reach calendar settings from the app, while keeping native capture controls outside the WebView.
- Feature 060 already provides calendar provider presets, connected sources, selected calendars, sync states, upcoming event summaries, safe title states, safe roster counts, disconnect behavior, and desktop prompts. Feature 063 should expose these capabilities to users with safe Russian wording.
- Feature 060 explicitly fixed the product boundary: future-only calendar context, no retrospective matching, no auto-record, no bot auto-join, no calendar mutation, no message sending, and no attendee-based access grants.

## Reference Findings

Clean-room reference review produced these product decisions:

- Krisp's calendar settings pattern is useful as a category baseline: settings sidebar, connected calendar summary, disconnect action, upcoming-meeting filters, and simple calendar display preferences. 2brain Rec must not copy Krisp branding, assets, visual expression, or text; the useful reference is the expectation that calendar settings are a calm working screen.
- Reclaim's connected-calendar model reinforces that a calendar settings page should show connected accounts and let the user choose which calendars are considered active for the product.
- Fireflies, Fathom, and Otter use connected calendars to drive auto-join, auto-record, summaries, and sharing. For 2brain Rec 063, this is an anti-reference: the settings screen must make clear that these actions are not enabled here.
- Integration management references such as Zapier, Demandbase, Merge, and ScalePad reinforce that sync health should be visible near the connection, include last successful or last attempted sync context, distinguish active/error/expired states, and offer test/reconnect or manual sync actions without forcing users to read logs.
- WCAG and WAI-ARIA guidance reinforces that settings must be keyboard reachable, have visible focus, expose labels/instructions, announce status/progress changes, and use binary controls only where the user is actually choosing one of two values.

References consulted:

- Reclaim connected-calendar settings: https://help.reclaim.ai/en/articles/6516465-how-to-select-and-manage-connected-calendars
- Reclaim all-day event sync preferences: https://help.reclaim.ai/en/articles/6326844-creating-and-customizing-your-calendar-sync-policies
- Fireflies calendar support and auto-join settings: https://guide.fireflies.ai/articles/4246295295-what-calendars-are-supported and https://guide.fireflies.ai/articles/3978936124-how-to-set-fireflies-to-join-only-meetings-you-want
- Otter Notetaker calendar auto-join and auto-share settings: https://help.otter.ai/hc/en-us/articles/13674910923671-Automatically-add-Otter-Notetaker-to-your-meetings and https://help.otter.ai/hc/en-us/articles/20424842990999-Manage-auto-share-settings
- Integration sync status patterns: https://help.zapier.com/hc/en-us/articles/8496290788109-Manage-your-app-connections, https://support.demandbase.com/hc/en-us/articles/360057789911-Understanding-Data-Sync-Status, https://docs.merge.dev/merge-unified/accounting/data-management/sync-status/list, and https://help.lifecyclemanager.com/hc/en-us/articles/17226844316571-Adjusting-your-IT-Glue-sync-settings
- WCAG 2.2 quick reference and WAI-ARIA switch pattern: https://www.w3.org/WAI/WCAG22/quickref/ and https://www.w3.org/WAI/ARIA/apg/patterns/switch/

## Information Architecture

### Cabinet Navigation

The calendar settings path is part of the main user cabinet, not admin-only by default.

- Top-level destination: `Настройки`.
- Settings category: `Интеграции`.
- Settings page: `Календари`.
- Breadcrumb or equivalent location cue: `Настройки / Интеграции / Календари`.
- Page title: `Календари`.
- Page subtitle meaning: "Подключите календарь, выберите нужные календари и настройте подсказки перед встречами."

### Page Content Order

The first screen must prioritize action and trust:

1. **Read-only boundary block**: concise Russian explanation of what 2brain Rec reads and what it never does in 063.
2. **Connected sources**: source cards or rows with current state, selected calendar count, sync health, and actions.
3. **Add calendar source**: provider list and connection method entry point.
4. **Calendar selection**: per-source list of selectable calendars after a source is connected.
5. **Upcoming and prompt behavior**: controls for which event categories appear and when prompts are shown.
6. **Sync details**: last successful sync, stale/error states, manual sync action, and safe troubleshooting. Stale state is visible on the source row/card first and repeated in preview only when stale data affects preview confidence.
7. **Disconnect zone**: explicit confirmation for removing a source.

The page must not hide useful controls behind a generic "coming soon" block once feature 063 is active.

### Embedded macOS Cabinet

The same settings hierarchy must work inside the macOS embedded cabinet:

- The native active-recording indicator and one-action Stop remain outside the embedded cabinet and visible when recording is active.
- If the embedded cabinet loses network/auth, the settings surface shows a safe unavailable or sign-in-required state while native recording controls remain usable.
- Provider authorization may open an external provider-controlled step only when necessary, but returning to the embedded settings screen must be clear and recoverable.
- The embedded screen must not suggest that calendar connection is required to record manually.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find Calendar Settings (Priority: P1)

As a 2brain Rec user, I want to open calendar settings from the cabinet so that I can connect a calendar without guessing where integrations live.

**Why this priority**: The current cabinet exposes settings as disabled or placeholder-like. Discovery is the first blocker for every other calendar action.

**Independent Test**: Starting from the cabinet home or meetings list, a user reaches `Настройки -> Интеграции -> Календари` in the web cabinet and embedded macOS cabinet, and the page shows actionable calendar settings rather than a disabled placeholder.

**Acceptance Scenarios**:

1. **Given** a signed-in user can access the cabinet, **When** they open Settings, **Then** they can navigate to Integrations and Calendar settings with Russian labels, a clear active state, and a location cue.
2. **Given** the same user opens the embedded cabinet inside the macOS app, **When** they navigate to Calendar settings, **Then** the embedded view shows the same calendar settings content without hiding native Record/Stop controls.
3. **Given** the user has no connected calendars, **When** they open Calendar settings, **Then** the first screen explains the read-only purpose and offers provider connection choices instead of showing an empty disabled page.
4. **Given** a user is not allowed to manage calendar connections because of workspace policy, **When** they open Calendar settings, **Then** the page explains the policy constraint and still shows read-only status where permitted.
5. **Given** the user opens Calendar settings while a recording is active, **When** the settings page loads, **Then** recording state remains visible locally and the settings page does not imply recording has stopped or changed.

---

### User Story 2 - Understand The Calendar Data Boundary (Priority: P1)

As a privacy-conscious user, I want the settings screen to explain calendar access in plain Russian so that I know what I am granting and what 2brain Rec will not do.

**Why this priority**: Calendar events contain meeting titles, links, participants, passcodes, locations, and private agenda text. Users must understand the read-only boundary before connecting.

**Independent Test**: Show the settings page to users before connection and verify they can correctly answer what 2brain Rec reads, what it stores, and what actions are out of scope.

**Acceptance Scenarios**:

1. **Given** the user has not connected a calendar, **When** they read the boundary block, **Then** they understand that 2brain Rec reads selected future calendar events to show upcoming meetings and prepare recording context.
2. **Given** the user reads the "not done by 063" explanation, **When** they are asked about side effects, **Then** they understand that 2brain Rec does not change calendar events, send messages, send summaries, invite attendees, or grant access to attendees.
3. **Given** the user is in the macOS app, **When** they read the credential explanation, **Then** they understand that provider credentials are server-owned and not stored in the desktop app.
4. **Given** a provider requires wider consent wording than the product feature uses, **When** the user returns from authorization, **Then** the settings page still explains the narrower 2brain Rec behavior and any provider limitation or admin review need.
5. **Given** a user wants automatic recording, **When** they inspect the settings screen, **Then** they see that real auto-record is not enabled in 063 and requires a separate approved feature.

---

### User Story 3 - Connect A Calendar Source (Priority: P1)

As a user, I want to connect my calendar with the method my provider supports so that 2brain Rec can show upcoming meetings and seed recording context.

**Why this priority**: Calendar settings deliver value only after a source is connected safely and understandably.

**Independent Test**: From Calendar settings, choose each supported provider family in a safe test environment and verify the user sees the correct connection method, read-only explanation, progress state, success state, and safe failure state.

**Acceptance Scenarios**:

1. **Given** the user opens the provider list, **When** provider choices are shown, **Then** the catalog covers Yandex Calendar, Mail.ru Calendar, Exchange / Exchange Server / EWS, Bitrix24, VK WorkSpace / custom CalDAV, Mailion / MyOffice, R7-Office, CommuniGate Pro, RuPost, Nextcloud / SOGo-like CalDAV, and Custom CalDAV, using the plain user-facing labels from the Provider Requirements table.
2. **Given** a provider requires an app password or mailbox credential, **When** the user enters the required information, **Then** the UI explains that the secret is submitted once, stored server-side, and never displayed again.
3. **Given** a provider requires a manual CalDAV URL, **When** the user enters the URL and account details, **Then** the UI validates that the source can be read and shows safe next steps if it cannot.
4. **Given** provider policy blocks the connection, **When** the flow ends, **Then** the user sees whether they can retry, reconnect, ask an admin, or choose another provider method.
5. **Given** connection succeeds but no calendars are readable, **When** the user returns to settings, **Then** the source does not look fully ready and the page explains that no calendars can be selected yet.
6. **Given** connection succeeds and readable calendars are found, **When** the user returns to settings, **Then** no calendars are selected by default and the source does not contribute future meetings or prompts until the user explicitly selects calendars.

---

### User Story 4 - Choose Calendars Inside A Source (Priority: P1)

As a user with one or more connected calendar sources, I want to choose exactly which calendars 2brain Rec uses so that only relevant future meetings appear.

**Why this priority**: A connected account often contains several calendars. Pulling every calendar by default can create noise and privacy risk.

**Independent Test**: Connect a source with multiple calendars, select and deselect calendars, save changes, and confirm upcoming events and prompts use only selected calendars while the source remains connected.

**Acceptance Scenarios**:

1. **Given** at least one calendar source is connected, **When** the user opens Calendar settings, **Then** each source shows provider name, safe account label, connection state, selected calendar count, last successful sync, and available actions.
2. **Given** a connected source contains multiple calendars, **When** the user opens its calendar list, **Then** they can select and deselect individual calendars with clear labels, color where safe, and state for private, shared, hidden, duplicate, or unavailable calendars.
3. **Given** no calendars are selected for a connected source, **When** the user views, saves, or leaves the screen, **Then** the UI warns that no future meetings will be pulled from that source until calendars are selected.
4. **Given** calendar selection changes, **When** settings are saved, **Then** future upcoming meetings and prompts reflect the new selection without retroactively linking past recordings.
5. **Given** two selected calendars contain the same event with the same stable provider event ID or the same meeting link, **When** the user sees upcoming meeting or prompt state, **Then** the UI treats the event as one meeting and avoids suggesting that duplicate selection creates duplicate recordings.
6. **Given** selected calendars contain different events with fully or partially overlapping time, **When** the overlapping interval is active and the event is used for join or recording context, **Then** the UI shows an overlap conflict group and asks the user to choose the intended event instead of silently picking one.
7. **Given** one event runs from 12:00 to 13:00 and another from 12:30 to 13:30, **When** the user is in 12:00-12:30 or 13:00-13:30, **Then** only the event active in that interval is treated as the current calendar context candidate.
8. **Given** one event runs from 12:00 to 13:00 and another from 12:30 to 13:30, **When** the user is in 12:30-13:00, **Then** both events are treated as an overlap conflict group.
9. **Given** a recording is already active with one calendar event context, **When** another selected event starts and overlaps the active recording, **Then** 2brain Rec must not automatically switch the recording context to the new event and may only offer an explicit user choice.
10. **Given** a calendar is shared or delegated, **When** the user sees it in the list, **Then** the UI shows that availability depends on provider permissions and private event policy.

---

### User Story 5 - Control Which Event Types Appear (Priority: P1)

As a user, I want to decide which kinds of calendar events should appear in upcoming meetings and prompts so that the app does not distract me with irrelevant events.

**Why this priority**: Calendar-driven products often become noisy when all-day events, placeholder holds, events without meeting links, or events without participants are treated like meetings.

**Independent Test**: Toggle event-category preferences and verify upcoming meeting previews and prompts include or exclude the selected categories without changing provider data.

**Acceptance Scenarios**:

1. **Given** event-category settings are available, **When** the user opens Calendar settings, **Then** they can control whether events without participants appear in upcoming meetings.
2. **Given** event-category settings are available, **When** the user opens Calendar settings, **Then** they can control whether events without a conference link or location appear in upcoming meetings.
3. **Given** event-category settings are available, **When** the user opens Calendar settings, **Then** they can control whether all-day events appear in upcoming meetings.
4. **Given** the user has not changed event-category defaults, **When** selected calendars contain future events, **Then** only timed events with participants or a meeting link/location are eligible by default, all-day events are excluded, and private/free-busy events do not trigger prompts by default.
5. **Given** a private/free-busy-only event matches selected categories after the user opts in, **When** it appears in preview or prompts, **Then** it uses safe minimum information instead of private title, attendee list, agenda, passcode, or link text.
6. **Given** a setting excludes an event category, **When** a recording is started manually during one of those events, **Then** manual recording remains possible and the UI does not imply that recording is blocked.

---

### User Story 6 - Understand Sync Health And Recover Safely (Priority: P1)

As a user, I want to see whether calendar sync is current, stale, broken, or waiting for my action so that I can fix connection problems without reading logs.

**Why this priority**: Calendar data loses trust quickly when users cannot tell whether it is fresh. Errors must be useful without leaking provider payloads or secrets.

**Independent Test**: Simulate connected, never-synced, syncing, synced, partial, stale, error, needs-action, disabled, disconnected, and provider-limited states and verify each state has clear Russian copy, safe details, and the right available action.

**Acceptance Scenarios**:

1. **Given** sync succeeds, **When** the user opens Calendar settings, **Then** they see the last successful sync time, selected calendar count, and a clear connected state.
2. **Given** a source has never synced, **When** the user opens Calendar settings, **Then** the UI explains that future meetings will appear after the first successful sync.
3. **Given** sync is running, **When** the user opens Calendar settings or starts manual sync, **Then** they see a non-blocking progress state that does not imply recording has started.
4. **Given** credentials are expired, revoked, missing, or require action, **When** sync cannot continue, **Then** the source shows a needs-action state with reconnect guidance and no raw provider error payload.
5. **Given** the provider returns a rate limit, timeout, service unavailable, or malformed calendar response, **When** sync fails, **Then** the user sees a safe Russian error category, last successful sync if available, and a retry or reconnect action where appropriate.
6. **Given** the last successful sync is older than 24 hours or the latest sync attempt failed, **When** the user opens Calendar settings, **Then** the source row/card shows a stale state, last successful sync time if available, and a manual sync or reconnect action.
7. **Given** manual sync is requested while another sync is running, **When** the user presses sync again, **Then** the UI says sync is already running instead of starting duplicate work.
8. **Given** a source is disabled or disconnected, **When** it is shown in settings history or feedback, **Then** the UI makes clear that it no longer contributes upcoming meetings.

---

### User Story 7 - Control Calendar-Driven Prompts (Priority: P1)

As a user, I want to control reminders and recording prompts based on calendar events so that 2brain Rec helps at the right moment without surprise recording.

**Why this priority**: Feature 060 introduced one-minute join prompts and at-start recording prompts. Users need understandable settings for those behaviors before the UI can feel trustworthy.

**Independent Test**: Toggle prompt settings and verify the settings screen explains what will happen before a meeting, at meeting start, in the menu bar or tray-style surface where available, and what remains manual.

**Acceptance Scenarios**:

1. **Given** reminder settings are available, **When** the user opens Calendar settings, **Then** they can control the one-minute-before-meeting prompt that offers to join or open the meeting.
2. **Given** recording prompt settings are available, **When** the user opens Calendar settings, **Then** they can control the at-start prompt that offers to start recording for the current event.
3. **Given** menu-bar or tray-style upcoming display is available, **When** the user opens Calendar settings, **Then** they can control whether upcoming event time and title are shown locally, with a safe title policy for private events.
4. **Given** the user disables a prompt, **When** the event time arrives, **Then** 2brain Rec does not show that prompt but manual recording remains available.
5. **Given** manual recording is allowed, **When** any calendar prompt setting changes, **Then** the UI states that manual start/stop remains available and active recording is always visible locally.
6. **Given** the product shows "do not ask again and record automatically" as a future or blocked option, **When** the user views it, **Then** the UI states that actual automatic recording is not enabled in 063 and requires separate approval/policy.
7. **Given** more than one selected calendar event overlaps the current time, **When** a join or recording prompt would use calendar context, **Then** the prompt shows the overlapping choices and lets the user choose one event or continue without calendar context.
8. **Given** a recording is already active and another selected calendar event starts during that recording, **When** 2brain Rec detects the overlap, **Then** it keeps the existing recording context unless the user explicitly changes it.
9. **Given** workspace policy limits prompts or recording, **When** the user views settings, **Then** constrained controls explain the controlling policy and do not look like errors.

---

### User Story 8 - Preview Upcoming Calendar Behavior Safely (Priority: P2)

As a user, I want a safe preview of what 2brain Rec will use from my calendar so that I can adjust settings before a real meeting starts.

**Why this priority**: A preview turns abstract settings into understandable behavior and helps users catch noisy calendars, missing links, and private-event limits before they matter.

**Independent Test**: With connected calendars and synthetic upcoming events, verify the settings page can show a safe upcoming preview that reflects selected calendars, event-category preferences, privacy policy, and prompt settings.

**Acceptance Scenarios**:

1. **Given** selected calendars contain upcoming events, **When** the user views the preview, **Then** they see safe event time, title state, meeting-link presence, provider/source, and whether join/record prompts would be eligible.
2. **Given** an event is private or free/busy-only, **When** it appears in preview, **Then** the preview shows only safe minimum information and a reason the title/details are hidden.
3. **Given** no upcoming events match the current settings, **When** the preview is shown, **Then** the empty state explains whether the cause is no selected calendars, no matching future events, sync not yet complete, or filters excluding all events.
4. **Given** the preview depends on a source whose last successful sync is older than 24 hours or whose latest sync failed, **When** the user opens settings, **Then** the preview shows stale state and does not claim it is current.
5. **Given** a provider limits event details, **When** the preview renders, **Then** the UI communicates the limitation without treating it as a product failure.

---

### User Story 9 - Disconnect A Calendar Source (Priority: P2)

As a user, I want to disconnect a calendar source with confirmation so that I can stop future sync and remove provider access intentionally.

**Why this priority**: Disconnect is required for user control and privacy. It must be clear what stops and what remains under meeting retention.

**Independent Test**: Disconnect a connected source, confirm the Russian dialog, and verify the source stops contributing future meetings while the UI explains the retention boundary for already matched meeting context.

**Acceptance Scenarios**:

1. **Given** a connected source exists, **When** the user chooses disconnect, **Then** the confirmation explains that future sync stops and provider credentials are removed or revoked where 2brain Rec controls them.
2. **Given** the user confirms disconnect, **When** disconnect completes, **Then** the source shows disconnected feedback and upcoming meetings from that source are no longer used.
3. **Given** a recording was already linked to a calendar event, **When** the source is disconnected, **Then** the UI does not promise retroactive erasure outside 2brain Rec control and explains that existing meeting context follows meeting retention/deletion policy.
4. **Given** disconnect fails or partially completes, **When** feedback is shown, **Then** the user sees a safe recoverable status without exposed secrets, tokens, or raw provider payloads.
5. **Given** sync is running when disconnect starts, **When** disconnect is confirmed, **Then** the UI shows that disconnect takes priority and the source should not continue contributing new future events.

---

### User Story 10 - Use Safe Empty, Loading, Error, And Accessibility States (Priority: P2)

As a keyboard or assistive-technology user, I want calendar settings to be readable and operable in every state so that I can manage integrations without hidden or mouse-only controls.

**Why this priority**: Calendar settings include credentials, privacy, destructive disconnect, and prompt controls. Accessibility and safe states are part of trust, not polish.

**Independent Test**: Navigate the full settings flow with keyboard and screen reader semantics across empty, loading, connected, needs-action, stale, error, and disconnected states.

**Acceptance Scenarios**:

1. **Given** the page is loading provider or source state, **When** a user navigates with keyboard or screen reader, **Then** progress is announced and controls are not falsely actionable.
2. **Given** an error or empty state is shown, **When** the user reaches it, **Then** the state has a useful heading, Russian explanation, and next action.
3. **Given** focus moves through provider choices, source actions, calendar selection, sync controls, prompt settings, upcoming preview, and disconnect confirmation, **When** keyboard navigation is used, **Then** focus order is logical and focus is visible.
4. **Given** a setting is binary and immediate, **When** it is presented visually as on/off, **Then** assistive technology receives a matching binary control state.
5. **Given** a user must select several calendars, **When** the selection list is presented, **Then** each calendar can be toggled independently and a selected count is announced or visible.
6. **Given** a private/free-busy event limitation affects what can be shown, **When** the limitation is explained, **Then** the UI uses a safe minimum and avoids private title, attendee, meeting link, or agenda text.

### Edge Cases

- A provider is listed but temporarily unavailable, disabled by admin policy, or available only through manual CalDAV.
- App password authentication fails because two-factor policy, mailbox policy, tenant policy, or provider app-password settings block it.
- A manual CalDAV URL is malformed, redirects, points to a calendar the user cannot access, returns only free/busy data, or exposes multiple calendars under one account.
- A connected source has zero calendars, many calendars, duplicate calendars, hidden calendars, shared calendars, delegated calendars, or calendars with identical display names.
- A source connects successfully and readable calendars exist, but the user has not selected any calendars yet.
- A selected calendar is later removed, renamed, made private, moved to another owner, or no longer readable.
- Sync is stale because the provider is down, rate-limited, unreachable, returning malformed events, or credentials expired.
- The last successful sync is older than 24 hours even though no new provider error is available.
- Some selected sources are current while others are stale; the UI must show source-level health and avoid claiming the whole preview is fully current when stale sources affect it.
- Manual sync is requested while another sync is already running.
- A user disconnects a source while sync is running.
- A user connects both personal and work calendars with fully or partially overlapping events; events with the same stable provider event ID or same meeting link are treated as duplicates, while other overlapping events must be shown as a conflict group only during the overlapping interval.
- Two events have similar titles, the same organizer name, or close start times, but different meeting links and no shared stable event ID; they must not be silently merged.
- A selected event starts while a recording is already active for another event; the active recording context must not change without explicit user choice.
- All calendars are deselected after a source was previously connected.
- Selected event-category preferences exclude every upcoming event.
- Default event-category preferences exclude all-day events and private/free-busy prompt candidates, even when the source and calendars are connected.
- The embedded macOS cabinet loses network/auth while native recording controls must remain available.
- Calendar settings are opened while a recording is active.
- A provider returns a calendar label or event title that includes a URL, email address, passcode, token-looking string, or private customer/project name.
- Private/free-busy events, attendee lists, meeting URLs, passcodes, agenda text, attachments, signed links, and provider raw payloads must not leak into settings, errors, logs, screenshots, or evidence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product MUST provide a Calendar settings screen reachable through `Настройки -> Интеграции -> Календари` in the web cabinet.
- **FR-002**: The embedded macOS cabinet MUST expose the same Calendar settings flow without requiring a confusing external browser handoff for normal settings management.
- **FR-003**: The Calendar settings first screen MUST be a working settings screen with current connection state, provider choices, and next actions; it MUST NOT be a marketing or placeholder page.
- **FR-004**: All user-facing calendar settings copy, labels, errors, confirmations, and helper text MUST be in simple Russian.
- **FR-005**: The provider catalog MUST include Yandex Calendar, Mail.ru Calendar, Exchange / Exchange Server / EWS, Bitrix24, VK WorkSpace / custom CalDAV, Mailion / MyOffice, R7-Office, CommuniGate Pro, RuPost, Nextcloud / SOGo-like CalDAV, and Custom CalDAV; the UI MUST use the user-facing labels in the Provider Requirements table.
- **FR-006**: The provider list MUST describe each provider in plain user language and indicate the available connection method category: app password or account credential, manual CalDAV URL, or provider-specific limitation.
- **FR-007**: The connection flow MUST explain before submission that 2brain Rec uses read-only calendar access and does not change events, send emails, send summaries, invite participants, or create meeting access for attendees.
- **FR-008**: Calendar provider credentials MUST remain server-owned; the desktop app MUST NOT store provider credentials.
- **FR-009**: The UI MUST never display raw tokens, app passwords, refresh tokens, private event text, attendee email dumps, signed links, passcodes, raw provider payloads, or live secret paths.
- **FR-010**: Users MUST be able to see all connected calendar sources with provider name, safe account label, connection state, selected calendar count, last successful sync state, and available actions.
- **FR-048**: Safe account/source labels MUST use a user-provided nickname, provider display name, domain-only label, or masked account identifier; they MUST NOT show full email addresses, raw provider account IDs, raw calendar URLs, token-looking strings, passcodes, or signed/private links.
- **FR-049**: Provider names, calendar labels, and event titles that contain URLs, email addresses, passcode-like strings, token-looking strings, signed/private links, or private customer/project names MUST be redacted or replaced with a generic safe label before they appear in settings, errors, screenshots, diagnostics, logs, analytics, or committed evidence.
- **FR-011**: Connected source states MUST include not connected, connecting, connected, needs action, stale, error, disabled by policy, disconnecting, disconnected, and syncing.
- **FR-012**: Users MUST be able to choose which calendars inside a connected source are used for future meeting context and prompts.
- **FR-013**: Calendar selection UI MUST make clear when no calendars are selected and that no future meetings or prompts will be pulled from that source.
- **FR-042**: After a calendar source is connected, no calendars MUST be selected by default; the source MUST NOT contribute future meetings or prompts until the user explicitly selects at least one calendar.
- **FR-043**: The calendar selection interface MUST show each readable calendar, selected or unselected state, source, selected count, and a clear "connected but not used yet" state until at least one calendar is selected.
- **FR-014**: Users MUST be able to start manual sync for a connected source when policy and current sync state allow it.
- **FR-015**: Manual sync feedback MUST show accepted, already-running, or safe error feedback within 2 seconds under normal server conditions, then show progress, last successful sync, safe error category, and next action without blocking recording controls or waiting for provider sync completion.
- **FR-046**: A connected source MUST be shown as stale when its last successful sync is older than 24 hours or its latest sync attempt failed.
- **FR-047**: Stale sync state MUST be visible on the connected source row/card, in source sync details, and in the upcoming preview when stale source data affects preview confidence; each stale state MUST show last successful sync time if available and an appropriate manual sync, reconnect, or safe troubleshooting action.
- **FR-016**: Users MUST be able to disconnect a calendar source after explicit Russian confirmation.
- **FR-017**: Disconnect confirmation MUST explain that future sync stops and provider credentials are removed or revoked where 2brain Rec controls them.
- **FR-018**: Disconnect copy MUST not promise universal deletion outside 2brain Rec control; already matched meeting context follows meeting retention/deletion policy.
- **FR-019**: Calendar settings MUST support the one-minute-before-meeting prompt preference that offers to join or open a meeting link when available.
- **FR-020**: Calendar settings MUST support the at-start meeting prompt preference that offers to start recording with event context.
- **FR-021**: Calendar prompt settings MUST preserve manual start/stop availability and MUST state that active recording remains visible locally with one-action Stop.
- **FR-022**: 063 MUST NOT enable real automatic recording, hidden recording, bot auto-join, calendar mutation, invite updates, email/message sending, summary/transcript/report delivery, attendee-based share grants, or retrospective matching of past recordings.
- **FR-023**: If "do not ask again and record automatically" appears in the UI, it MUST be represented as not enabled in 063 and MUST direct the decision to a separate high-risk feature.
- **FR-024**: Private/free-busy event states shown in settings MUST use safe minimum information and MUST NOT expose private title, agenda, attendee emails, meeting links, passcodes, or attachment links.
- **FR-025**: Empty, loading, connected, needs-action, stale, sync-error, sync-in-progress, disconnected, and policy-constrained states MUST have clear Russian copy and an appropriate next action or explanation.
- **FR-026**: All interactive controls in Calendar settings MUST be keyboard reachable, have visible focus states, and expose screen-reader labels that describe the action and state.
- **FR-027**: Calendar settings MUST work while a recording is active without hiding, disabling, or visually competing with the native active-recording indicator and one-action Stop path.
- **FR-028**: Calendar settings MUST make clear that calendar attendees are context only and do not become summary recipients, transcript recipients, report recipients, share-grant holders, or meeting participants with automatic access.
- **FR-029**: Calendar settings MUST make clear that selected calendars affect future/upcoming meetings only and do not retrospectively link old recordings.
- **FR-030**: The settings UI MUST support safe confirmation and recovery for cancelled connection, failed connection, expired authorization, provider policy block, provider downtime, and partial disconnect.
- **FR-031**: Users MUST be able to control whether events without participants appear in upcoming meetings and prompt candidates.
- **FR-032**: Users MUST be able to control whether events without conference link or location appear in upcoming meetings and prompt candidates.
- **FR-033**: Users MUST be able to control whether all-day events appear in upcoming meetings and prompt candidates.
- **FR-045**: Default event-category preferences MUST include timed events with participants or a meeting link/location and MUST exclude all-day events and private/free-busy prompt candidates until the user opts in.
- **FR-034**: The settings page MUST provide a safe upcoming preview or equivalent feedback that reflects selected calendars, event-category preferences, sync state, and privacy rules.
- **FR-035**: The settings page MUST distinguish prompt settings from source sync settings so a user does not confuse "calendar connected" with "record automatically."
- **FR-036**: The settings page MUST distinguish connection errors, credential errors, provider policy blocks, provider downtime, no readable calendars, no selected calendars, no matching events, and stale sync.
- **FR-037**: Calendar settings MUST expose provider capability limitations in user language, including when attendees, recurrence, private events, conference links, update/delete freshness, or free/busy detail are unavailable or admin-policy dependent.
- **FR-038**: Calendar settings MUST support multiple connected sources; when different selected events fully or partially overlap, the UI MUST show an overlap conflict group during the overlapping interval and require user choice before assigning join or recording context, while true duplicate events MUST NOT create duplicate recording behavior.
- **FR-041**: If a recording already has calendar context and another selected event begins during that recording, 2brain Rec MUST NOT automatically switch the recording context; changing context requires an explicit user action.
- **FR-044**: Calendar settings MUST treat overlapping events as duplicates only when they share a stable provider event ID or the same meeting link; title similarity, organizer similarity, or close start times alone MUST NOT merge events.
- **FR-039**: Calendar settings MUST preserve user control when workspace policy overrides local preference: constrained controls remain readable, explain the policy source, and do not look like broken controls.
- **FR-040**: Calendar settings MUST not require calendar connection before manual recording, meeting review, upload, transcript review, deletion, or other non-calendar MVP workflows.

### Provider Requirements

The `Provider` column is the provider family/capability group. The `Required user-facing label` column is the exact plain-language label shown in the settings UI and contracts.

| Provider | Required user-facing label | Connection method category | Required user explanation |
|---|---|---|---|
| Yandex Calendar | `Яндекс Календарь` | App password or CalDAV-style account connection where available | Read-only calendar sync; provider settings may require app password or calendar sync permission. |
| Mail.ru Calendar | `Mail.ru Календарь` | App password or CalDAV-style account connection where available | Read-only calendar sync; availability depends on account sync settings. |
| Exchange / Exchange Server / EWS | `Exchange / Exchange Server` | Organization or mailbox connection | Read-only connection may require tenant/admin support and may expose only fields permitted by Exchange policy. |
| Bitrix24 | `Bitrix24` | Provider-specific authorization or account connection | Calendar details depend on portal policy and user rights. |
| VK WorkSpace / custom CalDAV | `VK WorkSpace / CalDAV` | Manual URL or provider preset | User may need a CalDAV URL from their workspace settings. |
| Mailion / MyOffice | `Mailion / МойОфис` | Manual URL or provider preset | Calendar link and visible details depend on organization settings. |
| R7-Office | `R7-Офис` | Manual URL or provider preset | Calendar link may be copied from portal settings; private details may be limited. |
| CommuniGate Pro | `CommuniGate Pro` | Manual URL or provider preset | Calendar access depends on server and mailbox permissions. |
| RuPost | `RuPost` | Manual URL or provider preset | Calendar sync may depend on organization configuration. |
| Nextcloud / SOGo-like CalDAV | `Nextcloud / SOGo CalDAV` | Manual URL or provider preset | User chooses the server URL and calendars to include. |
| Custom CalDAV | `Другой CalDAV` | Manual URL | User supplies server/calendar URL; 2brain Rec only promises best-effort read-only sync after validation. |

### User-Facing State Vocabulary

Connection states must be translated into plain Russian and recoverable actions:

- **Not connected**: no source is connected; offer provider choices.
- **Connecting**: connection or authorization is in progress; explain whether the user is waiting for provider authorization or validation.
- **Connected**: the source is connected and can contribute selected calendars.
- **Connected, selection needed**: the source is connected, readable calendars exist, but no calendars are selected yet and the source does not contribute upcoming events or prompts.
- **Needs action**: user must reconnect, enter a new app password, fix a URL, or ask an admin.
- **Stale**: last successful sync is older than 24 hours, or the latest sync attempt failed; show last successful sync time if available and a recovery action.
- **Error**: sync or connection failed; show safe category and next step.
- **Disabled by policy**: workspace policy blocks user control.
- **Disconnecting**: disconnect was requested and is completing.
- **Disconnected**: source no longer contributes future meetings.

Sync states must distinguish:

- never synced;
- queued;
- syncing;
- synced;
- partial sync;
- stale;
- provider unavailable;
- rate limited;
- credential failed;
- failed closed.

Prompt states must distinguish:

- prompt off;
- prompt on;
- prompt blocked by policy;
- prompt not available because no selected calendars or no eligible event;
- prompt shown;
- prompt needs event choice because multiple selected events overlap;
- prompt dismissed;
- prompt expired;
- prompt led to opening a meeting link;
- prompt led to manual recording start.

### Required Russian Copy Meaning

The exact final wording can be refined during design, but these meanings must be present:

- "2brain Rec читает выбранные будущие события календаря, чтобы показать встречи и предложить начать запись."
- "2brain Rec не меняет события календаря, не отправляет письма и не рассылает саммари."
- "Участники календаря не получают доступ к записи автоматически."
- "Данные для подключения хранятся на сервере 2brain Rec; приложение на Mac не хранит пароль календаря."
- "Названия аккаунтов, календарей и событий могут быть сокращены или скрыты, если в них есть email, ссылка, код доступа, токен или приватное название."
- "Ручная запись и кнопка Stop всегда остаются доступными, если запись разрешена политикой."
- "После подключения выберите календари, которые 2brain Rec будет использовать. Пока календарь не выбран, встречи из этого источника не подтягиваются."
- "По умолчанию 2brain Rec показывает только встречи по времени: с участниками, ссылкой или местом. События на весь день и private/free-busy не будут звать на запись, пока вы сами это не включите."
- "Синхронизация устарела: последний успешный sync был больше 24 часов назад или последняя попытка не прошла. Встречи могут быть неактуальны."
- "Эта настройка не включает автоматическую запись. Автозапись требует отдельного включения и отдельной проверки безопасности."
- "Прошлые записи не связываются с календарем задним числом."
- "Удалить источник календаря" confirmation must say that future sync stops and already linked meeting context follows 2brain Rec meeting retention/deletion rules.

### Key Entities *(include if feature involves data)*

- **Calendar Settings Surface**: The user-facing settings area for calendar integration discovery, connection, source management, calendar selection, sync state, prompt preferences, upcoming preview, and disconnect.
- **Provider Preset**: A user-facing provider choice with plain name, connection method category, read-only explanation, and provider limitation state.
- **Connection Method**: The user-visible way to connect a provider: app password/account credential, manual CalDAV URL, or provider-specific/admin-limited route.
- **Calendar Source**: A connected provider account or calendar address shown to the user with provider name, safe account label, connection state, selected calendar count, sync state, and actions. Safe labels are masked or generic when provider-provided identifiers contain email addresses, raw IDs, URLs, tokens, passcodes, signed links, or private names.
- **Selectable Calendar**: A calendar inside a connected source that the user can include or exclude from future meeting context and prompts. Calendar labels are shown only after the same safe-label redaction rules are applied.
- **Calendar Selection Interface**: The settings area where the user sees readable calendars inside a connected source, selects or deselects them, sees the selected count, and understands whether the source is active for upcoming events and prompts.
- **Event Category Preference**: A user setting for including or excluding event types such as events without participants, events without conference link/location, all-day events, and private/free-busy prompt candidates. Defaults favor timed meeting-like events and avoid all-day/private prompt noise until the user opts in.
- **Sync Status**: User-facing freshness and recovery state for a source, including connected, syncing, stale, needs action, error, disabled, and disconnected. Stale means the last successful sync is older than 24 hours or the latest sync attempt failed.
- **Prompt Preference**: User-controlled behavior for one-minute join/open prompts, at-start recording prompts, and local upcoming display where available, bounded by workspace policy and recording safety rules.
- **Upcoming Preview Item**: A safe representation of a future event showing time, provider/source, title state, meeting-link presence, privacy state, and prompt eligibility without exposing private content or unsafe title text.
- **Overlap Conflict Group**: A safe group of two or more selected future events that overlap fully or partially in time and require the user to choose the intended event before 2brain Rec assigns calendar context to a join or recording prompt. For partial overlaps, the conflict exists only during the shared time interval.
- **Duplicate Calendar Event**: A selected event that appears through more than one calendar but shares a stable provider event ID or the same meeting link, so it may be shown as one meeting with multiple sources rather than as an overlap conflict.
- **Safe Error Message**: A user-facing explanation that names the recoverable category and next action without exposing secrets, raw payloads, private event text, attendee dumps, signed links, or passcodes.

## Out Of Scope

- Sending summaries, transcripts, reports, email, chat messages, or notifications to calendar attendees.
- Creating share links, share grants, or meeting access from calendar attendees.
- Updating, creating, deleting, or mutating calendar events.
- Bot auto-join or provider-side meeting join automation.
- Real automatic recording, hidden recording, or "always record this calendar" behavior.
- Retrospective matching or relinking of old recordings to calendar events.
- Speaker mapping from calendar attendees.
- Full organization admin panel for calendar integrations beyond what is required for personal calendar connection and policy-constrained states.
- New provider backend behavior beyond the already established read-only calendar layer from feature 060.
- Importing contacts or using calendar attendees as an address book for messaging.
- Fetching calendar attachments or opening signed attachment links.
- Producing exact final visual design, technical navigation identifiers, storage design, or provider adapter design.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can navigate from the cabinet to Calendar settings in 30 seconds or less in both web cabinet and embedded macOS cabinet.
- **SC-002**: A user with valid provider access can connect a calendar source and select at least one calendar in 3 minutes or less during a guided usability test.
- **SC-003**: 90% of tested users can correctly answer that 2brain Rec reads calendar data but does not change events, send messages, auto-record, or grant attendee access after reading the settings screen.
- **SC-004**: 100% of supported provider presets listed in FR-005 appear in the settings provider list with a readable Russian label and connection method category.
- **SC-005**: A user can identify connected, needs-action, stale, error, disabled, disconnected, and syncing states without viewing logs.
- **SC-006**: A user can run manual sync, see progress, and identify the last successful sync or safe failure reason for a connected source.
- **SC-020**: In sync freshness tests, a source with last successful sync older than 24 hours or a failed latest sync attempt shows stale state on the source row/card, in sync details, and in the upcoming preview when that stale source affects preview confidence.
- **SC-007**: A user can select calendars and correctly predict whether a future event from a selected vs. unselected calendar can appear in upcoming meetings.
- **SC-017**: After a successful connection with readable calendars, users see zero calendars selected by default and can make the source active only by explicitly selecting calendars in the calendar selection interface.
- **SC-008**: A user can adjust event-category preferences for events without participants, events without conference link/location, and all-day events, then see the preview reflect the choice.
- **SC-019**: With default event-category settings, all-day events and private/free-busy prompt candidates do not produce prompts, while timed events with participants or a meeting link/location can appear as upcoming or prompt-eligible events.
- **SC-009**: A user can disconnect a calendar source and see confirmation that the source no longer contributes future meetings.
- **SC-010**: Calendar settings acceptance coverage includes empty, loading, connecting, connected, needs-action, stale, sync-error, sync-in-progress, partial-sync, disconnected, policy-constrained, no-readable-calendars, no-selected-calendars, and no-matching-events states.
- **SC-011**: Accessibility validation confirms provider selection, calendar selection, manual sync, prompt settings, upcoming preview, and disconnect can be completed with keyboard navigation and understandable screen-reader labels.
- **SC-012**: Privacy review finds zero exposed raw tokens, app passwords, private event text, attendee email dumps, signed links, passcodes, raw provider payloads, private meeting links, or live secret paths in visible settings states, errors, screenshots, diagnostics, and committed evidence.
- **SC-013**: No acceptance path in 063 sends messages, mutates calendars, creates access grants, auto-joins meetings, starts hidden recording, enables real auto-record, or retrospectively links old recordings.
- **SC-014**: At least 90% of tested users understand that disabling calendar prompts does not disable manual recording and that connecting a calendar is not required for manual recording.
- **SC-015**: The embedded macOS cabinet variant passes a state review proving active recording visibility and one-action Stop remain visible while Calendar settings are open.
- **SC-016**: In overlap tests with two different selected events at the same time, including partial overlaps such as 12:00-13:00 plus 12:30-13:30, the UI never silently chooses or switches a calendar event for join or recording context; it shows the conflict group during the overlapping interval and lets the user choose or continue without calendar context.
- **SC-018**: In duplicate tests, events with the same stable provider event ID or same meeting link are shown as one meeting with multiple sources, while overlapping events with only similar titles, organizers, or start times remain separate conflict choices.

## Assumptions

- Feature 060's read-only calendar backend layer exists and remains the source for connected sources, provider presets, selected calendars, sync state, upcoming events, reminders, and recording-to-event context.
- Feature 063 is a user-facing settings specification and leaves technical design choices to later planning.
- Calendar settings are primarily personal-user settings for calendar connection and prompt behavior, with policy-constrained states shown where workspace policy limits the user.
- Calendar credentials are server-owned and never stored in the desktop app.
- Provider capabilities and connection methods may vary by tenant, license, admin policy, region, and deployment; the UI must show limitations honestly instead of claiming unsupported behavior.
- Calendar event data is sensitive meeting-adjacent content and must follow the same evidence discipline as meeting data.
- The macOS app keeps native recording state and one-action Stop outside the embedded cabinet, so settings navigation cannot hide active capture truth.
- The reference products inform category expectations only; 2brain Rec must keep original UX, Russian wording, product boundaries, and visual identity.
