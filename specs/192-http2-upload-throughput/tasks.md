# Tasks: Быстрая загрузка файлов через production edge

**Input**: Design documents from `/specs/192-http2-upload-throughput/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `quickstart.md`

**Tests**: The selected high-risk infrastructure lane requires the focused source check, installer syntax/dry-run where safe, production evidence reconciliation and fast repository CI described in `quickstart.md`.

**Organization**: The feature is one independently deliverable user story and one minimal implementation task. No setup, schema, dependency or application-code tasks are required.

## Phase 1: User Story 1 - Быстрая загрузка записи (Priority: P1) MVP

**Goal**: Preserve the verified HTTP/2 upload throughput fix in repository source-of-truth without changing the server-mediated upload architecture.

**Independent Test**: Complete `specs/192-http2-upload-throughput/quickstart.md`; the repository contains one bounded directive, validation gates pass, and the result reconciles with the accepted real-client production upload.

- [X] T001 [US1] Add the bounded HTTP/2 body preread setting to `infra/nginx/rec.2brain.pro.conf`, document the operational change in `CHANGELOG.md`, and complete the validation in `specs/192-http2-upload-throughput/quickstart.md`

**Checkpoint**: Repository source can be safely installed without reverting the live throughput fix.

## Dependencies & Execution Order

- **User Story 1**: No code or data prerequisites; T001 is the complete MVP.
- **Parallel opportunities**: None. The one-task slice is intentionally sequential and avoids coordination overhead.

## Implementation Strategy

1. Apply the one-line Nginx source change and one changelog entry.
2. Run the focused checks and existing fast CI gate.
3. Reconcile the repository setting with the already completed production evidence.
4. Do not add direct-to-MinIO upload, dependencies, helpers or a new test framework.
