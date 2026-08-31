# Infrastructure Checklist: Feature 221 migration repair

**Purpose**: Reviewer-owned gate for Dev database repair, backup/restore and
runtime boundary safety.
**Feature**: [spec.md](../spec.md)

Implementation agents MUST NOT mark these items complete. The reviewer records
the evidence and checkbox state after inspecting the actual run.

## Boundary and authorization

- [ ] Target is explicitly local Dev or isolated Dev; production compose,
      credentials, endpoints and volumes are rejected.
- [ ] The repair decision names owner, reviewer, reason, affected boundary,
      target SHA, rollback target and abort conditions.
- [ ] No `alembic stamp`, manual `alembic_version` edit, `down -v`, volume
      deletion or guessed reverse SQL is used.

## Backup and restore

- [ ] Backup is created before mutation and identified by a digest and size,
      without storing rows or user content in evidence.
- [ ] Restore rehearsal succeeds on a separate isolated target.
- [ ] Source and restored schema/object fingerprints match, or the mismatch is
      explicitly blocked and reviewed.
- [ ] Restore failure leaves the source untouched and preserves recoverable
      backup evidence.

## Migration and runtime

- [ ] Expected code head and target `alembic current` are recorded and equal.
- [ ] Two consecutive `upgrade head` runs are successful and the second is a
      no-op.
- [ ] Failed upgrade/readiness restores the previous Dev state or leaves a
      blocked state with a valid backup.
- [ ] Backend readiness, representative API and component SHA equality pass
      before active-manifest publication.

## Evidence and closeout

- [ ] Evidence is atomic, metadata-only, exact-SHA bound and passes the secret/
      private-path scanner.
- [ ] Any changed SHA, interrupted command, unknown PID identity or failed
      stage invalidates the evidence.
- [ ] Quickstart, focused tests, fast lane and issue/PR links are attached.
- [ ] Production migration/CD is explicitly recorded as not run.
