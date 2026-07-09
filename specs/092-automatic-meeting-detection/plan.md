# Implementation Plan: Automatic Meeting Detection

**Branch**: `codex/092-automatic-meeting-detection` | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/092-automatic-meeting-detection/spec.md`

## Summary

Deliver the automatic meeting detection foundation for GRAF without hidden
capture or broad app inventory collection. The first implementation path is
server/admin first: accept metadata-only meeting-detection telemetry from desktop
clients, filter and aggregate likely VKS candidates, show them in the existing
admin surface, and publish reviewed target registry versions. The macOS client
then consumes the server-published registry with a last-good local cache,
records bounded local rollups, uploads only VKS-filtered candidates, and finally
uses Gilb-style macOS `AudioHAL` app ownership for native app detection.

Browser meeting detection is planned as macOS browser metadata plus calendar or
join intent; browser extensions remain future optional adapters. First prompt
capability is limited to verified targets such as Zoom and Yandex Telemost, with
target-scoped auto-record only after explicit user opt-in from a prompt.

## Technical Context

**Language/Version**: Python 3.13 FastAPI server, SQLAlchemy asyncio/Alembic,
Jinja2 admin templates, static admin/cabinet CSS, Swift 6 macOS app and XCTest.

**Primary Dependencies**: Existing FastAPI, Pydantic, SQLAlchemy, Alembic,
Postgres/SQLite test support, existing auth/session/device context, admin web
surface, XCTest, `JSONEncoder`/`JSONDecoder`, Foundation `Process` for macOS log
streaming. No new frontend build pipeline or native third-party telemetry SDK.

**Storage**: New Postgres/Alembic tables for meeting target registry versions,
registry targets, telemetry batches, target health rollups, unknown VKS
candidates, candidate review actions, denylist entries, rate-limit buckets, and
publish audit. macOS stores registry cache and telemetry rollups as JSON files in
`~/Library/Application Support/GRAF/MeetingDetection/`.

**Testing**: Server pytest unit/contract/integration tests, migration/RLS
coverage, forbidden-content scans, admin rendering tests, OpenAPI contract
coverage, macOS XCTest for registry validation/cache, telemetry rollup store,
candidate filter, parser fixtures, uploader policy, and detector state machine.

**Risk / Validation Lane**: High-risk product area. The feature touches capture
start eligibility, privacy-sensitive telemetry, diagnostics, admin UX, backend
storage/API contracts, and future auto-record settings. Full Spec Kit sequence,
mandatory checklists, analyze, GitHub issue sync, and repository gate are
required before implementation closeout.

**Release Gate**: No deploy in this feature slice. Production rollout,
telemetry enablement for real users, and release notes require a separate
release/deploy lane and explicit approval.

**Target Platform**: Server on Linux containers plus macOS desktop app. Windows
fingerprints stay future-only registry data and are not runtime-supported in this
slice.

**Project Type**: Cross-module server/API/admin/macOS desktop feature with a
shared detection registry and telemetry contract.

**Performance Goals**: Native macOS detector idle p95 CPU below 1% over 10
minutes, monitoring p95 below 2%, additional steady-state RSS below 30 MB, local
telemetry disk writes below 256 KB/day, one registry fetch/day, one telemetry
upload/day, and at most one immediate high-score candidate upload/day.

**Constraints**: No hidden recording. Active detector-assisted recording must
show visible local state and one-action Stop. Unknown apps never prompt or start
recording. Client must not upload all installed apps or all mic-using apps. No
raw unified-log lines, audio, transcript text, private URLs, meeting codes,
passcodes, attendee emails, raw IP addresses, credentials, tokens, signed URLs,
secret paths, app paths, or user home paths in telemetry, diagnostics, tests, or
admin views. Registry/telemetry failure must not block manual recording.

**Scale/Scope**: MVP registry contains all researched global/Russian VKS targets
with honest modes, but prompt-capable behavior starts with verified targets.
Telemetry payloads are bounded to 50 KB compressed and retained locally for 14
days or 1 MB. Admin review queue shows aggregate candidates, not raw event logs.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Before Phase 0**: PASS with high-risk gates.

- Capture-first MVP integrity: PASS with required tasks. The first server/admin
  slice does not alter capture. The later macOS detector can only produce
  candidates and must route prompt/recording through existing prerequisite gates.
- Visible consent and user control: PASS with required tasks. No hidden capture;
  detector-assisted recording requires visible local state, one-action Stop, user
  prompt or prior target-scoped auto-record opt-in, and settings revocation.
- Data boundary and secret discipline: PASS with required tasks. Telemetry is
  metadata-only and owner-server mediated; no MediaScribe credentials or direct
  audio egress from desktop are introduced.
- Deletion truth and lifecycle accounting: PASS with required tasks. Telemetry
  and registry artifacts are metadata-only operational data and need retention
  limits plus admin/audit accounting; no meeting-content deletion promise is
  broadened.
- Spec-driven delivery: PASS. Full sequence is required: specify, clarify, plan,
  checklist, tasks, analyze, taskstoissues, implement.
- UI and brand-distance: PASS with required tasks. Admin review uses existing
  GRAF admin design, no Krisp UI/assets/copy/behavior.
- Ponytail form: PASS. Reuse existing FastAPI/admin/Alembic/macOS JSON patterns;
  no new frontend framework, telemetry SDK, or broad app-scanning service.

**After Phase 1 design**: PASS. Research, data model, contracts, and quickstart
keep capture safety in compiled code, registry changes reviewed, telemetry
bounded, and unknown candidates non-prompting.

## Validation Plan

- Run contract tests for `POST /api/v1/desktop/meeting-detection/telemetry`,
  `GET /api/v1/desktop/meeting-detection/target-registry`, and admin review
  actions.
- Run server unit/integration tests for schema validation, idempotency, rate
  limiting, forbidden-content rejection, candidate aggregation, denylist
  suppression, registry draft/publish flow, admin audit events, and RLS/tenant
  isolation.
- Run admin rendering tests for `/admin/meeting-detection` and static asset
  contracts to keep the existing no-build frontend boundary.
- Run macOS XCTest for registry cache fallback, VKS-candidate scoring, forbidden
  payload construction, telemetry rollup retention, uploader backoff, synthetic
  `AudioHAL` parser fixtures, debounce state machine, and
  prompt policy.
- Run quickstart scenarios from [quickstart.md](./quickstart.md).
- Run `infra/scripts/ci-local.sh` before closeout because this slice touches
  high-risk server/API/admin/macOS behavior and data contracts.
- Do not run production deploy dry-run or execute in this slice.

## Project Structure

### Documentation (this feature)

```text
specs/092-automatic-meeting-detection/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── fingerprints.md
├── native-allowlist.md
├── registry-telemetry.md
├── contracts/
│   ├── meeting-detection-admin-review.schema.json
│   ├── meeting-detection-api.md
│   ├── meeting-detection-telemetry.schema.json
│   └── meeting-target-registry.schema.json
├── checklists/
│   ├── requirements.md
│   ├── security-privacy.md
│   ├── telemetry-diagnostics.md
│   ├── audio-capture.md
│   └── admin-ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/api/
├── meeting_detection.py
└── schemas.py

apps/server/src/twobrain_rec_server/meeting_detection/
├── __init__.py
├── admin_review.py
├── candidates.py
├── registry.py
├── telemetry.py
└── redaction.py

apps/server/src/twobrain_rec_server/admin/
├── meeting_detection.py
├── view_models.py
├── web.py
└── templates/admin/meeting_detection.html

apps/server/src/twobrain_rec_server/db/
├── models/meeting_detection.py
├── models/__init__.py
└── migrations/versions/0017_meeting_detection_registry.py

apps/server/tests/
├── contract/
│   ├── test_meeting_detection_api_contract.py
│   ├── test_meeting_detection_admin_contract.py
│   └── test_meeting_detection_no_secret_content.py
├── integration/
│   ├── test_meeting_detection_admin_review.py
│   ├── test_meeting_detection_migrations.py
│   ├── test_meeting_detection_registry.py
│   └── test_meeting_detection_telemetry.py
└── unit/
    ├── test_meeting_detection_candidates.py
    ├── test_meeting_detection_registry.py
    └── test_meeting_detection_redaction.py

apps/macos/RecApp/Sources/MeetingDetection/
├── MacOSMeetingActivityDetector.swift
├── MeetingDetectionTelemetryUploader.swift
├── MeetingDetectionTelemetryRollupStore.swift
└── MeetingDetectionSettingsStore.swift

apps/macos/RecApp/Sources/Capture/
├── CaptureControlView.swift
├── CaptureScopeApprovalService.swift
└── CaptureSessionController.swift

apps/macos/RecApp/Sources/Cabinet/
└── DesktopCabinetRoutePolicy.swift

apps/macos/RecApp/Sources/Calendar/
└── DesktopCalendarReminderService.swift

apps/macos/RecApp/Sources/Diagnostics/
└── DiagnosticBundleService.swift

apps/server/src/twobrain_rec_server/db/migrations/data/
└── 0019_meeting_target_registry.json

apps/macos/Shared/Sources/MeetingDetection/
├── MacOSAudioOwnershipParser.swift
├── MeetingDetectionCandidateFilter.swift
├── MeetingDetectionModels.swift
├── MeetingDetectionPolicy.swift
└── MeetingTargetRegistry.swift

apps/macos/Shared/Tests/
├── AppControlAccessibilityTests.swift
├── BrowserTargetEvidenceTests.swift
├── CaptureControlTests.swift
├── DesktopCabinetRoutePolicyTests.swift
├── DesktopCalendarReminderTests.swift
├── MacOSAudioOwnershipParserTests.swift
├── MeetingDetectionCandidateFilterTests.swift
├── MeetingDetectionPolicyTests.swift
├── MeetingDetectionTelemetryTests.swift
├── MeetingTargetRegistryTests.swift
└── SystemAudioPermissionUXTests.swift

CHANGELOG.md
AGENTS.md
```

**Structure Decision**: Build the server/admin safety surface before enabling the
macOS detector uploader. Keep registry and telemetry schemas shared by contract
but implemented with native project patterns on each side: Pydantic/SQLAlchemy
on the server, Codable/JSON file cache on macOS. Keep macOS detector logic in a
new `MeetingDetection` module rather than mixing it into capture services until
policy explicitly starts recording through existing gates.

## Complexity Tracking

No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
