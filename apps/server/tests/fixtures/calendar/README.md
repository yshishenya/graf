# Calendar Fixture Rules

Calendar fixtures for feature 060 are synthetic only. They exist to prove provider
coverage, normalization boundaries, and privacy behavior without committing real
calendar payloads.

## Allowed

- Synthetic provider ids, calendar ids, event ids, and iCalendar UIDs.
- Synthetic names and domains under `example.test`.
- Provider limitation markers such as `unsupported`, `not_returned`,
  `private_redacted`, `free_busy_only`, `admin_policy_dependent`, and `unknown`.
- Redacted meeting-link previews and URL hashes.
- Attachment metadata shape without file URLs or fetched file contents.

## Forbidden

- Real provider credentials, OAuth tokens, app passwords, refresh tokens, API keys,
  signed URLs, meeting passcodes, or live credential paths.
- Real meeting titles, agenda text, customer names, attendee lists, screenshots,
  transcript text, raw provider payloads, or private calendar exports.
- Full meeting URLs in logs, diagnostics, evidence, or broad API responses.

## Fixture Expectations

- Keep attendee lists capped and intentionally small unless a test is explicitly
  exercising attendee-heavy behavior.
- Mark provider limitations explicitly instead of fabricating missing organizer,
  attendee, title, recurrence, or conference-link data.
- Use hashed or redacted URL fields for conference-link assertions.
- Treat Yandex and Mail.ru as CalDAV presets; treat Google Calendar, Microsoft
  Graph, Exchange EWS, and Bitrix24 as rich provider examples; treat VK WorkSpace,
  Mailion/MyOffice, R7-Office, CommuniGate Pro, RuPost, and Nextcloud/SOGo-like
  deployments as custom/generic CalDAV examples unless later vendor proof changes
  that boundary.
