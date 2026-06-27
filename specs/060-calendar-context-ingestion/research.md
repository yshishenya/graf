# Research: Calendar Context Ingestion

**Feature**: 060-calendar-context-ingestion

**Date**: 2026-06-26

**Purpose**: Record provider/API findings and reference-product patterns for the first calendar layer. This research supports calendar ingestion, normalization, recording-time context selection, naming, participant roster, and future recipient-candidate preparation. It does not authorize messaging, summary delivery, auto-join, auto-record, or calendar mutation.

## Decision Summary

- Build the first 060 layer around a **provider-neutral calendar event contract**.
- Use **CalDAV/iCalendar first** for Russian and self-hosted provider breadth.
- Add **rich capability adapters** where the provider exposes stronger event APIs: Google Calendar, Microsoft Graph/Exchange, and Bitrix24.
- Treat attendee emails as **calendar roster and future recipient candidates only**.
- Treat calendar event descriptions, URLs, passcodes, attachment links, and attendee emails as **sensitive meeting-adjacent content**.
- Sync selected calendars as a **rolling 12-month future horizon with no past-event ingestion**.
- Keep **message sending, share grants, report delivery, calendar invite updates, bot auto-join, and auto-record** out of scope.

See [provider-deep-dive.md](./provider-deep-dive.md) for the detailed
provider-by-provider plan, including Google Calendar, Microsoft Graph,
Exchange Server through EWS, Bitrix24, Yandex, Mail.ru, VK WorkSpace,
Mailion/MyOffice, R7-Office, CommuniGate Pro, RuPost, and conference-link
companion products.

## Phase 0 Planning Decisions

### Decision: Use a provider-neutral calendar domain layer

Rationale: The feature spans CalDAV/iCalendar, Google Calendar, Microsoft
Graph, Exchange EWS, and Bitrix24. A shared normalized event contract keeps
meeting naming, prompts, roster, retention, deletion, and audit behavior
consistent while letting adapters expose richer provider capabilities.

Alternatives considered:

- Provider-specific models per integration: rejected because meeting review,
  deletion, audit, and desktop prompt logic would duplicate provider rules.
- CalDAV-only model: rejected because Google, Microsoft, Exchange, and Bitrix24
  expose richer identity/version/conference/attendee fields that should be
  preserved when available.

### Decision: Server owns sync, credentials, and normalized event snapshots

Rationale: Calendar credentials are provider secrets and calendar events contain
sensitive meeting context. The desktop app should never store provider
app-passwords, OAuth refresh tokens, or EWS credentials. The server can apply
workspace access control, retention, deletion accounting, audit, and redaction
consistently.

Alternatives considered:

- Desktop-side direct provider sync: rejected because it would put provider
  secrets and sensitive event payloads in the client and complicate deletion
  accounting.
- Browser-only calendar integration: rejected because desktop prompts and
  recording-time context selection need local app coordination.

### Decision: Use sealed server-side credential envelopes for provider secrets

Rationale: Existing auth code stores session tokens as hashes and provider
client secrets as Docker secret files, but calendar sync needs reusable
per-source provider credentials. These must be encrypted/sealed at rest, exposed
only as state/fingerprint metadata, and purged on disconnect.

Alternatives considered:

- Plain DB storage: rejected because it violates secret discipline.
- Hash-only storage: rejected because provider sync needs reusable credentials.
- Desktop keychain storage: rejected for 060 because the server owns sync.

### Decision: Use existing HTTP stack and minimal provider adapters

Rationale: The backend already has `httpx`, FastAPI, Pydantic, SQLAlchemy, and
Alembic. Provider adapters should use those existing patterns, with stdlib XML
for CalDAV reports and bounded iCalendar extraction. Full calendar mutation,
provider-specific write APIs, and attachment fetching are out of scope.

Alternatives considered:

- Add a broad sync framework: rejected as too large for the first layer.
- Hand-build separate clients in API routes: rejected because provider logic
  needs tests, capability reporting, and redaction boundaries.

### Decision: Sync future context only

Rationale: Clarification established that 060 pulls selected calendars forward,
not backward. The sync horizon is rolling 12 months ahead with no past-event
ingestion, and event context is selected at recording time.

Alternatives considered:

- Retrospective matching of existing recordings: rejected by user
  clarification.
- Unlimited future sync: rejected because recurrence expansion and large
  calendars need a bounded operational envelope.

### Decision: Desktop prompts consume server upcoming context

Rationale: The server knows authorized calendar context, selected calendars,
privacy policy, and sync freshness; the desktop controls local recording and
notifications. Desktop should consume a small upcoming-context response, show a
join/open prompt one minute before start, and show a record prompt at event
start without auto-recording.

Alternatives considered:

- Server push notification service: rejected for 060 because it adds
  infrastructure and is unnecessary when the desktop app is running.
- Calendar provider reminders: rejected because 060 is read-only and must not
  mutate provider events.

## Provider/API Findings

### Yandex Calendar / Yandex 360

- Official Yandex docs describe desktop/mobile calendar sync through CalDAV and name `https://caldav.yandex.ru` as the server for sync clients.
- Yandex 360 business docs also describe service applications for organization-level integrations. That may support a future admin/service-app path, but it needs separate privacy/admin-consent research before broad workspace ingestion.
- 060 implication: P1 through CalDAV preset; later enterprise spike for service-app/admin-wide access.

Sources:

- https://yandex.com/support/yandex-360/customers/calendar/web/en/sync/sync-desktop
- https://yandex.com/support/yandex-360/customers/calendar/web/en/sync/sync-mobile
- https://yandex.ru/support/yandex-360/business/admin/ru/security-service-applications

### Mail.ru Calendar

- Official Mail.ru calendar help documents external app passwords for calendar synchronization.
- Public third-party CalDAV clients document `https://calendar.mail.ru` as the CalDAV base URL, but 2brain should rely on provider preset verification during implementation rather than hard-code from unofficial client docs alone.
- 060 implication: P1 through CalDAV preset and custom URL fallback.

Sources:

- https://help.mail.ru/calendar-help/synchronization/about/
- https://help.mail.ru/calendar-help/synchronization/calendar/
- https://www.davx5.com/tested-with/mailru

### VK WorkSpace / VK WorkMail

- Public official API documentation for a stable external calendar API was not found during this pass.
- Public materials and market articles confirm VK WorkSpace includes corporate mail with calendar/address book and has SaaS/on-prem variants.
- 060 implication: support as CalDAV-compatible only when the tenant exposes a usable CalDAV endpoint or administrator-provided URL. Do not claim a public VK calendar REST adapter until docs or vendor access confirm it.

Sources:

- https://habr.com/ru/companies/vk/articles/851128/
- https://www.tadviser.ru/index.php/%D0%A1%D1%82%D0%B0%D1%82%D1%8C%D1%8F%3A%D0%9B%D0%B0%D0%B1%D0%BE%D1%80%D0%B0%D1%82%D0%BE%D1%80%D0%B8%D1%8F_TAdviser%3A_%D0%94%D0%B5%D1%82%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B9_%D0%BE%D0%B1%D0%B7%D0%BE%D1%80_VK_WorkSpace_%E2%80%94_%D1%81%D1%83%D0%BF%D0%B5%D1%80%D0%B0%D0%BF%D0%BF%D0%B0_%D0%B4%D0%BB%D1%8F_%D1%81%D0%BE%D0%B2%D0%BC%D0%B5%D1%81%D1%82%D0%BD%D0%BE%D0%B9_%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D1%8B_%D0%BA%D0%BE%D0%BC%D0%B0%D0%BD%D0%B4_%D0%BB%D1%8E%D0%B1%D0%BE%D0%B3%D0%BE_%D0%BC%D0%B0%D1%81%D1%88%D1%82%D0%B0%D0%B1%D0%B0

### Bitrix24

- Bitrix24 has official REST calendar documentation.
- The calendar event overview states events contain date/time, location, and participants.
- Event methods include list, get by ID, upcoming events, update/delete, current user's participation status, and user availability.
- The `calendar.event.get` docs mention returned structures for meeting data, reminders, recurrence rules, relations, and attendee lists.
- 060 implication: rich P2/P1.5 adapter candidate because it can provide CRM/workspace context beyond generic CalDAV and is popular in Russian businesses.

Sources:

- https://apidocs.bitrix24.com/api-reference/calendar/index.html
- https://apidocs.bitrix24.com/api-reference/calendar/calendar-event/index.html
- https://apidocs.bitrix24.com/api-reference/calendar/calendar-event/calendar-event-get.html
- https://apidocs.bitrix24.com/api-reference/calendar/calendar-event/calendar-event-get-nearest.html
- https://apidocs.bitrix24.com/api-reference/calendar/calendar-event/calendar-event-get-by-id.html

### Mailion / MyOffice

- Mailion official support says users can copy a CalDAV calendar link and use Mailion calendars in third-party clients that support CalDAV.
- Release notes describe two-way transfer of events with external calendars connected through CalDAV and mention recurrence/attachments limitations.
- 060 implication: P2 through generic CalDAV and custom URL; do not fetch attachments, only attachment metadata if present and safe.

Sources:

- https://support.myoffice.ru/help/mailion/web/calender/actions_with_calendars/calendar_link_create/
- https://support.myoffice.ru/help/administration-squadus/desktop/topic/calendar/
- https://support.myoffice.ru/en/release/what-s-new-in-mailion-1-6/
- https://support.myoffice.ru/release/novye-vozmozhnosti-mailion-1-6/

### R7-Office

- R7-Office official support exposes API methods to get CalDAV and iCal links for calendars.
- R7 support also documents CalDAV server address usage in its Organizer setup.
- 060 implication: P2 provider preset/custom URL path, with possible future rich adapter if a customer needs R7 API-level calendar management.

Sources:

- https://support.r7-office.ru/community_server/api/settings-api/calendar-api/calendars_and_subscriptions/get-caldav-link/
- https://support.r7-office.ru/community_server/api/settings-api/calendar-api/calendars_and_subscriptions/get-ical-link/
- https://support.r7-office.ru/organizer/working-with-the-calendar-in-the-organizer/adding-a-calendar-from-the-portal-in-the-organizerdobavlenie-kalendarja-s-port/

### CommuniGate Pro

- Official CommuniGate docs say personal and group calendars are available through CalDAV and ActiveSync.
- The CalDAV module docs state users can access Calendar-type and Task-type mailboxes via CalDAV.
- 060 implication: P2 generic CalDAV for self-hosted enterprise deployments.

Sources:

- https://doc.communigatepro.ru/
- https://doc.communigatepro.ru/admin/access/
- https://doc.communigatepro.ru/russian/admin/access/WebDAV.html

### RuPost

- RuPost installation/configuration documentation lists calendars and tasks through CalDAV and contacts through CardDAV.
- Astra/RuPost knowledge base contains examples around CalDAV calendar synchronization.
- 060 implication: P2/P3 generic CalDAV for enterprise/on-prem deployments; validate tenant URLs and auth mode per customer.

Sources:

- https://astra.ru/local/ajax/download/docs/12/21557/
- https://wiki.astralinux.ru/kb/rupost-sinhronizatsiya-kalendarya-kontur-tolk-po-protokolu-caldav-326831820.html
- https://wiki.astralinux.ru/kb/rupost-216542210.html

### Google Calendar

- Google Calendar Events API exposes event resources; Google also offers a CalDAV interface.
- Event API supports richer event resource fields and conference data for Google Meet.
- 060 implication: rich adapter can provide better event metadata and sync behavior than generic CalDAV.

Sources:

- https://developers.google.com/workspace/calendar/api/v3/reference/events
- https://developers.google.com/workspace/calendar/api/guides/create-events
- https://developers.google.com/workspace/calendar/caldav/v2/guide

### Microsoft Graph / Exchange

- Microsoft Graph event resource represents events in user or Microsoft 365 group calendars and supports list/delta/update operations.
- Graph calendar APIs can read event collections in time ranges and include attendee/organizer/online meeting data depending on permissions and tenant policy.
- 060 implication: rich adapter for Microsoft 365/Exchange Online; on-prem Exchange may require a separate EWS/enterprise route if Graph is not available.

Sources:

- https://learn.microsoft.com/en-us/graph/api/resources/event?view=graph-rest-1.0
- https://learn.microsoft.com/en-us/graph/outlook-calendar-concept-overview
- https://learn.microsoft.com/en-us/graph/api/resources/calendar?view=graph-rest-1.0
- https://learn.microsoft.com/en-us/graph/api/resources/onlinemeeting?view=graph-rest-1.0

### Standards: iCalendar and CalDAV

- RFC 5545 defines iCalendar for events, to-dos, journal entries, and free/busy information independent of a particular calendar service.
- RFC 4791 defines CalDAV as WebDAV extensions for calendar access and notes that clients must handle server-side data changing between sync attempts.
- VEVENT examples include UID, organizer, attendee, start/end, status, summary, description, location, categories, privacy class, and recurrence.
- 060 implication: normalized event model should start from iCalendar fields and retain provider extras.

Sources:

- https://datatracker.ietf.org/doc/html/rfc5545
- https://datatracker.ietf.org/doc/html/rfc4791
- https://icalendar.org/iCalendar-RFC-5545/4-icalendar-object-examples.html
- https://icalendar.org/CalDAV-Access-RFC-4791/7-8-caldav-calendar-query-report.html

## Conference And Calendar Companion Products

### Fireflies

- Supports Google Calendar and Outlook Calendar.
- Detects upcoming meetings from the connected calendar and needs valid meeting links to join.
- Supports manual calendar invitation of its bot and auto-join preferences.
- 2brain takeaway: useful pattern is upcoming-meeting detection from calendar and meeting-link requirement; 060 should not implement bot join or auto-send.

Sources:

- https://guide.fireflies.ai/articles/4246295295-what-calendars-are-supported
- https://guide.fireflies.ai/articles/2596333792-upcoming-meetings-module-faqs
- https://guide.fireflies.ai/articles/9554534786-how-fireflies-joins-and-records-your-meetings-faqs

### Fathom

- Quick start asks users to connect Google or Microsoft calendar so Fathom can show upcoming meetings and automatically join meetings.
- Fathom docs note limits such as primary-calendar-only behavior and meeting link detection in calendar fields.
- 2brain takeaway: calendar-driven upcoming context is valuable, but 2brain should preserve local manual Record/Stop authority and avoid auto-join in 060.

Sources:

- https://help.fathom.video/en/articles/276608
- https://help.fathom.video/en/articles/5291969
- https://help.fathom.video/en/articles/449536
- https://help.fathom.video/en/articles/449216

### Otter

- Otter can connect Google and Microsoft calendars, plus device calendars on iOS.
- Connected calendar events populate the Home page; events with valid Zoom/Google Meet/Microsoft Teams URLs show notetaker controls.
- Otter supports recurring meeting management and calendar-linked notes.
- 2brain takeaway: recurring series settings and meeting-link detection matter, but sending notes back to calendar or auto-adding notetaker is later scope.

Sources:

- https://help.otter.ai/hc/en-us/articles/360048070154-Connect-your-Calendar-and-Contacts-to-Otter
- https://help.otter.ai/hc/en-us/articles/13676368852631-Manage-your-calendar-meeting-events
- https://help.otter.ai/hc/en-us/articles/25947061277975-Manage-recurring-meetings
- https://help.otter.ai/hc/en-us/articles/34963639460119-Add-Otter-meeting-notes-to-Google-calendar-events

### Russian conference/calendar companions

- MTS Link documents Yandex Calendar integration through CalDAV.
- Kontur.Talk documents integrations with calendars.
- TrueConf documents Calendar Connector integration for corporate calendars such as Microsoft Exchange, Thunderbird, R7-Office, and RuPost.
- 2brain takeaway: Russian conference tools often integrate through CalDAV or Exchange-style calendar bridges. For 060, parse their meeting links from calendar events as conference-link candidates only.

Sources:

- https://help.mts-link.ru/article/25655
- https://talk.kontur-f.ru/instructions/integraciya-s-kalendaryami/
- https://trueconf.ru/docs/server/ru/admin/calendar/

## Normalized Event Field Map

Identity:

- provider family
- provider account identity
- calendar identity
- provider event identity
- iCalendar UID
- recurring series identity
- recurring instance identity
- etag/version/sequence
- source created/updated/deleted/cancelled timestamps

Schedule:

- start
- end
- duration
- timezone
- all-day flag
- floating-time flag
- recurrence rule
- recurrence exceptions
- status
- transparency/free-busy state
- reminders/alarms metadata

Content/context:

- title/summary
- description/agenda
- location
- conference links and dial-in details
- provider conference metadata
- categories/color/tags
- attachments metadata only
- privacy/sensitivity/classification
- source URL when safe
- provider extras retained under lifecycle control

Participants:

- organizer
- creator
- owner
- required attendees
- optional attendees
- declined/no-response/accepted/tentative states
- resources/rooms
- groups/distribution lists
- display name
- email
- provider user id where available
- internal/external/resource/unknown classification

2brain-derived:

- recording-time context confidence
- context selection reasons
- selected/current-event/no-context state
- title source
- roster source
- conference provider family
- recipient candidate class
- privacy/evidence sensitivity class
- lifecycle/deletion state

## Product Decisions For 060

- Calendar event data is not harmless metadata; it can identify customers, agenda, attendees, rooms, and meeting links.
- Attendee emails are useful but dangerous. They become recipient candidates, not recipients.
- Event title is the best initial meeting title only when recording-time context confidence and workspace policy allow descriptive naming.
- Calendar roster is not diarization. It should not rename speakers without a later explicit speaker-mapping feature.
- CalDAV broad coverage beats a pile of bespoke adapters for the first slice.
- Bitrix24 is the first Russian rich-adapter candidate after generic CalDAV because it has official calendar REST APIs and business context.
- VK WorkSpace should not be represented as having a confirmed public external calendar API from this research pass; support it through CalDAV/custom endpoint until vendor docs prove a richer route.
- Calendar source disconnect must be explicit: stop future sync, purge/revoke credentials, purge unmatched/future cache, and keep matched meeting context only under the matched meeting's retention/deletion policy.
