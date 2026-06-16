# Desktop Embedded Detail Evidence

Feature: `034-mvp-loop-readiness`

Status: `blocked_for_live_capture`

## Safe Evidence

- Command: `swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinet|DesktopLocalPurge'`
- Result: `28 passed`
- Captured: `2026-06-16`
- Scope: verifies meeting detail URL construction, route-policy blocking for native capture/governance paths, upload-to-review identity continuity, and terminal upload states that must not open a review destination.

## Live Capture Boundary

No live embedded meeting-detail screenshot is committed in this file. The launch claim stays bounded until a metadata-safe desktop embedded detail capture or an accepted blocker is available.

## Forbidden Content Boundary

This note contains no raw audio, transcript text, private email, signed URL, token, local user path, or private Krisp screenshot.
