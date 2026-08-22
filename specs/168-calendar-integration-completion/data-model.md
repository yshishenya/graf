# Feature 168 data model and state semantics

## Existing entities to reuse

| Entity | Existing role | Feature 168 rule |
|---|---|---|
| `CalendarSource` | tenant/owner/provider connection and sync projection | Add only fields required for authoritative operation/provider status; persist only a non-reversible provider account subject hash in the existing capabilities projection; keep disconnected terminal semantics. |
| `CalendarCredentialEnvelope` | sealed server-owned provider material | Plaintext is never returned; disconnect makes it non-readable and records the local purge timestamp without provider-side revocation. |
| `ExternalCalendar` | provider calendar catalog and selected flag | Catalog rows are replaced/reconciled by stable provider ID; hidden/unavailable rows cannot be selected. |
| `CalendarEventSnapshot` | normalized future event cache | Stores policy-bounded event state; future rows purge on disconnect; matched references detach. |
| `CalendarParticipant` | bounded roster/recipient classification | No access grant, delivery, speaker rename or evidence egress. |
| `ConferenceLinkCandidate` | hashed/classified meeting link identity | Store hash/classification only; no raw URL/passcode in logs or UI. |
| `CalendarSettingsPreference` | prompt/event-filter settings | Server-owned, tenant-scoped, browser/embedded shared. |
| `CalendarAuditEvent` | metadata-only lifecycle/audit record | Operation/provider/outcome/reason/duration bucket only. |
| `RecordingCalendarMatchAttempt` | short-lived resolve decision | Source references are scrubbed/purged on disconnect; exact existing TTL remains. |
| `RecordingCalendarContextLink` | immutable meeting context projection | Retains safe meeting-retention snapshot and changes to `calendar_unavailable`/`deleted` when source or meeting lifecycle requires. |

## Proposed operation record (only if existing audit fields cannot carry it)

If the existing source timestamps and audit events cannot represent an in-flight
operation, add a small `CalendarOperation` row:

| Field | Rule |
|---|---|
| `id`, `workspace_id`, `source_id` | tenant-scoped opaque identity |
| `kind` | `connect`, `catalog`, `sync`, `disconnect` |
| `state` | `queued`, `running`, `succeeded`, `failed`, `cancelled` |
| `safe_reason_code` | allow-listed, no provider response body |
| `idempotency_key` | unique per source/owner/operation window |
| `started_at`, `finished_at`, `attempt_count` | bounded lifecycle metadata |
| `provider_request_id_hash` | optional hash only, never raw request ID if sensitive |

Do not add this table preemptively. First prove whether source/audit rows are
enough; this is the planned ponytail ceiling.

## Google credential/account fields

Reuse `CalendarCredentialEnvelope` for refresh-token material and provider
metadata. The existing `CalendarSource.capabilities_json.account_subject_hash`
stores only the hashed OIDC
`sub` returned by Google's server-side userinfo call; the email and ID token
are not persisted. Add only:

- provider account subject hash (not an email unless product/privacy approval
  requires it);
- safe account display label;
- granted scope set from an allow-list;
- token expiry/reconnect state;
- provider key version and revocation timestamp.

Never store authorization code, access token, raw refresh token in a normal
model field, calendar description, event body, analytics property or snapshot.

## Actionable meeting URL custody

The normalized raw meeting URL is encrypted before persistence and stored only
as `CalendarEventSnapshot.provider_extras_json.sealed_open_meeting_url`. The
ordinary browser read model exposes only `meeting_link_present`,
`open_meeting_available` and a tenant-authenticated internal open endpoint.
That endpoint may decrypt and redirect only after current tenant/source/event
checks. The bounded desktop upcoming endpoint may return a validated HTTPS URL
to the authenticated native client for an explicit user action; it must never
write that URL to logs, analytics, screenshots or committed evidence. Private
or free/busy events never expose the action.

## Invariants

1. Every row carries workspace scope; owner mutations enforce user ownership.
2. `disconnected` source cannot have selected calendars or a runnable sync.
3. `credential_state != sealed` means provider runtime must not decrypt/use the
   envelope.
4. Only `synced` data is eligible for automatic context; stale/failed data is
   fail-closed according to existing 098 rules.
5. One selected provider calendar maps to one source/catalog identity; duplicate
   selection IDs are removed deterministically.
6. Event snapshot identity includes provider event/ical/recurrence identity and
   source/calendar scope; sync deletes are explicit.
7. Matched context is immutable in user-visible title/roster/time; lifecycle
   may only detach provider references and mark safe unavailability.
8. Audit rows never contain raw credentials, provider payloads, titles,
   descriptions, participant emails or raw links.
9. A raw actionable meeting URL is never stored outside the sealed snapshot
   field and is never emitted by unauthenticated or cross-tenant reads.

## macOS tray projection

`CalendarTrayModel` is an in-memory, non-persistent projection with:

| Field | Rule |
|---|---|
| `events` | up to 12 server-projected events sorted by start time |
| `state` | `idle`, `loading`, `loaded`, `empty`, `needsSignIn`, `unavailable`, or `stale` |
| `lastUpdatedAt` | local observation time only; not an event timestamp persisted to disk |

The model requests a 15-minute-before/24-hour-after bounded window. It keeps
previous events only while reporting `stale` after a refresh error; it never
falls back to a local calendar cache. A disconnected or unauthorized source
therefore disappears or becomes an explicit sign-in/unavailable state on the
next server read.

## Retention/deletion matrix

| Data | Connect | Sync | Disconnect | Meeting deletion |
|---|---|---|---|---|
| Credential envelope | sealed server-side | runtime decrypt only | purge payload locally; retain content-free tombstone for 30 days | source policy |
| Calendar catalog | discovered | reconcile | mark disconnected and omit active projection | source policy |
| Future event snapshot | none until sync | upsert/delete by provider truth | purge future rows | source policy |
| Participants/link candidates | derived from snapshot | replace bounded rows | purge with future snapshot | source policy |
| Unconsumed match attempt | none/short TTL | no provider refresh | delete/scrub | delete at TTL/meeting delete |
| Consumed meeting context | none | immutable at match | detach source snapshot, mark unavailable; safe retained copy | account/purge under meeting policy |
| Audit metadata | connect events | outcomes/retries | cleanup outcome | deletion outcome |
