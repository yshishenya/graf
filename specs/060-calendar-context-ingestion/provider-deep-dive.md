# Provider Deep Dive: Calendar Context Ingestion

**Feature**: 060-calendar-context-ingestion

**Date**: 2026-06-26

**Scope**: Read-only calendar ingestion, event normalization, recording-time
calendar context selection, calendar participant roster, provider capabilities,
and future recipient candidate preparation.

**Explicitly out of scope**: email/message sending, summary/transcript/report
delivery, share grant creation from attendees, calendar invite mutation,
conference creation, bot auto-join, hidden capture, and automatic recording
start.

## Executive Summary

The safest first architecture is a provider-neutral calendar ingestion layer
with two adapter families:

- **Generic CalDAV/iCalendar adapter** for breadth across Russian, on-prem, and
  self-hosted providers.
- **Rich API adapters** for providers that expose better event objects and sync
  semantics: Google Calendar, Microsoft Graph, Exchange Server through EWS, and
  Bitrix24.

The first product layer should ingest and normalize all available context, but
must treat calendar data as sensitive meeting-adjacent content. Calendar
attendee emails are not recipients yet. They are only a roster and future
recipient candidates for a later, policy-gated sharing layer.
The 060 sync horizon is a rolling 12 months ahead from selected calendars, with
no past-event ingestion or retrospective matching of older recordings.

## Implementation Notes From Feature 060

- Implementation evidence uses synthetic provider fixtures, not live provider
  accounts. This keeps committed proof metadata-only and avoids storing real
  provider credentials, raw event payloads, passcodes, attendee dumps, or
  private meeting content.
- Generic CalDAV/iCalendar normalization covers Yandex, Mail.ru, custom
  Russian/on-prem provider presets, private/free-busy limitations, recurrence
  movement/cancellation, attendees/resources, and conference-link extraction.
- Native provider mappers now exist for Google Calendar event resources,
  Microsoft Graph events, Exchange EWS-style payloads, and Bitrix24 calendar
  events. They map into the common normalized event contract instead of keeping
  raw provider payloads.
- Rich provider adapters in 060 are read/normalize boundaries only. OAuth
  consent, live discovery, tenant-admin service access, delta polling against
  real providers, and provider-specific retry/backoff tuning need separate
  live-provider approval and metadata-only evidence before production rollout.
- Russian/on-prem providers without a stable public rich API remain supported
  through custom CalDAV/iCalendar configuration and capability labels, not by
  claiming unverified vendor-specific REST access.

## Common Event Contract

Every provider maps into the same 2brain Rec contract. If a provider cannot
return a field, store an explicit `unsupported`, `not_returned`,
`private_redacted`, or `free_busy_only` state instead of inventing data.

### Identity Fields

- `provider_family`: `caldav`, `yandex`, `mail_ru`, `vk_workspace`,
  `google_calendar`, `microsoft_graph`, `exchange_ews`, `bitrix24`,
  `mailion_myoffice`, `r7_office`, `communigate`, `rupost`, `custom_caldav`.
- `provider_account_id`: stable account/mailbox identifier where available.
- `calendar_id`: provider calendar collection identity.
- `calendar_display_name`: safe label shown after authorization.
- `event_id`: provider event/item id.
- `ical_uid`: iCalendar `UID` where available.
- `recurring_series_id`: provider series/master id.
- `recurrence_instance_id`: provider recurrence instance id or
  `RECURRENCE-ID`.
- `original_start`: original start for moved recurring instances.
- `version`: ETag, sequence, changeKey, sync token, CalDAV ctag, or provider
  version where available.
- `source_created_at`, `source_updated_at`, `source_deleted_at`.
- `source_status`: `confirmed`, `tentative`, `cancelled`, `deleted`,
  `private`, `free_busy_only`, `unknown`.

### Schedule Fields

- `starts_at`, `ends_at`, `duration_seconds`.
- `timezone`, `original_start_timezone`, `original_end_timezone`.
- `all_day`, `floating_time`.
- `transparency`: busy/free/working_elsewhere/out_of_office if available.
- `recurrence_rule`: RRULE or provider recurrence object.
- `recurrence_exceptions`: EXDATE/RDATE/modified/deleted occurrences.
- `reminders`: metadata only; do not create reminders in 060.

### Content And Context Fields

- `title` / `summary`.
- `description` / `body` / agenda.
- `location` and `locations`.
- `conference_links`: parsed links and provider conference metadata.
- `conference_provider_family`: Telemost, MTS Link, Kontur.Talk, TrueConf,
  VK Calls, Zoom, Google Meet, Microsoft Teams, Webex, generic.
- `dial_in_metadata`: phone/SIP/dial code metadata, sensitive by default.
- `categories`, `color`, `tags`.
- `attachments_metadata`: names/types/provider ids only; do not fetch files in
  the first layer.
- `privacy_class`: public/private/confidential/free-busy-only/unknown.
- `provider_extras`: bounded JSON snapshot for provider fields not yet modeled.

### People And Resource Fields

- `organizer`: email, display name, provider id, internal/external status.
- `creator`: email, display name, provider id.
- `owner`: calendar owner/mailbox owner.
- `attendees`: required/optional/resource/room/group/unknown.
- `attendee_response`: accepted/declined/tentative/needs-action/organizer.
- `attendee_email`, `attendee_display_name`, `provider_user_id`.
- `resource_kind`: room, equipment, distribution list, group, contact, user.
- `candidate_recipient_class`: internal, external, resource, group, declined,
  hidden, no_email, unknown.

### 2brain-Derived Fields

- `context_confidence`: selected, high, medium, low, ambiguous, none.
- `context_reasons`: current event, selected by user, meeting URL match,
  provider account match, organizer match, title similarity, target app hint.
- `title_source`: user, calendar, platform, generic.
- `roster_source`: calendar, transcript, manual, none.
- `safe_to_show_in_list`: boolean plus reason.
- `safe_to_use_as_title`: boolean plus policy/context reason.
- `retention_class` and `deletion_state`.

## Provider Priority Matrix

| Priority | Provider | Adapter | Why |
|---|---|---|---|
| P1 | Yandex Calendar | CalDAV preset | Russian default; official CalDAV sync and app passwords. |
| P1 | Mail.ru Calendar | CalDAV preset | Russian consumer/default mailbox; official CalDAV settings. |
| P1 | Google Calendar | Rich API plus optional CalDAV | Strong event model, Meet metadata, attendees, recurrence. |
| P1 | Microsoft 365 / Outlook | Microsoft Graph | Strong event model, Teams metadata, delta sync, enterprise auth. |
| P1.5 | Exchange Server on-prem | EWS | Required for self-hosted/on-prem Microsoft customers; richer than generic ICS. |
| P1.5 | Bitrix24 | REST API | Popular RU business stack; calendar has participants, CRM links, recurrence. |
| P2 | VK WorkSpace / VK WorkMail | CalDAV/custom endpoint until vendor proof | Important RU suite, but no stable public external calendar API found in this pass. |
| P2 | Mailion / MyOffice | CalDAV/custom URL | Official docs expose CalDAV links; common enterprise replacement stack. |
| P2 | R7-Office | CalDAV/custom URL plus API to get CalDAV link | Official support documents CalDAV link API. |
| P2 | CommuniGate Pro | CalDAV/custom URL | On-prem enterprise; official CalDAV support. |
| P2/P3 | RuPost | CalDAV/custom URL | On-prem/RU enterprise; public docs point to CalDAV/CalDAV integrations. |
| P3 | Kontur.Talk, MTS Link, TrueConf | Conference-link detectors, not calendar source of truth | Calendar companion/conference systems; useful to classify links, not own roster. |

## Provider Details

### Yandex Calendar / Yandex 360

**Recommended adapter**: `caldav_yandex` preset backed by the generic CalDAV
adapter.

**Evidence**: Yandex Calendar desktop sync docs say calendars sync through
CalDAV and describe app-password setup. The macOS advanced setup names
`caldav.yandex.ru`, SSL, and a principal path format. Yandex 360 business docs
also describe service applications, which may matter for a later admin-wide
enterprise adapter.

**Auth / connection model**:

- User-level app password.
- Username as mailbox/account, including domain for Yandex 360 business.
- Server preset: `caldav.yandex.ru`.
- Discovery by user-supplied CalDAV URL from the calendar export/settings tab
  or by principal URL when supported.
- Enterprise service-app access is future scope and requires an explicit admin
  consent, tenant, and privacy gate.

**Expected fields through CalDAV/iCalendar**:

- UID, SUMMARY, DTSTART, DTEND, timezone, STATUS, SEQUENCE.
- ORGANIZER and ATTENDEE when event permissions expose them.
- DESCRIPTION and LOCATION, including Telemost or other meeting links if stored
  in event body/location.
- RRULE/EXDATE/RECURRENCE-ID for recurrence.
- CLASS/private fields when exposed by the provider.

**What to ingest for 060**:

- All event identity and schedule fields.
- Title as candidate meeting title.
- Organizer and attendees as calendar roster.
- Conference URLs from description/location.
- Private/free-busy limitation state when Yandex hides content.

**Limitations / risks**:

- App passwords are secrets and must never touch desktop diagnostics.
- Users may have multiple calendars; connection must let them choose.
- Yandex docs warn app passwords are shown once; recovery UX must be clear.
- Admin-wide org sync is tempting but not first slice.

**2brain implementation stance**:

- P1 provider preset.
- Read-only sync only.
- No event mutation, no Telemost link creation, no invite updates.

Sources:

- https://yandex.com/support/yandex-360/customers/calendar/web/en/sync/sync-desktop
- https://yandex.com/support/yandex-360/customers/calendar/web/en/sync/sync-mobile
- https://yandex.ru/support/yandex-360/business/admin/ru/security-service-applications
- https://help.mts-link.ru/article/25655

### Mail.ru Calendar

**Recommended adapter**: `caldav_mail_ru` preset backed by the generic CalDAV
adapter.

**Evidence**: Official Mail Calendar help says sync works with clients that
support CalDAV, lists account type `CalDAV`, server `calendar.mail.ru`, mailbox
as username, and a special external-app password.

**Auth / connection model**:

- User mailbox as login.
- Special external application password.
- Server preset: `calendar.mail.ru`.
- If provider UI exposes a full CalDAV URL, accept it as a custom override.

**Expected fields through CalDAV/iCalendar**:

- Standard VEVENT identity, title, start/end, recurrence, organizer/attendees
  when exposed.
- Event body/location with meeting links.
- Participant availability/response may be visible depending on account and
  event role.

**What to ingest for 060**:

- Same common CalDAV mapping.
- Calendar account identity should be normalized by email domain because users
  can use Mail.ru, VK Mail, business domains, or aliases.
- Preserve provider limitations when attendee fields are incomplete.

**Limitations / risks**:

- Public docs describe sync settings, not an admin-wide calendar API.
- Some advanced fields may depend on Mail web UI behavior and not appear in
  CalDAV.
- External app password management must be treated as a recovery flow, not a
  normal password prompt.

**2brain implementation stance**:

- P1 provider preset.
- Do not claim Mail.ru REST calendar API.
- Use custom CalDAV URL fallback for tenant variants.

Sources:

- https://help.mail.ru/calendar-help/synchronization/about/
- https://help.mail.ru/calendar-help/synchronization/calendar/

### VK WorkSpace / VK WorkMail

**Recommended adapter**: `caldav_custom` with VK WorkSpace preset only after
tenant URL/auth proof.

**Evidence**: Public product materials show VK WorkSpace includes mail,
calendar, contacts, and communication tools. In this research pass, a stable
official external calendar REST API was not found. Because VK WorkSpace has
SaaS/on-prem variants, capabilities may differ by tenant and license.

**Auth / connection model**:

- Treat as custom CalDAV until a tenant-admin or vendor doc provides exact
  endpoint and auth mode.
- Allow provider label `vk_workspace` for capability reporting, but store
  actual adapter as CalDAV unless richer API is proven.
- Expect app-password or admin-provided credentials depending on deployment.

**Expected fields through CalDAV/iCalendar**:

- Standard VEVENT fields where the tenant exposes CalDAV.
- Organizer/attendees and recurrence if the CalDAV server emits them.
- Conference links from body/location.

**What to ingest for 060**:

- Provider-neutral CalDAV payload.
- Tenant capability result: `caldav_verified`, `calendar_api_unconfirmed`,
  `attendees_supported`, `private_events_supported`, etc.

**Limitations / risks**:

- Do not represent VK WorkSpace as having confirmed public REST calendar API
  until official docs or vendor access confirm it.
- SaaS/on-prem differences can be large.
- If endpoint is not discoverable, require manual URL entry and a clear test
  connection step.

**2brain implementation stance**:

- P2, after generic CalDAV works.
- Provider preset is mostly UX copy and validation, not a separate code path.
- Add a vendor-proof task before any rich adapter claim.

Sources:

- https://habr.com/ru/companies/vk/articles/851128/
- https://www.tadviser.ru/index.php/%D0%A1%D1%82%D0%B0%D1%82%D1%8C%D1%8F%3A%D0%9B%D0%B0%D0%B1%D0%BE%D1%80%D0%B0%D1%82%D0%BE%D1%80%D0%B8%D1%8F_TAdviser%3A_%D0%94%D0%B5%D1%82%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B9_%D0%BE%D0%B1%D0%B7%D0%BE%D1%80_VK_WorkSpace_%E2%80%94_%D1%81%D1%83%D0%BF%D0%B5%D1%80%D0%B0%D0%BF%D0%BF%D0%B0_%D0%B4%D0%BB%D1%8F_%D1%81%D0%BE%D0%B2%D0%BC%D0%B5%D1%81%D1%82%D0%BD%D0%BE%D0%B9_%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D1%8B_%D0%BA%D0%BE%D0%BC%D0%B0%D0%BD%D0%B4_%D0%BB%D1%8E%D0%B1%D0%BE%D0%B3%D0%BE_%D0%BC%D0%B0%D1%81%D1%88%D1%82%D0%B0%D0%B1%D0%B0

### Bitrix24

**Recommended adapter**: `bitrix24_calendar_rest`.

**Evidence**: Bitrix24 has official Calendar REST API docs. Calendar event
methods include listing events, upcoming events, getting by id, adding,
updating, deleting, participation status, and user availability. The event list
method returns user/group/company calendar scope, date window, event name,
start/end, time zones, meeting status, host, meeting settings, reminders,
recurrence, relations, attendees, sync ids, and CRM links.

**Auth / connection model**:

- OAuth or incoming webhook depending on customer installation.
- Workspace-scoped Bitrix24 portal URL.
- Calendar REST scope.
- User-owned calendar first; company/group calendars can be later if the user
  has rights.

**Expected fields through REST**:

- `ID`, `PARENT_ID`, `DELETED`, `CAL_TYPE`, `OWNER_ID`.
- `NAME`, `DATE_FROM`, `DATE_TO`, original date for recurrence, time zones.
- `DESCRIPTION`, `PRIVATE_EVENT`, `ACCESSIBILITY`, `IMPORTANCE`.
- `IS_MEETING`, `MEETING_STATUS`, `MEETING_HOST`, `MEETING` object.
- `LOCATION`, `REMIND`, `COLOR`, `RRULE`, `EXDATE`, recurrence relations.
- `ATTENDEE_LIST`, attendee entity list.
- `DAV_XML_ID`, `G_EVENT_ID`, `CAL_DAV_LABEL`, `VERSION`, `SYNC_STATUS`.
- `UF_CRM_CAL_EVENT` for linked CRM entities.

**What to ingest for 060**:

- Full rich event snapshot, including Bitrix IDs and sync ids.
- Host/participant status mapped to calendar roster.
- CRM links only as metadata ids/classes, not as fetched CRM data in 060.
- Availability/accessibility as schedule context.
- Meeting settings like hidden guests and invite flags as privacy hints.

**Limitations / risks**:

- Bitrix may expose CRM-linked customer context; treat as sensitive.
- Webhook integrations can be overbroad; prefer least-privilege OAuth where
  practical.
- External user access can be denied by Bitrix; safe error mapping required.
- Do not use add/update/delete APIs in 060 even though they exist.

**2brain implementation stance**:

- First rich RU business adapter after generic CalDAV.
- Good candidate for sales/customer-success teams.
- Requires fixtures for attendee statuses, hidden guests, CRM links,
  recurrence, and access denied.

Sources:

- https://apidocs.bitrix24.com/api-reference/calendar/index.html
- https://apidocs.bitrix24.com/api-reference/calendar/calendar-event/index.html
- https://apidocs.bitrix24.com/api-reference/calendar/calendar-event/calendar-event-get.html
- https://apidocs.bitrix24.com/api-reference/calendar/calendar-event/calendar-event-get-nearest.html
- https://apidocs.bitrix24.com/api-reference/calendar/calendar-event/calendar-event-get-by-id.html

### Mailion / MyOffice

**Recommended adapter**: `caldav_mailion_myoffice` preset plus custom CalDAV.

**Evidence**: Mailion docs say Mailion calendars can be used in third-party
mail clients if they support CalDAV and explain copying a CalDAV link. MyOffice
release notes describe two-way synchronization with external calendars through
CalDAV and mention recurrence/attachment-related limitations.

**Auth / connection model**:

- User copies CalDAV link from Mailion calendar UI.
- Auth mode depends on deployment.
- For on-prem customers, admin may provide base URL and auth instructions.

**Expected fields through CalDAV/iCalendar**:

- Standard VEVENT fields.
- Participants/resources if the server exposes them.
- Description/location/conference links.
- Attachment metadata may appear, but fetching attachments is out of scope.

**What to ingest for 060**:

- Full CalDAV event snapshot.
- Provider capability `attachments_metadata_only`.
- Provider limitation flags for recurrence, external calendar sync limits, or
  missing attendee data.

**Limitations / risks**:

- Docs are user-oriented; exact server behavior may vary by deployment.
- Attachment behavior needs safe metadata-only handling.
- Corporate installations may have custom domains and TLS/cert constraints.

**2brain implementation stance**:

- P2 after generic CalDAV.
- No separate rich adapter unless a customer proves a stronger API need.

Sources:

- https://support.myoffice.ru/help/mailion/web/calender/actions_with_calendars/calendar_link_create/
- https://support.myoffice.ru/help/administration-squadus/desktop/topic/calendar/
- https://support.myoffice.ru/en/release/what-s-new-in-mailion-1-6/
- https://support.myoffice.ru/release/novye-vozmozhnosti-mailion-1-6/

### R7-Office

**Recommended adapter**: `caldav_r7_office` preset plus optional API helper to
resolve CalDAV URL.

**Evidence**: R7 support documents an API endpoint
`GET api/2.0/calendar/{calendarId}/caldavurl` that returns the CalDAV link for
a calendar and requires authentication. R7 also exposes iCal links and calendar
API surfaces.

**Auth / connection model**:

- Authenticated portal API can return CalDAV URL.
- Generic CalDAV connection can then sync the actual calendar.
- For 060, it is enough to accept a copied CalDAV URL; helper discovery can be
  added if customer demand exists.

**Expected fields through CalDAV/iCalendar**:

- Standard VEVENT fields.
- Calendar ids/subscriptions from portal API if using helper route.
- iCal links may be read-only and less suitable for private participant data.

**What to ingest for 060**:

- CalDAV event snapshot.
- Portal/calendar id only if provided safely.
- Avoid relying on public iCal for sensitive private calendars unless explicitly
  authorized.

**Limitations / risks**:

- R7 versions differ; endpoint path may depend on product generation.
- API auth and CalDAV auth may be different.
- iCal links can be read-only snapshots and may lack attendee richness.

**2brain implementation stance**:

- P2. Start with custom/preset CalDAV.
- Add URL-discovery helper only after generic CalDAV is validated.

Sources:

- https://support.r7-office.ru/community_server/api/settings-api/calendar-api/calendars_and_subscriptions/get-caldav-link/
- https://support.r7-office.ru/community_server/api/settings-api/calendar-api/calendars_and_subscriptions/get-ical-link/

### CommuniGate Pro

**Recommended adapter**: `caldav_communigate` custom/preset.

**Evidence**: CommuniGate Pro docs say the server supports CalDAV as a WebDAV
extension. It lets CalDAV clients read and change user calendar and task data.
Docs include root and explicit `/CalDAV/` URL patterns, authenticated requests,
folder/calendar names, and an older iCalendar subscription/publish path.

**Auth / connection model**:

- Authenticated CalDAV over HTTP/S.
- Custom server URL, port, domain, mailbox/calendar folder.
- Discovery may work from server root, but UI should support explicit URL.

**Expected fields through CalDAV/iCalendar**:

- Standard VEVENT/VTODO fields.
- Calendar folders and shared folders where permissions allow.
- Attachments may be stored server-side; fetch nothing in 060.

**What to ingest for 060**:

- Calendar event snapshots from selected calendar folders.
- Shared calendar source owner and permissions as capability metadata.
- Ignore task/VTODO for recording-time context selection unless a later feature wants tasks.

**Limitations / risks**:

- On-prem TLS and port setup can vary.
- Shared calendars require explicit permissions.
- The server supports mutation paths; 060 must remain read-only.

**2brain implementation stance**:

- P2 for on-prem customers.
- Treat as generic CalDAV with better setup documentation.

Sources:

- https://doc.communigatepro.ru/russian/admin/access/WebDAV.html
- https://doc.communigatepro.ru/admin/access/

### RuPost

**Recommended adapter**: `caldav_rupost` custom/preset when customer provides
endpoint details.

**Evidence**: Public RuPost/Astra docs and KB materials reference CalDAV
calendar synchronization, including integration with Kontur.Talk over CalDAV.
Some detailed KB content may require support access.

**Auth / connection model**:

- Customer/admin-supplied CalDAV endpoint.
- On-prem credentials and TLS policy.
- Possibly paired with CardDAV address book in a future contacts feature; not
  required for 060.

**Expected fields through CalDAV/iCalendar**:

- Standard event data if exposed by the tenant.
- Participant/resource data depends on RuPost deployment and event source.

**What to ingest for 060**:

- Generic CalDAV events.
- Provider capability report that avoids overclaiming.
- Conference links from event body/location.

**Limitations / risks**:

- Public docs are less complete than Yandex/Mail.ru/R7/CommuniGate.
- Customer-specific validation is required before promising P1 support.

**2brain implementation stance**:

- P2/P3. Support through custom CalDAV first.
- Add fixture once a real tenant/export sample is available.

Sources:

- https://wiki.astralinux.ru/kb/rupost-sinhronizatsiya-kalendarya-kontur-tolk-po-protokolu-caldav-326831820.html
- https://wiki.astralinux.ru/kb/rupost-216542210.html

### Google Calendar

**Recommended adapter**: `google_calendar_api` rich adapter. Optional CalDAV is
fallback only.

**Evidence**: Google Calendar Events API exposes rich event resources including
start/end/timezone, recurrence, recurring event ids, organizer, attendees,
response status, location, event types, and conference data. Google also has a
CalDAV interface, but the Events API gives better sync and metadata control.

**Auth / connection model**:

- OAuth user authorization for individual calendar sync.
- Workspace domain-wide delegation only for a later admin feature with explicit
  admin consent.
- Store refresh tokens server-side only.

**Expected fields through API**:

- `id`, `iCalUID`, `etag`, `created`, `updated`, `status`, `sequence`.
- `summary`, `description`, `location`, `colorId`, `eventType`.
- `start`, `end`, `endTimeUnspecified`, timezone.
- `recurrence`, `recurringEventId`, `originalStartTime`.
- `organizer`, `creator`.
- `attendees`: email, displayName, optional, resource, organizer, self,
  responseStatus, comments, additional guests.
- `conferenceData`: Google Meet or third-party add-on type, entry points,
  meeting codes, passcodes, phones, SIP, notes.
- `attachments`, `extendedProperties`, reminders, transparency, visibility.

**What to ingest for 060**:

- All above fields that are returned by scopes/permissions.
- Conference passcodes as sensitive fields; never log or show in evidence.
- Attendees as roster/candidates only.
- Google Meet entry points as conference-link candidates.

**Limitations / risks**:

- Attendees may be omitted or truncated depending on API parameters.
- Service account attendee population requires domain-wide delegation; not a
  first-layer assumption.
- Google warns about conference data reuse causing access/privacy issues; 060
  does not create conference data.
- Consumer vs Workspace permissions/admin approval differ.

**2brain implementation stance**:

- P1 rich adapter.
- Read-only `calendar.events.readonly`-style scope where possible.
- Do not request write/conference creation scopes in 060.

Sources:

- https://developers.google.com/workspace/calendar/api/v3/reference/events
- https://developers.google.com/workspace/calendar/api/guides/create-events
- https://developers.google.com/workspace/calendar/caldav/v2/guide

### Microsoft 365 / Outlook Calendar Through Microsoft Graph

**Recommended adapter**: `microsoft_graph_calendar`.

**Evidence**: Microsoft Graph `event` resource includes attendees, body/body
preview, all-day/cancelled/draft flags, recurrence, instances, categories,
locations, organizer, online meeting info, join URL through `onlineMeeting`,
change keys, extensions, and more. Graph calendar APIs support Microsoft 365
calendar access and are the primary cloud route.

**Auth / connection model**:

- OAuth user delegated permissions for individual calendar sync.
- Application permissions/admin consent only for a later enterprise feature.
- Store refresh tokens server-side only.
- Tenant/admin approval must be visible as a recoverable connection state.

**Expected fields through Graph**:

- `id`, `iCalUId`, `changeKey`, created/lastModified times.
- `subject`, `body`, `bodyPreview`, `importance`, `sensitivity`.
- `start`, `end`, original time zones, `isAllDay`.
- `isCancelled`, `isDraft`, `showAs`, `responseStatus`.
- `organizer`, `attendees`.
- `location`, `locations`.
- `isOnlineMeeting`, `onlineMeetingProvider`, `onlineMeeting`, `onlineMeetingUrl`.
- `recurrence`, `seriesMasterId`, `instances`, cancelled occurrences where
  selected/expanded.
- `categories`, `hasAttachments`, extensions, extended properties.

**What to ingest for 060**:

- All event identity/schedule/content/participants returned by selected scope.
- Teams join URL only as sensitive conference metadata.
- Body/bodyPreview as sensitive agenda text.
- Sensitivity and `hideAttendees` as privacy flags.

**Limitations / risks**:

- Admin consent is common in enterprise tenants.
- `onlineMeetingUrl` is deprecated in favor of `onlineMeeting.joinUrl`;
  normalize both but prefer the modern join URL when returned.
- Extended properties are useful but can contain tenant-specific sensitive data.
- Exchange Online vs Outlook consumer behavior can differ.

**2brain implementation stance**:

- P1 rich adapter.
- Read-only events first.
- Use Graph for Microsoft 365/Outlook cloud; do not force on-prem Exchange into
  Graph if the customer is self-hosted.

Sources:

- https://learn.microsoft.com/en-us/graph/api/resources/event?view=graph-rest-1.0
- https://learn.microsoft.com/en-us/graph/outlook-calendar-concept-overview
- https://learn.microsoft.com/en-us/graph/api/resources/calendar?view=graph-rest-1.0
- https://learn.microsoft.com/en-us/graph/api/resources/onlinemeeting?view=graph-rest-1.0

### Microsoft Exchange Server On-Prem Through EWS

**Recommended adapter**: `exchange_ews_calendar`.

**Evidence**: Microsoft EWS docs describe EWS as a cross-platform SOAP/XML API
for mailbox items including meetings and contacts, usable against Exchange
Online and on-prem Exchange Server 2007+. EWS calendar docs cover calendar
folders/items, appointments, meetings, attendees, resources, rooms,
availability, time zones, recurrence, occurrences, exceptions, updates and
cancellations.

**Auth / connection model**:

- On-prem Basic over SSL, NTLM, or OAuth depending on Exchange version and
  customer configuration.
- Autodiscover or admin-supplied EWS endpoint.
- Optional impersonation/service account only with explicit admin approval in a
  later enterprise mode.
- Read-only mailbox/calendar access in 060.

**Expected fields through EWS**:

- Calendar item id/change key.
- Subject, body, sensitivity, categories, importance.
- Start/end, duration, time zones, all-day.
- Organizer, required attendees, optional attendees, resources, rooms.
- Location.
- Recurrence master, occurrences, exceptions, deleted occurrences.
- Meeting request/response status, cancellation/update state.
- Free/busy and availability if explicitly queried.
- Extended properties when selected.

**What to ingest for 060**:

- Rich event data for on-prem organizations that cannot use Microsoft Graph.
- Meeting attendees/resources as roster/candidates only.
- Calendar view bounded by date range for efficient sync.
- Change keys for update reconciliation.

**Limitations / risks**:

- EWS is older and tenant configurations vary widely.
- Auth can be painful: Basic/NTLM/OAuth, TLS, internal DNS, Autodiscover, proxy.
- Impersonation and service account access are high-risk and out of the first
  individual-user flow.
- EWS supports write/send operations; 060 must not create or update meetings.
- Some Exchange Online deployments may prefer Graph over EWS.

**2brain implementation stance**:

- P1.5 because the user explicitly asked not to forget Exchange Server.
- Separate from Microsoft Graph in UX and capability reporting.
- Start with user-provided EWS endpoint or Autodiscover spike in planning.
- Add fixtures for recurrence exceptions, attendee/resource rooms, cancellation,
  private sensitivity, and NTLM/OAuth connection errors.

Sources:

- https://learn.microsoft.com/en-us/exchange/client-developer/exchange-web-services/ews-applications-and-the-exchange-architecture
- https://learn.microsoft.com/en-us/exchange/client-developer/exchange-web-services/calendars-and-ews-in-exchange
- https://learn.microsoft.com/en-us/exchange/client-developer/exchange-web-services/properties-and-extended-properties-in-ews-in-exchange

## Conference And Calendar-Companion References

These products prove useful product patterns, but 2brain Rec should not copy
their auto-join/auto-send behavior in 060.

### Fireflies

- Supports Google Calendar and Outlook Calendar.
- Shows upcoming meetings from the connected calendar.
- Requires meeting links in the calendar to detect/join meetings.
- Has auto-join toggles and recap behavior.

2brain takeaway: use upcoming meetings and meeting-link detection as context.
Do not auto-join or send recaps in 060.

Sources:

- https://guide.fireflies.ai/articles/4246295295-what-calendars-are-supported
- https://guide.fireflies.ai/articles/2596333792-upcoming-meetings-module-faqs

### Fathom

- Connects Google or Microsoft calendars.
- Uses calendar schedule to show upcoming meetings and support auto-join.
- Its quick start also promotes auto-record and auto-share.

2brain takeaway: calendar context is a core onboarding step for this product
category, but auto-share and auto-record are explicitly later layers.

Sources:

- https://help.fathom.video/en/articles/276608

### Otter

- Connects Google Calendar and Microsoft Outlook calendar; iOS can connect a
  device calendar.
- Calendar events sync into Otter; Otter notes can later be connected to
  Google calendar events.
- Otter explicitly does not support on-prem Exchange calendars, which is a
  gap 2brain can cover through EWS for self-hosted customers.

2brain takeaway: support Microsoft 365/Google for common SaaS users and keep
Exchange Server as a differentiator for controlled/on-prem customers.

Sources:

- https://help.otter.ai/hc/en-us/articles/360048070154-Connect-your-Calendar-and-Contacts-to-Otter
- https://help.otter.ai/hc/en-us/articles/13676368852631-Manage-your-calendar-meeting-events

### MTS Link

- Documents a Yandex Calendar integration using Yandex CalDAV.
- Creates or updates meeting links as part of its integration, which is not in
  060 scope.

2brain takeaway: Russian products use CalDAV for Yandex integration; conference
links from MTS Link should be parsed as context only.

Sources:

- https://help.mts-link.ru/article/25655

### Kontur.Talk

- Public docs expose calendar integration guidance.
- RuPost KB references Kontur.Talk calendar sync over CalDAV.

2brain takeaway: parse Kontur.Talk links from event text/location and treat
Kontur.Talk as a conference provider, not a first-layer calendar source.

Sources:

- https://talk.kontur-f.ru/instructions/integraciya-s-kalendaryami/
- https://wiki.astralinux.ru/kb/rupost-sinhronizatsiya-kalendarya-kontur-tolk-po-protokolu-caldav-326831820.html

### TrueConf

- Documents Calendar Connector integrations with corporate calendars such as
  Exchange, Thunderbird, R7-Office, and RuPost.

2brain takeaway: TrueConf is mainly a conference target / calendar companion.
For 060, parse TrueConf links as meeting context and rely on the underlying
calendar source for roster and schedule truth.

Sources:

- https://trueconf.ru/docs/server/ru/admin/calendar/

## Implementation Order Recommendation

### Phase A: Provider-Neutral Core

1. Calendar source connection state and secret boundary.
2. Generic CalDAV client with rolling 12-month future sync horizon.
3. iCalendar parser and normalized event snapshot.
4. Provider capability matrix.
5. Event privacy/sensitivity classification.
6. Calendar participant roster.
7. Conference-link detector.
8. Recording-time event context link model.

### Phase B: Presets On Top Of Generic CalDAV

1. Yandex preset.
2. Mail.ru preset.
3. Custom CalDAV URL.
4. Mailion/MyOffice, R7, CommuniGate, RuPost setup notes.
5. VK WorkSpace-compatible setup only when tenant URL is verified.

### Phase C: Rich API Adapters

1. Google Calendar Events API.
2. Microsoft Graph Calendar.
3. Exchange Server EWS.
4. Bitrix24 Calendar REST.

### Phase D: UX And Validation Surface

1. Connected calendars and sync health.
2. Upcoming/current meetings context.
3. Calendar context on meeting detail.
4. Calendar roster separated from transcript speakers.
5. Future recipient candidates shown only as disabled/policy-pending context.
6. Metadata-only evidence and forbidden-content scans.

## Validation Fixtures Required

- Simple one-off event.
- Event with all-day dates.
- Event with floating time and timezone.
- Recurring series with moved instance.
- Recurring series with cancelled instance.
- Private/free-busy-only event.
- Event with organizer and attendees.
- Event with resources/rooms.
- Event with declined attendee.
- Event with group/distribution list.
- Event with >200 attendees or provider truncation.
- Event with multiple conference links.
- Event with passcode/PIN/dial-in.
- Event with attachment metadata.
- Event deleted after recording-time context link.
- Duplicate organizer/attendee calendar copies.
- Overlapping personal/work events.
- Bitrix24 event with CRM links.
- Google event with Meet conference data.
- Microsoft Graph event with Teams onlineMeeting.
- Exchange EWS recurring exception.

## Hard Product Rules For All Providers

- Read-only provider access in 060.
- Server owns calendar credentials.
- Desktop never stores provider tokens/app passwords.
- Calendar attendees are not meeting access grants.
- Calendar attendees are not message recipients.
- Calendar roster is not diarization.
- Calendar title can name a recording only with policy and confident
  recording-time context link.
- Event description, meeting links, passcodes, attachments, and emails are
  sensitive content.
- Logs/evidence never include private event text, attendee dumps, passcodes,
  secrets, signed links, or live credential paths.
- Provider downtime must not block recording upload, processing, playback, or
  meeting review.
