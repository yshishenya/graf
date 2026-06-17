# Quickstart: Recording Sync And Transcription Loop

Date: 2026-06-18

## Purpose

Validate the `042` MVP loop end to end:

1. macOS records locally while offline;
2. local package and upload queue survive restart;
3. upload reconciles from server truth and resumes;
4. server accepts one logical meeting and one initial media revision;
5. processing starts/reuses one workflow;
6. transcript appears in web and embedded desktop review;
7. evidence remains metadata-only.

## Prerequisites

- macOS development environment with Swift 6 toolchain.
- Server Python environment through `uv`.
- Docker available for compose validation when running full local gate.
- No live MediaScribe credentials in the repository or evidence.
- Use synthetic recordings/transcripts for automated tests.

## Local Contract Tests

Run macOS focused tests:

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'DesktopUploadQueueTests|CaptureControlTests|LocalRecordingManifestTests'
```

Run server focused tests:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_ingest_openapi_contract.py \
  tests/contract/test_processing_status_contract.py \
  tests/contract/test_cabinet_contract.py \
  tests/integration/test_upload_resume.py \
  tests/integration/test_processing_pickup.py \
  tests/integration/test_processing_result_idempotency.py \
  tests/integration/test_cabinet_meeting_detail.py
```

Run tenant-isolation focused tests when media-revision tables are added:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/integration/test_rls_meeting_content_policies.py \
  tests/integration/test_rls_worker_context.py
```

Expected:

- upload resume tests prove server-authoritative accepted ranges;
- processing pickup tests prove duplicate workflow reuse;
- cabinet tests prove transcript/review status is content-safe and authorized.
- RLS tests prove new revision-owned tables follow tenant isolation rules.

## Full Local Gate

```sh
infra/scripts/ci-local.sh
```

Expected:

- server tests pass;
- server lint passes;
- macOS tests pass;
- compose config renders.

## Manual Scenario 1: Offline Recording Retained

1. Disable network before pressing Record.
2. Start and stop a short meeting recording.
3. Restart the desktop app.
4. Open the local queue.

Expected:

- package remains visible;
- queue item keeps the same `directoryId`, `sessionId`, and
  `localMediaRevisionId`;
- no server success is claimed;
- upload state is queued/retrying/local-only with safe reason.

Evidence allowed:

- queue status labels;
- metadata-safe ids;
- byte counts and checksums;
- no local absolute paths in committed evidence.

## Manual Scenario 2: Reconnect And Resume Upload

1. Start upload with network available.
2. Interrupt network mid-upload.
3. Restore network.
4. Let automatic retry run or press manual retry.

Expected:

- desktop reconciles with server sync state;
- accepted bytes/ranges are reused;
- only missing ranges upload;
- finalization creates/reuses one meeting and one initial media revision;
- no duplicate upload session or processing job is created for retries.

## Manual Scenario 2a: Upload UI Dismissal Does Not Lose Local Media

1. Start upload with a local recording package selected or queued.
2. Close the upload/progress surface, navigate away, or quit the app before the
   upload completes.
3. Reopen the app and upload queue.
4. Reconnect network if it was unavailable.

Expected:

- local package remains present until explicit retention/deletion policy says
  otherwise;
- queue item keeps the same `directoryId`, `localMediaRevisionId`, server ids
  already learned, and accepted-range truth;
- upload resumes or shows a safe blocked/retry state;
- ordinary modal dismissal never says or behaves as if the file was lost.

## Manual Scenario 3: Processing And Review

1. Finalize an accepted upload.
2. Trigger or wait for processing pickup.
3. Open `/meetings/{meeting_id}` in browser.
4. Open `/desktop/meetings/{meeting_id}` in the installed desktop app.

Expected:

- both surfaces show the same meeting id and media revision provenance;
- processing status transitions from submitted/processing to ready or partial;
- transcript and speaker/provenance truth match the accepted revision;
- notes/action truth remains deferred unless stored generated outcomes exist.

## Manual Scenario 4: Conflict Visibility

Simulate one conflict at a time:

- delete a local audio file before retry;
- change a local checksum after queue creation;
- remove/revoke server meeting access;
- return server expected metadata mismatch;
- force processing failure.
- expire auth/session after partial upload;
- return stale/revoked device identity;
- expire upload session after partial ranges are accepted;
- trigger dependency-unavailable responses for MinIO, Temporal, MediaScribe, or
  cabinet timeout.

Expected:

- item becomes blocked/manual-only or failed with metadata-safe reason;
- no unsafe finalize occurs;
- upload success and processing failure are shown separately;
- desktop does not silently create a duplicate meeting.

## Metadata-Only Evidence Scan

Evidence files and diagnostics must not contain:

- raw audio bytes;
- transcript text from real meetings;
- credentials, tokens, passwords;
- signed URLs;
- private local paths;
- private Krisp captures or account names.

Suggested scan before committing evidence:

```sh
rg -n 'BEGIN PRIVATE KEY|Bearer [A-Za-z0-9._-]+|X-Content-SHA256:|/Users/[^ ]+|transcript text|signedUrl|presigned|mediascribe.*key' \
  specs/042-recording-sync-transcription-loop docs/evidence apps/server/tests apps/macos/Shared/Tests
```

Review any hit manually. Synthetic fixture text is allowed only when clearly
marked as synthetic and not copied from a real meeting.
