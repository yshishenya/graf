# Implementation Plan: Own Media Upload Processing

**Branch**: `codex/087-own-media-upload-processing` | **Date**: 2026-07-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/087-own-media-upload-processing/spec.md`

## Summary

Add an API-first manual media upload path that accepts one owner-provided media
file, stores it as a single accepted media source, starts the existing
processing workflow, submits that single source to MediaScribe's base
one-track transcription endpoint, imports transcript/summary metadata, and
reuses existing generated outcomes and cabinet review. Keep the desktop
dual-track path unchanged.

## Technical Context

**Language/Version**: Python 3.13 FastAPI server with SQLAlchemy/Alembic;
existing macOS Swift upload code remains unchanged.

**Primary Dependencies**: FastAPI, `python-multipart`, Pydantic, SQLAlchemy,
MinIO storage wrapper, Temporal workflow helper, existing `httpx`
MediaScribe client. No new dependency.

**Storage**: Existing Postgres tables for meetings, media revisions, upload
sessions, track artifacts, processing workflows/results/outcomes, plus a small
nullable MediaScribe job schema extension for one-track provenance. Existing
MinIO object storage remains the media store.

**Testing**: Server pytest focused on ingest/finalize, MediaScribe request
mapping, processing pickup/submit/import, migration/model shape, cabinet review
reuse, and existing dual-track regressions. Repository closeout gate:
`infra/scripts/ci-local.sh`.

**Risk / Validation Lane**: Significant/high-risk feature. It touches user
upload, object storage, MediaScribe, processing, transcript content, generated
outcomes, DB schema, and review readiness.

**Release Gate**: No deploy in this slice. Release/deploy requires a later
explicit release lane.

**Target Platform**: Linux containerized backend and browser/API clients. macOS
desktop upload remains a regression surface only.

**Project Type**: Web/API service with existing server-owned cabinet review.

**Performance Goals**: V1 accepts files within existing package/track limits,
does not load media bytes before size checks where existing upload helpers can
avoid it, and does not create duplicate dependency submissions on retry.

**Constraints**: No desktop MediaScribe egress, no client-visible dependency
secret or signed URL, no raw transcript/audio in logs or evidence, no new
transcoding dependency, no production deploy.

**Scale/Scope**: One authenticated owner upload at a time through existing
server limits. Bulk import, resumable browser UI, local transcoding, transcript
editing, and production rollout are out of scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Before Phase 0**: PASS with high-risk gates.

- Capture-first MVP integrity: PASS. The slice does not change native capture,
  record/stop, routing, or desktop upload queue behavior.
- Visible consent and user control: PASS. Manual upload is explicit user action
  and does not add hidden capture.
- Data boundary and secret discipline: PASS with guard. MediaScribe remains
  server-side only; no dependency secret or signed URL is exposed.
- Deletion truth and lifecycle accounting: PASS with required tasks. Uploaded
  media, transcript/results/outcomes, workflows, and dependency state must stay
  in existing lifecycle accounting.
- Spec-driven delivery: PASS. 087 uses full Spec Kit path.
- Ponytail form: PASS. Reuse existing ingest, storage, processing, import,
  outcomes, and review contracts; no new dependency; no separate pipeline.

**After Phase 1 design**: PASS. Contracts and tasks keep the one-track change
adjacent to existing processing selection instead of introducing a parallel
system.

## Validation Plan

- Run focused server tests for manual media upload/finalize, one-track
  MediaScribe request mapping, one-track processing/import/outcomes, duplicate
  retry, and dual-track regression.
- Run migration/model focused checks for nullable/single-track MediaScribe job
  provenance.
- Run no-secret/no-private-path checks in touched tests/evidence.
- Run feature quickstart commands.
- Run `infra/scripts/ci-local.sh` before closeout.
- Do not run production CD dry-run/execute in this slice.

## Project Structure

### Documentation (this feature)

```text
specs/087-own-media-upload-processing/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── one-track-media-upload-contract.md
├── checklists/
│   ├── requirements.md
│   ├── api.md
│   ├── security.md
│   └── infra.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/api/
apps/server/src/twobrain_rec_server/ingest/
apps/server/src/twobrain_rec_server/mediascribe/
apps/server/src/twobrain_rec_server/processing/
apps/server/src/twobrain_rec_server/db/models/
apps/server/src/twobrain_rec_server/db/migrations/versions/
apps/server/tests/contract/
apps/server/tests/integration/
apps/server/tests/unit/
CHANGELOG.md
AGENTS.md
```

**Structure Decision**: Use existing backend modules. Add only the smallest new
API/service helpers needed for one-file upload and source-mode selection.

## Complexity Tracking

No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
