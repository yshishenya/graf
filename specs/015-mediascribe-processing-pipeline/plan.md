# Implementation Plan: MediaScribe Processing Pipeline

**Branch**: `015-mediascribe-processing-pipeline` | **Date**: 2026-06-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/015-mediascribe-processing-pipeline/spec.md`

**Note**: This plan is the `$speckit-plan` output for the server-side MediaScribe processing slice.

## Summary

Implement the first durable processing stage after accepted ingest. The server
will pick up finalized `012` meetings, start an idempotent Temporal workflow,
submit dual-track artifacts to MediaScribe from server-controlled storage, poll
job state, import transcript and diarization results, expose content-safe
processing status, and record lifecycle/deletion dependency truth. No macOS
capture/upload behavior, dashboard UI, share/download surface, notes generation,
or deletion execution is part of this slice.

## Technical Context

**Language/Version**: Python >=3.13 for server code; SQLAlchemy/Alembic for
schema; existing Swift/macOS packages remain untouched.

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic,
MinIO Python SDK, HTTPX for MediaScribe HTTP calls, Temporal Python SDK for
durable workflows, structlog/redaction helpers.

**Storage**: Postgres for processing workflow/job/result/segment/audit state;
MinIO for already-ingested audio artifacts; optional future result archive
objects remain owner-controlled.

**Testing**: `uv run --extra dev pytest -q` for server contract/unit/integration
tests; Ruff for lint; Docker Compose config checks for processing dependencies;
secret/content scans for evidence.

**Target Platform**: 2brain Rec server containers on `2brain.dev` /
`rec.2brain.dev`; local development may run with fake Temporal and fake
MediaScribe adapters when real dependencies are unavailable.

**Project Type**: Backend web service plus worker/orchestration modules.

**Performance Goals**: Pickup and status APIs respond in under 1 second in
local validation; processing import is linear in result segment count; duplicate
pickup is constant-time against persisted workflow/job state; polling does not
block request handling.

**Constraints**: Desktop never calls MediaScribe or stores MediaScribe
credentials; ingest readiness remains independent from processing readiness;
workflow identifiers contain no PII/secrets; logs/traces/status responses are
metadata-only; MediaScribe request body limit is treated as a blocking/degraded
processing condition; no dashboard/share/download/delete execution in `015`.

**Scale/Scope**: MVP path for finalized dual-track meetings with Russian/English
transcription and diarization. This slice prepares a single processing workflow
type and canonical status model; broader queue tuning, search, notes, exports,
partial deletion, and customer-scale worker autoscaling are later slices.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Feature consumes finalized server artifacts only and does not change macOS capture, routing, or recording controls. |
| Visible consent and user control | PASS | No new capture start/stop behavior; processing starts after explicit recorded/uploaded artifact exists. |
| Data boundary and secret discipline | PASS | MediaScribe credentials stay server-side; desktop clients receive no dependency credentials or signed URLs; logs/status are metadata-only. |
| Deletion truth and lifecycle accounting | PASS | Plan adds MediaScribe workflow/job/result dependency state for future deletion accounting without promising deletion execution. |
| Spec-driven delivery with gates | PASS | Spec, clarify review, plan, checklists, tasks, analyze, and implementation validation are required before code completion. |
| Product/platform constraints | PASS | Server stays in Docker/Postgres/MinIO/Temporal/MediaScribe stack; UI brand-distance work is not touched. |

## Project Structure

### Documentation (this feature)

```text
specs/015-mediascribe-processing-pipeline/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── mediascribe-client-contract.md
│   ├── processing-status.openapi.yaml
│   ├── processing-lifecycle-events.md
│   └── temporal-workflow-contract.md
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
│   │   ├── health.py
│   │   ├── processing.py
│   │   └── schemas.py
│   ├── config.py
│   ├── db/
│   │   ├── migrations/versions/
│   │   └── models/
│   │       ├── meeting.py
│   │       └── processing.py
│   ├── domain/
│   │   └── statuses.py
│   ├── ingest/
│   │   └── processing_placeholder.py
│   ├── mediascribe/
│   │   ├── client.py
│   │   ├── import_results.py
│   │   └── schemas.py
│   ├── processing/
│   │   ├── audit.py
│   │   ├── lifecycle.py
│   │   ├── pickup.py
│   │   ├── status.py
│   │   ├── submit.py
│   │   └── store.py
│   ├── storage/
│   │   └── minio_client.py
│   └── workflows/
│       ├── processing_workflow.py
│       ├── temporal_client.py
│       └── worker.py
└── tests/
    ├── contract/
    ├── fakes/
    ├── integration/
    └── unit/

infra/
├── docker-compose.dev.yml
├── docker-compose.yml
└── env/rec.production.env.example
```

**Structure Decision**: Extend the existing `apps/server` FastAPI backend with
separate `processing`, `mediascribe`, and `workflows` modules. Keep MediaScribe
HTTP calls outside API handlers and outside Temporal workflow definitions;
non-deterministic I/O belongs in activities/adapters, with submission activity
logic in `apps/server/src/twobrain_rec_server/processing/submit.py`. Add
Postgres migrations for durable processing state, keep MinIO object access
server-side, and add Temporal/processing worker services to the Compose
definitions without exposing live secrets.

## Phase 0 Research

Research output is captured in [research.md](./research.md).

Resolved decisions:

- Use Temporal workflow identity `processing/<meeting_id>` with no user/title
  PII and reject/return existing workflows for duplicate starts.
- Put MediaScribe HTTP calls, MinIO reads, and Postgres writes in activities or
  service adapters, not deterministic workflow orchestration code.
- Use HTTPX with explicit timeout settings and application-level retry mapping;
  HTTPX transport retries alone only cover connection failures.
- Do not use FastAPI `BackgroundTasks` as the durable processing mechanism;
  it is request-lifecycle background work, not restart-safe orchestration.
- Treat MediaScribe missing/unavailable as processing-blocked, not ingest
  failure.
- Store transcript text only in controlled result tables/stores, never in logs,
  status responses, diagnostics, or default external observability.

## Phase 1 Design

Design artifacts created by this plan:

- [data-model.md](./data-model.md): processing workflows, MediaScribe jobs,
  result envelopes, transcript/diarization segments, audit events, and deletion
  dependency records.
- [contracts/temporal-workflow-contract.md](./contracts/temporal-workflow-contract.md):
  workflow identity, inputs, activities, retry semantics, and safe metadata.
- [contracts/mediascribe-client-contract.md](./contracts/mediascribe-client-contract.md):
  request/response mapping, credentials, result import, and failure handling.
- [contracts/processing-status.openapi.yaml](./contracts/processing-status.openapi.yaml):
  content-safe status endpoints for future clients.
- [contracts/processing-lifecycle-events.md](./contracts/processing-lifecycle-events.md):
  metadata-only audit/status event vocabulary.
- [quickstart.md](./quickstart.md): validation scenarios for happy path,
  duplicate pickup, fake MediaScribe result import, dependency outage,
  tenant denial, readiness, secret/content scans, and out-of-scope boundaries.

## Post-Design Constitution Re-check

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Design is backend-only and does not alter local capture packages or macOS routes. |
| Visible consent and user control | PASS | Processing acts only on finalized uploaded recordings; no hidden capture trigger is introduced. |
| Data boundary and secret discipline | PASS | Contracts require server-only MediaScribe credentials, safe workflow IDs, content-safe status, and redacted logs. |
| Deletion truth and lifecycle accounting | PASS | Data model includes processing dependency records for MediaScribe jobs/results and workflow payload accounting. |
| Spec-driven delivery with gates | PASS | Quickstart and contracts define validation gates before implementation can be accepted. |
| Product/platform constraints | PASS | Temporal and MediaScribe are used as selected MVP dependencies; UI brand work remains out of scope. |

## Complexity Tracking

No constitution violations require complexity exceptions.
