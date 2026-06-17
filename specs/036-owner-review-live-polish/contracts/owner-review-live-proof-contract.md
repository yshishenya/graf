# Contract: Owner Review Live Proof

Feature: `036-owner-review-live-polish`

## Purpose

Define the safe proof required to close or bound
`web-owner-live-auth-context` on `rec.2brain.pro`.

## Inputs

- Target origin: `https://rec.2brain.pro`.
- Temporary smoke owner identity/session created by existing production smoke
  helpers, or an already authenticated owner browser session.
- Device/workspace context required by existing auth dependencies.

## Required Behavior

1. Unauthenticated access to `/meetings` and `/meetings/{meeting_id}` must fail
   safe without leaking meeting existence, titles, transcript text, account
   identifiers, tokens, cookies, or private URLs.
2. Authenticated owner access must prove at least:
   - meeting list route state;
   - one meeting detail route state, or a safe empty-state reason;
   - governance/access/deletion state route or panel, or an explicit safe
     reason why it cannot be proven.
3. Temporary session issuance must never print the raw token to stdout/stderr.
4. Temporary token material must be written only to caller-selected local files
   with restrictive permissions and must not be committed.
5. Temporary session cleanup must remove session/binding rows or record a
   blocker before closeout.

## Evidence Shape

Committed evidence may include:

- sanitized HTTP status classes and safe error codes;
- safe route names without private query parameters;
- non-secret auth session id only when already accepted by existing smoke
  evidence rules;
- counts and state labels when they cannot identify private content;
- redacted or synthetic screenshots only.

Committed evidence must not include:

- bearer/session token values;
- cookies;
- raw request headers containing credentials;
- private meeting titles or transcript text;
- private account identifiers or emails;
- signed URLs;
- local private absolute paths except approved installed app path
  `/Applications/2brain Rec.app`.

## Acceptance

The gap `web-owner-live-auth-context` may close only when the production owner
review list, detail or safe empty detail, and governance/access state are proven
with metadata-safe evidence and cleanup passes. If only header-auth API proof
passes but normal browser review remains blocked, the gap must remain open or be
split into a narrower browser-handoff gap.
