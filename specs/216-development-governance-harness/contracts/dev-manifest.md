# Contract: Single Dev Manifest

## Operations

```text
build   --sha <exact-sha> [--dry-run]
promote --manifest <path> [--dry-run]
status  [--json]
smoke   [--json]
rollback [--manifest-id <id>] [--dry-run]
reset-data --confirm-dev-reset [--dry-run]
```

## Promotion rules

- A lock serializes promotion and rollback.
- The candidate is validated before activation.
- Backend, frontend, worker and Dev app must reference the same exact SHA.
- The active pointer changes atomically; failed activation leaves the previous
  manifest active.
- Production endpoints, production credentials and production data are
  rejected by configuration and path checks.

## macOS app rules

- Destination is exactly `/Applications/GRAF Dev.app`.
- Bundle ID is `pro.2brain.graf.dev` and channel is `dev`.
- Candidate and existing app must have the same designated requirement before
  replacement.
- Replacement is staged and atomic; failure restores the previous app.
- Public Developer ID/notarization remains a separate release gate.

## Status values

`ready`, `promoting`, `active`, `degraded`, `rollback_required`, `blocked`.
Status must include the active manifest ID, exact SHA and actionable reason.
