# Implementation Plan: Server Ingest Foundation

**Branch**: `012-server-ingest-foundation-continuation` | **Date**: 2026-06-04 | **Spec**: `specs/012-server-ingest-foundation/spec.md`

**Input**: Feature specification from `specs/012-server-ingest-foundation/spec.md`

## Summary

Create the backend ingest foundation for finalized local 2brain Rec meeting artifacts. The slice accepts server-mediated uploads from trusted clients, validates dual-track artifact metadata and limits, persists ownership/status metadata in Postgres, stores audio objects in MinIO, and exposes truthful ingest/status contracts. It intentionally does not implement the macOS uploader, dashboard review UI, federated auth providers, direct object-storage upload URLs, Temporal workflow starts, or MediaScribe processing.

## Technical Context

**Language/Version**: Python 3.13 for the new server service. Existing macOS package remains Swift and is not modified by this feature.

**Primary Dependencies**: FastAPI, Pydantic v2 plus `pydantic-settings`, SQLAlchemy 2 async ORM, Alembic, asyncpg, MinIO Python SDK, structlog or standard JSON logging, pytest, pytest-asyncio, httpx.

**Storage**: Dedicated Postgres database for ingest metadata and audit events; dedicated MinIO bucket for server-owned audio/manifest objects. No desktop-held object-storage credentials and no direct object-storage upload URLs in 012.

**Testing**: pytest unit, contract, and integration tests under `apps/server/tests`; Docker Compose-backed smoke validation for Postgres and MinIO; content/secret leakage checks for logs and API responses.

**Target Platform**: Self-hosted Linux/Docker runtime and local Docker Compose development. Public deployment target remains the future `rec.2brain.dev` stack, but this plan creates the ingest service foundation only.

**Project Type**: Backend API service plus infrastructure scaffold.

**Performance Goals**: Reliably accept 30-minute and 60-minute dual-track artifact validation fixtures; support resumable/idempotent retries without duplicate finalized meetings; avoid loading full audio tracks into process memory.

**Constraints**: Driver-first macOS MVP remains untouched; visible capture semantics remain local/client-owned; backend upload strategy is `server_mediated`; Temporal and MediaScribe are not runtime dependencies for ingest success in this slice; Langfuse/diagnostics remain metadata-only; no raw audio, transcripts, secrets, signed URLs, or bearer tokens in logs.

**Scale/Scope**: Internal MVP foundation for small teams and self-hosted deployments. Default configurable ingest limits: 4 hour maximum meeting duration, 2.5 GiB per track, 5 GiB per complete recording package, 24 hour upload-session TTL. Deployment can tighten these values without code changes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Reason |
|------|--------|--------|
| Driver-first macOS MVP | PASS | 012 works only after local capture has produced an artifact; it does not add a no-driver capture fallback. |
| Visible capture and one-action stop | PASS | Server ingest does not start, stop, or hide recording; it preserves post-capture status truth for clients. |
| Owner-controlled storage and egress | PASS | Audio lands in owner-controlled MinIO through backend APIs; desktop clients never receive MediaScribe or object-storage credentials. |
| MediaScribe and Langfuse boundaries | PASS | 012 stores `not_submitted` / `pending_processing` placeholders and does not call MediaScribe, start Temporal workflows, or emit content traces. |
| Deletion truthfulness | PASS | Data model records storage locations and downstream placeholders so later deletion work can truthfully describe what is and is not erased. |
| Security/privacy gates | PASS | Tenant checks, audit metadata, no secret/content logging, explicit limits, and cross-tenant denial are planned as first-class validation scenarios. |
| Spec Kit flow | PASS | Specify, clarify, and requirements checklist are complete; this plan creates research, data model, contracts, quickstart, and updates agent context. |
| Docker self-hosting | PASS | Plan introduces Docker Compose infrastructure for API, Postgres, and MinIO. |

No constitution violations are required for this feature.

## Project Structure

### Documentation (this feature)

```text
specs/012-server-ingest-foundation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.yaml
│   └── desktop-ingest-status.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/
├── macos/
│   └── Package.swift                 # Existing; no 012 implementation changes expected
└── server/
    ├── pyproject.toml
    ├── alembic.ini
    ├── src/twobrain_rec_server/
    │   ├── main.py
    │   ├── config.py
    │   ├── api/
    │   ├── auth/
    │   ├── db/
    │   ├── domain/
    │   ├── ingest/
    │   ├── observability/
    │   └── storage/
    ├── scripts/
    └── tests/
        ├── contract/
        ├── integration/
        └── unit/

infra/
├── docker-compose.dev.yml
├── docker-compose.yml
└── server/
    └── Dockerfile
```

**Structure Decision**: Add a separate backend service under `apps/server` because the current repository only contains the macOS Swift package and documentation. Keep infrastructure under `infra/` so the server can be developed and validated without changing the macOS app in this feature.

## Phase 0 Research

Research output is captured in `specs/012-server-ingest-foundation/research.md`.

Resolved decisions:

- Use FastAPI/Pydantic for typed HTTP contracts and streaming file input.
- Use SQLAlchemy 2 async plus Alembic for Postgres metadata and migrations.
- Use MinIO Python SDK from the server only; no direct object upload URLs in 012.
- Enforce tenant isolation in the application layer in 012; track PostgreSQL RLS as `RLS-hardening` rather than silently dropping it.
- Do not include Temporal or MediaScribe runtime dependencies in 012 readiness. Processing workflow start belongs to 015.
- Default ingest limits are configurable and documented above.

## Phase 1 Design

Design artifacts created by this plan:

- `data-model.md`: Organizations, workspaces, devices, meetings, upload sessions, tracks, audit events, processing placeholders, and status transitions.
- `contracts/openapi.yaml`: API surface for meeting creation, server-mediated upload sessions, part upload, retry/status, finalize/abort, and health checks.
- `contracts/desktop-ingest-status.md`: Desktop-facing status vocabulary and truth rules.
- `quickstart.md`: Validation scenarios for happy path, retries, idempotency, cross-tenant denial, over-limit rejection, object persistence, no workflow starts, and content/secret leak checks.

## Post-Design Constitution Re-check

| Gate | Status | Reason |
|------|--------|--------|
| Driver-first macOS MVP | PASS | Contracts consume finalized artifact metadata only; no capture fallback introduced. |
| Visible capture and one-action stop | PASS | Status contract does not imply remote invisible capture. |
| Owner-controlled storage and egress | PASS | API contract exposes only backend ingest endpoints and keeps object storage credentials server-side. |
| MediaScribe and Langfuse boundaries | PASS | Contracts and quickstart explicitly assert no MediaScribe calls, no Temporal workflow starts, and metadata-only observability. |
| Deletion truthfulness | PASS | Data model includes lifecycle/audit placeholders and avoids universal erasure promises. |
| Security/privacy gates | PASS | Cross-tenant denial, idempotency, limits, audit, and leakage checks are validation requirements. |
| Spec Kit flow | PASS | Artifacts are present and ready for checklist/tasks/analyze. |
| Docker self-hosting | PASS | Planned source layout includes Docker Compose and Dockerfile paths. |

No constitution violations are introduced by the design artifacts.

## Complexity Tracking

No constitution violations or unnecessary extra project layers are introduced.

## Product Acceptance Metrics

- 100% of happy-path dual-track artifact uploads finalize with `ingested_pending_processing`.
- 100% of duplicate/retry requests are idempotent when checksums match and rejected when they conflict.
- 100% of cross-tenant/workspace/device access attempts are denied in contract and integration tests.
- 100% of over-limit artifacts return truthful non-success status and do not leave finalized objects.
- 0 Temporal workflows and 0 MediaScribe jobs are started by 012 validation scenarios.
- 0 raw audio, transcript text, bearer tokens, MinIO credentials, signed URLs, or secrets appear in logs/API error bodies.

## Story Slice Map

| Story | Implementation slice |
|-------|----------------------|
| US1 Backend receives finalized local recording artifact | Meeting creation, upload session creation, server-mediated part upload, finalize, object persistence. |
| US2 Desktop/client can resume or understand upload status | Session status, missing ranges, idempotency, abort/expired/degraded states. |
| US3 Operators can deploy and trust ingest readiness | Docker Compose, health checks, config validation, audit/logging constraints. |
| US4 Later processing can safely pick up ingested artifacts | Processing placeholders, object metadata, checksums, `ingested_pending_processing` boundary. |
