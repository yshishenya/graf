# Current Code Surface Audit

This audit checks what the repository actually implements today, so the design
does not assume a product surface that already exists.

## macOS App

Primary files inspected:

- `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- `apps/macos/RecApp/Sources/AudioSetup/DriverSetupView.swift`
- `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationView.swift`
- `apps/macos/RecApp/Sources/AudioHealth/AudioHealthView.swift`

Current app structure:

- `ContentView` stacks `DriverSetupView`, `RouteVerificationView`,
  `CaptureControlView`, `AudioHealthView`, and `DiagnosticLogView`.
- Main window target is `minWidth: 720`, `minHeight: 620`.
- Header is `2brain Rec` plus a refresh icon and a snapshot summary.
- Capture controls support Record/Stop, local recording status, local path,
  upload queue summary, and live meters.
- Diagnostic/driver language is visible in the main first viewport.

Design implication:

- The current app is capture/diagnostics-capable but not product-ready.
- V6 desktop design must add the embedded cabinet as the main content surface
  and demote driver/route/diagnostic sections into recovery/settings.
- Current English copy in SwiftUI must not be the launch copy for the Russian
  MVP.

## Backend API

Primary files inspected:

- `apps/server/src/twobrain_rec_server/main.py`
- `apps/server/src/twobrain_rec_server/api/ingest.py`
- `apps/server/src/twobrain_rec_server/api/schemas.py`
- `apps/server/src/twobrain_rec_server/domain/statuses.py`

Implemented API shape:

- FastAPI app exposes health, auth, and ingest routers.
- Ingest endpoints cover meeting creation, upload session creation, track part
  upload, upload session status, missing ranges, finalization, and abort.
- Status enums currently cover ingest/upload states and a minimal processing
  placeholder: `not_submitted` and `pending_processing`.
- No full browser cabinet frontend is present in this worktree.

Design implication:

- Web cabinet is still a design/implementation gap, not an existing UI.
- V6 must specify product screens and contracts clearly enough for a future
  frontend implementation.
- Processing states needed by the product UI must align with the separate
  MediaScribe pipeline work, not be invented only in the design.

## Implementation Boundary For MVP

Native desktop must implement:

- Record/Stop and visible capture indicator.
- Permission recovery.
- Local recording artifact truth.
- Local upload queue truth.
- Tray/menu status.
- Embedded web host with route allowlist and fail-closed behavior.
- Diagnostics/recovery hidden behind secondary routes.

Server/web must implement:

- Meetings list and statuses.
- Manual media upload and metadata.
- Processing progress.
- Transcript review.
- Notes, decisions, action items.
- Speaker assignment lanes, naming, merge, and save conflicts.
- Account/session/policy surfaces.
- Browser handoffs for share, export, delete, billing, team, and admin.
