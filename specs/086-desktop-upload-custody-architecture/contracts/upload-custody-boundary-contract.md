# Upload Custody Boundary Contract

This contract defines what future refactor PRs must preserve. It is not a new
runtime API.

## Flow Contract

| Stage | Owner | Must Preserve |
|-------|-------|---------------|
| Local package discovery | Desktop | Completed package identity, manifest truth, upload eligibility checks |
| Queue persistence | Desktop | Existing queue document compatibility and retry/support/local-purge state |
| Upload transport | Desktop + server | Idempotency keys, upload session lifecycle, missing-range retry, finalize semantics |
| Server ingest truth | Server | Meeting/session/media revision status vocabulary and reconciliation response shape |
| Custody projection | Desktop | User-facing custody state, safe support report inputs, local purge state |
| Local purge acknowledgement | Server + desktop | Metadata-only verification and deletion report state updates |
| Support incident reporting | Desktop + server | Safe schema, redaction, rate-limit/idempotency behavior, no private content |

## Refactor Requirements

- A future PR must name exactly which stage it touches.
- A future PR must list all DTOs or persisted fields it moves.
- A future PR must prove no behavior change or explicitly open a separate spec.
- A future PR must include a rollback/stop condition.

## Non-Negotiable Boundaries

- Desktop does not send audio directly to MediaScribe.
- Desktop does not store MediaScribe credentials.
- Support reports remain metadata-only.
- Local purge acknowledgement does not include raw local paths or content.
- Deletion copy remains truthful about what 2brain Rec controls.
