# Implementation Plan: Production Deployment Plan

**Branch**: `021-production-deployment-plan` | **Date**: 2026-06-04 | **Spec**: `specs/021-production-deployment-plan/spec.md`

**Input**: Feature specification from `specs/021-production-deployment-plan/spec.md`

## Summary

Make the 2brain Rec production deployment path executable up to the `infra_smoke_ready` verdict. This slice hardens the existing Rec-owned Docker Compose stack, secret/env validation, migration/backup/rollback workflow, smoke identity/device setup, first production smoke, cleanup, and evidence capture for `https://rec.2brain.pro`. It intentionally stops at the accepted `012` ingest boundary: no federated auth implementation, desktop uploader implementation, MediaScribe processing, Temporal workflow starts, dashboard readiness, sharing, retention, deletion execution, or driver packaging.

## Technical Context

**Language/Version**: Python 3.13 for server scripts/tests; Docker Compose for runtime orchestration; shell scripts for operator runbook commands where appropriate.

**Primary Dependencies**: Existing FastAPI/Pydantic/SQLAlchemy/Alembic/MinIO stack from `apps/server`; Docker Compose; Postgres 17; MinIO; existing artifact helper scripts; pytest for validation.

**Storage**: Dedicated Rec-owned Postgres and MinIO Docker volumes. Evidence summaries live under `docs/deployments/2brain-rec/`; live secrets and raw production logs are never committed.

**Testing**: Compose config rendering; pytest for server/config/runbook helpers; dry-run backup/restore/rollback rehearsal tests; production-smoke helper validation against local or production-like stack; secret/log redaction scans.

**Target Platform**: Self-hosted Linux host in 2brain-controlled infrastructure with public endpoint `https://rec.2brain.pro`, backed by isolated Rec Docker Compose services.

**Project Type**: Backend infrastructure and operations readiness slice.

**Performance Goals**: First smoke must validate a small non-sensitive artifact only. The deployment remains compatible with `012` limits for 30/60 minute artifacts but does not need to prove high-throughput production scale in this slice.

**Constraints**: Public `rec.2brain.pro` may be reachable during smoke, but successful `021` evidence can only claim `infra_smoke_ready`; Docker secrets plus env templates are the secret source; restore/rollback rehearsal is a blocking gate; smoke artifacts must be cleaned up or truthfully recorded; MediaScribe/Langfuse checks are degraded-awareness only and must not create content egress.

**Scale/Scope**: Internal MVP infra smoke for the Rec-owned stack. User rollout, internal pilot, transcription, dashboard review, retention, deletion execution, desktop upload queue, and real auth remain future feature slices.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Reason |
|------|--------|--------|
| Driver-first macOS MVP | PASS | 021 does not add capture paths or no-driver fallback; it validates server deployment after accepted local artifacts exist. |
| Visible capture and one-action stop | PASS | First smoke uses synthetic/non-sensitive artifacts and does not start, stop, hide, or automate desktop capture. |
| Owner-controlled storage and egress | PASS | Rec-owned Postgres/MinIO remain isolated; MediaScribe/Langfuse are degraded-awareness dependencies only; no desktop-held secrets or direct object URLs are introduced. |
| MediaScribe and Langfuse boundaries | PASS | 021 records config/health awareness without MediaScribe jobs, Langfuse content traces, Temporal workflow starts, or content egress. |
| Deletion truthfulness | PASS | Smoke artifact cleanup and residue evidence are required; rollout wording is limited to `infra_smoke_ready`. |
| Security/privacy gates | PASS | Docker secrets/env templates, fail-closed production config, public endpoint truth, log redaction, and smoke identity boundaries are explicit gates. |
| Spec Kit flow | PASS | Specify and two clarify passes are complete; this plan creates research, data model, contracts, quickstart, and updates agent context. |
| Deployment gates | PASS | Docker secrets, health checks, backups, restore rehearsal, rollback, log redaction, disk-full behavior, and smoke evidence are first-class requirements. |

No constitution violations are required for this feature.

## Project Structure

### Documentation (this feature)

```text
specs/021-production-deployment-plan/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── deployment-readiness-contract.md
│   ├── smoke-evidence-contract.md
│   └── secrets-env-contract.md
└── tasks.md                       # Created by $speckit-tasks, not this command

docs/deployments/2brain-rec/
└── <deployment evidence summaries> # Created during implementation/smoke runs
```

### Source Code (repository root)

```text
apps/server/
├── src/twobrain_rec_server/
│   ├── config.py                   # Production fail-closed config validation
│   ├── api/health.py               # Liveness/readiness surfaces
│   ├── auth/                       # Smoke identity/device boundary hooks
│   └── observability/              # Log redaction and safe metadata
├── scripts/
│   ├── create_test_artifact.py
│   ├── seed_dev_identity.py        # Must not be reused as production smoke identity
│   ├── upload_test_artifact.py
│   └── <021 smoke/runbook helpers>
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

infra/
├── docker-compose.yml              # Production Rec-owned stack
├── docker-compose.dev.yml          # Local validation stack
├── server/Dockerfile
└── <021 deployment templates/scripts>
```

**Structure Decision**: Keep 021 in the existing backend/infra layout from 012. Add only narrowly scoped deployment helpers, templates, tests, and evidence-summary docs. Do not introduce a separate operations app or new service layer.

## Phase 0 Research

Research output is captured in `specs/021-production-deployment-plan/research.md`.

Resolved decisions:

- Keep the first smoke scoped to the accepted `012` ingest boundary.
- Treat `rec.2brain.pro` public reachability as separate from user rollout readiness.
- Use Docker secrets plus env templates as the production secret source.
- Require production-like restore/rollback rehearsal before `infra_smoke_ready`.
- Use a dedicated internal smoke identity/device, not real users and not local dev seed credentials.
- Store committed evidence summaries under `docs/deployments/2brain-rec/` while excluding live secrets, raw logs, and raw meeting artifacts.

## Phase 1 Design

Design artifacts created by this plan:

- `data-model.md`: deployment environment, service layout, secret policy, persistent volume, migration runbook, smoke identity/device, smoke test record, cleanup record, rollback decision, degraded-awareness status, readiness verdict.
- `contracts/deployment-readiness-contract.md`: allowed readiness states, blocking gates, and endpoint exposure rules.
- `contracts/smoke-evidence-contract.md`: required safe evidence fields and forbidden evidence content.
- `contracts/secrets-env-contract.md`: Docker secret/env template contract and production fail-closed rules.
- `quickstart.md`: local and production-like validation sequence for compose config, secret validation, backup/migration/restore rehearsal, first smoke, cleanup, evidence, and final verdict.

## Post-Design Constitution Re-check

| Gate | Status | Reason |
|------|--------|--------|
| Driver-first macOS MVP | PASS | Contracts do not change capture or driver behavior. |
| Visible capture and one-action stop | PASS | Smoke uses synthetic/non-sensitive artifacts and does not claim capture readiness. |
| Owner-controlled storage and egress | PASS | Contracts preserve Rec-owned Postgres/MinIO and no direct object-storage or MediaScribe desktop egress. |
| MediaScribe and Langfuse boundaries | PASS | Degraded-awareness contract forbids job creation, content traces, and content egress during 012 smoke. |
| Deletion truthfulness | PASS | Smoke cleanup/residue accounting is explicit and `infra_smoke_ready` wording prevents overstated rollout claims. |
| Security/privacy gates | PASS | Secret, evidence, log redaction, public endpoint, and smoke identity contracts are measurable. |
| Spec Kit flow | PASS | Planning artifacts are ready for checklist/tasks/analyze. |
| Deployment gates | PASS | Backup, restore, rollback, health, log redaction, and disk-full behavior are represented in plan/design. |

No constitution violations are introduced by the design artifacts.

## Complexity Tracking

No constitution violations or unnecessary extra project layers are introduced.

## Product Acceptance Metrics

- 100% of production compose validation scenarios fail closed when required secrets are missing or dev defaults are used.
- 100% of first-smoke evidence records include public endpoint state, migration version, backup reference, restore/rollback rehearsal result, smoke identity/device class, cleanup status, degraded-awareness status, and final verdict.
- 100% of successful 021 runs use `infra_smoke_ready` as the highest readiness verdict and reject `production_ready`, `user_rollout_ready`, and `internal_user_pilot_ready`.
- 0 MediaScribe jobs, 0 Temporal workflow starts, 0 notes jobs, 0 retention jobs, 0 deletion jobs, and 0 content-bearing Langfuse traces are created by 021 smoke.
- 0 live secrets, raw logs, raw audio, transcript text, bearer tokens, MinIO credentials, MediaScribe credentials, Langfuse credentials, or signed URLs are committed to evidence.

## Story Slice Map

| Story | Implementation slice |
|-------|----------------------|
| US1 Operator can prepare the production stack | Compose hardening, secret/env templates, service layout, public/private exposure checks. |
| US2 Operator can run migration and backup safely | Backup-before-migration commands, restore rehearsal, rollback decision evidence. |
| US3 Operator can perform first production smoke | Smoke identity/device setup, small-artifact upload, readiness/log checks, degraded-awareness record. |
| US4 Operator can roll back or halt rollout | Rollback/halt criteria, cleanup/residue accounting, final verdict contract. |
