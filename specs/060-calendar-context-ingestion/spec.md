# Feature Specification: Calendar Context Ingestion

**Feature Branch**: `060-calendar-context-ingestion`

**Created**: 2026-06-26

**Status**: Implemented, merged, released, and deployed; external distribution remains separate

**Input**: User description: "Feature 060. First build calendar integration only: connect calendars, ingest as much event information as available, use it for meeting context, naming, participants, and future recipient candidates. Message sending, transcript/summary delivery, and report distribution will be a later layer. Research Russian providers, their APIs, and products that already integrate with calendar services."

## Clarifications

### Session 2026-06-26

- Q: What should happen to calendar data after a calendar source disconnects? → A: Keep matched meeting context under meeting retention/deletion policy; purge credentials and unmatched/future cache.
- Q: What sync direction and matching model should the first calendar layer use? → A: Future-only calendar context; no retrospective matching. Event context is selected at recording time, and the app prompts at event start.
- Q: Should "do not ask again, always record" be included in feature 060? → A: No. Feature 060 only prompts to start recording; auto-record belongs to a separate feature.
- Q: What future sync horizon should represent "the whole calendar" for feature 060? → A: Rolling 12 months ahead, no past events.
- Q: What reminders should calendar events trigger? → A: One minute before start, offer to join the meeting; at start time, offer to record. A later automatic-recording option may skip pre-start prompts, but active recording visibility and one-action Stop remain mandatory.

## Provider Research Summary

The first layer is calendar context ingestion, not messaging or auto-send. Provider research on 2026-06-26 found three practical integration families:

- **Generic CalDAV/iCalendar**: broadest coverage for Russian and self-hosted providers. Target presets include Yandex Calendar, Mail.ru Calendar, VK WorkSpace where a CalDAV endpoint is available, Mailion/MyOffice, R7-Office, CommuniGate Pro, RuPost, Nextcloud/SOGo-like deployments, and manually supplied CalDAV URLs.
- **Rich calendar APIs**: Exchange EWS and Bitrix24 expose richer event objects, attendee state, conferencing fields, and organization-specific context.
- **Conference/calendar companion products**: Fireflies, Fathom, Otter, MTS Link, Kontur.Talk, TrueConf, and similar products use calendar data to show upcoming meetings, detect meeting links, match scheduled meetings, and drive later join/send behavior. For 2brain Rec, only ingestion, recording-time context selection, naming, participant roster, and privacy-safe context are in this feature.

Message sending, summary delivery, transcript delivery, calendar invite mutation, bot auto-join, and auto-record start are explicitly deferred to later feature slices.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Connect Calendar Sources (Priority: P1)

As a workspace user, I want to connect my calendar source to 2brain Rec so that upcoming meetings and new recordings can use trusted schedule context.

**Why this priority**: Calendar connection is the foundation for useful meeting names, event-start prompts, participant rosters, and later controlled sharing. Without a trusted calendar source, 2brain Rec must keep using generic recording titles.

**Independent Test**: Connect one calendar source in a safe test workspace, sync selected calendars for a rolling 12-month future horizon with no past events, and verify that 2brain Rec shows connection state, last sync state, provider family, and a metadata-safe list of synced events without starting recordings or sending messages.

**Acceptance Scenarios**:

1. **Given** a user has calendar access credentials or authorization, **When** they connect a supported calendar source, **Then** 2brain Rec stores a server-owned connection record, shows the provider family, and starts in read-only calendar ingestion mode.
2. **Given** the provider is CalDAV-compatible, **When** the user supplies provider preset credentials or a custom CalDAV URL, **Then** 2brain Rec discovers readable calendars and lets the user choose which calendars to ingest.
3. **Given** the provider is a rich API provider such as Exchange EWS or Bitrix24, **When** authorization succeeds, **Then** 2brain Rec records provider capabilities and syncs events through the provider's supported read path.
4. **Given** connection setup fails, expires, is revoked, or provider rate limits requests, **When** sync runs, **Then** the calendar source fails closed with a visible recoverable state and no recording, messaging, or hidden egress occurs.

---

### User Story 2 - Ingest Full Event Context Safely (Priority: P1)

As a meeting owner, I want 2brain Rec to capture all available calendar event context so that later meeting review can use the real event title, date, participants, and meeting metadata without asking me to re-enter them.

**Why this priority**: The user explicitly wants maximum calendar information captured first. This feature must preserve rich source context while treating calendar data as sensitive meeting data.

**Independent Test**: Sync fixture events covering simple, recurring, private, all-day, cancelled, conference-linked, room/resource, attachment-bearing, and attendee-heavy events. Verify that normalized event records preserve all available fields or safe provider-specific extras, and diagnostics contain only metadata.

**Acceptance Scenarios**:

1. **Given** a provider returns event identity, title, description, location, start/end, timezone, recurrence, status, organizer, creator, attendees, resources, conference links, categories, privacy, reminders, attachments, and provider version fields, **When** the event is ingested, **Then** 2brain Rec persists normalized fields plus a safe source snapshot for fields not yet modeled.
2. **Given** a provider omits fields or exposes only free/busy/private placeholders, **When** the event is ingested, **Then** 2brain Rec stores the limitation explicitly and does not fabricate title, attendees, organizer, or meeting links.
3. **Given** an event contains emails, meeting URLs, agenda text, private notes, attachments, or sensitive business context, **When** evidence, logs, diagnostics, or status pages are generated, **Then** those surfaces show only metadata-safe state unless an authorized meeting detail view is opened.
4. **Given** an event is deleted, cancelled, moved, or updated after initial sync, **When** the next sync runs, **Then** 2brain Rec preserves event history enough to explain recording-time context links and updates current future-event state.

---

### User Story 3 - Match Recordings To Calendar Events (Priority: P1)

As a user who records meetings, I want 2brain Rec to seed each new recording from the current or selected calendar event so that the recording title, participant list, and review context are correct from the start.

**Why this priority**: Calendar context only becomes useful when it can be attached to recordings without creating false matches. The first layer uses forward-looking event context at recording time instead of retroactively matching older recordings.

**Independent Test**: Record or simulate meetings that start during one, multiple, or no current/upcoming calendar events. Verify the selected event, confidence, title source, participant roster source, and fallback behavior.

**Acceptance Scenarios**:

1. **Given** recording starts from a current calendar prompt or a manually selected upcoming event, **When** recording begins, **Then** the recording is linked to that event with high confidence and the event title is used as the meeting title if policy allows descriptive names.
2. **Given** multiple current or upcoming events could seed the recording, **When** evidence is ambiguous, **Then** 2brain Rec stores candidate context, avoids destructive retitling, and asks the user to choose before claiming one event as canonical.
3. **Given** no current or selected future event is available when recording starts, **When** the recording is reviewed, **Then** the existing date/time fallback title remains and the missing calendar context is visible as `no_calendar_context`.
4. **Given** a user manually renames a meeting, **When** calendar sync later updates the event title, **Then** the user title remains primary and the calendar title is retained only as source context.

---

### User Story 4 - Build Calendar Participant Roster (Priority: P1)

As a meeting owner, I want participants from the calendar event to be available in the meeting review so that I can identify expected attendees and prepare later controlled sharing without typing email addresses manually.

**Why this priority**: Calendar attendees are useful for participant lists and later recipient candidates, but they are not proof of who spoke and they must not create automatic egress.

**Independent Test**: Sync events with organizer, required attendees, optional attendees, resources/rooms, groups, external guests, declined attendees, no-response attendees, and hidden/private attendees. Verify that roster classification is correct and no summary/transcript is sent.

**Acceptance Scenarios**:

1. **Given** a matched calendar event includes organizer and attendees, **When** the meeting review opens, **Then** 2brain Rec can show a calendar roster separated from transcript speaker labels and access/share policy.
2. **Given** an attendee has email, display name, role, response status, optional/resource classification, or group/resource marker, **When** the roster is stored, **Then** those fields are retained where available and source limitations are recorded where missing.
3. **Given** an attendee is external to the workspace or declined the meeting, **When** the roster is used, **Then** they remain candidate context only and do not gain meeting access, transcript access, summary access, or notification rights.
4. **Given** a calendar attendee name conflicts with diarized speaker labels, **When** review renders, **Then** 2brain Rec does not auto-assign speakers from calendar names without a later explicit speaker-mapping feature.

---

### User Story 5 - Keep Calendar Privacy, Retention, And Deletion Truth (Priority: P1)

As a security or workspace owner, I need calendar context to obey the same privacy, retention, deletion, and audit boundaries as meeting content so that calendar data does not become an unmanaged side channel.

**Why this priority**: Calendar events contain titles, agenda text, participant emails, meeting URLs, rooms, customer names, and attachments. This is sensitive meeting data and must not leak through logs, diagnostics, or future egress flows.

**Independent Test**: Exercise authorized, denied, expired, revoked, deleted, private-event, and provider-unavailable states. Verify that secrets and private calendar content are not present in logs, diagnostics, committed evidence, screenshots, or unauthorized responses.

**Acceptance Scenarios**:

1. **Given** a calendar source stores credentials, tokens, app passwords, or service-app secrets, **When** diagnostics, logs, status responses, or evidence are generated, **Then** no secret material or live credential path is exposed.
2. **Given** a meeting is deleted everywhere 2brain Rec controls, **When** deletion reporting runs, **Then** matched calendar context stored by 2brain Rec is deleted or retention-accounted, while external provider events are reported as outside 2brain Rec deletion control unless a later calendar-write feature exists.
3. **Given** a user disconnects a calendar source, **When** disconnect completes, **Then** future sync stops, credentials are revoked or purged where 2brain Rec controls them, unmatched and future-event cache is purged, and already matched meeting context remains under the matched meeting's retention/deletion policy.
4. **Given** a private/free-busy-only event is synced, **When** an unauthorized viewer or evidence report inspects it, **Then** only bounded availability and sync metadata are visible.

---

### User Story 6 - Provide Upcoming Meeting Context Without Starting Capture (Priority: P1)

As a user, I want 2brain Rec to show upcoming and current calendar meetings so that I can start or prepare recordings manually from the right context.

**Why this priority**: Products like Fireflies, Fathom, and Otter use calendars to surface upcoming meetings. For 2brain Rec, the safe first version is context, a one-minute join prompt, an event-start recording prompt, and visible user control, not bot auto-join or invisible capture.

**Independent Test**: Sync current and upcoming meetings with conference links and verify that the desktop surface can list the safe event title, time, provider, and status, show a join prompt one minute before start, show a recording prompt at start time, and avoid starting recording automatically in 060.

**Acceptance Scenarios**:

1. **Given** calendar sync has future meetings, **When** the user opens the calendar-aware Rec surface, **Then** current and upcoming meetings can be listed with provider, time, title policy state, and meeting-link presence.
2. **Given** the user selects an upcoming event, **When** they start a recording manually, **Then** the recording is seeded with the selected calendar event context and visible local Record/Stop control remains authoritative.
3. **Given** a synced event is one minute from its scheduled start time and has a meeting link, **When** the desktop app can notify the user, **Then** 2brain Rec can prompt the user to join or open the meeting without starting recording.
4. **Given** a synced event reaches its scheduled start time, **When** the user is active and recording is allowed by workspace policy, **Then** 2brain Rec can prompt the user to start recording with that event context.
5. **Given** an event contains a conference URL for Yandex Telemost, Kontur.Talk, TrueConf, MTS Link, VK Calls, Zoom, Webex, or another recognized target, **When** it is parsed, **Then** the URL is classified as meeting context only and does not cause bot auto-join or hidden capture behavior in this feature.

---

### User Story 7 - Prepare Future Recipient Candidates Without Sending (Priority: P2)

As the product owner, I want participant emails to be prepared for a later sharing layer so that the next feature can build summary/transcript/report delivery on top of safe calendar context.

**Why this priority**: The user wants message sending later. This feature must avoid sending while capturing the data and policy flags that later sending will need.

**Independent Test**: Sync meetings with internal, external, room/resource, group, hidden, duplicate, declined, and no-response participants. Verify that recipient candidate state exists but no message, email, webhook, calendar update, or share grant is created.

**Acceptance Scenarios**:

1. **Given** a matched event has attendee emails, **When** the roster is normalized, **Then** 2brain Rec can mark internal/external/resource/group/unknown candidate classes for future policy evaluation.
2. **Given** a participant email appears in the calendar, **When** this feature completes, **Then** no transcript, summary, report, invitation, share link, notification, or calendar update is sent.
3. **Given** a later sharing feature consumes the candidate list, **When** it needs to decide recipients, **Then** it can distinguish organizer, required attendee, optional attendee, declined attendee, external guest, room/resource, and manually removed candidate states.

### Edge Cases

- Calendar credentials are wrong, expired, revoked, rate-limited, locked by 2FA policy, or provider-side app passwords are disabled.
- Provider returns malformed iCalendar, invalid timezone, missing `DTEND`, all-day event dates, floating times, duplicate UIDs, or unsupported recurrence.
- Recurring event instance is moved, cancelled, edited independently, or has a different meeting URL from the series master.
- Two calendars contain the same future event through organizer and attendee copies.
- A user connects both personal and work calendars with overlapping events.
- A private event exposes only busy/free state and no title or attendees.
- A provider exposes attendee emails but not display names, or display names but not emails.
- An event has more than the expected attendee limit or contains distribution lists/groups.
- Event description contains multiple conference links, stale links, dial-in information, passcodes, tracking URLs, or sensitive agenda text.
- Provider returns attachments or file links that 2brain Rec cannot access or should not fetch.
- The event is cancelled after a recording was seeded from it.
- A user manually selects a calendar event, then a current-event prompt later points to a different candidate.
- Calendar source disconnects while recordings still reference matched event context.
- Calendar provider downtime happens during recording upload or review render.
- Workspace policy changes after events were synced, such as disabling descriptive titles or external-recipient candidates.
- Evidence screenshots accidentally include event titles, participant emails, meeting URLs, or agenda text.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support a calendar source connection model that records provider family, account owner, workspace scope, selected calendars, connection state, sync state, and safe error reason.
- **FR-002**: The system MUST ingest calendar events through a provider-neutral read-only layer before any later calendar-write, auto-join, auto-record, message-send, or summary-delivery layer is allowed.
- **FR-003**: The system MUST support generic CalDAV/iCalendar ingestion for provider presets and custom provider URLs, with first-class support targets for Yandex Calendar, Mail.ru Calendar, VK WorkSpace-compatible CalDAV, Mailion/MyOffice, R7-Office, CommuniGate Pro, RuPost, Nextcloud/SOGo-like deployments, and manually supplied CalDAV endpoints.
- **FR-004**: The system MUST support rich provider capability records for Exchange EWS and Bitrix24 so planning can use provider-specific event fields where available without weakening the provider-neutral model.
- **FR-005**: The system MUST store all available event identity fields required to reconcile updates, including provider, calendar identity, event identity, iCalendar UID, recurrence instance identity, provider version/etag/sequence where available, source updated time, and deletion/cancellation state.
- **FR-006**: The system MUST store all available schedule fields, including start, end, duration, timezone, all-day state, recurrence rules, recurrence exceptions, event status, transparency/free-busy state, and reminder metadata when available.
- **FR-007**: The system MUST store all available content/context fields, including title, description or agenda, location, conference/join metadata, categories, color/tags where available, attachments metadata, privacy/sensitivity, and provider-specific extras that are safe to retain.
- **FR-008**: The system MUST store all available human/resource fields, including organizer, creator, owner, required attendees, optional attendees, resources/rooms, groups/distribution lists where visible, response status, attendee role, display name, and email address where available.
- **FR-009**: The system MUST distinguish calendar roster participants from transcript speakers, meeting access grants, and message recipients.
- **FR-010**: The system MUST classify participant emails as candidate context only; they MUST NOT grant access, create share grants, send messages, or authorize summary/transcript/report egress in this feature.
- **FR-011**: The system MUST seed new recordings from current or explicitly selected future calendar events using explicit confidence states and source evidence such as selected event, event start time, conference URL, provider account, calendar owner, organizer, and target/service hints.
- **FR-012**: The system MUST use linked calendar event titles for meeting titles only when workspace policy allows descriptive names and recording-time context confidence is high enough; otherwise it MUST keep a safe fallback title.
- **FR-013**: The system MUST preserve user-renamed meeting titles over later calendar title changes while keeping calendar title as source context.
- **FR-014**: The system MUST expose calendar context in authorized meeting review and list surfaces without leaking private event content to denied, unauthenticated, deleted, private, or evidence-only contexts.
- **FR-015**: The system MUST record metadata-only audit events for calendar connect, disconnect, sync success, sync failure, event context link, event context unlink, manual context selection, and calendar-context deletion/retention decisions.
- **FR-016**: The system MUST treat calendar event context as meeting content for access control, retention, deletion accounting, backup expiry, diagnostics, forbidden-content scans, and evidence discipline.
- **FR-017**: The system MUST keep provider secrets, OAuth tokens, app passwords, service-app keys, refresh tokens, signed URLs, meeting passcodes, and live credential paths out of logs, diagnostics, API responses, screenshots, specs, plans, and committed evidence.
- **FR-018**: The system MUST support calendar source disconnect and credential purge/revocation accounting, purge unmatched and future-event cache on disconnect, and retain already matched meeting context only under the matched meeting's retention/deletion policy.
- **FR-019**: The system MUST provide provider capability and limitation state so users can tell whether a source supports attendees, recurrence, private events, conference links, updates/deletes, free/busy-only responses, and rich provider extras.
- **FR-020**: The system MUST recognize common conference URL families from calendar events as context, including Yandex Telemost, Kontur.Talk, TrueConf, MTS Link, VK Calls, Zoom, Webex, and provider-generic meeting links.
- **FR-021**: The system MUST fail closed when calendar sync cannot prove event freshness, event identity, or provider authorization; stale calendar data MUST NOT overwrite user titles, access policy, or meeting lifecycle state.
- **FR-022**: The system MUST ingest selected calendars on a rolling 12-month future horizon with no past events and without retrospective matching of past recordings; recurring expansion and event volume MUST be controlled so calendar sync cannot block recording upload, processing, playback, or review availability.
- **FR-023**: The system MUST provide a one-minute-before-start prompt to join or open a meeting link where available, and an at-start-time prompt to start recording with the event context, while preserving visible local Record/Stop control and workspace policy enforcement.
- **FR-024**: The system MUST include test fixtures or validation scenarios for Yandex/Mail.ru-style CalDAV, generic CalDAV, private/free-busy-only events, recurrence exceptions, attendee-heavy events, duplicate events, and Bitrix24-style rich event payloads.
- **FR-025**: The system MUST NOT send emails, messages, summaries, transcripts, reports, share links, calendar updates, meeting invitations, or bot join requests in this feature.
- **FR-026**: The system MUST NOT implement hidden capture, bot auto-join, provider-side meeting mutation, "do not ask again" automatic recording, always-record automation, or retrospective matching of past recordings in this feature; any later automatic-recording option MUST still keep active capture visible and provide one-action Stop.

### Key Entities *(include if feature involves data)*

- **Calendar Source**: A connected provider account or endpoint, including provider family, owner, workspace scope, selected calendars, credential state, sync state, capability state, and deletion/disconnect state.
- **Calendar Provider Capability**: The provider-specific support matrix for fields and behaviors such as attendees, recurrence, delta/update sync, private events, conference links, attachments metadata, free/busy, and rich extras.
- **External Calendar**: A specific calendar collection selected for ingestion, including provider calendar identity, display label, owner, color where available, visibility, and selected/unselected state.
- **Calendar Event Snapshot**: The normalized and source-preserving representation of one event or recurring instance, including identity, schedule, content/context, participant/resource roster, source version, privacy state, and provider extras.
- **Calendar Participant**: Organizer, creator, attendee, room, resource, or group entry attached to an event, including role, response status, optionality, email/display fields, workspace relation, and recipient-candidate classification.
- **Conference Link Candidate**: A meeting URL or dial-in field parsed from event location, description, conference metadata, or provider-specific fields, including provider family and sensitivity classification.
- **Recording Calendar Context Link**: The link between a 2brain Rec meeting and a current or explicitly selected future calendar event snapshot, including confidence, reasons, candidate list, manual override state, and title/roster source decisions.
- **Calendar Context Lifecycle Record**: Retention, deletion, disconnect, audit, and evidence state for calendar data stored under 2brain Rec control.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A test workspace can connect and sync at least one generic CalDAV calendar source and ingest selected calendars on a rolling 12-month future horizon with no past events, connection state, event count, sync time, and safe failure state visible.
- **SC-002**: Provider research and validation cover Yandex Calendar, Mail.ru Calendar, VK WorkSpace-compatible calendar surfaces, Mailion/MyOffice, R7-Office, CommuniGate Pro, RuPost, Nextcloud/SOGo-like CalDAV, Bitrix24/Exchange, and at least one generic CalDAV/custom URL source.
- **SC-003**: For fixture events containing all supported normalized fields, 100% of available identity, schedule, context, participant, recurrence, status, privacy, and provider-version fields are stored or explicitly marked as unavailable/unsupported.
- **SC-004**: For private/free-busy-only events, unauthorized contexts and evidence outputs expose 0 private titles, descriptions, attendee emails, meeting URLs, passcodes, attachment links, or agenda text.
- **SC-005**: Recording-time calendar context validation covers high-confidence selected event, ambiguous current events, no-context, manually selected future event, recurring-instance, cancelled-event, duplicate-calendar, and stale-sync cases with deterministic confidence and fallback outcomes.
- **SC-006**: Calendar participant roster validation proves that organizer, required attendee, optional attendee, external guest, room/resource, group, declined attendee, and no-response attendee states are preserved without granting access or sending any message.
- **SC-007**: Forbidden-content scans over committed docs, evidence, logs, and diagnostics for this feature find no provider secrets, tokens, app passwords, refresh tokens, meeting passcodes, raw private event text, attendee email dumps, signed URLs, or live credential paths.
- **SC-008**: Disconnect and deletion validation proves future sync stops, credentials are purged or revocation-accounted, unmatched and future-event cache is purged, and matched calendar context follows the matched meeting's retention/deletion policy.
- **SC-009**: Calendar sync and recording-time event context selection do not block upload, processing, playback, or meeting review availability; when calendar dependencies are unavailable, the meeting remains reviewable with `calendar_context_unavailable`.
- **SC-010**: No validation path in this feature sends an email, message, transcript, summary, report, share link, calendar invite, calendar update, auto-join request, hidden capture, "do not ask again" automatic recording, always-record automation, or retrospective past-recording match.
- **SC-011**: Reminder validation proves that a linked event can show a join/open prompt one minute before start and a record prompt at start time, and neither prompt starts recording automatically in 060.

## Assumptions

- Feature 060 is the first calendar layer: read-only calendar connection, future-event ingestion, normalization, recording-time context selection, naming, participant roster, provider capability reporting, one-minute join prompts, event-start recording prompts, and lifecycle accounting.
- Message sending, summary/transcript/report delivery, share grant creation from calendar attendees, calendar invite updates, bot auto-join, hidden capture, "do not ask again" automatic recording, always-record automation, and retrospective past-recording matching are separate later slices. A later automatic-recording option may skip pre-start prompts, but active capture visibility and one-action Stop remain mandatory.
- Existing user/session/device/workspace identity, meeting access, meeting review, retention/deletion, and upload/processing foundations remain the base.
- Calendar credentials and provider secrets are server-owned and never stored in the desktop client.
- Calendar event content is sensitive meeting-adjacent content and follows the same no-secret/no-private-content evidence discipline as recordings, transcripts, outcomes, and access/share data.
- CalDAV/iCalendar is the broadest first integration surface for Russian and self-hosted providers; rich provider adapters may add better field coverage without changing the normalized calendar event contract.
- Provider docs and capabilities may differ by SaaS/on-prem deployment, admin policy, license, app-password policy, and tenant settings; the feature must expose provider limitations instead of hiding them.
