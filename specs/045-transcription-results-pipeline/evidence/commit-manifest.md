# Commit Manifest: 045 Transcription Results Pipeline

**Feature**: `045-transcription-results-pipeline`
**Date**: 2026-06-24

This manifest records the intended 045 commit boundary before any
approval-gated staging or commit action.

## Intended 045 Include Set

### Product Code

- `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`
- `apps/macos/Shared/Sources/Models/AudioModels.swift`
- `apps/server/src/twobrain_rec_server/api/ingest.py`
- `apps/server/src/twobrain_rec_server/api/schemas.py`
- `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- `apps/server/src/twobrain_rec_server/cabinet/web.py`
- `apps/server/src/twobrain_rec_server/ingest/desktop_sync.py`
- `apps/server/src/twobrain_rec_server/ingest/processing_dispatch.py`
- `apps/server/src/twobrain_rec_server/processing/pickup.py`
- `apps/server/src/twobrain_rec_server/processing/store.py`

### Product Tests

- `apps/macos/Shared/Tests/DesktopCabinetUploadLinkTests.swift`
- `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`
- `apps/macos/Shared/Tests/LocalRecordingLeakageFinalizationTests.swift`
- `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`
- `apps/server/tests/contract/test_cabinet_no_secret_content_egress.py`
- `apps/server/tests/contract/test_ingest_openapi_contract.py`
- `apps/server/tests/contract/test_processing_status_contract.py`
- `apps/server/tests/contract/test_rls_evidence_contract.py`
- `apps/server/tests/fixtures/processing.py`
- `apps/server/tests/integration/test_cabinet_meeting_detail.py`
- `apps/server/tests/integration/test_cabinet_web_access_states.py`
- `apps/server/tests/integration/test_degraded_ingest.py`
- `apps/server/tests/integration/test_deletion_lifecycle_blocks_access.py`
- `apps/server/tests/integration/test_finalize_integrity.py`
- `apps/server/tests/integration/test_finalize_processing_autostart.py`
- `apps/server/tests/integration/test_mediascribe_processing_happy_path.py`
- `apps/server/tests/integration/test_processing_pickup.py`
- `apps/server/tests/integration/test_recording_sync_conflicts.py`
- `apps/server/tests/integration/test_transcription_orchestration_benchmark.py`
- `apps/server/tests/unit/test_cabinet_view_models.py`
- `apps/server/tests/unit/test_cabinet_web_shell.py`

### Spec Kit And Product Documentation

- `AGENTS.md`
- `CHANGELOG.md`
- `docs/audio-capture-backlog.md`
- `docs/current-product-status.md`
- `docs/post-mvp-editing-media-backlog.md`
- `specs/012-server-ingest-foundation/contracts/openapi.yaml`
- `specs/025-system-audio-capture-pivot/evidence/artifact-matrix.md`
- `specs/025-system-audio-capture-pivot/evidence/cpu-gates.md`
- `specs/025-system-audio-capture-pivot/evidence/driver-parked.md`
- `specs/042-recording-sync-transcription-loop/spec.md`
- `specs/045-transcription-results-pipeline/**`

The three `025` evidence files are included only as supporting metadata-safe
runtime evidence from the 045 current-branch non-recording and permissioned
desktop proof attempts. They do not change the accepted `025` product behavior
or revive any driver path.

## Exclude From 045 Commit Unless Explicitly Approved

### Separate 044 Clean-Audio Track

- `specs/044-speakerphone-echo-noise-suppression/**`

Reason: this tree belongs to the real echo/noise suppression feature. It is
related context, but it is not required for the 045 transcription/results
implementation and should not be silently mixed into a 045 PR.

### Agent Working Plan

- `docs/superpowers/plans/2026-06-24-045-mvp-closeout.md`

Reason: this is a local execution plan artifact. Keep it out of the product PR
unless the owner explicitly wants internal agent closeout planning committed.

## Current Approval Boundary

No staging, commit, push, PR creation, merge, or production deploy should happen
until the owner explicitly approves that action.
