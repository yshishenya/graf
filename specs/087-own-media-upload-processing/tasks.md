# Tasks: Own Media Upload Processing

**Input**: Design documents from `/specs/087-own-media-upload-processing/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/one-track-media-upload-contract.md`, `quickstart.md`

**Tests**: Required by the significant/high-risk validation lane. Write each
behavior test first and verify it fails before the matching implementation.

**Organization**: Tasks are grouped by independently testable user stories.

## Phase 1: Setup And Guardrails

**Purpose**: Lock the feature scope before production code.

- [X] T001 [P] Add one-track and mixed-track manifest validation tests in `apps/server/tests/unit/test_manifest_validation.py`
- [X] T002 [P] Add MediaScribe one-track request mapping tests in `apps/server/tests/unit/test_mediascribe_request_mapping.py`
- [X] T003 [P] Add manual media upload contract coverage in `apps/server/tests/contract/test_ingest_openapi_contract.py`
- [X] T004 [P] Add manual media upload integration coverage in `apps/server/tests/integration/test_manual_media_upload.py`
- [X] T005 [P] Add one-track processing/retry coverage in `apps/server/tests/integration/test_mediascribe_submit.py`

---

## Phase 2: Foundational Provenance

**Purpose**: Add the single media source vocabulary and durable provenance that
both upload and processing need.

- [X] T006 Add the `media` track role in `apps/server/src/twobrain_rec_server/domain/statuses.py`
- [X] T007 Update single-track finalize validation in `apps/server/src/twobrain_rec_server/ingest/manifest.py`
- [X] T008 Extend MediaScribe job provenance in `apps/server/src/twobrain_rec_server/db/models/processing.py`
- [X] T009 Add the matching Alembic migration in `apps/server/src/twobrain_rec_server/db/migrations/versions/`

**Checkpoint**: Existing dual-track validation still rejects incomplete desktop packages, while `manifest + media` is a valid one-track package.

---

## Phase 3: User Story 1 - Upload One Media File (Priority: P1)

**Goal**: An authenticated owner can submit one media file and receive a normal
meeting/upload/processing status without the macOS recorder.

**Independent Test**: `apps/server/tests/integration/test_manual_media_upload.py`

- [X] T010 Add manual upload response schemas in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T011 Implement `POST /api/v1/media-uploads` in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [X] T012 Reuse existing ingest helpers for meeting creation, upload session, object storage, finalize, and workflow dispatch in `apps/server/src/twobrain_rec_server/api/ingest.py`

**Checkpoint**: A small media file reaches `ingested_pending_processing` with exactly one retained `media` artifact.

---

## Phase 4: User Story 2 - Process Through One-Track Transcription (Priority: P1)

**Goal**: Accepted manual media uploads submit exactly one stored file to the
one-track MediaScribe endpoint and import results through existing review data.

**Independent Test**: `apps/server/tests/integration/test_mediascribe_submit.py`

- [X] T013 Add `submit_single_track` in `apps/server/src/twobrain_rec_server/mediascribe/client.py`
- [X] T014 Add processing source-mode selection in `apps/server/src/twobrain_rec_server/processing/store.py`
- [X] T015 Update processing pickup eligibility in `apps/server/src/twobrain_rec_server/processing/pickup.py`
- [X] T016 Update processing submission and retry behavior in `apps/server/src/twobrain_rec_server/processing/submit.py`
- [X] T017 Update fake MediaScribe support in `apps/server/tests/fakes/fake_mediascribe.py`

**Checkpoint**: One-track jobs persist `request_mode=single_track` and reuse a stored external job id on retry.

---

## Phase 5: User Story 3 - Preserve Dual-Track Recording Behavior (Priority: P1)

**Goal**: Existing desktop upload and dual-track processing behavior remains unchanged.

**Independent Test**: Existing dual-track ingest and processing tests.

- [X] T018 Run and keep existing dual-track regression coverage in `apps/server/tests/integration/test_recording_sync_processing.py`
- [X] T019 Run and keep existing dual-track happy-path coverage in `apps/server/tests/integration/test_mediascribe_processing_happy_path.py`

---

## Phase 6: Polish And Validation

**Purpose**: Close the high-risk slice with traceable evidence and no release.

- [X] T020 Update `CHANGELOG.md` with manual media upload processing behavior and no-deploy scope
- [X] T021 Run focused validation from `specs/087-own-media-upload-processing/quickstart.md`
- [X] T022 Run `infra/scripts/ci-local.sh` before implementation closeout
- [X] T023 Record selected lane, validation evidence, and out-of-scope deploy note in the final response

---

## Dependencies & Execution Order

1. Phase 1 tests precede production implementation.
2. Phase 2 blocks both user stories because track role and job provenance are shared.
3. User Story 1 and User Story 2 integrate through existing processing workflow and should be validated together after their independent tests pass.
4. User Story 3 regression runs after the one-track changes.
5. Phase 6 runs after all behavior tasks are complete.

## Parallel Opportunities

- T001-T005 can be authored in parallel because they touch different test files.
- T006-T009 are sequential for implementation because model/migration and validation vocabulary should align.
- T013-T017 are mostly parallel by file, then must be verified together through processing tests.

## Notes

- Do not introduce a new transcoding dependency in this slice.
- Do not expose MediaScribe credentials, dependency URLs, object keys, private filenames, raw audio, or transcript text in API responses, diagnostics, docs, or evidence.
- Do not deploy from this slice.
