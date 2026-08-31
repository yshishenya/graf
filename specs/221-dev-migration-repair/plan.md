# Implementation Plan: Безопасный repair локальной Dev migration state

**Branch**: `codex/221-dev-migration-repair`
**Date**: 2026-08-31
**Spec**: [spec.md](spec.md)
**Umbrella issue**: [#6146](https://github.com/yshishenya/graf/issues/6146)

## Risk and validation lane

`high-risk product area / infrastructure`: работа затрагивает Postgres,
Alembic, backup/restore и Dev deployment boundary. Обязательны clarify,
reviewer-owned infra checklist, analyze без CRITICAL/HIGH, quickstart и fast
CI. Production migration и destructive volume operations запрещены.

## Architecture

Repair оформляется как metadata-first pipeline:

```text
read-only probe → isolated backup/restore → repair decision → approved Dev repair
→ idempotent upgrade → component readiness → metadata-only evidence
```

Probe and evidence commands are thin adapters over existing Compose/Alembic
scripts. They must accept explicit paths and environment names, reject
production-looking boundaries, and write atomically. No second database or
parallel migration framework is introduced.

## Safety invariants

- Existing volume is read-only until a reviewer-approved decision exists.
- Every mutation has a recoverable backup digest and a named rollback target.
- `alembic current` equals the code head after repair; a second upgrade is a
  no-op.
- Active Dev manifest, backend, frontend, worker and app report one exact SHA.
- Any changed SHA, unknown process identity, failed readiness or production
  origin invalidates evidence and blocks publication.

## Phases

### Phase 0 — Evidence and decision

Implement the read-only probe, schema/graph inventory, boundary checks and
machine-readable repair decision/evidence contracts. Run them against a copied
or temporary database only.

### Phase 1 — Isolated rehearsal

Create a backup of the isolated copy, restore it into a second isolated target,
compare metadata fingerprints, and rehearse forward upgrade and rollback. No
existing user volume is changed.

### Phase 2 — Approved Dev repair

After reviewer approval, run the idempotent repair against the named Dev target,
verify `current == expected_head`, backend/API readiness, and exact component
identity. On failure restore the verified backup or leave an explicit blocked
state.

### Phase 3 — Closeout

Attach evidence to issue #6146, run `speckit-converge`, targeted governance
checks and `infra/scripts/ci-local.sh --fast`. Full CI is reserved for a frozen
release candidate; no product release or production deploy is part of this
feature.

## Validation matrix

| Gate | Evidence | Blocking condition |
|---|---|---|
| Probe | revision/heads/graph/SHA JSON | user rows, unknown boundary, production target |
| Restore rehearsal | source/target digest and schema fingerprint | mismatch or failed restore |
| Repair decision | owner, approval, backup, rollback, abort rules | missing reviewer approval |
| Migration | current/head plus two upgrade results | drift, non-idempotency, partial failure |
| Runtime | health, representative API, component SHAs | stale/mismatched SHA or readiness failure |
| Closeout | issue/PR links, lane, command results | missing evidence or unresolved high finding |

## Rollback and recovery

Rollback is restore-based, never reverse SQL guessed from the diff. If restore
cannot be proven, stop with `blocked` and preserve the backup and evidence
identifiers for a reviewer. Production credentials, endpoints and volumes are
never accepted by the adapter.

## Dependencies

- Feature 216 one-manifest Dev harness and SHA-bound CI contracts.
- Feature 220 legacy inventory; legacy migration contours are linked, not
  silently removed here.
- Existing Docker Compose, Postgres and Alembic configuration.

## Complexity ceiling (Ponytail)

Reuse existing migration and harness commands; add only stdlib metadata
validators and a thin repair adapter. Do not add a migration service, ORM, or
new dependency. Upgrade path for higher throughput is a dedicated migration
runner only if the current single-operator boundary becomes a measured limit.
