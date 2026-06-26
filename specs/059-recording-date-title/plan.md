# Implementation Plan: Recording Date And Smart Title

**Branch**: `codex/059-recording-date-title` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/059-recording-date-title/spec.md`

## Summary

Populate real recording dates and minimal initial meeting titles for new recordings while the frontend is being refactored. The smallest safe approach is to reuse the existing local manifest timing fields and existing server `Meeting.title`, `started_at`, and `ended_at` fields, then add only the missing already-available app/date or generic fallback metadata needed for idempotency and future safe filenames. Calendar integration is deferred to feature 060; window title collection is deferred to a later privacy-sensitive slice.

## Technical Context

**Language/Version**: Swift 6.0 package targeting macOS 14+ for local recording/upload metadata; Python >=3.13 for server ingest/cabinet tests.

**Primary Dependencies**: Existing local recording manifest writer, desktop upload queue/client, FastAPI ingest API, server-rendered cabinet, existing pytest/XCTest coverage. No calendar, window-title, new app-observer, or new permission dependency is planned in 059.

**Storage**: Existing local recording package manifest and desktop upload queue JSON for title provenance; existing server `meetings.title`, `meetings.started_at`, and `meetings.ended_at` columns for visible meeting metadata. Server-side provenance is optional only where an existing metadata-only path already supports it. Do not rename storage object keys or required local track files.

**Testing**: Focused Swift tests for manifest metadata, minimal title resolver including the 500 ms budget, upload queue/client payloads, and idempotent retries; focused server pytest for create-meeting date/title persistence, cabinet list/detail rendering, legacy fallback, search/sort, and contract drift if API schemas change.

**Risk / Validation Lane**: high-risk-feature. The feature touches local recording metadata, desktop upload identity, user-facing review UI, evidence rules, and explicit deferral of privacy-sensitive calendar/window metadata.

**Release Gate**: implementation closeout requires focused quickstart
validation plus `infra/scripts/ci-local.sh`; release/deploy/app-bundle evidence
is separate from local implementation readiness and must be recorded before any
production claim.

**Target Platform**: macOS desktop app plus web/embedded cabinet review surfaces.

**Project Type**: Hybrid native macOS capture/upload client plus server-rendered web cabinet.

**Performance Goals**: Title/date resolution completes before upload enqueue/create-meeting without delaying stop finalization by more than 500 ms in normal local cases. No calendar lookup, window-title lookup, or live foreground polling runs in 059.

**Constraints**: Metadata-only diagnostics; no raw URLs, participant emails, tokens, transcript text, audio, signed URLs, raw window titles, calendar event data, or live local paths in committed evidence. Preserve visible recording controls, upload idempotency, deletion accounting, and clean-room distance from KRISP.

**Scale/Scope**: One metadata/title slice for new recordings and legacy fallbacks. No broad frontend rewrite, no new rename UI/API, no download/export implementation, no transcript-derived title inference, no calendar lookup/connector, no new app/window observer, and no window-title collection in 059.

## Constitution Check

- **Capture-first MVP integrity**: PASS. The slice does not change capture mechanics, routing, audio tracks, or recording start/stop behavior.
- **Visible consent and user control**: PASS. Calendar/window metadata collection is not part of 059 and must be explicitly planned before any later slice collects it.
- **Data boundary and secret discipline**: PASS with guard. Title provenance is metadata-only; desktop still does not send audio to MediaScribe and no secrets are introduced.
- **Deletion truth and lifecycle accounting**: PASS. Titles and safe basenames do not become storage identity and do not alter deletion accounting.
- **Spec-driven delivery with testable gates**: PASS. Feature uses full Spec Kit planning because it is privacy-sensitive UX/data work.
- **Brand-distance UX**: PASS. KRISP is used as clean-room behavior benchmark only; copy, visuals, and implementation remain original.

## Validation Plan

- Run focused Swift tests for minimal title resolver, manifest metadata compatibility, upload queue item construction, upload client create-meeting payload, and retry idempotency.
- Run focused server tests for `POST /meetings` date/title persistence, cabinet list/detail rendering, date label fallback, title search, started-date sort, timezone-change fixtures, title identity compatibility, and legacy meetings without metadata.
- Run a metadata-only forbidden-content scan over feature evidence and fixtures before closeout.
- Run `infra/scripts/ci-local.sh` before PR/merge when implementation is in scope.
- `cd-remote.sh` deploy evidence is required only for the release/deploy
  closeout gate, not for the local implementation-readiness claim.

## Project Structure

### Documentation (this feature)

```text
specs/059-recording-date-title/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── recording-metadata-contract.md
└── checklists/
    ├── requirements.md
    └── privacy-ux.md
```

### Source Code (expected implementation touchpoints)

```text
apps/macos/Shared/Sources/Models/AudioModels.swift
apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift
apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift
apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift
apps/macos/RecApp/Sources/Upload/RecordingMetadataResolver.swift
apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift
apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift
apps/macos/Shared/Tests/RecordingMetadataResolverTests.swift
apps/macos/Shared/Tests/LocalRecordingManifestTests.swift
apps/macos/Shared/Tests/DesktopUploadQueueTests.swift
apps/macos/Shared/Tests/DesktopUploadClientTests.swift

apps/server/src/twobrain_rec_server/api/problems.py
apps/server/src/twobrain_rec_server/main.py
apps/server/src/twobrain_rec_server/ingest/meetings.py
apps/server/src/twobrain_rec_server/cabinet/queries.py
apps/server/src/twobrain_rec_server/cabinet/view_models.py
apps/server/src/twobrain_rec_server/cabinet/rendering.py
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html
apps/server/tests/contract/test_cabinet_no_secret_content_egress.py
apps/server/tests/integration/test_ingest_happy_path.py
apps/server/tests/integration/test_cabinet_meeting_list.py
apps/server/tests/unit/test_cabinet_view_models.py
```

**Structure Decision**: Reuse the existing manifest, upload queue, ingest API, and cabinet list/detail paths. Add the minimum local app/date/generic title resolver surface needed to feed existing server title/date fields; app/platform context may only come from already-available approved metadata, otherwise use the generic fallback. Avoid a new server title service, app/window observer, calendar connector, rename UI/API, export implementation, or frontend state layer.

## Phase 0: Research

See [research.md](./research.md).

## Phase 1: Design And Contracts

See [data-model.md](./data-model.md), [contracts/recording-metadata-contract.md](./contracts/recording-metadata-contract.md), and [quickstart.md](./quickstart.md).

## Post-Design Constitution Check

All initial constitution gates remain PASS. The plan deliberately avoids renaming track files/object keys, avoids transcript-derived titles, defers calendar title use to feature 060, and defers window title collection to a later privacy-sensitive slice.

## Complexity Tracking

No constitution violations or extra architecture layers.
