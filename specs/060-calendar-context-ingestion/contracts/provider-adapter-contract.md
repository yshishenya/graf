# Provider Adapter Contract

**Feature**: 060-calendar-context-ingestion

## Purpose

Every provider adapter maps external calendar data into the same 2brain Rec event contract. Provider-specific code must stay behind this boundary so the rest of the product uses normalized calendar sources, events, rosters, links, and capability states.

## Adapter Families

- `caldav`: Yandex, Mail.ru, custom CalDAV, VK WorkSpace-compatible endpoints, Mailion/MyOffice, R7-Office, CommuniGate Pro, RuPost.
- `exchange_ews`: on-prem Exchange through EWS.
- `bitrix24`: Bitrix24 Calendar REST.

## Required Adapter Operations

### Discover Calendars

Input:

- sealed credential handle
- provider endpoint or preset
- workspace/user context

Output:

- provider account id where available
- readable calendar list
- capability state
- safe error code on failure

Rules:

- Never return raw credentials.
- Do not fetch event bodies during discovery unless provider requires it for capability detection.
- Fail closed on invalid credential, MFA/app-password lockout, tenant policy denial, or provider timeout.

### Sync Future Events

Input:

- calendar source id
- selected calendar ids
- rolling 12-month future horizon
- provider sync token/ctag/delta token where available

Output:

- normalized event snapshots
- participant records
- conference-link candidates
- provider capability updates
- sync result counts and safe error codes

Rules:

- No past-event ingestion in 060.
- No retrospective matching of old recordings.
- Use provider pagination and delta tokens where available.
- For CalDAV, use time-range calendar queries and provider/server expansion where possible; preserve recurrence metadata and exceptions.
- Do not fetch attachment file content.
- Bound provider extras and redact diagnostics.

### Disconnect

Input:

- calendar source id
- actor user id

Output:

- credentials purged or revocation-accounted
- future sync stopped
- unmatched/future cache purged
- matched meeting context retained only under meeting retention/deletion policy

Rules:

- Do not mutate provider events in 060.
- Do not revoke provider-side access unless supported and safe; otherwise record revocation as outside 2brain control.

## Normalized Event Output

Required groups:

- identity: provider, calendar id, event id, iCalendar UID, recurrence identity, version/etag/sequence, source status
- schedule: start, end, duration, timezone, all-day, recurrence, transparency/free-busy
- context: title, description, location, conference metadata, categories, attachments metadata, privacy/sensitivity, provider extras
- people/resources: organizer, creator, attendees, rooms/resources, groups, response status, role, email/display fields where available
- 2brain derived: context confidence, title/roster source, sensitivity, lifecycle/deletion state

When a field is missing, use one of:

- `unsupported`
- `not_returned`
- `private_redacted`
- `free_busy_only`
- `admin_policy_dependent`
- `unknown`

Do not fabricate attendees, organizer, title, or meeting links.

## Security Requirements

- Adapter logs and audit events are metadata-only.
- Raw provider payloads are not written to logs or evidence.
- Secrets, tokens, app passwords, passcodes, signed links, attendee dumps, and private agenda text are forbidden in diagnostics.
- Provider request failures record safe reason codes only.

## Timeouts And Rate Limits

- Each provider request must have an explicit timeout.
- Rate limit responses move the source to a recoverable sync state and do not affect upload/review availability.
- Provider downtime returns calendar context unavailable; it never blocks recording upload, processing, playback, or review.

## Provider-Specific Notes

- Yandex and Mail.ru are P1 CalDAV presets.
- Exchange Server on-prem uses EWS.
- Bitrix24 is a rich business-stack adapter.
- VK WorkSpace is CalDAV/custom only until official external calendar API proof exists.
- MTS Link, Kontur.Talk, TrueConf, Telemost, Zoom, Webex, VK Calls, and generic meeting URLs are conference-link families, not calendar source-of-truth adapters in 060.
