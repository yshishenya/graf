# Data Model: Яндекс Календарь

Новая схема не нужна. Feature 201 использует существующие модели Feature 168.

## CalendarSource

- `provider_family = caldav_yandex` — allow-listed provider identity.
- `auth_mode = app_password` — способ подключения.
- `connection_state` — active/disconnected/error lifecycle.
- `credential_state` — sealed/revoked/purged/failed_closed.
- `sync_state` — never_synced/queued/syncing/synced/stale/failure states.
- `selected_calendar_count` — 0..20, derived from selected catalog rows.
- `capabilities_json` — bounded provider metadata and hashed account identity.

Relationships: one owner/workspace-scoped source has one or more
`ExternalCalendar` rows and at most one current readable credential envelope.

## CalendarCredentialEnvelope

- encrypted provider credential payload;
- secret kind `app_password`;
- non-reversible fingerprint for reconnect identity;
- revoked/purged lifecycle markers.

The plaintext password is never part of a response, browser projection,
desktop model, audit event, evidence or log.

## ExternalCalendar

- stable provider calendar ID;
- bounded display label;
- visibility/access role;
- selected flag and optional color/owner hash.

Selection is explicit and deduplicated. Zero selection is valid; more than 20 is
rejected without truncation.

## CalendarEventSnapshot

Existing normalized snapshot rows carry provider/event/calendar identity,
version/cancellation, time bounds, privacy class, safe title state and bounded
conference/participant metadata. Only selected calendars in the approved sync
horizon contribute to active upcoming/context projections.

## State rules

`connect request → provider validation/catalog → active source → selection →
queued → syncing → synced/stale/failure`.

Disconnect is local-first: stop new work, clear selection, purge future and
unmatched derived rows, make the credential unreadable, and retain only approved
meeting-owned context under the existing retention policy.
