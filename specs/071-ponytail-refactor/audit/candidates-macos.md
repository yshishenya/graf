# macOS Candidates

**Date**: 2026-06-30
**Scope**: `apps/macos/Package.swift`, Swift/C/C++ package source, validation scripts, installer scripts, and package tests.

## Static Evidence

- `Package.swift` has no remote dependencies.
- Full package validation passed with `706 tests, 0 failures`.
- Inventory found 265 tracked macOS source/script files under `Shared`, `RecApp`, `AudioDriver`, `Scripts`, and `Installer`.

## Candidate Decisions

### MAC-001: Large model files

Locations:

- `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`
- `apps/macos/Shared/Sources/Models/AudioModels.swift`

Decision: retained for now.

Reason:

- These files encode capture/audio state contracts and are covered by many capture, route, diagnostics, and upload tests.
- File size alone is not unused-code proof.

### MAC-002: Upload queue and custody files

Locations:

- `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
- `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`

Decision: retained for now.

Reason:

- These files protect local custody, upload reconciliation, deletion/purge truth, and metadata-only support reporting.
- Splitting tests or service code is possible later, but not a same-batch deletion.

### MAC-003: AudioDriver proof code

Locations:

- `apps/macos/AudioDriver/Sources/**`

Decision: retained.

Reason:

- The virtual driver is parked as future advanced-routing work, but proof code is product evidence and not an MVP runtime dependency to delete casually.
- Removing it would need product/backlog and safety evidence updates.

### MAC-004: macOS validation scripts

Locations:

- `apps/macos/Scripts/*.sh`
- `apps/macos/Installer/Scripts/*.sh`

Decision: retained.

Reason:

- Scripts are validation/release evidence entrypoints and passed shell syntax checks.

## Approved macOS Removals

None in the current audit pass.
