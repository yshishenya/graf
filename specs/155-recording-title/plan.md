# Implementation Plan: Meaningful Recording Titles

**Branch**: `155-recording-title` | **Date**: 2026-08-16 | **Spec**: [spec.md](spec.md)

## Summary

Restore the meaningful recording title already supplied by the macOS upload
metadata and project it consistently in the web cabinet, including the
embedded cabinet used by the macOS app. Automatic titles use calendar title,
source application title, or a dated generic fallback; user-confirmed and
manual-upload titles remain unchanged. Audio filenames and recording identity
are untouched.

## Technical Context

**Language/Version**: Python 3.11+ server; Swift 5.9+ macOS client (existing metadata contract only)

**Primary Dependencies**: FastAPI, SQLAlchemy, PostgreSQL; Swift Package Manager, SwiftUI/WebKit

**Storage**: Existing `meetings.title`, `meetings.title_source`, `started_at`, and `recording_display_timezone_offset_minutes`; no schema change

**Testing**: Focused pytest unit/integration tests; existing Swift metadata/upload tests; `swift test`, focused local Postgres tests, `infra/scripts/ci-local.sh`

**Risk / Validation Lane**: `high-risk-feature`; this changes privacy-sensitive meeting metadata presentation across owner and shared cabinet views, while preserving existing safe metadata filtering and lifecycle behavior

**Release Gate**: `no deploy`; release, signing, and production rollout are out of scope

**Target Platform**: macOS desktop app with embedded web cabinet plus browser web cabinet; Python web service

**Project Type**: native desktop app + web service

**Performance Goals**: title projection remains in existing in-memory view-model/rendering paths; no additional database query or network round trip

**Constraints**: reuse existing `safe_metadata_text`, title-source precedence, timezone offset, authorization, escaping, and lifecycle paths; no raw audio or filename mutation; no new dependency

**Scale/Scope**: Existing recording list/detail/shared-list projections and their focused tests; no new endpoint, entity, migration, or capture behavior

## Constitution Check

- **Capture-First MVP Integrity**: PASS — capture, upload, permissions, and audio artifacts are not changed.
- **Visible Consent And User Control**: PASS — no recording start/stop or indicator behavior changes.
- **Plaintext Observability For Internal MVP**: PASS — no new data egress or observability fields; existing safe metadata boundary remains in use.
- **Deletion Truth And Lifecycle Accounting**: PASS — title projection does not alter recording identity, artifacts, deletion state, or retained observability.
- **Public macOS Distribution And Update Integrity**: PASS — no packaging, signing, update, or release changes.
- **Spec-Driven Delivery**: PASS — clarify completed; checklist, research, design, tasks, and analyze precede implementation.

## Validation Plan

1. Run focused view-model unit tests for calendar, app-context, generic,
   user-confirmed, upload, unsafe, long, Unicode, and missing-timestamp titles.
2. Run focused cabinet integration tests proving the same projected title is
   used in web list/detail/shared surfaces and in the embedded desktop route.
3. Run existing Swift metadata and upload-contract tests to prove the client
   still sends the existing title/source fields and does not rename media.
4. Run the local CI gate `infra/scripts/ci-local.sh`; no deployment command is
   authorized by this feature.

## Project Structure

```text
specs/155-recording-title/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── recording-title.md
├── checklists/
│   └── requirements.md
└── tasks.md

apps/server/src/twobrain_rec_server/cabinet/view_models.py
apps/server/src/twobrain_rec_server/cabinet/queries.py
apps/server/src/twobrain_rec_server/cabinet/rendering.py
apps/server/tests/unit/test_cabinet_view_models.py
apps/server/tests/integration/test_cabinet_meeting_detail.py
apps/macos/RecApp/Sources/Upload/RecordingMetadataResolver.swift
apps/macos/Shared/Tests/RecordingMetadataResolverTests.swift
apps/macos/Shared/Tests/DesktopUploadClientTests.swift
```

**Structure Decision**: Keep the existing server-side presentation helper as
the single display boundary. The macOS app already embeds the same cabinet and
already sends the required metadata, so a native UI abstraction or new API is
unnecessary. Update only the shared projection and the smallest focused tests.

## Complexity Tracking

No constitution violations require an exception.
