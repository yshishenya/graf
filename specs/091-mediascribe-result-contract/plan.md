# Implementation Plan: MediaScribe Result Contract

**Branch**: `091-mediascribe-result-contract` | **Date**: 2026-07-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/091-mediascribe-result-contract/spec.md`

## Summary

Update the server-owned MediaScribe processing pipeline so the new
`transcript_status` result field is the authoritative transcript indicator.
Persist terminal no-transcript input-audio outcomes distinctly from MediaScribe
service failures, keep unavailable transcripts out of summary/outcome
generation, and expose safe diagnostics and UI copy that explain no speech or
invalid audio without suggesting a MediaScribe outage.

## Technical Context

**Language/Version**: Python 3.13 FastAPI server, SQLAlchemy async models and Alembic migrations, Pydantic result schemas, pytest.

**Primary Dependencies**: Existing MediaScribe HTTP client, processing store/import pipeline, outcome service, cabinet view models, admin/cabinet artifact egress helpers. No new runtime dependency.

**Storage**: Existing Postgres tables plus nullable metadata columns for failure reason/source where the current schema cannot represent the new business outcome.

**Testing**: Focused server contract/unit/integration pytest coverage for MediaScribe client parsing, processing import/classification, outcome blocking, UI/view-model copy, artifact egress, and migration/model presence. Final repository gate is `infra/scripts/ci-local.sh`.

**Risk / Validation Lane**: High-risk feature. It touches MediaScribe, AI/outcome gating, diagnostics, user-facing unavailable states, Postgres schema, and shared processing behavior.

**Release Gate**: No deploy. This slice prepares implementation and local evidence only; production deploy remains a separate release/deploy lane with explicit approval.

**Target Platform**: Linux/containerized GRAF server and browser/embedded cabinet surfaces. macOS capture behavior is a regression boundary only.

**Project Type**: Server web/API service with background processing worker.

**Performance Goals**: No additional MediaScribe network call is introduced for unavailable transcripts. Result import remains one poll/result transaction plus existing DB writes.

**Constraints**: No raw audio, raw transcript text, signed URLs, object keys, credentials, or private meeting content in logs/tests/evidence. Browser and desktop clients still never receive MediaScribe credentials or external job identifiers.

**Scale/Scope**: One contract update for MediaScribe result/poll handling. No new transcript regeneration, no live MediaScribe download proxy, no production deployment.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Before Phase 0**: PASS with high-risk gates.

- Capture-first MVP integrity: PASS. No macOS capture, audio routing, recording controls, or local upload queue behavior changes.
- Visible consent and user control: PASS. The change is post-processing only and does not add hidden capture or automatic recording.
- Data boundary and secret discipline: PASS with required tasks. MediaScribe remains server-side; diagnostics are metadata-only and omit raw content, credentials, signed URLs, object keys, and external download URLs.
- Deletion truth and lifecycle accounting: PASS. The slice adds no new external egress or deletion promise; MediaScribe dependency truth remains represented as metadata.
- Spec-driven delivery: PASS. Full high-risk Spec Kit flow is used: specify, clarify, plan, checklist, tasks, analyze, issue sync, implement.
- UI and brand-distance: PASS. UI copy changes are small unavailable-state messages inside the existing GRAF cabinet system.
- Ponytail form: PASS. Reuse existing DTOs, store helpers, outcome service, egress state, and tests; add only minimal fields and classification helpers needed for the contract.

**After Phase 1 design**: PASS. The design keeps MediaScribe server-owned, introduces no new dependency, and records only safe diagnostic metadata.

## Validation Plan

- Run focused contract tests for MediaScribe client result/poll parsing.
- Run focused processing integration tests for available transcript, no recognizable speech, invalid audio payload, and service-origin failed jobs.
- Run focused outcome tests for blocked input-audio outcomes and no summary generation.
- Run focused cabinet/admin view-model or egress tests for unavailable transcript download state and Russian copy.
- Run Alembic/model migration checks that cover the new nullable columns.
- Run forbidden-content scan over the new spec, processing code, tests, and changelog.
- Run `infra/scripts/ci-local.sh` before closeout because this changes high-risk shared server behavior, schema, UI copy, diagnostics, and outcome gating.
- Do not run production CD dry-run/execute in this slice.

## Project Structure

### Documentation (this feature)

```text
specs/091-mediascribe-result-contract/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── mediascribe-result-contract.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   └── infra.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/mediascribe/
├── client.py
├── import_results.py
└── schemas.py

apps/server/src/twobrain_rec_server/processing/
├── audit.py
├── reasons.py
├── status.py
├── store.py
└── submit.py

apps/server/src/twobrain_rec_server/outcomes/
├── service.py
└── store.py

apps/server/src/twobrain_rec_server/db/
├── models/outcomes.py
├── models/processing.py
└── migrations/versions/0018_mediascribe_result_contract.py

apps/server/src/twobrain_rec_server/cabinet/
├── egress.py
├── rendering.py
└── view_models.py

apps/server/src/twobrain_rec_server/admin/files.py

apps/server/tests/
├── contract/test_mediascribe_client_contract.py
├── integration/test_mediascribe_processing_happy_path.py
├── integration/test_processing_failures.py
├── integration/test_meeting_outcomes_generation.py
├── unit/test_cabinet_view_models.py
└── unit/test_notes_action_truth_view_models.py

CHANGELOG.md
AGENTS.md
```

**Structure Decision**: Keep the contract update inside the existing server processing pipeline. Add one migration for nullable failure metadata instead of introducing a parallel diagnostics table or a new result-import abstraction.

## Complexity Tracking

No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
