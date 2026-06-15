# ADR 003: Tenant Isolation With PostgreSQL RLS

**Status**: Accepted

**Date**: 2026-06-15

## Context

2brain Rec now has tenant-owned backend rows for identity, auth sessions,
devices, meetings, uploads, artifacts, processing workflows, MediaScribe jobs,
transcripts, diarization, audit, and dependency state. Future product slices
will add dashboard review, sharing, downloads, retention, deletion, and admin
workflows on top of the same data.

Application-level checks remain required, but they are not enough as the number
of query paths grows. PostgreSQL row-level security provides a database-level
fail-closed boundary when a future query misses an application predicate.

## Decision

Use PostgreSQL RLS as the second line of defense for tenant-owned backend
tables. Every request, worker, and approved maintenance operation must set
explicit tenant context before touching tenant-owned rows.

Every new tenant-owned table must declare before merge:

- isolation class;
- owner column or parent relationship;
- allowed context kinds;
- read access outcome;
- mutation access outcome;
- metadata-only evidence behavior.

The current accepted context kinds are:

- `request` for user/API request scope;
- `worker` for processing workers and job activities;
- `auth_public`, `auth_callback_lookup`, and `auth_bootstrap` for bounded login
  bootstrap only;
- `maintenance` for fixed allowlisted operations outside product RBAC.

## Future Product Surfaces

Future feature `016-meeting-dashboard-review` must use this RLS contract for
meeting list/detail, transcript, notes, playback, and review queries.

Future feature `017-access-sharing-downloads` must use this RLS contract for
team visibility, share links, public pages, audio/transcript/summary download,
and access audit rows.

Future feature `018-retention-deletion-execution` must use this RLS contract
for retention jobs, deletion jobs, deletion verification reports, backup expiry
accounting, and dependency deletion truth.

## Consequences

- Product admins do not receive a broad tenant-isolation bypass setting.
- Operator maintenance remains allowlisted, metadata-logged, and outside
  product UI/RBAC.
- SQLite can test application behavior, but PostgreSQL probes are required for
  the RLS acceptance claim.
- Live production enforcement requires separate operator approval after local,
  PostgreSQL, and production-like gates pass.
