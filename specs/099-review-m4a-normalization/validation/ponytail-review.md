# Feature 099 Ponytail Review

**Date**: 2026-07-14
**Task**: T106

## Decision

The final implementation diff was reviewed against
`docs/agent-guidance/ponytail-upstream.md` after tracing the accepted-source,
normalization, publication, deletion, rollback and operator-recovery paths.
The high-risk Spec Kit lane and its validation gates remain unchanged.

## Simplification results

- No new Python, Swift or JavaScript runtime dependency was added. Media work
  uses the packaged FFmpeg capability; coordination reuses SQLAlchemy,
  PostgreSQL row locks, the existing MinIO adapter and the existing Temporal
  boundary.
- The implementation reuses accepted `MediaRevision`/`TrackArtifact` custody,
  the existing cabinet projection, tenant context, deletion report and audit
  helpers instead of creating a second upload, playback or repair subsystem.
- One shared meeting lock serializes upload/publication with deletion. The
  immutable attempt key and existing cleanup worker are reused for late-object
  reconciliation.
- `rec-maintenance` and `rec-reprocess-maintenance` remain separate explicit
  operations-profile services. Combining them would give routine smoke cleanup
  an unnecessary MediaScribe credential; the small Compose duplication is an
  intentional secret-boundary decision, not a reusable abstraction gap.
- Runtime-role bootstrap and identity verification remain small standalone
  scripts using the already-installed database clients. No role framework or
  generic privilege DSL was introduced.

## Intentional bounded debt

An ambiguous deleted attempt whose object is still absent retains one durable
`cleaned_at IS NULL` tombstone and is checked in round-robin order without a
TTL. This is the smallest storage-independent solution that closes the
MinIO-response-loss race. The adjacent `ponytail:` comment records the ceiling
and the upgrade path to an object-store conditional-write tombstone if the
queue becomes operationally material. A time cutoff is intentionally rejected
because it can strand a late media object after deletion.

## Evidence

- Independent DB/deploy review: no remaining findings; raw rollback leaves
  zero runtime roles and the legacy API login is denied.
- Independent lifecycle review: no remaining findings; exact response-loss
  harness and a synthetic 365-day late arrival both converge to object removal.
- Focused Ruff, shell syntax, Compose rendering, PostgreSQL 17/RLS and lifecycle
  tests passed after the final simplification decisions.
- `git diff --check`: pass.

The repository-wide CI result is recorded separately by T108 after the last
code-affecting change.

## 2026-07-17 startup-recovery hotfix review

Lean already. Ship.

- The hotfix reuses the existing durable retry transition, audit, lease and
  Temporal dispatch path; it adds no dependency, schema, endpoint, worker or
  configuration surface.
- The sole startup-only selector is necessary to distinguish the durable
  `worker_interrupted` reason from ordinary retry reasons. Folding it into the
  periodic reconciler would weaken backoff and be a product regression.
- One integration regression covers both the allowed immediate recovery and the
  required non-preemption case. Full local CI passed; production proof remains
  the intentionally separate T120 gate.
