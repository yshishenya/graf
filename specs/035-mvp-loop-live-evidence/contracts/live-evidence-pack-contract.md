# Contract: Live Evidence Pack

Feature: `035-mvp-loop-live-evidence`

## Required Sections

The evidence pack must include:

1. `README.md` with scope, evidence boundary, and strongest claim.
2. `validation-log.md` with commands/manual flows, dates, results, and
   limitations.
3. `readiness-report.json` and `readiness-report.md`.
4. `launch-gap-register.md`.
5. `clean-room-reference.md`.
6. `screenshots/` with only metadata-safe images.

## Desktop Evidence Requirements

- Runtime path must be `/Applications/2brain Rec.app`.
- Evidence must include active, paused, resumed, stopped/list, and current idle
  or ready states unless blocked.
- Latest local artifact validation must be recorded.
- Manifest spot-check must describe metadata only: status, tracks,
  meeting-mute-truth decision, privacy segments, and scan result.

## Web Evidence Requirements

- Evidence must identify whether it is live metadata-safe or fixture-backed.
- Meeting list/detail/governance states must be represented.
- Notes/action output must be ready, blocked, or deferred with truthful copy.

## Forbidden Content

The pack must not contain raw audio, transcript text, private meeting content,
private account identifiers, private emails, credentials, tokens, signed URLs,
provider payloads, or private reference screenshots.
