# Implementation Plan: MediaScribe v0.5.3 integration fidelity

**Branch**: `203-mediascribe-v053-integration` | **Date**: 2026-08-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/203-mediascribe-v053-integration/spec.md`

## Summary

Bring GRAF’s existing MediaScribe v1 adapter in line with release v0.5.3. Add a strict typed WordItem boundary, correct omitted single-track source-role semantics, retain validated per-block words in the existing result lineage, and prove that GRAF displays provider-owned diarization blocks without re-segmentation. Reuse Feature 195’s durable Temporal recovery and only change it if the v0.5.3 contract matrix exposes a real gap.

## Technical Context

**Language/Version**: Python 3.11+; existing vanilla JavaScript/Jinja2 cabinet surface

**Primary Dependencies**: Existing FastAPI/Pydantic, SQLAlchemy/PostgreSQL, Alembic, MinIO, httpx, temporalio Python SDK and current MediaScribe `/v1` server boundary

**Storage**: Existing PostgreSQL `processing_results`, `transcript_segments` and `diarization_segments`; additive nullable JSON column for validated words; existing owner-controlled storage and Temporal persistence

**Testing**: Existing pytest unit/contract/integration suites, MediaScribe fake transport, Temporal workflow replay/time-skipping tests and cabinet/API contracts

**Risk / Validation Lane**: `high-risk-feature` — external AI contract, result integrity, Postgres migration, Temporal recovery and degraded-state UX are all in scope. Full Spec Kit, clarify/checklists, focused quickstart and repository CI are required.

**Release Gate**: `no deploy` — this slice changes code and migration design but does not authorize production rollout. A later release must verify exact master SHA, run the deployment dry-run and receive separate approval.

**Target Platform**: GRAF server/worker in the existing Docker deployment, browser cabinet and embedded desktop meeting review; MediaScribe v0.5.3 server boundary

**Project Type**: Multi-tenant web service with durable backend worker and shared cabinet projections

**Performance Goals**: Do not add polling per countdown tick or a second provider request per result row. Preserve provider retry hints, keep import O(n) over provider segments/words and keep status projections within existing request budgets.

**Constraints**: MediaScribe credentials server-side only; `/v1` only; no client-side provider block merging; same idempotency key/body for uncertain upload; tenant/revision/deletion fences; no raw result/audio/secret in ordinary logs, analytics or Temporal indexes; preserve legacy rows.

**Scale/Scope**: Existing multi-tenant meeting processing path and its browser/embedded review surfaces. One additive nullable JSON field is preferred over a new entity or service.

## Constitution Check

*GATE: Passed before Phase 0 research; re-check after Phase 1 design.*

- **AI/external dependency boundary**: Pass. MediaScribe remains a server-side owner-controlled dependency; no desktop egress or credential movement.
- **Data and deletion truth**: Pass. Words follow the existing result/deletion lineage and do not become a promise of deletion outside GRAF control.
- **Tenant isolation/RLS**: Pass with migration gate. The new JSON value is on an existing workspace/meeting/result-scoped table and must inherit current RLS and cleanup tests.
- **Temporal durability and determinism**: Pass. Provider I/O remains in Activities; provider hints become inputs to existing durable timers; no workflow wall-clock polling.
- **High-risk UX/accessibility**: Pass. Existing Feature 195 recovery and transcript gating are preserved and regression-tested; no unrelated redesign.
- **Privacy/observability**: Pass. Words are meeting content and stay out of ordinary logs, analytics, Search Attributes and committed evidence. Existing approved internal Temporal/Langfuse policy is not broadened.
- **Ponytail**: Pass. Reuse existing DTO/import/store/workflow/projection code and add only the typed field, one nullable storage field, migration, tests and necessary role correction. No generated SDK, webhook, provider console or second retry service.

Post-design re-check: passed. The design is additive, backwards-compatible for old rows, provider-owned for segmentation, and does not require a Temporal architecture change unless focused tests identify one.

## Phase 0 Research Summary

See [research.md](research.md). The controlling evidence is the user-provided OpenAPI v1 plus client documentation and the directly fetched MediaScribe v0.5.3 tag. The current GRAF code already uses `/v1`, provider retry hints and durable Temporal waits.

## Phase 1 Design Summary

- [data-model.md](data-model.md) defines WordItem, provider block and result/recovery invariants.
- [contracts/mediascribe-v053-boundary.md](contracts/mediascribe-v053-boundary.md) defines the trusted provider boundary and safe GRAF projection.
- [contracts/temporal-processing.md](contracts/temporal-processing.md) preserves deterministic Activity/timer/update semantics.
- [quickstart.md](quickstart.md) defines focused contract, persistence, Temporal, user-visible and repository checks.

## Implementation Approach

1. Update content-free provider fixtures and contract tests first so the new behavior is executable.
2. Add `MediaScribeWordItem` and words validation; change omitted single-track role normalization from `incoming` to `mixed` with explicit dual-track degraded handling.
3. Add a nullable `words_json` column to `diarization_segments`, persist validated words through the existing fenced import and deletion paths, and preserve result hashing.
4. Audit canonical speaker/view/export projections. Keep provider rows as the source of block boundaries; change only code that actually merges or resegments them.
5. Re-run Feature 195 transcript/summary/recovery/Temporal contracts. Modify Temporal code only if v0.5.3 lifecycle signals reveal an uncovered state.
6. Complete security/infra/UX checklists, run quickstart and full local CI, then stop for explicit commit/release approval.

## Project Structure

### Documentation (this feature)

```text
specs/203-mediascribe-v053-integration/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── mediascribe-v053-boundary.md
│   └── temporal-processing.md
├── checklists/
│   ├── requirements.md
│   ├── infra.md
│   ├── security.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── mediascribe/{schemas.py,client.py,import_results.py}
├── processing/{store.py,results.py,submit.py}
├── workflows/{processing_workflow.py,worker.py}
├── db/models/processing.py
├── db/migrations/versions/0081_mediascribe_words.py
├── domain/speaker_turns.py
└── cabinet/{view_models.py,egress.py,rendering.py}

apps/server/tests/
├── fakes/mediascribe_v1.py
├── contract/test_mediascribe_client_contract.py
├── unit/{test_mediascribe_result_import.py,test_canonical_speaker_turns.py,test_processing_temporal_workflow.py}
└── integration/{test_mediascribe_processing_happy_path.py,test_cabinet_meeting_detail.py,test_transcript_export_egress.py}
```

**Structure Decision**: Keep the current GRAF server boundaries and add only one result-column migration. No new service, queue or frontend framework is justified.

## Validation Plan

The implementation must complete [quickstart.md](quickstart.md), all four checklists, `git diff --check` and `infra/scripts/ci-local.sh`. Focused checks must cover valid and malformed words, absent/null words, omitted source roles, provider block fidelity, summary independence, result idempotency, deletion/revision fences, Temporal replay/restart/manual races, no-content telemetry and UI parity. No `cd-remote.sh --execute` belongs to this slice.

## Complexity Tracking

No constitution violations. Intentional simplifications: no generated SDK, no webhook, no provider-side change, no word-highlight UI, no new retry service and no Temporal rewrite unless a failing contract proves it necessary.
