# Implementation Plan: Backend Tenant Isolation RLS Hardening

**Branch**: `031-rls-hardening` | **Date**: 2026-06-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/031-rls-hardening/spec.md`

**Note**: This plan is the `$speckit-plan` output for the backend tenant
isolation hardening slice.

## Summary

Add PostgreSQL row-level security as a database-enforced second line of
defense for all accepted tenant-owned backend tables from ingest, auth,
sessions, devices, meetings, processing, transcripts, audit, and lifecycle
dependencies. The implementation will set explicit tenant context on backend
database sessions, add RLS policies and validation probes, preserve accepted
same-tenant ingest/auth/processing behavior, and document a gated rollout that
does not automatically enable live production enforcement.

## Technical Context

**Language/Version**: Python >=3.13 for server code; SQLAlchemy 2 async;
Alembic migrations; PostgreSQL for production RLS. Existing Swift/macOS code
remains untouched.

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic,
asyncpg, structlog/redaction helpers, existing MinIO/Temporal/MediaScribe
server modules only as protected data owners.

**Storage**: PostgreSQL is the enforcement target for tenant-owned backend
tables. SQLite remains a local/unit-test fallback and cannot prove RLS.

**Testing**: `uv run --extra dev pytest -q` for existing server tests; Ruff;
PostgreSQL-specific RLS migration/probe tests using an explicit test database;
`./infra/scripts/ci-local.sh` for full local regression; metadata-only
secret/content scans.

**Target Platform**: 2brain Rec server containers on `2brain.dev` /
`rec.2brain.dev`, with local and production-like validation before any
separate production enforcement decision.

**Project Type**: Backend web service plus worker/orchestration data access
modules.

**Performance Goals**: Tenant context setup adds no user-visible workflow step;
same-tenant API and worker validation remains green under existing local test
timeouts; RLS probe suites run deterministically without live customer data.

**Constraints**: No dashboard, share, download, retention, deletion execution,
admin UI, product RBAC bypass, desktop capture/upload behavior, MediaScribe
behavior change, or live production enforcement is authorized by this slice.
Logs, traces, diagnostics, and validation evidence remain metadata-only.

**Scale/Scope**: Current accepted backend schema only: identity/auth/session/
device, ingest/upload/artifact, meeting, processing/workflow/MediaScribe
result, transcript/diarization, audit, and dependency/lifecycle tables. Future
tenant-owned tables must declare an isolation contract before implementation.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Backend-only data isolation; macOS capture, routing, recording controls, and upload behavior are untouched. |
| Visible consent and user control | PASS | No recording start/stop behavior, auto-start behavior, or capture visibility setting changes. |
| Data boundary and secret discipline | PASS | RLS strengthens owner-controlled data boundaries and requires metadata-only diagnostics with no transcript, audio, credential, token, signed URL, password, or live secret path leakage. |
| Deletion truth and lifecycle accounting | PASS | The slice protects lifecycle/dependency rows and documents compensating controls for future deletion/retention work without promising deletion execution. |
| Spec-driven delivery with gates | PASS | Spec and five clarifications are complete; plan, checklist, tasks, analyze, issue sync, and implementation validation remain required. |
| Product/platform constraints | PASS | Uses selected Docker/Postgres backend stack; no UI/brand-distance or macOS platform scope is introduced. |

## Project Structure

### Documentation (this feature)

```text
specs/031-rls-hardening/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── access-outcomes.md
│   ├── rls-policy-matrix.md
│   └── tenant-context.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── pyproject.toml
├── src/twobrain_rec_server/
│   ├── api/
│   │   ├── problems.py
│   │   └── schemas.py
│   ├── auth/
│   │   ├── context.py
│   │   └── dependencies.py
│   ├── db/
│   │   ├── migrations/versions/
│   │   ├── models/
│   │   └── session.py
│   ├── ingest/
│   ├── processing/
│   └── observability/
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

infra/
├── docker-compose.dev.yml
├── docker-compose.yml
└── scripts/
```

**Structure Decision**: Extend the existing `apps/server` backend. Add a
tenant-context database helper near `apps/server/src/twobrain_rec_server/db/`
and wire request/worker code through existing auth context objects. Add an
Alembic revision after `0004_mediascribe_processing` for RLS functions,
policies, and rollback. Add PostgreSQL-only RLS probe tests plus ordinary
contract/unit tests for API access outcomes and metadata-only evidence.

## Phase 0 Research

Research output is captured in [research.md](./research.md).

Resolved decisions:

- Use PostgreSQL RLS policies with transaction-local session settings for
  tenant context, rather than relying only on ORM predicates.
- Use helper SQL functions around `current_setting(..., true)` to avoid
  casting failures and to keep policies readable.
- Classify tables into direct workspace, inherited workspace, organization,
  membership, identity-link, and maintenance-only access patterns.
- Keep operator maintenance context fixed and allowlisted, outside product UI,
  with metadata-only evidence.
- Keep SQLite tests for application behavior but require PostgreSQL probes for
  the RLS acceptance gate.
- Preserve the clarified API contract: cross-tenant reads are not found/empty,
  cross-tenant writes/deletes are authorization failures, and missing context
  is an auth/context failure.

## Phase 1 Design

Design artifacts created by this plan:

- [data-model.md](./data-model.md): tenant context, access outcome, hardening
  evidence, and table isolation classifications.
- [contracts/tenant-context.md](./contracts/tenant-context.md): request,
  worker, and maintenance context contract for database sessions.
- [contracts/rls-policy-matrix.md](./contracts/rls-policy-matrix.md): table
  coverage matrix and policy expectations for direct and inherited scopes.
- [contracts/access-outcomes.md](./contracts/access-outcomes.md): API-facing
  blocked-access result contract and validation evidence categories.
- [quickstart.md](./quickstart.md): local, PostgreSQL, production-like,
  rollback/halt, secret-scan, and out-of-scope validation scenarios.

## Post-Design Constitution Re-check

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Design is limited to server database isolation and does not change capture, local recording, or upload queue behavior. |
| Visible consent and user control | PASS | No recording automation or visibility behavior is introduced. |
| Data boundary and secret discipline | PASS | Contracts require RLS fail-closed behavior, metadata-only evidence, and content/secret redaction. |
| Deletion truth and lifecycle accounting | PASS | Protected dependency/lifecycle rows remain visible only through tenant or approved maintenance context; no deletion promise is broadened. |
| Spec-driven delivery with gates | PASS | Quickstart defines validation gates; tasks/analyze/implementation remain blocked until artifacts are complete. |
| Product/platform constraints | PASS | PostgreSQL is the production enforcement layer; live production enablement is a separate explicit operator decision. |

## Complexity Tracking

No constitution violations require complexity exceptions.
