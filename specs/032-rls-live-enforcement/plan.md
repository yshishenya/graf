# Implementation Plan: RLS Production Enforcement Truth

**Branch**: `codex/032-rls-live-enforcement` | **Date**: 2026-06-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/032-rls-live-enforcement/spec.md`

**Note**: This plan is the `$speckit-plan` output for correcting the `031`
RLS rollout truth gap after production inspection showed RLS is already enabled
and forced on covered production tables.

## Summary

Feature `031-rls-hardening` added and deployed PostgreSQL RLS policies. Live
production inspection now shows the production Rec stack is at Alembic
`0005_rls_hardening (head)` and every covered tenant-owned table has RLS
enabled and forced. This slice adds a safe, repeatable production truth check,
keeps destructive probes on disposable/test databases, updates stale `031`
"not changed" wording, and records metadata-only evidence so future dashboard,
access, retention, and deletion work knows the real production boundary.

## Technical Context

**Language/Version**: Python >=3.13 for server tooling and tests; POSIX shell
for deployment helper scripts; SQL for PostgreSQL system-catalog inspection.

**Primary Dependencies**: Existing FastAPI server package, SQLAlchemy 2 async,
Alembic, asyncpg, pytest, Ruff, existing deployment scripts, and existing
redaction/evidence helpers.

**Storage**: PostgreSQL production database `twobrain_rec` is inspected only
through read-only metadata queries. Disposable/test PostgreSQL databases remain
the only place where migrations, seed rows, and destructive same/cross-tenant
RLS probes may run.

**Testing**: `uv run --extra dev pytest -q` for focused server tests; Ruff;
`./infra/scripts/ci-local.sh`; direct local invocation of RLS validation helper
without `RLS_TEST_DATABASE_URL`; disposable PostgreSQL probe path when
available; remote read-only production metadata inspection.

**Target Platform**: 2brain Rec server containers on `2brain.dev` /
`rec.2brain.pro`, with remote deployment path `/opt/projects/2brain-rec`.

**Project Type**: Backend operational validation and documentation hardening
slice.

**Performance Goals**: Production RLS state inspection reads only PostgreSQL
catalog metadata and finishes in a normal operator command window; no live
customer rows are scanned or mutated.

**Constraints**: Do not run destructive RLS probes on the live production
`twobrain_rec` database. Do not expose transcript text, raw audio, object keys,
tokens, signed URLs, passwords, live secret paths, or customer meeting content.
Do not add dashboard, sharing, deletion execution, desktop upload,
MediaScribe behavior, product admin bypass, or customer settings.

**Scale/Scope**: Current accepted `031` tenant-owned table set only. Future
tenant-owned tables must continue to follow ADR `003-tenant-isolation-rls`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Backend-only production metadata verification; no macOS capture, routing, recording, or upload behavior changes. |
| Visible consent and user control | PASS | No recording start/stop, assisted auto-start, or capture visibility behavior is changed. |
| Data boundary and secret discipline | PASS | Strengthens truthful production tenant-boundary evidence and keeps production checks metadata-only. |
| Deletion truth and lifecycle accounting | PASS | Corrects lifecycle/status truth for future dashboard/access/retention/deletion work without adding deletion execution. |
| Spec-driven delivery with gates | PASS | Specify and clarify are complete; plan, checklist, tasks, analyze, issue sync, and implementation validation remain required. |
| Product/platform constraints | PASS | Uses existing Docker/PostgreSQL production stack and does not add UI, product bypass, or new external egress. |

## Project Structure

### Documentation (this feature)

```text
specs/032-rls-live-enforcement/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── production-rls-state.md
│   ├── rls-validation-output.md
│   └── rollout-truth-remediation.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── scripts/
│   └── verify_rls_hardening.py
├── src/twobrain_rec_server/db/
│   ├── migrations/versions/0005_rls_hardening.py
│   └── rls_validation.py
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

docs/
├── adr/003-tenant-isolation-rls.md
├── current-product-status.md
└── deployments/2brain-rec/rls-hardening-runbook.md

infra/scripts/
├── ci-local.sh
└── verify-rec-migration.sh
```

**Structure Decision**: Extend the existing RLS validation script/module and
contract tests instead of creating a separate deployment subsystem. The
production check belongs near `apps/server/scripts/verify_rls_hardening.py`
because it already owns RLS validation output, while docs updates belong in
the existing deployment runbook, ADR, product status, and changelog surfaces.

## Phase 0 Research

Research output is captured in [research.md](./research.md).

Resolved decisions:

- Use read-only PostgreSQL catalog inspection for production RLS truth.
- Keep destructive direct SQL RLS probes on disposable/test databases only.
- Share or derive the covered table inventory from the existing `031`
  migration/policy source to prevent table-list drift.
- Replace blanket `live_production_enforcement=not_changed` wording with
  environment-specific output that distinguishes test probes from production
  read-only verification.
- Correct stale `031` docs/status while preserving the historical fact that
  destructive production probes remain forbidden.

## Phase 1 Design

Design artifacts created by this plan:

- [data-model.md](./data-model.md): production truth verdict, table-state
  evidence, test-gate evidence, and stale-language remediation entities.
- [contracts/production-rls-state.md](./contracts/production-rls-state.md):
  read-only production table-state contract.
- [contracts/rls-validation-output.md](./contracts/rls-validation-output.md):
  validation output states for test/disposable and production read-only paths.
- [contracts/rollout-truth-remediation.md](./contracts/rollout-truth-remediation.md):
  required doc/status/changelog correction contract.
- [quickstart.md](./quickstart.md): validation and evidence commands for local,
  disposable database, production read-only inspection, stale-language scan,
  and content/secret scan.

## Post-Design Constitution Re-check

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Design only inspects backend metadata and updates backend/docs truth. |
| Visible consent and user control | PASS | No capture or user-control behavior changes. |
| Data boundary and secret discipline | PASS | Production inspection is catalog-only and evidence remains metadata-only. |
| Deletion truth and lifecycle accounting | PASS | Corrects lifecycle/dependency truth for future deletion and retention specs. |
| Spec-driven delivery with gates | PASS | Quickstart defines validation gates and tasks/analyze/implementation remain required. |
| Product/platform constraints | PASS | Uses existing PostgreSQL/Docker deployment stack and avoids product UI or broad admin bypass. |

## Complexity Tracking

No constitution violations require complexity exceptions.
