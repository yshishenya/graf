# Data Model: browser invitation error responses

## No persistence change

This feature adds no table, field, index, migration, retention rule or durable
state. The existing entities remain authoritative:

- `MeetingShareInvitation` owns invitation status, expiry, recipient binding
  and one-time continuation state.
- `MeetingShareGrant` owns the recipient-bound meeting access after acceptance.
- Auth session and device records own the browser session created by the first
  valid magic-link entry.

## State invariants

- A valid first entry may create the existing account/session/grant sequence.
- A replay, expiry, revoke or recipient mismatch must not create or broaden any
  of those records.
- The browser error response is transient presentation only and must not be
  persisted as meeting or auth data.
