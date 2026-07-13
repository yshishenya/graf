# Calendar Fixture Rules

Calendar fixtures are synthetic only. They exist to prove provider coverage,
normalization boundaries, matching behavior, and privacy behavior without
committing real calendar payloads.

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
- Treat Yandex and Mail.ru as CalDAV presets; treat Exchange EWS and Bitrix24 as
  richer provider examples; treat VK WorkSpace, Mailion/MyOffice, R7-Office,
  CommuniGate Pro, RuPost, Nextcloud/SOGo-like deployments, and custom CalDAV as
  generic CalDAV examples unless later vendor proof changes that boundary.

## Feature 098 Auto-Match Fixtures

`tests.fixtures.calendar_auto_match` provides deterministic builders for clear,
overlap, private/free-busy, stale/latest-failed, and recurring scenarios. All
participant and owner identities must use a `.test` domain. The builders remove
event descriptions and attachments and retain conference evidence only as a hash
plus a redacted preview; raw links and passcodes are forbidden.

The fixture-only bounds mirror the feature design: at most 4 selected sources,
50 event rows, 10 visible candidates, and 100 roster items. These constants are
test data limits, not production configuration.
